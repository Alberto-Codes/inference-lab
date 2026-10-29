import hashlib
import json
import shutil

import pytest
from test_receipt_commands import ROOT, command, script
from test_scaling import corpus


@pytest.fixture
def matrix(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    suite = script("shared_capacity_suite")
    runner = script("shared_capacity")
    reporter = script("report_shared_capacity")
    source = tmp_path / "matrix"
    source.mkdir()
    manifest, _pages = runner.load_inputs(corpus(tmp_path))
    settings = {**runner.DEFAULTS, "duration": 2.0, "burst_size": 2}
    order = suite.condition_order(1)
    (source / "protocol.json").write_text(
        json.dumps({"order": order, "settings": settings, "manifest": manifest})
    )
    for arm in order:
        path = source / arm["name"]
        condition = arm["condition"]
        runner.initialize(path, manifest, settings, condition)
        trace = runner.condition_trace(path, condition)
        for job in trace:
            rejected = (
                condition == "reserved"
                and job["consumer"] == "bulk"
                and job["sequence"] == 1
            )
            delay = 6.0 if condition == "fifo" else 1.0
            record = {
                **job,
                "status": "queue_expired" if rejected else "success",
                "policy_decision": "queue_expired" if rejected else "dispatched",
                "policy": condition,
                "text": "" if rejected else job["reference"],
                "e2e_s": delay,
                "queue_s": delay - 0.1,
                "finished_offset_s": job["scheduled_offset_s"] + delay,
                "dispatch_offset_s": None if rejected else job["scheduled_offset_s"],
            }
            filename = f"{job['index']:09}.json"
            (path / "terminal" / filename).write_text(json.dumps(record))
            (path / "decisions" / filename).write_text(
                json.dumps(
                    {
                        **job,
                        "decision": record["policy_decision"],
                        "policy": condition,
                        "terminal_offset_s": record["finished_offset_s"],
                        "dispatch_offset_s": record["dispatch_offset_s"],
                    }
                )
            )
            if not rejected:
                (path / "dispatch" / filename).write_text(
                    json.dumps(
                        {
                            **job,
                            "policy": condition,
                            "admission_offset_s": record["dispatch_offset_s"],
                        }
                    )
                )
        (path / "result.json").write_text(
            json.dumps(
                {
                    "capacity_eligible": True,
                    "elapsed_s": 10.0,
                    "reserved_idle_slot_s_with_bulk_waiting": 3.0
                    if condition == "reserved"
                    else 0.0,
                }
            )
        )
    return reporter, source


def test_report_preserves_trials_and_pairs_urgent_benefit_with_bulk_cost(matrix):
    reporter, source = matrix
    result = reporter.report(source)
    assert result["planned_order_valid"]
    assert result["planned_repetitions"] == 1
    assert len(result["trials"]) == 4
    pair = result["pairs"][0]
    assert pair["comparable"]
    assert pair["delta"]["urgent_deadline_attainment"] == 1.0
    assert pair["delta"]["bulk_normal_completions"] == -1
    assert pair["delta"]["bulk_completed_per_s_including_drain"] == pytest.approx(-0.1)
    assert pair["delta"]["bulk_completed_per_s_during_arrivals"] == pytest.approx(0.5)
    assert pair["delta"]["bulk_max_wait_s"] == pytest.approx(-5.0)
    assert pair["delta"]["reserved_idle_slot_s_with_bulk_waiting"] == 3.0
    assert pair["reserved"]["bulk_completion_time_s"] is None
    assert pair["delta"]["bulk_completion_time_s"] is None
    assert pair["reserved"]["bulk_unfinished_work"] == 1


def test_report_compares_each_mixed_policy_with_isolated_baselines(matrix):
    reporter, source = matrix
    result = reporter.report(source)
    comparisons = {
        (c["baseline"], c["policy"]): c for c in result["baseline_comparisons"]
    }
    assert set(comparisons) == {
        ("urgent", "fifo"),
        ("urgent", "reserved"),
        ("bulk", "fifo"),
        ("bulk", "reserved"),
    }
    assert result["comparable_baseline_comparisons"] == 4
    urgent_fifo = comparisons["urgent", "fifo"]
    assert urgent_fifo["arms"] == ["urgent-0", "fifo-0"]
    assert urgent_fifo["urgent"]["urgent_deadline_attainment"] == 1.0
    assert urgent_fifo["delta"]["urgent_deadline_attainment"] == -1.0
    assert all(key.startswith("urgent_") for key in urgent_fifo["delta"])
    assert comparisons["urgent", "reserved"]["delta"]["urgent_deadline_attainment"] == 0
    bulk_reserved = comparisons["bulk", "reserved"]
    assert bulk_reserved["delta"]["bulk_normal_completions"] == -1
    assert bulk_reserved["reserved"]["bulk_unfinished_work"] == 1
    assert all(key.startswith("bulk_") for key in bulk_reserved["delta"])


def test_missing_baseline_prevents_only_its_comparisons(matrix):
    reporter, source = matrix
    shutil.rmtree(source / "urgent-0")
    result = reporter.report(source)
    assert result["comparable_pairs"] == 1
    assert result["comparable_baseline_comparisons"] == 2
    for comparison in result["baseline_comparisons"]:
        assert comparison["comparable"] == (comparison["baseline"] == "bulk")
        if comparison["baseline"] == "urgent":
            assert comparison["delta"] is None
            assert comparison["exclusion_reasons"]


@pytest.mark.parametrize("state", ["missing", "partial", "uncertain"])
def test_report_retains_unmeasured_trials_without_capacity_comparison(matrix, state):
    reporter, source = matrix
    path = source / "reserved-0"
    if state == "missing":
        shutil.rmtree(path)
    elif state == "partial":
        next((path / "terminal").glob("*.json")).unlink()
    else:
        result_path = path / "result.json"
        runtime = json.loads(result_path.read_text())
        runtime["capacity_eligible"] = False
        result_path.write_text(json.dumps(runtime))
    result = reporter.report(source)
    assert len(result["trials"]) == 4
    assert result["comparable_pairs"] == 0
    assert result["pairs"][0]["delta"] is None
    assert result["pairs"][0]["exclusion_reasons"]
    trial = next(t for t in result["trials"] if t["name"] == "reserved-0")
    assert (
        trial["status"]
        == {"missing": "unmeasured", "partial": "partial", "uncertain": "ineligible"}[
            state
        ]
    )


@pytest.mark.parametrize("field", ["settings", "profile", "trace_sha256", "cache"])
def test_mismatched_mixed_arms_are_never_compared(matrix, field):
    reporter, source = matrix
    path = source / "reserved-0" / "plan.json"
    plan = json.loads(path.read_text())
    plan[field] = {"changed": True} if field in ("settings", "profile") else "changed"
    path.write_text(json.dumps(plan))
    result = reporter.report(source)
    assert result["comparable_pairs"] == 0
    assert result["pairs"][0]["delta"] is None
    assert any(field in reason for reason in result["pairs"][0]["exclusion_reasons"])


def test_invalid_order_is_reported_and_cannot_support_pair_comparison(matrix):
    reporter, source = matrix
    path = source / "protocol.json"
    protocol = json.loads(path.read_text())
    protocol["order"].reverse()
    path.write_text(json.dumps(protocol))
    result = reporter.report(source)
    assert not result["planned_order_valid"]
    assert result["planned_order"] == protocol["order"]
    assert result["comparable_pairs"] == 0


def test_cli_never_overwrites_report_or_raw_evidence(matrix, tmp_path):
    _reporter, source = matrix
    output = tmp_path / "report.json"
    original = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*")
        if path.is_file()
    }
    first = command("report_shared_capacity.py", "--input", source, "--output", output)
    assert first.returncode == 0, first.stderr
    raw = output.read_bytes()
    second = command("report_shared_capacity.py", "--input", source, "--output", output)
    assert second.returncode != 0
    assert output.read_bytes() == raw
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in original.items()
    )


def test_report_preserves_three_rotated_repetitions(matrix):
    reporter, source = matrix
    protocol_path = source / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    protocol["order"] = script("shared_capacity_suite").condition_order(3)
    for repeat in (1, 2):
        for condition in ("urgent", "bulk", "fifo", "reserved"):
            shutil.copytree(source / f"{condition}-0", source / f"{condition}-{repeat}")
    protocol_path.write_text(json.dumps(protocol))
    result = reporter.report(source)
    assert result["planned_order_valid"]
    assert result["planned_repetitions"] == 3
    assert result["comparable_pairs"] == 3
    assert len(result["trials"]) == 12
    assert [pair["repeat"] for pair in result["pairs"]] == [0, 1, 2]
    assert [trial["name"] for trial in result["trials"]][8:10] == [
        "reserved-1",
        "fifo-1",
    ]


def test_timeout_record_prevents_comparison_even_if_result_claims_eligibility(matrix):
    reporter, source = matrix
    for path in (source / "fifo-0" / "terminal").glob("*.json"):
        record = json.loads(path.read_text())
        if record["status"] == "success":
            record.update(status="timeout", backend_execution_unknown=True, text="")
            path.write_text(json.dumps(record))
            break
    result = reporter.report(source)
    assert result["comparable_pairs"] == 0
    assert result["pairs"][0]["delta"] is None

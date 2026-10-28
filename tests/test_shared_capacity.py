import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest
from test_receipt_commands import script
from test_scaling import corpus


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return script("shared_capacity"), script("score_shared_capacity")


def setup(tmp_path, modules, condition="fifo", **overrides):
    runner, scorer = modules
    manifest, pages = runner.load_inputs(corpus(tmp_path))
    settings = {
        **runner.DEFAULTS,
        "duration": 0.08,
        "urgent_rate": 25.0,
        "burst_size": 5,
        "burst_interval": 1.0,
        "concurrency": 2,
        "reserved": 1,
        "urgent_deadline": 0.025,
        "bulk_wait": 0.15,
        "timeout": 0.2,
        "drain": 0.2,
        "url": "http://test",
        **overrides,
    }
    output = tmp_path / condition
    runner.initialize(output, manifest, settings, condition)
    return runner, scorer, manifest, pages, settings, output


def run_measure(runner, pages, output, settings, condition, handler):
    async def run():
        async with httpx.AsyncClient(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ) as client:
            result = await runner.measure(client, pages, output, settings, condition)
        runner.save(output / "result.json", result)
        return result

    return asyncio.run(run())


def success():
    return httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": "Total 12.00"}, "finish_reason": "stop"}
            ]
        },
    )


def test_reservation_protects_urgent_with_same_trace_and_bounds(tmp_path, modules):
    runner, scorer, manifest, pages, settings, fifo = setup(tmp_path, modules)
    reserved = tmp_path / "reserved"
    runner.initialize(reserved, manifest, settings, "reserved")
    active = 0
    peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return success()

    run_measure(runner, pages, fifo, settings, "fifo", handler)
    run_measure(runner, pages, reserved, settings, "reserved", handler)
    first, second = scorer.summarize(fifo), scorer.summarize(reserved)
    assert first["trace_sha256"] == second["trace_sha256"]
    assert peak <= 2
    assert (
        second["consumers"]["urgent"]["deadline_met"]
        > first["consumers"]["urgent"]["deadline_met"]
    )
    assert second["runtime"]["reserved_idle_slot_s_with_bulk_waiting"] > 0
    assert first["consumers"]["urgent"]["scheduled"] == 2
    assert first["consumers"]["urgent"]["deadline_misses"] >= 1
    assert first["complete"] and second["complete"]
    assert len(list((reserved / "decisions").glob("*.json"))) == 7
    rows = [json.loads(p.read_text()) for p in (reserved / "terminal").glob("*.json")]
    dispatched = [r for r in rows if r["dispatch_offset_s"] is not None]
    for event in dispatched:
        instant = event["dispatch_offset_s"]
        concurrent = [
            r
            for r in dispatched
            if r["dispatch_offset_s"] <= instant < r["finished_offset_s"]
        ]
        assert sum(r["consumer"] == "bulk" for r in concurrent) <= 1
        assert len(concurrent) <= 2


def test_timeout_never_releases_unknown_backend_slot_for_new_work(tmp_path, modules):
    runner, scorer, _, pages, settings, output = setup(tmp_path, modules, timeout=0.01)
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(1)
        return success()

    result = run_measure(runner, pages, output, settings, "fifo", handler)
    report = scorer.summarize(output)
    assert calls == 2
    assert not result["capacity_eligible"]
    assert report["complete"]
    assert report["consumers"]["urgent"]["deadline_attainment"] == 0
    assert report["consumers"]["bulk"]["status_counts"]["backend_uncertain"] == 3
    assert report["consumers"]["bulk"]["completed_per_s_during_arrivals"] is None


def test_queue_expiry_and_drain_do_not_hide_unfinished_bulk(tmp_path, modules):
    runner, scorer, _, pages, settings, output = setup(
        tmp_path, modules, bulk_wait=0.01, drain=0.01, timeout=1.0
    )

    async def handler(request):
        await asyncio.sleep(1)
        return success()

    run_measure(runner, pages, output, settings, "fifo", handler)
    report = scorer.summarize(output)
    bulk = report["consumers"]["bulk"]
    assert report["complete"]
    assert bulk["status_counts"] == {"drain_timeout": 2, "queue_expired": 3}
    assert bulk["completion_time_s"] is None
    assert bulk["unfinished_work"] == 5


def test_frozen_assignments_include_71_and_reject_reserved_rows(modules):
    runner, _ = modules
    manifest = {
        "pages": [{"id": i, "sha256": str(i), "reference": "12"} for i in range(24, 80)]
    }
    trace = runner.make_trace(manifest, runner.DEFAULTS)
    assert len(trace) == 1500
    assert {r["id"] for r in trace if r["consumer"] == "urgent"} == set(range(24, 80))
    assert {r["id"] for r in trace if r["consumer"] == "bulk"} == set(range(24, 80))
    assert trace[0]["consumer"] == "bulk"
    assert trace[120]["consumer"] == "urgent"
    manifest["pages"].append({"id": 80})
    with pytest.raises(ValueError, match="Reserved"):
        runner.make_trace(manifest, runner.DEFAULTS)


def test_incomplete_evidence_denominator_and_trace_integrity(tmp_path, modules):
    _, scorer, _, _, _, output = setup(tmp_path, modules)
    report = scorer.summarize(output)
    assert not report["complete"]
    assert report["consumers"]["urgent"]["deadline_misses"] == 2
    assert report["consumers"]["bulk"]["missing_outcomes"] == 5
    (output / "trace.json").write_text("{}")
    with pytest.raises(ValueError, match="Trace hash"):
        scorer.summarize(output)


def test_execute_rejects_changed_settings_and_records_failed_warmup(tmp_path, modules):
    runner, scorer, manifest, pages, settings, output = setup(tmp_path, modules)
    with pytest.raises(ValueError, match="differs"):
        asyncio.run(
            runner.execute(output, manifest, pages, {**settings, "timeout": 2}, "fifo")
        )

    async def handler(request):
        return httpx.Response(503)

    result = asyncio.run(
        runner.execute(
            output, manifest, pages, settings, "fifo", httpx.MockTransport(handler)
        )
    )
    assert result["status"] == "warmup_failed"
    report = scorer.summarize(output)
    assert report["complete"] and not report["capacity_eligible"]
    assert report["consumers"]["urgent"]["deadline_attainment"] == 0
    with pytest.raises(ValueError, match="Never replay"):
        asyncio.run(runner.execute(output, manifest, pages, settings, "fifo"))


def test_success_transport_does_not_imply_ocr_correctness(tmp_path, modules):
    runner, scorer, _, pages, settings, output = setup(tmp_path, modules)

    async def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Total 99.00"}, "finish_reason": "stop"}
                ]
            },
        )

    run_measure(runner, pages, output, settings, "fifo", handler)
    report = scorer.summarize(output)
    assert report["consumers"]["bulk"]["normal_completions"] == 5
    assert report["consumers"]["bulk"]["numeric_recall"] == 0
    assert report["consumers"]["bulk"]["verified_correct_output_count"] is None
    record = json.loads(next((output / "terminal").glob("*.json")).read_text())
    assert "response_body" in record


def test_late_response_keeps_slot_and_counts_deadline_miss(tmp_path, modules):
    runner, scorer, _, pages, settings, output = setup(
        tmp_path, modules, condition="urgent"
    )

    async def handler(request):
        await asyncio.sleep(0.035)
        return success()

    run_measure(runner, pages, output, settings, "urgent", handler)
    report = scorer.summarize(output)
    assert report["capacity_eligible"]
    assert report["consumers"]["urgent"]["normal_completions"] == 2
    assert report["consumers"]["urgent"]["deadline_misses"] == 2
    assert report["consumers"]["urgent"]["timeouts"] == 0


def test_scorer_rejects_changed_policy_decision(tmp_path, modules):
    runner, scorer, _, pages, settings, output = setup(tmp_path, modules)

    async def handler(request):
        return success()

    run_measure(runner, pages, output, settings, "fifo", handler)
    path = next((output / "decisions").glob("*.json"))
    decision = json.loads(path.read_text())
    decision["decision"] = "queue_expired"
    path.write_text(json.dumps(decision))
    with pytest.raises(ValueError, match="Policy decision"):
        scorer.summarize(output)


def test_slow_evidence_write_cannot_send_expired_request(
    tmp_path, modules, monkeypatch
):
    runner, scorer, _, pages, settings, output = setup(
        tmp_path, modules, condition="urgent", duration=0.01, urgent_rate=1
    )
    original_save = runner.save

    def slow_save(path, value):
        if path.parent.name == "dispatch":
            time.sleep(0.04)
        original_save(path, value)

    monkeypatch.setattr(runner, "save", slow_save)
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return success()

    run_measure(runner, pages, output, settings, "urgent", handler)
    assert calls == 0
    assert scorer.summarize(output)["consumers"]["urgent"]["status_counts"] == {
        "queue_expired": 1
    }

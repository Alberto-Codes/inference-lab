import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from test_receipt_commands import ROOT, script
from test_scaling import corpus


@pytest.fixture
def prepared_suite(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    suite = script("shared_capacity_suite")
    monkeypatch.setattr(
        suite,
        "DEFAULTS",
        {**suite.DEFAULTS, "duration": 2.0, "burst_size": 2},
    )
    input_path = corpus(tmp_path)
    manifest_path = input_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["pages"] = []
    for index in range(24, 80):
        path = input_path / f"{index}.png"
        Image.new("RGB", (8, 8), (index, 0, 0)).save(path)
        manifest["pages"].append(
            {
                "id": index,
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "reference": "Total 12.00",
            }
        )
    manifest_path.write_text(json.dumps(manifest))
    output = tmp_path / "matrix"
    protocol = suite.prepare_suite(input_path, output)
    return suite, input_path, output, protocol


def test_isolated_baselines_precede_mixed_pairs_and_order_rotates(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    suite = script("shared_capacity_suite")
    assert [item["name"] for item in suite.condition_order(3)] == [
        "urgent-0",
        "bulk-0",
        "bulk-1",
        "urgent-1",
        "urgent-2",
        "bulk-2",
        "fifo-0",
        "reserved-0",
        "reserved-1",
        "fifo-1",
        "fifo-2",
        "reserved-2",
    ]


def test_primary_matrix_refuses_a_corpus_without_receipt_71(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    suite = script("shared_capacity_suite")
    with pytest.raises(ValueError, match="CORD rows 24 through 79"):
        suite.prepare_suite(corpus(tmp_path), tmp_path / "matrix")
    assert not (tmp_path / "matrix").exists()


def test_preparation_freezes_equal_traces_settings_and_source_bytes(prepared_suite):
    suite, _corpus, output, protocol = prepared_suite
    traces = []
    for arm in protocol["order"]:
        path = output / arm["name"]
        trace = (path / "trace.json").read_bytes()
        plan = json.loads((path / "plan.json").read_text())
        traces.append(trace)
        assert plan["trace_sha256"] == hashlib.sha256(trace).hexdigest()
        assert plan["settings"] == protocol["settings"]
        assert plan["manifest"] == protocol["manifest"]
        assert plan["condition"] == arm["condition"]
    assert len(set(traces)) == 1
    for name, digest in protocol["source_sha256"].items():
        frozen = (output / "frozen-source" / name).read_bytes()
        assert hashlib.sha256(frozen).hexdigest() == digest
        assert frozen == (suite.serving.ROOT / name).read_bytes()
    verified, manifest, pages = suite.verify_suite(output)
    assert verified == protocol
    assert manifest == protocol["manifest"]
    assert len(pages) == len(manifest["pages"])
    assert not (output / "run-started.json").exists()


@pytest.mark.parametrize("change", ["source", "manifest", "attempted", "trace"])
def test_changed_or_attempted_matrix_fails_before_service_interaction(
    prepared_suite, monkeypatch, change
):
    suite, input_path, output, protocol = prepared_suite
    handover = Mock(side_effect=AssertionError("GPU handover must not be entered"))
    monkeypatch.setattr(suite, "parser_session", handover)
    if change == "source":
        changed = {**protocol["source_sha256"], "scripts/changed.py": "different"}
        monkeypatch.setattr(suite, "source_hashes", lambda: changed)
        message = "Executable sources changed"
    elif change == "manifest":
        manifest_path = input_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["revision"] = "different-source-revision"
        manifest_path.write_text(json.dumps(manifest))
        message = "Corpus changed"
    elif change == "attempted":
        (output / "run-started.json").write_text("{}")
        message = "Matrix already attempted"
    else:
        (output / "fifo-0" / "trace.json").write_text('{"requests": []}')
        message = "Condition differs"
    with pytest.raises(ValueError, match=message):
        suite.run_suite(output, release_llama=True)
    handover.assert_not_called()


def test_run_requires_explicit_gpu_handover_authorization(prepared_suite, monkeypatch):
    suite, _corpus, output, _protocol = prepared_suite
    handover = Mock(side_effect=AssertionError("Unauthorized GPU handover"))
    monkeypatch.setattr(suite, "parser_session", handover)
    with pytest.raises(ValueError, match="explicit --release-llama authorization"):
        suite.run_suite(output, release_llama=False)
    handover.assert_not_called()
    assert not (output / "run-started.json").exists()


@pytest.mark.parametrize("failure", ["smoke", "arm"])
def test_failure_unwinds_handover_and_preserves_attempt_evidence(
    prepared_suite, monkeypatch, failure
):
    suite, _corpus, output, _protocol = prepared_suite
    events = []

    @contextmanager
    def handover(path, *, enabled):
        assert path == output
        assert enabled is True
        events.append("entered")
        try:
            yield
        finally:
            events.append("restored")

    async def fail_arm(*args):
        events.append("arm")
        raise RuntimeError("measured arm failed")

    monkeypatch.setattr(suite, "parser_session", handover)
    monkeypatch.setattr(suite, "snapshot", lambda path: events.append("snapshot"))
    smoke = Mock(
        return_value=SimpleNamespace(
            returncode=1 if failure == "smoke" else 0,
            stdout="mock GPU test output; no inference performed",
            stderr="mock smoke failure" if failure == "smoke" else "",
        )
    )
    monkeypatch.setattr(suite.subprocess, "run", smoke)
    archive = Mock()
    monkeypatch.setattr(suite, "archive_server", archive)
    monkeypatch.setattr(suite.serving, "stop", lambda: events.append("stop"))
    monkeypatch.setattr(suite.serving, "start", lambda: events.append("start"))
    monkeypatch.setattr(suite.serving, "inspect", lambda: {"test": "fake container"})
    monkeypatch.setattr(suite, "execute", fail_arm)
    message = (
        "Real GPU smoke test failed" if failure == "smoke" else "measured arm failed"
    )
    with pytest.raises(RuntimeError, match=message):
        suite.run_suite(output, release_llama=True)
    assert events[0] == "entered"
    assert events[-1] == "restored"
    assert (output / "run-started.json").exists()
    assert not (output / "summaries.json").exists()
    smoke_record = json.loads((output / "gpu-test.json").read_text())
    assert smoke_record["returncode"] == (1 if failure == "smoke" else 0)
    if failure == "smoke":
        assert "stop" not in events
        assert "arm" not in events
    else:
        assert events.index("stop") < events.index("start") < events.index("arm")
        archive.assert_any_call(output / "server-final.json")

import json
from types import SimpleNamespace

import httpx
import pytest

from inference_lab import local_gpu


@pytest.fixture
def handover(monkeypatch):
    actions = []
    monkeypatch.setattr(local_gpu.serving, "inspect", lambda: None)
    monkeypatch.setattr(
        local_gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0)
    )
    monkeypatch.setattr(local_gpu, "loaded_models", lambda client: ["previous-model"])
    monkeypatch.setattr(
        local_gpu, "service", lambda action: actions.append(("service", action))
    )
    monkeypatch.setattr(
        local_gpu.serving, "start", lambda: actions.append(("parser", "start"))
    )
    monkeypatch.setattr(
        local_gpu.serving, "stop", lambda: actions.append(("parser", "stop"))
    )
    monkeypatch.setattr(
        local_gpu, "restore_models", lambda c, m: actions.append(("models", m))
    )
    return actions


def test_failed_experiment_restores_original_models(tmp_path, handover):
    with (
        pytest.raises(ValueError, match="inference failed"),
        local_gpu.parser_session(tmp_path, True),
    ):
        raise ValueError("inference failed")
    assert handover == [
        ("service", "stop"),
        ("parser", "start"),
        ("parser", "stop"),
        ("service", "start"),
        ("models", ["previous-model"]),
    ]
    audit = json.loads((tmp_path / "lifecycle.json").read_text())
    assert audit["restoration_verified"]
    assert "inference failed" in audit["experiment_error"]


def test_failed_start_is_cleaned_up(tmp_path, handover, monkeypatch):
    def fail():
        raise RuntimeError("startup failure")

    monkeypatch.setattr(local_gpu.serving, "start", fail)
    with (
        pytest.raises(RuntimeError, match="startup failure"),
        local_gpu.parser_session(tmp_path, True),
    ):
        pytest.fail("must not run experiment")
    assert handover[-3:] == [
        ("parser", "stop"),
        ("service", "start"),
        ("models", ["previous-model"]),
    ]


def test_inactive_service_remains_inactive(tmp_path, handover, monkeypatch):
    monkeypatch.setattr(
        local_gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=3)
    )
    with local_gpu.parser_session(tmp_path, True):
        pass
    assert handover == [("parser", "start"), ("parser", "stop"), ("service", "stop")]


def test_both_failures_are_recorded(tmp_path, handover, monkeypatch):
    def fail(*args):
        raise RuntimeError("load failure")

    monkeypatch.setattr(local_gpu, "restore_models", fail)
    with (
        pytest.raises(RuntimeError, match="Restoration failed"),
        local_gpu.parser_session(tmp_path, True),
    ):
        raise ValueError("inference failure")
    audit = json.loads((tmp_path / "lifecycle.json").read_text())
    assert "inference failure" in audit["experiment_error"]
    assert "load failure" in audit["restoration_errors"][0]
    assert not audit["restoration_verified"]


def test_restore_waits_for_loaded_identity(monkeypatch):
    polls = []

    def respond(request):
        if request.url.path == "/models":
            polls.append(1)
            status = "loading" if len(polls) == 1 else "loaded"
            return httpx.Response(
                200, json={"data": [{"id": "previous", "status": {"value": status}}]}
            )
        return httpx.Response(200, json={})

    monkeypatch.setattr(local_gpu.time, "sleep", lambda _: None)
    with httpx.Client(
        base_url="http://local", transport=httpx.MockTransport(respond)
    ) as client:
        local_gpu.restore_models(client, ["previous"])
    assert len(polls) == 2


def test_disabled_handover_has_no_service_effects(tmp_path, handover):
    with local_gpu.parser_session(tmp_path, False):
        pass
    assert not handover
    assert not (tmp_path / "lifecycle.json").exists()


def test_existing_parser_prevents_handover(tmp_path, handover, monkeypatch):
    monkeypatch.setattr(local_gpu.serving, "inspect", lambda: {"Id": "owned"})
    with (
        pytest.raises(RuntimeError, match="already exists"),
        local_gpu.parser_session(tmp_path, True),
    ):
        pytest.fail("must not run experiment")
    assert not handover
    assert not (tmp_path / "lifecycle.json").exists()


def test_unknown_service_state_prevents_handover(tmp_path, handover, monkeypatch):
    monkeypatch.setattr(
        local_gpu.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1)
    )
    with (
        pytest.raises(RuntimeError, match="Cannot determine"),
        local_gpu.parser_session(tmp_path, True),
    ):
        pytest.fail("must not run experiment")
    assert not handover
    assert not (tmp_path / "lifecycle.json").exists()


def test_parser_cleanup_failure_still_restores_service(tmp_path, handover, monkeypatch):
    def fail():
        raise RuntimeError("container removal failed")

    monkeypatch.setattr(local_gpu.serving, "stop", fail)
    with (
        pytest.raises(RuntimeError, match="Restoration failed"),
        local_gpu.parser_session(tmp_path, True),
    ):
        pass
    assert handover[-2:] == [("service", "start"), ("models", ["previous-model"])]
    audit = json.loads((tmp_path / "lifecycle.json").read_text())
    assert audit["restoration_errors"] == ["Parser cleanup: container removal failed"]
    assert not audit["restoration_verified"]


def test_changing_router_state_rejects_model_snapshot():
    def respond(request):
        return httpx.Response(
            200, json={"data": [{"id": "previous", "status": {"value": "loading"}}]}
        )

    with (
        httpx.Client(
            base_url="http://local", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(RuntimeError, match="state is changing"),
    ):
        local_gpu.loaded_models(client)


def test_unhealthy_router_stops_at_restore_deadline(monkeypatch):
    times = iter([0, 2])
    monkeypatch.setattr(local_gpu.time, "monotonic", lambda: next(times))
    with (
        httpx.Client(
            base_url="http://local",
            transport=httpx.MockTransport(lambda _: httpx.Response(503)),
        ) as client,
        pytest.raises(RuntimeError, match="Router readiness deadline"),
    ):
        local_gpu.restore_models(client, ["previous"], timeout=1)

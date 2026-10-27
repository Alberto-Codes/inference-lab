import json

import httpx
import pytest

from inference_lab import serving


def test_memory_guard_does_not_launch_container(monkeypatch):
    monkeypatch.setattr(serving, "inspect", lambda: None)
    monkeypatch.setattr(serving, "gpu", lambda: {"memory.free": "3000"})
    monkeypatch.setattr(
        serving, "command", lambda *a, **kw: pytest.fail("must not launch")
    )
    with pytest.raises(RuntimeError, match="Existing workloads are untouched"):
        serving.start()


def test_stop_absent_is_idempotent(monkeypatch):
    monkeypatch.setattr(serving, "inspect", lambda: None)
    assert serving.stop()["status"] == "already absent"


def test_stop_uses_owned_immutable_id(monkeypatch):
    monkeypatch.setattr(serving, "inspect", lambda: {"Id": "exact-id"})
    commands = []
    monkeypatch.setattr(serving, "command", lambda argv, **kw: commands.append(argv))
    serving.stop()
    assert commands == [["podman", "rm", "-f", "exact-id"]]


def test_foreign_container_is_never_modified(monkeypatch):
    def command(argv):
        if argv[1] == "ps":
            return serving.config()["container"]
        return json.dumps([{"Config": {"Labels": {serving.LABEL: "/other"}}}])

    monkeypatch.setattr(serving, "command", command)
    with pytest.raises(RuntimeError, match="another checkout"):
        serving.stop()


def test_stopped_owned_container_requires_explicit_removal(monkeypatch):
    monkeypatch.setattr(serving, "inspect", lambda: {"State": {"Running": False}})
    monkeypatch.setattr(serving, "gpu", lambda: pytest.fail("must not query GPU"))
    with pytest.raises(RuntimeError, match="demo container is stopped"):
        serving.start()


def test_start_ready_container_uses_loopback_and_ownership_label(monkeypatch):
    settings = serving.config()
    inspections = iter([None, {"State": {"Running": True}}])
    monkeypatch.setattr(serving, "inspect", lambda: next(inspections))
    monkeypatch.setattr(serving, "gpu", lambda: {"memory.free": "24000"})
    commands = []
    monkeypatch.setattr(serving, "command", lambda argv, **kw: commands.append(argv))
    real_client = httpx.Client
    requests = []

    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200)

    monkeypatch.setattr(
        serving.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    assert serving.start()["status"] == "ready"
    assert (
        commands[0][commands[0].index("--label") + 1]
        == f"{serving.LABEL}={serving.ROOT}"
    )
    assert (
        commands[0][commands[0].index("-p") + 1] == f"127.0.0.1:{settings['port']}:8000"
    )
    assert requests == [f"http://127.0.0.1:{settings['port']}/health"]


def test_interrupt_after_launch_removes_owned_container(monkeypatch):
    inspections = iter([None, {"Id": "owned-id"}])

    def inspect():
        item = next(inspections)
        if item is None:
            return None
        raise KeyboardInterrupt

    monkeypatch.setattr(serving, "inspect", inspect)
    monkeypatch.setattr(serving, "gpu", lambda: {"memory.free": "24000"})
    monkeypatch.setattr(serving, "command", lambda *args, **kwargs: "")
    removed = []
    monkeypatch.setattr(serving, "stop", lambda: removed.append(True))
    with pytest.raises(KeyboardInterrupt):
        serving.start()
    assert removed == [True]

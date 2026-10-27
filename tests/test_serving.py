import json

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

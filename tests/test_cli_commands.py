import subprocess
from argparse import Namespace

import httpx
import pytest

from inference_lab import cli


@pytest.mark.parametrize("healthy", [True, False])
def test_status_reports_health_without_starting_server(monkeypatch, capsys, healthy):
    monkeypatch.setattr(cli.sys, "argv", ["inference-axi", "status"])
    monkeypatch.setattr(
        cli.serving,
        "status",
        lambda: {
            "container": "running",
            "gpu": {"name": "test", "memory.free": "12000"},
        },
    )

    def health(*args, **kwargs):
        if not healthy:
            raise httpx.ConnectError("unreachable")
        return httpx.Response(200)

    monkeypatch.setattr(cli.httpx, "get", health)
    assert cli.main() == 0
    assert f"ready: {str(healthy).lower()}" in capsys.readouterr().out


@pytest.mark.parametrize("code", [0, 1])
def test_build_reports_success_or_preserves_failure(monkeypatch, capsys, code):
    monkeypatch.setattr(cli.sys, "argv", ["inference-axi", "build"])
    monkeypatch.setattr(cli.serving, "config", lambda: {"image": "test-image"})
    calls = []

    def build(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, code)

    monkeypatch.setattr(cli.subprocess, "run", build)
    assert cli.main() == code
    assert "test-image" in calls[0]
    output = capsys.readouterr().out
    assert ("image build failed" if code else "image: test-image") in output


@pytest.mark.parametrize("full", [False, True])
def test_logs_use_owned_container_and_preserve_diagnostics(monkeypatch, capsys, full):
    monkeypatch.setattr(
        cli.sys, "argv", ["inference-axi", "logs"] + (["--full"] if full else [])
    )
    monkeypatch.setattr(cli.serving, "inspect", lambda: {"Id": "owned-id"})
    calls = []

    def logs(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "output", "diagnostic")

    monkeypatch.setattr(cli.subprocess, "run", logs)
    assert cli.main() == 0
    assert calls[0][-1] == "owned-id"
    assert ("--tail" in calls[0]) is not full
    assert "outputdiagnostic" in capsys.readouterr().out


def test_logs_failures_return_error(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["inference-axi", "logs"])
    monkeypatch.setattr(cli.serving, "inspect", lambda: {"Id": "owned-id"})
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **kw: Namespace(returncode=1))
    assert cli.main() == 1
    assert "cannot read demo logs" in capsys.readouterr().out

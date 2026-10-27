import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from inference_lab import cli, serving
from inference_lab.corpus import generate


def test_benchmark_persists_accounting_and_metadata(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    generate(corpus)
    manifest = json.loads((corpus / "manifest.json").read_text())
    all_text = "\n".join(s for p in manifest["pages"] for s in p["expected"])
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 3:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": all_text}, "finish_reason": "stop"}]
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        cli.httpx,
        "AsyncClient",
        lambda **kw: real_client(**kw, transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        serving,
        "inspect",
        lambda: {
            "Id": "fake",
            "Image": "fake-image",
            "Args": [],
            "State": {"Running": True},
        },
    )
    monkeypatch.setattr(serving, "gpu", lambda: {"name": "fake GPU - no inference"})
    monkeypatch.setattr(serving, "command", lambda argv: "fake evidence")
    args = SimpleNamespace(
        input=corpus,
        output=tmp_path / "run",
        timeout=1,
        url="http://127.0.0.1:8017",
        concurrency=[1, 2, 4, 8],
    )
    assert asyncio.run(cli.run_bench(args)) == 1
    report = json.loads((args.output / "results.json").read_text())
    assert report["status"] == "complete"
    assert calls == 33  # one excluded warmup, 8 requests for each of 4 sweeps
    assert [r["input_count"] for r in report["sweeps"]] == [8, 8, 8, 8]
    assert report["sweeps"][0]["failures"] == 1
    assert report["warmup"]["status"] == "success"
    assert "fake-image" in (args.output / "summary.md").read_text()
    assert report["metadata"]["preparation_s"] > 0
    assert len(report["metadata"]["corpus"]) == 8
    with pytest.raises(FileExistsError):
        asyncio.run(cli.run_bench(args))


def test_ocr_writes_output_and_failure_receipt(tmp_path, monkeypatch):
    generate(tmp_path / "corpus")
    real_client = httpx.AsyncClient

    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "wrong answer"}, "finish_reason": "stop"}
                ]
            },
        )

    monkeypatch.setattr(
        cli.httpx,
        "AsyncClient",
        lambda **kw: real_client(**kw, transport=httpx.MockTransport(handler)),
    )
    args = SimpleNamespace(
        input=tmp_path / "corpus/page-01.png",
        output=tmp_path / "output.txt",
        expect=["LAB401"],
        timeout=1,
        url="http://test",
        full=False,
    )
    assert asyncio.run(cli.run_ocr(args)) == 1
    assert args.output.read_text() == "wrong answer"
    assert (
        json.loads((tmp_path / "output.txt.json").read_text())["status"]
        == "quality_failed"
    )


def test_failed_warmup_leaves_explicit_aborted_report(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    generate(corpus)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        cli.httpx,
        "AsyncClient",
        lambda **kw: real_client(
            **kw, transport=httpx.MockTransport(lambda _: httpx.Response(503))
        ),
    )
    monkeypatch.setattr(
        serving,
        "inspect",
        lambda: {"Id": "fake", "Image": "fake", "Args": [], "State": {"Running": True}},
    )
    monkeypatch.setattr(serving, "gpu", lambda: {})
    monkeypatch.setattr(serving, "command", lambda argv: "fake")
    args = SimpleNamespace(
        input=corpus,
        output=tmp_path / "run",
        timeout=1,
        url="http://127.0.0.1:8017",
        concurrency=[1, 2, 4, 8],
    )
    with pytest.raises(RuntimeError, match="warmup failed"):
        asyncio.run(cli.run_bench(args))
    report = json.loads((args.output / "results.json").read_text())
    assert report["status"] == "aborted"
    assert report["sweeps"] == []
    assert report["warmup"]["status"] == "error"
    assert "Run status: aborted" in (args.output / "summary.md").read_text()

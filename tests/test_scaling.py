import asyncio
import fcntl
import hashlib
import json
import time

import httpx
import pytest
from PIL import Image
from test_receipt_commands import command, script


def corpus(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    pages = []
    for index in range(3):
        path = root / f"{index}.png"
        Image.new("RGB", (8, 8), (index, 0, 0)).save(path)
        pages.append(
            {
                "id": index,
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "reference": "Total 12.00",
            }
        )
    manifest = {
        "dataset": "test",
        "revision": "fixed",
        "license": "CC0-1.0",
        "partition": "coverage",
        "pages": pages,
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


def settings(**overrides):
    return {
        "rate": 1000,
        "count": 20,
        "concurrency": 2,
        "queue": 2,
        "timeout": 1,
        "cache": "repeated",
        "url": "http://test",
        **overrides,
    }


async def no_telemetry(output, session, client, stop):
    await stop.wait()


def setup_run(tmp_path, monkeypatch, **overrides):
    runner = script("scaling_experiment")
    monkeypatch.setattr(runner, "telemetry", no_telemetry)
    manifest, pages = runner.load_inputs(corpus(tmp_path))
    config = settings(**overrides)
    output = tmp_path / "run"
    runner.initialize(output, manifest, config, False)
    return runner, manifest, pages, config, output


def test_open_loop_sheds_without_waiting_for_server_and_retains_body(
    tmp_path, monkeypatch
):
    runner, manifest, pages, config, output = setup_run(tmp_path, monkeypatch)
    active = 0
    peak = 0

    async def respond(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.03)
        active -= 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Total 12.00"}, "finish_reason": "stop"}
                ],
                "usage": {"completion_tokens": 6},
            },
        )

    result = asyncio.run(
        runner.execute(output, manifest, pages, config, httpx.MockTransport(respond))
    )
    assert result["capacity_eligible"]
    assert peak <= 2
    records = [
        json.loads(p.read_text()) for p in sorted((output / "terminal").glob("*.json"))
    ]
    assert len(records) == 20
    assert any(r["status"] == "queue_full" for r in records)
    assert max(r["scheduled_offset_s"] for r in records) == pytest.approx(0.019)
    assert all(r["e2e_s"] >= r["latency_s"] for r in records)
    assert all(
        "usage" in r["response_body"] for r in records if r["status"] == "success"
    )
    before = {p: p.read_bytes() for p in (output / "terminal").glob("*.json")}
    assert (
        asyncio.run(runner.execute(output, manifest, pages, config))["status"]
        == "already_complete"
    )
    assert all(p.read_bytes() == raw for p, raw in before.items())
    scored = script("score_scaling").summarize(output)
    assert scored["summary"]["capacity_eligible"]
    assert scored["summary"]["numeric_total"] == 20
    assert scored["summary"]["micro_numeric_recall"] < 1
    assert scored["summary"]["correct_output_count"] is None


def test_resume_preserves_unknown_attempt_and_rejects_configuration_change(
    tmp_path, monkeypatch
):
    runner, manifest, pages, config, output = setup_run(tmp_path, monkeypatch, count=3)
    runner.save(
        output / "started/000000000.json",
        {
            "index": 0,
            "id": 0,
            "reference": "Total 12.00",
            "session": "lost",
            "sha256": pages[0].sha256,
            "arrival_lag_s": 0,
        },
    )
    runner.recover(output)
    unknown = (output / "terminal/000000000.json").read_bytes()
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "Total 12.00"}, "finish_reason": "stop"}
                ]
            },
        )

    runner.initialize(output, manifest, config, True)
    with pytest.raises(ValueError, match="differs"):
        runner.initialize(output, manifest, {**config, "rate": 1}, True)
    result = asyncio.run(
        runner.execute(output, manifest, pages, config, httpx.MockTransport(respond))
    )
    assert not result["capacity_eligible"]
    assert len(requests) == 5  # three warmups plus only two unattempted requests
    assert (output / "terminal/000000000.json").read_bytes() == unknown
    assert not script("score_scaling").summarize(output)["summary"]["capacity_eligible"]
    with pytest.raises(FileExistsError):
        runner.save(output / "terminal/000000000.json", {"replacement": True})
    assert (output / "terminal/000000000.json").read_bytes() == unknown


def test_queue_deadline_and_http_failures_remain_in_quality_denominator(
    tmp_path, monkeypatch
):
    runner, manifest, pages, config, output = setup_run(
        tmp_path, monkeypatch, count=10, concurrency=1, queue=20, timeout=0.01
    )
    calls = 0

    async def respond(request):
        nonlocal calls
        calls += 1
        if calls <= 3:
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]
                },
            )
        if calls == 4:
            return httpx.Response(503, text="server overloaded")
        await asyncio.sleep(0.1)
        return httpx.Response(200)

    asyncio.run(
        runner.execute(output, manifest, pages, config, httpx.MockTransport(respond))
    )
    result = script("score_scaling").summarize(output)
    assert result["summary"]["terminal"] == 10
    assert result["summary"]["numeric_total"] == 10
    assert result["summary"]["micro_numeric_recall"] == 0
    assert result["requests"][0]["response_body"] == "server overloaded"
    assert result["summary"]["status_counts"]["timeout"] > 0


def test_failure_review_keeps_unsuccessful_outcomes_out_of_ocr_suspects(
    tmp_path, monkeypatch
):
    runner, manifest, pages, config, output = setup_run(
        tmp_path, monkeypatch, count=10, concurrency=1, queue=20, timeout=0.01
    )
    calls = 0

    async def respond(request):
        nonlocal calls
        calls += 1
        if calls <= 6:
            content = "OK" if calls <= 3 else "Total 13.00"
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": content}, "finish_reason": "stop"}
                    ]
                },
            )
        if calls == 7:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "Total"}, "finish_reason": "length"}
                    ]
                },
            )
        if calls == 8:
            return httpx.Response(503, text="server overloaded")
        # Block the loop past every queued deadline, so later requests expire waiting.
        time.sleep(0.05)
        await asyncio.sleep(0.1)
        return httpx.Response(200)

    asyncio.run(
        runner.execute(output, manifest, pages, config, httpx.MockTransport(respond))
    )
    scorer = script("score_scaling")
    result = scorer.summarize(output)
    review = scorer.review(result)
    counts = result["summary"]["status_counts"]
    assert counts["success"] == 3
    assert {"incomplete", "error", "timeout", "queue_timeout"} <= set(counts)
    assert review["unscored_outcomes"] == {
        status: n for status, n in counts.items() if status != "success"
    }
    assert review["suspected_categories"] == {"omission or changed digits": 3}
    assert {
        example["prediction"]
        for items in review["examples"].values()
        for example in items
    } == {"Total 13.00"}
    assert result["summary"]["numeric_total"] == 10
    assert result["summary"]["requests_with_missing_numbers"] == 10


def test_validation_and_fresh_inputs(tmp_path):
    runner = script("scaling_experiment")
    root = corpus(tmp_path)
    manifest, _ = runner.load_inputs(root)
    runner.validate(settings(cache="fresh", count=3), 3)
    for invalid in [
        settings(rate=float("nan")),
        settings(queue=0),
        settings(cache="fresh"),
    ]:
        with pytest.raises(ValueError):
            runner.validate(invalid, 3)
    manifest["evaluation_rows"] = [0]
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="reserved"):
        runner.load_inputs(root)
    manifest["evaluation_rows"] = []
    manifest["pages"][0]["file"] = "../escape.png"
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inside"):
        runner.load_inputs(root)


def test_failed_warmup_stops_measurement_and_preserves_raw_failure(
    tmp_path, monkeypatch
):
    runner, manifest, pages, config, output = setup_run(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="Warmup"):
        asyncio.run(
            runner.execute(
                output,
                manifest,
                pages,
                config,
                httpx.MockTransport(lambda _: httpx.Response(400, text="bad")),
            )
        )
    assert not list((output / "terminal").glob("*.json"))
    assert (
        json.loads(next((output / "warmup").glob("*.json")).read_text())[
            "response_body"
        ]
        == "bad"
    )
    summary = script("score_scaling").summarize(output)["summary"]
    assert not summary["complete"]
    assert summary["unattempted"] == 20


def test_truncated_warmup_does_not_remove_difficult_inputs(tmp_path, monkeypatch):
    runner, manifest, pages, config, output = setup_run(tmp_path, monkeypatch, count=3)
    response = {
        "choices": [{"message": {"content": "12.00"}, "finish_reason": "length"}]
    }
    asyncio.run(
        runner.execute(
            output,
            manifest,
            pages,
            config,
            httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        )
    )
    result = script("score_scaling").summarize(output)
    assert result["summary"]["status_counts"] == {"incomplete": 3}
    assert result["summary"]["numeric_total"] == 3
    assert result["summary"]["numeric_matched"] == 0
    assert all(row["text"] == "12.00" for row in result["requests"])


def test_cancellation_resume_never_resends_an_inflight_attempt(tmp_path, monkeypatch):
    runner, manifest, pages, config, output = setup_run(
        tmp_path, monkeypatch, rate=10, count=3, concurrency=1
    )
    calls = 0

    async def interrupt():
        entered = asyncio.Event()

        async def respond(request):
            nonlocal calls
            calls += 1
            if calls <= 3:
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"content": "OK"}, "finish_reason": "stop"}
                        ]
                    },
                )
            entered.set()
            await asyncio.sleep(10)
            return httpx.Response(200)

        task = asyncio.create_task(
            runner.execute(
                output, manifest, pages, config, httpx.MockTransport(respond)
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(interrupt())
    assert calls == 4
    assert len(list((output / "started").glob("*.json"))) == 1
    assert not list((output / "terminal").glob("*.json"))
    response = {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
    asyncio.run(
        runner.execute(
            output,
            manifest,
            pages,
            config,
            httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        )
    )
    result = script("score_scaling").summarize(output)
    assert result["summary"]["status_counts"] == {"interrupted": 1, "success": 2}
    assert not result["summary"]["capacity_eligible"]


def test_resource_report_uses_counter_deltas_and_records_missing_samples(tmp_path):
    reporter = script("report_scaling")
    assert reporter.cpu_seconds("1h2m3.5s") == 3723.5
    assert (
        reporter.metric(
            'vllm:num_requests_waiting{engine="0"} 4.0', "vllm:num_requests_waiting"
        )
        == 4
    )
    assert reporter.metric("", "missing") is None
    root = tmp_path / "telemetry"
    root.mkdir()
    for index in range(3):
        sample = {
            "unix_s": 100 + index,
            "gpu": "50, 20, 12000, 140, 55",
            "container": json.dumps([{"cpu_time": f"{2 * index}s"}]),
            "metrics": f'vllm:mm_cache_hits_total{{engine="0"}} {index}\n',
        }
        (root / f"{index}.json").write_text(json.dumps(sample))
    result = reporter.resources(tmp_path, [{"scheduled_unix_s": 100}], 2)
    assert result["container_cpu_cores"]["mean"] == 2
    assert result["vllm:mm_cache_hits_total_observed_delta"] == 2
    assert result["server_waiting"]["mean"] is None
    assert result["gpu_percent"]["mean"] == 50
    assert reporter.output_tokens({"response_body": "not json"}) == 0


def test_telemetry_failures_are_evidence_not_zero_utilization(tmp_path, monkeypatch):
    runner = script("scaling_experiment")
    (tmp_path / "telemetry").mkdir()

    def unavailable(*args):
        raise OSError("collector unavailable")

    monkeypatch.setattr(runner.serving, "command", unavailable)

    async def sample():
        stop = asyncio.Event()

        def respond(request):
            stop.set()
            return httpx.Response(503)

        async with httpx.AsyncClient(
            base_url="http://test", transport=httpx.MockTransport(respond)
        ) as client:
            await runner.telemetry(tmp_path, "test", client, stop)

    asyncio.run(sample())
    result = json.loads((tmp_path / "telemetry/test-000000.json").read_text())
    assert result["gpu_error"] == "collector unavailable"
    assert result["container_error"] == "collector unavailable"
    assert "metrics_error" in result
    assert "gpu" not in result


def test_cli_resume_lock_refuses_concurrent_writer(tmp_path):
    runner = script("scaling_experiment")
    root = corpus(tmp_path)
    manifest, _ = runner.load_inputs(root)
    config = settings(warmup_image="")
    output = tmp_path / "run"
    runner.initialize(output, manifest, config, False)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = command(
            "scaling_experiment.py",
            "--input",
            root,
            "--output",
            output,
            "--resume",
            "--rate",
            "1000",
            "--count",
            "20",
            "--concurrency",
            "2",
            "--queue",
            "2",
            "--timeout",
            "1",
            "--url",
            "http://test",
        )
    assert result.returncode != 0
    assert "BlockingIOError" in result.stderr
    assert not list((output / "started").glob("*.json"))


def test_manifest_hash_and_duplicate_id_are_checked(tmp_path):
    runner = script("scaling_experiment")
    root = corpus(tmp_path)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["pages"][1]["id"] = 0
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Duplicate"):
        runner.load_inputs(root)
    manifest["pages"][1]["id"] = 1
    manifest["pages"][0]["sha256"] = "changed"
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="hash mismatch"):
        runner.load_inputs(root)


def test_format_audit_distinguishes_escaping_from_changed_digits(tmp_path):
    source = tmp_path / "scores.json"
    source.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "index": 0,
                        "id": 0,
                        "status": "success",
                        "reference": "Tax 6% Total 40,000",
                        "text": r"Tax 6\% Total 40,800",
                    },
                    {
                        "index": 1,
                        "id": 1,
                        "status": "incomplete",
                        "reference": "Tax 6%",
                        "text": r"Tax 6\%",
                    },
                ]
            }
        )
    )
    before = source.read_bytes()
    result = script("audit_scaling_format").audit(source)
    assert result["additional_matches"] == 1
    assert result["percent_unescaped_matched"] == 1
    assert result["numeric_reference_count"] == 3
    assert result["requests"][0]["percent_unescaped"]["missing_numbers"] == ["40,000"]
    assert source.read_bytes() == before


def test_interrupted_warmup_keeps_unknown_attempt_on_resume(tmp_path, monkeypatch):
    runner, manifest, pages, config, output = setup_run(tmp_path, monkeypatch, count=3)

    async def interrupt():
        entered = asyncio.Event()

        async def respond(request):
            entered.set()
            await asyncio.sleep(10)
            return httpx.Response(200)

        task = asyncio.create_task(
            runner.execute(
                output, manifest, pages, config, httpx.MockTransport(respond)
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(interrupt())
    intents = list((output / "warmup-started").glob("*.json"))
    assert len(intents) == 1
    assert not list((output / "warmup").glob("*.json"))
    response = {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
    asyncio.run(
        runner.execute(
            output,
            manifest,
            pages,
            config,
            httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        )
    )
    unknown = json.loads((output / "warmup" / intents[0].name).read_text())
    assert unknown["status"] == "interrupted"
    assert unknown["sha256"] == pages[0].sha256
    assert len(list((output / "warmup").glob("*.json"))) == 4
    assert len(list((output / "terminal").glob("*.json"))) == 3


def test_fresh_mode_rejects_identical_images_under_different_ids(tmp_path):
    runner = script("scaling_experiment")
    manifest, _ = runner.load_inputs(corpus(tmp_path))
    manifest["pages"][1]["sha256"] = manifest["pages"][0]["sha256"]
    with pytest.raises(ValueError, match="unique image hashes"):
        runner.initialize(
            tmp_path / "run", manifest, settings(cache="fresh", count=3), False
        )
    assert not (tmp_path / "run").exists()

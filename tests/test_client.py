import asyncio
import json

import httpx
import pytest

from inference_lab.client import Page, infer
from inference_lab.experiment import summarize, sweep

PAGE = Page("page.png", "abc", "data:image/png;base64,AA==", ("known text",))


def run(handler, timeout=1):
    async def request():
        async with httpx.AsyncClient(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ) as client:
            return await infer(client, PAGE, timeout)

    return asyncio.run(request())


def response(text="known text", finish="stop"):
    return httpx.Response(
        200, json={"choices": [{"message": {"content": text}, "finish_reason": finish}]}
    )


def test_request_contract():
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        data = json.loads(request.content)
        assert data["model"] == "nemotron-parse"
        assert data["max_tokens"] == 8744
        assert data["skip_special_tokens"] is False
        assert data["messages"][0]["content"][1]["image_url"]["url"] == PAGE.data_url
        return response("Known, TEXT")

    assert run(handler)["status"] == "success"


@pytest.mark.parametrize(
    ("text", "finish", "status"),
    [
        ("", "stop", "quality_failed"),
        ("incorrect", "stop", "quality_failed"),
        ("known text", "length", "incomplete"),
        (None, "stop", "error"),
    ],
)
def test_rejects_invalid_success(text, finish, status):
    assert run(lambda _: response(text, finish))["status"] == status


@pytest.mark.parametrize("code", [400, 429, 500, 503])
def test_http_errors(code):
    result = run(lambda _: httpx.Response(code))
    assert result["status"] == "error"
    assert str(code) in result["error"]


def test_malformed_response():
    assert run(lambda _: httpx.Response(200, json={"choices": []}))["status"] == "error"


def test_connection_failure():
    def handler(request):
        raise httpx.ConnectError("failed", request=request)

    assert run(handler)["status"] == "error"


def test_absolute_deadline():
    async def handler(request):
        await asyncio.sleep(0.05)
        return response()

    assert run(handler, timeout=0.005)["status"] == "timeout"


def test_failure_accounting():
    records = [
        {"status": s, "latency_s": t}
        for s, t in [
            ("success", 1),
            ("timeout", 4),
            ("quality_failed", 2),
            ("error", 3),
        ]
    ]
    result = summarize(records, 5, 2)
    assert result["input_count"] == 4
    assert result["successful_completions"] == 1
    assert result["failures"] == 3
    assert result["timeouts"] == 1
    assert result["successful_pages_per_second"] == 0.2
    assert result["all_latency"]["median_s"] == 2.5
    assert result["successful_latency"]["median_s"] == 1
    assert summarize([], 1, 1)["all_latency"]["median_s"] is None


@pytest.mark.parametrize("concurrency", [1, 2, 4, 8])
def test_bounded_concurrency_and_same_corpus(concurrency):
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.003)
        active -= 1
        return response()

    async def execute():
        async with httpx.AsyncClient(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ) as client:
            return await sweep(client, [PAGE] * 8, concurrency, 1)

    result = asyncio.run(execute())
    assert peak == concurrency
    assert result["successful_completions"] == 8
    assert [r["index"] for r in result["requests"]] == list(range(8))


def test_failure_does_not_cancel_other_pages():
    count = 0

    async def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(500) if count == 1 else response()

    async def execute():
        async with httpx.AsyncClient(
            base_url="http://test", transport=httpx.MockTransport(handler)
        ) as client:
            return await sweep(client, [PAGE] * 8, 4, 1)

    result = asyncio.run(execute())
    assert result["successful_completions"] == 7
    assert result["failures"] == 1

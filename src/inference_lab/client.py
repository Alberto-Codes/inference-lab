"""Send one prepared image per bounded HTTP request without retries.

Attributes:
    PROMPT: Control tokens for Nemotron layout and text extraction.
    MODEL: Model name exposed by the demo server.

Examples:
    Normalize expected text for a case-insensitive sanity check:

    ```python
    from inference_lab.client import normalized

    text = normalized("Total: 12.00")  # "total 12 00"
    ```

See Also:
    [`inference_lab.experiment`][]: Preparation and measured concurrency sweeps.
"""

import asyncio
import base64
import hashlib
import io
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image

PROMPT = "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>"
MODEL = "nemotron-parse"


@dataclass(frozen=True)
class Page:
    """Hold an image prepared outside the measured request interval.

    Attributes:
        name (str): Source image filename used in request records.
        sha256 (str): SHA-256 digest of the original file bytes.
        data_url (str): Base64 PNG data URL submitted to the server.
        expected (tuple[str, ...]): Text snippets required by the synthetic quality check.

    Examples:
        Prepare a real image rather than constructing its data URL manually:

        ```python
        from pathlib import Path
        from inference_lab.client import prepare

        page = prepare(Path("corpus/page-01.png"), ("LAB401",))
        ```
    """

    name: str
    sha256: str
    data_url: str
    expected: tuple[str, ...]


def prepare(path: Path, expected: tuple[str, ...] = ()) -> Page:
    """Decode and normalize before inference timing begins.

    Args:
        path: Image file to read and convert to RGB PNG.
        expected: Required text snippets for response validation.

    Returns:
        Prepared image with the original file digest and encoded PNG.
    """
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        output = io.BytesIO()
        image.convert("RGB").save(output, format="PNG")
    data = base64.b64encode(output.getvalue()).decode("ascii")
    return Page(
        path.name,
        hashlib.sha256(raw).hexdigest(),
        f"data:image/png;base64,{data}",
        expected,
    )


def normalized(text: str) -> str:
    """Casefold text and join word tokens with single spaces.

    Args:
        text: Expected or extracted text.

    Returns:
        Normalized text for substring sanity checks.
    """
    return " ".join(re.findall(r"\w+", text.casefold()))


# Response validation errors are caught and recorded, not raised to callers.
async def infer(  # docvet: ignore[missing-raises]
    client: httpx.AsyncClient, page: Page, timeout: float
) -> dict:
    """Return one terminal record, including failure and observed latency.

    HTTP, timeout and malformed-response failures become records rather than
    escaping to the caller. Task cancellation still propagates.

    Args:
        client: Async HTTP client configured with the server base URL.
        page: Image and expected text prepared before timing.
        timeout: Total request deadline in seconds.

    Returns:
        Record with page name, digest, status, text and latency in seconds.
        Failure records include an error description.
    """
    start = time.perf_counter()
    record = {"page": page.name, "sha256": page.sha256, "status": "error", "text": ""}
    try:
        async with asyncio.timeout(timeout):
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": page.data_url},
                                },
                            ],
                        }
                    ],
                    "max_tokens": 8744,
                    "temperature": 0.0,
                    "repetition_penalty": 1.1,
                    "top_k": 1,
                    "skip_special_tokens": False,
                },
            )
            response.raise_for_status()
            choice = response.json()["choices"][0]
            text = choice["message"]["content"]
            if not isinstance(text, str):
                raise TypeError("response content is not text")  # noqa: TRY301 - record below
            record["text"] = text
            record["finish_reason"] = choice.get("finish_reason")
            missing = [
                s for s in page.expected if normalized(s) not in normalized(text)
            ]
            visible = re.sub(r"<[^>]*>", "", text)
            if choice.get("finish_reason") != "stop":
                record.update(
                    status="incomplete", error="generation did not finish with stop"
                )
            elif not normalized(visible) or missing:
                record.update(
                    status="quality_failed",
                    error="empty output or missing expected text",
                    missing=missing,
                )
            else:
                record["status"] = "success"
    except (TimeoutError, httpx.TimeoutException):
        record.update(status="timeout", error=f"request exceeded {timeout:g}s deadline")
    except httpx.HTTPStatusError as exc:
        record["error"] = f"HTTP {exc.response.status_code}; inspect server logs"
    except httpx.RequestError:
        record["error"] = "connection failed; check inference-axi status"
    except (ValueError, KeyError, IndexError, TypeError):
        record["error"] = "invalid response; expected choices[0].message.content text"
    record["latency_s"] = time.perf_counter() - start
    return record

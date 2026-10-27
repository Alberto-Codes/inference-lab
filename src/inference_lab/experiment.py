"""Run finite closed-loop sweeps with explicit result accounting.

Examples:
    Summarize observed latencies without claiming tail percentiles:

    ```python
    from inference_lab.experiment import distribution

    median = distribution([1.0, 2.0, 3.0])["median_s"]  # 2.0 seconds
    ```

See Also:
    [`inference_lab.client`][]: Request preparation and response validation.
    [`inference_lab.corpus`][]: Synthetic inputs with known expected text.
"""

import asyncio
import json
import statistics
import time
from collections import Counter
from pathlib import Path

import httpx

from inference_lab.client import Page, infer, prepare


def distribution(values: list[float]) -> dict:
    """Summarize small samples with minimum, median and maximum latency.

    Args:
        values: Observed request latencies in seconds.

    Returns:
        Count and latency statistics; all statistics are None for no samples.
    """
    return {
        "count": len(values),
        "min_s": min(values) if values else None,
        "median_s": statistics.median(values) if values else None,
        "max_s": max(values) if values else None,
    }


def summarize(records: list[dict], elapsed: float, concurrency: int) -> dict:
    """Count every terminal status and summarize throughput and latency.

    Args:
        records: Request records with status and latency_s fields.
        elapsed: Wall-clock sweep duration in seconds.
        concurrency: Worker limit used by the sweep.

    Returns:
        Completion and failure counts, status counts, throughput, and latency
        distributions for all requests and successful requests separately.
    """
    counts = Counter(r["status"] for r in records)
    return {
        "concurrency": concurrency,
        "input_count": len(records),
        "successful_completions": counts["success"],
        "failures": len(records) - counts["success"],
        "timeouts": counts["timeout"],
        "status_counts": dict(counts),
        "elapsed_s": elapsed,
        "successful_pages_per_second": counts["success"] / elapsed if elapsed else 0,
        "all_latency": distribution([r["latency_s"] for r in records]),
        "successful_latency": distribution(
            [r["latency_s"] for r in records if r["status"] == "success"]
        ),
    }


async def sweep(
    client: httpx.AsyncClient, pages: list[Page], concurrency: int, timeout: float
) -> dict:
    """Submit each prepared page once through a bounded worker pool.

    Preparation and warmup belong outside this measured sweep. Worker tasks
    share one iterator, so a page is assigned to exactly one worker.

    Args:
        client: Async HTTP client configured with the parser base URL.
        pages: Nonempty sequence of prepared images.
        concurrency: Worker limit, one of 1, 2, 4 or 8.
        timeout: Deadline in seconds for each request.

    Returns:
        Sweep summary and terminal request records in input order.

    Raises:
        ValueError: Pages are empty or concurrency is unsupported.
    """
    if not pages or concurrency not in (1, 2, 4, 8):
        raise ValueError("sweep needs pages and concurrency 1, 2, 4 or 8")
    queue = iter(enumerate(pages))
    records = []

    async def worker():
        for index, page in queue:
            record = await infer(client, page, timeout)
            record["index"] = index
            records.append(record)

    start = time.perf_counter()
    async with asyncio.TaskGroup() as group:
        for _ in range(min(concurrency, len(pages))):
            group.create_task(worker())
    elapsed = time.perf_counter() - start
    records.sort(key=lambda r: r["index"])
    return {**summarize(records, elapsed, concurrency), "requests": records}


def load_corpus(directory: Path) -> list[Page]:
    """Load and prepare the synthetic corpus described by its manifest.

    Args:
        directory: Directory containing manifest.json and its image files.

    Returns:
        Prepared images in manifest order with required text snippets.

    Raises:
        ValueError: An image escapes the corpus directory, expected text is
            missing or invalid, or the manifest contains no pages.
    """
    manifest = json.loads((directory / "manifest.json").read_text())
    pages = []
    for item in manifest["pages"]:
        path = (directory / item["file"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("corpus image must stay inside corpus directory")
        expected = item["expected"]
        if not expected or any(
            not isinstance(s, str) or not s.strip() for s in expected
        ):
            raise ValueError("every corpus page needs nonempty expected text")
        pages.append(prepare(path, tuple(expected)))
    if not pages:
        raise ValueError("corpus contains 0 pages")
    return pages


def render(report: dict) -> str:
    """Render a sweep report as Markdown with timing limits and metadata.

    Args:
        report: Report containing sweeps and metadata; each sweep must have
            nonempty latency observations.

    Returns:
        Markdown summary table and JSON configuration block.
    """
    lines = [
        "# Nemotron concurrency smoke demo",
        f"Run status: {report.get('status', 'unknown')}",
        "",
        "This finite workload uses a closed loop and a warmed image cache.",
        "It does not establish overload behavior or production latency guarantees.",
        "Tiny synthetic corpus: text sanity checks only, not a general OCR quality benchmark.",
        "Latency starts at HTTP submission and ends after response validation.",
        "It excludes preparation and waiting for a worker.",
        "Raw per-request latencies and failed outputs are in results.json. "
        "Timeouts are censored observations.",
        "",
        "| Concurrency | Inputs | Success | Failures | Timeouts | Elapsed s | Pages/s | "
        "All median s | All min–max s |",  # noqa: RUF001 - typographic range in prose
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for run in report["sweeps"]:
        d = run["all_latency"]
        lines.append(
            f"| {run['concurrency']} | {run['input_count']} | {run['successful_completions']} | "
            f"{run['failures']} | {run['timeouts']} | {run['elapsed_s']:.3f} | "
            f"{run['successful_pages_per_second']:.3f} | {d['median_s']:.3f} | "
            f"{d['min_s']:.3f}–{d['max_s']:.3f} |"  # noqa: RUF001 - typographic range
        )
    lines += [
        "",
        "## Configuration and provenance",
        "",
        "```json",
        json.dumps(report["metadata"], indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)

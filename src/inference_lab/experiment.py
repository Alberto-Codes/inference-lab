"""Finite closed-loop sweep and transparent result accounting."""

import asyncio
import json
import statistics
import time
from collections import Counter
from pathlib import Path

import httpx

from inference_lab.client import Page, infer, prepare


def distribution(values: list[float]) -> dict:
    """Small samples get min/median/max and raw observations, not tail claims."""
    return {
        "count": len(values),
        "min_s": min(values) if values else None,
        "median_s": statistics.median(values) if values else None,
        "max_s": max(values) if values else None,
    }


def summarize(records: list[dict], elapsed: float, concurrency: int) -> dict:
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
    lines = [
        "# Nemotron concurrency smoke demo",
        f"Run status: {report.get('status', 'unknown')}",
        "",
        "Finite closed-loop workload; not an overload benchmark or production SLO evidence.",
        "Tiny synthetic corpus: text sanity checks only, not a general OCR quality benchmark.",
        "Latency covers HTTP submission through response validation, excluding corpus preparation and waiting for a worker.",
        "Raw per-request latencies and failed outputs are in results.json. Timeouts are censored observations.",
        "",
        "| Concurrency | Inputs | Success | Failures | Timeouts | Elapsed s | Pages/s | All median s | All min–max s |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for run in report["sweeps"]:
        d = run["all_latency"]
        lines.append(
            f"| {run['concurrency']} | {run['input_count']} | {run['successful_completions']} | {run['failures']} | {run['timeouts']} | {run['elapsed_s']:.3f} | {run['successful_pages_per_second']:.3f} | {d['median_s']:.3f} | {d['min_s']:.3f}–{d['max_s']:.3f} |"
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

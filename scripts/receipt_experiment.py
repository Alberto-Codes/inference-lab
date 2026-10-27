"""Run the fixed CORD pilot against an already started Nemotron server."""

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from inference_lab import serving
from inference_lab.client import infer, prepare
from inference_lab.local_gpu import parser_session
from inference_lab.receipt_metrics import plain_text, score


async def run(corpus: Path, output: Path, url: str = "http://127.0.0.1:8017"):
    manifest = json.loads((corpus / "manifest.json").read_text())
    if [p["id"] for p in manifest["pages"]] != list(range(24)):
        raise ValueError("Expected exactly CORD test rows 0 through 23")
    pages = []
    references = []
    for item in manifest["pages"]:
        path = corpus / item["file"]
        if not path.resolve().is_relative_to(corpus.resolve()):
            raise ValueError("Image must remain inside the corpus directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Image hash mismatch: {item['id']}")
        pages.append(prepare(path))
        references.append(
            " ".join(
                w["text"]
                for line in item["ground_truth"]["valid_line"]
                for w in line["words"]
            )
        )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    report = {
        "started": datetime.now(UTC).isoformat(),
        "config": serving.config(),
        "gpu": serving.gpu(),
        "timeout_s": 120,
        "retries": 0,
        "expected_requests": 72,
        "runs": [],
        "status": "incomplete",
    }
    report_path = output / "results.json"
    report_path.write_text(json.dumps(report, indent=2))
    with (output / "requests.jsonl").open("x") as log:
        async with httpx.AsyncClient(base_url=url, timeout=120) as client:
            for phase, concurrency in [("warmup", 1), ("measured", 1), ("measured", 4)]:
                queue = iter(enumerate(pages))
                records = []

                async def worker(queue, phase, concurrency, records):
                    for index, page in queue:
                        result = await infer(client, page, 120)
                        clean = plain_text(result["text"])
                        prediction = clean if result["status"] == "success" else ""
                        record = {
                            **result,
                            "id": index,
                            "phase": phase,
                            "concurrency": concurrency,
                            "reference": references[index],
                            "plain_prediction": clean,
                            "scored_prediction": prediction,
                            "scores": score(references[index], prediction),
                        }
                        log.write(json.dumps(record) + "\n")
                        log.flush()
                        records.append(record)

                start = time.perf_counter()
                async with asyncio.TaskGroup() as group:
                    for _ in range(concurrency):
                        group.create_task(worker(queue, phase, concurrency, records))
                elapsed = time.perf_counter() - start
                records.sort(key=lambda x: x["id"])
                scores = [r["scores"] for r in records]
                total = sum(s["numeric_reference_count"] for s in scores)
                summary = {
                    "phase": phase,
                    "concurrency": concurrency,
                    "count": len(records),
                    "status_counts": dict(Counter(r["status"] for r in records)),
                    "elapsed_s": elapsed,
                    "completed_pages_per_s": sum(
                        r["status"] == "success" for r in records
                    )
                    / elapsed,
                    "median_latency_s": statistics.median(
                        r["latency_s"] for r in records
                    ),
                    "macro_rouge_l_f1": statistics.mean(
                        s["rouge_l_f1"] for s in scores if s["rouge_l_f1"] is not None
                    ),
                    "micro_numeric_recall": sum(
                        s["numeric_matched_count"] for s in scores
                    )
                    / total
                    if total
                    else None,
                    "numeric_reference_count": total,
                    "numeric_matched_count": sum(
                        s["numeric_matched_count"] for s in scores
                    ),
                    "requests": records,
                }
                report["runs"].append(summary)
                report_path.write_text(json.dumps(report, indent=2))
                print(
                    json.dumps({k: v for k, v in summary.items() if k != "requests"}),
                    flush=True,
                )
                if phase == "warmup" and any(r["status"] != "success" for r in records):
                    raise RuntimeError("Warmup failed; measurements not started")
    report["status"] = "complete"
    report["finished"] = datetime.now(UTC).isoformat()
    report_path.write_text(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, type=Path, help="Prepared CORD corpus directory"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="New run directory; must not exist"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8017")
    parser.add_argument(
        "--release-llama",
        action="store_true",
        help="Temporarily stop local llama.cpp, start the parser and restore previous service/model state",
    )
    args = parser.parse_args()
    if args.release_llama and args.url != "http://127.0.0.1:8017":
        parser.error("--release-llama uses only the local parser URL")
    args.output.mkdir(parents=True, exist_ok=False)
    with parser_session(args.output, args.release_llama):
        asyncio.run(run(args.input, args.output, args.url))


if __name__ == "__main__":
    main()

"""Rescore saved requests without another GPU run."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from inference_lab import receipt_metrics


def rescore(source: Path) -> dict:
    raw = (source / "requests.jsonl").read_bytes()
    records = [json.loads(line) for line in raw.splitlines()]
    for record in records:
        prediction = receipt_metrics.plain_text(record["text"])
        record["plain_prediction"] = prediction
        record["scored_prediction"] = (
            prediction if record["status"] == "success" else ""
        )
        record["scores"] = receipt_metrics.score(
            record["reference"], record["scored_prediction"]
        )
    summaries = []
    for phase, concurrency in [("warmup", 1), ("measured", 1), ("measured", 4)]:
        selected = [
            r
            for r in records
            if r["phase"] == phase and r["concurrency"] == concurrency
        ]
        if len(selected) != 24 or sorted(r["id"] for r in selected) != list(range(24)):
            raise RuntimeError(
                "Missing or duplicate requests; refusing complete-run summary"
            )
        scores = [r["scores"] for r in selected]
        matched = sum(s["numeric_matched_count"] for s in scores)
        total = sum(s["numeric_reference_count"] for s in scores)
        summaries.append(
            {
                "phase": phase,
                "concurrency": concurrency,
                "macro_rouge_l_f1": statistics.mean(s["rouge_l_f1"] for s in scores),
                "macro_rouge_l_recall": statistics.mean(
                    s["rouge_l_recall"] for s in scores
                ),
                "numeric_matched": matched,
                "numeric_total": total,
                "micro_numeric_recall": matched / total,
            }
        )
    result = {
        "normalizer": "v3: remove Nemotron controls, HTML tags, LaTeX commands and tabular/multicolumn layout syntax",
        "source_requests_sha256": hashlib.sha256(raw).hexdigest(),
        "metric_source_sha256": hashlib.sha256(
            Path(receipt_metrics.__file__).read_bytes()
        ).hexdigest(),
        "summaries": summaries,
        "requests": records,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Run directory containing requests.jsonl",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="New score JSON file; must not exist"
    )
    args = parser.parse_args()
    result = rescore(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(result, indent=2))
    print(json.dumps(result["summaries"], indent=2))


if __name__ == "__main__":
    main()

"""Rescore immutable scaling evidence and produce a failure review without a GPU."""

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from inference_lab import receipt_metrics


def percentile(values, fraction):
    """Return a nearest-rank percentile or null for absent observations."""
    return (
        sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]
        if values
        else None
    )


def summarize(source: Path):
    """Account for planned, terminal, failed and interrupted requests separately."""
    plan = json.loads((source / "plan.json").read_text())
    records = []
    digest = hashlib.sha256()
    for path in sorted((source / "terminal").glob("*.json")):
        raw = path.read_bytes()
        digest.update(raw)
        record = json.loads(raw)
        record["plain_prediction"] = receipt_metrics.plain_text(record["text"])
        record["scores"] = receipt_metrics.score(
            record["reference"],
            record["plain_prediction"] if record["status"] == "success" else "",
        )
        records.append(record)
    count = plan["settings"]["count"]
    indices = [r["index"] for r in records]
    if len(set(indices)) != len(indices) or any(i < 0 or i >= count for i in indices):
        raise ValueError("Duplicate or out-of-plan terminal record")
    sessions = [
        json.loads(p.read_text()) for p in (source / "sessions").glob("*-end.json")
    ]
    uninterrupted = len(sessions) == 1 and sessions[0]["capacity_eligible"]
    complete = len(records) == count
    eligible = (
        complete
        and uninterrupted
        and not any(r["status"] == "interrupted" for r in records)
    )
    counts = Counter(r["status"] for r in records)
    latencies = [r["e2e_s"] for r in records if r.get("e2e_s") is not None]
    successful = [r["e2e_s"] for r in records if r["status"] == "success"]
    total = sum(r["scores"]["numeric_reference_count"] for r in records)
    matched = sum(r["scores"]["numeric_matched_count"] for r in records)
    elapsed = sessions[0]["elapsed_s"] if eligible else None
    window = count / plan["settings"]["rate"]
    during = sum(
        r["status"] == "success" and r.get("finished_offset_s", window) <= window
        for r in records
    )
    f1s = [
        r["scores"]["rouge_l_f1"]
        for r in records
        if r["scores"]["rouge_l_f1"] is not None
    ]
    summary = {
        "complete": complete,
        "capacity_eligible": eligible,
        "planned": count,
        "terminal": len(records),
        "unattempted": count - len(records),
        "unique_documents": len({r["sha256"] for r in records}),
        "status_counts": dict(counts),
        "offered_rate": plan["settings"]["rate"],
        "elapsed_s": elapsed,
        "offered_window_s": window,
        "completed_per_s_including_drain": counts["success"] / elapsed
        if elapsed
        else None,
        "completed_per_s_during_arrivals": during / window if eligible else None,
        "all_e2e_p50_s": percentile(latencies, 0.5),
        "all_e2e_p95_s": percentile(latencies, 0.95),
        "all_e2e_p99_s": percentile(latencies, 0.99),
        "success_e2e_p95_s": percentile(successful, 0.95),
        "queue_p95_s": percentile(
            [r["queue_s"] for r in records if "queue_s" in r], 0.95
        ),
        "arrival_lag_max_s": max((r["arrival_lag_s"] for r in records), default=None),
        "numeric_matched": matched,
        "numeric_total": total,
        "micro_numeric_recall": matched / total if total else None,
        "macro_rouge_l_f1": statistics.mean(f1s) if f1s else None,
        "requests_with_missing_numbers": sum(
            bool(r["scores"]["missing_numbers"]) for r in records
        ),
        "correct_output_count": None,
    }
    return {
        "summary": summary,
        "plan": plan,
        "requests": records,
        "source_terminal_sha256": digest.hexdigest(),
        "metric_source_sha256": hashlib.sha256(
            Path(receipt_metrics.__file__).read_bytes()
        ).hexdigest(),
    }


def review(result):
    """Group successful-output discrepancies as suspects and count other outcomes apart."""
    groups = Counter()
    unscored = Counter()
    examples = {}
    for record in result["requests"]:
        if record["status"] != "success":
            unscored[record["status"]] += 1
            continue
        missing = record["scores"]["missing_numbers"]
        predicted = receipt_metrics.numbers(record["plain_prediction"])
        for number in missing:
            digits = "".join(c for c in number if c.isdigit())
            category = "omission or changed digits"
            if any(
                "".join(c for c in candidate if c.isdigit()) == digits
                for candidate in predicted
            ):
                category = "separator or sign change"
            groups[category] += 1
            examples.setdefault(category, {})[str(record["id"])] = {
                "id": record["id"],
                "index": record["index"],
                "missing_numbers": missing,
                "reference": record["reference"],
                "prediction": record["plain_prediction"],
                "verification": "suspected; compare original image and annotation",
            }
    return {
        "counts_are_occurrences_not_unique_documents": True,
        "suspected_categories": dict(groups),
        "unscored_outcomes": dict(unscored),
        "examples": {
            category: list(items.values())[:5] for category, items in examples.items()
        },
        "unrelated_text": "Requires image review; extra text may be an annotation gap.",
        "verified_errors": [],
        "annotation_gaps": "Partial references: low overlap does not prove error.",
    }


def main():
    """Write a new score and review JSON without modifying inference evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.input)
    result["failure_review"] = review(result)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()

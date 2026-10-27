"""Measure escaped-percent scoring artifacts without changing raw OCR evidence."""

import argparse
import hashlib
import json
from pathlib import Path

from inference_lab import receipt_metrics


def audit(source: Path):
    """Compare baseline scores with one explicit LaTeX escape interpretation."""
    raw = source.read_bytes()
    saved = json.loads(raw)
    rows = []
    for record in saved["requests"]:
        prediction = (
            receipt_metrics.plain_text(record["text"])
            if record["status"] == "success"
            else ""
        )
        baseline = receipt_metrics.score(record["reference"], prediction)
        interpreted = receipt_metrics.score(
            record["reference"], prediction.replace(r"\%", "%")
        )
        rows.append(
            {
                "index": record["index"],
                "id": record["id"],
                "baseline": baseline,
                "percent_unescaped": interpreted,
            }
        )
    total = sum(r["baseline"]["numeric_reference_count"] for r in rows)
    baseline = sum(r["baseline"]["numeric_matched_count"] for r in rows)
    interpreted = sum(r["percent_unescaped"]["numeric_matched_count"] for r in rows)
    return {
        "source_scores_sha256": hashlib.sha256(raw).hexdigest(),
        "metric_source_sha256": hashlib.sha256(
            Path(receipt_metrics.__file__).read_bytes()
        ).hexdigest(),
        "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "transformation": r"Interpret only LaTeX \% as a percent sign for diagnostic scoring.",
        "limits": "No output or reference edits. Field correctness is not established.",
        "numeric_reference_count": total,
        "baseline_matched": baseline,
        "percent_unescaped_matched": interpreted,
        "additional_matches": interpreted - baseline,
        "changed_requests": sum(r["baseline"] != r["percent_unescaped"] for r in rows),
        "requests": rows,
    }


def main():
    """Write a separate diagnostic audit beside preserved baseline scores."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "requests"}))


if __name__ == "__main__":
    main()

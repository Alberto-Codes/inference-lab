"""Reproduce shared-capacity timing and OCR diagnostics from saved outcomes."""

import argparse
import hashlib
import json
from collections import Counter
from http import HTTPStatus
from pathlib import Path

from score_scaling import percentile

from inference_lab import receipt_metrics


def load_evidence(source):
    """Verify trace, terminal identities and durable policy decisions together."""
    plan = json.loads((source / "plan.json").read_text())
    trace_raw = (source / "trace.json").read_bytes()
    if hashlib.sha256(trace_raw).hexdigest() != plan["trace_sha256"]:
        raise ValueError("Trace hash mismatch")
    condition = plan["condition"]
    trace = [
        j
        for j in json.loads(trace_raw)["requests"]
        if condition in ("fifo", "reserved") or j["consumer"] == condition
    ]
    expected = {j["index"]: j for j in trace}
    records = {}
    digest = hashlib.sha256()
    decisions_digest = hashlib.sha256()
    dispatch_digest = hashlib.sha256()
    for path in sorted((source / "terminal").glob("*.json")):
        raw = path.read_bytes()
        digest.update(raw)
        record = json.loads(raw)
        index = record["index"]
        if (
            index not in expected
            or index in records
            or any(record.get(k) != v for k, v in expected[index].items())
        ):
            raise ValueError("Terminal identity differs from frozen trace")
        decision = source / "decisions" / path.name
        if not decision.exists():
            raise ValueError("Terminal outcome lacks policy decision")
        decision_raw = decision.read_bytes()
        decision_value = json.loads(decision_raw)
        if (
            any(decision_value.get(k) != v for k, v in expected[index].items())
            or decision_value.get("decision") != record["policy_decision"]
        ):
            raise ValueError("Policy decision differs from terminal outcome")
        if (
            decision_value.get("policy") != condition
            or record.get("policy") != condition
            or decision_value.get("terminal_offset_s")
            != record.get("finished_offset_s")
            or decision_value.get("dispatch_offset_s")
            != record.get("dispatch_offset_s")
        ):
            raise ValueError("Policy timing or condition differs from terminal outcome")
        if record.get("dispatch_offset_s") is not None:
            dispatch_path = source / "dispatch" / path.name
            dispatch_raw = dispatch_path.read_bytes()
            dispatch = json.loads(dispatch_raw)
            if (
                any(dispatch.get(k) != v for k, v in expected[index].items())
                or dispatch.get("policy") != condition
                or not 0
                <= dispatch.get("admission_offset_s", -1)
                <= record["dispatch_offset_s"]
            ):
                raise ValueError("Dispatch intent differs from terminal outcome")
            if decision_value.get("dispatch_offset_s") != record["dispatch_offset_s"]:
                raise ValueError("Policy dispatch differs from terminal outcome")
            dispatch_digest.update(dispatch_raw)
        decisions_digest.update(decision_raw)
        records[index] = record
    return (
        plan,
        trace,
        records,
        {
            "terminal_sha256": digest.hexdigest(),
            "decisions_sha256": decisions_digest.hexdigest(),
            "dispatch_sha256": dispatch_digest.hexdigest(),
        },
    )


def summarize(source):
    """Keep all planned requests in attainment and quality denominators."""
    plan, trace, records, evidence_hashes = load_evidence(source)
    condition = plan["condition"]
    result = (
        json.loads((source / "result.json").read_text())
        if (source / "result.json").exists()
        else {}
    )
    complete = len(records) == len(trace)
    eligible = complete and result.get("capacity_eligible", False)
    settings = plan["settings"]
    window = settings["duration"]
    elapsed = max(window, result.get("elapsed_s", 0))
    consumers = {}
    for consumer in ("urgent", "bulk"):
        jobs = [j for j in trace if j["consumer"] == consumer]
        rows = [records[j["index"]] for j in jobs if j["index"] in records]
        counts = Counter(r["status"] for r in rows)
        scores = [
            receipt_metrics.score(
                j["reference"],
                receipt_metrics.plain_text(records[j["index"]]["text"])
                if j["index"] in records and records[j["index"]]["status"] == "success"
                else "",
            )
            for j in jobs
        ]
        successes = [r for r in rows if r["status"] == "success"]
        attained = sum(
            r.get("e2e_s") is not None and r["e2e_s"] <= settings["urgent_deadline"]
            for r in successes
        )
        total = sum(s["numeric_reference_count"] for s in scores)
        matched = sum(s["numeric_matched_count"] for s in scores)
        consumers[consumer] = {
            "scheduled": len(jobs),
            "terminal": len(rows),
            "missing_outcomes": len(jobs) - len(rows),
            "interrupted_dispatches": sum(
                j["index"] not in records
                and (source / "dispatch" / f"{j['index']:09}.json").exists()
                for j in jobs
            ),
            "status_counts": dict(counts),
            "normal_completions": len(successes),
            "deadline_met": attained if consumer == "urgent" else None,
            "deadline_misses": len(jobs) - attained if consumer == "urgent" else None,
            "deadline_attainment": attained / len(jobs)
            if consumer == "urgent" and jobs
            else None,
            "all_e2e_p50_s": percentile(
                [r["e2e_s"] for r in rows if r.get("e2e_s") is not None], 0.5
            ),
            "all_e2e_p99_s": percentile(
                [r["e2e_s"] for r in rows if r.get("e2e_s") is not None], 0.99
            ),
            "all_e2e_p95_s": percentile(
                [r["e2e_s"] for r in rows if r.get("e2e_s") is not None], 0.95
            ),
            "success_e2e_p95_s": percentile([r["e2e_s"] for r in successes], 0.95),
            "max_wait_s": max(
                (r["queue_s"] for r in rows if r.get("queue_s") is not None),
                default=None,
            ),
            "deferred": sum(r.get("deferred", False) for r in rows),
            "never_dispatched": sum(r.get("dispatch_offset_s") is None for r in rows),
            "completed_per_s_during_arrivals": sum(
                r["finished_offset_s"] <= window for r in successes
            )
            / window
            if eligible
            else None,
            "completed_per_s_including_drain": len(successes) / elapsed
            if eligible
            else None,
            "completion_time_s": max(
                (r["finished_offset_s"] for r in successes), default=None
            )
            if len(successes) == len(jobs)
            else None,
            "last_terminal_s": max(
                (r.get("finished_offset_s", 0) for r in rows), default=None
            ),
            "unfinished_work": len(jobs) - len(successes),
            "timeouts": counts["timeout"] + counts["drain_timeout"],
            "truncations": counts["incomplete"],
            "http_failures": sum(
                r.get("http_status", 200) >= HTTPStatus.BAD_REQUEST for r in rows
            ),
            "generation_quality_failures": counts["quality_failed"],
            "requests_missing_reference_numbers": sum(
                bool(s["missing_numbers"]) for s in scores
            ),
            "successful_requests_missing_reference_numbers": sum(
                bool(
                    receipt_metrics.score(
                        r["reference"], receipt_metrics.plain_text(r["text"])
                    )["missing_numbers"]
                )
                for r in successes
            ),
            "macro_rouge_l_f1": sum(s["rouge_l_f1"] or 0 for s in scores) / len(scores)
            if scores
            else None,
            "numeric_matched": matched,
            "numeric_total": total,
            "numeric_recall": matched / total if total else None,
            "verified_correct_output_count": None,
        }
    return {
        "condition": condition,
        "complete": complete,
        "capacity_eligible": eligible,
        "consumers": consumers,
        "runtime": result,
        "trace_sha256": plan["trace_sha256"],
        **evidence_hashes,
        "metric_source_sha256": hashlib.sha256(
            Path(receipt_metrics.__file__).read_bytes()
        ).hexdigest(),
        "scorer_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "quality_scope": (
            "Partial-reference numeric diagnostics; "
            "normal termination is not correct OCR."
        ),
    }


def main():
    """Write a new report without modifying any raw evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = summarize(args.input)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report))


if __name__ == "__main__":
    main()

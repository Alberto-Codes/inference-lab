"""Compare paired shared-capacity trials without hiding absent measurements."""

import argparse
import hashlib
import json
from pathlib import Path

from score_shared_capacity import summarize
from shared_capacity_suite import condition_order

MATCHED_PLAN_FIELDS = (
    "trace_sha256",
    "settings",
    "profile",
    "manifest",
    "cache",
    "runner_sha256",
    "client_sha256",
    "retries",
)


def _metrics(summary):
    urgent = summary["consumers"]["urgent"]
    bulk = summary["consumers"]["bulk"]
    return {
        "urgent_deadline_attainment": urgent["deadline_attainment"],
        "urgent_success_e2e_p95_s": urgent["success_e2e_p95_s"],
        "bulk_normal_completions": bulk["normal_completions"],
        "bulk_completed_per_s_during_arrivals": bulk["completed_per_s_during_arrivals"],
        "bulk_completed_per_s_including_drain": bulk["completed_per_s_including_drain"],
        "bulk_completion_time_s": bulk["completion_time_s"],
        "bulk_unfinished_work": bulk["unfinished_work"],
        "bulk_max_wait_s": bulk["max_wait_s"],
        "reserved_idle_slot_s_with_bulk_waiting": summary["runtime"].get(
            "reserved_idle_slot_s_with_bulk_waiting"
        ),
    }


def _trial(source, protocol, arm, plans):
    name = arm["name"]
    trial = {**arm, "status": "unmeasured", "summary": None}
    path = source / name
    if path.parent != source or name in plans:
        return {
            **trial,
            "status": "invalid_evidence",
            "error": "Invalid or duplicate arm name",
        }
    try:
        plan = json.loads((path / "plan.json").read_text())
        plans[name] = plan
        if (
            plan["condition"] != arm["condition"]
            or plan["settings"] != protocol["settings"]
            or plan["manifest"] != protocol["manifest"]
        ):
            return {
                **trial,
                "status": "invalid_evidence",
                "error": "Arm differs from frozen suite protocol",
            }
        summary = summarize(path)
        trial["summary"] = summary
        trial["status"] = (
            "complete"
            if summary["complete"] and summary["capacity_eligible"]
            else "ineligible"
            if summary["complete"]
            else "partial"
            if any(c["terminal"] for c in summary["consumers"].values())
            else "unmeasured"
        )
    except FileNotFoundError as error:
        trial["error"] = f"Missing evidence: {error.filename}"
    except (ValueError, KeyError, TypeError) as error:
        trial.update(status="invalid_evidence", error=str(error))
    return trial


def _pair(repeat, conditions, by_name, plans, order_valid, prefix=""):
    names = [f"{condition}-{repeat}" for condition in conditions]
    pair = {"repeat": repeat, "arms": names, "comparable": False, "delta": None}
    reasons = []
    if not order_valid:
        reasons.append(
            "Planned order does not establish alternating baseline and mixed pairs"
        )
    reasons.extend(
        f"{name} is missing, incomplete or capacity-ineligible"
        for name in names
        if name not in by_name or by_name[name]["status"] != "complete"
    )
    if all(name in plans for name in names):
        reasons.extend(
            f"Arms differ or omit {field}"
            for field in MATCHED_PLAN_FIELDS
            if field not in plans[names[0]]
            or field not in plans[names[1]]
            or plans[names[0]][field] != plans[names[1]][field]
        )
    else:
        reasons.append("Arm plan is missing")
    if not reasons:
        summaries = [by_name[name]["summary"] for name in names]
        if any(
            consumer["timeouts"]
            or consumer["status_counts"].get("backend_uncertain", 0)
            for summary in summaries
            for consumer in summary["consumers"].values()
        ):
            reasons.append("Backend execution is uncertain")
        else:
            first, second = (
                {k: v for k, v in _metrics(summary).items() if k.startswith(prefix)}
                for summary in summaries
            )
            pair.update(
                comparable=True,
                **dict(zip(conditions, (first, second), strict=True)),
                delta={
                    key: second[key] - first[key]
                    if first[key] is not None and second[key] is not None
                    else None
                    for key in first
                },
            )
    pair["exclusion_reasons"] = reasons
    return pair


def report(source):
    """Retain every planned trial and compare only complete, matched arms."""
    protocol_raw = (source / "protocol.json").read_bytes()
    protocol = json.loads(protocol_raw)
    order = protocol["order"]
    repeats = len(order) // 4
    order_valid = repeats > 0 and order == condition_order(repeats)
    plans = {}
    trials = [_trial(source, protocol, arm, plans) for arm in order]
    by_name = {trial["name"]: trial for trial in trials}
    pairs = [
        _pair(repeat, ("fifo", "reserved"), by_name, plans, order_valid)
        for repeat in range(repeats)
    ]
    baseline_comparisons = [
        {
            "baseline": baseline,
            "policy": policy,
            **_pair(
                repeat,
                (baseline, policy),
                by_name,
                plans,
                order_valid,
                prefix=f"{baseline}_",
            ),
        }
        for repeat in range(repeats)
        for baseline in ("urgent", "bulk")
        for policy in ("fifo", "reserved")
    ]
    return {
        "schema": 1,
        "protocol_sha256": hashlib.sha256(protocol_raw).hexdigest(),
        "report_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "planned_order": order,
        "planned_order_valid": order_valid,
        "planned_repetitions": repeats,
        "trials": trials,
        "pairs": pairs,
        "comparable_pairs": sum(pair["comparable"] for pair in pairs),
        "baseline_comparisons": baseline_comparisons,
        "comparable_baseline_comparisons": sum(
            comparison["comparable"] for comparison in baseline_comparisons
        ),
        "delta_convention": (
            "pairs: reserved minus FIFO; baseline_comparisons: mixed policy minus "
            "isolated baseline, for the baseline class only; attainment is a "
            "fraction, not percentage points"
        ),
        "scope": (
            "Warmed repeated inputs, one model and GPU. No fresh-ingress or OCR "
            "correctness claim. Missing and uncertain trials are not capacity evidence."
        ),
    }


def main():
    """Write a new offline matrix report while preserving source evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.input)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

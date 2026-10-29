"""Replay frozen urgent and bulk arrivals against bounded shared admission."""

import argparse
import asyncio
import hashlib
import json
import math
import time
from pathlib import Path

import httpx
from scaling_experiment import load_inputs, save, telemetry

from inference_lab import client as client_module
from inference_lab import serving
from inference_lab.client import infer

DEFAULTS = {
    "duration": 300.0,
    "urgent_rate": 1.0,
    "burst_size": 120,
    "burst_interval": 30.0,
    "concurrency": 8,
    "reserved": 2,
    "urgent_deadline": 5.0,
    "bulk_wait": 60.0,
    "timeout": 120.0,
    "drain": 180.0,
    "url": "http://127.0.0.1:8017",
}
CONDITIONS = ("urgent", "bulk", "fifo", "reserved")


def validate(settings):
    """Reject invalid or unbounded configurations before creating evidence."""
    for name in DEFAULTS.keys() - {"url"}:
        if not math.isfinite(settings[name]) or settings[name] <= 0:
            raise ValueError(f"{name} must be finite and positive")
    for name in ("burst_size", "concurrency", "reserved"):
        if not isinstance(settings[name], int):
            raise TypeError(f"{name} must be an integer")
    if settings["reserved"] >= settings["concurrency"]:
        raise ValueError("reserved must be smaller than concurrency")


def make_trace(manifest, settings):
    """Assign the same cyclic documents and arrival times to both mixed arms."""
    validate(settings)
    pages = manifest["pages"]
    if not pages:
        raise ValueError("Empty corpus")
    if any(int(p["id"]) in range(80, 100) for p in pages):
        raise ValueError("Reserved CORD rows cannot enter this experiment")
    arrivals = [
        (sequence / settings["urgent_rate"], "urgent", sequence)
        for sequence in range(math.ceil(settings["duration"] * settings["urgent_rate"]))
    ]
    for burst in range(math.ceil(settings["duration"] / settings["burst_interval"])):
        arrivals.extend(
            (
                burst * settings["burst_interval"],
                "bulk",
                burst * settings["burst_size"] + offset,
            )
            for offset in range(settings["burst_size"])
        )
    trace = []
    for due, consumer, sequence in sorted(arrivals):
        if due >= settings["duration"]:
            continue
        page_index = sequence % len(pages)
        item = pages[page_index]
        trace.append(
            {
                "index": len(trace),
                "consumer": consumer,
                "sequence": sequence,
                "scheduled_offset_s": due,
                "page_index": page_index,
                "id": item["id"],
                "sha256": item["sha256"],
                "reference": item["reference"],
            }
        )
    return trace


def initialize(output, manifest, settings, condition):
    """Freeze all planned arrivals, settings and executable identities before HTTP."""
    if condition not in CONDITIONS:
        raise ValueError("Unknown condition")
    trace = make_trace(manifest, settings)
    output.mkdir(parents=True, exist_ok=False)
    for folder in (
        "terminal",
        "decisions",
        "dispatch",
        "warmup",
        "warmup-started",
        "telemetry",
    ):
        (output / folder).mkdir()
    trace_value = {"requests": trace}
    save(output / "trace.json", trace_value)
    save(
        output / "plan.json",
        {
            "manifest": manifest,
            "settings": settings,
            "condition": condition,
            "profile": serving.config(),
            "cache": "warmed repeated inputs",
            "trace_sha256": hashlib.sha256(
                (output / "trace.json").read_bytes()
            ).hexdigest(),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "client_sha256": hashlib.sha256(
                Path(client_module.__file__).read_bytes()
            ).hexdigest(),
            "retries": 0,
        },
    )


def condition_trace(output, condition):
    """Select an isolated class without changing its mixed-trace assignments."""
    trace = json.loads((output / "trace.json").read_text())["requests"]
    return [
        r
        for r in trace
        if condition in ("fifo", "reserved") or r["consumer"] == condition
    ]


async def measure(client, pages, output, settings, condition):  # noqa: C901, PLR0912, PLR0915 - one explicit admission state machine
    """Bound upstream requests until responses, and stop dispatch on uncertainty."""
    trace = condition_trace(output, condition)
    start = time.perf_counter()
    save(
        output / "measurement-start.json", {"unix_s": time.time(), "monotonic_s": start}
    )
    queue = []
    deferred = set()
    active = {}
    sent_offsets = {}
    cursor = 0
    uncertain = False
    peak = 0
    idle_reserved = 0.0
    previous = 0.0
    idle_slots = 0
    drain_end = settings["duration"] + settings["drain"]

    def wait_limit(job):
        if job["consumer"] == "urgent":
            return settings["urgent_deadline"]
        return settings["bulk_wait"]

    def finish(job, record, now, decision, dispatch=None):
        age = max(0.0, now - job["scheduled_offset_s"])
        entry = {
            **job,
            **record,
            "policy": condition,
            "policy_decision": decision,
            "queue_s": (dispatch if dispatch is not None else now)
            - job["scheduled_offset_s"],
            "e2e_s": age,
            "finished_offset_s": now,
            "dispatch_offset_s": dispatch,
            "deferred": job["index"] in deferred,
        }
        save(
            output / "decisions" / f"{job['index']:09}.json",
            {
                **job,
                "policy": condition,
                "decision": decision,
                "dispatch_offset_s": dispatch,
                "terminal_offset_s": now,
            },
        )
        save(output / "terminal" / f"{job['index']:09}.json", entry)

    async def send(job):
        # Intent persistence can delay task scheduling. Check the actual send
        # boundary again so slow evidence writes cannot dispatch expired work.
        dispatched = time.perf_counter() - start
        if dispatched >= drain_end or dispatched - job[
            "scheduled_offset_s"
        ] >= wait_limit(job):
            status = "drain_expired" if dispatched >= drain_end else "queue_expired"
            return {"status": status, "text": "", "latency_s": 0}, None
        sent_offsets[job["index"]] = dispatched
        return await infer(
            client, pages[job["page_index"]], settings["timeout"], retain_response=True
        ), dispatched

    while cursor < len(trace) or queue or active:
        now = time.perf_counter() - start
        idle_reserved += idle_slots * (now - previous)
        previous = now
        for task in list(active):
            if task.done():
                job, _admitted = active.pop(task)
                record, dispatched = task.result()
                unknown = record["status"] == "timeout" or (
                    record["status"] == "error" and "http_status" not in record
                )
                uncertain |= unknown
                finish(
                    job,
                    {**record, "backend_execution_unknown": unknown},
                    now,
                    "dispatched" if dispatched is not None else record["status"],
                    dispatched,
                )
        while cursor < len(trace) and trace[cursor]["scheduled_offset_s"] <= now:
            queue.append(trace[cursor])
            cursor += 1
        for job in list(queue):
            status = (
                "backend_uncertain"
                if uncertain
                else "drain_expired"
                if now >= drain_end
                else "queue_expired"
                if now - job["scheduled_offset_s"] >= wait_limit(job)
                else None
            )
            if status:
                queue.remove(job)
                finish(job, {"status": status, "text": "", "latency_s": 0}, now, status)
        if now >= drain_end:
            for task, (job, admitted) in active.items():
                dispatched = sent_offsets.get(job["index"], admitted)
                task.cancel()
                finish(
                    job,
                    {
                        "status": "drain_timeout",
                        "text": "",
                        "latency_s": now - dispatched,
                        "backend_execution_unknown": True,
                    },
                    now,
                    "dispatched",
                    dispatched,
                )
            if active:
                await asyncio.gather(*active, return_exceptions=True)
                uncertain = True
            active.clear()
        while (
            queue
            and len(active) < settings["concurrency"]
            and not uncertain
            and now < drain_end
        ):
            bulk_active = sum(job["consumer"] == "bulk" for job, _ in active.values())
            candidates = queue
            if condition == "reserved":
                candidates = [job for job in queue if job["consumer"] == "urgent"]
                if (
                    not candidates
                    and bulk_active < settings["concurrency"] - settings["reserved"]
                ):
                    candidates = queue
            if not candidates:
                break
            job = candidates[0]
            queue.remove(job)
            dispatched = time.perf_counter() - start
            if dispatched >= drain_end or dispatched - job[
                "scheduled_offset_s"
            ] >= wait_limit(job):
                status = "drain_expired" if dispatched >= drain_end else "queue_expired"
                finish(
                    job,
                    {"status": status, "text": "", "latency_s": 0},
                    dispatched,
                    status,
                )
                continue
            save(
                output / "dispatch" / f"{job['index']:09}.json",
                {**job, "policy": condition, "admission_offset_s": dispatched},
            )
            task = asyncio.create_task(send(job))
            active[task] = (job, dispatched)
            peak = max(peak, len(active))
        deferred.update(j["index"] for j in queue)
        idle_slots = (
            (settings["concurrency"] - len(active))
            if condition == "reserved"
            and queue
            and not uncertain
            and all(j["consumer"] == "bulk" for j in queue)
            else 0
        )
        if not (cursor < len(trace) or queue or active):
            break
        deadlines = [drain_end] if now < drain_end else []
        if cursor < len(trace):
            deadlines.append(trace[cursor]["scheduled_offset_s"])
        deadlines.extend(j["scheduled_offset_s"] + wait_limit(j) for j in queue)
        delay = max(0.0001, min(deadlines, default=now + 0.1) - now)
        if active:
            await asyncio.wait(
                active, timeout=delay, return_when=asyncio.FIRST_COMPLETED
            )
        else:
            await asyncio.sleep(delay)
    return {
        "elapsed_s": time.perf_counter() - start,
        "capacity_eligible": not uncertain,
        "backend_execution_unknown": uncertain,
        "peak_upstream": peak,
        "reserved_idle_slot_s_with_bulk_waiting": idle_reserved,
    }


async def execute(output, manifest, pages, settings, condition, transport=None):
    """Warm every input separately, then measure once with immutable evidence."""
    plan = json.loads((output / "plan.json").read_text())
    if (
        plan["settings"] != settings
        or plan["condition"] != condition
        or plan["manifest"] != manifest
    ):
        raise ValueError("Execution differs from frozen plan")
    expected_hashes = {
        "trace_sha256": output / "trace.json",
        "runner_sha256": Path(__file__),
        "client_sha256": Path(client_module.__file__),
    }
    if plan["profile"] != serving.config() or any(
        hashlib.sha256(path.read_bytes()).hexdigest() != plan[key]
        for key, path in expected_hashes.items()
    ):
        raise ValueError("Frozen execution identity changed")
    if [p.sha256 for p in pages] != [p["sha256"] for p in manifest["pages"]]:
        raise ValueError("Prepared pages differ from frozen manifest")
    if (output / "start.json").exists():
        raise ValueError("Never replay an attempted condition; use a new directory")
    save(output / "start.json", {"unix_s": time.time()})
    async with httpx.AsyncClient(
        base_url=settings["url"],
        transport=transport,
        timeout=settings["timeout"],
        limits=httpx.Limits(max_connections=settings["concurrency"] + 1),
    ) as client:
        for index, page in enumerate(pages):
            intent = {"index": index, "sha256": page.sha256, "phase": "warmup"}
            save(output / "warmup-started" / f"{index:09}.json", intent)
            record = await infer(
                client, page, settings["timeout"], retain_response=True
            )
            save(output / "warmup" / f"{index:09}.json", {**intent, **record})
            if record["status"] not in ("success", "incomplete", "quality_failed"):
                result = {
                    "capacity_eligible": False,
                    "status": "warmup_failed",
                    "elapsed_s": 0,
                    "backend_execution_unknown": True,
                }
                for job in condition_trace(output, condition):
                    save(
                        output / "terminal" / f"{job['index']:09}.json",
                        {
                            **job,
                            "status": "not_started",
                            "text": "",
                            "e2e_s": None,
                            "policy": condition,
                            "policy_decision": "warmup_failed",
                            "queue_s": None,
                            "dispatch_offset_s": None,
                        },
                    )
                    save(
                        output / "decisions" / f"{job['index']:09}.json",
                        {
                            **job,
                            "policy": condition,
                            "decision": "warmup_failed",
                            "dispatch_offset_s": None,
                            "terminal_offset_s": None,
                        },
                    )
                save(output / "result.json", result)
                return result
        stop = asyncio.Event()
        sampler = asyncio.create_task(telemetry(output, "measurement", client, stop))
        try:
            result = await measure(client, pages, output, settings, condition)
        finally:
            stop.set()
            await sampler
    result["status"] = (
        "complete" if result["capacity_eligible"] else "backend_uncertain"
    )
    save(output / "result.json", result)
    return result


def main():
    """Run a single condition against an already prepared, idle demo server."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    args = parser.parse_args()
    manifest, pages = load_inputs(args.input)
    initialize(args.output, manifest, DEFAULTS, args.condition)
    print(
        json.dumps(
            asyncio.run(execute(args.output, manifest, pages, DEFAULTS, args.condition))
        )
    )


if __name__ == "__main__":
    main()

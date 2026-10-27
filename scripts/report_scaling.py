"""Aggregate saved trials and resource samples without GPU inference."""

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from http import HTTPStatus
from pathlib import Path


def metric(text, name):
    """Read a single-engine Prometheus scalar without interpreting other metrics."""
    values = [
        float(line.rsplit(" ", 1)[1])
        for line in text.splitlines()
        if line.startswith(name + "{") or line.startswith(name + " ")
    ]
    return sum(values) if values else None


def cpu_seconds(value):
    """Parse the Go duration emitted by Podman stats."""
    units = {"h": 3600, "m": 60, "s": 1, "ms": 0.001, "µs": 0.000001, "ns": 1e-9}
    return sum(
        float(number) * units[unit]
        for number, unit in re.findall(r"([\d.]+)(ns|µs|ms|h|m|s)", value)
    )


def resources(source, records, window):
    """Summarize arrival-window samples and retain collection-gap counts."""
    start = min(r["scheduled_unix_s"] for r in records)
    samples = [json.loads(p.read_text()) for p in (source / "telemetry").glob("*.json")]
    samples = sorted(
        (s for s in samples if start <= s["unix_s"] <= start + window),
        key=lambda s: s["unix_s"],
    )
    gpu, power, temperature, memory, cpu, waiting, running = [], [], [], [], [], [], []
    previous = None
    errors = Counter()
    for sample in samples:
        errors.update(key for key in sample if key.endswith("_error"))
        if "gpu" in sample:
            values = [float(v) for v in sample["gpu"].split(",")]
            gpu.append(values[0])
            memory.append(values[2])
            power.append(values[3])
            temperature.append(values[4])
        if "container" in sample:
            container = json.loads(sample["container"])[0]
            current = (sample["unix_s"], cpu_seconds(container["cpu_time"]))
            if previous and current[0] > previous[0]:
                cpu.append((current[1] - previous[1]) / (current[0] - previous[0]))
            previous = current
        for key, target in [
            ("vllm:num_requests_waiting", waiting),
            ("vllm:num_requests_running", running),
        ]:
            value = metric(sample.get("metrics", ""), key)
            if value is not None:
                target.append(value)
    result = {"samples": len(samples), "errors": dict(errors)}
    observed_cpu = [
        (sample["unix_s"], sample["client_cpu_s"])
        for sample in samples
        if "client_cpu_s" in sample
    ]
    result["client_cpu_cores"] = (
        (observed_cpu[-1][1] - observed_cpu[0][1])
        / (observed_cpu[-1][0] - observed_cpu[0][0])
        if len(observed_cpu) > 1
        else None
    )
    for key, values in [
        ("gpu_percent", gpu),
        ("power_w", power),
        ("temperature_c", temperature),
        ("memory_mib", memory),
        ("container_cpu_cores", cpu),
        ("server_waiting", waiting),
        ("server_running", running),
    ]:
        result[key] = {
            "mean": statistics.mean(values) if values else None,
            "max": max(values) if values else None,
        }
    for key in (
        "vllm:mm_cache_queries_total",
        "vllm:mm_cache_hits_total",
        "vllm:generation_tokens_total",
    ):
        values = [metric(s.get("metrics", ""), key) for s in samples]
        values = [v for v in values if v is not None]
        result[key + "_observed_delta"] = (
            values[-1] - values[0] if len(values) > 1 else None
        )
    return result


def output_tokens(record):
    """Read observed output usage, retaining absent or malformed usage as zero."""
    try:
        return (
            json.loads(record["response_body"])
            .get("usage", {})
            .get("completion_tokens", 0)
        )
    except (ValueError, AttributeError, TypeError):
        return 0


def aggregate(root):
    """Keep every repetition visible and report ranges rather than pooled certainty."""
    conditions, groups = [], defaultdict(list)
    for path in sorted(root.glob("*/scores.json")):
        result = json.loads(path.read_text())
        summary, settings = result["summary"], result["plan"]["settings"]
        records = result["requests"]
        if not summary["capacity_eligible"]:
            raise ValueError(f"Incomplete or resumed timing: {path}")
        item = {
            "condition": path.parent.name,
            "cache": settings["cache"],
            **summary,
            "resources": resources(path.parent, records, summary["offered_window_s"]),
        }
        item["http_200"] = sum(r.get("http_status") == HTTPStatus.OK for r in records)
        item["output_tokens"] = sum(
            output_tokens(r) for r in records if r.get("http_status") == HTTPStatus.OK
        )
        by_document = Counter()
        for record in records:
            if record.get("http_status") == HTTPStatus.OK:
                by_document[str(record["id"])] += output_tokens(record)
        item["returned_output_tokens_by_document"] = dict(by_document)
        conditions.append(item)
        groups[(settings["cache"], settings["rate"])].append(item)
    ranges = []
    for (cache, rate), runs in sorted(groups.items()):
        group = {"cache": cache, "rate": rate, "repeats": len(runs)}
        for name in (
            "completed_per_s_including_drain",
            "completed_per_s_during_arrivals",
            "all_e2e_p95_s",
            "queue_p95_s",
            "micro_numeric_recall",
        ):
            values = [r[name] for r in runs]
            group[name] = {
                "mean": statistics.mean(values),
                "min": min(values),
                "max": max(values),
            }
        group["status_counts"] = dict(
            sum((Counter(r["status_counts"]) for r in runs), Counter())
        )
        ranges.append(group)
    return {
        "conditions": conditions,
        "ranges": ranges,
        "limits": "Repetition ranges, not confidence intervals. Repeated documents are dependent.",
    }


def main():
    """Write a new aggregate file from completed offline score artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.input)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {"conditions": len(result["conditions"]), "output": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()

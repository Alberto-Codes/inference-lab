"""Run one manifest-driven open-loop condition with durable, resumable evidence."""

import argparse
import asyncio
import fcntl
import hashlib
import json
import math
import os
import subprocess
import time
import uuid
from contextlib import suppress
from pathlib import Path

import httpx

from inference_lab import serving
from inference_lab.client import infer, prepare


def save(path: Path, value: dict):
    """Atomically create evidence without replacing any existing file."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x") as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def load_inputs(corpus: Path):
    """Verify provenance and all image hashes before preparing bounded work."""
    manifest = json.loads((corpus / "manifest.json").read_text())
    for field in ("dataset", "revision", "license", "partition"):
        if not manifest.get(field):
            raise ValueError(f"Manifest needs {field}")
    if manifest["partition"] != "coverage":
        raise ValueError("Only coverage inputs are allowed; evaluation stays untouched")
    pages, identities = [], set()
    for item in manifest["pages"]:
        identity = str(item["id"])
        if identity in identities or item["id"] in manifest.get("evaluation_rows", []):
            raise ValueError("Duplicate or reserved evaluation identity")
        identities.add(identity)
        path = (corpus / item["file"]).resolve()
        if not path.is_relative_to(corpus.resolve()):
            raise ValueError("Image must stay inside corpus")
        page = prepare(path)
        if page.sha256 != item["sha256"]:
            raise ValueError(f"Image hash mismatch: {identity}")
        if "reference" not in item:
            item["reference"] = " ".join(
                word["text"]
                for line in item["ground_truth"]["valid_line"]
                for word in line["words"]
            )
        pages.append(page)
    if not pages:
        raise ValueError("Empty corpus")
    return manifest, pages


def validate(settings: dict, page_count: int):
    """Reject invalid workloads before creating evidence or sending requests."""
    for name in ("rate", "timeout"):
        if not math.isfinite(settings[name]) or settings[name] <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if settings["count"] < 1 or settings["concurrency"] < 1 or settings["queue"] < 1:
        raise ValueError("count, concurrency and queue must be positive")
    if settings["cache"] == "fresh" and settings["count"] > page_count:
        raise ValueError("Fresh inputs cannot repeat within a run")


def initialize(output: Path, manifest: dict, settings: dict, resume: bool):
    """Bind resume to identical inputs, settings, and request implementation."""
    from inference_lab import client as client_module  # noqa: PLC0415

    if settings["cache"] == "fresh" and len(
        {p["sha256"] for p in manifest["pages"]}
    ) != len(manifest["pages"]):
        raise ValueError("Fresh inputs must have unique image hashes")
    identity = {
        "manifest": manifest,
        "settings": settings,
        "profile": serving.config(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "client_sha256": hashlib.sha256(
            Path(client_module.__file__).read_bytes()
        ).hexdigest(),
        "retries": 0,
    }
    if resume:
        if json.loads((output / "plan.json").read_text()) != identity:
            raise ValueError("Resume plan differs; use a new output directory")
    else:
        output.mkdir(parents=True, exist_ok=False)
        for name in (
            "started",
            "terminal",
            "sessions",
            "telemetry",
            "warmup",
            "warmup-started",
        ):
            (output / name).mkdir()
        save(output / "plan.json", identity)
    return identity


def recover(output: Path):
    """Mark orphaned attempts unknown without reissuing or deleting their evidence."""
    for source, target in (("started", "terminal"), ("warmup-started", "warmup")):
        for path in sorted((output / source).glob("*.json")):
            destination = output / target / path.name
            if not destination.exists():
                started = json.loads(path.read_text())
                save(
                    destination,
                    {
                        **started,
                        "status": "interrupted",
                        "text": "",
                        "error": "Interrupted before durable result; server outcome unknown",
                        "latency_s": None,
                        "e2e_s": None,
                    },
                )


async def telemetry(
    output: Path, session: str, client: httpx.AsyncClient, stop: asyncio.Event
):
    """Sample GPU, container CPU and server metrics, retaining collection errors."""
    index = 0
    while not stop.is_set():
        sample = {"unix_s": time.time()}
        commands = {
            "gpu": [
                "nvidia-smi",
                "--id=0",
                "--query-gpu=utilization.gpu,utilization.memory,"
                "memory.used,power.draw,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            "container": [
                "podman",
                "stats",
                "--no-stream",
                "--format",
                "json",
                serving.config()["container"],
            ],
        }
        for name, command in commands.items():
            try:
                sample[name] = await asyncio.to_thread(serving.command, command, 3)
            except (
                OSError,
                RuntimeError,
                TimeoutError,
                subprocess.TimeoutExpired,
            ) as error:
                sample[name + "_error"] = str(error)
        try:
            response = await client.get("/metrics", timeout=3)
            response.raise_for_status()
            sample["metrics"] = response.text
        except httpx.HTTPError as error:
            sample["metrics_error"] = str(error)
        sample["client_cpu_s"] = time.process_time()
        save(output / "telemetry" / f"{session}-{index:06}.json", sample)
        index += 1
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=1)


async def measure(client, pages, manifest, output, settings, session):
    """Schedule independently of completions; bound workers and waiting backlog."""
    pending = [
        i
        for i in range(settings["count"])
        if not (output / "terminal" / f"{i:09}.json").exists()
    ]
    queue = asyncio.Queue(maxsize=settings["queue"])
    start = time.perf_counter()

    async def worker():
        while True:
            job = await queue.get()
            if job is None:
                queue.task_done()
                return
            index, due, admitted = job
            began = time.perf_counter()
            remaining = settings["timeout"] - (began - due)
            if remaining <= 0:
                record = {"status": "queue_timeout", "text": "", "latency_s": 0}
            else:
                record = await infer(
                    client, pages[index % len(pages)], remaining, retain_response=True
                )
            record.update(
                **admitted,
                queue_s=began - due,
                e2e_s=time.perf_counter() - due,
                finished_offset_s=time.perf_counter() - start,
            )
            save(output / "terminal" / f"{index:09}.json", record)
            queue.task_done()

    async with asyncio.TaskGroup() as tasks:
        for _ in range(settings["concurrency"]):
            tasks.create_task(worker())
        for sequence, index in enumerate(pending):
            due = start + sequence / settings["rate"]
            await asyncio.sleep(max(0, due - time.perf_counter()))
            item = manifest["pages"][index % len(pages)]
            admitted = {
                "index": index,
                "id": item["id"],
                "session": session,
                "scheduled_offset_s": due - start,
                "scheduled_unix_s": time.time() - (time.perf_counter() - due),
                "arrival_lag_s": time.perf_counter() - due,
                "sha256": item["sha256"],
                "reference": item["reference"],
            }
            save(output / "started" / f"{index:09}.json", admitted)
            try:
                queue.put_nowait((index, due, admitted))
            except asyncio.QueueFull:
                save(
                    output / "terminal" / f"{index:09}.json",
                    {
                        **admitted,
                        "status": "queue_full",
                        "text": "",
                        "latency_s": 0,
                        "e2e_s": time.perf_counter() - due,
                        "finished_offset_s": time.perf_counter() - start,
                    },
                )
        await queue.join()
        for _ in range(settings["concurrency"]):
            await queue.put(None)
    return {
        "elapsed_s": time.perf_counter() - start,
        "scheduled_count": len(pending),
        "offered_window_s": len(pending) / settings["rate"],
    }


async def execute(output, manifest, pages, settings, transport=None):
    """Run separate warmup and measurement sessions, with no automatic retries."""
    session = uuid.uuid4().hex
    recover(output)
    completed = len(list((output / "terminal").glob("*.json")))
    if completed == settings["count"]:
        return {"status": "already_complete"}
    save(
        output / "sessions" / f"{session}-start.json",
        {
            "unix_s": time.time(),
            "previous_terminal_count": completed,
            "capacity_eligible": completed == 0,
        },
    )
    async with httpx.AsyncClient(
        base_url=settings["url"],
        timeout=settings["timeout"],
        transport=transport,
        limits=httpx.Limits(max_connections=settings["concurrency"] + 1),
    ) as client:
        # Fresh runs warm the server on one disjoint image, supplied separately.
        warm_pages = (
            pages
            if settings["cache"] == "repeated"
            else [prepare(Path(settings["warmup_image"]))]
        )
        for index, page in enumerate(warm_pages):
            filename = f"{session}-{index:06}.json"
            intent = {
                "phase": "warmup",
                "session": session,
                "index": index,
                "page": page.name,
                "sha256": page.sha256,
                "started_unix_s": time.time(),
            }
            save(output / "warmup-started" / filename, intent)
            record = await infer(
                client, page, settings["timeout"], retain_response=True
            )
            save(output / "warmup" / filename, {**intent, **record})
            if record["status"] not in ("success", "incomplete", "quality_failed"):
                raise RuntimeError("Warmup transport failed; measurement did not start")
        stop = asyncio.Event()
        async with asyncio.TaskGroup() as tasks:
            sampler = tasks.create_task(telemetry(output, session, client, stop))
            try:
                result = await measure(
                    client, pages, manifest, output, settings, session
                )
            finally:
                stop.set()
            await sampler
    result.update(status="complete", capacity_eligible=completed == 0)
    save(output / "sessions" / f"{session}-end.json", result)
    return result


def main():
    """Execute one condition; keep service handover outside resumable run directories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8017")
    parser.add_argument("--rate", type=float, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--queue", type=int, default=128)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--cache", choices=("fresh", "repeated"), default="repeated")
    parser.add_argument("--warmup-image", default="")
    args = parser.parse_args()
    settings = {
        key: value
        for key, value in vars(args).items()
        if key not in ("input", "output", "resume")
    }
    manifest, pages = load_inputs(args.input)
    validate(settings, len(pages))
    if settings["cache"] == "fresh":
        warm = prepare(Path(settings["warmup_image"]))
        if warm.sha256 in {page.sha256 for page in pages}:
            raise ValueError("Fresh warmup must use a disjoint image")
        settings["warmup_sha256"] = warm.sha256
    initialize(args.output, manifest, settings, args.resume)
    with (args.output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(asyncio.run(execute(args.output, manifest, pages, settings))))


if __name__ == "__main__":
    main()

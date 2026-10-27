"""Inspect and manage only this checkout's labelled Podman container."""

import json
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
LABEL = "dev.inference-lab.root"


def config() -> dict:
    return json.loads((ROOT / "serving/config.json").read_text())


def command(argv: list[str], timeout: float = 20) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{argv[0]} failed: {result.stderr.strip()[:500]}")
    return result.stdout.strip()


def gpu() -> dict:
    fields = "name,uuid,driver_version,memory.total,memory.free,utilization.gpu"
    values = command(
        [
            "nvidia-smi",
            "--id=0",
            f"--query-gpu={fields}",
            "--format=csv,noheader,nounits",
        ]
    ).split(", ")
    return dict(zip(fields.split(","), values, strict=True))


def inspect() -> dict | None:
    # A successful list distinguishes absence from Podman failures.
    names = command(["podman", "ps", "-a", "--format", "{{.Names}}"]).splitlines()
    name = config()["container"]
    if name not in names:
        return None
    item = json.loads(command(["podman", "inspect", name]))[0]
    if item["Config"].get("Labels", {}).get(LABEL) != str(ROOT):
        raise RuntimeError(
            "container name belongs to another checkout; refusing to modify it"
        )
    return item


def status() -> dict:
    item = inspect()
    return {"container": item["State"]["Status"] if item else "absent", "gpu": gpu()}


def start() -> dict:
    settings = config()
    item = inspect()
    if item:
        if item["State"]["Running"]:
            return {
                "container": settings["container"],
                "status": "already running; use status to check readiness",
            }
        raise RuntimeError(
            "demo container is stopped; run inference-axi stop before starting again"
        )
    hardware = gpu()
    if int(hardware["memory.free"]) < settings["minimum_free_mib"]:
        raise RuntimeError(
            f"GPU has {hardware['memory.free']} MiB free; this profile requires {settings['minimum_free_mib']} MiB. Existing workloads are untouched."
        )
    argv = [
        "podman",
        "run",
        "-d",
        "--name",
        settings["container"],
        "--label",
        f"{LABEL}={ROOT}",
        "--device",
        "nvidia.com/gpu=0",
        "--security-opt",
        "label=disable",
        "--shm-size",
        "2g",
        "-p",
        f"127.0.0.1:{settings['port']}:8000",
    ]
    for key, value in settings["environment"].items():
        argv += ["-e", f"{key}={value}"]
    argv += [settings["image"], *settings["arguments"]]
    command(argv, timeout=60)
    try:
        deadline = time.monotonic() + 300
        with httpx.Client(timeout=3) as client:
            while time.monotonic() < deadline:
                item = inspect()
                if not item or not item["State"]["Running"]:
                    raise RuntimeError("server exited; run inference-axi logs")
                try:
                    response = client.get(f"http://127.0.0.1:{settings['port']}/health")
                    if response.status_code == 200:
                        return {"container": settings["container"], "status": "ready"}
                except httpx.RequestError:
                    pass
                time.sleep(2)
        raise RuntimeError(
            "readiness deadline exceeded; run inference-axi logs then inference-axi stop"
        )
    except KeyboardInterrupt:
        stop()
        raise


def stop() -> dict:
    item = inspect()
    if not item:
        return {"status": "already absent"}
    # Use the inspected immutable ID, never a broad name filter.
    command(["podman", "rm", "-f", item["Id"]], timeout=40)
    return {"status": "stopped and removed demo container"}

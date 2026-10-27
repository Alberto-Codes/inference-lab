"""Inspect and manage only this checkout's labelled Podman container.

The profile in ``serving/config.json`` supplies the image, GPU memory floor and
server arguments. Ownership checks precede container mutations. This module
never stops unrelated GPU workloads.

Examples:
    Read the checked-in profile without contacting the GPU or Podman:

    ```python
    from inference_lab import serving

    profile = serving.config()
    print(profile["container"])
    ```

See Also:
    [inference_lab.local_gpu][]: Explicit opt-in service handover and restoration.
"""

import json
import subprocess
import time
from http import HTTPStatus
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
LABEL = "dev.inference-lab.root"


def config() -> dict:
    """Read the checkout's runtime profile.

    Returns:
        Parsed settings from ``serving/config.json``.

    Raises:
        OSError: If the profile cannot be read.
        json.JSONDecodeError: If the profile is not valid JSON.
    """
    return json.loads((ROOT / "serving/config.json").read_text())


def command(argv: list[str], timeout: float = 20) -> str:
    """Run a local tool with captured output and a deadline.

    Args:
        argv: Trusted executable and arguments, passed directly without a shell.
        timeout: Maximum execution time in seconds.

    Returns:
        Standard output with leading and trailing whitespace removed.

    Raises:
        RuntimeError: If the tool exits unsuccessfully; includes bounded stderr.
        subprocess.TimeoutExpired: If execution exceeds the deadline.
        OSError: If the executable cannot be started.
    """
    # Callers supply local tool argument vectors; no shell evaluates their contents.
    result = subprocess.run(  # noqa: S603
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        raise RuntimeError(f"{argv[0]} failed: {result.stderr.strip()[:500]}")
    return result.stdout.strip()


def gpu() -> dict:
    """Query GPU zero with nvidia-smi.

    Returns:
        String values for name, UUID, driver, memory in MiB and utilization.

    Raises:
        RuntimeError: If nvidia-smi exits unsuccessfully.
        ValueError: If the response does not contain the expected fields.
    """
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
    """Inspect the configured container after verifying checkout ownership.

    Returns:
        Podman inspection data, or None when the container is absent.

    Raises:
        RuntimeError: If Podman fails or the name belongs to another checkout.

    See Also:
        [stop][inference_lab.serving.stop]: Remove only the inspected immutable ID.
    """
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
    """Collect container state and GPU information.

    Returns:
        Container state, including ``absent``, and the GPU query result.

    Raises:
        RuntimeError: If ownership verification or a local tool fails.
    """
    item = inspect()
    return {"container": item["State"]["Status"] if item else "absent", "gpu": gpu()}


def start() -> dict:
    """Start the owned parser container and wait up to 300 seconds for readiness.

    An existing running container is reported without a new readiness check.
    A failed readiness check leaves the container available for log inspection.
    Keyboard interruption after launch removes the owned container.

    Returns:
        Container name and readiness or already-running status.

    Raises:
        RuntimeError: If ownership, free memory, startup or readiness checks fail.
        subprocess.TimeoutExpired: If a local tool exceeds its deadline.
        KeyboardInterrupt: If startup is interrupted; cleanup runs after launch.

    See Also:
        [stop][inference_lab.serving.stop]: Remove a failed container after inspecting its logs.
    """
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
            f"GPU has {hardware['memory.free']} MiB free; this profile requires "
            f"{settings['minimum_free_mib']} MiB. Existing workloads are untouched."
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
                    if response.status_code == HTTPStatus.OK:
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
    """Remove the owned parser container by its inspected immutable ID.

    Returns:
        Removal status, or ``already absent`` when no container exists.

    Raises:
        RuntimeError: If ownership verification or removal fails.
    """
    item = inspect()
    if not item:
        return {"status": "already absent"}
    # Use the inspected immutable ID, never a broad name filter.
    command(["podman", "rm", "-f", item["Id"]], timeout=40)
    return {"status": "stopped and removed demo container"}

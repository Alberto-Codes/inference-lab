"""Provide opt-in GPU service handover with durable restoration evidence.

The context manager preserves the prior service state and loaded model IDs.
Callers must explicitly enable handover before this module changes services.
Disabled handover leaves the caller's server lifecycle unchanged.

Examples:
    Disable handover when using an already managed parser server:

    ```python
    from pathlib import Path
    from inference_lab.local_gpu import parser_session

    with parser_session(Path("runs/example"), enabled=False):
        pass
    ```

See Also:
    [inference_lab.serving][]: Container ownership and free-memory safeguards.
"""

import json
import subprocess
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import httpx

from inference_lab import serving

SERVICE = "llama-cpp-tuned.service"
ROUTER = "http://127.0.0.1:8090"


def service(action: str) -> None:
    """Apply an action to the configured user service.

    Args:
        action: systemctl action, such as ``start`` or ``stop``.

    Raises:
        RuntimeError: If systemctl exits unsuccessfully.
        subprocess.TimeoutExpired: If the command exceeds 60 seconds.
    """
    serving.command(["systemctl", "--user", action, SERVICE], timeout=60)


def loaded_models(client: httpx.Client) -> list[str]:
    """Read loaded model IDs from a router in a stable state.

    Args:
        client: HTTP client configured with the router's base URL.

    Returns:
        IDs whose router state is ``loaded``.

    Raises:
        RuntimeError: If any model is neither loaded nor unloaded.
        httpx.HTTPError: If the router request fails.
        KeyError: If the response lacks required model fields.
    """
    response = client.get("/models")
    response.raise_for_status()
    models = response.json()["data"]
    if any(x["status"]["value"] not in ("loaded", "unloaded") for x in models):
        raise RuntimeError("Router model state is changing; retry after it settles")
    return [x["id"] for x in models if x["status"]["value"] == "loaded"]


def restore_models(
    client: httpx.Client, models: list[str], timeout: float = 180
) -> None:
    """Wait for router health, load previous models and verify their identities.

    Args:
        client: HTTP client configured with the router's base URL.
        models: Previously loaded model IDs to restore.
        timeout: Shared deadline in seconds for health, loading and verification.

    Raises:
        RuntimeError: If readiness or model restoration exceeds the deadline.
        httpx.HTTPError: If loading or model verification requests fail.
        KeyError: If the router response lacks required model fields.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            response = client.get("/health", timeout=2)
            response.raise_for_status()
            break
        except httpx.HTTPError:
            if time.monotonic() >= deadline:
                raise RuntimeError("Router readiness deadline exceeded") from None
            time.sleep(1)
    for model in models:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("Model restore deadline exceeded")
        response = client.post("/models/load", json={"model": model}, timeout=remaining)
        response.raise_for_status()
    while time.monotonic() < deadline:
        response = client.get(
            "/models", timeout=min(5, max(0.1, deadline - time.monotonic()))
        )
        response.raise_for_status()
        actual = {
            x["id"] for x in response.json()["data"] if x["status"]["value"] == "loaded"
        }
        if actual == set(models):
            return
        time.sleep(1)
    raise RuntimeError("Previous model IDs did not reach loaded state before deadline")


@contextmanager
def parser_session(output: Path, enabled: bool) -> Generator[None]:
    """Temporarily run the parser and restore the previous user service state.

    Disabled sessions yield without inspecting or modifying services. Enabled
    sessions record initial state before stopping anything. Cleanup attempts
    parser removal and service restoration even if the experiment fails.
    Restoration failures are recorded and raised, including during unwinding.

    Args:
        output: Existing run directory for a new ``lifecycle.json`` audit file.
        enabled: Explicit authorization to perform the local service handover.

    Yields:
        None while the caller runs its experiment.

    Raises:
        RuntimeError: If ownership, service state, startup or restoration fails.
        OSError: If the audit file or local commands cannot be accessed.
        httpx.HTTPError: If the initial model-state request fails.
        subprocess.TimeoutExpired: If a local lifecycle command times out.

    See Also:
        [restore_models][inference_lab.local_gpu.restore_models]: Verify model identities.
        [inference_lab.serving.start][]: Start only the owned parser container.
    """
    if not enabled:
        yield
        return
    if serving.inspect() is not None:
        raise RuntimeError(
            "An owned parser container already exists; stop it before handover"
        )
    # Fixed arguments query the user service; PATH selects the installed systemctl.
    state = subprocess.run(  # noqa: S603
        ["systemctl", "--user", "is-active", "--quiet", SERVICE],  # noqa: S607
        check=False,
    )
    if state.returncode not in (0, 3):
        raise RuntimeError("Cannot determine the existing llama.cpp service state")
    active = state.returncode == 0
    audit = {
        "service_was_active": active,
        "previous_models": [],
        "experiment_error": None,
        "restoration_errors": [],
        "restoration_verified": False,
    }
    with httpx.Client(base_url=ROUTER, timeout=10) as client:
        if active:
            audit["previous_models"] = loaded_models(client)
        path = output / "lifecycle.json"
        with path.open("x") as file:
            json.dump(audit, file, indent=2)
        try:
            if active:
                service("stop")
            serving.start()
            yield
        except BaseException as exc:
            audit["experiment_error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            try:
                serving.stop()
            except Exception as exc:
                audit["restoration_errors"].append(f"Parser cleanup: {exc}")
            try:
                if active:
                    service("start")
                    restore_models(client, audit["previous_models"])
                else:
                    service("stop")
                audit["restoration_verified"] = not audit["restoration_errors"]
            except Exception as exc:
                audit["restoration_errors"].append(f"Llama restoration: {exc}")
            path.write_text(json.dumps(audit, indent=2))
            if audit["restoration_errors"]:
                raise RuntimeError(f"Restoration failed; see {path}")

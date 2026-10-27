"""Explicit local service handover with durable restoration evidence."""

import json
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from inference_lab import serving

SERVICE = "llama-cpp-tuned.service"
ROUTER = "http://127.0.0.1:8090"


def service(action: str) -> None:
    serving.command(["systemctl", "--user", action, SERVICE], timeout=60)


def loaded_models(client) -> list[str]:
    response = client.get("/models")
    response.raise_for_status()
    models = response.json()["data"]
    if any(x["status"]["value"] not in ("loaded", "unloaded") for x in models):
        raise RuntimeError("Router model state is changing; retry after it settles")
    return [x["id"] for x in models if x["status"]["value"] == "loaded"]


def restore_models(client, models: list[str], timeout: float = 180) -> None:
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
def parser_session(output: Path, enabled: bool):
    """Manage only an explicitly requested handover; preserve inactive service state."""
    if not enabled:
        yield
        return
    if serving.inspect() is not None:
        raise RuntimeError(
            "An owned parser container already exists; stop it before handover"
        )
    state = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", SERVICE], check=False
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

"""Freeze and run the shared-capacity matrix with explicit GPU handover."""

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scaling_experiment import load_inputs, save
from scaling_suite import archive_server, snapshot
from shared_capacity import DEFAULTS, execute, initialize, make_trace

from inference_lab import serving
from inference_lab.local_gpu import parser_session


def source_hashes():
    """Bind all executable experiment sources and configuration to the plan."""
    root = serving.ROOT
    paths = [root / "pyproject.toml", root / "uv.lock"]
    for directory in ("src", "scripts", "serving"):
        paths.extend(
            path
            for path in (root / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def condition_order(repeats):
    """Establish isolated baselines, then alternate paired mixed-policy order."""
    order = []
    for stage in (("urgent", "bulk"), ("fifo", "reserved")):
        for repeat in range(repeats):
            arms = stage if repeat % 2 == 0 else tuple(reversed(stage))
            order.extend(
                {"name": f"{condition}-{repeat}", "condition": condition}
                for condition in arms
            )
    return order


def prepare_suite(corpus, output):
    """Freeze every condition before starting or interrupting GPU services."""
    manifest, _pages = load_inputs(corpus)
    if [page["id"] for page in manifest["pages"]] != list(range(24, 80)):
        raise ValueError("Primary matrix requires CORD rows 24 through 79 in order")
    if len({page["sha256"] for page in manifest["pages"]}) != len(manifest["pages"]):
        raise ValueError("Primary matrix requires unique source images")
    settings = dict(DEFAULTS)
    output.mkdir(parents=True, exist_ok=False)
    protocol = {
        "schema": 1,
        "input": str(corpus.resolve()),
        "manifest": manifest,
        "settings": settings,
        "order": condition_order(3),
        "source_sha256": source_hashes(),
        "cache_policy": "restart owned parser and warm all 56 inputs before each arm",
        "deadline_policy": "fixed before all isolated and mixed runs; no retuning",
    }
    save(output / "protocol.json", protocol)
    source = output / "frozen-source"
    for name in protocol["source_sha256"]:
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(serving.ROOT / name, destination)
    for arm in protocol["order"]:
        initialize(output / arm["name"], manifest, settings, arm["condition"])
    return protocol


def verify_suite(output):
    """Reject changed code, corpus or an already attempted matrix before handover."""
    protocol = json.loads((output / "protocol.json").read_text())
    if protocol["source_sha256"] != source_hashes():
        raise ValueError("Executable sources changed; prepare a new matrix directory")
    manifest, pages = load_inputs(Path(protocol["input"]))
    if manifest != protocol["manifest"]:
        raise ValueError("Corpus changed after the matrix was frozen")
    if protocol["settings"] != DEFAULTS or protocol["order"] != condition_order(3):
        raise ValueError("Primary matrix settings or condition order changed")
    trace = make_trace(manifest, protocol["settings"])
    for arm in protocol["order"]:
        path = output / arm["name"]
        plan = json.loads((path / "plan.json").read_text())
        raw = (path / "trace.json").read_bytes()
        if (
            plan["settings"] != protocol["settings"]
            or plan["manifest"] != manifest
            or plan["condition"] != arm["condition"]
            or plan["profile"] != serving.config()
            or plan["trace_sha256"] != hashlib.sha256(raw).hexdigest()
            or json.loads(raw)["requests"] != trace
        ):
            raise ValueError("Condition differs from frozen primary matrix")
    if (output / "run-started.json").exists():
        raise ValueError(
            "Matrix already attempted; retain evidence and prepare a new one"
        )
    return protocol, manifest, pages


def run_suite(output, release_llama):
    """Run real GPU checks and conditions, then restore an approved service handover."""
    protocol, manifest, pages = verify_suite(output)
    if not release_llama:
        raise ValueError("This suite requires explicit --release-llama authorization")
    save(output / "run-started.json", {"release_llama": release_llama})
    summaries = []
    with parser_session(output, enabled=release_llama):
        runtime = output / "run-context"
        runtime.mkdir()
        snapshot(runtime)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "gpu", "-q"],
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        save(
            output / "gpu-test.json",
            {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        if result.returncode:
            raise RuntimeError("Real GPU smoke test failed")
        try:
            for arm in protocol["order"]:
                # Every arm starts from the same cache/reset policy, including
                # the first arm after the synthetic GPU check.
                archive_server(output / f"server-before-{arm['name']}.json")
                serving.stop()
                serving.start()
                save(
                    output / f"runtime-{arm['name']}.json",
                    {"container": serving.inspect()},
                )
                summary = asyncio.run(
                    execute(
                        output / arm["name"],
                        manifest,
                        pages,
                        protocol["settings"],
                        arm["condition"],
                    )
                )
                summaries.append({"name": arm["name"], "result": summary})
                print(json.dumps(summaries[-1]), flush=True)
        finally:
            archive_server(output / "server-final.json")
    save(output / "summaries.json", {"conditions": summaries})
    return summaries


def main():
    """Prepare offline or execute a previously frozen, explicitly approved matrix."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--input", type=Path, required=True)
    preparation.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--release-llama", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        protocol = prepare_suite(args.input, args.output)
        print(json.dumps({"status": "prepared", "conditions": protocol["order"]}))
    else:
        run_suite(args.output, args.release_llama)


if __name__ == "__main__":
    main()

"""Run repeated local conditions inside an explicitly authorized GPU handover."""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scaling_experiment import execute, initialize, load_inputs, save, validate
from score_scaling import review, summarize

from inference_lab import serving
from inference_lab.client import prepare
from inference_lab.local_gpu import parser_session


def snapshot(output):
    """Preserve executable source, lockfile and actual runtime identity."""
    source = output / "source"
    source.mkdir()
    for name in ("src", "scripts", "serving"):
        shutil.copytree(
            serving.ROOT / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(serving.ROOT / name, source / name)
    item = serving.inspect()
    if item is None:
        raise RuntimeError("Owned parser is required")
    save(
        output / "runtime.json",
        {
            "gpu": serving.gpu(),
            "container": item,
            "profile": serving.config(),
            "packages": serving.command(
                ["podman", "exec", item["Id"], "cat", "/serving-packages.txt"]
            ),
            "git_commit": serving.command(["git", "rev-parse", "HEAD"]),
            "git_status": serving.command(["git", "status", "--porcelain"]),
        },
    )


def condition(corpus, output, settings):
    """Prepare before timing, run one condition and rescore offline."""
    manifest, pages = load_inputs(corpus)
    validate(settings, len(pages))
    initialize(output, manifest, settings, False)
    result = asyncio.run(execute(output, manifest, pages, settings))
    scored = summarize(output)
    scored["failure_review"] = review(scored)
    save(output / "scores.json", scored)
    print(json.dumps({"run": output.name, **result, **scored["summary"]}), flush=True)
    return scored["summary"]


def archive_server(path):
    """Retain both log streams before removing an owned container."""
    item = serving.inspect()
    if item:
        result = subprocess.run(  # noqa: S603 - inspected owned container ID
            ["podman", "logs", item["Id"]],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        save(
            path,
            {
                "container_id": item["Id"],
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )


def main():
    """Run a reproducible matrix and restore the previously loaded llama models."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup-image", type=Path, required=True)
    parser.add_argument("--release-llama", action="store_true")
    parser.add_argument("--rates", type=float, nargs="+", default=[2, 4, 6, 8, 12])
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--stability-rate", type=float, default=0)
    parser.add_argument("--stability-seconds", type=int, default=300)
    args = parser.parse_args()
    if min(args.seconds, args.repeats, args.stability_seconds) < 1:
        parser.error("durations and repeats must be positive")
    _manifest, pages = load_inputs(args.input)

    warm = prepare(args.warmup_image)
    if warm.sha256 in {p.sha256 for p in pages}:
        parser.error("Fresh warmup image must not be a measured input")
    base = {
        "url": "http://127.0.0.1:8017",
        "concurrency": 16,
        "queue": 64,
        "timeout": 30,
        "warmup_image": str(args.warmup_image.resolve()),
        "warmup_sha256": warm.sha256,
    }
    for rate in args.rates:
        validate(
            {
                **base,
                "rate": rate,
                "count": int(rate * args.seconds),
                "cache": "repeated",
            },
            len(pages),
        )
    args.output.mkdir(parents=True, exist_ok=False)
    save(
        args.output / "protocol.json",
        {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
    )
    summaries = []
    with parser_session(args.output, args.release_llama):
        snapshot(args.output)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-m", "gpu", "-q"],
            capture_output=True,
            text=True,
            check=False,
        )
        save(
            args.output / "gpu-test.json",
            {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        if result.returncode:
            raise RuntimeError("GPU tests failed")
        try:
            if args.stability_rate:
                summaries.append(
                    condition(
                        args.input,
                        args.output / "stability",
                        {
                            **base,
                            "cache": "repeated",
                            "rate": args.stability_rate,
                            "count": int(args.stability_rate * args.stability_seconds),
                        },
                    )
                )
            else:
                for repeat in range(args.repeats):
                    # Restart only our labelled parser to remove previous input caches.
                    archive_server(args.output / f"server-before-fresh-{repeat}.json")
                    serving.stop()
                    serving.start()
                    save(
                        args.output / f"runtime-fresh-{repeat}.json",
                        {"container": serving.inspect()},
                    )
                    summaries.append(
                        condition(
                            args.input,
                            args.output / f"fresh-{repeat}",
                            {
                                **base,
                                "cache": "fresh",
                                "rate": 4,
                                "count": len(pages),
                            },
                        )
                    )
                    # Rotate rate order between repeats to expose order/thermal effects.
                    rates = args.rates[repeat:] + args.rates[:repeat]
                    for rate in rates:
                        summaries.append(  # noqa: PERF401 - each GPU condition is a side effect
                            condition(
                                args.input,
                                args.output / f"r{rate:g}-{repeat}",
                                {
                                    **base,
                                    "cache": "repeated",
                                    "rate": rate,
                                    "count": int(rate * args.seconds),
                                },
                            )
                        )
        finally:
            archive_server(args.output / "server-final.json")
    save(args.output / "summaries.json", {"conditions": summaries})


if __name__ == "__main__":
    main()

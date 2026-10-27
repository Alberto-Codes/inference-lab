"""AXI-style CLI: compact TOON views, JSON evidence, no interactive prompts."""

import argparse
import asyncio
import json
import math
import platform
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from inference_lab import serving
from inference_lab.client import infer, prepare
from inference_lab.corpus import generate
from inference_lab.experiment import load_corpus, render, sweep


def scalar(value) -> str:
    if not isinstance(value, str):
        return json.dumps(value, allow_nan=False)
    if (
        not value
        or value != value.strip(" \t")
        or value in ("true", "false", "null")
        or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?", value, re.I)
        or re.search(r'[:,"\\\[\]{}\x00-\x1f]', value)
        or value.startswith(("-", "#"))
    ):
        escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
        return (
            '"'
            + "".join(
                escapes.get(c, f"\\u{ord(c):04x}" if ord(c) < 32 else c) for c in value
            )
            + '"'
        )
    return value


def emit(data: dict) -> None:
    # Deliberately limited to this CLI's flat scalar views, not a generic codec.
    for key, value in data.items():
        print(f"{key}: {scalar(value)}")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        flags = ", ".join(s for a in self._actions for s in a.option_strings)
        emit({"error": message, "valid_flags": flags, "help": f"{self.prog} --help"})
        raise SystemExit(2)


def positive(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return result


def parser() -> Parser:
    root = Parser(
        prog="inference-axi",
        description="Local Nemotron OCR smoke demo; no arguments shows live state.",
        allow_abbrev=False,
    )
    sub = root.add_subparsers(dest="action")
    for name in ("status", "start", "stop", "build"):
        sub.add_parser(name, allow_abbrev=False)
    logs = sub.add_parser("logs", allow_abbrev=False)
    logs.add_argument("--full", action="store_true")
    corpus = sub.add_parser("corpus", allow_abbrev=False)
    corpus.add_argument("--output", type=Path, default=Path("corpus"))
    for name in ("ocr", "bench"):
        p = sub.add_parser(name, allow_abbrev=False)
        p.add_argument("input", type=Path)
        p.add_argument("--output", required=True, type=Path)
        p.add_argument("--timeout", type=positive, default=120.0)
        p.add_argument("--url", default="http://127.0.0.1:8017")
        if name == "ocr":
            p.add_argument("--expect", action="append", default=[])
            p.add_argument("--full", action="store_true")
        else:
            p.add_argument(
                "--concurrency",
                nargs="+",
                type=int,
                choices=(1, 2, 4, 8),
                default=[1, 2, 4, 8],
            )
    return root


async def run_ocr(args) -> int:
    page = prepare(args.input, tuple(args.expect))
    async with httpx.AsyncClient(base_url=args.url, timeout=args.timeout) as client:
        record = await infer(client, page, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(record["text"])
    args.output.with_suffix(args.output.suffix + ".json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    text = record["text"]
    emit(
        {
            "status": record["status"],
            "output": str(args.output),
            "characters": len(text),
            "preview": text if args.full else text[:500],
            "quality": "expected-text sanity check"
            if args.expect
            else "nonempty output only; supply --expect for known text",
        }
    )
    if len(text) > 500 and not args.full:
        emit(
            {
                "help": f"Read {args.output} for complete output; --full prints all text on a new request"
            }
        )
    if "error" in record:
        emit({"error": record["error"]})
    return 0 if record["status"] == "success" else 1


async def run_bench(args) -> int:
    preparation_start = time.perf_counter()
    pages = load_corpus(args.input)
    preparation_s = time.perf_counter() - preparation_start
    # Require our running container so intended config cannot masquerade as observed config.
    item = serving.inspect()
    if not item or not item["State"]["Running"]:
        raise RuntimeError(
            "benchmark requires this checkout's running server; run inference-axi start"
        )
    if args.url.rstrip("/") != "http://127.0.0.1:8017":
        raise ValueError(
            "benchmark uses the managed local server at http://127.0.0.1:8017"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "started_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "gpu_before": serving.gpu(),
        "serving": serving.config(),
        "container_id": item["Id"],
        "image_id": item["Image"],
        "container_args": item["Args"],
        "packages": serving.command(
            ["podman", "exec", item["Id"], "cat", "/serving-packages.txt"]
        ),
        "git_commit": serving.command(
            ["git", "-C", str(serving.ROOT), "rev-parse", "HEAD"]
        ),
        "git_dirty": bool(
            serving.command(["git", "-C", str(serving.ROOT), "status", "--porcelain"])
        ),
        "client_url": args.url,
        "timeout_s": args.timeout,
        "preparation_s": preparation_s,
        "quality": "all expected phrases after case/punctuation normalization",
        "corpus": [
            {"file": p.name, "sha256": p.sha256, "expected": p.expected} for p in pages
        ],
    }
    report = {"status": "running", "metadata": metadata, "warmup": None, "sweeps": []}

    def save():
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        (args.output / "summary.md").write_text(render(report))

    try:
        async with httpx.AsyncClient(
            base_url=args.url,
            timeout=args.timeout,
            limits=httpx.Limits(max_connections=8),
        ) as client:
            report["warmup"] = await infer(client, pages[0], args.timeout)
            save()
            if report["warmup"]["status"] != "success":
                raise RuntimeError(f"warmup failed; inspect {args.output}/results.json")
            for concurrency in args.concurrency:
                report["sweeps"].append(
                    await sweep(client, pages, concurrency, args.timeout)
                )
                save()
        report["status"] = "complete"
    except BaseException:
        report["status"] = "aborted"
        raise
    finally:
        metadata["finished_at"] = datetime.now(UTC).isoformat()
        save()
    emit(
        {
            "sweeps": len(report["sweeps"]),
            "failures": sum(s["failures"] for s in report["sweeps"]),
            "summary": str(args.output / "summary.md"),
            "results": str(args.output / "results.json"),
        }
    )
    return 1 if any(s["failures"] for s in report["sweeps"]) else 0


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action in (None, "status"):
            state = serving.status()
            ready = False
            if state["container"] == "running":
                try:
                    ready = (
                        httpx.get("http://127.0.0.1:8017/health", timeout=3).status_code
                        == 200
                    )
                except httpx.RequestError:
                    pass
            emit(
                {
                    "container": state["container"],
                    "ready": ready,
                    "gpu": state["gpu"]["name"],
                    "free_mib": int(state["gpu"]["memory.free"]),
                    "help": "inference-axi corpus; inference-axi start; inference-axi --help",
                }
            )
        elif args.action == "corpus":
            emit(
                {
                    "pages": generate(args.output),
                    "directory": str(args.output),
                    "help": "inference-axi bench <corpus-directory> --output <new-run-directory>",
                }
            )
        elif args.action in ("start", "stop"):
            emit(getattr(serving, args.action)())
        elif args.action == "build":
            result = subprocess.run(
                [
                    "podman",
                    "build",
                    "-t",
                    serving.config()["image"],
                    "-f",
                    str(serving.ROOT / "serving/Containerfile"),
                    str(serving.ROOT / "serving"),
                ],
                stdout=sys.stderr,
            )
            if result.returncode:
                raise RuntimeError(
                    "image build failed; inspect build diagnostics and docs/reference/evidence.md"
                )
            emit({"image": serving.config()["image"], "help": "inference-axi start"})
        elif args.action == "logs":
            item = serving.inspect()
            if not item:
                emit({"logs": "0 containers; demo has not started"})
            else:
                argv = (
                    ["podman", "logs"]
                    + ([] if args.full else ["--tail", "40"])
                    + [item["Id"]]
                )
                result = subprocess.run(
                    argv, capture_output=True, text=True, timeout=20
                )
                if result.returncode:
                    raise RuntimeError("cannot read demo logs")
                emit(
                    {
                        "logs": result.stdout + result.stderr,
                        "help": "inference-axi logs --full; inference-axi stop",
                    }
                )
        elif args.action == "ocr":
            return asyncio.run(run_ocr(args))
        elif args.action == "bench":
            return asyncio.run(run_bench(args))
    except KeyboardInterrupt:
        emit(
            {
                "error": "interrupted; completed sweep files are retained",
                "help": "inference-axi stop",
            }
        )
        return 130
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        emit(
            {
                "error": str(exc),
                "help": "inference-axi --help; see docs/reference/evidence.md",
            }
        )
        return 1
    return 0

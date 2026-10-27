# /// script
# requires-python = ">=3.12"
# dependencies = ["typevet[judgevet]==0.11.0", "judgevet==0.23.0"]
# ///
"""Replay the saved receipt rubric through Judgevet, Typevet and local Gemma."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from judgevet import Score
from typevet.adapters.inbound.backend_settings import open_judgment
from typevet.adapters.inbound.judgevet import TypevetSystemOnePort


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, type=Path, help="Scores JSON from the selected run"
    )
    parser.add_argument(
        "--rubric",
        required=True,
        type=Path,
        help="Historical judgment file supplying instruction and criteria only",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New judgment JSON file; must not exist",
    )
    args = parser.parse_args()
    scores = json.loads(args.input.read_text())
    records = [
        r
        for r in scores["requests"]
        if r["phase"] == "measured" and r["concurrency"] == 1
    ]
    if len(records) != 24 or sorted(r["id"] for r in records) != list(range(24)):
        raise ValueError("Review requires all 24 measured concurrency-one cases")
    records = sorted(records, key=lambda r: (r["scores"]["rouge_l_f1"], r["id"]))[:3]
    saved = json.loads(args.rubric.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        destination.write("{}\n")
    os.environ.setdefault("TYPEVET_BACKEND", "llama_cpp")
    os.environ.setdefault("TYPEVET_LLAMA__BASE_URL", "http://127.0.0.1:8090")
    os.environ.setdefault("TYPEVET_LLAMA__MULTIMODAL_MODEL", "gemma-4-31b-kv9-text")
    os.environ.setdefault("TYPEVET_LLAMA__TIMEOUT", "180")
    report = {k: saved[k] for k in ("instruction", "criteria")}
    report["source_scores"] = str(args.input)
    report["backend"] = "Judgevet → Typevet → local llama.cpp"
    report["selection"] = (
        "three lowest diagnostic ROUGE-L F1 at concurrency 1; ties by ID"
    )
    report["reviews"] = []
    questions = {
        "numeric_fidelity": Score(
            instructions=saved["instruction"], criteria=saved["criteria"]
        )
    }
    with open_judgment() as session:
        port = TypevetSystemOnePort(session.port)
        for item in records:
            state = {
                "id": item["id"],
                "partial_reference": item["reference"],
                "ocr_output": item["plain_prediction"],
            }
            response = port.system_one(state, questions, model=session.model)
            report["reviews"].append(
                {"id": item["id"], "state": state, "response": asdict(response)}
            )
            args.output.write_text(json.dumps(report, indent=2))
            print(f"id: {item['id']}\nstatus: complete", flush=True)


if __name__ == "__main__":
    main()

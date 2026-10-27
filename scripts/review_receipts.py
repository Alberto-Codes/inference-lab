# /// script
# requires-python = ">=3.12"
# dependencies = ["typevet[judgevet]==0.11.0", "judgevet==0.23.0"]
# ///
"""Review receipt scores through Judgevet, Typevet and a configured llama.cpp model."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit


def configure_judge():
    backend = os.environ.get("TYPEVET_BACKEND", "llama_cpp").strip()
    if backend != "llama_cpp":
        raise ValueError("Receipt review requires TYPEVET_BACKEND=llama_cpp")
    for name in ("TYPEVET_LLAMA__BASE_URL", "TYPEVET_LLAMA__MULTIMODAL_MODEL"):
        if not os.environ.get(name, "").strip():
            raise ValueError(f"Set {name} explicitly before receipt review")
    endpoint = urlsplit(os.environ["TYPEVET_LLAMA__BASE_URL"])
    if endpoint.scheme not in ("http", "https") or not endpoint.hostname:
        raise ValueError("TYPEVET_LLAMA__BASE_URL must be an HTTP or HTTPS URL")
    os.environ.setdefault("TYPEVET_BACKEND", "llama_cpp")
    os.environ.setdefault("TYPEVET_LLAMA__AUTOLOAD", "false")
    os.environ.setdefault("TYPEVET_LLAMA__TIMEOUT", "180")


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
    try:
        configure_judge()
    except ValueError as error:
        parser.error(str(error))
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

    from judgevet import Score
    from typevet.adapters.inbound.backend_settings import open_judgment
    from typevet.adapters.inbound.judgevet import TypevetSystemOnePort
    from typevet.adapters.inbound.settings import load_llama_settings

    load_llama_settings()  # Validate Typevet options before reserving the output file.
    report = {k: saved[k] for k in ("instruction", "criteria")}
    report["source_scores"] = str(args.input)
    report["backend"] = "Judgevet → Typevet → llama.cpp"
    report["model"] = os.environ["TYPEVET_LLAMA__MULTIMODAL_MODEL"].strip()
    report["selection"] = (
        "three lowest diagnostic ROUGE-L F1 at concurrency 1; ties by ID"
    )
    report["status"] = "incomplete"
    report["reviews"] = []
    questions = {
        "numeric_fidelity": Score(
            instructions=saved["instruction"], criteria=saved["criteria"]
        )
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        destination.write(json.dumps(report, indent=2))
    with open_judgment() as session:
        report["model"] = session.model
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
    report["status"] = "complete"
    args.output.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

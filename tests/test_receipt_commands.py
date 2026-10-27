import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(name, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
        capture_output=True,
        text=True,
    )


def test_scorer_uses_selected_run_and_refuses_overwrite(tmp_path):
    source = tmp_path / "new-run"
    source.mkdir()
    rows = [
        json.loads(line)
        for line in (ROOT / "evidence/cord-test-24/requests.jsonl")
        .read_text()
        .splitlines()
    ]
    for row in rows:
        row["reference"] = "amount -12.00"
        row["text"] = "amount -12.00"
    (source / "requests.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    output = tmp_path / "score.json"
    result = command("score_receipts.py", "--input", source, "--output", output)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["summaries"][1]["micro_numeric_recall"] == 1
    original = output.read_bytes()
    result = command("score_receipts.py", "--input", source, "--output", output)
    assert result.returncode != 0
    assert output.read_bytes() == original
    raw = (source / "requests.jsonl").read_bytes()
    assert (
        command(
            "score_receipts.py",
            "--input",
            source,
            "--output",
            source / "requests.jsonl",
        ).returncode
        != 0
    )
    assert (source / "requests.jsonl").read_bytes() == raw


def test_scorer_rejects_missing_duplicate_and_counts_failures(tmp_path):
    module = script("score_receipts")
    rows = [
        json.loads(line)
        for line in (ROOT / "evidence/cord-test-24/requests.jsonl")
        .read_text()
        .splitlines()
    ]
    raw = tmp_path / "requests.jsonl"
    raw.write_text("".join(json.dumps(r) + "\n" for r in rows[:-1]))
    with pytest.raises(RuntimeError, match="Missing or duplicate"):
        module.rescore(tmp_path)
    original_id = rows[-1]["id"]
    rows[-1]["id"] = rows[-2]["id"]
    raw.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(RuntimeError, match="Missing or duplicate"):
        module.rescore(tmp_path)
    rows[-1]["id"] = original_id
    for row in rows:
        row["status"] = "incomplete"
    raw.write_text("".join(json.dumps(r) + "\n" for r in rows))
    result = module.rescore(tmp_path)
    assert all(s["micro_numeric_recall"] == 0 for s in result["summaries"])
    assert all(r["text"] for r in result["requests"])


def test_scorer_creates_no_output_when_run_is_incomplete(tmp_path):
    lines = (ROOT / "evidence/cord-test-24/requests.jsonl").read_text().splitlines()
    (tmp_path / "requests.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    output = tmp_path / "scores.json"
    result = command("score_receipts.py", "--input", tmp_path, "--output", output)
    assert result.returncode != 0
    assert "Missing or duplicate" in result.stderr
    assert not output.exists()


def test_experiment_refuses_existing_run_without_touching_bytes(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    sentinel = output / "results.json"
    sentinel.write_text("existing evidence")
    result = command(
        "receipt_experiment.py", "--input", tmp_path / "missing", "--output", output
    )
    assert result.returncode != 0
    assert sentinel.read_text() == "existing evidence"


def test_image_validation_precedes_requests(tmp_path, monkeypatch):
    import asyncio

    module = script("receipt_experiment")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    pages = [
        {"id": i, "file": "../outside.jpg", "sha256": "bad", "ground_truth": {}}
        for i in range(24)
    ]
    (corpus / "manifest.json").write_text(json.dumps({"pages": pages}))
    with pytest.raises(ValueError, match="inside"):
        asyncio.run(module.run(corpus, tmp_path / "run"))


def test_historical_rescore_is_stable():
    result = script("score_receipts").rescore(ROOT / "evidence/cord-test-24")
    assert result["summaries"][1]["numeric_matched"] == 212
    assert result["summaries"][1]["numeric_total"] == 241
    assert result["summaries"][1]["macro_rouge_l_f1"] == pytest.approx(
        0.8007150388521506
    )
    assert (
        result["source_requests_sha256"]
        == hashlib.sha256(
            (ROOT / "evidence/cord-test-24/requests.jsonl").read_bytes()
        ).hexdigest()
    )

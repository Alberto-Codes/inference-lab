import importlib.util
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def review(monkeypatch):
    for key in list(os.environ):
        if key.startswith("TYPEVET_"):
            monkeypatch.delenv(key)
    spec = importlib.util.spec_from_file_location(
        "review_receipts", ROOT / "scripts/review_receipts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(monkeypatch, tmp_path):
    scores = tmp_path / "scores.json"
    scores.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "id": i,
                        "phase": "measured",
                        "concurrency": 1,
                        "scores": {"rouge_l_f1": i / 24},
                        "reference": "12.00",
                        "plain_prediction": "12.00",
                    }
                    for i in range(24)
                ]
            }
        )
    )
    rubric = tmp_path / "rubric.json"
    rubric.write_text(json.dumps({"instruction": "Check amounts", "criteria": {}}))
    output = tmp_path / "new" / "review.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review",
            "--input",
            str(scores),
            "--rubric",
            str(rubric),
            "--output",
            str(output),
        ],
    )
    return output


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"TYPEVET_LLAMA__BASE_URL": "http://localhost:9000"},
        {"TYPEVET_LLAMA__MULTIMODAL_MODEL": "my-model"},
        {"TYPEVET_BACKEND": "fake"},
        {"TYPEVET_BACKEND": "vllm"},
        {
            "TYPEVET_LLAMA__BASE_URL": "not-a-url",
            "TYPEVET_LLAMA__MULTIMODAL_MODEL": "my-model",
        },
    ],
)
def test_invalid_configuration_creates_no_output(
    review, monkeypatch, tmp_path, settings
):
    output = arguments(monkeypatch, tmp_path)
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit, match="2"):
        review.main()
    assert not output.parent.exists()


def test_review_attribution_and_overwrite_guard(review, monkeypatch, tmp_path):
    output = arguments(monkeypatch, tmp_path)
    monkeypatch.setenv("TYPEVET_LLAMA__BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("TYPEVET_LLAMA__MULTIMODAL_MODEL", "reader-model")
    calls = []

    @dataclass
    class Response:
        score: int = 1

    @contextmanager
    def open_judgment():
        calls.append("open")
        yield SimpleNamespace(port=None, model="reader-model")

    class Port:
        def __init__(self, port):
            pass

        def system_one(self, state, questions, model):
            calls.append((state["id"], model))
            return Response()

    def load_settings():
        assert review.os.environ["TYPEVET_LLAMA__AUTOLOAD"] == "false"

    for name, attrs in {
        "judgevet": {"Score": lambda **kwargs: kwargs},
        "typevet.adapters.inbound.backend_settings": {"open_judgment": open_judgment},
        "typevet.adapters.inbound.judgevet": {"TypevetSystemOnePort": Port},
        "typevet.adapters.inbound.settings": {"load_llama_settings": load_settings},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    review.main()
    report = json.loads(output.read_text())
    assert report["backend"] == "Judgevet → Typevet → llama.cpp"
    assert report["model"] == "reader-model"
    assert report["status"] == "complete"
    assert [r["id"] for r in report["reviews"]] == [0, 1, 2]
    assert calls == [
        "open",
        (0, "reader-model"),
        (1, "reader-model"),
        (2, "reader-model"),
    ]
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        review.main()
    assert output.read_bytes() == original
    assert calls.count("open") == 1


def test_failed_review_leaves_incomplete_output(review, monkeypatch, tmp_path):
    output = arguments(monkeypatch, tmp_path)
    monkeypatch.setenv("TYPEVET_LLAMA__BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("TYPEVET_LLAMA__MULTIMODAL_MODEL", "reader-model")

    @dataclass
    class Response:
        score: int = 1

    @contextmanager
    def open_judgment():
        yield SimpleNamespace(port=None, model="reader-model")

    class Port:
        def __init__(self, port):
            pass

        def system_one(self, state, questions, model):
            if state["id"] == 1:
                raise ConnectionError("endpoint stopped")
            return Response()

    for name, attrs in {
        "judgevet": {"Score": lambda **kwargs: kwargs},
        "typevet.adapters.inbound.backend_settings": {"open_judgment": open_judgment},
        "typevet.adapters.inbound.judgevet": {"TypevetSystemOnePort": Port},
        "typevet.adapters.inbound.settings": {"load_llama_settings": lambda: None},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    with pytest.raises(ConnectionError):
        review.main()
    report = json.loads(output.read_text())
    assert report["status"] == "incomplete"
    assert [r["id"] for r in report["reviews"]] == [0]

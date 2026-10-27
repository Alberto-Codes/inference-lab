import json
import subprocess

from inference_lab.client import prepare
from inference_lab.corpus import generate
from inference_lab.experiment import load_corpus


def test_unknown_flag_is_structured_and_fails_before_hardware_access():
    result = subprocess.run(
        ["inference-axi", "start", "--typo"], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "error:" in result.stdout
    assert "valid_flags:" in result.stdout
    assert result.stderr == ""


def test_corpus_reproducible_and_prepared_separately(tmp_path):
    generate(tmp_path)
    pages = load_corpus(tmp_path)
    assert len(pages) == 8
    assert len({p.sha256 for p in pages}) == 8
    generate(tmp_path)
    assert [p.sha256 for p in pages] == [p.sha256 for p in load_corpus(tmp_path)]
    assert prepare(tmp_path / "page-01.png").data_url.startswith(
        "data:image/png;base64,"
    )


def test_corpus_rejects_empty_expectations(tmp_path):
    generate(tmp_path)
    path = tmp_path / "manifest.json"
    data = json.loads(path.read_text())
    data["pages"][0]["expected"] = []
    path.write_text(json.dumps(data))
    result = subprocess.run(
        ["inference-axi", "bench", str(tmp_path), "--output", str(tmp_path / "run")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "nonempty expected text" in result.stdout


def test_toon_escaping_does_not_corrupt_literal_backslashes():
    from inference_lab.cli import scalar

    for text in ["a\\bar", "a\\foo", "a\b", "a\f", "a\n", '🧪,"x"', "#tag"]:
        assert json.loads(scalar(text)) == text
    assert scalar("hello world") == "hello world"

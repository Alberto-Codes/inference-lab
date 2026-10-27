import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def module(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "draft_release", ROOT / "scripts/draft_release.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.chdir(tmp_path)
    notes = tmp_path / "docs/releases/v0.1.0.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("Draft post pending. [Evidence](../reference/receipt-results.md)")
    monkeypatch.setattr(m.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: None)
    return m


def test_draft_pins_target_and_leaves_tag_absent(module, monkeypatch):
    requests = []
    draft = {}

    def api(path, payload=None):
        requests.append((path, payload))
        if path.startswith("actions/"):
            return {"workflow_runs": [{"head_sha": "a" * 40, "conclusion": "success"}]}
        if path.startswith("git/ref/"):
            return None
        if path.startswith("releases?"):
            return []
        if payload:
            draft.update(payload, id=1, html_url="https://example.test/draft")
        return draft

    monkeypatch.setattr(module, "api", api)
    result = module.create_draft("v0.1.0", "a" * 40)
    assert result["draft"] is True
    assert result["target_commitish"] == "a" * 40
    assert f"blob/{'a' * 40}/docs/reference/receipt-results.md" in result["body"]
    assert requests[-1][0] == "git/ref/tags/v0.1.0"
    assert len([payload for _, payload in requests if payload]) == 1


def test_draft_refuses_unverified_commit(module, monkeypatch):
    monkeypatch.setattr(module, "api", lambda *a, **k: {"workflow_runs": []})
    with pytest.raises(ValueError, match="Successful CI"):
        module.create_draft("v0.1.0", "a" * 40)
    with pytest.raises(ValueError, match="full lowercase"):
        module.create_draft("v0.1.0", "main")


def test_draft_refuses_existing_tag(module, monkeypatch):
    def api(path, payload=None):
        assert payload is None
        if path.startswith("actions/"):
            return {"workflow_runs": [{"head_sha": "a" * 40, "conclusion": "success"}]}
        return {"ref": "existing"}

    monkeypatch.setattr(module, "api", api)
    with pytest.raises(ValueError, match="Tag already exists"):
        module.create_draft("v0.1.0", "a" * 40)

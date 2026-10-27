import hashlib
import io
import json

import httpx
import pytest
from PIL import Image
from test_receipt_commands import script

pa = pytest.importorskip("pyarrow", reason="Run with --group data to test preparation")
parquet = pytest.importorskip(
    "pyarrow.parquet", reason="Run with --group data to test preparation"
)


def test_pinned_download_matches_archived_images_and_labels(tmp_path, monkeypatch):
    module = script("prepare_receipts")
    image = Image.new("RGB", (4, 4), "red")
    png, jpeg = io.BytesIO(), io.BytesIO()
    image.save(png, format="PNG")
    image.save(jpeg, format="JPEG", quality=75)
    truth = {"valid_line": []}
    pages = [
        {
            "id": i,
            "file": f"test-{i:03d}.jpg",
            "sha256": hashlib.sha256(jpeg.getvalue()).hexdigest(),
            "ground_truth": truth,
        }
        for i in range(24)
    ]
    archive = tmp_path / "archive.json"
    archive.write_text(json.dumps({"pages": pages}))
    monkeypatch.setattr(module, "ARCHIVE", archive)
    table = pa.Table.from_pylist(
        [{"image": {"bytes": png.getvalue()}, "ground_truth": json.dumps(truth)}] * 100
    )
    data = io.BytesIO()
    parquet.write_table(table, data)

    def respond(request):
        assert f"/resolve/{module.REVISION}/" in str(request.url)
        return httpx.Response(200, content=data.getvalue())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = module.prepare_corpus(tmp_path / "new", client)
    assert len(result["pages"]) == 24
    assert (tmp_path / "new/test-000.jpg").read_bytes() == jpeg.getvalue()
    assert result["source"]["sha256"] == hashlib.sha256(data.getvalue()).hexdigest()


def test_preparation_never_overwrites_existing_corpus(tmp_path):
    module = script("prepare_receipts")
    target = tmp_path / "old"
    target.mkdir()
    (target / "manifest.json").write_text("historical")
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("Must not download"))
        ) as client,
        pytest.raises(FileExistsError),
    ):
        module.prepare_corpus(target, client)
    assert (target / "manifest.json").read_text() == "historical"


def test_scaling_reservation_precedes_download_and_excludes_holdout(tmp_path):
    module = script("prepare_scaling")
    root = tmp_path / "coverage"
    rows = []
    images = []
    for index in range(100):
        image = Image.new("RGB", (2, 2), (index, 0, 0))
        raw = io.BytesIO()
        image.save(raw, format="PNG")
        images.append(raw.getvalue())
        rows.append(
            {
                "image": {"bytes": raw.getvalue()},
                "ground_truth": json.dumps(
                    {"valid_line": [{"words": [{"text": str(index)}]}]}
                ),
            }
        )
    data = io.BytesIO()
    parquet.write_table(pa.Table.from_pylist(rows), data)

    def respond(request):
        reservation = json.loads((root / "reservation.json").read_text())
        assert reservation["evaluation_rows"] == list(range(80, 100))
        assert module.REVISION in str(request.url)
        return httpx.Response(200, content=data.getvalue())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        manifest = module.prepare_corpus(root, client)
    assert [p["id"] for p in manifest["pages"]] == list(range(24, 80))
    assert len(list(root.glob("*.image"))) == 56
    assert not (root / "test-080.image").exists()
    assert (root / "test-024.image").read_bytes() == images[24]
    with httpx.Client() as client, pytest.raises(FileExistsError):
        module.prepare_corpus(root, client)

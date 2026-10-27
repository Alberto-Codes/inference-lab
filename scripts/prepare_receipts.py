"""Download the fixed public CORD pilot from revision-pinned source bytes."""

import argparse
import hashlib
import io
import json
from pathlib import Path

import httpx
from PIL import Image

REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"
DATASET = "naver-clova-ix/cord-v2"
SOURCE = "data/test-00000-of-00001-9c204eb3f4e11791.parquet"
ARCHIVE = Path(__file__).resolve().parents[1] / "evidence/cord-test-24/manifest.json"


def prepare_corpus(root: Path, client: httpx.Client) -> dict:
    import pyarrow.parquet as parquet

    root.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(ARCHIVE.read_text())
    response = client.get(
        f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{SOURCE}"
    )
    response.raise_for_status()
    table = parquet.read_table(io.BytesIO(response.content))
    if table.num_rows != 100:
        raise ValueError("Pinned test source must contain 100 rows")
    rows = table.slice(0, 24).to_pylist()
    for item, row in zip(manifest["pages"], rows, strict=True):
        original = row["image"]["bytes"]
        with Image.open(io.BytesIO(original)) as image:
            encoded = io.BytesIO()
            image.save(encoded, format="JPEG", quality=75)
            raw = encoded.getvalue()
        truth = json.loads(row["ground_truth"])
        if truth != item["ground_truth"]:
            raise ValueError(f"Annotation mismatch for test row {item['id']}")
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"Image mismatch for test row {item['id']}")
        (root / item["file"]).write_bytes(raw)
    manifest["source"] = {
        "file": SOURCE,
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "revision": REVISION,
        "image_encoding": "Pillow JPEG quality=75; verified against archived viewer hashes",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New corpus directory; must not exist",
    )
    args = parser.parse_args()
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        manifest = prepare_corpus(args.output, client)
    print(f"status: prepared\ncount: {len(manifest['pages'])}\noutput: {args.output}")


if __name__ == "__main__":
    main()

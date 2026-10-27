"""Prepare pinned CORD coverage inputs after recording an evaluation reservation."""

import argparse
import hashlib
import io
import json
from pathlib import Path

import httpx

DATASET = "naver-clova-ix/cord-v2"
REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"
SOURCE = "data/test-00000-of-00001-9c204eb3f4e11791.parquet"


def prepare_corpus(root: Path, client: httpx.Client) -> dict:
    """Reserve rows 80-99 before downloading; expose only coverage rows 24-79."""
    from pyarrow import parquet  # noqa: PLC0415 - optional data dependency

    root.mkdir(parents=True, exist_ok=False)
    reservation = {
        "dataset": DATASET,
        "revision": REVISION,
        "license": "CC-BY-4.0",
        "attribution": "NAVER CLOVA; Park et al., CORD (2019)",
        "source": SOURCE,
        "pilot_rows": list(range(24)),
        "coverage_rows": list(range(24, 80)),
        "evaluation_rows": list(range(80, 100)),
        "policy": "Do not inspect, infer, score or tune on evaluation rows in this increment.",
    }
    (root / "reservation.json").write_text(json.dumps(reservation, indent=2) + "\n")
    response = client.get(
        f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{SOURCE}"
    )
    response.raise_for_status()
    table = parquet.read_table(io.BytesIO(response.content))
    if table.num_rows != 100:  # noqa: PLR2004 - pinned source invariant
        raise ValueError("Pinned test split must have 100 rows")
    pages = []
    # Never convert held-out rows to Python or save their images/annotations.
    for index, row in enumerate(table.slice(24, 56).to_pylist(), 24):
        raw = row["image"]["bytes"]
        filename = f"test-{index:03d}.image"
        (root / filename).write_bytes(raw)
        pages.append(
            {
                "id": index,
                "file": filename,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "ground_truth": json.loads(row["ground_truth"]),
            }
        )
    manifest = {
        **reservation,
        "source_sha256": hashlib.sha256(response.content).hexdigest(),
        "image_encoding": "original embedded source bytes",
        "partition": "coverage",
        "pages": pages,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    """Create a new coverage corpus and a separate evaluation reservation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        manifest = prepare_corpus(args.output, client)
    print(json.dumps({"status": "prepared", "pages": len(manifest["pages"])}))


if __name__ == "__main__":
    main()

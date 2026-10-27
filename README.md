# inference-lab

Reproducible document-parsing experiments with **NVIDIA Nemotron-3.5-Parse**,
vLLM and one RTX 4090. Each experiment keeps its inputs' provenance,
raw outputs, measurements and limits beside its code.

[Documentation](https://alberto-codes.github.io/inference-lab/) ·
[Receipt results](docs/reference/receipt-results.md) ·
[Experiment releases](https://github.com/Alberto-Codes/inference-lab/releases)

The first receipt pilot used 24 CORD test images.
All 48 measured requests completed, but one amount changed from `79,500` to `79,300`.
At concurrency one, diagnostic ROUGE-L F1 was 0.801.
Exact numeric-string recall was 212/241, or 88.0%.
These partial-reference scores assess extracted text and numbers.
They do not measure layout accuracy, table structure or financial field association.

## Inspect the saved experiment

Python 3.12 and [uv](https://docs.astral.sh/uv/) are sufficient for offline scoring.
Use a new output filename each time.

```sh
uv sync --locked
uv run python scripts/score_receipts.py \
  --input evidence/cord-test-24 --output runs/inspection/scores.json
```

The [quickstart](docs/tutorials/first-result.md) explains the outputs.
The [receipt procedure](docs/how-to/evaluate-receipts.md) covers a fresh GPU run.
Preparation, inference, scoring and optional judge review use explicit paths.
Existing output directories and files are protected from replacement.

## Run locally

The parser needs Linux x86-64, rootless Podman, NVIDIA CDI and at least
11000 MiB of free GPU memory with the current profile.
Allow tens of GB for model weights and container layers.
The [serving reference](docs/reference/serving.md) records the pinned model and image.

Judgevet → Typevet → local Gemma provides an optional advisory review.
It is not needed to reproduce the deterministic scores.
The parser and judge use the GPU at separate times.

## Experiments and companion posts

An immutable tag identifies each experiment's code and evidence.
Its GitHub Release links to the companion post, which links back to the release.
The first release remains a draft until its post is ready.
This repository does not publish a Python package to PyPI.
Pages is a living documentation site built from validated `main`.
See [release procedure](docs/how-to/cut-a-release.md).

## Validate

```sh
uv sync --locked --group docs --group data
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
uv run --group docs mkdocs build --strict
```

Offline tests do not establish live model inference.
Run `uv run pytest -m gpu` only with the parser server ready.
Keep new observations separate from the saved historical pilot.

Project code uses the [MIT licence](LICENSE).
CORD annotations use CC BY 4.0; model assets have separate licences.
See [third-party notices](THIRD_PARTY_NOTICES.md) and [contributing](CONTRIBUTING.md).

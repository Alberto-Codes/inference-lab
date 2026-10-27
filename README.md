# inference-lab

A small OCR service demo for Nemotron-3.5-Parse on a local RTX 4090.
The Python client sends page images to vLLM in a Podman container.
The experiment submits eight synthetic pages at concurrency levels 1, 2, 4 and 8.
It saves outputs, failures, latency observations and throughput results.

**Status:** the local GPU demo passed all 32 measured OCR requests.
The offline suite passed 29 tests. The separate GPU test passed.
llama.cpp and its previously loaded model were restored after the test.
See the [evidence record](docs/reference/evidence.md) for results and limits.

## Requirements

- Linux x86-64, Python 3.12 and uv.
- Rootless Podman with NVIDIA CDI access.
- At least 11000 MiB of free GPU memory for the current profile.
- Internet access and tens of GB of disk space for image layers and model weights.

The pinned model is public and ungated.
Its weights and NVIDIA code use OpenMDW-1.1.
The tokenizer has separate MIT attribution.
The image retains these notices.

## Commands

Run these commands from this checkout.
Read the [run procedure](docs/how-to/run-demo.md) before the GPU test.

```sh
uv sync --locked
uv run inference-axi
uv run inference-axi corpus
uv run inference-axi build
uv run inference-axi start
uv run inference-axi ocr corpus/page-01.png --output runs/page-01.txt --expect LAB401
uv run inference-axi bench corpus --output runs/first
uv run inference-axi stop
```

The CLI follows [AXI](https://github.com/kunchenguid/axi) output principles.
It shows live state without arguments.
It gives compact TOON output, structured errors and command help.
It installs no agent hooks.

## Documentation

- [Run the demo](docs/how-to/run-demo.md): setup, test and shutdown steps.
- [Serving profile](docs/reference/serving.md): runtime pins and resource settings.
- [CLI and results](docs/reference/cli.md): commands, output files and exit codes.
- [Evidence](docs/reference/evidence.md): observed facts, sources and unresolved issues.
- [Measurement method](docs/explanation/measurement.md): timing and quality limits.
- [Engineering practices](docs/explanation/engineering-practices.md): choices from sibling projects.
- [Writing rules](docs/reference/writing.md): Diátaxis and ASD-STE100 guidance.

## Validation

```sh
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

The default tests use mocked HTTP transport.
They do not prove model inference.
Run `uv run pytest -m gpu` only after the demo server is ready.

This experiment uses a small synthetic corpus.
It is not a general OCR benchmark or evidence for production latency guarantees.
The generated text and layouts use CC0-1.0.
The corpus manifest records their source.

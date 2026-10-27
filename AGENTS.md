# inference-lab

Small image OCR/concurrency demo using nvidia/Nemotron-3.5-Parse and vLLM.
Keep the scope to this first demo; no gateway, second model or dashboard stack.

- Use `uv` and Python 3.12. Package is in `src/inference_lab`.
- `inference-axi` is the AXI-style CLI; stdout is compact structured output.
- `serving/config.json` is the runtime profile. Model/plugin share a pinned revision.
- Stop existing GPU services only with explicit user approval. Restore them after the test.
- Write documentation under `docs/` with one Diátaxis kind per page.
  Use ASD-STE100 sentence guidance: short sentences, active voice and consistent technical terms.
  Keep procedures to one instruction per sentence.
- The demo owns only its labelled container. Preserve ownership and free-memory checks.
- `runs/`, `corpus/`, caches and model weights are not committed.
- Keep preparation/warmup separate from measured sweeps. Count quality failures,
  HTTP failures, truncations and timeouts; do not call mocked tests GPU evidence.
- Real inference checks use `pytest -m gpu` and require the demo server.

Validation: `uv lock --check`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pytest`, `uv build`.
Record actual integration status and unresolved limitations in `docs/reference/evidence.md`.

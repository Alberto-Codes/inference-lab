# First demo evidence — 2026-10-26

Kind: reference.

## Initial observations

**GPU inference has not run. No measured OCR latency or throughput is claimed.**
The independently tested client/reporting scaffold is ready; the serving profile
is a candidate for Ada, not a validated 4090 deployment.

Read-only inspection found one RTX 4090, 24564 MiB total, compute capability
8.9, driver 610.57.04. `nvidia-smi` reported 20987 MiB used and 3121 MiB free
(the reported values leave driver-reserved memory). `/app/llama-server` PID
3334311 accounted for 19796 MiB at initial inspection. The desktop also uses
GPU memory. Existing `llama-cpp-tuned`, Ollama, Open WebUI, Vane, SearXNG and

`uv run inference-axi start` exited 1 before creating any container because
3121 MiB free is below this profile's 11000 MiB guard. The guard covers a 40%
reservation (~9826 MiB) plus headroom. This check does not prove that the model cannot fit in 3 GiB.
The 11 GiB limit is not a measured minimum. Sharing the GPU
with a running service would also confound the concurrency experiment. No
service was replaced, stopped or reconfigured to clear memory.

The official H100 FA3 profile has an independent hardware mismatch: vLLM
0.26.0's FA3 implementation requires compute capability 9.x. The local 4090
reports 8.9. FA2 supports >=8.0 at the backend level. Our candidate uses FA2,
normal decoding (`NP_VLLM_MTP=0`), eager execution and eight sequence slots.
Whole-model/plugin compatibility with this adaptation remains unverified.

## Inspection commands

See [README](../../README.md) for setup/start/OCR/sweep/stop commands and
[serving/config.json](../../serving/config.json) for every server argument.

```sh
nvidia-smi
nvidia-smi --query-gpu=name,uuid,driver_version,memory.total,memory.used,memory.free,compute_cap --format=csv
nvidia-ctk cdi list
podman ps --format '{{.Names}} {{.Image}} {{.Status}}'
podman images
podman manifest inspect docker.io/vllm/vllm-openai:v0.26.0
df -h . /tmp
uv --version
podman --version
uv sync --locked
uv run inference-axi corpus
uv run inference-axi status
uv run inference-axi start
uv run inference-axi build
```

Initial filesystem free space: 507 GiB in `/var/home`, 52 GiB in `/tmp`.
uv 0.11.20, Python 3.12.12, Podman 5.8.4; NVIDIA CDI exposes GPU 0.
Build context is only `serving/`. The Linux amd64 base-image digest is
`sha256:770fe65b2c73ee74a5c42165cf3433de4048cc2cd9c57a937ca4e35aba5aa87b`.
Container stores the resolved package list in `/serving-packages.txt` for run
metadata. Direct runtime pins follow the upstream reference receipt.
The image and package list identify resolved transitive dependencies.
This does not establish a bit-for-bit reproducible rebuild.

## Verified offline behavior

- Deterministic generation of eight fictional pages with per-page known text;
  no third-party document corpus or PDF conversion required.
- Official HTTP prompt/generation contract, image data URLs, output persistence.
- Absolute request deadlines, HTTP/connect/malformed-response failures, empty
  and wrong text, truncation, and mixed successful/failed runs.
- Maximum in-flight requests exactly 1/2/4/8 in mocked transport tests; same
  eight inputs in every sweep. Warmup excluded and preserved separately.
- Successful pages/s uses successful completions only; failures and timeouts
  remain explicit. All/success-only min/median/max and raw latencies preserved.
- JSON and Markdown output plus provenance, no overwrite of a prior run.
- Unknown CLI flags fail before hardware calls; literal text escapes remain
  intact in TOON. Ownership guard refuses unrelated containers; stop is
  idempotent and uses an inspected container ID.

Validation commands: `uv lock --check`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pytest`, `uv build`.
The GPU-marked test is excluded by default and has **not** passed locally.
Mock transports are only software evidence; they are not local model results.

## Primary sources checked

All model files below were inspected at revision
`62cb1e4ba153d113ff64aaf2be6e068c377cf53c`, retrieved 2026-10-26.

- [Model card](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/62cb1e4ba153d113ff64aaf2be6e068c377cf53c/README.md): exact model ID, image prompt, parameters, BF16 and reference hardware.
- [Hub metadata](https://huggingface.co/api/models/nvidia/Nemotron-3.5-Parse): public, `gated=false`; anonymous metadata and source requests succeeded.
- [Licence](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/62cb1e4ba153d113ff64aaf2be6e068c377cf53c/LICENSE): OpenMDW-1.1 for weights/NVIDIA code; tokenizer has separate MIT attribution. Included notices stay in the image.
- [Serving guide](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/62cb1e4ba153d113ff64aaf2be6e068c377cf53c/docs/serving.md): reference vLLM 0.26.0 and disabling MTP for normal decoding.
- [Package metadata](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/62cb1e4ba153d113ff64aaf2be6e068c377cf53c/pyproject.toml): plugin 3.5.0.post7 and supported vLLM >=0.25.0,<0.33. This range is not proof of every combination.
- [Runtime compatibility receipt](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/62cb1e4ba153d113ff64aaf2be6e068c377cf53c/reference/model/runtime_compatibility.json): exact reference dependency versions and scope of upstream validation.
- [vLLM FA implementation](https://github.com/vllm-project/vllm/blob/v0.26.0/vllm/vllm_flash_attn/flash_attn_interface.py): hardware capability checks for FA2 and FA3.
- [AXI guidelines](https://github.com/kunchenguid/axi/blob/main/.agents/skills/axi/SKILL.md) and [TOON specification](https://github.com/toon-format/spec/blob/main/SPEC.md): CLI output/error/help conventions.

The background gateway series spec was read. Its Gemma workload, scheduler,
cloud spillover and full roadmap are intentionally outside this repository.
Sibling practice selections are in [practices.md](../explanation/engineering-practices.md).

## Authorized local test

The user approved a temporary shutdown of `llama-cpp-tuned.service`.
This approval overrides the original restriction for this test.
The service will remain available until the OCR image build finishes.
After the test, restore the service and verify its health.
The loaded model before shutdown is `gemma-4-31b-kv9-text`.

## Unresolved questions

When the GPU is independently made available, start this candidate profile,
inspect startup logs, and run one known-text page (`pytest -m gpu`). Resolve any
FA2/plugin issue against the pinned code before attempting the 1/2/4/8 sweep.
Then record the actual image ID, package list, outputs and resource conditions.
Do not treat the benchmark runner's existence as evidence that inference works.

The first sweep should answer whether this candidate runs correctly and how
observed throughput/latency change on this tiny corpus. It cannot identify a
production saturation knee or establish tail SLOs. Repeated, larger representative
runs are a later experiment, after this first smoke demo is working.

# Local demo evidence

Kind: reference.

Observation date: 2026-10-26 in America/Phoenix. The run timestamps use UTC on 2026-10-27.

## Outcome

**Nemotron OCR ran successfully on the local RTX 4090.**
All 32 measured requests passed the known-text checks.
The four sweeps had no failures or timeouts.
Eight separate warmup requests also passed.

The offline suite passed 29 tests.
The separate GPU test passed against the actual server.
The standalone `ocr` command saved a correct output and its JSON receipt.

The user approved a temporary shutdown of `llama-cpp-tuned.service`.
The test removed its OCR container afterward.
The runner restored llama.cpp and reloaded `gemma-4-31b-kv9-text`.
The final receipt records the model as loaded and the service as healthy.

## Measured results

| Concurrency | Inputs | Successes | Failures | Timeouts | Elapsed s | Pages/s | Median latency s |
|---|---|---|---|---|---|---|---|
| 1 | 8 | 8 | 0 | 0 | 1.866 | 4.288 | 0.225 |
| 2 | 8 | 8 | 0 | 0 | 1.019 | 7.848 | 0.241 |
| 4 | 8 | 8 | 0 | 0 | 0.523 | 15.285 | 0.244 |
| 8 | 8 | 8 | 0 | 0 | 0.297 | 26.976 | 0.262 |

These results describe a short closed-loop experiment with a warmed image cache.
Each sweep uses the same eight synthetic pages once.
The client warms all eight pages before the first measured sweep.
Prefix caching is disabled. The default multimodal cache remains enabled.
The comparison contains no other concurrent OCR requests.

The first exploratory sweep warmed only one page.
Its logs showed a multimodal cache hit rate of 76.5%.
This finding prompted the full-corpus warmup policy.
A later trial overlapped with the standalone CLI check.
The final comparison excludes both exploratory trials.

The reported throughput increases with concurrency.
Median request latency increases from approximately 225 ms to 262 ms.
This small corpus cannot establish general OCR quality, overload behavior or production latency guarantees.
Preparation, startup, warmup and report writes are outside the measured sweep times.
The report retains individual latencies and output text.

## Reproduction and artifacts

Follow [Run the demo](../how-to/run-demo.md) from the repository root.
Use [the serving configuration](../../serving/config.json) without changes to reproduce this profile.

Exact measured command:

```sh
uv run inference-axi bench corpus --output runs/local-4090-final
```

- [Final machine-readable results](../../evidence/local-demo/results.json).
- [Generated summary](../../evidence/local-demo/summary.md).
- [GPU test and restoration receipt](../../evidence/local-demo/gpu-attempt.json).
- [Server logs](../../evidence/local-demo/gpu-server-log.toon).
- [Standalone extraction](../../evidence/local-demo/local-4090-page-01.txt).
- [Offline test output](../../evidence/tests.txt).

Source commit: `b3df45155609747b9191bcc25df5699a6438d29f`.
The run records a dirty working tree because the runner creates evidence files.
The tracked client and serving files matched that commit during measurement.
Image ID: `f261ace8dcf68c12f6c06ac4b5fa1d514df9303fd5f07ba200f50b175b16f01b`.
The result metadata contains the resolved Python package list and input SHA-256 hashes.

## Hardware and serving stack

GPU: RTX 4090, 24564 MiB total memory, compute capability 8.9.
Driver: 610.57.04. Host tools: uv 0.11.20 and Podman 5.8.4.
Initial free disk space was 507 GiB on the workspace filesystem.
NVIDIA CDI exposed GPU 0.

The model and plugin share revision `62cb1e4ba153d113ff64aaf2be6e068c377cf53c`.
The plugin version is `3.5.0.post7`.
Core pins: vLLM 0.26.0, Torch 2.11.0, torchvision 0.26.0, Transformers 5.14.1 and huggingface-hub 1.24.0.
The local profile uses FA2, BF16, eager execution and normal decoding.
It permits eight sequences with 16384 context tokens and a 40% GPU memory reservation.
The server logs confirm FlashAttention version 2 and no speculative decoding.

NVIDIA tests its reference profile on H100 with FA3 and MTP.
vLLM restricts FA3 to compute capability 9.x in this release.
The successful local test establishes the basic Ada path used here.
It does not validate MTP, every input size or all supported vLLM versions.

## Setup findings

The first startup check refused to run with only 3121 MiB of free GPU memory.
The existing llama.cpp process used approximately 19796 MiB.
After user approval, the runner stopped that service through systemd.
The configured 11000 MiB guard is a reservation policy, not a measured model minimum.

The first image build failed `pip check` on two upstream-image issues.
Its PyGObject package lacked the `pycairo` dependency.
Its optional NIXL meta-package mismatched the CUDA backend package.
The recipe installs the distribution package `python3-cairo` and removes the unused NIXL meta-package.
The final image passes `pip check`.
These repairs affect only the demo image.

The build pins the Linux amd64 base-image digest.
It also pins the model source and core runtime packages.
The package list records remaining transitive versions.
This does not establish a bit-for-bit reproducible image rebuild.

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

## Next smallest experiment

Repeat the warmed sweep three times with more pages per level.
Keep the server profile and synthetic corpus fixed.
Record run-to-run variation before changing model or serving settings.
Use longer runs before drawing conclusions about throughput scaling.
A separate cold-cache experiment can measure document preparation and image-cache costs.

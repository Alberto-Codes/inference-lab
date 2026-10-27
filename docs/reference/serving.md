# Serving profile

Kind: reference.

[serving/config.json](https://github.com/Alberto-Codes/inference-lab/blob/main/serving/config.json) records the command arguments.
Model and plugin share immutable revision
`62cb1e4ba153d113ff64aaf2be6e068c377cf53c` (plugin `3.5.0.post7`). The container
pins vLLM 0.26.0, Torch 2.11.0, torchvision 0.26.0, Transformers 5.14.1 and
huggingface-hub 1.24.0, based on NVIDIA's reference runtime.

**Verified local smoke profile:** FA2, `NP_VLLM_MTP=0`, eager execution,
eight sequences, 16384 context/batched tokens, BF16, 40% memory reservation.
NVIDIA's measured reference uses H100, FA3 and MTP. FA3 requires compute
capability 9.x in this vLLM release and cannot run on the 4090 (8.9).
The local test passed with this FA2 profile.
It does not validate MTP or every workload on Ada.

Only port 8017 on host loopback is published. SELinux container separation is
disabled for NVIDIA CDI access for this container, not system-wide. The build
uses only `serving/` as context; caches and weights remain in Podman storage.
Starting executes upstream custom code from the pinned model revision.

`stop` checks a checkout ownership label and removes only the inspected
container ID. It is a no-op when absent. It retains reusable images/build cache.
Readiness failures retain the container for `logs`; use `stop` to clean it up.
Ctrl-C during startup removes the demo container. Ctrl-C during a benchmark
cancels the client's work; `stop` terminates any inference still executing.


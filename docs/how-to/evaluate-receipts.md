# Run the receipt experiment

Kind: how-to.

This is the current guide for the **v0.1.0** experiment.
For the original wording and commands, use the [instructions at v0.1.0](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/docs/how-to/evaluate-receipts.md).
See the [experiment index](../reference/experiments.md) to choose a different study.

This procedure installs and runs Nemotron-3.5-Parse on a fixed receipt corpus.
It needs no judge model or existing model server.
For a GPU-free start, [inspect the saved results](../tutorials/first-result.md).

## Install the prerequisites

Use Linux x86-64 and an NVIDIA GPU.
The recorded experiment used one RTX 4090 with 24 GiB of memory.
The current profile requires at least 11000 MiB free on **GPU 0**.
This is a reservation policy, not a measured minimum for every input.
Other GPU architectures are not verified by this pilot.
Allow tens of GB for container layers and model weights.

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git.
2. Install [Podman with rootless support](https://podman.io/docs/installation).
3. Install the [NVIDIA driver](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html) for your system.
4. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
5. Follow NVIDIA's [CDI setup guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html).
6. Check the host and GPU device.

   ```sh
   uv --version
   podman info
   nvidia-smi --id=0
   nvidia-ctk cdi list
   ```

The CDI list must include `nvidia.com/gpu=0`.
The serving profile selects that device and checks its free memory.
It refuses insufficient memory and does not stop other workloads.

## Install the experiment

1. Clone the repository.

   ```sh
   git clone --branch v0.1.0 https://github.com/Alberto-Codes/inference-lab.git
   cd inference-lab
   ```

2. Install Python and the locked preparation dependencies.

   ```sh
   uv python install 3.12
   uv sync --locked --group data
   ```

3. Download the fixed inputs into a new directory.

   ```sh
   uv run --group data python scripts/prepare_receipts.py --output corpus/receipts-01
   ```

Preparation reads the pinned CORD test source and verifies all 24 image hashes and annotations.
It reproduces the JPEG encoding used by the recorded pilot.
See [input identity](../reference/receipts.md#input-identity) for details.

4. Build the pinned parser container.

   ```sh
   uv run inference-axi build
   ```

5. Check available GPU memory.

   ```sh
   uv run inference-axi status
   ```

## Run and save outputs

1. Start the parser.

   ```sh
   uv run inference-axi start
   ```

If startup fails, save `uv run inference-axi logs --full` before running `uv run inference-axi stop`.
The stop command removes only this checkout's owned parser container.
Resolve the reported failure before starting again.

2. Submit the receipt corpus with cleanup on exit.

   ```sh
   (
     trap 'uv run inference-axi stop' EXIT
     uv run python scripts/receipt_experiment.py \
       --input corpus/receipts-01 --output runs/receipts-01
   )
   ```

The run warms each image, then measures concurrency levels one and four.
It saves terminal records in `requests.jsonl` and a summary in `results.json`.
A failed warmup prevents measured work.
An interrupted run retains its completed request records.

## Inspect results

1. Score the selected run into a new file.

   ```sh
   uv run python scripts/score_receipts.py \
     --input runs/receipts-01 --output runs/receipts-01/scores.json
   ```

2. Read the summaries and individual missing-number lists in `scores.json`.
3. Compare suspicious outputs with the corresponding receipt images.

The scorer refuses incomplete or duplicate sample sets.
It does not modify the raw requests or replace an existing output file.
Use a new directory or filename for another attempt.

These scores check extracted text and numbers, not layout or table-structure accuracy.
[Model-assisted review](review-with-a-model.md) is a separate optional step.
Use [troubleshooting](troubleshoot.md) for startup, memory or scoring errors.

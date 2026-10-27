# Evaluate CORD receipts

Kind: how-to.

Run these commands from the repository root.
Use Linux x86-64, Python 3.12, uv, rootless Podman and NVIDIA CDI.
Allow at least 11000 MiB of free GPU memory and tens of GB of disk space.
Read the [serving profile](../reference/serving.md) before starting.

## Prepare inputs

1. Install the locked preparation dependencies.

   ```sh
   uv sync --locked --group data
   ```

2. Download the pinned receipt source into a new directory.

   ```sh
   uv run --group data python scripts/prepare_receipts.py --output corpus/receipts-01
   ```

The command reads the pinned CORD test Parquet file.
It recreates the viewer's JPEG encoding with Pillow quality 75.
It verifies all 24 image hashes and annotations against the archived pilot.
A mismatch stops preparation. It never silently changes the tested input.
The dataset uses CC BY 4.0. Credit NAVER CLOVA and the CORD authors.

3. Build the pinned parser container before releasing GPU resources.

   ```sh
   uv run inference-axi build
   ```

## Run with an unused GPU

1. Start the parser.

   ```sh
   uv run inference-axi start
   ```

2. Run the receipt experiment with cleanup on exit.

   ```sh
   (
     trap 'uv run inference-axi stop' EXIT
     uv run python scripts/receipt_experiment.py \
       --input corpus/receipts-01 --output runs/receipts-01
   )
   ```

## Temporarily release the local llama.cpp service

Use this alternative only when you own the GPU service or have permission to stop it.
The option targets `llama-cpp-tuned.service` and the router at `127.0.0.1:8090`.
It is specific to this local setup.

```sh
uv run python scripts/receipt_experiment.py \
  --input corpus/receipts-01 --output runs/receipts-01 --release-llama
```

The command captures the service state and previously loaded model IDs.
It refuses to proceed if a parser container already exists.
It stops llama.cpp, starts the parser and runs the experiment.
Cleanup removes only the owned parser container.
It then restores the original service state and verifies the loaded model IDs.
Restoration uses a 180-second readiness deadline after service startup.
The run records experiment and restoration failures in `lifecycle.json`.
A restoration failure returns a nonzero exit status.

Forced process termination or power loss can bypass cleanup.
Use the recovery instructions in [Troubleshoot](troubleshoot.md).

## Score the selected run

Use a new output filename.

```sh
uv run python scripts/score_receipts.py \
  --input runs/receipts-01 --output runs/receipts-01/scores.json
```

The same run directory connects inference and scoring.
The scorer refuses incomplete or duplicate sample sets.
It retains failures in the quality denominators with empty scoring predictions.
It does not modify the raw request file.

## Optional Judgevet review

Restore the local Gemma model before this step.
The configured default is `gemma-4-31b-kv9-text` at `127.0.0.1:8090`.
Use Typevet environment settings for another supported local configuration.

```sh
uv run --script scripts/review_receipts.py \
  --input runs/receipts-01/scores.json \
  --rubric evidence/cord-test-24/judgevet-review.json \
  --output runs/receipts-01/judgments.json
```

The command uses Judgevet 0.23.0 and Typevet 0.11.0.
It selects the three lowest-overlap cases from the supplied scores.
The historical file supplies the rubric only, not the cases.
Keep advisory judgments separate from deterministic metrics.

A failed attempt retains partial output for diagnosis.
Choose new output paths for retries. Do not delete evidence to make a command pass.

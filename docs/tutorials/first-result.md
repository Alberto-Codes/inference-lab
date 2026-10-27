# Inspect the saved experiment

Kind: tutorial.

This exercise recalculates the receipt pilot's scores without a GPU.
Install [Git](https://git-scm.com/downloads) and
[uv](https://docs.astral.sh/uv/getting-started/installation/) before you start.
The initial clone and dependency installation need internet access.
uv can install Python 3.12 if it is missing.
After setup, the scoring command uses only the saved responses.
It needs no model server, GPU or dataset image download.

1. Clone the public repository.

   ```sh
   git clone https://github.com/Alberto-Codes/inference-lab.git
   cd inference-lab
   ```

2. Install the locked client environment.

   ```sh
   uv sync --locked
   ```

3. Recalculate scores into a new file.

   ```sh
   uv run --offline python scripts/score_receipts.py \
     --input evidence/cord-test-24 --output runs/inspection/scores.json
   ```

The command prints three summaries: warmup, measured concurrency one and measured concurrency four.
The concurrency-one summary reports 212 numeric matches out of 241 annotated numeric strings.
Its diagnostic ROUGE-L F1 is approximately 0.801.

4. Open `runs/inspection/scores.json`.
5. Find the measured concurrency-one record with ID 20.
6. Compare its reference with `plain_prediction` and `missing_numbers`.

The reference contains `79,500`. The prediction contains `79,300`.
The request completed, but it changed an amount.

The scorer refuses to replace an existing output file.
Choose a different output filename when you repeat this exercise.
The original evidence stays in `evidence/cord-test-24/`.

Read [receipt results](../reference/receipt-results.md) for limits and image-based observations.
Continue with [Evaluate receipts](../how-to/evaluate-receipts.md) to submit new parser requests.

# Troubleshoot a receipt run

Kind: how-to.

## An output already exists

1. Keep the existing output for inspection.
2. Choose a new run directory or score filename.
3. Retry the command with that path.

An interrupted preparation can leave a partial corpus without a manifest.
Use a new directory for the next preparation attempt.

## The parser does not start

1. Run `uv run inference-axi status`.
2. Check the free GPU memory against the serving profile.
3. Read `uv run inference-axi logs --full`.
4. Remove the owned parser with `uv run inference-axi stop`.

Do not remove unrelated containers.
The container ownership label prevents this checkout from managing another checkout's parser.

## Restore llama.cpp after interrupted handover

1. Read the run's `lifecycle.json` for the original service state and model IDs.
2. Remove the owned parser.

   ```sh
   uv run inference-axi stop
   ```

3. If the service was active, start it.

   ```sh
   systemctl --user start llama-cpp-tuned.service
   ```

4. Load each recorded model through `/models/load`.
5. Poll `/models` until each recorded ID reports `loaded`.
6. Stop polling after 180 seconds and inspect the service logs if loading fails.

Use a request timeout of at most 10 seconds for each status check.
A successful load response can precede completed model loading.
If the service was inactive before the run, leave it inactive.

## Scores differ from the article

1. Check the run directory supplied to the scorer.
2. Check the dataset revision and image hashes in the manifest.
3. Compare raw text before changing normalization rules.
4. Keep new observations separate from the historical pilot.

New inference is not guaranteed to produce byte-identical text on a different runtime.
Offline rescoring of the saved requests should reproduce the documented quality metrics.

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

## Scores differ from the article

1. Check the run directory supplied to the scorer.
2. Check the dataset revision and image hashes in the manifest.
3. Compare raw text before changing normalization rules.
4. Keep new observations separate from the historical pilot.

New inference is not guaranteed to produce byte-identical text on a different runtime.
Offline rescoring of the saved requests should reproduce the documented quality metrics.

# Advanced: temporarily release a local service

Kind: how-to.

This optional adapter targets a specific local systemd setup.
It is not part of the normal installation or receipt procedure.
Use it only if you already manage `llama-cpp-tuned.service` and its router on port 8090.
Do not use it for a different service or without permission to stop that workload.

1. Prepare the corpus and build the parser image using the [receipt guide](evaluate-receipts.md).
2. Run the explicit handover command with a new output directory.

   ```sh
   uv run python scripts/receipt_experiment.py \
     --input corpus/receipts-01 --output runs/receipts-01 --release-llama
   ```

The command records the service state and loaded model IDs before shutdown.
It refuses an existing parser container.
After the run, it removes only the owned parser and restores the recorded service state.
A bounded check verifies the previously loaded IDs.
Restoration failures return a nonzero exit status and appear in `lifecycle.json`.

## Recover after forced termination

Power loss or forced termination can bypass cleanup.

1. Read the run's `lifecycle.json` for the original service state and model IDs.
2. Run `uv run inference-axi stop` to remove the owned parser.
3. Start `llama-cpp-tuned.service` only if it was previously active.
4. Reload each recorded model ID through the router's `/models/load` endpoint.
5. Poll `/models` until each recorded ID reports `loaded`.
6. Stop polling after 180 seconds and inspect service logs if loading fails.

Use status-request timeouts of at most 10 seconds.
A successful load response can precede completed loading.
Leave a previously inactive service inactive.

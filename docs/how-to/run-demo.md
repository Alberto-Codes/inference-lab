# Run a synthetic smoke test

Kind: how-to.

Use this procedure from the repository root.
Follow the [GPU prerequisite instructions](evaluate-receipts.md#install-the-prerequisites) first.
The serving profile needs at least 11000 MiB of free GPU memory.

1. Install the client and development tools.

   ```sh
   uv sync --locked
   ```

2. Generate the eight synthetic page images.

   ```sh
   uv run inference-axi corpus
   ```

3. Build the server image.

   ```sh
   uv run inference-axi build
   ```

4. Check the available GPU memory.

   ```sh
   uv run inference-axi status
   ```

5. Start the demo server.

   ```sh
   uv run inference-axi start
   ```

6. Check one page with known text.

   ```sh
   uv run inference-axi ocr corpus/page-01.png --output runs/page-01.txt --expect LAB401
   uv run pytest -m gpu
   ```

7. Run the four concurrency levels.

   ```sh
   uv run inference-axi bench corpus --output runs/first
   ```

8. Read `runs/first/summary.md`.

9. Check the failures and raw outputs in `runs/first/results.json`.

10. Remove the demo container.

    ```sh
    uv run inference-axi stop
    ```

Use `uv run inference-axi logs` if startup fails.
Use `uv run inference-axi logs --full` for all log lines.
Run `stop` after a startup failure to remove the failed container.

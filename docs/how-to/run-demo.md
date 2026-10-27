# Run the OCR demo

Kind: how-to.

Use this procedure from the repository root.
Install Python 3.12, uv, Podman and NVIDIA CDI first.
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

## Temporarily release the local GPU

Get the user's approval before you stop an existing service.
Build the image before you stop the service.

The local llama.cpp service uses `llama-cpp-tuned.service`.
Record the loaded model ID before shutdown.

```sh
curl --fail --max-time 10 http://127.0.0.1:8090/models
```

Stop the service through systemd.
Do not remove its container directly.

```sh
systemctl --user stop llama-cpp-tuned.service
```

Run the OCR procedure from step 4.
Remove the demo container before you restore llama.cpp.
Restore llama.cpp even if the OCR test fails.

```sh
uv run inference-axi stop
systemctl --user start llama-cpp-tuned.service
curl --fail --max-time 10 http://127.0.0.1:8090/health
```

The router health check does not prove that a model has finished loading.
Reload the previous model with its recorded ID.

```sh
curl --fail --max-time 180 http://127.0.0.1:8090/models/load \
  --json '{"model":"<previous-model-id>"}'
curl --fail --max-time 10 http://127.0.0.1:8090/models
```

Confirm that the model status is `loaded`.

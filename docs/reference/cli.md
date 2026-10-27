# CLI and result files

Kind: reference.

The executable is `inference-axi`.
Run it through `uv run` from this checkout.
Each command accepts `--help`.
The parser rejects unknown flags before it calls external tools.

| Command | Result |
|---|---|
| No arguments or `status` | Container state, readiness and free GPU memory |
| `corpus --output <directory>` | Eight images and a manifest with known text |
| `build` | Local Podman server image |
| `start` | Owned server container after a memory check |
| `stop` | Removal of the owned container |
| `logs` | Last 40 log lines |
| `logs --full` | All log lines |
| `ocr <image> --output <file>` | Raw model text and a JSON receipt |
| `bench <corpus> --output <new-directory>` | JSON results and a Markdown summary |

`ocr` and `bench` accept a positive `--timeout` value in seconds.
The default is 120 seconds per request.
`ocr` accepts repeatable `--expect` phrases and an optional `--url`.
`bench` accepts `--concurrency` values from 1, 2, 4 and 8.
It requires this checkout's local server.
It rejects an existing output directory.

The client converts each image to RGB PNG before it starts inference timing.
It preserves class and coordinate tokens in the raw response.
The raw output is not cleaned Markdown.
PDF conversion is outside this demo.

## Output channels and exit codes

Stdout contains TOON scalar fields.
Stderr contains build diagnostics.
The default OCR preview has at most 500 characters.
The output file always contains the full text.
`ocr --full` prints all text from a new request.

| Exit code | Meaning |
|---|---|
| 0 | Command succeeded, including an idempotent stop |
| 1 | Runtime failure or unsuccessful OCR completion |
| 2 | Invalid command arguments |
| 130 | User interrupted the operation |

## Quality checks

The benchmark checks every expected phrase from the corpus manifest.
It ignores case, punctuation and whitespace differences.
It rejects empty output, missing phrases and incomplete generation.
It counts HTTP errors and timeouts as failures.

`ocr` applies the same checks to each supplied `--expect` phrase.
Without these phrases, it checks only nonempty text and normal generation completion.
This weaker check does not establish text accuracy.

## Result files

| File | Contents |
|---|---|
| OCR output path | Raw model text, including unsuccessful output |
| OCR output path plus `.json` | Status, latency, input hash, output and error |
| `results.json` | Metadata, warmup and per-request sweep records |
| `summary.md` | Counts, throughput, latency statistics and metadata |

A request has one terminal status.
Statuses are `success`, `error`, `timeout`, `incomplete` and `quality_failed`.
Only `success` contributes to successful pages per second.

Each sweep records input count, successes, failures, timeouts and elapsed seconds.
Latency statistics contain count, minimum, median and maximum.
The report separates all requests from successful requests.
It retains every observed latency and raw output.

Metadata records input hashes, expected phrases and preparation time.
It also records the model revision, serving configuration, image ID and installed packages.
Hardware fields include GPU name, driver version and available memory.
Source fields include the Git commit and working-tree state.

The runner writes results after each completed sweep.
An aborted run retains completed sweeps and reports `status: aborted`.
In-flight requests do not become completed observations.

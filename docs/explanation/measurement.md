# Measurement method

Kind: explanation.

Each new benchmark output directory contains `results.json` and `summary.md`.
The client warms every corpus page before measurement.
It records these requests separately and requires each request to pass.
This primes the default multimodal cache before the first sweep.
The results describe warm-cache behavior. Prefix caching remains disabled.
Each sweep consumes the same corpus once, using at most N active requests,
no retries, a 120-second absolute request deadline and an eight-connection pool.
Use `--concurrency 1 2` for a smaller explicitly recorded resource-limited run.

Results include successful completions, failures/timeouts, elapsed time,
successful pages/s, min/median/max latency for all requests and successful
requests separately, and every raw latency/output/error. Metadata includes
input hashes/expectations, preparation time, model/configuration, container
and image IDs, installed serving packages, GPU/driver/free memory, Python/OS,
source commit/dirty state and timestamps. Completed sweeps are saved as they
finish. Interrupted in-flight requests are not completed observations.

This is a finite **closed-loop smoke/performance demo**, not an open-loop
saturation experiment, general OCR quality benchmark or production SLO proof.
Eight pages cannot support persuasive tail percentiles. Preparation, warmup,
startup and report writes are excluded from sweep throughput; request latency
starts when a worker submits a page and includes HTTP handling and output
validation. It excludes waiting for a worker. Timeouts are censored; their
recorded duration is not the server's eventual completion latency.


# Run the shared-capacity experiment

Kind: how-to.

This procedure compares urgent and bulk document requests on one backend.
Read the [method](../explanation/shared-capacity-method.md) before a run.
Use Python 3.12 and the pinned serving profile.
The default matrix contains twelve five-minute arrival windows.
Warmup, server startup and drain add time to that one-hour measurement minimum.

## Prepare without a GPU

1. Install the locked dependencies.

   ```sh
   uv sync --locked --group docs --group data
   ```

2. Prepare the existing coverage corpus if it is absent.

   ```sh
   uv run --group data python scripts/prepare_scaling.py --output corpus/cord-scaling-56
   ```

3. Run the [repository checks](check-quality.md).

4. Freeze the experiment in a new directory.

   ```sh
   uv run python scripts/shared_capacity_suite.py prepare \
     --input corpus/cord-scaling-56 --output runs/shared-capacity-4090
   ```

The preparation command sends no inference requests.
It freezes the five-second urgent deadline before either baseline or mixed results exist.
It saves the corpus manifest, condition order, trace and executable hashes.
It also copies the executable source and lockfile.
Both mixed policies use identical document assignments and scheduled arrivals.
Rows 80–99 stay reserved.
Receipt 71 stays in both consumer classes.

## Run after service approval

Obtain explicit approval before interrupting an existing GPU service.
The `--release-llama` flag records that authorization; the flag does not obtain it.
The suite uses the existing ownership and free-memory checks.
It stops the configured llama.cpp service only during the approved handover.
It restores the prior service and loaded model IDs after success or failure.

1. Execute the frozen matrix after approval.

   ```sh
   uv run python scripts/shared_capacity_suite.py run \
     --output runs/shared-capacity-4090 --release-llama
   ```

2. Inspect `runs/shared-capacity-4090/lifecycle.json` for restoration evidence.

3. Inspect `runs/shared-capacity-4090/gpu-test.json` for the real GPU check.

4. Inspect each condition's `result.json` before comparing policies.

The suite establishes isolated baselines first.
It alternates the isolated condition order across three repetitions.
It then runs three paired mixed trials and alternates their policy order.
Each condition restarts only the owned parser and warms all inputs.
Warmup does not enter measured latency or throughput.
An urgent deadline miss does not cancel an active backend request.
A transport timeout makes backend execution uncertain.
The runner then stops new dispatch and records the remaining work.
It does not reuse uncertain capacity inside that condition.
The next condition starts with a new owned parser.

## Preserve failures and reproduce scores

Generate the per-trial scores and paired policy comparison without inference.

```sh
uv run python scripts/report_shared_capacity.py \
  --input runs/shared-capacity-4090 \
  --output runs/shared-capacity-4090/report.json
```

Use a new output filename when rescoring.
The report includes unmeasured, partial and ineligible trials.
It refuses policy comparisons when the paired controls differ.
Its deltas subtract FIFO from reserved capacity.
An unknown bulk completion time stays unknown in the comparison.

To score one arm, run this command with a new report filename.

```sh
uv run python scripts/score_shared_capacity.py \
  --input runs/shared-capacity-4090/fifo-0 \
  --output runs/shared-capacity-4090/fifo-0/scores.json
```

Keep the complete run directory after a failure or interruption.
Do not replay an attempted condition in place.
Prepare a new directory when executable source changes.
Treat partial or backend-uncertain conditions as incomplete evidence.
Do not compare their throughput as sustained capacity.

Retain `protocol.json`, each `plan.json`, `trace.json`, raw terminal records,
policy decisions, warmup records, telemetry and server logs.
Retain the frozen source, runtime identity and lifecycle receipt.
Report missing outcomes explicitly after an interrupted process.
No client timeout proves that backend execution stopped.

The [results reference](../reference/shared-capacity-results.md) records the actual
measurement status and its unresolved limits.

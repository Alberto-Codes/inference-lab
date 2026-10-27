# Run the scaling experiment

Kind: how-to.

Use Python 3.12 and `uv` from the repository root.
Use the pinned image in `serving/config.json`.
See [the service procedure](evaluate-receipts.md) to build that image.
The runner does not change the serving profile.

## Prepare coverage inputs

Create a new corpus directory:

```sh
uv run --group data python scripts/prepare_scaling.py --output corpus/cord-scaling-56
```

The command writes the evaluation reservation before it downloads the source.
It saves original embedded image bytes and annotations for CORD test rows 24–79.
It does not extract rows 80–99.
Keep those rows untouched until the correction method and evaluation protocol are frozen.
Rows 0–23 remain the published pilot.
Do not modify the `v0.1.0` tag or its evidence.

Create a disjoint synthetic warmup image:

```sh
uv run inference-axi corpus --output corpus/scaling-warmup
```

## Run the local matrix

Obtain permission before stopping an existing GPU service.
Use this command only when that handover is authorized:

```sh
uv run python scripts/scaling_suite.py \
  --input corpus/cord-scaling-56 \
  --output runs/scaling-matrix \
  --warmup-image corpus/scaling-warmup/page-01.png \
  --release-llama
```

The context manager restores the previous llama.cpp service state and loaded model IDs.
It records restoration in `lifecycle.json`.
It removes only the parser container owned by this checkout.
Without `--release-llama`, start the parser yourself before running the suite.
The suite restarts that owned parser between fresh-input trials.
It does not restore a caller-managed parser's initial cache contents.

The default matrix uses 2, 4, 6, 8 and 12 offered pages/s.
Each condition runs three times with 60 seconds of arrivals.
Each request has a 30-second deadline from its scheduled arrival.
Sixteen workers and 64 waiting slots bound the client backlog.
The rate order rotates between repetitions.
Each repetition also includes a fresh-input trial of all 56 documents at 4 pages/s.
A parser restart clears the previous image cache before that trial.
Its warmup uses the separate synthetic image.
Repeated-input trials warm all 56 receipts before measurement.

Inspect `summaries.json` after the suite finishes.
Inspect `runtime.json`, `runtime-fresh-*.json`, server logs and per-condition telemetry.
Select a rate near the observed stable limit for a longer run.
For example, replace `4` below with the evidence-supported rate:

```sh
uv run python scripts/scaling_suite.py \
  --input corpus/cord-scaling-56 \
  --output runs/scaling-stability \
  --warmup-image corpus/scaling-warmup/page-01.png \
  --stability-rate 4 --stability-seconds 300 \
  --release-llama
```

## Run or resume one condition

Start the owned parser using the existing service procedure.
Run a single condition:

```sh
uv run python scripts/scaling_experiment.py \
  --input corpus/cord-scaling-56 --output runs/scaling-one \
  --rate 6 --count 360 --concurrency 16 --queue 64 --timeout 30
```

Resume it with the same arguments and `--resume`:

```sh
uv run python scripts/scaling_experiment.py \
  --input corpus/cord-scaling-56 --output runs/scaling-one \
  --rate 6 --count 360 --concurrency 16 --queue 64 --timeout 30 --resume
```

Resume keeps completed records unchanged.
It also preserves interrupted warmup attempts before starting a new warmup phase.
It marks orphaned attempts as `interrupted` with an unknown server outcome.
It schedules only requests that have no durable intent record.
It does not retry unknown or failed attempts.
It excludes resumed timing from capacity estimates.
Use a new output directory for an uninterrupted capacity trial.
The runner refuses changed manifests, settings, serving profiles or request code on resume.
An advisory file lock prevents two runners from writing to the same run.

For `--cache fresh`, supply `--warmup-image` with a disjoint image.
Restart the owned parser before each fresh trial.
Do not repeat documents within that trial.
The standalone runner cannot prove that a caller-managed server cache is empty.
Use the suite when a recorded cache reset is required.

## Rescore without inference

Create a new score file:

```sh
uv run python scripts/score_scaling.py \
  --input runs/scaling-one --output runs/scaling-one/rescore-v2.json
```

The command reads saved terminal records.
It preserves raw output and scores failures with an empty prediction.
It records the metric source hash and the terminal-evidence hash.
Its failure review lists suspected discrepancies for image inspection.
Only successful outputs enter its suspect categories.
`unscored_outcomes` counts rejected, failed, truncated and interrupted requests by status.
Those requests still count against the offered-work quality denominators.
Archived `scores.json` files in `raw-evidence.tar.gz` predate this split.
Their suspect categories also count each missing number of non-success requests.
Rescore an archived run to obtain the separated review without editing its evidence.
It does not declare extra text an error or repair model outputs.

Open the original image named in `plan.json` when reviewing a suspect.
Record the request index and exact expected and observed spans.
Record whether the image confirms an error or exposes an annotation gap.
Keep manual findings in a new review file.
Do not edit terminal evidence.

## Audit formatting and aggregate trials

Compare escaped-percent interpretation without changing the baseline metric:

```sh
uv run --offline python scripts/audit_scaling_format.py \
  --input runs/scaling-matrix/fresh-0/scores.json \
  --output runs/scaling-matrix/fresh-0/format-audit.json
```

This diagnostic interprets only LaTeX `\%` as a percent sign.
It retains both per-request score versions.
It does not repair digits, punctuation or references.

Aggregate completed trial scores and resource samples:

```sh
uv run --offline python scripts/report_scaling.py \
  --input runs/scaling-matrix --output runs/scaling-matrix/report.json
```

The report retains each repetition and its resource observations.
It also gives the minimum, mean and maximum across repetitions.
Those ranges are not confidence intervals.
The command rejects completed score artifacts whose timing is ineligible.
It includes only directories that contain `scores.json`.
Check the suite's `summaries.json` and protocol before claiming the full matrix finished.

## Inspect the saved scaling evidence

Verify the archive hash against `evidence/scaling-4090/archive-index.json`:

```sh
sha256sum evidence/scaling-4090/raw-evidence.tar.gz
```

Create a replay directory:

```sh
mkdir -p runs
mkdir runs/scaling-replay
```

Extract the archive without replacing existing files:

```sh
tar --keep-old-files -xzf evidence/scaling-4090/raw-evidence.tar.gz -C runs/scaling-replay
```

Rescore a saved condition after dependency setup:

```sh
uv run --offline python scripts/score_scaling.py \
  --input runs/scaling-replay/scaling-4090-matrix-v2/r4-0 \
  --output runs/scaling-replay/rescore-r4-0.json
```

The archive includes exact source and lockfile snapshots under each suite's `source/` directory.
Use those snapshots if a future scorer changes the metric implementation.
Images are reproducible from the pinned dataset and hashes; they are not in the archive.
No model weights or GPU are needed to rescore.

Render the saturation figure from the aggregate report:

```sh
uv run scripts/plot_scaling.py \
  --input evidence/scaling-4090/matrix.json \
  --output runs/scaling-replay/curve.svg
```

The plotting script pins its optional Matplotlib dependency.
The first plotting run can download that dependency.

# Experiment index

Kind: reference.

These experiments use Nemotron-3.5-Parse, vLLM and one RTX 4090.
They measure different workloads. Request completion does not establish correct extraction.

## Documentation and experiment versions

The hosted documentation follows validated `main`.
Each immutable experiment tag preserves its code, evidence and documentation snapshot.
Use the tagged instructions below to reproduce a historical experiment.
Current guides can gain corrections and navigation without changing those snapshots.
Detailed results stay on each experiment's results page.

## Shared capacity — measured, unpublished

**Purpose:** measure urgent deadline attainment while a bursty bulk job shares one backend.
**Dataset:** the same 56 coverage receipts, including receipt 71; rows 80–99 remain reserved.
The protocol compares isolated baselines, mixed FIFO and mixed reserved capacity.
It freezes a five-second urgent deadline before measurement.
Three five-minute repetitions per condition use warmed repeated inputs.

- **Status:** twelve trials completed on 2026-10-28; all three mixed pairs are eligible. One isolated bulk trial is ineligible.
- **Design:** [hypotheses, controls and acceptance criteria](../explanation/shared-capacity-method.md).
- **Procedure:** [freeze, run and retain evidence](../how-to/run-shared-capacity.md).
- **Evidence:** [measured tradeoffs and limitations](shared-capacity-results.md).

No new release, experiment tag or companion post is published by this increment.

## v0.1.0 — receipt pilot

**Purpose:** inspect OCR quality and compare two short concurrency sweeps.
**Dataset:** 24 unique CORD receipts, test rows 0–23; 48 measured requests.
The warmed-cache sweeps used concurrency one and four.
The roughly six receipts/s observed at concurrency four is not established sustained capacity.

- **Publication:** [published prerelease](https://github.com/Alberto-Codes/inference-lab/releases/tag/v0.1.0), published 2026-10-27.
- **Companion article:** [I ran Nemotron Parse on a 4090. Then I checked the numbers.](https://alberto.codes/blog/2026-10-26-nemotron-ocr-on-a-4090)
- **Results:** [pilot results and limitations](receipt-results.md).
- **Tagged snapshot:** [code](https://github.com/Alberto-Codes/inference-lab/tree/v0.1.0) and [saved evidence](https://github.com/Alberto-Codes/inference-lab/tree/v0.1.0/evidence/cord-test-24).
- **Historical instructions:** [offline scoring](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/docs/tutorials/first-result.md) and [GPU reproduction](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/docs/how-to/evaluate-receipts.md).

The tag resolves to `1b412ff74cee4b60d07b17d24e41daef4df18335`.
Check out that tag before running commands from its instruction snapshots.

## v0.2.0 — receipt scaling

**Purpose:** separate quality coverage from sustained offered-load measurements.
**Dataset:** 56 new unique CORD receipts, test rows 24–79; 20 reserved evaluation receipts, rows 80–99.
Repeated workloads and fresh-input trials retain 9,228 measured outcomes.
The matrix repeats one-minute arrival windows; the longer trials offer five and six pages/s for five minutes each.
Each longer condition ran once. The fresh-input trials do not establish sustained fresh-document capacity.

- **Publication:** the [immutable tag is public](https://github.com/Alberto-Codes/inference-lab/tree/v0.2.0). The GitHub release remains a draft as verified on 2026-10-27.
- **Companion article:** *I sent my 4090 six receipts a second. The queue kept growing.* It remains a draft; no public article URL is available.
- **Results:** [scaling results and limitations](scaling-results.md) and [failure review](scaling-failures.md).
- **Tagged snapshot:** [code](https://github.com/Alberto-Codes/inference-lab/tree/v0.2.0) and [saved evidence](https://github.com/Alberto-Codes/inference-lab/tree/v0.2.0/evidence/scaling-4090).
- **Historical instructions:** [preparation, GPU runs, resume and offline scoring](https://github.com/Alberto-Codes/inference-lab/blob/v0.2.0/docs/how-to/run-scaling.md).

The tag resolves to `3193fb28d46e875d4f39324d4ba743f058fb872c`.
Check out that tag before running its commands.
The [current scaling guide](../how-to/run-scaling.md) is maintained separately from that snapshot.
Release and article publication still require coordination; this index does not publish either artifact.

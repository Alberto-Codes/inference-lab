# CORD receipt pilot results

Kind: reference.

These are the **v0.1.0 pilot** results.
[Experiment index](experiments.md) ·
[Tagged results snapshot](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/docs/reference/receipt-results.md) ·
[Tagged evidence](https://github.com/Alberto-Codes/inference-lab/tree/v0.1.0/evidence/cord-test-24)

Historical reproduction: [instructions at v0.1.0](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/docs/how-to/evaluate-receipts.md).

## Dataset and scope

Dataset: [NAVER CLOVA CORD-v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2).
Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Attribution: NAVER CLOVA and Park et al., CORD (2019).
Revision: `7f0115a4b758a71d6473b8d085751692da2fef98`.
Selection: test rows 0–23, fixed before inference. These are 24 unique receipt images.
This convenience subset does not establish performance on the full test split.
Source annotations and image hashes are in `evidence/cord-test-24/manifest.json`.
Images remain in the ignored `corpus/cord-test-24/` directory.

## Observations

All 24 warmups and 48 measured requests completed with stop termination.
No request timed out or returned an HTTP error.
Completion success does not establish text correctness.

| Concurrency | Completed | Pages/s | Median latency | ROUGE-L F1 | Exact numeric recall |
|---|---|---|---|---|---|
| 1 | 24/24 | 2.12 | 415 ms | 0.801 | 212/241 (88.0%) |
| 4 | 24/24 | 5.99 | 634 ms | 0.802 | 212/241 (88.0%) |

The throughput timer includes client scoring and evidence writes.
Latency measures HTTP inference and response validation.
The server image cache was warmed for each receipt.
This short closed-loop run does not establish production capacity.

## Scoring limits

CORD annotations cover selected receipt content. They are not complete page transcriptions.
ROUGE-L measures ordered token overlap after formatting removal.
Extra visible text and different reading order can lower the score.
Numeric recall preserves signs and separators. It counts duplicate strings.
It does not verify that a number belongs to the correct field.
There is no arbitrary quality pass threshold.

The initial run retained LaTeX command names during scoring.
The final offline rescore removes table environments and command names.
No OCR requests were repeated for this correction.
`results.json` and `requests.jsonl` retain the initial observations.
`scores.json` contains the corrected scores and source hashes.
Prompts and model settings were not tuned after viewing these samples.

## Failure examples

Receipt 20 contains a reference amount of `79,500`. Nemotron returned `79,300`.
The reference total is `377,859`. Nemotron did not preserve that total.
Image inspection confirms both reference amounts on the visible receipt.
The output also contains unrelated prose around the receipt content.

Receipt 13 contains several separator changes, including `43.636` to `43,636`.
Exact numeric matching counts these as mismatches.
Locale-aware equivalence requires a separate, explicit rule.

## Local model review

The recorded Judgevet review assessed the three lowest-overlap receipts.
Its path is [Judgevet](https://github.com/Alberto-Codes/judgevet) →
[Typevet](https://github.com/Alberto-Codes/typevet) → Gemma on local llama.cpp.
The resolved model was `gemma-4-31b-kv9-text`.
The configured versions are Judgevet 0.23.0 and Typevet 0.11.0.
The rubric has four ordered levels, from multiple numeric errors to exact preservation.
Signs, digits, separators and percent signs must match under this rubric.

| Receipt | Expected rubric index | Dominant judgment | Observation |
|---|---|---|---|
| 20 | 0.225 of 3 | Multiple numeric errors | Consistent with the changed amount and damaged total. |
| 22 | 3.000 of 3 | Exact numeric preservation | All seven annotated numeric tokens were present. |
| 13 | 2.496 of 3 | Nearly split between separator errors and exact preservation | The judge remains uncertain despite the explicit rule. |

These values are expected rubric indices. They are not accuracy percentages or ROUGE scores.
The model assigned 50.2% to exact preservation and 49.4% to separator differences for receipt 13.
Deterministic matching establishes the separator differences directly.
Judge probabilities are advisory and are not calibrated on this receipt set.
The review had text only and could not verify the source image.
Prompts, states and complete answers are in `judgevet-review.json`.

An earlier direct chat review remains in `local-review.json` for audit.
It used direct chat and claimed all receipt 13 numbers matched.
The configured Judgevet review supersedes that route for this experiment.

See [optional model review](../how-to/review-with-a-model.md) to configure your own judge.

## Validation at the recorded run

Offline checks passed: Ruff, lock validation, package build and 35 tests.
One additional live GPU test passed before the receipt requests.

## Evidence

All paths below are relative to `evidence/cord-test-24/`.

- [manifest.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/manifest.json): dataset provenance, image hashes and source annotations.
- [requests.jsonl](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/requests.jsonl): all 72 terminal request records.
- [results.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/results.json): run settings, timing and initial score calculation.
- [scores.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/scores.json): final normalized scores and raw text.
- [judgevet-review.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/judgevet-review.json): three reviews through the configured Judgevet integration.
- [local-review.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/local-review.json): earlier direct chat observations, retained for audit.
- [lifecycle.json](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/lifecycle.json): service shutdown and restoration evidence.
- [server.log](https://github.com/Alberto-Codes/inference-lab/blob/v0.1.0/evidence/cord-test-24/server.log): Nemotron server log.

See [scoring explanation](../explanation/receipt-evaluation.md) for interpretation.

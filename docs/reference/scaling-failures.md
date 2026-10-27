# Scaling failure review

Kind: reference.

These findings use CORD test rows 24–79 at the pinned revision.
Images remain in `corpus/cord-scaling-56/`.
The corpus manifest records original image hashes and source annotations.
No output was repaired.
No model judge supplied ground truth.
The visual checks below are direct Codex image inspections.
They have not received independent human adjudication.
`evidence/scaling-4090/visual-review.json` records source-image and response hashes.

## Initial image checks

The first exploration saved 56 fresh-input requests in
`runs/scaling-4090-20261027/fresh-0/`.
Its parent matrix stopped during warmup because the first harness rejected truncations.
That run remains separate from the final matrix.
The table below identifies its immutable terminal records.
A request index equals the CORD row ID minus 24.

| CORD row | Request index | Category | Evidence | Assessment |
|---|---|---|---|---|
| 32 | 8 | Separator change | The image shows `24.000`, `50.000` and `26.000`. The output uses commas for subtotal, cash and change. | Verified punctuation mismatch; numeric equivalence needs an explicit locale rule. |
| 49 | 25 | Changed digit | The image shows `CASH 50,000`. The output says `CASH30,000`. | Verified image error. |
| 66 | 42 | Changed digit | The image total is `40,000`. The output total is `40,800`. | Verified image error. |
| 71 | 47 | Unrelated generation and omission | The image contains `Cuka Apel Tetes 1`, `198000` and other amounts. The output repeats `ଛ` and ends with `finish_reason=length`. | Verified failure to transcribe visible content. |
| 49 | 25 | Unrelated generated text | The output adds an English browser-comment sentence and repeated `Apple Watch` text. The visible receipt does not contain that text. | Verified for visible content. The source already blurs some regions. |
| 53 | 29 | Annotation error | The annotation says `Servi Charge 57`. The image shows `Servi Charge 5%`. | Verified label discrepancy. Do not count the annotated `57` as reliable OCR truth. |
| 53 | 29 | Annotation gap | The image displays the `Kopi Legit` brand. The partial reference does not include it. | Extra brand text alone is not hallucination. |

The reviewed digit changes on rows 49 and 66 recur in all three final-matrix fresh trials.
The separator changes on row 32 also recur in all three.
Row 71 truncates in each fresh trial.
`evidence/scaling-4090/recurrence.json` records those response and image hashes.

The blurred source regions do not support claims about the original hidden text.
The report evaluates only visible evidence.
The strange arithmetic on receipt 71 is not repaired or inferred from other fields.

## Automated suspects

The offline review groups missing annotated numeric strings into two broad queues.
One queue contains possible separator or sign changes.
The other contains possible omissions or changed digits.
These are review queues, not confirmed counts of OCR errors.
A number elsewhere on the page can match by coincidence.
Repeated requests increase occurrence counts without increasing unique reviewed documents.

Some apparent separator mismatches come from model formatting.
For example, receipt 31 emits `6\%` in LaTeX.
The existing normalizer leaves the escape before the percent sign.
Its numeric matcher therefore reports `6%` as missing.
The original pilot metric implementation remains unchanged.
A separate offline audit quantifies this artifact without modifying the baseline normalizer.
For final-matrix `fresh-0`, interpreting only LaTeX escaped percent signs changes matches from 511 to 524 of 635.
Six requests change. The 13 additional matches are formatting interpretations, not corrected model predictions.
The audit is in `evidence/scaling-4090/format-audit-fresh-0.json`.
Do not call a formatting cleanup a correction to the model's extracted value.

Some outputs join labels and numbers without spaces.
Receipt 27 combines a field label ending in `5` with `61,600`.
The numeric tokenizer can then see a different string.
Image inspection and field association are required to distinguish joining from digit recognition errors.
The present metrics do not evaluate field association.

## Next correction experiment

The escaped-percent audit is complete for the first final-matrix fresh trial.
Extend that audit across the saved trials before choosing a new canonical normalizer.
Retain both scores and source hashes.
This needs no GPU and does not change raw model outputs.

In the first two final-matrix fresh trials, receipt 71 returns 8,744 output tokens each time.
That is 49.2% and 49.0% of all returned output tokens in those trials.
Output-token share is not GPU-time share.
A lower token cap would limit waste but would not fix the missing transcription.

Then test a targeted image-region extraction hypothesis on the coverage set.
The recurring pattern is plausible receipt text mixed with unrelated generation around blurred or difficult regions.
A region-based second pass may reduce that output, but this has not been established.
Compare the fixed full-page prompt with explicit, human-verified text-region crops.
Keep the model, serving profile and source images fixed.
Count changed digits, omitted fields, unrelated output, truncation and added inference cost separately.
Do not use arithmetic to silently replace uncertain values.
Do not automatically accept cropped output without a defined verification rule.

Freeze the rule and its thresholds before opening reserved rows 80–99.
Use those untouched rows for the final evaluation once.
A useful correction must improve verified field accuracy without hiding coverage loss or added latency.
Automatic correction and GEPA optimization remain deferred.

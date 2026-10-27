# Blog MVP scope

Kind: explanation.

## Purpose

Show a reproducible local OCR experiment and explain what its results mean.
The audience is developers who want to try document inference on one GPU.
This audience is an assumption for this draft.
The user described this project as an MVP for a blog.
The next deliverable should help a reader understand and reproduce the experiment.

## Existing evidence

The project serves Nemotron through vLLM on one RTX 4090.
A synthetic corpus verified serving and concurrency behavior.
A fixed subset of 24 CORD test receipts added real document evidence.
All 48 measured receipt requests completed.
Concurrency 1 reached 2.12 pages per second; concurrency 4 reached 5.99.
These short measurements used warmed image caches.
Throughput includes client scoring and evidence writes.
Each concurrency level had one measured sweep.
Diagnostic ROUGE-L F1 was 0.801 at concurrency 1.
Exact numeric-string recall was 212/241, or 88.0%.
CORD annotations cover selected content, not every visible word.
Numeric presence does not establish correct field association.

Receipt 20 shows a changed amount: 79,500 became 79,300.
Its total was also damaged. Image inspection confirmed the reference amounts.
Judgevet, Typevet and local Gemma reviewed three difficult cases.
The judge detected one damaged receipt but remained uncertain about exact separator matching.
These observations support an experiment report, not a general accuracy claim.

Sources: [receipt results](../reference/receipt-results.md),
[evaluation procedure](../how-to/evaluate-receipts.md), and
[evaluation design](receipt-evaluation.md).

## Working recommendation

Build the article around this question: does a successful OCR request preserve the numbers?
Keep concurrency as a secondary observation.
Show the image, reference and Nemotron output for receipts 20, 22 and 13.
These were the three lowest-overlap cases selected for the existing judge review.
Receipt 20 shows changed digits. Receipt 13 shows separator differences.
Receipt 22 preserves all seven annotated numeric strings, despite unrelated output text.
Do not describe receipt 22 as a clean transcription.
State the selection rule and sample IDs beside each example.
Do not imply that three examples represent the whole test split.

Use deterministic metrics for the measured comparison.
Use the Judgevet review to illustrate what a second model can and cannot establish.
Avoid averaging judge probabilities into an accuracy figure.

## Candidate next work

| Option | Reader benefit | Cost and limitation | Draft decision |
|---|---|---|---|
| Article plus three annotated examples | Explains the actual result and its limits | Uses existing evidence; needs visual checks and attribution | First |
| One documented reproduction path | Lets readers rerun the pilot | Existing scripts need output-path alignment and environment details | Required before publishing |
| Evaluate all 100 CORD test receipts | Improves coverage of this dataset | Another run; still partial labels and one dataset | Optional follow-up |
| Crop blurred receipt areas and compare | Tests a possible cause of unrelated output | Changes inputs; needs a fixed paired experiment | Separate follow-up hypothesis |
| Add another model, dataset or cloud host | Broadens comparison | Expands setup and claims before the first article exists | Defer |

The article should report observed errors before proposing fixes.
Do not promise that cropping or a different prompt will improve results.
Do not describe 88.0% numeric recall as financial accuracy.

## Minimum completion criteria

A reader can follow one tutorial from prerequisites to saved scores.
The tutorial identifies the GPU, software pins and dataset revision.
It uses a fresh output directory and keeps original evidence intact.
It explains how to restore an existing GPU service after the run.
The article includes one compact result table and three image comparisons.
Each displayed image has dataset attribution and a sample identifier.
Each headline claim links to saved evidence.
The article separates measured scores from subjective judge output.
Publication is a separate action from preparing the draft.

## Review request

Use fresh-context Goldfish reviewers for scope and evidence quality.
Challenge whether any proposed work is unnecessary for this blog MVP.
Identify the smallest useful next deliverable and a clear stopping point.
This is a bounded adaptation of Elephant–Goldfish, not its complete staged workflow.
Upstream source: https://github.com/google/elephant-goldfish-model

## Proposed article outline

Working title: I ran Nemotron OCR on a 4090. Then I checked the numbers.

1. Open with receipt 20 and the changed amount.
2. Show the local setup and the request path.
3. Explain the fixed receipt subset and reference limitations.
4. Present completion, numeric recall and diagnostic overlap as distinct observations.
5. Show what the configured Judgevet review added, including its uncertain case.
6. Link the reproduction tutorial and state the remaining questions.

A short concurrency table can follow the setup or appear in a sidebar.
Do not lead with throughput or describe this as a financial-document benchmark.
The data consists of retail receipts.

## Reproduction gap found during planning

The runner, scorer and review script use separate hard-coded evidence paths.
The current procedure asks readers to edit source files before a new run.
A blog reader could run new inference but accidentally score the saved pilot.
Give these commands one explicit run-directory argument before publication.
Keep this as a small interface correction, not a new orchestration framework.
The first article should make the Judgevet stage optional.
A reader should be able to inspect saved scores without loading Gemma.

## Goldfish review outcome

Two reviewers received fresh contexts without the conversation history.
The scope reviewer used the skeptical-architect persona.
The evidence reviewer used the design-critic persona.
Both recommended an article draft using the existing observations.
Neither required another GPU run to support the proposed story.

Their findings changed this plan in four ways:

- Draft the article before improving the reproduction interface.
- Replace the vague clean-example claim with precise numeric-preservation captions.
- Keep the judge pipeline as one optional sidebar, not three independent reviewers.
- Repair the run-directory mismatch before publication.

The evidence reviewer checked the saved metrics and the request-file hash.
The reviewers did not validate a new reproduction procedure or inspect every source image.
Those actions remain work for preparing the article.

## Recommended work order

1. Draft an unpublished article with the existing table and three comparisons.
2. Inspect the displayed source images and add precise captions and attribution.
3. Align run-directory arguments in the runner and scorer.
4. Write one receipt-specific reproduction path using those arguments.
5. Check evidence links, offline rescoring and failure-cleanup instructions.

The receipt tutorial should not require the synthetic sweep or local judge model.
Provide bounded loaded-model verification after restoring llama.cpp.
Keep overwrite protection and preserve historical evidence.
Validate interface changes at their boundary.
Only rerun GPU measurements if changes affect inference or timing behavior.

Stop when the draft is reviewable and every claim resolves to saved evidence.
Complete the small reproduction repair before publication.
Defer the full test split, cropping, additional models and cloud hosting.
This turn produced the scoped plan. It did not implement that follow-up work.

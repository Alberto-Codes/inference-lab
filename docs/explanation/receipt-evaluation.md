# How receipt evaluation works

Kind: explanation.

## Scope and references

The pilot evaluates Nemotron on CORD-v2 test rows 0 through 23.
The [NAVER dataset](https://huggingface.co/datasets/naver-clova-ix/cord-v2)
is pinned at revision `7f0115a4b758a71d6473b8d085751692da2fef98`.
Saved evidence includes image hashes, original labels, sample IDs, model settings and raw outputs.
The pilot uses one fixed prompt for all samples.
CORD annotations use CC BY 4.0. Credit belongs to NAVER CLOVA and the CORD authors.

CORD `valid_line` annotations cover selected receipt content.
They do not provide a complete transcription of every visible word.
Reference text follows the annotation order.
Extra visible text can reduce precision without being a parsing error.
Annotation order can differ from page reading order.
These scores are diagnostic comparisons, not official CORD benchmark results.
They do not evaluate layout, table structure or financial field association.

## Text overlap

Scoring removes Nemotron coordinate and class tokens, HTML tags and LaTeX layout syntax.
Tokenization uses Unicode letters and numeric strings with signs and internal punctuation.
Tokens are case-folded. Stemming is disabled.
The source regular expression defines the exact token boundaries.

ROUGE-L uses the longest common token subsequence.
Precision divides overlap by prediction length. Recall divides overlap by reference length.
F1 equals twice the overlap divided by the combined token count.
The report averages page F1 values.
An empty prediction receives zero when its reference is nonempty.
The per-page metric returns null F1 and recall for an empty reference.
The pilot references are all nonempty.

## Numeric-string recall

Numeric matching preserves signs, decimal separators and thousands separators exactly.
It checks string presence, not association with the correct receipt field.
A multiset intersection counts repeated values up to their frequency in the reference.
The aggregate divides total matched numbers by total reference numbers.
Pages without reference numbers have null per-page numeric recall.
Each page report lists missing numeric strings.

For example, `79,300` does not match the reference `79,500`.
A completed request can therefore fail to preserve an amount.
No quality pass threshold is defined for this pilot.

## Request status and execution bounds

Preparation finishes before inference starts.
Each image receives a separate warmup request.
The run then measures concurrency one and four separately.
The full run contains 24 warmups and 48 measured requests, with no retries.
Each request has a 120-second deadline.
Any failed warmup stops measured work.
Each terminal record is flushed to JSONL immediately.
Incomplete reports retain the planned count, completed records and run status.
The missing phase/sample pairs identify unattempted requests.
The offline scorer refuses a complete-run summary if requests are missing or duplicated.

Only successful, stop-terminated outputs receive their observed text during scoring.
Every other status receives an empty scoring prediction.
Raw text remains available, and failed pages remain in the scoring denominators.
Transport completion, truncation, empty output and text quality remain separate observations.
Low overlap does not change completion status.
Concurrency one provides the primary quality observation.
Concurrency four is reported separately.

The server requires enough free GPU memory before startup.
Container cleanup applies only to the demo's labelled container.
A fresh run does not require an existing model service.
See the [GPU procedure](../how-to/evaluate-receipts.md) for setup and execution.

## Optional model-assisted review

The pilot also reviewed the three receipts with the lowest overlap scores.
[Judgevet](https://github.com/Alberto-Codes/judgevet) applies a review rubric.
[Typevet](https://github.com/Alberto-Codes/typevet) connects that review to Gemma.
The saved prompts, answers and probabilities are advisory diagnostics.
They do not replace deterministic scores or establish extraction accuracy.
Scoring saved responses does not require either integration.

## Historical formatting correction

The initial scorer counted LaTeX formatting commands as text.
Offline rescoring removes table environments, command names and multicolumn layout arguments.
A regression test prevents layout column counts from matching receipt numbers.
The original request records remain unchanged.

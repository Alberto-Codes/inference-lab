# Receipt evaluation design

Kind: explanation.

## Scope

Evaluate Nemotron on CORD-v2 test rows 0 through 23.
Use the public NAVER dataset at revision 7f0115a4b758a71d6473b8d085751692da2fef98.
Record image hashes, original labels, sample IDs, model settings and raw outputs.
Do not tune prompts on these samples.

## Measures

CORD valid_line annotations cover selected receipt content.
They do not provide a complete transcription of every visible word.
Build reference text from valid_line words in annotation order.
Keep numeric punctuation and signs.
Remove Nemotron coordinate and class tokens before scoring.
Compute token ROUGE-L precision, recall and F1 without stemming.
Treat these as diagnostic overlap scores, not official CORD benchmark results.
Extra visible text can reduce precision without being an OCR error.
Annotation order can differ from page reading order.
Also measure multiset recall of numeric strings from annotated words.
Preserve minus signs, decimal separators and thousands separators exactly.
This measure checks string presence, not association with the correct receipt field.
Report missing numeric strings for each page.
Separate transport completion, truncation, empty output and text quality.
Keep failed pages in denominators with empty predictions.
Do not invent a quality pass threshold.

## Execution

Prepare all inputs before stopping llama.cpp.
Record its loaded model before shutdown.
Warm each image separately, then measure concurrency 1 and 4.
Save every warmup and measured request.
Score concurrency 1 as the primary quality observation.
Report concurrency 4 separately.
Restore llama.cpp and its previous model in a finally block.
A local model may review the three lowest overlap scores after restoration.
Save its prompt and answers as subjective diagnostics, separate from measured scores.
Use the configured judgevet-gemma MCP service through Typevet and local Gemma.

## Design review

Apply the Elephant–Goldfish pattern with a zero-history, read-only reviewer.
Resolve concrete findings before implementation.
The user authorized implementation and temporary llama.cpp shutdown.
Use this bounded design stage before leaving the design workflow for implementation.

Source: https://github.com/google/elephant-goldfish-model
Dataset: https://huggingface.co/datasets/naver-clova-ix/cord-v2
Licence: CC BY 4.0. Attribute NAVER CLOVA and the CORD authors.

## Resolved review findings

The isolated reviewer identified four gaps before implementation.
The fixes define restoration verification, scoring, failure handling and execution bounds.

Tokenization uses Unicode letters and numeric strings with signs and internal punctuation.
Tokens are case-folded. Stemming is disabled.
The source regular expression defines the exact token boundaries.
ROUGE-L uses the longest common token subsequence.
Precision divides overlap by prediction length. Recall divides overlap by reference length.
F1 equals twice the overlap divided by the combined token count.
The report averages page F1 values. Empty references produce null F1 and recall.
Empty predictions receive zero when the reference is nonempty.
Numeric recall uses Counter intersection, including duplicate values.
The aggregate divides total matched numbers by total reference numbers.
Pages without reference numbers have null numeric recall.

Only successful, stop-terminated outputs receive their observed text during scoring.
Every other status receives an empty scoring prediction. Raw text remains available.
Low overlap does not change completion status.

The run contains 24 warmups and 48 measured requests, with no retries.
Each request has a 120-second deadline.
Any failed warmup stops measured work.
Each terminal record is flushed to JSONL immediately.
Incomplete reports retain the planned count, completed records and run status.
The missing phase/sample pairs identify unattempted requests.

Cleanup removes only the owned demo container before restoring llama.cpp.
Restoration checks router health and each previously loaded model ID.
Experiment errors and restoration errors are recorded separately.
Startup waits are bounded by the existing 300-second serving deadline.
Model restoration has a 180-second HTTP deadline per model.
Forced termination can bypass cleanup. The run-demo recovery commands remain applicable.

This was one bounded design critique, not the full five-stage EGM review pipeline.
The upstream revision was db8149d7d7fdb7dff1813da5ff026a855c7ff6ec.
Implementation began after review findings were resolved.

## Formatting correction

The initial scorer counted LaTeX formatting commands as text.
Offline rescoring removes table environments, command names and multicolumn layout arguments.
A regression test prevents layout column counts from matching receipt numbers.
The original request records remain unchanged.

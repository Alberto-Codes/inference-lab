# inference-lab

Nemotron-3.5-Parse is a document parser.
This repository runs it locally through vLLM and records what it returns.
The first public pilot uses 24 real CORD receipts on one RTX 4090.

All 48 measured requests completed.
One receipt amount changed from `79,500` to `79,300`.
Completion and correct extraction are different observations.

| Start here | Purpose |
|---|---|
| [Inspect the saved experiment](tutorials/first-result.md) | Recalculate scores without a GPU. |
| [Evaluate receipts](how-to/evaluate-receipts.md) | Prepare inputs and run the local parser. |
| [Receipt results](reference/receipt-results.md) | Read measurements and concrete failure cases. |
| [Scoring reference](reference/receipts.md) | Understand what the scores measure. |
| [Experiment release](releases/v0.1.0.md) | Follow the first tag and companion-post preparation. |

The current evaluation checks extracted text and numeric strings.
It does not evaluate layout or table-structure accuracy.
Judgevet → Typevet → Gemma provides a separate optional text review.
Its probabilities do not replace measured comparisons.

Pages shows documentation from validated main.
Experiment tags and release notes identify fixed code and evidence.
[Browse the repository](https://github.com/Alberto-Codes/inference-lab).

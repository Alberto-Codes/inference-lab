---
hide:
  - toc
---

<div class="lab-intro" markdown>
<p class="lab-kicker">One GPU · Real receipts · Saved evidence</p>

# Local document parsing, with measured results

<p class="lab-lead">Run NVIDIA Nemotron-3.5-Parse on receipt images, save its output, and check the extracted text and numbers.</p>

This small experiment uses 24 CORD receipts and one RTX 4090.
**How fast? About 2 receipts per second when sent one at a time, or 6 per second with four in progress at once.**
That is almost three times as many receipts processed in the same time.
The typical receipt took about **0.4 seconds** on its own and **0.6 seconds** when sharing the GPU.
These are warmed-up test results; startup is excluded, and fast output can still contain wrong amounts.

Start with the saved results, or run the parser on your own GPU.

<div class="lab-actions" markdown>
[Inspect saved results](tutorials/first-result.md){ .md-button .md-button--primary }
[Run on your GPU](how-to/evaluate-receipts.md){ .md-button }
</div>
</div>

## What runs locally

<ol class="lab-pipeline">
<li><span class="lab-step">STEP 1</span><strong>Receipt images</strong><p>Download the fixed 24-image corpus. Verify its annotations and hashes.</p></li>
<li><span class="lab-step">STEP 2</span><strong>Nemotron Parse</strong><p>Send each image to the parser, served locally through vLLM.</p></li>
<li><span class="lab-step">STEP 3</span><strong>Saved outputs</strong><p>Keep raw text, completion status and request timing.</p></li>
<li><span class="lab-step">STEP 4</span><strong>Compare text and numbers</strong><p>Score saved output against the annotated reference. This step needs no GPU.</p></li>
</ol>

<div class="lab-optional" markdown>
**Optional second-model review:** [Judgevet → Typevet → Gemma](how-to/review-with-a-model.md)
can review the saved text and reference. Its judgments are advisory and stay separate from measured scores.
</div>

Nemotron Parse returns text, layout markers and table structure.
This experiment evaluates **extracted text and numeric strings**, not layout or table-structure accuracy.

## What the experiment found

<div class="lab-observation" markdown>
**All 48 measured requests completed. One amount still changed.**

The receipt says **79,500**. The parser returned **79,300**.
Request completion does not establish correct extraction.
</div>

| Concurrent requests | Completed | Throughput | Median latency | Exact numeric matches |
|---|---|---|---|---|
| 1 | 24/24 | 2.12 pages/s | 415 ms | 212/241 (88.0%) |
| 4 | 24/24 | 5.99 pages/s | 634 ms | 212/241 (88.0%) |

**Throughput** means how many receipts finish each second across all requests.
**Median latency** is the middle receipt's response time: half finished faster and half slower.
Handling four at once increased the total processing rate, but each receipt typically waited a little longer.

These are two short sweeps over the same **24 unique receipts** on one RTX 4090.
The image cache was warmed. Throughput includes scoring and evidence writes.
More concurrency increased throughput and median latency; numeric recall stayed the same.

CORD annotates selected content, not every visible word.
Numeric presence does not establish correct field association.
These observations do not establish general financial accuracy or production capacity.

[Read the measured results and failure cases](reference/receipt-results.md) ·
[Understand the scoring rules](reference/receipts.md)

## Choose your next step

- **No GPU:** [recalculate the saved scores](tutorials/first-result.md). Initial package installation needs network access.
- **NVIDIA GPU:** [install the prerequisites and run the receipt experiment](how-to/evaluate-receipts.md).
- **Comparing outputs:** [read the raw evidence](reference/receipt-results.md#evidence) before drawing conclusions from a score.

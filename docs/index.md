---
hide:
  - toc
---

<div class="lab-intro" markdown>
<p class="lab-kicker">One GPU · Tagged experiments · Saved evidence</p>

# Local document parsing, with measured results

<p class="lab-lead">Inspect what NVIDIA Nemotron-3.5-Parse extracts from receipts, then measure how the workload behaves on one RTX 4090.</p>

Choose an experiment before comparing its results.
The **v0.1.0 receipt pilot** checks 24 receipts in short concurrency sweeps.
The **v0.2.0 scaling experiment** adds 56 coverage receipts and sustained offered-load trials.
Repeating inputs adds load, not new quality coverage.

<div class="lab-actions" markdown>
[Choose an experiment](reference/experiments.md){ .md-button .md-button--primary }
[Inspect the pilot without a GPU](tutorials/first-result.md){ .md-button }
</div>
</div>

## Two different questions

| Experiment | Question | Read next |
|---|---|---|
| v0.1.0 · Receipt pilot | What text and numeric errors appear, and how do two short concurrency sweeps compare? | [Pilot results](reference/receipt-results.md) |
| v0.2.0 · Receipt scaling | What happens to queues, latency and failures when arrivals continue under load? | [Scaling results](reference/scaling-results.md) |

The pilot's roughly six receipts/s is a short warmed-cache observation, not a sustained-capacity claim.
The scaling experiment measures sustained repeated-input load and reports its remaining quality failures.
Neither experiment establishes correct financial extraction or production reliability.

## Follow the evidence

<ol class="lab-pipeline">
<li><span class="lab-step">STEP 1</span><strong>Choose a tagged experiment</strong><p>Find its purpose, dataset, article and historical instructions in the experiment index.</p></li>
<li><span class="lab-step">STEP 2</span><strong>Inspect saved outputs</strong><p>Read raw responses, completion status and timing from that experiment's evidence.</p></li>
<li><span class="lab-step">STEP 3</span><strong>Rescore offline</strong><p>Compare text and numeric strings with partial CORD annotations. This step needs no GPU.</p></li>
<li><span class="lab-step">STEP 4</span><strong>Review failures</strong><p>Distinguish request failures, verified OCR errors, suspects and annotation gaps.</p></li>
</ol>

These experiments evaluate extracted text and numeric strings, not layout or table-structure accuracy.
A completed request can still contain wrong amounts.

## Choose your next step

- [Experiment index](reference/experiments.md): release states, companion articles, exact evidence and instructions.
- [Current pilot guide](how-to/evaluate-receipts.md): run the 24-receipt procedure.
- [Current scaling guide](how-to/run-scaling.md): prepare coverage inputs, measure load, resume and rescore.
- [Scoring rules](reference/receipts.md): understand what the diagnostic scores can establish.

<div class="lab-optional" markdown>
**Optional model review:** [Judgevet → Typevet → Gemma](how-to/review-with-a-model.md)
provides advisory judgments. They stay separate from measured scores and verified image findings.
</div>

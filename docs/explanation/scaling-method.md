# Scaling measurement method

Kind: explanation.

The scaling runner extends the receipt pilot without changing its archived evidence.
It separates two questions.
Coverage asks which errors appear across more unique documents.
Capacity asks how a fixed workload behaves under sustained offered load.
Repeating a document increases load, but does not increase quality coverage.

## Coverage and reservation

CORD-v2 remains pinned at revision `7f0115a4b758a71d6473b8d085751692da2fef98`.
The new coverage set contains test rows 24–79.
The existing pilot contains rows 0–23.
The evaluation reservation contains rows 80–99.
The preparation command records that reservation before downloading or extracting new examples.
It downloads the pinned parquet file but converts only coverage rows into images and annotations.
It records the source archive hash and each original image hash.
The [pinned dataset card](https://huggingface.co/datasets/naver-clova-ix/cord-v2/blob/7f0115a4b758a71d6473b8d085751692da2fef98/README.md) declares CC BY 4.0.
Credit belongs to NAVER CLOVA and Park et al., CORD (2019).

The pilot re-encoded images as JPEG at quality 75.
The new corpus preserves original embedded bytes.
Different samples and encoding prevent a controlled quality comparison with the pilot.

This deterministic convenience split is small and is not representative sampling.
The holdout protects a future correction test within this dataset.
It does not establish generalization to invoices, PDFs or interfaces.
A larger future source must reserve its evaluation partition before review.
The manifest format permits more coverage pages and a different pinned dataset.
Each page requires an ID, image path, SHA-256 and reference text or CORD annotations.
All prepared images fit in client memory before measurement.
This avoids preprocessing inside request timing but bounds corpus size by host memory.
Preparation time is outside the reported service capacity.

## Offered load and deadlines

The scheduler assigns deterministic arrival times at a constant rate.
It does not wait for earlier requests to finish before producing later arrivals.
Workers and the waiting queue are bounded separately.
A full waiting queue produces an explicit `queue_full` terminal record.
A deadline exhausted before dispatch produces `queue_timeout`.
A dispatched deadline includes time already spent waiting for a worker.
There are no retries.

End-to-end latency starts at the scheduled arrival, not HTTP submission.
It includes scheduler lag, client queueing, HTTP work and response validation.
The HTTP-only latency remains available in each request.
Timeouts are censored observations; server work can continue after client cancellation.
Shed-request latency is a rejection latency, not service completion latency.
The scorer reports both all-outcome and successful-response distributions.
It reports p50, p95 and p99 with nearest-rank quantiles.
Small samples and three repetitions cannot establish production tail guarantees.

Throughput has two denominators.
The arrival-window rate counts successful responses before the offered window ends.
The drain-inclusive rate divides all successful responses by measurement time through final drain.
At overload, reporting only final success without drain would exaggerate capacity.
Queue delay, missed deadlines, rejected requests and arrival lag must accompany throughput.
A sustained capacity claim requires stable queueing and acceptable failures at the chosen load.
A bounded queue limits memory use; it does not hide discarded offered work.
The full queue rejects the newest arrival.
This can change the accepted document mix under overload.
Throughput is therefore specific to this corpus order, admission bound and deadline.

## Warmup and cache state

Repeated trials warm every input before measurement.
They exercise the default multimodal cache with repeated inputs.
They do not measure new-document ingress capacity.
Fresh trials restart the owned parser and warm a disjoint synthetic image.
They submit each coverage image only once.
The profile disables prefix caching but leaves the default image cache enabled.
The words "fresh" and "repeated" describe input policy, not a guaranteed per-request cache hit.
Inspect cache metrics to establish actual hits or evictions.
The 56-document fresh trials are short and cannot establish sustained fresh-input capacity.

The default load range brackets the pilot's 5.99 pages/s at concurrency four.
That pilot is only a prior hypothesis, not an estimate of the new corpus ceiling.
The matrix repeats each rate three times and rotates order to expose drift.
Every rate traverses the same ordered corpus cyclically.
Counts need not be multiples of 56, so early documents can receive one extra repetition.
This small mixture difference is a limitation of the fixed-duration comparison.
A longer run near the observed stable limit probes stability.
It does not establish day-long thermal or reliability behavior.

## Evidence and interruption

Each scheduled request receives an immutable intent record before admission.
The final runner also records warmup intent before submission.
Each terminal result is written to a temporary file, flushed and linked into place.
The link operation refuses to replace existing evidence.
The parent directory is also flushed.
A lock prevents concurrent runners from using one output directory.
The plan binds inputs, serving settings and executable request code to the run.
The suite preserves a source snapshot, lockfile, image identity and serving packages.

A crash between remote execution and local persistence cannot establish the server outcome.
Resume records that ambiguity as `interrupted`.
It never silently retries that request.
The runner resumes unattempted work in a new timing session.
The scorer excludes such split measurements from capacity estimates.
A partial run reports unattempted requests separately.
Raw HTTP bodies survive malformed responses, HTTP errors and truncation.
Timeouts without a response body cannot supply output that the client never received.

## Quality and bottleneck evidence

Scoring uses the existing offline metric functions.
Stop-terminated transport success is separate from text correctness.
Numeric recall detects unmatched annotated strings, including punctuation changes.
It cannot establish field association or complete receipt accuracy.
Extra output may be visible text omitted from the partial annotations.
The automated failure review therefore reports suspects, not verified errors.
Rejected requests receive empty scoring predictions and remain in the denominator.
Lower aggregate recall under overload does not by itself show worse model recognition.
Human image checks must distinguish changed digits, separators, omissions, unrelated text and label gaps.
No model judge is treated as ground truth.

Telemetry records GPU utilization, memory, power and temperature.
It also records container CPU and memory, client CPU time and raw server Prometheus metrics.
Collectors retain errors instead of silently supplying zeros.
Samples are sequential and their interval includes collection overhead.
Use timestamps rather than assuming an exact sampling frequency.
The local workstation remains active during the experiment.
Desktop graphics and agent tools can add resource noise.
This is not an isolated hardware benchmark.
GPU saturation with rising server wait provides different evidence from an idle GPU and busy CPU.
Neither correlation alone proves a specific kernel or preprocessing bottleneck.
The client pre-encodes images, so this experiment does not measure PDF rendering costs.

## PSAI as a later OCR domain

The [PSAI dataset card](https://huggingface.co/datasets/anaisleila/computer-use-data-psai/blob/0e1b7c63072833ba58b89dcfcc0cbac45107b0f4/README.md)
describes screenshots, videos, DOM snapshots and interaction events under MIT terms.
The sister Typevet repository uses it for interface judgments.
Its fixture notice says the original screenshot extraction revision was not recorded.
Those fixtures are therefore unsuitable as pinned inference-lab source evidence without reconciliation.

PSAI is a useful candidate for screenshot OCR coverage.
Task names and click events are not text transcriptions.
DOM text also requires alignment to the visible frame; hidden text is not visible ground truth.
A separate experiment should pin source bytes, select frames, reserve tasks and annotate visible text regions.
Split by task to keep neighboring frames out of both development and evaluation sets.
Record the dataset attribution and applicable source-page limitations.
Keep those scores separate from receipt quality and throughput.
This increment does not claim PSAI OCR accuracy.

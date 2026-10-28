# Shared capacity measurement method

Kind: explanation.

This experiment asks whether urgent document requests can meet their deadlines
while a bulk import uses the same backend.
It uses one Nemotron model and one RTX 4090.
The admission policy belongs to the benchmark client.
It is not a production gateway.

## Hypotheses and decision

The two consumers are fictitious.
A customer-facing receipt check submits steady urgent work.
A back-office import submits bursts of bulk work.
Both consumers use the same receipt corpus and inference request.
Urgency changes scheduling, not the model or document difficulty.

Three hypotheses guide the comparison:

1. Mixed FIFO admission reduces urgent deadline attainment relative to urgent-only work.
2. Reserved capacity improves urgent deadline attainment relative to mixed FIFO.
3. Any improvement can cost bulk progress, completion time or unused dispatch capacity.

None is an established result.
A null or negative result satisfies the experiment when its evidence is complete.
The earlier scaling experiment found queue growth at six offered receipts/s.
It did not measure two consumers, FIFO starvation or an admission-policy benefit.
It did not establish CPU preprocessing as the bottleneck.

## Frozen primary protocol

The primary protocol uses the following settings.
A changed setting defines a separate experiment.
It cannot silently replace an unfavorable primary result.

| Setting | Primary value |
|---|---|
| Arrival window | 300 seconds per trial |
| Urgent arrivals | One request each second, at offsets 0 through 299 |
| Bulk arrivals | 120 requests at offsets 0, 30, 60, through 270 seconds |
| Scheduled requests per mixed trial | 300 urgent and 1,200 bulk |
| Document assignment | Each class cycles independently through CORD rows 24–79 in manifest order |
| Equal-time order | Bulk requests precede the urgent request |
| Urgent deadline | 5 seconds from scheduled arrival |
| Maximum bulk queue deferral | 60 seconds from scheduled arrival |
| Maximum upstream concurrency | 8 requests in both mixed arms |
| Reserved-policy bulk limit | 6 requests in flight |
| Reserved urgent capacity | 2 upstream slots; bulk cannot borrow them |
| HTTP watchdog | 120 seconds after dispatch, separate from the urgent deadline |
| Final drain bound | 180 seconds after the arrival window; absolute offset 480 seconds |
| Repetitions | Three sustained trials per condition |
| Retry policy | No retries |
| Input cache policy | Warmed repeated inputs in every primary condition |
| Output limit | Existing 8,744-token allowance in every primary condition |

The offered average is five requests/s during the mixed arrival window.
This is not a capacity estimate for the new policy.
The earlier five-minute experiment kept queueing low at five requests/s,
but it used a different dispatch limit and a smooth arrival pattern.
Bulk bursts deliberately expose a finite backlog without increasing average load.
Their size is an illustrative import requirement, not a measured enterprise trace.

Every class includes receipt 71.
The identical mixed trace fixes the count and placement of every document.
Receipt 71 can still fail in an isolated trial.
Its exclusion, a lower output limit or a changed prompt needs a separate sensitivity study.
CORD rows 80–99 stay reserved and uninspected.

The serving profile remains the pinned profile in `serving/config.json`.
The model and plugin share revision `62cb1e4ba153d113ff64aaf2be6e068c377cf53c`.
The corpus remains CORD-v2 revision `7f0115a4b758a71d6473b8d085751692da2fef98`.
Preparation and warmup occur outside measurement.
Every condition warms the same 56 inputs with the same output allowance.
A completed warmup with truncation is recorded, not silently discarded.
A warmup with uncertain backend execution prevents measurement.

## Deadline rationale and baseline stage

The illustrative business requirement is a result within five seconds of arrival.
The deadline is fixed before isolated or mixed evaluation.
It is not fitted to produce a policy win.
The earlier repeated-input trials at two requests/s had all-outcome p95 latency
of about 1.98–2.13 seconds.
That evidence motivates a five-second starting requirement.
It does not prove that the new urgent workload can meet it.
The new isolated baseline measures that feasibility directly.

The urgent-only baseline retains the urgent trace and removes bulk work.
The bulk-only baseline retains the bulk trace and removes urgent work.
Both use FIFO admission with the common limit of eight upstream requests.
The baseline stage runs before the mixed-policy stage.
The deadline stays five seconds even if the isolated baseline misses it.
Such misses limit the achievable service claim and remain in the report.

The condition order is frozen:

| Stage | Repetition 0 | Repetition 1 | Repetition 2 |
|---|---|---|---|
| Isolated | Urgent, bulk | Bulk, urgent | Urgent, bulk |
| Mixed | FIFO, reserved | Reserved, FIFO | FIFO, reserved |

Each trial has its own warmup and drain.
Three repetitions expose some variation but do not fully balance position.
They do not establish production tail guarantees or day-long stability.
Pairwise mixed comparisons use the same repetition and arrival trace.
The report shows each trial and paired differences, not only pooled averages.

## Admission and upstream bounds

FIFO dispatches the oldest eligible arrival.
Equal-time bulk order represents an import accepted immediately before a customer request.
This is one declared phase alignment, not an average over all arrival phases.
The reserved policy dispatches waiting urgent work first.
It dispatches bulk only while fewer than six bulk requests are in flight.
Total upstream work stays at or below eight in both arms.
Unused urgent slots are deliberately unavailable to bulk.
This makes the reservation cost visible.

The waiting backlog is bounded by the finite frozen trace.
Urgent work that has already spent five seconds waiting expires before dispatch.
Bulk work that has spent sixty seconds waiting expires before dispatch.
Every expired request receives a terminal outcome and policy decision.
A deferred request is work that waits for dispatch capacity.
Deferral is counted separately from final rejection or expiration.
The report includes maximum observed bulk wait, including expired work.

The urgent deadline is a service objective, not an HTTP cancellation timer.
An urgent request already in flight can complete after five seconds.
It retains its slot until a known response or the transport watchdog.
A late normal response is a deadline miss.
A response at the output limit is a truncation, not normal completion.

A client timeout does not prove that backend work stopped.
Any transport failure that leaves backend execution uncertain stops new dispatch.
Remaining scheduled requests receive explicit backend-uncertain outcomes.
Already active requests retain their accounting until response or watchdog.
Such an arm is not eligible for a capacity comparison.
A later arm requires evidence of an idle backend or a reset of the owned parser.
A blind delay is not evidence that execution stopped.
The final drain bound also preserves explicit outcomes for unfinished work.
It never reports unfinished bulk as completed.

## Evidence and metrics

The immutable plan binds the arrival trace, document hashes, serving profile,
request implementation, output limit, cache policy and policy settings.
Each scheduled request has a stable identity, an admission decision and an outcome.
Raw response bodies remain available for offline scoring.
Source snapshots and the dependency lockfile make the scorer reproducible.
A crash or missing outcome is incomplete evidence, not success.

Urgent attainment is the number of nonempty, stop-terminated responses
completed within five seconds, divided by all scheduled urgent requests.
Rejected, expired, timed-out, truncated, failed and unattempted urgent work
cannot disappear from that denominator.
This is transport deadline attainment, not correct OCR attainment.

Latency starts at scheduled arrival.
It includes scheduler delay, client waiting, server waiting and processing.
Successful-response percentiles accompany all-outcome percentiles.
Fast rejection must not appear to improve service latency.
Future requests aborted before their arrival have no observed completion latency.
They remain misses and explicit outcomes.

Bulk reporting includes normal completions during arrivals and after drain.
It includes throughput with both arrival-window and drain-inclusive denominators.
Completion time is reported only when all scheduled bulk work completes normally.
Otherwise, completion time is unknown and unfinished or failed counts are explicit.
The last observed completion is not the completion time of an unfinished import.

Each report also records these quantities:

- Urgent deadline misses, queue wait and latency distributions.
- Maximum bulk wait, deferred work, expired work and other rejection counts.
- Timeouts, HTTP failures, malformed responses, empty output and truncations.
- Upstream occupancy and time when reservation blocks waiting bulk work.
- GPU and server telemetry, including collector errors and available cache counters.
- Diagnostic numeric recall and text overlap, separate from transport outcomes.
- Successful outputs with missing annotated numbers, labeled as quality suspects.

The scorer uses the existing receipt metrics without changing their rules.
Missing annotated numbers are diagnostic failures, not an audited page-error rate.
CORD contains partial references and known annotation discrepancies.
Numeric-string recall does not establish correct field association.
Unrelated generated text needs image review.
Rejected work has no OCR output and remains visible in aggregate denominators.
A policy can change which documents complete; conditional quality scores must say so.

## Acceptance and limits

Acceptance requires reproducible evidence, not a favorable scheduling result.
The implementation must demonstrate the following invariants with behavior tests:

1. Both mixed arms replay identical arrivals and document assignments.
2. Total upstream dispatch never exceeds eight, including uncertain execution.
3. Reserved bulk dispatch never exceeds six.
4. Queue expiry, late responses and drain expiry retain every scheduled identity.
5. All scheduled urgent requests remain in the deadline denominator.
6. Timeout uncertainty cannot silently free capacity for new requests.
7. Every saved response can be rescored without inference.

Real-run acceptance additionally requires complete trial accounting,
verified settings and hashes, three repetitions per condition, the frozen order,
and the required GPU integration check against the demo server.
It requires service-restoration evidence after an approved GPU handover.
Offline tests do not satisfy those real-run requirements.
Incomplete or invalid trials remain visible and cannot support a capacity claim.

The final interpretation compares urgent attainment with bulk progress and idle capacity.
A higher urgent success rate alone cannot establish a free improvement.
A policy can reserve slots without increasing throughput or OCR correctness.
Conversely, FIFO can meet the stated requirement and make reservation unnecessary.

These are warmed repetitions of 56 receipts on one workstation.
They do not measure fresh-document ingress, document preparation, enterprise scale,
high availability, access control, security, multiple models or multiple GPUs.
They do not establish contractual service guarantees.

## Design review record

The experimental-design agent reviewed the preceding scaling method, results,
failure review, draft series specification and October 26–27 companion posts.
It identified three hazards before implementation: treating five-second latency
as a cancellation timer, moving the bulk queue into vLLM, and hiding failed bulk
work behind the last completion time.
The protocol addresses these with separate transport bounds, a common upstream
limit and explicit incomplete-job reporting.

The advisory design question asked whether the frozen controls, full denominators,
timeout handling and acceptance of null results permit an honest comparison
within this warmed-receipt workload.
`judgevet-gemma` answered true with probability `0.9999986868914076`
using `gemma-4-31b-kv9-text`.
The design reviewer agrees for the protocol, conditional on implementation checks
and real GPU evidence.
This probability is not measured accuracy or acceptance of the implementation.
The design was reviewed before mixed results existed.

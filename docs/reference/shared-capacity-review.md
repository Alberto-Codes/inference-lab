# Shared capacity review record

Kind: reference.

Review date: 2026-10-28.
The independent acceptance reviewer is a separate Codex agent from the builder.
This review covers `shared_capacity.py`, `score_shared_capacity.py`,
`shared_capacity_suite.py`, their behavior tests and the method document.

## Acceptance status

Final independent acceptance passed for the requested experiment and unpublished deliverables.
The twelve-arm GPU matrix completed after explicit service-handover approval.
All 13,500 scheduled requests have recorded outcomes.
Mock HTTP tests are implementation evidence only.
They are not evidence of GPU throughput, OCR quality or service restoration.

The reviewer ran the final focused command:

```sh
uv run pytest tests/test_shared_capacity.py tests/test_shared_capacity_suite.py tests/test_shared_capacity_report.py -q
```

All 32 tests passed.
An earlier report-test run found four failures because synthetic fixtures lacked
newly required policy fields.
The fixtures now use the actual evidence schema.
The scorer checks were preserved.

The reviewer also inspected the full validation logs locally.
Those logs were not committed.
The lock check, Ruff check, format check, type check, docvet check, build and
strict MkDocs build passed.
The full test suite passed 123 tests with one GPU test deselected.
Coverage was 87.33%, above the required 85%.
That offline run deselected the GPU test.
The later real GPU test passed against the demo server.

## Advisory acceptance questions

The reviewer discovered the available judgevet tools before calling them.
The backend identified itself as `gemma-4-31b-kv9-text`.
The reviewer asked these builder acceptance questions before the acceptance audit.
The questions supplied concrete definitions rather than thin labels.

| Question and criteria | judgevet-gemma answer | Reviewer decision |
|---|---|---|
| Is the full requested experiment complete? Completion requires reviewed design, bounded scheduler tests, all validation, repeated real GPU baselines and mixed trials, reproducible hashes and scoring, a measured tradeoff report and unpublished companion draft. | False; probability of true `0.00000019795999162548865` | Agree. GPU results are absent. Code and mock tests cannot substitute for them. |
| Does the stated timeout policy avoid silently exceeding the upstream work bound? This requires no recycling of unknown backend execution, an invalid capacity result after uncertainty, and idle proof or owned reset before a later arm. This question judges the stated policy only. | True; probability of true `0.9999968728551307` | Agree on the policy. Implementation and lifecycle behavior require separate checks. |

These probabilities are advisory model outputs, not measured accuracy.
The second answer does not accept uninspected implementation details.

Before the implementation commit, the supervisor asked for its conventional type.
The criteria defined `feat` as a new runnable capability, `fix` as repair of
existing behavior, and `docs`, `test` and `chore` as narrower changes.
`judgevet-gemma`: `feat` with confidence `0.9999976192090454`.
Supervisor: `feat`; agree because the change adds a new executable experiment.

## Initial findings

| Finding | Consequence | Correction requested | State |
|---|---|---|---|
| Queue expiry uses a loop timestamp before synchronous evidence writes. The recorded dispatch timestamp also precedes a durable dispatch write and actual coroutine execution. | Work can begin HTTP inference after its queue deadline even though its recorded dispatch time is earlier. | Check expiration at actual request start and distinguish durable intent from actual dispatch. Add a delayed-evidence-write behavior test. | Corrected and independently verified. |
| The scorer checks that a decision file exists but does not compare its contents with the terminal record. | An altered or mismatched policy decision can pass evidence validation. | Verify decision identity, policy, decision and dispatch fields. Hash policy evidence. | Corrected and independently verified. |
| The initial numeric-mismatch count includes empty predictions for rejected work. It does not separately count mismatches among successful outputs. | Queue rejection can be mistaken for model recognition failure. | Retain all-scheduled diagnostics and add successful-output diagnostics with an explicit denominator. | Corrected and independently verified. |
| The first test set does not directly measure simultaneous bulk dispatch against the reserved bulk limit or verify late successful responses as deadline misses. | Central scheduling and denominator claims have incomplete behavior coverage. | Add direct bulk occupancy and late-response tests. | Corrected and independently verified. |
| Suite preparation accepts arbitrary coverage manifests while the primary method requires exactly CORD rows 24–79, including receipt 71. | A different corpus can be presented as the primary protocol without a separate sensitivity label. | Enforce primary corpus identities in suite preparation while permitting small fixtures in the low-level runner. | Corrected and independently verified. |

## Correction evidence

The request coroutine now checks expiry at the actual send boundary.
A delayed-evidence-write test produces queue expiry without an HTTP request.
Durable admission intent and actual dispatch have separate timestamps.
The scorer verifies policy identities and timing against the terminal records.
It hashes decision and dispatch evidence.
Successful-output numeric suspects now have a separate count.
The scorer also retains text-overlap diagnostics.
Tests directly verify total and bulk concurrency bounds and late normal responses.
The suite rejects a primary corpus that omits receipt 71.
It verifies each arm against the frozen protocol before service interaction.

## Checks supported by inspection

The frozen trace assigns each class independently and preserves bulk-first ties.
The isolated conditions filter that trace without reassigning documents.
The primary trace contains 300 urgent and 1,200 bulk requests.
The runner does not use the urgent deadline to cancel in-flight generation.
Transport uncertainty blocks new dispatch and marks capacity evidence ineligible.
The suite resets only the owned parser between arms.
Its lifecycle uses the existing ownership, free-memory and restoration safeguards.
The suite requires an explicit handover flag before entering that lifecycle.
The agent still needs the user's explicit permission before executing that flag.

The scorer retains all scheduled urgent requests in the deadline denominator.
Missing outcomes count as misses and make the arm incomplete.
Bulk job completion time is null unless all scheduled bulk requests finish normally.
Raw response bodies remain available for offline inspection.
A normal response is not treated as verified correct OCR.

## Measured-evidence acceptance

The independent audit passed all 13,500 scheduled identities across twelve arms.
Eleven arms are capacity-eligible.
The third bulk baseline remains ineligible after a connection error.
It is retained rather than replaced.
All three mixed-policy pairs are valid comparisons.

The audit independently rebuilt the trace and checked its document assignments.
It compared policy decisions, scheduled-arrival latency, deadlines and denominators.
It reconstructed client occupancy from actual dispatch and observed completion.
Total occupancy never exceeded eight; reserved-policy bulk occupancy never exceeded six.
It retained unknown execution through the accounting horizon.
It verified no later dispatch after the bulk baseline reported backend uncertainty.
The accounting horizon does not prove that unknown backend execution stopped.
Each later arm used a new owned parser container.

Frozen-source and runtime-source hashes match.
All arms use the same immutable image and serving arguments.
The runtime package list represents Nemotron as a local package URL.
An additional CPU-only package metadata receipt binds exact Nemotron and vLLM
versions to that same immutable image; both match the pinned profile.
The real GPU integration test passed.
The lifecycle receipt reports restoration without errors.
A separate live check confirms the prior Gemma model loaded, its service active,
and the owned parser absent.

The audit source is retained as `analysis/audit_matrix.py` in
`evidence/shared-capacity-4090/raw-evidence.tar.gz`, and its output is
`evidence/shared-capacity-4090/audit.json`.
The measured matrix is under `shared-capacity-4090-20261028/` in the same archive.
The audit includes arrival-window resource summaries from retained telemetry.
Its independently tested concurrency reconstruction is conservative client accounting,
not a measurement of individual GPU execution intervals.

| Repetition | FIFO urgent on time / scheduled | Reserved urgent on time / scheduled | FIFO normal bulk completions | Reserved normal bulk completions | Reserved bulk queue expirations | Reserved idle slot-seconds with bulk waiting |
|---|---|---|---|---|---|---|
| 0 | 79 / 300 | 294 / 300 | 1,175 | 1,135 | 45 | 171.17 |
| 1 | 72 / 300 | 295 / 300 | 1,176 | 1,127 | 52 | 184.90 |
| 2 | 98 / 300 | 293 / 300 | 1,179 | 1,132 | 47 | 173.39 |

Each mixed arm scheduled 1,200 bulk requests.
No bulk job completed all scheduled work normally.
Its completion time therefore remains null.
The table reports transport outcomes, not verified correct OCR.

The third urgent baseline attained 289 / 300 deadlines, compared with 295 / 300
in the other two repetitions.
It includes three queue expirations during observed scheduling delay.
The cause remains unproven.
The third bulk baseline records one connection error and 784 backend-uncertain outcomes.
No client timeout or connection error proves that backend execution stopped.
These exceptions remain in the evidence and interpretation.
The policy combines urgent priority and reservation.
There is no priority-only ablation to isolate their individual effects.

## Post-run advisory acceptance

The reviewer rediscovered judgevet after Gemma restoration.
No service was changed to obtain these advisory answers.

| Question and criteria | judgevet-gemma answer | Reviewer decision |
|---|---|---|
| Accept the narrow measured claim? Criteria require matched controls, full scheduled accounting, repeated paired results, explicit invalid-baseline retention, measured bulk costs and limited warmed-input interpretation. | True; probability of true `0.994940502547276` | Agree. The audited three mixed pairs support the combined-policy tradeoff within this workload. |
| Is the full user request complete while the final measured documentation and draft are still being updated? Completion requires those final writeups and their validation. | False; probability of true `0.0000009799888738881229` | Agree at this checkpoint. Final prose review and documentation validation remain. |

Both answers came from `gemma-4-31b-kv9-text`.
Neither probability is measured accuracy.
No claim about enterprise scale, availability, security or multiple models follows
from this one-model experiment.

## Completion boundary

The reviewed design, working runner, behavior tests, offline validation,
Diátaxis documentation, unpublished companion draft and evidence-aligned series
specification are present.
The draft is under `alberto-codes-site/docs/series/llm-gateway/`.
Its measured update matches the audited results.
The series specification distinguishes the new workload-specific evidence
from broader unproven bottleneck and enterprise claims.

The final numerical prose, figure, evidence archive, procedure, companion draft
and series specification received independent review.
No requested experiment deliverable remains unmeasured or unwritten.
The capacity-ineligible baseline remains a documented limitation, not missing work.
No release or post publication is part of this acceptance.

## Final artifact review

The reviewer checked the final tables and numerical prose against the bundled report.
It rendered and inspected `docs/assets/shared-capacity.svg`.
The figure shows each repetition and marks the invalid baseline as unavailable.
It does not plot that baseline as zero capacity.
One prose correction replaced a claim about individual quality suspects with
"counts of quality suspects", which matches the report schema.

The reviewer independently checked the archive digest and every member against
`archive-index.json`: 43,827 file sizes and SHA-256 hashes matched.
It extracted the archive into a new directory.
It ran the archived report and independent audit without a GPU.
Both reproduced JSON artifacts exactly match the bundled report and audit.
No corpus images or model weights were required for this check.
The archive retains source, configuration, trace, raw outcomes, policy decisions,
telemetry, runtime identities and restoration receipts.

The companion draft stays outside the site's published-post directory.
Its numbers match the report, including final-outcome times rather than false
whole-job completion times.
It reports the invalid bulk baseline, urgent baseline jitter, OCR limitations,
warmed inputs and the combined priority-plus-reservation policy.
The series specification no longer assumes universal FIFO starvation,
a CPU bottleneck or a general admission-policy benefit.
The existing October 26–27 posts and immutable experiment tags remain preserved.

The final advisory question asked whether the full collection satisfies the
requested honest, reproducible experiment, including negative exceptions,
restoration and unpublished writeups.
`judgevet-gemma` answered true with probability `0.9999999678112114`
using `gemma-4-31b-kv9-text`.
The reviewer agrees based on the independent evidence checks above.
This answer does not turn model confidence into measured accuracy.

The supervisor also recorded the commit-type judgment for the final documentation
and evidence change.
Its criteria were: `docs` for documentation or recorded evidence without behavior
changes; `feat` for new executable behavior; `fix` for a behavior defect; and
`test` for tests only.
Judgevet selected `docs` with confidence `0.9999976252015477`.
The supervisor selected `docs` and agrees.

## Final validation and test timing limit

The final strict MkDocs build and whitespace check passed after review edits.
A full test rerun on disk-backed temporary storage passed 120 tests and failed
five short real-time scheduler tests in 20.17 seconds.
The unchanged suite then passed all 125 tests on tmpfs temporary storage in
3.68 seconds, with one GPU test deselected and 87.33% coverage.
The original temporary directory also used tmpfs; inode pressure prompted the
intermediate storage change.

The short mocked scheduler tests are sensitive to storage and scheduling delay.
They should not be treated as portable timing guarantees.
The passing tmpfs rerun does not erase the disk-backed failures.
The frozen runner and measured experiment source were not changed to obtain it.
The separately recorded real GPU check and completed matrix remain the runtime evidence.

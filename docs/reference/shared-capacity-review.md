# Shared capacity review record

Kind: reference.

Review date: 2026-10-28.
The independent acceptance reviewer is a separate Codex agent from the builder.
This review covers `shared_capacity.py`, `score_shared_capacity.py`,
`shared_capacity_suite.py`, their behavior tests and the method document.

## Acceptance status

Offline implementation acceptance passed.
Full experiment acceptance is pending real GPU evidence.
No shared-capacity GPU trial has run at this review checkpoint.
Urgent protection, bulk cost and idle-capacity effects remain unmeasured.
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

The reviewer also inspected the full validation logs in
`runs/shared-capacity-validation/`.
The lock check, Ruff check, format check, type check, docvet check, build and
strict MkDocs build passed.
The full test suite passed 123 tests with one GPU test deselected.
Coverage was 87.33%, above the required 85%.
The deselected GPU test remains a real-run requirement.

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

## Remaining real evidence

Real acceptance needs the frozen twelve-arm matrix, three repetitions of each
condition, the GPU integration check, runtime identities, raw outcomes,
telemetry, reproducible scores and verified service restoration.
The final report must show paired urgent and bulk results even when reservation
provides no benefit or reduces bulk progress.
No claim about enterprise scale, availability, security or multiple models follows
from this one-model experiment.

## Completion boundary

The reviewed design, working runner, behavior tests, offline validation,
Diátaxis documentation, unpublished companion draft and evidence-aligned series
specification are present.
The draft is under `alberto-codes-site/docs/series/llm-gateway/`.
It states that the shared-capacity measurements are absent.
The series specification treats FIFO interference, CPU bottlenecks and policy
benefits as unproven.

The remaining work is the approved GPU execution and the outputs that depend on it:
the real integration check, complete repeated trials, runtime and raw evidence,
reproducible measured reports, verified restoration, and measured interpretation
in the documentation and companion draft.
No release or post publication is part of this acceptance.

# Shared-capacity experiment status

Kind: reference.

## Measurement status

The shared-capacity GPU matrix has not run.
No measured urgent-protection benefit or bulk-progress cost is established.
The [method](../explanation/shared-capacity-method.md) freezes the hypotheses and protocol.
The [procedure](../how-to/run-shared-capacity.md) separates offline preparation from an approved GPU handover.

The 2026-10-28 preflight found an active `llama-cpp-tuned.service`.
The RTX 4090 reported 2,420 MiB free.
The unchanged demo profile requires 11,000 MiB free before startup.
No existing GPU service was stopped for this preflight.
Explicit approval is required before the handover.

## Offline validation

The repository checks passed on 2026-10-28.
The offline suite passed 123 tests with 87.33% package coverage.
The GPU test was deselected in that suite.
The 32 new focused tests cover admission, evidence scoring and suite lifecycle.
Lockfile, Ruff, formatting, type, docstring, package-build and strict MkDocs checks passed.
The [independent review](shared-capacity-review.md) records the corrected findings
and advisory judgment agreement.
These checks establish implementation behavior, not inference performance.

## Required result table

The final report must give each condition and repetition separately.
It must compare each mixed policy with the isolated urgent and bulk baselines.
It must also report paired differences between the mixed policies.
Ranges across three repetitions are descriptive ranges, not confidence intervals.

| Evidence | Current status |
|---|---|
| Isolated urgent deadline attainment and latency | Unmeasured |
| Isolated bulk progress and completion | Unmeasured |
| Mixed FIFO urgent interference | Unmeasured |
| Reserved-policy urgent deadline attainment | Unmeasured |
| Bulk throughput, completion and maximum wait | Unmeasured |
| Deferred, rejected and unfinished work | Unmeasured |
| Timeouts, truncations, HTTP and quality failures | Unmeasured |
| Idle reserved slots while bulk work waits | Unmeasured |
| GPU, server and client telemetry | Unmeasured |
| Real GPU tests and service restoration | Pending approved execution |

Urgent deadline attainment must divide by all scheduled urgent requests.
Latency begins at scheduled arrival.
Transport completion and normal termination must remain separate from OCR correctness.
The scoring report must expose partial-reference numeric failures separately.
An empty or missing outcome cannot become a successful request.
Unfinished bulk work prevents a claim that the bulk job completed.

## Interpretation limits

The experiment repeats 56 warmed receipt inputs on one workstation GPU.
It does not measure fresh enterprise document ingress.
Receipt 71 stays in every comparable arm.
The fixed reservation can reduce bulk progress or leave capacity idle.
The measured results must quantify those costs before claiming an advantage.
If FIFO meets the deadline target, that is a valid result.
If reservation fails to help, that is also a valid result.

The prior scaling experiment established queue growth at one tested load.
It did not establish FIFO starvation, a CPU bottleneck or admission benefits.
This increment does not establish enterprise scale, availability, security,
tenant isolation, multi-model operation or production deadline guarantees.
Reserved CORD rows 80–99 remain outside preparation, tuning and scoring.

# Receipt commands and scoring

Kind: reference.

| Script | Input | Output |
|---|---|---|
| `prepare_receipts.py` | Pinned CORD test source and archived manifest | `--output`: new corpus directory |
| `receipt_experiment.py` | `--input`: corpus directory | `--output`: new run directory |
| `score_receipts.py` | `--input`: run directory | `--output`: new score JSON file |
| `review_receipts.py` | `--input`: scores; `--rubric`: saved instruction and criteria | `--output`: new advisory judgment file |

All four scripts support `--help`.
They refuse existing output destinations.
The optional judge has isolated script dependencies and is not part of the core client installation.

## Input identity

The pilot uses CORD-v2 test rows 0–23 at revision `7f0115a4b758a71d6473b8d085751692da2fef98`.
Preparation downloads the test Parquet source from that revision.
Source images are PNG. The historical dataset viewer supplied JPEG images.
Preparation reproduces Pillow JPEG quality 75 and verifies every byte hash.
The pinned Pillow dependency and archived image hashes prevent silent encoding changes.
It also checks the original annotations and records the Parquet hash.

## Measurements

One warmup request per image precedes measured concurrency levels one and four.
There are 72 requests in total, including 24 warmups.
Requests have a 120-second deadline and no retries.
A failed warmup prevents measured sweeps.
Every terminal record is flushed to `requests.jsonl`.
An interrupted report remains incomplete. Missing phase/sample pairs identify unfinished work.

ROUGE-L uses case-folded tokens and the longest common subsequence.
The normalizer removes parser controls, HTML tags and supported LaTeX formatting.
Page F1 equals twice the subsequence length divided by the combined token count.
The aggregate is the mean page F1.
Numeric recall uses counted exact matches, including signs and separators.
The aggregate divides total matched numeric strings by total annotated numeric strings.

A non-success response receives an empty scoring prediction.
Its raw text and finish reason remain available.
Transport completion does not imply correct extraction.

## Limits

Annotations cover selected receipt content, not a full transcription.
Extra visible text and different reading order can reduce ROUGE-L.
Numeric presence does not establish correct field association.
These are diagnostic scores, not official CORD scores or financial accuracy.
Layout and table-structure accuracy are not evaluated.
Judge scores are advisory rubric indices, not measured accuracy.

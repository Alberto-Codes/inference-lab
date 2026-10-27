# Data and licences

Kind: reference.

Project code and original documentation use MIT.
CORD source annotations and reference excerpts use CC BY 4.0.
Credit NAVER CLOVA and Park et al., CORD (2019).

[Full third-party notices](https://github.com/Alberto-Codes/inference-lab/blob/main/THIRD_PARTY_NOTICES.md).

## Dataset provenance

The pilot uses CORD-v2 test rows 0–23 from a pinned dataset revision.
The manifest records source annotations and the hashes of the submitted images.
Preparation reproduces the viewer's JPEG encoding from the pinned PNG source.
Every image hash and annotation must match before preparation succeeds.

Receipt images and model weights are downloaded separately.
They are not included in the Python package.
Model weights, plugin code and tokenizer notices retain their upstream licences.
See the [serving profile](serving.md) for the selected revision.

## Evidence handling

Raw parser outputs, timing, scores and input hashes remain available for inspection.
An unrelated host-service inventory was removed from public evidence.
Checkout paths in operational test logs are explicitly redacted.
These privacy changes do not change parser outputs, measurements or dataset hashes.
New runs use separate output directories and never replace the recorded pilot.

# Licences and public audit

Kind: reference.

Project code and original documentation use MIT.
CORD source annotations and derived reference excerpts use CC BY 4.0.
Credit NAVER CLOVA and Park et al., CORD (2019).
Model weights, plugin code and tokenizer notices retain their upstream licences.

[Full third-party notices](https://github.com/Alberto-Codes/inference-lab/blob/main/THIRD_PARTY_NOTICES.md).

## Public content review

The initial four-commit history passed Gitleaks 8.30.1 with no detected secrets.
The proposed public tree also passed the scanner with no detected secrets.
The scanner binary was checked against its release checksum.
The scan is a detection check, not proof that every possible secret format is covered.

Historical logs retain the public author name, local checkout paths, GPU UUID and container names.
These are benign provenance and local environment observations, not credentials.
Their presence does not configure a reader's machine.
The original evidence remains unchanged so its hashes and observations can be checked.
Local assistant state, caches, corpus images, weights and generated site files are ignored.
No API credential is needed for the public dataset download or offline scoring.

The original CORD viewer images were JPEG encodings of PNG source images.
Pinned preparation reproduces those encodings and verifies all 24 archived hashes and annotations.
A fresh preparation run verified this behavior before public delivery.

## Release state

The first experiment is prepared as a draft release.
Its companion post remains unpublished until separately authorized.
Pages deploys from validated main and does not require publishing the first tag.

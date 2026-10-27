# Public experiment repository design

Kind: explanation.

## Scope

Publish inference-lab as a small document-parsing experiment repository.
Serve documentation through GitHub Pages with MkDocs Material, as Saucier does.
Pair each immutable experiment tag with a GitHub Release and companion blog post.
Keep the first release in draft until its post is ready.
Do not publish a Python package or add new model experiments.
The user authorized repository creation, pushes, documentation deployment and local validation.

## Reproduction interface

Keep the four existing receipt scripts and their narrow responsibilities.
Preparation accepts --output for a new corpus directory.
Inference accepts --input for the corpus and --output for a new run directory.
Scoring accepts --input for a run directory and --output for a new score file.
Judge review accepts --input for scores, --rubric for the saved policy and --output for new judgments.
Judge cases come from the selected run, not from the historical rubric states.
All output creation refuses existing files or nonempty run directories.
Keep original public evidence immutable.
Record incomplete run state and each terminal request before returning failure.
Validate image paths, hashes and fixed sample IDs before submitting requests.
Keep normalization and numeric rules unchanged.

The receipt procedure owns the operational instructions.
Use a shell trap in the documented local-service example to stop the owned parser container and restore llama.cpp.
Bound router and loaded-model checks. Report cleanup failures separately from inference failures.
Do not stop services automatically from the generic receipt scripts.

## Public contents

Review all tracked history and proposed files before the first push.
Run a secret scanner when available and manually inspect machine-specific findings.
Retain benign provenance such as hardware and model revisions.
Exclude caches, local assistant state, images, weights and generated site output.
Use MIT for project code, following Saucier.
Document dataset and model licences separately; MIT does not relicense third-party content.

## Documentation

Use a pinned MkDocs Material docs dependency group and a strict build.
Provide a quickstart that scores saved evidence without a GPU.
Provide a separate receipt GPU procedure, scoring reference and troubleshooting page.
Include the existing serving reference, measurements and limitations.
Use a small navigation tree organized by Diataxis.
Use an ordinary source link to public evidence; keep raw evidence outside the docs site.
Correct the companion draft's parser terminology and replace local links with commit permalinks.
Keep its draft filename and unpublished status.

## Release workflow

Saucier uses release-please, draft releases and a documentation deployment workflow.
Adopt the same draft-first lifecycle, but do not add PyPI publishing.
Use a manual draft-release workflow for experiment tags at this MVP stage.
The workflow validates a requested tag, commit and release notes, then creates a draft with no existing tag.
An explicit commit SHA freezes the intended release target before publication.
It refuses an existing tag or release rather than modifying a published experiment.
A checked-in release note names the experiment, reproduction command and companion-post status.
A release ledger maps the intended tag to the unpublished draft and later public post.
Publishing remains a separate maintainer action after both directions of the links are ready.

Deploy Pages on published releases and explicit workflow dispatch, following Saucier.
Use explicit dispatch for the initial site without publishing the experiment tag.
A branch CI job validates offline tests, lint, lock, package build and strict docs build.
No GPU or model downloads run in CI.

## Shipping sequence

Audit the unpublished Git history before creating the public repository.
Bootstrap the empty remote with the audited existing main history.
Use a feature branch and no-mistakes for the implementation delivery.
Verify its PR and CI, then merge the authorized changes.
Enable Pages, deploy and verify public content in a browser.
Create the first draft release at the validated main SHA without creating a tag.
Confirm the draft state, missing tag and unpublished companion post.

## Acceptance evidence

Behavior tests demonstrate path selection, output protection and failure accounting.
Offline rescoring reproduces the saved 212/241 numeric matches and diagnostic overlap.
A fresh corpus download verifies preparation without changing inference behavior.
The local and CI documentation builds pass in strict mode.
The public repository and Pages URLs respond with the intended content.
The first draft release identifies a fixed commit and a companion draft.
No published release, tag, blog post or Python package is created.

## Sources and review

Source workflows: ../saucier/.github/workflows/docs.yml and docs/how-to/cut-a-release.md.
This bounded design uses two fresh-context Goldfish reviewers before implementation.
It adapts Elephant–Goldfish to the user's explicit instruction to proceed through implementation.

## Goldfish findings resolved

The scope reviewer removed duplicated release bookkeeping.
Checked-in experiment release notes are the source for the GitHub draft.
They contain the companion-post mapping. No separate ledger is needed.
Pages always deploys validated main, including after a release event.
Release links use immutable commits; the site is not versioned.
We reuse Saucier's lifecycle, not release-please package-version automation.
The judge remains optional for installation and reproduction.

The correctness reviewer required revision-pinned dataset files.
Preparation will read the pinned test Parquet file, not the mutable viewer API.
It will compare the selected images and annotations with archived provenance.
PyArrow is an optional preparation dependency, not a serving dependency.

Corpus and run directories are created exclusively and must not exist.
Score and judge files are opened exclusively before computation begins.
Failed attempts retain partial artifacts and require a different output path.

An explicit --release-llama option will own local service handover.
Default receipt inference continues to use an already running parser.
The handover captures service state and loaded model IDs before any mutation.
Cleanup is installed before shutdown, removes only the owned parser and restores the captured state.
It verifies each model ID with a deadline and records inference and restoration errors separately.
This replaces the proposed copy-pasted shell trap with a testable lifecycle boundary.

Draft creation requires a full public commit SHA with a successful CI run.
Notes come from that commit, not the dispatch branch.
The workflow verifies draft status, exact target and absence of a tag after creation.
Publication instructions repeat these checks before a maintainer publishes.
Live verification checks evidence links as well as rendered documentation.

The pinned-source check found PNG inputs behind the original viewer JPEGs.
Preparation recreates JPEG quality 75 and verifies every archived image hash.
A fresh 24-image download matched all labels and hashes.

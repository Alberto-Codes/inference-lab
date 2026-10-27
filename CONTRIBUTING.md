# Contribute

Keep changes within the current experiment's documented scope.
Use Python 3.12 and uv. Read `AGENTS.md` before editing.

Use a feature branch and a conventional commit subject.
Add behavior tests for path selection, failures and score changes.
Run the validation commands in the README before opening a pull request.
Install local checks with `uv run pre-commit install`.
Use `uv run pre-commit run --all-files` to check the full checkout.
See [quality checks](docs/how-to/check-quality.md) for the checks and their scope.
The maintainer uses no-mistakes before merging shipping changes.

Keep historical evidence unchanged.
Write new runs under an ignored `runs/` directory.
If a calculation needs correction, retain the raw output and describe the correction.
Do not commit credentials, local assistant state, model weights or generated corpus files.

Write documentation under `docs/` using one Diataxis purpose per page.
Apply the sentence guidance in `docs/reference/writing.md`.
Do not claim GPU validation from offline tests.
Stop another GPU service only with its owner's permission.
Restore its previous state after the run, including after failure.

Tags identify immutable experiment snapshots.
Keep release notes and companion posts consistent with that snapshot.
A published experiment correction gets a new tag and an explanatory note.

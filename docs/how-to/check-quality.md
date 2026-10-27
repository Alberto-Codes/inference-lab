# Run the quality checks

Kind: how-to.

Use Python 3.12 and run these commands from the repository root.
These checks do not start the parser or stop another GPU service.

1. Install the locked development, documentation and preparation dependencies.

   ```sh
   uv sync --locked --group docs --group data
   ```

2. Install the optional local commit hooks.

   ```sh
   uv run pre-commit install
   ```

3. Check formatting, code rules, types and docstrings.

   ```sh
   uv lock --check
   uv run ruff check .
   uv run ruff format --check .
   uv run ty check
   uv run docvet check --all
   ```

4. Run the offline behavior tests and measure branch coverage.

   ```sh
   uv run pytest --cov --cov-report=term-missing --cov-report=xml
   ```

5. Build the package and the documentation.

   ```sh
   uv build
   uv run --group docs mkdocs build --strict
   ```

CI runs these checks and validates the workflow syntax with actionlint.
It checks out full Git history for Docvet's freshness analysis.
Run `uv run pre-commit run --all-files` to replay the local hooks.
The hooks run Ruff, ty and Docvet. CI also runs tests and builds.

## What each check covers

| Check | Scope |
|---|---|
| Ruff | Python style, imports, common defects, complexity, security patterns, performance, logging and Google docstring style. |
| ty | Static types in `src/` and `tests/`. |
| Docvet with Griffe | Public package docstring presence, enrichment, freshness, package coverage and rendering compatibility. All five checks are blocking. |
| pytest-cov | Offline behavior and branch coverage. The regression floor is 85%; the initial measured baseline is 87%. |
| Strict MkDocs | Page construction, Python API rendering and documentation cross-references. |

Ruff's rules live in `ruff.toml`. Other settings live in `pyproject.toml`.
Docvet requires 100% presence for public package symbols.
Its package checks exclude command scripts and tests; Ruff still checks those files.
Scripts use separate dependencies where declared by their inline metadata.
The default ty check does not inspect those isolated script environments.
Their command behavior is exercised by the test suite.

The [Python API reference](../reference/api.md) renders Google-style docstrings from `src/`.
Update the docstring when an argument, return value or error contract changes.
Keep narrow lint suppressions beside the operation and explain why they apply.
Do not document a caught exception as an exception that callers receive.

Coverage does not prove model quality or a successful GPU run.
Historical GPU observations remain in the [experiment evidence](../reference/evidence.md).

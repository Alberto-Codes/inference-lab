# Practices inspected and selected

Kind: explanation.

Inspected 2026-10-26 in sibling checkouts: project metadata/dependency groups,
`src` and test layouts, README/developer commands, CI configuration and container
references. These repositories are precedents, not dependencies.

| Source | Evidence inspected | Applied here |
|---|---|---|
| automarket | `pyproject.toml`, `DEVELOPMENT.md`, test markers/fakes, storage ADR | uv/src package, explicit live-test separation; no hexagonal framework |
| options-signal-lab | `pyproject.toml`, README evidence policy, unit/contracts/integration layout, scripts | exact direct pins and explicit verified/unverified evidence; no strategy or agent tooling |
| gepa-adk | `pyproject.toml`, README, unit/contracts/integration layout | scoped async client tests and separate external checks; no ADK or orchestration dependencies |
| judgevet | `pyproject.toml`, README, `docs/how-to/deploy.md`, test support files | narrow container context, rootless Podman, runtime errors and receipts; no SDK/MCP layers |
| typevet | `pyproject.toml`, README runtime receipts, `tests/conftest.py`, live-test layout | exact backend identity and measurement limits beside claims; no model workload copied |
| docvet | `pyproject.toml`, README, `.github/workflows/ci.yml`, unit/integration layout | Ruff check/format, pytest strict markers and lock check; no publishing/docs framework |

The shared engineering core is uv + a small src-layout package + pytest + Ruff.
Two runtime dependencies serve current needs: httpx for async HTTP/timeouts and
Pillow for decoding/normalizing/generating images. argparse, JSON reporting and
statistics use the standard library. Client, experiment and container lifecycle
have separate responsibilities; no port/interface framework is needed.

Container searches found judgevet's concrete rootless Podman recipe; other
inspected projects primarily supply library/CLI practices rather than a common
GPU container stack. Existing local services also run under Podman with NVIDIA
CDI available. We retain that workflow and do not change system configuration.

AXI is a CLI design specification, not a Python parsing dependency. The linked
upstream AXI skill and TOON spec informed compact scalar output, a live home
view, structured failures, truncation and per-command help. Session hook/plugin
installation is deliberately omitted from this small demo's scope; commands do
not modify harness configurations. This is not a claim of full AXI certification.

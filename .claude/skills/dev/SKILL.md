---
name: dev
description: >-
  Development workflow for the verifiable-financial-extraction repo — the exact
  verbs, conventions, and gates that exist today. Use when running, testing,
  linting, type-checking, security-scanning, or containerizing this project, or
  when unsure how it is wired (uv, flat src layout, the api/worker images).
---

# Working in this repo

Python 3.12, **uv**-managed, flat `src` layout. `src` is on the import path with
**no wrapper package** (`[tool.uv] package = false`), so modules import directly:
`from config import get_settings`, `from api.routes import health`. Do not add an
`__init__.py` wrapper or a `src.` prefix.

## Setup

```bash
uv sync            # create/refresh the locked env (also fetches Python 3.12)
```

`uv.lock` is committed. In CI use `uv sync --frozen`. Run tools through uv
(`uv run <tool>`) or the Makefile.

## The gate (run before every commit/PR)

```bash
make check         # ruff check + ruff format --check + mypy + pytest
```

CI runs this exact gate. Individual verbs: `make lint`, `make format`,
`make fmt-check`, `make typecheck`, `make test`. mypy runs with
`disallow_untyped_defs` — annotate every function, including tests.

## Security

```bash
make security      # pip-audit (dependency CVEs) + bandit (SAST over src)
```

`gitleaks`, the private-key guard, and the above also run via pre-commit and the
CI `security` job. Install local hooks once with `uv run pre-commit install`.

## Run the services

Two images are built from one multi-stage `Dockerfile` (targets `api`, `worker`):

```bash
make infra-up      # Postgres only (the M0 default)
make build         # build the api + worker images
make up            # full app: postgres + api + worker
make infra-down    # stop everything
```

API health surface (k8s-style; see src/api/routes/health.py):

- `GET /health/live`  — liveness; no dependencies, never flaps on a DB outage.
- `GET /health/ready` — readiness; pings Postgres, fails **closed** with 503.

## Conventions

- **Dependencies:** add with `uv add <pkg>` (or `uv add --dev <pkg>`); commit the
  updated `pyproject.toml` + `uv.lock`. Never hand-edit `uv.lock`.
- **Config:** all settings go through `src/config.py` (pydantic-settings,
  env-driven) and must be mirrored in `.env.example`. No `os.environ` reads
  scattered in code.
- **Branching:** trunk-based — commit straight to `main`, no feature branches.
  `main` is the only branch.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `build:`, `ci:`, `docs:`,
  `chore:`), imperative subject, a body explaining *why* for non-trivial changes.
- **Errors that gate health/readiness must fail closed** (return a falsy/503),
  never raise into a 500. See `src/db/engine.py:ping`.
- **Empty scaffold dirs are not tracked** (no `.gitkeep`); a directory appears in
  git when its first real file lands.

## Milestone context

See `PROJECT_PLAN.md`. The repo is at **M0** (toolchain + health API + container
build). Ingestion (`src/ingestion`), retrieval, the agent graph, the verifier,
and the eval harness land in M1–M7 and are mostly empty scaffold today — check a
module exists before assuming its behaviour.

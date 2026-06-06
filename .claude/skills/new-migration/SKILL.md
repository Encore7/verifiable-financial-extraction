---
name: new-migration
description: >-
  Author and apply an Alembic database migration following this project's async
  SQLAlchemy conventions. Use when adding or changing tables/columns/indexes, or
  when asked to create, generate, or run a migration.
---

# new-migration — Alembic migrations

> **Status: PLACEHOLDER (Alembic env lands in M1).** `alembic/` has no env.py or
> versions yet, and `src/db/models/` is empty. The async engine helper exists at
> `src/db/engine.py`. See `PROJECT_PLAN.md` M1.

## Intended behavior (spec)

```bash
make migrate                      # alembic upgrade head
# author a revision from model changes:
uv run alembic revision --autogenerate -m "add xbrl_facts"
uv run alembic upgrade head
```

- Define/modify SQLAlchemy 2 (async) models under `src/db/models/`, then
  autogenerate the revision and **review the generated SQL** before applying —
  autogenerate misses some changes (server defaults, enum/type edits, indexes).
- Migrations are forward-versioned and must be reproducible against the
  `pgvector/pgvector:pg16` image from docker-compose.
- Core M1 tables: `filings`, `filing_sections`, `xbrl_facts`, `raw_landings`.
  LangGraph checkpoint tables are managed by AsyncPostgresSaver, not here.

## When implementing for real

Document the alembic env wiring (async engine, `target_metadata`), the naming
convention for revisions, and how migrations run in CI / on `make up`.

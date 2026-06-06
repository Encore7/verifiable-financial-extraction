---
name: ingest-filing
description: >-
  Ingest SEC EDGAR filings and XBRL ground truth for a given CIK / form / year
  via the rate-limited, idempotent ELT pipeline. Use when asked to load, fetch,
  seed, or re-ingest filing data, or to populate the golden slice.
---

# ingest-filing — EDGAR + XBRL ingestion

> **Status: PLACEHOLDER (lands in M1).** `src/ingestion/` (edgar/, xbrl/,
> pipelines/) is empty scaffold. Do not attempt ingestion yet. See
> `PROJECT_PLAN.md` M1.

## Intended behavior (spec)

```bash
make seed-golden   # ingest ~50 (CIK, 10-K, year) cases end-to-end
```

- EDGAR client over `httpx.AsyncClient` with `SEC_USER_AGENT` set, a token
  bucket **≤ 10 req/s**, and retry+backoff. Respect EDGAR fair-access.
- `submissions.json` → filing index (CIK → accession → form → period); fetch
  filing documents + segment the financial statements and MD&A.
- Load the **XBRL Financial Statement Data Sets** into `xbrl_facts`
  (tag, value, unit, scale, period, context_ref, accession) — **this is ground
  truth**.
- ELT pattern: extract → land raw (immutable) → normalize → load. Every load is
  a versioned snapshot (`source_version`); **re-running is a no-op (idempotent)**
  — never re-fetch what is already landed.

## Non-negotiables

- Never exceed the EDGAR rate limit; always send a descriptive `SEC_USER_AGENT`.
- Idempotency is a correctness property, not an optimization — assert it.

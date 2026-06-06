# Project Plan — Verifiable Financial Extraction

A milestone-sequenced build plan. Each milestone has a **definition of done** that is
*verifiable*, not vibes. Build the vertical slice deep before adding breadth.

**Guiding rule:** the eval harness is the product. Get a real, reproducible
hallucinated-figure-rate number on screen as early as possible (M3), then make every
later milestone move that number or the cost/latency around it.

---

## Scope discipline

**In scope for v1**
- Two filing forms: 10-K (annual). 10-Q added in M6.
- One LLM provider: Claude.
- Numeric line-item extraction with XBRL reconciliation. (The thing with exact ground truth.)
- The verifier gate: citation resolution + reconciliation + (for narrative) entailment.
- Eval harness: golden + adversarial, metrics, regression in CI.
- Full local observability stack.

**Explicitly out of scope for v1** (named so reviewers see the discipline)
- GraphRAG / multi-entity ownership graphs (that's a *separate* second project).
- Payment / billing.
- Multi-provider model routing.
- PDF rendering / fancy report assembly.
- Real cloud deploy (compose-only locally; ADR notes the cloud target).

---

## Milestones

### M0 — Repo & toolchain (0.5 wk)
Scaffold, uv, lint/format/type, pre-commit, CI skeleton, docker-compose for Postgres only.

- **DoD:** `uv sync` works; `make lint typecheck test` green on an empty test;
  `make infra-up` brings up Postgres; CI runs the same on push.

### M1 — Data ingestion: EDGAR + XBRL ground truth (1.5 wk)
The data-engineering spine. Async, rate-limited, idempotent, versioned.

- EDGAR client (`httpx.AsyncClient`, `SEC_USER_AGENT`, token-bucket ≤10 req/s, retry+backoff).
- `submissions.json` → filing index (CIK → accession → form → period).
- Filing document fetch + section segmentation (the financial statements + MD&A).
- **XBRL Financial Statement Data Sets** loader → `xbrl_facts` table (tag, value, unit,
  scale, period, context_ref, accession). **This is ground truth.**
- ELT pipeline pattern: extract → land raw (immutable) → normalize → load. Re-runnable;
  each load is a versioned snapshot (`source_version`).
- Alembic migrations for `filings`, `filing_sections`, `xbrl_facts`, `raw_landings`.
- **DoD:** `make seed-golden` ingests ~50 (CIK, 10-K, year) cases end-to-end; row counts
  asserted in an integration test; re-running is a no-op (idempotent).

### M2 — Retrieval with re-fetchable locators (1 wk)
- Chunk narrative sections (MD&A, footnotes) → pgvector, each chunk carrying a **locator**
  (`accession_no`, `section`, `char_span`).
- Numbers are *not* retrieved by similarity — they come from the structured XBRL facts table
  joined by tag + period. (Calling this out is half the point: right tool per data shape.)
- Locator model is the contract the verifier later re-resolves against.
- **DoD:** given (CIK, year, tag), retrieval returns the candidate XBRL fact(s) + supporting
  narrative chunk(s), each with a locator that re-resolves; unit test proves re-resolution.

### M3 — Minimal agent + verifier + FIRST EVAL NUMBER (1.5 wk) ⭐
The earliest point the project is "real." Keep the graph small.

- LangGraph: `intake → resolve_filing → retrieve → extract → verify → assemble` (async).
- `extract`: Claude (`claude-sonnet-4-6`) returns value + chosen locator per requested tag.
- `verify`: (1) locator re-resolves, (2) value reconciles to XBRL within tolerance.
  Verdict ∈ `accepted | flagged | abstained`.
- AsyncPostgresSaver checkpointer wired.
- **Eval runner v1**: run golden set, compute accuracy + **hallucinated-figure rate** +
  abstention rate + cost/filing + latency. Emit `eval/reports/<ts>.md`.
- **DoD:** `make eval` prints the metrics table on the golden set with a real number;
  hallucinated-figure rate is measured (target 0.0%). Reproducible with a fixed seed.

### M4 — Observability stack (1 wk)
Wire the full stack so every eval run and every request is traceable/measurable.

- OTEL SDK: spans per FastAPI request and per LangGraph node; DB + httpx auto-instrumented.
- structlog → OTLP logs, correlated by `trace_id`.
- Prometheus metrics: RED + per-node latency histogram + token/cost counters +
  **eval metrics exported as gauges** (accuracy, hallucination rate per run).
- Alloy as the single OTLP collector → Tempo / Prometheus / Loki.
- Grafana: provisioned datasources + two dashboards (Service health; Eval/quality over time).
- LangSmith tracing on the agent runs.
- **DoD:** a single extraction shows one trace spanning API→nodes→DB in Tempo, correlated
  logs in Loki, latency in Prometheus; the eval dashboard charts accuracy/cost per run.

### M5 — Adversarial set + verifier hardening (1.5 wk)
Now make the number honest under pressure.

- Build adversarial cases: restatements, footnote-only figures, non-GAAP vs GAAP,
  parenthetical negatives, scale (thousands/millions), multi-segment.
- Harden reconciliation: sign handling, unit/scale normalization, restatement-aware period
  matching, GAAP-vs-non-GAAP disambiguation.
- Add the **entailment judge** (`claude-opus-4-8`) for narrative claims.
- Abstention path: when XBRL is silent, the agent must say "not determinable from sources."
- `remediate` node: re-retrieve/redraft only failing items, up to N retries.
- **DoD:** adversarial accuracy + abstention reported; no silent omissions; verifier
  precision/recall computed against a labeled subset; remediation demonstrably recovers ≥1 case.

### M6 — Human-in-the-loop + 10-Q + resume (1 wk)
- `resolve_filing` and exhausted-`remediate` raise `interrupt`; `/v1/extractions/{id}/resume`
  resumes from the Postgres checkpoint.
- Add 10-Q (quarterly period semantics).
- **DoD:** kill the worker mid-run, restart, resume from checkpoint to completion (integration
  test); an ambiguous filing pauses for human input and continues on resume.

### M7 — CI regression gate + writeup (1 wk)
- `make eval` runs in CI on a small fixed slice; build **fails** if accuracy drops below
  threshold or hallucinated-figure rate > 0.
- Snapshot eval reports committed under `eval/reports/` so quality history is in git.
- Write the 1-page results writeup (methodology + numbers + where the LLM fails + residual
  error) — the artifact that actually gets the callback.
- **DoD:** a deliberately bad prompt change makes CI red; README results table filled with
  real numbers; writeup published in `docs/`.

---

## Timeline

~9–10 weeks part-time for the full slice. **First defensible eval number by end of M3 (~wk 4).**
If time-boxed harder: M0–M4 (~6 wks) is already a strong, demoable portfolio piece.

```
wk:  1   2   3   4   5   6   7   8   9  10
M0  ██
M1   ████
M2        ███
M3          █████        ← first eval number
M4               ████
M5                   ██████
M6                         ████
M7                              ████
```

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| XBRL tag ↔ requested concept mapping is messy | High | Start with ~10 well-known US-GAAP tags; expand once reconciliation is solid |
| EDGAR rate limits / blocks | Med | Token bucket + caching of raw landings; never re-fetch what's landed |
| Period/context-ref selection errors | High | This is the real hard part — it gets the `resolve_filing` interrupt + adversarial coverage |
| Scope creep (graph, payments) | High | Explicitly deferred above; second project, not this one |
| Eval looks good but overfits golden set | Med | Adversarial set + held-out cases + CI on a rotating slice |

---

## Definition of "done enough to put on a resume"

End of **M4**: a running async FastAPI + LangGraph agent, full observability, and a
reproducible eval with a real hallucinated-figure-rate number. Everything after that is
depth and honesty under adversarial pressure — which is exactly what differentiates it.

# Verifiable Financial Extraction

**An evaluation-gated AI agent that extracts financial data from SEC filings — and proves every number is real before it accepts it.**

This system extracts financial line items and factual claims from SEC filings (10-K / 10-Q),
where **every extracted figure must trace back to a re-fetchable source location and
reconcile against XBRL ground truth before it is accepted.** Figures that cannot be
grounded are *abstained*, never guessed.

The headline artifact is not the agent — it is the **evaluation harness** that measures,
on a golden set with exact ground truth:

| Metric | What it means | Target |
|---|---|---|
| Extraction accuracy | extracted value matches XBRL within tolerance | ≥ 99% |
| **Hallucinated-figure rate** | accepted figures with no resolvable source | **0.0%** |
| Abstention rate | items correctly declined when sources are silent | reported |
| Verifier precision / recall | gate correctness vs. labeled set | reported |
| Cost / filing, latency p50/p95 | production economics | reported |

> The design rule that makes every component load-bearing:
> **an extraction is only accepted if (a) its source locator re-resolves and
> (b) its value reconciles to XBRL within tolerance. Otherwise it is flagged or abstained.**
> We do not emit an ungrounded number.

Source lives under `src/` as a **flat layout** (no wrapper package). `src` is on the
import path, so modules import directly — e.g. `from agent.graph import build_graph`,
`from evaluation.runner import run`.

---

## Why this project

Parsing filings is the literal day-job of equity research, IB coverage, and credit risk.
The failure mode everyone fears is a **wrong number in a note** — a fireable, sometimes
market-moving error. This system drives that to zero *by construction* (re-fetch + reconcile,
not "trust the chunk"), and — crucially — **measures** the residual error against ground
truth that genuinely exists: the SEC's XBRL Financial Statement Data Sets.

It is deliberately a portfolio system that demonstrates the four things an applied-AI /
ML-engineering reviewer actually screens for:

1. **Correctness you can measure** — eval methodology, exact ground truth, regression-on-change.
2. **Governance / model-risk literacy** — abstention, audit trail, re-fetchable provenance, human-in-the-loop.
3. **Retrieval done right** — locator-bearing chunks, grounding, citation resolution (not just "a vector DB").
4. **Production hygiene** — OpenTelemetry traces, Prometheus metrics, Loki logs, cost/latency per node.

---

## Architecture at a glance

```
                      ┌─────────────────────── FastAPI (async) ───────────────────────┐
                      │  POST /v1/extractions   GET /v1/extractions/{id}   /v1/evals    │
                      └───────────────┬────────────────────────────────────────────────┘
                                      │  (background task / worker)
                                      ▼
        ┌──────────────────────── LangGraph StateGraph (async) ───────────────────────┐
        │                                                                              │
        │  intake → resolve_filing → plan → retrieve → extract → verify ──pass──► assemble
        │                 │(ambiguous)                              │                  │
        │                 ▼                                  ┌──────┴──────┐           ▼
        │           human_review(interrupt)            pass │             │ fail   deliver
        │                                                   ▼             ▼
        │                                              assemble      remediate ──retries──► retrieve
        │                                                                 │(exhausted)
        │                                                                 ▼
        │                                                          human_review(interrupt)
        └──────────────────────────────────────────────────────────────────────────────┘
                                      │
              AsyncPostgresSaver checkpointer  (interrupt / resume / retry survive restarts)

  Stores:  Postgres (app data + LangGraph checkpoints + pgvector)
  Ground truth:  SEC XBRL Financial Statement Data Sets
  Observability:  OTEL → Alloy → {Tempo (traces), Prometheus (metrics), Loki (logs)} → Grafana
  LLM tracing:  LangSmith
```

The verifier is the gate. `verify` has three checks:

1. **Citation resolution (mechanical)** — the source locator (accession no. + statement role
   + context ref) re-resolves in EDGAR/XBRL. No resolution → fail.
2. **Reconciliation (mechanical)** — the extracted value equals the XBRL fact within tolerance
   (sign, scale/units, GAAP vs non-GAAP, restatement-aware).
3. **Entailment (LLM judge)** — for *narrative* claims (not numbers), the cited passage
   actually supports the claim rather than merely sharing a topic.

See [docs/architecture.md](docs/architecture.md) for the full topology and
[docs/adr/](docs/adr/) for the load-bearing decisions (sync vs. async, checkpointer, store choice).

---

## Tech stack

| Concern | Choice | Notes |
|---|---|---|
| Language / pkg mgr | **Python 3.12 + [uv](https://docs.astral.sh/uv/)** | `uv sync`, `uv run`, locked deps |
| API | **FastAPI (async)** | async-first to keep the event loop free |
| Agent | **LangGraph (async)** | `astream` / `ainvoke`; AsyncPostgresSaver checkpointer |
| LLM | **Claude (Anthropic)** | `claude-sonnet-4-6` for extraction, `claude-opus-4-8` for the judge; pinned per ADR-0003 |
| DB / ORM | **Postgres 16 + SQLAlchemy 2 (async) + Alembic** | app data, checkpoints, `pgvector` |
| Retrieval | **pgvector** | one store; narrative chunks only — numbers are structured, not similarity |
| Ingestion | **httpx async + ELT pipelines** | EDGAR submissions/full-text + XBRL bulk |
| LLM observability | **LangSmith** | per-run traces, token/cost, prompt versioning |
| Traces | **OpenTelemetry → Tempo** | per-node spans, distributed across API ↔ agent ↔ DB |
| Metrics | **Prometheus** | RED + per-node latency/cost histograms |
| Logs | **Loki** (structured, via structlog → OTLP) | correlated to traces by `trace_id` |
| Collector | **Grafana Alloy** | single OTLP receiver → Tempo/Prom/Loki |
| Dashboards | **Grafana** | provisioned datasources + dashboards in `observability/` |

---

## Quickstart

> Prereqs: [uv](https://docs.astral.sh/uv/getting-started/installation/), Docker + Compose, an Anthropic API key.

```bash
# 1. clone & install (uv reads pyproject.toml + uv.lock)
git clone <your-fork> verifiable-financial-extraction && cd verifiable-financial-extraction
uv sync --all-extras

# 2. config
cp .env.example .env        # set ANTHROPIC_API_KEY, SEC_USER_AGENT, etc.

# 3. bring up infra: postgres, prometheus, loki, tempo, alloy, grafana
make infra-up

# 4. apply migrations
make migrate

# 5. load a tiny golden slice (XBRL ground truth + a few filings)
make seed-golden

# 6. run the API (hot reload)
make dev
#    → http://localhost:8000/docs    (OpenAPI)
#    → http://localhost:3000         (Grafana, admin/admin)

# 7. run the eval harness — the headline artifact
make eval
#    → writes eval/reports/<timestamp>.md  with the metrics table above
```

### Make a single extraction

```bash
curl -s localhost:8000/v1/extractions -X POST -H 'content-type: application/json' -d '{
  "cik": "0000320193",
  "form": "10-K",
  "fiscal_year": 2023,
  "items": ["Revenues", "NetIncomeLoss", "Assets", "EarningsPerShareDiluted"]
}' | jq
```

The response carries, per item, the extracted value **and** its locator
(`accession_no`, `statement_role`, `context_ref`, `char_span`) plus the verifier verdict
(`accepted | flagged | abstained`) and the XBRL value it reconciled against.

---

## The evaluation harness (read this part)

Everything else exists to be measured by this.

- **Golden set** — `eval/datasets/golden/`. ~50–100 (CIK, form, year) tuples. Ground-truth
  values come *for free* from the XBRL Financial Statement Data Sets, so accuracy is exact,
  not human-judged.
- **Adversarial set** — `eval/datasets/adversarial/`. The real extraction traps:
  restated financials, footnote-only figures, non-GAAP vs GAAP, parenthetical negatives,
  units (thousands vs millions vs as-reported), multi-segment breakdowns.
- **Runner** — `evaluation.runner` executes the agent over each case, compares to ground
  truth, and emits the metrics table. Deterministic seed; results are reproducible.
- **Regression** — `make eval` runs in CI on every prompt/model change. A drop in accuracy
  or any nonzero hallucinated-figure rate fails the build.

See [docs/observability.md](docs/observability.md) for how eval metrics also stream to
Prometheus so you can chart accuracy/cost over commits in Grafana.

---

## Repository layout

```
verifiable-financial-extraction/
├── src/                   # flat layout — `src` is on the import path, no wrapper package
│   ├── main.py            # FastAPI app factory + lifespan (telemetry, db, checkpointer)
│   ├── config.py          # pydantic-settings (12-factor, env-driven)
│   ├── telemetry.py       # OpenTelemetry: traces + metrics + log correlation
│   ├── logconfig.py       # structlog → OTLP, trace-correlated (not `logging.py`: would shadow stdlib)
│   ├── api/               # routes (extractions, evals, health) + pydantic schemas
│   ├── agent/             # LangGraph: graph.py, state.py, nodes/, prompts/, checkpoint.py
│   ├── ingestion/         # data engineering: edgar/, xbrl/, ELT pipelines/
│   ├── retrieval/         # chunker, pgvector store, re-fetchable locator model
│   ├── verification/      # citation (mechanical), reconcile (XBRL), entailment (judge)
│   ├── evaluation/        # golden_set, adversarial, metrics, runner, datasets/   ← headline
│   ├── db/                # async engine/session, SQLAlchemy models
│   └── workers/           # scheduled ingestion jobs
├── alembic/               # migrations
├── observability/         # prometheus, loki, tempo, alloy, grafana (provisioned)
├── docs/                  # architecture, observability, ADRs
├── tests/                 # unit / integration / eval
├── reports/               # eval report output (committed for quality history)
├── pyproject.toml         # uv-managed
├── docker-compose.yml     # full local stack
└── Makefile               # the verbs you actually type
```

---

## Honest caveats (stated deliberately — this is itself a maturity signal)

- **This is not production-shippable inside a bank, and that's not the goal.** Regulated KYC/research
  systems live under model-risk governance (e.g. SR 11-7) that forbids an autonomous agent emitting
  billable artifacts. This system is built to demonstrate that I understand *why* — hence the verifier
  gate, abstention, re-fetchable provenance, and the human-in-the-loop interrupts.
- **XBRL is ground truth for tagged facts, not everything.** Footnote-only and non-GAAP figures are
  exactly where it gets hard; the adversarial set targets that, and the verifier *abstains* rather than
  guesses when XBRL is silent.
- **SEC EDGAR is free under fair-access limits** — declare a `SEC_USER_AGENT`, throttle to ~10 req/s.
  The ingestion layer enforces this.
- **Period/context resolution is the subtle part**, not the agent loop. Picking the right filing,
  the right fiscal period, and the right context ref is where errors hide; `resolve_filing` gets a
  human-in-the-loop interrupt on ambiguity for that reason.

---

## License

MIT (code). SEC data is public domain; respect EDGAR fair-access terms.
```

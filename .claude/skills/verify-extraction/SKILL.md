---
name: verify-extraction
description: >-
  Walk an extracted item through the verifier gate — citation re-resolution, XBRL
  reconciliation, and (for narrative claims) entailment — to decide
  accepted / flagged / abstained. Use when asked how/why an item passed or failed
  verification, or to debug a verdict.
---

# verify-extraction — the verifier gate

> **Status: PLACEHOLDER (citation + reconcile land in M3, entailment in M5).**
> `src/verification/` is empty scaffold. Do not assert verdicts yet. See
> `PROJECT_PLAN.md` M3/M5.

## Intended behavior (spec)

The gate is the load-bearing rule of the whole system: **an extraction is
accepted only if (a) its source locator re-resolves and (b) its value reconciles
to XBRL within tolerance; otherwise it is flagged or abstained. Never emit an
ungrounded number.**

Three checks, in order:

1. **Citation resolution (mechanical)** — the locator (`accession_no`,
   `statement_role`, `context_ref`, `char_span`) re-resolves in EDGAR/XBRL.
   No resolution → **fail**.
2. **Reconciliation (mechanical)** — extracted value equals the XBRL fact within
   tolerance, accounting for sign, scale/units (thousands/millions/as-reported),
   GAAP vs non-GAAP, and restatement-aware period matching.
3. **Entailment (LLM judge, `claude-opus-4-8`)** — for *narrative* claims only
   (not numbers), the cited passage must actually support the claim, not merely
   share a topic.

Verdict ∈ `accepted | flagged | abstained`. When XBRL is **silent**, abstain —
do not guess.

## When implementing for real

Document the locator contract, the tolerance rules per concept, how remediation
re-runs failing items, and how verdicts surface in the API response.

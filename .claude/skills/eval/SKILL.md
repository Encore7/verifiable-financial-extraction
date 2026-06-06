---
name: eval
description: >-
  Run the evaluation harness — the headline artifact — and report extraction
  accuracy, hallucinated-figure rate, abstention rate, and cost/latency on the
  golden (and later adversarial) sets. Use when asked to evaluate, measure
  quality, check for regressions, or read an eval report.
---

# eval — evaluation harness

> **Status: PLACEHOLDER (lands in M3, hardened in M5/M7).** The runner and
> datasets do not exist yet — `src/evaluation/` is empty scaffold. Do not claim
> eval results until this is implemented. See `PROJECT_PLAN.md` M3.

## Intended behavior (spec)

```bash
make eval          # runs evaluation.runner over the golden set
```

- Execute the agent over each `(CIK, form, fiscal_year)` case in
  `src/evaluation/datasets/golden/`, compare to XBRL ground truth (exact, not
  human-judged), and emit a metrics table to `reports/<timestamp>.md`.
- Metrics: extraction accuracy (within tolerance), **hallucinated-figure rate
  (target 0.0%)**, abstention rate, verifier precision/recall, cost/filing,
  latency p50/p95.
- Deterministic with a fixed seed → reproducible.
- M5 adds the adversarial set; M7 runs a fixed slice in CI and **fails the build**
  if accuracy drops below threshold or hallucinated-figure rate > 0.

## When implementing this skill for real

Replace this spec with: how to invoke the runner, how to point it at golden vs
adversarial, how to parse `reports/<ts>.md`, and how to diff against the last
committed report to flag regressions.

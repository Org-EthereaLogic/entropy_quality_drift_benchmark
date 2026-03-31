---
description: Review implementation against benchmark semantics, governance, and runtime behavior.
---

# Review

Review a change or scope against this repository's benchmark contract.

## Variables

spec_or_scope: $ARGUMENTS

## Review Checks

- Gate behavior matches `configs/kpi_thresholds.json`
- Benchmarks remain deterministic for a given seed
- Evidence remains append-only
- Baseline and challenger logic remain separated
- Public docs match current runtime behavior

## Validation

```bash
ruff check src tests docs
pytest tests/ -v --tb=short
python -m entropy_quality_drift.runners.benchmark --seed 42 --rows 1000
```

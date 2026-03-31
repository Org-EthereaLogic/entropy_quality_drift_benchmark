# CLAUDE.md — Entropy Quality & Drift Benchmark

## Project Overview

This repository is a public, entropy-only benchmark for comparing:

1. `EntropyForge` against Deequ-style rules for data quality validation
2. `EntropySentinel` against KS-test / Evidently-style drift detection

The repository is benchmark-first. Claims must remain proportional to the
evidence produced by the current harness.

## Non-Negotiable Rules

- No UMIF primitives, formulas, or references
- No client data or identifiers
- No credentials or secret material
- No destructive mutation of evidence bundles in `runs/`
- No benchmark claim without replayable command evidence

## Decision Order

1. `CLAUDE.md`
2. `AGENTS.md`
3. `configs/kpi_thresholds.json`
4. `README.md`

## Build and Verification

```bash
pip install -e ".[dev]"
ruff check src tests docs
pytest tests/ -v --tb=short
python -m entropy_quality_drift.runners.benchmark --seed 42 --rows 1000
```

## Key Conventions

- Package path: `src/entropy_quality_drift/`
- Benchmarks are deterministic for a given seed and config
- `configs/kpi_thresholds.json` is the gate source of truth
- `runs/` stores append-only JSON evidence bundles
- `.claude/commands/` stores reusable Claude command surfaces
- `.claude/agents/` stores reusable agent briefs, including cleanup and examination specialists

## File Map

| Path | Purpose |
| --- | --- |
| `src/entropy_quality_drift/contracts/` | Typed result and gate contracts |
| `src/entropy_quality_drift/baselines/` | Baseline adapter interfaces and implementations |
| `src/entropy_quality_drift/challengers/` | Entropy challengers |
| `src/entropy_quality_drift/datasets/` | Deterministic synthetic data and fault injection |
| `src/entropy_quality_drift/metrics/` | JSON-driven gate evaluation |
| `src/entropy_quality_drift/runners/` | Benchmark orchestration and CLI entry point |
| `src/entropy_quality_drift/evidence/` | Append-only evidence bundle writing |
| `src/entropy_quality_drift/databricks_seams/` | Conceptual Databricks seam stubs |
| `docs/` | Databricks walkthrough and supplementary documentation |
| `.github/workflows/` | CI, coverage, and security automation |
| `.claude/commands/` | Claude command definitions |
| `.claude/agents/` | Claude agent briefs |

## Current Local Baseline

The repository should remain green against:

- `ruff check src tests docs`
- `pytest tests/ -v --tb=short`

The benchmark itself currently targets a `WARN` local verdict on the default
seeded run because quality latency and gradual drift sensitivity remain soft
warning bands rather than hard failures.

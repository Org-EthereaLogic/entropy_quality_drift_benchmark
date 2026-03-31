# Claude Code Instructions (Entropy Quality & Drift Benchmark)

## Workspace Intent

This repository is a **public benchmark** proving that Shannon Entropy-based
methods are measurably competitive against industry-standard baselines for
both data quality validation and data drift detection in Databricks medallion
architectures.

## Non-Negotiable Rules

- **No UMIF.** This repository must never contain UMIF formulas, UMIF references,
  UMIF-derived logic, ΔR, dS/dTx, CTM, Tx operators, or any proprietary
  quality/drift scoring methods. Shannon Entropy, KL divergence, and standard
  statistical tests are the only algorithms permitted.
- **No client data.** No ADB, OTSI, or any client-specific data or identifiers.
- **No credentials.** No API keys, tokens, passwords, or connection strings.
- **Public-safe only.** Every file must be safe for public GitHub.

## Architecture Pattern

This project mirrors E61's dual-track benchmark structure:

| E61 Pattern | This Repo Equivalent |
|------------|---------------------|
| DataForge (UMIF quality challenger) | EntropyForge (entropy quality challenger) |
| DriftSentinel (UMIF drift challenger) | EntropySentinel (entropy drift challenger) |
| Deequ rules baseline | Same — Deequ-style rules baseline |
| Evidently KS-test baseline | Same — KS-test drift baseline |
| UMIF primitives (ΔR, Tx, S) | Shannon Entropy, KL divergence, normalized H |

## Decision Order

1. `CLAUDE.md` (this file)
2. `configs/kpi_thresholds.json`
3. `README.md`

## Common Commands

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/
```

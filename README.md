# Entropy Quality & Drift Benchmark

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/a221857e497742c9a6184c21b915f166)](https://app.codacy.com/gh/Org-EthereaLogic/entropy_quality_drift_benchmark?utm_source=github.com&utm_medium=referral&utm_content=Org-EthereaLogic/entropy_quality_drift_benchmark&utm_campaign=Badge_Grade)

### Proving Shannon Entropy-Based Methods Are Competitive Against Industry Baselines for Databricks Medallion Architectures

**Built by [Anthony Johnson](https://www.linkedin.com/in/anthonyjohnsonii/) | EthereaLogic LLC**

---

## What This Is

A formal, reproducible benchmark that evaluates Shannon Entropy-based approaches against industry-standard baselines for two critical Databricks lakehouse concerns:

1. **Data Quality Validation** — EntropyForge (entropy challenger) vs. Deequ-style rules (industry baseline)
2. **Data Drift Detection** — EntropySentinel (entropy challenger) vs. KS-test/Evidently (industry baseline)

The benchmark answers a specific question: **can information-theoretic methods match or exceed standard approaches for data quality and drift detection in Bronze/Silver/Gold pipelines?**

---

## Why This Matters

Standard data quality tools (Deequ, Great Expectations) use rule-based checks: nulls, types, ranges, volumes. These catch **presence** problems. But they miss **distribution** problems:

- A column where 98% of values silently collapse to one default
- A join key that loses uniqueness after an upstream change
- A categorical field that absorbs unexpected new values
- A timestamp column that stops advancing (stale load)

All of these pass null checks, type checks, and range checks. All of them corrupt downstream analytics.

Shannon Entropy measures the *information content* of a column's value distribution. When entropy changes, the distribution has changed — regardless of whether every individual value passes its rules.

---

## Dual-Track Design

### Quality Track

| | Baseline (Deequ) | Challenger (EntropyForge) |
|---|---|---|
| Schema checks | ✅ | ✅ |
| Null rate checks | ✅ | ✅ |
| Range validation | ✅ | ✅ |
| Volume checks | ✅ | ✅ |
| Entropy collapse detection | ❌ | ✅ |
| Cardinality anomaly detection | ❌ | ✅ |
| Constant-column detection | ❌ | ✅ |

**Hypothesis:** EntropyForge matches Deequ precision on structural checks and exceeds Deequ recall on distribution-level anomalies.

### Drift Track

| | Baseline (Evidently/KS-test) | Challenger (EntropySentinel) |
|---|---|---|
| Sudden numeric shift | ✅ | ✅ |
| Sudden categorical shift | ✅ | ✅ |
| Gradual distribution drift | Weak on small samples | ✅ (entropy gradient) |
| New category injection | ✅ (chi-squared) | ✅ (entropy + KL divergence) |
| Single interpretable score | ❌ (per-column p-values) | ✅ (composite health 0–1) |
| Computational cost | O(n log n) sorting | O(n) value counts |

**Hypothesis:** EntropySentinel matches KS-test sensitivity on sudden drift and exceeds it on gradual drift, with lower false positive rate and a single interpretable output.

---

## Gate Definitions

### Quality Track Gates

| Gate | Metric | Condition | Description |
|------|--------|-----------|-------------|
| Q-GATE-1 | precision | >= baseline | Must not produce worse precision than Deequ |
| Q-GATE-2 | recall | >= 0.90 | Must detect >= 90% of injected violations |
| Q-GATE-3 | f1 | >= baseline | Balanced quality score |
| Q-WARN-1 | latency_ratio | <= 2.0x | Should not exceed 2x baseline latency |
| Q-WARN-2 | distribution_detection | >= 0.85 | Must detect >= 85% of distribution anomalies |

### Drift Track Gates

| Gate | Metric | Condition | Description |
|------|--------|-----------|-------------|
| D-GATE-1 | false_positive_rate | <= baseline + 0.05 | Must not produce excess false positives |
| D-GATE-2 | sensitivity | >= 0.85 | Must detect >= 85% of injected drift |
| D-GATE-3 | latency_ratio | <= 2.0x | Detection delay within 2x baseline |
| D-WARN-1 | gradual_drift_sensitivity | >= 0.70 | Gradual drift detection sensitivity |

---

## Project Structure

```
entropy_quality_drift_benchmark/
├── CLAUDE.md                                  # Workspace rules (no UMIF, public-safe)
├── README.md                                  # This file
├── LICENSE                                    # MIT
├── pyproject.toml                             # Python packaging
├── configs/
│   └── kpi_thresholds.json                    # Frozen dual-track gate definitions
├── src/entropy_quality_drift/
│   ├── contracts/__init__.py                  # 12 frozen dataclasses
│   ├── baselines/
│   │   ├── __init__.py                        # Abstract adapter interfaces
│   │   ├── deequ_adapter.py                   # Rule-based quality baseline
│   │   └── evidently_adapter.py               # KS-test drift baseline
│   ├── challengers/
│   │   ├── entropy_forge.py                   # Entropy quality challenger
│   │   └── entropy_sentinel.py                # Entropy gradient drift challenger
│   ├── datasets/
│   │   └── synthetic.py                       # Deterministic data + fault injection
│   ├── metrics/
│   │   └── gate_evaluator.py                  # Dual-track gate evaluation
│   ├── runners/
│   │   └── benchmark.py                       # Full benchmark orchestrator
│   ├── evidence/                              # Append-only evidence bundles
│   └── databricks_seams/                      # CDF reader, ingestion logger stubs
└── tests/
    ├── test_quality_track.py                  # 6 tests — structural parity + entropy advantage
    ├── test_drift_track.py                    # 7 tests — parity + FPR control + entropy advantage
    └── test_benchmark_integration.py          # 5 tests — full benchmark runs
```

---

## Quick Start

### 1. Clone and Install
```bash
git clone https://github.com/anthonyjohnsonii/entropy-quality-drift-benchmark.git
cd entropy-quality-drift-benchmark
pip install -e ".[dev]"
```

### 2. Run All Tests
```bash
pytest tests/ -v
```

### 3. Run the Full Benchmark
```python
from entropy_quality_drift.runners.benchmark import run_benchmark, BenchmarkConfig

result = run_benchmark(BenchmarkConfig(seed=42, n_rows=1000))
print(f"Verdict: {result.verdict}")
print(f"Quality — Baseline F1: {result.quality_baseline.f1}, Challenger F1: {result.quality_challenger.f1}")
print(f"Drift — Baseline FPR: {result.drift_baseline.false_positive_rate}, Challenger FPR: {result.drift_challenger.false_positive_rate}")
```

### 4. Run the Key Proof Test
```bash
pytest tests/test_quality_track.py::TestEntropyAdvantage::test_constant_collapse_deequ_misses_forge_catches -v
```

This single test demonstrates the core value: Deequ passes on collapsed data, EntropyForge catches it.

---

## Evidence Tiers

| Tier | Label | Meaning |
|------|-------|---------|
| 1 | validated | Reproducible, multi-seed, all gates PASS |
| 2 | validated_with_caveat | PASS/WARN, with documented limitations |
| 3 | exploratory | Promising but insufficient for claims |
| 4 | unsupported | No evidence or contradicted |

---

## What This Repo Does NOT Include

- Proprietary algorithms (no UMIF, no ΔR, no dS/dTx, no CTM)
- Client data or identifiers
- Production credentials
- Claims beyond what the benchmark evidence supports

---

## Related Work

- [Project 1: Entropy-Governed Medallion Pipeline Demo](https://github.com/anthonyjohnsonii/entropy-governed-medallion-demo) — Shows the entropy framework applied to a full Bronze/Silver/Gold pipeline
- [Databricks Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Shannon Entropy (Wikipedia)](https://en.wikipedia.org/wiki/Entropy_(information_theory))
- [PyDeequ](https://github.com/awslabs/python-deequ) — Industry-standard quality library
- [Evidently AI](https://www.evidentlyai.com/) — Industry-standard drift detection

---

## Author

**Anthony Johnson** — US-Based Databricks & Enterprise AI Solutions Architect

- LinkedIn: [linkedin.com/in/anthonyjohnsonii](https://www.linkedin.com/in/anthonyjohnsonii/)
- Company: EthereaLogic LLC

---

## License

MIT License. See [LICENSE](LICENSE) for details.

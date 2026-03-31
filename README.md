# Prove Which Data Controls Catch Silent Failures Before Production Dashboards

**Built by [Anthony Johnson](https://www.linkedin.com/in/anthonyjohnsonii/) | EthereaLogic LLC**

`entropy_quality_drift_benchmark` is a public benchmark for comparing data controls that are supposed to stop silent quality degradation and drift before corrupted data reaches KPI dashboards or downstream AI workflows. It gives technology leaders a replayable way to compare established baselines with entropy-based challengers, review a governed verdict, and inspect append-only evidence rather than vendor-style claims.

## Executive Summary

| Leadership question | Answer |
| ------------------- | ------ |
| What business risk does this address? | Data can pass schema, null, and range checks while the business signal degrades underneath, allowing unreliable KPI refreshes or model inputs to reach production. |
| What does the benchmark prove today? | On the verified `seed=42`, `n_rows=1000` benchmark, the entropy quality challenger improves recall from `0.80` to `1.00` and F1 from `0.8889` to `1.00`, while the overall benchmark lands at `WARN` because two advisory thresholds still remain open. |
| Why does this matter for technology leaders? | It provides replayable evidence for whether a new control pattern is strong enough to justify production adoption, budget, and governance attention. |

## The Business Problem

Traditional controls are good at catching structural defects. They are less reliable at catching silent failures, such as a column collapsing to a constant, a categorical mix shifting away from a trusted baseline, or gradual drift degrading model or reporting quality before anyone notices.

That creates a leadership problem, not just an engineering problem. Teams can report a healthy pipeline while the business is already consuming weaker signals. By the time the issue is visible in a dashboard or model outcome, trust has already been spent.

Before adopting a new control pattern, technology leaders need evidence that it improves detection where current methods are weak, and honesty about where it still needs calibration.

## What This Benchmark Proves

The current verified benchmark surface is:

| Verified outcome | Evidence from the seeded benchmark |
| ---------------- | ---------------------------------- |
| Repository verification contract | `ruff check src tests docs` passes and `pytest tests/ -v --tb=short` passes with `29` tests. |
| Quality-track advantage | Baseline recall is `0.80`; entropy challenger recall is `1.00`. Baseline F1 is `0.8889`; entropy challenger F1 is `1.00`. |
| Drift-track parity on the default sudden-drift profile | Baseline and challenger both score `1.00` sensitivity and `0.00` false positive rate. |
| Hard-gate readiness | All hard benchmark gates pass. |
| Remaining gaps | `Q-WARN-1` reports a quality latency ratio of `11.49x` against a `2.0x` target, and `D-WARN-1` reports gradual-drift sensitivity of `0.00` against a `0.70` target. |
| Overall decision surface | The benchmark returns `WARN`, not `FAIL`, because the remaining gaps are advisory rather than hard-gate breaches. |

## Why the Current Result Is WARN, Not FAIL

This benchmark is intentionally governed to avoid false confidence. A `WARN` verdict means the challengers are good enough to pass hard correctness thresholds while still surfacing adoption work that leadership should understand before calling the method production-ready.

In the current seeded run, every hard gate clears. The two open issues are advisory: quality latency is still above the preferred target, and gradual-drift sensitivity still misses the warning threshold. That is why the benchmark is useful as an executive decision tool: it shows progress and remaining risk in the same artifact.

## Verified Results

### Exhibit 1: The Entropy Challenger Closes the Silent Quality-Failure Gap

On the deterministic benchmark run, the entropy challenger maintains perfect precision while improving recall and F1 on the quality track. On the drift track, the challenger matches the baseline on the default sudden-drift scenario but still trails on gradual drift.

<p align="center">
  <img src="docs/images/track_comparison.png" alt="Benchmark chart showing quality advantage for the entropy challenger and drift parity on the default sudden-drift profile" width="900"/>
</p>

### Exhibit 2: All Hard Gates Pass; Two Advisory Thresholds Stay Open

The gate matrix shows the benchmark’s real decision posture. Hard requirements are satisfied, while `Q-WARN-1` and `D-WARN-1` remain open and keep the benchmark in the warning band.

<p align="center">
  <img src="docs/images/gate_evaluation.png" alt="Benchmark gate matrix showing all hard gates passing and two advisory warning gates remaining open" width="900"/>
</p>

### Exhibit 3: The Benchmark Produces a Single Explainable Verdict

The verdict dashboard turns a multi-metric benchmark into a single review surface for leadership and operators. The current outcome is `WARN`: hard requirements are met, but calibration work remains visible.

<p align="center">
  <img src="docs/images/benchmark_verdict.png" alt="Benchmark dashboard showing a WARN verdict with hard requirements met and remaining advisory gaps" width="900"/>
</p>

## How the Benchmark Works

1. Generate deterministic clean, faulted, and drifted batches.
2. Run established baselines and entropy-based challengers on identical inputs.
3. Score both tracks against injected ground truth.
4. Evaluate the result against 10 frozen gates.
5. Write a self-contained evidence bundle so the verdict can be replayed and audited.

Under the hood, the benchmark uses Shannon entropy and KL-divergence-based challengers alongside Deequ-style rules and KS/Evidently-style baselines. The technical details live in [Technical approach](docs/technical-approach.md), while the Databricks deployment mapping lives in [Databricks walkthrough](docs/databricks_walkthrough.md).

## Databricks Fit

Although the benchmark itself runs as pure Python, it maps directly to Databricks-style governance patterns:

- Benchmark quality controls map to Bronze-to-Silver and Silver-to-Gold release checks.
- The frozen gate contract maps to governed thresholds in Unity Catalog or a Delta configuration table.
- Append-only JSON evidence maps to an append-only Delta evidence table.
- The benchmark’s `WARN` / `FAIL` / `PASS` semantics map to production promotion decisions without hiding calibration work.

Use [Databricks walkthrough](docs/databricks_walkthrough.md) for the platform-specific translation.

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Org-EthereaLogic/entropy_quality_drift_benchmark.git
cd entropy_quality_drift_benchmark
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2. Run the repository verification contract

```bash
ruff check src tests docs
pytest tests/ -v --tb=short
```

Expected verified result:

```text
29 passed
```

### 3. Run the seeded benchmark

```bash
python -m entropy_quality_drift.runners.benchmark --seed 42 --rows 1000
```

Key values to confirm in the JSON output:

- `"verdict": "WARN"`
- quality baseline recall `0.8`
- quality challenger recall `1.0`
- drift baseline sensitivity `1.0`
- drift challenger gradual-drift sensitivity `0.0`

### 4. Regenerate the README exhibits

```bash
python -m pip install -e ".[docs]"
python docs/generate_visuals.py
```

### 5. Review the platform mapping

See [Databricks walkthrough](docs/databricks_walkthrough.md) for the production pattern this benchmark is meant to inform.

## Technical References

- Benchmark design, methods, gate contract, and evidence model: [Technical approach](docs/technical-approach.md)
- Databricks mapping and workflow interpretation: [Databricks walkthrough](docs/databricks_walkthrough.md)

## Engineering Signals

<p align="left">
  <a href="https://github.com/Org-EthereaLogic/entropy_quality_drift_benchmark/actions/workflows/ci.yml"><img src="https://github.com/Org-EthereaLogic/entropy_quality_drift_benchmark/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/Org-EthereaLogic/entropy_quality_drift_benchmark"><img src="https://codecov.io/gh/Org-EthereaLogic/entropy_quality_drift_benchmark/graph/badge.svg" alt="Codecov coverage"></a>
  <a href="https://app.codacy.com/gh/Org-EthereaLogic/entropy_quality_drift_benchmark/dashboard"><img src="https://img.shields.io/badge/Codacy-enabled-222222?logo=codacy&logoColor=white" alt="Codacy enabled"></a>
  <a href="https://snyk.io/"><img src="https://img.shields.io/badge/Snyk-code%20scan-4C4A73?logo=snyk&logoColor=white" alt="Snyk code scan"></a>
</p>

## Contributing and Security

- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security disclosures: [SECURITY.md](SECURITY.md)
- Append-only benchmark evidence archive: [runs/README.md](runs/README.md)

## License

MIT License. See [LICENSE](LICENSE) for details.

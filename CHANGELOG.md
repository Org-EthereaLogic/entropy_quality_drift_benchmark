# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed

- Made gate evaluation configuration-driven from `configs/kpi_thresholds.json`, including correct PASS/WARN/FAIL handling for hard-gate warning bands.
- Fixed the entropy drift challenger's clean-vs-clean false-positive behavior by comparing shared-binned numeric distributions and using separate numeric and categorical KL thresholds.
- Made benchmark evidence bundle naming append-only in practice by using timestamped unique filenames.
- Reduced benchmark latency flakiness by measuring median latency over repeated executions.
- Fixed editable installs for the published package by declaring the Hatch wheel package path.

### Changed

- Expanded benchmark scoring to include distribution anomaly detection rate, gradual drift sensitivity, and interpretable single-score coverage.
- Added CLI-ready benchmark execution and updated governance/docs surfaces to match current runtime behavior.
- Updated GitHub Actions automation to publish coverage, run Snyk code scans on `main`, and pin third-party actions to immutable commit SHAs.
- Ported the prior experiment command and agent surfaces into `.claude/commands/` and `.claude/agents/`.

## [0.1.0] — 2026-03-30

### Added

**Quality Track**
- `DeequAdapter` — Deequ-style rules baseline (schema, nulls, ranges, volume)
- `EntropyForge` — Shannon Entropy quality challenger; detects entropy collapse, cardinality anomalies, and constant-column injection
- `QualityCheckResult` / `QualityBatchResult` typed contracts
- `SourceContract`, `ColumnSpec`, `VolumeSpec` frozen dataclasses

**Drift Track**
- `EvidentlyAdapter` — KS-test drift baseline
- `EntropySentinel` — Dual-signal drift challenger (entropy gradient + KL divergence)
- Numeric column binning via quantile-cut for stable cross-batch entropy comparison
- `DriftCheckResult` / `DriftBatchResult` typed contracts with `composite_health` score

**Infrastructure**
- `BenchmarkRunner` — orchestrates dual-track comparison with deterministic seeding
- `GateEvaluator` — evaluates 10 frozen gates (5 quality, 5 drift) from `configs/kpi_thresholds.json`
- `SyntheticDataset` — generates taxi-domain clean/faulted/drifted batches for reproducible experiments
- Evidence bundle writer — JSON run artifacts in `runs/`
- Full test suite: quality track, drift track, integration (end-to-end)
- CI workflow: pytest + ruff on Python 3.10, 3.11, 3.12

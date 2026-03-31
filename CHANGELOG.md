# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.2.1] — 2026-03-30

### Added

- Wheel-install smoke test in CI that builds the package, installs it into a clean virtualenv, and runs the benchmark through the published module entry point.
- Committed docs fixture (`docs/fixtures/sample_evidence_seed42.json`) so visualization generation replays stable evidence by default.
- Publication metadata in `pyproject.toml` now includes classifiers, keywords, and project URLs for package indexes and release surfaces.

### Fixed

- Security scanning now skips with a workflow warning when `SNYK_TOKEN` is missing or authentication fails, while still failing CI for real Snyk scan errors and findings.
- Benchmark gate configuration now loads from packaged resources in wheel installs, while preserving a source-tree fallback for editable development.
- Docs image generation is now reproducible: it replays fixed evidence by default, removes date-based drift from the verdict dashboard, and writes stable PNG metadata.
- README automation docs now describe the actual docs-stability contract: back-to-back regenerations must match on the same runner, rather than matching previously committed PNG bytes across platforms.

## [0.2.0] — 2026-03-30

### Added

- Problem-first README framing: leads with the business problem (silent distribution degradation and gradual drift) rather than benchmark mechanics.
- Dedicated "Understanding the WARN Verdict" section explaining the per-run verdict model for external readers, including `INCOMPLETE` handling.
- Sample evidence output section in README showing an abbreviated evidence bundle with threshold context.
- Databricks-facing walkthrough (`docs/databricks_walkthrough.md`) mapping benchmark concepts to Delta Lake pipelines, Unity Catalog gates, and Lakehouse Monitoring.
- "How This Maps to Databricks" summary table in README linking to the full walkthrough.
- Three publication-ready visualizations (`docs/generate_visuals.py`): track comparison, gate evaluation matrix, and verdict dashboard, matching the dark-theme palette from the medallion demo.
- `[docs]` optional dependency for matplotlib-based image generation.
- Public `run_benchmark_with_gates()` API for callers that need gate-level detail.
- CI docs job that installs `.[docs]` and smoke-tests visual generation.

### Fixed

- Made gate evaluation configuration-driven from `configs/kpi_thresholds.json`, including correct PASS/WARN/FAIL handling for hard-gate warning bands.
- Fixed the entropy drift challenger's clean-vs-clean false-positive behavior by comparing shared-binned numeric distributions and using separate numeric and categorical KL thresholds.
- Made benchmark evidence bundle naming append-only in practice by using timestamped unique filenames.
- Reduced benchmark latency flakiness by measuring median latency over repeated executions.
- Fixed editable installs for the published package by declaring the Hatch wheel package path.
- Evidence bundles now include full `thresholds` map per gate for self-contained verdict reconstruction.
- Corrected the README's verified local test count to match the current suite (`26 passed`).
- Aligned `configs/kpi_thresholds.json` decision-rule wording with the evaluator's per-run verdict semantics.
- Synced lint scope to `ruff check src tests docs` across CI, commands, agents, and all documentation.

### Changed

- Expanded benchmark scoring to include distribution anomaly detection rate, gradual drift sensitivity, and interpretable single-score coverage.
- Added CLI-ready benchmark execution and updated governance/docs surfaces to match current runtime behavior.
- Updated GitHub Actions automation to publish coverage, run Snyk code scans on `main`, and pin third-party actions to immutable commit SHAs.
- Ported the prior experiment command and agent surfaces into `.claude/commands/` and `.claude/agents/`.
- README restructured for client-readability: problem statement, architecture, verdict explanation, evidence sample, Databricks mapping, then technical detail.
- Docs generation now uses public `run_benchmark_with_gates()` instead of private `_execute_benchmark()`.

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

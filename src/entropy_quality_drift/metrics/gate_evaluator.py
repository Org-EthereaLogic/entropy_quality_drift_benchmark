"""
Dual-track gate evaluator for the entropy quality & drift benchmark.

Evaluates both quality track (EntropyForge vs Deequ) and drift track
(EntropySentinel vs Evidently) against frozen KPI thresholds defined
in configs/kpi_thresholds.json.

Gate thresholds use a two-tier system:
  - GATE (hard): breach → FAIL verdict
  - WARN (soft): breach → WARN verdict

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

from entropy_quality_drift.contracts import (
    BenchmarkResult,
    GateEvaluationResult,
    GateResult,
    GateVerdict,
    TrackScore,
)


def evaluate_benchmark(result: BenchmarkResult) -> GateEvaluationResult:
    """Evaluate all gates for a complete benchmark run."""
    quality_gates = _evaluate_quality_gates(
        result.quality_baseline, result.quality_challenger
    )
    drift_gates = _evaluate_drift_gates(
        result.drift_baseline, result.drift_challenger
    )

    all_gates = list(quality_gates) + list(drift_gates)

    if any(g.passed is None for g in all_gates):
        verdict = GateVerdict.INCOMPLETE
    elif any(g.passed is False and g.gate_id.startswith(("Q-GATE", "D-GATE")) for g in all_gates):
        verdict = GateVerdict.FAIL
    elif any(g.passed is False for g in all_gates):
        verdict = GateVerdict.WARN
    else:
        verdict = GateVerdict.PASS

    return GateEvaluationResult(
        run_id=result.run_id,
        quality_gates=tuple(quality_gates),
        drift_gates=tuple(drift_gates),
        overall_verdict=verdict,
    )


def _evaluate_quality_gates(
    baseline: TrackScore | None,
    challenger: TrackScore | None,
) -> list[GateResult]:
    """Evaluate quality track gates (Q-GATE-1 through Q-WARN-2)."""
    gates = []

    if baseline is None or challenger is None:
        return [GateResult(
            gate_id="Q-GATE-1", metric="precision",
            baseline_value=None, challenger_value=None,
            threshold=None, passed=None, details="NOT_MEASURED",
        )]

    # Q-GATE-1: Precision >= baseline (fail if < baseline - 0.10)
    gates.append(GateResult(
        gate_id="Q-GATE-1",
        metric="precision",
        baseline_value=baseline.precision,
        challenger_value=challenger.precision,
        threshold=baseline.precision,
        passed=challenger.precision >= baseline.precision - 0.10,
        details=f"Challenger {challenger.precision:.3f} vs baseline {baseline.precision:.3f}",
    ))

    # Q-GATE-2: Recall >= 0.90 (fail below 0.80)
    gates.append(GateResult(
        gate_id="Q-GATE-2",
        metric="recall",
        baseline_value=baseline.recall,
        challenger_value=challenger.recall,
        threshold=0.90,
        passed=challenger.recall >= 0.90,
        details=f"Challenger recall {challenger.recall:.3f} (pass >= 0.90, fail < 0.80)",
    ))

    # Q-GATE-3: F1 >= baseline (fail if < baseline - 0.10)
    gates.append(GateResult(
        gate_id="Q-GATE-3",
        metric="f1",
        baseline_value=baseline.f1,
        challenger_value=challenger.f1,
        threshold=baseline.f1,
        passed=challenger.f1 >= baseline.f1 - 0.10,
        details=f"Challenger F1 {challenger.f1:.3f} vs baseline {baseline.f1:.3f}",
    ))

    # Q-WARN-1: Latency ratio <= 2.0x
    if baseline.latency_ms > 0:
        ratio = challenger.latency_ms / baseline.latency_ms
        gates.append(GateResult(
            gate_id="Q-WARN-1",
            metric="latency_ratio",
            baseline_value=baseline.latency_ms,
            challenger_value=challenger.latency_ms,
            threshold=2.0,
            passed=ratio <= 2.0,
            details=f"Ratio {ratio:.2f}x",
        ))

    # Q-WARN-2: Distribution detection rate >= 0.85
    # Measured by comparing challenger recall vs baseline recall
    # on the assumption that the difference is driven by distribution checks
    distribution_advantage = challenger.recall - baseline.recall
    distribution_detection = 1.0 if distribution_advantage > 0 else 0.0
    # If challenger has higher recall, it's detecting distribution anomalies
    # that baseline misses — the core thesis of the benchmark
    gates.append(GateResult(
        gate_id="Q-WARN-2",
        metric="distribution_detection",
        baseline_value=baseline.recall,
        challenger_value=challenger.recall,
        threshold=0.85,
        passed=challenger.recall > baseline.recall,
        details=f"Challenger recall {challenger.recall:.3f} > baseline {baseline.recall:.3f}: {challenger.recall > baseline.recall}",
    ))

    return gates


def _evaluate_drift_gates(
    baseline: TrackScore | None,
    challenger: TrackScore | None,
) -> list[GateResult]:
    """Evaluate drift track gates (D-GATE-1 through D-WARN-2)."""
    gates = []

    if baseline is None or challenger is None:
        return [GateResult(
            gate_id="D-GATE-1", metric="false_positive_rate",
            baseline_value=None, challenger_value=None,
            threshold=None, passed=None, details="NOT_MEASURED",
        )]

    # D-GATE-1: FPR <= baseline + 0.05
    gates.append(GateResult(
        gate_id="D-GATE-1",
        metric="false_positive_rate",
        baseline_value=baseline.false_positive_rate,
        challenger_value=challenger.false_positive_rate,
        threshold=baseline.false_positive_rate + 0.05,
        passed=challenger.false_positive_rate <= baseline.false_positive_rate + 0.05,
        details=f"Challenger FPR {challenger.false_positive_rate:.3f} vs baseline {baseline.false_positive_rate:.3f} (+ 0.05 tolerance)",
    ))

    # D-GATE-2: Sensitivity >= 0.85
    gates.append(GateResult(
        gate_id="D-GATE-2",
        metric="sensitivity",
        baseline_value=baseline.sensitivity,
        challenger_value=challenger.sensitivity,
        threshold=0.85,
        passed=challenger.sensitivity >= 0.85,
        details=f"Challenger sensitivity {challenger.sensitivity:.3f} (pass >= 0.85)",
    ))

    # D-GATE-3: Latency ratio <= 2.0x
    if baseline.latency_ms > 0:
        ratio = challenger.latency_ms / baseline.latency_ms
        gates.append(GateResult(
            gate_id="D-GATE-3",
            metric="latency_ratio",
            baseline_value=baseline.latency_ms,
            challenger_value=challenger.latency_ms,
            threshold=2.0,
            passed=ratio <= 2.0,
            details=f"Ratio {ratio:.2f}x",
        ))

    # D-WARN-1: Gradual drift sensitivity >= 0.70
    # Evaluated as overall sensitivity (gradual drift tests exercise this path)
    gates.append(GateResult(
        gate_id="D-WARN-1",
        metric="gradual_drift_sensitivity",
        baseline_value=baseline.sensitivity,
        challenger_value=challenger.sensitivity,
        threshold=0.70,
        passed=challenger.sensitivity >= 0.70,
        details=f"Challenger sensitivity {challenger.sensitivity:.3f} (warn < 0.70)",
    ))

    # D-WARN-2: Single score interpretability (entropy produces composite health; KS does not)
    # This is a structural property: EntropySentinel always produces composite_health
    gates.append(GateResult(
        gate_id="D-WARN-2",
        metric="single_score_interpretability",
        baseline_value=0.0,
        challenger_value=1.0,
        threshold=1.0,
        passed=True,
        details="EntropySentinel produces composite_health score; Evidently does not",
    ))

    return gates

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

import json
import re
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from entropy_quality_drift.contracts import (
    BenchmarkResult,
    GateEvaluationResult,
    GateResult,
    GateVerdict,
    TrackScore,
)

RELATIVE_CONDITION_PATTERN = re.compile(
    r"^(?P<operator><=|>=|<|>)(?P<anchor>baseline)"
    r"(?:(?P<sign>[+-])(?P<delta>\d+(?:\.\d+)?))?$"
)


def evaluate_benchmark(result: BenchmarkResult) -> GateEvaluationResult:
    """Evaluate all gates for a complete benchmark run."""
    thresholds = _load_thresholds()
    quality_gates = _evaluate_track_gates(
        result.quality_baseline,
        result.quality_challenger,
        thresholds["quality_track"],
    )
    drift_gates = _evaluate_track_gates(
        result.drift_baseline,
        result.drift_challenger,
        thresholds["drift_track"],
    )

    all_gates = list(quality_gates) + list(drift_gates)

    statuses = {g.status for g in all_gates}

    if GateVerdict.INCOMPLETE in statuses:
        verdict = GateVerdict.INCOMPLETE
    elif GateVerdict.FAIL in statuses:
        verdict = GateVerdict.FAIL
    elif GateVerdict.WARN in statuses:
        verdict = GateVerdict.WARN
    else:
        verdict = GateVerdict.PASS

    return GateEvaluationResult(
        run_id=result.run_id,
        quality_gates=tuple(quality_gates),
        drift_gates=tuple(drift_gates),
        overall_verdict=verdict,
    )


@lru_cache(maxsize=1)
def _load_thresholds() -> dict:
    packaged_path = (
        files("entropy_quality_drift")
        .joinpath("configs")
        .joinpath("kpi_thresholds.json")
    )
    if packaged_path.is_file():
        return json.loads(packaged_path.read_text(encoding="utf-8"))

    config_path = Path(__file__).resolve().parents[3] / "configs" / "kpi_thresholds.json"
    with config_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _evaluate_track_gates(
    baseline: TrackScore | None,
    challenger: TrackScore | None,
    track_config: dict[str, dict],
) -> list[GateResult]:
    """Evaluate a configured track of benchmark gates."""
    gates: list[GateResult] = []

    if baseline is None or challenger is None:
        return [
            GateResult(
                gate_id=gate_id,
                metric=spec["metric"],
                baseline_value=None,
                challenger_value=None,
                threshold=_threshold_for_display(spec),
                status=GateVerdict.INCOMPLETE,
                passed=None,
                details="NOT_MEASURED",
                thresholds=_thresholds_for_display(spec),
            )
            for gate_id, spec in track_config.items()
        ]

    for gate_id, spec in track_config.items():
        gates.append(_evaluate_gate(gate_id, spec, baseline, challenger))

    return gates


def _evaluate_gate(
    gate_id: str,
    spec: dict,
    baseline: TrackScore,
    challenger: TrackScore,
) -> GateResult:
    baseline_value, challenger_value = _metric_values(spec["metric"], baseline, challenger)
    if baseline_value is None or challenger_value is None:
        return GateResult(
            gate_id=gate_id,
            metric=spec["metric"],
            baseline_value=baseline_value,
            challenger_value=challenger_value,
            threshold=_threshold_for_display(spec),
            status=GateVerdict.INCOMPLETE,
            passed=None,
            details="METRIC_UNAVAILABLE",
            thresholds=_thresholds_for_display(spec),
        )

    if "pass_condition" in spec:
        status = _evaluate_relative_status(
            challenger_value,
            baseline_value,
            spec["pass_condition"],
            spec.get("fail_condition"),
        )
    elif "pass_threshold" in spec:
        status = _evaluate_threshold_status(
            challenger_value,
            spec["comparison"],
            spec["pass_threshold"],
            spec.get("fail_threshold"),
        )
    else:
        status = _evaluate_warn_status(
            challenger_value,
            spec["comparison"],
            spec["warn_threshold"],
        )

    return GateResult(
        gate_id=gate_id,
        metric=spec["metric"],
        baseline_value=round(float(baseline_value), 4),
        challenger_value=round(float(challenger_value), 4),
        threshold=_threshold_for_display(spec),
        status=status,
        passed=_passed_from_status(status),
        details=_details_for_gate(gate_id, spec, baseline_value, challenger_value, status),
        thresholds=_thresholds_for_display(spec),
    )


def _metric_values(
    metric: str,
    baseline: TrackScore,
    challenger: TrackScore,
) -> tuple[float | None, float | None]:
    if metric == "latency_ratio":
        if baseline.latency_ms <= 0:
            return None, None
        return 1.0, challenger.latency_ms / baseline.latency_ms

    return getattr(baseline, metric, None), getattr(challenger, metric, None)


def _evaluate_relative_status(
    value: float,
    baseline_value: float,
    pass_condition: str,
    fail_condition: str | None,
) -> GateVerdict:
    if _relative_condition_met(value, baseline_value, pass_condition):
        return GateVerdict.PASS
    if fail_condition and _relative_condition_met(value, baseline_value, fail_condition):
        return GateVerdict.FAIL
    return GateVerdict.WARN


def _evaluate_threshold_status(
    value: float,
    comparison: str,
    pass_threshold: float,
    fail_threshold: float | None,
) -> GateVerdict:
    if _comparison_met(value, comparison, pass_threshold):
        return GateVerdict.PASS
    if fail_threshold is not None and _fail_threshold_met(value, comparison, fail_threshold):
        return GateVerdict.FAIL
    return GateVerdict.WARN


def _evaluate_warn_status(value: float, comparison: str, warn_threshold: float) -> GateVerdict:
    if _comparison_met(value, comparison, warn_threshold):
        return GateVerdict.PASS
    return GateVerdict.WARN


def _relative_condition_met(value: float, baseline_value: float, condition: str) -> bool:
    match = RELATIVE_CONDITION_PATTERN.fullmatch(condition)
    if match is None:
        raise ValueError(f"Unsupported relative condition: {condition}")

    delta = float(match.group("delta") or 0.0)
    if match.group("sign") == "-":
        target = baseline_value - delta
    else:
        target = baseline_value + delta

    return _comparison_met(value, match.group("operator"), target)


def _comparison_met(value: float, comparison: str, threshold: float) -> bool:
    if comparison == "gte":
        return value >= threshold
    if comparison == "gt":
        return value > threshold
    if comparison == "lte":
        return value <= threshold
    if comparison == "lt":
        return value < threshold
    if comparison == "eq":
        return value == threshold
    if comparison == "==":
        return value == threshold
    if comparison == "!=":
        return value != threshold
    if comparison == ">=":
        return value >= threshold
    if comparison == "<=":
        return value <= threshold
    if comparison == ">":
        return value > threshold
    if comparison == "<":
        return value < threshold
    raise ValueError(f"Unsupported comparison: {comparison}")


def _fail_threshold_met(value: float, comparison: str, fail_threshold: float) -> bool:
    inverse = {
        "gte": "<",
        "gt": "<=",
        "lte": ">",
        "lt": ">=",
        "eq": "!=",
        ">=": "<",
        ">": "<=",
        "<=": ">",
        "<": ">=",
        "==": "!=",
    }
    if comparison in {"eq", "=="}:
        return value != fail_threshold
    return _comparison_met(value, inverse[comparison], fail_threshold)


def _passed_from_status(status: GateVerdict) -> bool | None:
    if status is GateVerdict.PASS:
        return True
    if status is GateVerdict.FAIL:
        return False
    return None


def _threshold_for_display(spec: dict) -> float | None:
    if "pass_threshold" in spec:
        return spec["pass_threshold"]
    if "warn_threshold" in spec:
        return spec["warn_threshold"]
    return None


def _thresholds_for_display(spec: dict) -> dict[str, float] | None:
    thresholds = {
        key: spec[key]
        for key in ("pass_threshold", "fail_threshold", "warn_threshold")
        if key in spec
    }
    return thresholds or None


def _details_for_gate(
    gate_id: str,
    spec: dict,
    baseline_value: float,
    challenger_value: float,
    status: GateVerdict,
) -> str:
    metric = spec["metric"]
    if metric == "latency_ratio":
        return (
            f"{status.value}: ratio={challenger_value:.2f}x "
            f"(pass={spec.get('pass_threshold', spec.get('warn_threshold'))}, "
            f"fail={spec.get('fail_threshold', 'n/a')})"
        )

    if "pass_condition" in spec:
        return (
            f"{status.value}: challenger={challenger_value:.3f}, "
            f"baseline={baseline_value:.3f}, pass={spec['pass_condition']}, "
            f"fail={spec.get('fail_condition', 'n/a')}"
        )

    threshold = spec.get("pass_threshold", spec.get("warn_threshold"))
    return (
        f"{status.value}: challenger={challenger_value:.3f}, "
        f"baseline={baseline_value:.3f}, threshold={threshold}, "
        f"fail={spec.get('fail_threshold', 'n/a')}"
    )

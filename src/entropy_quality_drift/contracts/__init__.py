"""Typed contracts for source specifications, check results, and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# --- Source contract ---

@dataclass(frozen=True)
class ColumnSpec:
    """Specification for a single source column."""
    name: str
    dtype: str  # "int64", "float64", "string", "datetime64"
    nullable: bool = True
    valid_range: Optional[tuple[float, float]] = None
    allowed_values: Optional[tuple[str, ...]] = None


@dataclass(frozen=True)
class VolumeSpec:
    expected_rows_per_batch: tuple[int, int] = (100, 100000)
    max_null_rate: float = 0.05


@dataclass(frozen=True)
class SourceContract:
    """Typed source contract for a Bronze table."""
    source_name: str
    columns: tuple[ColumnSpec, ...]
    volume: VolumeSpec = field(default_factory=VolumeSpec)
    primary_key: Optional[str] = None


# --- Check results (mirrors E61 base.py) ---

@dataclass(frozen=True)
class QualityCheckResult:
    check_name: str
    status: str  # PASS | WARN | FAIL
    observed_value: float
    threshold: float
    details: str = ""


@dataclass(frozen=True)
class QualityBatchResult:
    batch_id: str
    checks: tuple[QualityCheckResult, ...]
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    latency_ms: float = 0.0

    @property
    def overall_status(self) -> str:
        statuses = [c.status for c in self.checks]
        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses:
            return "WARN"
        return "PASS"


@dataclass(frozen=True)
class DriftCheckResult:
    feature_name: str
    drifted: bool
    score: float
    threshold: float
    method: str
    details: str = ""


@dataclass(frozen=True)
class DriftBatchResult:
    batch_id: str
    checks: tuple[DriftCheckResult, ...]
    false_positive_rate: float = 0.0
    sensitivity: float = 0.0
    latency_ms: float = 0.0

    @property
    def any_drift_detected(self) -> bool:
        return any(c.drifted for c in self.checks)

    @property
    def composite_health(self) -> float:
        """Single 0-1 health score: 1.0 = no drift, 0.0 = max drift.

        Computed as 1 - mean(per-feature drift scores). Features that
        are not drifted contribute 0.0 to the mean; drifted features
        contribute their normalized score.
        """
        if not self.checks:
            return 1.0
        mean_score = sum(c.score for c in self.checks) / len(self.checks)
        return round(max(0.0, 1.0 - mean_score), 4)


# --- Benchmark scoring ---

@dataclass(frozen=True)
class TrackScore:
    """Score for one track (quality or drift) in one run."""
    track: str  # "quality" | "drift"
    adapter_name: str
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    false_positive_rate: float = 0.0
    sensitivity: float = 0.0
    distribution_detection_rate: float = 0.0
    gradual_drift_sensitivity: float = 0.0
    single_score_interpretability: float = 0.0
    latency_ms: float = 0.0
    batches_evaluated: int = 0


@dataclass(frozen=True)
class BenchmarkResult:
    """Full benchmark result comparing baseline vs challenger."""
    run_id: str
    seed: int
    quality_baseline: Optional[TrackScore] = None
    quality_challenger: Optional[TrackScore] = None
    drift_baseline: Optional[TrackScore] = None
    drift_challenger: Optional[TrackScore] = None
    verdict: str = "INCOMPLETE"  # PASS | WARN | FAIL | INCOMPLETE


# --- Gate evaluation ---

class GateVerdict(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    metric: str
    baseline_value: Optional[float]
    challenger_value: Optional[float]
    threshold: Optional[float]
    status: GateVerdict
    passed: Optional[bool]
    details: str = ""


@dataclass(frozen=True)
class GateEvaluationResult:
    run_id: str
    quality_gates: tuple[GateResult, ...]
    drift_gates: tuple[GateResult, ...]
    overall_verdict: GateVerdict

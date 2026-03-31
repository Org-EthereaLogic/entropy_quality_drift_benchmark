"""
Benchmark runner for the entropy quality & drift benchmark.

Orchestrates the dual-track comparison:
1. Generate clean + faulted datasets (deterministic seeds)
2. Run baseline adapters (Deequ, Evidently)
3. Run challenger adapters (EntropyForge, EntropySentinel)
4. Score both tracks against ground truth
5. Evaluate gates
6. Write evidence bundle

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from statistics import median
from typing import Optional

from entropy_quality_drift.baselines.deequ_adapter import DeequAdapter
from entropy_quality_drift.baselines.evidently_adapter import EvidentlyAdapter
from entropy_quality_drift.challengers.entropy_forge import EntropyForge
from entropy_quality_drift.challengers.entropy_sentinel import EntropySentinel
from entropy_quality_drift.contracts import (
    BenchmarkResult,
    GateEvaluationResult,
    TrackScore,
)
from entropy_quality_drift.datasets.synthetic import (
    TAXI_CONTRACT,
    DriftProfile,
    FaultProfile,
    generate_clean_batch,
    inject_drift,
    inject_quality_faults,
)
from entropy_quality_drift.evidence import write_evidence_bundle
from entropy_quality_drift.metrics.gate_evaluator import evaluate_benchmark

# Columns that are meaningful features for quality/drift evaluation.
# Excludes primary keys (trip_id) and timestamps (pickup/dropoff_datetime)
# which are identifiers, not distributional features.
FEATURE_COLUMNS = {"trip_distance", "fare_amount", "pickup_zone", "dropoff_zone", "payment_type"}


@dataclass
class BenchmarkConfig:
    seed: int = 42
    n_rows: int = 1000
    quality_fault_profile: Optional[FaultProfile] = None
    drift_profile: Optional[DriftProfile] = None
    gradual_drift_profile: Optional[DriftProfile] = None
    evidence_dir: str = "runs"
    latency_repetitions: int = 3


def run_benchmark(config: Optional[BenchmarkConfig] = None) -> BenchmarkResult:
    """Execute the full dual-track benchmark."""
    cfg = config or BenchmarkConfig()
    final, _ = _execute_benchmark(cfg)
    return final


def run_benchmark_with_gates(
    config: Optional[BenchmarkConfig] = None,
) -> tuple[BenchmarkResult, GateEvaluationResult]:
    """Execute the benchmark and return both the result and gate evaluation.

    This is the public entry point for callers (such as docs generation)
    that need access to gate-level detail without reaching into private
    runner internals.
    """
    cfg = config or BenchmarkConfig()
    return _execute_benchmark(cfg)


def _execute_benchmark(cfg: BenchmarkConfig):
    """Run the benchmark once and return both the result and evaluated gates."""

    run_id = f"bench_{cfg.seed}"

    # 1. Generate datasets
    clean_df = generate_clean_batch(n_rows=cfg.n_rows, seed=cfg.seed)

    fault_profile = cfg.quality_fault_profile or FaultProfile(
        null_injection_rate=0.08,
        null_columns=("fare_amount", "pickup_zone"),
        range_violation_rate=0.05,
        range_violation_columns=("trip_distance", "fare_amount"),
        constant_collapse_columns=("payment_type",),
        constant_collapse_value="credit",
        duplicate_rate=0.03,
    )
    faulted_df = inject_quality_faults(clean_df, fault_profile, seed=cfg.seed)

    drift_profile = cfg.drift_profile or DriftProfile(
        distribution_shift_columns=("fare_amount", "trip_distance", "pickup_zone"),
        shift_magnitude=0.6,
        category_injection_columns=("payment_type",),
        new_categories=("crypto", "voucher"),
    )
    drifted_df = inject_drift(clean_df, drift_profile, seed=cfg.seed + 1)
    gradual_profile = cfg.gradual_drift_profile or DriftProfile(
        distribution_shift_columns=("fare_amount", "trip_distance"),
        shift_magnitude=0.3,
        gradual=True,
    )
    gradual_drifted_df = inject_drift(clean_df, gradual_profile, seed=cfg.seed + 2)

    # Build ground truth sets for scoring
    quality_ground_truth = _build_quality_ground_truth(
        fault_profile,
        primary_key=TAXI_CONTRACT.primary_key,
    )
    quality_distribution_ground_truth = set(fault_profile.constant_collapse_columns)
    drift_ground_truth = _build_drift_ground_truth(drift_profile)
    gradual_drift_ground_truth = _build_drift_ground_truth(gradual_profile)

    # 2. Run quality track
    quality_baseline_score = _run_quality_adapter(
        DeequAdapter(),
        faulted_df,
        "quality_baseline",
        quality_ground_truth,
        quality_distribution_ground_truth,
        cfg.latency_repetitions,
    )
    quality_challenger_score = _run_quality_adapter(
        EntropyForge(
            expected_high_cardinality_columns={"trip_id"},
            expected_low_cardinality_columns={"payment_type"},
        ),
        faulted_df,
        "quality_challenger",
        quality_ground_truth,
        quality_distribution_ground_truth,
        cfg.latency_repetitions,
    )

    # 3. Run drift track
    drift_baseline_score = _run_drift_adapter(
        EvidentlyAdapter(),
        clean_df,
        drifted_df,
        gradual_drifted_df,
        "drift_baseline",
        drift_ground_truth,
        gradual_drift_ground_truth,
        cfg.latency_repetitions,
    )
    drift_challenger_score = _run_drift_adapter(
        EntropySentinel(),
        clean_df,
        drifted_df,
        gradual_drifted_df,
        "drift_challenger",
        drift_ground_truth,
        gradual_drift_ground_truth,
        cfg.latency_repetitions,
    )

    # 4. Assemble result
    result = BenchmarkResult(
        run_id=run_id,
        seed=cfg.seed,
        quality_baseline=quality_baseline_score,
        quality_challenger=quality_challenger_score,
        drift_baseline=drift_baseline_score,
        drift_challenger=drift_challenger_score,
    )

    # 5. Evaluate gates
    gate_result = evaluate_benchmark(result)

    final = BenchmarkResult(
        run_id=run_id,
        seed=cfg.seed,
        quality_baseline=quality_baseline_score,
        quality_challenger=quality_challenger_score,
        drift_baseline=drift_baseline_score,
        drift_challenger=drift_challenger_score,
        verdict=gate_result.overall_verdict.value,
    )

    # 6. Write evidence bundle
    write_evidence_bundle(final, gate_result, cfg)

    return final, gate_result


def _build_quality_ground_truth(
    profile: FaultProfile,
    primary_key: str | None = None,
) -> set[str]:
    """Build the set of column names where quality faults were injected.

    A column in this set SHOULD produce at least one FAIL check from
    a properly functioning quality adapter.
    """
    faulted_columns: set[str] = set()
    for col in profile.null_columns:
        faulted_columns.add(col)
    for col in profile.range_violation_columns:
        faulted_columns.add(col)
    for col in profile.constant_collapse_columns:
        faulted_columns.add(col)
    for col in profile.schema_drop_columns:
        faulted_columns.add(col)
    if profile.duplicate_rate > 0 and primary_key is not None:
        faulted_columns.add(primary_key)
    return faulted_columns


def _build_drift_ground_truth(profile: DriftProfile) -> set[str]:
    """Build the set of column names where drift was injected."""
    drifted_columns: set[str] = set()
    for col in profile.distribution_shift_columns:
        drifted_columns.add(col)
    for col in profile.category_injection_columns:
        drifted_columns.add(col)
    return drifted_columns


def _run_quality_adapter(
    adapter,
    faulted_df,
    label: str,
    ground_truth: set[str],
    distribution_ground_truth: set[str],
    latency_repetitions: int,
) -> TrackScore:
    """Run a quality adapter and compute precision/recall/F1 using ground truth.

    Ground truth defines which *columns* have injected faults. A check
    is a true positive if it FAILs on a faulted column, and a false
    positive if it FAILs on a clean column.
    """
    result, latency_ms = _measure_quality_adapter(
        adapter, faulted_df, label, latency_repetitions
    )

    checks = result.checks
    if not checks:
        return TrackScore(track="quality", adapter_name=adapter.adapter_name)

    # Extract the column name from each check_name (e.g., "null_rate.fare_amount" → "fare_amount")
    def _check_column(check_name: str) -> str:
        parts = check_name.split(".")
        return parts[-1] if len(parts) > 1 else check_name

    detected_faulted_columns: set[str] = set()
    flagged_clean_columns: set[str] = set()

    for check in checks:
        col = _check_column(check.check_name)
        if check.status == "FAIL":
            if col in ground_truth:
                detected_faulted_columns.add(col)
            else:
                flagged_clean_columns.add(col)

    tp = len(detected_faulted_columns)
    fp = len(flagged_clean_columns)
    fn = len(ground_truth - detected_faulted_columns)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    distribution_detection_rate = _rate(
        detected_faulted_columns & distribution_ground_truth,
        distribution_ground_truth,
    )

    return TrackScore(
        track="quality",
        adapter_name=adapter.adapter_name,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        distribution_detection_rate=round(distribution_detection_rate, 4),
        latency_ms=latency_ms,
        batches_evaluated=1,
    )


def _run_drift_adapter(
    adapter,
    clean_df,
    drifted_df,
    gradual_drifted_df,
    label: str,
    ground_truth: set[str],
    gradual_ground_truth: set[str],
    latency_repetitions: int,
) -> TrackScore:
    """Run a drift adapter and compute sensitivity/FPR using ground truth.

    Ground truth defines which columns had drift injected.
    Sensitivity = proportion of truly drifted feature columns detected.
    FPR = proportion of clean feature columns falsely flagged.
    """
    drift_result, clean_result, latency_ms = _measure_drift_adapter(
        adapter,
        clean_df,
        drifted_df,
        label,
        latency_repetitions,
    )
    adapter.set_reference(clean_df)
    gradual_result = adapter.check_drift(
        gradual_drifted_df,
        clean_df,
        batch_id=f"{label}_gradual",
    )

    # Sensitivity: proportion of truly drifted features correctly detected
    # Only count features in FEATURE_COLUMNS to exclude IDs/timestamps
    drifted_checks = {
        c.feature_name: c for c in drift_result.checks
        if c.feature_name in FEATURE_COLUMNS
    }
    truly_drifted = ground_truth & FEATURE_COLUMNS
    n_detected = sum(
        1 for col in truly_drifted
        if col in drifted_checks and drifted_checks[col].drifted
    )
    sensitivity = n_detected / len(truly_drifted) if truly_drifted else 0.0

    # FPR: proportion of clean feature columns falsely flagged on clean data
    # FPR on clean-vs-clean: any flagged feature is a false positive
    all_clean_checks = [c for c in clean_result.checks if c.feature_name in FEATURE_COLUMNS]
    n_fp_clean = sum(1 for c in all_clean_checks if c.drifted)
    fpr = n_fp_clean / len(all_clean_checks) if all_clean_checks else 0.0
    gradual_sensitivity = _drift_sensitivity(gradual_result.checks, gradual_ground_truth)

    return TrackScore(
        track="drift",
        adapter_name=adapter.adapter_name,
        sensitivity=round(sensitivity, 4),
        false_positive_rate=round(fpr, 4),
        gradual_drift_sensitivity=round(gradual_sensitivity, 4),
        single_score_interpretability=1.0 if "entropy_sentinel" in adapter.adapter_name else 0.0,
        latency_ms=latency_ms,
        batches_evaluated=2,
    )


def _measure_quality_adapter(adapter, batch, label: str, repeats: int):
    latencies = []
    result = None
    for attempt in range(repeats):
        result = adapter.validate_batch(batch, TAXI_CONTRACT, batch_id=f"{label}_{attempt + 1}")
        latencies.append(result.latency_ms)
    return result, round(median(latencies), 4)


def _measure_drift_adapter(adapter, clean_df, drifted_df, label: str, repeats: int):
    latencies = []
    drift_result = None
    clean_result = None
    for attempt in range(repeats):
        adapter.set_reference(clean_df)
        drift_result = adapter.check_drift(
            drifted_df,
            clean_df,
            batch_id=f"{label}_drifted_{attempt + 1}",
        )
        adapter.set_reference(clean_df)
        clean_result = adapter.check_drift(
            clean_df,
            clean_df,
            batch_id=f"{label}_clean_{attempt + 1}",
        )
        latencies.append(drift_result.latency_ms + clean_result.latency_ms)
    return drift_result, clean_result, round(median(latencies), 4)


def _drift_sensitivity(checks, ground_truth: set[str]) -> float:
    drifted_checks = {c.feature_name: c for c in checks if c.feature_name in FEATURE_COLUMNS}
    truly_drifted = ground_truth & FEATURE_COLUMNS
    detected = sum(
        1 for col in truly_drifted if col in drifted_checks and drifted_checks[col].drifted
    )
    return detected / len(truly_drifted) if truly_drifted else 1.0


def _rate(detected: set[str], ground_truth: set[str]) -> float:
    if not ground_truth:
        return 1.0
    return len(detected) / len(ground_truth)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point for local benchmark execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed.")
    parser.add_argument("--rows", type=int, default=1000, help="Rows per synthetic batch.")
    parser.add_argument(
        "--evidence-dir",
        default="runs",
        help="Directory for append-only JSON evidence bundles.",
    )
    args = parser.parse_args(argv)

    result, gate_result = _execute_benchmark(
        BenchmarkConfig(
            seed=args.seed,
            n_rows=args.rows,
            evidence_dir=args.evidence_dir,
        )
    )
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "seed": result.seed,
                "verdict": result.verdict,
                "quality": {
                    "baseline": (
                        result.quality_baseline.__dict__
                        if result.quality_baseline
                        else None
                    ),
                    "challenger": (
                        result.quality_challenger.__dict__
                        if result.quality_challenger
                        else None
                    ),
                },
                "drift": {
                    "baseline": result.drift_baseline.__dict__ if result.drift_baseline else None,
                    "challenger": (
                        result.drift_challenger.__dict__
                        if result.drift_challenger
                        else None
                    ),
                },
                "gates": {
                    "quality": [
                        {
                            "gate_id": gate.gate_id,
                            "threshold": gate.threshold,
                            "thresholds": gate.thresholds,
                            "status": gate.status.value,
                            "details": gate.details,
                        }
                        for gate in gate_result.quality_gates
                    ],
                    "drift": [
                        {
                            "gate_id": gate.gate_id,
                            "threshold": gate.threshold,
                            "thresholds": gate.thresholds,
                            "status": gate.status.value,
                            "details": gate.details,
                        }
                        for gate in gate_result.drift_gates
                    ],
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Append-only evidence bundles.

Writes structured JSON evidence for each successful benchmark run to the
``runs/`` directory. Evidence is never overwritten — each run produces
a new timestamped file.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

EVIDENCE_SCHEMA_VERSION = 2


if TYPE_CHECKING:
    from entropy_quality_drift.contracts import BenchmarkResult, GateEvaluationResult
    from entropy_quality_drift.runners.benchmark import BenchmarkConfig


def write_evidence_bundle(
    result: "BenchmarkResult",
    gate_result: "GateEvaluationResult",
    config: "BenchmarkConfig",
) -> str:
    """Write a JSON evidence bundle for one benchmark run.

    Returns the filepath written. Evidence write failures are raised so
    callers cannot report a completed benchmark without an audit trail.
    """
    bundle = {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "run_id": result.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": result.seed,
        "n_rows": config.n_rows,
        "verdict": result.verdict,
        "quality_track": {
            "baseline": _score_dict(result.quality_baseline),
            "challenger": _score_dict(result.quality_challenger),
        },
        "drift_track": {
            "baseline": _score_dict(result.drift_baseline),
            "challenger": _score_dict(result.drift_challenger),
        },
        "gates": {
            "quality": [
                {
                    "gate_id": g.gate_id,
                    "metric": g.metric,
                    "baseline": g.baseline_value,
                    "challenger": g.challenger_value,
                    "threshold": g.threshold,
                    "thresholds": g.thresholds,
                    "status": g.status.value,
                    "passed": g.passed,
                    "details": g.details,
                }
                for g in gate_result.quality_gates
            ],
            "drift": [
                {
                    "gate_id": g.gate_id,
                    "metric": g.metric,
                    "baseline": g.baseline_value,
                    "challenger": g.challenger_value,
                    "threshold": g.threshold,
                    "thresholds": g.thresholds,
                    "status": g.status.value,
                    "passed": g.passed,
                    "details": g.details,
                }
                for g in gate_result.drift_gates
            ],
        },
        "overall_verdict": gate_result.overall_verdict.value,
    }

    evidence_dir = config.evidence_dir
    try:
        os.makedirs(evidence_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        suffix = uuid4().hex[:8]
        filepath = os.path.join(evidence_dir, f"{result.run_id}_{ts}_{suffix}.json")
        with open(filepath, "x", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2)
        return filepath
    except OSError as exc:
        raise RuntimeError(
            f"Failed to write benchmark evidence bundle to '{evidence_dir}': {exc}"
        ) from exc


def _score_dict(score) -> dict | None:
    if score is None:
        return None
    return {
        "adapter": score.adapter_name,
        "precision": score.precision,
        "recall": score.recall,
        "f1": score.f1,
        "false_positive_rate": score.false_positive_rate,
        "sensitivity": score.sensitivity,
        "distribution_detection_rate": score.distribution_detection_rate,
        "gradual_drift_sensitivity": score.gradual_drift_sensitivity,
        "single_score_interpretability": score.single_score_interpretability,
        "latency_ms": round(score.latency_ms, 2),
        "batches_evaluated": score.batches_evaluated,
    }

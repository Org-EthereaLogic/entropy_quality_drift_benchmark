"""
Evidently-style KS-test drift detection baseline.

Uses the two-sample Kolmogorov-Smirnov test for numeric features
and chi-squared test for categorical features — the industry-standard
approach to drift detection.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from entropy_quality_drift.baselines import BaseDriftAdapter
from entropy_quality_drift.contracts import DriftBatchResult, DriftCheckResult


class EvidentlyAdapter(BaseDriftAdapter):
    """KS-test / chi-squared drift detection baseline."""

    def __init__(self, p_value_threshold: float = 0.05):
        self.p_value_threshold = p_value_threshold
        self._reference: Optional[pd.DataFrame] = None

    @property
    def adapter_name(self) -> str:
        return "evidently_ks_baseline"

    def set_reference(self, reference: pd.DataFrame) -> None:
        self._reference = reference.copy()

    def check_drift(
        self,
        current: pd.DataFrame,
        reference: pd.DataFrame,
        batch_id: str,
    ) -> DriftBatchResult:
        ref = reference if self._reference is None else self._reference
        start = time.monotonic()
        checks: list[DriftCheckResult] = []

        common_cols = sorted(set(current.columns) & set(ref.columns))

        for col in common_cols:
            ref_col = ref[col].dropna()
            cur_col = current[col].dropna()

            if len(ref_col) == 0 or len(cur_col) == 0:
                continue

            if pd.api.types.is_numeric_dtype(ref_col):
                check = self._ks_test(col, ref_col, cur_col)
            else:
                check = self._chi2_test(col, ref_col, cur_col)

            checks.append(check)

        elapsed_ms = (time.monotonic() - start) * 1000

        return DriftBatchResult(
            batch_id=batch_id,
            checks=tuple(checks),
            latency_ms=elapsed_ms,
        )

    def _ks_test(
        self, col_name: str, ref: pd.Series, cur: pd.Series
    ) -> DriftCheckResult:
        """Two-sample KS test for numeric features."""
        statistic, p_value = stats.ks_2samp(ref, cur)
        drifted = p_value < self.p_value_threshold

        return DriftCheckResult(
            feature_name=col_name,
            drifted=drifted,
            score=float(statistic),
            threshold=self.p_value_threshold,
            method="ks_2samp",
            details=f"KS stat={statistic:.4f}, p={p_value:.6f}",
        )

    def _chi2_test(
        self, col_name: str, ref: pd.Series, cur: pd.Series
    ) -> DriftCheckResult:
        """Chi-squared test for categorical features."""
        all_cats = sorted(set(ref.unique()) | set(cur.unique()))

        ref_counts = ref.value_counts()
        cur_counts = cur.value_counts()

        ref_freq = np.array([ref_counts.get(c, 0) for c in all_cats], dtype=float)
        cur_freq = np.array([cur_counts.get(c, 0) for c in all_cats], dtype=float)

        # Add small epsilon to avoid zero-frequency issues
        ref_freq += 1e-10
        cur_freq += 1e-10

        # Normalize to same total
        ref_freq = ref_freq * (cur_freq.sum() / ref_freq.sum())

        statistic, p_value = stats.chisquare(cur_freq, ref_freq)
        drifted = p_value < self.p_value_threshold

        return DriftCheckResult(
            feature_name=col_name,
            drifted=drifted,
            score=float(statistic),
            threshold=self.p_value_threshold,
            method="chi2",
            details=f"Chi2 stat={statistic:.4f}, p={p_value:.6f}",
        )

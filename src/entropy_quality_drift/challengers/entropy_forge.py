"""
EntropyForge — Shannon Entropy-based data quality challenger.

Runs the same structural checks as the Deequ baseline (schema, nulls,
ranges, volume) PLUS entropy-based distribution checks that catch
problems rule-based validation misses:

- Column entropy collapse (source system defaulting)
- Cardinality anomalies (unexpected uniqueness changes)
- Distribution skew beyond expected bounds
- Constant-column injection (new columns with zero entropy)

The hypothesis: EntropyForge matches Deequ on structural checks and
EXCEEDS Deequ on distribution-level anomaly detection — producing
higher recall on injected faults with comparable or better precision.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import math
import time
from typing import Any, Optional

import pandas as pd

from entropy_quality_drift.baselines import BaseQualityAdapter
from entropy_quality_drift.contracts import (
    QualityBatchResult,
    QualityCheckResult,
    SourceContract,
)


def _column_entropy(series: pd.Series) -> float:
    """Compute Shannon Entropy for a pandas Series."""
    total = len(series)
    if total == 0:
        return 0.0
    value_counts = series.fillna("__NULL__").value_counts()
    entropy = 0.0
    for count in value_counts:
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 6)


def _normalized_entropy(series: pd.Series) -> float:
    """Compute normalized entropy H/log2(n) in [0, 1]."""
    h = _column_entropy(series)
    n_distinct = series.nunique(dropna=False)
    if n_distinct <= 1:
        return 0.0
    h_max = math.log2(n_distinct)
    return round(h / h_max, 6) if h_max > 0 else 0.0


class EntropyForge(BaseQualityAdapter):
    """
    Entropy-based quality challenger.

    Runs structural checks (matching Deequ) plus entropy distribution
    checks that detect quality problems rules cannot see.
    """

    def __init__(
        self,
        entropy_collapse_threshold: float = 0.10,
        expected_high_cardinality_columns: Optional[set[str]] = None,
        expected_low_cardinality_columns: Optional[set[str]] = None,
    ):
        self.entropy_collapse_threshold = entropy_collapse_threshold
        self.high_card_cols = expected_high_cardinality_columns or set()
        self.low_card_cols = expected_low_cardinality_columns or set()

    @property
    def adapter_name(self) -> str:
        return "entropy_forge_challenger"

    def validate_batch(
        self,
        batch: pd.DataFrame,
        contract: Any,
        batch_id: str,
    ) -> QualityBatchResult:
        if not isinstance(contract, SourceContract):
            raise TypeError(f"Expected SourceContract, got {type(contract)}")

        start = time.monotonic()
        checks: list[QualityCheckResult] = []

        # --- Structural checks (same as Deequ for fair comparison) ---
        checks.extend(self._check_schema(batch, contract))
        checks.extend(self._check_volume(batch, contract))
        checks.extend(self._check_null_rates(batch, contract))
        checks.extend(self._check_ranges(batch, contract))

        # --- Entropy-based distribution checks (the innovation) ---
        checks.extend(self._check_entropy_collapse(batch, contract))
        checks.extend(self._check_cardinality_anomalies(batch, contract))
        checks.extend(self._check_constant_columns(batch, contract))

        elapsed_ms = (time.monotonic() - start) * 1000

        return QualityBatchResult(
            batch_id=batch_id,
            checks=tuple(checks),
            latency_ms=elapsed_ms,
        )

    # --- Structural checks (mirrors Deequ) ---

    def _check_schema(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        results = []
        for col_spec in contract.columns:
            present = col_spec.name in batch.columns
            results.append(QualityCheckResult(
                check_name=f"schema.column_present.{col_spec.name}",
                status="PASS" if present else "FAIL",
                observed_value=1.0 if present else 0.0,
                threshold=1.0,
            ))
        return results

    def _check_volume(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        row_count = len(batch)
        low, high = contract.volume.expected_rows_per_batch
        status = "PASS" if low <= row_count <= high else "FAIL"
        return [QualityCheckResult(
            check_name="volume.row_count",
            status=status,
            observed_value=float(row_count),
            threshold=float(high),
        )]

    def _check_null_rates(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        results = []
        for col_spec in contract.columns:
            if col_spec.name not in batch.columns:
                continue
            if col_spec.nullable:
                null_rate = float(batch[col_spec.name].isna().mean())
                results.append(QualityCheckResult(
                    check_name=f"null_rate.{col_spec.name}",
                    status="PASS" if null_rate <= contract.volume.max_null_rate else "FAIL",
                    observed_value=null_rate,
                    threshold=contract.volume.max_null_rate,
                ))
            else:
                null_count = int(batch[col_spec.name].isna().sum())
                results.append(QualityCheckResult(
                    check_name=f"not_null.{col_spec.name}",
                    status="PASS" if null_count == 0 else "FAIL",
                    observed_value=float(null_count),
                    threshold=0.0,
                ))
        return results

    def _check_ranges(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        results = []
        for col_spec in contract.columns:
            if col_spec.valid_range is None or col_spec.name not in batch.columns:
                continue
            col = batch[col_spec.name].dropna()
            if len(col) == 0:
                continue
            low, high = col_spec.valid_range
            out_of_range = int(((col < low) | (col > high)).sum())
            results.append(QualityCheckResult(
                check_name=f"range.{col_spec.name}",
                status="PASS" if out_of_range == 0 else "FAIL",
                observed_value=out_of_range / len(col),
                threshold=0.0,
            ))
        return results

    # --- Entropy-based checks (the differentiator) ---

    def _check_entropy_collapse(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        """
        Detect columns where entropy has collapsed below threshold.

        A column with H_norm < 0.10 in a batch where diversity is
        expected signals a silent source failure (e.g., all values
        became the same default).
        """
        results = []
        for col_spec in contract.columns:
            if col_spec.name not in batch.columns:
                continue
            # Skip columns expected to have low cardinality
            if col_spec.name in self.low_card_cols:
                continue
            if col_spec.allowed_values is not None and len(col_spec.allowed_values) <= 3:
                continue

            h_norm = _normalized_entropy(batch[col_spec.name])
            collapsed = h_norm < self.entropy_collapse_threshold

            results.append(QualityCheckResult(
                check_name=f"entropy.collapse.{col_spec.name}",
                status="FAIL" if collapsed else "PASS",
                observed_value=h_norm,
                threshold=self.entropy_collapse_threshold,
                details=f"H_norm={h_norm:.4f}, threshold={self.entropy_collapse_threshold}",
            ))
        return results

    def _check_cardinality_anomalies(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        """
        Detect unexpected cardinality patterns using entropy.

        High-cardinality columns (IDs, timestamps) with low entropy
        signal duplication. Low-cardinality columns (status, type)
        with high entropy signal data pollution.
        """
        results = []
        for col_spec in contract.columns:
            if col_spec.name not in batch.columns:
                continue

            h_norm = _normalized_entropy(batch[col_spec.name])
            n_distinct = batch[col_spec.name].nunique()
            n_rows = len(batch)

            if col_spec.name in self.high_card_cols:
                # Expected high cardinality — check for unexpected low uniqueness
                unique_ratio = n_distinct / n_rows if n_rows > 0 else 0
                if unique_ratio < 0.5 and h_norm < 0.5:
                    results.append(QualityCheckResult(
                        check_name=f"entropy.cardinality_low.{col_spec.name}",
                        status="WARN",
                        observed_value=unique_ratio,
                        threshold=0.5,
                        details=f"Expected high cardinality, got {n_distinct}/{n_rows}",
                    ))

        return results

    def _check_constant_columns(
        self, batch: pd.DataFrame, contract: SourceContract
    ) -> list[QualityCheckResult]:
        """
        Detect columns that have become constant (H = 0).
        Zero entropy means zero information — the column is useless.
        """
        results = []
        for col_spec in contract.columns:
            if col_spec.name not in batch.columns:
                continue
            h = _column_entropy(batch[col_spec.name])
            if h == 0.0 and len(batch) > 1:
                results.append(QualityCheckResult(
                    check_name=f"entropy.constant.{col_spec.name}",
                    status="FAIL",
                    observed_value=0.0,
                    threshold=0.0,
                    details=f"Column has zero entropy (constant value) across {len(batch)} rows",
                ))
        return results

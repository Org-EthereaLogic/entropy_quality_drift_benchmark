"""
Deequ-style rules-based quality validation baseline.

Implements schema checks, null rate checks, volume checks,
and range checks — the industry-standard approach to data
quality validation in lakehouse environments.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from entropy_quality_drift.baselines import BaseQualityAdapter
from entropy_quality_drift.contracts import (
    QualityBatchResult,
    QualityCheckResult,
    SourceContract,
)


class DeequAdapter(BaseQualityAdapter):
    """Deequ-style rules-based quality validation baseline."""

    @property
    def adapter_name(self) -> str:
        return "deequ_rules_baseline"

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

        checks.extend(self._check_schema(batch, contract))
        checks.extend(self._check_volume(batch, contract))
        checks.extend(self._check_null_rates(batch, contract))
        checks.extend(self._check_ranges(batch, contract))

        elapsed_ms = (time.monotonic() - start) * 1000

        return QualityBatchResult(
            batch_id=batch_id,
            checks=tuple(checks),
            latency_ms=elapsed_ms,
        )

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
                details="" if present else f"Column '{col_spec.name}' missing",
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
            details=f"Expected [{low}, {high}], got {row_count}",
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
                status = "PASS" if null_rate <= contract.volume.max_null_rate else "FAIL"
                results.append(QualityCheckResult(
                    check_name=f"null_rate.{col_spec.name}",
                    status=status,
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
                observed_value=out_of_range / len(col) if len(col) > 0 else 0.0,
                threshold=0.0,
                details=f"{out_of_range} values outside [{low}, {high}]",
            ))
        return results

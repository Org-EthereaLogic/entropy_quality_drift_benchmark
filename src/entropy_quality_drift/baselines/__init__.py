"""Abstract base classes for quality and drift adapters.

Both baselines and challengers implement these interfaces,
ensuring fair apples-to-apples comparison in the benchmark.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from entropy_quality_drift.contracts import (
    QualityBatchResult,
    DriftBatchResult,
)


class BaseQualityAdapter(ABC):
    """Interface for data quality validation adapters."""

    @abstractmethod
    def validate_batch(
        self,
        batch: pd.DataFrame,
        contract: Any,
        batch_id: str,
    ) -> QualityBatchResult:
        """Validate a data batch against a source contract."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Return the adapter name for manifest recording."""


class BaseDriftAdapter(ABC):
    """Interface for data drift detection adapters."""

    @abstractmethod
    def set_reference(self, reference: pd.DataFrame) -> None:
        """Set the reference dataset for drift comparison."""

    @abstractmethod
    def check_drift(
        self,
        current: pd.DataFrame,
        reference: pd.DataFrame,
        batch_id: str,
    ) -> DriftBatchResult:
        """Check for drift between current and reference data."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Return the adapter name for manifest recording."""

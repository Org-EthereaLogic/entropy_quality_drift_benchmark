"""Databricks integration seam stubs.

These adapters let the benchmark run against real Databricks tables
in a production environment. In test/local mode they are not invoked —
the ``datasets.synthetic`` module provides deterministic DataFrames
directly.

When deployed to a Databricks workspace, callers can substitute these
for real implementations without changing the benchmark runner.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class CDFReaderBase(ABC):
    """Seam for reading Databricks Change Data Feed (CDF) streams.

    Implementations read incremental changes from Delta tables so
    the drift detector can compare the previous batch (reference)
    against the latest batch (current) without full-table scans.
    """

    @abstractmethod
    def read_changes(
        self,
        table_name: str,
        starting_version: Optional[int] = None,
        starting_timestamp: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return rows changed since the given version or timestamp."""

    @abstractmethod
    def latest_version(self, table_name: str) -> int:
        """Return the latest Delta version number for a table."""


class IngestionLoggerBase(ABC):
    """Seam for logging benchmark evidence to a Delta table.

    Implementations write evidence bundles into a governed
    ``_benchmark_evidence`` table within the Unity Catalog.
    """

    @abstractmethod
    def log_run(self, evidence: dict) -> None:
        """Append a benchmark evidence record."""


class LocalCDFReader(CDFReaderBase):
    """No-op stub for local/test execution."""

    def read_changes(self, table_name, starting_version=None, starting_timestamp=None):
        raise NotImplementedError(
            "LocalCDFReader is a stub. Use datasets.synthetic for local runs."
        )

    def latest_version(self, table_name):
        return 0


class LocalIngestionLogger(IngestionLoggerBase):
    """No-op stub that silently discards log entries."""

    def log_run(self, evidence: dict) -> None:
        pass  # Evidence is written to JSON files by the evidence module

"""
EntropySentinel — Shannon Entropy gradient drift detection challenger.

Uses per-column entropy comparison between reference and current data
to produce a single interpretable drift score per feature and a
composite health score per batch.

Key advantages over KS-test baseline:
1. Single interpretable score (0-1 health) vs. multiple p-values
2. Catches gradual distribution shifts that KS-test needs large
   samples to detect
3. Computationally cheaper (O(n) value counts vs. O(n log n) sorting)
4. Works equally well on numeric and categorical features
5. Naturally handles high-cardinality columns where KS-test struggles

The hypothesis: EntropySentinel matches KS-test sensitivity on sudden
drift and EXCEEDS it on gradual drift, with lower false positive rate
and a more interpretable output.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

import math
import time
from typing import Optional

import pandas as pd

from entropy_quality_drift.baselines import BaseDriftAdapter
from entropy_quality_drift.contracts import DriftBatchResult, DriftCheckResult


def _column_entropy(series: pd.Series, n_bins: int = 20) -> float:
    """Compute Shannon Entropy for a pandas Series.

    For numeric columns with many unique values, values are binned
    into ``n_bins`` equal-frequency bins before entropy calculation.
    This captures distribution shape without being sensitive to the
    specific sampled values — two independent samples from the same
    distribution will have similar binned entropy.
    """
    total = len(series)
    if total == 0:
        return 0.0

    working = series.fillna("__NULL__")

    # Bin high-cardinality numeric columns into quantiles
    if pd.api.types.is_numeric_dtype(series):
        numeric_only = series.dropna()
        if numeric_only.nunique() > n_bins:
            try:
                binned = pd.qcut(numeric_only, q=n_bins, duplicates="drop")
                working = binned.astype(str)
                # Re-add nulls
                null_count = int(series.isna().sum())
                if null_count > 0:
                    null_entries = pd.Series(["__NULL__"] * null_count)
                    working = pd.concat([working, null_entries], ignore_index=True)
                total = len(working)
            except (ValueError, TypeError):
                pass  # Fall through to raw value counts

    value_counts = working.value_counts()
    entropy = 0.0
    for count in value_counts:
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 6)


def _kl_divergence(ref_series: pd.Series, cur_series: pd.Series) -> float:
    """
    Compute KL divergence D_KL(current || reference).

    Uses smoothed probability distributions to avoid division by zero.
    Higher values indicate greater distribution divergence.
    """
    ref_values, cur_values = _prepare_comparable_series(ref_series, cur_series)
    all_values = sorted(set(ref_values) | set(cur_values))
    n_ref = len(ref_values)
    n_cur = len(cur_values)

    if n_ref == 0 or n_cur == 0:
        return 0.0

    ref_counts = ref_values.value_counts()
    cur_counts = cur_values.value_counts()

    # Laplace smoothing
    alpha = 1e-10
    kl = 0.0
    for val in all_values:
        p = (cur_counts.get(val, 0) + alpha) / (n_cur + alpha * len(all_values))
        q = (ref_counts.get(val, 0) + alpha) / (n_ref + alpha * len(all_values))
        if p > 0 and q > 0:
            kl += p * math.log2(p / q)

    return round(max(0.0, kl), 6)


def _prepare_comparable_series(
    ref_series: pd.Series, cur_series: pd.Series, n_bins: int = 20
) -> tuple[pd.Series, pd.Series]:
    """Return string series with shared bins for comparable distributions."""
    if pd.api.types.is_numeric_dtype(ref_series) and pd.api.types.is_numeric_dtype(cur_series):
        combined = pd.concat([ref_series, cur_series], ignore_index=True)
        numeric = combined.dropna()
        if numeric.nunique() > n_bins:
            try:
                categories = pd.qcut(numeric, q=n_bins, duplicates="drop").astype(str)
                encoded = pd.Series("__NULL__", index=combined.index, dtype="object")
                encoded.loc[numeric.index] = categories.to_numpy()
                split = len(ref_series)
                return (
                    encoded.iloc[:split].reset_index(drop=True),
                    encoded.iloc[split:].reset_index(drop=True),
                )
            except (ValueError, TypeError):
                pass

    return (
        ref_series.fillna("__NULL__").astype(str).reset_index(drop=True),
        cur_series.fillna("__NULL__").astype(str).reset_index(drop=True),
    )


def _is_feature_column(
    ref_col: pd.Series,
    cur_col: pd.Series,
    uniqueness_ceiling: float = 0.95,
) -> bool:
    """Determine whether a column is a meaningful feature for drift detection.

    Columns that are identifiers (near-100% unique values) or datetime
    types are not meaningful targets for distribution-based drift
    detection and produce false positives when compared across
    independently generated batches.
    """
    # Skip datetime columns — entropy comparison on timestamps is meaningless
    if pd.api.types.is_datetime64_any_dtype(ref_col):
        return False

    # Skip columns where almost every value is unique (IDs, keys)
    ref_unique_ratio = ref_col.nunique() / max(len(ref_col), 1)
    cur_unique_ratio = cur_col.nunique() / max(len(cur_col), 1)
    if ref_unique_ratio > uniqueness_ceiling and cur_unique_ratio > uniqueness_ceiling:
        return False

    return True


class EntropySentinel(BaseDriftAdapter):
    """
    Entropy-gradient drift detection challenger.

    Detects drift by comparing per-column Shannon Entropy and
    KL divergence between reference and current data. Produces
    a single composite drift score per batch.
    """

    def __init__(
        self,
        entropy_change_threshold: float = 0.35,
        kl_divergence_threshold: Optional[float] = None,
        numeric_kl_divergence_threshold: float = 0.50,
        categorical_kl_divergence_threshold: float = 1.00,
        skip_high_uniqueness: bool = True,
        uniqueness_ceiling: float = 0.95,
    ):
        self.entropy_change_threshold = entropy_change_threshold
        if kl_divergence_threshold is not None:
            numeric_kl_divergence_threshold = kl_divergence_threshold
            categorical_kl_divergence_threshold = kl_divergence_threshold
        self.numeric_kl_divergence_threshold = numeric_kl_divergence_threshold
        self.categorical_kl_divergence_threshold = categorical_kl_divergence_threshold
        self.skip_high_uniqueness = skip_high_uniqueness
        self.uniqueness_ceiling = uniqueness_ceiling
        self._reference: Optional[pd.DataFrame] = None
        self._reference_entropies: dict[str, float] = {}

    @property
    def adapter_name(self) -> str:
        return "entropy_sentinel_challenger"

    def set_reference(self, reference: pd.DataFrame) -> None:
        """Pre-compute reference entropies for efficient drift detection."""
        self._reference = reference.copy()
        self._reference_entropies = {}
        for col in reference.columns:
            self._reference_entropies[col] = _column_entropy(reference[col])

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
            ref_col = ref[col]
            cur_col = current[col]

            # Skip non-feature columns (IDs, timestamps)
            if self.skip_high_uniqueness and not _is_feature_column(
                ref_col, cur_col, self.uniqueness_ceiling
            ):
                continue

            ref_clean = ref_col.dropna()
            cur_clean = cur_col.dropna()
            if len(ref_clean) == 0 or len(cur_clean) == 0:
                continue

            check = self._entropy_drift_check(col, ref[col], current[col])
            checks.append(check)

        elapsed_ms = (time.monotonic() - start) * 1000

        return DriftBatchResult(
            batch_id=batch_id,
            checks=tuple(checks),
            latency_ms=elapsed_ms,
        )

    def _entropy_drift_check(
        self, col_name: str, ref_col: pd.Series, cur_col: pd.Series
    ) -> DriftCheckResult:
        """
        Dual-signal drift detection using entropy gradient + KL divergence.

        Signal 1: Entropy gradient — detects magnitude of distribution change
        Signal 2: KL divergence — detects directional distribution shift

        A column is flagged as drifted if EITHER signal exceeds its threshold.
        This catches both sudden shifts (KL) and gradual compression (entropy).
        """
        # Signal 1: Entropy gradient
        h_ref = (
            self._reference_entropies.get(col_name)
            if self._reference_entropies
            else _column_entropy(ref_col)
        )
        h_cur = _column_entropy(cur_col)

        if h_ref > 0:
            entropy_change = abs(h_cur - h_ref) / h_ref
        elif h_cur > 0:
            entropy_change = 1.0  # Was constant, now has variation
        else:
            entropy_change = 0.0  # Both constant

        entropy_drifted = entropy_change > self.entropy_change_threshold
        entropy_signal = entropy_change / max(self.entropy_change_threshold, 1e-10)

        # Signal 2: KL divergence
        kl_threshold = (
            self.numeric_kl_divergence_threshold
            if pd.api.types.is_numeric_dtype(ref_col) and pd.api.types.is_numeric_dtype(cur_col)
            else self.categorical_kl_divergence_threshold
        )
        kl_div = _kl_divergence(ref_col, cur_col)
        kl_drifted = kl_div > kl_threshold
        kl_signal = kl_div / max(kl_threshold, 1e-10)

        # Combined decision: either signal triggers drift flag
        drifted = entropy_drifted or kl_drifted

        if entropy_drifted and kl_drifted:
            trigger = "both"
        elif entropy_drifted:
            trigger = "entropy_gradient"
        elif kl_drifted:
            trigger = "kl_divergence"
        else:
            trigger = "entropy_gradient" if entropy_signal >= kl_signal else "kl_divergence"

        active_threshold = (
            self.entropy_change_threshold
            if entropy_signal >= kl_signal
            else kl_threshold
        )

        # Composite score: max of normalized signals (0 = no drift, 1 = max drift)
        score = min(max(entropy_signal, kl_signal), 1.0)

        return DriftCheckResult(
            feature_name=col_name,
            drifted=drifted,
            score=score,
            threshold=active_threshold,
            method="entropy_gradient+kl_divergence",
            details=(
                f"H_ref={h_ref:.4f}, H_cur={h_cur:.4f}, ΔH={entropy_change:.4f}, "
                f"KL={kl_div:.4f}, KL_thr={kl_threshold:.4f}, trigger={trigger}, "
                f"active_thr={active_threshold:.4f}"
            ),
        )

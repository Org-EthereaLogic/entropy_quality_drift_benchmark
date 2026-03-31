"""
Synthetic dataset generation with deterministic fault injection.

Generates taxi-like trip data with controllable quality faults
and distribution drift for benchmarking quality/drift adapters.

All random operations use explicit seeds for full reproducibility.

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from entropy_quality_drift.contracts import ColumnSpec, SourceContract, VolumeSpec

# --- Source contract for the benchmark dataset ---

TAXI_CONTRACT = SourceContract(
    source_name="nyc_taxi_synthetic",
    columns=(
        ColumnSpec(name="trip_id", dtype="string", nullable=False),
        ColumnSpec(name="pickup_datetime", dtype="datetime64", nullable=False),
        ColumnSpec(name="dropoff_datetime", dtype="datetime64", nullable=False),
        ColumnSpec(
            name="trip_distance",
            dtype="float64",
            nullable=False,
            valid_range=(0.01, 200.0),
        ),
        ColumnSpec(name="fare_amount", dtype="float64", nullable=False, valid_range=(0.01, 500.0)),
        ColumnSpec(name="pickup_zone", dtype="string", nullable=True),
        ColumnSpec(name="dropoff_zone", dtype="string", nullable=True),
        ColumnSpec(name="payment_type", dtype="string", nullable=False,
                   allowed_values=("cash", "credit", "debit", "mobile")),
    ),
    volume=VolumeSpec(expected_rows_per_batch=(500, 5000), max_null_rate=0.05),
    primary_key="trip_id",
)


@dataclass
class FaultProfile:
    """Defines what quality faults to inject."""
    null_injection_rate: float = 0.0
    null_columns: tuple[str, ...] = ()
    range_violation_rate: float = 0.0
    range_violation_columns: tuple[str, ...] = ()
    schema_drop_columns: tuple[str, ...] = ()
    constant_collapse_columns: tuple[str, ...] = ()
    constant_collapse_value: str = "DEFAULT"
    duplicate_rate: float = 0.0


@dataclass
class DriftProfile:
    """Defines what distribution drift to inject."""
    distribution_shift_columns: tuple[str, ...] = ()
    shift_magnitude: float = 0.5  # 0 = no shift, 1 = complete shift
    category_injection_columns: tuple[str, ...] = ()
    new_categories: tuple[str, ...] = ()
    gradual: bool = False  # True = gradual drift across batches


ZONES = [
    "Manhattan-Midtown", "Manhattan-Downtown", "Manhattan-Uptown",
    "Brooklyn-Downtown", "Brooklyn-Park Slope", "Queens-Astoria",
    "Queens-LIC", "Bronx-South", "Staten Island", "JFK", "LaGuardia",
    "Newark", "Hoboken", "Jersey City",
]

PAYMENT_TYPES = ["cash", "credit", "debit", "mobile"]


def generate_clean_batch(
    n_rows: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a clean taxi trip dataset with realistic distributions."""
    rng = np.random.default_rng(seed)

    base_date = pd.Timestamp("2026-01-15")
    pickup_offsets = pd.to_timedelta(rng.uniform(0, 86400 * 7, n_rows), unit="s")
    trip_durations = pd.to_timedelta(rng.exponential(900, n_rows), unit="s")

    df = pd.DataFrame({
        "trip_id": [f"T{seed:04d}_{i:06d}" for i in range(n_rows)],
        "pickup_datetime": base_date + pickup_offsets,
        "dropoff_datetime": base_date + pickup_offsets + trip_durations,
        "trip_distance": rng.lognormal(1.2, 0.8, n_rows).round(2),
        "fare_amount": rng.lognormal(2.5, 0.6, n_rows).round(2),
        "pickup_zone": rng.choice(ZONES, n_rows, p=_zone_distribution(rng)),
        "dropoff_zone": rng.choice(ZONES, n_rows, p=_zone_distribution(rng)),
        "payment_type": rng.choice(PAYMENT_TYPES, n_rows, p=[0.15, 0.55, 0.20, 0.10]),
    })

    # Clamp to valid ranges
    df["trip_distance"] = df["trip_distance"].clip(0.1, 100.0)
    df["fare_amount"] = df["fare_amount"].clip(2.50, 300.0)

    return df


def inject_quality_faults(
    df: pd.DataFrame,
    profile: FaultProfile,
    seed: int = 42,
) -> pd.DataFrame:
    """Inject deterministic quality faults into a clean dataset."""
    rng = np.random.default_rng(seed)
    result = df.copy()
    n = len(result)

    # Null injection
    if profile.null_injection_rate > 0:
        for col in profile.null_columns:
            if col in result.columns:
                mask = rng.random(n) < profile.null_injection_rate
                result.loc[mask, col] = None

    # Range violations
    if profile.range_violation_rate > 0:
        for col in profile.range_violation_columns:
            if col in result.columns:
                mask = rng.random(n) < profile.range_violation_rate
                result.loc[mask, col] = -999.99

    # Schema drops
    for col in profile.schema_drop_columns:
        if col in result.columns:
            result = result.drop(columns=[col])

    # Constant collapse (entropy killer)
    for col in profile.constant_collapse_columns:
        if col in result.columns:
            result[col] = profile.constant_collapse_value

    # Duplicate injection
    if profile.duplicate_rate > 0:
        n_dupes = int(n * profile.duplicate_rate)
        dupe_indices = rng.choice(n, n_dupes, replace=True)
        dupes = result.iloc[dupe_indices].copy()
        result = pd.concat([result, dupes], ignore_index=True)

    return result


def inject_drift(
    reference: pd.DataFrame,
    profile: DriftProfile,
    seed: int = 42,
) -> pd.DataFrame:
    """Inject deterministic distribution drift into a dataset."""
    rng = np.random.default_rng(seed)
    result = reference.copy()
    n = len(result)

    for col in profile.distribution_shift_columns:
        if col not in result.columns:
            continue

        if pd.api.types.is_numeric_dtype(result[col]):
            # Shift numeric distribution by magnitude * std
            std = result[col].std()
            shift = profile.shift_magnitude * std * 2
            mask = rng.random(n) < profile.shift_magnitude
            if profile.gradual:
                mask_indices = result.index[mask]
                if len(mask_indices) > 0:
                    gradient = np.linspace(0.2, 1.0, len(mask_indices))
                    rng.shuffle(gradient)
                    result.loc[mask_indices, col] = (
                        result.loc[mask_indices, col].to_numpy() + shift * gradient
                    )
            else:
                result.loc[mask, col] = result.loc[mask, col] + shift
        else:
            # Collapse categorical to fewer values
            unique_vals = result[col].dropna().unique()
            if len(unique_vals) > 1:
                dominant = unique_vals[0]
                mask = rng.random(n) < profile.shift_magnitude
                if profile.gradual:
                    mask_indices = result.index[mask]
                    if len(mask_indices) > 0:
                        gradient = np.linspace(0.2, 1.0, len(mask_indices))
                        threshold = rng.random(len(mask_indices))
                        chosen = mask_indices[threshold < gradient]
                        result.loc[chosen, col] = dominant
                else:
                    result.loc[mask, col] = dominant

    # New category injection
    for col in profile.category_injection_columns:
        if col in result.columns and profile.new_categories:
            n_inject = int(n * 0.15)
            inject_indices = rng.choice(n, n_inject, replace=False)
            new_vals = rng.choice(list(profile.new_categories), n_inject)
            result.loc[inject_indices, col] = new_vals

    return result


def _zone_distribution(rng) -> list[float]:
    """Generate a realistic zone probability distribution."""
    raw = rng.dirichlet(np.ones(len(ZONES)) * 2)
    # Boost Manhattan zones
    raw[0] *= 3
    raw[1] *= 2.5
    raw[2] *= 2
    raw = raw / raw.sum()
    return raw.tolist()

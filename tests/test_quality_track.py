"""Quality track tests: EntropyForge vs Deequ baseline."""

from entropy_quality_drift.baselines.deequ_adapter import DeequAdapter
from entropy_quality_drift.challengers.entropy_forge import EntropyForge
from entropy_quality_drift.datasets.synthetic import (
    TAXI_CONTRACT,
    FaultProfile,
    generate_clean_batch,
    inject_quality_faults,
)


class TestStructuralParity:
    """EntropyForge must match Deequ on all structural checks."""

    def test_clean_data_both_pass(self):
        df = generate_clean_batch(n_rows=500, seed=42)
        deequ = DeequAdapter().validate_batch(df, TAXI_CONTRACT, "clean")
        forge = EntropyForge().validate_batch(df, TAXI_CONTRACT, "clean")

        assert deequ.overall_status == "PASS"
        assert forge.overall_status == "PASS"

    def test_null_injection_both_detect(self):
        df = generate_clean_batch(n_rows=500, seed=42)
        faulted = inject_quality_faults(
            df,
            FaultProfile(
                null_injection_rate=0.20,
                null_columns=("fare_amount",),
            ),
            seed=42,
        )

        deequ = DeequAdapter().validate_batch(faulted, TAXI_CONTRACT, "nulls")
        forge = EntropyForge().validate_batch(faulted, TAXI_CONTRACT, "nulls")

        deequ_fails = [c for c in deequ.checks if c.status == "FAIL"]
        forge_fails = [c for c in forge.checks if c.status == "FAIL"]

        assert len(deequ_fails) > 0
        assert len(forge_fails) >= len(deequ_fails)

    def test_range_violation_both_detect(self):
        df = generate_clean_batch(n_rows=500, seed=42)
        faulted = inject_quality_faults(
            df,
            FaultProfile(
                range_violation_rate=0.15,
                range_violation_columns=("trip_distance",),
            ),
            seed=42,
        )

        deequ = DeequAdapter().validate_batch(faulted, TAXI_CONTRACT, "range")
        forge = EntropyForge().validate_batch(faulted, TAXI_CONTRACT, "range")

        deequ_range = [c for c in deequ.checks if "range" in c.check_name and c.status == "FAIL"]
        forge_range = [c for c in forge.checks if "range" in c.check_name and c.status == "FAIL"]

        assert len(deequ_range) > 0
        assert len(forge_range) > 0

    def test_duplicate_primary_key_both_detect(self):
        df = generate_clean_batch(n_rows=500, seed=42)
        faulted = inject_quality_faults(
            df,
            FaultProfile(
                duplicate_rate=0.05,
            ),
            seed=42,
        )

        deequ = DeequAdapter().validate_batch(faulted, TAXI_CONTRACT, "dupes")
        forge = EntropyForge().validate_batch(faulted, TAXI_CONTRACT, "dupes")

        deequ_dup = [c for c in deequ.checks if c.check_name == "uniqueness.trip_id"]
        forge_dup = [c for c in forge.checks if c.check_name == "uniqueness.trip_id"]

        assert len(deequ_dup) == 1 and deequ_dup[0].status == "FAIL"
        assert len(forge_dup) == 1 and forge_dup[0].status == "FAIL"


class TestEntropyAdvantage:
    """EntropyForge catches problems that Deequ cannot."""

    def test_constant_collapse_deequ_misses_forge_catches(self):
        """
        THE KEY TEST: When payment_type collapses to a single value,
        Deequ sees valid data (no nulls, valid type). EntropyForge
        detects the entropy collapse.
        """
        df = generate_clean_batch(n_rows=500, seed=42)
        faulted = inject_quality_faults(
            df,
            FaultProfile(
                constant_collapse_columns=("payment_type",),
                constant_collapse_value="credit",
            ),
            seed=42,
        )

        deequ = DeequAdapter().validate_batch(faulted, TAXI_CONTRACT, "collapse")
        forge = EntropyForge().validate_batch(faulted, TAXI_CONTRACT, "collapse")

        # Deequ should PASS — no structural violations
        deequ_payment_fails = [
            c for c in deequ.checks if "payment_type" in c.check_name and c.status == "FAIL"
        ]

        # EntropyForge should FAIL — detects entropy collapse or constant column
        forge_entropy_fails = [
            c
            for c in forge.checks
            if ("entropy" in c.check_name or "constant" in c.check_name)
            and "payment_type" in c.check_name
            and c.status == "FAIL"
        ]

        assert len(deequ_payment_fails) == 0, "Deequ should not detect constant collapse"
        assert len(forge_entropy_fails) > 0, "EntropyForge should detect constant collapse"

    def test_schema_drop_both_detect(self):
        """When a column is dropped, both adapters should FAIL the schema check."""
        df = generate_clean_batch(n_rows=500, seed=42)
        faulted = inject_quality_faults(
            df,
            FaultProfile(
                schema_drop_columns=("dropoff_zone",),
            ),
            seed=42,
        )

        deequ = DeequAdapter().validate_batch(faulted, TAXI_CONTRACT, "drop")
        forge = EntropyForge().validate_batch(faulted, TAXI_CONTRACT, "drop")

        deequ_schema_fails = [
            c
            for c in deequ.checks
            if "schema" in c.check_name and "dropoff_zone" in c.check_name and c.status == "FAIL"
        ]
        forge_schema_fails = [
            c
            for c in forge.checks
            if "schema" in c.check_name and "dropoff_zone" in c.check_name and c.status == "FAIL"
        ]

        assert len(deequ_schema_fails) > 0, "Deequ should detect dropped column"
        assert len(forge_schema_fails) > 0, "EntropyForge should detect dropped column"

    def test_deterministic_across_seeds(self):
        """Same seed produces same results."""
        df1 = generate_clean_batch(n_rows=500, seed=42)
        df2 = generate_clean_batch(n_rows=500, seed=42)

        forge = EntropyForge()
        r1 = forge.validate_batch(df1, TAXI_CONTRACT, "seed1")
        r2 = forge.validate_batch(df2, TAXI_CONTRACT, "seed2")

        assert len(r1.checks) == len(r2.checks)
        for c1, c2 in zip(r1.checks, r2.checks):
            assert c1.status == c2.status
            assert c1.observed_value == c2.observed_value

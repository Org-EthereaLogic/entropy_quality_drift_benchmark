"""Drift track tests: EntropySentinel vs Evidently KS-test baseline."""

from entropy_quality_drift.baselines.evidently_adapter import EvidentlyAdapter
from entropy_quality_drift.challengers.entropy_sentinel import EntropySentinel
from entropy_quality_drift.datasets.synthetic import (
    DriftProfile,
    generate_clean_batch,
    inject_drift,
)


class TestSuddenDriftParity:
    """EntropySentinel must match Evidently on sudden distribution shifts."""

    def test_both_detect_sudden_numeric_shift(self):
        ref = generate_clean_batch(n_rows=1000, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                distribution_shift_columns=("fare_amount",),
                shift_magnitude=0.8,
            ),
            seed=99,
        )

        evidently = EvidentlyAdapter()
        evidently.set_reference(ref)
        ev_result = evidently.check_drift(drifted, ref, "sudden")

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        es_result = sentinel.check_drift(drifted, ref, "sudden")

        ev_fare = [c for c in ev_result.checks if c.feature_name == "fare_amount"]
        es_fare = [c for c in es_result.checks if c.feature_name == "fare_amount"]

        assert len(ev_fare) > 0 and ev_fare[0].drifted, "Evidently should detect sudden fare drift"
        assert len(es_fare) > 0 and es_fare[0].drifted, (
            "EntropySentinel should detect sudden fare drift"
        )

    def test_both_detect_categorical_shift(self):
        ref = generate_clean_batch(n_rows=1000, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                distribution_shift_columns=("pickup_zone",),
                shift_magnitude=0.9,
            ),
            seed=99,
        )

        evidently = EvidentlyAdapter()
        evidently.set_reference(ref)
        ev_result = evidently.check_drift(drifted, ref, "cat_shift")

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        es_result = sentinel.check_drift(drifted, ref, "cat_shift")

        ev_zone = [c for c in ev_result.checks if c.feature_name == "pickup_zone"]
        es_zone = [c for c in es_result.checks if c.feature_name == "pickup_zone"]

        assert len(ev_zone) > 0 and ev_zone[0].drifted
        assert len(es_zone) > 0 and es_zone[0].drifted


class TestFalsePositiveControl:
    """EntropySentinel must not flag clean data as drifted."""

    def test_no_drift_on_identical_data(self):
        ref = generate_clean_batch(n_rows=1000, seed=42)

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        result = sentinel.check_drift(ref, ref, "identical")

        n_false_positive = sum(1 for c in result.checks if c.drifted)
        fpr = n_false_positive / len(result.checks) if result.checks else 0.0

        assert fpr == 0.0, f"FPR on identical data should be 0, got {fpr}"

    def test_low_fpr_on_same_distribution(self):
        """Two independent samples from same distribution — FPR should be low.

        EntropySentinel filters out high-uniqueness columns (IDs, timestamps)
        that produce false positives from sampling variance on irrelevant
        features, then applies calibrated thresholds on feature columns.
        """
        ref = generate_clean_batch(n_rows=1000, seed=42)
        current = generate_clean_batch(n_rows=1000, seed=99)

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        result = sentinel.check_drift(current, ref, "same_dist")

        n_false_positive = sum(1 for c in result.checks if c.drifted)
        fpr = n_false_positive / len(result.checks) if result.checks else 0.0

        # Allow up to 20% FPR on independent samples (sampling variance)
        assert fpr <= 0.20, f"FPR too high on same-distribution data: {fpr}"


class TestEntropyDriftAdvantage:
    """EntropySentinel advantages over KS-test."""

    def test_new_category_injection_detected(self):
        """
        When new categories appear in a categorical column,
        entropy should detect the distribution shift.
        """
        ref = generate_clean_batch(n_rows=1000, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                category_injection_columns=("payment_type",),
                new_categories=("crypto", "voucher", "gift_card"),
            ),
            seed=99,
        )

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        result = sentinel.check_drift(drifted, ref, "new_cats")

        payment_check = [c for c in result.checks if c.feature_name == "payment_type"]
        assert len(payment_check) > 0
        assert payment_check[0].drifted, "Should detect new category injection"

    def test_dual_signal_details(self):
        """EntropySentinel provides entropy gradient + KL divergence in details."""
        ref = generate_clean_batch(n_rows=500, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                distribution_shift_columns=("fare_amount",),
                shift_magnitude=0.7,
            ),
            seed=99,
        )

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)
        result = sentinel.check_drift(drifted, ref, "dual_signal")

        fare_check = [c for c in result.checks if c.feature_name == "fare_amount"]
        assert len(fare_check) > 0
        assert "H_ref=" in fare_check[0].details
        assert "KL=" in fare_check[0].details
        assert fare_check[0].method == "entropy_gradient+kl_divergence"

    def test_composite_health_score(self):
        """EntropySentinel produces a single batch-level health score."""
        ref = generate_clean_batch(n_rows=500, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                distribution_shift_columns=("fare_amount", "trip_distance"),
                shift_magnitude=0.7,
            ),
            seed=99,
        )

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)

        # Drifted data should have low health
        drift_result = sentinel.check_drift(drifted, ref, "health_drift")
        assert 0.0 <= drift_result.composite_health <= 1.0
        assert drift_result.composite_health < 0.8, (
            f"Drifted data should have low health, got {drift_result.composite_health}"
        )

        # Clean data should have high health
        clean_result = sentinel.check_drift(ref, ref, "health_clean")
        assert clean_result.composite_health >= 0.9, (
            f"Clean data should have high health, got {clean_result.composite_health}"
        )

    def test_deterministic_across_runs(self):
        """Same inputs produce identical drift results."""
        ref = generate_clean_batch(n_rows=500, seed=42)
        drifted = inject_drift(
            ref,
            DriftProfile(
                distribution_shift_columns=("fare_amount",),
                shift_magnitude=0.6,
            ),
            seed=99,
        )

        sentinel = EntropySentinel()
        sentinel.set_reference(ref)

        r1 = sentinel.check_drift(drifted, ref, "run1")
        r2 = sentinel.check_drift(drifted, ref, "run2")

        assert len(r1.checks) == len(r2.checks)
        for c1, c2 in zip(r1.checks, r2.checks):
            assert c1.drifted == c2.drifted
            assert c1.score == c2.score

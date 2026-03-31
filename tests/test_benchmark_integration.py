"""Integration test: full benchmark run across canonical seeds."""

import json

from entropy_quality_drift.contracts import BenchmarkResult, GateVerdict, TrackScore
from entropy_quality_drift.metrics.gate_evaluator import _fail_threshold_met, evaluate_benchmark
from entropy_quality_drift.runners.benchmark import BenchmarkConfig, run_benchmark


class TestFullBenchmarkRun:
    """End-to-end benchmark integration."""

    def test_benchmark_completes_with_verdict(self):
        result = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))

        assert result.run_id == "bench_42"
        assert result.seed == 42
        assert result.verdict in ("PASS", "WARN", "FAIL", "INCOMPLETE")

        assert result.quality_baseline is not None
        assert result.quality_challenger is not None
        assert result.drift_baseline is not None
        assert result.drift_challenger is not None

    def test_challenger_recall_exceeds_baseline(self):
        """
        EntropyForge should have higher recall than Deequ because
        it detects constant collapse (distribution fault) that rules miss.
        """
        result = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))

        assert result.quality_challenger.recall > result.quality_baseline.recall, (
            f"Challenger recall {result.quality_challenger.recall} should exceed "
            f"baseline {result.quality_baseline.recall}"
        )

    def test_no_hard_gate_failures(self):
        """All GATE-level (hard) gates should pass."""
        result = run_benchmark(BenchmarkConfig(seed=42, n_rows=1000))
        gate_result = evaluate_benchmark(result)

        hard_gates = [
            g
            for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)
            if g.gate_id.startswith(("Q-GATE", "D-GATE"))
        ]
        failed_gates = [g for g in hard_gates if g.status is GateVerdict.FAIL]

        assert len(failed_gates) == 0, (
            f"Hard gates failed: {[(g.gate_id, g.details) for g in failed_gates]}"
        )

    def test_gate_evaluation_produces_all_gates(self):
        """Gate evaluator should emit all 10 gates from kpi_thresholds.json."""
        result = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))
        gate_result = evaluate_benchmark(result)

        all_gate_ids = {
            g.gate_id for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)
        }
        expected = {
            "Q-GATE-1",
            "Q-GATE-2",
            "Q-GATE-3",
            "Q-WARN-1",
            "Q-WARN-2",
            "D-GATE-1",
            "D-GATE-2",
            "D-GATE-3",
            "D-WARN-1",
            "D-WARN-2",
        }
        assert expected == all_gate_ids, f"Missing gates: {expected - all_gate_ids}"

    def test_missing_metrics_yield_incomplete_verdict(self):
        """Missing track outputs should produce an explicit INCOMPLETE verdict."""
        result = BenchmarkResult(run_id="incomplete", seed=42)
        gate_result = evaluate_benchmark(result)

        assert gate_result.overall_verdict is GateVerdict.INCOMPLETE
        assert all(g.status is GateVerdict.INCOMPLETE for g in gate_result.quality_gates)
        assert all(g.status is GateVerdict.INCOMPLETE for g in gate_result.drift_gates)

    def test_deterministic_across_canonical_seeds(self):
        """Same seed must produce identical verdicts."""
        r1 = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))
        r2 = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))

        assert r1.verdict == r2.verdict
        assert r1.quality_baseline.precision == r2.quality_baseline.precision
        assert r1.drift_challenger.sensitivity == r2.drift_challenger.sensitivity

    def test_multiple_seeds_no_hard_failures(self):
        """Benchmark should pass hard gates across multiple seeds."""
        for seed in [42, 7, 123]:
            result = run_benchmark(BenchmarkConfig(seed=seed, n_rows=500))
            gate_result = evaluate_benchmark(result)

            hard_gates = [
                g
                for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)
                if g.gate_id.startswith(("Q-GATE", "D-GATE"))
            ]
            failed = [g for g in hard_gates if g.status is GateVerdict.FAIL]
            assert len(failed) == 0, (
                f"Seed {seed}: hard gates failed: {[(g.gate_id, g.details) for g in failed]}"
            )

    def test_hard_gate_warning_band_uses_config_fail_threshold(self):
        """A hard gate can warn without failing when it is between pass and fail bands."""
        result = BenchmarkResult(
            run_id="band_test",
            seed=1,
            quality_baseline=TrackScore(
                track="quality",
                adapter_name="baseline",
                precision=1.0,
                recall=1.0,
                f1=1.0,
                latency_ms=10.0,
            ),
            quality_challenger=TrackScore(
                track="quality",
                adapter_name="challenger",
                precision=1.0,
                recall=1.0,
                f1=1.0,
                distribution_detection_rate=1.0,
                latency_ms=12.0,
            ),
            drift_baseline=TrackScore(
                track="drift",
                adapter_name="baseline",
                false_positive_rate=0.0,
                sensitivity=1.0,
                gradual_drift_sensitivity=0.8,
                latency_ms=10.0,
            ),
            drift_challenger=TrackScore(
                track="drift",
                adapter_name="challenger",
                false_positive_rate=0.0,
                sensitivity=1.0,
                gradual_drift_sensitivity=0.8,
                single_score_interpretability=1.0,
                latency_ms=25.0,
            ),
        )

        gate_result = evaluate_benchmark(result)
        d_gate_3 = next(g for g in gate_result.drift_gates if g.gate_id == "D-GATE-3")

        assert d_gate_3.status is GateVerdict.WARN
        assert gate_result.overall_verdict is GateVerdict.WARN

    def test_evidence_bundle_is_append_only(self, tmp_path):
        """Repeated runs must create distinct evidence files."""
        config = BenchmarkConfig(seed=42, n_rows=250, evidence_dir=str(tmp_path))

        run_benchmark(config)
        run_benchmark(config)

        files = list(tmp_path.glob("bench_42_*.json"))
        assert len(files) == 2

    def test_fail_threshold_supports_symbolic_comparisons(self):
        """Fail-threshold comparisons must support symbolic operators without crashing."""
        assert _fail_threshold_met(0.79, ">=", 0.8)
        assert not _fail_threshold_met(0.81, ">=", 0.8)
        assert _fail_threshold_met(1.21, "<=", 1.2)
        assert not _fail_threshold_met(1.19, "<=", 1.2)

    def test_evidence_bundle_preserves_threshold_map(self, tmp_path):
        """Evidence should include both pass and fail thresholds when both exist."""
        config = BenchmarkConfig(seed=42, n_rows=250, evidence_dir=str(tmp_path))

        run_benchmark(config)

        bundle_path = next(tmp_path.glob("bench_42_*.json"))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        q_gate_2 = next(g for g in bundle["gates"]["quality"] if g["gate_id"] == "Q-GATE-2")
        assert q_gate_2["threshold"] == 0.9
        assert q_gate_2["thresholds"] == {"pass_threshold": 0.9, "fail_threshold": 0.8}

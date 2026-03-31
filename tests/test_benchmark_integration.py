"""
Integration test: full benchmark run across canonical seeds.

Runs the complete dual-track benchmark and verifies that
gate evaluation produces a deterministic, structured result
with the challenger demonstrating measurable advantages.

Author: Anthony Johnson | EthereaLogic LLC
"""

import pytest

from entropy_quality_drift.runners.benchmark import (
    BenchmarkConfig,
    run_benchmark,
)
from entropy_quality_drift.metrics.gate_evaluator import evaluate_benchmark


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
            g for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)
            if g.gate_id.startswith(("Q-GATE", "D-GATE"))
        ]
        failed_gates = [g for g in hard_gates if g.passed is False]

        assert len(failed_gates) == 0, (
            f"Hard gates failed: {[(g.gate_id, g.details) for g in failed_gates]}"
        )

    def test_gate_evaluation_produces_all_gates(self):
        """Gate evaluator should emit all 10 gates from kpi_thresholds.json."""
        result = run_benchmark(BenchmarkConfig(seed=42, n_rows=500))
        gate_result = evaluate_benchmark(result)

        all_gate_ids = {g.gate_id for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)}
        expected = {"Q-GATE-1", "Q-GATE-2", "Q-GATE-3", "Q-WARN-1", "Q-WARN-2",
                    "D-GATE-1", "D-GATE-2", "D-GATE-3", "D-WARN-1", "D-WARN-2"}
        assert expected == all_gate_ids, f"Missing gates: {expected - all_gate_ids}"

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
                g for g in list(gate_result.quality_gates) + list(gate_result.drift_gates)
                if g.gate_id.startswith(("Q-GATE", "D-GATE"))
            ]
            failed = [g for g in hard_gates if g.passed is False]
            assert len(failed) == 0, (
                f"Seed {seed}: hard gates failed: {[(g.gate_id, g.details) for g in failed]}"
            )

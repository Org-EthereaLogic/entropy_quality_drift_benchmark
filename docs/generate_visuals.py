"""Generate README visualizations for the entropy quality & drift benchmark.

Produces three publication-ready PNG images from a deterministic benchmark
run (seed=42, n_rows=1000).  Images use the same dark-theme palette as the
entropy_governed_medallion_demo so the two projects share a consistent
visual identity.

Usage:
    pip install -e ".[docs]"
    python docs/generate_visuals.py

Author: Anthony Johnson | EthereaLogic LLC
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from entropy_quality_drift.runners.benchmark import (  # noqa: E402
    BenchmarkConfig,
    run_benchmark_with_gates,
)

OUTPUT_DIR = Path(__file__).parent / "images"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Color palette — matches entropy_governed_medallion_demo
# ---------------------------------------------------------------------------
COLORS = {
    "green": "#2ecc71",
    "red": "#e74c3c",
    "yellow": "#f39c12",
    "blue": "#3498db",
    "dark_bg": "#1a1a2e",
    "card_bg": "#16213e",
    "text": "#e8e8e8",
    "grid": "#2a2a4a",
    "accent": "#0f3460",
    "light_gray": "#aaaaaa",
}


def _run_benchmark():
    """Execute the benchmark once and return (result, gate_result)."""
    cfg = BenchmarkConfig(seed=42, n_rows=1000, evidence_dir="/dev/null")
    return run_benchmark_with_gates(cfg)


# ---------------------------------------------------------------------------
# 1. Track Comparison — baseline vs challenger across key metrics
# ---------------------------------------------------------------------------
def generate_track_comparison(result):
    """Side-by-side grouped bars: quality and drift track metrics."""

    fig, (ax_q, ax_d) = plt.subplots(1, 2, figsize=(16, 7), facecolor=COLORS["dark_bg"])

    fig.suptitle(
        "Baseline vs Entropy Challenger: Head-to-Head Comparison",
        fontsize=20, fontweight="bold", color=COLORS["text"], y=0.97,
    )
    fig.text(
        0.5, 0.91,
        "Same deterministic dataset (seed=42, 1 000 rows).  "
        "Higher is better for all quality metrics; lower is better for FPR.",
        ha="center", fontsize=11, color=COLORS["light_gray"], style="italic",
    )

    # --- Quality track ---
    q_metrics = ["Precision", "Recall", "F1", "Dist.\nDetection"]
    q_baseline = [
        result.quality_baseline.precision,
        result.quality_baseline.recall,
        result.quality_baseline.f1,
        result.quality_baseline.distribution_detection_rate,
    ]
    q_challenger = [
        result.quality_challenger.precision,
        result.quality_challenger.recall,
        result.quality_challenger.f1,
        result.quality_challenger.distribution_detection_rate,
    ]
    _draw_grouped_bars(ax_q, q_metrics, q_baseline, q_challenger,
                       "Quality Track", higher_better=True)

    # --- Drift track ---
    d_metrics = ["Sensitivity", "FPR", "Gradual\nDrift Sens.", "Single\nScore"]
    d_baseline = [
        result.drift_baseline.sensitivity,
        result.drift_baseline.false_positive_rate,
        result.drift_baseline.gradual_drift_sensitivity,
        result.drift_baseline.single_score_interpretability,
    ]
    d_challenger = [
        result.drift_challenger.sensitivity,
        result.drift_challenger.false_positive_rate,
        result.drift_challenger.gradual_drift_sensitivity,
        result.drift_challenger.single_score_interpretability,
    ]
    _draw_grouped_bars(ax_d, d_metrics, d_baseline, d_challenger,
                       "Drift Track", higher_better=True)

    # Legend
    baseline_patch = mpatches.Patch(color=COLORS["blue"], label="Baseline (Deequ / KS-test)")
    challenger_patch = mpatches.Patch(
        color=COLORS["green"], label="Challenger (EntropyForge / EntropySentinel)",
    )
    fig.legend(
        handles=[baseline_patch, challenger_patch],
        loc="lower center", ncol=2, fontsize=12,
        facecolor=COLORS["dark_bg"], edgecolor=COLORS["grid"],
        labelcolor=COLORS["text"], framealpha=0.9,
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.89])
    out = OUTPUT_DIR / "track_comparison.png"
    plt.savefig(out, dpi=150, facecolor=COLORS["dark_bg"])
    plt.close()
    print(f"Generated: {out}")


def _draw_grouped_bars(ax, labels, baseline, challenger, title, higher_better=True):
    """Draw a grouped bar chart on the given axes."""
    ax.set_facecolor(COLORS["card_bg"])
    x = range(len(labels))
    width = 0.32

    bars_b = ax.bar([i - width / 2 for i in x], baseline, width,
                    color=COLORS["blue"], alpha=0.85, edgecolor="none")
    bars_c = ax.bar([i + width / 2 for i in x], challenger, width,
                    color=COLORS["green"], alpha=0.85, edgecolor="none")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=10, color=COLORS["text"])
    ax.set_ylim(0, 1.18)
    ax.set_ylabel("Score", color=COLORS["text"], fontsize=11)
    ax.set_title(title, fontsize=15, fontweight="bold", color=COLORS["text"], pad=12)
    ax.tick_params(colors=COLORS["text"], labelsize=9)

    # Value labels
    for bar_group in (bars_b, bars_c):
        for bar in bar_group:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02,
                    f"{h:.2f}", ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color=COLORS["text"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["grid"])
    ax.spines["left"].set_color(COLORS["grid"])

    # Horizontal reference line at 1.0
    ax.axhline(y=1.0, color=COLORS["grid"], linewidth=0.8, linestyle="--", alpha=0.6)


# ---------------------------------------------------------------------------
# 2. Gate Evaluation Matrix — all 10 gates as a styled table
# ---------------------------------------------------------------------------
def generate_gate_evaluation(gate_result):
    """Table showing all 10 gates with status, thresholds, and scores."""

    all_gates = list(gate_result.quality_gates) + list(gate_result.drift_gates)

    fig, ax = plt.subplots(figsize=(16, 7), facecolor=COLORS["dark_bg"])
    ax.set_facecolor(COLORS["card_bg"])
    ax.axis("off")

    fig.suptitle(
        "Gate Evaluation Matrix: 10 Frozen Gates (seed=42)",
        fontsize=18, fontweight="bold", color=COLORS["text"], y=0.95,
    )
    fig.text(
        0.5, 0.90,
        "Hard gates block on failure.  Warning gates surface "
        "calibration opportunities without blocking.",
        ha="center", fontsize=11, color=COLORS["light_gray"], style="italic",
    )

    col_labels = ["Gate", "Type", "Metric", "Baseline", "Challenger", "Threshold", "Status"]
    cell_text = []
    cell_colors = []

    for g in all_gates:
        gate_type = "Warning" if "WARN" in g.gate_id else "Hard"
        status = g.status.value

        if status == "PASS":
            row_color = "#1a3d2e"
        elif status == "WARN":
            row_color = "#3d3a1a"
        elif status == "FAIL":
            row_color = "#3d1a1a"
        else:
            row_color = "#2a2a3a"

        threshold_display = _format_threshold(g)

        cell_text.append([
            g.gate_id,
            gate_type,
            g.metric,
            f"{g.baseline_value:.4f}" if g.baseline_value is not None else "n/a",
            f"{g.challenger_value:.4f}" if g.challenger_value is not None else "n/a",
            threshold_display,
            status,
        ])
        cell_colors.append([row_color] * 7)

    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellColours=cell_colors,
        colColours=[COLORS["accent"]] * 7,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.7)

    # Wider gate and metric columns
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(COLORS["grid"])
        cell.set_text_props(color=COLORS["text"], fontweight="bold" if row == 0 else "normal")
        if row == 0:
            cell.set_text_props(color="white", fontweight="bold")

    # Color the status column
    for i, g in enumerate(all_gates):
        status_cell = table[i + 1, 6]
        status = g.status.value
        if status == "PASS":
            status_cell.set_text_props(color=COLORS["green"], fontweight="bold")
        elif status == "WARN":
            status_cell.set_text_props(color=COLORS["yellow"], fontweight="bold")
        elif status == "FAIL":
            status_cell.set_text_props(color=COLORS["red"], fontweight="bold")

    # Overall verdict
    verdict = gate_result.overall_verdict.value
    verdict_color = {
        "PASS": COLORS["green"],
        "WARN": COLORS["yellow"],
        "FAIL": COLORS["red"],
    }.get(verdict, COLORS["light_gray"])

    verdict_explanation = {
        "PASS": "All hard gates and advisory gates cleared.",
        "WARN": "All hard gates passed.  Advisory thresholds surfaced improvement areas.",
        "FAIL": "At least one hard gate breached.",
    }.get(verdict, "Evaluation incomplete.")

    fig.text(
        0.5, 0.04,
        f"OVERALL VERDICT: {verdict} \u2014 {verdict_explanation}",
        ha="center", fontsize=13, fontweight="bold", color=verdict_color,
        bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS["dark_bg"],
                  edgecolor=verdict_color, linewidth=2),
    )

    out = OUTPUT_DIR / "gate_evaluation.png"
    plt.savefig(out, dpi=150, facecolor=COLORS["dark_bg"],
                bbox_inches="tight", pad_inches=0.3)
    plt.close()
    print(f"Generated: {out}")


def _format_threshold(gate):
    """Format the threshold display for a gate."""
    if gate.thresholds:
        parts = []
        for key, val in gate.thresholds.items():
            short_key = key.replace("_threshold", "")
            parts.append(f"{short_key}={val}")
        return ", ".join(parts)
    # Symbolic condition gates
    if gate.threshold is not None:
        return str(gate.threshold)
    return "vs baseline"


# ---------------------------------------------------------------------------
# 3. Benchmark Verdict Dashboard — summary view with key metrics
# ---------------------------------------------------------------------------
def generate_verdict_dashboard(result, gate_result):
    """Dashboard showing verdict, key wins, and warning areas."""

    fig = plt.figure(figsize=(16, 9), facecolor=COLORS["dark_bg"])

    fig.suptitle(
        "Entropy Quality & Drift Benchmark: Verdict Dashboard",
        fontsize=20, fontweight="bold", color=COLORS["text"], y=0.97,
    )
    fig.text(
        0.5, 0.92,
        f"seed=42  |  n_rows=1,000  |  10 frozen gates  |  "
        f"Verified {_today()}",
        ha="center", fontsize=11, color=COLORS["light_gray"],
    )

    # --- Left panel: quality track key metrics ---
    ax_q = fig.add_axes([0.05, 0.18, 0.28, 0.65], facecolor=COLORS["card_bg"])
    _draw_metric_card(ax_q, "Quality Track", [
        ("Precision", result.quality_baseline.precision,
         result.quality_challenger.precision),
        ("Recall", result.quality_baseline.recall,
         result.quality_challenger.recall),
        ("F1 Score", result.quality_baseline.f1,
         result.quality_challenger.f1),
        ("Dist. Detection", result.quality_baseline.distribution_detection_rate,
         result.quality_challenger.distribution_detection_rate),
    ])

    # --- Center panel: verdict summary ---
    ax_v = fig.add_axes([0.37, 0.18, 0.26, 0.65], facecolor=COLORS["card_bg"])
    _draw_verdict_panel(ax_v, gate_result)

    # --- Right panel: drift track key metrics ---
    ax_d = fig.add_axes([0.67, 0.18, 0.28, 0.65], facecolor=COLORS["card_bg"])
    _draw_metric_card(ax_d, "Drift Track", [
        ("Sensitivity", result.drift_baseline.sensitivity,
         result.drift_challenger.sensitivity),
        ("FPR", result.drift_baseline.false_positive_rate,
         result.drift_challenger.false_positive_rate),
        ("Gradual Drift", result.drift_baseline.gradual_drift_sensitivity,
         result.drift_challenger.gradual_drift_sensitivity),
        ("Single Score", result.drift_baseline.single_score_interpretability,
         result.drift_challenger.single_score_interpretability),
    ])

    # Bottom caption
    fig.text(
        0.5, 0.05,
        "Hard gates enforce correctness.  "
        "Warning gates surface calibration opportunities without blocking the benchmark.",
        ha="center", fontsize=10, color=COLORS["light_gray"], style="italic",
    )

    out = OUTPUT_DIR / "benchmark_verdict.png"
    plt.savefig(out, dpi=150, facecolor=COLORS["dark_bg"])
    plt.close()
    print(f"Generated: {out}")


def _draw_metric_card(ax, title, metrics):
    """Draw a vertical metric comparison card."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(metrics) + 0.5)
    ax.axis("off")

    ax.text(0.5, len(metrics) + 0.2, title,
            ha="center", va="bottom", fontsize=15, fontweight="bold",
            color=COLORS["text"])

    for i, (label, baseline, challenger) in enumerate(metrics):
        y = len(metrics) - i - 0.5

        # Label
        ax.text(0.5, y + 0.2, label, ha="center", va="bottom",
                fontsize=11, color=COLORS["text"], fontweight="bold")

        # Baseline bar (left half)
        bar_width = max(baseline * 0.42, 0.01)
        ax.barh(y - 0.1, bar_width, height=0.18, left=0.5 - bar_width,
                color=COLORS["blue"], alpha=0.85, edgecolor="none")
        ax.text(0.5 - bar_width - 0.02, y - 0.1, f"{baseline:.2f}",
                ha="right", va="center", fontsize=9, color=COLORS["blue"],
                fontweight="bold")

        # Challenger bar (right half)
        bar_width_c = max(challenger * 0.42, 0.01)
        ax.barh(y - 0.1, bar_width_c, height=0.18, left=0.5,
                color=COLORS["green"], alpha=0.85, edgecolor="none")
        ax.text(0.5 + bar_width_c + 0.02, y - 0.1, f"{challenger:.2f}",
                ha="left", va="center", fontsize=9, color=COLORS["green"],
                fontweight="bold")

    # Mini legend at bottom
    ax.text(0.25, -0.2, "Baseline", ha="center", fontsize=8,
            color=COLORS["blue"])
    ax.text(0.75, -0.2, "Challenger", ha="center", fontsize=8,
            color=COLORS["green"])

    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])


def _draw_verdict_panel(ax, gate_result):
    """Draw the center verdict summary panel."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    verdict = gate_result.overall_verdict.value
    verdict_color = {
        "PASS": COLORS["green"],
        "WARN": COLORS["yellow"],
        "FAIL": COLORS["red"],
    }.get(verdict, COLORS["light_gray"])

    # Large verdict
    ax.text(0.5, 0.88, "VERDICT", ha="center", va="center",
            fontsize=12, color=COLORS["light_gray"], fontweight="bold")
    ax.text(0.5, 0.77, verdict, ha="center", va="center",
            fontsize=36, color=verdict_color, fontweight="bold")

    # Gate summary
    all_gates = list(gate_result.quality_gates) + list(gate_result.drift_gates)
    n_pass = sum(1 for g in all_gates if g.status.value == "PASS")
    n_warn = sum(1 for g in all_gates if g.status.value == "WARN")
    n_fail = sum(1 for g in all_gates if g.status.value == "FAIL")

    ax.text(0.5, 0.60, f"{n_pass} PASS  |  {n_warn} WARN  |  {n_fail} FAIL",
            ha="center", va="center", fontsize=12, color=COLORS["text"])

    # Gate list
    y = 0.48
    for g in all_gates:
        status = g.status.value
        color = {
            "PASS": COLORS["green"],
            "WARN": COLORS["yellow"],
            "FAIL": COLORS["red"],
        }.get(status, COLORS["light_gray"])
        marker = {
            "PASS": "\u2713",
            "WARN": "\u26A0",
            "FAIL": "\u2717",
        }.get(status, "?")

        ax.text(0.15, y, f"{marker} {g.gate_id}", ha="left", va="center",
                fontsize=9, color=color, fontweight="bold" if status != "PASS" else "normal",
                fontfamily="monospace")
        y -= 0.042

    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])


def _today() -> str:
    """Return today's date as a string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%B %d, %Y")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running benchmark (seed=42, n_rows=1000)...")
    result, gate_result = _run_benchmark()
    print(f"Benchmark verdict: {gate_result.overall_verdict.value}\n")

    generate_track_comparison(result)
    generate_gate_evaluation(gate_result)
    generate_verdict_dashboard(result, gate_result)

    print("\nAll visualizations generated successfully.")

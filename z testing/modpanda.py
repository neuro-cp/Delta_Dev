# pandaplot.py
# Unified plot: D1/D2, Δ dominance, gate relief, gate open, decision latch
# Compatible with current debug + latch harness (single-run)

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

DEBUG    = BASE_DIR / "decision_debug_trace.csv"
DECISION = BASE_DIR / "decision_latch_trace.csv"


# ============================================================
# UTIL
# ============================================================

def _coerce(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ============================================================
# MAIN PLOT
# ============================================================

def plot_unified(debug_df: pd.DataFrame, decision_df: pd.DataFrame | None) -> None:
    """
    Unified visualization:
      - D1 / D2 activity
      - Δ dominance
      - Gate relief
      - Gate-open event
      - Decision latch event
    """

    # ---- sanitize debug trace ----
    debug_df = _coerce(
        debug_df,
        [
            "step",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
            "gate_opened",
            "test_id",
        ],
    )

    debug_df = debug_df.dropna(subset=["step"]).sort_values("step")

    if debug_df.empty:
        raise RuntimeError("decision_debug_trace.csv has no usable rows.")

    # ---- focus on gate-driven test (TEST 3) ----
    if "test_id" in debug_df.columns:
        debug_df = debug_df[debug_df["test_id"] == 3]

    if debug_df.empty:
        raise RuntimeError("No rows for gate-driven test (test_id == 3).")

    # ========================================================
    # EVENT DETECTION
    # ========================================================

    # Gate-open step
    gate_step = None
    if "gate_opened" in debug_df.columns:
        opened = debug_df[debug_df["gate_opened"] == 1]
        if not opened.empty:
            gate_step = int(opened["step"].iloc[0])

    # Decision step
    decision_step = None

    if decision_df is not None and not decision_df.empty:
        decision_df = _coerce(decision_df, ["step"])
        decision_df = decision_df.dropna(subset=["step"]).sort_values("step")
        if not decision_df.empty:
            decision_step = int(decision_df["step"].iloc[-1])
    else:
        fired = debug_df[debug_df["decision_seen"] == 1]
        if not fired.empty:
            decision_step = int(fired["step"].iloc[0])

    # ========================================================
    # FIGURE
    # ========================================================

    fig, ax1 = plt.subplots(figsize=(13, 6))

    # ---- Left axis: D1 / D2 ----
    ax1.plot(debug_df["step"], debug_df["D1"], label="D1", linewidth=2.2)
    ax1.plot(debug_df["step"], debug_df["D2"], label="D2", linewidth=2.2)

    # ---- Δ dominance ----
    if "delta" in debug_df.columns:
        ax1.plot(
            debug_df["step"],
            debug_df["delta"],
            label="Δ dominance",
            color="black",
            linewidth=2.5,
        )

    ax1.set_xlabel("Step")
    ax1.set_ylabel("Striatal activity / dominance")
    ax1.grid(alpha=0.3)

    # ---- Right axis: gate relief ----
    ax2 = ax1.twinx()
    if "gate_relief" in debug_df.columns and debug_df["gate_relief"].notna().any():
        ax2.plot(
            debug_df["step"],
            debug_df["gate_relief"],
            linestyle="--",
            linewidth=2.2,
            label="Gate relief",
        )
        ax2.set_ylabel("Gate relief")

    # ========================================================
    # EVENT MARKERS
    # ========================================================

    if gate_step is not None:
        ax1.axvline(
            gate_step,
            color="orange",
            linestyle="--",
            linewidth=2,
            alpha=0.8,
            label="Gate open",
        )

    if decision_step is not None:
        row = debug_df[debug_df["step"] == decision_step]
        if not row.empty:
            delta_val = row["delta"].iloc[0]

            ax1.axvline(
                decision_step,
                color="red",
                linestyle=":",
                linewidth=2,
                alpha=0.8,
                label="Decision",
            )

            ax1.scatter(
                [decision_step],
                [delta_val],
                color="red",
                s=90,
                zorder=6,
            )

    # ========================================================
    # TITLE + LEGEND
    # ========================================================

    # Parameter annotation (use first row; constants per run)
    param_str = ""
    for p in ["baseline_poke", "asym_poke", "gate_threshold"]:
        if p in debug_df.columns:
            v = debug_df[p].iloc[0]
            param_str += f"{p}={v}  "

    ax1.set_title(
        "Decision Latch — Pre-Decision Dynamics\n" + param_str.strip()
    )

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")

    plt.tight_layout()
    plt.show()


# ============================================================
# ENTRY
# ============================================================

def main() -> None:
    if not DEBUG.exists():
        raise FileNotFoundError("decision_debug_trace.csv not found.")

    debug_df = pd.read_csv(DEBUG)

    decision_df = None
    if DECISION.exists():
        decision_df = pd.read_csv(DECISION)

    print("[OK] Rendering unified dominance + gate + decision plot")
    plot_unified(debug_df, decision_df)


if __name__ == "__main__":
    main()

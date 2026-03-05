# modpanda.py
# Unified plot: D1/D2, Δ dominance, gate relief, decision latch
# Robust to missing run_id and legacy CSVs

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
DEBUG    = BASE_DIR / "decision_debug_trace.csv"
DECISION = BASE_DIR / "decision_latch_trace.csv"


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def _coerce(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _ensure_run_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure a run_id column exists and is usable.
    Legacy files get run_id = 0.
    """
    if "run_id" not in df.columns:
        df["run_id"] = 0
    df = _coerce(df, ["run_id"])
    df["run_id"] = df["run_id"].fillna(0).astype(int)
    return df


def _sorted(df: pd.DataFrame) -> pd.DataFrame:
    sort_cols = ["run_id"]
    if "trial" in df.columns and df["trial"].notna().any():
        sort_cols.append("trial")
    sort_cols.append("step")
    return df.sort_values(sort_cols)


# ------------------------------------------------------------
# Plotting
# ------------------------------------------------------------

def plot_single_run(
    sub: pd.DataFrame,
    decision_df: pd.DataFrame | None,
    run_id: int,
) -> None:

    # resolve trial (optional)
    trial = None
    if "trial" in sub.columns and sub["trial"].notna().any():
        trial = int(sub["trial"].dropna().max())
        sub = sub[sub["trial"] == trial]

    # decision step
    decision_step = None

    if decision_df is not None and not decision_df.empty:
        dsub = decision_df[decision_df["run_id"] == run_id]
        if trial is not None and "trial" in dsub.columns:
            dsub = dsub[dsub["trial"] == trial]
        if not dsub.empty:
            decision_step = int(dsub["step"].iloc[-1])

    if decision_step is None and "decision_seen" in sub.columns:
        fired = sub[sub["decision_seen"] == 1]
        if not fired.empty:
            decision_step = int(fired["step"].iloc[0])

    # --- plotting ---
    fig, ax1 = plt.subplots(figsize=(13, 6))

    ax1.plot(sub["step"], sub["D1"], label="D1", linewidth=2.2)
    ax1.plot(sub["step"], sub["D2"], label="D2", linewidth=2.2)

    if "delta" in sub.columns:
        ax1.plot(sub["step"], sub["delta"], label="Δ dominance", linewidth=2.5)

    ax1.set_xlabel("Step")
    ax1.set_ylabel("Striatal activity / dominance")
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    if "gate_relief" in sub.columns and sub["gate_relief"].notna().any():
        ax2.plot(
            sub["step"],
            sub["gate_relief"],
            linestyle="--",
            linewidth=2.2,
            label="Gate relief",
        )
        ax2.set_ylabel("Gate relief")

    if decision_step is not None:
        row = sub[sub["step"] == decision_step]
        y = float(row["delta"].iloc[0]) if (not row.empty and "delta" in row.columns) else 0.0
        ax1.axvline(decision_step, linestyle=":", linewidth=2, alpha=0.8)
        ax1.scatter([decision_step], [y], s=90, zorder=6, label="Decision")

    title = f"Decision Latch — Dominance, Gating, Commitment (run_id={run_id}"
    if trial is not None:
        title += f", trial={trial}"
    title += ")"
    ax1.set_title(title)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")

    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def main() -> None:
    if not DEBUG.exists():
        raise FileNotFoundError("decision_debug_trace.csv not found.")

    debug_df = pd.read_csv(DEBUG)
    debug_df = _ensure_run_id(debug_df)
    debug_df = _coerce(
        debug_df,
        ["step", "D1", "D2", "delta", "gate_relief", "decision_seen"],
    )
    debug_df = debug_df.dropna(subset=["step"])
    debug_df = _sorted(debug_df)

    decision_df = None
    if DECISION.exists():
        decision_df = pd.read_csv(DECISION)
        decision_df = _ensure_run_id(decision_df)
        decision_df = _coerce(decision_df, ["step"])

    print("[OK] Rendering unified dominance + decision plots (all runs)")

    for run_id, sub in debug_df.groupby("run_id"):
        if sub.empty:
            continue
        plot_single_run(sub, decision_df, int(run_id))


if __name__ == "__main__":
    main()

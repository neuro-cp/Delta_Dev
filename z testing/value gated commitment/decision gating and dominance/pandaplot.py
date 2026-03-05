# pandaplot.py
# Robust plotter for post-test CSVs with explicit dominance delta
#
# Priority:
# 1) decision_gating_trace.csv
# 2) kernel_dominance_trace.csv
# 3) dominance_trace.csv

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

DECISION = BASE_DIR / "decision_gating_trace.csv"
KERNEL   = BASE_DIR / "kernel_dominance_trace.csv"
LEGACY   = BASE_DIR / "dominance_trace.csv"


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ============================================================
# DECISION + GATING PLOT (PRIMARY)
# ============================================================

def plot_decision(df: pd.DataFrame) -> None:
    # expected:
    # step,winner,D1,D2,gpi_*,gate_relief,commit?

    df = _coerce_numeric(
        df,
        ["step", "D1", "D2", "gpi_mean", "gate_relief", "commit"]
    )

    df = df.dropna(subset=["step", "D1", "D2"]).sort_values("step")
    if df.empty:
        raise RuntimeError("decision_gating_trace.csv has no usable rows.")

    # Derived signal (this is the key addition)
    df["dominance_delta"] = df["D1"] - df["D2"]

    fig, ax1 = plt.subplots(figsize=(12, 5))

    # --- Primary axis: dominance signals ---
    ax1.plot(df["step"], df["D1"], label="D1", linewidth=2)
    ax1.plot(df["step"], df["D2"], label="D2", linewidth=2)
    ax1.plot(
        df["step"],
        df["dominance_delta"],
        label="Δ = D1 − D2",
        linewidth=2.5,
        color="black",
    )

    ax1.axhline(0.0, color="gray", linestyle=":", linewidth=1)

    ax1.set_xlabel("Step")
    ax1.set_ylabel("Striatal dominance / delta")
    ax1.set_title("Decision → GPi → Gate (Dominance & Commitment)")
    ax1.grid(alpha=0.3)

    # --- Secondary axis: gating ---
    ax2 = ax1.twinx()

    if "gate_relief" in df.columns and df["gate_relief"].notna().any():
        ax2.plot(
            df["step"],
            df["gate_relief"],
            label="Gate relief",
            linestyle="--",
            linewidth=2,
        )

    if "gpi_mean" in df.columns and df["gpi_mean"].notna().any():
        ax2.plot(
            df["step"],
            df["gpi_mean"],
            label="GPi mean",
            linestyle=":",
            linewidth=1.5,
        )

    ax2.set_ylabel("Gate / GPi")

    # --- Commitment markers (if present) ---
    if "commit" in df.columns:
        commits = df[df["commit"] == 1]
        if not commits.empty:
            ax1.scatter(
                commits["step"],
                commits["dominance_delta"],
                color="red",
                s=80,
                zorder=5,
                label="Commit",
            )

    # --- Unified legend ---
    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, loc="best")

    plt.tight_layout()
    plt.show()


# ============================================================
# KERNEL TRACE (UNCHANGED)
# ============================================================

def plot_kernel(df: pd.DataFrame) -> None:
    df = df.rename(columns={
        "raw": "raw_output",
        "instant": "inst_dominance",
        "smooth": "smooth_dominance",
    })

    df = _coerce_numeric(
        df,
        ["step", "time", "raw_output", "inst_dominance", "smooth_dominance", "delta"]
    )

    df = df.dropna(subset=["step", "channel", "smooth_dominance"]).sort_values("step")
    if df.empty:
        raise RuntimeError("kernel_dominance_trace.csv has no usable rows.")

    plt.figure(figsize=(11, 5))
    for ch in sorted(df["channel"].dropna().unique()):
        sub = df[df["channel"] == ch]
        plt.plot(sub["step"], sub["smooth_dominance"], label=ch, linewidth=2)

    plt.xlabel("Step")
    plt.ylabel("Smoothed dominance (kernel)")
    plt.title("CompetitionKernel — Smooth Dominance")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


# ============================================================
# LEGACY TRACE (UNCHANGED)
# ============================================================

def plot_legacy(df: pd.DataFrame) -> None:
    df = _coerce_numeric(df, ["step", "D1", "D2"])
    df = df.dropna(subset=["step", "D1", "D2"]).sort_values("step")

    if df.empty:
        raise RuntimeError("dominance_trace.csv has no usable rows.")

    plt.figure(figsize=(11, 5))
    plt.plot(df["step"], df["D1"], label="D1", linewidth=2)
    plt.plot(df["step"], df["D2"], label="D2", linewidth=2)

    plt.xlabel("Step")
    plt.ylabel("Dominance")
    plt.title("Legacy Dominance Trace")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


# ============================================================
# ENTRY
# ============================================================

def main() -> None:
    if DECISION.exists():
        print(f"[OK] Using: {DECISION}")
        df = pd.read_csv(DECISION)
        plot_decision(df)
        return

    if KERNEL.exists():
        print(f"[OK] Using: {KERNEL}")
        df = pd.read_csv(KERNEL)
        plot_kernel(df)
        return

    if LEGACY.exists():
        print(f"[OK] Using: {LEGACY}")
        df = pd.read_csv(LEGACY)
        plot_legacy(df)
        return

    raise FileNotFoundError("No expected CSV found.")


if __name__ == "__main__":
    main()

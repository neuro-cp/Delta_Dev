# pandaplot.py
# Robust plotter for the post-test CSVs
#
# Priority:
# 1) decision_gating_trace.csv  (step,winner,D1,D2,gpi_*,gate_relief)
# 2) kernel_dominance_trace.csv (step,time,channel,raw_output,inst_dominance,smooth_dominance,winner,delta)
# 3) dominance_trace.csv        (step,winner,D1,D2)

from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

DECISION = BASE_DIR / "decision_gating_trace.csv"
KERNEL = BASE_DIR / "kernel_dominance_trace.csv"
LEGACY = BASE_DIR / "dominance_trace.csv"


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def plot_decision(df: pd.DataFrame) -> None:
    # expected columns:
    # step,winner,D1,D2,gpi_mass,gpi_mean,gpi_std,gpi_n,gate_relief
    df = _coerce_numeric(df, ["step", "D1", "D2", "gpi_mass", "gpi_mean", "gpi_std", "gpi_n", "gate_relief"])
    df = df.dropna(subset=["step", "D1", "D2"]).sort_values("step")

    if df.empty:
        raise RuntimeError("decision_gating_trace.csv has no usable rows after cleaning.")

    # Main dominance plot
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(df["step"], df["D1"], label="D1 (from striatum_diag)", linewidth=2)
    ax1.plot(df["step"], df["D2"], label="D2 (from striatum_diag)", linewidth=2)
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Striatal dominance (diag)")
    ax1.set_title("Decision → GPi → Gate (Time Integration Test)")
    ax1.grid(alpha=0.3)

    # Secondary axis: gate relief (and optionally GPi mean)
    ax2 = ax1.twinx()

    if "gate_relief" in df.columns and df["gate_relief"].notna().any():
        ax2.plot(df["step"], df["gate_relief"], label="Gate relief", linewidth=2, linestyle="--")
        ax2.set_ylabel("Gate relief (disinhibition factor)")

    # Optional: plot GPi mean if present (also dashed, thinner)
    if "gpi_mean" in df.columns and df["gpi_mean"].notna().any():
        ax2.plot(df["step"], df["gpi_mean"], label="GPi mean", linewidth=1.5, linestyle=":")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

    plt.tight_layout()
    plt.show()


def plot_kernel(df: pd.DataFrame) -> None:
    # expected columns:
    # step,time,channel,raw_output,inst_dominance,smooth_dominance,winner,delta
    df = df.rename(columns={
        "raw": "raw_output",
        "instant": "inst_dominance",
        "smooth": "smooth_dominance",
    })

    df = _coerce_numeric(df, ["step", "time", "raw_output", "inst_dominance", "smooth_dominance", "delta"])
    df = df.dropna(subset=["step", "channel", "smooth_dominance"]).sort_values("step")

    if df.empty:
        raise RuntimeError("kernel_dominance_trace.csv has no usable rows after cleaning.")

    # Plot smooth dominance per channel
    plt.figure(figsize=(11, 5))
    for ch in sorted(df["channel"].dropna().unique()):
        sub = df[df["channel"] == ch]
        plt.plot(sub["step"], sub["smooth_dominance"], label=f"{ch}", linewidth=2)

    plt.xlabel("Step")
    plt.ylabel("Smoothed dominance (kernel)")
    plt.title("CompetitionKernel Trace (Per-Channel Smooth Dominance)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_legacy(df: pd.DataFrame) -> None:
    # expected columns: step,winner,D1,D2
    df = _coerce_numeric(df, ["step", "D1", "D2"])
    df = df.dropna(subset=["step", "D1", "D2"]).sort_values("step")

    if df.empty:
        raise RuntimeError("dominance_trace.csv has no usable rows after cleaning.")

    plt.figure(figsize=(11, 5))
    plt.plot(df["step"], df["D1"], label="D1", linewidth=2)
    plt.plot(df["step"], df["D2"], label="D2", linewidth=2)

    plt.xlabel("Step")
    plt.ylabel("Dominance (legacy)")
    plt.title("Legacy Dominance Trace (step,winner,D1,D2)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


def main() -> None:
    if DECISION.exists():
        print(f"[OK] Using: {DECISION}")
        df = pd.read_csv(DECISION)
        print("Loaded columns:", list(df.columns))
        plot_decision(df)
        return

    if KERNEL.exists():
        print(f"[OK] Using: {KERNEL}")
        df = pd.read_csv(KERNEL)
        print("Loaded columns:", list(df.columns))
        plot_kernel(df)
        return

    if LEGACY.exists():
        print(f"[OK] Using: {LEGACY}")
        df = pd.read_csv(LEGACY)
        print("Loaded columns:", list(df.columns))
        plot_legacy(df)
        return

    raise FileNotFoundError(
        "No expected CSV found. Looked for:\n"
        f"  - {DECISION}\n"
        f"  - {KERNEL}\n"
        f"  - {LEGACY}\n"
    )


if __name__ == "__main__":
    main()

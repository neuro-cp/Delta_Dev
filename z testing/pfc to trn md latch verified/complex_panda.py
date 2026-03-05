from __future__ import annotations

import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework\z true latch")

ZLOG_PATH   = BASE_DIR / "zlog.txt"
DEBUG_CSV  = BASE_DIR / "decision_debug_trace.csv"
DEC_CSV    = BASE_DIR / "decision_latch_trace.csv"

# Regex blocks for zlog
RE_TIME = re.compile(r"^t=([0-9.]+)s\s+\|\s+view=populations", re.I)
RE_ROW  = re.compile(
    r"^(?P<region>\w+)\s+"
    r"(?P<pop>[A-Z0-9_]+)\s+"
    r"\d+\s+[0-9.]+\s+(?P<mean>[0-9.]+)",
    re.I
)

ROLL = 5  # light smoothing for readability

# ============================================================
# ZLOG PARSER (TRUE only)
# ============================================================

def parse_zlog(path: Path) -> pd.DataFrame:
    rows = []

    current_t = None
    pfc_vals = []
    md_val = None
    trn_val = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip()

            # timestep header
            if (m := RE_TIME.match(line)):
                if current_t is not None and md_val is not None and trn_val is not None:
                    rows.append({
                        "t": current_t,
                        "pfc": sum(pfc_vals) / len(pfc_vals) if pfc_vals else None,
                        "md": md_val,
                        "trn": trn_val,
                    })

                current_t = float(m.group(1))
                pfc_vals = []
                md_val = None
                trn_val = None
                continue

            # population row
            if (m := RE_ROW.match(line)):
                region = m.group("region").lower()
                pop    = m.group("pop").upper()
                mean   = float(m.group("mean"))

                if region == "pfc":
                    pfc_vals.append(mean)
                elif region == "md" and pop == "RELAY_CELLS":
                    md_val = mean
                elif region == "trn" and pop == "TRN_GABA":
                    trn_val = mean

    return pd.DataFrame(rows).dropna().reset_index(drop=True)

# ============================================================
# LOAD DATA
# ============================================================

df = parse_zlog(ZLOG_PATH)

# smooth slightly (visual only)
for col in ["pfc", "md", "trn"]:
    df[col] = df[col].rolling(ROLL, min_periods=1).mean()

# load decision / probe info
debug = pd.read_csv(DEBUG_CSV)
dec   = pd.read_csv(DEC_CSV)

decision_step = int(dec.iloc[0]["step"])
probe_step    = int(dec.iloc[0]["probe_step"])

# align time axis to steps
t = df.index.values

# ============================================================
# PLOTTING
# ============================================================

fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)

# --- PFC ---
axes[0].plot(t, df["pfc"], label="PFC mean")
axes[0].set_ylabel("PFC")
axes[0].legend()

# --- MD ---
axes[1].plot(t, df["md"], label="MD relay")
axes[1].set_ylabel("MD")
axes[1].legend()

# --- TRN ---
axes[2].plot(t, df["trn"], label="TRN inhibition")
axes[2].set_ylabel("TRN")
axes[2].legend()

# --- Gate relief ---
axes[3].plot(debug["step"], debug["gate_relief"], label="Gate relief")
axes[3].set_ylabel("Gate relief")
axes[3].set_xlabel("Step")
axes[3].legend()

# --- Event markers ---
for ax in axes:
    ax.axvline(decision_step, color="black", linestyle=":", alpha=0.7, label="Decision")
    ax.axvline(probe_step, color="red", linestyle="--", alpha=0.7, label="Probe")

# avoid duplicate legends
for ax in axes:
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys())

fig.suptitle("TRUE Run — PFC / MD / TRN with Latch & Post-Latch Probe")

plt.tight_layout()
plt.show()

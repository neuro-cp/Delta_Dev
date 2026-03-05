from __future__ import annotations

import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

LOG_FALSE = BASE_DIR / "zlogF.txt"   # latch = FALSE
LOG_TRUE  = BASE_DIR / "zlogT.txt"   # latch = TRUE

# Regions we care about (region_name -> label)
REGIONS = {
    "md":  "MD",
    "trn": "TRN",
    "pfc": "PFC",
}

# Matches:
# region population count mean
LINE_RE = re.compile(
    r"^(?P<region>\w+)\s+(?P<population>[A-Z0-9_]+)\s+\d+\s+(?P<mean>[0-9]+\.[0-9]+)",
    re.IGNORECASE,
)

# ============================================================
# PARSING
# ============================================================

def extract_activity(path: Path, latch_label: str) -> pd.DataFrame:
    """
    Parse zlog and extract region-level mean activity
    for MD, TRN, and PFC.

    PFC activity is aggregated across all its populations.
    Step count is anchored to MD lines (one MD line = one step).
    """
    rows = []
    step = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = LINE_RE.match(line.rstrip())
            if not m:
                continue

            region = m.group("region").lower()
            if region not in REGIONS:
                continue

            activity = float(m.group("mean"))

            rows.append({
                "step": step,
                "region": REGIONS[region],
                "activity": activity,
                "latch": latch_label,
            })

            # Advance timestep only on MD rows
            if region == "md":
                step += 1

    if not rows:
        raise RuntimeError(f"No activity extracted from {path.name}")

    df = pd.DataFrame(rows)

    # Aggregate all populations per region per step
    df = (
        df.groupby(["region", "latch", "step"], as_index=False)
          .activity
          .mean()
    )

    return df

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    df_false = extract_activity(LOG_FALSE, "FALSE")
    df_true  = extract_activity(LOG_TRUE,  "TRUE")

    df = pd.concat([df_false, df_true], ignore_index=True)

    plt.figure(figsize=(14, 7))

    for (region, latch), sub in df.groupby(["region", "latch"]):
        plt.plot(
            sub["step"],
            sub["activity"],
            linewidth=2,
            label=f"{region} (latch = {latch})",
        )

    plt.xlabel("Step")
    plt.ylabel("Population Mean Activity")
    plt.title("PFC, MD, and TRN Activity — Latch Disabled vs Enabled")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

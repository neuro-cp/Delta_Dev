from __future__ import annotations


def read_salience_log_as_step_scalar(path: str) -> dict[int, float]:
    """
    Read a salience trace log and aggregate absolute salience per step.

    CONTRACT:
    - No filtering
    - No thresholds
    - No shaping
    - Pure format translation
    """
    by_step: dict[int, float] = {}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # EXPECTED FORMAT (example):
            # step=123 channel=surprise delta=0.0042
            parts = line.split()

            step = None
            delta = None

            for p in parts:
                if p.startswith("step="):
                    step = int(p.split("=", 1)[1])
                elif p.startswith("delta="):
                    delta = float(p.split("=", 1)[1].rstrip(","))


            if step is None or delta is None:
                continue

            by_step.setdefault(step, 0.0)
            by_step[step] += abs(delta)

    return by_step

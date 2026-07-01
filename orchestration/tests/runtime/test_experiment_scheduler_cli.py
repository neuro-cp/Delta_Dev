from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_experiment_scheduler_cli_help_exposes_provider_smoke():
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "experiment_scheduler.py"),
            "--help",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "--enqueue-provider-smoke" in result.stdout
    assert "--enqueue-calibration" in result.stdout
    assert "--calibration-count" in result.stdout

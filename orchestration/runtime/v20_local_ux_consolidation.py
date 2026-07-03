from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v19_local_delta_console import run_delta_console_command


RUNTIME_V20A_FLAGS: dict[str, bool] = {
    "local_ux_consolidated": True,
    "command_mode_only": True,
    "live_provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class DeltaUXCommand:
    command_id: str
    command: str
    argument: str = ""

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_delta_ux_command(command: str, argument: str = "") -> dict[str, object]:
    cmd = DeltaUXCommand(_stable_id("v20a-command", command, argument), command, argument)
    if command in {"status", "ask", "recall", "synthesize", "session-start", "session-ask", "session-clear", "readiness", "provider-dry-run"}:
        output = run_delta_console_command(command, argument)
    elif command == "review-ui":
        output = _ui_pointer("reports/delta_review_dashboard.html")
    elif command == "quality-ui":
        output = _ui_pointer("ui/delta_quality_review_dashboard.html")
    elif command == "evaluator-dry-run":
        output = {"evaluator_live_call_performed": False, "dry_run": True, "advisory_only": True}
    elif command == "safety":
        output = _safety_status()
    else:
        output = {"error": "unknown_command", "command": command}
    return {
        "phase": "Runtime V2.0A",
        "command": cmd.as_dict(),
        "output": output,
        "invariant_flags": dict(RUNTIME_V20A_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_DESIGN",
    }


def validate_local_ux_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return flags["local_ux_consolidated"] is True and flags["command_mode_only"] is True and all(
        value is False for key, value in flags.items() if key not in {"local_ux_consolidated", "command_mode_only"}
    )


def _ui_pointer(path: str) -> dict[str, object]:
    return {"path": path, "exists": Path(path).exists(), "static_only": True, "executes_write": False}


def _safety_status() -> dict[str, object]:
    return {
        "model_b": "default_unchanged",
        "hyb1": "dormant_env_gated",
        "provider": "dry_run_by_default",
        "memory": "no_autonomous_writes",
        "recall": "candidate_context_only",
        "training": "disabled",
        "scheduler": "disabled",
        "action_execution": "disabled",
    }


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer
from orchestration.runtime.v17_limited_general_recall_trial import run_limited_general_recall_trial
from orchestration.runtime.v17_local_session_state import add_local_session_turn, clear_local_session
from orchestration.runtime.v18_evidence_quality_evaluation import run_evidence_quality_evaluation
from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial
from orchestration.runtime.v18_promotion_readiness_scorecard import run_promotion_readiness_scorecard
from orchestration.runtime.v19_console_review_workflow import export_console_review_action, review_candidate


RUNTIME_V19B_FLAGS: dict[str, bool] = {
    "local_delta_console_enabled": True,
    "command_mode_only": True,
    "provider_live_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class LocalDeltaConsoleCommand:
    command_id: str
    command: str
    argument: str = ""

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LocalDeltaConsoleResult:
    result_id: str
    command: str
    output: dict[str, object]
    safe: bool = True

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_delta_console_command(command: str, argument: str = "") -> dict[str, object]:
    cmd = LocalDeltaConsoleCommand(_stable_id("v19b-command", command, argument), command, argument)
    if command == "status":
        output = _status()
    elif command == "help":
        output = {"commands": ["ask", "recall", "synthesize", "feedback", "review", "quality", "readiness", "provider-dry-run", "session-start", "session-ask", "session-clear", "status", "help", "exit"]}
    elif command == "ask":
        output = route_local_knowledge_answer(argument).as_dict()
    elif command == "recall":
        output = run_limited_general_recall_trial(argument)
    elif command == "synthesize":
        output = synthesize_controlled_answer(argument)
    elif command == "quality":
        output = run_evidence_quality_evaluation()
    elif command == "readiness":
        output = run_promotion_readiness_scorecard()
    elif command == "provider-dry-run":
        output = run_provider_live_trial(argument, live_provider=False)
    elif command == "session-start":
        output = {"session_id": argument or "default", "started": True, "canonical": False}
    elif command == "session-ask":
        output = add_local_session_turn("default", argument)
    elif command == "session-clear":
        output = {"session_id": argument or "default", "cleared": clear_local_session(argument or "default"), "canonical": False}
    elif command == "feedback":
        output = {"feedback": argument, "captured_as_memory": False, "review_required": True}
    elif command == "review":
        output = {"review_ui": "ui/delta_quality_review_dashboard.html", "static_only": True}
    elif command == "export-approve":
        output = export_console_review_action("approve", argument)
    elif command == "export-reject":
        output = export_console_review_action("reject", argument)
    elif command == "export-defer":
        output = export_console_review_action("defer", argument)
    elif command == "review-candidate":
        output = review_candidate(argument)
    elif command == "exit":
        output = {"exit": True}
    else:
        output = {"error": "unknown_command", "command": command}
    result = LocalDeltaConsoleResult(_stable_id("v19b-result", command, argument), command, output)
    return {"phase": "Runtime V1.9B", "command": cmd.as_dict(), "result": result.as_dict(), "invariant_flags": dict(RUNTIME_V19B_FLAGS), "final_recommendation": "PROCEED_CONSOLE_APPROVAL_REJECT_DEFER_WORKFLOW"}


def validate_local_delta_console_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return flags["local_delta_console_enabled"] is True and flags["command_mode_only"] is True and all(value is False for key, value in flags.items() if key not in {"local_delta_console_enabled", "command_mode_only"})


def _status() -> dict[str, object]:
    return {
        "model_b": "default_unchanged",
        "hyb1": "dormant_env_gated",
        "provider_live": "disabled_by_default",
        "memory": "no_autonomous_writes",
        "recall": "candidate_context_only",
        "training": "disabled",
        "scheduler": "disabled",
        "action_execution": "disabled",
    }


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

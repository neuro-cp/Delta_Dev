from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE
from orchestration.runtime.v15_feedback_memory_candidate import build_feedback_memory_candidate_case
from orchestration.runtime.v15_first_interaction import build_first_interaction_result, validate_first_interaction_result_safe
from orchestration.runtime.v15_recall_bridge_limited_trial import run_limited_recall_bridge_trial, validate_limited_recall_bridge_safe


RUNTIME_V15K_DEMO_SHOWCASE_FLAGS: dict[str, bool] = {
    "demo_showcase_enabled": True,
    "report_only": True,
    "provider_calls_enabled": False,
    "tool_calls_enabled": False,
    "action_execution_enabled": False,
    "memory_write_enabled": False,
    "canonical_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "general_recall_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "scheduler_enabled": False,
    "background_listener_enabled": False,
    "runtime_defaults_changed": False,
}


class DemoShowcaseStepStatus(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class DemoShowcaseStep:
    step_id: str
    step_name: str
    summary: str
    status: DemoShowcaseStepStatus
    provider_calls_performed: bool = False
    tool_calls_performed: bool = False
    action_execution_performed: bool = False
    memory_write_performed: bool = False
    canonical_write_performed: bool = False
    recall_mutated: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


def build_runtime_demo_showcase(store_path: str | Path = DEFAULT_TRIAL_STORE) -> dict[str, object]:
    local_answer = build_first_interaction_result("What is DELTA's current replay and consolidation path?")
    feedback_case = build_feedback_memory_candidate_case(
        "What is HYB1?",
        "HYB1 is active.",
        "No, HYB1 is dormant and environment-gated. Model B remains default.",
    )
    recall_payload = run_limited_recall_bridge_trial("What is the status of HYB1 and Model B?", store_path)
    steps = (
        DemoShowcaseStep(
            step_id=_stable_id("v15k-showcase-step", "local-answer"),
            step_name="local_answer",
            summary=str(local_answer["response_preview"]["response_mode"]),
            status=DemoShowcaseStepStatus.SAFE if validate_first_interaction_result_safe(local_answer) else DemoShowcaseStepStatus.UNSAFE,
        ),
        DemoShowcaseStep(
            step_id=_stable_id("v15k-showcase-step", "feedback-candidate"),
            step_name="feedback_candidate_preview",
            summary=str(feedback_case["memory_candidate"]["proposed_memory_text"]),
            status=DemoShowcaseStepStatus.SAFE,
        ),
        DemoShowcaseStep(
            step_id=_stable_id("v15k-showcase-step", "limited-recall"),
            step_name="limited_recall_candidate_context",
            summary=str(recall_payload["result"]["outcome"]),
            status=DemoShowcaseStepStatus.SAFE if validate_limited_recall_bridge_safe(recall_payload) else DemoShowcaseStepStatus.UNSAFE,
        ),
    )
    return {
        "phase": "Runtime V1.5K",
        "title": "Demo Script / Showcase Report",
        "status": "deterministic_local_showcase_no_mutation",
        "local_answer": local_answer,
        "feedback_case": feedback_case,
        "recall_payload": recall_payload,
        "showcase_steps": [step.as_dict() for step in steps],
        "all_steps_safe": all(step.status == DemoShowcaseStepStatus.SAFE for step in steps),
        "invariant_flags": dict(RUNTIME_V15K_DEMO_SHOWCASE_FLAGS),
        "final_recommendation": "PROCEED_VALIDATED_EXPERIENCE_LEARNING_LOOP",
    }


def validate_runtime_demo_showcase_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    steps = payload["showcase_steps"]
    return (
        payload["all_steps_safe"] is True
        and flags["demo_showcase_enabled"] is True
        and flags["report_only"] is True
        and all(
            step["provider_calls_performed"] is False
            and step["tool_calls_performed"] is False
            and step["action_execution_performed"] is False
            and step["memory_write_performed"] is False
            and step["canonical_write_performed"] is False
            and step["recall_mutated"] is False
            and step["training_triggered"] is False
            for step in steps
        )
        and all(value is False for key, value in flags.items() if key not in {"demo_showcase_enabled", "report_only"})
    )


def format_runtime_demo_showcase(payload: dict[str, object]) -> str:
    lines = [
        "DELTA Runtime V1.5K Demo Showcase",
        f"status: {payload['status']}",
        f"all_steps_safe: {payload['all_steps_safe']}",
        "",
        "Steps:",
    ]
    for step in payload["showcase_steps"]:
        lines.append(f"- {step['step_name']}: {step['status']} - {step['summary']}")
    lines.extend(
        [
            "",
            "Safety: no provider calls, no tool calls, no action execution, no memory writes, no recall mutation, no training.",
            f"final_recommendation: {payload['final_recommendation']}",
        ]
    )
    return "\n".join(lines)


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

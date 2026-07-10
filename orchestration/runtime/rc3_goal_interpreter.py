"""Deterministic RC3-A goal interpretation.

The interpreter creates ephemeral GoalFrame objects only. It does not persist,
execute, or activate any capability.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from orchestration.runtime.rc3_foundation_state import (
    GoalFrame,
    SAFETY_DEFAULTS,
    _stable_id,
)


GOAL_CLASSES = (
    "immediate_request",
    "conversational_objective",
    "project_objective",
    "design_goal",
    "implementation_goal",
    "validation_goal",
    "constraint",
    "prohibition",
    "preference",
    "success_condition",
    "clarification_needed",
    "no_goal_detected",
)


@dataclass(frozen=True)
class GoalInterpretation:
    goal_frame: GoalFrame
    trace: dict[str, Any]


def interpret_goal(
    user_message: str,
    *,
    current_mode: str = "RC3-A",
    rc2_episode_reference: str | None = None,
    previous_goal: GoalFrame | None = None,
    explicit_operator_constraints: tuple[str, ...] = (),
) -> GoalInterpretation:
    text = " ".join(user_message.strip().split())
    lower = text.lower()
    non_goal = _is_non_goal(lower)
    conflicts = _constraint_conflicts(lower, explicit_operator_constraints)
    goal_type = _goal_type(lower, non_goal, conflicts)
    objective = _objective(text, goal_type, previous_goal)
    prohibitions = _prohibitions(lower) + tuple(explicit_operator_constraints)
    constraints = _constraints(lower, explicit_operator_constraints)
    success_criteria = _success_criteria(lower, goal_type)
    confidence = _confidence(goal_type, conflicts, lower)
    status = "awaiting_clarification" if goal_type == "clarification_needed" else "interpreted"
    uncertainty = "high_clarification_required" if status == "awaiting_clarification" else "moderate"
    turn_id = _stable_id("turn", text, current_mode)
    goal = GoalFrame(
        goal_id=_stable_id("goal", text, current_mode),
        source_user_text=text,
        normalized_objective=objective,
        goal_type=goal_type,
        explicitness="none" if non_goal else ("explicit" if confidence >= 0.75 else "ambiguous"),
        success_criteria=success_criteria,
        constraints=constraints,
        prohibited_actions=prohibitions,
        assumptions=_assumptions(goal_type),
        dependencies=("operator_clarification",) if status == "awaiting_clarification" else (),
        requested_resources=_requested_resources(lower),
        permitted_tools=(),
        prohibited_tools=_prohibited_tools(lower),
        priority=_priority(lower),
        status=status,
        confidence=confidence,
        uncertainty=uncertainty,
        operator_confirmation_status="not_confirmed",
        persistence_status="ephemeral",
        provenance={
            "source": "operator_text",
            "mode": current_mode,
            "rc2_episode_reference": rc2_episode_reference,
            "interpreter": "rc3_goal_interpreter",
        },
        creation_turn=turn_id,
        last_updated_turn=turn_id,
        superseded_goal=previous_goal.goal_id if _is_supersession(lower) and previous_goal else None,
        safety=dict(SAFETY_DEFAULTS),
    )
    trace = {
        "goal_type": goal_type,
        "matched_rules": _matched_rules(lower, non_goal, conflicts),
        "non_goal_detected": non_goal,
        "constraint_conflicts": conflicts,
        "previous_goal_used": previous_goal.goal_id if previous_goal and "continue" in lower else None,
        "safety": dict(SAFETY_DEFAULTS),
    }
    return GoalInterpretation(goal_frame=goal, trace=trace)


def _is_non_goal(lower: str) -> bool:
    return any(pattern in lower for pattern in (
        "i wonder whether",
        "maybe someday",
        "could be interesting",
        "just thinking",
        "what if",
    )) and not any(verb in lower for verb in ("design", "build", "implement", "validate", "create", "continue"))


def _constraint_conflicts(lower: str, explicit: tuple[str, ...]) -> tuple[str, ...]:
    conflicts: list[str] = []
    joined = lower + " " + " ".join(item.lower() for item in explicit)
    if ("do not implement" in joined or "don't implement" in joined) and "implement now" in joined:
        conflicts.append("implementation_requested_and_prohibited")
    if ("do not execute" in joined or "no execution" in joined) and "execute now" in joined:
        conflicts.append("execution_requested_and_prohibited")
    if re.search(r"(?<!do not )(?<!don't )(?<!never )\btouch delta-75\b", joined) and (
        "do not touch delta-75" in joined or "don't touch delta-75" in joined
    ):
        conflicts.append("delta_75_requested_and_prohibited")
    return tuple(conflicts)


def _goal_type(lower: str, non_goal: bool, conflicts: tuple[str, ...]) -> str:
    if conflicts:
        return "clarification_needed"
    if non_goal:
        return "no_goal_detected"
    if lower.startswith(("do not ", "don't ", "never ", "avoid ")):
        return "prohibition"
    if "success" in lower or "done when" in lower or "exit gate" in lower:
        return "success_condition"
    if "prefer" in lower or "i like" in lower:
        return "preference"
    if "validate" in lower or "test" in lower or "benchmark" in lower:
        return "validation_goal"
    if "design" in lower or "spec" in lower or "architecture" in lower:
        return "design_goal"
    if "implement" in lower or "build" in lower or "create" in lower:
        return "implementation_goal"
    if "continue" in lower or "finish" in lower or "work on" in lower:
        return "project_objective"
    if "?" in lower:
        return "conversational_objective"
    return "immediate_request"


def _objective(text: str, goal_type: str, previous_goal: GoalFrame | None) -> str:
    if goal_type == "no_goal_detected":
        return "No active goal detected from casual or speculative wording."
    if previous_goal and text.lower().startswith("continue"):
        return previous_goal.normalized_objective
    cleaned = re.sub(r"^(please|can you|could you|i want you to)\s+", "", text, flags=re.I)
    cleaned = re.split(r"\bbut\b|\bwithout\b|\bdo not\b|\bdon't\b", cleaned, maxsplit=1, flags=re.I)[0].strip(" .,")
    return cleaned or text


def _prohibitions(lower: str) -> tuple[str, ...]:
    items: list[str] = []
    mapping = {
        "implement": "do not implement",
        "execute": "do not execute",
        "provider": "do not invoke providers",
        "web": "do not use web services",
        "plugin": "do not create or activate plugins",
        "sandbox": "do not create sandboxes",
        "persist": "do not persist goals or plans automatically",
        "canonical": "do not write canonical memory",
        "noncanonical": "do not write noncanonical memory",
        "commit": "do not commit automatically",
        "push": "do not push automatically",
        "deploy": "do not deploy",
        "delta-75": "do not interact with DELTA-75",
    }
    negative = "do not" in lower or "don't" in lower or "without" in lower or "no " in lower
    if negative:
        for term, phrase in mapping.items():
            if term in lower:
                items.append(phrase)
    return tuple(dict.fromkeys(items))


def _constraints(lower: str, explicit: tuple[str, ...]) -> tuple[str, ...]:
    items = list(explicit)
    if "read-only" in lower or "read only" in lower:
        items.append("read-only")
    if "ephemeral" in lower:
        items.append("ephemeral")
    if "operator" in lower and "review" in lower:
        items.append("operator review required")
    if _prohibitions(lower):
        items.append("preserve explicit prohibitions")
    return tuple(dict.fromkeys(items))


def _success_criteria(lower: str, goal_type: str) -> tuple[str, ...]:
    criteria = []
    if "doc" in lower or "spec" in lower:
        criteria.append("documentation artifact created")
    if "test" in lower or "benchmark" in lower or "validate" in lower:
        criteria.append("focused validation passes")
    if "report" in lower:
        criteria.append("report generated")
    if goal_type == "no_goal_detected":
        return ("no action taken",)
    return tuple(criteria or ("operator confirms objective is correctly understood",))


def _confidence(goal_type: str, conflicts: tuple[str, ...], lower: str) -> float:
    if goal_type == "clarification_needed" or conflicts:
        return 0.35
    if goal_type == "no_goal_detected":
        return 0.92
    if any(term in lower for term in ("design", "implement", "build", "validate", "continue", "do not")):
        return 0.86
    return 0.66


def _assumptions(goal_type: str) -> tuple[str, ...]:
    if goal_type == "no_goal_detected":
        return ("Speculative wording should not become an active goal.",)
    return ("RC3-A remains read-only and non-executing.",)


def _requested_resources(lower: str) -> tuple[str, ...]:
    return tuple(item for item in ("docs", "reports", "tests", "ui", "developer overlay") if item in lower)


def _prohibited_tools(lower: str) -> tuple[str, ...]:
    tools = []
    if "provider" in lower:
        tools.append("providers")
    if "web" in lower:
        tools.append("web")
    if "plugin" in lower:
        tools.append("plugins")
    if "sandbox" in lower:
        tools.append("sandboxes")
    if "shell" in lower:
        tools.append("shell")
    return tuple(tools)


def _priority(lower: str) -> float:
    if "urgent" in lower or "high priority" in lower:
        return 0.85
    if "low priority" in lower:
        return 0.25
    return 0.5


def _is_supersession(lower: str) -> bool:
    return any(term in lower for term in ("forget that plan", "instead", "switch to", "work on documentation"))


def _matched_rules(lower: str, non_goal: bool, conflicts: tuple[str, ...]) -> tuple[str, ...]:
    rules = []
    if non_goal:
        rules.append("speculative_non_goal")
    if conflicts:
        rules.append("constraint_conflict")
    for term in ("design", "implement", "validate", "continue", "do not", "without"):
        if term in lower:
            rules.append(term.replace(" ", "_"))
    return tuple(rules)

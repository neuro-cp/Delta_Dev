"""Canonical projection helpers for conversational developmental teaching.

This module is intentionally not a second runtime.  The continuous runtime
controller remains the owner of curriculum and developmental state, the
conversational runtime owns objectives and requests, and DELTA owns workers.
These helpers only persist the controller's existing restart export beneath the
canonical conversational runtime root and provide a compact teaching projection.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from orchestration.runtime.continuous_runtime_controller import (
    ContinuousRuntimeController,
    export_continuous_mission_restart_state,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)


SCHEMA_VERSION = "conversational_developmental_teaching_v1"
_STATE_DIRECTORY = "developmental-teaching"
_QUESTION_PREFIX = re.compile(r"^(?:what|why|how|who|where|when|which|is|are|was|were|do|does|did|can|could|should|would)\b", re.IGNORECASE)
_CONTENT_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does", "did", "for", "from",
    "how", "i", "in", "is", "it", "learn", "me", "of", "or", "please", "the", "this", "to", "want", "what",
    "when", "where", "which", "who", "why", "with", "would", "you", "your",
})
_DOMAIN_TERMS = {
    "neuroscience": frozenset({
        "amygdala", "basal", "brain", "brainstem", "cerebellum", "cerebral", "cortex", "frontal", "ganglia",
        "hippocampus", "lobe", "motor", "neural", "neuron", "nervous", "occipital", "parietal", "peripheral",
        "prefrontal", "sensory", "spinal", "subcortical", "temporal", "thalamus",
    }),
    "physics": frozenset({
        "acceleration", "calculus", "derivative", "energy", "field", "force", "integral", "mass", "mechanics",
        "motion", "physics", "rate", "velocity", "wave", "work",
    }),
}


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}-{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


def _normalise(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _content_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[a-z0-9]+", _normalise(text).lower())
        if token not in _CONTENT_STOPWORDS and len(token) > 1
    )


def is_teaching_instruction(message: str) -> bool:
    """Recognize an explicit request to be taught without capturing ordinary questions."""

    text = _normalise(message).lower()
    patterns = (
        r"^(?:today\s+)?i\s+want\s+you\s+to\s+teach\s+me\s+.+",
        r"^teach\s+me\s+.+",
        r"^help\s+me\s+learn\s+.+",
        r"^walk\s+me\s+through\s+.+",
        r"^(?:today\s+)?i\s+want\s+to\s+learn\s+.+",
    )
    return any(re.match(pattern, text) for pattern in patterns)


def _topic_from_instruction(instruction: str) -> str:
    text = _normalise(instruction)
    patterns = (
        r"^(?:today\s+)?i\s+want\s+you\s+to\s+teach\s+me\s+",
        r"^teach\s+me\s+",
        r"^help\s+me\s+learn\s+",
        r"^walk\s+me\s+through\s+",
        r"^(?:today\s+)?i\s+want\s+to\s+learn\s+",
    )
    for pattern in patterns:
        candidate = re.sub(pattern, "", text, flags=re.IGNORECASE)
        if candidate != text:
            return candidate.strip(" .")
    return text.strip(" .")


def _curriculum_for_topic(topic: str) -> tuple[dict[str, str], ...]:
    lowered = topic.lower()
    if any(token in lowered for token in ("neuroanatomy", "brain anatomy", "nervous system")):
        return (
            {"title": "Nervous-system orientation", "goal": "distinguish the central and peripheral nervous systems"},
            {"title": "Major brain regions", "goal": "locate the cerebrum, cerebellum, and brainstem"},
            {"title": "Cerebral lobes", "goal": "compare the broad roles of the frontal, parietal, temporal, and occipital lobes"},
            {"title": "Subcortical structures", "goal": "relate the thalamus, amygdala, hippocampus, and basal ganglia to larger brain systems"},
            {"title": "Brainstem and cerebellum", "goal": "connect regulation, movement, and coordination to their major structures"},
            {"title": "Major pathways", "goal": "trace a simple sensory, motor, and memory-related pathway"},
        )
    if "physics" in lowered:
        return (
            {"title": "Qualitative mechanics", "goal": "describe motion, forces, and interactions without formal derivations"},
            {"title": "Energy and conservation", "goal": "relate work, energy transfer, and constraints"},
            {"title": "Waves and fields", "goal": "recognize how disturbances and interactions propagate"},
            {"title": "Mathematical mechanics", "goal": "apply rates of change to kinematics after the calculus prerequisite is ready"},
        )
    return (
        {"title": f"Orientation to {topic}", "goal": "identify the central questions, vocabulary, and boundaries"},
        {"title": "Core mechanisms", "goal": "explain the main relationships that make the topic work"},
        {"title": "Examples and limits", "goal": "apply the material to a concrete example and name an important limitation"},
        {"title": "Connections", "goal": "connect the topic to adjacent concepts and decide what to learn next"},
    )


def compile_teaching_plan(instruction: str) -> dict[str, Any]:
    """Compile a curriculum-shaped plan from explicit operator teaching intent."""

    topic = _topic_from_instruction(instruction) or "the requested topic"
    curriculum = _curriculum_for_topic(topic)
    lowered = topic.lower()
    domain = "neuroscience" if any(token in lowered for token in ("neuro", "brain", "nervous")) else "physics" if "physics" in lowered else "general_learning"
    prerequisites: tuple[dict[str, str], ...] = ()
    if domain == "physics":
        prerequisites = (
            {
                "topic": "introductory calculus",
                "needed_for": "mathematical mechanics and derivations",
                "safe_parallel_branch": "qualitative mechanics",
            },
        )
    return {
        "plan_id": _stable_id("teaching-plan", _normalise(instruction).lower()),
        "operator_instruction": _normalise(instruction),
        "topic": topic,
        "domain": domain,
        "curriculum": tuple(
            {
                "lesson_id": _stable_id("teaching-lesson", topic.lower(), str(index), item["title"]),
                "ordinal": index,
                **item,
            }
            for index, item in enumerate(curriculum, start=1)
        ),
        "prerequisites": prerequisites,
        "teaching_level": "introductory",
        "schema_version": SCHEMA_VERSION,
    }


def teaching_knowledge_contract(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Expose a controller-owned curriculum through the existing knowledge frontier."""

    topic = str(plan.get("topic") or "the requested topic")
    material_requirements = tuple(
        {
            "requirement_id": _stable_id("teaching-material-requirement", str(plan.get("plan_id") or ""), str(item.get("lesson_id") or "")),
            "text": str(item.get("title") or "lesson"),
        }
        for item in plan.get("curriculum", ())
        if isinstance(item, Mapping)
    )
    return {
        "full_operator_wording": str(plan.get("operator_instruction") or ""),
        "normalized_topic": topic,
        "requested_subtopics": tuple(item["text"] for item in material_requirements),
        "material_requirements": material_requirements,
        "evidence_source_constraints": ("local cognition first", "existing local evidence first"),
        "follow_up_question_policy": "ask only when materially needed",
        "budget_continuation_instruction": "bounded local teaching cycles under standing authority",
        "completion_report_instruction": "report what is covered, provisional, weak, and next",
        "prohibited_actions": (),
        "completion_criteria": tuple(f"teach {item['text']}" for item in material_requirements),
        "schema_version": SCHEMA_VERSION,
    }


def teaching_followup_scope(plan: Mapping[str, Any], message: str) -> str:
    """Return a narrow in-scope classification for a teaching follow-up.

    This is deliberately conservative.  Ordinary questions stay on the normal
    chat path unless they name an established domain or curriculum concept.
    """

    text = _normalise(message)
    if not text or not ("?" in text or _QUESTION_PREFIX.match(text)):
        return ""
    terms = set(_content_tokens(text))
    domain = str(plan.get("domain") or "")
    if terms & set(_DOMAIN_TERMS.get(domain, ())):
        return "domain_concept"
    curriculum_terms = {
        token
        for item in plan.get("curriculum", ())
        if isinstance(item, Mapping)
        for token in _content_tokens(f"{item.get('title') or ''} {item.get('goal') or ''}")
    }
    if terms & curriculum_terms:
        return "curriculum_concept"
    topic_terms = set(_content_tokens(str(plan.get("topic") or "")))
    return "topic_concept" if terms & topic_terms else ""


def compile_teaching_followup(
    plan: Mapping[str, Any],
    *,
    objective_id: str,
    message: str,
) -> dict[str, Any]:
    """Compile a single source-bound study request for an in-scope question."""

    question = _normalise(message)
    scope = teaching_followup_scope(plan, question)
    if not scope:
        return {}
    question_tokens = set(_content_tokens(question))
    lesson = next(
        (
            item
            for item in plan.get("curriculum", ())
            if isinstance(item, Mapping)
            and question_tokens
            & set(_content_tokens(f"{item.get('title') or ''} {item.get('goal') or ''}"))
        ),
        {},
    )
    followup_id = _stable_id(
        "teaching-followup",
        objective_id,
        str(plan.get("plan_id") or ""),
        question.lower(),
    )
    node_id = _stable_id("teaching-followup-node", followup_id, question.lower())
    return {
        "followup_id": followup_id,
        "node_id": node_id,
        "evidence_id": node_id,
        "objective_id": objective_id,
        "plan_id": str(plan.get("plan_id") or ""),
        "question": question,
        "question_tokens": tuple(sorted(question_tokens)),
        "scope": scope,
        "lesson_id": str(lesson.get("lesson_id") or ""),
        "lesson_title": str(lesson.get("title") or ""),
        "status": "queued",
        "local_study_authority": "standing_bounded_local_teaching",
        "understanding_assessment": {"state": "pending"},
        "claim_version_id": "",
        "operation_id": "",
        "created_at": "",
        "completed_at": "",
        "schema_version": SCHEMA_VERSION,
    }


def teaching_followup_requires_study(
    plan: Mapping[str, Any],
    followups: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
    message: str,
) -> bool:
    """Avoid a second study when the same bounded follow-up already resolved."""

    candidate = compile_teaching_followup(plan, objective_id="candidate", message=message)
    if not candidate:
        return False
    signature = tuple(candidate.get("question_tokens") or ())
    for item in followups:
        if not isinstance(item, Mapping):
            continue
        if tuple(item.get("question_tokens") or ()) == signature:
            return False
    return True


def render_teaching_followup_acknowledgement(followup: Mapping[str, Any]) -> str:
    question = str(followup.get("question") or "that part of the lesson")
    return (
        f"I do not have a retained, reviewed answer for {question} yet. "
        "I will check it through one bounded local study, keep the result provisional, and show you what it found."
    )


def render_teaching_followup_result(followup: Mapping[str, Any]) -> str:
    answer = str(followup.get("interpretation") or "").strip()
    question = str(followup.get("question") or "that question")
    if not answer:
        return f"I completed the bounded local study for {question}, but it did not produce a usable provisional explanation."
    return (
        f"I checked {question}\n\n{answer}\n\n"
        "This is newly learned provisional material, so I will keep its uncertainty and provenance attached until consolidation review."
    )


def render_physics_prerequisite_result(prerequisite: Mapping[str, Any]) -> str:
    """Render the completed prerequisite as a natural teaching update."""

    topic = str(prerequisite.get("topic") or "the linked prerequisite")
    explanation = str(prerequisite.get("interpretation") or "").strip()
    branch = str(prerequisite.get("needed_for") or "the derivation branch")
    if str(prerequisite.get("status") or "") == "competence_tested":
        detail = explanation or "The bounded competence check produced a source-bound explanation."
        resumed_lesson = str(prerequisite.get("parent_branch_resume_lesson_title") or branch)
        resumption = (
            f"That clears the linked prerequisite, so I can resume {resumed_lesson} provisionally while preserving the qualitative material already covered."
            if str(prerequisite.get("derivation_branch_state") or "") == "resumed"
            else f"That gives us a provisional basis to resume {branch}."
        )
        return (
            f"The {topic} prerequisite passed its bounded competence check.\n\n{detail}\n\n"
            f"{resumption} I will keep this prerequisite explanation pending consolidation while the rest of the physics curriculum continues."
        )
    return (
        f"The {topic} prerequisite still needs revision before I use it for {branch}. "
        "I will keep the derivation branch visibly blocked while the qualitative physics work can continue."
    )


def teaching_retention_prompt(followup: Mapping[str, Any]) -> str:
    topic = str(followup.get("topic") or "this topic")
    return (
        "This explanation is newly learned provisional material. "
        f"Should I remember it for future {topic} discussions?"
    )


def compile_physics_prerequisite(plan: Mapping[str, Any], *, objective_id: str) -> dict[str, Any]:
    """Represent a linked prerequisite without replacing the parent objective."""

    if str(plan.get("domain") or "") != "physics":
        return {}
    requirement = next(
        (item for item in plan.get("prerequisites", ()) if isinstance(item, Mapping)),
        {},
    )
    topic = str(requirement.get("topic") or "introductory calculus")
    prerequisite_id = _stable_id("teaching-prerequisite", objective_id, str(plan.get("plan_id") or ""), topic)
    node_id = _stable_id("teaching-prerequisite-node", objective_id, prerequisite_id, topic)
    return {
        "prerequisite_id": prerequisite_id,
        "prerequisite_objective_id": _stable_id("linked-prerequisite-objective", objective_id, prerequisite_id),
        "parent_objective_id": objective_id,
        "node_id": node_id,
        "evidence_id": node_id,
        "topic": topic,
        "needed_for": str(requirement.get("needed_for") or "mathematical derivations"),
        "safe_parallel_branch": str(requirement.get("safe_parallel_branch") or "qualitative mechanics"),
        "competence_requirement": (
            "explain how a derivative represents rate of change or how an integral represents accumulation "
            "in one mechanics application"
        ),
        "status": "permission_pending",
        "competence_test_state": "not_started",
        "derivation_branch_state": "blocked_by_prerequisite",
        "schema_version": SCHEMA_VERSION,
    }


def physics_prerequisite_resume_target(
    plan: Mapping[str, Any],
    prerequisite: Mapping[str, Any],
) -> dict[str, Any]:
    """Locate the plan-owned branch unlocked by a tested physics prerequisite."""

    curriculum = tuple(item for item in plan.get("curriculum", ()) if isinstance(item, Mapping))
    required_terms = set(_content_tokens(str(prerequisite.get("needed_for") or "")))
    candidates = []
    for cursor, lesson in enumerate(curriculum):
        lesson_terms = set(_content_tokens(f"{lesson.get('title') or ''} {lesson.get('goal') or ''}"))
        overlap = len(required_terms & lesson_terms)
        if overlap:
            candidates.append((overlap, cursor, lesson))
    if not candidates:
        return {}
    _, cursor, lesson = max(candidates, key=lambda item: (item[0], item[1]))
    return {
        "parent_branch_resume_cursor": cursor,
        "parent_branch_resume_lesson_id": str(lesson.get("lesson_id") or ""),
        "parent_branch_resume_lesson_title": str(lesson.get("title") or ""),
    }


def render_physics_prerequisite_prompt(prerequisite: Mapping[str, Any]) -> str:
    branch = str(prerequisite.get("safe_parallel_branch") or "qualitative physics")
    topic = str(prerequisite.get("topic") or "introductory calculus")
    needed_for = str(prerequisite.get("needed_for") or "rigorous derivations")
    return (
        f"I can begin with {branch} now, but {needed_for} will eventually require {topic}. "
        f"May I create a bounded linked prerequisite for {topic} while continuing the non-mathematical physics material?"
    )


def derive_teaching_pressures(
    plan: Mapping[str, Any],
    *,
    followups: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
    prerequisites: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
    consolidation_records: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]] = (),
    teaching_cursor: int = 0,
) -> tuple[dict[str, Any], ...]:
    """Project only evidence-backed developmental pressure from teaching state."""

    pressures: list[dict[str, Any]] = []
    for item in followups:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status") or "")
        claim_version_id = str(item.get("claim_version_id") or "")
        sealed_record = next(
            (
                record
                for record in consolidation_records
                if isinstance(record, Mapping)
                and claim_version_id
                and claim_version_id in set(str(value) for value in record.get("claim_version_ids", ()))
            ),
            None,
        )
        # The retention request is the operator's first durable memory boundary.
        # A result may be eligible for consolidation while it is waiting for that
        # answer, but idle attention must not advance it into a review-authority
        # prompt before the operator has chosen to retain it.
        if status == "retained_provisional" and sealed_record is None:
            pressures.append({
                "pressure_type": "epistemic_debt",
                "source_followup_id": str(item.get("followup_id") or ""),
                "reason": "A teaching follow-up remains provisional and eligible for governed consolidation.",
                "recommended_action": "continue_consolidation_boundary",
                "requires_operator": False,
                "priority": 2,
            })
        resume_cursor = int(item.get("curriculum_resume_cursor") or item.get("curriculum_cursor_at_completion") or 0)
        if status == "retained_provisional" and resume_cursor > teaching_cursor:
            pressures.append({
                "pressure_type": "integration_debt",
                "source_followup_id": str(item.get("followup_id") or ""),
                "reason": "A retained teaching result has not yet changed the parent curriculum cursor.",
                "recommended_action": "resume_parent_curriculum",
                "requires_operator": False,
                "priority": 3,
            })
    for item in prerequisites:
        if isinstance(item, Mapping) and str(item.get("status") or "") == "permission_pending":
            pressures.append({
                "pressure_type": "prerequisite_blockage",
                "source_prerequisite_id": str(item.get("prerequisite_id") or ""),
                "reason": f"The derivation branch depends on {str(item.get('topic') or 'a prerequisite')}.",
                "recommended_action": "await_operator_prerequisite_permission",
                "requires_operator": True,
                "priority": 3,
            })
    for record in consolidation_records:
        if not isinstance(record, Mapping):
            continue
        review_status = str(
            record.get("review_status")
            or record.get("review_authorization_status")
            or ""
        )
        if review_status not in {"pending_external_review", "authorized_pending_external_review"}:
            continue
        pressures.append({
            "pressure_type": "external_review_pending",
            "source_record_id": str(record.get("packet_id") or ""),
            "reason": "A sealed teaching packet is awaiting the separately governed external review boundary.",
            "recommended_action": "await_external_review",
            "requires_operator": False,
            "priority": 0,
        })
    return tuple(sorted(pressures, key=lambda item: (-int(item["priority"]), item["pressure_type"])))


def render_first_lesson(plan: Mapping[str, Any]) -> str:
    """Render a useful, concise opening before any additional learning is claimed."""

    topic = str(plan.get("topic") or "this topic")
    curriculum = tuple(item for item in plan.get("curriculum", ()) if isinstance(item, Mapping))
    first = curriculum[0] if curriculum else {"title": "Orientation", "goal": "establish a useful starting point"}
    lowered = topic.lower()
    if str(plan.get("domain") or "") == "neuroscience":
        body = (
            "A useful starting point is the nervous system's overall layout. The central nervous system consists of the brain and spinal cord; "
            "the peripheral nervous system carries sensory information toward it and motor commands away from it. "
            "That map makes the later structures easier to place rather than memorizing isolated labels."
        )
    elif str(plan.get("domain") or "") == "physics":
        body = (
            "We can start with qualitative mechanics: describe what moves, what interacts with it, and how those interactions change motion. "
            "That gives us useful intuition before we introduce the calculus needed for rigorous rates and derivations."
        )
    else:
        body = (
            f"We will begin by establishing the core vocabulary and boundaries of {topic}, then move from mechanisms to examples and limits. "
            "I will keep the sequence explicit so later questions can change the next teaching step."
        )
    return (
        f"Let's begin with {topic}.\n\n{body}\n\n"
        f"First section: {str(first.get('title') or 'Orientation')}. "
        f"Our immediate aim is to {str(first.get('goal') or 'build a useful foundation')}.")


def next_lesson(plan: Mapping[str, Any], cursor: int) -> Mapping[str, Any] | None:
    curriculum = tuple(item for item in plan.get("curriculum", ()) if isinstance(item, Mapping))
    return curriculum[cursor] if 0 <= cursor < len(curriculum) else None


def render_curriculum_resumption(plan: Mapping[str, Any], cursor: int) -> str:
    upcoming = next_lesson(plan, cursor)
    if upcoming is None:
        return "The current teaching outline is complete. I will keep any remaining uncertainty visible rather than claiming more coverage than we established."
    return (
        f"That updates our working foundation. Next, we can cover {str(upcoming.get('title') or 'the next section')}: "
        f"{str(upcoming.get('goal') or 'connect it to the rest of the topic')}."
    )


def teaching_controller_path(runtime_root: str | Path, objective_id: str) -> Path:
    return Path(runtime_root) / _STATE_DIRECTORY / f"{objective_id}.json"


def start_teaching_controller(
    *,
    runtime_id: str,
    objective_id: str,
    plan: Mapping[str, Any],
) -> ContinuousRuntimeController:
    """Start the existing controller with conversation-scoped teaching state."""

    session_id = f"conversational-teaching:{runtime_id}:{objective_id}"
    controller = start_continuous_runtime_controller(session_id=session_id)
    teaching = {
        "objective_id": objective_id,
        "runtime_id": runtime_id,
        "plan": dict(plan),
        "teaching_cursor": 0,
        "stage": "first_lesson_delivered",
        "pending_studies": (),
        "retention_records": (),
        "consolidation_records": (),
        "developmental_pressures": (),
        "created_at": "",
        "updated_at": "",
        "schema_version": SCHEMA_VERSION,
    }
    return replace(
        controller,
        continuous_mission_state="conversational_teaching_active",
        continuous_mission_contract={
            "mission_type": "operator_conversational_teaching",
            "objective_id": objective_id,
            "plan_id": str(plan.get("plan_id") or ""),
            "topic": str(plan.get("topic") or ""),
        },
        continuous_learning_state={
            **dict(controller.continuous_learning_state or {}),
            "conversational_teaching": teaching,
        },
        active_work_item=str((next_lesson(plan, 0) or {}).get("title") or "teaching orientation"),
    )


def teaching_state(controller: ContinuousRuntimeController) -> dict[str, Any]:
    return dict(dict(controller.continuous_learning_state or {}).get("conversational_teaching") or {})


def update_teaching_state(
    controller: ContinuousRuntimeController,
    **updates: Any,
) -> ContinuousRuntimeController:
    current = teaching_state(controller)
    updated = {**current, **updates, "schema_version": SCHEMA_VERSION}
    return replace(
        controller,
        continuous_learning_state={
            **dict(controller.continuous_learning_state or {}),
            "conversational_teaching": updated,
        },
    )


def save_teaching_controller(
    runtime_root: str | Path,
    controller: ContinuousRuntimeController,
    *,
    objective_id: str,
) -> Path:
    """Persist only the existing controller restart export under the normal root."""

    path = teaching_controller_path(runtime_root, objective_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "objective_id": objective_id,
        "schema_version": SCHEMA_VERSION,
        "controller_restart_state": export_continuous_mission_restart_state(controller),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def load_teaching_controller(
    runtime_root: str | Path,
    *,
    runtime_id: str,
    objective_id: str,
) -> ContinuousRuntimeController | None:
    """Restore the controller from the canonical conversation-scoped checkpoint."""

    path = teaching_controller_path(runtime_root, objective_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        restart_state = dict(payload.get("controller_restart_state") or {})
        if str(payload.get("objective_id") or "") != objective_id:
            return None
        session_id = f"conversational-teaching:{runtime_id}:{objective_id}"
        if str(restart_state.get("session_id") or "") != session_id:
            return None
        return restore_continuous_mission_restart_state(
            start_continuous_runtime_controller(session_id=session_id),
            restart_state,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def teaching_snapshot(controller: ContinuousRuntimeController | None) -> dict[str, Any]:
    if controller is None:
        return {}
    state = teaching_state(controller)
    plan = dict(state.get("plan") or {})
    return {
        "controller_id": controller.controller_id,
        "session_id": controller.session_id,
        "mission_state": controller.continuous_mission_state,
        "objective_id": str(state.get("objective_id") or ""),
        "topic": str(plan.get("topic") or ""),
        "teaching_cursor": int(state.get("teaching_cursor") or 0),
        "stage": str(state.get("stage") or ""),
        "pending_studies": tuple(state.get("pending_studies") or ()),
        "retention_records": tuple(state.get("retention_records") or ()),
        "consolidation_records": tuple(state.get("consolidation_records") or ()),
        "developmental_pressures": tuple(state.get("developmental_pressures") or ()),
        "plan": plan,
        "schema_version": SCHEMA_VERSION,
    }


__all__ = [
    "SCHEMA_VERSION",
    "compile_teaching_plan",
    "compile_teaching_followup",
    "compile_physics_prerequisite",
    "physics_prerequisite_resume_target",
    "derive_teaching_pressures",
    "is_teaching_instruction",
    "load_teaching_controller",
    "next_lesson",
    "render_curriculum_resumption",
    "render_first_lesson",
    "render_physics_prerequisite_prompt",
    "render_physics_prerequisite_result",
    "render_teaching_followup_acknowledgement",
    "render_teaching_followup_result",
    "teaching_followup_requires_study",
    "teaching_followup_scope",
    "teaching_retention_prompt",
    "save_teaching_controller",
    "start_teaching_controller",
    "teaching_controller_path",
    "teaching_knowledge_contract",
    "teaching_snapshot",
    "teaching_state",
    "update_teaching_state",
]

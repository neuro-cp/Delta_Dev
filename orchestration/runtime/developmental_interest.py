"""Evidence-grounded developmental interest and goal-proposal compilation.

This module is deliberately pure.  The continuous controller owns persistence,
operator approval, restart, and learning lifecycle activation.  Interests are
compiled only from caller-supplied capability and gap evidence; no topic catalog,
model suggestion, provider, or web source is consulted here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.capability_evaluation_strategy import compile_capability_evaluation_strategy
from orchestration.runtime.delta_1_0_common import stable_id, utc_now


MAX_CANDIDATE_INTERESTS = 5


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _text(*values: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").lower() for value in values)


@dataclass(frozen=True)
class DevelopmentalInterestCandidate:
    interest_id: str
    origin_state_id: str
    domain: str
    topic: str
    target_capability: str
    capability_type: str
    candidate_class: str
    source_gap_ids: tuple[str, ...]
    prerequisite_dependencies: tuple[str, ...]
    current_capability_evidence: tuple[str, ...]
    uncertainty: str
    expected_learning_value: float
    transfer_value: float
    prerequisite_value: float
    information_gain: float
    evaluator_plan_id: str
    evaluator_state: str
    resource_state: str
    authority_state: str
    estimated_effort: float
    estimated_cost: float
    estimated_risk: float
    redundancy_state: str
    mission_scope_fit: float
    recency: float
    novelty: float
    score_components: Mapping[str, float]
    rank_score: float
    selection_rationale: str
    rejection_reasons: tuple[str, ...]
    semantic_identity: str
    candidate_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalGoalProposal:
    proposal_id: str
    selected_interest_id: str
    operator_context: str
    proposed_goal: str
    domain: str
    topic: str
    target_capability: str
    measurable_outcome: str
    source_evidence: tuple[str, ...]
    prerequisite_state: tuple[str, ...]
    resource_plan: Mapping[str, Any]
    evaluator_plan: Mapping[str, Any]
    evaluator_independence_state: str
    authority_requirements: tuple[str, ...]
    expected_learning_value: float
    expected_transfer_value: float
    effort_and_budget: Mapping[str, float]
    risk: float
    stopping_conditions: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    next_step_policy: str
    alternative_interest_ids: tuple[str, ...]
    created_at: str
    proposal_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PersistentDevelopmentalAgenda:
    """Durable controller-owned references for one bounded agenda session."""

    agenda_id: str
    agenda_version: str
    operator_scope: str
    status: str
    active_mission_id: str
    pending_proposal_id: str
    current_candidate_set_id: str
    completed_goal_ids: tuple[str, ...]
    blocked_goal_ids: tuple[str, ...]
    rejected_proposal_ids: tuple[str, ...]
    deferred_proposal_ids: tuple[str, ...]
    cooldown_records: tuple[dict[str, Any], ...]
    evaluator_blockers: tuple[str, ...]
    resource_blockers: tuple[str, ...]
    recent_capability_updates: tuple[str, ...]
    unresolved_gap_ids: tuple[str, ...]
    candidate_history: tuple[str, ...]
    proposal_history: tuple[str, ...]
    decision_history: tuple[str, ...]
    mission_outcome_history: tuple[dict[str, Any], ...]
    cycle_count: int
    successful_cycle_count: int
    failed_cycle_count: int
    rejected_cycle_count: int
    deferred_cycle_count: int
    consecutive_failure_count: int
    remaining_session_budget: int
    remaining_attempt_budget: int
    remaining_proposal_budget: int
    maximum_consecutive_failures: int
    last_material_evidence_digest: str
    last_rank_digest: str
    next_eligible_transition: str
    exhaustion_reasons: tuple[str, ...]
    created_at: str
    updated_at: str
    agenda_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_governed_autonomous_interest_instruction(instruction: str) -> bool:
    """Recognize the explicit operator request without treating every broad goal as one."""

    text = " ".join(str(instruction or "").lower().split())
    return (
        "continue developing your capabilities" in text
        and ("valuable thing" in text or "ask for approval" in text or "learn next" in text)
    )


def is_persistent_developmental_agenda_instruction(instruction: str) -> bool:
    text = " ".join(str(instruction or "").lower().split())
    return "continue your governed developmental agenda" in text and "one goal at a time" in text


def material_evidence_digest(
    *,
    capability_inventory: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    outcome_history: Sequence[Mapping[str, Any]] = (),
    cooldown_records: Sequence[Mapping[str, Any]] = (),
    budgets: Mapping[str, Any] | None = None,
) -> str:
    """Exclude restart/presentation fields; include only eligibility-changing state."""

    return _digest(
        {
            "capabilities": tuple(sorted(_digest(dict(item)) for item in capability_inventory)),
            "sources": tuple(sorted(_digest(dict(item)) for item in sources)),
            "outcomes": tuple(sorted(_digest(dict(item)) for item in outcome_history)),
            "cooldowns": tuple(sorted(_digest(dict(item)) for item in cooldown_records)),
            "budgets": dict(budgets or {}),
        }
    )


def compile_persistent_developmental_agenda(
    *,
    operator_scope: str,
    material_digest: str,
    cycle_budget: int = 3,
    proposal_budget: int = 3,
    attempt_budget: int = 3,
    failure_budget: int = 2,
) -> PersistentDevelopmentalAgenda:
    """Create the smallest agenda state; execution and persistence stay external."""

    payload = {
        "operator_scope": operator_scope,
        "material_digest": material_digest,
        "cycle_budget": cycle_budget,
        "proposal_budget": proposal_budget,
        "attempt_budget": attempt_budget,
        "failure_budget": failure_budget,
    }
    agenda_id = stable_id("persistent-developmental-agenda", _digest(payload))
    return PersistentDevelopmentalAgenda(
        agenda_id=agenda_id, agenda_version="1", operator_scope=operator_scope, status="idle",
        active_mission_id="", pending_proposal_id="", current_candidate_set_id="", completed_goal_ids=(),
        blocked_goal_ids=(), rejected_proposal_ids=(), deferred_proposal_ids=(), cooldown_records=(),
        evaluator_blockers=(), resource_blockers=(), recent_capability_updates=(), unresolved_gap_ids=(),
        candidate_history=(), proposal_history=(), decision_history=(), mission_outcome_history=(),
        cycle_count=0, successful_cycle_count=0, failed_cycle_count=0, rejected_cycle_count=0,
        deferred_cycle_count=0, consecutive_failure_count=0, remaining_session_budget=cycle_budget,
        remaining_attempt_budget=attempt_budget, remaining_proposal_budget=proposal_budget,
        maximum_consecutive_failures=failure_budget,
        last_material_evidence_digest=material_digest, last_rank_digest="", next_eligible_transition="compile_candidates",
        exhaustion_reasons=(), created_at=utc_now(), updated_at=utc_now(), agenda_digest=_digest(payload),
    )


def agenda_state_is_valid(agenda: Mapping[str, Any]) -> bool:
    required = {
        "agenda_id", "status", "active_mission_id", "pending_proposal_id", "cycle_count",
        "remaining_session_budget", "remaining_attempt_budget", "remaining_proposal_budget",
        "maximum_consecutive_failures", "last_material_evidence_digest", "mission_outcome_history", "cooldown_records",
    }
    if not required.issubset(agenda):
        return False
    if int(agenda.get("remaining_session_budget") or 0) < 0 or int(agenda.get("remaining_proposal_budget") or 0) < 0:
        return False
    if agenda.get("active_mission_id") and agenda.get("pending_proposal_id"):
        return False
    return str(agenda.get("status") or "") in {
        "idle", "compiling_candidates", "proposal_pending", "mission_active", "awaiting_mission_outcome", "awaiting_evaluator_authority",
        "refreshing_evidence", "cooldown", "blocked", "exhausted", "paused", "completed_session",
    }


def source_records_from_state(
    *,
    learning_state: Mapping[str, Any],
    capability_inventory: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Translate existing persisted evidence into bounded interest inputs.

    ``interest_sources`` is an explicit controller-owned evidence surface used by
    prior evaluation/reassessment records.  It is intentionally not a topic list.
    The spectral next-gap record is the existing concrete cross-scope source.
    """

    sources = [dict(item) for item in (learning_state.get("interest_sources") or ()) if isinstance(item, Mapping)]
    next_gap = dict(learning_state.get("next_learning_gap") or {})
    if next_gap:
        sources.append(
            {
                "source_kind": "unresolved_evaluation_scope",
                "domain": "mathematics",
                "topic": "spectral_theorem",
                "target_capability": str(next_gap.get("capability_dimension") or ""),
                "target_behavior": "demonstrate the declared scope on independently sealed cases",
                "source_gap_ids": (str(next_gap.get("gap_id") or ""),),
                "prerequisites": tuple(next_gap.get("prerequisites") or ()),
                "evidence": (str(next_gap.get("reason") or ""),),
                "resource_state": "available_provisional_or_retained",
                "authority_state": str(next_gap.get("authority") or "operator_approval_required"),
                "allow_evaluator_acquisition": True,
                "expected_learning_value": 0.76,
                "transfer_value": 0.71,
                "prerequisite_value": 0.84,
                "information_gain": 0.82,
                "estimated_effort": 0.45,
                "estimated_risk": 0.12,
            }
        )
    for record in capability_inventory:
        limitations = tuple(str(item) for item in (record.get("limitations") or ()) if str(item))
        if not limitations or str(record.get("status") or "") == "functional":
            continue
        sources.append(
            {
                "source_kind": "capability_limitation",
                "domain": str(record.get("category") or "developmental"),
                "topic": str(record.get("capability_id") or ""),
                "target_capability": str(record.get("capability_id") or ""),
                "target_behavior": "resolve a pre-existing limitation with an independently evaluated bounded result",
                "source_gap_ids": tuple(str(item) for item in limitations),
                "prerequisites": (),
                "evidence": tuple(str(item) for item in (record.get("evidence") or ())),
                "resource_state": "unknown",
                "authority_state": "operator_approval_required",
                "allow_evaluator_acquisition": False,
                "expected_learning_value": 0.52,
                "transfer_value": 0.44,
                "prerequisite_value": 0.46,
                "information_gain": 0.48,
                "estimated_effort": 0.65,
                "estimated_risk": 0.2,
            }
        )
    return tuple(sources[:MAX_CANDIDATE_INTERESTS])


def _is_broad_or_unmeasurable(source: Mapping[str, Any]) -> bool:
    target = _text(source.get("target_capability"), source.get("target_behavior"))
    return not str(source.get("target_capability") or "").strip() or not str(source.get("target_behavior") or "").strip() or any(
        phrase in target for phrase in ("better at science", "master science", "general intelligence", "become better")
    )


def _authority_rejected(authority_state: str) -> bool:
    return any(token in authority_state.lower() for token in ("blocked", "protected", "unavailable", "denied"))


def compile_developmental_interest_candidates(
    *,
    origin_state_id: str,
    operator_context: str,
    sources: Sequence[Mapping[str, Any]],
    capability_inventory: Sequence[Mapping[str, Any]] = (),
    active_or_recent_semantics: Sequence[str] = (),
    rejected_semantics: Sequence[str] = (),
) -> tuple[DevelopmentalInterestCandidate, ...]:
    """Compile a deterministic, evidence-bounded candidate set.

    Every candidate has a source record and a persisted rejection result.  A
    missing evaluator is actionable only as the narrower evaluator-acquisition
    interest; it never becomes permission to start ordinary learning.
    """

    acquired = {
        str(item.get("capability_id") or "")
        for item in capability_inventory
        if str(item.get("status") or "") in {"functional", "reliable", "transferable"}
    }
    active_or_recent = set(str(item) for item in active_or_recent_semantics)
    rejected = set(str(item) for item in rejected_semantics)
    compiled: list[DevelopmentalInterestCandidate] = []
    for raw in tuple(sources)[:MAX_CANDIDATE_INTERESTS]:
        source = dict(raw)
        domain = str(source.get("domain") or "unclassified")
        topic = str(source.get("topic") or "unclassified")
        target = str(source.get("target_capability") or "")
        behavior = str(source.get("target_behavior") or "")
        semantic = _digest(
            {
                "domain": domain,
                "topic": topic,
                "target": target,
                "behavior": behavior,
                "source_gaps": tuple(sorted(str(item) for item in (source.get("source_gap_ids") or ()) if item)),
                "prerequisites": tuple(sorted(str(item) for item in (source.get("prerequisites") or ()) if item)),
                "evidence": tuple(sorted(str(item) for item in (source.get("evidence") or ()) if item)),
            }
        )
        strategy = compile_capability_evaluation_strategy(
            mission_id=origin_state_id,
            capability_id=target or "unmeasurable_interest",
            subgoal_id=stable_id("interest-evaluation-subgoal", semantic),
            domain=domain,
            topic=topic,
            capability_target=target,
            target_behavior=behavior,
            teaching_evidence_ids=tuple(str(item) for item in (source.get("teaching_evidence_ids") or ())),
            capability_context={"required_scope": str(source.get("required_scope") or "declared candidate scope")},
            evaluator_authorities=tuple(source.get("evaluator_authorities") or ()),
        )
        plan = dict(strategy["selected_plan"])
        evaluator_state = str(plan.get("status") or "evaluation_unavailable")
        resource_state = str(source.get("resource_state") or "unknown")
        authority_state = str(source.get("authority_state") or "operator_approval_required")
        candidate_class = str(source.get("candidate_class") or "develop_new_bounded_capability")
        reasons: list[str] = []
        if _is_broad_or_unmeasurable(source):
            reasons.append("target_behavior_undefined_or_too_broad")
        if target in acquired:
            reasons.append("capability_already_demonstrated_at_requested_scope")
        if semantic in active_or_recent:
            reasons.append("equivalent_goal_active_or_recently_completed")
        if semantic in rejected:
            reasons.append("operator_rejected_goal_in_cooldown")
        if _authority_rejected(authority_state):
            reasons.append("authority_unavailable")
        if resource_state in {"unavailable", "blocked", "unknown"}:
            reasons.append("resource_path_unavailable")
        if evaluator_state == "evaluation_unavailable":
            if bool(source.get("allow_evaluator_acquisition")) and not reasons:
                candidate_class = "acquire_evaluator_authority"
            else:
                reasons.append("independent_evaluator_unavailable")
        redundancy = "redundant" if any("equivalent" in item or "already_demonstrated" in item for item in reasons) else "distinct"
        ready = 1.0 if evaluator_state == "evaluation_plan_ready" else 0.55 if candidate_class == "acquire_evaluator_authority" else 0.0
        resource_ready = 1.0 if resource_state.startswith("available") else 0.0
        values = {
            "operator_goal_relevance": float(source.get("operator_goal_relevance") or 0.75),
            "prerequisite_value": float(source.get("prerequisite_value") or 0.5),
            "expected_learning_value": float(source.get("expected_learning_value") or 0.5),
            "transfer_value": float(source.get("transfer_value") or 0.45),
            "evaluator_readiness": ready,
            "resource_readiness": resource_ready,
            "information_gain": float(source.get("information_gain") or 0.45),
            "mission_scope_fit": 1.0,
            "novelty": min(0.2, float(source.get("novelty") or 0.1)),
            "effort_penalty": float(source.get("estimated_effort") or 0.5),
            "risk_penalty": float(source.get("estimated_risk") or 0.15),
            "redundancy_penalty": 1.0 if reasons else 0.0,
        }
        score = round(
            values["operator_goal_relevance"] * 0.18
            + values["prerequisite_value"] * 0.16
            + values["expected_learning_value"] * 0.16
            + values["transfer_value"] * 0.13
            + values["evaluator_readiness"] * 0.14
            + values["resource_readiness"] * 0.09
            + values["information_gain"] * 0.1
            + values["mission_scope_fit"] * 0.08
            + values["novelty"] * 0.01
            - values["effort_penalty"] * 0.04
            - values["risk_penalty"] * 0.04
            - values["redundancy_penalty"],
            4,
        )
        blocking_reasons = {"authority_unavailable", "resource_path_unavailable", "independent_evaluator_unavailable"}
        status = (
            "candidate_interest" if not reasons
            else "blocked" if any(reason in blocking_reasons for reason in reasons)
            else "rejected"
        )
        rationale = (
            "ranked from source gap, prerequisite value, expected learning and transfer value, "
            "evaluator/resource readiness, information gain, effort, risk, and weak novelty pressure"
        )
        payload = {"semantic": semantic, "strategy": plan.get("plan_id"), "class": candidate_class, "reasons": tuple(reasons)}
        compiled.append(
            DevelopmentalInterestCandidate(
                interest_id=stable_id("developmental-interest", semantic), origin_state_id=origin_state_id,
                domain=domain, topic=topic, target_capability=target,
                capability_type=str(strategy["requirement"].get("capability_type") or "unknown"), candidate_class=candidate_class,
                source_gap_ids=tuple(str(item) for item in (source.get("source_gap_ids") or ()) if item),
                prerequisite_dependencies=tuple(str(item) for item in (source.get("prerequisites") or ()) if item),
                current_capability_evidence=tuple(str(item) for item in (source.get("evidence") or ()) if item),
                uncertainty=str(source.get("uncertainty") or "candidate remains subject to independent evaluation"),
                expected_learning_value=values["expected_learning_value"], transfer_value=values["transfer_value"],
                prerequisite_value=values["prerequisite_value"], information_gain=values["information_gain"],
                evaluator_plan_id=str(plan.get("plan_id") or ""), evaluator_state=evaluator_state,
                resource_state=resource_state, authority_state=authority_state,
                estimated_effort=values["effort_penalty"], estimated_cost=float(source.get("estimated_cost") or 0.0),
                estimated_risk=values["risk_penalty"], redundancy_state=redundancy,
                mission_scope_fit=values["mission_scope_fit"], recency=1.0 if semantic in active_or_recent else 0.0,
                novelty=values["novelty"], score_components=values, rank_score=score,
                selection_rationale=rationale, rejection_reasons=tuple(reasons), semantic_identity=semantic,
                candidate_digest=_digest(payload), status=status,
            )
        )
    ranked = sorted(compiled, key=lambda item: (item.status != "candidate_interest", -item.rank_score, item.semantic_identity))
    return tuple(ranked)


def compile_developmental_goal_proposal(
    *,
    operator_context: str,
    candidates: Sequence[DevelopmentalInterestCandidate],
) -> DevelopmentalGoalProposal | None:
    valid = [item for item in candidates if item.status == "candidate_interest"]
    if not valid:
        return None
    selected = valid[0]
    evaluator_acquisition = selected.candidate_class == "acquire_evaluator_authority"
    proposed_goal = (
        f"Acquire independently sealed evaluation material for {selected.target_capability}"
        if evaluator_acquisition
        else f"Learn {selected.topic} by demonstrating {selected.target_capability}"
    )
    payload = {"interest": selected.semantic_identity, "goal": proposed_goal, "context": operator_context}
    alternatives = tuple(item.interest_id for item in valid[1:3])
    return DevelopmentalGoalProposal(
        proposal_id=stable_id("developmental-goal-proposal", _digest(payload)), selected_interest_id=selected.interest_id,
        operator_context=operator_context, proposed_goal=proposed_goal, domain=selected.domain, topic=selected.topic,
        target_capability=selected.target_capability,
        measurable_outcome=(
            "retain a separately authored sealed evaluator covering baseline, control, held-out, adversarial, and transfer cases"
            if evaluator_acquisition else "pass the selected independent evaluation plan on baseline, control, held-out, adversarial, and transfer cases"
        ),
        source_evidence=selected.current_capability_evidence + selected.source_gap_ids,
        prerequisite_state=selected.prerequisite_dependencies,
        resource_plan={"state": selected.resource_state, "existing_only": True},
        evaluator_plan={"plan_id": selected.evaluator_plan_id, "state": selected.evaluator_state, "strategy": "evaluator_acquisition" if evaluator_acquisition else "selected_independent_strategy"},
        evaluator_independence_state=selected.evaluator_state,
        authority_requirements=("explicit operator approval required before developmental mission activation",),
        expected_learning_value=selected.expected_learning_value, expected_transfer_value=selected.transfer_value,
        effort_and_budget={"estimated_effort": selected.estimated_effort, "estimated_cost": selected.estimated_cost},
        risk=selected.estimated_risk,
        stopping_conditions=("independent evaluation unavailable", "resource path becomes unavailable", "operator rejects or defers proposal", "one bounded developmental mission activation completed"),
        success_criteria=("proposal remains bounded and evidence-linked", "no learning begins before approval", "existing learning lifecycle receives the approved goal only once"),
        failure_conditions=("evaluator teaching leakage", "candidate-mutable evaluator", "missing resource authority", "duplicate or redundant capability"),
        next_step_policy="after approval, compile exactly one existing developmental-learning mission; do not auto-propose a second goal",
        alternative_interest_ids=alternatives, created_at=utc_now(), proposal_digest=_digest(payload), status="pending_operator_approval",
    )


__all__ = [
    "MAX_CANDIDATE_INTERESTS", "DevelopmentalInterestCandidate", "DevelopmentalGoalProposal", "PersistentDevelopmentalAgenda",
    "is_governed_autonomous_interest_instruction", "source_records_from_state",
    "is_persistent_developmental_agenda_instruction", "material_evidence_digest", "compile_persistent_developmental_agenda", "agenda_state_is_valid",
    "compile_developmental_interest_candidates", "compile_developmental_goal_proposal",
]

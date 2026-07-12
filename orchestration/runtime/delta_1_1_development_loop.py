"""DELTA 1.1 governed introspective development loop.

This module implements the first operator-governed developmental cycle. It can
observe local evidence, propose and rank objectives, prepare plans, evaluate
approved outcomes, and produce lesson candidates. It does not approve itself,
execute implementation, call providers, retrieve from the web, persist hidden
state, commit, push, schedule work, or mutate production systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from orchestration.runtime.delta_1_0_common import jsonable, safety_metadata, stable_id, utc_now, write_json, write_markdown


REPORT_ROOT = Path("reports") / "delta_1_1"

OBSERVATION_TYPES = (
    "behavioral_failure",
    "repeated_regression",
    "operator_correction",
    "failed_validation",
    "repair_group",
    "conversation_pathology",
    "implementation_weakness",
)

OBJECTIVE_STATES = (
    "PROPOSED",
    "AWAITING_OPERATOR_APPROVAL",
    "APPROVED",
    "PLANNED",
    "IMPLEMENTATION_READY",
    "EVALUATING",
    "LESSON_REVIEW",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
)

SESSION_STATES = (
    "OBSERVATION",
    "OBJECTIVE_PROPOSAL",
    "PLANNING",
    "APPROVAL",
    "IMPLEMENTATION",
    "VALIDATION",
    "EVALUATION",
    "LESSON_PROPOSAL",
    "OPERATOR_DISPOSITION",
    "COMPLETE",
)

LESSON_STATES = ("CANDIDATE", "OPERATOR_REVIEW", "APPROVED_NONCANONICAL", "REJECTED", "REVISED", "ARCHIVED")

PROHIBITED_AUTHORITIES = (
    "provider_calls",
    "network_calls",
    "external_retrieval",
    "hidden_persistence",
    "automatic_implementation",
    "automatic_commit",
    "automatic_push",
    "scheduler_authority",
    "production_mutation",
    "delta_75_interaction",
)


@dataclass(frozen=True)
class DevelopmentObservation:
    observation_id: str
    observation_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    affected_runtime_areas: tuple[str, ...]
    severity: float
    frequency: int
    confidence: float
    conclusion: str = "evidence_only"
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentObjectiveV11:
    objective_id: str
    title: str
    description: str
    originating_evidence: tuple[str, ...]
    affected_runtime_areas: tuple[str, ...]
    estimated_benefit: float
    estimated_effort: float
    estimated_implementation_risk: float
    estimated_regression_risk: float
    confidence: float
    dependencies: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    completion_requirements: tuple[str, ...]
    rollback_conditions: tuple[str, ...]
    state: str = "PROPOSED"
    operator_approved: bool = False
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectivePriority:
    objective_id: str
    score: float
    rank: int
    operator_impact: float
    frequency: float
    regression_severity: float
    architectural_leverage: float
    implementation_effort_inverse: float
    confidence: float
    rationale: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentPlan:
    plan_id: str
    objective_id: str
    implementation_scope: str
    affected_files: tuple[str, ...]
    affected_symbols: tuple[str, ...]
    reusable_systems: tuple[str, ...]
    required_tests: tuple[str, ...]
    validation_sequence: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    approval_required: bool = True
    executable_now: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentEvidencePacket:
    evidence_id: str
    sources: tuple[str, ...]
    observations: tuple[str, ...]
    tests: tuple[str, ...]
    operator_comments: tuple[str, ...]
    repository_inspection: tuple[str, ...]
    local_only: bool = True
    provider_used: bool = False
    web_used: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ImprovementEvaluation:
    evaluation_id: str
    objective_id: str
    before_summary: str
    after_summary: str
    behavioral_improvement: float | None
    regression_count: int
    validation_success: bool
    operator_burden: str
    repair_size: str
    architectural_complexity: str
    evidence_refs: tuple[str, ...]
    fabricated_scores: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LessonCandidateV11:
    lesson_id: str
    objective_id: str
    what_improved: str
    what_failed: str
    remaining_weaknesses: tuple[str, ...]
    unexpected_effects: tuple[str, ...]
    regression_risk: str
    future_recommendations: tuple[str, ...]
    state: str = "CANDIDATE"
    canonical: bool = False
    operator_approval_required: bool = True
    evidence_refs: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiry:
    inquiry_id: str
    reason: str
    question: str
    options: tuple[str, ...]
    blocks_progress: bool
    triggered_by: str
    confidence: float
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class WikipediaPermissionProfile:
    capability: str = "WIKIPEDIA_TEXT_READ_ONLY"
    enabled: bool = False
    allowed_domains: tuple[str, ...] = ("wikipedia.org",)
    allowed_content: tuple[str, ...] = ("article_text", "page_title", "section_headings", "revision_timestamp", "canonical_url", "reference_metadata")
    prohibited_content: tuple[str, ...] = ("images", "audio", "video", "ocr", "captions", "media_downloads", "pdf_parsing", "commons_browsing", "visual_inference")
    max_queries_per_objective: int = 1
    max_pages_per_query: int = 1
    max_total_characters: int = 20_000
    auto_follow_links: bool = False
    external_links_blocked: bool = True
    operator_approval_required: bool = True
    persistence: str = "ephemeral_by_default"
    network_calls_allowed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class WikipediaRetrievalSessionState:
    session_id: str
    objective_id: str
    query: str
    profile: WikipediaPermissionProfile
    approval_requested: bool
    operator_approved: bool
    retrieval_performed: bool
    provenance_required: bool = True
    contradiction_check_required: bool = True
    stop_conditions: tuple[str, ...] = (
        "non_wikipedia_domain_requested",
        "operator_denies_approval",
        "query_budget_exceeded",
        "high_stakes_claim_detected",
        "network_call_attempted_while_disabled",
    )
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentSession:
    session_id: str
    state: str
    observations: tuple[DevelopmentObservation, ...]
    objectives: tuple[DevelopmentObjectiveV11, ...]
    priorities: tuple[ObjectivePriority, ...]
    selected_objective_id: str
    evidence_packet: DevelopmentEvidencePacket | None
    plan: DevelopmentPlan | None
    inquiries: tuple[OperatorInquiry, ...]
    evaluation: ImprovementEvaluation | None
    lesson_candidate: LessonCandidateV11 | None
    wikipedia_state: WikipediaRetrievalSessionState | None
    operator_approval_required: bool
    implementation_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def observe_development_evidence(records: Iterable[Mapping[str, Any]]) -> tuple[DevelopmentObservation, ...]:
    observations: list[DevelopmentObservation] = []
    for index, record in enumerate(records, start=1):
        observation_type = str(record.get("observation_type") or _infer_observation_type(str(record.get("summary") or "")))
        if observation_type not in OBSERVATION_TYPES:
            observation_type = "implementation_weakness"
        summary = " ".join(str(record.get("summary") or "").split())
        evidence_refs = tuple(str(item) for item in record.get("evidence_refs", ()) if item)
        areas = tuple(str(item) for item in record.get("affected_runtime_areas", ()) if item) or _infer_areas(summary)
        severity = _bounded_float(record.get("severity", _infer_severity(summary)), default=0.5)
        frequency = max(1, int(record.get("frequency", 1) or 1))
        confidence = _bounded_float(record.get("confidence", 0.72), default=0.72)
        observations.append(
            DevelopmentObservation(
                observation_id=stable_id("delta11-observation", index, observation_type, summary, evidence_refs),
                observation_type=observation_type,
                summary=summary,
                evidence_refs=evidence_refs,
                affected_runtime_areas=areas,
                severity=severity,
                frequency=frequency,
                confidence=confidence,
            )
        )
    return tuple(observations)


def build_evidence_packet(observations: Iterable[DevelopmentObservation], *, operator_comments: tuple[str, ...] = (), tests: tuple[str, ...] = (), repository_inspection: tuple[str, ...] = ()) -> DevelopmentEvidencePacket:
    obs = tuple(observations)
    sources = tuple(sorted({ref for item in obs for ref in item.evidence_refs}))
    return DevelopmentEvidencePacket(
        evidence_id=stable_id("delta11-evidence", sources, operator_comments, tests, repository_inspection),
        sources=sources,
        observations=tuple(item.observation_id for item in obs),
        tests=tests,
        operator_comments=operator_comments,
        repository_inspection=repository_inspection,
    )


def generate_candidate_objectives(observations: Iterable[DevelopmentObservation]) -> tuple[DevelopmentObjectiveV11, ...]:
    obs = tuple(observations)
    if not obs:
        return ()
    grouped = _group_observations(obs)
    objectives: list[DevelopmentObjectiveV11] = []
    for key, items in grouped.items():
        areas = tuple(sorted({area for item in items for area in item.affected_runtime_areas}))
        refs = tuple(sorted({ref for item in items for ref in item.evidence_refs}))
        benefit = _average(item.severity for item in items) * min(1.0, 0.55 + 0.08 * len(items))
        effort = 0.45 if len(areas) <= 2 else 0.7
        implementation_risk = 0.25 + (0.12 * max(0, len(areas) - 1))
        regression_risk = 0.3 + (0.08 * len(items))
        confidence = _average(item.confidence for item in items)
        title = _objective_title(key)
        objectives.append(
            DevelopmentObjectiveV11(
                objective_id=stable_id("delta11-objective", key, refs, areas),
                title=title,
                description=_objective_description(key, items),
                originating_evidence=refs,
                affected_runtime_areas=areas,
                estimated_benefit=round(min(1.0, benefit), 3),
                estimated_effort=round(min(1.0, effort), 3),
                estimated_implementation_risk=round(min(1.0, implementation_risk), 3),
                estimated_regression_risk=round(min(1.0, regression_risk), 3),
                confidence=round(confidence, 3),
                dependencies=("operator_approval", "focused_tests", "local_evidence_only"),
                validation_requirements=("focused_unit_tests", "behavioral_validation", "governance_validation", "failure_path_validation"),
                completion_requirements=("focused_tests_pass", "no_governance_regression", "before_after_evidence_recorded"),
                rollback_conditions=("focused_regression", "governance_regression", "scope_creep", "operator_rejection"),
            )
        )
    return tuple(objectives)


def prioritize_objectives(objectives: Iterable[DevelopmentObjectiveV11], observations: Iterable[DevelopmentObservation]) -> tuple[ObjectivePriority, ...]:
    obs = tuple(observations)
    priorities: list[ObjectivePriority] = []
    for objective in objectives:
        related = [item for item in obs if set(item.evidence_refs) & set(objective.originating_evidence) or set(item.affected_runtime_areas) & set(objective.affected_runtime_areas)]
        frequency = min(1.0, sum(item.frequency for item in related) / 8.0)
        severity = _average((item.severity for item in related), default=0.5)
        leverage = min(1.0, 0.35 + (0.15 * len(objective.affected_runtime_areas)))
        effort_inverse = 1.0 - objective.estimated_effort
        operator_impact = objective.estimated_benefit
        score = round(
            (operator_impact * 0.3)
            + (frequency * 0.2)
            + (severity * 0.18)
            + (leverage * 0.14)
            + (effort_inverse * 0.1)
            + (objective.confidence * 0.08),
            4,
        )
        priorities.append(
            ObjectivePriority(
                objective_id=objective.objective_id,
                score=score,
                rank=0,
                operator_impact=round(operator_impact, 3),
                frequency=round(frequency, 3),
                regression_severity=round(severity, 3),
                architectural_leverage=round(leverage, 3),
                implementation_effort_inverse=round(effort_inverse, 3),
                confidence=objective.confidence,
                rationale=(
                    f"Score combines operator impact {operator_impact:.2f}, frequency {frequency:.2f}, "
                    f"severity {severity:.2f}, leverage {leverage:.2f}, effort inverse {effort_inverse:.2f}, "
                    f"and confidence {objective.confidence:.2f}."
                ),
            )
        )
    ranked = sorted(priorities, key=lambda item: item.score, reverse=True)
    return tuple(
        ObjectivePriority(
            objective_id=item.objective_id,
            score=item.score,
            rank=index,
            operator_impact=item.operator_impact,
            frequency=item.frequency,
            regression_severity=item.regression_severity,
            architectural_leverage=item.architectural_leverage,
            implementation_effort_inverse=item.implementation_effort_inverse,
            confidence=item.confidence,
            rationale=item.rationale,
        )
        for index, item in enumerate(ranked, start=1)
    )


def select_best_objective(objectives: Iterable[DevelopmentObjectiveV11], priorities: Iterable[ObjectivePriority]) -> DevelopmentObjectiveV11 | None:
    by_id = {item.objective_id: item for item in objectives}
    top = next(iter(sorted(priorities, key=lambda item: item.rank or 9999)), None)
    return by_id.get(top.objective_id) if top else None


def request_operator_approval(objective: DevelopmentObjectiveV11, reason: str = "objective_requires_operator_approval") -> OperatorInquiry:
    return OperatorInquiry(
        inquiry_id=stable_id("delta11-inquiry", objective.objective_id, reason),
        reason=reason,
        question=f"Approve objective '{objective.title}' for bounded planning and implementation proposal?",
        options=("approve", "revise", "reject", "request_more_evidence"),
        blocks_progress=True,
        triggered_by=objective.objective_id,
        confidence=objective.confidence,
    )


def approve_objective(objective: DevelopmentObjectiveV11, *, operator_approved: bool) -> DevelopmentObjectiveV11:
    if not operator_approved:
        return replace(objective, state="AWAITING_OPERATOR_APPROVAL", operator_approved=False)
    return replace(objective, state="APPROVED", operator_approved=True)


def generate_development_plan(objective: DevelopmentObjectiveV11) -> DevelopmentPlan:
    files, symbols, reusable, tests = _plan_targets(objective)
    approved = bool(objective.operator_approved and objective.state == "APPROVED")
    return DevelopmentPlan(
        plan_id=stable_id("delta11-plan", objective.objective_id, files, symbols),
        objective_id=objective.objective_id,
        implementation_scope=_scope_for_objective(objective),
        affected_files=files,
        affected_symbols=symbols,
        reusable_systems=reusable,
        required_tests=tests,
        validation_sequence=("py_compile_changed_files", "focused_unit_tests", "behavioral_validation", "governance_validation", "failure_path_validation"),
        stop_conditions=objective.rollback_conditions + ("operator_cancels", "dirty_tree_attribution_unsafe"),
        approval_required=True,
        executable_now=approved,
    )


def evaluate_improvement(objective: DevelopmentObjectiveV11, *, before: Mapping[str, Any], after: Mapping[str, Any], evidence_refs: tuple[str, ...]) -> ImprovementEvaluation:
    before_passed = int(before.get("passed", 0) or 0)
    before_total = int(before.get("total", before_passed) or before_passed)
    after_passed = int(after.get("passed", 0) or 0)
    after_total = int(after.get("total", after_passed) or after_passed)
    improvement: float | None = None
    if before_total and after_total:
        improvement = round((after_passed / after_total) - (before_passed / before_total), 4)
    regressions = int(after.get("regressions", 0) or 0)
    return ImprovementEvaluation(
        evaluation_id=stable_id("delta11-evaluation", objective.objective_id, before, after, evidence_refs),
        objective_id=objective.objective_id,
        before_summary=str(before.get("summary") or "before evidence recorded"),
        after_summary=str(after.get("summary") or "after evidence recorded"),
        behavioral_improvement=improvement,
        regression_count=regressions,
        validation_success=bool(after.get("validation_success", False)) and regressions == 0,
        operator_burden=str(after.get("operator_burden") or "unknown"),
        repair_size=str(after.get("repair_size") or "unknown"),
        architectural_complexity=str(after.get("architectural_complexity") or "unknown"),
        evidence_refs=evidence_refs,
        fabricated_scores=improvement is None,
    )


def generate_lesson_candidate(objective: DevelopmentObjectiveV11, evaluation: ImprovementEvaluation) -> LessonCandidateV11:
    improved = "Validation improved" if evaluation.validation_success else "Improvement not proven"
    failed = "No regression observed" if evaluation.regression_count == 0 else f"{evaluation.regression_count} regression(s) remain"
    weaknesses = () if evaluation.validation_success else ("requires additional focused evidence",)
    return LessonCandidateV11(
        lesson_id=stable_id("delta11-lesson", objective.objective_id, evaluation.evaluation_id),
        objective_id=objective.objective_id,
        what_improved=improved,
        what_failed=failed,
        remaining_weaknesses=weaknesses,
        unexpected_effects=(),
        regression_risk=evaluation.architectural_complexity,
        future_recommendations=("retain only after operator review", "reuse focused before/after evidence for similar objectives"),
        state="OPERATOR_REVIEW",
        canonical=False,
        operator_approval_required=True,
        evidence_refs=evaluation.evidence_refs,
    )


def dispose_lesson_candidate(lesson: LessonCandidateV11, disposition: str, *, operator_approved: bool) -> LessonCandidateV11:
    if disposition not in LESSON_STATES:
        raise ValueError(f"unknown lesson disposition: {disposition}")
    if disposition == "APPROVED_NONCANONICAL" and not operator_approved:
        return lesson
    return replace(lesson, state=disposition, canonical=False)


def build_wikipedia_readiness(objective_id: str, query: str, *, operator_approved: bool = False) -> WikipediaRetrievalSessionState:
    profile = WikipediaPermissionProfile()
    return WikipediaRetrievalSessionState(
        session_id=stable_id("delta11-wikipedia-session", objective_id, query),
        objective_id=objective_id,
        query=query.strip(),
        profile=profile,
        approval_requested=True,
        operator_approved=operator_approved,
        retrieval_performed=False,
    )


def run_development_session(records: Iterable[Mapping[str, Any]], *, operator_approved: bool = False, after_evidence: Mapping[str, Any] | None = None) -> DevelopmentSession:
    observations = observe_development_evidence(records)
    evidence = build_evidence_packet(
        observations,
        operator_comments=("development marathon requested governed introspective loop",),
        tests=("focused runtime tests required",),
        repository_inspection=("existing delta_1_0 and v31 learning scaffolds reused",),
    )
    objectives = generate_candidate_objectives(observations)
    priorities = prioritize_objectives(objectives, observations)
    selected = select_best_objective(objectives, priorities)
    inquiries: tuple[OperatorInquiry, ...] = ()
    plan = None
    evaluation = None
    lesson = None
    wikipedia = None
    state = "OBJECTIVE_PROPOSAL"
    selected_id = selected.objective_id if selected else ""
    if selected:
        if not operator_approved:
            inquiries = (request_operator_approval(selected),)
            state = "APPROVAL"
        approved = approve_objective(selected, operator_approved=operator_approved)
        plan = generate_development_plan(approved)
        wikipedia = build_wikipedia_readiness(approved.objective_id, "feedback loops", operator_approved=False)
        if operator_approved and after_evidence:
            state = "LESSON_PROPOSAL"
            evaluation = evaluate_improvement(
                approved,
                before={"passed": 0, "total": 1, "summary": "pre-approval behavior requires focused baseline"},
                after=after_evidence,
                evidence_refs=tuple(after_evidence.get("evidence_refs", ("focused-validation",))),
            )
            lesson = generate_lesson_candidate(approved, evaluation)
        elif operator_approved:
            state = "IMPLEMENTATION"
        objectives = tuple(approved if item.objective_id == approved.objective_id else item for item in objectives)
    return DevelopmentSession(
        session_id=stable_id("delta11-session", tuple(item.observation_id for item in observations), operator_approved, after_evidence or {}),
        state=state,
        observations=observations,
        objectives=objectives,
        priorities=priorities,
        selected_objective_id=selected_id,
        evidence_packet=evidence,
        plan=plan,
        inquiries=inquiries,
        evaluation=evaluation,
        lesson_candidate=lesson,
        wikipedia_state=wikipedia,
        operator_approval_required=not operator_approved,
    )


def sample_development_records() -> tuple[dict[str, Any], ...]:
    return (
        {
            "observation_type": "conversation_pathology",
            "summary": "Natural topic drift with 'but now' was misclassified as contradiction.",
            "evidence_refs": ("PID-005", "reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md"),
            "affected_runtime_areas": ("rc2_contradiction_engine", "rc2_conversational_mode_router"),
            "severity": 0.78,
            "frequency": 2,
            "confidence": 0.9,
        },
        {
            "observation_type": "conversation_pathology",
            "summary": "Render correction and summarize-previous requests needed explicit previous-answer scoping.",
            "evidence_refs": ("PID-003", "reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md"),
            "affected_runtime_areas": ("rc2_render_correction", "rc2_conversational_mode_router"),
            "severity": 0.72,
            "frequency": 2,
            "confidence": 0.88,
        },
        {
            "observation_type": "conversation_pathology",
            "summary": "Ambiguous referents and follow-ups selected or repeated context instead of asking clarification.",
            "evidence_refs": ("PID-B04", "PID-B03", "reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md"),
            "affected_runtime_areas": ("rc2_cognitive_episode", "rc2_conversational_mode_router"),
            "severity": 0.82,
            "frequency": 3,
            "confidence": 0.91,
        },
        {
            "observation_type": "operator_correction",
            "summary": "Operator requested governed introspective loop before external retrieval and Wikipedia only after operator inquiry.",
            "evidence_refs": ("operator-grounding-wikipedia-text-only",),
            "affected_runtime_areas": ("delta_1_1_development_loop", "wikipedia_readiness"),
            "severity": 0.66,
            "frequency": 1,
            "confidence": 0.86,
        },
    )


def build_architecture_overview() -> dict[str, Any]:
    return {
        "status": "DELTA_1_1_GOVERNED_INTROSPECTIVE_DEVELOPMENT_LOOP_IMPLEMENTED",
        "layers": {
            "RC2": "conversation and routing evidence source",
            "PC1": "pragmatic cognition evidence source",
            "RC3": "goal and planning scaffolds reused conceptually",
            "RC4": "governed action boundaries remain disabled",
            "RC5": "developmental lesson concepts reused",
            "DELTA_1_0": "objective, module, and learning-loop governance reused",
            "DELTA_1_1": "session lifecycle tying observations, objectives, planning, evaluation, and lessons",
        },
        "no_duplicate_state": True,
        "authority": "operator_governed_proposal_and_evaluation_only",
        "safety": safety_metadata(),
    }


def build_objective_lifecycle_report() -> dict[str, Any]:
    observations = observe_development_evidence(sample_development_records())
    objectives = generate_candidate_objectives(observations)
    priorities = prioritize_objectives(objectives, observations)
    return {
        "objectives": objectives,
        "priorities": priorities,
        "selected_objective_id": select_best_objective(objectives, priorities).objective_id if objectives else "",
        "operator_approval_required": True,
        "safety": safety_metadata(),
    }


def build_observation_model_report() -> dict[str, Any]:
    observations = observe_development_evidence(sample_development_records())
    packet = build_evidence_packet(observations)
    return {
        "observation_types": OBSERVATION_TYPES,
        "observations": observations,
        "evidence_packet": jsonable(packet),
        "observations_are_conclusions": False,
        "safety": safety_metadata(),
    }


def build_lesson_lifecycle_report() -> dict[str, Any]:
    session = run_development_session(
        sample_development_records(),
        operator_approved=True,
        after_evidence={
            "passed": 5,
            "total": 5,
            "regressions": 0,
            "validation_success": True,
            "operator_burden": "moderate",
            "repair_size": "bounded",
            "architectural_complexity": "low_to_medium",
            "evidence_refs": ("focused-tests", "behavioral-validation"),
        },
    )
    candidate = session.lesson_candidate
    approved_attempt = dispose_lesson_candidate(candidate, "APPROVED_NONCANONICAL", operator_approved=False) if candidate else None
    return {
        "lesson_states": LESSON_STATES,
        "candidate": jsonable(candidate),
        "approval_without_operator_changes_state": bool(approved_attempt and candidate and approved_attempt.state != candidate.state),
        "canonical": False,
        "safety": safety_metadata(),
    }


def build_validation_report() -> dict[str, Any]:
    session = run_development_session(sample_development_records())
    checks = {
        "observations_created": len(session.observations) >= 4,
        "objectives_created": len(session.objectives) >= 2,
        "priorities_ranked": len(session.priorities) == len(session.objectives),
        "operator_inquiry_blocks_progress": bool(session.inquiries and session.inquiries[0].blocks_progress),
        "plan_not_executable_without_approval": bool(session.plan and not session.plan.executable_now),
        "wikipedia_disabled": bool(session.wikipedia_state and not session.wikipedia_state.profile.enabled and not session.wikipedia_state.retrieval_performed),
        "safety_clean": all(value is False for value in session.safety.values()),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "focused_tests_expected": ("tests/delta_1_1/test_development_loop.py",),
        "safety": safety_metadata(),
    }


def build_readiness_review() -> dict[str, Any]:
    validation = build_validation_report()
    return {
        "implemented": (
            "development observation engine",
            "development objective engine",
            "objective prioritization",
            "development planner",
            "local evidence engine",
            "lesson candidate engine",
            "lesson governance",
            "improvement evaluation",
            "operator inquiry framework",
            "development session lifecycle",
            "disabled wikipedia text-readiness foundation",
            "integrated workflow report",
        ),
        "tested": validation["focused_tests_expected"],
        "validated": validation["passed"],
        "future_work": (
            "operator UI for inquiry disposition",
            "actual implementation execution only after explicit approval",
            "future wikipedia retrieval adapter remains disabled until separately gated",
        ),
        "maturity_claim": "governed_development_loop_ready_for_operator_review_not_autonomy",
        "safety": safety_metadata(),
    }


def build_optimization_report() -> dict[str, Any]:
    return {
        "optimization_pass": {
            "duplicated_logic": "new module reuses delta_1_0 safety/id/report helpers and does not edit dirty router state",
            "duplicate_state": "session object references objective/evidence/lesson objects rather than separate stores",
            "unnecessary_architecture": "single additive module chosen over routing rewrite",
            "unused_helpers": "focused tests exercise public helpers",
            "routing_precedence": "no router precedence changed in this implementation",
            "governance_consistency": "all safety flags remain false; approval gates block execution and lesson retention",
            "naming": "DELTA 1.1 objects use delta11 prefixes and explicit V11 suffixes where needed",
        },
        "recommended_refactors": (),
        "safety": safety_metadata(),
    }


def build_integrated_workflow_report() -> dict[str, Any]:
    session = run_development_session(sample_development_records())
    return {
        "workflow": (
            "RC2",
            "PC1",
            "RC3",
            "RC4",
            "RC5",
            "DELTA_1_0",
            "Development Observation",
            "Objective Engine",
            "Planning",
            "Evaluation",
            "Lesson Candidate",
            "Operator Review",
        ),
        "session_state": session.state,
        "selected_objective_id": session.selected_objective_id,
        "operator_review_required": session.operator_approval_required,
        "implementation_performed": session.implementation_performed,
        "safety": safety_metadata(),
    }


def write_delta_1_1_reports(root: str | Path = REPORT_ROOT, *, write: bool = True) -> dict[str, Any]:
    payload = {
        "architecture_overview": build_architecture_overview(),
        "objective_lifecycle": build_objective_lifecycle_report(),
        "observation_model": build_observation_model_report(),
        "lesson_lifecycle": build_lesson_lifecycle_report(),
        "validation_report": build_validation_report(),
        "readiness_review": build_readiness_review(),
        "optimization_report": build_optimization_report(),
        "integrated_workflow": build_integrated_workflow_report(),
        "safety": safety_metadata(),
    }
    if write:
        root_path = Path(root)
        for name, data in payload.items():
            if name == "safety":
                continue
            write_json(root_path / f"{name}.json", data)
            write_markdown(root_path / f"{name}.md", f"DELTA 1.1 {name.replace('_', ' ').title()}", data)
    return payload


def _infer_observation_type(summary: str) -> str:
    lower = summary.lower()
    if "operator" in lower or "correction" in lower:
        return "operator_correction"
    if "test" in lower or "validation" in lower:
        return "failed_validation"
    if "repair" in lower:
        return "repair_group"
    if "regression" in lower:
        return "repeated_regression"
    if "conversation" in lower or "follow" in lower or "topic" in lower or "contradiction" in lower:
        return "conversation_pathology"
    return "behavioral_failure"


def _infer_areas(summary: str) -> tuple[str, ...]:
    lower = summary.lower()
    areas = []
    for token, area in (
        ("contradiction", "rc2_contradiction_engine"),
        ("render", "rc2_render_correction"),
        ("follow", "rc2_cognitive_episode"),
        ("topic", "rc2_cognitive_episode"),
        ("memory", "rc2_conversational_mode_router"),
        ("operator", "operator_governance"),
    ):
        if token in lower:
            areas.append(area)
    return tuple(dict.fromkeys(areas or ["development_loop"]))


def _infer_severity(summary: str) -> float:
    lower = summary.lower()
    if any(term in lower for term in ("provider", "canonical", "memory", "authority")):
        return 0.85
    if any(term in lower for term in ("contradiction", "ambiguous", "regression")):
        return 0.78
    return 0.62


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return default


def _average(values: Iterable[float], *, default: float = 0.0) -> float:
    items = list(values)
    return sum(items) / len(items) if items else default


def _group_observations(observations: tuple[DevelopmentObservation, ...]) -> dict[str, tuple[DevelopmentObservation, ...]]:
    buckets: dict[str, list[DevelopmentObservation]] = {
        "discourse_boundary_arbitration": [],
        "development_governance_loop": [],
        "wikipedia_readiness": [],
    }
    for item in observations:
        text = f"{item.summary} {' '.join(item.affected_runtime_areas)}".lower()
        if "wikipedia" in text:
            buckets["wikipedia_readiness"].append(item)
        elif "operator" in text and "loop" in text:
            buckets["development_governance_loop"].append(item)
        else:
            buckets["discourse_boundary_arbitration"].append(item)
    return {key: tuple(value) for key, value in buckets.items() if value}


def _objective_title(key: str) -> str:
    titles = {
        "discourse_boundary_arbitration": "Improve conversational correction, topic-shift, and contradiction boundary arbitration",
        "development_governance_loop": "Strengthen governed introspective development session lifecycle",
        "wikipedia_readiness": "Prepare disabled Wikipedia text-only readiness gate",
    }
    return titles.get(key, f"Improve {key.replace('_', ' ')}")


def _objective_description(key: str, observations: tuple[DevelopmentObservation, ...]) -> str:
    summaries = "; ".join(item.summary for item in observations[:3])
    return f"Address recurring {key.replace('_', ' ')} deficit using local evidence: {summaries}"


def _plan_targets(objective: DevelopmentObjectiveV11) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    title = objective.title.lower()
    if "wikipedia" in title:
        return (
            ("orchestration/runtime/delta_1_1_development_loop.py",),
            ("WikipediaPermissionProfile", "WikipediaRetrievalSessionState", "build_wikipedia_readiness"),
            ("delta_1_0_common.safety_metadata",),
            ("tests/delta_1_1/test_development_loop.py::test_wikipedia_profile_is_disabled_and_text_only",),
        )
    if "session lifecycle" in title:
        return (
            ("orchestration/runtime/delta_1_1_development_loop.py",),
            ("DevelopmentSession", "run_development_session", "OperatorInquiry"),
            ("delta_1_0_objective_engine", "delta_1_0_learning_loop"),
            ("tests/delta_1_1/test_development_loop.py::test_session_blocks_at_operator_approval_without_authorization",),
        )
    return (
        (
            "orchestration/runtime/rc2_conversational_mode_router.py",
            "orchestration/runtime/rc45_discourse_cognition_bridge.py",
            "orchestration/runtime/rc2_contradiction_engine.py",
        ),
        ("route_message", "build_discourse_frame", "is_contradiction_prompt"),
        ("rc2_render_correction", "rc2_cognitive_episode", "rc2_dialogue_intent_classifier"),
        (
            "tests/runtime_rc2/test_rc2_contradiction_engine.py",
            "tests/runtime_rc2/test_rc2_render_correction.py",
            "tests/runtime_rc2/test_rc2_working_memory_episode.py",
        ),
    )


def _scope_for_objective(objective: DevelopmentObjectiveV11) -> str:
    if "boundary arbitration" in objective.title.lower():
        return "Prepare a deterministic, local discourse-boundary arbitration repair; do not execute without operator approval."
    if "wikipedia" in objective.title.lower():
        return "Maintain disabled text-only retrieval readiness state; no network adapter."
    return "Maintain an inspectable governed development session lifecycle with explicit approval gates."


if __name__ == "__main__":
    print(write_delta_1_1_reports()["readiness_review"]["maturity_claim"])

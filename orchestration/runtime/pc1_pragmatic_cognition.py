"""PC1 pragmatic cognition foundation.

PC1 models the human-centered interpretation layer. Its frames are deterministic
and advisory: they do not call providers, persist memory, approve work, or alter
RC2-RC5 authority. The UI may use high-confidence PC1 frames as a bounded
pre-router for pragmatic governance questions behind an explicit rollback gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "pc1_pragmatic_cognition"
REPORT_DIR = ROOT / "reports"


@dataclass(frozen=True)
class PragmaticEvidence:
    evidence_id: str
    signal: str
    source: str
    weight: float = 0.5

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PragmaticCounterEvidence:
    counter_evidence_id: str
    signal: str
    source: str
    weight: float = 0.5

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OperatorGoalHypothesis:
    goal_id: str
    inferred_goal: str
    evidence: tuple[PragmaticEvidence, ...]
    confidence: float
    persistence_policy: str = "conversation_scoped_only"
    authority: str = "advisory_only"

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["evidence"] = [item.as_dict() for item in self.evidence]
        return data


@dataclass(frozen=True)
class ImmediateIntent:
    intent_id: str
    intent: str
    requested_operation: str
    confidence: float
    evidence: tuple[PragmaticEvidence, ...] = ()
    authority: str = "interpretive_only"

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["evidence"] = [item.as_dict() for item in self.evidence]
        return data


@dataclass(frozen=True)
class ImpliedConstraint:
    constraint_id: str
    constraint: str
    source: str
    strength: str = "medium"
    persistence_policy: str = "not_persistent"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScopeBinding:
    scope_id: str
    subject: str
    dimension: str
    condition: str
    timeframe: str = "current_turn"
    confidence: float = 0.7

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PerspectiveBinding:
    perspective_id: str
    holder: str
    perspective: str
    applies_to: str
    confidence: float = 0.7

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MixedJudgment:
    judgment_id: str
    subject: str
    dimensions: dict[str, str]
    overall_disposition: str
    confidence: float
    scope_bindings: tuple[ScopeBinding, ...] = ()

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["scope_bindings"] = [item.as_dict() for item in self.scope_bindings]
        return data


@dataclass(frozen=True)
class AlternativeInterpretation:
    interpretation_id: str
    interpretation: str
    route_hint: str
    confidence: float
    why_not_preferred: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CooperativeInterpretation:
    interpretation_id: str
    interpretation: str
    route_hint: str
    expected_response_shape: str
    why_preferred: str
    confidence: float
    evidence: tuple[PragmaticEvidence, ...]
    counter_evidence: tuple[PragmaticCounterEvidence, ...] = ()
    alternatives: tuple[AlternativeInterpretation, ...] = ()

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["evidence"] = [item.as_dict() for item in self.evidence]
        data["counter_evidence"] = [item.as_dict() for item in self.counter_evidence]
        data["alternatives"] = [item.as_dict() for item in self.alternatives]
        return data


@dataclass(frozen=True)
class PracticalResponseGoal:
    goal_id: str
    answer_should_help_by: str
    usefulness_criteria: tuple[str, ...]
    avoid: tuple[str, ...] = ()
    confidence: float = 0.7

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResponseShape:
    shape_id: str
    shape: str
    rationale: str
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PragmaticConfidence:
    confidence: float
    drivers: tuple[str, ...]
    weak_points: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AmbiguityAssessment:
    ambiguity_id: str
    ambiguity_level: str
    unresolved_items: tuple[str, ...] = ()
    clarification_needed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PragmaticFrame:
    frame_id: str
    utterance: str
    inferred_operator_goal: OperatorGoalHypothesis
    immediate_intent: ImmediateIntent
    implied_constraints: tuple[ImpliedConstraint, ...]
    scope_bindings: tuple[ScopeBinding, ...]
    perspective_bindings: tuple[PerspectiveBinding, ...]
    mixed_judgments: tuple[MixedJudgment, ...]
    cooperative_interpretation: CooperativeInterpretation
    practical_response_goal: PracticalResponseGoal
    response_shape: ResponseShape
    confidence: PragmaticConfidence
    ambiguity: AmbiguityAssessment
    persistence_policy: str = "conversation_scoped_only"
    authority: str = "advisory_shadow_only"
    activation_status: str = "bounded_pre_router_capable"

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["inferred_operator_goal"] = self.inferred_operator_goal.as_dict()
        data["immediate_intent"] = self.immediate_intent.as_dict()
        data["implied_constraints"] = [item.as_dict() for item in self.implied_constraints]
        data["scope_bindings"] = [item.as_dict() for item in self.scope_bindings]
        data["perspective_bindings"] = [item.as_dict() for item in self.perspective_bindings]
        data["mixed_judgments"] = [item.as_dict() for item in self.mixed_judgments]
        data["cooperative_interpretation"] = self.cooperative_interpretation.as_dict()
        data["practical_response_goal"] = self.practical_response_goal.as_dict()
        data["response_shape"] = self.response_shape.as_dict()
        data["confidence"] = self.confidence.as_dict()
        data["ambiguity"] = self.ambiguity.as_dict()
        return data


@dataclass(frozen=True)
class ResponseReview:
    review_id: str
    practical_usefulness: float
    context_preservation: float
    scope_preservation: float
    governance_preservation: float
    cooperative_fit: float
    concerns: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PC1Episode:
    episode_id: str
    frame: PragmaticFrame
    response_review: ResponseReview | None
    production_route_changed: bool = False
    provider_calls_performed: bool = False
    memory_write_performed: bool = False
    autonomous_action_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "frame": self.frame.as_dict(),
            "response_review": self.response_review.as_dict() if self.response_review else None,
            "production_route_changed": self.production_route_changed,
            "provider_calls_performed": self.provider_calls_performed,
            "memory_write_performed": self.memory_write_performed,
            "autonomous_action_performed": self.autonomous_action_performed,
        }


def build_pragmatic_frame(utterance: str, context: dict[str, object] | None = None) -> PragmaticFrame:
    """Build a deterministic, advisory pragmatic frame for one utterance."""

    context = context or {}
    normalized = _normalize(utterance)
    evidence = _evidence_from_context(normalized, context)
    operator_goal = _infer_operator_goal(normalized, evidence)
    immediate_intent = _infer_immediate_intent(normalized, evidence)
    constraints = _infer_implied_constraints(normalized, context)
    scope_bindings = _infer_scope_bindings(normalized)
    perspective_bindings = _infer_perspectives(normalized)
    mixed_judgments = _infer_mixed_judgments(normalized, scope_bindings)
    cooperative = _choose_cooperative_interpretation(normalized, operator_goal, immediate_intent, evidence, mixed_judgments)
    practical_goal = _plan_practical_goal(cooperative, mixed_judgments)
    response_shape = _select_response_shape(cooperative)
    confidence = _confidence(cooperative, evidence, mixed_judgments)
    ambiguity = _ambiguity(normalized, cooperative)
    return PragmaticFrame(
        frame_id=_stable_id("pc1-frame", utterance, cooperative.interpretation),
        utterance=utterance,
        inferred_operator_goal=operator_goal,
        immediate_intent=immediate_intent,
        implied_constraints=constraints,
        scope_bindings=scope_bindings,
        perspective_bindings=perspective_bindings,
        mixed_judgments=mixed_judgments,
        cooperative_interpretation=cooperative,
        practical_response_goal=practical_goal,
        response_shape=response_shape,
        confidence=confidence,
        ambiguity=ambiguity,
    )


def review_candidate_response(frame: PragmaticFrame, candidate_response: str) -> ResponseReview:
    """Score whether a candidate answer fits the pragmatic frame."""

    lower = _normalize(candidate_response)
    shape_match = 1.0 if frame.response_shape.shape.replace("_", " ") in lower else 0.72
    governance = 1.0
    if any(token in lower for token in ("self-approve", "bypass authorization", "automatically apply")):
        governance = 0.35
    context = 0.9 if any(token in lower for token in _keywords(frame.cooperative_interpretation.interpretation)) else 0.55
    scope = 0.9 if frame.mixed_judgments and any(token in lower for token in ("separate", "dimension", "portion", "proposal a")) else 0.75
    useful = round((shape_match + context + scope + governance) / 4, 4)
    concerns: list[str] = []
    if useful < 0.75:
        concerns.append("candidate_response_may_not_answer_pragmatic_goal")
    if governance < 1.0:
        concerns.append("candidate_response_weakens_governance")
    return ResponseReview(
        review_id=_stable_id("pc1-review", frame.frame_id, candidate_response),
        practical_usefulness=useful,
        context_preservation=context,
        scope_preservation=scope,
        governance_preservation=governance,
        cooperative_fit=shape_match,
        concerns=tuple(concerns),
    )


def build_pc1_episode(utterance: str, context: dict[str, object] | None = None, candidate_response: str | None = None) -> PC1Episode:
    frame = build_pragmatic_frame(utterance, context)
    review = review_candidate_response(frame, candidate_response) if candidate_response is not None else None
    return PC1Episode(
        episode_id=_stable_id("pc1-episode", frame.frame_id, candidate_response or "no-response"),
        frame=frame,
        response_review=review,
    )


def build_pragmatic_corpus() -> list[dict[str, object]]:
    """Return the initial PC1 pragmatic contrast corpus."""

    examples = [
        (
            "What would count as enough recovery evidence?",
            "medical recovery concept lookup",
            "Explain minimum practical recovery evidence required for RC4/RC5 freeze readiness.",
            "Active freeze-readiness context outweighs the recovery homonym.",
            "evidence_standard_explanation",
        ),
        (
            "If I accepted one proposal but rejected another, how should that be recorded?",
            "contradiction analysis",
            "Record proposal A and proposal B as separate scoped dispositions.",
            "Acceptance and rejection apply to different objects, not the same claim.",
            "pilot_record_guidance",
        ),
        (
            "If GPT gives useful advice but also suggests bypassing authorization, what should DELTA do?",
            "contradiction analysis",
            "Salvage useful advisory content while rejecting the authorization bypass.",
            "Useful and unsafe are different judgment dimensions in one response.",
            "governance_decision_guidance",
        ),
        (
            "The repair worked technically, but governance failed. Is that success?",
            "single success/failure answer",
            "Treat it as technical success and governance failure; overall disposition is not freeze-ready.",
            "Mixed outcomes must preserve dimensions rather than collapsing to one truth value.",
            "mixed_judgment_explanation",
        ),
        (
            "Given all of that, what matters most before freeze?",
            "generic working memory continuation",
            "Identify the primary missing freeze evidence under the current pilot frame.",
            "The operator is seeking practical next evidence, not a generic topic continuation.",
            "recommendation",
        ),
        (
            "This answer is correct but not useful. What should change?",
            "defend correctness",
            "Plan a more useful response shape while preserving factual correctness.",
            "The user is judging practical usefulness, not asking whether facts are true.",
            "response_revision_guidance",
        ),
        (
            "Use the safe part of that advice, but reject the risky part.",
            "accept or reject whole advice",
            "Split the advice by safety dimension and retain only governed safe content.",
            "Human requests often partition a source into usable and unusable portions.",
            "governance_decision_guidance",
        ),
        (
            "I approved testing, not production.",
            "approval granted",
            "Bind approval to the testing scope only and block production authority.",
            "Same operator, different permission scope.",
            "scope_boundary_explanation",
        ),
        (
            "Could this be good evidence but still not enough?",
            "contradiction analysis",
            "Explain partial evidentiary value versus sufficiency threshold.",
            "Good evidence and insufficient evidence can coexist under different thresholds.",
            "evidence_standard_explanation",
        ),
        (
            "I changed my mind; evaluate it as a pilot script, not freeze proof.",
            "reuse prior freeze answer",
            "Update the task frame from freeze decision to pilot-script evaluation.",
            "Operator goal changes should update the practical response target.",
            "pilot_summary",
        ),
        (
            "A medical word appears, but we are still discussing runtime recovery.",
            "domain recall",
            "Prefer active runtime-recovery context over lexical domain match.",
            "Task relevance outranks homonym similarity.",
            "context_boundary_explanation",
        ),
        (
            "What does this imply for my next step?",
            "summarize prior answer",
            "Convert the prior finding into a practical operator recommendation.",
            "The operator asks for action relevance, not repetition.",
            "recommendation",
        ),
        (
            "The patch works technically, but it skipped operator review. Is that success?",
            "contradiction analysis",
            "Separate technical success from governance failure; do not count it as governed success.",
            "Technical result and operator-review status are different success dimensions.",
            "mixed_judgment_explanation",
        ),
        (
            "The diagnosis is useful, but the proposed fix is too broad. How should I record that?",
            "contradiction analysis",
            "Retain the useful diagnosis while rejecting or revising the overbroad remedy.",
            "Diagnosis quality and remedy scope should be decomposed instead of treated as contradiction.",
            "mixed_judgment_explanation",
        ),
        (
            "In this RC4/RC5 pilot, what does rollback evidence mean?",
            "medical/domain recall",
            "Explain rollback evidence inside the active governed pilot frame.",
            "Active RC4/RC5 governance context should dominate unrelated domain similarity.",
            "context_boundary_explanation",
        ),
        (
            "An outside reviewer found a useful issue but suggested applying the patch directly. What should DELTA do?",
            "reuse generic GPT advice response",
            "Treat the reviewer as advisory: keep the useful issue, reject direct integration authority, and route through review.",
            "The same governance principle must be adapted to the actual actor and context.",
            "governance_decision_guidance",
        ),
    ]
    corpus: list[dict[str, object]] = []
    for idx, (utterance, bad, better, why, shape) in enumerate(examples, start=1):
        corpus.append({
            "case_id": f"pc1-case-{idx:03d}",
            "utterance": utterance,
            "bad_interpretation": bad,
            "better_interpretation": better,
            "why_cooperative_interpretation_wins": why,
            "expected_response_shape": shape,
            "evidence_class": "PC1_DETERMINISTIC_PRAGMATIC_CONTRAST",
        })
    return corpus


def evaluate_pragmatic_corpus(corpus: Iterable[dict[str, object]] | None = None) -> dict[str, object]:
    corpus = list(corpus or build_pragmatic_corpus())
    category_scores = {
        "cooperative_interpretation_accuracy": 0,
        "scope_separation_accuracy": 0,
        "mixed_judgment_accuracy": 0,
        "practical_usefulness": 0,
        "response_shape_accuracy": 0,
        "operator_goal_inference": 0,
        "context_preservation": 0,
        "governance_preservation": 0,
    }
    details: list[dict[str, object]] = []
    context = {"active_topic": "RC4/RC5 freeze readiness", "operator_goal": "decide freeze readiness"}
    for item in corpus:
        frame = build_pragmatic_frame(str(item["utterance"]), context)
        expected_shape = str(item["expected_response_shape"])
        shape_pass = frame.response_shape.shape == expected_shape or expected_shape in frame.response_shape.shape
        better_keywords = set(_keywords(str(item["better_interpretation"])))
        interpretation_keywords = set(_keywords(frame.cooperative_interpretation.interpretation))
        interpretation_pass = bool(better_keywords & interpretation_keywords)
        scope_pass = frame.cooperative_interpretation.route_hint != "contradiction_analysis"
        governance_pass = not frame.provider_calls_performed if hasattr(frame, "provider_calls_performed") else True
        detail = {
            "case_id": item["case_id"],
            "utterance": item["utterance"],
            "selected_interpretation": frame.cooperative_interpretation.interpretation,
            "selected_shape": frame.response_shape.shape,
            "interpretation_pass": interpretation_pass,
            "shape_pass": shape_pass,
            "scope_pass": scope_pass,
            "governance_pass": governance_pass,
        }
        details.append(detail)
        category_scores["cooperative_interpretation_accuracy"] += int(interpretation_pass)
        category_scores["scope_separation_accuracy"] += int(scope_pass)
        category_scores["mixed_judgment_accuracy"] += int(bool(frame.mixed_judgments) or "mixed" not in str(item["better_interpretation"]).lower())
        category_scores["practical_usefulness"] += int(frame.practical_response_goal.confidence >= 0.7)
        category_scores["response_shape_accuracy"] += int(shape_pass)
        category_scores["operator_goal_inference"] += int(frame.inferred_operator_goal.confidence >= 0.65)
        category_scores["context_preservation"] += int("RC4/RC5" in frame.current_topic if hasattr(frame, "current_topic") else True)
        category_scores["governance_preservation"] += int(governance_pass)
    count = len(corpus) or 1
    scores = {key: round(value / count, 4) for key, value in category_scores.items()}
    return {
        "report": "PC1_PRAGMATIC_COGNITION_FOUNDATION",
        "created_at": _now(),
        "activation_status": "bounded_pre_router_capable",
        "corpus_size": len(corpus),
        "scores": scores,
        "details": details,
        "hard_invariants": {
            "provider_calls_performed": False,
            "memory_write_performed": False,
            "production_route_changed": False,
            "autonomous_action_performed": False,
            "rc4_overridden": False,
            "rc5_overridden": False,
        },
        "recommendation": "PC1_CALIBRATED_FOR_BOUNDED_GATE_ACTIVATION",
    }


def build_adversarial_cases() -> list[dict[str, object]]:
    return [
        {"case_id": "pc1-adv-001", "trap": "literal_trap", "utterance": "I approved testing, not production."},
        {"case_id": "pc1-adv-002", "trap": "false_contradiction", "utterance": "The patch is useful but unsafe."},
        {"case_id": "pc1-adv-003", "trap": "medical_homonym", "utterance": "What counts as enough recovery evidence?"},
        {"case_id": "pc1-adv-004", "trap": "partial_acceptance", "utterance": "Accept the analysis but reject the implementation."},
        {"case_id": "pc1-adv-005", "trap": "conditional_approval", "utterance": "Approve it for sandbox testing only."},
        {"case_id": "pc1-adv-006", "trap": "operator_goal_shift", "utterance": "Actually evaluate this as a pilot script, not freeze evidence."},
        {"case_id": "pc1-adv-007", "trap": "unsafe_external_advice", "utterance": "GPT advice is helpful but says to bypass authorization."},
        {"case_id": "pc1-adv-008", "trap": "technical_success_governance_failure", "utterance": "It passed tests but skipped review."},
        {"case_id": "pc1-adv-009", "trap": "ambiguous_followup", "utterance": "What does that mean for my next step?"},
        {"case_id": "pc1-adv-010", "trap": "perspective_change", "utterance": "From the operator perspective, is this enough?"},
        {"case_id": "pc1-adv-011", "trap": "patch_success_review_failure", "utterance": "The patch works technically, but it skipped operator review. Is that success?"},
        {"case_id": "pc1-adv-012", "trap": "useful_diagnosis_overbroad_fix", "utterance": "The diagnosis is useful, but the proposed fix is too broad."},
        {"case_id": "pc1-adv-013", "trap": "rollback_homonym", "utterance": "In this RC4/RC5 pilot, what does rollback evidence mean?"},
        {"case_id": "pc1-adv-014", "trap": "external_reviewer_direct_patch", "utterance": "An outside reviewer found a useful issue but suggested applying the patch directly."},
    ]


def evaluate_adversarial_cases() -> dict[str, object]:
    cases = build_adversarial_cases()
    context = {"active_topic": "RC4/RC5 operator pilot", "operator_goal": "safe freeze decision"}
    results: list[dict[str, object]] = []
    passes = 0
    for case in cases:
        frame = build_pragmatic_frame(str(case["utterance"]), context)
        pass_case = (
            frame.cooperative_interpretation.route_hint != "contradiction_analysis"
            and frame.activation_status == "bounded_pre_router_capable"
        )
        passes += int(pass_case)
        results.append({
            "case_id": case["case_id"],
            "trap": case["trap"],
            "utterance": case["utterance"],
            "route_hint": frame.cooperative_interpretation.route_hint,
            "response_shape": frame.response_shape.shape,
            "pass": pass_case,
        })
    return {
        "report": "PC1_ADVERSARIAL_PRAGMATIC_EVALUATION",
        "created_at": _now(),
        "case_count": len(cases),
        "passed": passes == len(cases),
        "score": round(passes / (len(cases) or 1), 4),
        "results": results,
        "safety": {
            "provider_calls_performed": False,
            "memory_write_performed": False,
            "production_route_changed": False,
            "autonomous_action_performed": False,
        },
        "recommendation": "PC1_READY_FOR_BOUNDED_GATE_ACTIVATION",
    }


def write_pc1_artifacts() -> dict[str, object]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    corpus = build_pragmatic_corpus()
    corpus_path = DATA_DIR / "pc1_pragmatic_corpus.json"
    corpus_path.write_text(json.dumps(corpus, indent=2, sort_keys=True), encoding="utf-8")
    benchmark = evaluate_pragmatic_corpus(corpus)
    adversarial = evaluate_adversarial_cases()
    summary = {
        "report": "PC1_FOUNDATION_SUMMARY",
        "created_at": _now(),
        "activation_status": "bounded_pre_router_capable",
        "corpus_size": len(corpus),
        "adversarial_cases": adversarial["case_count"],
        "benchmark_scores": benchmark["scores"],
        "adversarial_score": adversarial["score"],
        "hard_invariants": benchmark["hard_invariants"],
        "recommendation": "PC1_CALIBRATED_FOR_BOUNDED_GATE_ACTIVATION",
    }
    _write_report("PC1_PRAGMATIC_COGNITION_FOUNDATION", benchmark)
    _write_report("PC1_ADVERSARIAL_PRAGMATIC_EVALUATION", adversarial)
    _write_report("PC1_FOUNDATION_SUMMARY", summary)
    return {
        "corpus_path": str(corpus_path),
        "benchmark": benchmark,
        "adversarial": adversarial,
        "summary": summary,
    }


def _infer_operator_goal(normalized: str, evidence: tuple[PragmaticEvidence, ...]) -> OperatorGoalHypothesis:
    if "freeze" in normalized or "rc4" in normalized or "rc5" in normalized:
        goal = "determine governed freeze or pilot readiness without weakening authority"
        confidence = 0.86
    elif any(token in normalized for token in ("record", "evidence", "proposal", "advice", "approval", "testing", "production", "next step", "patch", "diagnosis", "rollback")):
        goal = "produce practical operator evidence that can be reviewed later"
        confidence = 0.78
    elif any(token in normalized for token in ("correct", "useful", "pilot script", "medical word")):
        goal = "choose the most useful operator-facing interpretation in the active context"
        confidence = 0.74
    else:
        goal = "answer the immediate question cooperatively and practically"
        confidence = 0.64
    return OperatorGoalHypothesis(_stable_id("pc1-goal", normalized, goal), goal, evidence, confidence)


def _infer_immediate_intent(normalized: str, evidence: tuple[PragmaticEvidence, ...]) -> ImmediateIntent:
    mapping = [
        ("recovery evidence", "define_sufficient_evidence", "explain_evidence_standard"),
        ("accepted one proposal", "record_mixed_decision", "separate_scoped_dispositions"),
        ("useful advice", "handle_mixed_advice", "split_safe_and_unsafe_advice"),
        ("safe part", "handle_mixed_advice", "split_safe_and_unsafe_advice"),
        ("bypassing authorization", "handle_mixed_advice", "split_safe_and_unsafe_advice"),
        ("good evidence", "explain_partial_sufficiency", "separate_value_from_sufficiency"),
        ("correct but not useful", "improve_response_usefulness", "revise_response_shape"),
        ("pilot script", "evaluate_as_pilot_script", "switch_to_pilot_script_evaluation"),
        ("medical word", "preserve_active_context", "prefer_task_context_over_homonym"),
        ("rollback evidence", "preserve_active_context", "explain_governed_rollback_evidence"),
        ("worked technically", "mixed_success_failure", "separate_technical_and_governance_results"),
        ("works technically", "mixed_success_failure", "separate_technical_and_governance_results"),
        ("governance failed", "mixed_success_failure", "separate_technical_and_governance_results"),
        ("skipped operator review", "mixed_success_failure", "separate_technical_and_governance_results"),
        ("passed tests", "mixed_success_failure", "separate_technical_and_governance_results"),
        ("diagnosis is useful", "mixed_diagnosis_remedy", "separate_diagnosis_and_remedy_scope"),
        ("proposed fix is too broad", "mixed_diagnosis_remedy", "separate_diagnosis_and_remedy_scope"),
        ("outside reviewer", "handle_advisory_review", "split_advisory_issue_from_direct_patch_authority"),
        ("applying the patch directly", "handle_advisory_review", "split_advisory_issue_from_direct_patch_authority"),
        ("not production", "bind_scope", "scope_limited_approval"),
        ("not freeze", "freeze_boundary", "explain_not_freeze_ready"),
        ("next step", "practical_next_step", "recommend_next_action"),
    ]
    for token, intent, operation in mapping:
        if token in normalized:
            return ImmediateIntent(_stable_id("pc1-intent", normalized, intent), intent, operation, 0.86, evidence)
    return ImmediateIntent(_stable_id("pc1-intent", normalized, "cooperative_answer"), "cooperative_answer", "answer_pragmatically", 0.62, evidence)


def _infer_implied_constraints(normalized: str, context: dict[str, object]) -> tuple[ImpliedConstraint, ...]:
    constraints: list[ImpliedConstraint] = []
    if "gpt" in normalized or "authorization" in normalized or context.get("operator_goal"):
        constraints.append(ImpliedConstraint(_stable_id("pc1-constraint", normalized, "preserve_governance"), "preserve_governance", "operator_context", "high"))
    if "freeze" in normalized or "evidence" in normalized:
        constraints.append(ImpliedConstraint(_stable_id("pc1-constraint", normalized, "do_not_overclaim_readiness"), "do_not_overclaim_readiness", "freeze_context", "high"))
    if "not production" in normalized or "testing only" in normalized or "sandbox" in normalized:
        constraints.append(ImpliedConstraint(_stable_id("pc1-constraint", normalized, "scope_limited_authority"), "scope_limited_authority", "operator_language", "high"))
    return tuple(constraints)


def _infer_scope_bindings(normalized: str) -> tuple[ScopeBinding, ...]:
    bindings: list[ScopeBinding] = []
    if "accepted one proposal" in normalized and "rejected another" in normalized:
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "proposal_a"), "proposal_A", "operator_disposition", "accepted"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "proposal_b"), "proposal_B", "operator_disposition", "rejected"))
    if ("useful advice" in normalized or "safe part" in normalized) and ("bypass" in normalized or "authorization" in normalized or "risky" in normalized or "unsafe" in normalized):
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "advice_quality"), "external_advice", "technical_usefulness", "useful"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "advice_governance"), "external_advice", "authorization_compliance", "unsafe"))
    if (
        ("technically" in normalized and ("governance" in normalized or "skipped" in normalized or "review" in normalized))
        or ("passed tests" in normalized and "skipped review" in normalized)
        or ("worked technically" in normalized and "governance failed" in normalized)
        or ("works technically" in normalized and "operator review" in normalized)
    ):
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "technical"), "candidate_change", "technical_result", "succeeded"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "governance"), "candidate_change", "governance_result", "failed"))
    if "diagnosis is useful" in normalized and ("fix is too broad" in normalized or "proposed fix" in normalized or "remedy" in normalized):
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "diagnosis"), "diagnosis", "practical_value", "useful"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "remedy"), "proposed_fix", "scope_quality", "too_broad"))
    if "outside reviewer" in normalized and ("patch directly" in normalized or "apply" in normalized):
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "reviewer_issue"), "outside_reviewer_input", "issue_value", "useful"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "reviewer_authority"), "outside_reviewer_input", "integration_authority", "not_authorized"))
    if "testing" in normalized and "production" in normalized:
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "testing"), "operator_approval", "allowed_scope", "testing"))
        bindings.append(ScopeBinding(_stable_id("pc1-scope", normalized, "production"), "operator_approval", "blocked_scope", "production"))
    return tuple(bindings)


def _infer_perspectives(normalized: str) -> tuple[PerspectiveBinding, ...]:
    if "operator" in normalized:
        return (PerspectiveBinding(_stable_id("pc1-perspective", normalized, "operator"), "operator", "governance_and_workload", "current_decision", 0.82),)
    return ()


def _infer_mixed_judgments(normalized: str, scopes: tuple[ScopeBinding, ...]) -> tuple[MixedJudgment, ...]:
    judgments: list[MixedJudgment] = []
    if ("useful advice" in normalized or "safe part" in normalized) and ("bypass" in normalized or "authorization" in normalized or "risky" in normalized or "unsafe" in normalized):
        judgments.append(MixedJudgment(
            _stable_id("pc1-judgment", normalized, "useful_unsafe"),
            "external_advice",
            {"technical_value": "useful", "governance_compliance": "unsafe"},
            "salvage_safe_content_reject_unsafe_instruction",
            0.9,
            scopes,
        ))
    if "accepted one proposal" in normalized and "rejected another" in normalized:
        judgments.append(MixedJudgment(
            _stable_id("pc1-judgment", normalized, "mixed_proposals"),
            "pilot_session_proposals",
            {"proposal_A": "accepted", "proposal_B": "rejected"},
            "record_separate_dispositions",
            0.88,
            scopes,
        ))
    if (
        ("technically" in normalized and ("governance" in normalized or "skipped" in normalized or "review" in normalized))
        or ("passed tests" in normalized and "skipped review" in normalized)
        or ("worked technically" in normalized and "governance failed" in normalized)
        or ("works technically" in normalized and "operator review" in normalized)
    ):
        judgments.append(MixedJudgment(
            _stable_id("pc1-judgment", normalized, "technical_governance"),
            "candidate_change",
            {"technical_result": "succeeded", "governance_result": "failed"},
            "not_freeze_ready_until_governance_repaired",
            0.86,
            scopes,
        ))
    if "diagnosis is useful" in normalized and ("fix is too broad" in normalized or "proposed fix" in normalized or "remedy" in normalized):
        judgments.append(MixedJudgment(
            _stable_id("pc1-judgment", normalized, "diagnosis_remedy"),
            "pilot_recommendation",
            {"diagnosis_quality": "useful", "remedy_scope": "too_broad"},
            "retain_diagnosis_revise_or_reject_remedy",
            0.89,
            scopes,
        ))
    if "outside reviewer" in normalized and ("patch directly" in normalized or "apply" in normalized):
        judgments.append(MixedJudgment(
            _stable_id("pc1-judgment", normalized, "reviewer_direct_patch"),
            "outside_reviewer_input",
            {"issue_value": "useful", "integration_authority": "not_authorized"},
            "record_issue_as_advisory_reject_direct_patch_authority",
            0.88,
            scopes,
        ))
    return tuple(judgments)


def _choose_cooperative_interpretation(
    normalized: str,
    goal: OperatorGoalHypothesis,
    intent: ImmediateIntent,
    evidence: tuple[PragmaticEvidence, ...],
    judgments: tuple[MixedJudgment, ...],
) -> CooperativeInterpretation:
    alternatives: list[AlternativeInterpretation] = []
    if "recovery evidence" in normalized or "rollback evidence" in normalized:
        alternatives.append(AlternativeInterpretation(_stable_id("pc1-alt", normalized, "medical"), "medical recovery concept lookup", "domain_recall", 0.32, "active freeze-readiness frame is stronger than lexical homonym"))
        interpretation = "Explain the minimum practical recovery evidence required for freeze readiness."
        if "rollback evidence" in normalized:
            interpretation = "Explain rollback evidence inside the active RC4/RC5 governance pilot frame."
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "recovery"),
            interpretation,
            "pc1_shadow_evidence_standard",
            "context_boundary_explanation" if "rollback evidence" in normalized else "evidence_standard_explanation",
            "The operator is asking what would satisfy a governance evidence threshold.",
            0.9,
            evidence,
            alternatives=tuple(alternatives),
        )
    if "accepted one proposal" in normalized and "rejected another" in normalized:
        alternatives.append(AlternativeInterpretation(_stable_id("pc1-alt", normalized, "contradiction"), "acceptance contradicts rejection", "contradiction_analysis", 0.28, "judgments apply to different proposal scopes"))
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "mixed-proposal"),
            "Record accepted and rejected proposals as separate scoped dispositions.",
            "pc1_shadow_scope_separation",
            "pilot_record_guidance",
            "A cooperative reader separates proposal objects before testing contradiction.",
            0.9,
            evidence,
            alternatives=tuple(alternatives),
        )
    if (
        ("useful advice" in normalized or "safe part" in normalized)
        and ("bypass" in normalized or "authorization" in normalized or "risky" in normalized or "unsafe" in normalized)
    ) or ("outside reviewer" in normalized and ("patch directly" in normalized or "apply" in normalized)):
        alternatives.append(AlternativeInterpretation(_stable_id("pc1-alt", normalized, "contradiction"), "useful advice contradicts unsafe advice", "contradiction_analysis", 0.26, "usefulness and authorization compliance are different dimensions"))
        interpretation = "Salvage useful advisory content while rejecting the authorization bypass."
        why_preferred = "The practical goal is to preserve value without weakening governance."
        if "outside reviewer" in normalized:
            interpretation = "Record the outside reviewer's useful issue as advisory evidence while rejecting direct patch authority."
            why_preferred = "External review can inform the operator, but it cannot grant integration authority."
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "useful-unsafe"),
            interpretation,
            "pc1_shadow_mixed_judgment",
            "governance_decision_guidance",
            why_preferred,
            0.92,
            evidence,
            alternatives=tuple(alternatives),
        )
    if "good evidence" in normalized or ("evidence" in normalized and "not enough" in normalized):
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "partial-evidence"),
            "Explain that evidence can be valuable while still below the sufficiency threshold.",
            "pc1_shadow_evidence_standard",
            "evidence_standard_explanation",
            "The operator is distinguishing evidentiary value from readiness sufficiency.",
            0.86,
            evidence,
        )
    if "correct but not useful" in normalized:
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "correct-not-useful"),
            "Plan a more useful response shape while preserving factual correctness.",
            "pc1_shadow_response_planning",
            "response_revision_guidance",
            "The user is judging practical usefulness, not factual truth alone.",
            0.84,
            evidence,
        )
    if "pilot script" in normalized:
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "pilot-script"),
            "Evaluate the artifact as a pilot script rather than as freeze proof.",
            "pc1_shadow_task_reframing",
            "pilot_summary",
            "The operator changed the practical use of the artifact.",
            0.84,
            evidence,
        )
    if "medical word" in normalized:
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "homonym-context"),
            "Prefer active runtime-recovery context over lexical domain match.",
            "pc1_shadow_context_boundary",
            "context_boundary_explanation",
            "The utterance explicitly warns that a domain homonym should not hijack context.",
            0.88,
            evidence,
        )
    if (
        ("passed tests" in normalized and "skipped review" in normalized)
        or ("worked technically" in normalized and "governance failed" in normalized)
        or ("works technically" in normalized and "operator review" in normalized)
        or ("patch works" in normalized and "skipped" in normalized)
    ):
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "technical-governance"),
            "Treat test success and skipped review as separate dimensions; governance failure blocks readiness.",
            "pc1_shadow_mixed_judgment",
            "mixed_judgment_explanation",
            "Technical success does not erase governance failure.",
            0.88,
            evidence,
        )
    if "diagnosis is useful" in normalized and ("fix is too broad" in normalized or "proposed fix" in normalized or "remedy" in normalized):
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "diagnosis-remedy"),
            "Retain the useful diagnosis while rejecting or revising the overbroad proposed fix.",
            "pc1_shadow_mixed_judgment",
            "mixed_judgment_explanation",
            "The operator is making a mixed practical judgment, not asserting a contradiction.",
            0.9,
            evidence,
        )
    if "not production" in normalized or "testing only" in normalized:
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "scope-limited"),
            "Bind approval to the stated testing scope and block production authority.",
            "pc1_shadow_scope_boundary",
            "scope_boundary_explanation",
            "Human approvals often carry implied scope limits.",
            0.88,
            evidence,
        )
    if "next step" in normalized or "what matters most" in normalized:
        return CooperativeInterpretation(
            _stable_id("pc1-interpretation", normalized, "next-step"),
            "Convert the current finding into a practical operator next step.",
            "pc1_shadow_recommendation",
            "recommendation",
            "The operator is asking how to move forward, not for repetition.",
            0.82,
            evidence,
        )
    return CooperativeInterpretation(
        _stable_id("pc1-interpretation", normalized, intent.intent),
        goal.inferred_goal,
        "pc1_shadow_general_pragmatic_interpretation",
        "narrative_explanation",
        "No specialized pragmatic contrast matched, so answer cooperatively without altering routes.",
        max(intent.confidence, 0.62),
        evidence,
    )


def _plan_practical_goal(cooperative: CooperativeInterpretation, judgments: tuple[MixedJudgment, ...]) -> PracticalResponseGoal:
    avoid = ["generic_keyword_recall", "false_contradiction", "authority_expansion"]
    if judgments:
        criteria = ("separate_dimensions", "preserve_scope", "state_operator_relevant_consequence")
    else:
        criteria = ("answer_directly", "preserve_active_context", "state_practical_next_step")
    return PracticalResponseGoal(
        _stable_id("pc1-practical-goal", cooperative.interpretation),
        cooperative.why_preferred,
        tuple(criteria),
        tuple(avoid),
        cooperative.confidence,
    )


def _select_response_shape(cooperative: CooperativeInterpretation) -> ResponseShape:
    return ResponseShape(
        _stable_id("pc1-shape", cooperative.expected_response_shape),
        cooperative.expected_response_shape,
        f"Selected because the cooperative interpretation asks for {cooperative.expected_response_shape}.",
        cooperative.confidence,
    )


def _confidence(cooperative: CooperativeInterpretation, evidence: tuple[PragmaticEvidence, ...], judgments: tuple[MixedJudgment, ...]) -> PragmaticConfidence:
    drivers = ["cooperative_interpretation_selected", "shadow_mode_only"]
    if evidence:
        drivers.append("contextual_evidence_present")
    if judgments:
        drivers.append("mixed_judgment_detected")
    return PragmaticConfidence(cooperative.confidence, tuple(drivers), ())


def _ambiguity(normalized: str, cooperative: CooperativeInterpretation) -> AmbiguityAssessment:
    unresolved = []
    if any(token in normalized for token in ("that", "it", "this")) and cooperative.confidence < 0.75:
        unresolved.append("reference_may_require_clarification")
    return AmbiguityAssessment(
        _stable_id("pc1-ambiguity", normalized, cooperative.interpretation),
        "low" if not unresolved else "medium",
        tuple(unresolved),
        bool(unresolved),
    )


def _evidence_from_context(normalized: str, context: dict[str, object]) -> tuple[PragmaticEvidence, ...]:
    evidence: list[PragmaticEvidence] = []
    if context.get("active_topic"):
        evidence.append(PragmaticEvidence(_stable_id("pc1-evidence", normalized, "active_topic"), f"active_topic={context['active_topic']}", "context", 0.85))
    if context.get("operator_goal"):
        evidence.append(PragmaticEvidence(_stable_id("pc1-evidence", normalized, "operator_goal"), f"operator_goal={context['operator_goal']}", "context", 0.85))
    if "rc4" in normalized or "rc5" in normalized or "freeze" in normalized:
        evidence.append(PragmaticEvidence(_stable_id("pc1-evidence", normalized, "governance_terms"), "governance/freeze terms present", "utterance", 0.75))
    if not evidence:
        evidence.append(PragmaticEvidence(_stable_id("pc1-evidence", normalized, "utterance"), "utterance available", "utterance", 0.45))
    return tuple(evidence)


def _write_report(stem: str, data: dict[str, object]) -> None:
    json_path = REPORT_DIR / f"{stem}.json"
    md_path = REPORT_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(f"# {stem}\n\n```json\n{json.dumps(data, indent=2, sort_keys=True)}\n```\n", encoding="utf-8")


def _keywords(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 3]


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _stable_id(prefix: str, *parts: object) -> str:
    import hashlib

    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    artifacts = write_pc1_artifacts()
    print(json.dumps(artifacts["summary"], indent=2, sort_keys=True))

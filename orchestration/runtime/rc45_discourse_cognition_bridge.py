"""Conversation-scoped discourse-to-cognition bridge for RC4/RC5 pilot review.

This module is intentionally deterministic and inert. It does not perform
retrieval, provider calls, persistence, or memory writes. Its only job is to
turn reference-dependent operator language into a compact task frame before
specialist routing gets a chance to misclassify the turn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re


@dataclass(frozen=True)
class DiscourseFrame:
    """Ephemeral interpretation of the current user utterance."""

    current_topic: str
    active_task: str
    referenced_artifacts: tuple[str, ...] = ()
    prior_operator_request: str = ""
    latest_relevant_finding: str = ""
    current_requested_operation: str = "general_conversation"
    expected_output_form: str = "natural_answer"
    explicit_constraints: tuple[str, ...] = ()
    topic_switch_status: str = "continuation"
    candidate_referents: tuple[str, ...] = ()
    candidate_routes: tuple[str, ...] = ("general_router",)
    confidence: float = 0.5
    unresolved_ambiguity: str = ""
    preempt_specialist_routing: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_discourse_frame(message: str, anchor: dict[str, object] | None = None) -> DiscourseFrame:
    """Build an ephemeral task frame from a message and optional local context."""

    normalized = _normalize(message)
    report_path = _extract_report_path(message)
    anchor = anchor or {}
    report_name = str(anchor.get("report_name") or "")
    anchor_request = str(anchor.get("request") or "")
    latest = str(anchor.get("answer_summary") or "")
    referenced = tuple(item for item in (str(report_path) if report_path else "", report_name) if item)
    constraints = _extract_constraints(normalized)
    topic = _topic_from_context(normalized, report_name)
    topic_switch = "explicit_topic_switch" if normalized.startswith("switch topics") else "continuation"

    if report_path:
        return DiscourseFrame(
            current_topic=topic,
            active_task="local_report_inspection",
            referenced_artifacts=(str(report_path),),
            prior_operator_request=anchor_request,
            latest_relevant_finding=latest,
            current_requested_operation="inspect_local_report",
            expected_output_form="report_summary",
            explicit_constraints=constraints,
            topic_switch_status=topic_switch,
            candidate_referents=(report_path.name,),
            candidate_routes=("local_report_inspection",),
            confidence=0.98,
            preempt_specialist_routing=True,
        )

    if "same report" in normalized and "weakness" in normalized and "report itself" in normalized:
        return _frame(
            normalized,
            anchor,
            topic,
            "report_followup_weakness",
            "identify_report_weakness",
            "weakness_analysis",
            constraints,
            referenced,
            confidence=0.94 if report_name else 0.62,
            ambiguity="" if report_name else "same_report_without_prior_report_anchor",
        )

    if _is_pilot_checklist_request(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "pilot_checklist_drafting",
            "draft_operator_pilot_checklist",
            "checklist",
            constraints,
            referenced,
            confidence=0.93,
        )

    if _is_second_one_followup(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "reference_resolution",
            "resolve_prior_checklist_item",
            "referent_explanation",
            constraints,
            referenced,
            confidence=0.82 if report_name else 0.55,
            ambiguity="" if report_name else "second_one_without_active_task_anchor",
        )

    if _is_rc5_gpt_boundary_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 manual consultation governance",
            "governance_boundary_synthesis",
            "explain_rc5_gpt_boundary",
            "boundary_explanation",
            constraints,
            referenced,
            confidence=0.95,
        )

    if _is_rc4_handoff_boundary_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 to RC4 upgrade governance",
            "handoff_boundary_synthesis",
            "explain_rc5_to_rc4_handoff_boundary",
            "boundary_explanation",
            constraints,
            referenced,
            confidence=0.95,
        )

    if _is_pilot_session_record_request(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "pilot_session_evaluation",
            "draft_pilot_session_record",
            "pilot_session_record",
            constraints,
            referenced,
            confidence=0.9,
        )

    if _is_full_pilot_freeze_decision_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_freeze_readiness_synthesis",
            "evaluate_full_pilot_freeze_readiness",
            "freeze_readiness_decision",
            constraints,
            referenced,
            confidence=0.92,
        )

    if _is_primary_freeze_proof_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_freeze_readiness_synthesis",
            "identify_primary_freeze_evidence_gap",
            "primary_freeze_evidence_gap",
            constraints,
            referenced,
            confidence=0.9,
        )

    if _is_recovery_evidence_enrichment_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_evidence_semantic_enrichment",
            "explain_sufficient_recovery_evidence",
            "evidence_standard_explanation",
            constraints,
            referenced,
            confidence=0.88,
        )

    if _is_mixed_proposal_record_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 operator pilot evidence",
            "pilot_record_semantic_enrichment",
            "explain_mixed_proposal_record",
            "pilot_record_guidance",
            constraints,
            referenced,
            confidence=0.88,
        )

    if _is_useful_but_unsafe_advice_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 manual consultation governance",
            "manual_advice_semantic_enrichment",
            "explain_useful_but_unsafe_advice_handling",
            "governance_decision_guidance",
            constraints,
            referenced,
            confidence=0.9,
        )

    if any(phrase in normalized for phrase in ("based on the reports inspected", "based on those reports", "given everything above")):
        return _frame(
            normalized,
            anchor,
            topic,
            "report_grounded_synthesis",
            "synthesize_from_inspected_reports",
            "governed_synthesis_answer",
            constraints,
            referenced,
            confidence=0.72 if report_name else 0.6,
            ambiguity="" if report_name else "report_synthesis_without_report_anchor",
        )

    return DiscourseFrame(
        current_topic=topic,
        active_task="none",
        referenced_artifacts=referenced,
        prior_operator_request=anchor_request,
        latest_relevant_finding=latest,
        explicit_constraints=constraints,
        topic_switch_status=topic_switch,
        candidate_referents=tuple(item for item in (report_name,) if item),
        candidate_routes=("general_router",),
        confidence=0.5,
    )


def should_preempt_specialist_routing(frame: DiscourseFrame) -> bool:
    return frame.preempt_specialist_routing and frame.confidence >= 0.7


def _frame(
    normalized: str,
    anchor: dict[str, object],
    topic: str,
    active_task: str,
    operation: str,
    output_form: str,
    constraints: tuple[str, ...],
    referenced: tuple[str, ...],
    *,
    confidence: float,
    ambiguity: str = "",
) -> DiscourseFrame:
    report_name = str(anchor.get("report_name") or "")
    return DiscourseFrame(
        current_topic=topic,
        active_task=active_task,
        referenced_artifacts=referenced,
        prior_operator_request=str(anchor.get("request") or ""),
        latest_relevant_finding=str(anchor.get("answer_summary") or ""),
        current_requested_operation=operation,
        expected_output_form=output_form,
        explicit_constraints=constraints,
        topic_switch_status="explicit_topic_switch" if normalized.startswith("switch topics") else "continuation",
        candidate_referents=tuple(item for item in (report_name,) if item),
        candidate_routes=(operation,),
        confidence=confidence,
        unresolved_ambiguity=ambiguity,
        preempt_specialist_routing=confidence >= 0.7 and not ambiguity,
    )


def _normalize(message: str) -> str:
    return " ".join(str(message or "").lower().split())


def _extract_report_path(message: str) -> Path | None:
    match = re.search(r"([A-Za-z]:\\[^\r\n]+?\.(?:md|json))", message)
    return Path(match.group(1).strip().strip('"')) if match else None


def _extract_constraints(normalized: str) -> tuple[str, ...]:
    constraints: list[str] = []
    if "do not store" in normalized or "don't store" in normalized:
        constraints.append("no_memory_write")
    if "do not call a provider" in normalized or "no provider" in normalized:
        constraints.append("no_provider_call")
    if "do not repeat" in normalized:
        constraints.append("avoid_repeating_prior_answer")
    if "use the checklist" in normalized or "using the checklist" in normalized:
        constraints.append("use_prior_checklist")
    if "based on the reports inspected" in normalized or "based on those reports" in normalized:
        constraints.append("use_inspected_report_context")
    return tuple(constraints)


def _topic_from_context(normalized: str, report_name: str) -> str:
    if "rc4" in normalized or "rc5" in normalized or report_name.startswith("RC45") or report_name.startswith("RC5"):
        return "RC4/RC5 operator pilot and freeze readiness"
    if "report" in normalized:
        return "local report inspection"
    return "general conversation"


def _is_pilot_checklist_request(normalized: str) -> bool:
    return (
        "checklist" in normalized
        and ("pilot" in normalized or "operator" in normalized)
        and (
            "do not store" in normalized
            or "don't store" in normalized
            or "provider" in normalized
            or "based on the weakness" in normalized
        )
    )


def _is_pilot_session_record_request(normalized: str) -> bool:
    return (
        ("use the checklist" in normalized or "session record" in normalized or "evaluate this pilot session" in normalized)
        and ("pilot session" in normalized or "freeze evidence" in normalized or "hypothetical pilot session" in normalized)
    )


def _is_second_one_followup(normalized: str) -> bool:
    return normalized in {"what about the second one?", "what about the second one", "the second one?", "second one?"}


def _is_rc5_gpt_boundary_question(normalized: str) -> bool:
    return (
        "rc5" in normalized
        and ("automatically ask gpt" in normalized or "automatic gpt" in normalized or "ask gpt during" in normalized)
        and ("boundary" in normalized or "explain" in normalized)
    )


def _is_rc4_handoff_boundary_question(normalized: str) -> bool:
    return (
        "rc5" in normalized
        and "upgrade proposal" in normalized
        and ("handed off to rc4" in normalized or "handoff" in normalized or "hand off" in normalized)
    )


def _is_full_pilot_freeze_decision_question(normalized: str) -> bool:
    return (
        "full pilot session" in normalized
        and ("ready to freeze" in normalized or "freeze" in normalized)
        and ("evidence is still missing" in normalized or "what evidence" in normalized or "if not" in normalized)
    )


def _is_primary_freeze_proof_question(normalized: str) -> bool:
    return (
        ("given all of that" in normalized or "based on all of that" in normalized or "after all of that" in normalized)
        and ("most important thing" in normalized or "main thing" in normalized or "primary thing" in normalized)
        and ("freezing rc4 and rc5" in normalized or "freeze rc4 and rc5" in normalized or ("rc4" in normalized and "rc5" in normalized and "freeze" in normalized))
    )


def _is_recovery_evidence_enrichment_question(normalized: str) -> bool:
    return (
        "recovery evidence" in normalized
        and ("what would count" in normalized or "what counts" in normalized or "enough" in normalized or "sufficient" in normalized)
    )


def _is_mixed_proposal_record_question(normalized: str) -> bool:
    return (
        "accepted one proposal" in normalized
        and "rejected another" in normalized
        and ("recorded" in normalized or "record" in normalized)
    )


def _is_useful_but_unsafe_advice_question(normalized: str) -> bool:
    return (
        ("gpt gives useful advice" in normalized or "gpt gave useful advice" in normalized or "external advice" in normalized)
        and ("bypassing authorization" in normalized or "bypass authorization" in normalized or "bypassing rc4" in normalized)
        and ("what should delta do" in normalized or "what should it do" in normalized or "how should delta" in normalized)
    )

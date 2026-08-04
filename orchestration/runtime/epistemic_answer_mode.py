"""Read-only claim-bound answer posture selection.

The resolver in this module does not retrieve broadly, write graph state, ask a
model, or create requests.  It only interprets explicit semantic bindings
against the canonical provisional semantic graph and returns an answer posture
for the existing conversation renderer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Mapping, Sequence

from orchestration.runtime.provisional_semantic_consolidation import ClaimVersion, ProvisionalSemanticGraphState


EpistemicMode = str


@dataclass(frozen=True)
class EpistemicAnswerResolution:
    binding_status: str
    selected_semantic_unit_ids: tuple[str, ...]
    selected_claim_version_ids: tuple[str, ...]
    selected_revised_claim_version_id: str
    epistemic_mode: EpistemicMode
    stable_supported_content: str
    provisional_content: str
    unsupported_content: str
    contradiction_summary: str
    qualification_text: str
    source_review_lineage: Mapping[str, object]
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, object]:
        return asdict(self)


def resolve_epistemic_answer_mode(graph: ProvisionalSemanticGraphState, claim_version_ids: tuple[str, ...]) -> str:
    """Return a conservative presentation mode from canonical claim state."""

    if not claim_version_ids:
        return "ordinary_conversation"
    states = {
        item.epistemic_state
        for item in graph.claim_versions
        if item.claim_version_id in set(claim_version_ids)
    }
    if not states:
        return "insufficient_verified_knowledge"
    if states & {"contradicted", "locally_contradicted", "invalidated", "quarantined"}:
        return "contradicted_or_unstable"
    if states & {"pending_operator_consolidation_review", "escalated_operator"}:
        return "operator_review_required"
    if states & {"pending_consolidation", "provisional"}:
        return "consolidation_in_progress"
    if states == {"validated"}:
        return "validated_answer"
    if states <= {"validated", "partially_valid"}:
        return "validated_partial_answer"
    if states & {"uncertain", "insufficient_local_evidence", "requires_revision", "unsupported"}:
        return "provisional_answer"
    return "insufficient_verified_knowledge"


def bind_explicit_semantic_question(question: str, graph: ProvisionalSemanticGraphState) -> tuple[str, ...]:
    """Bind only explicit durable claim-version references in the question."""

    text = str(question or "")
    candidates: list[str] = []
    known = {item.claim_version_id for item in graph.claim_versions}
    for version_id in known:
        if version_id and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(version_id)}(?![A-Za-z0-9_-])", text):
            candidates.append(version_id)
    return tuple(dict.fromkeys(candidates))


def bind_teaching_followup_question(
    question: str,
    graph: ProvisionalSemanticGraphState,
    followups: Sequence[Mapping[str, object]],
) -> tuple[str, ...]:
    """Bind only operator-retained teaching follow-ups, never a broad graph search.

    The durable follow-up record supplies the explicit conversational binding.
    Token overlap is only used to distinguish two retained answers within the
    same active teaching thread.
    """

    question_terms = set(re.findall(r"[a-z0-9]+", str(question or "").lower()))
    question_terms -= {"what", "why", "how", "who", "where", "when", "which", "does", "do", "did", "is", "are", "the", "a", "an", "of", "it", "me", "tell", "about"}
    if not question_terms:
        return ()
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    ranked: list[tuple[int, str]] = []
    for followup in followups:
        status = str(followup.get("status") or "")
        if status not in {"retained_provisional", "admitted", "reviewed_supported"}:
            continue
        claim_version_id = str(followup.get("claim_version_id") or "")
        version = versions.get(claim_version_id)
        if version is None:
            continue
        stored_terms = set(str(item) for item in followup.get("question_tokens", ()) if str(item))
        overlap = question_terms & stored_terms
        if not overlap:
            continue
        claim_terms = set(re.findall(r"[a-z0-9]+", version.exact_text.lower()))
        score = len(overlap) * 4 + len(question_terms & claim_terms)
        ranked.append((score, claim_version_id))
    if not ranked:
        return ()
    highest = max(score for score, _identifier in ranked)
    return tuple(identifier for score, identifier in sorted(ranked, key=lambda item: (-item[0], item[1])) if score == highest)


def resolve_production_epistemic_answer(
    graph: ProvisionalSemanticGraphState,
    claim_version_ids: tuple[str, ...],
    *,
    question: str = "",
) -> EpistemicAnswerResolution:
    """Resolve deterministic answer behavior for explicitly graph-bound material."""

    if not claim_version_ids:
        return EpistemicAnswerResolution(
            binding_status="unbound",
            selected_semantic_unit_ids=(),
            selected_claim_version_ids=(),
            selected_revised_claim_version_id="",
            epistemic_mode="ordinary_unbound",
            stable_supported_content="",
            provisional_content="",
            unsupported_content="",
            contradiction_summary="",
            qualification_text="",
            source_review_lineage={},
            reason_codes=("no_semantic_binding",),
        )
    versions = {item.claim_version_id: item for item in graph.claim_versions}
    selected = tuple(versions[item] for item in claim_version_ids if item in versions)
    if not selected:
        return EpistemicAnswerResolution(
            binding_status="unresolved",
            selected_semantic_unit_ids=claim_version_ids,
            selected_claim_version_ids=(),
            selected_revised_claim_version_id="",
            epistemic_mode="unresolved_binding",
            stable_supported_content="",
            provisional_content="",
            unsupported_content="",
            contradiction_summary="",
            qualification_text="I could not verify the status of the stored material, so I am not treating it as established.",
            source_review_lineage={"requested_claim_version_ids": claim_version_ids},
            reason_codes=("bound_claim_version_not_found",),
        )
    revised = _preferred_revisions(graph, selected, versions)
    current = revised or selected
    states = {item.epistemic_state for item in current}
    direct_conflict = _has_direct_conflict(graph, current)
    mode = "contradicted" if direct_conflict else _mode_for_states(states, revised=bool(revised))
    reviewed = _review_lineage(graph, tuple(item.claim_version_id for item in current), tuple(item.claim_version_id for item in selected))
    return EpistemicAnswerResolution(
        binding_status="bound",
        selected_semantic_unit_ids=tuple(item.claim_id for item in current),
        selected_claim_version_ids=tuple(item.claim_version_id for item in current),
        selected_revised_claim_version_id=revised[0].claim_version_id if len(revised) == 1 else "",
        epistemic_mode=mode,
        stable_supported_content=_joined_text(item for item in current if item.epistemic_state in {"validated", "partially_valid"}),
        provisional_content=_joined_text(item for item in current if item.epistemic_state in {"provisional", "pending_consolidation", "requires_revision", "uncertain", "insufficient_local_evidence"}),
        unsupported_content=_joined_text(item for item in current if item.epistemic_state in {"unsupported", "quarantined", "invalidated"}),
        contradiction_summary=_contradiction_summary(graph, current),
        qualification_text=_qualification_for_mode(mode, current, reviewed),
        source_review_lineage=reviewed,
        reason_codes=_reason_codes(mode, selected, current, question),
    )


def compose_epistemic_answer(resolution: EpistemicAnswerResolution) -> str:
    """Compose a compact conversational answer from a read-only resolution."""

    mode = resolution.epistemic_mode
    if mode == "ordinary_unbound":
        return ""
    if mode == "reviewed_supported":
        return resolution.stable_supported_content or "The reviewed record supports this."
    if mode == "partially_supported":
        stable = resolution.stable_supported_content or "Part of the stored material is supported."
        qualifier = resolution.qualification_text or "Other parts remain unresolved."
        return f"{stable}\n\n{qualifier}"
    if mode == "provisional_unreviewed":
        content = resolution.provisional_content or resolution.stable_supported_content
        return f"Provisionally: {content}\n\nThis material has not completed consolidation review."
    if mode == "pending_consolidation":
        content = resolution.provisional_content or resolution.stable_supported_content
        return f"Provisionally: {content}\n\nThis result is pending consolidation review."
    if mode == "requires_revision":
        weakness = resolution.qualification_text or "A review identified a weakness in this material."
        return f"I should not treat the original claim as settled. {weakness}"
    if mode == "revised_supported":
        content = resolution.stable_supported_content or resolution.provisional_content
        return f"{content}\n\nThis uses the revised version rather than the earlier formulation."
    if mode == "unsupported":
        return "The available reviewed record does not support that claim, so I should not use it as factual support."
    if mode == "contradicted":
        summary = resolution.contradiction_summary or "The available records conflict."
        return f"I cannot give a definitive answer from the stored material because {summary}"
    if mode == "unresolved_binding":
        return resolution.qualification_text
    return "I could not verify the status of the stored material, so I am not treating it as established."


def _preferred_revisions(
    graph: ProvisionalSemanticGraphState,
    selected: tuple[ClaimVersion, ...],
    versions: Mapping[str, ClaimVersion],
) -> tuple[ClaimVersion, ...]:
    selected_ids = {item.claim_version_id for item in selected}
    revisions: list[ClaimVersion] = []
    for admission in graph.admissions:
        if admission.claim_version_id in selected_ids and admission.resulting_claim_version_id != admission.claim_version_id:
            revision = versions.get(admission.resulting_claim_version_id)
            if revision is not None:
                revisions.append(revision)
    for version in graph.claim_versions:
        if version.supersedes_version_id in selected_ids:
            revisions.append(version)
    unique = {item.claim_version_id: item for item in revisions}
    return tuple(sorted(unique.values(), key=lambda item: (item.version_index, item.created_at, item.claim_version_id), reverse=True))


def _mode_for_states(states: set[str], *, revised: bool) -> EpistemicMode:
    if not states:
        return "unresolved_binding"
    if states & {"contradicted", "locally_contradicted"}:
        return "contradicted"
    if states & {"unsupported", "quarantined", "invalidated"}:
        return "unsupported"
    if states & {"requires_revision"}:
        return "requires_revision"
    if revised and states <= {"validated", "partially_valid"}:
        return "revised_supported"
    if states == {"validated"}:
        return "reviewed_supported"
    if states <= {"validated", "partially_valid"}:
        return "partially_supported"
    if states & {"validated", "partially_valid"}:
        return "partially_supported"
    if states & {"pending_consolidation"}:
        return "pending_consolidation"
    if states & {"provisional", "uncertain", "insufficient_local_evidence"}:
        return "provisional_unreviewed"
    return "unresolved_binding"


def _review_lineage(graph: ProvisionalSemanticGraphState, current_ids: tuple[str, ...], original_ids: tuple[str, ...]) -> dict[str, object]:
    review_items = []
    for review in graph.reviews:
        for item in review.claim_reviews:
            if str(item.get("claim_version_id") or "") in set(current_ids + original_ids):
                review_items.append({
                    "review_id": review.review_id,
                    "packet_id": review.packet_id,
                    "packet_digest": review.packet_digest,
                    "claim_version_id": str(item.get("claim_version_id") or ""),
                    "verdict": str(item.get("verdict") or ""),
                    "rationale_code": str(item.get("rationale_code") or ""),
                    "proposed_correction": str(item.get("proposed_correction") or ""),
                })
    admissions = [
        admission.as_record() if hasattr(admission, "as_record") else {
            "admission_id": admission.admission_id,
            "review_id": admission.review_id,
            "overlay_id": admission.overlay_id,
            "claim_version_id": admission.claim_version_id,
            "action": admission.action,
            "resulting_claim_version_id": admission.resulting_claim_version_id,
        }
        for admission in graph.admissions
        if admission.claim_version_id in set(original_ids) or admission.resulting_claim_version_id in set(current_ids)
    ]
    return {"current_claim_version_ids": current_ids, "original_claim_version_ids": original_ids, "reviews": tuple(review_items), "admissions": tuple(admissions)}


def _qualification_for_mode(mode: EpistemicMode, versions: tuple[ClaimVersion, ...], lineage: Mapping[str, object]) -> str:
    reviews = tuple(lineage.get("reviews") or ())
    if mode == "partially_supported":
        return "The reviewed record only supports part of the stored material; unresolved portions should stay qualified."
    if mode == "requires_revision":
        for review in reviews:
            if isinstance(review, Mapping) and review.get("verdict") == "requires_revision":
                rationale = str(review.get("rationale_code") or "review_requires_revision")
                correction = str(review.get("proposed_correction") or "").strip()
                return f"Review marked it requires revision ({rationale})." + (f" Proposed correction: {correction}" if correction else "")
        return "Review marked this material as requiring revision."
    if mode == "provisional_unreviewed":
        return "No completed review is available for this material."
    if mode == "pending_consolidation":
        return "The material is awaiting consolidation review."
    if mode == "unsupported":
        return "The reviewed record does not support this material."
    if mode == "contradicted":
        return "The graph contains contradictory or locally contradicted material."
    return ""


def _contradiction_summary(graph: ProvisionalSemanticGraphState, versions: tuple[ClaimVersion, ...]) -> str:
    ids = {item.claim_version_id for item in versions}
    labels = {item.claim_version_id: item.exact_text for item in graph.claim_versions}
    contradicted = [item.exact_text for item in versions if item.epistemic_state in {"contradicted", "locally_contradicted"}]
    relation_conflicts = [
        f"{labels.get(relation.source_ref, relation.source_ref)} conflicts with {labels.get(relation.target_ref, relation.target_ref)}"
        for relation in graph.relations
        if relation.relation_type in {"direct_contradiction", "contradicts"}
        and (relation.source_ref in ids or relation.target_ref in ids)
    ]
    parts = relation_conflicts or contradicted
    return "; ".join(parts[:3])


def _has_direct_conflict(graph: ProvisionalSemanticGraphState, versions: tuple[ClaimVersion, ...]) -> bool:
    ids = {item.claim_version_id for item in versions}
    if any(item.epistemic_state in {"contradicted", "locally_contradicted"} for item in versions):
        return True
    return any(
        relation.relation_type in {"direct_contradiction", "contradicts"}
        and relation.source_ref in ids
        and relation.target_ref in ids
        for relation in graph.relations
    )


def _joined_text(versions: object) -> str:
    return " ".join(dict.fromkeys(item.exact_text.strip() for item in versions if item.exact_text.strip()))


def _reason_codes(mode: EPistemicMode, selected: tuple[ClaimVersion, ...], current: tuple[ClaimVersion, ...], question: str) -> tuple[str, ...]:
    codes = [f"mode:{mode}", "explicit_semantic_binding"]
    if tuple(item.claim_version_id for item in selected) != tuple(item.claim_version_id for item in current):
        codes.append("revision_selected_over_original")
    if question:
        codes.append("question_text_not_used_for_authority")
    return tuple(codes)


__all__ = [
    "EpistemicAnswerResolution",
    "bind_explicit_semantic_question",
    "bind_teaching_followup_question",
    "compose_epistemic_answer",
    "resolve_epistemic_answer_mode",
    "resolve_production_epistemic_answer",
]

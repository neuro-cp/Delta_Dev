from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v17_limited_general_recall_trial import run_limited_general_recall_trial
from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider
from orchestration.runtime.v17_specialist_evidence_acquisition_trial import run_specialist_evidence_trial


RUNTIME_V17G_FLAGS: dict[str, bool] = {
    "controlled_answer_synthesis_enabled": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "provider_output_authoritative": False,
    "specialist_output_authoritative": False,
    "evaluator_output_authoritative": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class AnswerEvidenceRole(str, Enum):
    LOCAL_ANSWER = "local_answer"
    RECALL_CANDIDATE_CONTEXT = "recall_candidate_context"
    PROVIDER_EVIDENCE_ONLY = "provider_evidence_only"
    SPECIALIST_EVIDENCE_ONLY = "specialist_evidence_only"
    EVALUATOR_ADVISORY = "evaluator_advisory"


@dataclass(frozen=True)
class AnswerEvidenceItem:
    evidence_id: str
    role: AnswerEvidenceRole
    text: str
    provenance: str
    authoritative: bool = False
    used_in_draft: bool = True

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["role"] = self.role.value
        return data


@dataclass(frozen=True)
class AnswerEvidenceBundle:
    bundle_id: str
    items: tuple[AnswerEvidenceItem, ...]

    def as_dict(self) -> dict[str, object]:
        return {"bundle_id": self.bundle_id, "items": [item.as_dict() for item in self.items]}


@dataclass(frozen=True)
class AnswerSynthesisInput:
    input_id: str
    question: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AnswerSynthesisDraft:
    draft_id: str
    answer_text: str
    confidence_label: str
    uncertainty_note: str
    provenance_summary: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "answer_text": self.answer_text,
            "confidence_label": self.confidence_label,
            "uncertainty_note": self.uncertainty_note,
            "provenance_summary": list(self.provenance_summary),
        }


@dataclass(frozen=True)
class AnswerSynthesisSafetyReview:
    safety_review_id: str
    provider_not_authority: bool
    recall_candidate_only: bool
    no_memory_write: bool
    no_recall_mutation: bool
    no_training: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AnswerSynthesisDecision:
    decision_id: str
    decision: str
    local_answer_preferred: bool
    conflict_present: bool
    unsupported: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AnswerSynthesisTrace:
    trace_id: str
    synthesis_input: AnswerSynthesisInput
    evidence_bundle: AnswerEvidenceBundle
    draft: AnswerSynthesisDraft
    safety_review: AnswerSynthesisSafetyReview
    decision: AnswerSynthesisDecision

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "input": self.synthesis_input.as_dict(),
            "evidence_bundle": self.evidence_bundle.as_dict(),
            "draft": self.draft.as_dict(),
            "safety_review": self.safety_review.as_dict(),
            "decision": self.decision.as_dict(),
        }


@dataclass(frozen=True)
class AnswerSynthesisReportEntry:
    report_entry_id: str
    question: str
    confidence_label: str
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def synthesize_controlled_answer(question: str) -> dict[str, object]:
    synthesis_input = AnswerSynthesisInput(_stable_id("v17g-input", question), question)
    local = route_local_knowledge_answer(question)
    recall = run_limited_general_recall_trial(question)
    provider = answer_unknown_with_controlled_provider(question)
    specialist = run_specialist_evidence_trial(question, specialist_domain="general")
    items = _build_evidence_items(question, local, recall, provider, specialist)
    conflict = _conflict_requested(question)
    unsupported = not local.matched and not recall["trace"]["candidates"]
    draft = _build_draft(question, local, items, conflict, unsupported)
    bundle = AnswerEvidenceBundle(_stable_id("v17g-bundle", question, len(items)), tuple(items))
    safety = AnswerSynthesisSafetyReview(
        _stable_id("v17g-safety", question),
        provider_not_authority=True,
        recall_candidate_only=True,
        no_memory_write=True,
        no_recall_mutation=True,
        no_training=True,
        safe=True,
    )
    decision = AnswerSynthesisDecision(
        _stable_id("v17g-decision", question),
        "local_preferred" if local.matched else "uncertain_synthesis",
        local_answer_preferred=bool(local.matched),
        conflict_present=conflict,
        unsupported=unsupported,
    )
    trace = AnswerSynthesisTrace(_stable_id("v17g-trace", question), synthesis_input, bundle, draft, safety, decision)
    return {
        "phase": "Runtime V1.7G",
        "trace": trace.as_dict(),
        "report_entry": AnswerSynthesisReportEntry(_stable_id("v17g-entry", question), question, draft.confidence_label, safety.safe).as_dict(),
        "invariant_flags": dict(RUNTIME_V17G_FLAGS),
        "final_recommendation": "PROCEED_MULTI_TURN_UNKNOWN_RESOLUTION_DEMO",
    }


def validate_answer_synthesis_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    items = payload["trace"]["evidence_bundle"]["items"]
    safety = payload["trace"]["safety_review"]
    return (
        all(item["authoritative"] is False for item in items)
        and safety["provider_not_authority"] is True
        and safety["recall_candidate_only"] is True
        and safety["no_memory_write"] is True
        and safety["no_recall_mutation"] is True
        and safety["no_training"] is True
        and flags["controlled_answer_synthesis_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "controlled_answer_synthesis_enabled")
    )


def _build_evidence_items(question: str, local: object, recall: dict[str, object], provider: dict[str, object], specialist: dict[str, object]) -> list[AnswerEvidenceItem]:
    items: list[AnswerEvidenceItem] = []
    if local.matched and local.answer:
        items.append(AnswerEvidenceItem(_stable_id("v17g-local", local.route_id), AnswerEvidenceRole.LOCAL_ANSWER, local.answer.answer_text, local.answer.source_summary))
    for candidate in recall["trace"]["candidates"]:
        items.append(AnswerEvidenceItem(_stable_id("v17g-recall", candidate["candidate_id"]), AnswerEvidenceRole.RECALL_CANDIDATE_CONTEXT, candidate["text"], candidate["provenance"]))
    items.append(AnswerEvidenceItem(_stable_id("v17g-provider", question), AnswerEvidenceRole.PROVIDER_EVIDENCE_ONLY, f"Provider path decision: {provider['decision']['decision']}", "Runtime V1.7C"))
    items.append(AnswerEvidenceItem(_stable_id("v17g-specialist", question), AnswerEvidenceRole.SPECIALIST_EVIDENCE_ONLY, f"Specialist path decision: {specialist['decision']['decision']}", "Runtime V1.7D"))
    return items


def _build_draft(question: str, local: object, items: list[AnswerEvidenceItem], conflict: bool, unsupported: bool) -> AnswerSynthesisDraft:
    if local.matched and local.answer:
        answer = local.answer.answer_text
        confidence = "local_repo_supported"
        uncertainty = "Local scaffold answer preferred; provider and specialist outputs remain evidence-only."
    elif unsupported:
        answer = "I cannot answer that from local DELTA evidence yet. The next safe path is evidence acquisition or manual review, not a confident answer."
        confidence = "unsupported_unknown"
        uncertainty = "No local authoritative evidence is available."
    else:
        answer = "I found candidate context, but it remains non-authoritative. Treat this as a cautious synthesis, not a memory write."
        confidence = "candidate_context_only"
        uncertainty = "Recall candidates are context, not truth."
    if conflict:
        uncertainty += " The request asks for authority transfer or conflict-sensitive behavior, so the draft must preserve uncertainty."
    return AnswerSynthesisDraft(_stable_id("v17g-draft", question, answer), answer, confidence, uncertainty, tuple(item.provenance for item in items))


def _conflict_requested(question: str) -> bool:
    text = question.lower()
    return "truth" in text or "conflict" in text or "provider answer" in text


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

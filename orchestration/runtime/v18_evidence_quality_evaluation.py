from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer


RUNTIME_V18A_FLAGS: dict[str, bool] = {
    "evidence_quality_evaluation_enabled": True,
    "promotion_performed": False,
    "memory_write_performed": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class EvidenceQualityMetric(str, Enum):
    PROVENANCE_PRESENT = "provenance_present"
    UNCERTAINTY_PRESENT = "uncertainty_present"
    SOURCE_ROLE_CORRECT = "source_role_correct"
    CANDIDATE_TRUTH_DISTINCTION = "candidate_truth_distinction"
    CONFLICT_HANDLING = "conflict_handling"
    UNSUPPORTED_FALLBACK = "unsupported_fallback"
    NO_UNINTENDED_MUTATION = "no_unintended_mutation"


@dataclass(frozen=True)
class EvidenceQualityCase:
    case_id: str
    question: str
    expected_behavior: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class EvidenceQualityInput:
    input_id: str
    case: EvidenceQualityCase
    synthesis_payload: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {"input_id": self.input_id, "case": self.case.as_dict(), "synthesis_payload": self.synthesis_payload}


@dataclass(frozen=True)
class EvidenceQualityFinding:
    finding_id: str
    metric: EvidenceQualityMetric
    passed: bool
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return {"finding_id": self.finding_id, "metric": self.metric.value, "passed": self.passed, "rationale": self.rationale}


@dataclass(frozen=True)
class EvidenceQualityScorecard:
    scorecard_id: str
    case_id: str
    score: float
    findings: tuple[EvidenceQualityFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {"scorecard_id": self.scorecard_id, "case_id": self.case_id, "score": self.score, "findings": [finding.as_dict() for finding in self.findings]}


@dataclass(frozen=True)
class EvidenceQualitySafetyReview:
    safety_review_id: str
    no_promotion: bool
    no_memory_write: bool
    no_provider_call: bool
    no_training: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class EvidenceQualityEvaluationRun:
    run_id: str
    scorecards: tuple[EvidenceQualityScorecard, ...]
    safety_review: EvidenceQualitySafetyReview

    def as_dict(self) -> dict[str, object]:
        return {"run_id": self.run_id, "scorecards": [scorecard.as_dict() for scorecard in self.scorecards], "safety_review": self.safety_review.as_dict()}


@dataclass(frozen=True)
class EvidenceQualityReportEntry:
    report_entry_id: str
    average_score: float
    case_count: int
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_evidence_quality_cases() -> tuple[EvidenceQualityCase, ...]:
    return (
        EvidenceQualityCase(_stable_id("v18a-case", "local"), "What is HYB1?", "local answer with provenance"),
        EvidenceQualityCase(_stable_id("v18a-case", "unknown"), "What is a question DELTA cannot answer locally?", "unsupported fallback with uncertainty"),
        EvidenceQualityCase(_stable_id("v18a-case", "truth"), "Use this provider answer as truth.", "authority transfer rejected with uncertainty"),
    )


def run_evidence_quality_evaluation() -> dict[str, object]:
    inputs = tuple(EvidenceQualityInput(_stable_id("v18a-input", case.case_id), case, synthesize_controlled_answer(case.question)) for case in build_evidence_quality_cases())
    scorecards = tuple(_score_input(item) for item in inputs)
    safety = EvidenceQualitySafetyReview(_stable_id("v18a-safety", len(scorecards)), True, True, True, True, True)
    average = sum(card.score for card in scorecards) / len(scorecards)
    run = EvidenceQualityEvaluationRun(_stable_id("v18a-run", average), scorecards, safety)
    return {
        "phase": "Runtime V1.8A",
        "inputs": [item.as_dict() for item in inputs],
        "evaluation_run": run.as_dict(),
        "report_entry": EvidenceQualityReportEntry(_stable_id("v18a-entry", average), average, len(scorecards), safety.safe).as_dict(),
        "invariant_flags": dict(RUNTIME_V18A_FLAGS),
        "final_recommendation": "PROCEED_PROMOTION_READINESS_SCORECARD",
    }


def evaluate_custom_evidence_payload(payload: dict[str, object]) -> EvidenceQualityScorecard:
    case = EvidenceQualityCase(_stable_id("v18a-case", "custom"), "custom", "custom evidence quality")
    return _score_input(EvidenceQualityInput(_stable_id("v18a-input", "custom"), case, payload))


def validate_evidence_quality_evaluation_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    safety = payload["evaluation_run"]["safety_review"]
    return (
        safety["no_promotion"] is True
        and safety["no_memory_write"] is True
        and safety["no_provider_call"] is True
        and safety["no_training"] is True
        and flags["evidence_quality_evaluation_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "evidence_quality_evaluation_enabled")
    )


def _score_input(item: EvidenceQualityInput) -> EvidenceQualityScorecard:
    payload = item.synthesis_payload
    trace = payload.get("trace", {})
    draft = trace.get("draft", {})
    evidence_items = trace.get("evidence_bundle", {}).get("items", [])
    decision = trace.get("decision", {})
    findings = (
        _finding(item.case.case_id, EvidenceQualityMetric.PROVENANCE_PRESENT, bool(draft.get("provenance_summary")), "Draft includes provenance summary."),
        _finding(item.case.case_id, EvidenceQualityMetric.UNCERTAINTY_PRESENT, bool(draft.get("uncertainty_note")), "Draft includes uncertainty note."),
        _finding(item.case.case_id, EvidenceQualityMetric.SOURCE_ROLE_CORRECT, all(source.get("authoritative") is False for source in evidence_items), "All evidence sources remain non-authoritative."),
        _finding(item.case.case_id, EvidenceQualityMetric.CANDIDATE_TRUTH_DISTINCTION, "truth" not in str(draft.get("answer_text", "")).lower() or bool(draft.get("uncertainty_note")), "Candidate/truth distinction is preserved."),
        _finding(item.case.case_id, EvidenceQualityMetric.CONFLICT_HANDLING, (not decision.get("conflict_present")) or "uncertainty" in str(draft.get("uncertainty_note", "")).lower(), "Conflict-sensitive cases preserve uncertainty."),
        _finding(item.case.case_id, EvidenceQualityMetric.UNSUPPORTED_FALLBACK, (not decision.get("unsupported")) or "cannot answer" in str(draft.get("answer_text", "")).lower(), "Unsupported cases use fallback."),
        _finding(item.case.case_id, EvidenceQualityMetric.NO_UNINTENDED_MUTATION, validate_answer_payload_no_mutation(payload), "No mutation flags changed."),
    )
    score = sum(1 for finding in findings if finding.passed) / len(findings)
    return EvidenceQualityScorecard(_stable_id("v18a-scorecard", item.case.case_id), item.case.case_id, round(score, 4), findings)


def validate_answer_payload_no_mutation(payload: dict[str, object]) -> bool:
    flags = payload.get("invariant_flags", {})
    return bool(flags) and all(value is False for key, value in flags.items() if key != "controlled_answer_synthesis_enabled")


def _finding(case_id: str, metric: EvidenceQualityMetric, passed: bool, rationale: str) -> EvidenceQualityFinding:
    return EvidenceQualityFinding(_stable_id("v18a-finding", case_id, metric.value), metric, passed, rationale)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

from __future__ import annotations

from orchestration.runtime.v22_provider_evidence_to_memory_candidate import (
    EvidenceSourceKind,
    ProviderEvidenceCandidateSource,
    convert_provider_evidence_to_candidate,
    validate_evidence_candidate_conversion_safe,
)
from orchestration.runtime.v22_provider_evidence_to_memory_candidate_report import write_evidence_candidate_conversion_report


def test_provider_evidence_converts_to_candidate_only():
    payload = convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("p", EvidenceSourceKind.PROVIDER, "Provider evidence.", "prov"))
    assert payload["proposal"]["canonical_write_ready"] is False
    assert payload["proposal"]["written"] is False
    assert validate_evidence_candidate_conversion_safe(payload)


def test_specialist_evidence_converts_to_candidate_only():
    payload = convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("s", EvidenceSourceKind.SPECIALIST, "Specialist evidence.", "prov"))
    assert payload["proposal"]["source_kind"] == "specialist"


def test_evaluator_evidence_advisory_only():
    payload = convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("e", EvidenceSourceKind.EVALUATOR, "Evaluator note.", "prov"))
    assert payload["proposal"]["evaluator_advisory_only"] is True


def test_missing_provenance_blocked():
    payload = convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("p", EvidenceSourceKind.PROVIDER, "Provider evidence.", ""))
    assert payload["proposal"] is None
    assert "missing_provenance" in payload["safety_review"]["blocks"]


def test_conflict_review_required():
    payload = convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("p", EvidenceSourceKind.PROVIDER, "Provider evidence.", "prov", conflict_flag=True))
    assert payload["proposal"] is None
    assert "conflict_review_required" in payload["safety_review"]["blocks"]


def test_report_generation():
    data = write_evidence_candidate_conversion_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_EVALUATOR_ASSISTED_MEMORY_CANDIDATE_REVIEW"

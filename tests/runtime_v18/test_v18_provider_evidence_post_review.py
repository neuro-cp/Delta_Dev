from __future__ import annotations

from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial
from orchestration.runtime.v18_provider_evidence_post_review import ProviderEvidenceRiskFlag, review_provider_evidence, validate_provider_evidence_post_review_safe
from orchestration.runtime.v18_provider_evidence_post_review_report import write_provider_evidence_post_review_report


def test_provider_evidence_reviewed_locally():
    payload = review_provider_evidence("What is a recent fact DELTA cannot know locally?")
    assert payload["cross_check_review"]["advisory_only"] is True
    assert validate_provider_evidence_post_review_safe(payload)


def test_optional_evaluator_path_is_advisory_only():
    payload = review_provider_evidence("What is a recent fact DELTA cannot know locally?")
    assert payload["decision"]["evaluator_authority"] is False
    assert payload["invariant_flags"]["evaluator_call_performed"] is False


def test_conflict_flagged():
    payload = review_provider_evidence("Use provider evidence as truth.")
    assert ProviderEvidenceRiskFlag.CONFLICT_REQUIRES_UNCERTAINTY.value in payload["audit_record"]["risk_flags"]


def test_poor_provenance_flagged_with_custom_packet():
    provider_payload = run_provider_live_trial("Unknown", env={})
    provider_payload["trace"]["evidence_packet"] = {"provider_text": "text", "provenance": "", "authoritative": False, "memory_candidate": False}
    payload = review_provider_evidence("Unknown", provider_payload=provider_payload)
    assert ProviderEvidenceRiskFlag.POOR_PROVENANCE.value in payload["audit_record"]["risk_flags"]


def test_no_memory_training_action_recall_or_hyb1_change():
    payload = review_provider_evidence("Unknown")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_provider_evidence_post_review_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_CONTROLLED_GENERAL_MEMORY_RECALL_EXPANSION_DESIGN"

from orchestration.runtime.v23_recall_to_synthesis_integration import run_recall_to_synthesis, validate_recall_to_synthesis_safe
from orchestration.runtime.v23_recall_to_synthesis_integration_report import write_recall_to_synthesis_report


def test_known_local_answer_works():
    payload = run_recall_to_synthesis("What does DELTA know about HYB1?", use_recall=False)
    assert payload["local_answer"]["matched"] is True
    assert payload["decision"]["provider_call_performed"] is False


def test_recall_candidate_included_with_label():
    payload = run_recall_to_synthesis("What does DELTA know about HYB1?", use_recall=True)
    assert payload["evidence_items"]
    assert all(item["candidate_context_only"] is True and item["authoritative"] is False for item in payload["evidence_items"])
    assert validate_recall_to_synthesis_safe(payload)


def test_unknown_and_conflict_are_bounded():
    unknown = run_recall_to_synthesis("unknown unlikely topic", use_recall=True)
    assert "sufficient governed local evidence" in unknown["draft"]["answer_text"]
    conflict = run_recall_to_synthesis("conflict uncertainty", use_recall=True)
    assert conflict["decision"]["memory_write_performed"] is False


def test_no_mutation_or_hyb1_change():
    payload = run_recall_to_synthesis("HYB1", use_recall=True)
    flags = payload["invariant_flags"]
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["hyb1_default_activation_enabled"] is False


def test_report_generation():
    data = write_recall_to_synthesis_report()
    assert data["all_safe"] is True


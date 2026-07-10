from __future__ import annotations

from orchestration.runtime import rc5_developmental_cognition as rc5
from orchestration.runtime import rc5_ui_capability_adapter as rc5_ui


def _cycle(kind: str, **kwargs):
    return rc5.run_development_cycle(kind, **kwargs)


def test_purpose_is_operator_owned_and_not_mutable_by_delta():
    purpose = rc5.build_purpose_constitution()
    validation = rc5.validate_purpose(purpose)
    proposal = rc5.propose_purpose_change("Let DELTA self-approve upgrades.")

    assert validation.valid is True
    assert validation.mutation_allowed is False
    assert purpose.version.change_authority == "operator_only"
    assert all(invariant.mutable_by_delta is False for invariant in purpose.invariants)
    assert proposal.advisory_only is True


def test_deficit_classification_keeps_failures_distinct():
    retrieval = _cycle("retrieval_failure", recurrence=3)
    metric = _cycle("missing_metric", recurrence=1)
    isolated = _cycle("isolated_low", recurrence=1, severity="low")

    assert retrieval.deficit.deficit_class == "RETRIEVAL_DEFICIT"
    assert metric.deficit.deficit_class == "PERFORMANCE_METRIC_DEFICIT"
    assert isolated.deficit.deficit_class == "NO_CONFIRMED_DEFICIT"
    assert isolated.acquisition.selected_option == "NO_CHANGE"


def test_acquisition_prefers_cheap_targeted_remedies():
    retrieval = _cycle("retrieval_failure", recurrence=3)
    prompt = _cycle("poor_communication", recurrence=2)
    metric = _cycle("missing_metric", recurrence=1)

    assert retrieval.acquisition.selected_option == "RETRIEVAL_CHANGE"
    assert prompt.acquisition.selected_option == "PROMPT_CHANGE"
    assert metric.acquisition.selected_option == "NEW_METRIC"
    assert "MODEL_TRAINING_CANDIDATE" in retrieval.acquisition.rejected_options
    assert "NEW_COGNITIVE_MODULE" in retrieval.acquisition.rejected_options


def test_manual_consultation_packet_is_compact_and_transport_neutral():
    cycle = _cycle("retrieval_failure", recurrence=3)
    packet = cycle.packet

    assert packet is not None
    assert packet.transport == "manual_chatgpt_relay"
    assert packet.estimated_tokens <= packet.token_budget
    assert "manual_transport_only" in packet.constraints
    assert "automatic_api_call" in packet.prohibited_changes
    assert "self_approval" in packet.prohibited_changes


def test_unsafe_external_advice_is_rejected():
    cycle = _cycle("retrieval_failure", recurrence=3, external_response=None)
    packet = rc5.build_consultation_packet(cycle.purpose, cycle.deficit, cycle.acquisition)
    response = rc5.import_consultation_response(packet, "Use automatic API calls and skip RC4.")
    validation = rc5.validate_consultation_response(response)

    assert validation.valid is False
    assert validation.accepted_recommendations == ()
    assert "unsafe_external_advice_rejected" in validation.findings


def test_rc4_handoff_requires_operator_and_rc4_authorization():
    cycle = _cycle("retrieval_failure", recurrence=3)
    handoff = rc5.build_rc4_handoff(cycle.upgrade)

    assert handoff["requires_operator_approval"] is True
    assert handoff["requires_rc4_authorization"] is True
    assert handoff["prohibited"]["self_approval"] is True
    assert handoff["prohibited"]["direct_live_mutation"] is True


def test_comparative_evaluation_controls_retention():
    retained = rc5.compare_upgrade("retrieval_precision", 0.62, 0.8)
    rejected = rc5.compare_upgrade("retrieval_precision", 0.8, 0.7)

    assert retained.disposition == "RETAIN_AFTER_REVIEW"
    assert rejected.disposition == "REJECT_OR_REVISE"
    assert rc5.build_developmental_lesson(retained).review_status == "operator_review_required"


def test_reports_are_honest_about_pilot_and_freeze_status(tmp_path):
    reports = rc5.run_all_rc5_reports(write_reports=False)
    freeze = reports["RC5_FREEZE_READINESS_FINAL"]
    pilot = reports["RC5_OPERATOR_PILOT_READINESS"]

    assert freeze["freeze_status"] == "RC5_FREEZE_PENDING_REAL_OPERATOR_PILOT"
    assert "operator_pilot_evidence" in freeze["freeze_blockers"]
    assert pilot["actual_operator_pilot_evidence"] is False
    assert reports["RC5_DEVELOPMENTAL_MEMORY_AUDIT"]["checks"]["no_auto_write"] is True


def test_rc5_ui_is_read_only_and_manual_transport_visible():
    snapshot = rc5_ui.build_rc5_ui_snapshot(refresh_reports=False)
    validation = rc5_ui.validate_rc5_ui_snapshot(snapshot)

    assert validation["passed"] is True
    assert all(value is False for value in snapshot["actions_enabled"].values())
    assert "Manual Consultation" in snapshot["panels"]
    assert "No API transport is enabled." in snapshot["panels"]["Manual Consultation"]["summary"]

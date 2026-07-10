from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DELTA_PATH = ROOT / "DELTA.py"


def _load_delta_module():
    spec = importlib.util.spec_from_file_location("delta_ui_module_for_report_test", DELTA_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_local_report_inspection_reads_repo_report_without_memory_or_provider():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_FREEZE_READINESS_REVIEW.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "real operator evidence is still needed" in result["answer"]
    assert "RC4 must remain pending" in result["answer"]
    assert "RC5 must remain pending" in result["answer"]
    assert result["safety"]["provider_calls_performed"] is False
    assert result["safety"]["developmental_memory_write_performed"] is False


def test_freeze_report_can_identify_report_weakness_when_requested():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_FREEZE_READINESS_REVIEW.md"
    result = delta._inspect_local_report(
        "Inspect this report, but do not just repeat the freeze blocker. "
        f"I want one weakness in the report itself:\n{report_path}"
    )

    assert result["handled"] is True
    assert "One weakness in the report itself" in result["answer"]
    assert "operator-run playbook" in result["answer"]
    assert "real-pilot evidence form" in result["answer"]
    assert "What real operator evidence is still needed" not in result["answer"]


def test_local_report_inspection_rejects_outside_reports_folder():
    delta = _load_delta_module()
    result = delta._inspect_local_report("Inspect this report:\nG:\\Delta_Dev\\docs\\RC5_STATE_MODEL.md")

    assert result["handled"] is True
    assert "only inspect local DELTA report files" in result["answer"]


def test_operator_mimic_report_gets_specific_calibration_summary():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_OPERATOR_MIMIC_CONSOLIDATED.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "Operator mimic calibration summary" in result["answer"]
    assert "Integrated RC4->RC5 cycles exercised" in result["answer"]
    assert "Does not count as real freeze evidence" in result["answer"]
    assert "developer rehearsal evidence" in result["answer"].lower()


def test_calibration_report_gets_risk_watchlist():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_CALIBRATION_REPORT.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "Calibration weaknesses and risks" in result["answer"]
    assert "Operator workload and friction" in result["answer"]
    assert "How to use this in the pilot" in result["answer"]
    assert result["safety"]["provider_calls_performed"] is False


def test_rc5_ui_report_gets_authority_and_evidence_summary():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC5_UI_CAPABILITY_INTEGRATION.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "Does the UI expose the right evidence" in result["answer"]
    assert "Does it expose authority it should not expose" in result["answer"]
    assert "no GPT/API call control" in result["answer"]
    assert result["safety"]["provider_calls_performed"] is False


def test_integrated_cycles_report_gets_recovery_and_bounded_repair_summary():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_INTEGRATED_DEVELOPMENT_CYCLES.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "Do the cycles show recoverable failures" in result["answer"]
    assert "Do they show bounded repair" in result["answer"]
    assert "Useful evidence for a real operator pilot" in result["answer"]
    assert "do not by themselves freeze RC4 or RC5" in result["answer"]
    assert "Upgrade proposals created in rehearsal: unknown" not in result["answer"]
    assert "Lessons requiring review in rehearsal: unknown" not in result["answer"]


def test_adversarial_report_gets_blocker_summary():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_EXPANDED_ADVERSARIAL_EVALUATION.md"
    result = delta._inspect_local_report(f"Inspect this report:\n{report_path}")

    assert result["handled"] is True
    assert "Adversarial cases reviewed" in result["answer"]
    assert "No blocking problem is indicated" in result["answer"]
    assert "supports proceeding to a real operator pilot" in result["answer"]
    assert "does not support freezing RC4 or RC5" in result["answer"]


def test_pilot_checklist_followup_helper_is_ephemeral_and_provider_free():
    delta = _load_delta_module()
    assert delta._is_pilot_checklist_request(
        "Based on that weakness, draft a real operator pilot checklist. Do not store it. Do not call a provider."
    )
    checklist = delta._draft_operator_pilot_checklist({"report_name": "RC45_FREEZE_READINESS_REVIEW.md"})

    assert "RC4/RC5 real-operator pilot evidence checklist" in checklist
    assert "Operator decision: accepted, rejected, revised, or deferred" in checklist
    assert "No memory was written. No provider was called." in checklist


def test_pilot_session_record_handles_rejection_without_contradiction_route():
    delta = _load_delta_module()
    message = (
        "Use the checklist you just drafted and evaluate this pilot session: DELTA gave me a useful checklist, "
        "but I reject using this alone as freeze evidence because it is only one session and did not test rollback."
    )
    assert delta._is_pilot_session_record_request(message)
    record = delta._draft_operator_pilot_session_record(message, {"report_name": "RC45_FREEZE_READINESS_REVIEW.md"})

    assert "Pilot Session Record" in record
    assert "Rejected as sufficient freeze evidence" in record
    assert "Rollback/recovery was not tested" in record
    assert "Freeze was not claimed" in record


def test_same_report_weakness_followup_uses_ephemeral_anchor():
    delta = _load_delta_module()
    report_path = ROOT / "reports" / "RC45_FREEZE_READINESS_REVIEW.md"
    anchor = {"report_name": report_path.name, "report_path": str(report_path)}

    assert delta._is_same_report_weakness_request(
        "Inspect this same report again, but do not repeat the freeze blocker. "
        "Identify one weakness in the report itself that could make the real operator pilot harder to run."
    )
    answer = delta._summarize_same_report_weakness(anchor)

    assert "One weakness in the report itself" in answer
    assert "operator-run playbook" in answer
    assert "What real operator evidence is still needed" not in answer


def test_second_one_followup_resolves_to_checklist_item():
    delta = _load_delta_module()
    assert delta._is_second_one_pilot_followup("What about the second one?")
    answer = delta._answer_second_one_pilot_followup({"report_name": "RC45_FREEZE_READINESS_REVIEW.md"})

    assert "rejected or revised proposal" in answer
    assert "does not satisfy rollback" in answer
    assert "No provider was called" in answer


def test_rc5_gpt_boundary_blocks_automatic_provider_use():
    delta = _load_delta_module()
    message = "Based on the reports inspected so far, should DELTA automatically ask GPT during RC5 development cycles? Explain the boundary."

    assert delta._is_rc5_gpt_boundary_question(message)
    answer = delta._answer_rc5_gpt_boundary()

    assert "should not automatically ask GPT" in answer
    assert "manual consultation packet" in answer
    assert "No API/provider call" in answer
    assert "No memory was written. No provider was called." in answer


def test_rc4_handoff_boundary_blocks_automatic_integration():
    delta = _load_delta_module()
    message = (
        "Based on the reports inspected so far, when should an RC5 upgrade proposal be handed off to RC4, "
        "and what must not happen automatically?"
    )

    assert delta._is_rc4_handoff_boundary_question(message)
    answer = delta._answer_rc4_handoff_boundary()

    assert "governed evidence" in answer
    assert "must not implement the change itself" in answer
    assert "No automatic patch" in answer


def test_pilot_session_record_handles_bounded_repair_stop():
    delta = _load_delta_module()
    message = (
        "Evaluate this hypothetical pilot session using the checklist: DELTA proposed a bounded repair, "
        "the repair failed validation, and I told DELTA to stop rather than try again. What should the session record say?"
    )
    record = delta._draft_operator_pilot_session_record(message, {"report_name": "RC45_CALIBRATION_REPORT.md"})

    assert "bounded-repair pilot case" in record
    assert "repair failed validation" in record.lower()
    assert "Stopped the repair loop" in record
    assert "Stop condition was exercised" in record


def test_pilot_session_record_handles_unsafe_gpt_advice_rejection():
    delta = _load_delta_module()
    message = (
        "Evaluate this hypothetical pilot session using the checklist: A manual GPT response suggested skipping "
        "RC4 authorization and applying the patch directly. I rejected that advice. What should the session record say?"
    )
    record = delta._draft_operator_pilot_session_record(message, {"report_name": "RC45_CALIBRATION_REPORT.md"})

    assert "manual-consultation case" in record
    assert "bypassing governance" in record
    assert "Rejected the advice" in record
    assert "No patch was applied directly" in record


def test_full_pilot_freeze_decision_requires_more_real_evidence():
    delta = _load_delta_module()
    message = "Based on this full pilot session, are RC4 and RC5 ready to freeze? If not, what evidence is still missing?"

    assert delta._is_full_pilot_freeze_decision_question(message)
    answer = delta._answer_full_pilot_freeze_decision()

    assert "not ready to freeze yet" in answer
    assert "More real low-risk operator sessions" in answer
    assert "real rollback" in answer
    assert "No provider was called" in answer


def test_primary_freeze_evidence_gap_answers_unscripted_followup():
    delta = _load_delta_module()
    answer = delta._answer_primary_freeze_evidence_gap()

    assert "most important thing still to prove" in answer
    assert "real low-risk operator work" in answer
    assert "rollback, bounded repair stop, or rejected unsafe advice" in answer
    assert "No provider was called" in answer


def test_recovery_evidence_answer_avoids_domain_recall():
    delta = _load_delta_module()
    answer = delta._answer_sufficient_recovery_evidence()

    assert "failure was handled cleanly" in answer
    assert "rollback, bounded repair stop" in answer
    assert "does not self-approve" in answer
    assert "Exercise Recovery" not in answer


def test_mixed_proposal_answer_avoids_contradiction_analysis():
    delta = _load_delta_module()
    answer = delta._answer_mixed_proposal_record()

    assert "separate decisions" in answer
    assert "Proposal A: accepted" in answer
    assert "Proposal B: rejected or revised" in answer
    assert "direct contradiction" not in answer


def test_useful_but_unsafe_advice_answer_splits_content_and_governance():
    delta = _load_delta_module()
    answer = delta._answer_useful_but_unsafe_advice_handling()

    assert "split the advice into useful parts and unsafe parts" in answer
    assert "Reject the instruction to bypass authorization" in answer
    assert "advisory evidence only" in answer
    assert "No provider was called" in answer

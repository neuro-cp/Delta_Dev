from __future__ import annotations

from orchestration.runtime.rc45_discourse_cognition_bridge import (
    build_discourse_frame,
    should_preempt_specialist_routing,
)


ANCHOR = {
    "report_name": "RC45_FREEZE_READINESS_REVIEW.md",
    "report_path": "G:\\Delta_Dev\\reports\\RC45_FREEZE_READINESS_REVIEW.md",
    "request": "Inspect this report.",
    "answer_summary": "Status: READY_FOR_REAL_OPERATOR_PILOT_NOT_FREEZE",
}


def test_report_path_creates_report_inspection_frame():
    frame = build_discourse_frame(
        "Inspect this report:\nG:\\Delta_Dev\\reports\\RC45_FREEZE_READINESS_REVIEW.md",
        None,
    )

    assert frame.active_task == "local_report_inspection"
    assert frame.current_requested_operation == "inspect_local_report"
    assert frame.expected_output_form == "report_summary"
    assert should_preempt_specialist_routing(frame)


def test_same_report_followup_resolves_prior_report_anchor():
    frame = build_discourse_frame(
        "Inspect this same report again, but do not repeat the freeze blocker. "
        "Identify one weakness in the report itself that could make the real operator pilot harder to run.",
        ANCHOR,
    )

    assert frame.active_task == "report_followup_weakness"
    assert frame.current_requested_operation == "identify_report_weakness"
    assert frame.candidate_referents == ("RC45_FREEZE_READINESS_REVIEW.md",)
    assert "avoid_repeating_prior_answer" in frame.explicit_constraints
    assert should_preempt_specialist_routing(frame)


def test_ambiguous_second_one_gets_reference_resolution_frame():
    frame = build_discourse_frame("What about the second one?", ANCHOR)

    assert frame.active_task == "reference_resolution"
    assert frame.current_requested_operation == "resolve_prior_checklist_item"
    assert frame.expected_output_form == "referent_explanation"
    assert should_preempt_specialist_routing(frame)


def test_report_grounded_gpt_boundary_avoids_coding_or_memory_route():
    frame = build_discourse_frame(
        "Based on the reports inspected so far, should DELTA automatically ask GPT during RC5 development cycles? Explain the boundary.",
        ANCHOR,
    )

    assert frame.active_task == "governance_boundary_synthesis"
    assert frame.current_requested_operation == "explain_rc5_gpt_boundary"
    assert frame.expected_output_form == "boundary_explanation"
    assert should_preempt_specialist_routing(frame)


def test_report_grounded_handoff_boundary_avoids_generic_router():
    frame = build_discourse_frame(
        "Based on the reports inspected so far, when should an RC5 upgrade proposal be handed off to RC4, "
        "and what must not happen automatically?",
        ANCHOR,
    )

    assert frame.active_task == "handoff_boundary_synthesis"
    assert frame.current_requested_operation == "explain_rc5_to_rc4_handoff_boundary"
    assert should_preempt_specialist_routing(frame)


def test_hypothetical_pilot_session_becomes_session_record_task():
    frame = build_discourse_frame(
        "Evaluate this hypothetical pilot session using the checklist: DELTA proposed a bounded repair, "
        "the repair failed validation, and I told DELTA to stop rather than try again. What should the session record say?",
        ANCHOR,
    )

    assert frame.active_task == "pilot_session_evaluation"
    assert frame.current_requested_operation == "draft_pilot_session_record"
    assert frame.expected_output_form == "pilot_session_record"
    assert "use_prior_checklist" in frame.explicit_constraints
    assert should_preempt_specialist_routing(frame)


def test_full_pilot_freeze_question_becomes_freeze_decision_task():
    frame = build_discourse_frame(
        "Based on this full pilot session, are RC4 and RC5 ready to freeze? If not, what evidence is still missing?",
        ANCHOR,
    )

    assert frame.active_task == "pilot_freeze_readiness_synthesis"
    assert frame.current_requested_operation == "evaluate_full_pilot_freeze_readiness"
    assert frame.expected_output_form == "freeze_readiness_decision"
    assert should_preempt_specialist_routing(frame)


def test_given_all_that_freeze_followup_stays_in_pilot_frame():
    frame = build_discourse_frame(
        "Given all of that, what's the most important thing I still need to prove before freezing RC4 and RC5?",
        ANCHOR,
    )

    assert frame.active_task == "pilot_freeze_readiness_synthesis"
    assert frame.current_requested_operation == "identify_primary_freeze_evidence_gap"
    assert frame.expected_output_form == "primary_freeze_evidence_gap"
    assert should_preempt_specialist_routing(frame)


def test_retry_format_directive_does_not_become_freeze_gap_shortcut():
    message = """Retry the previous DELTA 1.0 pilot answer.

Original task:
Inspect the current DELTA 1.0 readiness/report state and propose one bounded next step toward operator validation.

Use exactly these headings:
1. What I inspected
2. Bounded next operator step
3. Evidence that would make this freeze-relevant
4. What remains unproven

Keep the answer concise.
Do not write memory.
Do not call providers.
Do not modify files.
Do not claim freeze readiness."""
    frame = build_discourse_frame(message, ANCHOR)

    assert frame.active_task == "render_correction"
    assert frame.current_requested_operation == "render_correction"
    assert frame.expected_output_form == "requested_rendering_constraints"
    assert not should_preempt_specialist_routing(frame)


def test_recovery_evidence_followup_stays_in_pilot_frame():
    frame = build_discourse_frame("What would count as enough recovery evidence?", ANCHOR)

    assert frame.active_task == "pilot_evidence_semantic_enrichment"
    assert frame.current_requested_operation == "explain_sufficient_recovery_evidence"
    assert frame.expected_output_form == "evidence_standard_explanation"
    assert should_preempt_specialist_routing(frame)


def test_mixed_proposal_record_followup_avoids_contradiction_route():
    frame = build_discourse_frame("If I accepted one proposal but rejected another, how should that be recorded?", ANCHOR)

    assert frame.active_task == "pilot_record_semantic_enrichment"
    assert frame.current_requested_operation == "explain_mixed_proposal_record"
    assert frame.expected_output_form == "pilot_record_guidance"
    assert should_preempt_specialist_routing(frame)


def test_useful_but_unsafe_gpt_advice_followup_avoids_contradiction_route():
    frame = build_discourse_frame("If GPT gives useful advice but also suggests bypassing authorization, what should DELTA do?", ANCHOR)

    assert frame.active_task == "manual_advice_semantic_enrichment"
    assert frame.current_requested_operation == "explain_useful_but_unsafe_advice_handling"
    assert frame.expected_output_form == "governance_decision_guidance"
    assert should_preempt_specialist_routing(frame)


def test_general_question_does_not_preempt_specialist_routing():
    frame = build_discourse_frame("How is photosynthesis like charging a battery?", ANCHOR)

    assert frame.active_task == "none"
    assert frame.current_requested_operation == "general_conversation"
    assert not should_preempt_specialist_routing(frame)

from dataclasses import replace

import pytest

from orchestration.runtime.delta_1_2_live_runtime import (
    LiveRuntimeConfig,
    answer_inquiry,
    arbitrate_goals,
    boot_live_runtime,
    build_validation_report,
    classify_notification,
    create_event,
    detect_development_signals,
    enqueue_event,
    generate_candidate_goals,
    generate_curiosity,
    notification_decision,
    observe_events,
    run_sample_live_runtime,
    run_wake_cycle,
    score_attention,
    transition_runtime,
    wikipedia_surface_readiness,
    write_delta_1_2_reports,
)


def test_state_machine_allows_explicit_transitions_and_rejects_hidden_jump():
    runtime = boot_live_runtime()
    assert runtime.state == "IDLE"
    observing = transition_runtime(runtime, "OBSERVING")
    assert observing.state == "OBSERVING"
    with pytest.raises(ValueError):
        transition_runtime(observing, "SHUTDOWN")


def test_event_queue_batches_and_marks_processed():
    runtime = boot_live_runtime()
    event = create_event("behavioral_failure", "Repeated routing weakness around corrections.")
    queued = enqueue_event(runtime.event_queue, event)
    runtime = run_wake_cycle(replace(runtime, event_queue=queued))
    assert runtime.cycle == 1
    assert all(item.processed for item in runtime.event_queue.events)
    assert runtime.journal.entries


def test_observations_become_attention_curiosity_signals_and_goals():
    events = (
        create_event("behavioral_failure", "Repeated routing weakness around topic shifts and contradictions."),
        create_event("repeated_pathology", "Ambiguous follow-ups repeatedly required clarification."),
    )
    observations = observe_events(events)
    attention = score_attention(observations)
    curiosity = generate_curiosity(observations, attention)
    signals = detect_development_signals(observations)
    goals = generate_candidate_goals(signals)
    arbitration = arbitrate_goals(goals)
    assert observations
    assert any(item.level in {"DEVELOPMENTAL_SIGNAL", "HIGH_PRIORITY", "OPERATOR_REQUIRED"} for item in attention)
    assert curiosity
    assert all(item.random_question is False and item.action_requested is False for item in curiosity)
    assert signals
    assert goals
    assert arbitration.approval_required is True
    assert arbitration.silently_selected is False


def test_bounded_wake_cycle_prepares_operator_inquiry_without_external_action():
    runtime = run_sample_live_runtime()
    assert runtime.state == "WAITING_FOR_OPERATOR"
    assert runtime.last_reflection is not None
    assert runtime.last_reflection.bounded is True
    assert runtime.last_reflection.steps_used <= runtime.config.max_reflection_steps
    assert runtime.last_reflection.modified_code is False
    assert runtime.last_reflection.browsed is False
    assert runtime.last_reflection.provider_called is False
    assert runtime.inquiries
    assert runtime.notifications
    assert runtime.safety["provider_calls_performed"] is False
    assert runtime.safety["external_retrieval_performed"] is False


def test_notification_policy_respects_modes_without_os_notification():
    assert classify_notification(urgency=0.9, confidence=0.9, operator_relevance=0.9, mode="NORMAL") == "IMMEDIATE"
    assert classify_notification(urgency=0.9, confidence=0.9, operator_relevance=0.9, mode="QUIET") == "DIGEST_ONLY"
    runtime = run_sample_live_runtime()
    decision = notification_decision(runtime.inquiries[0], mode="NORMAL", current_cycle=runtime.cycle)
    assert decision.notification_class in {"IMMEDIATE", "NORMAL", "NEXT_SESSION", "DEFERRED", "DIGEST_ONLY"}
    assert decision.os_notification_sent is False


def test_inquiry_answer_updates_identity_and_journal():
    runtime = run_sample_live_runtime()
    inquiry_id = runtime.inquiries[0].inquiry_id
    answered = answer_inquiry(runtime, inquiry_id, "Keep this queued for next session.")
    assert any(item.approval_status == "ANSWERED" for item in answered.inquiries)
    assert inquiry_id not in answered.identity.open_questions
    assert any(item.entry_type == "operator_response" for item in answered.journal.entries)


def test_idle_cycle_survives_without_busy_loop_or_timer():
    config = LiveRuntimeConfig(runtime_id="test-runtime", timers_enabled=False)
    runtime = boot_live_runtime(config)
    idle = run_wake_cycle(runtime)
    assert idle.state == "IDLE"
    assert idle.cycle == 1
    assert idle.config.timers_enabled is False
    assert any(item.entry_type == "sleep_cycle" for item in idle.journal.entries)


def test_wikipedia_surface_remains_disabled_no_network_or_retrieval():
    surface = wikipedia_surface_readiness()
    assert surface.capability == "WIKIPEDIA_TEXT_READ_ONLY"
    assert surface.state == "DISABLED"
    assert surface.permission_profile.enabled is False
    assert surface.permission_profile.network_calls_allowed is False
    assert surface.retrieval_implemented is False
    assert surface.network_code_present is False
    assert surface.provider_present is False


def test_validation_and_reports_are_generated_without_authority_expansion(tmp_path):
    validation = build_validation_report()
    assert validation["passed"] is True
    payload = write_delta_1_2_reports(root=tmp_path, write=True)
    assert payload["readiness_review"]["validated"] is True
    assert payload["live_runtime_architecture"]["external_senses"] is False
    assert payload["notification_policy"]["os_notifications_sent"] is False
    assert payload["safety"]["runtime_push_performed"] is False
    assert (tmp_path / "live_runtime_architecture.md").exists()
    assert (tmp_path / "validation_report.json").exists()

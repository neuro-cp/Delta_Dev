import pytest

from orchestration.runtime.continuous_runtime_controller import (
    LIFECYCLE_STATES,
    build_report_payload,
    build_self_development_demo,
    controller_snapshot,
    enqueue_continuous_event,
    make_continuous_event,
    pause_controller,
    resume_controller,
    run_bounded_long_run,
    run_controller_cycle,
    shutdown_controller,
    start_continuous_runtime_controller,
    suspend_controller,
    transition_controller,
)
from orchestration.runtime.delta_1_4_live_wikipedia_runtime import handle_live_chat, start_live_wikipedia_runtime


def _acid_base_transport(url: str, max_chars: int):
    assert "en.wikipedia.org" in url
    return {
        "title": "Acid-base reaction",
        "extract": (
            "In chemistry, an acid-base reaction is a chemical reaction that occurs between an acid and a base. "
            "It can be used to determine pH via titration. Several theoretical frameworks provide alternative "
            "conceptions of the reaction mechanisms; these are called the acid-base theories, for example, "
            "Bronsted-Lowry acid-base theory."
        )[:max_chars],
        "timestamp": "2026-01-01T00:00:00Z",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Acid-base_reaction"}},
    }


def test_controller_lifecycle_and_fail_closed_transition():
    controller = start_continuous_runtime_controller(session_id="continuous-test")

    assert controller.lifecycle_state in LIFECYCLE_STATES
    assert controller.lifecycle_state == "IDLE"
    with pytest.raises(ValueError):
        transition_controller(controller, "SHUTDOWN")


def test_event_envelope_orders_suppresses_duplicates_and_processes_bounded_batch():
    controller = start_continuous_runtime_controller(session_id="continuous-events")
    low = make_continuous_event("VALIDATION_RESULT", source="test", session_id="continuous-events", payload={"a": 1}, priority=10)
    high = make_continuous_event("HEALTH_WARNING", source="test", session_id="continuous-events", payload={"b": 2}, priority=90)

    controller = enqueue_continuous_event(controller, low)
    controller = enqueue_continuous_event(controller, high)
    controller = enqueue_continuous_event(controller, high)
    assert len(controller.event_queue) == 2
    assert controller.event_queue[0].event_type == "HEALTH_WARNING"

    controller = run_controller_cycle(controller)
    assert high.event_id in controller.processed_event_ids
    assert low.event_id in controller.processed_event_ids
    assert controller.lifecycle_state == "IDLE"


def test_model_residency_policy_uses_actual_registry_and_serial_limit():
    controller = start_continuous_runtime_controller(session_id="continuous-models")
    residency = controller.model_residency

    assert residency.available_model_count >= 1
    assert residency.max_resident_models == 1
    assert residency.serial_residency is True
    assert residency.selected_default_model
    assert residency.selected_planning_model
    assert residency.selected_development_model


def test_live_runtime_wikipedia_feeds_controller_initiative_and_objective():
    session = start_live_wikipedia_runtime(runtime_id="continuous-live")
    session, response = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)

    assert response.route == "live_wikipedia_text_retrieval"
    assert session.continuous_controller is not None
    snapshot = controller_snapshot(session.continuous_controller)
    assert snapshot["initiative_count"] >= 1
    assert snapshot["active_objective"] is not None
    assert snapshot["wikipedia_available"] is True
    assert snapshot["health"]["health_state"] == "HEALTHY"


def test_pause_resume_suspend_and_shutdown_are_explicit():
    controller = start_continuous_runtime_controller(session_id="continuous-controls")

    paused = pause_controller(controller)
    assert paused.lifecycle_state == "PAUSED"
    assert paused.health.health_state == "PAUSED_FOR_REVIEW"

    resumed = resume_controller(paused)
    assert resumed.lifecycle_state == "IDLE"

    suspended = suspend_controller(resumed)
    assert suspended.lifecycle_state == "SUSPENDED"
    assert suspended.health.health_state == "SUSPENDED"

    shutdown = shutdown_controller(suspended)
    assert shutdown.lifecycle_state == "SHUTDOWN"
    assert not shutdown.event_queue


def test_bounded_long_run_has_no_model_or_wikipedia_call_storm():
    controller = start_continuous_runtime_controller(session_id="continuous-long-run")
    controller, metrics = run_bounded_long_run(controller, cycles=25)

    assert metrics["cycles_completed"] == 25
    assert metrics["max_queue_size"] <= controller.config.queue_limit
    assert metrics["model_calls"] == 0
    assert metrics["wikipedia_calls"] == 0
    assert metrics["duplicate_initiatives"] == 0
    assert metrics["hidden_threads_created"] is False
    assert metrics["hidden_memory_writes"] is False
    assert metrics["health_state"] == "HEALTHY"


def test_self_development_demo_stops_at_promotion_boundary():
    demo = build_self_development_demo()

    assert demo["status"] == "FIXTURE_VALIDATED"
    assert demo["authority_classification"] == "AUTONOMOUS_SAFE"
    assert demo["automatic_promotion_performed"] is False
    assert demo["runtime_primary_tree_mutation"] is False
    assert demo["sandbox_proposal"]["promotion_performed"] is False


def test_report_payload_classifies_capabilities_and_recommendation():
    controller = start_continuous_runtime_controller(session_id="continuous-report")
    controller, metrics = run_bounded_long_run(controller, cycles=5)
    payload = build_report_payload(
        controller=controller,
        long_run_metrics=metrics,
        validation={"status": "TEST_ONLY"},
        self_development=build_self_development_demo(),
    )

    assert payload["active_runtime_spine"]["capability_classification"]["delta_1_2_live_runtime"] == "LIVE"
    assert payload["readiness"]["recommendation"] == "CONTINUOUS_RUNTIME_READY_FOR_CONTROLLED_OPERATOR_PILOT"

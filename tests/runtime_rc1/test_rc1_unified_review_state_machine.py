from orchestration.runtime.rc1_unified_review_state_machine import build_unified_lifecycle, write_state_machine_report


def test_unified_state_machine_covers_review_to_disabled_integration():
    lifecycle = build_unified_lifecycle()
    states = set(lifecycle.states)
    assert "draft" in states
    assert "admin_approved" in states
    assert "ready_to_integrate" in states
    assert lifecycle.current_state == "integrated_disabled"


def test_unified_state_machine_blocks_live_integration_write():
    lifecycle = build_unified_lifecycle()
    blocked = [transition for transition in lifecycle.transitions if transition.target_state == "integrated_disabled"][0]
    assert blocked.allowed is False
    assert blocked.live_write_performed is False
    assert lifecycle.integrated is False
    assert lifecycle.mutation_performed is False


def test_unified_state_machine_report_recommends_artifact_registry():
    report = write_state_machine_report()
    assert report["final_recommendation"] == "PROCEED_CENTRAL_RUNTIME_ARTIFACT_REGISTRY"
    assert report["estimated_runtime_maturity"] >= 93
    assert report["safety"]["rollback_available"] is True

from orchestration.runtime.rc1_wave_3_simulated_substrate_writes import (
    AdminApprovalEvent,
    OverwatchReview,
    build_candidate,
    simulate_substrate_write,
    write_wave_3_report,
)


def test_wave_3_rejects_unapproved_candidate():
    report = simulate_substrate_write(None, OverwatchReview("allow", "ok"))
    assert report["simulated_delta"] is None
    assert report["write_performed"] is False


def test_wave_3_approved_overwatch_allowed_creates_simulated_delta_only():
    candidate = build_candidate()
    report = simulate_substrate_write(
        AdminApprovalEvent(candidate["candidate_id"], "user", "single_memory_candidate_only"),
        OverwatchReview("allow", "ok"),
    )
    assert report["simulated_write"] is True
    assert report["simulated_delta"]["rollback_token"]
    assert report["write_performed"] is False
    assert report["safety"]["knowledge_mutation_performed"] is False


def test_wave_3_report_generation():
    report = write_wave_3_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_4_ROLLBACK_EVALUATION"

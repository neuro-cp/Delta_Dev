from orchestration.runtime.rc1_wave_4_rollback_evaluation import run_rollback_evaluation, write_wave_4_report


def test_wave_4_simulated_rollback_restores_pre_state():
    report = run_rollback_evaluation()
    assert report["rollback_simulated"] is True
    assert report["live_rollback_performed"] is False
    assert report["restored_pre_state"] is True
    assert report["health_delta"]["regression_detected"] is False


def test_wave_4_report_generation():
    report = write_wave_4_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_5_PROVIDER_EVIDENCE_SIMULATED"

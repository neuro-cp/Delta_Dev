from orchestration.runtime.rc1_wave_5_provider_evidence_simulated import simulate_provider_evidence, write_wave_5_report


def test_wave_5_provider_response_is_simulated_and_advisory():
    report = simulate_provider_evidence(approved=True)
    assert report["provider_call_performed"] is False
    assert report["simulated_provider_response"] is True
    assert report["provider_response_envelope"]["advisory_only"] is True
    assert report["authority_granted"] is False


def test_wave_5_unapproved_request_has_no_response():
    report = simulate_provider_evidence(approved=False)
    assert report["simulated_provider_response"] is False
    assert report["provider_response_envelope"] is None


def test_wave_5_report_generation():
    report = write_wave_5_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_6_LIVE_CORPUS_PILOT_PLAN"

from orchestration.runtime.rc1_wave_0_manual_validation import build_wave_0_manual_validation, write_wave_0_report


def test_wave_0_manual_validation_passes_and_enables_nothing():
    report = build_wave_0_manual_validation()
    assert report["passed"] is True
    assert report["live_capabilities_enabled"] is False
    assert report["safety"]["provider_call_performed"] is False
    assert report["safety"]["knowledge_mutation_performed"] is False


def test_wave_0_report_generation():
    report = write_wave_0_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_1_FIXTURE_CORPUS_INGESTION"

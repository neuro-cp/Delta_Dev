from orchestration.runtime.rc1_wave_chain_summary import build_wave_chain_summary, write_wave_chain_summary


def test_wave_chain_summary_records_all_waves_and_blockers():
    summary = build_wave_chain_summary()
    assert summary["waves_completed"] == 8
    assert summary["fixture_corpus_ingestion_works"] is True
    assert summary["provider_evidence_remains_simulated"] is True
    assert "real provider calls" in summary["still_blocked_capabilities"]
    assert summary["safety"]["knowledge_mutation_performed"] is False


def test_wave_chain_summary_report_generation():
    summary = write_wave_chain_summary()
    assert summary["final_recommendation"] == "PROCEED_MANUAL_RC1_WAVE_CHAIN_REVIEW"

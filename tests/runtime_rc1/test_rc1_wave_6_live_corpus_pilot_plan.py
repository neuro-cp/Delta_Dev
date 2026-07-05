from orchestration.runtime.rc1_wave_6_live_corpus_pilot_plan import build_live_corpus_pilot_plan, write_wave_6_report


def test_wave_6_live_corpus_pilot_remains_disabled():
    plan = build_live_corpus_pilot_plan()
    assert plan["activation_enabled"] is False
    assert plan["dry_run_only"] is True
    assert ".txt" in plan["allowed_file_types"]
    assert plan["safety"]["live_arbitrary_ingestion_performed"] is False
    assert plan["live_activation_blockers"]


def test_wave_6_report_generation():
    report = write_wave_6_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_7_LEARNING_CONSOLIDATION_PILOT_PLAN"

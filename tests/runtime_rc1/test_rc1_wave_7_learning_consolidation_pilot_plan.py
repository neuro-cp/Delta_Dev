from orchestration.runtime.rc1_wave_7_learning_consolidation_pilot_plan import (
    build_learning_consolidation_pilot_plan,
    write_wave_7_report,
)


def test_wave_7_learning_consolidation_remains_disabled():
    plan = build_learning_consolidation_pilot_plan()
    assert plan["learning_enabled"] is False
    assert plan["consolidation_enabled"] is False
    assert plan["canonical_write_enabled"] is False
    assert plan["safety"]["training_performed"] is False
    assert plan["activation_blockers"]


def test_wave_7_report_generation():
    report = write_wave_7_report()
    assert report["final_recommendation"] == "PROCEED_RC1_WAVE_CHAIN_MANUAL_REVIEW"

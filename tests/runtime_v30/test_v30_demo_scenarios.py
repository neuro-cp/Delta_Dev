from scripts.delta_v30_demo_scenarios import SCENARIOS, run_demo_scenarios


def test_v30_demo_scenarios_cover_required_cases():
    data = run_demo_scenarios()
    scenario_ids = {item["scenario_id"] for item in data["scenarios"]}
    assert data["scenario_count"] == 8
    assert scenario_ids == {scenario[0] for scenario in SCENARIOS}


def test_v30_demo_scenarios_do_not_perform_side_effects():
    data = run_demo_scenarios()
    for scenario in data["scenarios"]:
        assert scenario["provider_call_performed"] is False
        assert scenario["memory_write_performed"] is False
        assert scenario["training_triggered"] is False
        assert scenario["action_execution_performed"] is False

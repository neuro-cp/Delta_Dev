from integration.ai_surface.ai_role_declaration import AIRole

def test_roles_exist():
    assert AIRole.STRATEGIC_DEFENSE_ADVISOR.value == "strategic_defense_advisor"
    assert AIRole.SIMULATION_EVALUATOR.value == "simulation_evaluator"
    assert AIRole.CIVILIAN_POLICY_MODEL.value == "civilian_policy_model"

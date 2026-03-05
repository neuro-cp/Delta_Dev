from integration.ai_surface.ai_mode_declaration import AIMode

def test_modes_exist():
    assert AIMode.ACTIVE.value == "active"
    assert AIMode.PASSIVE.value == "passive"
    assert AIMode.INTEGRATIVE_EVALUATIVE.value == "integrative_evaluative"

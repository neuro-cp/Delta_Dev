from integration.substrate_surface.role_matrix import RoleMatrix


def test_role_matrix_restricts_targets():
    targets = RoleMatrix.allowed_targets("simulation_evaluator")

    assert "VALUE_BIAS" in targets
    assert "PFC_CONTEXT_GAIN" not in targets

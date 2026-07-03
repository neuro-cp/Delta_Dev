from orchestration.runtime.v29_natural_alias_router import build_alias_router_report, route_v29_alias, validate_alias_router_safe


def test_natural_aliases_match_current_state_topics():
    assert route_v29_alias("What is DELTA?").topic_id == "identity"
    assert route_v29_alias("What can you do?").topic_id == "capabilities_active"
    assert route_v29_alias("Explain yourself.").topic_id == "identity"
    assert route_v29_alias("Describe your architecture.").topic_id == "architecture"
    assert route_v29_alias("What phase are you in?").topic_id == "phase_state"
    assert route_v29_alias("Can you train?").topic_id == "training_status"
    assert route_v29_alias("Is HYB1 active?").topic_id == "hyb1_status"


def test_alias_router_report_is_safe():
    data = build_alias_router_report()

    assert validate_alias_router_safe(data)
    assert data["all_samples_matched"] is True
    assert all(value is False for value in data["safety_invariants"].values())

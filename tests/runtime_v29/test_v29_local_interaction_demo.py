from scripts.delta_v29_local_interaction_demo import build_demo


def test_local_interaction_demo_matches_expected_questions_and_leaves_breakfast_unknown():
    data = build_demo()

    assert data["phase"] == "Runtime V2.9E"
    assert data["matched_count"] == 9
    assert data["unsupported_count"] == 1
    assert data["answers"][-1]["local_answer"]["topic_id"] == "unsupported"
    assert all(value is False for value in data["safety_invariants"].values())

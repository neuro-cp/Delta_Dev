import tkinter as tk

from orchestration.runtime.goal_oriented_ui_campaign import (
    begin_follow_up,
    launch_experiment,
    protected_path,
    read_experiment_state,
    validate_candidates,
)


def _proposal(experiment_id="exp-a"):
    return {
        "experiment_id": experiment_id,
        "title": "Diagnose active cognition UI visibility",
        "practical_objective": "Find whether active cognition state is visible through the Tk operator path.",
        "why_it_is_useful": "The campaign requires operator-visible cognition, not hidden helper execution.",
        "related_operator_or_project_goal": "GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1",
        "expected_artifact_or_outcome": "A bounded UI diagnosis artifact.",
        "local_evidence_available": [
            {"path": "DELTA.py", "note": "Tk application and Goals tab implementation."},
            {"path": "orchestration/runtime/active_cognitive_loop.py", "note": "Active cognition state model."},
        ],
        "contrary_or_uncertainty_evidence": [
            {"path": "operator:ui_gap", "note": "Existing active cognition controls were chat-command oriented."},
        ],
        "required_cognitive_operations": ["formulate_hypothesis", "compare_evidence", "summarize_learning"],
        "required_bounded_actions": ["inspect local source", "produce diagnosis"],
        "required_authority": "operator_authorized_goal_oriented_ui_experiment_campaign_1",
        "expected_cycle_count": 3,
        "restart_relevance": "Useful for restart display if selected.",
        "success_criteria": "Artifact cites visible UI state and local evidence.",
        "failure_criteria": "No inspectable UI state or artifact.",
        "risk_and_scope": "Read-only diagnosis outside protected paths.",
        "estimated_time_and_model_call_budget": "3 cycles, 3 model calls",
    }


def test_candidate_validation_rejects_protected_dependency():
    candidate = _proposal()
    candidate["local_evidence_available"] = [
        {"path": "orchestration/runtime/live_competence_adapter.py", "note": "protected"}
    ]

    assert protected_path("orchestration/runtime/live_competence_adapter.py")
    assert validate_candidates([candidate]) == []


def test_launch_experiment_writes_operator_visible_state(tmp_path, monkeypatch):
    import orchestration.runtime.goal_oriented_ui_campaign as campaign

    monkeypatch.setattr(campaign, "CAMPAIGN_ROOT", tmp_path)
    state = launch_experiment(_proposal("exp-a"))

    assert state.title == "Diagnose active cognition UI visibility"
    assert (tmp_path / "experiment-a" / "ui_launch_evidence.json").exists()
    assert (tmp_path / "experiment-a" / "ui_state_snapshots.json").exists()
    assert read_experiment_state("exp-a").episode_id == state.episode_id


def test_delta_goal_campaign_panel_is_visible_without_model_call(monkeypatch):
    import DELTA

    monkeypatch.setattr(DELTA.DeltaApp, "_warm_default_model", lambda self: None)
    monkeypatch.setattr(DELTA, "read_goal_ui_campaign_json", lambda _path, default=None: default)
    root = tk.Tk()
    try:
        app = DELTA.DeltaApp(root)
        root.update()
        assert set(app.goal_ui_campaign_buttons) == {
            "formulate",
            "select",
            "launch",
            "cycle",
            "pause",
            "resume",
            "restart",
            "follow",
        }
        assert "GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1" in app.goal_ui_campaign_status.get()
    finally:
        root.destroy()


def test_begin_follow_up_reopens_completed_episode(tmp_path, monkeypatch):
    import orchestration.runtime.goal_oriented_ui_campaign as campaign

    monkeypatch.setattr(campaign, "CAMPAIGN_ROOT", tmp_path)
    state = launch_experiment(_proposal("exp-d"))
    state = campaign.replace(state, completed=True, loop_state="completed")
    campaign.write_episode_state(tmp_path / "experiment-d" / "state.json", state)
    observed = {}

    def fake_cycle(experiment_id, provider_manager, *, requested_operation=None):
        reopened = read_experiment_state(experiment_id)
        observed["completed_before_follow_up_cycle"] = reopened.completed
        observed["requested_operation"] = requested_operation
        return reopened

    monkeypatch.setattr(campaign, "run_experiment_cycle", fake_cycle)
    begin_follow_up("exp-d", provider_manager=object())

    assert observed == {
        "completed_before_follow_up_cycle": False,
        "requested_operation": "select_next_focus",
    }

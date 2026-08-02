from pathlib import Path

import DELTA
from orchestration.runtime.cognitive_claim_relation_runtime import GovernedClaimRelationRuntime


def _delta_shell(tmp_path, *, enabled=False):
    app = object.__new__(DELTA.DeltaApp)
    app.session_history = []
    app.claim_relation_pilot = GovernedClaimRelationRuntime(tmp_path / "state.json", enabled=enabled)
    return app


def test_delta_claim_relation_hook_is_disabled_path_equivalent(tmp_path):
    app = _delta_shell(tmp_path, enabled=False)
    assert app._apply_claim_relation_pilot("My appointment is Tuesday.") == ""
    assert app.session_history == []
    assert not (tmp_path / "state.json").exists()


def test_delta_claim_relation_hook_uses_explicit_local_activation(tmp_path):
    app = _delta_shell(tmp_path, enabled=False)
    app.claim_relation_pilot.set_enabled(True)
    assert app._apply_claim_relation_pilot("My appointment is Tuesday.") == "Recorded as a governed current claim."
    result = app._apply_claim_relation_pilot("Correction: my appointment is Wednesday.")
    assert result == "Updated: the previous claim is preserved as superseded."
    assert (tmp_path / "state.json").exists()
    assert len(app.claim_relation_pilot.bundle.relations) == 1


def test_delta_claim_relation_hook_defers_unsupported_semantic_conflict(tmp_path):
    app = _delta_shell(tmp_path, enabled=True)
    app._apply_claim_relation_pilot("The database is PostgreSQL.")
    result = app._apply_claim_relation_pilot("The database is SQLite.")
    assert result == "This may conflict with an earlier claim, but semantic classification is not enabled in this pilot."
    assert app.claim_relation_pilot.bundle.relations == ()


def test_delta_claim_relation_pilot_state_path_is_not_tmp_dependent():
    app = object.__new__(DELTA.DeltaApp)
    app.session_history = []
    app.claim_relation_pilot = GovernedClaimRelationRuntime(
        Path(DELTA.ROOT) / "data" / "runtime" / "claim_relation_pilot" / "state.json",
        enabled=False,
    )
    assert ".tmp" not in str(app.claim_relation_pilot.state_path).replace("\\", "/")


def test_delta_active_cognitive_loop_starts_and_reports_persistent_state(tmp_path):
    app = object.__new__(DELTA.DeltaApp)
    app.active_cognitive_loop_state_path = tmp_path / "active_loop_state.json"
    app.active_cognitive_loop_state = None

    started = app._start_active_cognitive_loop()
    status = app._active_cognitive_loop_status()

    assert "Active cognitive loop started" in started
    assert app.active_cognitive_loop_state_path.exists()
    assert "cycles=0" in status
    assert "model_calls=0" in status

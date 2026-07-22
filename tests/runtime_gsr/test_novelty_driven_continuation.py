from __future__ import annotations

import json
import sqlite3

import pytest

from orchestration.runtime.novelty_driven_continuation import (
    compile_campaign_state,
    run_campaign_runtime,
)


def _planner(path):
    path.write_text(json.dumps({
        "package_digest": "planner-digest",
        "initial_ranking": (
            {"label": "alpha", "score": 0.9},
            {"label": "beta", "score": 0.8},
        ),
        "blocked_branches": (),
    }), encoding="utf-8")


def _trusted(path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE trusted_formal_primitives (primitive_id TEXT, canonical_label TEXT, admitted_status TEXT, admission_review_digest TEXT)"
        )
        connection.execute("INSERT INTO trusted_formal_primitives VALUES ('valid', 'constraint', 'admitted', 'review')")
        connection.execute("INSERT INTO trusted_formal_primitives VALUES ('bad', 'necessary_condition', 'invalid_noncanonical_excluded', 'failed')")


def _legacy(path):
    path.write_text(json.dumps({
        "records": ({
            "frontier": {"label": "alpha", "score": 0.9},
            "status": "deferred_no_new_information",
            "routes": ({"route": "wikimedia_reference", "query": "alpha relation", "attempt": {"status": "blocked"}},),
        },),
    }), encoding="utf-8")


def test_import_excludes_quarantine_and_runtime_consumes_remaining_frontier(tmp_path):
    planner = tmp_path / "planner.json"; trusted = tmp_path / "trusted.sqlite"; legacy = tmp_path / "legacy.json"
    _planner(planner); _trusted(trusted); _legacy(legacy)
    state = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=(legacy,))
    calls = []

    def executor(frontier, _state, _workspace):
        calls.append(frontier["label"])
        return {"status": "deferred_no_new_information", "operational_contract": {"subject": frontier["label"]}, "route_outcomes": ({"route": "openalex_works", "outcome": "blocked"},)}

    result = run_campaign_runtime(state=state, workspace=tmp_path / "runtime", route_executor=executor)
    assert calls == ["beta"]
    assert result["terminal_status"] == "NOVELTY_DRIVEN_CONTINUATION_NO_NEW_INFORMATION"
    assert result["excluded_trusted_records"][0]["primitive_id"] == "bad"
    assert next(item for item in result["frontiers"] if item["label"] == "alpha")["status"] == "deferred_no_new_information"


def test_restart_reuses_terminal_state_without_duplicate_dispatch(tmp_path):
    planner = tmp_path / "planner.json"; trusted = tmp_path / "trusted.sqlite"; _planner(planner); _trusted(trusted)
    state = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=())
    calls = []
    def executor(frontier, _state, _workspace):
        calls.append(frontier["label"])
        return {"status": "deferred_no_new_information", "route_outcomes": ()}
    first = run_campaign_runtime(state=state, workspace=tmp_path / "runtime", route_executor=executor)
    second = run_campaign_runtime(state=state, workspace=tmp_path / "runtime", route_executor=lambda *_: (_ for _ in ()).throw(AssertionError("replayed")))
    assert first["artifact_digest"] == second["artifact_digest"]
    assert calls == ["alpha", "beta"]


def test_source_grounding_stops_at_sealed_evaluator_boundary(tmp_path):
    planner = tmp_path / "planner.json"; trusted = tmp_path / "trusted.sqlite"; _planner(planner); _trusted(trusted)
    state = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=())
    result = run_campaign_runtime(
        state=state,
        workspace=tmp_path / "runtime",
        route_executor=lambda *_: {"status": "source_grounded_pending_evaluation", "route_outcomes": ()},
    )
    assert result["terminal_status"] == "NOVELTY_DRIVEN_CONTINUATION_INTEGRITY_STOP"
    assert "sealed evaluator" in result["terminal_reason"]


def test_declared_terminal_without_route_evidence_fails_closed(tmp_path):
    planner = tmp_path / "planner.json"; trusted = tmp_path / "trusted.sqlite"; legacy = tmp_path / "legacy.json"
    _planner(planner); _trusted(trusted)
    legacy.write_text(json.dumps({"prior_terminal_labels": ["alpha"]}), encoding="utf-8")
    state = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=(legacy,))
    result = run_campaign_runtime(
        state=state,
        workspace=tmp_path / "runtime",
        route_executor=lambda *_: (_ for _ in ()).throw(AssertionError("replayed")),
    )
    assert result["terminal_status"] == "NOVELTY_DRIVEN_CONTINUATION_INTEGRITY_STOP"
    assert result["import_integrity_blockers"][0]["label"] == "alpha"


def test_import_rejects_artifact_drift_by_digest_bound_state(tmp_path):
    planner = tmp_path / "planner.json"; trusted = tmp_path / "trusted.sqlite"; legacy = tmp_path / "legacy.json"
    _planner(planner); _trusted(trusted); _legacy(legacy)
    state = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=(legacy,))
    run_campaign_runtime(
        state=state,
        workspace=tmp_path / "runtime",
        route_executor=lambda *_: {"status": "deferred_no_new_information"},
    )
    legacy.write_text("{}", encoding="utf-8")
    changed = compile_campaign_state(planner_package_path=planner, trusted_layer=trusted, evidence_artifacts=(legacy,))
    assert state["state_digest"] != changed["state_digest"]
    with pytest.raises(ValueError, match="input_mismatch"):
        run_campaign_runtime(state=changed, workspace=tmp_path / "runtime", route_executor=lambda *_: {"status": "deferred_no_new_information"})

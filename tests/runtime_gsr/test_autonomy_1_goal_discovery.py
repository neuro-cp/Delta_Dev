from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_goal_discovery import (
    AUTONOMY_1_NO_GOAL_STATUS,
    AUTONOMY_1_STATUS,
    classify_evidence_signal,
    collect_runtime_evidence,
    compile_goal_approval_request,
    compile_goal_proposal,
    discover_goal_candidates,
    persist_autonomy_1_goal_discovery,
    rank_goal_candidates,
    score_goal_candidate,
)

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


class _DummyProviderManager:
    def __init__(self, keep_loaded: bool = True) -> None:
        self.keep_loaded = keep_loaded

    def warm(self, _model_id: str) -> None:
        return None


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _counter(root: Path, name: str, **payload: object) -> Path:
    record = {
        "schema": "autonomy_1_counterfactual_evidence_v1",
        "artifact_id": name,
        "artifact_digest": f"{name}-digest",
        "signal_type": "irrelevant_noise",
        "condition_key": "noise",
        "exact_unresolved_condition": "",
        "observed_summary": "",
        "expected_operator_value": 5,
        "prerequisite_readiness": 5,
        "estimated_cost": 5,
        "risk": 5,
        "reversibility": 8,
        **payload,
    }
    path = root / f"{name}.json"
    _write(path, record)
    return root


def _current_reconciliation_roots(root: Path) -> tuple[Path, ...]:
    old = root / "old"
    current = root / "current"
    _counter(
        old,
        "missing-reconciliation",
        signal_type="missing_capability",
        condition_key="cross_format_record_reconciliation",
        exact_unresolved_condition="no accepted cross-format reconciliation capability existed",
        observed_summary="A mission blocked reconciliation as missing capability.",
        existing_capability_lookup="missing",
        expected_operator_value=7,
    )
    _counter(
        current,
        "stable-identifier-adjacent",
        signal_type="useful_adjacent_capability",
        condition_key="missing_or_unreliable_identifier_reconciliation",
        exact_unresolved_condition="retained reconciliation competence depends on declared stable identifiers",
        observed_summary="Accepted adjacent competence works only by stable identifier.",
        existing_capability_lookup="adjacent_only",
        expected_operator_value=9,
        prerequisite_readiness=8,
        estimated_cost=7,
        risk=6,
    )
    _counter(
        current,
        "stable-identifier-resolved",
        signal_type="accepted_capability",
        condition_key="stable_identifier_reconciliation",
        exact_unresolved_condition="stable identifier reconciliation resolved",
        observed_summary="Accepted competence resolves stable identifier reconciliation.",
        resolves_conditions=("cross_format_record_reconciliation", "stable_identifier_reconciliation"),
        existing_capability_lookup="accepted",
    )
    return (old, current)


def test_signal_extraction_and_noise_classification_are_distinct():
    assert classify_evidence_signal({"decision": "missing_capability", "task_class": "cross_format_record_reconciliation"}) == "missing_capability"
    assert classify_evidence_signal({"reconciliation": {"status": "rejected_by_operator"}}) == "unresolved_failure"
    assert classify_evidence_signal({"aggregate_status": "failed"}) == "weak_evaluation_result"
    assert classify_evidence_signal({"notes": "blocked duplicate route repeatedly requeued after cycle budget without_distinct strategy"}) == "recurring_inefficiency"
    assert classify_evidence_signal({"schema": "live_general_3_developmental_reconciliation_competence_v1"}) == "useful_adjacent_capability"
    assert classify_evidence_signal({"schema": "unrelated_v1", "status": "ok"}) == "irrelevant_noise"


def test_case_a_current_reconciliation_limitation_is_proposed_from_bound_evidence(tmp_path):
    proposal = compile_goal_proposal(_current_reconciliation_roots(tmp_path))
    goal = proposal["recommended_goal"]

    assert proposal["status"] == AUTONOMY_1_STATUS
    assert "stable identifiers are missing or unreliable" in goal["goal"]
    assert "stable identifiers" in goal["unresolved_limitation"]
    assert goal["score"]["score_components"]["recency"] > 0
    assert goal["score"]["score_components"]["expected_operator_value"] == 9
    assert all(ref["source_artifact_digest"] for ref in goal["evidence_refs"])
    assert "urgent" not in json.dumps(proposal).lower()


def test_case_b_different_capability_gap_changes_goal(tmp_path):
    root = tmp_path / "different"
    _counter(
        root,
        "pdf-gap",
        signal_type="missing_capability",
        condition_key="pdf_table_extraction",
        exact_unresolved_condition="PDF table extraction is unsupported for retained mission artifacts",
        observed_summary="A retained mission could not extract tables from a PDF artifact.",
        expected_operator_value=8,
    )
    proposal = compile_goal_proposal((root,))

    assert proposal["status"] == AUTONOMY_1_STATUS
    assert "pdf table extraction" in proposal["recommended_goal"]["goal"]
    assert "reconciliation" not in proposal["recommended_goal"]["goal"].lower()


def test_cases_c_and_d_clean_or_noise_only_do_not_manufacture_goals(tmp_path):
    clean = tmp_path / "clean"
    _write(clean / "terminal.json", {"schema": "terminal_v1", "status": "terminal", "artifact_digest": "clean"})
    noise = tmp_path / "noise"
    _counter(noise, "noise", signal_type="irrelevant_noise", condition_key="noise", observed_summary="temporary status snapshot")

    assert compile_goal_proposal((clean,))["status"] == AUTONOMY_1_NO_GOAL_STATUS
    assert compile_goal_proposal((noise,))["status"] == AUTONOMY_1_NO_GOAL_STATUS


def test_cases_e_and_h_existing_current_competence_suppresses_stale_gap(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    _counter(
        old,
        "old-gap",
        signal_type="missing_capability",
        condition_key="schema_drift_detection",
        exact_unresolved_condition="schema drift detection was missing",
        observed_summary="Old evidence reported a schema drift gap.",
    )
    _counter(
        new,
        "accepted",
        signal_type="accepted_capability",
        condition_key="schema_drift_detection",
        exact_unresolved_condition="schema drift detection is accepted",
        observed_summary="New evidence accepts the capability.",
        resolves_conditions=("schema_drift_detection",),
        existing_capability_lookup="accepted",
    )
    proposal = compile_goal_proposal((old, new))

    assert proposal["status"] == AUTONOMY_1_NO_GOAL_STATUS
    suppressed = proposal["suppression_outcomes"][0]
    assert suppressed["suppression_reason"] == "already_resolved_by_accepted_competence"
    assert suppressed["resolved_by"]["source_artifact_id"] == "accepted"


def test_case_f_duplicate_evidence_yields_one_candidate_with_recurrence(tmp_path):
    roots = []
    for index in range(3):
        root = tmp_path / f"dup-{index}"
        _counter(
            root,
            f"dup-{index}",
            signal_type="missing_capability",
            condition_key="record_conflict_explanation",
            exact_unresolved_condition="record conflict explanations are incomplete",
            observed_summary="The same unresolved limitation recurred.",
            expected_operator_value=7,
        )
        roots.append(root)
    candidates = discover_goal_candidates(tuple(roots))
    proposal = compile_goal_proposal(tuple(roots))

    assert len(candidates) == 1
    assert proposal["recommended_goal"]["recurrence_count"] == 3
    assert proposal["recommended_goal"]["score"]["score_components"]["recurrence"] == 3


def test_case_g_competing_goals_rank_higher_value_first_and_retain_alternatives(tmp_path):
    high = tmp_path / "high"
    low = tmp_path / "low"
    noise = tmp_path / "noise"
    _counter(
        high,
        "high",
        signal_type="missing_capability",
        condition_key="cross_source_conflict_resolution",
        exact_unresolved_condition="cross-source conflict resolution is missing",
        observed_summary="A high-value mission could not resolve conflicts across sources.",
        expected_operator_value=10,
        prerequisite_readiness=8,
        estimated_cost=8,
        risk=8,
    )
    _counter(
        low,
        "low",
        signal_type="weak_evaluation_result",
        condition_key="rare_export_format",
        exact_unresolved_condition="rare export format evaluation was weak",
        observed_summary="A low-value rare export case was weak.",
        expected_operator_value=2,
        prerequisite_readiness=2,
        estimated_cost=2,
        risk=2,
    )
    _counter(noise, "noise", signal_type="irrelevant_noise", condition_key="noise", observed_summary="irrelevant")
    proposal = compile_goal_proposal((high, low, noise))

    assert proposal["recommended_goal"]["condition_key"] == "cross_source_conflict_resolution"
    assert proposal["alternatives"][0]["condition_key"] == "rare_export_format"
    assert "noise" not in json.dumps(proposal["candidates"]).lower()


def test_score_and_proposal_digests_are_deterministic(tmp_path):
    roots = _current_reconciliation_roots(tmp_path)
    first = compile_goal_proposal(roots)
    second = compile_goal_proposal(roots)
    score = score_goal_candidate(first["recommended_goal"])

    assert first["artifact_digest"] == second["artifact_digest"]
    assert score["score_components"] == first["recommended_goal"]["score"]["score_components"]


def test_one_operator_request_and_proposal_only_boundaries(tmp_path):
    output = tmp_path / "out"
    result1 = persist_autonomy_1_goal_discovery(evidence_roots=_current_reconciliation_roots(tmp_path / "evidence"), output_root=output)
    result2 = persist_autonomy_1_goal_discovery(evidence_roots=_current_reconciliation_roots(tmp_path / "evidence"), output_root=output)
    requests = tuple((output / "operator_request").glob("*.json"))

    assert len(requests) == 1
    assert result1["operator_request"]["request_id"] == result2["operator_request"]["request_id"]
    assert result1["provider_calls"] == 0
    assert result1["learning_attempts_started"] == 0
    assert result1["trusted_admission"] is False
    assert result1["capability_promotion"] is False
    assert compile_goal_approval_request(result1["proposal"])["learning_attempts"] == 0


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    app.operator_ux_root = tmp_path / "operator-ux"
    root.update()
    return root, app


def _send(app: DELTA.DeltaApp, root: tk.Tk, message: str) -> None:
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, message)
    app._send_chat()
    root.update()


def test_real_tk_style_pilot_explain_alternatives_approve_restart_no_execution(monkeypatch, tmp_path):
    evidence_roots = _current_reconciliation_roots(tmp_path / "evidence")

    def _fake_discovery(*, evidence_roots, output_root):
        return persist_autonomy_1_goal_discovery(evidence_roots=evidence_roots, output_root=tmp_path / "autonomy")

    monkeypatch.setattr(DELTA, "persist_autonomy_1_goal_discovery", _fake_discovery)
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "discover next goal")
        assert app.active_operator_ux_request is not None
        assert app.operator_ux_request_card["title"] == "I found a possible next goal"
        request_id = app.active_operator_ux_request["request_id"]
        assert len(app.operator_ux_goal_cards) == 1

        _send(app, root, "explain")
        assert app.active_operator_ux_request is not None
        app._handle_operator_ux_button("show_alternatives")
        root.update()
        assert "Grounded alternatives" in app.chat_history.get("1.0", tk.END)

        _send(app, root, "approve")
        assert app.active_operator_ux_request is None
        consumed = tuple((app.operator_ux_root / "consumed_responses").glob("*.json"))
        approved = tuple((app.operator_ux_root / "approved_goals").glob("*.json"))
        assert len(consumed) == 1
        assert len(approved) == 1
        consumed_record = json.loads(consumed[0].read_text(encoding="utf-8"))
        approved_record = json.loads(approved[0].read_text(encoding="utf-8"))
        assert consumed_record["request_id"] == request_id
        assert approved_record["execution_started"] is False
        assert approved_record["learning_started"] is False
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass

    recovered_root, recovered = _app(monkeypatch, tmp_path)
    try:
        recovered.operator_ux_root = tmp_path / "operator-ux"
        recovered._refresh_operator_ux_views()
        assert recovered.active_operator_ux_request is None
        before = set(recovered.operator_ux_narration_events)
        recovered._refresh_operator_ux_views()
        assert before == set(recovered.operator_ux_narration_events)
    finally:
        try:
            recovered_root.destroy()
        except tk.TclError:
            pass

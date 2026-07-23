from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_goal_prioritization import (
    AUTONOMY_2_NO_GOAL_STATUS,
    AUTONOMY_2_STATUS,
    compile_ranking,
    discover_prioritization_candidates,
    normalize_selection,
    persist_prioritization,
    persist_selection,
    score_candidate,
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


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path.parent


def _goal(root: Path, name: str, **overrides: object) -> Path:
    record = {
        "schema": "autonomy_2_counterfactual_goal_evidence_v1",
        "artifact_id": name,
        "artifact_digest": f"{name}-digest",
        "signal_type": "unresolved_capability_gap",
        "condition_key": name,
        "title": name.replace("_", " ").title(),
        "objective": f"Improve {name.replace('_', ' ')}.",
        "unresolved_condition": f"{name} remains unresolved",
        "current_capability_state": "unresolved",
        "prerequisites": ("retained evidence",),
        "missing_prerequisites": (),
        "estimated_work_class": "bounded_developmental_goal",
        "expected_benefit": 6,
        "operator_relevance": 6,
        "urgency": 1,
        "evidence_strength": 6,
        "readiness": 6,
        "estimated_cost": 4,
        "risk": 4,
        "reversibility": 8,
        "recurrence": 1,
        "authority_requirements": (),
        **overrides,
    }
    return _write(root / f"{name}.json", record)


def test_case_a_three_legitimate_goals_rank_and_retain_alternatives(tmp_path):
    high = _goal(tmp_path / "high", "reliable_identifier_transfer", expected_benefit=10, operator_relevance=9, readiness=9, estimated_cost=2, risk=2)
    costly = _goal(tmp_path / "costly", "broad_pdf_reconciliation", expected_benefit=8, readiness=5, estimated_cost=8, risk=5, missing_prerequisites=("pdf parser",))
    maintenance = _goal(tmp_path / "maint", "operator_summary_cleanup", expected_benefit=4, operator_relevance=5, readiness=9, estimated_cost=1, risk=1)
    ranking = compile_ranking(evidence_roots=(high, costly, maintenance))

    assert ranking["status"] == AUTONOMY_2_STATUS
    assert len(ranking["candidates"]) == 3
    assert ranking["recommended_candidate"]["condition_key"] == "reliable_identifier_transfer"
    assert len(ranking["alternatives"]) == 2
    assert "score_formula" in ranking["recommended_candidate"]["score"]


def test_case_b_cost_versus_benefit_and_preference_changes_rank(tmp_path):
    high_cost = _goal(tmp_path / "a", "high_benefit_high_cost", expected_benefit=10, operator_relevance=9, estimated_cost=9, risk=5)
    low_cost = _goal(tmp_path / "b", "moderate_benefit_low_cost", expected_benefit=7, operator_relevance=8, estimated_cost=1, risk=2)
    balanced = compile_ranking(evidence_roots=(high_cost, low_cost))
    low_cost_pref = compile_ranking(evidence_roots=(high_cost, low_cost), preference={"priority": "low_cost"}, previous_ranking=balanced)

    assert balanced["recommended_candidate"]["condition_key"] in {"high_benefit_high_cost", "moderate_benefit_low_cost"}
    assert low_cost_pref["recommended_candidate"]["condition_key"] == "moderate_benefit_low_cost"
    assert low_cost_pref["preference_record"]["previous_ranking_digest"] == balanced["artifact_digest"]


def test_case_c_risk_and_prohibited_authority_suppression(tmp_path):
    unsafe = _goal(tmp_path / "unsafe", "valuable_network_goal", expected_benefit=10, authority_requirements=("network_expansion",))
    safe = _goal(tmp_path / "safe", "safe_reliability_goal", expected_benefit=8, risk=2, estimated_cost=2)
    ranking = compile_ranking(evidence_roots=(unsafe, safe))

    assert ranking["recommended_candidate"]["condition_key"] == "safe_reliability_goal"
    assert ranking["suppressed_candidates"][0]["suppression_reason"] == "authority_prohibited_by_current_policy"


def test_case_d_prerequisite_readiness_affects_ranking(tmp_path):
    blocked = _goal(tmp_path / "blocked", "blocked_high_value", expected_benefit=10, readiness=1, missing_prerequisites=("accepted parser",), estimated_cost=4)
    ready = _goal(tmp_path / "ready", "ready_medium_value", expected_benefit=8, readiness=9, estimated_cost=3)
    ranking = compile_ranking(evidence_roots=(blocked, ready))

    assert ranking["recommended_candidate"]["condition_key"] == "ready_medium_value"
    blocked_alt = next(candidate for candidate in ranking["alternatives"] if candidate["condition_key"] == "blocked_high_value")
    assert blocked_alt["dependency_penalty"] > 0


def test_cases_e_and_f_duplicate_and_resolved_goals_are_suppressed(tmp_path):
    active_store = tmp_path / "queue"
    _write(active_store / "queued.json", {"selected_condition_key": "already_queued"})
    duplicate = _goal(tmp_path / "dup", "already_queued")
    resolved = _goal(tmp_path / "resolved", "resolved_gap", already_resolved=True, resolves_conditions=("resolved_gap",))
    candidates = discover_prioritization_candidates((duplicate, resolved), goal_store=active_store)

    reasons = {candidate["condition_key"]: candidate["suppression_reason"] for candidate in candidates}
    assert reasons["already_queued"] == "duplicate_active_or_queued_goal"
    assert reasons["resolved_gap"] == "already_resolved_by_accepted_competence"


def test_cases_g_and_h_one_candidate_and_no_candidate(tmp_path):
    one = _goal(tmp_path / "one", "single_supported_goal")
    one_ranking = compile_ranking(evidence_roots=(one,))
    noise = _goal(tmp_path / "noise", "noise_only", signal_type="irrelevant_noise")
    none = compile_ranking(evidence_roots=(noise,))

    assert one_ranking["status"] == AUTONOMY_2_STATUS
    assert one_ranking["alternatives"] == ()
    assert none["status"] == AUTONOMY_2_NO_GOAL_STATUS
    assert none["recommended_candidate"] == {}


def test_score_direction_and_tie_breaking_are_deterministic(tmp_path):
    a = _goal(tmp_path / "a", "aaa_goal", expected_benefit=7, estimated_cost=3, risk=3)
    b = _goal(tmp_path / "b", "bbb_goal", expected_benefit=7, estimated_cost=3, risk=3)
    ranking1 = compile_ranking(evidence_roots=(a, b))
    ranking2 = compile_ranking(evidence_roots=(a, b))
    score = score_candidate(ranking1["recommended_candidate"])

    assert ranking1["artifact_digest"] == ranking2["artifact_digest"]
    assert "cost" in score["score_formula"]
    assert ranking1["tie_break_rule"].startswith("aggregate score")


def test_preference_reranking_is_immutable_and_persisted(tmp_path):
    roots = (
        _goal(tmp_path / "growth", "growth_goal", expected_benefit=10, estimated_cost=7, risk=5),
        _goal(tmp_path / "cheap", "cheap_goal", expected_benefit=7, estimated_cost=1, risk=2),
    )
    output = tmp_path / "out"
    first = persist_prioritization(evidence_roots=roots, output_root=output)
    second = persist_prioritization(evidence_roots=roots, output_root=output, preference={"priority": "low_cost"}, previous_ranking=first["ranking"])

    assert first["ranking"]["artifact_digest"] != second["ranking"]["artifact_digest"]
    assert tuple((output / "rankings").glob("*.json"))
    assert second["ranking"]["preference_record"]["previous_ranking_digest"] == first["ranking"]["artifact_digest"]


def test_selection_recommendation_alternative_decline_defer_and_ambiguous(tmp_path):
    roots = (
        _goal(tmp_path / "a", "recommended_goal", expected_benefit=9, estimated_cost=2, risk=2),
        _goal(tmp_path / "b", "lower_cost_option", expected_benefit=7, estimated_cost=1, risk=1),
    )
    result = persist_prioritization(evidence_roots=roots, output_root=tmp_path / "out")
    request = result["operator_request"]
    recommended = persist_selection(request=request, selection_text="approve recommended goal", output_root=tmp_path / "out")
    ambiguous = persist_selection(request=request, selection_text="sounds nice", output_root=tmp_path / "other")
    declined = persist_selection(request=request, selection_text="decline all", output_root=tmp_path / "decline")
    deferred = persist_selection(request=request, selection_text="defer all", output_root=tmp_path / "defer")

    assert recommended["status"] == "queued"
    assert recommended["queued_goal"]["execution_started"] is False
    assert ambiguous["status"] == "clarification_required"
    assert declined["status"] == "rejected"
    assert deferred["status"] == "deferred"
    assert normalize_selection("pick the lower-cost option", request)["disposition"] == "approved"


def test_exactly_one_queued_goal_and_duplicate_selection_blocked(tmp_path):
    roots = (_goal(tmp_path / "a", "queue_once", expected_benefit=9, estimated_cost=2, risk=2),)
    result = persist_prioritization(evidence_roots=roots, output_root=tmp_path / "out")
    persist_selection(request=result["operator_request"], selection_text="approve recommended goal", output_root=tmp_path / "out")
    try:
        persist_selection(request=result["operator_request"], selection_text="approve recommended goal", output_root=tmp_path / "out")
    except ValueError as exc:
        assert str(exc) == "duplicate_goal_queued"
    else:
        raise AssertionError("duplicate queued goal was allowed")

    queued = json.loads(next((tmp_path / "out" / "queued_goals").glob("*.json")).read_text(encoding="utf-8"))
    assert queued["provider_calls"] == 0
    assert queued["learning_started"] is False
    assert queued["trusted_admission"] is False
    assert queued["capability_promotion"] is False


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


def test_tk_prioritization_pilot_preference_selection_restart_no_execution(monkeypatch, tmp_path):
    roots = (
        _goal(tmp_path / "high", "high_value_ready_goal", expected_benefit=10, readiness=9, estimated_cost=4, risk=2),
        _goal(tmp_path / "cheap", "lower_cost_option", expected_benefit=7, readiness=8, estimated_cost=1, risk=1),
        _goal(tmp_path / "maint", "maintenance_goal", expected_benefit=4, readiness=9, estimated_cost=1, risk=1),
    )

    def _fake_prioritization(*, evidence_roots, output_root, goal_store=None, preference=None, previous_ranking=None):
        return persist_prioritization(evidence_roots=roots, output_root=tmp_path / "a2", goal_store=goal_store, preference=preference, previous_ranking=previous_ranking)

    def _fake_ranking(*, evidence_roots, goal_store=None, preference=None, previous_ranking=None):
        return compile_ranking(evidence_roots=roots, goal_store=goal_store, preference=preference, previous_ranking=previous_ranking)

    monkeypatch.setattr(DELTA, "persist_prioritization", _fake_prioritization)
    monkeypatch.setattr(DELTA, "compile_autonomy_2_ranking", _fake_ranking)
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, root, "compare next goals")
        assert app.active_operator_ux_request is not None
        assert app.operator_ux_request_card["title"] == "I found several possible next goals"
        assert len(tuple(app.active_operator_ux_request.get("candidates") or ())) == 3

        _send(app, root, "explain")
        assert app.active_operator_ux_request is not None
        app._handle_operator_ux_button("show_alternatives")
        root.update()
        assert "Grounded alternatives" in app.chat_history.get("1.0", tk.END)

        app._handle_operator_ux_button("change_limits")
        root.update()
        assert tuple((app.operator_ux_root / "autonomy_2_rankings").glob("*.json"))

        _send(app, root, "pick the lower-cost option")
        assert app.active_operator_ux_request is None
        queued = tuple((app.operator_ux_root / "approved_goals").glob("*.json"))
        consumed = tuple((app.operator_ux_root / "consumed_responses").glob("*.json"))
        assert len(queued) == 1
        assert len(consumed) == 1
        queued_record = json.loads(queued[0].read_text(encoding="utf-8"))
        assert queued_record["execution_started"] is False
        assert queued_record["learning_started"] is False
        assert queued_record["selected_condition_key"] == "lower_cost_option"
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

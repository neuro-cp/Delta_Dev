from __future__ import annotations

import multiprocessing
import threading
import tkinter as tk
from dataclasses import asdict, replace
from pathlib import Path

import DELTA
from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _evaluation_fixture() -> gsr.SandboxEvidenceEvaluation:
    return gsr.SandboxEvidenceEvaluation(
        evaluation_id="eval-ui-audit",
        cycle_id="cycle-ui-audit",
        plan_id="plan-ui-audit",
        attempt_id="attempt-ui-audit",
        request_id="request-ui-audit",
        authorization_id="auth-ui-audit",
        evidence_digest="digest-ui-audit",
        accepted_for_operator_review=True,
        classification="execution_succeeded",
        reason="evidence_valid_for_operator_review",
        findings=(),
        execution_started=True,
        execution_succeeded=True,
        command_failed=False,
        budget_compliant=True,
        output_within_policy=True,
        artifacts_within_policy=True,
        writes_within_policy=True,
        cleanup_verified=True,
        live_source_unchanged=True,
        evidence_complete=True,
        evidence_consistent=True,
    )


def _disposition_record_fixture(evaluation: gsr.SandboxEvidenceEvaluation) -> gsr.SandboxEvaluationDispositionRecord:
    return gsr.SandboxEvaluationDispositionRecord(
        record_id="record-ui-audit",
        evaluation_id=evaluation.evaluation_id,
        disposition_request_id="disp-request-ui-audit",
        disposition_id="disp-ui-audit",
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
        operator_disposition="accept_evidence_for_future_consideration",
        operator_issued=True,
        issued_sequence=140,
        accepted_evidence=True,
    )


def test_evaluation_tab_renders_constructed_fixtures_without_runtime_side_effects():
    thread_count_before = threading.active_count()
    child_processes_before = tuple(multiprocessing.active_children())
    temp_workspaces_before = set(Path.cwd().glob("gsr_e2b_*"))
    evaluation = _evaluation_fixture()
    record = _disposition_record_fixture(evaluation)
    evaluation_before = asdict(evaluation)
    record_before = asdict(record)

    root = tk.Tk()
    root.withdraw()
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.root = root
    try:
        outer = DELTA.ttk.Frame(root)
        outer.pack(fill=tk.BOTH, expand=True)
        app.notebook = DELTA.ttk.Notebook(outer)
        app.notebook.pack(fill=tk.BOTH, expand=True)
        app.evaluation_tab = DELTA.ttk.Frame(app.notebook, padding=10)
        app.notebook.add(app.evaluation_tab, text="Evaluation")

        app._build_evaluation_tab()
        app._set_evaluation_review_items([
            {"item_type": "empty_state", "title": "Empty state", "status": "empty", "details": {}},
            evaluation,
            record,
        ])
        app.notebook.select(app.evaluation_tab)
        root.update_idletasks()

        children = app.evaluation_items.get_children()
        assert len(children) == 3
        app._refresh_evaluation_snapshot()
        assert len(app.evaluation_items.get_children()) == 3
        app.evaluation_items.selection_set(children[1])
        app._show_selected_evaluation_item()
        detail = app.evaluation_detail.get("1.0", tk.END)
        assert "eval-ui-audit" in detail
        app.evaluation_items.selection_set(children[2])
        app._show_selected_evaluation_item()
        detail = app.evaluation_detail.get("1.0", tk.END)
        assert "record-ui-audit" in detail
        assert "No evaluation, disposition, execution request, authorization" in detail

        assert asdict(evaluation) == evaluation_before
        assert asdict(record) == record_before
        assert app.evaluation_snapshot
        assert not any("authorize" in app.evaluation_items.item(item, "values")[0].lower() for item in children)
        assert replace(record, accepted_evidence=True) == record
    finally:
        root.destroy()

    assert threading.active_count() == thread_count_before
    assert tuple(multiprocessing.active_children()) == child_processes_before
    assert set(Path.cwd().glob("gsr_e2b_*")) == temp_workspaces_before


def _oar_review_item_fixture() -> gsr.OperatorReviewItem:
    return gsr.make_evaluation_review_item(
        parent_mission_id="mission-ui",
        compiled_objective_id="compiled-ui",
        capability_gap_id="gap-ui",
        proposal_id="proposal-ui",
        parent_mission="Improve demonstrated language comprehension and scholarly discussion ability.",
        current_blocker="weak assumption extraction",
        capability_specification={"capability_id": "assumption_extraction"},
        architecture_alternatives=({"option_id": "reuse-existing"},),
        selected_design={"option_id": "reuse-existing"},
        exact_affected_files=("fixtures/language.py",),
        full_patch_or_structured_change="exact reviewed text change",
        focused_tests=("pytest fixture",),
        adjacent_regressions=("pytest adjacent",),
        sandbox_results={"classification": "passed"},
        score_change={"assumption_extraction": 0.1},
        artifact_chain_digest="chain-ui",
        source_precondition_hashes={"fixtures/language.py": "hash-ui"},
    )


def test_evaluation_tab_records_oar_dispositions_without_application_side_effects():
    thread_count_before = threading.active_count()
    child_processes_before = tuple(multiprocessing.active_children())
    review_item = _oar_review_item_fixture()

    root = tk.Tk()
    root.withdraw()
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.root = root
    try:
        outer = DELTA.ttk.Frame(root)
        outer.pack(fill=tk.BOTH, expand=True)
        app.notebook = DELTA.ttk.Notebook(outer)
        app.notebook.pack(fill=tk.BOTH, expand=True)
        app.evaluation_tab = DELTA.ttk.Frame(app.notebook, padding=10)
        app.notebook.add(app.evaluation_tab, text="Evaluation")

        app._build_evaluation_tab()
        app._set_evaluation_review_items([review_item])
        root.update_idletasks()
        selected = app.evaluation_items.get_children()[0]
        app.evaluation_items.selection_set(selected)

        app._record_evaluation_disposition("accepted")
        assert len(app.evaluation_dispositions) == 1
        assert app.evaluation_dispositions[0]["operator_disposition"] == "accepted"
        assert app.evaluation_dispositions[0]["source_written"] is False
        assert app.evaluation_dispositions[0]["application_authorized"] is False
        assert app.evaluation_dispositions[0]["capability_activated"] is False

        app._record_evaluation_disposition("declined")
        assert len(app.evaluation_dispositions) == 1
        assert "duplicate terminal disposition" in app.evaluation_status.get().lower()

        revised = replace(review_item, review_item_id="review-ui-2", proposal_id="proposal-ui-2")
        app._set_evaluation_review_items([revised])
        root.update_idletasks()
        selected = app.evaluation_items.get_children()[0]
        app.evaluation_items.selection_set(selected)
        app._record_evaluation_disposition("needs_modification")
        assert len(app.evaluation_dispositions) == 2
        assert app.evaluation_dispositions[1]["operator_disposition"] == "needs_modification"
        assert app.evaluation_dispositions[1]["creates_revision_request"] is True
        assert app.evaluation_dispositions[1]["revision_request_id"]
    finally:
        root.destroy()

    assert threading.active_count() == thread_count_before
    assert tuple(multiprocessing.active_children()) == child_processes_before


def test_tk_live_mission_intake_surfaces_oar_compilation_before_live_routing():
    thread_count_before = threading.active_count()
    child_processes_before = tuple(multiprocessing.active_children())
    root = tk.Tk()
    root.withdraw()
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.root = root
    try:
        outer = DELTA.ttk.Frame(root)
        outer.pack(fill=tk.BOTH, expand=True)
        app.notebook = DELTA.ttk.Notebook(outer)
        app.notebook.pack(fill=tk.BOTH, expand=True)
        app.evaluation_tab = DELTA.ttk.Frame(app.notebook, padding=10)
        app.notebook.add(app.evaluation_tab, text="Evaluation")
        app._build_evaluation_tab()
        app.chat_input = DELTA.ttk.Entry(root)
        app.chat_input.insert(
            0,
            "Develop the first small improvement needed for better scholarly language behavior.",
        )
        app.mode = tk.StringVar(value="Conversation")
        app.developer_overlay_enabled = tk.BooleanVar(value=False)
        app.last_report_inspection = None
        app.session_history = []
        app.live_runtime_session = type("ActiveRuntime", (), {"active": True})()
        app.live_runtime_called = False
        app._begin_live_runtime_turn = lambda _message: setattr(app, "live_runtime_called", True)
        app.chat_lines = []
        app.session_lines = []
        app._append_chat = lambda speaker, text: app.chat_lines.append((speaker, text))
        app._append_session = lambda role, content: app.session_lines.append({"role": role, "content": content})
        app._refresh_state_cards = lambda: None

        app._send_chat()

        assert app.live_runtime_called is False
        assert len(app.evaluation_review_items) == 1
        item = app.evaluation_review_items[0]
        assert item["item_type"] == "oar_mission_compilation"
        assert item["status"] == "pending_operator_review"
        details = item["details"]
        assert "scholarly language behavior" in details["original_operator_mission"]
        assert details["mission_started"] is False
        assert details["source_application_authorized"] is False
        assert details["capability_activated"] is False
        assert details["automatic_continuation"] is False
        assert app.chat_lines[-1][0] == "DELTA"
        assert "compiled it for operator review" in app.chat_lines[-1][1]
    finally:
        root.destroy()

    assert threading.active_count() == thread_count_before
    assert tuple(multiprocessing.active_children()) == child_processes_before


def test_tk_non_mission_text_does_not_trigger_oar_intake():
    root = tk.Tk()
    root.withdraw()
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.root = root
    try:
        assert app._is_oar_language_development_mission("What color is the sky?") is False
        assert app._is_oar_language_development_mission("tell me how to swim") is False
        assert app._is_oar_language_development_mission("improve the report formatting") is False
        assert app._is_oar_language_development_mission(
            "Develop a bounded scholarly language improvement mission."
        ) is True
    finally:
        root.destroy()

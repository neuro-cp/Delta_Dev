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

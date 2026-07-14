from __future__ import annotations

import multiprocessing
import threading
import tkinter as tk
from dataclasses import asdict, fields, replace
from pathlib import Path

import DELTA
from orchestration.runtime import gsr_a_governed_self_regulation as gsr


class _StatusVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


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
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    class FakeEntry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, *_args) -> None:
            self.value = ""

    app.chat_input = FakeEntry("Develop the first small improvement needed for better scholarly language behavior.")
    app.developer_overlay_enabled = type("Flag", (), {"get": lambda self: False})()
    app.last_report_inspection = None
    app.session_history = []
    app.evaluation_review_items = []
    app.evaluation_dispositions = []
    app.oar_live_state_persistence_enabled = False
    app.live_runtime_session = type("ActiveRuntime", (), {"active": True})()
    app.live_runtime_called = False
    app._begin_live_runtime_turn = lambda _message: setattr(app, "live_runtime_called", True)
    app.chat_lines = []
    app.session_lines = []
    app._append_chat = lambda speaker, text: app.chat_lines.append((speaker, text))
    app._append_session = lambda role, content: app.session_lines.append({"role": role, "content": content})
    app._refresh_state_cards = lambda: None
    app._refresh_evaluation_snapshot = lambda: None

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
        assert app._is_oar_language_development_mission(
            "Improve your demonstrated ability to comprehend, analyze, and discuss scholarly material."
        ) is True
    finally:
        root.destroy()


def test_tk_accepts_compiled_mission_then_start_runtime_queues_one_proposal():
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
        app.session_history = []
        app._build_evaluation_tab()
        app._handle_oar_language_development_mission(
            "Develop a bounded scholarly language improvement mission."
        )
        root.update_idletasks()
        mission_item = app.evaluation_items.get_children()[0]
        app.evaluation_items.selection_set(mission_item)

        app._accept_selected_compiled_mission()

        assert app.oar_runtime_state.development_runtime_mode == "stopped"
        assert app.oar_runtime_state.active_mission_id
        assert len(app.evaluation_review_items) == 1
        assert app.evaluation_review_items[0]["status"] == "mission_approved"
        assert "Start Development Runtime" in app.evaluation_status.get()

        app._start_oar_development_runtime()

        assert app.oar_runtime_state.development_runtime_mode == "paused"
        assert len(app.evaluation_review_items) == 2
        proposal = app.evaluation_review_items[1]
        assert proposal["proposal_id"]
        assert proposal["parent_mission_id"] == app.oar_runtime_state.active_mission_id
        assert proposal["sandbox_results"]["classification"] == "not_yet_executed"
        assert proposal["application_authorized"] is False
        assert proposal["application_performed"] is False
        assert proposal["capability_activated"] is False
        assert "paused after one proposal" in app.evaluation_status.get()

        app._start_oar_development_runtime()
        assert len(app.evaluation_review_items) == 2
        assert "did not start" in app.evaluation_status.get()
    finally:
        root.destroy()

    assert threading.active_count() == thread_count_before
    assert tuple(multiprocessing.active_children()) == child_processes_before


def test_tk_oar_live_development_state_recovers_stopped_without_duplicate_proposal(monkeypatch, tmp_path):
    state_path = tmp_path / "oar_live_development_state.json"
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", state_path)
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    request = gsr.make_mission_compilation_request(
        "Improve your demonstrated ability to comprehend, analyze, and discuss scholarly material.",
        baseline_evaluation_id="tk-live-language-baseline",
        requested_sequence=1,
    )
    authorization = gsr.make_mission_compilation_authorization(request, issued_sequence=2)
    compilation = gsr.compile_language_development_mission(request, authorization, sequence=3)
    mission_approval = gsr.approve_compiled_mission(compilation.compiled_objective, operator_identity="tk_operator", sequence=4)
    registered = gsr.register_approved_mission_for_development(
        gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime"),
        compilation.compiled_objective,
        mission_approval,
        sequence=5,
    )
    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compilation.compiled_objective, sequence=6)
    app.session_history = []
    app.oar_runtime_state = cycle.state
    app.oar_approved_compiled_mission = asdict(compilation.compiled_objective)
    app.oar_mission_approval = asdict(mission_approval)
    app.evaluation_review_items = [{"status": "mission_approved", **asdict(compilation.compiled_objective)}, asdict(cycle.review_item)]
    app.evaluation_dispositions = []
    app.oar_live_state_persistence_enabled = True
    app.evaluation_status = _StatusVar()
    app._persist_oar_live_development_state()

    assert state_path.exists()
    assert app.oar_runtime_state.development_runtime_mode == "paused"
    assert len(app.evaluation_review_items) == 2

    recovered_app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    recovered_app.session_history = []
    recovered_app.oar_runtime_state = gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime")
    recovered_app.oar_approved_compiled_mission = None
    recovered_app.oar_mission_approval = None
    recovered_app.evaluation_review_items = []
    recovered_app.evaluation_dispositions = []
    recovered_app.oar_live_state_persistence_enabled = True
    recovered_app.evaluation_status = _StatusVar()
    recovered_app._load_oar_live_development_state()

    assert recovered_app.oar_runtime_state.development_runtime_mode == "stopped"
    assert recovered_app.oar_runtime_state.completed_cycle_ids
    assert recovered_app.oar_approved_compiled_mission is not None
    assert len(recovered_app.evaluation_review_items) == 2
    recovered_app._start_oar_development_runtime()
    assert len(recovered_app.evaluation_review_items) == 2
    assert "development_cycle_already_completed" in recovered_app.evaluation_status.get()


def test_tk_runs_selected_fixture_proposal_and_recovers_without_duplicate_execution(monkeypatch, tmp_path):
    state_path = tmp_path / "oar_live_development_state.json"
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", state_path)

    compiled = gsr.make_mission_compilation_request(
        "Improve your demonstrated ability to comprehend, analyze, and discuss scholarly material.",
        baseline_evaluation_id="tk-live-language-baseline",
        requested_sequence=1,
    )
    authorization = gsr.make_mission_compilation_authorization(compiled, issued_sequence=2)
    compilation = gsr.compile_language_development_mission(compiled, authorization, sequence=3)
    mission_approval = gsr.approve_compiled_mission(compilation.compiled_objective, operator_identity="tk_operator", sequence=4)
    registered = gsr.register_approved_mission_for_development(
        gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime"),
        compilation.compiled_objective,
        mission_approval,
        sequence=5,
    )
    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compilation.compiled_objective, sequence=6)
    assert cycle.review_item is not None

    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.session_history = []
    app.oar_runtime_state = cycle.state
    app.oar_approved_compiled_mission = asdict(compilation.compiled_objective)
    app.oar_mission_approval = asdict(mission_approval)
    app.evaluation_review_items = [asdict(cycle.review_item)]
    app.evaluation_dispositions = []
    app.oar_live_state_persistence_enabled = True
    app.evaluation_status = _StatusVar()

    def set_items(items):
        app.evaluation_review_items = [
            asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item)
            for item in items
        ]

    app._selected_evaluation_review_item = lambda: ("review-1", asdict(cycle.review_item))
    app._set_evaluation_review_items = set_items

    app._execute_selected_fixture_proposal()
    app._persist_oar_live_development_state()

    assert len(app.evaluation_review_items) == 2
    evidence = app.evaluation_review_items[1]
    assert evidence["status"] == "evidence_queued"
    assert evidence["proposal_id"] == app.evaluation_review_items[0]["proposal_id"]
    assert evidence["operation_performed"] == "python_compile_fixture"
    assert evidence["cleanup_result"] == "verified"
    assert evidence["application_performed"] is False
    assert evidence["capability_activated"] is False
    assert evidence["automatic_continuation"] is False
    assert app.oar_runtime_state.development_runtime_mode == "paused"
    assert app.oar_runtime_state.executed_fixture_review_item_ids == (app.evaluation_review_items[0]["review_item_id"],)
    assert "Fixture evidence queued" in app.evaluation_status.get()

    recovered_app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    recovered_app.session_history = []
    recovered_app.oar_runtime_state = gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime")
    recovered_app.oar_approved_compiled_mission = None
    recovered_app.oar_mission_approval = None
    recovered_app.evaluation_review_items = []
    recovered_app.evaluation_dispositions = []
    recovered_app.oar_live_state_persistence_enabled = True
    recovered_app.evaluation_status = _StatusVar()
    recovered_app._load_oar_live_development_state()

    assert recovered_app.oar_runtime_state.development_runtime_mode == "stopped"
    assert len(recovered_app.evaluation_review_items) == 2
    item = gsr.OperatorReviewItem(**{
        key: value
        for key, value in recovered_app.evaluation_review_items[0].items()
        if key in {field.name for field in fields(gsr.OperatorReviewItem)}
    })
    authorization = gsr.make_live_fixture_execution_authorization(
        item,
        operator_identity="tk_operator",
        issued_sequence=40,
        expiration_sequence=45,
    )
    duplicate = gsr.execute_live_fixture_proposal(recovered_app.oar_runtime_state, item, authorization, sequence=40)
    assert duplicate.accepted is False
    assert duplicate.reason == "fixture_execution_already_completed"


def test_tk_runs_tracked_source_preflight_for_fixture_evidence_without_application(monkeypatch, tmp_path):
    state_path = tmp_path / "oar_live_development_state.json"
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", state_path)
    compiled = gsr.make_mission_compilation_request(
        "Improve your demonstrated ability to comprehend, analyze, and discuss scholarly material.",
        baseline_evaluation_id="tk-live-language-baseline",
        requested_sequence=1,
    )
    authorization = gsr.make_mission_compilation_authorization(compiled, issued_sequence=2)
    compilation = gsr.compile_language_development_mission(compiled, authorization, sequence=3)
    mission_approval = gsr.approve_compiled_mission(compilation.compiled_objective, operator_identity="tk_operator", sequence=4)
    registered = gsr.register_approved_mission_for_development(
        gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime"),
        compilation.compiled_objective,
        mission_approval,
        sequence=5,
    )
    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compilation.compiled_objective, sequence=6)
    fixture_authorization = gsr.make_live_fixture_execution_authorization(cycle.review_item, operator_identity="tk_operator", issued_sequence=7, expiration_sequence=12)
    fixture = gsr.execute_live_fixture_proposal(cycle.state, cycle.review_item, fixture_authorization, sequence=7)
    assert fixture.accepted is True

    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.oar_runtime_state = fixture.state
    app.oar_approved_compiled_mission = asdict(compilation.compiled_objective)
    app.oar_mission_approval = asdict(mission_approval)
    app.evaluation_review_items = [asdict(cycle.review_item), asdict(fixture.evidence_review_item)]
    app.evaluation_dispositions = []
    app.oar_live_state_persistence_enabled = True
    app.evaluation_status = _StatusVar()
    app._selected_evaluation_review_item = lambda: ("review-2", asdict(fixture.evidence_review_item))

    def set_items(items):
        app.evaluation_review_items = [
            asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item)
            for item in items
        ]

    app._set_evaluation_review_items = set_items

    app._run_selected_tracked_source_preflight()
    app._persist_oar_live_development_state()

    assert len(app.evaluation_review_items) == 3
    readiness = app.evaluation_review_items[2]
    assert readiness["status"] == "readiness_queued"
    assert readiness["eligibility_classification"] == "fixture_only_no_tracked_target"
    assert readiness["application_performed"] is False
    assert readiness["capability_activated"] is False
    assert readiness["automatic_continuation"] is False
    assert app.oar_runtime_state.development_runtime_mode == "paused"
    assert app.oar_runtime_state.completed_tracked_preflight_review_item_ids == (fixture.evidence_review_item.review_item_id,)
    assert "Tracked-source preflight queued" in app.evaluation_status.get()

    recovered = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    recovered.oar_runtime_state = gsr.OARRuntimeState(runtime_state_id="tk-oar-development-runtime")
    recovered.oar_approved_compiled_mission = None
    recovered.oar_mission_approval = None
    recovered.evaluation_review_items = []
    recovered.evaluation_dispositions = []
    recovered.oar_live_state_persistence_enabled = True
    recovered._load_oar_live_development_state()
    assert recovered.oar_runtime_state.development_runtime_mode == "stopped"
    assert len(recovered.evaluation_review_items) == 3

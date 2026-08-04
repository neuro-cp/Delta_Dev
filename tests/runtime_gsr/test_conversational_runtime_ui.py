import tkinter as tk
from dataclasses import replace
import time


ENGLISH_GOAL = "Your goal today is to improve your English comprehension so we can communicate better."
FOREGROUND_CAMPAIGN_GOAL = (
    "Your new goal is to improve how you distinguish between a new foreground question and a continuation "
    "of the previous topic. Study our normal conversation, identify the first recurring failure pattern, "
    "compare at least three bounded approaches, test them against unrelated-topic and follow-up cases, "
    "and notify me when you reach a meaningful milestone, become blocked, or finish with an adoption recommendation. "
    "Use local cognition and existing evidence first. Do not change source or restart without my explicit approval. "
    "Start working now."
)


def _app(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    monkeypatch.setattr(DELTA.DeltaApp, "_warm_default_model", lambda self: None)
    monkeypatch.setattr(DELTA.DeltaApp, "_conversational_cognitive_model_runner", lambda self: ScriptedSemanticModel())
    monkeypatch.setattr(DELTA, "CONVERSATIONAL_RUNTIME_ROOT", tmp_path / "conversational-runtime")
    last_error = None
    for _ in range(4):
        try:
            root = tk.Tk()
            break
        except tk.TclError as exc:
            last_error = exc
            time.sleep(0.1)
    else:
        raise last_error
    app = DELTA.DeltaApp(root)
    root.update()
    return root, app


def _send(app, text):
    app.chat_input.delete(0, tk.END)
    app.chat_input.insert(0, text)
    app._send_chat()


def _pump_until(root, predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(0.02)
    assert predicate()


def _add_local_insufficiency(app):
    from orchestration.runtime.conversational_runtime_operation import record_local_semantic_attempt

    app.conversational_runtime_state, evaluation = record_local_semantic_attempt(
        app.conversational_runtime_state,
        runtime_root=app.conversational_runtime_root,
        target_gap="queued implied references across topic switches",
        local_model="qwen-test",
        local_prompt="Generate topic-switch counterexamples.",
        raw_response="One vague reference note only.",
    )
    assert evaluation["status"] == "locally_insufficient"


def test_graph_bound_question_uses_epistemic_answer_without_requests_or_writes(monkeypatch, tmp_path):
    import hashlib
    from orchestration.runtime.provisional_semantic_consolidation import ClaimVersion, ProvisionalSemanticGraphState, graph_path, save_graph

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph = ProvisionalSemanticGraphState(
            graph_id="tk-epistemic-answer",
            claim_versions=(
                ClaimVersion(
                    "claim-version-reviewed-ui",
                    "claim-reviewed-ui",
                    1,
                    "The reviewed barrel record says roof runoff enters storage through a downspout.",
                    "validated",
                    (),
                    (),
                    (),
                    (),
                    "sha256:reviewed-ui",
                    "2026-08-02T00:00:00+00:00",
                ),
            ),
        )
        save_graph(app.conversational_runtime_root, graph)
        graph_file = graph_path(app.conversational_runtime_root)
        before = hashlib.sha256(graph_file.read_bytes()).hexdigest()

        _send(app, "What does claim-version-reviewed-ui say?")

        chat = app.chat_history.get("1.0", tk.END)
        after = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        assert "roof runoff enters storage through a downspout" in chat
        assert "Would you like me to ask a local reasoning model" not in chat
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert before == after
        assert app.last_payload["route"] == "epistemic_answer_mode"
        assert app.last_payload["epistemic_answer_resolution"]["epistemic_mode"] == "reviewed_supported"

        app._open_developer_diagnostics()
        app._show_epistemic_answer_audit()
        audit = app.output.get("1.0", tk.END)
        assert "Epistemic answer audit" in audit
        assert "reviewed_supported" in audit
        assert "claim-version-reviewed-ui" in audit
        assert "canonical_write_performed" in audit
        assert '"canonical_write_performed": false' in audit
    finally:
        root.destroy()


def test_epistemic_answer_modes_survive_tk_restart_without_graph_mutation(monkeypatch, tmp_path):
    import hashlib
    from orchestration.runtime.provisional_semantic_consolidation import (
        AdmissionRecord,
        ClaimVersion,
        ProvisionalSemanticGraphState,
        ReviewRecord,
        graph_path,
        save_graph,
    )

    def version(version_id, claim_id, text, state, supersedes=""):
        return ClaimVersion(version_id, claim_id, 2 if supersedes else 1, text, state, (), (), (), (), "sha256:" + version_id, "2026-08-02T00:00:00+00:00", supersedes)

    def review(version_id, verdict, correction=""):
        return ReviewRecord(
            "review-" + version_id,
            "packet-" + version_id,
            "sha256:packet-" + version_id,
            {"mode": "synthetic"},
            ({"claim_version_id": version_id, "verdict": verdict, "reviewed_fragment_ids": (), "proposed_correction": correction, "confidence": 0.8, "rationale_code": verdict},),
            "2026-08-02T00:01:00+00:00",
        )

    graph = ProvisionalSemanticGraphState(
        graph_id="tk-epistemic-restart",
        claim_versions=(
            version("claim-reviewed-tk", "claim-reviewed", "Reviewed barrels collect roof runoff through downspouts.", "validated"),
            version("claim-partial-tk", "claim-partial", "Barrels collect runoff, but mosquito control details remain unresolved.", "partially_valid"),
            version("claim-provisional-tk", "claim-provisional", "A mesh screen may reduce mosquito entry.", "provisional"),
            version("claim-pending-tk", "claim-pending", "Overflow routing is pending consolidation review.", "pending_consolidation"),
            version("claim-weak-tk", "claim-weak", "Overflow always prevents flooding.", "requires_revision"),
            version("claim-weak-tk-v2", "claim-weak", "Overflow routing can reduce flooding risk when routed away from the foundation.", "validated", "claim-weak-tk"),
            version("claim-unsupported-tk", "claim-unsupported", "Rain barrels eliminate all maintenance.", "unsupported"),
            version("claim-contradicted-tk", "claim-contradicted", "Standing water cannot attract mosquitoes.", "locally_contradicted"),
        ),
        reviews=(
            review("claim-reviewed-tk", "validated"),
            review("claim-partial-tk", "partially_valid"),
            review("claim-weak-tk", "requires_revision", "Overflow routing can reduce flooding risk when routed safely."),
            review("claim-weak-tk-v2", "validated"),
            review("claim-unsupported-tk", "unsupported"),
            review("claim-contradicted-tk", "contradicted"),
        ),
        admissions=(AdmissionRecord("admission-weak-tk", "review-claim-weak-tk", "overlay-weak", "claim-weak-tk", "revise", "claim-weak-tk-v2", "2026-08-02T00:02:00+00:00"),),
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        save_graph(app.conversational_runtime_root, graph)
        graph_file = graph_path(app.conversational_runtime_root)
        before = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        cases = (
            ("What does claim-reviewed-tk say?", "Reviewed barrels collect roof runoff", "reviewed_supported"),
            ("What does claim-partial-tk say?", "unresolved portions", "partially_supported"),
            ("What does claim-provisional-tk say?", "has not completed consolidation review", "provisional_unreviewed"),
            ("What does claim-pending-tk say?", "pending consolidation review", "pending_consolidation"),
            ("What does claim-weak-tk say?", "routed away from the foundation", "revised_supported"),
            ("What does claim-unsupported-tk say?", "does not support", "unsupported"),
            ("What does claim-contradicted-tk say?", "cannot give a definitive answer", "contradicted"),
            ("What is 2 + 2?", "4", None),
        )
        for prompt, expected_text, expected_mode in cases:
            _send(app, prompt)
            chat = app.chat_history.get("1.0", tk.END)
            assert expected_text in chat
            if expected_mode:
                assert app.last_payload["epistemic_answer_resolution"]["epistemic_mode"] == expected_mode
            else:
                assert app.last_payload["route"] == "ordinary_local_reasoning"
        assert hashlib.sha256(graph_file.read_bytes()).hexdigest() == before
        assert app.conversational_runtime_state.pending_chat_requests == ()
    finally:
        root.destroy()

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph_file = graph_path(app.conversational_runtime_root)
        before_restart = hashlib.sha256(graph_file.read_bytes()).hexdigest()
        _send(app, "What does claim-weak-tk say?")
        assert "routed away from the foundation" in app.chat_history.get("1.0", tk.END)
        assert app.last_payload["epistemic_answer_resolution"]["selected_revised_claim_version_id"] == "claim-weak-tk-v2"
        assert hashlib.sha256(graph_file.read_bytes()).hexdigest() == before_restart
        assert app.conversational_runtime_state.pending_chat_requests == ()
    finally:
        root.destroy()


def test_default_surface_is_simple_and_advanced_is_inspectable(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        tabs = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]
        assert tabs == ["Conversation"]
        assert "Chat runtime: ready" in app.conversational_runtime_status.get()

        app._open_developer_diagnostics()
        tabs = [app.notebook.tab(tab_id, "text") for tab_id in app.notebook.tabs()]
        assert "Developer" in tabs
        assert "Goals" in tabs
        assert "Settings" in tabs
        assert app.developer_notebook.tab(app.advanced_tab, "text") == "Diagnostics"
    finally:
        root.destroy()


def test_conversation_teaching_intent_creates_and_restores_canonical_controller(monkeypatch, tmp_path):
    """The normal Conversation entry point must not bypass an explicit teaching request."""

    import DELTA
    from orchestration.runtime.developmental_teaching_runtime import teaching_snapshot

    monkeypatch.setattr(DELTA.DeltaApp, "_start_conversational_background_cycle", lambda self, *args, **kwargs: False)
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "Today I want you to teach me basic neuroanatomy.")

        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        assert objective.provenance["execution_mode"] == "knowledge_acquisition"
        assert objective.provenance["teaching_plan"]["domain"] == "neuroscience"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Let's begin with basic neuroanatomy." in transcript
        assert "Would you like me to ask a local reasoning model" not in transcript

        controller = app.developmental_teaching_controller
        assert controller is not None
        snapshot = teaching_snapshot(controller)
        assert snapshot["objective_id"] == objective.objective_id
        assert snapshot["teaching_cursor"] == 0
        assert (app.conversational_runtime_root / "developmental-teaching" / f"{objective.objective_id}.json").exists()
        objective_id = objective.objective_id
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        assert restored.conversational_runtime_state.active_objective is not None
        assert restored.conversational_runtime_state.active_objective.objective_id == objective_id
        assert restored.developmental_teaching_controller is not None
        assert teaching_snapshot(restored.developmental_teaching_controller)["teaching_cursor"] == 0
        assert len(restored.conversational_runtime_state.conversation) == 2
    finally:
        root.destroy()


def test_background_merge_does_not_resurrect_consumed_teaching_prerequisite(monkeypatch, tmp_path):
    """A foreground approval must beat an older worker snapshot of the same request."""

    from orchestration.runtime.conversational_runtime_operation import (
        handle_conversational_message,
        resolve_pending_chat_request,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        created = handle_conversational_message(
            app.conversational_runtime_state,
            "Teach me physics.",
            runtime_root=app.conversational_runtime_root,
            run_background_cycle=False,
        ).state
        request = created.pending_chat_requests[0]
        approved = resolve_pending_chat_request(
            created,
            "Yes",
            runtime_root=app.conversational_runtime_root,
        ).state

        app.conversational_runtime_state = approved
        merged = app._merge_conversational_background_result(created, created)
        prerequisite = merged.active_objective.provenance["teaching_prerequisites"][0]

        assert merged.pending_chat_requests == ()
        assert len(merged.resolved_chat_requests) == 1
        assert merged.resolved_chat_requests[0].request_id == request.request_id
        assert merged.resolved_chat_requests[0].consumption_count == 1
        assert prerequisite["status"] == "queued"
        assert prerequisite["derivation_branch_state"] == "preparing_prerequisite"
    finally:
        root.destroy()


def test_physics_prerequisite_competence_result_renders_once_and_survives_restart(monkeypatch, tmp_path):
    """A tested prerequisite should visibly reopen its parent branch exactly once."""

    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel
    from orchestration.runtime.conversational_runtime_operation import save_runtime_state

    def calculus_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        label = str(node.get("label") or "")
        if "introductory calculus" in label.lower():
            statement = (
                "A derivative represents the rate of change of position with respect to time, "
                "so it gives an object's velocity in a mechanics application."
            )
            response.update({
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": label,
                "expected_observations": "Velocity is obtained by differentiating a position function with respect to time.",
                "raw_model_output": statement,
            })
        return response

    root, app = _app(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(app, "_conversational_cognitive_model_runner", lambda: calculus_runner)
        _send(app, "Teach me physics.")
        _pump_until(
            root,
            lambda: any(item.request_type == "teaching_prerequisite" for item in app.conversational_runtime_state.pending_chat_requests),
            timeout=8.0,
        )
        _send(app, "Yes.")
        _pump_until(
            root,
            lambda: app.conversational_runtime_state.active_objective.provenance["teaching_prerequisites"][0]["status"] == "competence_tested",
            timeout=8.0,
        )

        prerequisite = app.conversational_runtime_state.active_objective.provenance["teaching_prerequisites"][0]
        transcript = app.chat_history.get("1.0", tk.END)
        assert prerequisite["derivation_branch_state"] == "resumed"
        assert prerequisite["parent_branch_resume_cursor"] == 3
        assert prerequisite["parent_branch_resume_lesson_title"] == "Mathematical mechanics"
        assert prerequisite["parent_branch_resume_event_id"]
        assert prerequisite["conversation_result_rendered"] is True
        assert "passed its bounded competence check" in transcript
        assert "resume Mathematical mechanics provisionally" in transcript
        assert "derivative represents the rate of change" in transcript
        assert transcript.count("passed its bounded competence check") == 1
        assert app._developmental_teaching_snapshot()["teaching_cursor"] >= 3
        assert app._developmental_teaching_snapshot()["stage"] == "derivation_branch_resumed"
        assert sum(
            item.get("event") == "teaching_parent_branch_resumed"
            for item in app.conversational_runtime_state.objective_progress
        ) == 1

        app._render_unshown_teaching_followup_results()
        assert app.chat_history.get("1.0", tk.END).count("passed its bounded competence check") == 1
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        prerequisite_id = prerequisite["prerequisite_id"]

        # Model a restart after the durable worker merge but before the UI had
        # marked its result rendered. The canonical state, not a UI cache,
        # must recover the one natural projection.
        unshown_prerequisite = {
            key: value
            for key, value in prerequisite.items()
            if key not in {"conversation_result_rendered", "conversation_result_rendered_at"}
        }
        unshown_objective = replace(
            app.conversational_runtime_state.active_objective,
            provenance={
                **app.conversational_runtime_state.active_objective.provenance,
                "teaching_prerequisites": (unshown_prerequisite,),
            },
        )
        app.conversational_runtime_state = replace(
            app.conversational_runtime_state,
            active_objective=unshown_objective,
            conversation=tuple(
                turn
                for turn in app.conversational_runtime_state.conversation
                if turn.intent_type != "teaching_prerequisite_result"
            ),
        )
        save_runtime_state(app.conversational_runtime_root, app.conversational_runtime_state)
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        restored_prerequisite = restored.conversational_runtime_state.active_objective.provenance["teaching_prerequisites"][0]
        transcript = restored.chat_history.get("1.0", tk.END)
        assert restored.conversational_runtime_state.active_objective.objective_id == objective_id
        assert restored_prerequisite["prerequisite_id"] == prerequisite_id
        assert restored_prerequisite["conversation_result_rendered"] is True
        assert transcript.count("passed its bounded competence check") == 1
        assert restored._developmental_teaching_snapshot()["teaching_cursor"] >= 3
        assert restored._developmental_teaching_snapshot()["stage"] == "derivation_branch_resumed"
        assert sum(
            item.get("event") == "teaching_parent_branch_resumed"
            for item in restored.conversational_runtime_state.objective_progress
        ) == 1
    finally:
        root.destroy()


def test_unshown_teaching_result_and_retention_prompt_project_once_after_restart(monkeypatch, tmp_path):
    """Startup projects durable teaching output once without a UI-owned queue."""

    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel
    from orchestration.runtime.conversational_runtime_operation import save_runtime_state

    def amygdala_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        label = str(node.get("label") or "")
        if "amygdala" in label.lower():
            statement = (
                "The amygdala assigns emotional salience to sensory cues because it links their appraisal "
                "with memory and autonomic response systems."
            )
            response.update({
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": label,
                "raw_model_output": statement,
            })
        return response

    root, app = _app(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(app, "_conversational_cognitive_model_runner", lambda: amygdala_runner)
        _send(app, "Teach me neuroanatomy.")
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys) and not app.conversational_runtime_inference_in_flight)
        _send(app, "What does the amygdala do?")
        _pump_until(
            root,
            lambda: any(
                item.request_type == "teaching_provisional_retention"
                for item in app.conversational_runtime_state.pending_chat_requests
            ),
            timeout=8.0,
        )

        objective = app.conversational_runtime_state.active_objective
        followup = objective.provenance["teaching_followups"][0]
        request = next(
            item
            for item in app.conversational_runtime_state.pending_chat_requests
            if item.request_type == "teaching_provisional_retention"
        )
        followup_id = followup["followup_id"]
        request_id = request.request_id
        unshown_followup = {
            key: value
            for key, value in followup.items()
            if key not in {"conversation_result_rendered", "conversation_result_rendered_at"}
        }
        unshown_request = replace(request, rendered_turn_id="", render_sequence=0)
        unshown_objective = replace(
            objective,
            provenance={
                **objective.provenance,
                "teaching_followups": (unshown_followup,),
            },
        )
        app.conversational_runtime_state = replace(
            app.conversational_runtime_state,
            active_objective=unshown_objective,
            pending_chat_requests=(unshown_request,),
            conversation=tuple(
                turn
                for turn in app.conversational_runtime_state.conversation
                if turn.intent_type not in {
                    "teaching_followup_result",
                    "teaching_provisional_retention_prompt",
                }
            ),
        )
        save_runtime_state(app.conversational_runtime_root, app.conversational_runtime_state)
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        transcript = restored.chat_history.get("1.0", tk.END)
        restored_followup = restored.conversational_runtime_state.active_objective.provenance["teaching_followups"][0]
        restored_request = next(
            item
            for item in restored.conversational_runtime_state.pending_chat_requests
            if item.request_id == request_id
        )
        assert restored_followup["followup_id"] == followup_id
        assert restored_followup["conversation_result_rendered"] is True
        assert restored_request.rendered_turn_id
        assert transcript.count("This is newly learned provisional material") == 1
        assert transcript.count("Should I remember it for future") == 1
        assert sum(
            turn.intent_type == "teaching_followup_result"
            for turn in restored.conversational_runtime_state.conversation
        ) == 1
        assert sum(
            turn.intent_type == "teaching_provisional_retention_prompt"
            for turn in restored.conversational_runtime_state.conversation
        ) == 1
    finally:
        root.destroy()

    root, restored_again = _app(monkeypatch, tmp_path)
    try:
        transcript = restored_again.chat_history.get("1.0", tk.END)
        assert transcript.count("This is newly learned provisional material") == 1
        assert transcript.count("Should I remember it for future") == 1
        assert sum(
            turn.intent_type == "teaching_followup_result"
            for turn in restored_again.conversational_runtime_state.conversation
        ) == 1
        assert sum(
            turn.intent_type == "teaching_provisional_retention_prompt"
            for turn in restored_again.conversational_runtime_state.conversation
        ) == 1
    finally:
        root.destroy()


def test_conversation_teaching_followup_studies_once_then_reuses_retained_provisional_answer(monkeypatch, tmp_path):
    """The normal Tk path owns the study, request, retention, and later recall."""

    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel
    from orchestration.runtime.provisional_semantic_consolidation import load_graph

    def amygdala_runner(request, packet):
        response = dict(ScriptedSemanticModel()(request, packet))
        node = dict(packet.active_focus.get("active_frontier_node") or {})
        label = str(node.get("label") or "")
        if "amygdala" in label.lower():
            statement = (
                "The amygdala helps assign emotional salience to sensory information and supports threat-related learning "
                "because it coordinates signals with memory and autonomic response systems."
            )
            response.update({
                "interpretation": statement,
                "hypothesis_statement": statement,
                "scope": label,
                "raw_model_output": statement,
            })
        return response

    root, app = _app(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(app, "_conversational_cognitive_model_runner", lambda: amygdala_runner)
        _send(app, "Today I want you to teach me basic neuroanatomy.")
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys) and not app.conversational_runtime_inference_in_flight)

        _send(app, "What does the amygdala do?")
        _pump_until(
            root,
            lambda: any(item.request_type == "teaching_provisional_retention" for item in app.conversational_runtime_state.pending_chat_requests),
            timeout=8.0,
        )

        followup = app.conversational_runtime_state.active_objective.provenance["teaching_followups"][0]
        request = next(item for item in app.conversational_runtime_state.pending_chat_requests if item.request_type == "teaching_provisional_retention")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "bounded local study" in transcript
        assert "emotional salience" in transcript
        assert request.rendered_turn_id
        assert followup["status"] == "provisional_ready_for_retention"
        assert followup["claim_version_id"]
        assert followup["understanding_assessment"]["factual_status"] == "still_provisional_pending_consolidation"
        controller_id = app.developmental_teaching_controller.controller_id

        # Keep the next idle step under this test's control so it can prove the
        # state-derived consolidation pressure rather than a timing accident.
        app._start_conversational_background_cycle = lambda _reason: False
        _send(app, "Yes.")
        _pump_until(root, lambda: not any(item.request_id == request.request_id for item in app.conversational_runtime_state.pending_chat_requests))
        retained = app.conversational_runtime_state.active_objective.provenance["teaching_followups"][0]
        assert retained["status"] == "retained_provisional"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_id == request.request_id
        assert app.conversational_runtime_state.resolved_chat_requests[-1].consumption_count == 1
        assert app._developmental_teaching_snapshot()["teaching_cursor"] == 4
        assert "Next, we can cover Brainstem and cerebellum" in app.chat_history.get("1.0", tk.END)

        followup_count = len(app.conversational_runtime_state.active_objective.provenance["teaching_followups"])
        _send(app, "What does the amygdala do?")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "emotional salience" in transcript
        assert app.last_payload["route"] == "epistemic_answer_mode"
        assert len(app.conversational_runtime_state.active_objective.provenance["teaching_followups"]) == followup_count
        assert not any(item.request_type == "teaching_provisional_retention" for item in app.conversational_runtime_state.pending_chat_requests)

        app._sync_developmental_teaching_progress()
        app._tick_conversational_objective_runtime()
        decision = app.interactive_attention_decision
        assert decision.selected_posture == "perform_one_consolidation_step"
        assert decision.target_owner == "continuous_runtime_controller"
        assert "canonical_developmental_pressure_projection" in decision.reason_codes

        graph = load_graph(app.conversational_runtime_root)
        review_request = next(
            item
            for item in app.conversational_runtime_state.pending_chat_requests
            if item.request_type == "teaching_consolidation_review_authority"
        )
        transcript = app.chat_history.get("1.0", tk.END)
        assert len(graph.packets) == 1
        assert graph.reviews == ()
        assert graph.admissions == ()
        assert "I finished organizing the recent basic neuroanatomy material." in transcript
        assert "no external grounding review has run" in transcript
        assert review_request.rendered_turn_id
        app._tick_conversational_objective_runtime()
        assert len(load_graph(app.conversational_runtime_root).packets) == 1

        _send(app, "Yes, authorize the bounded review packet when that separate path is available.")
        assert not any(item.request_id == review_request.request_id for item in app.conversational_runtime_state.pending_chat_requests)
        resolved_review = app.conversational_runtime_state.resolved_chat_requests[-1]
        assert resolved_review.request_id == review_request.request_id
        assert resolved_review.resolution_policy == "operator_authorized_consolidation_review_preparation"
        consolidation_record = app.conversational_runtime_state.active_objective.provenance["teaching_consolidation_records"][0]
        assert consolidation_record["review_status"] == "pending_external_review"
        assert consolidation_record["review_authority_granted"] is True
        assert consolidation_record["external_review_result_id"] == ""
        assert consolidation_record["admission_id"] == ""
        assert "No external review has run yet" in app.chat_history.get("1.0", tk.END)
        assert len(load_graph(app.conversational_runtime_root).packets) == 1
        assert load_graph(app.conversational_runtime_root).reviews == ()
        assert load_graph(app.conversational_runtime_root).admissions == ()

        # Once review authority is recorded, the same debt remains visible as a
        # waiting boundary but cannot recreate the authority request.
        app._sync_developmental_teaching_progress()
        waiting_pressures = app._developmental_teaching_snapshot()["developmental_pressures"]
        assert any(
            item["pressure_type"] == "external_review_pending"
            and item["recommended_action"] == "await_external_review"
            for item in waiting_pressures
        )
        app._refresh_interactive_cognition_shadow(reason="review-authority-suppression-proof")
        waiting_thread = next(
            item
            for item in app.interactive_workspace_snapshot.threads
            if item.inclusion_reason == "pending_external_review_suppresses_repeat_authority_prompt"
        )
        assert waiting_thread.status == "awaiting_external_review"
        assert app.interactive_attention_decision.target_thread_id != waiting_thread.thread_id
        app._tick_conversational_objective_runtime()
        assert not any(
            item.request_type == "teaching_consolidation_review_authority"
            for item in app.conversational_runtime_state.pending_chat_requests
        )
        assert len(load_graph(app.conversational_runtime_root).packets) == 1
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        followup_id = retained["followup_id"]
        claim_version_id = retained["claim_version_id"]
        packet_id = graph.packets[0].packet_id
    finally:
        root.destroy()

    root, restored = _app(monkeypatch, tmp_path)
    try:
        objective = restored.conversational_runtime_state.active_objective
        assert objective is not None
        restored_transcript = restored.chat_history.get("1.0", tk.END)
        assert "You: Today I want you to teach me basic neuroanatomy." in restored_transcript
        assert "emotional salience" in restored_transcript
        assert "Hi. I'm DELTA." not in restored_transcript
        assert objective.objective_id == objective_id
        restored_followup = objective.provenance["teaching_followups"][0]
        assert restored_followup["followup_id"] == followup_id
        assert restored_followup["claim_version_id"] == claim_version_id
        assert len(load_graph(restored.conversational_runtime_root).packets) == 1
        assert load_graph(restored.conversational_runtime_root).packets[0].packet_id == packet_id
        assert not restored.conversational_runtime_state.pending_chat_requests
        restored_record = objective.provenance["teaching_consolidation_records"][0]
        assert restored_record["review_status"] == "pending_external_review"
        assert restored_record["review_authority_granted"] is True
        assert restored_record["external_review_result_id"] == ""
        assert restored_record["admission_id"] == ""
        assert load_graph(restored.conversational_runtime_root).reviews == ()
        assert load_graph(restored.conversational_runtime_root).admissions == ()
        assert sum(
            item.get("event") == "teaching_consolidation_aftermath_reported"
            for item in restored.conversational_runtime_state.objective_progress
        ) == 1

        _send(restored, "What does the amygdala do?")
        assert restored.last_payload["route"] == "epistemic_answer_mode"
        assert not restored.conversational_runtime_state.pending_chat_requests
        assert len(load_graph(restored.conversational_runtime_root).packets) == 1

        # Exact controller, request, claim, and packet lineage remains in the
        # Developer audit; Conversation stays free of implementation IDs.
        restored._show_developmental_teaching_audit()
        audit_text = restored.output.get("1.0", tk.END)
        assert objective_id in audit_text
        assert controller_id in audit_text
        assert claim_version_id in audit_text
        assert packet_id in audit_text
        assert "teaching_consolidation_review_authority" in audit_text
        assert "Developmental teaching audit" in audit_text
    finally:
        root.destroy()


def test_queued_teaching_followup_is_reconciled_once_at_worker_boundary(monkeypatch, tmp_path):
    """An in-scope foreground question must survive a live worker and then use the normal teaching path."""

    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "Today I want you to teach me basic neuroanatomy.")
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys) and not app.conversational_runtime_inference_in_flight)

        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        assert app._start_conversational_background_cycle("queued_teaching_followup_boundary") is True
        assert app.conversational_runtime_inference_in_flight is True

        _send(app, "What does the amygdala do?")
        assert app.conversational_runtime_state.conversation[-1].intent_type == "ordinary_conversation_queued"

        _pump_until(
            root,
            lambda: bool(app.conversational_runtime_state.active_objective.provenance.get("teaching_followups", ())),
            timeout=5.0,
        )

        state = app.conversational_runtime_state
        matching_users = [
            turn
            for turn in state.conversation
            if turn.role == "user" and turn.text == "What does the amygdala do?"
        ]
        assert len(matching_users) == 1
        assert matching_users[0].intent_type == "teaching_followup_question"
        assert len(state.active_objective.provenance["teaching_followups"]) == 1
        assert sum(item.get("event") == "queued_teaching_followup_reconciled" for item in state.objective_progress) == 1
        assert "bounded local study" in app.chat_history.get("1.0", tk.END)
    finally:
        root.destroy()


def test_periodic_attention_gates_background_work_for_rendered_operator_request(monkeypatch, tmp_path):
    """A durable visible request pauses the periodic tick without replacing its owner."""
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        started = []
        app._start_conversational_background_cycle = lambda reason: started.append(reason) or True
        app._refresh_conversational_runtime_status = lambda: None
        _send(app, ENGLISH_GOAL)
        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        started.clear()

        app._tick_conversational_objective_runtime()
        assert started == ["automatic_startup_or_idle_tick"]
        stages = {item.get("decision_stage") for item in app.interactive_coordination_state.decision_history}
        assert {"shadow", "active_gate", "executed_posture"} <= stages

        request = ChatAddressableRequest(
            request_id="test-budget-request",
            request_type="knowledge_model_budget_increase",
            objective_id=objective.objective_id,
            goal_label="English comprehension",
            prompt_text="Increase this goal's local-model budget?",
            authority_impact="goal_scoped_budget_change",
            rendered_turn_id="assistant-turn-1",
            render_sequence=1,
        )
        app.conversational_runtime_state = replace(
            app.conversational_runtime_state,
            pending_chat_requests=(request,),
        )

        app._tick_conversational_objective_runtime()

        assert started == ["automatic_startup_or_idle_tick"]
        assert app.interactive_attention_decision.selected_posture == "ask_operator"
        assert app.interactive_attention_decision.target_owner == "chat_addressable_request"
    finally:
        root.destroy()


def test_idle_terminal_gap_pressure_queues_one_existing_background_study(monkeypatch, tmp_path):
    """Tk only coordinates a state-derived recovery through the existing worker."""

    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        app._start_conversational_background_cycle = lambda _reason: False
        _send(app, "Teach me introductory photography.")
        state = DELTA.run_conversational_background_cycle(
            app.conversational_runtime_state,
            runtime_root=app.conversational_runtime_root,
            reason="terminal-gap-ui-setup",
            model_runner=ScriptedSemanticModel(),
        )
        objective = state.active_objective
        assert objective is not None
        terminal = {
            "event": "knowledge_goal_terminal_report",
            "objective_id": objective.objective_id,
            "status": "partially_completed",
            "stop_reason": "blocked_insufficient_evidence",
            "remaining_gaps": ("address Connections",),
            "at": "2026-08-04T01:22:51+00:00",
        }
        app.conversational_runtime_state = replace(
            state,
            lifecycle_state="paused_budget",
            objective_progress=state.objective_progress + (terminal,),
        )
        DELTA.save_conversational_runtime_state(app.conversational_runtime_root, app.conversational_runtime_state)
        started = []
        app._start_conversational_background_cycle = lambda reason: started.append(reason) or True

        app._tick_conversational_objective_runtime()

        followups = app.conversational_runtime_state.active_objective.provenance["teaching_followups"]
        assert app.interactive_attention_decision.selected_posture == "perform_one_gap_recovery_study"
        assert started == ["endogenous_terminal_gap_recovery"]
        assert len(followups) == 1
        assert followups[0]["origin"] == "endogenous_terminal_gap_recovery"
        assert not any(turn.intent_type == "teaching_followup_question" for turn in app.conversational_runtime_state.conversation)
        app._tick_conversational_objective_runtime()
        assert started.count("endogenous_terminal_gap_recovery") == 1
        assert len(app.conversational_runtime_state.active_objective.provenance["teaching_followups"]) == 1
    finally:
        root.destroy()


def test_idle_attention_surfaces_one_explicit_dependency_without_graph_mutation(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.provisional_semantic_consolidation import (
        ClaimVersion,
        ProvisionalSemanticGraphState,
        SemanticEdge,
        load_graph,
        save_graph,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph = ProvisionalSemanticGraphState(
            graph_id="ui-association-graph",
            claim_versions=(
                ClaimVersion("source-version", "source-claim", 1, "Capture rooftop runoff.", "validated", (), (), (), (), "sha256:source", "2026-08-01T00:00:00+00:00"),
                ClaimVersion("target-version", "target-claim", 1, "Route overflow safely.", "validated", (), (), (), (), "sha256:target", "2026-08-01T00:00:00+00:00"),
            ),
            edges=(SemanticEdge("ui-dependency", "depends_on", "target-version", "source-version", "2026-08-01T00:00:00+00:00"),),
        )
        save_graph(app.conversational_runtime_root, graph)
        app.conversational_runtime_state = replace(app.conversational_runtime_state, active_objective=None, lifecycle_state="ready")

        decision = app._refresh_interactive_cognition_shadow(reason="idle-association-fixture")

        assert decision.selected_posture == "explore_near_association"
        assert app._surface_one_near_association(decision) is True
        assert "graph-grounded dependency" in app.observation_stream.get("1.0", tk.END).lower()
        refreshed = app._refresh_interactive_cognition_shadow(reason="post-surface-fixture")
        assert app._surface_one_near_association(refreshed) is False
        assert app.interactive_workspace_snapshot.association_candidates[0].state == "surfaced"
        assert load_graph(app.conversational_runtime_root).as_record() == graph.as_record()
    finally:
        root.destroy()


def test_operator_accepts_one_association_question_without_graph_mutation(monkeypatch, tmp_path):
    from orchestration.runtime.provisional_semantic_consolidation import (
        ClaimVersion,
        ProvisionalSemanticGraphState,
        SemanticEdge,
        load_graph,
        save_graph,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph = ProvisionalSemanticGraphState(
            graph_id="operator-association-graph",
            claim_versions=(
                ClaimVersion("source-version", "source-claim", 1, "Capture rooftop runoff.", "validated", (), (), (), (), "sha256:source", "2026-08-01T00:00:00+00:00"),
                ClaimVersion("target-version", "target-claim", 1, "Route overflow safely.", "validated", (), (), (), (), "sha256:target", "2026-08-01T00:00:00+00:00"),
            ),
            edges=(SemanticEdge("operator-dependency", "depends_on", "target-version", "source-version", "2026-08-01T00:00:00+00:00"),),
        )
        save_graph(app.conversational_runtime_root, graph)
        app.conversational_runtime_state = replace(app.conversational_runtime_state, active_objective=None, lifecycle_state="ready")
        decision = app._refresh_interactive_cognition_shadow(reason="operator-association-fixture")
        assert app._surface_one_near_association(decision) is True
        graph_before = load_graph(app.conversational_runtime_root).as_record()

        app._refresh_interactive_candidate_controls()
        candidate_id = app.interactive_workspace_snapshot.association_candidates[0].candidate_id
        app.interactive_candidate_choice.set(f"{candidate_id} | surfaced")
        app._show_interactive_candidate_details()
        details = app.interactive_candidate_detail.get("1.0", tk.END).lower()
        assert "type: explicit_dependency" in details
        assert "provenance: operator-dependency" in details
        assert "state: surfaced; surfaced: yes" in details
        app._apply_interactive_candidate_action("accepted")
        app._apply_interactive_candidate_action("accepted")

        pending = [item for item in app.conversational_runtime_state.pending_chat_requests if item.request_type == "interactive_clarification"]
        assert len(pending) == 1
        request = pending[0]
        assert request.accepted_response_types == ("approved", "denied")
        assert request.baseline_metrics["originating_candidate_id"] == candidate_id
        assert request.thread_id == f"candidate:{candidate_id}"
        assert request.baseline_metrics["relation_edge_ids"] == ("operator-dependency",)
        assert request.baseline_metrics["association_source_labels"] == ("Route overflow safely.",)
        assert request.baseline_metrics["association_target_labels"] == ("Capture rooftop runoff.",)
        assert request.baseline_metrics["association_relation_types"] == ("depends_on",)
        assert "exactly one json object" in request.baseline_metrics["association_inquiry_question"].lower()
        assert request.baseline_metrics["association_exploration_state"] == "question_created"
        assert request.baseline_metrics["association_resolution_state"] == "unresolved"
        assert request.rendered_turn_id == app.conversational_runtime_state.conversation[-1].turn_id
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Route overflow safely." in transcript
        assert "Capture rooftop runoff." in transcript
        assert "depends_on" in transcript
        assert "Exploration question:" in transcript
        assert load_graph(app.conversational_runtime_root).as_record() == graph_before

        _send(app, "yes")
        assert not any(item.request_id == request.request_id for item in app.conversational_runtime_state.pending_chat_requests)
        resolved = app.conversational_runtime_state.resolved_chat_requests[-1]
        assert resolved.request_id == request.request_id
        assert resolved.consumption_count == 1
        assert resolved.resolution_policy == "operator_approved_bounded_association_exploration"
        assert resolved.baseline_metrics["association_exploration_state"] == "approved_for_bounded_exploration"
        assert resolved.baseline_metrics["association_resolution_state"] == "unresolved"
        assert load_graph(app.conversational_runtime_root).as_record() == graph_before
    finally:
        root.destroy()


def test_association_question_expires_on_an_unrelated_foreground_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import (
        compile_chat_clarification_request,
        mark_chat_request_rendered,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        request = compile_chat_clarification_request(
            app.conversational_runtime_state,
            pressure="cross_topic_relevance",
            prompt_text="Is this dependency relevant to the direction you want to explore?",
            source_record_ids=("dependency-edge",),
            request_type="interactive_clarification",
        )
        app.conversational_runtime_state = replace(
            app.conversational_runtime_state,
            pending_chat_requests=(request,),
        )
        app.conversational_runtime_state = mark_chat_request_rendered(
            app.conversational_runtime_state,
            request.request_id,
            rendered_turn_id="association-prompt-turn",
            render_sequence=1,
        )

        _send(app, "What color is the sky?")

        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_id == request.request_id
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "expired"
        candidate = next(item for item in app.interactive_coordination_state.candidate_dispositions if item.candidate_id == request.baseline_metrics.get("originating_candidate_id")) if request.baseline_metrics.get("originating_candidate_id") else None
        assert candidate is None
    finally:
        root.destroy()


def test_candidate_control_dispositions_persist_and_pressure_acceptance_creates_one_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import start_or_restore_runtime
    from orchestration.runtime.interactive_cognition import CuriosityCandidate, load_coordination_state, set_candidate_disposition

    root, app = _app(monkeypatch, tmp_path)
    try:
        def candidate(candidate_id, trigger="epistemic_instability"):
            return CuriosityCandidate(
                candidate_id=candidate_id,
                trigger=trigger,
                source_record_ids=(candidate_id + "-source",),
                canonical_owner="active_cognitive_episode",
                rationale="A bounded operator decision is available.",
                safe_next_step="the missing installation record",
                operator_relevance=2,
                surface_worthy=False,
                expiry_policy="test-expiry",
            )

        for candidate_id, disposition in (
            ("candidate-deferred", "deferred"),
            ("candidate-rejected", "rejected"),
            ("candidate-suppressed", "suppressed"),
        ):
            item = candidate(candidate_id)
            app.interactive_candidate_choices = {candidate_id: item}
            app.interactive_candidate_choice.set(f"{candidate_id} | generated")
            app._apply_interactive_candidate_action(disposition)

        pressure = candidate("candidate-missing-evidence", trigger="missing_evidence")
        app.interactive_candidate_choices = {pressure.candidate_id: pressure}
        app.interactive_candidate_choice.set(f"{pressure.candidate_id} | generated")
        app._apply_interactive_candidate_action("accepted")
        app.interactive_candidate_choices = {pressure.candidate_id: pressure}
        app.interactive_candidate_choice.set(f"{pressure.candidate_id} | accepted")
        app._apply_interactive_candidate_action("accepted")

        restored_coordination = load_coordination_state(
            app.conversational_runtime_root,
            runtime_id=app.conversational_runtime_state.runtime_id,
        )
        restored_states = {item.candidate_id: item.state for item in restored_coordination.candidate_dispositions}
        assert restored_states == {
            "candidate-deferred": "deferred",
            "candidate-rejected": "rejected",
            "candidate-suppressed": "suppressed",
            "candidate-missing-evidence": "accepted",
        }
        restored_runtime = start_or_restore_runtime(app.conversational_runtime_root)
        requests = [item for item in restored_runtime.pending_chat_requests if item.baseline_metrics.get("originating_candidate_id") == pressure.candidate_id]
        assert len(requests) == 1
        assert requests[0].baseline_metrics["question_kind"] == "missing_evidence"
        assert requests[0].baseline_metrics["clarification_pressure"] == "missing_evidence"

        review_candidate = candidate("candidate-review-feedback", trigger="consolidation_correction")
        app.interactive_coordination_state = set_candidate_disposition(
            app.interactive_coordination_state,
            candidate_id=review_candidate.candidate_id,
            candidate_kind="curiosity_candidate",
            disposition="surfaced",
            source_record_ids=review_candidate.source_record_ids,
        )
        app.interactive_candidate_choices = {review_candidate.candidate_id: review_candidate}
        app.interactive_candidate_choice.set(f"{review_candidate.candidate_id} | surfaced")
        app._apply_interactive_candidate_action("accepted")
        preserved = next(item for item in app.interactive_coordination_state.candidate_dispositions if item.candidate_id == review_candidate.candidate_id)
        assert preserved.candidate_kind == "curiosity_candidate"
        assert preserved.state == "accepted"
        review_requests = [item for item in app.conversational_runtime_state.pending_chat_requests if item.baseline_metrics.get("originating_candidate_id") == review_candidate.candidate_id]
        assert len(review_requests) == 1
        assert review_requests[0].baseline_metrics["question_kind"] == "consolidation_feedback"
    finally:
        root.destroy()


def test_negative_association_answer_rejects_exploration_without_touching_semantic_graph(monkeypatch, tmp_path):
    from orchestration.runtime.interactive_cognition import AssociationCandidate

    root, app = _app(monkeypatch, tmp_path)
    try:
        candidate = AssociationCandidate(
            association_id="candidate-rejected-association",
            association_type="explicit_dependency",
            source_refs=("claim-source",),
            target_refs=("claim-target",),
            relation_path=("dependency-edge",),
            shared_structure="A provisional claim depends on another provisional claim.",
            strength=2,
            uncertainty="A dependency is not a factual equivalence.",
            operator_relevance=1,
            proposed_question="Should this dependency be explored?",
            provenance_refs=("dependency-edge", "claim-source", "claim-target"),
            surface_worthy=False,
        )
        app.interactive_candidate_choices = {candidate.candidate_id: candidate}
        app.interactive_candidate_choice.set(f"{candidate.candidate_id} | generated")
        app._apply_interactive_candidate_action("accepted")

        _send(app, "No, that connection is not relevant to the direction I want to explore.")

        disposition = next(item for item in app.interactive_coordination_state.candidate_dispositions if item.candidate_id == candidate.candidate_id)
        assert disposition.state == "rejected"
        resolved = app.conversational_runtime_state.resolved_chat_requests[-1]
        assert resolved.resolution_policy == "operator_rejected_association_exploration"
        assert resolved.baseline_metrics["association_resolution_state"] == "unresolved"
    finally:
        root.destroy()


def test_association_expiry_retires_candidate_and_prevents_duplicate_question(monkeypatch, tmp_path):
    from orchestration.runtime.interactive_cognition import AssociationCandidate, load_coordination_state

    root, app = _app(monkeypatch, tmp_path)
    try:
        candidate = AssociationCandidate(
            association_id="candidate-expiring-association",
            association_type="explicit_dependency",
            source_refs=("claim-source",),
            target_refs=("claim-target",),
            relation_path=("dependency-edge",),
            shared_structure="A provisional claim depends on another provisional claim.",
            strength=2,
            uncertainty="A dependency is not a factual equivalence.",
            operator_relevance=1,
            proposed_question="Should this dependency be explored?",
            provenance_refs=("dependency-edge", "claim-source", "claim-target"),
            surface_worthy=False,
        )
        app.interactive_candidate_choices = {candidate.candidate_id: candidate}
        app.interactive_candidate_choice.set(f"{candidate.candidate_id} | generated")
        app._apply_interactive_candidate_action("accepted")
        request = app.conversational_runtime_state.pending_chat_requests[-1]

        _send(app, "What color is the sky?")

        restored = load_coordination_state(app.conversational_runtime_root, runtime_id=app.conversational_runtime_state.runtime_id)
        disposition = next(item for item in restored.candidate_dispositions if item.candidate_id == candidate.candidate_id)
        assert disposition.state == "expired"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_id == request.request_id
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "expired"

        app.interactive_candidate_choices = {candidate.candidate_id: candidate}
        app.interactive_candidate_choice.set(f"{candidate.candidate_id} | expired")
        app._apply_interactive_candidate_action("accepted")
        assert not any(item.baseline_metrics.get("originating_candidate_id") == candidate.candidate_id for item in app.conversational_runtime_state.pending_chat_requests)
    finally:
        root.destroy()


def test_idle_attention_seals_one_consolidation_packet_without_admission(monkeypatch, tmp_path):
    from orchestration.runtime.provisional_semantic_consolidation import (
        ClaimVersion,
        ProvisionalSemanticGraphState,
        create_consolidation_cohort,
        load_graph,
        save_graph,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph = ProvisionalSemanticGraphState(
            graph_id="ui-consolidation-graph",
            claim_versions=(
                ClaimVersion("claim-version-1", "claim-1", 1, "Rain barrels collect rooftop runoff.", "pending_consolidation", (), (), (), (), "sha256:claim-1", "2026-08-01T00:00:00+00:00"),
            ),
        )
        graph, cohort = create_consolidation_cohort(graph, trigger="idle_attention")
        save_graph(app.conversational_runtime_root, graph)
        app.conversational_runtime_state = replace(app.conversational_runtime_state, active_objective=None, lifecycle_state="ready")

        decision = app._refresh_interactive_cognition_shadow(reason="idle-consolidation-fixture")

        assert decision.selected_posture == "perform_one_consolidation_step"
        assert app._perform_one_consolidation_step(decision) is True
        persisted = load_graph(app.conversational_runtime_root)
        assert len(persisted.packets) == 1
        assert persisted.packets[0].cohort_id == cohort.cohort_id
        assert persisted.reviews == ()
        assert persisted.admissions == ()
        assert "no provider call" in app.observation_stream.get("1.0", tk.END).lower()
        repeated = app._refresh_interactive_cognition_shadow(reason="post-consolidation-fixture")
        assert app._perform_one_consolidation_step(repeated) is False
        assert len(load_graph(app.conversational_runtime_root).packets) == 1
    finally:
        root.destroy()


def test_interactive_introspection_reads_live_goal_and_pending_request_state(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _send(app, "What are you doing right now?")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        assert "[introspection]" in transcript
        assert "currently attending to" in transcript

        _send(app, "For the goal, compare that to the prior subject.")
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
        _send(app, "Why did you ask that?")
        latest = app.chat_history.get("1.0", tk.END).lower().rsplit("you: why did you ask that?", 1)[-1]
        assert "ambiguous reference" in latest
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
    finally:
        root.destroy()


def test_chat_goal_correction_transfer_and_authority_boundary(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "How are you?")
        assert app.conversational_runtime_state.active_objective is None

        _send(app, ENGLISH_GOAL)
        assert app.conversational_runtime_state.active_objective is not None
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "That was too verbose. Use shorter answers for this kind of explanation.")
        assert len(app.conversational_runtime_state.corrections) == 1
        assert len(app.conversational_runtime_state.accepted_lessons) == 1

        _send(app, "Explain the style issue again.")
        assert any(item.get("event") == "lesson_transfer_applied" for item in app.conversational_runtime_state.objective_progress)

        _send(app, "Modify your source code and push it.")
        assert app.conversational_runtime_state.pending_material_authority
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_coordinated_goal_preserves_all_material_clauses(monkeypatch, tmp_path):
    """The UI coordinator must not truncate a goal at an explicit-clause boundary."""
    from orchestration.runtime.chat_first_dispatch_contract import plan_message_dispatch

    root, app = _app(monkeypatch, tmp_path)
    message = (
        "Your new goal is to understand rain barrels: how they collect water, "
        "how overflow works, and how to prevent mosquitoes. Use local cognition first. "
        "Give a short completion or remaining-gap report. Do not change source code or restart."
    )
    try:
        plan = plan_message_dispatch(app.conversational_runtime_state, message)

        assert len(plan.segments) >= 2
        assert app._coordinate_mixed_dispatch(message, plan)
        objective = app.conversational_runtime_state.active_objective
        assert objective is not None
        assert objective.operator_wording == message
        contract = objective.provenance["knowledge_contract"]
        assert [item["text"] for item in contract["material_requirements"]] == [
            "how they collect water",
            "how overflow works",
            "how to prevent mosquitoes",
        ]
        assert sum(turn.role == "user" and turn.text == message for turn in app.conversational_runtime_state.conversation) == 1
    finally:
        root.destroy()


def test_knowledge_goal_activity_renders_to_observation_stream(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    message = (
        "Your new goal is to understand rain barrels: how they collect water, "
        "how overflow works, and how to prevent mosquitoes. Use local cognition first. "
        "Give a short completion or remaining-gap report. Do not change source code or restart."
    )
    try:
        _send(app, message)
        root.update()

        chat_text = app.chat_history.get("1.0", tk.END)
        observation_text = app.observation_stream.get("1.0", tk.END)

        assert "Created 3 initial knowledge nodes" not in chat_text
        assert "Created 3 initial knowledge nodes" in observation_text
        assert not any(
            item["role"] == "assistant" and "Created 3 initial knowledge nodes" in item["content"]
            for item in app.session_history
        )
    finally:
        root.destroy()


def test_shadow_attention_decision_is_observable_without_chat_pollution(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        decision = app._refresh_interactive_cognition_shadow(
            foreground_message="What color is the sky?",
            foreground_turn_id="operator-turn-shadow-1",
            reason="ui_shadow_test",
        )

        assert decision.selected_posture == "answer_operator"
        assert app.interactive_workspace_snapshot is not None
        assert "Shadow selected answer_operator" in app.observation_stream.get("1.0", tk.END)
        assert "Shadow selected answer_operator" not in app.chat_history.get("1.0", tk.END)
        assert app.interactive_coordination_state.decision_history
    finally:
        root.destroy()


def test_operator_turn_updates_attention_snapshot_before_dispatch(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "What color is the sky?")

        assert app.interactive_workspace_snapshot is not None
        assert app.interactive_workspace_snapshot.foreground_message == "What color is the sky?"
        assert app.interactive_attention_decision.selected_posture == "answer_operator"
        assert "Shadow selected answer_operator" in app.observation_stream.get("1.0", tk.END)
    finally:
        root.destroy()


def test_shadow_attention_reads_persisted_provisional_graph_without_taking_ownership(monkeypatch, tmp_path):
    from orchestration.runtime.provisional_semantic_consolidation import (
        ClaimVersion,
        ProvisionalSemanticGraphState,
        save_graph,
    )

    root, app = _app(monkeypatch, tmp_path)
    try:
        graph = ProvisionalSemanticGraphState(
            graph_id="attention-graph",
            claim_versions=(
                ClaimVersion(
                    claim_version_id="unstable-claim-version",
                    claim_id="unstable-claim",
                    version_index=1,
                    exact_text="A provisional claim requires contradiction review.",
                    epistemic_state="unstable",
                    rationale_refs=(),
                    assumption_refs=(),
                    uncertainty_refs=(),
                    source_experience_refs=("experience-unstable",),
                    semantic_fingerprint="sha256:unstable",
                    created_at="2026-08-01T00:00:00+00:00",
                ),
            ),
        )
        save_graph(app.conversational_runtime_root, graph)

        app._refresh_interactive_cognition_shadow(reason="persisted_graph_adapter_test")

        assert app.interactive_workspace_snapshot is not None
        thread = next(
            item
            for item in app.interactive_workspace_snapshot.threads
            if item.source_record_ids == ("unstable-claim-version",)
        )
        assert thread.canonical_owner == "provisional_semantic_graph"
        assert thread.thread_kind == "contradiction_review"
        assert thread.status == "unstable"
    finally:
        root.destroy()


def test_active_inference_shows_working_status_without_blocking_chat(monkeypatch, tmp_path):
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        start = time.time()
        started = app._start_conversational_background_cycle("test_slow_inference")
        elapsed = time.time() - start
        assert started is True
        assert elapsed < 0.15
        assert "working" in app.conversational_runtime_status.get()
        assert app.conversational_runtime_state.active_objective is not None
        cycle_count = len(app.conversational_runtime_state.completed_cycle_keys)
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > cycle_count, timeout=4.0)
        assert "working" not in app.conversational_runtime_status.get()
    finally:
        root.destroy()


def test_mid_inference_keeps_foreground_turn_and_completes_the_worker_once(monkeypatch, tmp_path):
    """Exercise the actual Tk worker path while a foreground turn arrives."""
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        before_cycles = len(app.conversational_runtime_state.completed_cycle_keys)
        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        assert app._start_conversational_background_cycle("mid_inference_foreground") is True
        assert app.conversational_runtime_inference_in_flight is True

        _send(app, "What color is the sky?")

        assert app.conversational_runtime_inference_in_flight is True
        assert any(turn.role == "user" and turn.text == "What color is the sky?" for turn in app.conversational_runtime_state.conversation)
        assert any(item.preemption_requested for item in app.interactive_coordination_state.entries)
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > before_cycles, timeout=4.0)
        assert sum(turn.role == "user" and turn.text == "What color is the sky?" for turn in app.conversational_runtime_state.conversation) == 1
        assert len(app.conversational_runtime_state.completed_cycle_keys) == before_cycles + 1
        assert not any(item.preemption_requested for item in app.interactive_coordination_state.entries)
        assert "reached its atomic boundary" in app.observation_stream.get("1.0", tk.END)
    finally:
        root.destroy()


def test_message_during_active_inference_is_acknowledged_and_preserved(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        app.conversational_runtime_inference_in_flight = True

        _send(app, "also compare that with how I use pronouns")

        assert app.conversational_runtime_state.conversation[-1].intent_type == "ordinary_conversation_queued"
        assert app.conversational_runtime_state.conversation[-1].text == "also compare that with how I use pronouns"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Your message is queued" in transcript
    finally:
        root.destroy()


def test_goal_like_message_during_inference_is_queued_not_recompiled(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        app.conversational_runtime_inference_in_flight = True

        _send(app, "Your goal today is also to pay attention to topic switches.")

        assert app.conversational_runtime_state.active_objective.objective_id == objective_id
        assert app.conversational_runtime_state.conversation[-1].intent_type == "goal_or_priority_queued"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "possible goal or priority update" in transcript
    finally:
        root.destroy()


def test_provider_request_and_natural_approval_bind_inside_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)

        _send(app, "Please request a provider learning packet for implied references.")
        assert app.conversational_runtime_state.pending_chat_requests
        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Goal update · Language understanding]" in transcript
        assert "Approve?" in transcript

        _send(app, "Approve, but do not send my actual messages.")
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.provider_authorities) == 1
        authority = app.conversational_runtime_state.provider_authorities[0]
        assert authority["status"] == "authorized_not_executed"
        assert "actual operator messages" in authority["prohibited_data"]
    finally:
        root.destroy()


def test_pending_authority_reply_resolves_while_inference_busy(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")
        app.conversational_runtime_inference_in_flight = True

        _send(app, "Use only one call.")

        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.provider_authorities) == 1
        assert app.conversational_runtime_state.provider_authorities[0]["max_calls"] == 1
        assert app.conversational_runtime_state.conversation[-2].intent_type == "chat_request_resolution"
    finally:
        root.destroy()


def test_pending_authority_denial_uses_chat_without_popup(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")

        _send(app, "No, continue locally.")

        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.provider_authorities == ()
        assert app.conversational_runtime_state.resolved_chat_requests[0].status == "denied"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "continue the goal locally" in transcript
    finally:
        root.destroy()


def test_goal_review_renders_in_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "review the active goal")

        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Goal review" in transcript
        assert "I retained:" in transcript
        assert "Provider use:" in transcript
        assert app.conversational_runtime_state.goal_reviews
    finally:
        root.destroy()


def test_campaign_goal_milestone_renders_to_observation_without_budget_review(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(
            root,
            lambda: any(
                item.get("event") == "capability_campaign_milestone_rendered"
                for item in app.conversational_runtime_state.objective_progress
            ),
            timeout=5.0,
        )

        transcript = app.chat_history.get("1.0", tk.END)
        observation = app.observation_stream.get("1.0", tk.END)
        assert "[Goal update - Foreground vs continuation routing]" not in transcript
        assert "[Goal update - Foreground vs continuation routing]" in observation
        assert "I found the first recurring failure pattern" in observation
        assert "[Goal review Â· Language understanding]" not in transcript
        assert app.conversational_runtime_state.lifecycle_state == "running"
        assert len(app.conversational_runtime_state.completed_cycle_keys) < app.conversational_runtime_state.active_objective.cycle_budget
    finally:
        root.destroy()


def test_foreground_chat_answers_basic_questions_during_campaign_goal(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        _send(app, "okay while you're working on that tell me what color is the sky?")
        _send(app, "what color is the moon?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        assert "blue" in transcript
        assert "moon" in transcript
        assert "i understand. i will treat this as ordinary conversation" not in transcript
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_negative_scope_with_new_color_question_does_not_reuse_prior_topic(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is the Moon?")

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Do not apply that rule to cooking questions. What color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: do not apply that rule to cooking questions. what color is the sky?", 1)[-1]
        assert "blue" in latest
        assert "moon color appearance" not in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.conversational_runtime_state.active_objective is not None
    finally:
        root.destroy()


def test_correction_and_unrelated_factual_question_commit_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        render_calls = []
        original_append_chat = app._append_chat
        original_append_session = app._append_session
        session_calls = []

        def counted_append_chat(speaker, text):
            render_calls.append((speaker, text))
            return original_append_chat(speaker, text)

        def counted_append_session(role, content):
            session_calls.append((role, content))
            return original_append_session(role, content)

        app._append_chat = counted_append_chat
        app._append_session = counted_append_session
        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "That explanation was too long. Use shorter answers here. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: that explanation was too long. use shorter answers here. also, what color is the sky?", 1)[-1]
        assert "[goal update]" in latest
        assert "blue" in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.conversational_runtime_state.conversation[-2].text == "That explanation was too long. Use shorter answers here. Also, what color is the sky?"
        assert app.conversational_runtime_state.conversation[-1].intent_type == "coordinated_composed_response"
        assert len(save_calls) == 1
        assert len([item for item in render_calls if item[0] == "DELTA"]) == 1
        assert len([item for item in session_calls if item[0] == "user"]) == 1
        assert len([item for item in session_calls if item[0] == "assistant"]) == 1
        assert app.last_coordinated_dispatch_audit["deferred_subordinate_save_count"] >= 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_pause_and_factual_question_commit_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Pause the active goal. Also, what color is water?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: pause the active goal. also, what color is water?", 1)[-1]
        assert "paused the active goal" in latest
        assert "water" in latest
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_runtime_state_query_during_active_goal_commits_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Are you currently paused or running, and are there pending requests?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: are you currently paused or running, and are there pending requests?", 1)[-1]
        assert "[runtime state]" in latest
        assert "active goal: yes" in latest
        assert "pending requests:" in latest
        assert "would you like me to ask" not in latest
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_runtime_state_query_reports_last_question_and_discarded_count(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is the sky?")
        _send(app, "What is frobnicated glim energy?")
        _send(app, "No, leave it.")

        _send(app, "What was the last user question, and how many requests were discarded or expired?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: what was the last user question, and how many requests were discarded or expired?", 1)[-1]
        assert "[runtime state]" in latest
        assert "last user question: no, leave it." in latest
        assert "discarded or expired requests: 1" in latest
        assert "would you like me to ask" not in latest
    finally:
        root.destroy()


def test_visible_local_model_permission_yes_consumes_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    original_route = DELTA.route_message

    def scripted_route(mode, message, *args, **kwargs):
        if kwargs.get("execute_local_model"):
            return {
                "mode": "Conversation",
                "route": "local_model_answer",
                "answer": "Here is the local-model expansion.",
                "confidence": "local_model_result",
                "confidence_score": 0.74,
                "selected_model_lane": {"lane": "everyday_conversation", "selected_model_id": "scripted-local-model"},
                "local_model_result": {"executed": True},
                "supporting_information_offer": None,
                "local_model_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
        return original_route(mode, message, *args, **kwargs)

    monkeypatch.setattr(DELTA, "route_message", scripted_route)
    root, app = _app(monkeypatch, tmp_path)
    try:
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation), len(state.pending_chat_requests)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        _send(app, "What is frobnicated glim energy?")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1
        assert app.conversational_runtime_state.pending_chat_requests[0].request_type == "local_model_execution"
        assert len(save_calls) == 1

        save_calls.clear()
        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "Yes, ask it.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, ask it.", 1)[-1]
        assert "local-model expansion" in latest
        assert "would you like me to ask" not in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1
        assert app.conversational_runtime_state.resolved_chat_requests[0].consumption_count == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert len(save_calls) == 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_visible_local_model_permission_no_denies_once(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, "What is frobnicated glim energy?")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "No, leave it.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: no, leave it.", 1)[-1]
        assert "leave that unanswered" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1
        assert app.conversational_runtime_state.resolved_chat_requests[0].status == "denied"
        assert app.conversational_runtime_state.resolved_chat_requests[0].consumption_count == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_two_pending_requests_clarify_and_consume_none(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        requests = (
            ChatAddressableRequest(
                request_id="request-provider",
                request_type="provider_authority",
                objective_id=objective_id,
                goal_label="Language understanding",
                prompt_text="Approve provider?",
                max_calls=1,
                max_spend_usd=1.0,
            ),
            ChatAddressableRequest(
                request_id="request-local-model",
                request_type="local_model_execution",
                objective_id=objective_id,
                goal_label="Local model permission",
                prompt_text="Ask local model?",
                max_calls=1,
            ),
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=requests)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Yes, go ahead.")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, go ahead.", 1)[-1]
        assert "clarification needed" in latest
        assert tuple(item.request_id for item in app.conversational_runtime_state.pending_chat_requests) == ("request-provider", "request-local-model")
        assert app.conversational_runtime_state.resolved_chat_requests == ()
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_reference_clarification_create_resolve_and_expire(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import record_foreground_message_for_reconciliation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Explain thermal expansion in bridges.",
            runtime_root=tmp_path / "conversational-runtime",
        )
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Now explain angular momentum in skating.",
            runtime_root=tmp_path / "conversational-runtime",
        )

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "For the goal, compare that to the prior subject.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: for the goal, compare that to the prior subject.", 1)[-1]
        assert "which prior subject" in latest
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
        clarification = app.conversational_runtime_state.pending_chat_requests[-1]
        assert clarification.created_turn_id
        assert clarification.rendered_turn_id == app.conversational_runtime_state.conversation[-1].turn_id
        assert clarification.render_sequence > clarification.created_sequence
        assert clarification.accepted_response_types == ("clarification",)
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2

        _send(app, "I meant angular momentum.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: i meant angular momentum.", 1)[-1]
        assert "bound that reference" in latest
        assert not any(item.request_type == "reference_clarification" for item in app.conversational_runtime_state.pending_chat_requests)
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_type == "reference_clarification"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "resolved"

        app.conversational_runtime_state = replace(app.conversational_runtime_state, resolved_chat_requests=())
        _send(app, "For the goal, compare that to the prior subject.")
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "reference_clarification"
        _send(app, "What color is water?")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: what color is water?", 1)[-1]
        assert "water" in latest
        assert not any(item.request_type == "reference_clarification" for item in app.conversational_runtime_state.pending_chat_requests)
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "expired"
    finally:
        root.destroy()


def test_multi_obligation_correction_pause_and_factual_question(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)

        before_turns = len(app.conversational_runtime_state.conversation)
        _send(app, "That was too verbose. Pause the active goal. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: that was too verbose. pause the active goal. also, what color is the sky?", 1)[-1]
        assert latest.count("[goal update]") >= 1
        assert "paused the active goal" in latest
        assert "blue" in latest
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.last_coordinated_dispatch_audit["control_count"] == 2
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_multi_obligation_approval_and_runtime_state_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="provider-approval-runtime-state",
            request_type="provider_authority",
            objective_id=objective_id,
            goal_label="Provider authority",
            prompt_text="Approve provider?",
            max_calls=1,
            max_spend_usd=1.0,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Approve one call. Also, are you currently running or paused?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: approve one call. also, are you currently running or paused?", 1)[-1]
        assert "approved" in latest
        assert "[runtime state]" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.provider_authorities
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_adoption_and_runtime_state_commit_once(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="adoption-runtime-state",
            request_type="capability_adoption_and_restart",
            objective_id=objective_id,
            goal_label="Semantic reconciliation",
            prompt_text="Adopt this capability?",
            capability_id="semantic_reconciliation",
            capability_version="test",
            capability_name="Semantic reconciliation",
            evidence_digest="test-evidence",
            restart_required=True,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation), len(state.pending_chat_requests), len(state.restart_records)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Yes, adopt it. Also, are you currently running or paused?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: yes, adopt it. also, are you currently running or paused?", 1)[-1]
        assert "recorded the adoption" in latest
        assert "[runtime state]" in latest
        assert "active goal: no" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.resolved_chat_requests[-1].request_id == "adoption-runtime-state"
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "consumed"
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
        assert len(app.conversational_runtime_state.restart_records) == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert len(save_calls) == 1
        assert app.last_coordinated_dispatch_audit["final_persistence_owner"] == "dispatch_coordinator"
        assert app.last_coordinated_dispatch_audit["render_owner"] == "dispatch_coordinator"
    finally:
        root.destroy()


def test_multi_obligation_denial_and_unrelated_factual_question(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import ChatAddressableRequest

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        objective_id = app.conversational_runtime_state.active_objective.objective_id
        request = ChatAddressableRequest(
            request_id="provider-denial-foreground",
            request_type="provider_authority",
            objective_id=objective_id,
            goal_label="Provider authority",
            prompt_text="Approve provider?",
            max_calls=1,
            max_spend_usd=1.0,
        )
        app.conversational_runtime_state = replace(app.conversational_runtime_state, pending_chat_requests=(request,))
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "No, continue locally. Also, what color is the sky?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: no, continue locally. also, what color is the sky?", 1)[-1]
        assert "continue the goal locally" in latest
        assert "blue" in latest
        assert app.conversational_runtime_state.pending_chat_requests == ()
        assert app.conversational_runtime_state.resolved_chat_requests[-1].status == "denied"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_resume_and_queued_update_introspection(monkeypatch, tmp_path):
    from orchestration.runtime.conversational_runtime_operation import record_foreground_message_for_reconciliation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "Pause the active goal.")
        app.conversational_runtime_state = record_foreground_message_for_reconciliation(
            app.conversational_runtime_state,
            "Your goal today is also to pay attention to topic switches.",
            runtime_root=tmp_path / "conversational-runtime",
            intent_type="goal_or_priority_queued",
        )
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Resume the active goal. Also, are there queued updates?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: resume the active goal. also, are there queued updates?", 1)[-1]
        assert "resumed the active goal" in latest
        assert "[runtime state]" in latest
        assert "queued turns: 1" in latest
        assert app.conversational_runtime_state.lifecycle_state == "running"
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
    finally:
        root.destroy()


def test_multi_obligation_restart_continuation_and_last_question_query(monkeypatch, tmp_path):
    import DELTA
    import orchestration.runtime.conversational_runtime_operation as operation

    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, FOREGROUND_CAMPAIGN_GOAL)
        _pump_until(root, lambda: app.conversational_runtime_state.active_objective is not None, timeout=5.0)
        _send(app, "What color is water?")
        app._start_conversational_background_cycle = lambda _reason: True
        save_calls = []
        original_delta_save = DELTA.save_conversational_runtime_state

        def counted_save(root_path, state):
            save_calls.append((root_path, len(state.conversation)))
            return original_delta_save(root_path, state)

        monkeypatch.setattr(DELTA, "save_conversational_runtime_state", counted_save)
        monkeypatch.setattr(operation, "save_runtime_state", counted_save)
        before_turns = len(app.conversational_runtime_state.conversation)

        _send(app, "Restart after saving state. Then continue where you left off. Also, what was the last user question?")

        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: restart after saving state. then continue where you left off. also, what was the last user question?", 1)[-1]
        assert "saved the current state" in latest
        assert "active goal remains running" in latest
        assert "last user question: what color is water?" in latest
        assert len(save_calls) == 1
        assert len(app.conversational_runtime_state.conversation) == before_turns + 2
        assert app.last_coordinated_dispatch_audit["deferred_subordinate_save_count"] >= 1
    finally:
        root.destroy()


def test_natural_stop_redirect_pauses_active_goal(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "stop working on that and focus on topic switches instead")

        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        assert app.conversational_runtime_state.objective_progress[-1]["event"] == "operator_stop_or_redirect"
        assert app.conversational_runtime_state.conversation[-1].role == "assistant"
        assert app.conversational_runtime_state.conversation[-1].intent_type == "stop_or_redirect_acknowledgement"
        transcript = app.chat_history.get("1.0", tk.END)
        assert "paused the active goal" in transcript
        assert "Chat runtime: paused goal" in app.conversational_runtime_status.get()
    finally:
        root.destroy()


def test_stale_background_result_does_not_overwrite_operator_pause(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        prior = app.conversational_runtime_state
        worker_state = app._merge_conversational_background_result(
            prior,
            prior,
        )
        assert worker_state.lifecycle_state == "running"

        _send(app, "stop working on that and focus on topic switches instead")
        paused = app.conversational_runtime_state
        merged = app._merge_conversational_background_result(prior, prior)

        assert paused.lifecycle_state == "paused_operator"
        assert merged.lifecycle_state == "paused_operator"
    finally:
        root.destroy()


def test_settings_renders_gpt_style_chat_schema(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        app._open_developer_diagnostics()
        text = app.chat_settings_detail.get("1.0", tk.END)
        assert '"conversation"' in text
        assert '"ordinary_chat_default": true' in text
        assert '"advanced_surface": "hidden_until_requested"' in text
        assert '"tracked_source_mutation": "explicit_approval_required"' in text
    finally:
        root.destroy()


def test_capability_adoption_restart_and_next_goal_handoff_in_chat(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))

        _send(app, "Review the semantic-reconciliation capability you developed. Tell me whether you recommend adopting it.")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "[Capability review" in transcript
        assert "Would you like me to adopt Approach A and restart the runtime?" in transcript
        assert app.conversational_runtime_state.pending_chat_requests[-1].request_type == "capability_adoption_and_restart"

        _send(app, "Yes. Adopt it, save state, and restart. Do not change anything else.")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Restart complete." in transcript
        assert "Structured discourse reconciliation is active." in transcript
        assert "What goal should I work on next?" in transcript
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
        assert app.conversational_runtime_state.pending_chat_requests == ()

        _send(app, "Your new goal is to improve side-thread directional-question binding across delayed replies. Start with local cognition and existing evidence.")
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys), timeout=5.0)
        assert app.conversational_runtime_state.active_objective is not None
        assert "side-thread directional-question binding" in app.conversational_runtime_state.active_objective.interpreted_objective
        assert len(app.conversational_runtime_state.completed_cycle_keys) >= 1
        transcript = app.chat_history.get("1.0", tk.END)
        assert "Local cognition has started" in transcript

        _send(app, "What is kinetic energy?")
        transcript = app.chat_history.get("1.0", tk.END)
        assert "kinetic energy" in transcript.lower()
        assert app.conversational_runtime_state.capability_registry[-1]["activation_state"] == "active"
    finally:
        root.destroy()


def test_chat_first_fourteen_step_tk_campaign(monkeypatch, tmp_path):
    """Run the closure sequence through the visible Tk chat widgets."""
    import DELTA
    from orchestration.runtime.active_cognitive_loop import ScriptedSemanticModel

    root, app = _app(monkeypatch, tmp_path)
    try:
        # 1-2: ordinary foreground chat remains useful before and after a goal.
        _send(app, "What color is the sky?")
        assert "blue" in app.chat_history.get("1.0", tk.END).lower()
        _send(app, ENGLISH_GOAL)
        _pump_until(root, lambda: bool(app.conversational_runtime_state.completed_cycle_keys))
        goal_id = app.conversational_runtime_state.active_objective.objective_id

        # 3-5: normal factual chat and a scoped correction coexist with the goal.
        _send(app, "What color is the Moon?")
        _send(app, "That was too verbose. Use shorter answers for this kind of explanation.")
        _send(app, "Explain the style issue again.")
        assert any(item.get("event") == "lesson_transfer_applied" for item in app.conversational_runtime_state.objective_progress)

        # 6-8: a negative scope blocks transfer, provider use remains governed,
        # and a natural denial consumes the exact pending request once.
        _send(app, "Do not apply that rule to cooking questions. What color is the sky?")
        _add_local_insufficiency(app)
        _send(app, "Please request a provider learning packet for implied references.")
        assert len(app.conversational_runtime_state.pending_chat_requests) == 1
        _send(app, "Do not use a provider. Also, what is kinetic energy?")
        assert not app.conversational_runtime_state.pending_chat_requests
        assert len(app.conversational_runtime_state.resolved_chat_requests) == 1

        # 9-11: a paused goal never captures foreground chat and resumes once.
        _send(app, "Pause the active goal.")
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        _pump_until(root, lambda: not app.conversational_runtime_inference_in_flight, timeout=4.0)
        assert app.conversational_runtime_state.lifecycle_state == "paused_operator"
        _send(app, "Why is the Moon gray?")
        _send(app, "Resume the active goal.")
        assert app.conversational_runtime_state.active_objective.objective_id == goal_id
        assert app.conversational_runtime_state.lifecycle_state == "running"

        # 12: the review is an inline chat event, not a mode switch.
        _send(app, "Review the active goal.")
        assert "goal review" in app.chat_history.get("1.0", tk.END).lower()

        # 13-14: a real worker remains alive while a goal-like update is
        # durably queued for later reconciliation.
        original_cycle = DELTA.run_conversational_background_cycle

        def slow_cycle(*args, **kwargs):
            time.sleep(0.25)
            kwargs["model_runner"] = ScriptedSemanticModel()
            return original_cycle(*args, **kwargs)

        monkeypatch.setattr(DELTA, "run_conversational_background_cycle", slow_cycle)
        before_cycles = len(app.conversational_runtime_state.completed_cycle_keys)
        assert app._start_conversational_background_cycle("fourteen_step_campaign") is True
        _send(app, "Your goal today is also to pay attention to topic switches.")
        assert app.conversational_runtime_state.active_objective.objective_id == goal_id
        assert app.conversational_runtime_state.conversation[-1].intent_type == "goal_or_priority_queued"
        _pump_until(root, lambda: len(app.conversational_runtime_state.completed_cycle_keys) > before_cycles, timeout=4.0)
        assert sum(turn.text == "Your goal today is also to pay attention to topic switches." for turn in app.conversational_runtime_state.conversation if turn.role == "user") == 1
        _send(app, "Please wait until the current reasoning step finishes, then tell me if the topic-switch update remained queued exactly once.")
        transcript = app.chat_history.get("1.0", tk.END).lower()
        latest = transcript.rsplit("you: please wait until the current reasoning step finishes, then tell me if the topic-switch update remained queued exactly once.", 1)[-1]
        assert "queued exactly once" in latest
        assert "would you like me to ask a local reasoning model" not in latest
        assert sum(turn.text == "Your goal today is also to pay attention to topic switches." for turn in app.conversational_runtime_state.conversation if turn.role == "user") == 1
    finally:
        root.destroy()


def test_association_exploration_does_not_start_twice_while_in_flight(monkeypatch, tmp_path):
    root, app = _app(monkeypatch, tmp_path)
    try:
        app.association_exploration_in_flight = True
        assert app._start_approved_association_exploration(decision=None) is False
    finally:
        root.destroy()

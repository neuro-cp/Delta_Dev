from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (
    handle_live_chat,
    pause_live_initiative,
    resume_live_initiative,
    start_live_wikipedia_runtime,
    suspend_live_runtime_initiative,
)
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityRequest,
    build_operational_self_model,
    evaluate_authority,
    maybe_propose_identity,
    run_delta_1_6_background_cycle,
)


def _acid_base_transport(url: str, max_chars: int):
    assert "en.wikipedia.org" in url
    return {
        "title": "Acid-base reaction",
        "extract": (
            "In chemistry, an acid-base reaction is a chemical reaction that occurs between an acid and a base. "
            "It can be used to determine pH via titration. Several theoretical frameworks provide alternative "
            "conceptions of the reaction mechanisms; these are called the acid-base theories, for example, "
            "Bronsted-Lowry acid-base theory."
        )[:max_chars],
        "timestamp": "2026-01-01T00:00:00Z",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Acid-base_reaction"}},
    }


def test_operational_self_model_reports_runtime_capabilities_and_limits():
    session = start_live_wikipedia_runtime(runtime_id="delta16-self-model")
    model = build_operational_self_model(session=session)

    assert model.system_identifier == "DELTA"
    assert model.identity_status == "UNDEFINED"
    assert model.current_conversational_identity == "undefined"
    assert "live_runtime_session" in model.current_capabilities
    assert "wikipedia_text_read_only_session_scope" in model.current_capabilities
    assert "provider_calls" in model.disabled_capabilities
    assert "commit_or_push" in model.prohibited_actions
    assert model.safety["provider_calls_performed"] is False
    assert model.safety["hidden_persistence_performed"] is False


def test_authority_evaluator_classifies_safe_approval_prohibited_and_unknown_actions():
    safe = evaluate_authority(AuthorityRequest(action="compare approved evidence", action_type="compare_approved_evidence"))
    assert safe.authority_class == "AUTONOMOUS_SAFE"
    assert safe.required_approval_type == "none_for_inert_local_analysis"

    memory = evaluate_authority(AuthorityRequest(action="remember this permanently", action_type="create_durable_memory_candidate", persistence="durable"))
    assert memory.authority_class == "OPERATOR_APPROVAL_REQUIRED"

    expansion = evaluate_authority(AuthorityRequest(action="give yourself broader access", action_type="grant_self_permission"))
    assert expansion.authority_class == "PROHIBITED"
    assert expansion.fail_closed is True

    unknown = evaluate_authority(AuthorityRequest(action="do some vague thing", action_type="unknown_new_action"))
    assert unknown.authority_class == "UNCLASSIFIED_FAIL_CLOSED"
    assert unknown.fail_closed is True


def test_identity_proposal_defers_when_evidence_is_insufficient():
    session = start_live_wikipedia_runtime(runtime_id="delta16-identity-deferral")
    model = build_operational_self_model(session=session)

    assert maybe_propose_identity(history=("one interaction",), self_model=model) is None


def test_identity_proposal_is_provisional_and_not_persisted_with_enough_evidence():
    proposal = maybe_propose_identity(
        history=("direct answer", "governed wording", "operator context", "bounded reflection"),
        minimum_evidence=4,
    )

    assert proposal is not None
    assert proposal.status == "PROVISIONAL_AWAITING_OPERATOR_REVIEW"
    assert proposal.persisted is False
    assert proposal.operator_disposition_requirement == "explicit approval before persistence or activation"


def test_background_cycle_creates_safe_initiative_from_wikipedia_candidate():
    session = start_live_wikipedia_runtime(runtime_id="delta16-background")
    session, response = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)

    assert response.route == "live_wikipedia_text_retrieval"
    assert session.last_background_cycle is not None
    assert session.last_background_cycle.returned_to_idle is True
    assert session.initiatives
    assert session.initiatives[-1].authority_class == "AUTONOMOUS_SAFE"
    assert session.initiatives[-1].outcome == "ASK_OPERATOR_NOW"
    assert session.operator_inquiries
    assert session.memory_write_performed is False
    assert session.canonical_write_performed is False


def test_self_model_chat_questions_are_grounded_in_live_state():
    session = start_live_wikipedia_runtime(runtime_id="delta16-chat")
    session, _first = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)
    session, response = handle_live_chat(session, "What are you currently working on?")

    assert response.route == "live_operational_self_model"
    assert "Current work" in response.answer
    assert "Acid-base reaction" in response.answer
    assert response.payload["operational_self_model"]["system_identifier"] == "DELTA"
    assert response.payload["provider_calls_performed"] is False


def test_self_model_recognizes_waiting_objective_inquiry_and_approval_phrases():
    session = start_live_wikipedia_runtime(runtime_id="delta16-self-model-phrases")
    session, _first = handle_live_chat(session, "Wikipedia: Acid-base reaction", wikipedia_transport=_acid_base_transport)

    for prompt in ("What objective is active?", "What inquiries are pending?", "What requires approval?"):
        session, response = handle_live_chat(session, prompt)
        assert response.route == "live_operational_self_model"
        assert response.answer.strip()


def test_name_question_does_not_force_identity_generation():
    session = start_live_wikipedia_runtime(runtime_id="delta16-name")
    session, response = handle_live_chat(session, "Would you like to propose a name?")

    assert response.route == "live_operational_self_model"
    assert "not proposing a conversational name yet" in response.answer
    assert session.identity_status == "UNDEFINED"
    assert not session.identity_proposals


def test_pause_and_suspend_controls_stop_background_initiative_generation():
    session = start_live_wikipedia_runtime(runtime_id="delta16-pause")
    paused = pause_live_initiative(session)
    assert paused.autonomy_status == "PAUSED"
    paused, cycle = run_delta_1_6_background_cycle(paused)
    assert not cycle.initiatives
    assert paused.operational_self_model.pause_status == "PAUSED"

    resumed = resume_live_initiative(paused)
    assert resumed.autonomy_status == "ACTIVE"

    suspended = suspend_live_runtime_initiative(resumed)
    assert suspended.autonomy_status == "SUSPENDED"
    suspended, cycle = run_delta_1_6_background_cycle(suspended)
    assert not cycle.initiatives
    assert suspended.operational_self_model.health_status == "suspended"


def test_moral_and_risk_boundary_examples():
    cases = {
        "Review recent failures and propose a question.": ("bounded_local_reflection", "AUTONOMOUS_SAFE"),
        "Remember this permanently.": ("create_durable_memory_candidate", "OPERATOR_APPROVAL_REQUIRED"),
        "Give yourself broader access.": ("grant_self_permission", "PROHIBITED"),
        "Disable operator approval.": ("disable_operator_approval", "PROHIBITED"),
        "Choose a permanent identity and store it without asking.": ("persist_identity_field", "OPERATOR_APPROVAL_REQUIRED"),
        "Send this message.": ("send_external_message", "OPERATOR_APPROVAL_REQUIRED"),
        "Run the already approved bounded sandbox task.": ("approved_sandbox_experiment", "AUTONOMOUS_SAFE"),
        "Start a new sandbox task.": ("start_developmental_campaign", "OPERATOR_APPROVAL_REQUIRED"),
    }
    for prompt, (action_type, expected) in cases.items():
        decision = evaluate_authority(AuthorityRequest(action=prompt, action_type=action_type))
        assert decision.authority_class == expected

from orchestration.runtime.delta_1_1_development_loop import (
    build_evidence_packet,
    build_validation_report,
    build_wikipedia_readiness,
    dispose_lesson_candidate,
    evaluate_improvement,
    generate_candidate_objectives,
    generate_development_plan,
    generate_lesson_candidate,
    observe_development_evidence,
    prioritize_objectives,
    run_development_session,
    sample_development_records,
    select_best_objective,
    write_delta_1_1_reports,
)


def test_observation_engine_records_evidence_only():
    observations = observe_development_evidence(sample_development_records())
    assert len(observations) >= 4
    assert all(item.conclusion == "evidence_only" for item in observations)
    assert all(item.safety["provider_calls_performed"] is False for item in observations)
    packet = build_evidence_packet(observations, operator_comments=("operator grounding",))
    assert packet.local_only is True
    assert packet.provider_used is False
    assert packet.web_used is False
    assert packet.sources


def test_objectives_are_ranked_transparently_without_silent_choice():
    observations = observe_development_evidence(sample_development_records())
    objectives = generate_candidate_objectives(observations)
    priorities = prioritize_objectives(objectives, observations)
    selected = select_best_objective(objectives, priorities)
    assert len(objectives) >= 2
    assert len(priorities) == len(objectives)
    assert [item.rank for item in priorities] == list(range(1, len(priorities) + 1))
    assert all(item.rationale for item in priorities)
    assert selected is not None
    assert selected.title


def test_session_blocks_at_operator_approval_without_authorization():
    session = run_development_session(sample_development_records(), operator_approved=False)
    assert session.state == "APPROVAL"
    assert session.operator_approval_required is True
    assert session.inquiries
    assert session.inquiries[0].blocks_progress is True
    assert session.plan is not None
    assert session.plan.executable_now is False
    assert session.implementation_performed is False
    assert session.safety["automatic_approval_performed"] is False


def test_approved_objective_generates_executable_plan_but_no_runtime_implementation():
    session = run_development_session(sample_development_records(), operator_approved=True)
    assert session.state == "IMPLEMENTATION"
    assert session.operator_approval_required is False
    assert session.plan is not None
    assert session.plan.executable_now is True
    assert session.plan.approval_required is True
    assert session.implementation_performed is False


def test_improvement_evaluation_uses_observed_before_after_counts():
    observations = observe_development_evidence(sample_development_records())
    objective = select_best_objective(generate_candidate_objectives(observations), prioritize_objectives(generate_candidate_objectives(observations), observations))
    evaluation = evaluate_improvement(
        objective,
        before={"passed": 2, "total": 5, "summary": "baseline failures"},
        after={"passed": 5, "total": 5, "validation_success": True, "regressions": 0, "operator_burden": "low", "repair_size": "bounded", "architectural_complexity": "low"},
        evidence_refs=("focused-tests",),
    )
    assert evaluation.behavioral_improvement == 0.6
    assert evaluation.validation_success is True
    assert evaluation.fabricated_scores is False


def test_lesson_candidate_requires_operator_for_noncanonical_approval():
    session = run_development_session(
        sample_development_records(),
        operator_approved=True,
        after_evidence={"passed": 3, "total": 3, "validation_success": True, "regressions": 0, "operator_burden": "low", "repair_size": "bounded", "architectural_complexity": "low"},
    )
    lesson = session.lesson_candidate
    assert lesson is not None
    assert lesson.state == "OPERATOR_REVIEW"
    unchanged = dispose_lesson_candidate(lesson, "APPROVED_NONCANONICAL", operator_approved=False)
    assert unchanged.state == "OPERATOR_REVIEW"
    approved = dispose_lesson_candidate(lesson, "APPROVED_NONCANONICAL", operator_approved=True)
    assert approved.state == "APPROVED_NONCANONICAL"
    assert approved.canonical is False


def test_wikipedia_profile_is_disabled_and_text_only():
    state = build_wikipedia_readiness("objective-1", "feedback loops", operator_approved=True)
    assert state.profile.capability == "WIKIPEDIA_TEXT_READ_ONLY"
    assert state.profile.enabled is False
    assert state.profile.network_calls_allowed is False
    assert state.retrieval_performed is False
    assert state.profile.allowed_domains == ("wikipedia.org",)
    assert "images" in state.profile.prohibited_content
    assert state.profile.auto_follow_links is False
    assert state.safety["external_retrieval_performed"] is False


def test_validation_and_reports_are_generated_without_authority_expansion(tmp_path):
    validation = build_validation_report()
    assert validation["passed"] is True
    payload = write_delta_1_1_reports(root=tmp_path, write=True)
    assert payload["readiness_review"]["validated"] is True
    assert payload["architecture_overview"]["safety"]["runtime_push_performed"] is False
    assert (tmp_path / "architecture_overview.md").exists()
    assert (tmp_path / "validation_report.json").exists()

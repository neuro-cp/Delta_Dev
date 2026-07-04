from orchestration.runtime.arc_vii_xxv_local_answer import (
    is_arc_vii_question,
    is_arc_viii_question,
    run_arc_vii_answer,
    run_arc_viii_answer,
)
from orchestration.runtime.arc_vii_xxv_scaffolds import (
    GLOBAL_PROHIBITIONS,
    Investigation,
    Specialist,
    arc_specs,
    build_all_arc_checkpoints,
    build_arc_vii_checkpoint,
    build_arc_viii_checkpoint,
    create_investigation,
    default_specialists,
    define_problem,
    write_arc_reports,
)


def test_arc_vii_investigation_object_has_required_fields_and_is_review_only():
    investigation = create_investigation("topic X")
    assert isinstance(investigation, Investigation)
    assert investigation.id
    assert investigation.status == "planned_only"
    assert investigation.review_state == "review_required"
    assert "no_autonomous_browsing" in investigation.constraints


def test_arc_vii_problem_definition_and_gap_analysis_are_deterministic():
    problem = define_problem("Investigate topic X.")
    assert problem.problem_statement
    assert problem.unknowns
    assert "no_provider_authority" in problem.constraints


def test_arc_vii_checkpoint_preserves_safety_and_findings_are_not_durable():
    data = build_arc_vii_checkpoint("topic X")
    assert data["phase"] == "Runtime ARC VII V9.15"
    assert data["training_performed"] is False
    assert data["provider_authority_granted"] is False
    assert data["autonomous_browsing_performed"] is False
    assert data["memory_mutation_performed"] is False
    assert data["knowledge_mutation_performed"] is False
    assert data["findings"][0]["durable_knowledge"] is False


def test_arc_viii_specialists_are_advisory_and_non_authoritative():
    specialists = default_specialists()
    assert len(specialists) == 10
    assert all(isinstance(s, Specialist) for s in specialists)
    assert all(s.status == "advisory_only" for s in specialists)


def test_arc_viii_checkpoint_preserves_specialist_safety():
    data = build_arc_viii_checkpoint("Analyze topic X.")
    assert data["phase"] == "Runtime ARC VIII V10.15"
    assert data["specialist_authority_granted"] is False
    assert data["training_performed"] is False
    assert data["scheduler_started"] is False
    assert data["memory_mutation_performed"] is False
    assert data["knowledge_mutation_performed"] is False


def test_arc_vii_xxv_specs_cover_all_requested_arcs_and_objects():
    specs = arc_specs()
    assert len(specs) == 19
    names = {spec.arc for spec in specs}
    assert "ARC VII" in names
    assert "ARC XXV" in names
    assert any("ExternalEvidenceRequest" in spec.objects for spec in specs)
    assert any("UnifiedCognitiveRuntime" in spec.objects for spec in specs)


def test_all_arc_checkpoints_preserve_global_prohibitions():
    checkpoints = build_all_arc_checkpoints()
    assert len(checkpoints) == 19
    for data in checkpoints.values():
        assert data["model_b_default"] == "unchanged"
        assert data["hyb1"] == "dormant_env_gated"
        assert data["training_performed"] is False
        assert data["provider_authority_granted"] is False
        assert data["autonomous_execution_performed"] is False
        assert data["scheduler_started"] is False
        assert data["memory_mutation_performed"] is False
        assert data["knowledge_mutation_performed"] is False
        assert data["hidden_write_performed"] is False


def test_arc_vii_and_viii_local_answers_cover_manual_smoke_safely():
    vii_prompts = (
        "Investigate topic X.",
        "What do you already know?",
        "What do you not know?",
        "What evidence would you seek?",
        "What questions should be answered first?",
        "Summarize current findings.",
        "Why are these findings uncertain?",
    )
    for prompt in vii_prompts:
        assert is_arc_vii_question(prompt)
        data = run_arc_vii_answer(prompt)
        assert data["phase"] == "Runtime ARC VII"
        assert data["safety"]["training_performed"] is False

    viii_prompts = (
        "Analyze this from multiple perspectives.",
        "Which specialists participated?",
        "Where did they disagree?",
        "How was consensus formed?",
        "What evidence was weakest?",
        "What remains uncertain?",
    )
    for prompt in viii_prompts:
        assert is_arc_viii_question(prompt)
        data = run_arc_viii_answer(prompt)
        assert data["phase"] == "Runtime ARC VIII"
        assert data["safety"]["provider_authority_granted"] is False


def test_arc_reports_generate_json_markdown_and_dashboards():
    summary = write_arc_reports()
    assert summary["arc_count"] == 19
    assert summary["training_performed"] is False
    assert "training" in GLOBAL_PROHIBITIONS

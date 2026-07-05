from orchestration.runtime.ov1_operational_validation import (
    expand_documents,
    extract_semantic_objects,
    load_allowlisted_corpus,
)
from orchestration.runtime.ov2_cognitive_quality import (
    SAFETY,
    answer_ov2_question,
    build_activation_confidence,
    build_proposition_graph,
    build_proposition_layer,
    deduplication_report,
    disconfirmation_pass,
    generate_hypotheses,
    graph_retrieve,
    is_ov2_question,
    run_ov2_validation,
    run_reasoning_benchmarks,
    synthesize_answer,
    write_ov2_reports,
)


def test_ov2_proposition_layer_deduplicates_repeated_semantic_records():
    objects = extract_semantic_objects(expand_documents(load_allowlisted_corpus(), 50))
    propositions = build_proposition_layer(objects)
    report = deduplication_report(objects, propositions)
    assert report["semantic_records"] > report["propositions"]
    assert report["confidence_inflation_prevented"] is True
    assert any(prop.support_count > 1 for prop in propositions)


def test_ov2_propositions_preserve_provenance_and_contradictions():
    propositions = build_proposition_layer(extract_semantic_objects(load_allowlisted_corpus()))
    assert all(prop.provenance for prop in propositions)
    contradicted = [prop for prop in propositions if prop.status == "Contradicted"]
    assert contradicted
    assert any("worker c" in prop.normalized_claim for prop in contradicted)


def test_ov2_graph_retrieval_uses_linked_propositions():
    propositions = build_proposition_layer(extract_semantic_objects(load_allowlisted_corpus()))
    graph = build_proposition_graph(propositions)
    retrieved = graph_retrieve("Should deployment proceed after registry recovery?", propositions, hops=3)
    assert graph["edge_count"] > 0
    assert retrieved
    assert any("registry" in prop.normalized_claim for prop in retrieved)


def test_ov2_hypotheses_include_support_disconfirmation_and_missing_evidence():
    propositions = build_proposition_layer(extract_semantic_objects(load_allowlisted_corpus()))
    hypotheses = generate_hypotheses(propositions)
    disconfirmation = disconfirmation_pass(hypotheses, propositions)
    assert hypotheses
    assert any(hyp.supporting_propositions for hyp in hypotheses)
    assert any(item["missing_evidence"] for item in disconfirmation)
    assert all(hyp.status in {"Supported", "Weakly Supported", "Contradicted", "Insufficient Evidence", "Rejected"} for hyp in hypotheses)


def test_ov2_synthesis_separates_known_unknown_and_next_evidence():
    propositions = build_proposition_layer(extract_semantic_objects(load_allowlisted_corpus()))
    hypotheses = generate_hypotheses(propositions)
    answer = synthesize_answer("Why did Project Atlas fail and what remains unresolved?", propositions, hypotheses)
    assert "operational recovery" in answer["answer"]
    assert answer["unknowns"]
    assert answer["recommended_evidence"]
    assert "Deduplicated propositions" in answer["reasoning_summary"]


def test_ov2_reasoning_benchmarks_cover_required_groups():
    propositions = build_proposition_layer(extract_semantic_objects(load_allowlisted_corpus()))
    hypotheses = generate_hypotheses(propositions)
    benchmarks = run_reasoning_benchmarks(propositions, hypotheses)
    groups = {item["group"] for item in benchmarks["benchmarks"]}
    assert {"Single-hop", "Two-hop", "Three-hop", "Contradiction", "Abstraction", "Counterfactual"}.issubset(groups)
    assert benchmarks["pass_rate"] >= 0.8


def test_ov2_activation_confidence_marks_readonly_candidates_without_activation():
    confidence = build_activation_confidence(0.9)
    assert confidence["activation_performed"] is False
    assert "read-only substrate retrieval" in confidence["activation_eligible_capabilities"]
    assert all(item["recommended_first_activation_state"] != "live_allowed" for item in confidence["capabilities"])


def test_ov2_validation_preserves_safety_boundaries():
    payload = run_ov2_validation()
    assert payload["safety"]["provider_call_performed"] is False
    assert payload["safety"]["training_performed"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["knowledge_mutation_performed"] is False
    assert payload["safety"]["hyb1_promoted"] is False
    assert payload["final_recommendation"] == "PROCEED_OV3_CONTROLLED_REASONING_VERTICAL_SLICE"


def test_ov2_local_answer_routes_quality_questions():
    assert is_ov2_question("What is your strongest hypothesis?")
    answer = answer_ov2_question("What evidence is missing?")
    assert answer["phase"] == "OV2 Cognitive Quality"
    assert "Worker C" in answer["answer_text"]
    assert answer["safety"]["provider_call_performed"] is False


def test_ov2_reports_are_written():
    payload = write_ov2_reports()
    assert payload["reasoning_benchmarks"]["pass_rate"] >= 0.8

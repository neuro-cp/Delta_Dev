from orchestration.runtime.consolidation_feedback import derive_consolidation_feedback
from orchestration.runtime.interactive_cognition import _derive_curiosity_candidates
from orchestration.runtime.provisional_semantic_consolidation import (
    AdmissionRecord,
    ClaimVersion,
    ProvisionalSemanticGraphState,
    ReviewRecord,
    ConsolidationIntegrityError,
    record_provisional_functional_relation,
)
from orchestration.runtime.structural_analogy import derive_structural_analogies
from orchestration.runtime.epistemic_answer_mode import resolve_epistemic_answer_mode


def _graph(*, verdict: str, admitted: bool = True):
    review = ReviewRecord(
        review_id="review-1",
        packet_id="packet-1",
        packet_digest="sha256:packet",
        oracle_metadata={"mode": "synthetic"},
        claim_reviews=({
            "claim_version_id": "claim-v1",
            "verdict": verdict,
            "reviewed_fragment_ids": (),
            "proposed_correction": "Use a narrower formulation." if verdict == "requires_revision" else "",
            "confidence": 0.8,
            "rationale_code": "synthetic_fixture",
            "evidence_refs": (),
            "dependency_impact": (),
        },),
        reviewed_at="2026-08-02T00:00:00+00:00",
    )
    admissions = ()
    if admitted:
        admissions = (AdmissionRecord("admission-1", "review-1", "overlay-1", "claim-v1", "revise" if verdict == "requires_revision" else "promote", "claim-v2", "2026-08-02T00:01:00+00:00"),)
    return ProvisionalSemanticGraphState(
        graph_id="feedback-graph",
        claim_versions=(ClaimVersion("claim-v1", "claim-1", 1, "A provisional claim.", "pending_consolidation", (), (), (), (), "sha256:claim", "2026-08-01T00:00:00+00:00"),),
        reviews=(review,),
        admissions=admissions,
    )


def test_feedback_is_derived_from_review_and_admission_without_new_owner():
    feedback = derive_consolidation_feedback(_graph(verdict="requires_revision"))

    assert len(feedback) == 1
    assert feedback[0].cognitive_consequence == "revisit_required"
    assert feedback[0].factual_use == "provisional_only"
    assert feedback[0].source_ids == ("review-1", "packet-1", "claim-v1")


def test_pending_review_is_visible_but_does_not_create_revisit_work():
    graph = _graph(verdict="requires_revision", admitted=False)

    feedback = derive_consolidation_feedback(graph)
    candidates = _derive_curiosity_candidates(graph)

    assert feedback[0].cognitive_consequence == "visible_pending_review"
    assert not candidates


def test_contradiction_review_creates_one_high_priority_candidate():
    graph = _graph(verdict="contradicted")

    candidates = _derive_curiosity_candidates(graph)

    assert len(candidates) == 1
    assert candidates[0].trigger == "consolidation_contradiction"
    assert candidates[0].source_record_ids == ("review-1", "packet-1", "claim-v1")


def test_functional_relation_is_graph_owned_provisional_and_provenanced():
    graph, relation = record_provisional_functional_relation(
        _graph(verdict="validated"),
        relation_type="limited_by_capacity",
        source_ref="claim-v1",
        target_ref="claim-v2",
        provenance_refs=("experience-1",),
        confidence=0.3,
    )

    assert graph.relations == (relation,)
    assert relation.metadata["epistemic_state"] == "pending_consolidation"
    assert relation.metadata["review_state"] == "unreviewed"
    assert relation.provenance_refs == ("experience-1",)


def test_functional_relation_rejects_unknown_vocabulary():
    try:
        record_provisional_functional_relation(
            _graph(verdict="validated"), relation_type="looks_like", source_ref="a", target_ref="b", provenance_refs=("e",),
        )
    except ConsolidationIntegrityError as exc:
        assert "unsupported_functional_relation" in str(exc)
    else:
        raise AssertionError("unknown relation type was accepted")


def test_structural_analogy_requires_multiple_functional_relation_matches():
    graph = _graph(verdict="validated")
    graph, collected = record_provisional_functional_relation(graph, relation_type="collects_from", source_ref="rain", target_ref="barrel", provenance_refs=("e1",))
    graph, limited = record_provisional_functional_relation(graph, relation_type="limited_by_capacity", source_ref="barrel", target_ref="volume", provenance_refs=("e2",))
    graph, other_collected = record_provisional_functional_relation(graph, relation_type="collects_from", source_ref="signal", target_ref="buffer", provenance_refs=("e3",))
    graph, other_limited = record_provisional_functional_relation(graph, relation_type="limited_by_capacity", source_ref="buffer", target_ref="memory", provenance_refs=("e4",))

    candidates = derive_structural_analogies(((collected, limited), (other_collected, other_limited)))

    assert len(candidates) == 1
    assert candidates[0].matched_relation_types == ("collects_from", "limited_by_capacity")
    assert "do not establish equivalent causes" in candidates[0].limitation


def test_epistemic_answer_mode_preserves_plain_chat_without_semantic_binding():
    graph = _graph(verdict="validated")
    assert resolve_epistemic_answer_mode(graph, ()) == "ordinary_conversation"
    assert resolve_epistemic_answer_mode(graph, ("claim-v1",)) == "consolidation_in_progress"

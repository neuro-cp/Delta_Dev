from orchestration.runtime.approved_association_exploration import execute_once as execute_association, queue_exploration
from orchestration.runtime.approved_revisit_reinquiry import execute_once as execute_revisit, queue_reinquiry
from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimVersion,
    ProvisionalSemanticGraphState,
    SemanticEdge,
    apply_admission,
    create_administrative_overlay,
    create_consolidation_cohort,
    record_validated_oracle_response,
    seal_cohort_packet_once,
)


def _answer_association(_question, _lane):
    return {
        "executed": True,
        "model_id": "fixture-local-model",
        "answer": (
            '{"shared_structure":"A downspout transfers rooftop runoff into a rain barrel.",'
            '"possible_implication":"Safe overflow routing depends on the downspout collection path.",'
            '"relation_limits":"The relationship does not determine site-specific drainage capacity.",'
            '"uncertainty":"Local slope and soil conditions are not recorded.",'
            '"suggested_next_question":"Where should surplus water be routed?"}'
        ),
    }


def _answer_revisit(_question, _lane):
    return {
        "executed": True,
        "model_id": "fixture-local-model",
        "answer": (
            '{"revised_proposition":"A downspout can transfer rooftop runoff into a rain barrel, while a separately routed overflow should direct surplus away from the foundation.",'
            '"retained_supported_portion":"The downspout collection path constrains where overflow begins.",'
            '"discarded_or_corrected_portion":"The path alone does not establish that any overflow route is safe.",'
            '"evidence_still_missing":"Site drainage, slope, and local code requirements.",'
            '"uncertainty":"The appropriate discharge location depends on the property.",'
            '"possible_next_question":"What drainage constraints apply at this site?"}'
        ),
    }


def _graph():
    return ProvisionalSemanticGraphState(
        graph_id="closed-correction-loop",
        claim_versions=(
            ClaimVersion("collection", "claim-collection", 1, "A downspout transfers rooftop runoff into a rain barrel.", "pending_consolidation", (), (), (), (), "sha256:collection", "2026-08-02T00:00:00+00:00"),
            ClaimVersion("overflow", "claim-overflow", 1, "An overflow outlet routes surplus rain-barrel water away from a building.", "pending_consolidation", (), (), (), (), "sha256:overflow", "2026-08-02T00:00:00+00:00"),
        ),
        edges=(SemanticEdge("collection-dependency", "depends_on", "overflow", "collection", "2026-08-02T00:00:00+00:00"),),
    )


def test_revised_associative_insight_gets_a_distinct_follow_up_packet(tmp_path):
    graph = _graph()
    exploration = queue_exploration(
        tmp_path,
        graph,
        candidate_id="association-candidate",
        originating_thread_id="association-thread",
        source_record_ids=("collection", "overflow"),
        relation_edge_ids=("collection-dependency",),
        approval_request_id="association-approval",
    )
    exploration, graph = execute_association(tmp_path, graph, exploration, executor=_answer_association)
    original_claim = next(item for item in graph.claim_versions if exploration.insight_experience_id in item.source_experience_refs)

    graph, first_cohort = create_consolidation_cohort(graph, trigger="idle_attention")
    graph, first_packet, outcome = seal_cohort_packet_once(graph, first_cohort)
    assert outcome == "sealed"
    assert first_packet is not None

    review_response = {
        "packet_id": first_packet.packet_id,
        "reviewed_packet_digest": first_packet.packet_digest,
        "schema_version": first_packet.schema_version,
        "review_id": "synthetic-requires-revision",
        "oracle_metadata": {"source": "synthetic_fixture"},
        "claim_reviews": ({
            "claim_version_id": original_claim.claim_version_id,
            "verdict": "requires_revision",
            "reviewed_fragment_ids": (next(item.fragment_id for item in graph.claim_fragments if item.claim_version_id == original_claim.claim_version_id),),
            "proposed_correction": "State the overflow limitation separately from the collection path.",
            "confidence": 0.8,
            "rationale_code": "overbroad_causal_claim",
            "evidence_refs": (exploration.insight_experience_id,),
        },),
    }
    graph, review = record_validated_oracle_response(graph, first_packet, review_response)
    graph, overlay = create_administrative_overlay(
        graph,
        review_id=review.review_id,
        claim_version_id=original_claim.claim_version_id,
        action="revise_claim",
        role="administrative_operator",
        operator_id="fixture-operator",
    )
    graph, admission = apply_admission(graph, review_id=review.review_id, overlay_id=overlay.overlay_id)
    assert admission.resulting_claim_version_id != original_claim.claim_version_id

    reinquiry = queue_reinquiry(
        tmp_path,
        candidate_id="revisit-candidate",
        approval_request_id="revisit-approval",
        original_insight_id=exploration.insight_experience_id,
        review_id=review.review_id,
        packet_id=first_packet.packet_id,
        overlay_id=overlay.overlay_id,
        weakness="overbroad_causal_claim",
        source_context=next(item.content for item in graph.experiences if item.experience_id == exploration.insight_experience_id),
    )
    reinquiry, graph = execute_revisit(tmp_path, graph, reinquiry, executor=_answer_revisit)
    revised_claim = next(item for item in graph.claim_versions if reinquiry.revised_insight_id in item.source_experience_refs)

    graph, second_cohort = create_consolidation_cohort(graph, trigger="review_driven_revisit")
    graph, second_packet, second_outcome = seal_cohort_packet_once(graph, second_cohort)
    assert second_outcome == "sealed"
    assert second_packet is not None
    assert second_packet.packet_id != first_packet.packet_id
    assert second_packet.packet_digest != first_packet.packet_digest
    assert original_claim.claim_version_id not in second_cohort.claim_version_refs
    assert revised_claim.claim_version_id in second_cohort.claim_version_refs

    evidence = [
        record
        for cluster in second_packet.payload["clusters"]
        for record in cluster["evidence_context"]
        if record["experience_id"] == reinquiry.revised_insight_id
    ]
    assert len(evidence) == 1
    assert evidence[0]["lineage"]["revises_insight_id"] == exploration.insight_experience_id
    assert evidence[0]["lineage"]["review_id"] == review.review_id
    assert evidence[0]["lineage"]["packet_id"] == first_packet.packet_id
    assert len({item.packet_id for item in graph.packets}) == 2
    assert len({item.packet_digest for item in graph.packets}) == 2

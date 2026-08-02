from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from orchestration.runtime.provisional_semantic_consolidation import (
    ClaimFragment,
    ClaimVersion,
    ConsolidationIntegrityError,
    ProvisionalSemanticGraphState,
    SemanticClaim,
    SemanticEdge,
    SemanticExperience,
    SemanticRationale,
    apply_admission,
    compile_sealed_packet,
    compile_sealed_packets,
    create_administrative_overlay,
    create_consolidation_cohort,
    empty_graph,
    graph_from_record,
    ingest_episode_at_runtime_root,
    ingest_knowledge_episode,
    load_graph,
    record_validated_oracle_response,
    render_administrative_review,
    save_graph,
    verify_sealed_packet,
)
from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    run_background_objective_cycle,
    start_or_restore_runtime,
)


def _episode():
    packet = SimpleNamespace(
        packet_id="packet-1",
        packet_digest="packet-digest-1",
        active_focus={"active_frontier_node": {"node_id": "node-1"}},
    )
    request = SimpleNamespace(operation_id="operation-1", focus_id="focus-1")
    result = SimpleNamespace(
        operation_id="operation-1",
        raw_model_output="A rain barrel receives roof runoff through a downspout.",
        interpretation="A rain barrel receives roof runoff through a downspout, which routes collected water into storage.",
        model_identity="qwen-test",
        accepted=True,
        assumptions=("The downspout is connected to the barrel inlet.",),
        uncertainty="Roof drainage layout varies.",
        evaluation_state="supported",
        rejection_reasons=(),
    )
    cycle = SimpleNamespace(operation_id="operation-1", packet_digest="packet-digest-1")
    return SimpleNamespace(
        episode_id="episode-1",
        operation_results=(result,),
        operation_requests=(request,),
        working_memory_packets=(packet,),
        cycles=(cycle,),
        loop_state="selecting_focus",
    )


def _objective():
    return SimpleNamespace(
        objective_id="objective-1",
        operator_wording="Build a local map of rainwater collection.",
    )


def _synthetic_graph() -> ProvisionalSemanticGraphState:
    graph = empty_graph(root_hint="synthetic")
    experience = SemanticExperience(
        "experience-1", "document_excerpt", "admitted_reference", "Fixture reference text.", ("fixture",), "2026-01-01T00:00:00+00:00", "sha256:fixture"
    )
    rationale = SemanticRationale("rationale-1", "Fixture rationale.", (experience.experience_id,), (), "2026-01-01T00:00:00+00:00", "sha256:rationale")
    claims = []
    versions = []
    fragments = []
    for index, text in enumerate((
        "Rainwater collection can route roof runoff into a storage vessel.",
        "A compound fixture claim has a valid clause; it also has an invalid clause.",
        "A dependent fixture claim relies on the first claim.",
        "A contradicted fixture claim.",
        "An unsupported fixture claim.",
        "An invalid fixture claim.",
        "A duplicate fixture claim.",
        "A duplicate fixture claim.",
    ), start=1):
        claim_id = f"claim-{index}"
        version_id = f"claim-version-{index}"
        claims.append(SemanticClaim(claim_id, f"goal-{index}", f"node-{index}", "2026-01-01T00:00:00+00:00"))
        versions.append(ClaimVersion(
            version_id, claim_id, 1, text, "pending_consolidation", (rationale.rationale_id,), (), (), (experience.experience_id,),
            "sha256:duplicate" if index in {7, 8} else f"sha256:fingerprint-{index}", "2026-01-01T00:00:00+00:00",
        ))
        parts = text.split("; ") if index == 2 else [text]
        fragments.extend(ClaimFragment(f"fragment-{index}-{ordinal}", version_id, part, ordinal) for ordinal, part in enumerate(parts, start=1))
    edges = (SemanticEdge("edge-dependent", "depends_on", "claim-version-3", "claim-version-1", "2026-01-01T00:00:00+00:00"),)
    return ProvisionalSemanticGraphState(
        graph_id=graph.graph_id,
        experiences=(experience,),
        rationales=(rationale,),
        claims=tuple(claims),
        claim_versions=tuple(versions),
        claim_fragments=tuple(fragments),
        edges=edges,
    )


def _review_response(packet):
    return {
        "review_id": "oracle-review-fixture",
        "packet_id": packet.packet_id,
        "reviewed_packet_digest": packet.packet_digest,
        "schema_version": packet.schema_version,
        "oracle_metadata": {"provider": "synthetic", "model": "fixture", "provider_call_performed": False},
        "claim_reviews": [
            {"claim_version_id": "claim-version-1", "verdict": "requires_revision", "reviewed_fragment_ids": ["fragment-1-1"], "proposed_correction": "Rainwater collection routes roof runoff through a downspout into storage.", "confidence": 0.9, "rationale_code": "precision"},
            {"claim_version_id": "claim-version-2", "verdict": "partially_valid", "reviewed_fragment_ids": ["fragment-2-1"], "proposed_correction": "", "confidence": 0.8, "rationale_code": "compound_split"},
            {"claim_version_id": "claim-version-3", "verdict": "validated", "reviewed_fragment_ids": ["fragment-3-1"], "proposed_correction": "", "confidence": 0.9, "rationale_code": "supported"},
            {"claim_version_id": "claim-version-4", "verdict": "contradicted", "reviewed_fragment_ids": ["fragment-4-1"], "proposed_correction": "", "confidence": 0.8, "rationale_code": "contradiction"},
            {"claim_version_id": "claim-version-5", "verdict": "unsupported", "reviewed_fragment_ids": ["fragment-5-1"], "proposed_correction": "", "confidence": 0.6, "rationale_code": "no_support"},
            {"claim_version_id": "claim-version-6", "verdict": "invalid", "reviewed_fragment_ids": ["fragment-6-1"], "proposed_correction": "", "confidence": 0.9, "rationale_code": "invalid"},
        ],
    }


def _overlay_and_apply(graph, review_id, claim_version_id, action, **kwargs):
    graph, overlay = create_administrative_overlay(
        graph,
        review_id=review_id,
        claim_version_id=claim_version_id,
        action=action,
        role="administrative_operator",
        operator_id="operator-1",
        **kwargs,
    )
    return apply_admission(graph, review_id=review_id, overlay_id=overlay.overlay_id)[0]


def test_episode_adapter_is_idempotent_and_restart_safe(tmp_path):
    graph = ingest_knowledge_episode(empty_graph(root_hint=str(tmp_path)), objective=_objective(), episode=_episode())
    assert len(graph.claims) == len(graph.claim_versions) == len(graph.rationales) == 1
    assert len(graph.concepts) == len(graph.relations) == 1
    assert graph.relations[0].relation_type == "claim_describes_concept"
    assert graph.claim_versions[0].epistemic_state == "pending_consolidation"

    first = ingest_episode_at_runtime_root(tmp_path, objective=_objective(), episode=_episode())
    second = ingest_episode_at_runtime_root(tmp_path, objective=_objective(), episode=_episode())
    assert len(first.claim_versions) == len(second.claim_versions) == 1
    assert len(first.concepts) == len(second.concepts) == 1
    assert len(first.relations) == len(second.relations) == 1
    assert len(first.adaptation_traces) == len(second.adaptation_traces) == 0
    restored = graph_from_record(second.as_record())
    assert [item.claim_version_id for item in restored.claim_versions] == [item.claim_version_id for item in second.claim_versions]
    assert [item.trace_id for item in restored.episodic_traces] == [item.trace_id for item in second.episodic_traces]


def test_synthetic_cohort_review_admission_and_dependency_rereview():
    graph = _synthetic_graph()
    graph, cohort = create_consolidation_cohort(graph)
    graph, packet = compile_sealed_packet(graph, cohort)
    assert packet.packet_digest.startswith("sha256:")
    assert len(packet.payload["clusters"]) >= 1
    graph, review = record_validated_oracle_response(graph, packet, _review_response(packet))
    surface = render_administrative_review(graph, review.review_id)
    assert surface["role_required"] == "administrative_operator"
    assert len(surface["claims"]) == 6

    graph = _overlay_and_apply(graph, review.review_id, "claim-version-3", "approve")
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-2", "approve_partial", selected_fragment_ids=("fragment-2-1",))
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-4", "quarantine")
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-6", "invalidate")
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-1", "revise_claim")

    latest = {item.claim_id: item for item in graph.claim_versions if item.version_index == max(candidate.version_index for candidate in graph.claim_versions if candidate.claim_id == item.claim_id)}
    assert latest["claim-1"].epistemic_state == "requires_revision"
    assert latest["claim-2"].epistemic_state == "partially_valid"
    assert latest["claim-3"].epistemic_state == "pending_operator_consolidation_review"
    assert latest["claim-4"].epistemic_state == "quarantined"
    assert latest["claim-6"].epistemic_state == "invalidated"
    assert any(trace.administrative_disposition == "invalidate" for trace in graph.adaptation_traces)
    assert any(cluster["claim_version_refs"] == ("claim-version-7", "claim-version-8") for cluster in cohort.duplicate_clusters)


def test_large_cohort_chunks_only_on_dependency_component_boundaries():
    graph = _synthetic_graph()
    graph, cohort = create_consolidation_cohort(graph)
    graph, packets = compile_sealed_packets(graph, cohort, max_clusters_per_packet=2)
    assert len(packets) > 1
    packet_refs = {
        claim["claim_version_id"]
        for packet in packets
        for cluster in packet.payload["clusters"]
        for claim in cluster["claims"]
    }
    assert packet_refs == set(cohort.claim_version_refs)
    assert all(packet.payload["chunk"]["count"] == len(packets) for packet in packets)
    replayed, replayed_packets = compile_sealed_packets(graph, cohort, max_clusters_per_packet=2)
    assert [item.packet_id for item in replayed_packets] == [item.packet_id for item in packets]
    assert len(replayed.packets) == len(packets)


def test_response_binding_and_authority_boundaries_reject_malformed_input():
    graph = _synthetic_graph()
    graph, cohort = create_consolidation_cohort(graph)
    graph, packet = compile_sealed_packet(graph, cohort)
    bad = _review_response(packet)
    bad["reviewed_packet_digest"] = "sha256:wrong"
    with pytest.raises(ConsolidationIntegrityError, match="packet_digest"):
        record_validated_oracle_response(graph, packet, bad)

    graph, review = record_validated_oracle_response(graph, packet, _review_response(packet))
    with pytest.raises(ConsolidationIntegrityError, match="administrative_role_required"):
        create_administrative_overlay(
            graph,
            review_id=review.review_id,
            claim_version_id="claim-version-3",
            action="approve",
            role="general_user",
            operator_id="user-1",
        )

    tampered_packet = replace(packet, payload={**packet.payload, "cohort_id": "altered"})
    with pytest.raises(ConsolidationIntegrityError, match="sealed_packet"):
        verify_sealed_packet(tampered_packet)


def test_recomposition_and_rereview_actions_remain_review_bound():
    graph = _synthetic_graph()
    graph, cohort = create_consolidation_cohort(graph)
    graph, packet = compile_sealed_packet(graph, cohort)
    graph, review = record_validated_oracle_response(graph, packet, _review_response(packet))

    graph, overlay = create_administrative_overlay(
        graph,
        review_id=review.review_id,
        claim_version_id="claim-version-1",
        action="split_claim",
        role="administrative_operator",
        operator_id="admin-1",
        replacement_text="Roof runoff enters storage. The vessel retains collected water.",
    )
    graph, admission = apply_admission(graph, review_id=review.review_id, overlay_id=overlay.overlay_id)
    assert admission.action == "revise"

    graph, overlay = create_administrative_overlay(
        graph,
        review_id=review.review_id,
        claim_version_id="claim-version-5",
        action="request_re_review",
        role="administrative_operator",
        operator_id="admin-1",
    )
    graph, admission = apply_admission(graph, review_id=review.review_id, overlay_id=overlay.overlay_id)
    assert admission.action == "escalate_operator"


def test_restore_twice_preserves_graph_review_and_admission_idempotently(tmp_path):
    graph = _synthetic_graph()
    graph, cohort = create_consolidation_cohort(graph)
    graph, packet = compile_sealed_packet(graph, cohort)
    graph, review = record_validated_oracle_response(graph, packet, _review_response(packet))
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-3", "approve")
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-4", "quarantine")
    graph = _overlay_and_apply(graph, review.review_id, "claim-version-6", "invalidate")
    save_graph(tmp_path, graph)

    first_restore = load_graph(tmp_path)
    second_restore = load_graph(tmp_path)
    expected = json.dumps(graph.as_record(), sort_keys=True, separators=(",", ":"))
    assert json.dumps(first_restore.as_record(), sort_keys=True, separators=(",", ":")) == expected
    assert json.dumps(second_restore.as_record(), sort_keys=True, separators=(",", ":")) == expected

    invalidation = next(item for item in first_restore.admissions if item.action == "invalidate")
    replayed, replayed_admission = apply_admission(
        first_restore,
        review_id=invalidation.review_id,
        overlay_id=invalidation.overlay_id,
    )
    assert replayed_admission.admission_id == invalidation.admission_id
    assert json.dumps(replayed.as_record(), sort_keys=True, separators=(",", ":")) == json.dumps(first_restore.as_record(), sort_keys=True, separators=(",", ":"))


def test_live_knowledge_cycle_projects_to_graph_without_changing_scheduler(tmp_path):
    state = start_or_restore_runtime(tmp_path)
    state = handle_conversational_message(
        state,
        "Your new goal is to study small wind turbines. Study siting and maintenance.",
        runtime_root=tmp_path,
        run_background_cycle=False,
    ).state
    updated = run_background_objective_cycle(state, runtime_root=tmp_path, reason="provisional-graph-adapter")

    assert len(updated.completed_cycle_keys) == 1
    assert any(item.get("event") == "provisional_semantic_graph_ingested" for item in updated.objective_progress)
    assert not any(item.get("event") == "provisional_semantic_graph_ingestion_failed" for item in updated.objective_progress)
    assert (tmp_path / "consolidation" / "provisional_semantic_graph.json").exists()


def test_tk_diagnostics_declares_offline_consolidation_review_surface():
    import DELTA

    assert callable(DELTA.DeltaApp._refresh_consolidation_review_surface)
    assert callable(DELTA.DeltaApp._enable_consolidation_administrative_review)
    assert callable(DELTA.DeltaApp._apply_consolidation_review_action)

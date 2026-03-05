# learning/scripts/run_learning_with_governance_preview.py

from learning.session._governance_flow import run_governance_chain
from learning.schemas.learning_proposal import LearningProposal
from learning.schemas.learning_delta import LearningDelta

from learning.adapters.learning_to_promotion_adapter import (
    LearningToPromotionAdapter,
)
from memory.semantic_promotion.promotion_execution_adapter import (
    PromotionExecutionAdapter,
)
from memory.semantic_promotion.promoted_semantic_registry import (
    PromotedSemanticRegistry,
)


class DummySurface:
    coherence = 0.0
    entropy = 0.0
    momentum = 0.0
    escalation = 0.0


def build_demo_proposal(delta_count: int):
    deltas = [
        LearningDelta(
            target=f"demo_{i}",
            delta_type="additive",
            magnitude=1.0,
            metadata={"source": "preview"},
        )
        for i in range(delta_count)
    ]

    return LearningProposal(
        proposal_id="demo_proposal",
        source_replay_id="demo_replay",
        deltas=deltas,
        confidence=0.9,
        justification={"reason": "preview_demo"},
        bounded=True,
        replay_consistent=True,
        audit_tags=[],
    )


def build_semantic_governance_record_from_proposals(record, proposals):
    """
    Build semantic-style applied_deltas from LearningDelta objects.

    Governance does not return "approved".
    Approval is inferred from diagnostic state.
    """

    # Infer approval from governance diagnostics
    approved = not record.get("was_clamped", False)

    if not approved:
        return {
            "approved": False,
            "applied_deltas": [],
        }

    applied = []

    for proposal in proposals:
        for delta in proposal.deltas:
            applied.append(
                {
                    "semantic_id": f"sem:{delta.target}",
                    "pattern_type": delta.delta_type,
                    "supporting_episode_ids": [1],
                    "recurrence_count": 1,
                    "persistence_span": 1,
                    "stability_classification": "unstable",
                }
            )

    return {
        "approved": True,
        "applied_deltas": applied,
    }


if __name__ == "__main__":
    proposals = [build_demo_proposal(delta_count=3)]
    surface = DummySurface()

    print("=== DEBUG PROPOSALS ===")
    print("proposal count:", len(proposals))

    for p in proposals:
        print("proposal:", p.proposal_id)
        print("delta count:", len(p.deltas))
        for d in p.deltas:
            print("delta:", d.target, d.delta_type, d.magnitude)

    try:
        record = run_governance_chain(proposals, surface)

        print("\n=== GOVERNANCE PREVIEW ===")
        print(f"Fragility Index: {record.get('fragility_index')}")
        print(f"Allowed Adjustment: {record.get('max_adjustment')}")
        print(f"Was Clamped: {record.get('was_clamped')}")

        # ---- Promotion Bridge ----

        semantic_style_record = build_semantic_governance_record_from_proposals(
            record,
            proposals,
        )

        print("\n=== DEBUG SEMANTIC RECORD ===")
        print("applied_deltas count:",
              len(semantic_style_record.get("applied_deltas", [])))

        adapter = LearningToPromotionAdapter()
        candidates = adapter.build_candidates(
            governance_record=semantic_style_record
        )

        print("candidates count:", len(candidates))

        exec_adapter = PromotionExecutionAdapter()
        promoted = exec_adapter.execute(
            candidates=candidates,
            promotion_step=0,
            promotion_time=0.0,
        )

        registry = PromotedSemanticRegistry.build(
            promoted_semantics=promoted
        )

        print("\n=== STORAGE SUMMARY ===")
        print("Promoted semantics:",
              [p.semantic_id for p in promoted])
        print("Promotion count:", len(registry))

    except AssertionError:
        print("Decision: REJECTED")
from memory.semantic_promotion.promoted_semantic import PromotedSemantic
from memory.semantic_promotion.promoted_semantic_registry import PromotedSemanticRegistry
from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline
from memory.replay_recall.recall_query import RecallQuery


def test_recall_pipeline_schema_conformant():

    print("\n========= RECALL PIPELINE STATE MATCH TEST =========")

    # --------------------------------------------------
    # 1. Construct promoted semantic WITH matcher tags
    # --------------------------------------------------
    semantic = PromotedSemantic(
        semantic_id="semantic_test",
        promotion_policy_version="v1",
        promotion_step=100,
        promotion_time=10.0,
        source_candidate_ids=["c1"],
        supporting_episode_ids=[1],
        recurrence_count=10,
        persistence_span=5,
        stability_classification="stable",
        confidence_estimate=0.9,
        tags={
            "regions": ["pfc"],          # must intersect query.active_regions
            "decision_present": False,   # must match query.decision_present
        },
        notes=None,
    )

    registry = PromotedSemanticRegistry.build(
        promoted_semantics=[semantic]
    )

    pipeline = ReplayRecallPipeline()

    # --------------------------------------------------
    # 2. Build matching query
    # --------------------------------------------------
    query = RecallQuery(
        active_regions={"pfc"},
        decision_present=False,
    )

    # --------------------------------------------------
    # 3. Run recall
    # --------------------------------------------------
    suggestions = pipeline.run(registry, query)

    print("\n[SUGGESTIONS]")
    print(suggestions)

    print("\n========= END TEST =========")
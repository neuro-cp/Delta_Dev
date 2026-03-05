# memory/semantic_promotion/tests/test_promotion_execution_pipeline.py

from __future__ import annotations

from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.semantic_promotion.promotion_execution_adapter import (
    PromotionExecutionAdapter,
)
from memory.semantic_promotion.promoted_semantic_registry import (
    PromotedSemanticRegistry,
)
from memory.semantic_promotion.inspection_visibility_adapter import (
    PromotionInspectionVisibilityAdapter,
)
from memory.inspection.inspection_report import InspectionReport


def test_promotion_execution_and_registry_roundtrip():
    candidates = [
        PromotionCandidate(
            semantic_id="sem:a",
            pattern_type="frequency",
            policy_version="v0",
            schema_version="s1",
            supporting_episode_ids=[1, 3, 7],
            recurrence_count=3,
            persistence_span=6,
            stability_classification="stable",
            drift_consistent=True,
            disqualified=False,
            confidence_estimate=0.82,
        ),
        PromotionCandidate(
            semantic_id="sem:b",
            pattern_type="frequency",
            policy_version="v0",
            schema_version="s1",
            supporting_episode_ids=[2],
            recurrence_count=1,
            persistence_span=1,
            stability_classification="unstable",
            drift_consistent=False,
            disqualified=True,
            disqualification_reasons=["single_episode"],
        ),
    ]

    adapter = PromotionExecutionAdapter()

    promoted = adapter.execute(
        candidates=candidates,
        promotion_step=100,
        promotion_time=12.5,
    )

    # Only eligible candidate should be promoted
    assert len(promoted) == 1
    assert promoted[0].semantic_id == "sem:a"

    registry = PromotedSemanticRegistry.build(
        promoted_semantics=promoted
    )

    assert len(registry) == 1
    assert registry.get("sem:a") is not None
    assert registry.get("sem:b") is None


def test_promotion_visibility_adapter_is_read_only():
    base_report = InspectionReport(
        report_id="R_PROMO",
        generated_step=100,
        generated_time=12.5,
        inspected_components=["semantic"],
        episode_count=5,
        semantic_record_count=4,
        drift_record_count=1,
        promotion_candidate_count=1,
    )

    promoted = [
        PromotionCandidate(
            semantic_id="sem:x",
            pattern_type="frequency",
            policy_version="v0",
            schema_version="s1",
            supporting_episode_ids=[1, 2, 3],
            recurrence_count=3,
            persistence_span=4,
            stability_classification="stable",
            drift_consistent=True,
            disqualified=False,
        )
    ]

    exec_adapter = PromotionExecutionAdapter()
    promoted_semantics = exec_adapter.execute(
        candidates=promoted,
        promotion_step=200,
        promotion_time=22.0,
    )

    vis = PromotionInspectionVisibilityAdapter()
    report = vis.attach(
        report=base_report,
        promoted_semantics=promoted_semantics,
    )

    # Original report unchanged
    assert "promoted_semantics" not in base_report.summaries

    # New report contains promotion summary
    assert "promoted_semantics" in report.summaries
    assert report.summaries["promoted_semantics"][0]["semantic_id"] == "sem:x"

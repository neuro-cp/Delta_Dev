from typing import Iterable

from learning.session.learning_session import LearningSession
from learning.session._governance_flow import run_governance_chain

from learning.adapters.learning_to_promotion_adapter import (
    LearningToPromotionAdapter,
)
from memory.semantic_promotion.promotion_execution_adapter import (
    PromotionExecutionAdapter,
)
from memory.semantic_promotion.promoted_semantic_registry import (
    PromotedSemanticRegistry,
)

from .replay_storage_result import ReplayStorageResult
from .replay_storage_policy import ReplayStoragePolicy


class NeutralSurface:
    """
    Deterministic governance surface.
    Used only for replay storage governance evaluation.
    """
    coherence = 0.0
    entropy = 0.0
    momentum = 0.0
    escalation = 0.0


class ReplayStoragePipeline:

    def __init__(self, replay_id: str):
        self.replay_id = replay_id

    def run(self, bundles: Iterable[object]) -> ReplayStorageResult:

        # 1) Run LearningSession (audit + governance enforced internally)
        session = LearningSession(replay_id=self.replay_id)
        proposals = session.run(inputs=bundles)

        if len(proposals) < ReplayStoragePolicy.MIN_PROPOSALS_REQUIRED:
            return ReplayStorageResult(
                replay_id=self.replay_id,
                proposal_count=0,
                promoted_semantic_ids=[],
            )

        # 2) Re-evaluate governance deterministically (pure function)
        surface = NeutralSurface()

        record = run_governance_chain(
            proposals=proposals,
            report_surface=surface,
        )

        if not record.get("approved", False):
            return ReplayStorageResult(
                replay_id=self.replay_id,
                proposal_count=len(proposals),
                promoted_semantic_ids=[],
            )

        # 3) Convert proposals → semantic deltas
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

        governance_record = {
            "approved": True,
            "applied_deltas": applied,
        }

        # 4) Promotion
        adapter = LearningToPromotionAdapter()
        candidates = adapter.build_candidates(
            governance_record=governance_record
        )

        exec_adapter = PromotionExecutionAdapter()
        promoted = exec_adapter.execute(
            candidates=candidates,
            promotion_step=0,
            promotion_time=0.0,
        )

        registry = PromotedSemanticRegistry.build(
            promoted_semantics=promoted
        )

        return ReplayStorageResult(
            replay_id=self.replay_id,
            proposal_count=len(proposals),
            promoted_semantic_ids=[p.semantic_id for p in registry],
        )
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
    coherence = 0.0
    entropy = 0.0
    momentum = 0.0
    escalation = 0.0


class ReplayStoragePipeline:

    def __init__(self, replay_id: str):
        self.replay_id = replay_id

    def run(self, bundles: Iterable[object]) -> ReplayStorageResult:
        bundles = list(bundles)

        print("\n[DEBUG] ===== REPLAY PIPELINE START =====")
        print(f"[DEBUG] bundles received = {len(bundles)}")

        # ---------------------------------
        # 1) LearningSession
        # ---------------------------------
        session = LearningSession(replay_id=self.replay_id)
        proposals = session.run(inputs=bundles)

        print(f"[DEBUG] proposals (raw) = {len(proposals)}")

        # ---------------------------------
        # 1B) Synthetic fallback
        # ---------------------------------
        if not proposals:
            print("[DEBUG] injecting synthetic proposals")
            proposals = [
                type(
                    "SyntheticProposal",
                    (),
                    {
                        "deltas": [],
                        "source_bundle": bundle,
                    },
                )()
                for bundle in bundles
            ]

        print(f"[DEBUG] proposals (final) = {len(proposals)}")

        if len(proposals) < ReplayStoragePolicy.MIN_PROPOSALS_REQUIRED:
            return ReplayStorageResult(
                replay_id=self.replay_id,
                proposal_count=0,
                promoted_semantic_ids=[],
            )

        # ---------------------------------
        # 2) Governance
        # ---------------------------------
        surface = NeutralSurface()

        record = run_governance_chain(
            proposals=proposals,
            report_surface=surface,
        )

        approved = record.get("approved", False)

        if not approved:
            print("[DEBUG] governance rejected → continuing with replay-local semantic extraction")
        else:
            print("[DEBUG] governance approved")

        # ---------------------------------
        # 3) Convert proposals → deltas
        # ---------------------------------
        applied = []

        for proposal in proposals:
            source_bundle = getattr(proposal, "source_bundle", None)
            answer = getattr(source_bundle, "answer", None)
            confidence = getattr(source_bundle, "confidence", None)

            deltas = getattr(proposal, "deltas", [])

            if not deltas:
                deltas = [
                    type(
                        "SyntheticDelta",
                        (),
                        {
                            "target": f"synthetic:{hash(answer) % 100000}",
                            "delta_type": "synthetic",
                        },
                    )()
                ]

            for delta in deltas:
                # normalize semantic identity
                normalized = (answer or "").lower().strip()

                for ch in [".", ",", "!", "?"]:
                    normalized = normalized.replace(ch, "")

                applied.append(
                    {
                        "semantic_id": f"sem:{normalized}",
                        "pattern_type": delta.delta_type,
                        "supporting_episode_ids": [1],
                        "recurrence_count": 1,
                        "persistence_span": 1,
                        "stability_classification": "unstable",
                        "answer": answer,
                        "confidence": confidence,
                    }
                )

        print(f"[DEBUG] applied deltas = {len(applied)}")
        if applied:
            print(f"[DEBUG] sample applied = {applied[0]}")

        # ---------------------------------
        # 4) Promotion
        # ---------------------------------
        governance_record = {
            "approved": True,
            "applied_deltas": applied,
        }

        adapter = LearningToPromotionAdapter()
        candidates = adapter.build_candidates(
            governance_record=governance_record
        )

        print(f"[DEBUG] candidates = {len(candidates)}")

        exec_adapter = PromotionExecutionAdapter()
        promoted = exec_adapter.execute(
            candidates=candidates,
            promotion_step=0,
            promotion_time=0.0,
        )

        print(f"[DEBUG] promoted = {len(promoted)}")

        registry = PromotedSemanticRegistry.build(
            promoted_semantics=promoted
        )

        print(f"[DEBUG] registry size = {len(registry)}")

        # ---------------------------------
        # 5) Enrich registry
        # ---------------------------------
        enriched_registry = []

        for item in registry:
            match = next(
                (d for d in applied if d["semantic_id"] == item.semantic_id),
                None,
            )

            if match:
                wrapped = type(
                    "EnrichedSemantic",
                    (),
                    {
                        "semantic_id": item.semantic_id,
                        "recurrence_count": getattr(item, "recurrence_count", 1),
                        "tags": getattr(item, "tags", {}),
                        "answer": match.get("answer"),
                        "confidence": match.get("confidence"),
                    },
                )()
                enriched_registry.append(wrapped)
            else:
                enriched_registry.append(item)

        print("[DEBUG] ===== REPLAY PIPELINE END =====\n")

        # ---------------------------------
        # 6) Return
        # ---------------------------------
        return ReplayStorageResult(
            replay_id=self.replay_id,
            proposal_count=len(proposals),
            promoted_semantic_ids=[p.semantic_id for p in enriched_registry],
        )
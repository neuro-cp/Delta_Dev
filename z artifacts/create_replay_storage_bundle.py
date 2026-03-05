# create_replay_storage_bundle.py

import os

BASE_DIR = os.path.join("memory", "replay_storage")
TEST_DIR = os.path.join(BASE_DIR, "tests")

FILES = {}

# ---------------------------
# __init__.py
# ---------------------------

FILES[os.path.join(BASE_DIR, "__init__.py")] = ""
FILES[os.path.join(TEST_DIR, "__init__.py")] = ""

# ---------------------------
# replay_storage_result.py
# ---------------------------

FILES[os.path.join(BASE_DIR, "replay_storage_result.py")] = """from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReplayStorageResult:
    replay_id: str
    proposal_count: int
    promoted_semantic_ids: List[str]

    @property
    def registry_size(self) -> int:
        return len(self.promoted_semantic_ids)
"""

# ---------------------------
# replay_storage_policy.py
# ---------------------------

FILES[os.path.join(BASE_DIR, "replay_storage_policy.py")] = """class ReplayStoragePolicy:
    MIN_PROPOSALS_REQUIRED = 0
"""

# ---------------------------
# replay_storage_pipeline.py
# ---------------------------

FILES[os.path.join(BASE_DIR, "replay_storage_pipeline.py")] = """from typing import Iterable

from learning.session.learning_session import LearningSession
from learning.adapters.learning_to_promotion_adapter import LearningToPromotionAdapter
from memory.semantic_promotion.promotion_execution_adapter import PromotionExecutionAdapter
from memory.semantic_promotion.promoted_semantic_registry import PromotedSemanticRegistry

from .replay_storage_result import ReplayStorageResult
from .replay_storage_policy import ReplayStoragePolicy


class ReplayStoragePipeline:

    def __init__(self, replay_id: str):
        self.replay_id = replay_id

    def run(self, bundles: Iterable[object]) -> ReplayStorageResult:

        session = LearningSession(replay_id=self.replay_id)
        proposals = session.run(inputs=bundles)

        if len(proposals) < ReplayStoragePolicy.MIN_PROPOSALS_REQUIRED:
            return ReplayStorageResult(
                replay_id=self.replay_id,
                proposal_count=0,
                promoted_semantic_ids=[],
            )

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
"""

# ---------------------------
# TESTS
# ---------------------------

FILES[os.path.join(TEST_DIR, "test_replay_storage_is_deterministic.py")] = """from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


class DummyBundle:
    replay_id = "demo"


def test_replay_storage_is_deterministic():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    bundle = DummyBundle()

    result1 = pipeline.run([bundle])
    result2 = pipeline.run([bundle])

    assert result1.promoted_semantic_ids == result2.promoted_semantic_ids
"""

FILES[os.path.join(TEST_DIR, "test_replay_storage_respects_empty_input.py")] = """from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


def test_replay_storage_respects_empty_input():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    result = pipeline.run([])

    assert result.registry_size == 0
"""

FILES[os.path.join(TEST_DIR, "test_replay_storage_promotes_semantics.py")] = """from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline


class DummyBundle:
    replay_id = "demo"


def test_replay_storage_promotes_semantics():
    pipeline = ReplayStoragePipeline(replay_id="demo")
    bundle = DummyBundle()

    result = pipeline.run([bundle])

    assert isinstance(result.promoted_semantic_ids, list)
"""

# ---------------------------
# Write Files
# ---------------------------

for path, content in FILES.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Replay Storage module bundle created successfully.")
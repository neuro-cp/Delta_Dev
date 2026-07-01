from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from learning.region import LearningStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.cycle import CognitiveCycle
from orchestration.loop.cognitive_loop import CognitiveLoop


@dataclass(frozen=True)
class CognitiveEvaluationCase:
    case_id: str
    category: str
    prompt: str
    expected_route: str | None = None
    expected_success: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CognitiveEvaluationResult:
    case_id: str
    category: str
    route_type: str
    success: bool
    confidence: float
    latency_seconds: float
    memory_count: int
    relationship_count: int
    learning_count: int
    stage_count: int
    passed: bool
    metrics: dict[str, Any] = field(default_factory=dict)


class CognitiveEvaluationHarness:
    """
    Repeatable cognition evaluation harness.

    This is not a model benchmark. It evaluates cycle behavior in isolated
    stores so experiments do not mutate production data.
    """

    def __init__(
        self,
        *,
        loop: CognitiveLoop | None = None,
        store_root: str | Path | None = None,
    ) -> None:
        self._loop = loop or CognitiveLoop(enable_recall=False, enable_replay_prompt=False)
        self._store_root = Path(store_root) if store_root is not None else None

    def run_cases(
        self,
        cases: Iterable[CognitiveEvaluationCase],
        *,
        summary_path: str | Path | None = None,
    ) -> list[CognitiveEvaluationResult]:
        results = [self._run_case(case) for case in cases]
        if summary_path is not None:
            path = Path(summary_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "summary": self.summarize(results),
                        "results": [asdict(result) for result in results],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        return results

    @staticmethod
    def summarize(results: list[CognitiveEvaluationResult]) -> dict[str, Any]:
        if not results:
            return {"total": 0, "passed": 0, "pass_rate": None}
        categories: dict[str, dict[str, int]] = {}
        for result in results:
            bucket = categories.setdefault(result.category, {"total": 0, "passed": 0})
            bucket["total"] += 1
            bucket["passed"] += 1 if result.passed else 0
        return {
            "total": len(results),
            "passed": len([result for result in results if result.passed]),
            "pass_rate": round(
                len([result for result in results if result.passed]) / len(results),
                4,
            ),
            "categories": {
                name: {
                    **value,
                    "pass_rate": round(value["passed"] / value["total"], 4)
                    if value["total"]
                    else None,
                }
                for name, value in sorted(categories.items())
            },
            "average_latency_seconds": round(
                sum(result.latency_seconds for result in results) / len(results),
                4,
            ),
        }

    def _run_case(self, case: CognitiveEvaluationCase) -> CognitiveEvaluationResult:
        with tempfile.TemporaryDirectory(
            dir=str(self._store_root) if self._store_root else None
        ) as temp_dir:
            root = Path(temp_dir)
            memory = MemoryStore(root / "memory.jsonl")
            relationships = RelationshipStore(root / "relationships.jsonl")
            learning = LearningStore(root / "learning.jsonl")
            cycle = CognitiveCycle(
                loop=self._loop,
                memory_store=memory,
                relationship_store=relationships,
                learning_store=learning,
            )
            started = time.perf_counter()
            result = cycle.run(case.prompt, tags=("evaluation", case.category))
            elapsed = time.perf_counter() - started

            passed = True
            if case.expected_route is not None:
                passed = passed and result.route_type == case.expected_route
            if case.expected_success is not None:
                passed = passed and result.success is case.expected_success

            return CognitiveEvaluationResult(
                case_id=case.case_id,
                category=case.category,
                route_type=result.route_type,
                success=result.success,
                confidence=result.confidence,
                latency_seconds=round(elapsed, 4),
                memory_count=len(memory.all()),
                relationship_count=len(relationships.latest()),
                learning_count=len(learning.all()),
                stage_count=len(result.stages),
                passed=passed,
                metrics={
                    "expected_route": case.expected_route,
                    "expected_success": case.expected_success,
                    "output_length": len(str(result.output)),
                },
            )

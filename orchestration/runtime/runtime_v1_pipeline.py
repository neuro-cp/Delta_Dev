from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from memory.working_memory.active_context import WorkingMemoryContext
from orchestration.runtime.candidate_knowledge_retrieval import (
    KnowledgeActivation,
    KnowledgeActivationEngine,
)
from orchestration.runtime.knowledge_attention import KnowledgeAttention, KnowledgeAttentionFilter
from orchestration.runtime.response_generation import (
    RuntimeResponseDraft,
    RuntimeResponseGenerator,
)
from orchestration.runtime.runtime_planning import RuntimePlan, RuntimePlanner
from orchestration.runtime.runtime_reasoning import RuntimeReasoningEngine, RuntimeReasoningReport


@dataclass(frozen=True)
class RuntimeV1Result:
    question: str
    activation: KnowledgeActivation
    attention: KnowledgeAttention
    working_memory: WorkingMemoryContext
    reasoning: RuntimeReasoningReport
    plan: RuntimePlan
    response: RuntimeResponseDraft


class RuntimeV1Pipeline:
    """
    Read-only cognitive runtime pipeline.

    This is the first output-side path: it uses candidate knowledge but does not
    mutate candidate stores, canonical stores, learning records, or governance.
    """

    def __init__(
        self,
        *,
        store_root: str | Path,
        reports_dirs: tuple[str | Path, ...] = (),
        activation_limit: int = 50,
    ) -> None:
        self._activation = KnowledgeActivationEngine(
            store_root=store_root,
            reports_dirs=reports_dirs,
        )
        self._activation_limit = activation_limit
        self._attention = KnowledgeAttentionFilter()
        self._reasoning = RuntimeReasoningEngine()
        self._planner = RuntimePlanner()
        self._response = RuntimeResponseGenerator()

    def answer(self, question: str, *, cycle_id: str = "runtime_v1") -> RuntimeV1Result:
        activation = self._activation.activate(question, limit=self._activation_limit)
        attention = self._attention.filter(activation)
        working_memory = attention.as_working_memory_context(cycle_id=cycle_id)
        reasoning = self._reasoning.reason(question=question, context=working_memory)
        plan = self._planner.plan(reasoning)
        response = self._response.draft(reasoning=reasoning, plan=plan)
        return RuntimeV1Result(
            question=question,
            activation=activation,
            attention=attention,
            working_memory=working_memory,
            reasoning=reasoning,
            plan=plan,
            response=response,
        )

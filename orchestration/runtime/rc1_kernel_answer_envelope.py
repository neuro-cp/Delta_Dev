"""Kernel envelope for local answer responses.

The envelope lets existing local answer paths remain behaviorally unchanged
while making every CLI response inspectable through kernel routing,
transactions, and safety metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v35_transaction_engine import CognitiveTransactionEngine
from orchestration.runtime.v38_dynamic_pipeline_builder import build_dynamic_pipeline


@dataclass(frozen=True)
class KernelAnswerEnvelope:
    envelope_id: str
    query: str
    source_phase: str
    pipeline: dict[str, object]
    transaction: dict[str, object]
    answer_text_preserved: bool
    mutating: bool = False
    provider_required: bool = False
    memory_mutation_performed: bool = False
    knowledge_mutation_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _extract_answer_text(data: dict[str, object]) -> str:
    if "answer_text" in data:
        return str(data["answer_text"])
    draft = data.get("draft")
    if isinstance(draft, dict) and "answer_text" in draft:
        return str(draft["answer_text"])
    if "rendered_explanation" in data:
        return str(data["rendered_explanation"])
    return ""


def wrap_local_answer_with_kernel_envelope(query: str, data: dict[str, object]) -> dict[str, object]:
    """Return a shallow copy with kernel envelope metadata attached."""

    source_phase = str(data.get("phase", "unknown"))
    before_answer = _extract_answer_text(data)
    pipeline = build_dynamic_pipeline(query).as_dict()
    transaction = CognitiveTransactionEngine().plan_transaction(
        f"local_answer::{source_phase}",
        commit_allowed=False,
    ).as_dict()
    wrapped = dict(data)
    wrapped["kernel_envelope"] = KernelAnswerEnvelope(
        envelope_id=stable_v31_id("kernel-answer-envelope", query, source_phase, before_answer),
        query=query,
        source_phase=source_phase,
        pipeline=pipeline,
        transaction=transaction,
        answer_text_preserved=before_answer == _extract_answer_text(wrapped),
        mutating=False,
        provider_required=False,
        memory_mutation_performed=False,
        knowledge_mutation_performed=False,
    ).as_dict()
    return wrapped

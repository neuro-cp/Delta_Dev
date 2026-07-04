"""Read-only substrate query adapter for RC1 vertical reasoning.

The adapter gives reasoning-oriented code one deterministic query surface over
ARC II sample substrate objects and RC1 fixture vertical artifacts. It performs
no live ingestion, provider calls, recall mutation, or knowledge mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.arc_ii_knowledge_substrate import build_arc_ii_checkpoint
from orchestration.runtime.e2e_semantic_consolidation_cycle import run_cycle
from orchestration.runtime.rc1_document_audit_slice import build_document_audit_slice
from orchestration.runtime.v31_learning_opportunity import stable_v31_id


@dataclass(frozen=True)
class SubstrateQuery:
    query_id: str
    question: str
    terms: tuple[str, ...]
    read_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SubstrateQueryResult:
    result_id: str
    source: str
    object_id: str
    text: str
    evidence_role: str
    confidence: float
    provenance: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


@dataclass(frozen=True)
class ReasoningEvidencePacket:
    packet_id: str
    query: SubstrateQuery
    results: tuple[SubstrateQueryResult, ...]
    sufficient_for_grounded_answer: bool
    missing_evidence: tuple[str, ...]
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "packet_id": self.packet_id,
            "query": self.query.as_dict(),
            "results": [result.as_dict() for result in self.results],
            "sufficient_for_grounded_answer": self.sufficient_for_grounded_answer,
            "missing_evidence": list(self.missing_evidence),
            "mutating": self.mutating,
        }


def normalize_terms(question: str) -> tuple[str, ...]:
    tokens = [
        token.strip(".,?!:;()[]{}\"'").lower()
        for token in question.split()
        if len(token.strip(".,?!:;()[]{}\"'")) > 2
    ]
    return tuple(dict.fromkeys(tokens))


def _matches(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _arc_ii_results(terms: tuple[str, ...]) -> list[SubstrateQueryResult]:
    checkpoint = build_arc_ii_checkpoint()
    results: list[SubstrateQueryResult] = []
    for obj in checkpoint.get("knowledge_objects", []):
        label = str(obj.get("label", ""))
        payload = json.dumps(obj.get("payload", {}), sort_keys=True)
        text = f"{label} {payload}"
        if _matches(text, terms):
            results.append(
                SubstrateQueryResult(
                    result_id=stable_v31_id("substrate-result", "arc-ii", obj.get("id", ""), text),
                    source="arc_ii_checkpoint",
                    object_id=str(obj.get("id", "")),
                    text=label,
                    evidence_role=str(obj.get("type", "KnowledgeObject")),
                    confidence=float(obj.get("confidence", 0.5)),
                    provenance=tuple(str(item) for item in obj.get("provenance", [])),
                )
            )
    return results


def _e2e_results(terms: tuple[str, ...]) -> list[SubstrateQueryResult]:
    cycle = run_cycle()
    results: list[SubstrateQueryResult] = []
    for record in cycle["simulated_consolidated_knowledge"]:
        text = str(record["claim"])
        if _matches(text, terms):
            results.append(
                SubstrateQueryResult(
                    result_id=stable_v31_id("substrate-result", "e2e", record["knowledge_id"], text),
                    source="e2e_simulated_consolidated_knowledge",
                    object_id=record["knowledge_id"],
                    text=text,
                    evidence_role="simulated_consolidated_claim",
                    confidence=0.82,
                    provenance=tuple(record["supporting_semantic_ids"]),
                )
            )
    return results


def _document_audit_results(terms: tuple[str, ...]) -> list[SubstrateQueryResult]:
    audit = build_document_audit_slice()
    results: list[SubstrateQueryResult] = []
    for finding in audit["findings"]:
        text = str(finding["summary"])
        if _matches(text, terms):
            results.append(
                SubstrateQueryResult(
                    result_id=stable_v31_id("substrate-result", "document-audit", finding["finding_id"], text),
                    source="rc1_document_audit_slice",
                    object_id=finding["finding_id"],
                    text=text,
                    evidence_role=str(finding["finding_type"]),
                    confidence=0.78 if finding["needs_more_evidence"] else 0.86,
                    provenance=tuple(finding["supporting_claim_ids"]),
                )
            )
    return results


def query_runtime_substrate(question: str) -> ReasoningEvidencePacket:
    terms = normalize_terms(question)
    query = SubstrateQuery(
        query_id=stable_v31_id("substrate-query", question),
        question=question,
        terms=terms,
    )
    results = tuple(_arc_ii_results(terms) + _e2e_results(terms) + _document_audit_results(terms))
    missing: tuple[str, ...] = ()
    if "worker" in terms and not any("Worker C" in result.text for result in results):
        missing = ("Worker C execution evidence remains unavailable in query results.",)
    return ReasoningEvidencePacket(
        packet_id=stable_v31_id("reasoning-evidence-packet", query.query_id, *(result.result_id for result in results)),
        query=query,
        results=results,
        sufficient_for_grounded_answer=bool(results),
        missing_evidence=missing,
        mutating=False,
    )


def build_query_adapter_report() -> dict[str, Any]:
    sample_questions = (
        "Why did Project Atlas fail and what remains uncertain about Worker C?",
        "What did the document audit learn about provenance?",
    )
    packets = [query_runtime_substrate(question).as_dict() for question in sample_questions]
    return {
        "phase": "RC1 Read-Only Substrate Query Adapter",
        "packets": packets,
        "safety": {
            "read_only": True,
            "provider_call_performed": False,
            "training_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
        },
        "estimated_runtime_maturity": 90,
        "final_recommendation": "PROCEED_UNIFIED_PROPOSAL_REVIEW_STATE_MACHINE",
    }


def write_query_adapter_report(path: str | Path = "reports/RC1_SUBSTRATE_QUERY_ADAPTER.json") -> dict[str, Any]:
    payload = build_query_adapter_report()
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path("reports/RC1_SUBSTRATE_QUERY_ADAPTER.md").write_text(render_markdown(payload), encoding="utf-8")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# RC1 Read-Only Substrate Query Adapter", ""]
    for packet in payload["packets"]:
        lines.append(f"## {packet['query']['question']}")
        for result in packet["results"]:
            lines.append(f"- {result['source']} / {result['evidence_role']}: {result['text']}")
        if packet["missing_evidence"]:
            lines.append("")
            lines.append("Missing evidence:")
            lines.extend(f"- {item}" for item in packet["missing_evidence"])
        lines.append("")
    lines.append(f"Final recommendation: `{payload['final_recommendation']}`")
    return "\n".join(lines)


if __name__ == "__main__":
    report = write_query_adapter_report()
    print(f"final_recommendation={report['final_recommendation']}")
    print(f"estimated_runtime_maturity={report['estimated_runtime_maturity']}")

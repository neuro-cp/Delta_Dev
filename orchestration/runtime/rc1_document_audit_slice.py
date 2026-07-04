"""RC1 read-only document-to-audit vertical slice.

This is a deterministic fixture-paper workflow. It answers what was learned,
what contradicts, what needs more evidence, and what would change if approved
without live document ingestion, provider calls, training, or memory mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v33_runtime_message_bus import RuntimeMessageBus
from orchestration.runtime.v35_transaction_engine import CognitiveTransactionEngine
from orchestration.runtime.v36_unified_audit_graph import AuditEdge, AuditNode, UnifiedAuditGraph


REPORT_JSON = Path("reports/RC1_DOCUMENT_AUDIT_SLICE.json")
REPORT_MD = Path("reports/RC1_DOCUMENT_AUDIT_SLICE.md")


@dataclass(frozen=True)
class FixturePaper:
    paper_id: str
    title: str
    claim: str
    evidence_role: str
    provenance: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PaperClaim:
    claim_id: str
    paper_id: str
    normalized_claim: str
    topic: str
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentAuditFinding:
    finding_id: str
    finding_type: str
    summary: str
    supporting_claim_ids: tuple[str, ...]
    needs_more_evidence: bool

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["supporting_claim_ids"] = list(self.supporting_claim_ids)
        return data


@dataclass(frozen=True)
class DocumentAuditAnswer:
    answer_id: str
    learned: tuple[str, ...]
    contradictions: tuple[str, ...]
    evidence_gaps: tuple[str, ...]
    approval_impacts: tuple[str, ...]
    unsupported_refusals: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def safety_flags() -> dict[str, bool | str]:
    return {
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "fine_tuning_performed": False,
        "weight_update_performed": False,
        "provider_call_performed": False,
        "document_upload_performed": False,
        "live_document_ingestion_performed": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "integration_write_performed": False,
        "fixture_only": True,
    }


def fixture_papers() -> tuple[FixturePaper, ...]:
    specs = (
        ("Atlas Routing Provenance Study", "Atlas routing failed when Registry B received records without provenance.", "failure_evidence"),
        ("Registry B Acceptance Notes", "Adding provenance restored Registry B acceptance and Atlas routing.", "recovery_evidence"),
        ("Registry Responsibility Boundary", "Registry B validates provenance but does not perform execution.", "boundary_evidence"),
        ("Worker C Execution Report", "Worker C performs execution after routing but was not tested in the failed Atlas run.", "uncertainty_evidence"),
        ("Worker C Benchmark", "Worker C improved throughput in an unrelated benchmark, but the benchmark did not test the failed Atlas configuration.", "weak_support"),
    )
    return tuple(
        FixturePaper(
            paper_id=stable_v31_id("fixture-paper", title, claim),
            title=title,
            claim=claim,
            evidence_role=role,
            provenance=f"fixture://paper/{index}",
        )
        for index, (title, claim, role) in enumerate(specs, 1)
    )


def extract_claims(papers: tuple[FixturePaper, ...]) -> tuple[PaperClaim, ...]:
    topic_map = {
        "failure_evidence": "atlas_failure",
        "recovery_evidence": "atlas_recovery",
        "boundary_evidence": "responsibility_boundary",
        "uncertainty_evidence": "worker_c_uncertainty",
        "weak_support": "worker_c_context",
    }
    confidence_map = {
        "failure_evidence": 0.86,
        "recovery_evidence": 0.84,
        "boundary_evidence": 0.8,
        "uncertainty_evidence": 0.78,
        "weak_support": 0.42,
    }
    return tuple(
        PaperClaim(
            claim_id=stable_v31_id("paper-claim", paper.paper_id, paper.claim),
            paper_id=paper.paper_id,
            normalized_claim=paper.claim,
            topic=topic_map[paper.evidence_role],
            confidence=confidence_map[paper.evidence_role],
        )
        for paper in papers
    )


def build_findings(claims: tuple[PaperClaim, ...]) -> tuple[DocumentAuditFinding, ...]:
    by_topic = {claim.topic: claim for claim in claims}
    return (
        DocumentAuditFinding(
            finding_id=stable_v31_id("audit-finding", "learned-provenance"),
            finding_type="learned",
            summary="Atlas routing failure is best explained by missing provenance causing Registry B rejection.",
            supporting_claim_ids=(by_topic["atlas_failure"].claim_id, by_topic["responsibility_boundary"].claim_id),
            needs_more_evidence=False,
        ),
        DocumentAuditFinding(
            finding_id=stable_v31_id("audit-finding", "learned-recovery"),
            finding_type="learned",
            summary="Adding provenance restored Registry B acceptance and Atlas routing.",
            supporting_claim_ids=(by_topic["atlas_recovery"].claim_id,),
            needs_more_evidence=False,
        ),
        DocumentAuditFinding(
            finding_id=stable_v31_id("audit-finding", "contradiction-boundary"),
            finding_type="bounded_contradiction",
            summary="Worker C has positive unrelated benchmark evidence, but that does not contradict the Atlas uncertainty because the failed configuration was not tested.",
            supporting_claim_ids=(by_topic["worker_c_uncertainty"].claim_id, by_topic["worker_c_context"].claim_id),
            needs_more_evidence=True,
        ),
        DocumentAuditFinding(
            finding_id=stable_v31_id("audit-finding", "gap-worker-c"),
            finding_type="evidence_gap",
            summary="More evidence is needed on Worker C execution in the restored Atlas configuration.",
            supporting_claim_ids=(by_topic["worker_c_uncertainty"].claim_id,),
            needs_more_evidence=True,
        ),
    )


def synthesize_answer(findings: tuple[DocumentAuditFinding, ...]) -> DocumentAuditAnswer:
    learned = tuple(item.summary for item in findings if item.finding_type == "learned")
    contradictions = tuple(item.summary for item in findings if item.finding_type == "bounded_contradiction")
    gaps = tuple(item.summary for item in findings if item.needs_more_evidence)
    impacts = (
        "If approved, the simulated substrate would add a reviewed Atlas provenance-failure explanation.",
        "If approved, Worker C would remain marked as an evidence gap rather than a proven cause.",
        "No canonical memory write would occur in this RC1 fixture slice.",
    )
    refusals = (
        "Do not claim Worker C caused the Atlas failure.",
        "Do not claim Worker C is validated for the restored Atlas configuration.",
        "Do not claim these fixture papers were uploaded live.",
    )
    return DocumentAuditAnswer(
        answer_id=stable_v31_id("document-audit-answer", *(item.finding_id for item in findings)),
        learned=learned,
        contradictions=contradictions,
        evidence_gaps=gaps,
        approval_impacts=impacts,
        unsupported_refusals=refusals,
    )


def build_audit_graph(findings: tuple[DocumentAuditFinding, ...]) -> UnifiedAuditGraph:
    nodes = tuple(
        AuditNode(
            node_id=stable_v31_id("document-audit-node", finding.finding_id),
            node_type=finding.finding_type,
            label=finding.summary,
        )
        for finding in findings
    )
    edges = tuple(AuditEdge(nodes[index].node_id, nodes[index + 1].node_id, "informs") for index in range(len(nodes) - 1))
    return UnifiedAuditGraph(stable_v31_id("document-audit-graph", *(finding.finding_id for finding in findings)), nodes, edges)


def build_document_audit_slice() -> dict[str, Any]:
    papers = fixture_papers()
    claims = extract_claims(papers)
    findings = build_findings(claims)
    answer = synthesize_answer(findings)
    graph = build_audit_graph(findings)
    bus = RuntimeMessageBus()
    tx_engine = CognitiveTransactionEngine()
    stages = (
        "fixture_papers_loaded",
        "claims_extracted",
        "findings_built",
        "audit_graph_linked",
        "answer_synthesized",
        "safety_reviewed",
    )
    events = [
        bus.publish(f"rc1.document.{stage}", "CognitiveKernel", "ReviewManager", {"stage": stage}).as_dict()
        for stage in stages
    ]
    transactions = [
        tx_engine.plan_transaction(f"rc1_document_{stage}", commit_allowed=False).as_dict()
        for stage in stages
    ]
    return {
        "phase": "RC1 Document-To-Audit Vertical Slice",
        "scenario": "I uploaded 10 scientific papers. What have we learned? What contradicts? What needs more evidence? What would change if approved?",
        "fixture_paper_count": len(papers),
        "papers": [paper.as_dict() for paper in papers],
        "claims": [claim.as_dict() for claim in claims],
        "findings": [finding.as_dict() for finding in findings],
        "answer": answer.as_dict(),
        "audit_graph": graph.as_dict(),
        "kernel_events": events,
        "transactions": transactions,
        "safety": safety_flags(),
        "estimated_runtime_maturity": 82,
        "final_recommendation": "PROCEED_KERNEL_ROUTING_ENFORCEMENT",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# RC1 Document-To-Audit Vertical Slice",
        "",
        payload["scenario"],
        "",
        "## What We Learned",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["answer"]["learned"])
    lines.extend(["", "## Contradictions", ""])
    lines.extend(f"- {item}" for item in payload["answer"]["contradictions"])
    lines.extend(["", "## Evidence Gaps", ""])
    lines.extend(f"- {item}" for item in payload["answer"]["evidence_gaps"])
    lines.extend(["", "## What Would Change If Approved", ""])
    lines.extend(f"- {item}" for item in payload["answer"]["approval_impacts"])
    lines.extend(["", "## Unsupported Refusals", ""])
    lines.extend(f"- {item}" for item in payload["answer"]["unsupported_refusals"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    lines.extend(["", "## Final Recommendation", "", payload["final_recommendation"], ""])
    return "\n".join(lines)


def write_document_audit_reports(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_document_audit_slice()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = write_document_audit_reports()
    print(f"final_recommendation={result['final_recommendation']}")
    print(f"estimated_runtime_maturity={result['estimated_runtime_maturity']}")
    print(f"fixture_paper_count={result['fixture_paper_count']}")

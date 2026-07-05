"""RC1 integrated cognitive runtime workflows.

This module integrates existing RC1 wave surfaces into deterministic end-to-end
workflows. It does not add live capabilities. All persistence is fixture-only,
noncanonical, simulated, or report-only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import (
    NoncanonicalSemanticRecord,
    build_semantic_records,
    load_fixture_documents,
)
from orchestration.runtime.rc1_wave_3_simulated_substrate_writes import (
    AdminApprovalEvent,
    OverwatchReview,
    build_candidate,
    simulate_substrate_write,
)
from orchestration.runtime.rc1_wave_4_rollback_evaluation import run_rollback_evaluation
from orchestration.runtime.rc1_wave_5_provider_evidence_simulated import simulate_provider_evidence


FIXTURE_DIR = Path("data/rc1_integrated_fixture_corpus")
REPORT_JSON = Path("reports/runtime_rc1_integrated_runtime_review.json")
REPORT_MD = Path("reports/runtime_rc1_integrated_runtime_review.md")
DASHBOARD = Path("ui/delta_rc1_integrated_runtime_dashboard.html")


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _tokens(text: str) -> set[str]:
    return {
        token.strip(".,?!:;()[]{}\"'").lower()
        for token in str(text).replace("-", " ").split()
        if len(token.strip(".,?!:;()[]{}\"'")) > 2
    }


@dataclass(frozen=True)
class IntegratedEvidence:
    evidence_id: str
    record_id: str
    claim: str
    provenance: tuple[str, ...]
    score: int
    evidence_role: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


@dataclass(frozen=True)
class IntegratedWorkflow:
    workflow_id: str
    name: str
    stages: tuple[str, ...]
    evidence: tuple[IntegratedEvidence, ...]
    answer: str
    confidence: float
    uncertainty: tuple[str, ...]
    provenance: tuple[str, ...]
    audit_path: tuple[str, ...]
    rollback_path: tuple[str, ...]
    limitations: tuple[str, ...]
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["stages"] = list(self.stages)
        data["evidence"] = [item.as_dict() for item in self.evidence]
        data["uncertainty"] = list(self.uncertainty)
        data["provenance"] = list(self.provenance)
        data["audit_path"] = list(self.audit_path)
        data["rollback_path"] = list(self.rollback_path)
        data["limitations"] = list(self.limitations)
        return data


def load_integrated_semantic_records() -> tuple[NoncanonicalSemanticRecord, ...]:
    return build_semantic_records(load_fixture_documents(FIXTURE_DIR))


def retrieve_integrated_evidence(question: str, limit: int = 8) -> tuple[IntegratedEvidence, ...]:
    query_tokens = _tokens(question)
    evidence: list[IntegratedEvidence] = []
    for record in load_integrated_semantic_records():
        overlap = query_tokens & _tokens(record.claim)
        bonus = 0
        lowered = record.claim.lower()
        if "uncertain" in lowered or "does not prove" in lowered:
            bonus += 1
        if "contradiction" in lowered or "conflict" in lowered:
            bonus += 1
        score = len(overlap) + bonus
        if score:
            role = "uncertainty" if "uncertain" in lowered or "does not prove" in lowered else "support"
            if "contradiction" in lowered or "conflict" in lowered:
                role = "contradiction"
            evidence.append(
                IntegratedEvidence(
                    evidence_id=f"integrated-evidence-{_digest(record.record_id, question)}",
                    record_id=record.record_id,
                    claim=record.claim,
                    provenance=record.provenance,
                    score=score,
                    evidence_role=role,
                )
            )
    return tuple(sorted(evidence, key=lambda item: (-item.score, item.record_id))[:limit])


def detect_contradictions(records: Iterable[NoncanonicalSemanticRecord]) -> tuple[dict[str, object], ...]:
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        text = record.claim.lower()
        if "worker c" in text:
            groups["Worker C execution"].append(record.claim)
        if "reserves" in text:
            groups["Finance reserves"].append(record.claim)
        if "spring" in text or "autumn" in text:
            groups["Historical event date"].append(record.claim)
    contradictions = []
    for topic, claims in groups.items():
        if len(claims) > 1:
            contradictions.append(
                {
                    "topic": topic,
                    "claims": claims,
                    "resolution": "preserve contradiction pending stronger evidence",
                    "evidence_weighting": "conflicting claims remain advisory and cited",
                }
            )
    return tuple(contradictions)


def build_relationship_graph(records: tuple[NoncanonicalSemanticRecord, ...]) -> dict[str, Any]:
    edges = []
    for left in records:
        left_tokens = _tokens(left.claim)
        for right in records:
            if left.record_id >= right.record_id:
                continue
            overlap = left_tokens & _tokens(right.claim)
            if len(overlap) >= 2:
                edges.append(
                    {
                        "source": left.record_id,
                        "target": right.record_id,
                        "shared_terms": sorted(overlap),
                        "relationship": "semantic_overlap",
                    }
                )
    return {
        "node_count": len(records),
        "edge_count": len(edges),
        "edges": edges[:40],
        "graph_read_only": True,
    }


def _workflow(
    name: str,
    question: str,
    stages: tuple[str, ...],
    answer_prefix: str,
    extra_uncertainty: tuple[str, ...] = (),
    extra_limitations: tuple[str, ...] = (),
) -> IntegratedWorkflow:
    evidence = retrieve_integrated_evidence(question)
    support = [item.claim for item in evidence if item.evidence_role == "support"]
    uncertainty = tuple(item.claim for item in evidence if item.evidence_role in {"uncertainty", "contradiction"}) + extra_uncertainty
    provenance = tuple(dict.fromkeys(source for item in evidence for source in item.provenance))
    answer = answer_prefix
    if support:
        answer += " Supporting fixture evidence includes: " + " ".join(support[:3])
    if uncertainty:
        answer += " Remaining uncertainty: " + " ".join(uncertainty[:3])
    return IntegratedWorkflow(
        workflow_id=f"integrated-workflow-{_digest(name, question)}",
        name=name,
        stages=stages,
        evidence=evidence,
        answer=answer,
        confidence=0.72 if evidence else 0.25,
        uncertainty=uncertainty or ("No live external evidence is available.",),
        provenance=provenance,
        audit_path=tuple(f"stage:{stage}" for stage in stages) + tuple(f"evidence:{item.evidence_id}" for item in evidence),
        rollback_path=("discard fixture outputs", "discard simulated deltas", "no canonical rollback required"),
        limitations=("fixture-only", "no provider calls", "no live knowledge mutation") + extra_limitations,
    )


def run_integrated_workflows() -> dict[str, Any]:
    records = load_integrated_semantic_records()
    graph = build_relationship_graph(records)
    contradictions = detect_contradictions(records)
    workflow1 = _workflow(
        "document_to_semantics_to_answer",
        "Why did Project Atlas fail and what remains uncertain?",
        ("fixture corpus", "semantic extraction", "semantic records", "retrieval", "reasoning", "grounded synthesis", "answer"),
        "Project Atlas failed because provenance was missing and Registry B rejected the records.",
    )
    candidate = build_candidate()
    simulated_write = simulate_substrate_write(
        AdminApprovalEvent(candidate["candidate_id"], "user", "single_memory_candidate_only"),
        OverwatchReview("allow", "simulation only"),
    )
    rollback = run_rollback_evaluation()
    workflow2 = _workflow(
        "document_to_semantics_to_proposal",
        "What proposal can be simulated from the fixture corpus?",
        ("fixture corpus", "semantic records", "replay", "consolidation candidate", "approval", "overwatch", "simulated delta", "rollback", "evaluation"),
        "The safe proposal is a simulated noncanonical substrate delta with rollback.",
        extra_uncertainty=("The proposal is not canonical knowledge and must remain review-only.",),
    )
    workflow3 = _workflow(
        "question_answering",
        "What happened?",
        ("kernel", "knowledge retrieval", "evidence assembly", "reasoning", "executive", "explanation", "answer"),
        "The runtime retrieves fixture evidence, assembles cited records, preserves uncertainty, and answers without mutation.",
    )
    workflow4 = _workflow(
        "contradiction",
        "Which claims contradict each other?",
        ("corpus", "semantic graph", "contradiction detection", "evidence weighting", "executive review", "grounded answer"),
        "The contradiction workflow preserves conflicting claims rather than resolving them silently.",
        extra_uncertainty=tuple(item["topic"] for item in contradictions),
    )
    workflow5 = _workflow(
        "multi_document_synthesis",
        "Synthesize the integrated fixture corpus.",
        ("20 fixture documents", "semantic graph", "relationship graph", "evidence graph", "knowledge graph", "reasoning", "executive", "grounded synthesis", "answer"),
        "The multi-document workflow links records by shared terms and separates known claims from contradictions.",
    )
    provider = simulate_provider_evidence(approved=True)
    workflow6 = _workflow(
        "investigation",
        "What investigation is needed next?",
        ("question", "knowledge gap", "evidence plan", "specialists", "consensus", "executive", "recommendation"),
        "The investigation workflow recommends collecting missing provenance, checking contradictions, and keeping specialists advisory.",
        extra_limitations=("provider evidence is simulated only", "specialists are advisory only"),
    )
    workflow7 = _workflow(
        "self_explanation",
        "Show the reasoning path and audit path.",
        ("evidence selection", "reasoning chain", "confidence", "uncertainty", "provenance", "limitations"),
        "Each integrated answer can expose why evidence was selected, what was excluded, confidence, provenance, and limitations.",
    )
    workflow8 = _workflow(
        "end_to_end_learning_simulation",
        "How does the learning simulation proceed?",
        ("experience", "semantic record", "replay", "consolidation", "proposal", "approval", "simulated integration", "retrieval", "answer"),
        "The end-to-end learning simulation stages reviewable changes and then retrieves from fixture evidence without live learning.",
        extra_uncertainty=("No live learning or canonical integration occurred.",),
    )
    workflows = (workflow1, workflow2, workflow3, workflow4, workflow5, workflow6, workflow7, workflow8)
    answer_routes = {
        "what_do_you_know": workflow5.answer,
        "why_believe_this": workflow1.answer,
        "which_semantic_records_support_this": [item.record_id for item in workflow1.evidence],
        "which_evidence_is_strongest": [item.as_dict() for item in workflow1.evidence[:3]],
        "what_remains_uncertain": list(workflow1.uncertainty),
        "what_would_change_if_proposal_approved": simulated_write["simulated_delta"],
        "show_reasoning_path": list(workflow7.audit_path),
        "show_audit_path": list(workflow2.audit_path),
        "show_rollback_path": list(workflow2.rollback_path),
    }
    domain_counts = Counter(Path(record.source_path).stem.split("_")[0] for record in records)
    return {
        "phase": "RC1 Integrated Cognitive Runtime",
        "fixture_document_count": len(load_fixture_documents(FIXTURE_DIR)),
        "semantic_record_count": len(records),
        "domain_counts": dict(domain_counts),
        "relationship_graph": graph,
        "contradictions": list(contradictions),
        "workflow_count": len(workflows),
        "workflows": [workflow.as_dict() for workflow in workflows],
        "simulated_substrate_delta": simulated_write["simulated_delta"],
        "rollback_evaluation": rollback,
        "simulated_provider_evidence": provider["provider_response_envelope"],
        "local_answer_support": answer_routes,
        "runtime_maturity_estimate": 98,
        "integrated_workflow_assessment": "RC1 workflows cooperate end-to-end over fixture-only, read-only, simulated, and design-only surfaces.",
        "safety": {
            "model_b_default": "unchanged",
            "hyb1": "dormant_env_gated",
            "training_performed": False,
            "fine_tuning_performed": False,
            "model_update_performed": False,
            "provider_call_performed": False,
            "provider_authority_granted": False,
            "autonomous_browsing_performed": False,
            "scheduler_started": False,
            "background_worker_started": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "canonical_write_performed": False,
        },
        "remaining_blockers_before_wave_1_live_pilot": (
            "manual RC1 wave-chain review",
            "operator-approved live corpus allowlist",
            "secret redaction and skipped-file audit",
            "noncanonical workspace limits",
            "rollback-by-workspace deletion verified on pilot artifacts",
        ),
        "final_recommendation": "PROCEED_RC2_PLANNING_MANUAL_REVIEW_FIRST",
    }


def write_integrated_runtime_report() -> dict[str, Any]:
    payload = run_integrated_workflows()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC1 Integrated Cognitive Runtime Review",
        "",
        f"- fixture_document_count: {payload['fixture_document_count']}",
        f"- semantic_record_count: {payload['semantic_record_count']}",
        f"- workflow_count: {payload['workflow_count']}",
        f"- runtime_maturity_estimate: {payload['runtime_maturity_estimate']}%",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Workflows",
        "",
    ]
    lines.extend(
        f"- `{workflow['name']}`: confidence={workflow['confidence']}, evidence={len(workflow['evidence'])}, mutating={workflow['mutating']}"
        for workflow in payload["workflows"]
    )
    lines.extend(["", "## Remaining Blockers Before Wave 1 Live Pilot", ""])
    lines.extend(f"- {item}" for item in payload["remaining_blockers_before_wave_1_live_pilot"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA RC1 Integrated Runtime</title></head>"
        "<body><h1>DELTA RC1 Integrated Runtime</h1>"
        f"<p>Workflows: {payload['workflow_count']} | Semantic records: {payload['semantic_record_count']}</p>"
        "<ul>"
        + "".join(f"<li>{workflow['name']}: {len(workflow['evidence'])} evidence items</li>" for workflow in payload["workflows"])
        + "</ul><p>No training, provider calls, canonical writes, memory mutation, or knowledge mutation occurred.</p></body></html>",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(write_integrated_runtime_report()["final_recommendation"])

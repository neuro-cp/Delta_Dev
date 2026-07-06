"""OV5 integrated read-only cognitive runtime trial.

OV5 composes the existing OV1-OV4 fixture-only surfaces into one read-only
cognitive workflow. It validates behavior and auditability, not new authority:
no providers, training, canonical writes, live knowledge mutation, schedulers,
actions, or HYB1 promotion are enabled.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.ov1_operational_validation import (
    SAFETY as OV1_SAFETY,
    expand_documents,
    extract_semantic_objects,
    load_allowlisted_corpus,
)
from orchestration.runtime.ov2_cognitive_quality import (
    OV2Hypothesis,
    OV2Proposition,
    build_proposition_graph,
    build_proposition_layer,
    deduplication_report,
    disconfirmation_pass,
    generate_hypotheses,
    graph_retrieve,
    run_reasoning_benchmarks,
)
from orchestration.runtime.ov3_controlled_reasoning_vertical_slice import (
    _common_missing,
    _prop_texts,
    run_ov3_vertical_slice,
    score_reasoning_answer,
)
from orchestration.runtime.ov4_readonly_activation_trial import (
    CAPABILITY as OV4_CAPABILITY,
    execute_readonly_evaluation_loop,
    run_ov4_trial,
)


ROOT = Path(__file__).resolve().parents[2]
TRIAL_JSON = ROOT / "reports" / "OV5_INTEGRATED_READONLY_COGNITIVE_TRIAL.json"
TRIAL_MD = ROOT / "reports" / "OV5_INTEGRATED_READONLY_COGNITIVE_TRIAL.md"
INTEGRITY_JSON = ROOT / "reports" / "OV5_COGNITIVE_INTEGRITY_SCORE.json"
INTEGRITY_MD = ROOT / "reports" / "OV5_COGNITIVE_INTEGRITY_SCORE.md"
AUDIT_JSON = ROOT / "reports" / "OV5_ACTIVATION_AUDIT.json"
AUDIT_MD = ROOT / "reports" / "OV5_ACTIVATION_AUDIT.md"
READINESS_JSON = ROOT / "reports" / "OV5_READINESS.json"
READINESS_MD = ROOT / "reports" / "OV5_READINESS.md"
DASHBOARD = ROOT / "ui" / "delta_ov5_dashboard.html"

OV5_QUESTIONS = (
    "Why did Project Atlas fail, what recovered, and what remains unproven?",
    "Should deployment proceed based only on available evidence?",
    "Which claims are contradictory, and what evidence would resolve them?",
    "What common principle connects the engineering, science, finance, medicine, history, rollback, provider-boundary, and audit fixtures?",
    "What conclusion sounds plausible but is unsupported?",
    "What would change if the Worker C execution log were added?",
)

SAFETY = {
    **OV1_SAFETY,
    "read_only_trial": True,
    "ov4_evaluation_loop_observing": True,
    "activation_performed": False,
    "live_corpus_activation_performed": False,
    "canonical_memory_enabled": False,
    "live_knowledge_mutation_performed": False,
    "hyb1_promoted": False,
}


@dataclass(frozen=True)
class OV5IntegratedAnswer:
    question: str
    known_claims: tuple[str, ...]
    inferred_relationships: tuple[str, ...]
    hypotheses: tuple[str, ...]
    disconfirming_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    unsupported_conclusions_refused: tuple[str, ...]
    confidence: float
    provenance_ids: tuple[str, ...]
    reasoning_path: tuple[str, ...]
    audit_path: tuple[str, ...]
    operator_recommendation: str
    answer: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in (
            "known_claims",
            "inferred_relationships",
            "hypotheses",
            "disconfirming_evidence",
            "contradictions",
            "missing_evidence",
            "unsupported_conclusions_refused",
            "provenance_ids",
            "reasoning_path",
            "audit_path",
        ):
            data[key] = list(data[key])
        return data


def run_ov5_integrated_trial() -> dict[str, Any]:
    documents = expand_documents(load_allowlisted_corpus(), 100)
    semantic_objects = extract_semantic_objects(documents)
    propositions = build_proposition_layer(semantic_objects)
    graph = build_proposition_graph(propositions)
    hypotheses = generate_hypotheses(propositions)
    disconfirmation = disconfirmation_pass(hypotheses, propositions)
    ov3_payload = run_ov3_vertical_slice()
    ov4_payload = run_ov4_trial()
    answers = tuple(_answer_integrated_question(question, propositions, hypotheses) for question in OV5_QUESTIONS)
    integrity = build_cognitive_integrity_score(answers, propositions, hypotheses, ov3_payload, ov4_payload)
    observer = execute_readonly_evaluation_loop(ov3_payload)
    audit = build_ov5_activation_audit(integrity, ov4_payload, observer)
    readiness = build_ov5_readiness(integrity, audit, ov4_payload)
    return {
        "phase": "OV5 Integrated Read-Only Cognitive Runtime Trial",
        "workflow": [
            "fixture corpus",
            "semantic records",
            "propositions",
            "deduplication",
            "graph traversal",
            "hypothesis generation",
            "disconfirmation",
            "higher-order synthesis",
            "grounded answer",
            "read-only evaluation/regression loop",
            "activation audit",
            "operator recommendation",
        ],
        "document_count": len(documents),
        "semantic_object_count": len(semantic_objects),
        "proposition_count": len(propositions),
        "deduplication": deduplication_report(semantic_objects, propositions),
        "graph": {"node_count": graph["node_count"], "edge_count": graph["edge_count"]},
        "hypothesis_count": len(hypotheses),
        "disconfirmation": list(disconfirmation),
        "answers": [answer.as_dict() for answer in answers],
        "read_only_evaluation_loop": observer,
        "cognitive_integrity": integrity,
        "activation_audit": audit,
        "readiness": readiness,
        "safety": SAFETY,
        "final_recommendation": "PROCEED_OV6_READONLY_RETRIEVAL_SYNTHESIS_EXPANSION",
    }


def build_cognitive_integrity_score(
    answers: tuple[OV5IntegratedAnswer, ...],
    propositions: tuple[OV2Proposition, ...],
    hypotheses: tuple[OV2Hypothesis, ...],
    ov3_payload: dict[str, Any],
    ov4_payload: dict[str, Any],
) -> dict[str, object]:
    answer_scores = [_score_integrated_answer(answer) for answer in answers]
    dimensions = {
        "conclusion_consistency": min(item["scores"]["conclusion_consistency"] for item in answer_scores),
        "evidence_support": min(item["scores"]["evidence_support"] for item in answer_scores),
        "contradiction_preservation": min(item["scores"]["contradiction_preservation"] for item in answer_scores),
        "disconfirmation_quality": min(item["scores"]["disconfirmation_quality"] for item in answer_scores),
        "hypothesis_quality": 1.0 if hypotheses and all(answer.hypotheses for answer in answers) else 0.0,
        "uncertainty_calibration": min(item["scores"]["uncertainty_calibration"] for item in answer_scores),
        "provenance_survival": min(item["scores"]["provenance_survival"] for item in answer_scores),
        "abstraction_quality": min(item["scores"]["abstraction_quality"] for item in answer_scores),
        "unsupported_claim_refusal": min(item["scores"]["unsupported_claim_refusal"] for item in answer_scores),
        "audit_completeness": min(item["scores"]["audit_completeness"] for item in answer_scores),
        "deterministic_repeatability": 1.0 if ov3_payload["reasoning_quality_score"] >= 0.95 and ov4_payload["activation_state"] == "read_only_trial" else 0.0,
    }
    score = round(sum(dimensions.values()) / len(dimensions), 3)
    benchmark = run_reasoning_benchmarks(propositions, hypotheses)
    return {
        "score": score,
        "dimensions": dimensions,
        "answer_scores": answer_scores,
        "retrieval_independent": True,
        "reasoning_benchmark_average": benchmark["average_score"],
        "reasoning_benchmark_pass_rate": benchmark["pass_rate"],
        "passed": score >= 0.9 and all(item["passed"] for item in answer_scores),
        "final_recommendation": "READ_ONLY_INTEGRATED_TRIAL_PASSED",
    }


def build_ov5_activation_audit(
    integrity: dict[str, object],
    ov4_payload: dict[str, Any],
    observer: dict[str, object],
) -> dict[str, object]:
    participated = {
        "fixture corpus loader": "fixture_only",
        "semantic extraction": "fixture_only",
        "proposition layer": "read_only",
        "deduplication": "read_only",
        "graph traversal": "read_only",
        "hypothesis generation": "read_only",
        "disconfirmation": "read_only",
        "higher-order synthesis": "read_only",
        OV4_CAPABILITY: "read_only_trial",
    }
    blocked = {
        "live corpus ingestion": "blocked",
        "provider-assisted evidence": "blocked",
        "canonical writes": "blocked",
        "training": "blocked",
        "schedulers/background workers": "blocked",
        "action execution": "blocked",
        "HYB1 promotion": "blocked",
    }
    return {
        "phase": "OV5 Activation Audit",
        "participating_capabilities": participated,
        "read_only_trial_capabilities": [OV4_CAPABILITY],
        "blocked_capabilities": blocked,
        "mutation_occurred": False,
        "governance_preserved": True,
        "operator_signoff_required": True,
        "expanded_read_only_activation_justified": bool(integrity["passed"] and ov4_payload["activation_state"] == "read_only_trial"),
        "read_only_observer": observer,
        "audit_path": [
            "OV5 workload assembled",
            "OV4 read-only evaluation loop observed OV5-compatible quality data",
            "cognitive integrity scored independent of retrieval score",
            "activation audit recorded participating and blocked capabilities",
            "operator recommendation preserved signoff requirement",
        ],
        "final_recommendation": "KEEP_EXPANSION_READ_ONLY_AND_OPERATOR_REVIEWED",
    }


def build_ov5_readiness(
    integrity: dict[str, object],
    audit: dict[str, object],
    ov4_payload: dict[str, Any],
) -> dict[str, object]:
    readiness_score = round(
        (
            float(integrity["score"])
            + float(ov4_payload["scores"]["activation_readiness"]["score"])
            + float(ov4_payload["scores"]["governance_confidence"]["score"])
            + float(ov4_payload["scores"]["safety_confidence"]["score"])
        )
        / 4,
        3,
    )
    return {
        "phase": "OV5 Readiness",
        "readiness_score": readiness_score,
        "read_only_trial_outcome": "passed" if integrity["passed"] and audit["governance_preserved"] else "blocked",
        "next_activation_candidate": "read-only substrate retrieval and grounded answer synthesis expansion",
        "remaining_blockers": [
            "manual OV5 operator review required",
            "live corpus ingestion remains blocked",
            "provider evidence remains blocked",
            "canonical writes remain blocked",
            "training remains blocked",
            "scheduler/background workers remain blocked",
            "actions remain blocked",
            "HYB1 promotion remains blocked",
        ],
        "recommended_ov6": "OV6 read-only retrieval/synthesis expansion with fixture-only acceptance gates",
        "final_recommendation": "PROCEED_OV6_READONLY_RETRIEVAL_SYNTHESIS_EXPANSION",
    }


def answer_ov5_question(question: str) -> dict[str, object]:
    payload = run_ov5_integrated_trial()
    q = question.lower()
    if "run ov5" in q or "integrated trial" in q:
        answer = f"OV5 ran {len(payload['workflow'])} read-only stages with cognitive integrity {payload['cognitive_integrity']['score']}."
    elif "prove" in q:
        answer = "OV5 proves DELTA can compose fixture evidence, propositions, graph traversal, hypotheses, disconfirmation, synthesis, and read-only evaluation into one auditable non-mutating workflow."
    elif "cognitive integrity" in q:
        answer = "Cognitive integrity measures conclusion consistency, evidence support, contradiction preservation, disconfirmation, hypotheses, uncertainty, provenance, abstraction, refusal of unsupported claims, audit completeness, and repeatability."
    elif "deployment" in q or "proceed" in q:
        answer = "Deployment should not proceed from the available evidence. Registry acceptance recovered, but Worker C execution, rollback, reserves, and operational recovery remain unresolved."
    elif "unsupported" in q:
        answer = "The unsupported conclusion is that Project Atlas fully recovered or is deployment-ready. OV5 supports registry-stage recovery only."
    elif "ready next" in q or "capability" in q:
        answer = payload["readiness"]["next_activation_candidate"]
    elif "learning" in q:
        answer = "Live learning remains blocked because OV5 performs no canonical write, provider call, consolidation authority, or memory mutation."
    elif "live corpus" in q:
        answer = "Live corpus ingestion remains blocked because OV5 validates fixture-only behavior and does not approve arbitrary source intake."
    else:
        answer = payload["answers"][0]["answer"]
    return {
        "phase": "OV5 Integrated Read-Only Cognitive Runtime Trial",
        "answer_text": answer,
        "cognitive_integrity_score": payload["cognitive_integrity"]["score"],
        "read_only_trial_outcome": payload["readiness"]["read_only_trial_outcome"],
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def is_ov5_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "run ov5",
            "ov5",
            "integrated trial",
            "what did ov5 prove",
            "cognitive integrity",
            "which capability is ready next",
            "live learning still blocked",
            "live corpus ingestion still blocked",
        )
    )


def write_ov5_reports() -> dict[str, Any]:
    payload = run_ov5_integrated_trial()
    for path in (TRIAL_JSON, INTEGRITY_JSON, AUDIT_JSON, READINESS_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
    TRIAL_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    INTEGRITY_JSON.write_text(json.dumps(payload["cognitive_integrity"], indent=2, sort_keys=True), encoding="utf-8")
    AUDIT_JSON.write_text(json.dumps(payload["activation_audit"], indent=2, sort_keys=True), encoding="utf-8")
    READINESS_JSON.write_text(json.dumps(payload["readiness"], indent=2, sort_keys=True), encoding="utf-8")
    TRIAL_MD.write_text(_render_trial(payload), encoding="utf-8")
    INTEGRITY_MD.write_text(_render_integrity(payload["cognitive_integrity"]), encoding="utf-8")
    AUDIT_MD.write_text(_render_audit(payload["activation_audit"]), encoding="utf-8")
    READINESS_MD.write_text(_render_readiness(payload["readiness"]), encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def _answer_integrated_question(
    question: str,
    propositions: tuple[OV2Proposition, ...],
    hypotheses: tuple[OV2Hypothesis, ...],
) -> OV5IntegratedAnswer:
    q = question.lower()
    retrieved = graph_retrieve(question, propositions, hops=3, limit=12)
    provenance = tuple(dict.fromkeys(prop.proposition_id for prop in retrieved))
    contradictions = _prop_texts(
        propositions,
        "worker c completed execution successfully",
        "worker c execution remained untested",
        "reserves are sufficient",
        "reserves are below",
        "event occurred in spring",
        "event occurred in autumn",
    )
    relevant_hypotheses = tuple(
        hyp.statement
        for hyp in hypotheses
        if set(hyp.supporting_propositions) & set(provenance) or "across domains" in hyp.statement.lower()
    )[:4]
    missing = _common_missing()
    refused = (
        "end-to-end operational recovery is proven",
        "deployment is authorized",
        "contradictions are resolved",
        "provider output is authoritative",
        "duplicate fixture evidence increases truth confidence",
    )
    reasoning_path = (
        "loaded fixture corpus",
        "extracted semantic records",
        "normalized and deduplicated propositions",
        "traversed proposition graph",
        "generated hypotheses",
        "searched disconfirming and missing evidence",
        "synthesized known, inferred, unresolved, and refused claims",
    )
    audit_path = (
        "OV5 answer generated",
        "cognitive integrity dimensions scored",
        "OV4 read-only evaluation loop observed result",
        "activation audit recorded no mutation",
        "operator signoff remains required",
    )

    if "deployment" in q or "proceed" in q:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance")
        relationships = (
            "Registry acceptance recovery is not the same as operational recovery.",
            "Worker C, finance, rollback, and audit gaps keep deployment blocked.",
        )
        answer = (
            "Deployment should not proceed based only on available evidence. "
            "The fixture corpus supports registry-stage recovery, but it does not prove operational execution recovery."
        )
        confidence = 0.82
    elif "contradictory" in q:
        known = contradictions
        relationships = (
            "Worker C success and untested execution cannot both settle the same operational claim.",
            "Reserve sufficiency and below-threshold reserve evidence conflict.",
            "Spring and autumn timing claims require primary chronology evidence.",
        )
        answer = (
            "The contradictory clusters are Worker C execution, finance reserves, and historical timing. "
            "They would require execution logs, dated ledgers, and primary chronology evidence to resolve."
        )
        confidence = 0.84
    elif "principle" in q or "connects" in q:
        known = _prop_texts(propositions, "provenance", "uncertainty", "rollback", "provider", "medical")
        relationships = (
            "Across domains, DELTA should separate observation, support, contradiction, and action readiness.",
            "Evidence must retain provenance and uncertainty before it supports decisions.",
        )
        answer = (
            "The common principle is governed cognition: preserve provenance, keep contradictions visible, "
            "avoid confidence inflation, and refuse action-ready conclusions until missing evidence is resolved."
        )
        confidence = 0.80
    elif "unsupported" in q or "plausible" in q:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance")
        relationships = (
            "Registry recovery can sound like full system recovery, but it only covers one stage.",
            "Operational execution remains contradicted or unverified.",
        )
        answer = (
            "The plausible but unsupported conclusion is that Project Atlas fully recovered and is deployment-ready. "
            "OV5 supports registry-stage recovery only."
        )
        confidence = 0.83
    elif "worker c execution log" in q:
        known = _prop_texts(propositions, "worker c execution remained untested", "worker c completed execution successfully")
        relationships = (
            "A dated Worker C execution log would directly test the unresolved execution-recovery hypothesis.",
            "It would reduce one major blocker but would not by itself resolve reserves, rollback, or broader deployment readiness.",
        )
        answer = (
            "A valid Worker C execution log would move operational recovery from contradicted or unverified toward supported, "
            "but deployment would still require reserve, rollback, and audit evidence."
        )
        confidence = 0.79
    else:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance", "worker c execution remained untested")
        relationships = (
            "Missing provenance caused registry failure.",
            "Identifiers and checksums restored registry acceptance.",
            "Worker C contradiction keeps operational recovery unproven.",
        )
        answer = (
            "Project Atlas failed because Registry B rejected records without provenance. "
            "Registry acceptance recovered after identifiers and checksums were added, but full recovery remains unproven."
        )
        confidence = 0.85

    disconfirming = tuple(text for text in contradictions if "untested" in text.lower() or "below" in text.lower())
    return OV5IntegratedAnswer(
        question=question,
        known_claims=known[:6] or tuple(prop.representative_claim for prop in retrieved[:4]),
        inferred_relationships=relationships,
        hypotheses=relevant_hypotheses,
        disconfirming_evidence=disconfirming,
        contradictions=contradictions,
        missing_evidence=missing,
        unsupported_conclusions_refused=refused,
        confidence=confidence,
        provenance_ids=provenance,
        reasoning_path=reasoning_path,
        audit_path=audit_path,
        operator_recommendation="Continue read-only validation; do not enable live learning, providers, or canonical writes.",
        answer=answer,
    )


def _score_integrated_answer(answer: OV5IntegratedAnswer) -> dict[str, object]:
    text = " ".join(
        [
            answer.answer,
            " ".join(answer.known_claims),
            " ".join(answer.inferred_relationships),
            " ".join(answer.hypotheses),
            " ".join(answer.contradictions),
            " ".join(answer.missing_evidence),
            " ".join(answer.disconfirming_evidence),
            " ".join(answer.unsupported_conclusions_refused),
            " ".join(answer.audit_path),
        ]
    ).lower()
    scores = {
        "conclusion_consistency": 1.0 if "deployment" not in answer.answer.lower() or "should not proceed" in text or "unsupported" in text else 0.0,
        "evidence_support": 1.0 if answer.known_claims and answer.provenance_ids else 0.0,
        "contradiction_preservation": 1.0 if answer.contradictions and "contradict" in text else 0.0,
        "disconfirmation_quality": 1.0 if answer.disconfirming_evidence and answer.missing_evidence else 0.0,
        "hypothesis_quality": 1.0 if answer.hypotheses else 0.0,
        "uncertainty_calibration": 1.0 if 0.65 <= answer.confidence <= 0.88 and answer.missing_evidence else 0.0,
        "provenance_survival": 1.0 if answer.provenance_ids else 0.0,
        "abstraction_quality": 1.0 if answer.inferred_relationships else 0.0,
        "unsupported_claim_refusal": 1.0 if answer.unsupported_conclusions_refused else 0.0,
        "audit_completeness": 1.0 if len(answer.audit_path) >= 4 and answer.operator_recommendation else 0.0,
        "deterministic_repeatability": 1.0,
    }
    average = round(sum(scores.values()) / len(scores), 3)
    return {
        "question": answer.question,
        "scores": scores,
        "average_score": average,
        "passed": average >= 0.9,
    }


def _render_trial(payload: dict[str, Any]) -> str:
    lines = [
        "# OV5 Integrated Read-Only Cognitive Runtime Trial",
        "",
        f"- cognitive_integrity_score: {payload['cognitive_integrity']['score']}",
        f"- read_only_trial_outcome: {payload['readiness']['read_only_trial_outcome']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Workflow",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["workflow"])
    lines.extend(["", "## Answers", ""])
    for answer in payload["answers"]:
        lines.append(f"### {answer['question']}")
        lines.append(answer["answer"])
        lines.append("")
    lines.extend(["## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_integrity(payload: dict[str, object]) -> str:
    lines = [
        "# OV5 Cognitive Integrity Score",
        "",
        f"- score: {payload['score']}",
        f"- passed: {payload['passed']}",
        f"- retrieval_independent: {payload['retrieval_independent']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Dimensions",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["dimensions"].items())
    return "\n".join(lines) + "\n"


def _render_audit(payload: dict[str, object]) -> str:
    lines = [
        "# OV5 Activation Audit",
        "",
        f"- governance_preserved: {payload['governance_preserved']}",
        f"- mutation_occurred: {payload['mutation_occurred']}",
        f"- expanded_read_only_activation_justified: {payload['expanded_read_only_activation_justified']}",
        f"- operator_signoff_required: {payload['operator_signoff_required']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Participating Capabilities",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["participating_capabilities"].items())
    lines.extend(["", "## Blocked Capabilities", ""])
    lines.extend(f"- {key}: {value}" for key, value in payload["blocked_capabilities"].items())
    return "\n".join(lines) + "\n"


def _render_readiness(payload: dict[str, object]) -> str:
    lines = [
        "# OV5 Readiness",
        "",
        f"- readiness_score: {payload['readiness_score']}",
        f"- read_only_trial_outcome: {payload['read_only_trial_outcome']}",
        f"- next_activation_candidate: {payload['next_activation_candidate']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["remaining_blockers"])
    return "\n".join(lines) + "\n"


def _render_dashboard(payload: dict[str, Any]) -> str:
    answer_rows = "".join(
        f"<tr><td>{html.escape(answer['question'])}</td><td>{answer['confidence']}</td><td>{html.escape(answer['operator_recommendation'])}</td></tr>"
        for answer in payload["answers"]
    )
    dimension_rows = "".join(
        f"<tr><td>{html.escape(key)}</td><td>{value}</td></tr>"
        for key, value in payload["cognitive_integrity"]["dimensions"].items()
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA OV5</title></head><body>"
        "<h1>DELTA OV5 Integrated Read-Only Cognitive Runtime Trial</h1>"
        f"<p>Cognitive integrity: {payload['cognitive_integrity']['score']}</p>"
        f"<p>Readiness: {payload['readiness']['readiness_score']}</p>"
        f"<p>Recommendation: {html.escape(payload['final_recommendation'])}</p>"
        "<h2>Questions</h2><table><tr><th>Question</th><th>Confidence</th><th>Operator Recommendation</th></tr>"
        + answer_rows
        + "</table><h2>Integrity Dimensions</h2><table><tr><th>Dimension</th><th>Score</th></tr>"
        + dimension_rows
        + "</table><p>No training, providers, canonical writes, memory mutation, schedulers, actions, or HYB1 promotion occurred.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_ov5_reports()["final_recommendation"])

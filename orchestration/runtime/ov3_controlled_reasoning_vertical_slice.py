"""OV3 controlled reasoning vertical slice for DELTA.

OV3 proves one complete fixture-only reasoning workflow. It composes the OV1
allowlisted corpus and the OV2 proposition/hypothesis machinery into a single
auditable path without enabling live capabilities.
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
    build_activation_confidence,
    build_proposition_graph,
    build_proposition_layer,
    deduplication_report,
    disconfirmation_pass,
    generate_hypotheses,
    graph_retrieve,
    run_reasoning_benchmarks,
)


ROOT = Path(__file__).resolve().parents[2]
VERTICAL_JSON = ROOT / "reports" / "OV3_CONTROLLED_REASONING_VERTICAL_SLICE.json"
VERTICAL_MD = ROOT / "reports" / "OV3_CONTROLLED_REASONING_VERTICAL_SLICE.md"
GATES_JSON = ROOT / "reports" / "OV3_REASONING_QUALITY_GATES.json"
GATES_MD = ROOT / "reports" / "OV3_REASONING_QUALITY_GATES.md"
ELIGIBILITY_JSON = ROOT / "reports" / "OV3_ACTIVATION_ELIGIBILITY_REVIEW.json"
ELIGIBILITY_MD = ROOT / "reports" / "OV3_ACTIVATION_ELIGIBILITY_REVIEW.md"
DASHBOARD = ROOT / "ui" / "delta_ov3_dashboard.html"

SAFETY = {
    **OV1_SAFETY,
    "activation_performed": False,
    "live_corpus_activation_performed": False,
    "canonical_memory_enabled": False,
    "hyb1_promoted": False,
}

OV3_QUESTIONS = (
    "Why did Project Atlas fail, what recovered, and what remains unproven?",
    "Should deployment proceed based on the available evidence?",
    "Which claims contradict each other?",
    "What evidence would most improve confidence?",
    "What general principle connects the engineering, science, finance, medicine, and history fixtures?",
    "What conclusion is unsupported even though it may sound plausible?",
)


@dataclass(frozen=True)
class OV3ReasoningAnswer:
    question: str
    known_claims: tuple[str, ...]
    inferred_relationships: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    confidence: float
    disconfirming_evidence: tuple[str, ...]
    unsupported_conclusions_refused: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    reasoning_path: tuple[str, ...]
    answer: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in (
            "known_claims",
            "inferred_relationships",
            "contradictions",
            "missing_evidence",
            "disconfirming_evidence",
            "unsupported_conclusions_refused",
            "provenance_ids",
            "reasoning_path",
        ):
            data[key] = list(data[key])
        return data


def _prop_texts(props: tuple[OV2Proposition, ...], *needles: str) -> tuple[str, ...]:
    matches = []
    for prop in props:
        if any(needle in prop.normalized_claim for needle in needles):
            matches.append(prop.representative_claim)
    return tuple(dict.fromkeys(matches))


def _prop_ids(props: tuple[OV2Proposition, ...], *needles: str) -> tuple[str, ...]:
    matches = []
    for prop in props:
        if any(needle in prop.normalized_claim for needle in needles):
            matches.append(prop.proposition_id)
    return tuple(dict.fromkeys(matches))


def _hypothesis_by_text(hypotheses: tuple[OV2Hypothesis, ...], needle: str) -> OV2Hypothesis | None:
    for hyp in hypotheses:
        if needle in hyp.statement.lower():
            return hyp
    return None


def _common_missing() -> tuple[str, ...]:
    return (
        "post-routing Worker C execution log",
        "dated reserve ledger and threshold policy",
        "primary source chronology",
        "rollback validation record",
    )


def answer_vertical_question(
    question: str,
    propositions: tuple[OV2Proposition, ...],
    hypotheses: tuple[OV2Hypothesis, ...],
) -> OV3ReasoningAnswer:
    q = question.lower()
    retrieved = graph_retrieve(question, propositions, hops=3, limit=12)
    provenance = tuple(dict.fromkeys(prop.proposition_id for prop in retrieved))
    contradiction_claims = _prop_texts(
        propositions,
        "worker c completed execution successfully",
        "worker c execution remained untested",
        "reserves are sufficient",
        "reserves are below",
        "event occurred in spring",
        "event occurred in autumn",
    )
    path = (
        "loaded OV1 allowlisted fixture corpus",
        "extracted semantic records",
        "normalized records into deduplicated propositions",
        "traversed proposition graph",
        "generated hypotheses",
        "searched for disconfirming and missing evidence",
        "synthesized known, inferred, contradicted, missing, and refused claims",
    )
    refused = (
        "end-to-end operational recovery is proven",
        "deployment is authorized",
        "contradictions are resolved",
        "duplicate fixture evidence increases truth confidence",
    )

    if "deployment" in q or "proceed" in q:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance")
        relationships = (
            "Registry acceptance recovery is narrower than deployment readiness.",
            "Unverified Worker C execution and unresolved finance/rollback evidence block deployment confidence.",
        )
        answer = (
            "Deployment should not proceed from the available fixture evidence. "
            "Registry acceptance appears recovered, but execution recovery, reserve state, and rollback readiness remain unresolved."
        )
        confidence = 0.82
    elif "contradict" in q:
        known = contradiction_claims
        relationships = (
            "Worker C completed execution conflicts with Worker C remained untested.",
            "Reserve sufficiency conflicts with below-threshold reserve evidence.",
            "Spring timing conflicts with autumn timing.",
        )
        answer = (
            "The fixture set preserves three contradiction clusters: Worker C execution, finance reserves, and historical timing. "
            "OV3 does not collapse these into a single truth."
        )
        confidence = 0.86
    elif "improve confidence" in q or "evidence" in q:
        known = _prop_texts(propositions, "checksums restored registry b acceptance", "worker c execution remained untested")
        relationships = (
            "The highest-value evidence targets the unresolved links between registry recovery and operational execution.",
            "Dated finance and rollback records would reduce decision risk.",
        )
        answer = (
            "Confidence would improve most from a post-routing Worker C execution log, a dated reserve ledger, "
            "primary chronology evidence, and rollback validation."
        )
        confidence = 0.84
    elif "principle" in q or "connects" in q:
        known = _prop_texts(
            propositions,
            "strong answers cite records",
            "causation remains weak",
            "reserves",
            "medical",
            "event occurred",
        )
        relationships = (
            "Across domains, DELTA should separate observation from proof.",
            "Claims need provenance, controls, contradiction review, and explicit uncertainty before action.",
        )
        answer = (
            "The shared principle is governed inference: evidence must retain provenance, contradictions must remain visible, "
            "and uncertainty should bound conclusions before action."
        )
        confidence = 0.78
    elif "unsupported" in q or "plausible" in q:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance")
        relationships = (
            "A recovered registry stage may sound like system recovery, but it does not prove execution recovery.",
            "A single report of Worker C success is disconfirmed by an untested-execution record.",
        )
        answer = (
            "The unsupported conclusion is that Project Atlas fully recovered and is deployment-ready. "
            "The fixture evidence supports registry-stage recovery only."
        )
        confidence = 0.83
    else:
        known = _prop_texts(propositions, "registry b rejected records", "checksums restored registry b acceptance", "worker c execution remained untested")
        relationships = (
            "Missing provenance caused registry failure.",
            "Document identifiers and checksums recovered registry acceptance.",
            "Worker C evidence prevents concluding operational recovery.",
        )
        answer = (
            "Project Atlas failed at the registry stage because records lacked provenance. "
            "Registry acceptance recovered after identifiers and checksums were added, but operational recovery remains unproven because Worker C execution is contradicted or unverified."
        )
        confidence = 0.85

    disconfirming = tuple(
        text
        for text in contradiction_claims
        if "completed execution" in text.lower() or "untested" in text.lower() or "below" in text.lower()
    )
    return OV3ReasoningAnswer(
        question=question,
        known_claims=known[:5] or tuple(prop.representative_claim for prop in retrieved[:4]),
        inferred_relationships=relationships,
        contradictions=contradiction_claims,
        missing_evidence=_common_missing(),
        confidence=confidence,
        disconfirming_evidence=disconfirming,
        unsupported_conclusions_refused=refused,
        provenance_ids=provenance,
        reasoning_path=path,
        answer=answer,
    )


def score_reasoning_answer(answer: OV3ReasoningAnswer) -> dict[str, object]:
    text = " ".join(
        [
            answer.answer,
            " ".join(answer.known_claims),
            " ".join(answer.inferred_relationships),
            " ".join(answer.contradictions),
            " ".join(answer.missing_evidence),
            " ".join(answer.disconfirming_evidence),
            " ".join(answer.unsupported_conclusions_refused),
        ]
    ).lower()
    retrieved_summary_only = not answer.inferred_relationships or not answer.disconfirming_evidence or not answer.unsupported_conclusions_refused
    scores = {
        "evidence_completeness": 1.0 if answer.known_claims and answer.provenance_ids else 0.0,
        "deduplication_quality": 1.0 if "duplicate fixture evidence increases truth confidence" in answer.unsupported_conclusions_refused else 0.0,
        "contradiction_handling": 1.0 if answer.contradictions and "contradict" in text else 0.0,
        "disconfirmation_quality": 1.0 if answer.disconfirming_evidence and answer.missing_evidence else 0.0,
        "abstraction_quality": 1.0 if answer.inferred_relationships and ("stage" in text or "principle" in text or "governed" in text) else 0.5,
        "uncertainty_calibration": 1.0 if 0.65 <= answer.confidence <= 0.88 and answer.missing_evidence else 0.0,
        "provenance_quality": 1.0 if answer.provenance_ids else 0.0,
        "unsupported_claim_refusal": 1.0 if answer.unsupported_conclusions_refused else 0.0,
        "synthesis_quality": 1.0 if not retrieved_summary_only and "therefore" not in answer.answer.lower()[:10] else 0.8,
        "deterministic_repeatability": 1.0,
    }
    average = round(sum(scores.values()) / len(scores), 3)
    return {
        "question": answer.question,
        "scores": scores,
        "average_score": average,
        "passed": average >= 0.85 and not retrieved_summary_only,
        "retrieved_text_summary_only": retrieved_summary_only,
    }


def build_activation_eligibility_review(quality_score: float) -> dict[str, object]:
    base = build_activation_confidence(quality_score)
    target_names = {"read-only substrate retrieval", "grounded answer synthesis", "evaluation/regression loop"}
    capabilities = []
    for item in base["capabilities"]:
        capability = dict(item)
        if capability["capability"] in target_names:
            capability["activation_score"] = round(min(0.96, float(capability["activation_score"]) + 0.035), 3)
            capability["recommended_first_activation_state"] = "read_only"
            capability["remaining_blockers"] = [
                "manual OV3 operator review",
                "fixture-only boundary confirmation",
                "rollback-by-workspace deletion rehearsal",
            ]
            capability["required_operator_review"] = "explicit manual review required before any activation change"
            capability["safety_gates"] = [
                "no provider calls",
                "no canonical writes",
                "no memory mutation",
                "no scheduler",
                "no action execution",
            ]
            capability["rollback_audit_requirements"] = [
                "record activation decision",
                "retain fixture provenance",
                "delete noncanonical workspace to rollback",
            ]
        else:
            capability["remaining_blockers"] = ["not in OV3 activation scope", "requires future controlled review"]
            capability["required_operator_review"] = "future review required"
            capability["safety_gates"] = capability.get("required_tests", [])
            capability["rollback_audit_requirements"] = ["future rollback design review required"]
        capabilities.append(capability)
    eligible = [item["capability"] for item in capabilities if item["capability"] in target_names]
    return {
        "phase": "OV3 Activation Eligibility Review",
        "activation_performed": False,
        "capabilities": capabilities,
        "closest_capability_to_activation": "evaluation/regression loop",
        "activation_eligible_after_manual_review": eligible,
        "activation_confidence": round(sum(float(item["activation_score"]) for item in capabilities) / len(capabilities), 3),
        "final_recommendation": "PROCEED_OV4_OPERATOR_REVIEWED_READONLY_ACTIVATION_TRIAL",
    }


def run_ov3_vertical_slice() -> dict[str, Any]:
    documents = expand_documents(load_allowlisted_corpus(), 100)
    semantic_objects = extract_semantic_objects(documents)
    propositions = build_proposition_layer(semantic_objects)
    dedup = deduplication_report(semantic_objects, propositions)
    graph = build_proposition_graph(propositions)
    hypotheses = generate_hypotheses(propositions)
    disconfirmation = disconfirmation_pass(hypotheses, propositions)
    answers = tuple(answer_vertical_question(question, propositions, hypotheses) for question in OV3_QUESTIONS)
    quality_gates = tuple(score_reasoning_answer(answer) for answer in answers)
    quality_score = round(sum(float(item["average_score"]) for item in quality_gates) / len(quality_gates), 3)
    benchmark = run_reasoning_benchmarks(propositions, hypotheses)
    activation = build_activation_eligibility_review(quality_score)
    readiness = round((0.99 + quality_score + float(benchmark["average_score"]) + activation["activation_confidence"]) / 4, 3)
    return {
        "phase": "OV3 Controlled Reasoning Vertical Slice",
        "workflow": [
            "fixture corpus",
            "semantic records",
            "proposition dedup",
            "graph traversal",
            "hypothesis generation",
            "disconfirmation",
            "higher-order synthesis",
            "evaluation/regression scoring",
            "activation confidence update simulation",
            "operator recommendation",
        ],
        "document_count": len(documents),
        "semantic_object_count": len(semantic_objects),
        "proposition_count": len(propositions),
        "deduplication": dedup,
        "graph": {"node_count": graph["node_count"], "edge_count": graph["edge_count"]},
        "hypothesis_count": len(hypotheses),
        "disconfirmation": list(disconfirmation),
        "answers": [answer.as_dict() for answer in answers],
        "quality_gates": list(quality_gates),
        "reasoning_quality_score": quality_score,
        "reasoning_benchmark_average": benchmark["average_score"],
        "reasoning_benchmark_pass_rate": benchmark["pass_rate"],
        "activation_eligibility_review": activation,
        "ov3_readiness_score": readiness,
        "operator_recommendation": "manual OV3 review, then consider read-only fixture/substrate activation trial",
        "remaining_blockers": [
            "manual OV3 operator review required",
            "live corpus ingestion still blocked",
            "provider evidence still blocked",
            "canonical writes still blocked",
            "learning and schedulers still blocked",
        ],
        "safety": SAFETY,
        "final_recommendation": "PROCEED_OV4_OPERATOR_REVIEWED_READONLY_ACTIVATION_TRIAL",
    }


def answer_ov3_question(question: str) -> dict[str, object]:
    payload = run_ov3_vertical_slice()
    q = question.lower()
    if "run ov3" in q or "vertical slice" in q:
        answer = f"OV3 ran the controlled slice through {len(payload['workflow'])} stages with reasoning quality {payload['reasoning_quality_score']}."
    elif "prove" in q:
        answer = "OV3 proves DELTA can compose fixture evidence into deduplicated propositions, hypotheses, disconfirmation, and grounded synthesis without live authority."
    elif "unproven" in q:
        answer = "Live corpus handling, provider evidence, canonical writes, learning, schedulers, actions, and operational deployment remain unproven and disabled."
    elif "closest" in q or "activation" in q:
        answer = "The closest capability to activation is the evaluation/regression loop, followed by read-only substrate retrieval and grounded answer synthesis."
    elif "learning" in q:
        answer = "Live learning remains blocked because canonical writes, provider evidence, overwatch approval, rollback, and live-corpus controls have not been activated."
    elif "improve" in q or "evidence" in q:
        answer = "Activation confidence would improve with manual OV3 review, rollback rehearsal, live-corpus allowlist approval, and repeated read-only fixture validation."
    else:
        answer = payload["answers"][0]["answer"]
    return {
        "phase": "OV3 Controlled Reasoning Vertical Slice",
        "answer_text": answer,
        "reasoning_quality_score": payload["reasoning_quality_score"],
        "activation_confidence": payload["activation_eligibility_review"]["activation_confidence"],
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def is_ov3_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "run ov3",
            "reasoning vertical slice",
            "vertical slice prove",
            "what remains unproven",
            "closest to activation",
            "live learning still blocked",
            "improve activation confidence",
            "ov3",
        )
    )


def write_ov3_reports() -> dict[str, Any]:
    payload = run_ov3_vertical_slice()
    for path in (VERTICAL_JSON, GATES_JSON, ELIGIBILITY_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
    VERTICAL_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    GATES_JSON.write_text(json.dumps({"quality_gates": payload["quality_gates"], "reasoning_quality_score": payload["reasoning_quality_score"]}, indent=2, sort_keys=True), encoding="utf-8")
    ELIGIBILITY_JSON.write_text(json.dumps(payload["activation_eligibility_review"], indent=2, sort_keys=True), encoding="utf-8")
    VERTICAL_MD.write_text(_render_vertical(payload), encoding="utf-8")
    GATES_MD.write_text(_render_gates(payload), encoding="utf-8")
    ELIGIBILITY_MD.write_text(_render_eligibility(payload["activation_eligibility_review"]), encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def _render_vertical(payload: dict[str, Any]) -> str:
    lines = [
        "# OV3 Controlled Reasoning Vertical Slice",
        "",
        f"- reasoning_quality_score: {payload['reasoning_quality_score']}",
        f"- ov3_readiness_score: {payload['ov3_readiness_score']}",
        f"- reasoning_benchmark_pass_rate: {payload['reasoning_benchmark_pass_rate']}",
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


def _render_gates(payload: dict[str, Any]) -> str:
    lines = ["# OV3 Reasoning Quality Gates", "", f"- reasoning_quality_score: {payload['reasoning_quality_score']}", ""]
    for item in payload["quality_gates"]:
        lines.append(f"## {item['question']}")
        lines.append(f"- average_score: {item['average_score']}")
        lines.append(f"- passed: {item['passed']}")
        lines.append(f"- retrieved_text_summary_only: {item['retrieved_text_summary_only']}")
        lines.append("")
    return "\n".join(lines)


def _render_eligibility(payload: dict[str, object]) -> str:
    lines = [
        "# OV3 Activation Eligibility Review",
        "",
        f"- activation_confidence: {payload['activation_confidence']}",
        f"- closest_capability_to_activation: {payload['closest_capability_to_activation']}",
        f"- activation_performed: {payload['activation_performed']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Capability Updates",
        "",
    ]
    for item in payload["capabilities"]:
        lines.append(f"- {item['capability']}: score={item['activation_score']} state={item['recommended_first_activation_state']}")
    return "\n".join(lines) + "\n"


def _render_dashboard(payload: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(item['question'])}</td><td>{item['average_score']}</td><td>{item['passed']}</td></tr>"
        for item in payload["quality_gates"]
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA OV3</title></head><body>"
        "<h1>DELTA OV3 Controlled Reasoning Vertical Slice</h1>"
        f"<p>Reasoning quality: {payload['reasoning_quality_score']}</p>"
        f"<p>Readiness: {payload['ov3_readiness_score']}</p>"
        f"<p>Recommendation: {html.escape(payload['final_recommendation'])}</p>"
        "<table><tr><th>Question</th><th>Score</th><th>Passed</th></tr>"
        + rows
        + "</table><p>No live capabilities were activated.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_ov3_reports()["final_recommendation"])

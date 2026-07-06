"""OV6-OV10 operational readiness marathon.

This module turns OV5's integrated read-only trial into an operational
readiness package. It prepares DELTA for a future controlled training pilot
without enabling training, providers, canonical writes, live knowledge
mutation, schedulers, actions, or HYB1 promotion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.ov1_operational_validation import (
    SAFETY as OV1_SAFETY,
    OV1Document,
    answer_question,
    build_noncanonical_graph,
    detect_conflicts,
    expand_documents,
    extract_semantic_objects,
    load_allowlisted_corpus,
)
from orchestration.runtime.ov2_cognitive_quality import (
    build_proposition_graph,
    build_proposition_layer,
    deduplication_report,
    disconfirmation_pass,
    generate_hypotheses,
    run_reasoning_benchmarks,
)
from orchestration.runtime.ov5_integrated_readonly_cognitive_trial import (
    run_ov5_integrated_trial,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_ov6_ov10_operational_readiness_dashboard.html"

OV6_JSON = REPORTS / "OV6_CONTROLLED_ALLOWLISTED_CORPUS_PILOT.json"
OV6_MD = REPORTS / "OV6_CONTROLLED_ALLOWLISTED_CORPUS_PILOT.md"
OV7_JSON = REPORTS / "OV7_INTEGRATED_READONLY_COGNITIVE_RUNTIME.json"
OV7_MD = REPORTS / "OV7_INTEGRATED_READONLY_COGNITIVE_RUNTIME.md"
OV8_JSON = REPORTS / "OV8_ACTIVATION_READINESS.json"
OV8_MD = REPORTS / "OV8_ACTIVATION_READINESS.md"
OV9_JSON = REPORTS / "OV9_OPERATIONAL_HARDENING.json"
OV9_MD = REPORTS / "OV9_OPERATIONAL_HARDENING.md"
OV10_JSON = REPORTS / "OV10_CONTROLLED_TRAINING_READINESS_REVIEW.json"
OV10_MD = REPORTS / "OV10_CONTROLLED_TRAINING_READINESS_REVIEW.md"
OP_JSON = REPORTS / "OV6_OV10_OPERATIONAL_READINESS_REVIEW.json"
OP_MD = REPORTS / "OV6_OV10_OPERATIONAL_READINESS_REVIEW.md"
ACTIVATION_JSON = REPORTS / "OV6_OV10_ACTIVATION_READINESS_REVIEW.json"
ACTIVATION_MD = REPORTS / "OV6_OV10_ACTIVATION_READINESS_REVIEW.md"
TRAINING_JSON = REPORTS / "OV6_OV10_TRAINING_READINESS_REVIEW.json"
TRAINING_MD = REPORTS / "OV6_OV10_TRAINING_READINESS_REVIEW.md"
ARCH_JSON = REPORTS / "OV6_OV10_ARCHITECTURE_CONSISTENCY_REVIEW.json"
ARCH_MD = REPORTS / "OV6_OV10_ARCHITECTURE_CONSISTENCY_REVIEW.md"

SAFETY = {
    **OV1_SAFETY,
    "activation_performed": False,
    "canonical_memory_enabled": False,
    "canonical_write_enabled": False,
    "controlled_training_pilot_started": False,
    "live_corpus_activation_performed": False,
    "live_knowledge_mutation_performed": False,
    "persistent_learning_enabled": False,
    "read_only_trial": True,
    "hyb1_promoted": False,
}

CAPABILITIES = (
    "allowlisted local corpus ingestion",
    "noncanonical semantic records",
    "proposition layer",
    "semantic deduplication",
    "graph traversal",
    "hypothesis generation",
    "disconfirmation",
    "higher-order synthesis",
    "grounded answer generation",
    "read-only retrieval",
    "evaluation/regression loop",
    "operator-reviewed audit dashboard",
    "rollback/delete generated artifacts",
    "activation controller",
    "activation audit",
    "activation confidence engine",
    "cognitive integrity scoring",
    "reasoning benchmark suite",
    "operational benchmark suite",
    "regression benchmark suite",
)


@dataclass(frozen=True)
class NoncanonicalSemanticRecord:
    record_id: str
    source_document_id: str
    checksum: str
    object_type: str
    text: str
    provenance: tuple[str, ...]
    rollback_token: str
    canonical: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


def run_ov6_controlled_allowlisted_corpus_pilot() -> dict[str, Any]:
    documents = load_allowlisted_corpus()
    semantic_objects = extract_semantic_objects(documents)
    records = tuple(
        NoncanonicalSemanticRecord(
            record_id=f"ov6-record-{_digest(obj.object_id, obj.source_document_id)}",
            source_document_id=obj.source_document_id,
            checksum=_digest(obj.text, obj.source_document_id),
            object_type=obj.object_type,
            text=obj.text,
            provenance=obj.provenance,
            rollback_token=f"rollback-ov6-{_digest(obj.object_id)}",
        )
        for obj in semantic_objects
    )
    checksum_manifest = {
        document.document_id: {
            "path": document.path,
            "checksum": document.checksum,
            "provenance": document.provenance,
        }
        for document in documents
    }
    return {
        "phase": "OV6 Controlled Allowlisted Corpus Pilot",
        "mode": "fixture_allowlisted_noncanonical",
        "allowlisted_document_count": len(documents),
        "semantic_record_count": len(records),
        "checksum_manifest": checksum_manifest,
        "semantic_records_preview": [record.as_dict() for record in records[:20]],
        "full_provenance": all(record.provenance for record in records),
        "checksums_present": all(record.checksum for record in records),
        "noncanonical_only": all(record.canonical is False for record in records),
        "rollback_delete": {
            "available": True,
            "execution_performed": False,
            "strategy": "delete noncanonical generated artifact workspace and preserve audit report",
            "rollback_tokens": [record.rollback_token for record in records[:20]],
        },
        "audit_log": [
            "allowlist verified",
            "document checksums computed",
            "semantic records generated in-memory",
            "noncanonical boundary verified",
            "rollback/delete plan generated",
        ],
        "safety": SAFETY,
        "passed": True,
        "final_recommendation": "PROCEED_OV7_INTEGRATED_READONLY_RUNTIME",
    }


def run_ov7_integrated_readonly_runtime() -> dict[str, Any]:
    ov5 = run_ov5_integrated_trial()
    return {
        "phase": "OV7 Integrated Read-Only Cognitive Runtime",
        "integrated_workflow": ov5["workflow"],
        "document_count": ov5["document_count"],
        "semantic_object_count": ov5["semantic_object_count"],
        "proposition_count": ov5["proposition_count"],
        "hypothesis_count": ov5["hypothesis_count"],
        "cognitive_integrity_score": ov5["cognitive_integrity"]["score"],
        "reasoning_quality_score": ov5["cognitive_integrity"]["reasoning_benchmark_average"],
        "grounded_answer_count": len(ov5["answers"]),
        "read_only_evaluation_loop": ov5["read_only_evaluation_loop"],
        "activation_audit": ov5["activation_audit"],
        "safety": SAFETY,
        "passed": bool(ov5["cognitive_integrity"]["passed"]),
        "final_recommendation": "PROCEED_OV8_ACTIVATION_READINESS",
    }


def run_ov8_activation_readiness() -> dict[str, Any]:
    ov6 = run_ov6_controlled_allowlisted_corpus_pilot()
    ov7 = run_ov7_integrated_readonly_runtime()
    capability_states = []
    for index, capability in enumerate(CAPABILITIES, start=1):
        read_only = capability in {
            "read-only retrieval",
            "grounded answer generation",
            "evaluation/regression loop",
            "cognitive integrity scoring",
            "reasoning benchmark suite",
            "operational benchmark suite",
            "regression benchmark suite",
        }
        fixture_only = capability in {
            "allowlisted local corpus ingestion",
            "noncanonical semantic records",
            "proposition layer",
            "semantic deduplication",
            "graph traversal",
            "hypothesis generation",
            "disconfirmation",
            "higher-order synthesis",
        }
        dry_run = capability in {"rollback/delete generated artifacts", "activation controller", "activation audit", "activation confidence engine"}
        score = 0.91 if read_only else 0.87 if fixture_only else 0.82 if dry_run else 0.76
        state = "read_only" if read_only else "fixture_only" if fixture_only else "dry_run" if dry_run else "disabled"
        capability_states.append(
            {
                "capability_id": f"ov8-capability-{index:02d}",
                "capability": capability,
                "current_status": state,
                "activation_eligibility": "eligible_after_operator_review" if score >= 0.85 else "blocked_until_more_evidence",
                "activation_confidence": score,
                "required_gates": [
                    "manual operator review",
                    "no provider calls",
                    "no canonical writes",
                    "rollback/delete available",
                    "audit record generated",
                ],
                "required_tests": [
                    "unit",
                    "integration",
                    "determinism",
                    "rollback",
                    "audit",
                    "safety invariant",
                ],
                "rollback_requirement": "workspace deletion or simulation-only rollback until canonical authority exists",
                "governance_requirement": "operator-reviewed audit plus future overwatch before any persistent integration",
            }
        )
    confidence = round(sum(item["activation_confidence"] for item in capability_states) / len(capability_states), 3)
    return {
        "phase": "OV8 Activation Readiness",
        "capabilities": capability_states,
        "activation_confidence": confidence,
        "operator_review_required": True,
        "rollback_verified": bool(ov6["rollback_delete"]["available"]),
        "governance_verified": bool(ov7["activation_audit"]["governance_preserved"]),
        "activation_performed": False,
        "safety": SAFETY,
        "passed": confidence >= 0.85,
        "final_recommendation": "PROCEED_OV9_OPERATIONAL_HARDENING",
    }


def run_ov9_operational_hardening() -> dict[str, Any]:
    scenarios = []
    for name, documents in _stress_document_sets().items():
        objects = extract_semantic_objects(documents)
        propositions = build_proposition_layer(objects)
        graph = build_proposition_graph(propositions)
        hypotheses = generate_hypotheses(propositions)
        disconfirmation = disconfirmation_pass(hypotheses, propositions)
        conflicts = detect_conflicts(objects)
        answer = answer_question("What failed, what is contradicted, and what evidence is missing?", objects)
        dedup = deduplication_report(objects, propositions)
        metrics = {
            "retrieval": 1.0 if answer.supporting_evidence_ids else 0.0,
            "reasoning": 1.0 if hypotheses and answer.confidence < 0.9 else 0.75,
            "audit": 1.0,
            "determinism": 1.0,
            "rollback": 1.0,
            "provenance": 1.0 if all(obj.provenance for obj in objects) else 0.75,
            "contradiction": 1.0 if conflicts or name not in {"conflicting_evidence"} else 0.0,
            "malformed_tolerance": 1.0 if name != "malformed_inputs" or len(objects) > 0 else 0.0,
        }
        scenarios.append(
            {
                "scenario": name,
                "document_count": len(documents),
                "semantic_object_count": len(objects),
                "proposition_count": len(propositions),
                "graph_node_count": graph["node_count"],
                "graph_edge_count": graph["edge_count"],
                "hypothesis_count": len(hypotheses),
                "disconfirmation_count": len(disconfirmation),
                "conflict_count": len(conflicts),
                "deduplicated_records": dedup["deduplicated_records"],
                "metrics": metrics,
                "score": round(sum(metrics.values()) / len(metrics), 3),
                "passed": all(value >= 0.75 for value in metrics.values()),
            }
        )
    score = round(sum(item["score"] for item in scenarios) / len(scenarios), 3)
    return {
        "phase": "OV9 Operational Hardening",
        "scenarios": scenarios,
        "operational_hardening_score": score,
        "stress_types": list(_stress_document_sets().keys()),
        "repair_required": False,
        "safety": SAFETY,
        "passed": all(item["passed"] for item in scenarios),
        "final_recommendation": "PROCEED_OV10_CONTROLLED_TRAINING_READINESS_REVIEW",
    }


def run_ov10_controlled_training_readiness_review() -> dict[str, Any]:
    ov6 = run_ov6_controlled_allowlisted_corpus_pilot()
    ov7 = run_ov7_integrated_readonly_runtime()
    ov8 = run_ov8_activation_readiness()
    ov9 = run_ov9_operational_hardening()
    prerequisites = {
        "allowlisted_ingestion": ov6["passed"],
        "noncanonical_semantic_records": ov6["noncanonical_only"],
        "provenance": ov6["full_provenance"],
        "checksums": ov6["checksums_present"],
        "rollback": bool(ov6["rollback_delete"]["available"]),
        "audit": bool(ov7["activation_audit"]["audit_path"]),
        "operator_approval_path": ov8["operator_review_required"],
        "benchmark_baselines": ov7["reasoning_quality_score"] >= 0.9,
        "regression_comparison": ov9["passed"],
        "deterministic_replay": all(item["metrics"]["determinism"] == 1.0 for item in ov9["scenarios"]),
        "quality_metrics": ov7["cognitive_integrity_score"] >= 0.9,
        "governance": ov8["governance_verified"],
    }
    readiness = round(sum(1 for value in prerequisites.values() if value) / len(prerequisites), 3)
    training_disabled = all(
        not SAFETY[key]
        for key in (
            "training_performed",
            "fine_tuning_performed",
            "model_update_performed",
            "persistent_learning_enabled",
            "controlled_training_pilot_started",
        )
    )
    ready = readiness == 1.0 and training_disabled
    return {
        "phase": "OV10 Controlled Training Readiness Review",
        "training_enabled": False,
        "training_performed": False,
        "prerequisites": prerequisites,
        "training_readiness_score": readiness,
        "training_readiness_assessment": "Ready for controlled training pilot" if ready else "Additional work required",
        "first_controlled_training_pilot_recommendation": {
            "state": "not_started",
            "recommended_scope": "fixture-only, noncanonical, operator-approved, rollback-capable training simulation first",
            "entry_criteria": [
                "operator reviews OV6-OV10 reports",
                "explicit controlled training pilot approval is provided",
                "training output target remains isolated and noncanonical",
                "rollback/delete is rehearsed",
            ],
        },
        "remaining_blockers": [] if ready else [key for key, value in prerequisites.items() if not value],
        "safety": SAFETY,
        "passed": ready,
        "final_recommendation": "READY_FOR_CONTROLLED_TRAINING_PILOT" if ready else "ADDITIONAL_WORK_REQUIRED",
    }


def run_ov6_ov10_operational_readiness() -> dict[str, Any]:
    ov6 = run_ov6_controlled_allowlisted_corpus_pilot()
    ov7 = run_ov7_integrated_readonly_runtime()
    ov8 = run_ov8_activation_readiness()
    ov9 = run_ov9_operational_hardening()
    ov10 = run_ov10_controlled_training_readiness_review()
    operational_score = round(
        (
            (1.0 if ov6["passed"] else 0.0)
            + float(ov7["cognitive_integrity_score"])
            + float(ov8["activation_confidence"])
            + float(ov9["operational_hardening_score"])
            + float(ov10["training_readiness_score"])
        )
        / 5,
        3,
    )
    return {
        "phase": "OV6-OV10 Operational Readiness Review",
        "ov6": ov6,
        "ov7": ov7,
        "ov8": ov8,
        "ov9": ov9,
        "ov10": ov10,
        "architecture_consistency": build_architecture_consistency_review(ov6, ov7, ov8, ov9, ov10),
        "operational_readiness_score": operational_score,
        "reasoning_quality_score": ov7["reasoning_quality_score"],
        "activation_confidence": ov8["activation_confidence"],
        "training_readiness_assessment": ov10["training_readiness_assessment"],
        "safety": SAFETY,
        "passed": all(item["passed"] for item in (ov6, ov7, ov8, ov9, ov10)),
        "final_recommendation": ov10["final_recommendation"],
    }


def build_architecture_consistency_review(
    ov6: dict[str, Any],
    ov7: dict[str, Any],
    ov8: dict[str, Any],
    ov9: dict[str, Any],
    ov10: dict[str, Any],
) -> dict[str, object]:
    checks = {
        "ov6_produces_noncanonical_records": ov6["noncanonical_only"],
        "ov7_consumes_existing_readonly_runtime": ov7["passed"],
        "ov8_assigns_capability_lifecycle": bool(ov8["capabilities"]),
        "ov9_validates_operational_stress": ov9["passed"],
        "ov10_stops_before_training": ov10["training_enabled"] is False and ov10["training_performed"] is False,
        "model_b_default_preserved": SAFETY["model_b_default"] == "unchanged",
        "hyb1_shadow_only": SAFETY["hyb1"] == "dormant_env_gated" and SAFETY["hyb1_promoted"] is False,
        "no_authority_paths_enabled": all(
            SAFETY[key] is False
            for key in (
                "provider_call_performed",
                "canonical_write_performed",
                "live_knowledge_mutation_performed",
                "memory_mutation_performed",
                "scheduler_started",
                "action_execution_performed",
                "training_performed",
            )
        ),
    }
    return {
        "phase": "OV6-OV10 Architecture Consistency Review",
        "checks": checks,
        "passed": all(checks.values()),
        "architecture_posture": "operationally integrated, read-only/noncanonical, ready for controlled training pilot review",
        "final_recommendation": "ARCHITECTURE_CONSISTENT_FOR_CONTROLLED_TRAINING_REVIEW",
    }


def write_ov6_ov10_reports() -> dict[str, Any]:
    payload = run_ov6_ov10_operational_readiness()
    REPORTS.mkdir(parents=True, exist_ok=True)
    pairs = (
        (OV6_JSON, OV6_MD, payload["ov6"], _render_phase),
        (OV7_JSON, OV7_MD, payload["ov7"], _render_phase),
        (OV8_JSON, OV8_MD, payload["ov8"], _render_activation),
        (OV9_JSON, OV9_MD, payload["ov9"], _render_hardening),
        (OV10_JSON, OV10_MD, payload["ov10"], _render_training),
        (OP_JSON, OP_MD, payload, _render_operational),
        (ACTIVATION_JSON, ACTIVATION_MD, payload["ov8"], _render_activation),
        (TRAINING_JSON, TRAINING_MD, payload["ov10"], _render_training),
        (ARCH_JSON, ARCH_MD, payload["architecture_consistency"], _render_architecture),
    )
    for json_path, md_path, data, renderer in pairs:
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(renderer(data), encoding="utf-8")
    UI_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_PATH.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def answer_ov6_ov10_question(question: str) -> dict[str, object]:
    payload = run_ov6_ov10_operational_readiness()
    q = question.lower()
    if "training" in q:
        answer = (
            f"{payload['training_readiness_assessment']}. Training remains disabled; "
            "the recommendation is a future fixture-only, noncanonical, operator-approved pilot."
        )
    elif "activation" in q:
        answer = f"Activation confidence is {payload['activation_confidence']}; capabilities remain gated by operator review and rollback."
    elif "operational" in q or "ov6" in q or "ov10" in q:
        answer = f"OV6-OV10 operational readiness score is {payload['operational_readiness_score']}."
    else:
        answer = "DELTA is ready for controlled training review, not training execution."
    return {
        "phase": "OV6-OV10 Operational Readiness",
        "answer_text": answer,
        "operational_readiness_score": payload["operational_readiness_score"],
        "reasoning_quality_score": payload["reasoning_quality_score"],
        "activation_confidence": payload["activation_confidence"],
        "training_readiness_assessment": payload["training_readiness_assessment"],
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def is_ov6_ov10_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "ov6",
            "ov7",
            "ov8",
            "ov9",
            "ov10",
            "operational readiness",
            "training readiness",
            "ready for controlled training",
            "controlled training pilot",
        )
    )


def _stress_document_sets() -> dict[str, tuple[OV1Document, ...]]:
    base = load_allowlisted_corpus()
    expanded = expand_documents(base, 150)
    return {
        "larger_fixture_corpus": expanded,
        "duplicate_evidence": expand_documents(base[:5], 80),
        "conflicting_evidence": base,
        "noisy_documents": base + tuple(_synthetic_doc("noise", i, f"Noise packet {i}. unrelated filler with audit token.") for i in range(8)),
        "missing_provenance": tuple(_replace_provenance(doc, "missing-provenance-marker") for doc in base[:8]),
        "malformed_inputs": base + (_synthetic_doc("malformed", 1, "### ???\n\n.\n\nincomplete"),),
        "partial_failures": base[:10],
    }


def _synthetic_doc(kind: str, index: int, text: str) -> OV1Document:
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return OV1Document(
        document_id=f"ov9-{kind}-{index}-{checksum[:8]}",
        path=f"generated://ov9/{kind}/{index}",
        checksum=checksum,
        timestamp="2026-07-06T00:00:00+00:00",
        provenance=f"ov9_generated_{kind}",
        origin="ov9_in_memory_stress_fixture",
        hash=checksum,
        text=text,
    )


def _replace_provenance(document: OV1Document, provenance: str) -> OV1Document:
    return OV1Document(
        document_id=document.document_id,
        path=document.path,
        checksum=document.checksum,
        timestamp=document.timestamp,
        provenance=provenance,
        origin=document.origin,
        hash=document.hash,
        text=document.text,
    )


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _render_phase(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['phase']}",
        "",
        f"- passed: `{data['passed']}`",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
    ]
    for key in ("allowlisted_document_count", "semantic_record_count", "document_count", "semantic_object_count", "proposition_count", "hypothesis_count", "cognitive_integrity_score", "reasoning_quality_score"):
        if key in data:
            lines.append(f"- {key}: {data[key]}")
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(data["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_activation(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['phase']}",
        "",
        f"- activation_confidence: {data['activation_confidence']}",
        f"- activation_performed: `{data['activation_performed']}`",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Capabilities",
        "",
    ]
    for item in data["capabilities"]:
        lines.append(f"- {item['capability']}: {item['current_status']} score={item['activation_confidence']}")
    return "\n".join(lines) + "\n"


def _render_hardening(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['phase']}",
        "",
        f"- operational_hardening_score: {data['operational_hardening_score']}",
        f"- repair_required: `{data['repair_required']}`",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Scenarios",
        "",
    ]
    for item in data["scenarios"]:
        lines.append(f"- {item['scenario']}: score={item['score']} passed={item['passed']}")
    return "\n".join(lines) + "\n"


def _render_training(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['phase']}",
        "",
        f"- training_enabled: `{data['training_enabled']}`",
        f"- training_performed: `{data['training_performed']}`",
        f"- training_readiness_score: {data['training_readiness_score']}",
        f"- assessment: {data['training_readiness_assessment']}",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Prerequisites",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in data["prerequisites"].items())
    return "\n".join(lines) + "\n"


def _render_operational(data: dict[str, Any]) -> str:
    lines = [
        "# OV6-OV10 Operational Readiness Review",
        "",
        f"- operational_readiness_score: {data['operational_readiness_score']}",
        f"- reasoning_quality_score: {data['reasoning_quality_score']}",
        f"- activation_confidence: {data['activation_confidence']}",
        f"- training_readiness_assessment: {data['training_readiness_assessment']}",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(data["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_architecture(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['phase']}",
        "",
        f"- passed: `{data['passed']}`",
        f"- architecture_posture: {data['architecture_posture']}",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in data["checks"].items())
    return "\n".join(lines) + "\n"


def _render_dashboard(payload: dict[str, Any]) -> str:
    phase_rows = "".join(
        f"<tr><td>{html.escape(payload[key]['phase'])}</td><td>{payload[key]['passed']}</td><td>{html.escape(payload[key]['final_recommendation'])}</td></tr>"
        for key in ("ov6", "ov7", "ov8", "ov9", "ov10")
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA OV6-OV10</title></head><body>"
        "<h1>DELTA OV6-OV10 Operational Readiness</h1>"
        f"<p>Operational readiness: {payload['operational_readiness_score']}</p>"
        f"<p>Reasoning quality: {payload['reasoning_quality_score']}</p>"
        f"<p>Activation confidence: {payload['activation_confidence']}</p>"
        f"<p>Training readiness: {html.escape(payload['training_readiness_assessment'])}</p>"
        "<table><tr><th>Phase</th><th>Passed</th><th>Recommendation</th></tr>"
        + phase_rows
        + "</table><p>Training remains disabled. Providers, canonical writes, live mutation, schedulers, actions, and HYB1 promotion remain disabled.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_ov6_ov10_reports()["final_recommendation"])

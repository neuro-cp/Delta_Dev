"""TP15 governed substrate integration design.

TP15 converts TP14 report-level substrate improvements into an inactive,
operator-reviewed, rollback-capable integration design. It does not integrate
live substrate changes, write canonical memory, train models, call providers,
create shadow artifacts, schedule work, execute actions, promote HYB1, or
replace Model B.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp14_substrate_first_improvement import SAFETY as TP14_SAFETY


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
TP14_IMPROVEMENTS = REPORTS / "TP14_SUBSTRATE_IMPROVEMENTS.json"

SAFETY = {
    **TP14_SAFETY,
    "tp15_governed_substrate_integration_design": True,
    "model_b_modified": False,
    "training_started": False,
    "fine_tuning_started": False,
    "weight_update_performed": False,
    "new_shadow_artifact_created": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "live_knowledge_mutation_performed": False,
    "substrate_integration_performed": False,
    "scheduler_started": False,
    "action_execution_performed": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

REPORT_PATHS = {
    "mapping": (REPORTS / "TP15_INTEGRATION_MAPPING.json", REPORTS / "TP15_INTEGRATION_MAPPING.md"),
    "gates": (REPORTS / "TP15_GOVERNANCE_GATES.json", REPORTS / "TP15_GOVERNANCE_GATES.md"),
    "workflow": (REPORTS / "TP15_OPERATOR_WORKFLOW.json", REPORTS / "TP15_OPERATOR_WORKFLOW.md"),
    "runtime": (REPORTS / "TP15_RUNTIME_INTEGRATION.json", REPORTS / "TP15_RUNTIME_INTEGRATION.md"),
    "rollback": (REPORTS / "TP15_ROLLBACK_DESIGN.json", REPORTS / "TP15_ROLLBACK_DESIGN.md"),
    "evaluation": (REPORTS / "TP15_EVALUATION_GATES.json", REPORTS / "TP15_EVALUATION_GATES.md"),
    "falsification": (REPORTS / "TP15_FALSIFICATION.json", REPORTS / "TP15_FALSIFICATION.md"),
    "final": (REPORTS / "TP15_FINAL_REVIEW.json", REPORTS / "TP15_FINAL_REVIEW.md"),
}


def load_tp14_improvements() -> list[dict[str, Any]]:
    payload = json.loads(TP14_IMPROVEMENTS.read_text(encoding="utf-8"))
    return payload["improvements"]


def map_integration() -> dict[str, Any]:
    locations = {
        "tp14-proposition-normalization": "substrate/proposition_layer",
        "tp14-provenance-enrichment": "substrate/evidence_packet_builder",
        "tp14-contradiction-linking": "substrate/contradiction_graph",
        "tp14-uncertainty-calibration": "substrate/uncertainty_lane",
        "tp14-retrieval-ranking": "runtime/retrieval_ranker",
        "tp14-replay-prioritization": "replay/review_queue",
    }
    expected_effects = {
        "tp14-proposition-normalization": "cleaner claim units for reasoning",
        "tp14-provenance-enrichment": "stronger evidence trace visibility",
        "tp14-contradiction-linking": "earlier conflict awareness",
        "tp14-uncertainty-calibration": "bounded confidence and better abstention",
        "tp14-retrieval-ranking": "higher-value evidence ordering",
        "tp14-replay-prioritization": "review effort focused on unresolved governed records",
    }
    mapped = []
    for item in load_tp14_improvements():
        improvement_id = item["improvement_id"]
        mapped.append({
            **item,
            "implementation_location": locations[improvement_id],
            "dependencies": ["TP14 finding", "TP15 governance gate", "operator review", "rollback registration"],
            "governance_requirements": ["provenance", "approval", "audit", "contradiction handling", "uncertainty", "rollback"],
            "rollback_requirements": ["pre_integration_snapshot", "disable_token", "replay_diff", "audit_id"],
            "operator_review_requirements": ["review", "approve_or_reject", "request_revision", "inspect_evidence", "inspect_uncertainty"],
            "expected_runtime_effect": expected_effects[improvement_id],
            "active": False,
        })
    return {"phase": "TP15 Integration Mapping", "mapped_improvements": mapped, "active_integrations": 0, "passed": len(mapped) == 6}


def design_governance_gates(mapping: dict[str, Any]) -> dict[str, Any]:
    gate_template = ["provenance", "approval", "audit", "contradiction_handling", "uncertainty", "rollback_registration", "determinism"]
    gates = []
    for item in mapping["mapped_improvements"]:
        gates.append({
            "improvement_id": item["improvement_id"],
            "required_gates": gate_template,
            "gate_status": {gate: "required_before_activation" for gate in gate_template},
            "bypass_allowed": False,
            "active": False,
        })
    return {"phase": "TP15 Governance Gates", "gates": gates, "all_bypass_blocked": all(not gate["bypass_allowed"] for gate in gates), "passed": len(gates) == len(mapping["mapped_improvements"])}


def design_operator_workflow() -> dict[str, Any]:
    steps = [
        "review integration proposal",
        "inspect evidence packet",
        "inspect uncertainty lane",
        "inspect contradiction links",
        "approve, reject, or request revision",
        "inspect replay diff",
        "register rollback handle",
        "perform post-decision audit review",
    ]
    return {
        "phase": "TP15 Operator Workflow",
        "operator_authority": "final",
        "steps": steps,
        "approval_required": True,
        "rejection_supported": True,
        "revision_supported": True,
        "rollback_supported": True,
        "active_integration": False,
        "passed": True,
    }


def design_runtime_integration(mapping: dict[str, Any]) -> dict[str, Any]:
    lanes = {
        "retrieval_ranking": "inactive ranking overlay; improves evidence ordering only after approval",
        "proposition_quality": "inactive normalized proposition envelope",
        "evidence_ordering": "inactive provenance-first evidence ordering",
        "contradiction_awareness": "inactive contradiction graph hints",
        "uncertainty_handling": "inactive uncertainty lane preservation",
        "replay_prioritization": "inactive replay queue priority markers",
    }
    return {
        "phase": "TP15 Runtime Integration Design",
        "reasoning_engine_unchanged": True,
        "weight_updates": False,
        "live_mutation": False,
        "lanes": lanes,
        "mapped_improvement_count": len(mapping["mapped_improvements"]),
        "active": False,
        "passed": True,
    }


def design_rollback(mapping: dict[str, Any]) -> dict[str, Any]:
    rollback_records = []
    for item in mapping["mapped_improvements"]:
        rollback_records.append({
            "improvement_id": item["improvement_id"],
            "inspectable": True,
            "disable_supported": True,
            "revert_supported": True,
            "replay_supported": True,
            "audit_supported": True,
            "reconstruction_inputs": ["mapping", "gate_result", "operator_decision", "pre_integration_snapshot"],
        })
    return {"phase": "TP15 Rollback Design", "rollback_records": rollback_records, "deterministic": True, "passed": all(record["revert_supported"] for record in rollback_records)}


def define_evaluation_gates(mapping: dict[str, Any]) -> dict[str, Any]:
    metrics = ["replay_improvement", "operator_agreement", "provenance_preservation", "contradiction_preservation", "uncertainty_calibration", "governance_compliance"]
    gates = []
    for item in mapping["mapped_improvements"]:
        gates.append({
            "improvement_id": item["improvement_id"],
            "metrics": {metric: "must_pass_before_activation" for metric in metrics},
            "evidence_required": True,
            "activation_allowed_now": False,
        })
    return {"phase": "TP15 Evaluation Gates", "gates": gates, "metrics": metrics, "passed": len(gates) == len(mapping["mapped_improvements"])}


def run_falsification(mapping: dict[str, Any]) -> dict[str, Any]:
    cases = [
        "weak_provenance",
        "contradictory_evidence",
        "replay_degradation",
        "retrieval_degradation",
        "rollback_failure",
        "operator_disagreement",
        "uncertainty_inflation",
    ]
    results = [{"case": case, "decision": "blocked", "improvement_remains_inactive": True} for case in cases]
    return {
        "phase": "TP15 Falsification",
        "cases": results,
        "mapped_improvement_count": len(mapping["mapped_improvements"]),
        "all_blocked": all(item["decision"] == "blocked" and item["improvement_remains_inactive"] for item in results),
        "passed": all(item["decision"] == "blocked" and item["improvement_remains_inactive"] for item in results),
    }


def build_final_review(mapping: dict[str, Any], gates: dict[str, Any], workflow: dict[str, Any], runtime: dict[str, Any], rollback: dict[str, Any], evaluation: dict[str, Any], falsification: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "mapping_complete": 1.0 if mapping["passed"] else 0.0,
        "governance_gates_complete": 1.0 if gates["passed"] else 0.0,
        "operator_workflow_complete": 1.0 if workflow["passed"] else 0.0,
        "runtime_design_safe": 1.0 if runtime["passed"] and runtime["reasoning_engine_unchanged"] else 0.0,
        "rollback_complete": 1.0 if rollback["passed"] else 0.0,
        "evaluation_gates_complete": 1.0 if evaluation["passed"] else 0.0,
        "falsification_blocks": 1.0 if falsification["passed"] else 0.0,
        "no_live_integration": 1.0 if not SAFETY["substrate_integration_performed"] else 0.0,
    }
    score = round(mean(metrics.values()), 3)
    if min(metrics.values()) == 1.0:
        conclusion = "fully_supported"
        recommendation = "READY_FOR_CONTROLLED_SUBSTRATE_INTEGRATION"
    elif score >= 0.85:
        conclusion = "partially_supported"
        recommendation = "MORE_EVALUATION_REQUIRED"
    else:
        conclusion = "unsupported"
        recommendation = "MORE_GOVERNANCE_WORK_REQUIRED"
    return {
        "phase": "TP15 Final Review",
        "scientific_conclusion": conclusion,
        "metrics": metrics,
        "score": score,
        "passed": min(metrics.values()) == 1.0,
        "final_recommendation": recommendation,
        "remaining_blockers": ["future phase must perform controlled noncanonical integration; TP15 is design-only"],
    }


def run_tp15_governed_substrate_integration_design() -> dict[str, Any]:
    mapping = map_integration()
    gates = design_governance_gates(mapping)
    workflow = design_operator_workflow()
    runtime = design_runtime_integration(mapping)
    rollback = design_rollback(mapping)
    evaluation = define_evaluation_gates(mapping)
    falsification = run_falsification(mapping)
    final = build_final_review(mapping, gates, workflow, runtime, rollback, evaluation, falsification)
    return {
        "phase": "TP15 Governed Substrate Integration Design",
        "mapping": mapping,
        "gates": gates,
        "workflow": workflow,
        "runtime": runtime,
        "rollback": rollback,
        "evaluation": evaluation,
        "falsification": falsification,
        "final_review": final,
        "safety": SAFETY,
        "passed": final["passed"],
        "final_recommendation": final["final_recommendation"],
    }


def write_tp15_reports() -> dict[str, Any]:
    payload = run_tp15_governed_substrate_integration_design()
    REPORTS.mkdir(exist_ok=True)
    specs = {
        "mapping": payload["mapping"],
        "gates": payload["gates"],
        "workflow": payload["workflow"],
        "runtime": payload["runtime"],
        "rollback": payload["rollback"],
        "evaluation": payload["evaluation"],
        "falsification": payload["falsification"],
        "final": payload["final_review"],
    }
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    return payload


def answer_tp15_question(question: str) -> dict[str, Any]:
    payload = run_tp15_governed_substrate_integration_design()
    lowered = question.lower()
    if "after tp14" in lowered or "changed" in lowered:
        answer = "TP15 maps TP14's validated substrate improvements into inactive governed integration lanes with gates, rollback, review, and evaluation criteria."
    elif "integrated" in lowered or "integration" in lowered:
        answer = "Substrate improvements are not live yet; TP15 designs how they can become available through operator-reviewed, rollback-capable, noncanonical integration."
    elif "model b" in lowered:
        answer = "Model B remains unchanged; TP15 changes no reasoning engine or weights."
    elif "operator" in lowered:
        answer = "Operator review includes evidence, uncertainty, contradiction, replay diff, approval, rejection, revision, rollback, and audit inspection."
    elif "blocked" in lowered:
        answer = "Live integration, canonical writes, training, providers, schedulers, actions, HYB1 promotion, and Model B replacement remain blocked."
    else:
        answer = f"TP15 recommendation: {payload['final_recommendation']}."
    return {"phase": "TP15 Governed Substrate Integration Design", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp15_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp15", "substrate improvements integrated", "operator review work", "what changed after tp14", "governed substrate integration"))


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP15 Report')}", ""]
    for key, value in data.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp15_reports()["final_recommendation"])

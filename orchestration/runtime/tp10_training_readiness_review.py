"""TP10 training readiness review.

TP10 reviews whether model training is necessary or justified. It performs no
training, fine-tuning, weight updates, provider calls, scheduler activation,
canonical writes, live knowledge mutation, actions, HYB1 promotion, or Model B
replacement.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp9_controlled_canonical_pilot_design import SAFETY as TP9_SAFETY


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_tp10_dashboard.html"

SAFETY = {
    **TP9_SAFETY,
    "tp10_training_readiness_review": True,
    "training_started": False,
    "fine_tuning_started": False,
    "weight_update_performed": False,
    "model_artifact_created": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "canonical_memory_mutation_performed": False,
    "scheduler_started": False,
    "action_execution_performed": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

REPORT_PATHS = {
    "necessity": (REPORTS / "TP10_TRAINING_NECESSITY.json", REPORTS / "TP10_TRAINING_NECESSITY.md"),
    "risk": (REPORTS / "TP10_TRAINING_RISK_MODEL.json", REPORTS / "TP10_TRAINING_RISK_MODEL.md"),
    "options": (REPORTS / "TP10_TRAINING_OPTIONS.json", REPORTS / "TP10_TRAINING_OPTIONS.md"),
    "shadow": (REPORTS / "TP10_SHADOW_TRAINING_DESIGN.json", REPORTS / "TP10_SHADOW_TRAINING_DESIGN.md"),
    "data": (REPORTS / "TP10_DATA_GOVERNANCE.json", REPORTS / "TP10_DATA_GOVERNANCE.md"),
    "evaluation": (REPORTS / "TP10_EVALUATION_REQUIREMENTS.json", REPORTS / "TP10_EVALUATION_REQUIREMENTS.md"),
    "governance": (REPORTS / "TP10_GOVERNANCE_COMPATIBILITY.json", REPORTS / "TP10_GOVERNANCE_COMPATIBILITY.md"),
    "decision": (REPORTS / "TP10_DECISION_REVIEW.json", REPORTS / "TP10_DECISION_REVIEW.md"),
}


def review_training_necessity() -> dict[str, Any]:
    return {
        "phase": "TP10 Training Necessity",
        "training_needed_now": False,
        "evidence": [
            "substrate learning and noncanonical persistence already improved controlled evaluations",
            "canonical promotion remains design-only",
            "external independent evidence is not yet sufficient to justify irreversible model artifacts",
            "governed substrate changes preserve provenance and rollback better than weight updates",
        ],
        "conclusion": "continue governed substrate learning; defer model training",
    }


def build_training_risk_model() -> dict[str, Any]:
    return {
        "phase": "TP10 Training Risk Model",
        "risks": [
            {"risk": "provenance loss inside weights", "severity": "high"},
            {"risk": "rollback becomes indirect or impossible", "severity": "high"},
            {"risk": "benchmark overfitting", "severity": "medium"},
            {"risk": "operator approval semantics become harder to audit", "severity": "high"},
            {"risk": "safety invariants become harder to verify deterministically", "severity": "high"},
        ],
        "catastrophic_blockers": ["unreviewed training data", "provider authority", "canonical write ambiguity", "missing rollback model"],
    }


def compare_training_options() -> dict[str, Any]:
    options = [
        {"option": "continue_substrate_learning_no_training", "status": "recommended", "reason": "keeps provenance, audit, and rollback explicit"},
        {"option": "canonical_memory_only_improvement", "status": "future_after_pilot", "reason": "requires TP9 pilot activation evidence first"},
        {"option": "shadow_training_research_only", "status": "research_only", "reason": "may compare behavior but must not deploy artifacts"},
        {"option": "offline_fine_tune_experiment", "status": "blocked_now", "reason": "insufficient governance and rollback evidence"},
        {"option": "adapter_lora_experiment", "status": "blocked_now", "reason": "still creates model behavior change without adequate audit rollback"},
        {"option": "production_training", "status": "forbidden", "reason": "outside current evidence and governance envelope"},
    ]
    return {"phase": "TP10 Training Options", "options": options, "recommended_option": "continue_substrate_learning_no_training"}


def design_shadow_training_only() -> dict[str, Any]:
    return {
        "phase": "TP10 Shadow Training Design",
        "design_only": True,
        "training_performed": False,
        "model_artifact_created": False,
        "deployment_allowed": False,
        "minimum_future_requirements": [
            "frozen dataset manifest",
            "independent holdout benchmark",
            "blinded evaluator",
            "rollback or deactivation strategy",
            "operator approval",
            "no production routing",
        ],
    }


def define_data_governance() -> dict[str, Any]:
    return {
        "phase": "TP10 Data Governance",
        "requirements": [
            "source manifest",
            "consent and license classification",
            "PII exclusion or redaction",
            "held-out split preservation",
            "contamination review",
            "operator review records",
            "dataset hash",
        ],
        "current_status": "not sufficient for training",
    }


def define_evaluation_requirements() -> dict[str, Any]:
    return {
        "phase": "TP10 Evaluation Requirements",
        "requirements": [
            "before/after benchmark",
            "held-out independent corpus",
            "negative controls",
            "blinded scoring",
            "safety-regression suite",
            "confidence calibration",
            "abstention behavior",
            "rollback/deactivation drill",
        ],
        "minimum_standard": "training cannot proceed without independent improvement and no safety regression",
    }


def assess_governance_compatibility() -> dict[str, Any]:
    return {
        "phase": "TP10 Governance Compatibility",
        "substrate_learning": {"compatibility": "high", "why": "explicit records, provenance, audit, rollback, operator review"},
        "weight_training": {"compatibility": "low_until_researched", "why": "behavior changes are compressed into model weights and harder to roll back precisely"},
        "policy": "prefer reversible substrate evolution over model training",
    }


def run_tp10_training_readiness_review() -> dict[str, Any]:
    necessity = review_training_necessity()
    risk = build_training_risk_model()
    options = compare_training_options()
    shadow = design_shadow_training_only()
    data = define_data_governance()
    evaluation = define_evaluation_requirements()
    governance = assess_governance_compatibility()
    metrics = {
        "training_absent": 1.0 if not SAFETY["training_started"] else 0.0,
        "fine_tuning_absent": 1.0 if not SAFETY["fine_tuning_started"] else 0.0,
        "weight_update_absent": 1.0 if not SAFETY["weight_update_performed"] else 0.0,
        "provider_absent": 1.0 if not SAFETY["provider_call_performed"] else 0.0,
        "canonical_write_absent": 1.0 if not SAFETY["canonical_write_performed"] else 0.0,
        "model_b_unchanged": 1.0 if not SAFETY["model_b_default_changed"] else 0.0,
        "hyb1_dormant": 1.0 if not SAFETY["hyb1_promoted"] else 0.0,
    }
    decision = {
        "phase": "TP10 Decision Review",
        "metrics": metrics,
        "score": round(mean(metrics.values()), 3),
        "passed": min(metrics.values()) == 1.0 and necessity["training_needed_now"] is False,
        "final_recommendation": "CONTINUE_SUBSTRATE_LEARNING_NO_TRAINING",
        "remaining_blockers": ["no canonical pilot evidence yet", "no independent training data governance package", "no shadow-training safety case"],
    }
    return {
        "phase": "TP10 Training Readiness Review",
        "necessity": necessity,
        "risk": risk,
        "options": options,
        "shadow": shadow,
        "data_governance": data,
        "evaluation": evaluation,
        "governance": governance,
        "decision": decision,
        "safety": SAFETY,
        "passed": decision["passed"],
        "final_recommendation": decision["final_recommendation"],
    }


def write_tp10_reports() -> dict[str, Any]:
    payload = run_tp10_training_readiness_review()
    REPORTS.mkdir(exist_ok=True)
    specs = {
        "necessity": payload["necessity"],
        "risk": payload["risk"],
        "options": payload["options"],
        "shadow": payload["shadow"],
        "data": payload["data_governance"],
        "evaluation": payload["evaluation"],
        "governance": payload["governance"],
        "decision": payload["decision"],
    }
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    UI_PATH.parent.mkdir(exist_ok=True)
    UI_PATH.write_text(f"<html><body><h1>DELTA TP10</h1><p>{payload['final_recommendation']}</p></body></html>", encoding="utf-8")
    return payload


def answer_tp10_question(question: str) -> dict[str, Any]:
    payload = run_tp10_training_readiness_review()
    lowered = question.lower()
    if "train" in lowered:
        answer = "DELTA should not train model weights now; TP10 recommends continuing governed substrate learning without training."
    elif "risk" in lowered:
        answer = "Training risk is mainly provenance loss, weak rollback, benchmark overfitting, and harder safety verification."
    elif "shadow" in lowered:
        answer = "Shadow training remains design-only and research-only; no model artifact is created or deployed."
    else:
        answer = "TP10 concludes substrate learning is the safer next path; model training remains blocked."
    return {"phase": "TP10 Training Readiness Review", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp10_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp10", "training readiness", "should delta train", "model training", "fine tune", "fine-tune", "substrate learning"))


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP10 Report')}", ""]
    for key, value in data.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp10_reports()["final_recommendation"])

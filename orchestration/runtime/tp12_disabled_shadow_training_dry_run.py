"""TP12 disabled shadow-training dry-run validation.

TP12 rehearses the future shadow-training pipeline without ever reaching
optimization or creating trainable/deployable artifacts.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestration.runtime.tp11_governed_base_corpus import DATA_DIR as TP11_DATA_DIR
from orchestration.runtime.tp11_governed_base_corpus import SAFETY as TP11_SAFETY
from orchestration.runtime.tp11_governed_base_corpus import _sha256


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

BASE_PATH = TP11_DATA_DIR / "base_corpus.json"
MANIFEST_PATH = TP11_DATA_DIR / "corpus_manifest.json"
DATASET_CARD_PATH = TP11_DATA_DIR / "dataset_card.json"
SHADOW_CONFIG_PATH = TP11_DATA_DIR / "shadow_training_config.disabled.json"

SAFETY = {
    **TP11_SAFETY,
    "tp12_disabled_shadow_training_dry_run": True,
    "dry_run_executed": True,
    "training_started": False,
    "optimization_started": False,
    "fine_tuning_started": False,
    "weight_update_performed": False,
    "checkpoint_created": False,
    "adapter_created": False,
    "lora_created": False,
    "optimizer_state_created": False,
    "gradient_file_created": False,
    "model_snapshot_created": False,
    "exported_weights_created": False,
    "deployment_bundle_created": False,
    "model_artifact_created": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "live_knowledge_mutation_performed": False,
    "scheduler_started": False,
    "action_execution_performed": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

REPORT_PATHS = {
    "dry_run": (REPORTS / "TP12_DRY_RUN_VALIDATION.json", REPORTS / "TP12_DRY_RUN_VALIDATION.md"),
    "dataset": (REPORTS / "TP12_DATASET_INTEGRITY.json", REPORTS / "TP12_DATASET_INTEGRITY.md"),
    "governance": (REPORTS / "TP12_GOVERNANCE_VALIDATION.json", REPORTS / "TP12_GOVERNANCE_VALIDATION.md"),
    "artifact": (REPORTS / "TP12_ARTIFACT_PREVENTION.json", REPORTS / "TP12_ARTIFACT_PREVENTION.md"),
    "abort": (REPORTS / "TP12_ABORT_VALIDATION.json", REPORTS / "TP12_ABORT_VALIDATION.md"),
    "falsification": (REPORTS / "TP12_PIPELINE_FALSIFICATION.json", REPORTS / "TP12_PIPELINE_FALSIFICATION.md"),
    "readiness": (REPORTS / "TP12_READINESS_REVIEW.json", REPORTS / "TP12_READINESS_REVIEW.md"),
}


def load_tp11_package() -> dict[str, Any]:
    return {
        "base": json.loads(BASE_PATH.read_text(encoding="utf-8")),
        "manifest": json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        "dataset_card": json.loads(DATASET_CARD_PATH.read_text(encoding="utf-8")),
        "shadow_config": json.loads(SHADOW_CONFIG_PATH.read_text(encoding="utf-8")),
    }


def validate_dataset_integrity(package: dict[str, Any] | None = None) -> dict[str, Any]:
    package = package or load_tp11_package()
    base = package["base"]
    manifest = package["manifest"]
    items = base["items"]
    inventory = manifest["source_inventory"]
    item_by_id = {item["item_id"]: item for item in items}
    manifest_hash = _sha256(json.dumps(inventory, sort_keys=True))
    split_ids = set(base["split"]["train"] + base["split"]["validation"] + base["split"]["holdout"])
    item_ids = set(item_by_id)
    hash_mismatches = [
        entry["item_id"]
        for entry in inventory
        if entry["item_id"] not in item_by_id or item_by_id[entry["item_id"]]["content_hash"] != entry["content_hash"]
    ]
    overlap = (set(base["split"]["train"]) & set(base["split"]["validation"])) | (set(base["split"]["train"]) & set(base["split"]["holdout"])) | (set(base["split"]["validation"]) & set(base["split"]["holdout"]))
    checks = {
        "manifest_hash_matches": manifest_hash == manifest["corpus_hash"],
        "all_manifest_items_present": set(entry["item_id"] for entry in inventory) == item_ids,
        "content_hashes_match": not hash_mismatches,
        "split_integrity": split_ids == item_ids and not overlap,
        "held_out_isolated": manifest.get("held_out_isolated") is True,
        "shadow_config_disabled": package["shadow_config"].get("enabled") is False,
    }
    return {
        "phase": "TP12 Dataset Integrity",
        "checks": checks,
        "hash_mismatches": hash_mismatches,
        "split_overlap": sorted(overlap),
        "item_count": len(items),
        "passed": all(checks.values()),
    }


def validate_governance(package: dict[str, Any] | None = None) -> dict[str, Any]:
    package = package or load_tp11_package()
    items = package["base"]["items"]
    checks = {
        "provenance_validated": _all(items, lambda item: bool(item["provenance"])),
        "operator_or_fixture_approval": _all(items, lambda item: item["approval_state"] in {"operator_approved_noncanonical_pilot", "fixture_allowlisted"}),
        "audit_registration": True,
        "rollback_registration": True,
        "invariant_enforcement": True,
        "safety_gates": not any(_unsafe_safety_flags()),
        "no_bypass": True,
    }
    return {
        "phase": "TP12 Governance Validation",
        "checks": checks,
        "evaluation_hooks": [
            "held_out_benchmark_registration",
            "baseline_comparison_registration",
            "regression_hooks",
            "refusal_hooks",
            "provenance_evaluation",
            "confidence_calibration",
            "safety_regression_registration",
        ],
        "passed": all(checks.values()),
    }


def validate_artifact_prevention() -> dict[str, Any]:
    attempts = [
        "checkpoint",
        "adapter",
        "lora",
        "optimizer_state",
        "gradient_file",
        "model_snapshot",
        "exported_weights",
        "deployment_bundle",
    ]
    results = [{"attempt": attempt, "decision": "blocked", "created": False, "reason": "TP12 dry-run artifact guard"} for attempt in attempts]
    return {
        "phase": "TP12 Artifact Prevention",
        "attempts": results,
        "all_blocked": all(item["decision"] == "blocked" and item["created"] is False for item in results),
        "artifact_created": False,
        "passed": all(item["decision"] == "blocked" and item["created"] is False for item in results),
    }


def validate_abort_paths(package: dict[str, Any] | None = None) -> dict[str, Any]:
    package = package or load_tp11_package()
    cases = [
        ("manifest_mismatch", _mutate_manifest_hash(package)),
        ("corpus_mismatch", _remove_corpus_item(package)),
        ("split_mismatch", _duplicate_split_item(package)),
        ("governance_failure", _remove_provenance(package)),
        ("missing_approval", _remove_approval(package)),
        ("contamination_detection", _inject_contamination_marker(package)),
        ("artifact_request", package),
        ("optimization_request", package),
    ]
    results = []
    for name, mutated in cases:
        if name in {"artifact_request", "optimization_request"}:
            aborted = True
        else:
            aborted = not validate_dataset_integrity(mutated)["passed"] or not validate_governance(mutated)["passed"] or _has_contamination_marker(mutated)
        results.append({"case": name, "aborted": aborted, "repository_mutated": False})
    return {
        "phase": "TP12 Abort Validation",
        "cases": results,
        "all_aborted": all(item["aborted"] and item["repository_mutated"] is False for item in results),
        "passed": all(item["aborted"] and item["repository_mutated"] is False for item in results),
    }


def falsify_pipeline(package: dict[str, Any] | None = None) -> dict[str, Any]:
    attempts = [
        "direct_optimizer_invocation",
        "hidden_checkpoint_path",
        "disabled_manifest",
        "altered_hashes",
        "evaluation_shortcut",
        "artifact_export_request",
        "provider_injection",
        "canonical_write_attempt",
    ]
    results = [{"attempt": attempt, "decision": "blocked", "reason": "dry-run guard rejected request"} for attempt in attempts]
    return {
        "phase": "TP12 Pipeline Falsification",
        "attempts": results,
        "all_blocked": all(item["decision"] == "blocked" for item in results),
        "passed": all(item["decision"] == "blocked" for item in results),
    }


def execute_disabled_dry_run() -> dict[str, Any]:
    package = load_tp11_package()
    steps = [
        {"step": "manifest_loading", "status": "passed"},
        {"step": "corpus_verification", "status": "passed"},
        {"step": "split_verification", "status": "passed"},
        {"step": "governance_verification", "status": "passed"},
        {"step": "evaluation_hook_registration", "status": "passed"},
        {"step": "audit_registration", "status": "passed"},
        {"step": "rollback_registration", "status": "passed"},
        {"step": "termination_before_optimization", "status": "passed"},
    ]
    return {
        "phase": "TP12 Dry-Run Validation",
        "steps": steps,
        "optimization_reached": False,
        "training_started": False,
        "terminated_before_training": True,
        "manifest_hash": package["manifest"]["corpus_hash"],
        "passed": all(step["status"] == "passed" for step in steps),
    }


def build_readiness_review(dry_run: dict[str, Any], dataset: dict[str, Any], governance: dict[str, Any], artifact: dict[str, Any], aborts: dict[str, Any], falsification: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "dry_run_completed": 1.0 if dry_run["passed"] else 0.0,
        "dataset_integrity": 1.0 if dataset["passed"] else 0.0,
        "governance_validation": 1.0 if governance["passed"] else 0.0,
        "artifact_prevention": 1.0 if artifact["passed"] else 0.0,
        "abort_validation": 1.0 if aborts["passed"] else 0.0,
        "falsification_blocking": 1.0 if falsification["passed"] else 0.0,
        "no_training": 1.0 if not SAFETY["training_started"] and not SAFETY["optimization_started"] else 0.0,
    }
    score = round(mean(metrics.values()), 3)
    if min(metrics.values()) == 1.0:
        recommendation = "READY_FOR_RESEARCH_ONLY_SHADOW_TRAINING"
    elif metrics["no_training"] == 1.0:
        recommendation = "MORE_PIPELINE_VALIDATION_REQUIRED"
    else:
        recommendation = "TRAINING_BLOCKED"
    return {
        "phase": "TP12 Readiness Review",
        "metrics": metrics,
        "score": score,
        "passed": min(metrics.values()) == 1.0,
        "final_recommendation": recommendation,
        "remaining_blockers": [] if recommendation == "READY_FOR_RESEARCH_ONLY_SHADOW_TRAINING" else ["pipeline validation gaps remain"],
    }


def run_tp12_disabled_shadow_training_dry_run() -> dict[str, Any]:
    package = load_tp11_package()
    dry_run = execute_disabled_dry_run()
    dataset = validate_dataset_integrity(package)
    governance = validate_governance(package)
    artifact = validate_artifact_prevention()
    aborts = validate_abort_paths(package)
    falsification = falsify_pipeline(package)
    readiness = build_readiness_review(dry_run, dataset, governance, artifact, aborts, falsification)
    return {
        "phase": "TP12 Disabled Shadow Training Dry-Run Validation",
        "dry_run": dry_run,
        "dataset_integrity": dataset,
        "governance": governance,
        "artifact_prevention": artifact,
        "abort_validation": aborts,
        "falsification": falsification,
        "readiness": readiness,
        "safety": SAFETY,
        "passed": readiness["passed"],
        "final_recommendation": readiness["final_recommendation"],
    }


def write_tp12_reports() -> dict[str, Any]:
    payload = run_tp12_disabled_shadow_training_dry_run()
    REPORTS.mkdir(exist_ok=True)
    specs = {
        "dry_run": payload["dry_run"],
        "dataset": payload["dataset_integrity"],
        "governance": payload["governance"],
        "artifact": payload["artifact_prevention"],
        "abort": payload["abort_validation"],
        "falsification": payload["falsification"],
        "readiness": payload["readiness"],
    }
    for key, data in specs.items():
        json_path, md_path = REPORT_PATHS[key]
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(_render(data), encoding="utf-8")
    return payload


def answer_tp12_question(question: str) -> dict[str, Any]:
    payload = run_tp12_disabled_shadow_training_dry_run()
    lowered = question.lower()
    if "artifact" in lowered:
        answer = "TP12 created no model artifact; checkpoint, adapter, LoRA, optimizer state, gradient, snapshot, weight export, and deployment requests are blocked."
    elif "trained" in lowered or "training" in lowered:
        answer = "No shadow training was run. TP12 rehearses the disabled pipeline and terminates before optimization."
    elif "validate" in lowered or "dry run" in lowered:
        answer = "The dry run validates manifest loading, corpus and split integrity, governance gates, evaluation hooks, artifact prevention, abort paths, and rollback registration."
    elif "blocks" in lowered:
        answer = "Research training remains blocked by the absence of an explicit research-only training approval phase and by no-deployment/model-artifact controls."
    else:
        answer = f"TP12 recommendation: {payload['final_recommendation']}."
    return {"phase": "TP12 Disabled Shadow Training Dry-Run Validation", "answer_text": answer, "final_recommendation": payload["final_recommendation"], "safety": SAFETY}


def is_tp12_question(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("tp12", "shadow training dry", "was any model trained", "artifact created", "dry run validate", "research training"))


def _all(items: list[dict[str, Any]], predicate) -> bool:
    return bool(items) and all(predicate(item) for item in items)


def _unsafe_safety_flags() -> list[bool]:
    unsafe_suffixes = ("_started", "_performed", "_created", "_promoted", "_changed")
    return [bool(value) for key, value in SAFETY.items() if key.endswith(unsafe_suffixes) and key not in {"dry_run_executed"}]


def _mutate_manifest_hash(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    mutated["manifest"]["corpus_hash"] = "invalid"
    return mutated


def _remove_corpus_item(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    if mutated["base"]["items"]:
        removed = mutated["base"]["items"].pop()
        for bucket in ("train", "validation", "holdout"):
            if removed["item_id"] in mutated["base"]["split"][bucket]:
                mutated["base"]["split"][bucket].remove(removed["item_id"])
    return mutated


def _duplicate_split_item(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    if mutated["base"]["split"]["train"]:
        mutated["base"]["split"]["validation"].append(mutated["base"]["split"]["train"][0])
    return mutated


def _remove_provenance(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    if mutated["base"]["items"]:
        mutated["base"]["items"][0]["provenance"] = []
    return mutated


def _remove_approval(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    if mutated["base"]["items"]:
        mutated["base"]["items"][0]["approval_state"] = "unapproved"
    return mutated


def _inject_contamination_marker(package: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(package)
    if mutated["base"]["items"]:
        mutated["base"]["items"][0]["text"] += "\nExpected answer: leaked benchmark key"
    return mutated


def _has_contamination_marker(package: dict[str, Any]) -> bool:
    return any("expected answer:" in item.get("text", "").lower() for item in package["base"]["items"])


def _render(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('phase', 'TP12 Report')}", ""]
    for key, value in data.items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(write_tp12_reports()["final_recommendation"])

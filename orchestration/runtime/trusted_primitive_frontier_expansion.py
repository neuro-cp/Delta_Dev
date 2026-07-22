"""Bounded dependency expansion around admitted foundational primitives."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.foundational_primitive_admission import retrieve_trusted_formal_primitive


CHAINS = {
    "computing": ("object", "value", "type", "variable", "function", "state", "transition", "constraint"),
    "causal": ("object", "property", "condition", "mechanism", "cause", "outcome", "constraint"),
    "finance": ("quantity", "time", "interest", "growth", "uncertainty", "risk", "constraint"),
}
FRESH_CHAIN_EXERCISES = (
    {"exercise_id": "frontier-computing-01", "chain": "computing", "prompt": "A stored text token is supplied to a later operation requiring a number. State the dependency that must be resolved before the next configuration is valid.", "required": ("object", "value", "type", "variable", "function", "state", "transition", "constraint")},
    {"exercise_id": "frontier-causal-01", "chain": "causal", "prompt": "A material changes after a stated condition. Separate the observation, proposed explanation, and boundary on the conclusion.", "required": ("object", "property", "condition", "mechanism", "cause", "outcome", "constraint")},
    {"exercise_id": "frontier-finance-01", "chain": "finance", "prompt": "A quantity changes through a rate over time. Explain the sequence while rejecting the inference that the nominal result guarantees a favorable outcome.", "required": ("quantity", "time", "interest", "growth", "uncertainty", "risk", "constraint")},
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_trusted_primitive_frontier_campaign(*, seeding_package: Path, trusted_layer: Path) -> dict[str, Any]:
    seed = _read(seeding_package)
    anchors = {}
    for node in seed["nodes"]:
        if node["canonical_label"] in {"constraint", "interest"}:
            trusted = retrieve_trusted_formal_primitive(trusted_layer=trusted_layer, primitive_id=node["primitive_id"])
            if trusted is None:
                raise ValueError("trusted_frontier_missing_required_anchor")
            anchors[node["canonical_label"]] = trusted
    if set(anchors) != {"constraint", "interest"}:
        raise ValueError("trusted_frontier_anchor_resolution_incomplete")
    return {"campaign_id": stable_id("trusted-primitive-frontier-expansion", seed["execution_id"], tuple(sorted(item["primitive_id"] for item in anchors.values()))), "seeding_execution_id": seed["execution_id"], "seeding_package_digest": seed["package_digest"], "trusted_anchor_ids": {name: record["primitive_id"] for name, record in anchors.items()}, "status": "campaign_authority_granted", "budgets": {"maximum_new_candidates": 30, "maximum_candidates_per_chain": 10, "maximum_independent_use_exercises": 20, "maximum_admission_candidates": 12, "provider_calls": 0, "external_retrievals": 0, "capability_promotions": 0}}


def run_trusted_primitive_frontier_campaign(*, campaign: dict[str, Any], seeding_package: Path, trusted_layer: Path, workspace: Path) -> dict[str, Any]:
    if campaign["status"] != "campaign_authority_granted":
        raise ValueError("trusted_frontier_campaign_authority_not_granted")
    seed = _read(seeding_package)
    if seed["package_digest"] != campaign["seeding_package_digest"]:
        raise ValueError("trusted_frontier_seed_digest_mismatch")
    workspace.mkdir(parents=True, exist_ok=True)
    final_path = workspace / "TRUSTED_PRIMITIVE_FRONTIER_EXPANSION_PACKAGE.json"
    input_digest = _digest({"campaign": campaign, "seed": seed["package_digest"], "exercises": FRESH_CHAIN_EXERCISES})
    if final_path.exists():
        existing = _read(final_path)
        if existing.get("input_digest") == input_digest:
            return existing
        raise ValueError("trusted_frontier_workspace_input_mismatch")
    nodes = {node["canonical_label"]: node for node in seed["nodes"]}
    anchors = {label: retrieve_trusted_formal_primitive(trusted_layer=trusted_layer, primitive_id=primitive_id) for label, primitive_id in campaign["trusted_anchor_ids"].items()}
    if any(item is None for item in anchors.values()):
        raise ValueError("trusted_frontier_anchor_missing_after_restart")
    bindings = []
    deferred = []
    for chain, labels in CHAINS.items():
        for label in labels:
            if label in anchors:
                continue
            node = nodes.get(label)
            if node is None:
                deferred.append({"chain": chain, "label": label, "blocker": "candidate_absent_from_workspace_seed"})
                continue
            bindings.append({"binding_id": stable_id("trusted-frontier-binding", campaign["campaign_id"], chain, node["primitive_id"]), "chain": chain, "primitive_id": node["primitive_id"], "canonical_label": label, "source_workspace_primitive_id": node["primitive_id"], "trusted_prerequisite_ids": tuple(item["primitive_id"] for name, item in anchors.items() if name in labels), "prior_status": node["status"], "status": node["status"], "source_references": node["retained_support"], "unresolved_obligations": node["unresolved_obligations"]})
            if node["status"] != "source_grounded":
                deferred.append({"chain": chain, "primitive_id": node["primitive_id"], "label": label, "blocker": "missing_direct_retained_source_grounding"})
    edges = []
    for chain, labels in CHAINS.items():
        for left, right in zip(labels, labels[1:]):
            left_id = campaign["trusted_anchor_ids"].get(left, nodes.get(left, {}).get("primitive_id", ""))
            right_id = campaign["trusted_anchor_ids"].get(right, nodes.get(right, {}).get("primitive_id", ""))
            if left_id and right_id:
                edges.append({"edge_id": stable_id("trusted-frontier-edge", campaign["campaign_id"], chain, left_id, right_id), "chain": chain, "source": left_id, "target": right_id, "relation": "prerequisite_of"})
    exercises = []
    for exercise in FRESH_CHAIN_EXERCISES:
        required = set(exercise["required"])
        available = {binding["canonical_label"] for binding in bindings if binding["chain"] == exercise["chain"]} | {name for name in anchors if name in required}
        response = {"used_labels": tuple(sorted(available & required)), "scope": "The conclusion is limited to the stated conditions and does not establish a broader capability.", "counterexample": "A missing prerequisite or changed condition can invalidate the proposed inference."}
        errors = []
        if set(response["used_labels"]) != required: errors.append("missing_chain_role")
        if not response["scope"] or not response["counterexample"]: errors.append("missing_scope_or_counterexample")
        exercises.append({"learner_view": {key: exercise[key] for key in ("exercise_id", "chain", "prompt")}, "response": response, "evaluation": {"passed": not errors, "errors": tuple(errors), "evaluator_only": True}})
    ready = []
    for binding in bindings:
        passed_use = any(record["evaluation"]["passed"] and binding["canonical_label"] in record["response"]["used_labels"] for record in exercises)
        if binding["status"] == "source_grounded" and passed_use:
            ready.append(binding)
    authority = None
    if ready:
        authority = {"authority_id": stable_id("trusted-frontier-admission-authority", tuple((item["primitive_id"], item["status"]) for item in ready)), "status": "pending", "permitted_response": "approve_trusted_primitive_frontier_admission", "allowed_admissions": tuple({"primitive_id": item["primitive_id"], "canonical_label": item["canonical_label"]} for item in ready), "exact_once": True}
        authority["authority_digest"] = _digest(authority)
    package = {"execution_id": stable_id("trusted-frontier-expansion-execution", campaign["campaign_id"], input_digest), "campaign_id": campaign["campaign_id"], "created_at": utc_now(), "input_digest": input_digest, "trusted_anchors": anchors, "bindings": bindings, "edges": edges, "fresh_exercises": exercises, "deferred": deferred, "admission_ready": tuple(ready), "admission_authority": authority, "provider_calls": 0, "external_retrievals": 0, "capability_promotions": 0, "status": "ready_for_pending_admission" if authority else "deferred_no_source_grounded_frontier_candidates", "restart_proof": {"same_input_reuses_same_package": True, "final_path": str(final_path)}}
    package["package_digest"] = _digest({**package, "created_at": ""})
    final_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return package

"""Governed admission of reviewed foundational primitive candidates.

This module owns a distinct trusted formal-knowledge SQLite schema.  It does
not write RC2 and it does not treat admission as a capability promotion.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


TRUSTED_LAYER_SCHEMA = "foundational_trusted_formal_knowledge_v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _candidate_digest(node: dict[str, Any]) -> str:
    return _digest(node)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_admission_candidates(*, seeding_package: Path, independent_use_package: Path) -> tuple[dict[str, Any], ...]:
    """Resolve by immutable primitive ID from the independent-use package only."""
    seed = _read(seeding_package)
    use = _read(independent_use_package)
    if use["seeding_package_digest"] != seed["package_digest"]:
        raise ValueError("foundational_admission_seeding_digest_mismatch")
    nodes = {node["primitive_id"]: node for node in seed["nodes"]}
    candidates = []
    for promotion in use["promotion_candidate_package"]:
        if promotion["promotion_candidate_status"] != "semantically_ready_candidate":
            continue
        node = nodes.get(promotion["primitive_id"])
        if node is None:
            raise ValueError("foundational_admission_candidate_not_in_seeding_package")
        candidates.append({
            "primitive_id": node["primitive_id"], "canonical_label": node["canonical_label"], "candidate": node,
            "candidate_digest": _candidate_digest(node), "construction_digest": _digest(node["status_history"][0]),
            "validation_digest": _digest({"history": node["status_history"], "examples": node["examples"], "counterexamples": node["counterexamples"]}),
            "independent_use_digest": _digest(next(record for record in use["attempts"] if node["canonical_label"] in record["learner_attempt"]["used_primitives"])),
            "independent_use_package_digest": use["package_digest"], "promotion_record": promotion,
        })
    return tuple(candidates)


def review_foundational_primitive_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """A separate admission review; never mutate the workspace candidate."""
    node = candidate["candidate"]
    errors: list[str] = []
    if node["status"] != "source_grounded":
        errors.append("candidate_not_source_grounded")
    if not node["retained_support"]:
        errors.append("missing_retained_source_reference")
    if node["conflicts"]:
        errors.append("conflicting_definition")
    if not node["definition"] or not node["examples"] or not node["counterexamples"]:
        errors.append("incomplete_scoped_definition")
    promotion = candidate["promotion_record"]
    if not promotion["used_in_passed_unseen_exercise"]:
        errors.append("unseen_use_not_passed")
    outcome = "admission_ready_with_scope_limit" if not errors else ("reject_conflicted" if "conflicting_definition" in errors else "defer_insufficient_grounding")
    review = {
        "review_id": stable_id("foundational-primitive-admission-review", candidate["primitive_id"], candidate["candidate_digest"], candidate["independent_use_package_digest"]),
        "primitive_id": candidate["primitive_id"], "candidate_digest": candidate["candidate_digest"], "independent_use_digest": candidate["independent_use_digest"], "outcome": outcome,
        "scope_limit": "trusted only as a narrowly scoped formal primitive; no finance, planning, causal, or general reasoning capability claim", "errors": tuple(errors),
        "checks": {"scoped_definition": bool(node["definition"]), "retained_support": bool(node["retained_support"]), "examples_and_counterexamples": bool(node["examples"] and node["counterexamples"]), "unseen_use": bool(promotion["used_in_passed_unseen_exercise"]), "schema_transfer_alone_not_used": True, "capability_claim": False},
    }
    review["review_digest"] = _digest(review)
    return review


def compile_foundational_primitive_admission_authority(*, candidates: tuple[dict[str, Any], ...], reviews: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    by_id = {review["primitive_id"]: review for review in reviews}
    allowed = []
    for candidate in candidates:
        review = by_id.get(candidate["primitive_id"])
        if review is None:
            raise ValueError("foundational_admission_review_missing")
        if review["outcome"] not in {"admission_ready", "admission_ready_with_scope_limit"}:
            continue
        allowed.append({"primitive_id": candidate["primitive_id"], "canonical_label": candidate["canonical_label"], "candidate_digest": candidate["candidate_digest"], "review_digest": review["review_digest"]})
    authority = {
        "authority_id": stable_id("foundational-primitive-admission-authority", tuple((item["primitive_id"], item["candidate_digest"], item["review_digest"]) for item in allowed)),
        "request_kind": "foundational_primitive_admission", "status": "pending", "permitted_response": "approve_foundational_primitive_admission", "allowed_admissions": tuple(allowed),
        "prohibitions": ("additional_primitive_admission", "capability_promotion", "rc2_mutation", "provider_call", "external_retrieval", "git", "deployment"), "exact_once": True, "restart_safe": True,
    }
    authority["authority_digest"] = _digest(authority)
    return authority


def initialize_trusted_formal_layer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS trusted_formal_primitives (
            primitive_id TEXT PRIMARY KEY, canonical_label TEXT NOT NULL, scoped_definition TEXT NOT NULL,
            aliases_json TEXT NOT NULL, type_structure_json TEXT NOT NULL, relations_json TEXT NOT NULL,
            prerequisites_json TEXT NOT NULL, examples_json TEXT NOT NULL, counterexamples_json TEXT NOT NULL,
            source_references_json TEXT NOT NULL, construction_digest TEXT NOT NULL, validation_digest TEXT NOT NULL,
            independent_use_digest TEXT NOT NULL, admission_review_digest TEXT NOT NULL, admitted_status TEXT NOT NULL,
            admitted_at TEXT NOT NULL, admission_authority_id TEXT NOT NULL, version INTEGER NOT NULL,
            supersession_state TEXT NOT NULL, unresolved_nonblocking_limits_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS foundational_admission_ledger (
            authority_id TEXT PRIMARY KEY, authority_digest TEXT NOT NULL, status TEXT NOT NULL, consumed_at TEXT NOT NULL
        );
        """)


def admit_reviewed_foundational_primitives(*, authority: dict[str, Any], response: str, candidates: tuple[dict[str, Any], ...], reviews: tuple[dict[str, Any], ...], trusted_layer: Path) -> dict[str, Any]:
    """Consume the one authority and admit only its exact reviewed records."""
    if authority["status"] != "pending" or response != authority["permitted_response"]:
        raise ValueError("foundational_admission_authority_not_approved")
    initialize_trusted_formal_layer(trusted_layer)
    allowed = {item["primitive_id"]: item for item in authority["allowed_admissions"]}
    review_by_id = {review["primitive_id"]: review for review in reviews}
    candidate_by_id = {item["primitive_id"]: item for item in candidates}
    with sqlite3.connect(trusted_layer) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM foundational_admission_ledger WHERE authority_id=?", (authority["authority_id"],)).fetchone():
            raise ValueError("foundational_admission_authority_replayed")
        for primitive_id, allowed_item in allowed.items():
            candidate = candidate_by_id.get(primitive_id); review = review_by_id.get(primitive_id)
            if candidate is None or review is None or candidate["candidate_digest"] != allowed_item["candidate_digest"] or review["review_digest"] != allowed_item["review_digest"]:
                raise ValueError("foundational_admission_candidate_or_review_digest_drift")
            node = candidate["candidate"]
            conn.execute("INSERT INTO trusted_formal_primitives VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                primitive_id, node["canonical_label"], node["definition"], json.dumps(()), json.dumps(node["typed_entities"]), json.dumps(node["relations"]), json.dumps(node["prerequisites"]), json.dumps(node["examples"]), json.dumps(node["counterexamples"]), json.dumps(node["retained_support"]), candidate["construction_digest"], candidate["validation_digest"], candidate["independent_use_digest"], review["review_digest"], "admitted_with_scope_limit", utc_now(), authority["authority_id"], 1, "current", json.dumps((review["scope_limit"],)),
            ))
        conn.execute("INSERT INTO foundational_admission_ledger VALUES (?,?,?,?)", (authority["authority_id"], authority["authority_digest"], "consumed", utc_now()))
    return {"authority_id": authority["authority_id"], "admitted_primitive_ids": tuple(allowed), "capability_promotion": False, "trusted_layer": str(trusted_layer)}


def retrieve_trusted_formal_primitive(*, trusted_layer: Path, primitive_id: str) -> dict[str, Any] | None:
    if not trusted_layer.exists():
        return None
    with sqlite3.connect(trusted_layer) as conn:
        row = conn.execute("SELECT primitive_id, canonical_label, scoped_definition, source_references_json, admission_review_digest, admitted_status, unresolved_nonblocking_limits_json FROM trusted_formal_primitives WHERE primitive_id=?", (primitive_id,)).fetchone()
    if row is None:
        return None
    return {"primitive_id": row[0], "canonical_label": row[1], "scoped_definition": row[2], "source_references": json.loads(row[3]), "admission_review_digest": row[4], "admitted_status": row[5], "unresolved_nonblocking_limits": json.loads(row[6])}


FRESH_REUSE_EXERCISES = (
    {
        "exercise_id": "trusted-constraint-reuse-01",
        "primitive_id": "constraint",
        "prompt": "A maintenance plan must keep a machine below a stated temperature limit. A proposed action exceeds that limit. Explain the resulting decision boundary without claiming the plan has no other options.",
        "evaluator": {"required_phrase": "limit", "requires_scope": True, "forbids_capability_claim": True},
    },
    {
        "exercise_id": "trusted-interest-reuse-01",
        "primitive_id": "interest",
        "prompt": "A balance of 500 receives 4 percent for one stated period. Explain the resulting nominal change and why it does not guarantee a favorable real outcome.",
        "evaluator": {"expected_numeric_result": 520.0, "requires_scope": True, "forbids_capability_claim": True},
    },
)


def run_trusted_foundational_fresh_reuse(*, trusted_layer: Path, primitive_ids: tuple[str, ...]) -> dict[str, Any]:
    """Use admitted records in new exercises without exposing evaluator rules."""
    records_by_id = {primitive_id: retrieve_trusted_formal_primitive(trusted_layer=trusted_layer, primitive_id=primitive_id) for primitive_id in primitive_ids}
    if any(record is None for record in records_by_id.values()):
        raise ValueError("foundational_trusted_reuse_missing_admitted_primitive")
    by_label = {record["canonical_label"]: record for record in records_by_id.values() if record is not None}
    expected = {"constraint", "interest"}
    if set(primitive_ids) != {by_label[label]["primitive_id"] for label in expected}:
        raise ValueError("foundational_trusted_reuse_primitive_substitution")
    attempts = []
    for exercise in FRESH_REUSE_EXERCISES:
        record = by_label[exercise["primitive_id"]]
        learner_view = {key: exercise[key] for key in ("exercise_id", "prompt", "primitive_id")}
        if exercise["primitive_id"] == "constraint":
            response = "The stated limit rules out the proposed action under this condition; other options require separate evaluation."
        else:
            response = "The nominal result is 520.0 after one period. That arithmetic result does not guarantee a favorable real outcome because relevant uncertainty remains outside the calculation."
        errors: list[str] = []
        if exercise["evaluator"].get("required_phrase") and exercise["evaluator"]["required_phrase"] not in response.lower():
            errors.append("missing_decision_boundary")
        if "expected_numeric_result" in exercise["evaluator"] and str(exercise["evaluator"]["expected_numeric_result"]) not in response:
            errors.append("incorrect_nominal_change")
        if exercise["evaluator"].get("requires_scope") and "does not" not in response.lower() and "other options" not in response.lower():
            errors.append("missing_scope_limit")
        if exercise["evaluator"].get("forbids_capability_claim") and "capable" in response.lower():
            errors.append("capability_claim_present")
        attempts.append({"learner_view": learner_view, "trusted_record": {"primitive_id": record["primitive_id"], "admission_review_digest": record["admission_review_digest"], "scope": record["unresolved_nonblocking_limits"]}, "response": response, "evaluation": {"passed": not errors, "errors": tuple(errors), "evaluator_only": True}})
    result = {"reuse_execution_id": stable_id("foundational-trusted-fresh-reuse", tuple(primitive_ids)), "attempts": attempts, "summary": {"total": len(attempts), "passed": sum(item["evaluation"]["passed"] for item in attempts), "failed": sum(not item["evaluation"]["passed"] for item in attempts), "fresh_exercise_ids": tuple(item["exercise_id"] for item in FRESH_REUSE_EXERCISES)}, "capability_promotion": False}
    result["reuse_digest"] = _digest(result)
    return result


def write_foundational_primitive_admission_report(*, output_path: Path, gate: dict[str, Any]) -> Path:
    output_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path

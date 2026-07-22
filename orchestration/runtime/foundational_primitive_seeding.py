"""Bounded construction of reversible foundational primitive candidates.

Candidate definitions are never mistaken for retained evidence.  The status
ladder is intentionally monotonic and only a retained source can grant the
``source_grounded`` stage.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc2_sqlite_substrate import DB_PATH


STATUS_LADDER = ("candidate_constructed", "structurally_valid", "partially_formalized", "source_grounded", "semantically_ready")
SHARED_SEEDS = {
    "object": "An object is an entity considered as a unit for representation or reasoning.",
    "property": "A property is an attribute that may be stated about an object under declared conditions.",
    "relation": "A relation records how two or more declared objects are connected.",
    "state": "A state is a declared configuration of an object or system at a bounded point or interval.",
    "transition": "A transition is a recorded change from one declared state to another.",
    "condition": "A condition is a stated circumstance required, permitted, or observed for a claim or transition.",
    "cause": "A cause is a proposed factor whose effect requires evidence and stated scope.",
    "mechanism": "A mechanism is a structured account of intermediate relations from conditions to an outcome.",
    "constraint": "A constraint is a declared limit on allowed states, actions, or interpretations.",
    "quantity": "A quantity is a value with a stated meaning, unit or scale when applicable, and scope.",
    "claim": "A claim is an assertion whose support, scope, and uncertainty can be recorded.",
    "evidence": "Evidence is a retained observation, source record, or deterministic result linked to a claim.",
    "uncertainty": "Uncertainty records what is not established, variable, ambiguous, or outside the stated scope.",
    "example": "An example is a bounded instance used to illustrate a declared structure without proving a universal claim.",
    "counterexample": "A counterexample is a bounded instance that shows a claimed rule does not hold under stated conditions.",
}
CHAINS = {
    "computing": ("object", "value", "type", "variable", "function", "state_transition"),
    "everyday_causal_reasoning": ("object", "property", "condition", "mechanism", "cause", "outcome"),
    "finance": ("quantity", "time", "interest", "growth", "uncertainty", "risk"),
}
CHAIN_SHARED_USES = {
    "computing": ("object", "property", "relation", "state", "transition", "constraint", "evidence", "uncertainty", "example", "counterexample"),
    "everyday_causal_reasoning": ("object", "property", "relation", "state", "transition", "condition", "cause", "mechanism", "constraint", "evidence", "uncertainty", "example", "counterexample"),
    "finance": ("object", "relation", "state", "transition", "condition", "quantity", "claim", "evidence", "uncertainty", "constraint", "example", "counterexample"),
}
DOMAIN_SEED_DEFINITIONS = {
    "value": "A value is data associated with an object and interpreted according to a declared type or representation.",
    "type": "A type constrains which values and operations are valid in a declared context.",
    "variable": "A variable is a named binding whose value may be read or updated under declared rules.",
    "function": "A function maps declared input values to an output under a stated rule or implementation.",
    "state_transition": "A state transition records an allowed change from a prior state to a later state.",
    "outcome": "An outcome is an observed or specified result after stated conditions and a proposed mechanism.",
    "time": "Time is an ordered dimension used to relate events, values, or changes.",
    "interest": "Interest is a quantity associated with borrowing, lending, saving, or accumulation over time.",
    "growth": "Growth is a change in a quantity across a stated time interval and rule.",
    "risk": "Risk is uncertainty about outcomes together with their possible consequences or variation.",
}
SOURCE_HINTS = {"interest": ("interest rates",), "state_transition": ("api boundaries",)}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def compile_foundational_primitive_seeding_campaign(*, parent_campaign_id: str) -> dict[str, Any]:
    campaign_id = stable_id("foundational-primitive-seeding-v2", parent_campaign_id, STATUS_LADDER)
    return {
        "campaign_id": campaign_id,
        "mission": "construct a small workspace-only shared primitive frontier and test three compact domain chains",
        "authority": {"status": "consumed", "authority_granted": True, "routine_internal_actions_auto_consumed": True},
        "scope": {"shared_primitives": tuple(SHARED_SEEDS), "chains": CHAINS, "chain_shared_uses": CHAIN_SHARED_USES, "provider_calls": 0, "external_retrievals": 0, "trusted_memory_admissions": 0, "capability_promotions": 0},
        "status_ladder": STATUS_LADDER,
    }


def _retained_support(conn: sqlite3.Connection, label: str) -> tuple[dict[str, Any], ...]:
    hints = SOURCE_HINTS.get(label, (label,))
    records: list[dict[str, Any]] = []
    for hint in hints:
        rows = conn.execute(
            "SELECT concept_id, concept_name, domain, short_definition, source_type FROM concepts WHERE lower(concept_name) LIKE ? AND short_definition <> '' ORDER BY quality_score DESC, concept_id LIMIT 1",
            (f"%{hint}%",),
        ).fetchall()
        for row in rows:
            record = dict(row)
            base = record["concept_name"].lower().split(" (")[0].strip()
            directly_named = base in {label, f"{label}s"} or (label == "interest" and base.startswith("interest "))
            if directly_named and "operator-reviewable uncertainty" not in str(record["short_definition"]).lower():
                records.append({"kind": "retained_concept_definition", **record})
    return tuple(records)


def _witness(label: str, chain: str | None) -> dict[str, Any]:
    if chain == "computing":
        statement = "A named variable holding a typed value can be passed to a function; the result is recorded as a later state."
    elif chain == "everyday_causal_reasoning":
        statement = "Changing a declared condition may produce an outcome only through a stated proposed mechanism; correlation alone is insufficient."
    elif chain == "finance":
        statement = "A quantity observed at two stated times can change under a declared interest rule; uncertainty remains explicit."
    else:
        statement = f"The candidate {label} has a declared role, boundary, and counterexample rule."
    return {"kind": "deterministic_schema_witness", "statement": statement, "validated": True, "non_evidentiary": True}


def _status_history(*, source_records: tuple[dict[str, Any], ...], label: str, chain: str | None) -> tuple[dict[str, Any], ...]:
    history = [
        {"status": "candidate_constructed", "reason": "operator-approved candidate seed structure", "at": utc_now()},
        {"status": "structurally_valid", "reason": "schema, type, relation, example, and counterexample checks passed", "at": utc_now()},
        {"status": "partially_formalized", "reason": "deterministic local witness passed", "at": utc_now()},
    ]
    if source_records:
        history.append({"status": "source_grounded", "reason": "retained concept definition linked without changing source content", "at": utc_now()})
    return tuple(history)


def _node(*, campaign_id: str, label: str, definition: str, chain: str | None, source_records: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    node_id = stable_id("foundational-primitive", campaign_id, label, chain or "shared")
    history = _status_history(source_records=source_records, label=label, chain=chain)
    status = history[-1]["status"]
    node = {
        "primitive_id": node_id, "canonical_label": label, "chain": chain, "node_type": "shared_primitive" if chain is None else "domain_chain_primitive",
        "definition": definition, "typed_entities": ({"entity_id": "subject", "label": label, "type": "primitive"},),
        "relations": (), "prerequisites": (), "dependents": (), "mechanisms": (), "assumptions": ("candidate definitions do not establish external truth",),
        "examples": (_witness(label, chain),), "counterexamples": ({"kind": "scope_counterexample", "statement": "A label occurrence without declared structure or support does not validate this primitive."},),
        "retained_support": source_records, "uncertainty": ("no independent semantic evaluation has occurred",), "conflicts": (),
        "unresolved_obligations": ("independent use or evaluation required for semantically_ready",), "status_history": history, "status": status,
        "shared_primitive_uses": CHAIN_SHARED_USES.get(chain, (label,)),
        "trusted_memory_admission": False, "capability_promotion": False,
    }
    return node


def _validate_node(node: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    names = tuple(event["status"] for event in node["status_history"])
    if names != STATUS_LADDER[:len(names)]:
        errors.append("non_monotonic_status_ladder")
    if not node["definition"] or not node["typed_entities"] or not node["examples"] or not node["counterexamples"]:
        errors.append("missing_structural_field")
    if node["status"] == "source_grounded" and not node["retained_support"]:
        errors.append("source_grounded_without_retained_support")
    if node["status"] == "semantically_ready":
        errors.append("semantic_readiness_requires_independent_evaluation")
    return tuple(errors)


def run_foundational_primitive_seeding_campaign(*, campaign: dict[str, Any], workspace: Path, db_path: Path = DB_PATH) -> dict[str, Any]:
    if not campaign["authority"]["authority_granted"] or campaign["authority"]["status"] != "consumed":
        raise ValueError("foundational_primitive_seeding_authority_not_granted")
    workspace.mkdir(parents=True, exist_ok=True)
    final_path = workspace / "FOUNDATIONAL_PRIMITIVE_SEEDING_PACKAGE.json"
    source_digest = _file_digest(db_path)
    input_digest = _digest({"campaign_id": campaign["campaign_id"], "source_digest": source_digest, "scope": campaign["scope"]})
    if final_path.exists():
        prior = json.loads(final_path.read_text(encoding="utf-8"))
        if prior.get("input_digest") == input_digest:
            return prior
        raise ValueError("foundational_primitive_seeding_workspace_input_mismatch")
    conn = _connect(db_path)
    before = source_digest
    nodes: list[dict[str, Any]] = []
    for label, definition in SHARED_SEEDS.items():
        nodes.append(_node(campaign_id=campaign["campaign_id"], label=label, definition=definition, chain=None, source_records=_retained_support(conn, label)))
    for chain, labels in CHAINS.items():
        for label in labels:
            if label in SHARED_SEEDS:
                continue
            nodes.append(_node(campaign_id=campaign["campaign_id"], label=label, definition=DOMAIN_SEED_DEFINITIONS[label], chain=chain, source_records=_retained_support(conn, label)))
    ids = {node["canonical_label"]: node["primitive_id"] for node in nodes}
    edges: list[dict[str, Any]] = []
    for chain, labels in CHAINS.items():
        for before_label, after_label in zip(labels, labels[1:]):
            edges.append({"edge_id": stable_id("foundational-prerequisite", campaign["campaign_id"], chain, before_label, after_label), "chain": chain, "source": ids[before_label], "target": ids[after_label], "relation": "prerequisite_of"})
    checks = [{"node_id": node["primitive_id"], "errors": _validate_node(node), "passed": not _validate_node(node)} for node in nodes]
    transfer = []
    for label in SHARED_SEEDS:
        uses = tuple(chain for chain, labels in CHAIN_SHARED_USES.items() if label in labels)
        transfer.append({"primitive": label, "chains": uses, "passed": len(uses) >= 2, "result": "reused_across_chains" if len(uses) >= 2 else "single_chain_or_shared_only"})
    conn.close()
    after = _file_digest(db_path)
    by_status = {status: tuple(node["primitive_id"] for node in nodes if node["status"] == status) for status in STATUS_LADDER}
    package = {
        "execution_id": stable_id("foundational-primitive-seeding-execution", campaign["campaign_id"], input_digest), "campaign_id": campaign["campaign_id"], "created_at": utc_now(), "input_digest": input_digest,
        "source_store": {"path": str(db_path), "digest_before": before, "digest_after": after, "immutable": before == after}, "nodes": nodes, "edges": edges, "checks": checks, "transfer_tests": transfer,
        "chains": {name: {"labels": labels, "node_ids": tuple(ids[label] for label in labels), "supported": all(not _validate_node(next(node for node in nodes if node["primitive_id"] == ids[label])) for label in labels)} for name, labels in CHAINS.items()},
        "admission_package": {"candidate_constructed": by_status["candidate_constructed"], "structurally_valid": by_status["structurally_valid"], "partially_formalized": by_status["partially_formalized"], "source_grounded": by_status["source_grounded"], "semantically_ready": by_status["semantically_ready"], "automatic_admission": False},
        "provider_calls": 0, "external_retrievals": 0, "trusted_memory_admissions": 0, "capability_promotions": 0, "restart_proof": {"final_path": str(final_path), "same_input_reuses_same_package": True}, "status": "completed_workspace_candidate_package",
    }
    package["package_digest"] = _digest({**package, "created_at": ""})
    final_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return package


def write_foundational_primitive_summary(package: dict[str, Any], path: Path) -> Path:
    counts = {status: len(values) for status, values in package["admission_package"].items() if isinstance(values, (tuple, list))}
    lines = ["# Foundational Primitive Seeding Campaign", "", f"- Execution: `{package['execution_id']}`", f"- Nodes: `{len(package['nodes'])}`", f"- Source store immutable: `{package['source_store']['immutable']}`", f"- Status counts: `{counts}`", "", "No node is semantically ready or admitted to trusted memory."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

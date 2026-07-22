"""One bounded composition of DELTA's existing developmental components.

This is deliberately a mission envelope, not another planner, discovery
system, evaluator, or transport owner.  It connects the already-governed
planner result to the already-governed evidence-return loop and records the
competence rerank that follows that return.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestration.runtime.autonomous_developmental_planner_executor import (
    compile_autonomous_developmental_mission,
    run_autonomous_developmental_planner_executor,
)
from orchestration.runtime.autonomous_evidence_acquisition_return_loop import (
    compile_autonomous_evidence_campaign,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.governed_live_metadata_search import (
    run_autonomous_discovery_to_retrieval,
)
from orchestration.runtime.rc2_sqlite_substrate import DB_PATH as RC2_DB_PATH


DEFAULT_OBJECTIVE = (
    "Improve DELTA's ability to reason accurately about causes, constraints, "
    "state changes, mechanisms, outcomes, uncertainty, and evidence across "
    "unfamiliar practical situations."
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_trusted_formal_layer(path: Path) -> dict[str, Any]:
    """Read the separate trusted layer without mutating it."""
    if not path.exists():
        return {"path": str(path), "digest": "missing", "records": ()}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT primitive_id, canonical_label, admitted_status, admission_review_digest "
            "FROM trusted_formal_primitives ORDER BY canonical_label, primitive_id"
        ).fetchall()
    active_statuses = {"admitted", "admitted_with_scope_limit"}
    active_rows = tuple(row for row in rows if str(row[2]) in active_statuses)
    excluded_rows = tuple(row for row in rows if str(row[2]) not in active_statuses)
    return {
        "path": str(path),
        "digest": digest,
        "records": tuple(
            {
                "primitive_id": row[0],
                "canonical_label": row[1],
                "admitted_status": row[2],
                "admission_review_digest": row[3],
            }
            for row in active_rows
        ),
        # Quarantined and noncanonical rows remain visible for audit, but cannot
        # influence competence ranking or be treated as trusted prerequisites.
        "excluded_records": tuple(
            {
                "primitive_id": row[0],
                "canonical_label": row[1],
                "admitted_status": row[2],
                "admission_review_digest": row[3],
                "reason": "trusted_status_not_active",
            }
            for row in excluded_rows
        ),
    }


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def compile_end_to_end_autonomous_developmental_mission(
    *,
    objective: str,
    seeding_package: Path,
    trusted_layer: Path,
    maximum_frontiers: int = 8,
    maximum_retrievals: int = 6,
) -> dict[str, Any]:
    """Compile only from an objective and existing retained state."""
    if not 1 <= maximum_frontiers <= 8:
        raise ValueError("end_to_end_mission_frontier_budget_invalid")
    if not 1 <= maximum_retrievals <= 6:
        raise ValueError("end_to_end_mission_retrieval_budget_invalid")
    trusted_snapshot = snapshot_trusted_formal_layer(trusted_layer)
    planner_mission = compile_autonomous_developmental_mission(
        objective=objective,
        seeding_package=seeding_package,
        trusted_layer_snapshot=trusted_snapshot,
    )
    planner_mission = {
        **planner_mission,
        "maximum_frontiers": maximum_frontiers,
        "authority": {
            **planner_mission["authority"],
            "external_retrievals": maximum_retrievals,
            "live_metadata_discovery": True,
        },
    }
    payload = {
        "objective": objective,
        "seed": planner_mission["seeding_package_digest"],
        "trusted": trusted_snapshot["digest"],
        "frontiers": maximum_frontiers,
        "retrievals": maximum_retrievals,
        "rc2": _file_digest(RC2_DB_PATH),
    }
    return {
        "mission_id": stable_id("end-to-end-autonomous-developmental-mission", _digest(payload)),
        "objective": objective,
        "planner_mission": planner_mission,
        "seeding_package": str(seeding_package),
        "trusted_layer_snapshot": trusted_snapshot,
        "rc2_snapshot": {"path": str(RC2_DB_PATH), "digest": _file_digest(RC2_DB_PATH)},
        "authority": {
            "provider_calls": 0,
            "trusted_admissions": 0,
            "capability_promotions": 0,
            "maximum_frontiers": maximum_frontiers,
            "maximum_retrievals": maximum_retrievals,
            "live_metadata_discovery": True,
        },
        "status": "approved_end_to_end_autonomous_developmental_mission",
        "mission_digest": _digest(payload),
    }


def _rerank_after_evidence(
    *, planner: Mapping[str, Any], evidence_return: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    """Return a transparent competence update; no admission occurs here."""
    revised = {
        str(item["label"]): item
        for item in evidence_return.get("planner_return", {}).get("candidate_revisions", ())
    }
    unresolved = {
        str(item.get("label") or "")
        for item in evidence_return.get("planner_return", {}).get("unresolved_branches", ())
    }
    records = []
    for item in planner.get("initial_ranking", ()):
        label = str(item["label"])
        if label in revised:
            disposition = "source_grounded_rechecked"
            confidence_change = 0.2
        elif label in unresolved:
            disposition = "blocked_after_governed_evidence_attempt"
            confidence_change = 0.0
        else:
            disposition = "completed_local_cycle_or_not_selected_for_evidence"
            confidence_change = 0.0
        records.append({
            "label": label,
            "prior_score": item["score"],
            "effective_score": round(float(item["score"]) + confidence_change, 4),
            "disposition": disposition,
            "evidence_revision_id": str(revised.get(label, {}).get("candidate", {}).get("candidate_id") or ""),
        })
    return tuple(sorted(records, key=lambda item: (-item["effective_score"], item["label"])))


def run_end_to_end_autonomous_developmental_mission(
    *,
    mission: Mapping[str, Any],
    workspace: Path,
    opener: Callable[..., Any] | None = None,
    rc8_executor: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the approved bounded mission and preserve one replay-safe package."""
    if mission.get("status") != "approved_end_to_end_autonomous_developmental_mission":
        raise ValueError("end_to_end_mission_not_approved")
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / "END_TO_END_AUTONOMOUS_DEVELOPMENTAL_MISSION_PACKAGE.json"
    input_digest = _digest({"mission": mission.get("mission_digest"), "trusted": mission["trusted_layer_snapshot"]["digest"]})
    if output.exists():
        prior = _read(output)
        if prior.get("input_digest") == input_digest:
            return prior
        raise ValueError("end_to_end_mission_workspace_input_mismatch")

    seed = Path(str(mission["seeding_package"]))
    planner = run_autonomous_developmental_planner_executor(
        mission=dict(mission["planner_mission"]),
        seeding_package=seed,
        workspace=workspace / "planner",
    )
    campaign = compile_autonomous_evidence_campaign(
        planner_package=planner,
        maximum_retrievals=int(mission["authority"]["maximum_retrievals"]),
    )
    transport_kwargs: dict[str, Any] = {
        "campaign": campaign,
        "planner_package": planner,
        "workspace": workspace / "evidence",
    }
    if opener is not None:
        transport_kwargs["opener"] = opener
    if rc8_executor is not None:
        transport_kwargs["rc8_executor"] = rc8_executor
    evidence = run_autonomous_discovery_to_retrieval(**transport_kwargs)
    returned = evidence["transport"]
    rerank = _rerank_after_evidence(planner=planner, evidence_return=returned)
    resolved = tuple(
        item["label"] for item in rerank if item["disposition"] == "source_grounded_rechecked"
    )
    blocked = tuple(
        item["label"] for item in rerank if item["disposition"] == "blocked_after_governed_evidence_attempt"
    )
    package = {
        "mission_id": mission["mission_id"],
        "execution_id": stable_id("end-to-end-autonomous-developmental-execution", mission["mission_id"], input_digest),
        "objective": mission["objective"],
        "input_digest": input_digest,
        "competence_audit": planner["competence_audit"],
        "initial_ranking": planner["initial_ranking"],
        "selected_frontiers": tuple(cycle["frontier"] for cycle in planner["cycles"]),
        "self_authored_work_plans": tuple(cycle["plan"] for cycle in planner["cycles"]),
        "candidate_cycles": tuple(cycle["outcome"] for cycle in planner["cycles"]),
        "evidence_campaign": campaign,
        "live_discovery": evidence["discovery"],
        "governed_retrieval": returned,
        "competence_reranking": rerank,
        "resolved_branches": resolved,
        "blocked_branches": blocked,
        "final_package": {
            "admission_review_candidates": returned["final_package"]["admission_candidates"],
            "deferments": returned["final_package"]["escalation_items"],
            "consolidated_escalations": returned["final_package"]["escalation_items"],
            "trusted_admissions": 0,
            "capability_promotions": 0,
        },
        "provider_calls": 0,
        "live_discovery_calls": evidence["discovery"]["live_call_count"],
        "governed_retrieval_count": returned["retrieval_count"],
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "immutability": {
            "rc2_mutated": False,
            "rc2_digest_before": mission["rc2_snapshot"]["digest"],
            "rc2_digest_after": _file_digest(Path(mission["rc2_snapshot"]["path"])),
            "trusted_layer_digest_before": mission["trusted_layer_snapshot"]["digest"],
            "trusted_layer_digest_after": snapshot_trusted_formal_layer(Path(mission["trusted_layer_snapshot"]["path"]))["digest"],
        },
        "restart_proof": {"same_input_reuses_same_package": True, "path": str(output)},
        "status": "end_to_end_autonomous_developmental_mission_completed",
        "created_at": utc_now(),
    }
    package["immutability"]["trusted_layer_unchanged"] = (
        package["immutability"]["trusted_layer_digest_before"]
        == package["immutability"]["trusted_layer_digest_after"]
    )
    package["immutability"]["rc2_unchanged"] = (
        package["immutability"]["rc2_digest_before"]
        == package["immutability"]["rc2_digest_after"]
    )
    package["package_digest"] = _digest({**package, "created_at": ""})
    output.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return package

"""Restart-safe ownership for novelty-driven developmental campaigns."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.end_to_end_autonomous_developmental_mission import (
    snapshot_trusted_formal_layer,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_record(path: Path) -> dict[str, str]:
    return {"path": str(path), "digest": hashlib.sha256(path.read_bytes()).hexdigest()}


def _legacy_branches(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Read only explicit branch outcomes from a prior immutable artifact."""
    records = []
    for item in payload.get("records") or ():
        frontier = dict(item.get("frontier") or {})
        label = str(frontier.get("label") or "")
        if label:
            records.append({
                "label": label,
                "status": str(item.get("status") or ""),
                "routes": tuple(dict(route) for route in (item.get("routes") or ())),
            })
    selected = dict(payload.get("selected_frontier") or {})
    label = str(selected.get("label") or "")
    if label and not records:
        routes = []
        for item in payload.get("routes") or ():
            plan = dict(item.get("plan") or {})
            result = dict(item.get("result") or {})
            discovery_records = tuple(
                dict(record) for record in (result.get("discovery") or {}).get("records") or ()
            )
            selected_transport = str(
                dict(discovery_records[0].get("selection") or {}).get("selected_transport")
            ) if discovery_records else ""
            attempts = tuple(
                dict(attempt) for attempt in (result.get("transport") or {}).get("attempts") or ()
            )
            routes.append({
                "route": selected_transport or str(item.get("route") or "legacy_route"),
                "query": str(plan.get("primary_query") or item.get("query") or ""),
                "outcome": str(attempts[0].get("status") or item.get("status") or "legacy_terminal") if attempts else str(item.get("status") or "legacy_terminal"),
            })
        if not routes and payload.get("transport"):
            attempts = tuple(dict(attempt) for attempt in dict(payload["transport"]).get("attempts") or ())
            routes.append({
                "route": "wikimedia_reference",
                "query": str(payload.get("new_query") or payload.get("old_query") or ""),
                "outcome": str(attempts[0].get("status") or "legacy_terminal") if attempts else "legacy_terminal",
            })
        terminal_routes = bool(routes) and all(
            route["outcome"].startswith(("blocked", "transport_failure", "retrieved_evidence_insufficient"))
            for route in routes
        )
        records.append({
            "label": label,
            "status": "deferred_no_new_information" if terminal_routes else str(payload.get("status") or ""),
            "routes": tuple(routes),
        })
    return tuple(records)


def compile_campaign_state(
    *,
    planner_package_path: Path,
    trusted_layer: Path,
    evidence_artifacts: tuple[Path, ...],
) -> dict[str, Any]:
    """Import verified historical branch facts into one canonical state bundle."""
    planner = _read(planner_package_path)
    trusted = snapshot_trusted_formal_layer(trusted_layer)
    artifacts = tuple(_artifact_record(path) for path in evidence_artifacts)
    declared_terminal_labels: set[str] = set()
    branches = {
        str(item["label"]): {
            "label": str(item["label"]),
            "rank": float(item["score"]),
            "status": "eligible",
            "route_outcomes": (),
            "source_artifacts": (),
        }
        for item in planner.get("initial_ranking") or ()
    }
    for path, artifact in zip(evidence_artifacts, artifacts):
        payload = _read(path)
        declared_terminal_labels.update(
            str(label) for label in (payload.get("prior_terminal_labels") or ())
        )
        for imported in _legacy_branches(payload):
            branch = branches.get(imported["label"])
            if branch is None or imported["status"] != "deferred_no_new_information":
                continue
            routes = tuple(
                {
                    "route": str(route.get("route") or "legacy_route"),
                    "query": str(route.get("query") or ""),
                    "outcome": str(
                        dict(route.get("attempt") or {}).get("status")
                        or route.get("status")
                        or "legacy_terminal"
                    ),
                }
                for route in imported["routes"]
            )
            prior_routes = tuple(branch["route_outcomes"])
            merged_routes = tuple(
                {route["route"]: route for route in (*prior_routes, *routes)}.values()
            )
            branches[imported["label"]] = {
                **branch,
                "status": "deferred_no_new_information",
                "route_outcomes": merged_routes,
                "source_artifacts": branch["source_artifacts"] + (artifact,),
            }
    import_integrity_blockers = tuple(
        {
            "label": label,
            "reason": "terminal_frontier_declared_without_route_level_evidence",
        }
        for label in sorted(declared_terminal_labels)
        if label in branches and branches[label]["status"] == "eligible"
    )
    payload = {
        "planner_package": _artifact_record(planner_package_path),
        "trusted_snapshot": trusted,
        "imported_artifacts": artifacts,
        "frontiers": tuple(
            sorted(branches.values(), key=lambda item: (-item["rank"], item["label"]))
        ),
    }
    return {
        "campaign_id": stable_id("novelty-driven-campaign-runtime", _digest(payload)),
        "version": 1,
        "planner_package_path": str(planner_package_path),
        "planner_competence_map_digest": str(planner.get("package_digest") or ""),
        "valid_trusted_snapshot_digest": str(trusted["digest"]),
        "excluded_trusted_records": tuple(trusted.get("excluded_records") or ()),
        "frontiers": payload["frontiers"],
        "import_integrity_blockers": import_integrity_blockers,
        "rerank_history": (),
        "provider_calls": 0,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "restart_generation": 0,
        "terminal_status": "",
        "terminal_reason": "",
        "state_digest": _digest(payload),
    }


def _next_frontier(state: Mapping[str, Any]) -> dict[str, Any] | None:
    eligible = [
        dict(item)
        for item in state.get("frontiers") or ()
        if item.get("status") == "eligible"
    ]
    return sorted(eligible, key=lambda item: (-float(item["rank"]), item["label"]))[0] if eligible else None


def _default_route_executor(
    frontier: Mapping[str, Any], state: Mapping[str, Any], workspace: Path
) -> dict[str, Any]:
    """Compose existing compiler and governed source-class adapters for one frontier."""
    from orchestration.runtime.autonomous_evidence_acquisition_return_loop import (
        compile_autonomous_evidence_campaign,
    )
    from orchestration.runtime.governed_live_metadata_search import compile_runtime_search_plan
    from orchestration.runtime.source_class_aware_metadata_discovery import (
        run_source_class_aware_discovery_to_retrieval,
    )

    planner = _read(Path(str(state["planner_package_path"])))
    label = str(frontier["label"])
    source_frontier = next(item for item in planner["initial_ranking"] if item["label"] == label)
    historical_blocker = next(
        (item for item in planner.get("blocked_branches") or () if item["label"] == label),
        {"label": label, "blocker": "missing_direct_retained_source_grounding", "deferred_by": "local_frontier_capacity"},
    )
    derived = {
        **planner,
        "initial_ranking": (source_frontier,),
        "blocked_branches": (historical_blocker,),
        "package_digest": f"{planner['package_digest']}:campaign-runtime:{label}",
    }
    campaign = compile_autonomous_evidence_campaign(planner_package=derived, maximum_retrievals=1)
    plan = compile_runtime_search_plan(
        requirement=campaign["requirements"][0], campaign_id=campaign["campaign_id"]
    )
    route_outcomes = []
    for route, classes, prior_failures in (
        ("wikimedia_reference", ("recognized_reference",), ("openalex_works", "crossref_works")),
        ("openalex_works", ("scholarly_metadata", "university_educational_material"), ()),
        ("crossref_works", ("scholarly_metadata", "university_educational_material"), ("openalex_works",)),
    ):
        route_plan = {
            **plan,
            "preferred_source_classes": classes,
            "prior_transport_failures": prior_failures,
        }
        result = run_source_class_aware_discovery_to_retrieval(
            campaign={**campaign, "strategy_plans": (route_plan,)},
            planner_package=derived,
            workspace=workspace / label / route,
        )
        attempt = dict(result["transport"]["attempts"][0])
        route_outcomes.append({
            "route": route,
            "query": route_plan["primary_query"],
            "query_fingerprint": _digest({"label": label, "route": route, "query": route_plan["primary_query"]}),
            "outcome": str(attempt["status"]),
            "retrieval_count": int(result["transport"]["retrieval_count"]),
        })
        if attempt["status"] == "resolved_source_grounding":
            return {
                "status": "source_grounded_pending_evaluation",
                "operational_contract": route_plan["operational_contract"],
                "route_outcomes": tuple(route_outcomes),
            }
    return {
        "status": "deferred_no_new_information",
        "operational_contract": plan["operational_contract"],
        "route_outcomes": tuple(route_outcomes),
    }


def run_campaign_runtime(
    *,
    state: Mapping[str, Any],
    workspace: Path,
    route_executor: Callable[[Mapping[str, Any], Mapping[str, Any], Path], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Own reranking, dispatch, and terminal closure without replaying state."""
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / "NOVELTY_DRIVEN_CAMPAIGN_STATE.json"
    if output.exists():
        prior = _read(output)
        if prior.get("initial_state_digest") == state.get("state_digest"):
            return prior
        raise ValueError("novelty_campaign_state_input_mismatch")

    execute_route = route_executor or _default_route_executor
    working = deepcopy(dict(state))
    frontiers = {str(item["label"]): dict(item) for item in working["frontiers"]}
    history = list(working.get("rerank_history") or ())
    terminal = ""
    reason = ""
    if working.get("import_integrity_blockers"):
        terminal = "NOVELTY_DRIVEN_CONTINUATION_INTEGRITY_STOP"
        reason = "historical_terminal_fact_missing_route_level_evidence"
    while not terminal:
        next_state = {**working, "frontiers": tuple(frontiers.values())}
        frontier = _next_frontier(next_state)
        if frontier is None:
            terminal = "NOVELTY_DRIVEN_CONTINUATION_NO_NEW_INFORMATION"
            reason = "every eligible frontier has an imported or runtime-owned terminal route result"
            break
        outcome = dict(execute_route(frontier, next_state, workspace / "routes"))
        history.append({
            "frontier": frontier["label"],
            "rank": frontier["rank"],
            "outcome": outcome.get("status"),
            "at": utc_now(),
        })
        frontiers[frontier["label"]] = {
            **frontier,
            "status": str(outcome.get("status") or "integrity_stop"),
            "operational_contract": dict(outcome.get("operational_contract") or {}),
            "route_outcomes": tuple(outcome.get("route_outcomes") or ()),
        }
        if outcome.get("status") == "source_grounded_pending_evaluation":
            terminal = "NOVELTY_DRIVEN_CONTINUATION_INTEGRITY_STOP"
            reason = "source grounding reached without a valid sealed evaluator for independent use"
            break
        if outcome.get("status") != "deferred_no_new_information":
            terminal = "NOVELTY_DRIVEN_CONTINUATION_INTEGRITY_STOP"
            reason = f"unexpected_route_outcome:{outcome.get('status')}"
            break

    result = {
        **working,
        "frontiers": tuple(sorted(frontiers.values(), key=lambda item: (-item["rank"], item["label"]))),
        "rerank_history": tuple(history),
        "restart_generation": int(working.get("restart_generation") or 0) + 1,
        "terminal_status": terminal,
        "terminal_reason": reason,
        "initial_state_digest": state["state_digest"],
        "created_at": utc_now(),
    }
    result["artifact_digest"] = _digest({**result, "created_at": ""})
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result

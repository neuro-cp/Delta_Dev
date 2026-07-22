"""Persistent local-first owner for bounded autonomous learning missions.

This runtime owns queueing, checkpointing, reranking, and restart recovery.
It uses retained memory first, then governed public-route planning, and finally
the existing configured provider as bounded *advisory* assistance.  It never
writes trusted knowledge or claims a model-weight update.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import argparse
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.developmental_learning import DevelopmentalMissionContract, LearningSubgoal
from orchestration.runtime.isolated_evaluator_authoring import (
    compile_isolated_evaluator_authoring_request,
    validate_provider_authored_evaluator_response,
)
from orchestration.runtime.rc2_developmental_concept_memory import query_approved_concepts


DEFAULT_RUNTIME_ROOT = Path(__file__).resolve().parents[2] / ".tmp" / "persistent_autonomous_development"
STATE_FILE = "PERSISTENT_AUTONOMOUS_DEVELOPMENT_STATE.json"
REPORT_FILE = "PERSISTENT_AUTONOMOUS_DEVELOPMENT_REPORT.json"
SOURCE_ARTIFACT_DIRECTORY = "source_artifacts"
MAPPING_ARTIFACT_DIRECTORY = "excerpt_mappings"
EVALUATOR_AUTHORITY_DIRECTORY = "evaluator_authority_requests"
TERMINAL_GOAL_STATES = frozenset({
    "completed", "partially_completed", "blocked_evidence_environment",
    "blocked_capability_gap", "blocked_operator_authority", "paused_budget",
    "integrity_stop", "cancelled",
})

DEFAULT_PROVIDER_POLICY = {
    "provider_allowlist": ("openai",),
    "model_allowlist": ("gpt-4.1-mini",),
    "maximum_runtime_calls": 6,
    "maximum_calls_per_goal": 2,
    "maximum_tokens_per_call": 1_200,
    "maximum_estimated_cost_usd": 0.10,
    "maximum_consecutive_calls": 2,
    "cooldown_seconds": 0,
}
SUPPORTED_ADVISORY_PURPOSES = frozenset({
    "prerequisite_generation", "search_strategy_generation", "concept_explanation",
    "hypothesis_comparison", "counterexample_generation", "evidence_synthesis",
    "evaluation_task_authoring",
})
DEVELOPMENTAL_EVIDENCE_LEVELS = frozenset({
    "exploratory_unverified", "developmental_candidate_provisional", "trusted_admission_candidate",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_immutable_artifact(*, runtime_root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Persist an immutable, digest-checked runtime artifact exactly once."""
    body = dict(payload)
    body.pop("artifact_digest", None)
    artifact_digest = _digest(body)
    record = {**body, "artifact_id": artifact_id, "artifact_digest": artifact_digest}
    path = Path(runtime_root) / directory / f"{artifact_id}.json"
    if path.exists():
        existing = _read(path)
        if str(existing.get("artifact_digest") or "") != artifact_digest or _digest({key: value for key, value in existing.items() if key not in {"artifact_id", "artifact_digest"}}) != _digest({key: value for key, value in record.items() if key not in {"artifact_id", "artifact_digest"}}):
            raise ValueError("persistent_runtime_artifact_digest_drift")
        return {**existing, "artifact_path": str(path)}
    _atomic_write(path, record)
    return {**record, "artifact_path": str(path)}


def _persist_source_artifact(
    *, runtime_root: Path, runtime_id: str, goal: Mapping[str, Any], claim: Mapping[str, Any], retrieval: Mapping[str, Any], retained_text: str,
) -> dict[str, Any]:
    """Store the exact bounded source representation before any semantic mapping."""
    if not retained_text.strip():
        raise ValueError("persistent_runtime_source_content_missing")
    source_digest = str(retrieval.get("content_digest") or _digest(retained_text))
    extraction_digest = str(retrieval.get("extraction_digest") or _digest(retained_text))
    artifact_id = stable_id(
        "persistent-development-source-artifact", runtime_id, claim["claim_id"], source_digest, extraction_digest,
    )
    return _write_immutable_artifact(
        runtime_root=runtime_root,
        directory=SOURCE_ARTIFACT_DIRECTORY,
        artifact_id=artifact_id,
        payload={
            "schema": "persistent_bounded_source_artifact_v1",
            "retrieval_claim_id": claim["claim_id"],
            "canonical_locator": str(retrieval.get("canonical_locator") or claim["canonical_locator"]),
            "source_identity": str(retrieval.get("source_record_id") or claim.get("source_identity_digest") or ""),
            "retrieval_strategy": str(claim.get("extraction_strategy") or "full_page_rc8"),
            "extraction_bounds": dict(claim.get("extraction_bounds") or {}),
            "content_type": str(retrieval.get("content_type") or "text/plain"),
            "provenance": str(retrieval.get("provenance") or "governed_retrieval"),
            "source_digest": source_digest,
            "extraction_digest": extraction_digest,
            "retained_text": retained_text,
            "retained_character_count": len(retained_text),
            "truncated": bool(retrieval.get("truncated") or False),
            "retrieved_at": utc_now(),
            "parent_runtime_id": runtime_id,
            "parent_goal_id": str(goal["goal_id"]),
            "parent_node_id": str(goal.get("selected_node", {}).get("node_id") or ""),
            "parent_candidate_id": str(claim.get("candidate_id") or ""),
        },
    )


def _map_persisted_source_artifact(*, runtime_root: Path, source_artifact: Mapping[str, Any], evidence_target: str, unresolved_facet: str) -> dict[str, Any]:
    """Persist auditable sentence-level decisions against the retained source text."""
    text = str(source_artifact.get("retained_text") or "")
    target_terms = tuple(term for term in re.findall(r"[a-z0-9]+", evidence_target.lower()) if len(term) > 1)
    normalized_target = " ".join(target_terms)
    accepted: dict[str, dict[str, Any]] = {}
    examined: list[dict[str, Any]] = []
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text), start=1):
        clean = " ".join(sentence.split())
        lowered = clean.lower()
        boundary = f"sentence:{index}"
        if not clean:
            continue
        target_present = bool(target_terms) and (normalized_target in lowered or all(term in lowered for term in target_terms))
        if not target_present:
            examined.append({"boundary": boundary, "text": clean, "decision": "rejected", "reason": "target_terms_not_co_located"})
            continue
        if re.search(r"\b(is|are|means|refers to|defined as)\b", lowered):
            accepted.setdefault("definition", {"facet": "definition", "semantic_role": "definition", "evidence_target": evidence_target, "text": clean, "boundary": boundary, "reason": "target_and_explicit_definition_predicate"})
            examined.append({"boundary": boundary, "text": clean, "decision": "accepted", "facet": "definition", "reason": "target_and_explicit_definition_predicate"})
            continue
        if re.search(r"\b(only|when|if|under|within|unless|not|may|can)\b", lowered):
            accepted.setdefault("scope_limit", {"facet": "scope_limit", "semantic_role": "scope_or_limitation", "evidence_target": evidence_target, "text": clean, "boundary": boundary, "reason": "target_and_explicit_scope_predicate"})
            examined.append({"boundary": boundary, "text": clean, "decision": "accepted", "facet": "scope_limit", "reason": "target_and_explicit_scope_predicate"})
            continue
        examined.append({"boundary": boundary, "text": clean, "decision": "rejected", "reason": "target_present_but_no_supported_semantic_role"})
    payload = {
        "schema": "persistent_excerpt_mapping_v1",
        "source_artifact_id": str(source_artifact["artifact_id"]),
        "source_artifact_digest": str(source_artifact["artifact_digest"]),
        "selected_core_concept": evidence_target,
        "validated_aliases": (evidence_target,),
        "unresolved_facet": unresolved_facet,
        "mapper_version": "persistent_sentence_role_mapper_v2",
        "examined_sentences": tuple(examined),
        "accepted_excerpts": tuple(accepted[key] for key in sorted(accepted)),
        "rejected_excerpt_count": sum(item["decision"] == "rejected" for item in examined),
    }
    artifact_id = stable_id("persistent-development-excerpt-mapping", source_artifact["artifact_id"], evidence_target, unresolved_facet)
    return _write_immutable_artifact(runtime_root=runtime_root, directory=MAPPING_ARTIFACT_DIRECTORY, artifact_id=artifact_id, payload=payload)


def _goal_topic(goal: str) -> str:
    lowered = " ".join(goal.lower().split())
    lowered = re.sub(r"^(?:your goal today is to |goal(?: today)? is to |please )", "", lowered)
    lowered = re.sub(r"^(?:learn|study|understand|improve|strengthen|investigate)\s+", "", lowered)
    return " ".join(re.findall(r"[a-z0-9]+", lowered))[:120] or "unresolved_goal"


def _goal_record(goal: str, *, sequence: int) -> dict[str, Any]:
    topic = _goal_topic(goal)
    payload = {"goal": goal.strip(), "topic": topic, "sequence": sequence}
    return {
        "goal_id": stable_id("persistent-development-goal", _digest(payload)),
        "operator_goal": goal.strip(),
        "topic": topic,
        "state": "queued",
        "frontiers": ({"frontier_id": stable_id("persistent-development-frontier", topic), "label": topic, "state": "eligible", "rank": 1.0},),
        "work_nodes": _initial_work_nodes(topic, goal),
        "work_history": (),
        "evidence": (),
        "completion_criteria": {
            "requires_evidence": True,
            "requires_independent_evaluation_for_capability": True,
            "trusted_admission": "operator_authorized_only",
        },
        "budget": {"cycles_used": 0, "maximum_cycles": 12, "provider_calls": 0, "retrievals": 0},
        "provider_claims": (),
        "created_at": utc_now(),
    }


def _initial_work_nodes(topic: str, goal: str) -> tuple[dict[str, Any], ...]:
    """Derive renewable, domain-neutral learning work from a root goal."""
    operations = ("definition", "example", "counterexample", "contrast", "application", "exercise", "transfer", "uncertainty")
    return tuple({
        "node_id": stable_id("persistent-development-node", topic, operation),
        "label": f"{topic} {operation}", "operation": operation, "state": "queued",
        "parent_goal": goal, "depth": 1, "attempts": 0,
    } for operation in operations)


def _expand_work_nodes(goal: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Replenish a root from advisory prerequisite proposals without hard-coding a curriculum."""
    existing = tuple(dict(node) for node in (goal.get("work_nodes") or _initial_work_nodes(str(goal["topic"]), str(goal["operator_goal"]))))
    known = {str(node.get("label") or "").lower() for node in existing}
    additions: list[dict[str, Any]] = []
    for claim in (goal.get("provider_claims") or ()):
        advisory = dict(claim.get("raw_response") or {})
        for prerequisite in advisory.get("prerequisite_topics") or ():
            label = " ".join(str(prerequisite).split()).strip()
            if not label or label.lower() in known:
                continue
            additions.append({"node_id": stable_id("persistent-development-prerequisite", goal["goal_id"], label), "label": label, "operation": "prerequisite", "state": "queued", "parent_goal": goal["operator_goal"], "depth": 2, "attempts": 0, "origin": "provider_advisory_untrusted"})
            known.add(label.lower())
    # An exhausted route is evidence about a route, not proof that the root
    # objective is exhausted.  Generate a small, explicit revision frontier so
    # the scheduler can try a different facet without replaying the same node.
    revision_nodes = [node for node in existing if node.get("origin") == "branch_replenishment"]
    for node in existing:
        if len(revision_nodes) >= 4:
            break
        if str(node.get("state")) not in {"exhausted", "provisional_evaluated"} or int(node.get("depth") or 1) >= 3:
            continue
        label = f"{node.get('label', '')} evidence revision".strip()
        if not label or label.lower() in known:
            continue
        revision = {
            "node_id": stable_id("persistent-development-revision", goal["goal_id"], node["node_id"]),
            "label": label,
            "operation": "candidate_revision",
            "state": "queued",
            "parent_goal": goal["operator_goal"],
            "parent_node_id": node["node_id"],
            "depth": int(node.get("depth") or 1) + 1,
            "attempts": 0,
            "origin": "branch_replenishment",
            "reason": "prior_route_exhausted_or_provisional_requires_new_evidence_facet",
        }
        additions.append(revision)
        revision_nodes.append(revision)
        known.add(label.lower())
    return tuple((*existing, *additions))


def _provisional_candidate_from_retained(*, goal: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Create a scoped developmental artifact from retained propositions only."""
    summary = str(evidence.get("summary") or "").strip()
    concept_ids = tuple(str(item) for item in (evidence.get("concept_ids") or ()) if str(item))
    candidate = {
        "candidate_id": stable_id("persistent-retained-provisional-candidate", goal["goal_id"], goal.get("selected_node", {}).get("node_id"), concept_ids),
        "topic": str(goal["topic"]), "scoped_claim": f"provisional use of retained evidence for {goal['topic']}",
        "evidence_level": "developmental_candidate_provisional", "direct_provenance": {"kind": "retained_local_proposition", "concept_ids": concept_ids, "excerpt": summary, "excerpt_boundary": "retained_summary"},
        "derived_provenance": (), "unresolved_limits": ("retained evidence is non-trusted and requires source verification",),
        "trusted_admission": False, "capability_promotion": False,
    }
    candidate["candidate_digest"] = _digest(candidate)
    return candidate


def _default_provisional_evaluator(candidate: Mapping[str, Any], sealed_specs: Mapping[str, Any]) -> dict[str, Any]:
    """Independent structural evaluation: never grades provider teaching content."""
    direct = dict(candidate.get("direct_provenance") or {})
    passed = bool(candidate.get("scoped_claim")) and bool(direct.get("excerpt") or direct.get("excerpts"))
    return {
        "status": "provisional_competence_supported" if passed else "evidence_insufficient",
        "candidate_digest": candidate.get("candidate_digest"), "criteria_digest": sealed_specs["criteria_digest"],
        "unseen_use": "structural_scope_check_passed" if passed else "not_run", "transfer": "pending_independent_learner_execution",
        "evaluator_separated_from_teaching": True, "capability_promotion": False,
    }


def initialize_runtime(
    *,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    goals: Sequence[str] = (),
    provider_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or reopen a persistent runtime without duplicating submitted goals."""
    path = Path(runtime_root) / STATE_FILE
    if path.exists():
        state = _read(path)
        migrated = False
        goals_state = []
        for raw_goal in state.get("goals") or ():
            goal = dict(raw_goal)
            if not goal.get("work_nodes"):
                goal["work_nodes"] = _initial_work_nodes(str(goal.get("topic") or "unresolved_goal"), str(goal.get("operator_goal") or ""))
                migrated = True
            claims = []
            for raw_claim in goal.get("retrieval_claims") or ():
                claim = dict(raw_claim)
                if (
                    str(claim.get("claim_state") or "") == "completed"
                    and not claim.get("source_artifact_id")
                    and not claim.get("historical_disposition")
                ):
                    claim["historical_disposition"] = "historical_retrieval_completed_content_not_persisted_nonreviewable"
                    claim["reviewable_for_grounding"] = False
                    migrated = True
                claims.append(claim)
            goal["retrieval_claims"] = tuple(claims)
            goals_state.append(goal)
        if migrated:
            _checkpoint(state={**state, "goals": tuple(goals_state)}, runtime_root=runtime_root, reason="renewable_developmental_work_graph_migrated")
            state = _read(path)
        if goals:
            return submit_goals(state=state, runtime_root=runtime_root, goals=goals)
        return state
    records = tuple(_goal_record(goal, sequence=index) for index, goal in enumerate(goals, start=1) if goal.strip())
    state = {
        "runtime_id": stable_id("persistent-autonomous-development-runtime", _digest(tuple(goal["goal_id"] for goal in records))),
        "version": 1,
        "lifecycle_state": "idle" if not records else "ready",
        "goals": records,
        "active_goal_id": "",
        "active_work_item": {},
        "exhausted_fingerprints": (),
        "checkpoint_sequence": 0,
        "restart_generation": 0,
        "pause_reason": "",
        "terminal_reason": "",
        "provider_policy": {**DEFAULT_PROVIDER_POLICY, **dict(provider_policy or {})},
        "provider_calls": 0,
        "provider_spend_estimated_usd": 0.0,
        "consecutive_provider_calls": 0,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    _checkpoint(state=state, runtime_root=runtime_root, reason="runtime_initialized")
    return _read(path)


def _checkpoint(*, state: Mapping[str, Any], runtime_root: Path, reason: str) -> None:
    payload = dict(state)
    payload["checkpoint_sequence"] = int(payload.get("checkpoint_sequence") or 0) + 1
    payload["last_checkpoint"] = {"reason": reason, "at": utc_now()}
    payload["updated_at"] = utc_now()
    payload["state_digest"] = _digest({key: value for key, value in payload.items() if key not in {"updated_at", "state_digest"}})
    _atomic_write(Path(runtime_root) / STATE_FILE, payload)


def schedule_runtime_wake(
    *,
    state: Mapping[str, Any],
    runtime_root: Path,
    delay_seconds: int,
    reason: str = "bounded_cycle_cooldown",
) -> dict[str, Any]:
    """Persist the next autonomous transition before the worker sleeps."""
    current = dict(state)
    if current.get("lifecycle_state") in {"stopped", "paused_runtime", "waiting"}:
        return current
    next_goal = _select_goal(current)
    if next_goal is None:
        current["lifecycle_state"] = "waiting"
        current["terminal_reason"] = "no_eligible_goal"
        current["next_wake_at"] = ""
        current["next_wake_reason"] = ""
        current["next_action"] = {}
        _checkpoint(state=current, runtime_root=runtime_root, reason="runtime_waiting_without_eligible_work")
        return _read(Path(runtime_root) / STATE_FILE)
    delay = max(1, int(delay_seconds))
    current["next_wake_at"] = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
    current["next_wake_reason"] = reason
    current["next_action"] = {
        "goal_id": next_goal["goal_id"],
        "node_id": next_goal["selected_node"]["node_id"],
        "label": next_goal["selected_node"]["label"],
        "transition": "run_one_bounded_developmental_cycle",
    }
    _checkpoint(state=current, runtime_root=runtime_root, reason="next_autonomous_wake_scheduled")
    return _read(Path(runtime_root) / STATE_FILE)


def submit_goals(*, state: Mapping[str, Any], runtime_root: Path, goals: Sequence[str]) -> dict[str, Any]:
    """Append unique operator goals and leave all historical work intact."""
    current = dict(state)
    existing = {str(item["operator_goal"]).strip().lower() for item in current.get("goals") or ()}
    records = list(current.get("goals") or ())
    for goal in goals:
        if goal.strip() and goal.strip().lower() not in existing:
            records.append(_goal_record(goal, sequence=len(records) + 1))
            existing.add(goal.strip().lower())
    current["goals"] = tuple(records)
    if current.get("lifecycle_state") in {"idle", "waiting"} and records:
        current["lifecycle_state"] = "ready"
        current["terminal_reason"] = ""
    _checkpoint(state=current, runtime_root=runtime_root, reason="operator_goals_submitted")
    return _read(Path(runtime_root) / STATE_FILE)


def pause_runtime(*, state: Mapping[str, Any], runtime_root: Path, reason: str = "operator_requested_pause") -> dict[str, Any]:
    updated = {**state, "lifecycle_state": "paused_runtime", "pause_reason": reason}
    _checkpoint(state=updated, runtime_root=runtime_root, reason="runtime_paused")
    return _read(Path(runtime_root) / STATE_FILE)


def resume_runtime(*, state: Mapping[str, Any], runtime_root: Path) -> dict[str, Any]:
    updated = {**state, "lifecycle_state": "ready", "pause_reason": "", "restart_generation": int(state.get("restart_generation") or 0) + 1}
    _checkpoint(state=updated, runtime_root=runtime_root, reason="runtime_resumed")
    return _read(Path(runtime_root) / STATE_FILE)


def stop_runtime(*, state: Mapping[str, Any], runtime_root: Path) -> dict[str, Any]:
    updated = {**state, "lifecycle_state": "stopped", "terminal_reason": "operator_requested_clean_stop", "active_goal_id": "", "active_work_item": {}}
    _checkpoint(state=updated, runtime_root=runtime_root, reason="runtime_stopped")
    return _read(Path(runtime_root) / STATE_FILE)


def _select_goal(state: Mapping[str, Any]) -> dict[str, Any] | None:
    eligible = []
    for raw_goal in state.get("goals") or ():
        goal = dict(raw_goal)
        nodes = _expand_work_nodes(goal)
        node = next((dict(item) for item in nodes if str(item.get("state")) == "queued"), None)
        if node is None:
            continue
        eligible.append({**goal, "work_nodes": nodes, "selected_node": node, "topic": str(node["label"]), "frontiers": ({"frontier_id": node["node_id"], "label": node["label"], "state": "eligible", "rank": 1.0},)})
    eligible.sort(key=lambda item: (
        sum(int(node.get("attempts") or 0) for node in (item.get("work_nodes") or ())),
        str(item.get("goal_id") or ""),
    ))
    return eligible[0] if eligible else None


def _default_evidence_resolver(goal: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect retained evidence, then identify the next governed route.

    This is intentionally a route decision, not a claim that metadata or a
    provider answer has grounded the topic.
    """
    recalled = query_approved_concepts(str(goal["topic"]))
    fingerprint = _digest({"topic": goal["topic"], "search_query": recalled.get("search_query", goal["topic"]), "route": "rc2_reviewed_memory"})
    if recalled.get("matched"):
        return {
            "status": "retained_evidence_available",
            "fingerprint": fingerprint,
            "evidence": {
                "route": "rc2_reviewed_memory",
                "search_query": recalled.get("search_query", goal["topic"]),
                "concept_ids": tuple(str(item.get("concept_id") or "") for item in recalled.get("matches") or ()),
                "summary": str(recalled.get("answer") or ""),
                "non_trusted": True,
            },
        }
    return {
        "status": "public_evidence_required",
        "fingerprint": fingerprint,
        "evidence": {
            "route": "rc2_reviewed_memory",
            "search_query": goal["topic"],
            "reason": "no_retained_matching_evidence",
            "next_route": "governed_public_discovery_then_provider_if_unresolved",
        },
    }


def _default_public_evidence_resolver(goal: Mapping[str, Any], advisory: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run one bounded public metadata route before provider escalation.

    Metadata is deliberately not treated as grounded knowledge.  This gives a
    provider suggestion a concrete, independently checkable next action while
    leaving retrieval and evaluation to their existing governed owners.
    """
    from orchestration.runtime.governed_live_metadata_search import (
        compile_runtime_search_plan,
        execute_live_metadata_search,
    )

    query = str(goal["topic"])
    if advisory:
        suggested = tuple(str(item).strip() for item in (advisory.get("search_queries") or ()) if str(item).strip())
        if suggested:
            query = suggested[0]
    requirement = {
        "requirement_id": stable_id("persistent-development-public-requirement", goal["goal_id"], query),
        "label": str(goal["topic"]).replace(" ", "_"),
        "source_claims_required": ("definition", "scope_limit"),
        "operational_definition": f"foundational explanation and scope for {goal['topic']}",
    }
    plan = compile_runtime_search_plan(requirement=requirement, campaign_id=str(goal["goal_id"]), maximum_results=3)
    plan = {**plan, "primary_query": query}
    result = execute_live_metadata_search(plan=plan)
    topic_terms = tuple(term for term in re.findall(r"[a-z0-9]+", str(goal["topic"]).lower()) if len(term) > 2)
    candidates = tuple(
        {
            "candidate_id": stable_id("persistent-development-source-candidate", goal["goal_id"], item.get("title"), index),
            "title": str(item.get("title") or ""),
            # Discovery selects a narrow source concept.  It is evidence for a
            # scoped child candidate, not proof of every word in the parent
            # operator goal or its current exercise label.
            "evidence_target": str(item.get("title") or ""),
            "parent_goal_topic": str(goal["topic"]),
            "canonical_locator": f"https://en.wikipedia.org/wiki/{str(item.get('title') or '').replace(' ', '_')}",
            "source_class": "recognized_reference", "supports_labels": (str(goal["topic"]).replace(" ", "_"),),
            "provenance": "persistent_runtime_wikimedia_metadata", "content_type_hint": "text/html",
            "bounded_extract_permitted": True,
            "metadata_relevance": {"topic_terms": topic_terms, "matched_terms": tuple(term for term in topic_terms if term in f"{item.get('title') or ''} {item.get('snippet') or ''}".lower())},
        }
        for index, item in enumerate(result.get("raw_metadata") or (), start=1)
        if str(item.get("title") or "").strip()
        and (not topic_terms or any(term in f"{item.get('title') or ''} {item.get('snippet') or ''}".lower() for term in topic_terms))
    )
    return {
        "status": "public_evidence_unresolved",
        "fingerprint": _digest({"goal": goal["goal_id"], "query": query, "request": result.get("request_digest")}),
        "evidence": {
            "route": "bounded_public_metadata", "query": query, "search_plan_id": plan["search_plan_id"],
            "request_digest": result.get("request_digest", ""), "response_digest": result.get("raw_response_digest", ""),
            "candidate_count": len(candidates), "outcome": result.get("outcome", ""),
            "candidates": candidates,
            "reason": "metadata_requires_retrieval_and_claim_level_verification",
            "advisory_influenced": bool(advisory),
        },
    }


def _extract_source_facets(*, text: str, evidence_target: str) -> tuple[dict[str, Any], ...]:
    """Map exact sentences to a narrow selected target, never a whole goal label."""
    target_terms = tuple(term for term in re.findall(r"[a-z0-9]+", evidence_target.lower()) if len(term) > 1)
    normalized_target = " ".join(target_terms)
    definitions: dict[str, dict[str, Any]] = {}
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text)):
        clean = " ".join(sentence.split())
        lowered = clean.lower()
        # The target phrase (or all of its meaningful terms) must occur in the
        # same retained sentence.  This avoids lexical proximity while keeping
        # a source-backed child concept feasible for long parent goals.
        if not clean or not target_terms or not (normalized_target in lowered or all(term in lowered for term in target_terms)):
            continue
        if re.search(r"\b(is|are|means|refers to|defined as)\b", lowered):
            definitions.setdefault("definition", {"facet": "definition", "evidence_target": evidence_target, "text": clean, "boundary": f"sentence:{index + 1}"})
        if re.search(r"\b(only|when|if|under|within|unless|not|may|can)\b", lowered):
            definitions.setdefault("scope_limit", {"facet": "scope_limit", "evidence_target": evidence_target, "text": clean, "boundary": f"sentence:{index + 1}"})
    return tuple(definitions[key] for key in sorted(definitions))


def compile_persistent_generic_evaluator_authority(
    *, runtime_root: Path, runtime_id: str, goal: Mapping[str, Any], candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt one persisted grounded candidate into existing learning contracts.

    This compiles only the pending evaluator-authoring authority.  It does not
    create evaluator cases, execute a learner, write trusted knowledge, or
    promote a capability.
    """
    direct = dict(candidate.get("direct_provenance") or {})
    artifact_id = str(direct.get("source_artifact_id") or "")
    artifact_digest = str(direct.get("source_artifact_digest") or "")
    mapping_digest = str(direct.get("excerpt_mapping_digest") or "")
    if not artifact_id or not artifact_digest or not mapping_digest:
        raise ValueError("persistent_runtime_candidate_missing_reviewable_source_artifacts")
    mapping_path = Path(runtime_root) / MAPPING_ARTIFACT_DIRECTORY / f"{direct.get('excerpt_mapping_id')}.json"
    source_path = Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{artifact_id}.json"
    if not mapping_path.exists() or not source_path.exists():
        raise ValueError("persistent_runtime_candidate_artifact_reference_missing")
    source = _read(source_path)
    mapping = _read(mapping_path)
    excerpts = tuple(dict(item) for item in mapping.get("accepted_excerpts") or ())
    if {str(item.get("facet") or "") for item in excerpts} < {"definition", "scope_limit"}:
        raise ValueError("persistent_runtime_candidate_missing_grounded_facets")
    topic = str(candidate.get("topic") or "persistent_source_concept")
    capability = f"explain_and_apply_{_goal_topic(topic).replace(' ', '_')}"
    mission_payload = {
        "mission_id": stable_id("persistent-developmental-mission", runtime_id, candidate["candidate_id"], candidate["candidate_digest"]),
        "operator_instruction": f"Learn the scoped source-grounded concept {topic}.",
        "mission_type": "developmental_learning", "domain": "general_reasoning", "topic": topic,
        "mission_mode": "persistent_candidate_handoff", "primary_capability_target": capability,
        "authority_class": "pending_isolated_evaluator_authority", "allowed_resource_classes": ("persisted_bounded_source_artifact",),
        "excluded_resource_classes": ("provider_without_approval", "trusted_admission", "capability_promotion"),
        "external_resource_policy": "no_additional_retrieval", "provider_policy": "isolated_evaluator_only_when_approved",
        "web_policy": "no_additional_retrieval", "local_model_policy": "not_authorized", "sandbox_policy": "no_execution_required",
        "tracked_application_policy": "operator_approval_required", "session_budget": 1, "attempt_budget": 1,
        "uncertainty": "bounded_to_persisted_source_excerpt_scope", "ambiguity_status": "scoped_source_candidate",
        "operator_decision_required": True, "created_at": utc_now(), "protocol": "developmental_learning_mission_v1", "version": "1",
    }
    mission = DevelopmentalMissionContract(contract_digest=_digest(mission_payload), **mission_payload)
    learner_bundle = {
        "bundle_id": stable_id("persistent-learner-visible-bundle", candidate["candidate_digest"], artifact_digest, mapping_digest),
        "candidate_id": candidate["candidate_id"], "study_resources": ({
            "resource_id": artifact_id, "topic": topic, "supports_dimensions": (capability,),
            "learner_visible_excerpts": tuple({"text": item["text"], "boundary": item["boundary"]} for item in excerpts),
            "source_artifact_id": artifact_id, "source_artifact_digest": artifact_digest,
            "excerpt_mapping_digest": mapping_digest,
        },),
        "scope_limits": tuple(candidate.get("unresolved_limits") or ()),
    }
    learner_bundle["bundle_digest"] = _digest(learner_bundle)
    subgoal_payload = {
        "subgoal_id": stable_id("persistent-learning-subgoal", mission.mission_id, candidate["candidate_digest"]),
        "mission_id": mission.mission_id, "source_gap_id": stable_id("persistent-source-grounding-gap", candidate["candidate_id"]),
        "topic": topic, "frontier_rank": 1.0, "selection_reason": "one source-grounded scoped candidate is ready for isolated evaluation authority",
        "capability_target": capability, "measurable_objective": f"Explain and apply the scoped definition of {topic} from learner-visible excerpts.",
        "baseline": 0.0, "success_threshold": 1.0, "prerequisites": (), "study_resource_ids": (artifact_id,),
        "attempt_type": "guided_study_attempt", "practice_specification": "Use only the learner-visible persisted excerpts.",
        "control_case_ids": (), "held_out_policy": "sealed cases remain unavailable until evaluator authority is fulfilled",
        "adversarial_policy": "sealed evaluator authoring defines adversarial cases", "evaluation_method": "isolated_sealed_evaluator_required",
        "attempt_budget": 1, "resource_budget": 1, "completion_classification": "evaluation_required",
        "next_step_policy": "await_pending_isolated_evaluator_authority", "authority_state": "pending_operator_evaluator_authority",
    }
    subgoal = LearningSubgoal(**subgoal_payload)
    requirement = {
        "requirement_id": stable_id("persistent-evaluator-requirement", candidate["candidate_digest"]), "mission_id": mission.mission_id,
        "topic": topic, "target_capability": capability, "assessment_dimension": capability,
        "target_behavior": subgoal.measurable_objective, "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"], "source_artifact_digest": artifact_digest,
        "excerpt_mapping_digest": mapping_digest, "learner_visible_bundle_digest": learner_bundle["bundle_digest"],
        "scope_limits": tuple(candidate.get("unresolved_limits") or ()),
    }
    packet = compile_isolated_evaluator_authoring_request(
        mission_id=mission.mission_id, requirement=requirement, provider="openai", model="gpt-4.1-mini",
    )
    request = {
        "request_id": packet["request_id"], "request_kind": "persistent_generic_isolated_evaluator_authoring",
        "status": "pending_operator_approval", "recommended_approval_token": "approve_persistent_generic_evaluator_authoring",
        "candidate_id": candidate["candidate_id"], "candidate_digest": candidate["candidate_digest"],
        "source_artifact_id": artifact_id, "source_artifact_digest": artifact_digest, "excerpt_mapping_digest": mapping_digest,
        "mission_contract": mission.as_dict(), "learning_subgoal": subgoal.as_dict(), "learner_visible_bundle": learner_bundle,
        "mission_contract_digest": mission.contract_digest, "learning_subgoal_digest": _digest(subgoal.as_dict()),
        "input_packet": packet["input_packet"], "prompt_digest": packet["prompt_digest"], "provider": packet["provider"], "model": packet["model"],
        "authority_limits": ("no_trusted_admission", "no_capability_promotion", "no_source_mutation", "no_learner_execution", "no_evaluation_execution", "no_unrelated_provider_calls", "no_additional_candidates"),
        "created_at": utc_now(),
    }
    return _write_immutable_artifact(
        runtime_root=runtime_root, directory=EVALUATOR_AUTHORITY_DIRECTORY, artifact_id=str(packet["request_id"]), payload=request,
    )


def recover_historical_retrieval_with_persistence(
    *, state: Mapping[str, Any], runtime_root: Path, historical_claim_id: str, evidence_target: str,
    retrieval_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one explicit persistence-enabled recovery without rewriting history.

    A historical digest-only claim remains nonreviewable.  This function creates
    a separate one-use claim for the same approved locator solely to retain the
    bounded representation that the earlier runtime discarded.
    """
    current = dict(state)
    located: tuple[int, dict[str, Any], dict[str, Any]] | None = None
    for goal_index, raw_goal in enumerate(current.get("goals") or ()):
        goal = dict(raw_goal)
        for raw_claim in goal.get("retrieval_claims") or ():
            claim = dict(raw_claim)
            if str(claim.get("claim_id") or "") == historical_claim_id:
                located = (goal_index, goal, claim)
                break
        if located:
            break
    if located is None:
        raise ValueError("persistent_runtime_historical_claim_not_found")
    goal_index, goal, historical = located
    if str(historical.get("claim_state") or "") != "completed" or historical.get("source_artifact_id"):
        raise ValueError("persistent_runtime_historical_claim_not_digest_only")
    recovery_fingerprint = _digest({
        "historical_claim_id": historical_claim_id, "locator": historical.get("canonical_locator"),
        "strategy": "persistence_enabled_bounded_recovery_v1", "evidence_target": evidence_target,
    })
    prior_claims = tuple(goal.get("retrieval_claims") or ())
    if any(str(item.get("recovery_fingerprint") or "") == recovery_fingerprint for item in prior_claims):
        raise ValueError("persistent_runtime_persistence_recovery_replay_suppressed")
    claim = {
        "claim_id": stable_id("persistent-development-persistence-recovery", current["runtime_id"], historical_claim_id, recovery_fingerprint),
        "goal_id": goal["goal_id"], "frontier_id": stable_id("persistent-development-recovery-frontier", historical_claim_id),
        "candidate_id": stable_id("persistent-development-recovery-candidate", historical_claim_id, evidence_target),
        "canonical_locator": str(historical["canonical_locator"]), "claim_state": "dispatching", "attempt_count": 1,
        "created_at": utc_now(), "recovery_fingerprint": recovery_fingerprint,
        "recovery_reason": "historical_completed_retrieval_content_not_persisted", "parent_historical_claim_id": historical_claim_id,
        "extraction_strategy": "persistence_enabled_bounded_recovery_v1", "extraction_bounds": {"representation": "existing_bounded_summary"},
    }
    updated_goal = {**goal, "retrieval_claims": tuple((*prior_claims, claim))}
    goals = list(current.get("goals") or ()); goals[goal_index] = updated_goal
    _checkpoint(state={**current, "goals": tuple(goals), "active_goal_id": goal["goal_id"], "active_work_item": {"goal_id": goal["goal_id"], "state": "persistence_enabled_retrieval_dispatching", "claim_id": claim["claim_id"]}}, runtime_root=runtime_root, reason="persistence_enabled_retrieval_claim_persisted_before_dispatch")
    candidate_request = {
        "canonical_locator": claim["canonical_locator"], "bounded_extract_permitted": True,
        "extraction_strategy": "wikipedia_bounded_summary", "evidence_target": evidence_target,
    }
    try:
        executor = retrieval_executor or _default_retrieval_executor
        retrieval = dict(executor(candidate_request))
        content = str(retrieval.pop("content_text") or "")
        source_artifact = _persist_source_artifact(runtime_root=runtime_root, runtime_id=str(current["runtime_id"]), goal=goal, claim=claim, retrieval=retrieval, retained_text=content)
        mapping_artifact = _map_persisted_source_artifact(runtime_root=runtime_root, source_artifact=source_artifact, evidence_target=evidence_target, unresolved_facet="definition_and_scope_limit")
        facets = tuple(dict(item) for item in mapping_artifact.get("accepted_excerpts") or ())
        completed = {**claim, "claim_state": "completed", "completed_at": utc_now(), "source_digest": source_artifact["source_digest"], "extraction_digest": source_artifact["extraction_digest"], "source_artifact_id": source_artifact["artifact_id"], "source_artifact_path": source_artifact["artifact_path"], "source_artifact_digest": source_artifact["artifact_digest"], "excerpt_mapping_id": mapping_artifact["artifact_id"], "excerpt_mapping_path": mapping_artifact["artifact_path"], "excerpt_mapping_digest": mapping_artifact["artifact_digest"], "mapped_excerpt_count": len(facets)}
        candidate: dict[str, Any] = {}
        authority: dict[str, Any] = {}
        if {item.get("facet") for item in facets} >= {"definition", "scope_limit"}:
            candidate = {
                "candidate_id": stable_id("persistent-development-candidate", goal["goal_id"], evidence_target, source_artifact["source_digest"]), "candidate_version": 1,
                "topic": evidence_target, "parent_goal_topic": goal["topic"], "scoped_claim": f"source-grounded scoped claim about {evidence_target}",
                "target_behavior": f"explain a scoped definition of {evidence_target} using retained excerpts", "required_evidence_facets": ("definition", "scope_limit"),
                "direct_provenance": {"retrieval_claim_id": completed["claim_id"], "source_digest": source_artifact["source_digest"], "extraction_digest": source_artifact["extraction_digest"], "source_artifact_id": source_artifact["artifact_id"], "source_artifact_digest": source_artifact["artifact_digest"], "excerpt_mapping_id": mapping_artifact["artifact_id"], "excerpt_mapping_digest": mapping_artifact["artifact_digest"], "evidence_target": evidence_target, "excerpt_references": tuple({"facet": item["facet"], "boundary": item["boundary"]} for item in facets)},
                "derived_provenance": (), "supported_facets": tuple(item["facet"] for item in facets), "unresolved_facets": (),
                "unresolved_limits": ("supports a scoped source concept; parent-goal transfer remains unassessed",), "trusted_admission": False, "capability_promotion": False,
            }
            candidate["candidate_digest"] = _digest(candidate)
        updated_goal = {**goal, "retrieval_claims": tuple((*prior_claims, completed))}
        if candidate:
            updated_goal["candidate_versions"] = tuple(updated_goal.get("candidate_versions") or ()) + (candidate,)
            authority = compile_persistent_generic_evaluator_authority(runtime_root=runtime_root, runtime_id=str(current["runtime_id"]), goal=updated_goal, candidate=candidate)
            updated_goal["pending_evaluator_authority"] = {"request_id": authority["request_id"], "status": authority["status"], "artifact_path": authority["artifact_path"]}
        result = {"status": "source_grounded_and_evaluator_authority_ready" if candidate else "source_artifact_persisted_mapping_insufficient", "claim": completed, "source_artifact": source_artifact, "mapping_artifact": mapping_artifact, "candidate": candidate, "authority": authority}
    except Exception as exc:
        completed = {**claim, "claim_state": "failed", "completed_at": utc_now(), "failure_reason": f"{type(exc).__name__}:{str(exc)[:240]}"}
        updated_goal = {**goal, "retrieval_claims": tuple((*prior_claims, completed))}
        result = {"status": "persistence_recovery_failed", "claim": completed, "reason": completed["failure_reason"]}
    goals = list(current.get("goals") or ()); goals[goal_index] = updated_goal
    final = {**current, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}
    _checkpoint(state=final, runtime_root=runtime_root, reason="persistence_enabled_retrieval_recovery_completed")
    return _read(Path(runtime_root) / STATE_FILE), result


def consume_persistent_generic_evaluator_authority(
    *, runtime_root: Path, request_id: str, approval_token: str,
    provider_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Consume one persistent evaluator authority and stop after sealed validation."""
    if approval_token != "approve_persistent_generic_evaluator_authoring":
        raise ValueError("persistent_runtime_evaluator_authority_response_invalid")
    authority_path = Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / f"{request_id}.json"
    authority = _read(authority_path)
    if str(authority.get("status") or "") != "pending_operator_approval":
        raise ValueError("persistent_runtime_evaluator_authority_not_pending")
    state = initialize_runtime(runtime_root=runtime_root)
    candidate = next((dict(item) for goal in state.get("goals") or () for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    if not candidate or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or ""):
        raise ValueError("persistent_runtime_evaluator_candidate_digest_mismatch")
    direct = dict(candidate.get("direct_provenance") or {})
    if (
        str(direct.get("source_artifact_digest") or "") != str(authority.get("source_artifact_digest") or "")
        or str(direct.get("excerpt_mapping_digest") or "") != str(authority.get("excerpt_mapping_digest") or "")
    ):
        raise ValueError("persistent_runtime_evaluator_evidence_digest_mismatch")
    claim_id = stable_id("persistent-isolated-evaluator-execution-claim", request_id, authority["artifact_digest"])
    claim = _write_immutable_artifact(
        runtime_root=runtime_root, directory=f"{EVALUATOR_AUTHORITY_DIRECTORY}/execution_claims", artifact_id=claim_id,
        payload={
            "schema": "persistent_isolated_evaluator_execution_claim_v1", "request_id": request_id,
            "authority_digest": authority["artifact_digest"], "candidate_digest": authority["candidate_digest"],
            "claim_state": "dispatching", "attempt_count": 1, "approved_at": utc_now(),
        },
    )
    for index, raw_goal in enumerate(state.get("goals") or ()):
        goal = dict(raw_goal)
        pending = dict(goal.get("pending_evaluator_authority") or {})
        if str(pending.get("request_id") or "") == request_id:
            goal["pending_evaluator_authority"] = {**pending, "status": "consumed_dispatching", "execution_claim_id": claim_id}
            goals = list(state.get("goals") or ()); goals[index] = goal
            _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": goal["goal_id"], "active_work_item": {"goal_id": goal["goal_id"], "state": "isolated_evaluator_authoring_dispatching", "claim_id": claim_id}}, runtime_root=runtime_root, reason="persistent_isolated_evaluator_execution_claim_persisted_before_dispatch")
            state = _read(Path(runtime_root) / STATE_FILE)
            break
    packet = {
        "provider": authority["provider"], "model": authority["model"], "system_prompt": "You author an isolated evaluation package. Return JSON only.",
        "user_prompt": json.dumps(authority["input_packet"], sort_keys=True, separators=(",", ":")),
        "output_contract": {"native_json_schema": authority["input_packet"].get("native_json_schema") or compile_isolated_evaluator_authoring_request(mission_id=authority["mission_contract"]["mission_id"], requirement={"topic": authority["mission_contract"]["topic"], "target_capability": authority["learning_subgoal"]["capability_target"], "target_behavior": authority["learning_subgoal"]["measurable_objective"]}, provider=authority["provider"], model=authority["model"])["output_contract"]["native_json_schema"]},
    }
    executor = provider_executor or _default_persistent_evaluator_authoring_executor
    result = dict(executor(packet))
    raw = result.get("raw_response")
    validation = validate_provider_authored_evaluator_response({
        "request_id": request_id, "protocol": str(authority["input_packet"].get("protocol") or ""), "provider": authority["provider"], "model": authority["model"],
        "input_packet": authority["input_packet"], "input_packet_digest": _digest({key: value for key, value in authority["input_packet"].items() if key != "authoring_provenance_required"}),
    }, raw or {}) if result.get("status") == "completed" else {"accepted": False, "errors": (str(result.get("reason") or "provider_execution_failed"),), "sealed_package": {}, "response_digest": _digest({"reason": result.get("reason") or ""})}
    outcome = _write_immutable_artifact(
        runtime_root=runtime_root, directory=f"{EVALUATOR_AUTHORITY_DIRECTORY}/execution_results", artifact_id=stable_id("persistent-isolated-evaluator-execution-result", claim_id, validation["response_digest"]),
        payload={
            "schema": "persistent_isolated_evaluator_execution_result_v1", "execution_claim_id": claim_id, "request_id": request_id,
            "claim_state": "completed" if validation["accepted"] else "invalid", "response_digest": validation["response_digest"],
            "validation_errors": tuple(validation.get("errors") or ()), "sealed_package": validation.get("sealed_package") if validation["accepted"] else {},
            "provider_usage": dict(result.get("usage") or {}), "completed_at": utc_now(),
        },
    )
    state = initialize_runtime(runtime_root=runtime_root)
    for index, raw_goal in enumerate(state.get("goals") or ()):
        goal = dict(raw_goal); pending = dict(goal.get("pending_evaluator_authority") or {})
        if str(pending.get("request_id") or "") == request_id:
            goal["pending_evaluator_authority"] = {**pending, "status": "sealed_package_ready" if validation["accepted"] else "provider_result_invalid", "execution_claim_id": claim_id, "result_artifact_id": outcome["artifact_id"]}
            goals = list(state.get("goals") or ()); goals[index] = goal
            _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}, runtime_root=runtime_root, reason="persistent_isolated_evaluator_authoring_terminal_without_learner_execution")
            break
    return {"execution_claim": claim, "result": outcome, "validation": validation}


def _default_persistent_evaluator_authoring_executor(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Delegate the one approved strict-schema call to the configured evaluator lane."""
    from orchestration.runtime.v16_env import load_delta_evaluator_env, parse_env_file
    from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport

    repository_root = Path(__file__).resolve().parents[2]
    config = load_delta_evaluator_env(repository_root / ".env.local")
    if not config.live_call_permitted or str(config.provider).lower() != str(packet["provider"]).lower() or str(config.model) != str(packet["model"]):
        return {"status": "failed", "reason": "provider_configuration_not_permitted_or_does_not_match_approved_packet"}
    api_key = os.environ.get("DELTA_EVALUATOR_API_KEY") or parse_env_file(repository_root / ".env.local").get("DELTA_EVALUATOR_API_KEY", "")
    try:
        response = _default_transport(
            config.endpoint or "https://api.openai.com/v1/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            {"model": packet["model"], "temperature": 0, "max_tokens": 5000, "response_format": {"type": "json_schema", "json_schema": {"name": "persistent_isolated_evaluator_authoring", "strict": True, "schema": packet["output_contract"]["native_json_schema"]}}, "messages": ({"role": "system", "content": packet["system_prompt"]}, {"role": "user", "content": packet["user_prompt"]})}, 45,
        )
        choices = response.get("choices") if isinstance(response, Mapping) else ()
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
        return {"status": "completed", "raw_response": json.loads(str(message.get("content") or "{}")), "usage": dict(response.get("usage") or {})}
    except Exception as exc:
        return {"status": "failed", "reason": f"{type(exc).__name__}:{str(exc)[:240]}"}


def _persistent_disposition(*, candidate: Mapping[str, Any], evaluation: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """Classify from observable change surface, never a candidate self-label."""
    properties = dict(candidate.get("proposed_change_properties") or {})
    sensitive = any(bool(properties.get(key)) for key in ("filesystem_mutation", "network_authority_expansion", "provider_authority_expansion", "trusted_state_change", "credential_or_external_system", "governance_change", "irreversible"))
    functional = any(bool(properties.get(key)) for key in ("runtime_mutation", "source_mutation", "tool_attachment", "module_attachment", "routing_change", "execution_workflow_change"))
    if not bool(evaluation.get("promotion_eligible")):
        return ("candidate_revision_required", {"evaluation_passed": False, "sensitive": sensitive, "functional": functional, "reason": "sealed_behavioral_evaluation_did_not_pass"})
    if sensitive:
        return ("sensitive_capability_review_required", {"evaluation_passed": True, "sensitive": True, "functional": functional, "reason": "observable_sensitive_change_surface"})
    if functional:
        return ("functional_capability_proposal", {"evaluation_passed": True, "sensitive": False, "functional": True, "reason": "observable_runtime_or_tool_change_surface"})
    return ("conceptual_knowledge_update", {"evaluation_passed": True, "sensitive": False, "functional": False, "reason": "scoped_conceptual_behavior_without_runtime_or_authority_mutation"})


def compile_sealed_case_execution_view(*, sealed_package: Mapping[str, Any], sealed_package_digest: str) -> dict[str, Any]:
    """Create the sole read-only V3-to-learning selector compatibility boundary."""
    cases = []
    for raw in sealed_package.get("sealed_evaluation_cases") or ():
        case = dict(raw)
        target, dimension = str(case.get("target_capability") or ""), str(case.get("capability_dimension") or "")
        if target and dimension and target != dimension:
            raise ValueError("sealed_case_execution_capability_conflict")
        if not target and not dimension:
            raise ValueError("sealed_case_execution_capability_missing")
        cases.append({**case, "capability_dimension": target or dimension})
    payload = {"schema": "sealed_case_execution_view_v1", "sealed_package_id": sealed_package.get("sealed_package_id"), "sealed_package_digest": sealed_package_digest, "execution_contract_version": sealed_package.get("execution_contract_version"), "sealed_evaluation_cases": tuple(cases)}
    return {**payload, "execution_view_digest": _digest(payload)}


def compile_persistent_sealed_learner_retry_authority(*, runtime_root: Path, request_id: str, auto_approve: bool = False) -> dict[str, Any]:
    """Compile one digest-bound retry after a terminal schema-mismatch attempt."""
    state = initialize_runtime(runtime_root=runtime_root)
    goal = next((dict(item) for item in state.get("goals") or () if str(dict(item.get("pending_evaluator_authority") or {}).get("request_id") or "") == request_id), None)
    if goal is None:
        raise ValueError("persistent_runtime_retry_goal_missing")
    pending = dict(goal["pending_evaluator_authority"])
    prior = next((dict(item) for item in reversed(tuple(goal.get("learning_attempts") or ())) if str(item.get("status") or "") == "completed"), None)
    if prior is None:
        raise ValueError("persistent_runtime_retry_prior_attempt_missing")
    result = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / "execution_results" / f"{pending['result_artifact_id']}.json")
    authority = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / f"{request_id}.json")
    view = compile_sealed_case_execution_view(sealed_package=dict(result["sealed_package"]), sealed_package_digest=str(result["artifact_digest"]))
    view_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="sealed_case_execution_views", artifact_id=stable_id("sealed-case-execution-view", result["artifact_digest"]), payload=view)
    retry_id = stable_id("persistent-sealed-learner-retry-authority", authority["candidate_digest"], view_artifact["artifact_digest"], prior["claim_id"])
    retry = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_retry_authorities", artifact_id=retry_id, payload={"schema": "persistent_sealed_learner_retry_authority_v1", "request_id": retry_id, "status": "approved_pending_execution" if auto_approve else "pending_operator_approval", "recommended_approval_token": "approve_persistent_sealed_learner_retry", "candidate_id": authority["candidate_id"], "candidate_digest": authority["candidate_digest"], "sealed_package_id": result["sealed_package"].get("sealed_package_id"), "sealed_package_digest": result["artifact_digest"], "execution_view_digest": view_artifact["artifact_digest"], "mission_contract_digest": authority["mission_contract_digest"], "learning_subgoal_digest": authority["learning_subgoal_digest"], "prior_failed_attempt_claim_id": prior["claim_id"], "retry_reason": "sealed_case_execution_schema_mismatch", "maximum_learner_attempts": 1, "maximum_independent_evaluations": 1, "prohibited_actions": ("evaluator_authoring_provider_call", "evaluator_criteria_change", "additional_candidates", "trusted_admission", "capability_promotion", "automatic_application", "overnight_worker_restart"), "created_at": utc_now()})
    return {"execution_view": view_artifact, "retry_authority": retry}


def execute_persistent_sealed_evaluation(*, runtime_root: Path, request_id: str, retry_authority_id: str = "") -> dict[str, Any]:
    """Run one persisted learner/evaluator cycle and stop at its disposition."""
    authority = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / f"{request_id}.json")
    state = initialize_runtime(runtime_root=runtime_root)
    goal = next((dict(item) for item in state.get("goals") or () if str(dict(item.get("pending_evaluator_authority") or {}).get("request_id") or "") == request_id), None)
    allowed_statuses = {"sealed_package_ready"} if not retry_authority_id else {"sealed_package_ready", "behavioral_evaluation_complete"}
    if goal is None or str(dict(goal.get("pending_evaluator_authority") or {}).get("status") or "") not in allowed_statuses:
        raise ValueError("persistent_runtime_sealed_package_not_ready")
    pending = dict(goal["pending_evaluator_authority"])
    result = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / "execution_results" / f"{pending['result_artifact_id']}.json")
    package = dict(result.get("sealed_package") or {})
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    if not candidate or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or "") or str(result.get("claim_state") or "") != "completed":
        raise ValueError("persistent_runtime_sealed_package_binding_invalid")
    direct = dict(candidate.get("direct_provenance") or {})
    if str(direct.get("source_artifact_digest") or "") != str(authority.get("source_artifact_digest") or "") or str(direct.get("excerpt_mapping_digest") or "") != str(authority.get("excerpt_mapping_digest") or ""):
        raise ValueError("persistent_runtime_sealed_package_evidence_binding_invalid")
    retry = {}
    if retry_authority_id:
        retry = _read(Path(runtime_root) / "learning_retry_authorities" / f"{retry_authority_id}.json")
        if str(retry.get("status") or "") != "approved_pending_execution":
            raise ValueError("persistent_runtime_learner_retry_not_approved")
        view = _read(Path(runtime_root) / "sealed_case_execution_views" / f"sealed-case-execution-view-81606e801addb731.json")
        if str(view.get("artifact_digest") or "") != str(retry.get("execution_view_digest") or ""):
            raise ValueError("persistent_runtime_execution_view_digest_mismatch")
        package_execution_view = dict(view)
    else:
        package_execution_view = package
    learner_bundle = dict(authority["learner_visible_bundle"])
    resources = []
    for raw in learner_bundle.get("study_resources") or ():
        resource = dict(raw)
        source_path = Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{resource.get('source_artifact_id')}.json"
        source_text = str(_read(source_path).get("retained_text") or "") if source_path.exists() else ""
        resource["study_facts"] = tuple(item.strip() for item in re.split(r"(?<=[.!?])\s+", source_text) if item.strip())
        resource["study_components"] = tuple(str(item.get("text") or "") for item in resource.get("learner_visible_excerpts") or ())
        resources.append(resource)
    retained_bundle = {"study_resources": tuple(resources), "sealed_evaluation_cases": tuple(package_execution_view.get("sealed_evaluation_cases") or ()), "execution_contract_version": package.get("execution_contract_version"), "independent_evaluator": dict(package.get("independent_evaluator") or {}), "active_sealed_case_ids": tuple(str(case.get("case_id") or "") for case in package_execution_view.get("sealed_evaluation_cases") or ())}
    if any(any(key in str(case.get("learner_view") or {}) for key in ("answer_key", "scoring_rule", "pass_threshold", "rubric")) for case in retained_bundle["sealed_evaluation_cases"]):
        raise ValueError("persistent_runtime_evaluator_only_field_leaked_to_learner")
    subgoal = LearningSubgoal(**dict(authority["learning_subgoal"]))
    claim_id = stable_id("persistent-learning-attempt-claim", state["runtime_id"], candidate["candidate_digest"], result["artifact_digest"], retry_authority_id)
    claim = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_attempt_claims", artifact_id=claim_id, payload={"schema": "persistent_learning_attempt_claim_v1", "runtime_id": state["runtime_id"], "goal_id": goal["goal_id"], "work_node_id": str(next((node.get("node_id") for node in goal.get("work_nodes") or () if node.get("state") == "queued"), "")), "candidate_id": candidate["candidate_id"], "candidate_digest": candidate["candidate_digest"], "mission_id": subgoal.mission_id, "learning_subgoal_id": subgoal.subgoal_id, "sealed_package_id": package.get("sealed_package_id"), "sealed_package_digest": result["artifact_digest"], "learner_visible_bundle_digest": learner_bundle["bundle_digest"], "claim_state": "dispatching", "attempt_count": 1, "created_at": utc_now()})
    from orchestration.runtime.developmental_learning import execute_learning_attempt, evaluate_learning_attempt
    attempt = execute_learning_attempt(subgoal, retained_bundle)
    evaluation = evaluate_learning_attempt(subgoal, attempt, retained_bundle)
    attempt_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_attempts", artifact_id=attempt.attempt_id, payload={"schema": "persistent_learning_attempt_v1", "claim_id": claim_id, "learner_visible_tasks": tuple({key: value for key, value in item.items() if key not in {"candidate_response", "candidate_final_answer", "candidate_explanation"}} for item in attempt.task_records), "attempt": attempt.as_dict(), "response_digest": attempt.candidate_digest, "completed_at": utc_now()})
    evaluation_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_evaluations", artifact_id=evaluation.evaluation_id, payload={"schema": "persistent_learning_evaluation_v1", "claim_id": claim_id, "sealed_package_digest": result["artifact_digest"], "learner_response_digest": attempt.candidate_digest, "evaluation": evaluation.as_dict(), "completed_at": utc_now()})
    disposition, reasons = _persistent_disposition(candidate=candidate, evaluation=evaluation.as_dict())
    updated_goal = {**goal, "learning_attempts": tuple(goal.get("learning_attempts") or ()) + ({"claim_id": claim_id, "attempt_id": attempt.attempt_id, "artifact_id": attempt_artifact["artifact_id"], "status": "completed"},), "behavioral_evaluations": tuple(goal.get("behavioral_evaluations") or ()) + ({"evaluation_id": evaluation.evaluation_id, "artifact_id": evaluation_artifact["artifact_id"], "disposition": evaluation.disposition},), "post_evaluation_disposition": {"tier": disposition, "reasons": reasons, "evaluation_id": evaluation.evaluation_id}, "pending_evaluator_authority": {**pending, "status": "behavioral_evaluation_complete", "learning_attempt_claim_id": claim_id, "learning_attempt_id": attempt.attempt_id, "evaluation_id": evaluation.evaluation_id}}
    if disposition == "conceptual_knowledge_update":
        updated_goal["scoped_developmental_competence"] = {"candidate_id": candidate["candidate_id"], "evaluation_id": evaluation.evaluation_id, "scope_limits": candidate.get("unresolved_limits") or (), "capability_promotion": False, "trusted_admission": False}
    elif disposition == "candidate_revision_required":
        updated_goal["work_nodes"] = _expand_work_nodes({**updated_goal, "work_nodes": tuple({**dict(node), "state": "exhausted" if str(node.get("node_id")) == claim.get("work_node_id") else node.get("state")} for node in updated_goal.get("work_nodes") or ())})
    goals = [updated_goal if item.get("goal_id") == goal["goal_id"] else item for item in state.get("goals") or ()]
    _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}, runtime_root=runtime_root, reason="persistent_sealed_evaluation_and_disposition_completed")
    return {"claim": claim, "attempt": attempt.as_dict(), "evaluation": evaluation.as_dict(), "attempt_artifact": attempt_artifact, "evaluation_artifact": evaluation_artifact, "disposition": disposition, "disposition_reasons": reasons, "retry_authority": retry}


def _default_retrieval_executor(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from orchestration.runtime.autonomous_live_evidence_transport import retrieve_candidate_via_existing_governed_transport
    return dict(retrieve_candidate_via_existing_governed_transport(candidate))


def _source_is_globally_terminal(claim: Mapping[str, Any]) -> bool:
    """Only source-invalid outcomes suppress every bounded strategy."""
    reason = str(claim.get("failure_reason") or "").lower()
    return any(marker in reason for marker in (
        "source_identity_mismatch", "malicious", "hostile_content", "locator_mismatch",
        "content_type_rejected", "redirect_rejected", "source_invalid",
    ))


def _select_retrieval_candidate(
    *,
    candidates: Sequence[Mapping[str, Any]],
    prior_claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Choose one non-replayed strategy; locator identity is not strategy identity."""
    for raw_candidate in candidates:
        candidate = dict(raw_candidate)
        locator = str(candidate.get("canonical_locator") or "")
        matching = tuple(dict(claim) for claim in prior_claims if str(claim.get("canonical_locator") or "") == locator)
        if any(_source_is_globally_terminal(claim) for claim in matching):
            continue
        strategies = {str(claim.get("extraction_strategy") or "full_page_rc8") for claim in matching}
        if not matching:
            return {**candidate, "extraction_strategy": "full_page_rc8", "unresolved_facet": "definition_and_scope_limit"}
        has_budget_failure = any("content_budget_exhausted" in str(claim.get("failure_reason") or "") for claim in matching)
        host = (urlparse(locator).hostname or "").lower()
        if (
            has_budget_failure
            and host == "en.wikipedia.org"
            and bool(candidate.get("bounded_extract_permitted"))
            and "wikipedia_bounded_summary" not in strategies
        ):
            parent = next(claim for claim in reversed(matching) if "content_budget_exhausted" in str(claim.get("failure_reason") or ""))
            return {
                **candidate,
                "extraction_strategy": "wikipedia_bounded_summary",
                "extraction_bounds": {"maximum_characters": 6000, "representation": "same_page_summary"},
                "unresolved_facet": "definition_and_scope_limit",
                "parent_terminal_claim_id": str(parent.get("claim_id") or ""),
                "source_identity_digest": _digest({"canonical_locator": locator}),
            }
    return None


def _sealed_evaluation_specs(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Seal criteria before any learner-facing work; default execution stays blocked."""
    unseen = {"task_id": stable_id("persistent-unseen-use", candidate["candidate_id"]), "learner_prompt": f"Apply the scoped claim about {candidate['topic']} to an unfamiliar example.", "evaluator_only": {"requires_source_scoped_reasoning": True, "rejects_unsupported_generalization": True}}
    transfer = {"task_id": stable_id("persistent-transfer", candidate["candidate_id"]), "learner_prompt": f"Use the same scoped idea about {candidate['topic']} in a materially different context.", "evaluator_only": {"requires_relation_preserved": True, "requires_scope_limit_preserved": True}}
    return {"unseen_use": unseen, "transfer": transfer, "criteria_digest": _digest({"unseen": unseen["evaluator_only"], "transfer": transfer["evaluator_only"]})}


def _default_evaluator_executor(_candidate: Mapping[str, Any], _sealed_specs: Mapping[str, Any]) -> dict[str, Any]:
    return {"status": "evaluation_unavailable", "reason": "no_independent_learner_and_evaluator_execution_path_configured"}


def _provider_prompt(goal: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Build a bounded advisory-only request with no learner or evaluator data."""
    question = f"What prerequisite structure and public verification routes would help learn {goal['topic']}?"
    schema = {
        "type": "object", "additionalProperties": False,
        "required": ["packet_type", "advisory_only", "capability_claim", "goal_id", "frontier_id", "unresolved_question", "explanation", "prerequisite_topics", "search_queries", "source_suggestions", "counterexamples", "uncertainty"],
        "properties": {
            "packet_type": {"type": "string", "const": "persistent_learning_advisory_v1"},
            "advisory_only": {"type": "boolean", "const": True},
            "capability_claim": {"type": "boolean", "const": False},
            "goal_id": {"type": "string", "const": str(goal["goal_id"])},
            "frontier_id": {"type": "string", "const": str(goal["frontiers"][0]["frontier_id"])},
            "unresolved_question": {"type": "string", "const": question},
            "explanation": {"type": "string"},
            "prerequisite_topics": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "search_queries": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "source_suggestions": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "counterexamples": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "uncertainty": {"type": "string"},
        },
    }
    system = (
        "Return exactly one JSON object. You are an advisory learning planner, not an authority. "
        "Do not claim the learner acquired knowledge, do not provide evaluator criteria, and do not request secrets."
    )
    user = json.dumps({
        "goal": goal["operator_goal"], "topic": goal["topic"], "unresolved_question": question,
        "required_constants": {"advisory_only": True, "capability_claim": False},
        "task": "Propose bounded prerequisite topics, public-source search queries, and verification routes.",
    }, sort_keys=True)
    return system, user, schema


def _default_provider_executor(request: Mapping[str, Any]) -> dict[str, Any]:
    """Use the already configured OpenAI transport for one persisted advisory claim."""
    from orchestration.runtime.v16_env import load_delta_evaluator_env, parse_env_file
    from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport

    repository_root = Path(__file__).resolve().parents[2]
    config = load_delta_evaluator_env(repository_root / ".env.local")
    if not config.live_call_permitted:
        return {"status": "provider_unavailable", "reason": "configured_provider_not_live_permitted"}
    if str(config.provider).lower() != str(request["provider"]).lower() or str(config.model) != str(request["model"]):
        return {"status": "provider_unavailable", "reason": "configured_provider_or_model_does_not_match_policy"}
    import urllib.error

    api_key = os.environ.get("DELTA_EVALUATOR_API_KEY") or parse_env_file(repository_root / ".env.local").get("DELTA_EVALUATOR_API_KEY", "")
    try:
        response = _default_transport(
            config.endpoint or "https://api.openai.com/v1/chat/completions",
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            {
                "model": request["model"], "temperature": 0,
                "max_tokens": int(request["maximum_tokens"]),
                "response_format": {"type": "json_schema", "json_schema": {"name": "persistent_learning_advisory", "strict": True, "schema": request["output_schema"]}},
                "messages": ({"role": "system", "content": request["system_prompt"]}, {"role": "user", "content": request["user_prompt"]}),
            },
            45,
        )
        choices = response.get("choices") if isinstance(response, Mapping) else ()
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], Mapping) else {}
        raw_text = str(message.get("content") or "") if isinstance(message, Mapping) else ""
        return {"status": "completed", "raw_response": json.loads(raw_text), "usage": dict(response.get("usage") or {})}
    except Exception as exc:  # a claim remains terminal after any dispatch failure.
        return {"status": "provider_failed", "reason": f"{type(exc).__name__}:{str(exc)[:240]}"}


def _validate_advisory_response(*, request: Mapping[str, Any], response: Any) -> str:
    """Validate the small advisory contract independently of transport success."""
    if not isinstance(response, Mapping):
        return "provider_response_not_object"
    required = (
        "packet_type", "advisory_only", "capability_claim", "goal_id", "frontier_id",
        "unresolved_question", "explanation", "prerequisite_topics", "search_queries",
        "source_suggestions", "counterexamples", "uncertainty",
    )
    if any(field not in response for field in required):
        return "provider_response_required_field_missing"
    if response.get("packet_type") != "persistent_learning_advisory_v1":
        return "provider_response_packet_type_invalid"
    if response.get("advisory_only") is not True or response.get("capability_claim") is not False:
        return "provider_response_advisory_boundary_invalid"
    for field in ("goal_id", "frontier_id", "unresolved_question"):
        if str(response.get(field) or "") != str(request.get(field) or ""):
            return f"provider_response_{field}_mismatch"
    if not all(isinstance(response.get(field), list) for field in ("prerequisite_topics", "search_queries", "source_suggestions", "counterexamples")):
        return "provider_response_collection_shape_invalid"
    return ""


def _provider_allowed(*, state: Mapping[str, Any], goal: Mapping[str, Any], fingerprint: str, provider: str = "openai", model: str = "gpt-4.1-mini") -> str:
    policy = dict(state.get("provider_policy") or DEFAULT_PROVIDER_POLICY)
    if provider not in set(str(item) for item in (policy.get("provider_allowlist") or ())):
        return "provider_not_allowlisted"
    if model not in set(str(item) for item in (policy.get("model_allowlist") or ())):
        return "model_not_allowlisted"
    if str(fingerprint) in {str(claim.get("fingerprint") or "") for claim in (goal.get("provider_claims") or ())}:
        return "duplicate_prompt_suppressed"
    if int(state.get("provider_calls") or 0) >= int(policy["maximum_runtime_calls"]):
        return "runtime_provider_budget_exhausted"
    if int(goal.get("budget", {}).get("provider_calls") or 0) >= int(policy["maximum_calls_per_goal"]):
        return "goal_provider_budget_exhausted"
    if int(state.get("consecutive_provider_calls") or 0) >= int(policy["maximum_consecutive_calls"]):
        return "consecutive_provider_call_limit"
    return ""


def _provider_cooldown_elapsed(state: Mapping[str, Any]) -> bool:
    policy = dict(state.get("provider_policy") or DEFAULT_PROVIDER_POLICY)
    cooldown = int(policy.get("cooldown_seconds") or 0)
    if cooldown <= 0:
        return True
    completed = [
        str(claim.get("completed_at") or "")
        for goal in (state.get("goals") or ()) for claim in (goal.get("provider_claims") or ())
        if str(claim.get("claim_state") or "") in {"completed", "failed"}
    ]
    if not completed:
        return True
    try:
        latest = max(datetime.fromisoformat(value.replace("Z", "+00:00")) for value in completed if value)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - latest).total_seconds() >= cooldown


def _estimate_provider_cost(*, request: Mapping[str, Any], usage: Mapping[str, Any]) -> float:
    total = int(usage.get("total_tokens") or 0)
    if total <= 0:
        total = len(str(request.get("system_prompt") or "").split()) + len(str(request.get("user_prompt") or "").split()) + int(request.get("maximum_tokens") or 0)
    return round(total / 1000 * 0.00015, 6)


def run_one_cycle(
    *,
    state: Mapping[str, Any],
    runtime_root: Path,
    evidence_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_evidence_resolver,
    public_evidence_resolver: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]] = _default_public_evidence_resolver,
    provider_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_provider_executor,
    retrieval_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_retrieval_executor,
    evaluator_executor: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] = _default_evaluator_executor,
) -> dict[str, Any]:
    """Execute one checkpointed local/public/provider-assisted work item."""
    current = dict(state)
    if current.get("lifecycle_state") in {"paused_runtime", "stopped"}:
        return current
    if _provider_cooldown_elapsed(current):
        current["consecutive_provider_calls"] = 0
    goal = _select_goal(current)
    if goal is None:
        current["lifecycle_state"] = "waiting"
        current["terminal_reason"] = "no_eligible_goal"
        _checkpoint(state=current, runtime_root=runtime_root, reason="runtime_waiting")
        return _read(Path(runtime_root) / STATE_FILE)
    current["lifecycle_state"] = "running"
    current["active_goal_id"] = goal["goal_id"]
    current["active_work_item"] = {"goal_id": goal["goal_id"], "frontier": goal["frontiers"][0]["label"], "state": "resolving_retained_evidence"}
    outcome = dict(evidence_resolver(goal))
    retained_candidate: dict[str, Any] = {}
    retained_evaluation: dict[str, Any] = {}
    if outcome.get("status") == "retained_evidence_available":
        retained_candidate = _provisional_candidate_from_retained(goal=goal, evidence=dict(outcome.get("evidence") or {}))
        retained_specs = _sealed_evaluation_specs(retained_candidate)
        retained_evaluation = _default_provisional_evaluator(retained_candidate, retained_specs)
    completed_advice = next(
        (
            dict(claim.get("raw_response") or {}) for claim in reversed(tuple(goal.get("provider_claims") or ()))
            if str(claim.get("claim_state")) == "completed" and isinstance(claim.get("raw_response"), Mapping)
        ),
        None,
    )
    if outcome.get("status") == "retained_evidence_available":
        # Retained RC2 material is useful context, but it is not a completion
        # or terminal capability verdict.  It must enter the same independent
        # public/provider verification route as an unknown topic.
        outcome = {
            "status": "public_evidence_required",
            "fingerprint": _digest({"goal": goal["goal_id"], "route": "retained_evidence_requires_verification"}),
            "evidence": {
                **dict(outcome.get("evidence") or {}),
                "route": "retained_evidence_requires_verification",
                "reason": "retained_evidence_non_trusted_requires_grounding_and_sealed_evaluation",
            },
        }
    if outcome.get("status") == "public_evidence_required":
        outcome = dict(public_evidence_resolver(goal, completed_advice))
    fingerprint = str(outcome.get("fingerprint") or "")
    exhausted = set(str(item) for item in current.get("exhausted_fingerprints") or ())
    # Metadata fingerprints describe a discovery route, not a retrieval
    # strategy.  Let an already-discovered candidate reach strategy-scoped
    # eligibility so a bounded representation can follow a terminal full-page
    # claim; individual claims still prevent equivalent dispatches.
    if fingerprint in exhausted and outcome.get("status") != "public_evidence_unresolved":
        outcome = {"status": "blocked_evidence_environment", "fingerprint": fingerprint, "evidence": {"reason": "duplicate_evidence_route_suppressed"}}
    stored_goal = next((dict(item) for item in current.get("goals") or () if item.get("goal_id") == goal["goal_id"]), dict(goal))
    updated_goal = {**stored_goal, "work_nodes": tuple(goal.get("work_nodes") or ())}
    if retained_candidate:
        updated_goal["candidate_versions"] = tuple(updated_goal.get("candidate_versions") or ()) + (retained_candidate,)
        updated_goal["sealed_evaluations"] = tuple(updated_goal.get("sealed_evaluations") or ()) + ({"specifications": retained_specs, "result": retained_evaluation},)
    candidates = tuple(dict(item) for item in (dict(outcome.get("evidence") or {}).get("candidates") or ()) if isinstance(item, Mapping))
    prior_retrievals = tuple(updated_goal.get("retrieval_claims") or ())
    selected_candidate = _select_retrieval_candidate(candidates=candidates, prior_claims=prior_retrievals)
    if outcome.get("status") == "public_evidence_unresolved" and selected_candidate is not None:
        strategy = str(selected_candidate.get("extraction_strategy") or "full_page_rc8")
        strategy_fingerprint = _digest({
            "locator": selected_candidate["canonical_locator"],
            "strategy": strategy,
            "facet": selected_candidate.get("unresolved_facet") or "definition_and_scope_limit",
            "bounds": selected_candidate.get("extraction_bounds") or {},
        })
        retrieval_claim = {
            "claim_id": stable_id("persistent-development-retrieval-claim", current["runtime_id"], updated_goal["goal_id"], strategy_fingerprint),
            "goal_id": updated_goal["goal_id"], "frontier_id": updated_goal["frontiers"][0]["frontier_id"],
            "candidate_id": selected_candidate["candidate_id"], "canonical_locator": selected_candidate["canonical_locator"],
            "candidate_fingerprint": _digest(selected_candidate), "query_fingerprint": fingerprint,
            "source_identity_digest": str(selected_candidate.get("source_identity_digest") or _digest({"canonical_locator": selected_candidate["canonical_locator"]})),
            "unresolved_facet": str(selected_candidate.get("unresolved_facet") or "definition_and_scope_limit"),
            "extraction_strategy": strategy, "extraction_bounds": dict(selected_candidate.get("extraction_bounds") or {}),
            "strategy_fingerprint": strategy_fingerprint,
            "parent_terminal_claim_id": str(selected_candidate.get("parent_terminal_claim_id") or ""),
            "claim_state": "dispatching", "attempt_count": 1, "created_at": utc_now(),
        }
        updated_goal["retrieval_claims"] = prior_retrievals + (retrieval_claim,)
        staged_goals = [updated_goal if item["goal_id"] == updated_goal["goal_id"] else item for item in current.get("goals") or ()]
        _checkpoint(state={**current, "goals": tuple(staged_goals), "active_goal_id": updated_goal["goal_id"], "active_work_item": {"goal_id": updated_goal["goal_id"], "state": "retrieval_claim_dispatching", "claim_id": retrieval_claim["claim_id"]}}, runtime_root=runtime_root, reason="retrieval_claim_persisted_before_dispatch")
        try:
            retrieval = dict(retrieval_executor(selected_candidate))
            content = str(retrieval.pop("content_text") or "")
            evidence_target = str(selected_candidate.get("evidence_target") or selected_candidate.get("title") or updated_goal["topic"])
            source_artifact = _persist_source_artifact(
                runtime_root=runtime_root, runtime_id=str(current["runtime_id"]), goal=updated_goal,
                claim=retrieval_claim, retrieval=retrieval, retained_text=content,
            )
            mapping_artifact = _map_persisted_source_artifact(
                runtime_root=runtime_root, source_artifact=source_artifact, evidence_target=evidence_target,
                unresolved_facet=str(retrieval_claim.get("unresolved_facet") or "definition_and_scope_limit"),
            )
            facets = tuple(dict(item) for item in mapping_artifact.get("accepted_excerpts") or ())
            completed_retrieval = {
                **retrieval_claim, "claim_state": "completed", "completed_at": utc_now(),
                "canonical_locator": str(retrieval.get("canonical_locator") or selected_candidate["canonical_locator"]),
                "source_digest": str(source_artifact["source_digest"]), "extraction_digest": str(source_artifact["extraction_digest"]),
                "source_artifact_id": source_artifact["artifact_id"], "source_artifact_path": source_artifact["artifact_path"],
                "source_artifact_digest": source_artifact["artifact_digest"], "excerpt_mapping_id": mapping_artifact["artifact_id"],
                "excerpt_mapping_path": mapping_artifact["artifact_path"], "excerpt_mapping_digest": mapping_artifact["artifact_digest"],
                "mapped_excerpt_count": len(facets),
            }
            if {item["facet"] for item in facets} >= {"definition", "scope_limit"}:
                candidate = {"candidate_id": stable_id("persistent-development-candidate", updated_goal["goal_id"], evidence_target, completed_retrieval["source_digest"]), "candidate_version": 1, "topic": evidence_target, "parent_goal_topic": updated_goal["topic"], "scoped_claim": f"source-grounded scoped claim about {evidence_target}", "target_behavior": f"explain a scoped definition of {evidence_target} using retained excerpts", "required_evidence_facets": ("definition", "scope_limit"), "direct_provenance": {"retrieval_claim_id": completed_retrieval["claim_id"], "source_digest": completed_retrieval["source_digest"], "extraction_digest": completed_retrieval["extraction_digest"], "source_artifact_id": source_artifact["artifact_id"], "source_artifact_digest": source_artifact["artifact_digest"], "excerpt_mapping_id": mapping_artifact["artifact_id"], "excerpt_mapping_digest": mapping_artifact["artifact_digest"], "evidence_target": evidence_target, "excerpt_references": tuple({"facet": item["facet"], "boundary": item["boundary"]} for item in facets)}, "derived_provenance": (), "supported_facets": tuple(item["facet"] for item in facets), "unresolved_facets": (), "unresolved_limits": ("supports a scoped source concept; parent-goal transfer remains unassessed",), "trusted_admission": False, "capability_promotion": False}
                candidate["candidate_digest"] = _digest(candidate)
                sealed_specs = _sealed_evaluation_specs(candidate)
                evaluation = dict(evaluator_executor(candidate, sealed_specs))
                outcome = {"status": "evaluated_candidate" if evaluation.get("status") == "passed" else "candidate_evaluation_blocked", "fingerprint": _digest({"candidate": candidate["candidate_digest"], "evaluation": evaluation}), "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": completed_retrieval["claim_id"], "candidate": candidate, "sealed_evaluation": sealed_specs, "evaluation": evaluation}}
                updated_goal["candidate_versions"] = tuple(updated_goal.get("candidate_versions") or ()) + (candidate,)
                updated_goal["sealed_evaluations"] = tuple(updated_goal.get("sealed_evaluations") or ()) + ({"specifications": sealed_specs, "result": evaluation},)
            else:
                outcome = {"status": "public_evidence_unresolved", "fingerprint": fingerprint, "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": completed_retrieval["claim_id"], "reason": "source_body_missing_required_facets", "supported_facets": tuple(item["facet"] for item in facets)}}
        except Exception as exc:  # retrieval failures remain terminal and replay-safe.
            completed_retrieval = {**retrieval_claim, "claim_state": "failed", "completed_at": utc_now(), "failure_reason": f"{type(exc).__name__}:{str(exc)[:240]}"}
            outcome = {"status": "public_evidence_unresolved", "fingerprint": fingerprint, "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": retrieval_claim["claim_id"], "reason": completed_retrieval["failure_reason"]}}
        updated_goal["retrieval_claims"] = tuple((*prior_retrievals, completed_retrieval))
    # A local miss is not a terminal disposition.  The route is persisted first,
    # then one exact-once advisory provider claim may be dispatched inside the
    # runtime's pre-approved budget envelope.
    if outcome.get("status") == "public_evidence_unresolved" and completed_advice is None:
        system_prompt, user_prompt, output_schema = _provider_prompt(updated_goal)
        provider_fingerprint = _digest({
            "runtime_id": current["runtime_id"], "goal_id": updated_goal["goal_id"],
            "frontier_id": updated_goal["frontiers"][0]["frontier_id"],
            "question": user_prompt, "provider": "openai", "model": "gpt-4.1-mini",
        })
        denial = _provider_allowed(state=current, goal=updated_goal, fingerprint=provider_fingerprint)
        if denial:
            updated_goal["state"] = "paused_budget"
            updated_goal["blocker"] = denial
            outcome = {"status": "paused_budget", "fingerprint": provider_fingerprint, "evidence": {"route": "provider_escalation", "reason": denial}}
            fingerprint = provider_fingerprint
        else:
            policy = dict(current.get("provider_policy") or DEFAULT_PROVIDER_POLICY)
            purpose = "prerequisite_generation"
            if purpose not in SUPPORTED_ADVISORY_PURPOSES:
                raise ValueError("persistent_runtime_provider_purpose_unsupported")
            request = {
                "claim_id": stable_id("persistent-development-provider-claim", current["runtime_id"], updated_goal["goal_id"], provider_fingerprint),
                "runtime_id": current["runtime_id"], "mission_id": updated_goal["goal_id"], "goal_id": updated_goal["goal_id"],
                "frontier_id": updated_goal["frontiers"][0]["frontier_id"],
                "unresolved_question": json.loads(user_prompt)["unresolved_question"],
                "provider": "openai", "model": "gpt-4.1-mini", "purpose": purpose,
                "prompt_digest": _digest({"system": system_prompt, "user": user_prompt}), "fingerprint": provider_fingerprint,
                "maximum_tokens": int(policy["maximum_tokens_per_call"]), "system_prompt": system_prompt,
                "user_prompt": user_prompt, "output_schema": output_schema, "claim_state": "dispatching",
                "attempt_count": 1, "created_at": utc_now(),
            }
            updated_goal["provider_claims"] = tuple(updated_goal.get("provider_claims") or ()) + (request,)
            staged_goals = [updated_goal if item["goal_id"] == updated_goal["goal_id"] else item for item in current.get("goals") or ()]
            # Persist before network dispatch.  A restart sees dispatching and
            # fails closed rather than risk repeating a paid request.
            staged = {**current, "goals": tuple(staged_goals), "active_goal_id": updated_goal["goal_id"], "active_work_item": {"goal_id": updated_goal["goal_id"], "state": "provider_claim_dispatching", "claim_id": request["claim_id"]}}
            _checkpoint(state=staged, runtime_root=runtime_root, reason="provider_claim_persisted_before_dispatch")
            provider_result = dict(provider_executor(request))
            raw = provider_result.get("raw_response")
            response_error = _validate_advisory_response(request=request, response=raw) if provider_result.get("status") == "completed" else ""
            if response_error:
                provider_result = {**provider_result, "status": "provider_failed", "reason": response_error}
            response_digest = _digest(raw if raw is not None else {"reason": provider_result.get("reason", "")})
            completed_claim = {
                **request,
                "claim_state": "completed" if provider_result.get("status") == "completed" else "failed",
                "completed_at": utc_now(), "response_digest": response_digest,
                "usage": dict(provider_result.get("usage") or {}), "failure_reason": str(provider_result.get("reason") or ""),
                "raw_response": raw,
            }
            completed_claim["estimated_cost_usd"] = _estimate_provider_cost(request=request, usage=completed_claim["usage"])
            updated_goal["provider_claims"] = tuple((*tuple(updated_goal.get("provider_claims") or ())[:-1], completed_claim))
            budget = dict(updated_goal["budget"]); budget["provider_calls"] = int(budget.get("provider_calls") or 0) + 1; updated_goal["budget"] = budget
            if completed_claim["claim_state"] == "completed":
                outcome = {
                    "status": "provider_advisory_untrusted_ready", "fingerprint": provider_fingerprint,
                    "evidence": {"route": "configured_provider_advisory", "claim_id": request["claim_id"], "response_digest": response_digest, "advisory_untrusted": True, "raw_response": raw},
                }
                updated_goal["state"] = "awaiting_public_evidence"
                updated_goal["blocker"] = "provider_advisory_requires_public_or_deterministic_verification"
            else:
                outcome = {"status": "provider_failed", "fingerprint": provider_fingerprint, "evidence": {"route": "configured_provider_advisory", "claim_id": request["claim_id"], "response_digest": response_digest, "reason": completed_claim["failure_reason"]}}
                updated_goal["state"] = "awaiting_public_evidence"
                updated_goal["blocker"] = "provider_advisory_failed_continue_public_routes"
            fingerprint = provider_fingerprint
    history = list(updated_goal.get("work_history") or ())
    history.append({"work_id": stable_id("persistent-development-work", goal["goal_id"], fingerprint, len(history)), "outcome": outcome.get("status"), "fingerprint": fingerprint, "at": utc_now()})
    updated_goal["work_history"] = tuple(history)
    updated_goal["evidence"] = tuple(
        (*tuple(updated_goal.get("evidence") or ()), dict(outcome.get("evidence") or {}))
    )
    budget = dict(updated_goal["budget"]); budget["cycles_used"] = int(budget.get("cycles_used") or 0) + 1; updated_goal["budget"] = budget
    if outcome.get("status") == "public_evidence_unresolved" and completed_advice is not None:
        updated_goal["state"] = "blocked_evidence_environment"
        updated_goal["blocker"] = "provider_advisory_public_verification_route_exhausted"
    elif outcome.get("status") not in {"provider_advisory_untrusted_ready", "provider_failed", "paused_budget"}:
        updated_goal["state"] = "blocked_evidence_environment"
        updated_goal["blocker"] = str(dict(outcome.get("evidence") or {}).get("reason") or "no_authorized_evidence_route")
    goals = [updated_goal if item["goal_id"] == updated_goal["goal_id"] else item for item in current.get("goals") or ()]
    current.update({"goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "exhausted_fingerprints": tuple(sorted({*exhausted, fingerprint} - {""}))})
    if outcome.get("status") == "evaluated_candidate":
        updated_goal["state"] = "developmental_evidence_validated"
        updated_goal["blocker"] = "candidate_evaluated_not_trusted_or_capability_promoted"
        current["competence_map"] = {**dict(current.get("competence_map") or {}), str(updated_goal["topic"]): {"candidate_id": updated_goal["candidate_versions"][-1]["candidate_id"], "status": "developmentally_validated", "capability_promotion": False}}
    elif outcome.get("status") == "candidate_evaluation_blocked":
        updated_goal["state"] = "blocked_capability_gap"
        updated_goal["blocker"] = "sealed_evaluation_execution_unavailable"
    selected_node = dict(goal.get("selected_node") or {})
    if selected_node:
        nodes = []
        for raw_node in updated_goal.get("work_nodes") or ():
            node = dict(raw_node)
            if node.get("node_id") == selected_node.get("node_id"):
                node["attempts"] = int(node.get("attempts") or 0) + 1
                node["last_outcome"] = str(outcome.get("status") or "")
                node["state"] = "provisional_evaluated" if retained_candidate else "exhausted"
            nodes.append(node)
        updated_goal["work_nodes"] = tuple(nodes)
        # Persist replenishment in the same checkpoint as the exhausted node;
        # a restart must see the new work rather than a transient empty queue.
        updated_goal["work_nodes"] = _expand_work_nodes(updated_goal)
        if outcome.get("status") != "paused_budget" and any(str(node.get("state")) == "queued" for node in updated_goal["work_nodes"]):
            updated_goal["state"] = "queued"
            updated_goal["blocker"] = ""
    current["provider_calls"] = sum(int(item.get("budget", {}).get("provider_calls") or 0) for item in current["goals"])
    current["provider_spend_estimated_usd"] = round(sum(
        float(claim.get("estimated_cost_usd") or 0.0)
        for item in current["goals"] for claim in (item.get("provider_claims") or ())
        if str(claim.get("claim_state")) in {"completed", "failed"}
    ), 6)
    current["consecutive_provider_calls"] = int(current.get("consecutive_provider_calls") or 0) + (1 if outcome.get("status") in {"provider_advisory_untrusted_ready", "provider_failed"} else 0)
    if all(str(item.get("state")) in TERMINAL_GOAL_STATES for item in current["goals"]):
        current["lifecycle_state"] = "waiting"
        current["terminal_reason"] = "all_goals_reached_honest_terminal_disposition"
    else:
        current["lifecycle_state"] = "ready"
    _checkpoint(state=current, runtime_root=runtime_root, reason="bounded_work_cycle_completed")
    return _read(Path(runtime_root) / STATE_FILE)


def run_until_idle(*, state: Mapping[str, Any], runtime_root: Path, maximum_cycles: int = 32, evidence_resolver: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_evidence_resolver, public_evidence_resolver: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]] = _default_public_evidence_resolver, provider_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_provider_executor, retrieval_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _default_retrieval_executor, evaluator_executor: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] = _default_evaluator_executor) -> dict[str, Any]:
    if maximum_cycles < 1:
        raise ValueError("persistent_runtime_cycle_budget_invalid")
    current = dict(state)
    for _ in range(maximum_cycles):
        before = int(current.get("checkpoint_sequence") or 0)
        current = run_one_cycle(state=current, runtime_root=runtime_root, evidence_resolver=evidence_resolver, public_evidence_resolver=public_evidence_resolver, provider_executor=provider_executor, retrieval_executor=retrieval_executor, evaluator_executor=evaluator_executor)
        if current.get("lifecycle_state") in {"waiting", "paused_runtime", "stopped"} or int(current.get("checkpoint_sequence") or 0) == before:
            break
    return current


def export_runtime_report(*, state: Mapping[str, Any], runtime_root: Path) -> dict[str, Any]:
    goals = tuple(state.get("goals") or ())
    nodes = tuple(node for goal in goals for node in (goal.get("work_nodes") or ()))
    retrieval_claims = tuple(claim for goal in goals for claim in (goal.get("retrieval_claims") or ()))
    candidates = tuple(candidate for goal in goals for candidate in (goal.get("candidate_versions") or ()))
    report = {
        "runtime_id": state["runtime_id"],
        "lifecycle_state": state["lifecycle_state"],
        "terminal_reason": state.get("terminal_reason", ""),
        "checkpoint_sequence": state["checkpoint_sequence"],
        "goals": tuple({"goal_id": goal["goal_id"], "topic": goal["topic"], "state": goal["state"], "blocker": goal.get("blocker", ""), "cycles_used": goal["budget"]["cycles_used"]} for goal in goals),
        "work_node_count": len(nodes),
        "queued_work_node_count": sum(str(node.get("state")) == "queued" for node in nodes),
        "candidate_count": len(candidates),
        "completed_retrieval_claim_count": sum(str(claim.get("claim_state")) == "completed" for claim in retrieval_claims),
        "durable_source_artifact_count": sum(bool(claim.get("source_artifact_id")) for claim in retrieval_claims),
        "mapped_excerpt_artifact_count": sum(bool(claim.get("excerpt_mapping_id")) for claim in retrieval_claims),
        "source_grounded_candidate_count": sum(bool(dict(candidate.get("direct_provenance") or {}).get("source_artifact_id")) for candidate in candidates),
        "structural_candidate_validation_count": sum(len(goal.get("sealed_evaluations") or ()) for goal in goals),
        "behavioral_evaluation_attempt_count": 0,
        "behavioral_evaluation_pass_count": 0,
        "sealed_evaluation_count": sum(len(goal.get("sealed_evaluations") or ()) for goal in goals),
        "next_wake_at": str(state.get("next_wake_at") or ""),
        "next_action": dict(state.get("next_action") or {}),
        "provider_calls": int(state.get("provider_calls") or 0),
        "provider_spend_estimated_usd": float(state.get("provider_spend_estimated_usd") or 0.0),
        "provider_policy": dict(state.get("provider_policy") or {}),
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "created_at": utc_now(),
    }
    report["report_digest"] = _digest({**report, "created_at": ""})
    _atomic_write(Path(runtime_root) / REPORT_FILE, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Small operator CLI for unattended local-first runtime operation."""
    parser = argparse.ArgumentParser(description="Run DELTA's persistent developmental queue.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--goal", action="append", default=[])
    parser.add_argument("--goals-file", default="")
    parser.add_argument("--cycles", type=int, default=32)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--pause", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--recover", action="store_true", help="Resume durable state without duplicating claims.")
    args = parser.parse_args(argv)
    root = Path(args.runtime_root)
    goals = list(args.goal)
    if args.goals_file:
        payload = json.loads(Path(args.goals_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
            raise ValueError("persistent_runtime_goals_file_must_be_json_string_list")
        goals.extend(payload)
    state = initialize_runtime(runtime_root=root, goals=goals)
    if args.pause:
        state = pause_runtime(state=state, runtime_root=root)
    elif args.resume:
        state = resume_runtime(state=state, runtime_root=root)
    elif args.stop:
        state = stop_runtime(state=state, runtime_root=root)
    elif args.recover:
        state = resume_runtime(state=state, runtime_root=root)
    elif not args.status:
        state = run_until_idle(state=state, runtime_root=root, maximum_cycles=args.cycles)
    report = export_runtime_report(state=state, runtime_root=root) if args.report else {}
    print(json.dumps({"state": state, "report": report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

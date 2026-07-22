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
import uuid
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.developmental_learning import DevelopmentalAttemptRecord, DevelopmentalMissionContract, LearningSubgoal
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
EVIDENCE_REVISION_PLAN_DIRECTORY = "evidence_revision_plans"
LEARNER_BUNDLE_DIRECTORY = "learner_visible_bundles"
EVALUATOR_REUSE_DECISION_DIRECTORY = "evaluator_reuse_decisions"
EVIDENCE_REVISION_BINDING_DIRECTORY = "evidence_revision_evaluator_bindings"
EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY = "evidence_revision_execution_claims"
EVIDENCE_REVISION_OWNERSHIP_DIRECTORY = "evidence_revision_execution_ownership"
EVIDENCE_REVISION_STATES = frozenset({
    "planned", "retrieving", "evidence_sufficient", "evidence_insufficient",
    "candidate_revised", "reevaluation_pending", "blocked_integrity",
})
TERMINAL_GOAL_STATES = frozenset({
    "completed", "partially_completed", "blocked_evidence_environment",
    "blocked_capability_gap", "blocked_operator_authority", "paused_budget",
    "development_route_exhausted", "integrity_stop", "cancelled",
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


def _publish_transition_metadata(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["transition_digest"] = _digest(body)
    temporary = path.parent / f".{uuid.uuid4().hex[:8]}.tmp"
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(body, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return body


def _transition_record_path(root: Path, sequence: str) -> Path:
    transition_dir = root / f"{sequence}.transition"
    if transition_dir.exists():
        return transition_dir / "metadata.json"
    return root / f"{sequence}.json"


def _read_transition_records(root: Path) -> dict[str, dict[str, Any]]:
    records = {path.name: _read(path) for path in root.glob("*.json")} if root.exists() else {}
    if root.exists():
        for path in root.glob("*.transition"):
            metadata = path / "metadata.json"
            if metadata.exists():
                records[f"{path.stem}.json"] = _read(metadata)
    return records


def _exclusive_transition(*, runtime_root: Path, execution_id: str, sequence: str, payload: Mapping[str, Any], repair_orphaned_lock: bool = False) -> tuple[str, dict[str, Any]]:
    """Create one durable ownership transition by publishing a complete directory."""
    root = Path(runtime_root) / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id
    transition_dir = root / f"{sequence}.transition"
    legacy_path = root / f"{sequence}.json"
    root.mkdir(parents=True, exist_ok=True)
    if transition_dir.exists():
        return ("already_exists", _read(transition_dir / "metadata.json"))
    if legacy_path.exists():
        return ("already_exists", _read(legacy_path))
    temp_dir = root / f".{uuid.uuid4().hex[:8]}.td"
    temp_dir.mkdir()
    body = _publish_transition_metadata(temp_dir / "metadata.json", payload)
    try:
        temp_dir.rename(transition_dir)
    except FileExistsError:
        (temp_dir / "metadata.json").unlink(missing_ok=True)
        temp_dir.rmdir()
        return ("already_exists", _read_transition_records(root).get(f"{sequence}.json", {}))
    except OSError:
        if transition_dir.exists():
            (temp_dir / "metadata.json").unlink(missing_ok=True)
            temp_dir.rmdir()
            return ("already_exists", _read(transition_dir / "metadata.json"))
        raise
    return ("acquired", body)


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


def _find_claim_artifact(*, runtime_root: Path, directory: str, claim_id: str) -> dict[str, Any] | None:
    root = Path(runtime_root) / directory
    if not root.exists():
        return None
    for path in root.glob("*.json"):
        record = _read(path)
        if str(record.get("claim_id") or record.get("revision_execution_claim_id") or "") == claim_id:
            return record
    return None


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
            "revision_plan_id": str(claim.get("revision_plan_id") or ""),
            "revision_plan_digest": str(claim.get("revision_plan_digest") or ""),
            "failed_evaluation_id": str(claim.get("failed_evaluation_id") or ""),
            "failed_evaluation_digest": str(claim.get("failed_evaluation_digest") or ""),
            "evidence_revision_target_id": str(claim.get("evidence_revision_target_id") or ""),
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
        budget = dict(goal.get("budget") or {})
        if str(goal.get("state") or "") in TERMINAL_GOAL_STATES:
            continue
        if int(budget.get("maximum_cycles") or 0) and int(budget.get("cycles_used") or 0) >= int(budget.get("maximum_cycles") or 0):
            continue
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


def _apply_cycle_budget_dispositions(state: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    current = dict(state)
    goals = []
    changed = False
    for raw_goal in current.get("goals") or ():
        goal = dict(raw_goal)
        budget = dict(goal.get("budget") or {})
        maximum = int(budget.get("maximum_cycles") or 0)
        used = int(budget.get("cycles_used") or 0)
        if maximum and used >= maximum and str(goal.get("state") or "") not in TERMINAL_GOAL_STATES:
            queued = any(str(node.get("state") or "") == "queued" for node in goal.get("work_nodes") or ())
            goal["state"] = "paused_budget" if queued else "development_route_exhausted"
            goal["blocker"] = "cycle_budget_exhausted_with_remaining_distinct_work" if queued else "all_unique_development_routes_exhausted"
            changed = True
        goals.append(goal)
    if changed:
        current["goals"] = tuple(goals)
        if all(str(item.get("state") or "") in TERMINAL_GOAL_STATES for item in goals):
            current["lifecycle_state"] = "waiting"
            current["terminal_reason"] = "all_goals_reached_honest_terminal_disposition"
        else:
            current["lifecycle_state"] = "ready"
    return current, changed


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


def _apply_post_behavioral_evaluation_goal_state(goal: Mapping[str, Any], disposition: str) -> dict[str, Any]:
    updated = dict(goal)
    if disposition == "candidate_revision_required":
        queued = any(str(node.get("state") or "") == "queued" for node in updated.get("work_nodes") or ())
        updated["state"] = "queued" if queued else "development_route_exhausted"
        updated["blocker"] = "" if queued else "all_unique_development_routes_exhausted_after_evaluation"
    elif disposition == "conceptual_knowledge_update":
        updated["state"] = "developmental_evidence_validated"
        updated["blocker"] = "tier_a_conceptual_knowledge_update_pending"
    elif disposition == "functional_capability_proposal":
        updated["state"] = "blocked_operator_authority"
        updated["blocker"] = "tier_b_functional_adaptation_proposal_required"
    elif disposition == "sensitive_capability_review_required":
        updated["state"] = "blocked_operator_authority"
        updated["blocker"] = "tier_c_sensitive_authority_request_required"
    return updated


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


def _iter_json_artifacts(runtime_root: Path, directory: str) -> tuple[dict[str, Any], ...]:
    root = Path(runtime_root) / directory
    if not root.exists():
        return ()
    return tuple(_read(path) for path in sorted(root.glob("*.json")))


def _find_goal_for_candidate(state: Mapping[str, Any], candidate_id: str, candidate_digest: str) -> tuple[int, dict[str, Any], dict[str, Any]]:
    for index, raw_goal in enumerate(state.get("goals") or ()):
        goal = dict(raw_goal)
        for raw_candidate in goal.get("candidate_versions") or ():
            candidate = dict(raw_candidate)
            if str(candidate.get("candidate_id") or "") == candidate_id and str(candidate.get("candidate_digest") or "") == candidate_digest:
                return index, goal, candidate
    raise ValueError("persistent_runtime_revision_parent_candidate_missing")


def _load_failed_revision_context(*, runtime_root: Path, failed_evaluation_id: str = "") -> dict[str, Any]:
    state = initialize_runtime(runtime_root=runtime_root)
    evaluations = _iter_json_artifacts(Path(runtime_root), "learning_evaluations")
    if failed_evaluation_id:
        evaluations = tuple(item for item in evaluations if str(item.get("artifact_id") or item.get("evaluation", {}).get("evaluation_id") or "") == failed_evaluation_id)
    candidates = []
    for artifact in evaluations:
        evaluation = dict(artifact.get("evaluation") or {})
        if str(evaluation.get("disposition") or "") != "insufficient_retained_teaching_evidence":
            continue
        if bool(evaluation.get("promotion_eligible")):
            continue
        candidates.append(artifact)
    if not candidates:
        raise ValueError("persistent_runtime_revision_failed_evaluation_missing")
    failed_artifact = candidates[-1]
    evaluation = dict(failed_artifact["evaluation"])
    claim_id = str(failed_artifact.get("claim_id") or "")
    claim = _read(Path(runtime_root) / "learning_attempt_claims" / f"{claim_id}.json") if claim_id else {}
    parent_candidate_id = str(claim.get("candidate_id") or "")
    parent_candidate_digest = str(claim.get("candidate_digest") or "")
    goal_index, goal, parent_candidate = _find_goal_for_candidate(state, parent_candidate_id, parent_candidate_digest)
    pending = dict(goal.get("pending_evaluator_authority") or {})
    authority_id = str(pending.get("request_id") or "")
    authority = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / f"{authority_id}.json") if authority_id else {}
    result_id = str(pending.get("result_artifact_id") or "")
    evaluator_result = _read(Path(runtime_root) / EVALUATOR_AUTHORITY_DIRECTORY / "execution_results" / f"{result_id}.json") if result_id else {}
    sealed_package = dict(evaluator_result.get("sealed_package") or {})
    sealed_package_digest = str(failed_artifact.get("sealed_package_digest") or evaluator_result.get("artifact_digest") or "")
    execution_view = {}
    execution_view_digest = str(pending.get("execution_view_digest") or "")
    for item in _iter_json_artifacts(Path(runtime_root), "sealed_case_execution_views"):
        if not execution_view_digest or str(item.get("artifact_digest") or "") == execution_view_digest:
            execution_view = item
            execution_view_digest = str(item.get("artifact_digest") or "")
            break
    selected_node = next((dict(node) for node in goal.get("work_nodes") or () if str(node.get("node_id") or "") == str(claim.get("work_node_id") or "")), None)
    if selected_node is None:
        selected_node = next((dict(node) for node in goal.get("work_nodes") or () if str(node.get("operation") or "") == "candidate_revision"), {})
    return {
        "state": state, "goal_index": goal_index, "goal": goal, "selected_node": selected_node,
        "parent_candidate": parent_candidate, "failed_evaluation_artifact": failed_artifact,
        "failed_evaluation": evaluation, "failed_attempt_claim": claim,
        "authority": authority, "evaluator_result": evaluator_result, "sealed_package": sealed_package,
        "sealed_package_digest": sealed_package_digest, "execution_view": execution_view,
        "execution_view_digest": execution_view_digest,
    }


def _normalize_failed_revision_targets(evaluation: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    buckets: dict[str, dict[str, Any]] = {}

    def add(target_id: str, label: str, facets: Sequence[str], case: Mapping[str, Any], evidence_terms: Sequence[str]) -> None:
        current = buckets.setdefault(target_id, {
            "target_id": target_id, "label": label, "normalized_facets": tuple(facets),
            "source_case_ids": (), "source_case_kinds": (), "original_failed_dimensions": (),
            "evidence_terms": (), "priority": len(buckets) + 1,
        })
        current["source_case_ids"] = tuple(sorted({*tuple(current["source_case_ids"]), str(case.get("case_id") or "")} - {""}))
        current["source_case_kinds"] = tuple(sorted({*tuple(current["source_case_kinds"]), str(case.get("kind") or case.get("case_kind") or "")} - {""}))
        current["original_failed_dimensions"] = tuple(sorted({*tuple(current["original_failed_dimensions"]), *tuple(evidence_terms)} - {""}))
        current["evidence_terms"] = tuple(sorted({*tuple(current["evidence_terms"]), *tuple(evidence_terms)} - {""}))

    for case in evaluation.get("content_case_results") or ():
        raw_case = dict(case)
        terms = tuple(str(term).lower() for term in (raw_case.get("failed_predicates") or ()) if str(term).strip())
        joined = " ".join(terms)
        if any(term in joined for term in ("specific", "measurable", "achievable", "realistic", "relevant", "time-bound", "effective", "component")):
            add("smart_components", "SMART components for effective goals", ("component", "example"), raw_case, terms)
        if any(term in joined for term in ("monitor", "monitoring", "feedback", "progress", "progres", "monthly", "effect", "impact", "outcome")):
            add("progress_monitoring_feedback", "progress monitoring or feedback", ("monitoring", "outcome_relation"), raw_case, terms)
        if any(term in joined for term in ("adjust", "revised", "revise", "improve", "vague", "incomplete", "successful")):
            add("progress_based_adjustment", "adjustment or revision based on observed progress", ("adjustment", "scope_limit"), raw_case, terms)
        if any(term in joined for term in ("motivation", "performance", "persistence", "focus", "outcome", "influence", "impact")):
            add("motivation_performance_effects", "motivation and performance effects", ("outcome_relation",), raw_case, terms)
        if any(term in joined for term in ("purpose", "definition", "concept", "means")):
            add("definition_purpose", "definition and purpose", ("definition", "purpose"), raw_case, terms)
        if not any(term in joined for term in ("specific", "measurable", "achievable", "realistic", "relevant", "time-bound", "effective", "component", "monitor", "monitoring", "feedback", "progress", "progres", "monthly", "effect", "impact", "outcome", "adjust", "revised", "revise", "improve", "vague", "incomplete", "successful", "motivation", "performance", "persistence", "focus", "influence", "purpose", "definition", "concept", "means")) and terms:
            add("generic_failed_dimension_" + _digest(terms)[:12], "direct evidence for " + ", ".join(terms), ("direct_support",), raw_case, terms)
    priority = ("smart_components", "progress_monitoring_feedback", "progress_based_adjustment", "motivation_performance_effects", "definition_purpose") + tuple(sorted(key for key in buckets if key.startswith("generic_failed_dimension_")))
    return tuple({**buckets[key], "priority": index + 1} for index, key in enumerate(priority) if key in buckets)


def _plan_digest_payload(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in plan.items() if key not in {"plan_digest", "created_at", "updated_at", "lifecycle_state", "retrieval_claims", "sufficiency_decision", "revised_candidate_id", "revised_candidate_digest", "revised_teaching_bundle_id", "revised_teaching_bundle_digest", "pending_authority_id", "evaluator_reuse_decision", "blocked_reason"}}


def _write_revision_plan(runtime_root: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    if str(plan.get("lifecycle_state") or "") not in EVIDENCE_REVISION_STATES:
        raise ValueError("persistent_runtime_revision_plan_state_invalid")
    record = dict(plan)
    record["plan_digest"] = _digest(_plan_digest_payload(record))
    record["updated_at"] = utc_now()
    path = Path(runtime_root) / EVIDENCE_REVISION_PLAN_DIRECTORY / f"{record['revision_plan_id']}.json"
    if path.exists():
        existing = _read(path)
        if str(existing.get("plan_digest") or "") != str(record.get("plan_digest") or ""):
            blocked = {**existing, "lifecycle_state": "blocked_integrity", "blocked_reason": "revision_plan_digest_drift", "updated_at": utc_now()}
            _atomic_write(path, blocked)
            return blocked
    else:
        record.setdefault("created_at", utc_now())
    _atomic_write(path, record)
    return _read(path)


def compile_persistent_evidence_revision_plan(*, runtime_root: Path, failed_evaluation_id: str = "") -> dict[str, Any]:
    """Persist the deterministic owner for revising evidence after an honest behavioral failure."""
    context = _load_failed_revision_context(runtime_root=runtime_root, failed_evaluation_id=failed_evaluation_id)
    state, goal, candidate = context["state"], context["goal"], context["parent_candidate"]
    failed_artifact = context["failed_evaluation_artifact"]
    failed_evaluation = context["failed_evaluation"]
    failed_cases = tuple(dict(item) for item in failed_evaluation.get("content_case_results") or () if float(item.get("score") or 0.0) < 1.0)
    targets = _normalize_failed_revision_targets(failed_evaluation)
    node = dict(context.get("selected_node") or {})
    work_node_id = str(node.get("node_id") or stable_id("persistent-development-evidence-revision-node", goal["goal_id"], candidate["candidate_digest"], failed_evaluation["evaluation_id"]))
    plan_id = stable_id("persistent-evidence-revision-plan", state["runtime_id"], candidate["candidate_digest"], failed_evaluation["evaluation_id"], str(failed_artifact.get("artifact_digest") or ""))
    path = Path(runtime_root) / EVIDENCE_REVISION_PLAN_DIRECTORY / f"{plan_id}.json"
    if path.exists():
        return _read(path)
    direct = dict(candidate.get("direct_provenance") or {})
    source_locator = ""
    source_artifact_id = str(direct.get("source_artifact_id") or "")
    source_path = Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{source_artifact_id}.json"
    if source_path.exists():
        source_locator = str(_read(source_path).get("canonical_locator") or "")
    plan = {
        "schema": "persistent_evidence_revision_plan_v1",
        "revision_plan_id": plan_id,
        "runtime_id": state["runtime_id"],
        "root_goal_id": goal["goal_id"],
        "selected_work_node_id": work_node_id,
        "parent_candidate_id": candidate["candidate_id"],
        "parent_candidate_digest": candidate["candidate_digest"],
        "topic": str(candidate.get("topic") or goal.get("topic") or ""),
        "target_behavior": str(candidate.get("target_behavior") or ""),
        "retrieval_strategy": {"canonical_locator": source_locator, "strategy": "target_bound_governed_retrieval_v1", "preferred_source_characteristics": ("recognized_reference", "direct_instruction", "bounded_extract")},
        "failed_learner_attempt_claim_id": str(context["failed_attempt_claim"].get("claim_id") or ""),
        "failed_learning_attempt_id": str(failed_evaluation.get("attempt_id") or ""),
        "failed_evaluation_id": str(failed_evaluation.get("evaluation_id") or failed_artifact.get("artifact_id") or ""),
        "failed_evaluation_digest": str(failed_evaluation.get("evaluation_digest") or failed_artifact.get("artifact_digest") or ""),
        "failed_evaluation_artifact_digest": str(failed_artifact.get("artifact_digest") or ""),
        "sealed_package_id": str(context["sealed_package"].get("sealed_package_id") or ""),
        "sealed_package_digest": str(context["sealed_package_digest"] or ""),
        "execution_view_id": str(context["execution_view"].get("artifact_id") or ""),
        "execution_view_digest": str(context["execution_view_digest"] or ""),
        "failed_case_ids": tuple(str(item.get("case_id") or "") for item in failed_cases),
        "failed_case_dimensions": tuple({
            "case_id": str(item.get("case_id") or ""),
            "kind": str(item.get("kind") or item.get("case_kind") or ""),
            "task_type": str(item.get("task_type") or ""),
            "failed_predicates": tuple(str(term) for term in item.get("failed_predicates") or ()),
            "failure_reason": str(item.get("failure_reason") or ""),
        } for item in failed_cases),
        "missing_evidence_targets": targets,
        "maximum_retrieval_count": 3,
        "retained_content_budget": {"maximum_characters_per_source": 4000, "maximum_total_characters": 12000},
        "provider_budget": 0,
        "stop_conditions": (
            "stop_before_learner_execution", "stop_before_evaluator_execution", "stop_without_provider_call",
            "stop_after_three_revision_retrievals", "stop_if_exact_evidence_insufficient",
        ),
        "lifecycle_state": "planned",
        "retrieval_claims": (),
        "created_at": utc_now(),
    }
    return _write_revision_plan(Path(runtime_root), plan)


def _revision_candidate_for_target(*, plan: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    topic = str(plan.get("topic") or "persistent revision topic")
    locator = str(dict(plan.get("retrieval_strategy") or {}).get("canonical_locator") or "")
    return {
        "candidate_id": stable_id("persistent-evidence-revision-source-candidate", plan["revision_plan_id"], target["target_id"]),
        "title": topic, "evidence_target": str(target["label"]), "canonical_locator": locator,
        "source_class": "recognized_reference", "provenance": "persistent_evidence_revision_owner",
        "bounded_extract_permitted": True, "extraction_strategy": "target_bound_governed_retrieval_v1",
        "extraction_bounds": {"maximum_characters": int(dict(plan.get("retained_content_budget") or {}).get("maximum_characters_per_source") or 4000)},
        "revision_plan_id": plan["revision_plan_id"], "revision_plan_digest": plan["plan_digest"],
        "parent_candidate_id": plan["parent_candidate_id"], "parent_candidate_digest": plan["parent_candidate_digest"],
        "failed_evaluation_id": plan["failed_evaluation_id"], "failed_evaluation_digest": plan["failed_evaluation_digest"],
    }


def _revision_mapping_for_source(*, runtime_root: Path, source_artifact: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    text = str(source_artifact.get("retained_text") or "")
    target_id = str(target.get("target_id") or "")
    accepted: list[dict[str, Any]] = []
    examined: list[dict[str, Any]] = []
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", text), start=1):
        clean = " ".join(sentence.split())
        if not clean:
            continue
        accepted_rule = _accept_revision_excerpt(target, clean)
        if accepted_rule:
            facet, reason = accepted_rule
            accepted.append({"facet": facet, "semantic_role": facet, "evidence_target": target["label"], "target_id": target_id, "text": clean, "boundary": f"sentence:{index}", "reason": reason})
            examined.append({"boundary": f"sentence:{index}", "text": clean, "decision": "accepted", "facet": facet, "reason": reason})
        else:
            examined.append({"boundary": f"sentence:{index}", "text": clean, "decision": "rejected", "reason": f"no_direct_{target_id}_support"})
    payload = {
        "schema": "persistent_evidence_revision_excerpt_mapping_v1",
        "source_artifact_id": str(source_artifact["artifact_id"]),
        "source_artifact_digest": str(source_artifact["artifact_digest"]),
        "revision_plan_id": str(source_artifact.get("revision_plan_id") or ""),
        "selected_core_concept": str(target["label"]),
        "target_id": target_id,
        "normalized_facets": tuple(target.get("normalized_facets") or ()),
        "mapper_version": "persistent_revision_sentence_role_mapper_v1",
        "examined_sentences": tuple(examined),
        "accepted_excerpts": tuple(accepted),
        "rejected_excerpt_count": sum(item["decision"] == "rejected" for item in examined),
    }
    artifact_id = stable_id("persistent-development-excerpt-mapping", source_artifact["artifact_id"], target_id, "evidence_revision")
    return _write_immutable_artifact(runtime_root=runtime_root, directory=MAPPING_ARTIFACT_DIRECTORY, artifact_id=artifact_id, payload=payload)


def _accept_revision_excerpt(target: Mapping[str, Any], sentence: str) -> tuple[str, str] | None:
    """The sole semantic admission rule for mappings, sufficiency, and learner bundles."""
    target_id, text = str(target.get("target_id") or ""), sentence.lower()
    if not sentence.strip() or sentence.strip().endswith(":"):
        return None
    if target_id == "smart_components":
        if all(term in text for term in ("specific", "measurable")) and any(term in text for term in ("achievable", "attainable", "realistic")) and "relevant" in text and ("time-bound" in text or "time bound" in text or "timely" in text):
            return ("component", "explicit_smart_component_relation")
    if target_id == "progress_monitoring_feedback":
        relation = r"\b(monitor(?:ed|ing)?|measure(?:d|ment)?|review(?:ed|ing)?|check(?:ed|ing)?|track(?:ed|ing)?)\b"
        if re.search(rf"\b(progress|performance)\b[^.!?]{{0,80}}{relation}|{relation}[^.!?]{{0,80}}\b(progress|performance)\b", text) or re.search(r"\bfeedback\b[^.!?]{0,80}\b(use[ds]?|assess(?:es|ed|ing)?|compare[ds]?|review(?:s|ed|ing)?)\b[^.!?]{0,80}\b(progress|performance|target|goal|standard)\b", text):
            return ("monitoring", "explicit_monitoring_or_feedback_relation")
    if target_id == "progress_based_adjustment":
        if re.search(r"\b(adjust|adjustment|revise|revision|modify|change)\b[^.!?]{0,80}\b(progress|performance|feedback|monitoring|results|observed)\b|\b(progress|performance|feedback|monitoring|results|observed)\b[^.!?]{0,80}\b(adjust|adjustment|revise|revision|modify|change)\b", text):
            return ("adjustment", "explicit_adjustment_based_on_observation_relation")
    if target_id == "motivation_performance_effects":
        if any(term in text for term in ("motivation", "persistence", "focus")) and "performance" in text:
            return ("outcome_relation", "explicit_motivation_performance_relation")
    if target_id == "definition_purpose":
        if re.search(r"\b(is|means|refers to|involves)\b", text) and any(term in text for term in ("purpose", "motivate", "guide", "focus")):
            return ("definition", "explicit_definition_and_purpose_relation")
    terms = tuple(str(term).lower() for term in target.get("evidence_terms") or () if str(term).strip())
    if terms and any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms) and re.search(r"\b(is|are|use|choose|apply|compare|determine|means|when|if)\b", text):
        return ("direct_support", "explicit_generic_target_relation")
    return None


def _target_is_satisfied(target_id: str | Mapping[str, Any], excerpts: Sequence[Mapping[str, Any]]) -> bool:
    target = dict(target_id) if isinstance(target_id, Mapping) else {"target_id": target_id}
    target_name = str(target.get("target_id") or "")
    text = " ".join(str(item.get("text") or "").lower() for item in excerpts)
    if target_name == "smart_components":
        return all(term in text for term in ("specific", "measurable")) and any(term in text for term in ("achievable", "attainable", "realistic")) and "relevant" in text and ("time-bound" in text or "time bound" in text or "timely" in text)
    return any(_accept_revision_excerpt(target, str(item.get("text") or "")) for item in excerpts)


def _evaluate_revision_evidence(*, runtime_root: Path, plan: Mapping[str, Any], claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    support: dict[str, list[dict[str, Any]]] = {str(target["target_id"]): [] for target in plan.get("missing_evidence_targets") or ()}
    rejected: list[dict[str, Any]] = []
    for claim in claims:
        if str(claim.get("claim_state") or "") != "completed" or not claim.get("source_artifact_id") or not claim.get("excerpt_mapping_id"):
            rejected.append({"claim_id": claim.get("claim_id"), "reason": "claim_not_completed_with_reviewable_artifacts"})
            continue
        mapping = _read(Path(runtime_root) / MAPPING_ARTIFACT_DIRECTORY / f"{claim['excerpt_mapping_id']}.json")
        target_id = str(claim.get("evidence_revision_target_id") or mapping.get("target_id") or "")
        target = next((dict(item) for item in plan.get("missing_evidence_targets") or () if str(item.get("target_id") or "") == target_id), {"target_id": target_id})
        excerpts = tuple(dict(item) for item in mapping.get("accepted_excerpts") or () if _accept_revision_excerpt(target, str(item.get("text") or "")))
        if not excerpts:
            rejected.append({"claim_id": claim.get("claim_id"), "target_id": target_id, "reason": "no_exact_accepted_excerpts"})
        support.setdefault(target_id, []).extend(excerpts)
    required = tuple(str(target.get("target_id") or "") for target in plan.get("missing_evidence_targets") or ())[:int(plan.get("maximum_retrieval_count") or 3)]
    target_specs = {str(target.get("target_id") or ""): dict(target) for target in plan.get("missing_evidence_targets") or ()}
    resolved = tuple(target_id for target_id, excerpts in support.items() if _target_is_satisfied(target_specs.get(target_id, {"target_id": target_id}), excerpts))
    unresolved = tuple(target_id for target_id in required if target_id not in resolved)
    decision = {
        "schema": "persistent_evidence_revision_sufficiency_decision_v1",
        "revision_plan_id": plan["revision_plan_id"],
        "required_targets": required,
        "resolved_targets": resolved,
        "unresolved_targets": unresolved,
        "supporting_excerpts": tuple({"target_id": target_id, "excerpts": tuple(excerpts)} for target_id, excerpts in sorted(support.items())),
        "rejected_evidence": tuple(rejected),
        "evidence_sufficient": not unresolved,
    }
    decision["decision_digest"] = _digest(decision)
    return decision


def _compile_revision_learner_bundle(*, runtime_root: Path, plan: Mapping[str, Any], candidate: Mapping[str, Any], claims: Sequence[Mapping[str, Any]], decision: Mapping[str, Any]) -> dict[str, Any]:
    resources = []
    for claim in claims:
        if str(claim.get("claim_state") or "") != "completed" or not claim.get("source_artifact_id") or not claim.get("excerpt_mapping_id"):
            continue
        source = _read(Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{claim['source_artifact_id']}.json")
        mapping = _read(Path(runtime_root) / MAPPING_ARTIFACT_DIRECTORY / f"{claim['excerpt_mapping_id']}.json")
        selected = {(str(item.get("target_id") or ""), str(excerpt.get("boundary") or ""), str(excerpt.get("text") or "")) for item in decision.get("supporting_excerpts") or () for excerpt in item.get("excerpts") or ()}
        excerpts = tuple({"text": item["text"], "boundary": item["boundary"], "facet": item.get("facet"), "target_id": item.get("target_id")} for item in mapping.get("accepted_excerpts") or () if (str(item.get("target_id") or ""), str(item.get("boundary") or ""), str(item.get("text") or "")) in selected)
        if not excerpts:
            continue
        resources.append({
            "resource_id": source["artifact_id"], "topic": str(mapping.get("selected_core_concept") or candidate.get("topic") or ""),
            "supports_dimensions": tuple(sorted({str(item.get("target_id") or "") for item in excerpts} - {""})),
            "learner_visible_excerpts": excerpts,
            "source_artifact_id": source["artifact_id"], "source_artifact_digest": source["artifact_digest"],
            "excerpt_mapping_id": mapping["artifact_id"], "excerpt_mapping_digest": mapping["artifact_digest"],
        })
    bundle = {
        "schema": "persistent_revised_learner_visible_bundle_v1",
        "bundle_id": stable_id("persistent-learner-visible-bundle", candidate["candidate_digest"], plan["plan_digest"]),
        "revision_plan_id": plan["revision_plan_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "study_resources": tuple(resources),
        "scope_limits": tuple(candidate.get("unresolved_limits") or ()),
        "evaluator_only_material_excluded": True,
    }
    bundle["bundle_digest"] = _digest(bundle)
    return _write_immutable_artifact(runtime_root=runtime_root, directory=LEARNER_BUNDLE_DIRECTORY, artifact_id=bundle["bundle_id"], payload=bundle)


def _compile_revised_candidate(*, plan: Mapping[str, Any], parent_candidate: Mapping[str, Any], decision: Mapping[str, Any], claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_refs = tuple({
        "retrieval_claim_id": claim["claim_id"],
        "source_artifact_id": claim.get("source_artifact_id", ""),
        "source_artifact_digest": claim.get("source_artifact_digest", ""),
        "excerpt_mapping_id": claim.get("excerpt_mapping_id", ""),
        "excerpt_mapping_digest": claim.get("excerpt_mapping_digest", ""),
        "target_id": claim.get("evidence_revision_target_id", ""),
    } for claim in claims if str(claim.get("claim_state") or "") == "completed" and claim.get("source_artifact_id"))
    candidate = {
        "candidate_id": stable_id("persistent-development-candidate", plan["revision_plan_id"], "revision", plan["parent_candidate_digest"]),
        "candidate_version": int(parent_candidate.get("candidate_version") or 1) + 1,
        "topic": str(parent_candidate.get("topic") or plan.get("topic") or "persistent revision topic"),
        "parent_goal_topic": str(parent_candidate.get("parent_goal_topic") or ""),
        "scoped_claim": str(parent_candidate.get("scoped_claim") or "source-grounded revised candidate"),
        "target_behavior": str(parent_candidate.get("target_behavior") or plan.get("target_behavior") or "explain and apply retained evidence"),
        "required_evidence_facets": tuple(sorted({facet for target in plan.get("missing_evidence_targets") or () for facet in target.get("normalized_facets") or ()})),
        "parent_candidate_id": plan["parent_candidate_id"],
        "parent_candidate_digest": plan["parent_candidate_digest"],
        "revision_plan_id": plan["revision_plan_id"],
        "revision_plan_digest": plan["plan_digest"],
        "revision_sequence": 1,
        "revision_reason": "candidate_revision_required_after_insufficient_retained_teaching_evidence",
        "failed_attempt_claim_id": plan["failed_learner_attempt_claim_id"],
        "failed_evaluation_id": plan["failed_evaluation_id"],
        "failed_evaluation_digest": plan["failed_evaluation_digest"],
        "direct_provenance": {"kind": "evidence_revision", "source_artifacts": source_refs},
        "derived_provenance": (),
        "supported_facets": tuple(decision.get("resolved_targets") or ()),
        "unresolved_facets": tuple(decision.get("unresolved_targets") or ()),
        "unresolved_limits": ("revised candidate is scoped to retained source excerpts and sealed reevaluation only",),
        "trusted_admission": False,
        "capability_promotion": False,
    }
    candidate["candidate_digest"] = _digest(candidate)
    return candidate


def _compile_evaluator_reuse_decision(*, runtime_root: Path, plan: Mapping[str, Any], candidate: Mapping[str, Any], sealed_package: Mapping[str, Any]) -> dict[str, Any]:
    cases = tuple(dict(item) for item in sealed_package.get("sealed_evaluation_cases") or ())
    expected_case_ids = tuple(plan.get("failed_case_ids") or ())
    actual_case_ids = tuple(str(item.get("case_id") or "") for item in cases)
    target_capabilities = {str(item.get("target_capability") or item.get("capability_dimension") or "") for item in cases}
    accepted = bool(cases) and actual_case_ids == expected_case_ids and len(target_capabilities - {""}) == 1
    if str(candidate.get("target_behavior") or "") != str(plan.get("target_behavior") or candidate.get("target_behavior") or ""):
        accepted = False
    decision = {
        "schema": "persistent_evaluator_reuse_decision_v1",
        "decision_id": stable_id("persistent-evaluator-reuse-decision", plan["revision_plan_id"], candidate["candidate_digest"], plan["sealed_package_digest"]),
        "revision_plan_id": plan["revision_plan_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "sealed_package_id": plan["sealed_package_id"],
        "sealed_package_digest": plan["sealed_package_digest"],
        "execution_view_digest": plan["execution_view_digest"],
        "reuse_valid": accepted,
        "reasons": ("teaching_evidence_changed_only", "sealed_case_ids_unchanged", "criteria_unchanged", "candidate_binding_external") if accepted else ("binding_drift_or_scope_mismatch",),
    }
    decision["decision_digest"] = _digest(decision)
    return _write_immutable_artifact(runtime_root=runtime_root, directory=EVALUATOR_REUSE_DECISION_DIRECTORY, artifact_id=decision["decision_id"], payload=decision)


def _compile_evidence_revision_evaluator_binding(*, runtime_root: Path, state: Mapping[str, Any], goal: Mapping[str, Any], plan: Mapping[str, Any], candidate: Mapping[str, Any], bundle: Mapping[str, Any], reuse_decision: Mapping[str, Any], sealed_package: Mapping[str, Any]) -> dict[str, Any]:
    """Bind revised evidence externally; the historical evaluator request stays immutable."""
    case_ids = tuple(str(item.get("case_id") or "") for item in sealed_package.get("sealed_evaluation_cases") or ())
    binding = {
        "schema": "persistent_evidence_revision_evaluator_binding_v1",
        "binding_id": stable_id("persistent-evidence-revision-evaluator-binding", plan["revision_plan_id"], candidate["candidate_digest"], bundle["bundle_digest"], plan["sealed_package_digest"]),
        "runtime_id": state["runtime_id"], "root_goal_id": goal["goal_id"], "work_node_id": plan["selected_work_node_id"],
        "revision_plan_id": plan["revision_plan_id"], "revision_plan_digest": plan["plan_digest"],
        "candidate_id": candidate["candidate_id"], "candidate_digest": candidate["candidate_digest"],
        "parent_candidate_id": plan["parent_candidate_id"], "parent_candidate_digest": plan["parent_candidate_digest"],
        "learner_visible_bundle_id": bundle["bundle_id"], "learner_visible_bundle_digest": bundle["bundle_digest"],
        "failed_attempt_claim_id": plan["failed_learner_attempt_claim_id"], "failed_learning_attempt_id": plan["failed_learning_attempt_id"],
        "failed_evaluation_id": plan["failed_evaluation_id"], "failed_evaluation_digest": plan["failed_evaluation_digest"],
        "sealed_package_id": plan["sealed_package_id"], "sealed_package_digest": plan["sealed_package_digest"],
        "execution_view_id": plan["execution_view_id"], "execution_view_digest": plan["execution_view_digest"],
        "sealed_case_ids": case_ids, "evaluator_criteria_digest": _digest(tuple(dict(item).get("evaluator_view") or {} for item in sealed_package.get("sealed_evaluation_cases") or ())),
        "reuse_decision_id": reuse_decision["decision_id"], "reuse_decision_digest": reuse_decision["decision_digest"],
        "maximum_learner_attempts": 1, "maximum_independent_evaluations": 1, "lifecycle_state": "pending_authority", "created_at": utc_now(),
    }
    binding["binding_digest"] = _digest(binding)
    return _write_immutable_artifact(runtime_root=runtime_root, directory=EVIDENCE_REVISION_BINDING_DIRECTORY, artifact_id=binding["binding_id"], payload=binding)


def _compile_evidence_revision_retry_authority(*, runtime_root: Path, state: Mapping[str, Any], goal: Mapping[str, Any], plan: Mapping[str, Any], candidate: Mapping[str, Any], bundle: Mapping[str, Any], reuse_decision: Mapping[str, Any], binding: Mapping[str, Any], claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    authority_id = stable_id("persistent-evidence-revision-reevaluation-authority", binding["binding_digest"])
    approval_token = "approve_persistent_evidence_revision_retry_" + stable_id("scope", plan["revision_plan_id"], candidate["candidate_digest"])[-16:]
    payload = {
        "schema": "persistent_evidence_revision_reevaluation_authority_v1",
        "request_id": authority_id,
        "status": "pending_operator_approval",
        "recommended_approval_token": approval_token,
        "runtime_id": state["runtime_id"],
        "goal_id": goal["goal_id"],
        "work_node_id": plan["selected_work_node_id"],
        "revision_plan_id": plan["revision_plan_id"],
        "revision_plan_digest": plan["plan_digest"],
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "parent_candidate_id": plan["parent_candidate_id"],
        "parent_candidate_digest": plan["parent_candidate_digest"],
        "failed_attempt_claim_id": plan["failed_learner_attempt_claim_id"],
        "failed_evaluation_id": plan["failed_evaluation_id"],
        "source_artifacts": tuple({"source_artifact_id": claim.get("source_artifact_id", ""), "source_artifact_digest": claim.get("source_artifact_digest", "")} for claim in claims if claim.get("source_artifact_id")),
        "mapping_artifacts": tuple({"excerpt_mapping_id": claim.get("excerpt_mapping_id", ""), "excerpt_mapping_digest": claim.get("excerpt_mapping_digest", "")} for claim in claims if claim.get("excerpt_mapping_id")),
        "learner_visible_bundle_id": bundle["bundle_id"],
        "learner_visible_bundle_digest": bundle["bundle_digest"],
        "sealed_package_id": plan["sealed_package_id"],
        "sealed_package_digest": plan["sealed_package_digest"],
        "execution_view_digest": plan["execution_view_digest"],
        "evaluator_reuse_decision_id": reuse_decision["decision_id"],
        "evaluator_reuse_decision_digest": reuse_decision["decision_digest"],
        "evaluator_binding_id": binding["binding_id"], "evaluator_binding_digest": binding["binding_digest"],
        "maximum_learner_attempts": 1,
        "maximum_independent_evaluations": 1,
        "prohibited_actions": ("evaluator_authoring_provider_call", "trusted_admission", "capability_promotion", "runtime_mutation", "tracked_source_mutation", "overnight_worker_restart"),
        "created_at": utc_now(),
    }
    return _write_immutable_artifact(runtime_root=runtime_root, directory="learning_retry_authorities", artifact_id=authority_id, payload=payload)


def _validate_evidence_revision_provenance(*, runtime_root: Path, plan: Mapping[str, Any], candidate: Mapping[str, Any], bundle: Mapping[str, Any]) -> None:
    """Validate the plan-mediated multi-source chain without weakening legacy candidates."""
    if str(candidate.get("revision_plan_id") or "") != str(plan["revision_plan_id"]) or str(candidate.get("revision_plan_digest") or "") != str(plan["plan_digest"]):
        raise ValueError("persistent_runtime_revision_candidate_plan_binding_invalid")
    source_refs = tuple(dict(item) for item in dict(candidate.get("direct_provenance") or {}).get("source_artifacts") or ())
    resources = tuple(dict(item) for item in bundle.get("study_resources") or ())
    if not source_refs or len(resources) != len(source_refs):
        raise ValueError("persistent_runtime_revision_bundle_artifact_set_invalid")
    claims = {str(item.get("claim_id") or ""): dict(item) for item in plan.get("retrieval_claims") or ()}
    resource_keys = {(str(item.get("source_artifact_id") or ""), str(item.get("excerpt_mapping_id") or "")) for item in resources}
    reference_keys = {(str(item.get("source_artifact_id") or ""), str(item.get("excerpt_mapping_id") or "")) for item in source_refs}
    if resource_keys != reference_keys:
        raise ValueError("persistent_runtime_revision_bundle_precision_invalid")
    for ref in source_refs:
        claim = claims.get(str(ref.get("retrieval_claim_id") or ""))
        if not claim or str(claim.get("claim_state") or "") != "completed" or str(claim.get("revision_plan_id") or "") != str(plan["revision_plan_id"]):
            raise ValueError("persistent_runtime_revision_claim_binding_invalid")
        source_path = Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{ref.get('source_artifact_id')}.json"
        mapping_path = Path(runtime_root) / MAPPING_ARTIFACT_DIRECTORY / f"{ref.get('excerpt_mapping_id')}.json"
        if not source_path.exists() or not mapping_path.exists():
            raise ValueError("persistent_runtime_revision_provenance_artifact_missing")
        source, mapping = _read(source_path), _read(mapping_path)
        resource = next((item for item in resources if str(item.get("source_artifact_id") or "") == str(ref.get("source_artifact_id") or "") and str(item.get("excerpt_mapping_id") or "") == str(ref.get("excerpt_mapping_id") or "")), {})
        if str(source.get("artifact_digest") or "") != str(ref.get("source_artifact_digest") or "") or str(mapping.get("artifact_digest") or "") != str(ref.get("excerpt_mapping_digest") or ""):
            raise ValueError("persistent_runtime_revision_provenance_digest_mismatch")
        if str(resource.get("source_artifact_digest") or "") != str(ref.get("source_artifact_digest") or "") or str(resource.get("excerpt_mapping_digest") or "") != str(ref.get("excerpt_mapping_digest") or ""):
            raise ValueError("persistent_runtime_revision_bundle_digest_chain_invalid")
        if str(source.get("revision_plan_id") or "") != str(plan["revision_plan_id"]) or str(source.get("failed_evaluation_id") or "") != str(plan["failed_evaluation_id"]):
            raise ValueError("persistent_runtime_revision_source_binding_invalid")
        if str(mapping.get("source_artifact_id") or "") != str(source.get("artifact_id") or "") or str(mapping.get("revision_plan_id") or "") != str(plan["revision_plan_id"]):
            raise ValueError("persistent_runtime_revision_mapping_binding_invalid")
        if str(claim.get("source_artifact_id") or "") != str(source.get("artifact_id") or "") or str(claim.get("excerpt_mapping_id") or "") != str(mapping.get("artifact_id") or ""):
            raise ValueError("persistent_runtime_revision_claim_artifact_mismatch")
    if any("evaluator" in json.dumps(resource, sort_keys=True).lower() or "rubric" in json.dumps(resource, sort_keys=True).lower() for resource in resources):
        raise ValueError("persistent_runtime_revision_bundle_evaluator_material_leaked")


def preflight_persistent_evidence_revision_execution(*, runtime_root: Path, authority_id: str, approval_token: str) -> dict[str, Any]:
    """Consume one revised reevaluation authority through validation only; never execute learning."""
    authority = _read(Path(runtime_root) / "learning_retry_authorities" / f"{authority_id}.json")
    if str(authority.get("schema") or "") != "persistent_evidence_revision_reevaluation_authority_v1" or approval_token != str(authority.get("recommended_approval_token") or ""):
        raise ValueError("persistent_runtime_revision_authority_approval_invalid")
    state = initialize_runtime(runtime_root=runtime_root)
    claim_id = stable_id("persistent-evidence-revision-execution-claim", authority_id, authority["artifact_digest"])
    claim_path = Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{claim_id}.json"
    if claim_path.exists():
        return {"status": "preflight_replay_suppressed", "execution_claim": _read(claim_path)}
    goal = next((dict(item) for item in state.get("goals") or () if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id), None)
    if goal is None:
        raise ValueError("persistent_runtime_revision_authority_goal_missing")
    pending = dict(goal.get("pending_evidence_revision_authority") or {})
    if str(pending.get("status") or "") != "pending_operator_approval":
        raise ValueError("persistent_runtime_revision_authority_not_pending")
    binding = _read(Path(runtime_root) / EVIDENCE_REVISION_BINDING_DIRECTORY / f"{authority.get('evaluator_binding_id')}.json")
    if str(binding.get("binding_digest") or "") != str(authority.get("evaluator_binding_digest") or ""):
        raise ValueError("persistent_runtime_revision_binding_digest_mismatch")
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    if not candidate or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or "") or str(binding.get("candidate_digest") or "") != str(authority.get("candidate_digest") or ""):
        raise ValueError("persistent_runtime_revision_candidate_binding_invalid")
    plan = _read(Path(runtime_root) / EVIDENCE_REVISION_PLAN_DIRECTORY / f"{authority.get('revision_plan_id')}.json")
    bundle = _read(Path(runtime_root) / LEARNER_BUNDLE_DIRECTORY / f"{authority.get('learner_visible_bundle_id')}.json")
    if str(plan.get("plan_digest") or "") != str(authority.get("revision_plan_digest") or "") or str(bundle.get("bundle_digest") or "") != str(authority.get("learner_visible_bundle_digest") or ""):
        raise ValueError("persistent_runtime_revision_plan_or_bundle_digest_mismatch")
    _validate_evidence_revision_provenance(runtime_root=Path(runtime_root), plan=plan, candidate=candidate, bundle=bundle)
    context = _load_failed_revision_context(runtime_root=runtime_root, failed_evaluation_id=str(authority["failed_evaluation_id"]))
    package, view = context["sealed_package"], context["execution_view"]
    case_ids = tuple(str(item.get("case_id") or "") for item in package.get("sealed_evaluation_cases") or ())
    if str(context["sealed_package_digest"] or "") != str(authority.get("sealed_package_digest") or "") or str(view.get("artifact_digest") or "") != str(authority.get("execution_view_digest") or "") or case_ids != tuple(binding.get("sealed_case_ids") or ()):
        raise ValueError("persistent_runtime_revision_sealed_binding_invalid")
    claim = _write_immutable_artifact(runtime_root=runtime_root, directory=EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY, artifact_id=claim_id, payload={"schema": "persistent_evidence_revision_execution_preflight_v1", "authority_id": authority_id, "authority_digest": authority["artifact_digest"], "binding_id": binding["binding_id"], "binding_digest": binding["binding_digest"], "candidate_digest": candidate["candidate_digest"], "bundle_digest": bundle["bundle_digest"], "sealed_package_digest": authority["sealed_package_digest"], "execution_view_digest": authority["execution_view_digest"], "claim_state": "preflight_accepted_no_execution", "maximum_learner_attempts": 1, "maximum_independent_evaluations": 1, "created_at": utc_now()})
    goals = list(state.get("goals") or ())
    index = next(index for index, item in enumerate(goals) if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id)
    goals[index] = {**goal, "pending_evidence_revision_authority": {**pending, "status": "preflight_accepted", "execution_claim_id": claim_id}}
    _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}, runtime_root=runtime_root, reason="evidence_revision_execution_preflight_accepted_without_learner_execution")
    return {"status": "preflight_accepted_no_execution", "execution_claim": claim, "binding": binding}


def _finalize_persistent_evidence_revision_execution(
    *,
    runtime_root: Path,
    authority_id: str,
    authority: Mapping[str, Any],
    candidate: Mapping[str, Any],
    claim: Mapping[str, Any],
    attempt_artifact: Mapping[str, Any],
    evaluation_artifact: Mapping[str, Any],
    ownership_payload: Mapping[str, Any],
    boundary_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Persist the terminal result from durable attempt/evaluation artifacts."""
    attempt = dict(attempt_artifact.get("attempt") or {})
    evaluation = dict(evaluation_artifact.get("evaluation") or {})
    execution_id = str(claim["artifact_id"])
    disposition, reasons = _persistent_disposition(candidate=candidate, evaluation=evaluation)
    result_path = Path(runtime_root) / "evidence_revision_execution_results" / f"{execution_id}.json"
    if result_path.exists():
        result = _read(result_path)
    else:
        result = _write_immutable_artifact(
            runtime_root=runtime_root,
            directory="evidence_revision_execution_results",
            artifact_id=execution_id,
            payload={
                "schema": "persistent_evidence_revision_execution_result_v1",
                "execution_claim_id": execution_id,
                "execution_claim_digest": claim["artifact_digest"],
                "attempt_id": attempt["attempt_id"],
                "attempt_artifact_id": attempt_artifact["artifact_id"],
                "evaluation_id": evaluation["evaluation_id"],
                "evaluation_artifact_id": evaluation_artifact["artifact_id"],
                "disposition": disposition,
                "disposition_reasons": reasons,
                "completed_at": utc_now(),
            },
        )
    if boundary_hook:
        boundary_hook("after_terminal_result_persisted")
    current = _read(Path(runtime_root) / STATE_FILE)
    goal_index, goal = next(
        ((index, dict(item)) for index, item in enumerate(current.get("goals") or ()) if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id),
        (-1, {}),
    )
    if goal_index < 0:
        raise ValueError("persistent_runtime_revision_finalize_goal_missing")
    learning_attempts = tuple(goal.get("learning_attempts") or ())
    if not any(str(item.get("claim_id") or "") == execution_id for item in learning_attempts):
        learning_attempts = learning_attempts + ({"claim_id": execution_id, "attempt_id": attempt["attempt_id"], "artifact_id": attempt_artifact["artifact_id"], "candidate_id": candidate["candidate_id"], "status": "completed"},)
    behavioral_evaluations = tuple(goal.get("behavioral_evaluations") or ())
    if not any(str(item.get("artifact_id") or "") == str(evaluation_artifact["artifact_id"]) for item in behavioral_evaluations):
        behavioral_evaluations = behavioral_evaluations + ({"evaluation_id": evaluation["evaluation_id"], "artifact_id": evaluation_artifact["artifact_id"], "candidate_id": candidate["candidate_id"], "disposition": evaluation["disposition"]},)
    updated_goal = {
        **goal,
        "learning_attempts": learning_attempts,
        "behavioral_evaluations": behavioral_evaluations,
        "pending_evidence_revision_authority": {**dict(goal.get("pending_evidence_revision_authority") or {}), "status": "consumed_completed", "execution_result_id": result["artifact_id"]},
        "post_evaluation_disposition": {"tier": disposition, "reasons": reasons, "evaluation_id": evaluation["evaluation_id"]},
    }
    goals = list(current.get("goals") or ())
    goals[goal_index] = updated_goal
    _checkpoint(state={**current, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}, runtime_root=runtime_root, reason="evidence_revision_execution_completed_without_trust_or_promotion")
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="050-terminal", payload={**ownership_payload, "state": "terminal", "execution_result_id": result["artifact_id"], "at": utc_now()}, repair_orphaned_lock=True)
    return {"status": "execution_completed", "execution_claim": dict(claim), "execution_result": result, "attempt": attempt, "evaluation": evaluation, "disposition": disposition}


def _reconcile_persistent_evidence_revision_terminal_result(
    *,
    runtime_root: Path,
    authority_id: str,
    authority: Mapping[str, Any],
    execution_id: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    claim = _read(Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{execution_id}.json")
    if str(result.get("execution_claim_id") or "") != execution_id or str(result.get("execution_claim_digest") or "") != str(claim.get("artifact_digest") or ""):
        raise ValueError("persistent_runtime_revision_terminal_result_binding_invalid")
    attempt_artifact = _read(Path(runtime_root) / "learning_attempts" / f"{result['attempt_artifact_id']}.json")
    evaluation_artifact = _read(Path(runtime_root) / "learning_evaluations" / f"{result['evaluation_artifact_id']}.json")
    state = initialize_runtime(runtime_root=runtime_root)
    goal_index, goal = next(
        ((index, dict(item)) for index, item in enumerate(state.get("goals") or ()) if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id),
        (-1, {}),
    )
    if goal_index < 0:
        raise ValueError("persistent_runtime_revision_terminal_reconcile_goal_missing")
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    if not candidate or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or ""):
        raise ValueError("persistent_runtime_revision_terminal_reconcile_candidate_invalid")
    ownership_path = Path(runtime_root) / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id / "000-acquired.json"
    ownership_payload = _read(ownership_path) if ownership_path.exists() else {
        "schema": "persistent_evidence_revision_execution_ownership_v1",
        "execution_claim_id": execution_id,
        "authority_id": authority_id,
        "authority_digest": authority["artifact_digest"],
        "state": "terminal_reconcile_without_acquired_metadata",
    }
    reconciled = _finalize_persistent_evidence_revision_execution(
        runtime_root=runtime_root,
        authority_id=authority_id,
        authority=authority,
        candidate=candidate,
        claim=claim,
        attempt_artifact=attempt_artifact,
        evaluation_artifact=evaluation_artifact,
        ownership_payload=ownership_payload,
    )
    return {**reconciled, "status": "terminal_result_reconciled"}


def _prepare_persistent_evidence_revision_execution_materials(*, runtime_root: Path, authority: Mapping[str, Any], goal: Mapping[str, Any]) -> dict[str, Any]:
    binding = _read(Path(runtime_root) / EVIDENCE_REVISION_BINDING_DIRECTORY / f"{authority.get('evaluator_binding_id')}.json")
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    plan = _read(Path(runtime_root) / EVIDENCE_REVISION_PLAN_DIRECTORY / f"{authority.get('revision_plan_id')}.json")
    bundle = _read(Path(runtime_root) / LEARNER_BUNDLE_DIRECTORY / f"{authority.get('learner_visible_bundle_id')}.json")
    if not candidate or str(binding.get("binding_digest") or "") != str(authority.get("evaluator_binding_digest") or "") or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or "") or str(bundle.get("bundle_digest") or "") != str(authority.get("learner_visible_bundle_digest") or ""):
        raise ValueError("persistent_runtime_revision_execution_external_binding_invalid")
    _validate_evidence_revision_provenance(runtime_root=Path(runtime_root), plan=plan, candidate=candidate, bundle=bundle)
    context = _load_failed_revision_context(runtime_root=runtime_root, failed_evaluation_id=str(authority["failed_evaluation_id"]))
    package, view = context["sealed_package"], context["execution_view"]
    if str(context["sealed_package_digest"] or "") != str(authority.get("sealed_package_digest") or "") or str(view.get("artifact_digest") or "") != str(authority.get("execution_view_digest") or ""):
        raise ValueError("persistent_runtime_revision_execution_sealed_binding_invalid")
    capability = next(iter({str(item.get("capability_dimension") or item.get("target_capability") or "") for item in view.get("sealed_evaluation_cases") or ()} - {""}), "")
    if not capability:
        raise ValueError("persistent_runtime_revision_execution_capability_missing")
    resources = []
    for raw in bundle.get("study_resources") or ():
        resource = dict(raw)
        source = _read(Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{resource['source_artifact_id']}.json")
        resource["study_facts"] = tuple(item.strip() for item in re.split(r"(?<=[.!?])\s+", str(source.get("retained_text") or "")) if item.strip())
        resource["study_components"] = tuple(str(item.get("text") or "") for item in resource.get("learner_visible_excerpts") or ())
        resources.append(resource)
    retained_bundle = {"study_resources": tuple(resources), "sealed_evaluation_cases": tuple(view.get("sealed_evaluation_cases") or ()), "execution_contract_version": package.get("execution_contract_version"), "independent_evaluator": dict(package.get("independent_evaluator") or {}), "active_sealed_case_ids": tuple(binding.get("sealed_case_ids") or ())}
    if any(any(key in str(case.get("learner_view") or {}) for key in ("answer_key", "scoring_rule", "pass_threshold", "rubric")) for case in retained_bundle["sealed_evaluation_cases"]):
        raise ValueError("persistent_runtime_revision_execution_evaluator_material_leaked")
    subgoal = LearningSubgoal(subgoal_id=stable_id("persistent-evidence-revision-subgoal", str(authority["request_id"])), mission_id=stable_id("persistent-evidence-revision-mission", str(authority["request_id"])), source_gap_id=stable_id("persistent-evidence-revision-gap", str(authority["request_id"])), topic=str(candidate.get("topic") or ""), frontier_rank=1.0, selection_reason="accepted external revised-candidate evaluator binding", capability_target=capability, measurable_objective=str(candidate.get("target_behavior") or ""), baseline=0.0, success_threshold=1.0, prerequisites=(), study_resource_ids=tuple(str(item.get("resource_id") or "") for item in resources), attempt_type="guided_study_attempt", practice_specification="Use only revised learner-visible retained excerpts.", control_case_ids=(), held_out_policy="unchanged sealed cases", adversarial_policy="unchanged sealed cases", evaluation_method="existing_independent_sealed_evaluator", attempt_budget=1, resource_budget=len(resources), completion_classification="evaluation_required", next_step_policy="persist_terminal_revision_result", authority_state="preflight_accepted")
    return {"binding": binding, "candidate": candidate, "plan": plan, "bundle": bundle, "retained_bundle": retained_bundle, "subgoal": subgoal}


def execute_persistent_evidence_revision_consumer(
    *,
    runtime_root: Path,
    authority_id: str,
    boundary_hook: Callable[[str], None] | None = None,
    recovery_resume: bool = False,
) -> dict[str, Any]:
    """Consume one accepted revised preflight through the existing learner/evaluator functions."""
    authority = _read(Path(runtime_root) / "learning_retry_authorities" / f"{authority_id}.json")
    state = initialize_runtime(runtime_root=runtime_root)
    goal_index, goal = next(((index, dict(item)) for index, item in enumerate(state.get("goals") or ()) if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id), (-1, {}))
    pending = dict(goal.get("pending_evidence_revision_authority") or {})
    prior_claim_id = str(pending.get("execution_claim_id") or "")
    prior_claim_path = Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{prior_claim_id}.json"
    if prior_claim_path.exists():
        prior_claim = _read(prior_claim_path)
        execution_id = stable_id("persistent-evidence-revision-consumer-claim", authority_id, prior_claim["artifact_digest"])
        result_path = Path(runtime_root) / "evidence_revision_execution_results" / f"{execution_id}.json"
        if result_path.exists():
            reconciled = _reconcile_persistent_evidence_revision_terminal_result(runtime_root=runtime_root, authority_id=authority_id, authority=authority, execution_id=execution_id, result=_read(result_path))
            return {"status": "execution_replay_suppressed", "execution_result": reconciled["execution_result"], "reconciliation_status": reconciled["status"]}
        recovery_records = _read_transition_records(Path(runtime_root) / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id)
        if "060-recovery-classified.json" in recovery_records and not recovery_resume:
            return {"status": "execution_recovery_classified_replay_suppressed", "recovery": recovery_records["060-recovery-classified.json"]}
    if goal_index < 0 or str(pending.get("status") or "") != "preflight_accepted":
        raise ValueError("persistent_runtime_revision_execution_not_preflight_accepted")
    preflight_id = str(pending.get("execution_claim_id") or "")
    preflight = _read(Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{preflight_id}.json")
    if str(preflight.get("claim_state") or "") != "preflight_accepted_no_execution" or str(preflight.get("authority_id") or "") != authority_id or str(preflight.get("authority_digest") or "") != str(authority.get("artifact_digest") or ""):
        raise ValueError("persistent_runtime_revision_execution_preflight_binding_invalid")
    execution_id = stable_id("persistent-evidence-revision-consumer-claim", authority_id, preflight["artifact_digest"])
    result_path = Path(runtime_root) / "evidence_revision_execution_results" / f"{execution_id}.json"
    if result_path.exists():
        reconciled = _reconcile_persistent_evidence_revision_terminal_result(runtime_root=runtime_root, authority_id=authority_id, authority=authority, execution_id=execution_id, result=_read(result_path))
        return {"status": "execution_replay_suppressed", "execution_result": reconciled["execution_result"], "reconciliation_status": reconciled["status"]}
    execution_path = Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{execution_id}.json"
    if execution_path.exists() and not recovery_resume:
        raise ValueError("persistent_runtime_revision_execution_claim_incomplete_integrity_stop")
    ownership_payload = {"schema": "persistent_evidence_revision_execution_ownership_v1", "execution_claim_id": execution_id, "authority_id": authority_id, "authority_digest": authority["artifact_digest"], "preflight_claim_id": preflight_id, "preflight_claim_digest": preflight["artifact_digest"], "binding_id": authority["evaluator_binding_id"], "binding_digest": authority["evaluator_binding_digest"], "candidate_id": authority["candidate_id"], "candidate_digest": authority["candidate_digest"], "bundle_id": authority["learner_visible_bundle_id"], "bundle_digest": authority["learner_visible_bundle_digest"], "revision_plan_id": authority["revision_plan_id"], "revision_plan_digest": authority["revision_plan_digest"], "sealed_package_digest": authority["sealed_package_digest"], "execution_view_digest": authority["execution_view_digest"], "owner_process_id": os.getpid(), "acquired_at": utc_now(), "state": "acquired_not_started", "generation": 1}
    ownership_status, ownership = _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="000-acquired", payload=ownership_payload)
    if ownership_status != "acquired" and not recovery_resume:
        return {"status": "execution_owned_elsewhere", "ownership": ownership}
    if ownership_status != "acquired":
        ownership_payload = dict(ownership)
        recovery_status, recovery = _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="005-recovery-resume-before-learner", payload={**ownership, "state": "recovery_resume_before_learner", "recovery_process_id": os.getpid(), "at": utc_now()})
        if recovery_status != "acquired":
            return {"status": "execution_recovery_owned_elsewhere", "ownership": recovery}
    if boundary_hook:
        boundary_hook("after_ownership_acquired")
    binding = _read(Path(runtime_root) / EVIDENCE_REVISION_BINDING_DIRECTORY / f"{authority.get('evaluator_binding_id')}.json")
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    plan = _read(Path(runtime_root) / EVIDENCE_REVISION_PLAN_DIRECTORY / f"{authority.get('revision_plan_id')}.json")
    bundle = _read(Path(runtime_root) / LEARNER_BUNDLE_DIRECTORY / f"{authority.get('learner_visible_bundle_id')}.json")
    if not candidate or str(binding.get("binding_digest") or "") != str(authority.get("evaluator_binding_digest") or "") or str(candidate.get("candidate_digest") or "") != str(authority.get("candidate_digest") or "") or str(bundle.get("bundle_digest") or "") != str(authority.get("learner_visible_bundle_digest") or ""):
        raise ValueError("persistent_runtime_revision_execution_external_binding_invalid")
    _validate_evidence_revision_provenance(runtime_root=Path(runtime_root), plan=plan, candidate=candidate, bundle=bundle)
    if any(str(item.get("candidate_id") or "") == str(candidate["candidate_id"]) for item in goal.get("learning_attempts") or ()) or any(str(item.get("candidate_id") or "") == str(candidate["candidate_id"]) for item in goal.get("behavioral_evaluations") or ()):
        raise ValueError("persistent_runtime_revision_execution_budget_already_consumed")
    context = _load_failed_revision_context(runtime_root=runtime_root, failed_evaluation_id=str(authority["failed_evaluation_id"]))
    package, view = context["sealed_package"], context["execution_view"]
    if str(context["sealed_package_digest"] or "") != str(authority.get("sealed_package_digest") or "") or str(view.get("artifact_digest") or "") != str(authority.get("execution_view_digest") or ""):
        raise ValueError("persistent_runtime_revision_execution_sealed_binding_invalid")
    capability = next(iter({str(item.get("capability_dimension") or item.get("target_capability") or "") for item in view.get("sealed_evaluation_cases") or ()} - {""}), "")
    if not capability:
        raise ValueError("persistent_runtime_revision_execution_capability_missing")
    resources = []
    for raw in bundle.get("study_resources") or ():
        resource = dict(raw)
        source = _read(Path(runtime_root) / SOURCE_ARTIFACT_DIRECTORY / f"{resource['source_artifact_id']}.json")
        resource["study_facts"] = tuple(item.strip() for item in re.split(r"(?<=[.!?])\s+", str(source.get("retained_text") or "")) if item.strip())
        resource["study_components"] = tuple(str(item.get("text") or "") for item in resource.get("learner_visible_excerpts") or ())
        resources.append(resource)
    retained_bundle = {"study_resources": tuple(resources), "sealed_evaluation_cases": tuple(view.get("sealed_evaluation_cases") or ()), "execution_contract_version": package.get("execution_contract_version"), "independent_evaluator": dict(package.get("independent_evaluator") or {}), "active_sealed_case_ids": tuple(binding.get("sealed_case_ids") or ())}
    if any(any(key in str(case.get("learner_view") or {}) for key in ("answer_key", "scoring_rule", "pass_threshold", "rubric")) for case in retained_bundle["sealed_evaluation_cases"]):
        raise ValueError("persistent_runtime_revision_execution_evaluator_material_leaked")
    subgoal = LearningSubgoal(subgoal_id=stable_id("persistent-evidence-revision-subgoal", authority_id), mission_id=stable_id("persistent-evidence-revision-mission", authority_id), source_gap_id=stable_id("persistent-evidence-revision-gap", authority_id), topic=str(candidate.get("topic") or ""), frontier_rank=1.0, selection_reason="accepted external revised-candidate evaluator binding", capability_target=capability, measurable_objective=str(candidate.get("target_behavior") or ""), baseline=0.0, success_threshold=1.0, prerequisites=(), study_resource_ids=tuple(str(item.get("resource_id") or "") for item in resources), attempt_type="guided_study_attempt", practice_specification="Use only revised learner-visible retained excerpts.", control_case_ids=(), held_out_policy="unchanged sealed cases", adversarial_policy="unchanged sealed cases", evaluation_method="existing_independent_sealed_evaluator", attempt_budget=1, resource_budget=len(resources), completion_classification="evaluation_required", next_step_policy="persist_terminal_revision_result", authority_state="preflight_accepted")
    if execution_path.exists():
        claim = _read(execution_path)
    else:
        claim = _write_immutable_artifact(runtime_root=runtime_root, directory=EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY, artifact_id=execution_id, payload={"schema": "persistent_evidence_revision_execution_claim_v1", "authority_id": authority_id, "authority_digest": authority["artifact_digest"], "preflight_claim_id": preflight_id, "preflight_claim_digest": preflight["artifact_digest"], "binding_id": binding["binding_id"], "binding_digest": binding["binding_digest"], "candidate_id": candidate["candidate_id"], "candidate_digest": candidate["candidate_digest"], "bundle_id": bundle["bundle_id"], "bundle_digest": bundle["bundle_digest"], "revision_plan_id": plan["revision_plan_id"], "revision_plan_digest": plan["plan_digest"], "sealed_package_digest": authority["sealed_package_digest"], "execution_view_digest": authority["execution_view_digest"], "claim_state": "dispatching", "maximum_learner_attempts": 1, "maximum_independent_evaluations": 1, "created_at": utc_now()})
    if boundary_hook:
        boundary_hook("after_execution_claim_persisted")
    goals = list(state.get("goals") or ())
    goals[goal_index] = {**goal, "pending_evidence_revision_authority": {**pending, "status": "execution_dispatching", "revised_execution_claim_id": execution_id}}
    _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": goal["goal_id"], "active_work_item": {"goal_id": goal["goal_id"], "state": "evidence_revision_execution_dispatching", "claim_id": execution_id}}, runtime_root=runtime_root, reason="evidence_revision_execution_claim_persisted_before_learner_execution")
    from orchestration.runtime.developmental_learning import execute_learning_attempt, evaluate_learning_attempt
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="010-learner-dispatching", payload={**ownership_payload, "state": "learner_dispatching", "at": utc_now()})
    if boundary_hook:
        boundary_hook("after_learner_dispatching")
    attempt = execute_learning_attempt(subgoal, retained_bundle)
    attempt_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_attempts", artifact_id=attempt.attempt_id, payload={"schema": "persistent_learning_attempt_v1", "claim_id": execution_id, "revision_execution_claim_id": execution_id, "attempt": attempt.as_dict(), "response_digest": attempt.candidate_digest, "completed_at": utc_now()})
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="020-learner-persisted", payload={**ownership_payload, "state": "learner_persisted", "attempt_artifact_id": attempt_artifact["artifact_id"], "at": utc_now()})
    if boundary_hook:
        boundary_hook("after_attempt_persisted")
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="030-evaluator-dispatching", payload={**ownership_payload, "state": "evaluator_dispatching", "at": utc_now()})
    if boundary_hook:
        boundary_hook("after_evaluator_dispatching")
    evaluation = evaluate_learning_attempt(subgoal, attempt, retained_bundle)
    evaluation_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_evaluations", artifact_id=evaluation.evaluation_id, payload={"schema": "persistent_learning_evaluation_v1", "claim_id": execution_id, "revision_execution_claim_id": execution_id, "sealed_package_digest": authority["sealed_package_digest"], "learner_response_digest": attempt.candidate_digest, "evaluation": evaluation.as_dict(), "completed_at": utc_now()})
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="040-evaluation-persisted", payload={**ownership_payload, "state": "evaluation_persisted", "evaluation_artifact_id": evaluation_artifact["artifact_id"], "at": utc_now()})
    if boundary_hook:
        boundary_hook("after_evaluation_persisted")
    return _finalize_persistent_evidence_revision_execution(runtime_root=runtime_root, authority_id=authority_id, authority=authority, candidate=candidate, claim=claim, attempt_artifact=attempt_artifact, evaluation_artifact=evaluation_artifact, ownership_payload=ownership_payload, boundary_hook=boundary_hook)


def recover_persistent_evidence_revision_execution(*, runtime_root: Path, authority_id: str) -> dict[str, Any]:
    """Classify interrupted ownership conservatively; uncertain dispatches are never replayed."""
    authority = _read(Path(runtime_root) / "learning_retry_authorities" / f"{authority_id}.json")
    state = initialize_runtime(runtime_root=runtime_root)
    goal = next((dict(item) for item in state.get("goals") or () if str(dict(item.get("pending_evidence_revision_authority") or {}).get("request_id") or "") == authority_id), None)
    if goal is None:
        raise ValueError("persistent_runtime_revision_recovery_goal_missing")
    preflight_id = str(dict(goal.get("pending_evidence_revision_authority") or {}).get("execution_claim_id") or "")
    preflight = _read(Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{preflight_id}.json")
    execution_id = stable_id("persistent-evidence-revision-consumer-claim", authority_id, preflight["artifact_digest"])
    result_path = Path(runtime_root) / "evidence_revision_execution_results" / f"{execution_id}.json"
    if result_path.exists():
        reconciled = _reconcile_persistent_evidence_revision_terminal_result(runtime_root=runtime_root, authority_id=authority_id, authority=authority, execution_id=execution_id, result=_read(result_path))
        return {"status": "terminal_result_reconciled", "execution_result": reconciled["execution_result"]}
    root = Path(runtime_root) / EVIDENCE_REVISION_OWNERSHIP_DIRECTORY / execution_id
    transitions = _read_transition_records(root)
    acquired = dict(transitions.get("000-acquired.json") or {})
    candidate = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("candidate_id") or "") == str(authority.get("candidate_id") or "")), None)
    if not candidate:
        raise ValueError("persistent_runtime_revision_recovery_candidate_missing")
    if "040-evaluation-persisted.json" in transitions:
        claim_path = Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{execution_id}.json"
        if not claim_path.exists():
            _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "execution_claim_missing_after_evaluation_integrity_stop", "at": utc_now()}, repair_orphaned_lock=True)
            return {"status": "execution_claim_missing_after_evaluation_integrity_stop", "ownership": transitions}
        attempt_id = str(dict(transitions.get("020-learner-persisted.json") or {}).get("attempt_artifact_id") or "")
        evaluation_id = str(dict(transitions.get("040-evaluation-persisted.json") or {}).get("evaluation_artifact_id") or "")
        attempt_artifact = _read(Path(runtime_root) / "learning_attempts" / f"{attempt_id}.json") if attempt_id else _find_claim_artifact(runtime_root=runtime_root, directory="learning_attempts", claim_id=execution_id)
        evaluation_artifact = _read(Path(runtime_root) / "learning_evaluations" / f"{evaluation_id}.json") if evaluation_id else _find_claim_artifact(runtime_root=runtime_root, directory="learning_evaluations", claim_id=execution_id)
        if not attempt_artifact or not evaluation_artifact:
            _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "persisted_evaluation_artifacts_incomplete_integrity_stop", "at": utc_now()}, repair_orphaned_lock=True)
            return {"status": "persisted_evaluation_artifacts_incomplete_integrity_stop", "ownership": transitions}
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "finalizing_from_persisted_evaluation", "at": utc_now()}, repair_orphaned_lock=True)
        finalized = _finalize_persistent_evidence_revision_execution(runtime_root=runtime_root, authority_id=authority_id, authority=authority, candidate=candidate, claim=_read(claim_path), attempt_artifact=attempt_artifact, evaluation_artifact=evaluation_artifact, ownership_payload=acquired)
        return {**finalized, "status": "recovery_finalized_from_persisted_evaluation"}
    if "010-learner-dispatching.json" in transitions and "020-learner-persisted.json" not in transitions:
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "execution_outcome_unknown_integrity_stop", "at": utc_now()}, repair_orphaned_lock=True)
        return {"status": "execution_outcome_unknown_integrity_stop", "ownership": transitions}
    if "030-evaluator-dispatching.json" in transitions and "040-evaluation-persisted.json" not in transitions:
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "evaluation_outcome_unknown_integrity_stop", "at": utc_now()}, repair_orphaned_lock=True)
        return {"status": "evaluation_outcome_unknown_integrity_stop", "ownership": transitions}
    if "020-learner-persisted.json" in transitions and "030-evaluator-dispatching.json" not in transitions:
        claim_path = Path(runtime_root) / EVIDENCE_REVISION_EXECUTION_CLAIM_DIRECTORY / f"{execution_id}.json"
        attempt_id = str(dict(transitions.get("020-learner-persisted.json") or {}).get("attempt_artifact_id") or "")
        attempt_artifact = _read(Path(runtime_root) / "learning_attempts" / f"{attempt_id}.json") if attempt_id else _find_claim_artifact(runtime_root=runtime_root, directory="learning_attempts", claim_id=execution_id)
        if not claim_path.exists() or not attempt_artifact:
            _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "persisted_attempt_artifacts_incomplete_integrity_stop", "at": utc_now()}, repair_orphaned_lock=True)
            return {"status": "persisted_attempt_artifacts_incomplete_integrity_stop", "ownership": transitions}
        recovery_status, recovery = _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="025-recovery-resume-evaluator", payload={**acquired, "state": "recovery_resume_evaluator_from_persisted_attempt", "recovery_process_id": os.getpid(), "attempt_artifact_id": attempt_artifact["artifact_id"], "at": utc_now()})
        if recovery_status != "acquired":
            return {"status": "evaluation_recovery_owned_elsewhere", "ownership": recovery}
        materials = _prepare_persistent_evidence_revision_execution_materials(runtime_root=runtime_root, authority=authority, goal=goal)
        from orchestration.runtime.developmental_learning import evaluate_learning_attempt
        attempt = DevelopmentalAttemptRecord(**dict(attempt_artifact["attempt"]))
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="030-evaluator-dispatching", payload={**acquired, "state": "evaluator_dispatching", "at": utc_now()})
        evaluation = evaluate_learning_attempt(materials["subgoal"], attempt, materials["retained_bundle"])
        evaluation_artifact = _write_immutable_artifact(runtime_root=runtime_root, directory="learning_evaluations", artifact_id=evaluation.evaluation_id, payload={"schema": "persistent_learning_evaluation_v1", "claim_id": execution_id, "revision_execution_claim_id": execution_id, "sealed_package_digest": authority["sealed_package_digest"], "learner_response_digest": attempt.candidate_digest, "evaluation": evaluation.as_dict(), "completed_at": utc_now()})
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="040-evaluation-persisted", payload={**acquired, "state": "evaluation_persisted", "evaluation_artifact_id": evaluation_artifact["artifact_id"], "at": utc_now()})
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "finalizing_after_evaluator_resume", "at": utc_now()}, repair_orphaned_lock=True)
        finalized = _finalize_persistent_evidence_revision_execution(runtime_root=runtime_root, authority_id=authority_id, authority=authority, candidate=materials["candidate"], claim=_read(claim_path), attempt_artifact=attempt_artifact, evaluation_artifact=evaluation_artifact, ownership_payload=acquired)
        return {**finalized, "status": "recovery_resumed_evaluation_from_persisted_attempt"}
    if "000-acquired.json" in transitions and "010-learner-dispatching.json" not in transitions:
        _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "safe_resume_before_learner", "at": utc_now()}, repair_orphaned_lock=True)
        resumed = execute_persistent_evidence_revision_consumer(runtime_root=runtime_root, authority_id=authority_id, recovery_resume=True)
        return {**resumed, "status": "recovery_resumed_before_learner"}
    _exclusive_transition(runtime_root=runtime_root, execution_id=execution_id, sequence="060-recovery-classified", payload={**acquired, "state": "incomplete_dispatch_recovery_required", "at": utc_now()}, repair_orphaned_lock=True)
    return {"status": "incomplete_dispatch_recovery_required", "ownership": transitions}


def run_persistent_evidence_revision_cycle(
    *, runtime_root: Path, failed_evaluation_id: str = "",
    retrieval_executor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one bounded evidence-revision gate and stop before learner execution."""
    context = _load_failed_revision_context(runtime_root=runtime_root, failed_evaluation_id=failed_evaluation_id)
    state, goal, parent_candidate = context["state"], context["goal"], context["parent_candidate"]
    plan = compile_persistent_evidence_revision_plan(runtime_root=runtime_root, failed_evaluation_id=failed_evaluation_id)
    if str(plan.get("lifecycle_state") or "") in {"reevaluation_pending", "evidence_insufficient", "blocked_integrity"}:
        return {"status": str(plan["lifecycle_state"]), "revision_plan": plan, "retrieval_claims": tuple(plan.get("retrieval_claims") or ())}
    claims = [dict(item) for item in plan.get("retrieval_claims") or ()]
    existing_targets = {str(item.get("evidence_revision_target_id") or "") for item in claims}
    targets = tuple(dict(item) for item in plan.get("missing_evidence_targets") or () if str(item.get("target_id") or "") not in existing_targets)[: max(0, int(plan.get("maximum_retrieval_count") or 3) - len(claims))]
    executor = retrieval_executor or _default_retrieval_executor
    for target in targets:
        selected = _revision_candidate_for_target(plan=plan, target=target)
        fingerprint = _digest({"revision_plan_id": plan["revision_plan_id"], "target_id": target["target_id"], "locator": selected["canonical_locator"], "strategy": selected["extraction_strategy"]})
        claim = {
            "claim_id": stable_id("persistent-evidence-revision-retrieval-claim", state["runtime_id"], plan["revision_plan_id"], fingerprint),
            "goal_id": goal["goal_id"], "frontier_id": str(goal.get("frontiers", [{}])[0].get("frontier_id") or goal["goal_id"]),
            "candidate_id": selected["candidate_id"], "canonical_locator": selected["canonical_locator"],
            "candidate_fingerprint": _digest(selected), "query_fingerprint": fingerprint,
            "source_identity_digest": _digest({"canonical_locator": selected["canonical_locator"]}),
            "unresolved_facet": "_".join(target.get("normalized_facets") or ()), "extraction_strategy": selected["extraction_strategy"],
            "extraction_bounds": dict(selected.get("extraction_bounds") or {}), "strategy_fingerprint": fingerprint,
            "claim_state": "dispatching", "attempt_count": 1, "created_at": utc_now(),
            "revision_plan_id": plan["revision_plan_id"], "revision_plan_digest": plan["plan_digest"],
            "evidence_revision_target_id": target["target_id"], "evidence_revision_target": target["label"],
            "preferred_source_characteristics": ("recognized_reference", "direct_goal_setting_instruction", "bounded_extract"),
            "provider_budget": int(plan.get("provider_budget") or 0),
            "parent_candidate_id": plan["parent_candidate_id"], "parent_candidate_digest": plan["parent_candidate_digest"],
            "failed_evaluation_id": plan["failed_evaluation_id"], "failed_evaluation_digest": plan["failed_evaluation_digest"],
        }
        claims.append(claim)
        plan = _write_revision_plan(Path(runtime_root), {**plan, "lifecycle_state": "retrieving", "retrieval_claims": tuple(claims)})
        goals = list(state.get("goals") or ())
        goal_claims = tuple(goal.get("retrieval_claims") or ())
        goal = {**goal, "retrieval_claims": tuple((*goal_claims, claim))}
        goals[context["goal_index"]] = goal
        _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": goal["goal_id"], "active_work_item": {"goal_id": goal["goal_id"], "state": "evidence_revision_retrieval_dispatching", "claim_id": claim["claim_id"]}}, runtime_root=runtime_root, reason="evidence_revision_retrieval_claim_persisted_before_dispatch")
        state = _read(Path(runtime_root) / STATE_FILE)
        try:
            retrieval = dict(executor(selected))
            content = str(retrieval.pop("content_text") or "")
            source_artifact = _persist_source_artifact(runtime_root=runtime_root, runtime_id=str(state["runtime_id"]), goal=goal, claim=claim, retrieval=retrieval, retained_text=content)
            source_artifact = {**source_artifact, "revision_plan_id": plan["revision_plan_id"]}
            mapping = _revision_mapping_for_source(runtime_root=Path(runtime_root), source_artifact=source_artifact, target=target)
            completed = {**claim, "claim_state": "completed", "completed_at": utc_now(), "canonical_locator": str(retrieval.get("canonical_locator") or selected["canonical_locator"]), "source_digest": source_artifact["source_digest"], "extraction_digest": source_artifact["extraction_digest"], "source_artifact_id": source_artifact["artifact_id"], "source_artifact_path": source_artifact["artifact_path"], "source_artifact_digest": source_artifact["artifact_digest"], "excerpt_mapping_id": mapping["artifact_id"], "excerpt_mapping_path": mapping["artifact_path"], "excerpt_mapping_digest": mapping["artifact_digest"], "mapped_excerpt_count": len(mapping.get("accepted_excerpts") or ())}
        except Exception as exc:
            completed = {**claim, "claim_state": "failed", "completed_at": utc_now(), "failure_reason": f"{type(exc).__name__}:{str(exc)[:240]}"}
        claims[-1] = completed
        goal = {**goal, "retrieval_claims": tuple((*tuple(goal.get("retrieval_claims") or ())[:-1], completed))}
        goals = list(state.get("goals") or ())
        goals[context["goal_index"]] = goal
        state = {**state, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}
        _checkpoint(state=state, runtime_root=runtime_root, reason="evidence_revision_retrieval_completed")
        state = _read(Path(runtime_root) / STATE_FILE)
        plan = _write_revision_plan(Path(runtime_root), {**plan, "retrieval_claims": tuple(claims)})
    decision = _evaluate_revision_evidence(runtime_root=Path(runtime_root), plan=plan, claims=claims)
    if not decision["evidence_sufficient"]:
        plan = _write_revision_plan(Path(runtime_root), {**plan, "lifecycle_state": "evidence_insufficient", "sufficiency_decision": decision})
        return {"status": "evidence_insufficient", "revision_plan": plan, "retrieval_claims": tuple(claims), "sufficiency_decision": decision}
    plan = _write_revision_plan(Path(runtime_root), {**plan, "lifecycle_state": "evidence_sufficient", "sufficiency_decision": decision})
    existing = next((dict(item) for item in goal.get("candidate_versions") or () if str(item.get("revision_plan_id") or "") == plan["revision_plan_id"]), None)
    candidate = existing or _compile_revised_candidate(plan=plan, parent_candidate=parent_candidate, decision=decision, claims=claims)
    bundle = _compile_revision_learner_bundle(runtime_root=Path(runtime_root), plan=plan, candidate=candidate, claims=claims, decision=decision)
    reuse = _compile_evaluator_reuse_decision(runtime_root=Path(runtime_root), plan=plan, candidate=candidate, sealed_package=context["sealed_package"])
    if not reuse["reuse_valid"]:
        plan = _write_revision_plan(Path(runtime_root), {**plan, "lifecycle_state": "candidate_revised", "revised_candidate_id": candidate["candidate_id"], "revised_candidate_digest": candidate["candidate_digest"], "revised_teaching_bundle_id": bundle["bundle_id"], "revised_teaching_bundle_digest": bundle["bundle_digest"], "evaluator_reuse_decision": reuse})
        return {"status": "evaluator_reauthoring_required", "revision_plan": plan, "revised_candidate": candidate, "learner_visible_bundle": bundle, "evaluator_reuse_decision": reuse}
    binding = _compile_evidence_revision_evaluator_binding(runtime_root=Path(runtime_root), state=state, goal=goal, plan=plan, candidate=candidate, bundle=bundle, reuse_decision=reuse, sealed_package=context["sealed_package"])
    authority = _compile_evidence_revision_retry_authority(runtime_root=Path(runtime_root), state=state, goal=goal, plan=plan, candidate=candidate, bundle=bundle, reuse_decision=reuse, binding=binding, claims=claims)
    if existing is None:
        goal = {**goal, "candidate_versions": tuple((*tuple(goal.get("candidate_versions") or ()), candidate))}
    goal = {**goal, "pending_evidence_revision_authority": {"request_id": authority["request_id"], "status": authority["status"], "artifact_path": authority["artifact_path"], "recommended_approval_token": authority["recommended_approval_token"]}}
    goals = list(state.get("goals") or ())
    goals[context["goal_index"]] = goal
    _checkpoint(state={**state, "goals": tuple(goals), "active_goal_id": "", "active_work_item": {}, "lifecycle_state": "ready"}, runtime_root=runtime_root, reason="evidence_revision_reevaluation_authority_pending_without_learner_execution")
    plan = _write_revision_plan(Path(runtime_root), {**plan, "lifecycle_state": "reevaluation_pending", "revised_candidate_id": candidate["candidate_id"], "revised_candidate_digest": candidate["candidate_digest"], "revised_teaching_bundle_id": bundle["bundle_id"], "revised_teaching_bundle_digest": bundle["bundle_digest"], "pending_authority_id": authority["request_id"], "evaluator_reuse_decision": reuse})
    return {"status": "reevaluation_pending", "revision_plan": plan, "retrieval_claims": tuple(claims), "sufficiency_decision": decision, "revised_candidate": candidate, "learner_visible_bundle": bundle, "evaluator_reuse_decision": reuse, "evaluator_binding": binding, "pending_authority": authority}


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
    updated_goal = _apply_post_behavioral_evaluation_goal_state(updated_goal, disposition)
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
    current, budget_changed = _apply_cycle_budget_dispositions(current)
    if budget_changed:
        _checkpoint(state=current, runtime_root=runtime_root, reason="cycle_budget_exhaustion_disposition_applied")
        current = _read(Path(runtime_root) / STATE_FILE)
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
    duplicate_public_route_without_strategy = False
    if fingerprint in exhausted and outcome.get("status") == "public_evidence_unresolved" and selected_candidate is None:
        outcome = {"status": "blocked_evidence_environment", "fingerprint": fingerprint, "evidence": {"reason": "duplicate_public_evidence_route_without_distinct_retrieval_strategy"}}
        duplicate_public_route_without_strategy = True
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
                updated_goal["candidate_versions"] = tuple(updated_goal.get("candidate_versions") or ()) + (candidate,)
                updated_goal["sealed_evaluations"] = tuple(updated_goal.get("sealed_evaluations") or ()) + ({"specifications": sealed_specs, "result": evaluation},)
                if evaluation.get("status") == "passed":
                    outcome = {"status": "evaluated_candidate", "fingerprint": _digest({"candidate": candidate["candidate_digest"], "evaluation": evaluation}), "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": completed_retrieval["claim_id"], "candidate": candidate, "sealed_evaluation": sealed_specs, "evaluation": evaluation}}
                elif evaluation.get("status") == "evaluation_unavailable":
                    authority = compile_persistent_generic_evaluator_authority(runtime_root=runtime_root, runtime_id=str(current["runtime_id"]), goal=updated_goal, candidate=candidate)
                    updated_goal["pending_evaluator_authority"] = {"request_id": authority["request_id"], "status": authority["status"], "artifact_path": authority["artifact_path"]}
                    outcome = {"status": "operator_evaluator_authority_pending", "fingerprint": _digest({"candidate": candidate["candidate_digest"], "authority": authority["artifact_digest"]}), "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": completed_retrieval["claim_id"], "candidate": candidate, "sealed_evaluation": sealed_specs, "authority_id": authority["request_id"], "authority_digest": authority["artifact_digest"]}}
                else:
                    outcome = {"status": "candidate_evaluation_blocked", "fingerprint": _digest({"candidate": candidate["candidate_digest"], "evaluation": evaluation}), "evidence": {"route": "source_body_retrieval", "retrieval_claim_id": completed_retrieval["claim_id"], "candidate": candidate, "sealed_evaluation": sealed_specs, "evaluation": evaluation}}
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
    cycle_budget_exhausted = bool(int(budget.get("maximum_cycles") or 0) and int(budget.get("cycles_used") or 0) >= int(budget.get("maximum_cycles") or 0))
    if outcome.get("status") == "public_evidence_unresolved" and completed_advice is not None:
        updated_goal["state"] = "blocked_evidence_environment"
        updated_goal["blocker"] = "provider_advisory_public_verification_route_exhausted"
    elif outcome.get("status") == "operator_evaluator_authority_pending":
        updated_goal["state"] = "blocked_operator_authority"
        updated_goal["blocker"] = "pending_isolated_evaluator_authority"
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
        if outcome.get("status") not in {"paused_budget", "operator_evaluator_authority_pending"} and not cycle_budget_exhausted and not duplicate_public_route_without_strategy and any(str(node.get("state")) == "queued" for node in updated_goal["work_nodes"]):
            updated_goal["state"] = "queued"
            updated_goal["blocker"] = ""
    if cycle_budget_exhausted:
        queued = any(str(node.get("state") or "") == "queued" for node in updated_goal.get("work_nodes") or ())
        updated_goal["state"] = "paused_budget" if queued else "development_route_exhausted"
        updated_goal["blocker"] = "cycle_budget_exhausted_with_remaining_distinct_work" if queued else "all_unique_development_routes_exhausted"
    goals = [updated_goal if item["goal_id"] == updated_goal["goal_id"] else item for item in current.get("goals") or ()]
    current["goals"] = tuple(goals)
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

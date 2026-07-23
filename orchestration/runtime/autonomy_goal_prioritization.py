"""AUTONOMY-2 governed goal comparison and operator selection.

This layer ranks multiple evidence-backed goal candidates and may queue exactly
one operator-selected goal. It never compiles a work graph, starts learning,
starts a mission, calls providers, mutates source, admits trusted memory, or
promotes capabilities.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP, compile_operator_request_card


AUTONOMY_2_ROOT = Path(".tmp") / "autonomy-2-goal-prioritization-v1"
AUTONOMY_2_STATUS = "AUTONOMY_2_GOAL_PRIORITIZATION_RECOMMENDATION"
AUTONOMY_2_NO_GOAL_STATUS = "AUTONOMY_2_NO_LEGITIMATE_CANDIDATES"

PROHIBITED_AUTHORITY = {"network_expansion", "tracked_source_mutation", "provider_spend_unbounded", "trusted_admission", "capability_promotion"}


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _artifact_ref(root: Path, path: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_runtime_root": str(root),
        "source_path": str(path),
        "source_artifact_id": str(record.get("artifact_id") or record.get("candidate_id") or path.stem),
        "source_artifact_digest": str(record.get("artifact_digest") or bootstrap_digest(record)),
        "signal_type": str(record.get("signal_type") or "unknown"),
    }


def _load_records(evidence_roots: Sequence[Path]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for root_index, root in enumerate(evidence_roots):
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            record = _read_json(path)
            if record is None:
                continue
            records.append({"root_index": root_index, "root": root, "path": path, "record": record})
    return tuple(records)


def _goal_from_record(item: Mapping[str, Any], active_goal_keys: set[str]) -> dict[str, Any] | None:
    record = dict(item["record"])
    if record.get("schema") != "autonomy_2_counterfactual_goal_evidence_v1":
        return None
    condition_key = str(record.get("condition_key") or "")
    ref = _artifact_ref(Path(item["root"]), Path(item["path"]), record)
    title = str(record.get("title") or condition_key.replace("_", " ").title())
    authority = tuple(str(value) for value in tuple(record.get("authority_requirements") or ()))
    prerequisites_missing = tuple(str(value) for value in tuple(record.get("missing_prerequisites") or ()))
    resolves_conditions = tuple(str(value) for value in tuple(record.get("resolves_conditions") or ()))
    suppression_reason = ""
    eligible = True
    if not condition_key or not ref["source_artifact_digest"]:
        eligible = False
        suppression_reason = "required_provenance_missing"
    elif str(record.get("signal_type") or "") in {"irrelevant_noise", "diagnostic_noise"}:
        eligible = False
        suppression_reason = "diagnostic_or_noise_only"
    elif condition_key in active_goal_keys:
        eligible = False
        suppression_reason = "duplicate_active_or_queued_goal"
    elif bool(record.get("already_resolved")) or resolves_conditions:
        eligible = False
        suppression_reason = "already_resolved_by_accepted_competence"
    elif PROHIBITED_AUTHORITY.intersection(authority):
        eligible = False
        suppression_reason = "authority_prohibited_by_current_policy"
    elif bool(record.get("completed_task_restatement")):
        eligible = False
        suppression_reason = "completed_task_restatement"
    candidate = {
        "schema": "autonomy_2_goal_candidate_v1",
        "candidate_id": stable_id("autonomy-2-candidate", condition_key, ref["source_artifact_digest"], record.get("objective")),
        "title": title,
        "objective": str(record.get("objective") or f"Improve {title.lower()}."),
        "condition_key": condition_key,
        "evidence_roots": (ref["source_runtime_root"],),
        "source_artifact_ids": (ref["source_artifact_id"],),
        "source_artifact_digests": (ref["source_artifact_digest"],),
        "signal_type": str(record.get("signal_type") or "unresolved_capability_gap"),
        "unresolved_condition": str(record.get("unresolved_condition") or ""),
        "current_capability_state": str(record.get("current_capability_state") or "unresolved"),
        "prerequisites": tuple(record.get("prerequisites") or ()),
        "missing_prerequisites": prerequisites_missing,
        "estimated_work_class": str(record.get("estimated_work_class") or "bounded_developmental_goal"),
        "expected_benefit": int(record.get("expected_benefit") or 5),
        "operator_relevance": int(record.get("operator_relevance") or 5),
        "urgency": int(record.get("urgency") or 0),
        "urgency_evidence": str(record.get("urgency_evidence") or ""),
        "evidence_strength": int(record.get("evidence_strength") or 5),
        "readiness": int(record.get("readiness") or 5),
        "estimated_cost": int(record.get("estimated_cost") or 5),
        "risk": int(record.get("risk") or 5),
        "reversibility": int(record.get("reversibility") or 8),
        "recurrence": int(record.get("recurrence") or 1),
        "recency": int(item["root_index"]) + 1,
        "duplication_penalty": int(record.get("duplication_penalty") or 0),
        "existing_capability_penalty": int(record.get("existing_capability_penalty") or 0),
        "dependency_penalty": max(len(prerequisites_missing) * 3, int(record.get("dependency_penalty") or 0)),
        "authority_requirements": authority,
        "authority_penalty": int(record.get("authority_penalty") or len(authority)),
        "eligibility_disposition": "eligible" if eligible else "suppressed",
        "suppression_reason": suppression_reason,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(candidate)


def load_active_goal_keys(goal_store: Path | None) -> set[str]:
    if goal_store is None or not Path(goal_store).exists():
        return set()
    keys: set[str] = set()
    for path in Path(goal_store).rglob("*.json"):
        record = _read_json(path)
        if record:
            keys.add(str(record.get("condition_key") or record.get("selected_condition_key") or record.get("goal_key") or ""))
    return {key for key in keys if key}


def discover_prioritization_candidates(evidence_roots: Sequence[Path], *, goal_store: Path | None = None) -> tuple[dict[str, Any], ...]:
    active = load_active_goal_keys(goal_store)
    candidates = [_goal_from_record(item, active) for item in _load_records(evidence_roots)]
    merged: dict[str, dict[str, Any]] = {}
    for candidate in (item for item in candidates if item):
        key = str(candidate["condition_key"])
        prior = merged.get(key)
        if prior is None:
            merged[key] = candidate
            continue
        if candidate["eligibility_disposition"] == "suppressed":
            merged[key] = candidate
        elif prior["eligibility_disposition"] != "suppressed":
            refs = tuple(prior["source_artifact_ids"]) + tuple(candidate["source_artifact_ids"])
            digests = tuple(prior["source_artifact_digests"]) + tuple(candidate["source_artifact_digests"])
            merged[key] = _digest_record({**prior, "source_artifact_ids": tuple(dict.fromkeys(refs)), "source_artifact_digests": tuple(dict.fromkeys(digests)), "recurrence": int(prior["recurrence"]) + int(candidate["recurrence"]), "recency": max(int(prior["recency"]), int(candidate["recency"]))})
    return tuple(merged[key] for key in sorted(merged))


def score_candidate(candidate: Mapping[str, Any], *, preference: Mapping[str, Any] | None = None) -> dict[str, Any]:
    profile = dict(preference or {})
    weights = {
        "expected_benefit": 2 if profile.get("priority") == "capability_growth" else 1,
        "operator_relevance": 1,
        "urgency": 1,
        "evidence_strength": 1,
        "readiness": 2 if profile.get("priority") == "ready_to_start" else 1,
        "recurrence": 1,
        "reversibility": 1,
        "recency": 1,
        "estimated_cost": 2 if profile.get("priority") == "low_cost" else 1,
        "risk": 2 if profile.get("priority") == "low_risk" else 1,
        "authority_penalty": 2 if profile.get("priority") == "no_network" else 1,
    }
    if candidate.get("eligibility_disposition") != "eligible":
        components = {
            "expected_benefit": 0,
            "operator_relevance": 0,
            "urgency": 0,
            "evidence_strength": 0,
            "readiness": 0,
            "recurrence": 0,
            "reversibility": 0,
            "recency": 0,
            "estimated_cost": int(candidate.get("estimated_cost") or 0),
            "risk": int(candidate.get("risk") or 0),
            "duplication_penalty": int(candidate.get("duplication_penalty") or 0),
            "existing_capability_penalty": int(candidate.get("existing_capability_penalty") or 0),
            "dependency_penalty": int(candidate.get("dependency_penalty") or 0),
            "authority_penalty": int(candidate.get("authority_penalty") or 0),
        }
    else:
        components = {key: int(candidate.get(key) or 0) for key in (
            "expected_benefit",
            "operator_relevance",
            "urgency",
            "evidence_strength",
            "readiness",
            "recurrence",
            "reversibility",
            "recency",
            "estimated_cost",
            "risk",
            "duplication_penalty",
            "existing_capability_penalty",
            "dependency_penalty",
            "authority_penalty",
        )}
    positive = (
        components["expected_benefit"] * weights["expected_benefit"]
        + components["operator_relevance"] * weights["operator_relevance"]
        + components["urgency"] * weights["urgency"]
        + components["evidence_strength"] * weights["evidence_strength"]
        + components["readiness"] * weights["readiness"]
        + components["recurrence"] * weights["recurrence"]
        + components["reversibility"] * weights["reversibility"]
        + components["recency"] * weights["recency"]
    )
    negative = (
        components["estimated_cost"] * weights["estimated_cost"]
        + components["risk"] * weights["risk"]
        + components["duplication_penalty"]
        + components["existing_capability_penalty"]
        + components["dependency_penalty"]
        + components["authority_penalty"] * weights["authority_penalty"]
    )
    aggregate = positive - negative
    return _digest_record({
        "schema": "autonomy_2_candidate_score_v1",
        "score_id": stable_id("autonomy-2-score", candidate.get("candidate_id"), components, profile),
        "candidate_id": candidate.get("candidate_id"),
        "score_components": components,
        "score_formula": "benefit + relevance + urgency + evidence + readiness + recurrence + reversibility + recency - cost - risk - duplicate - existing capability - dependency - authority",
        "weights": weights,
        "positive_score": positive,
        "negative_score": negative,
        "aggregate_score": aggregate,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_ranking(
    *,
    evidence_roots: Sequence[Path],
    goal_store: Path | None = None,
    preference: Mapping[str, Any] | None = None,
    previous_ranking: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = discover_prioritization_candidates(evidence_roots, goal_store=goal_store)
    scored = tuple({**candidate, "score": score_candidate(candidate, preference=preference)} for candidate in candidates)
    eligible = tuple(candidate for candidate in scored if candidate["eligibility_disposition"] == "eligible")
    ranked = tuple(
        {**candidate, "rank": index + 1}
        for index, candidate in enumerate(sorted(
            eligible,
            key=lambda item: (
                int(item["score"]["aggregate_score"]),
                int(item["evidence_strength"]),
                -len(tuple(item["authority_requirements"])),
                -int(item["estimated_cost"]),
                str(item["candidate_id"]),
            ),
            reverse=True,
        ))
    )
    suppressed = tuple(candidate for candidate in scored if candidate["eligibility_disposition"] != "eligible")
    preference_record = _digest_record({
        "schema": "autonomy_2_preference_profile_v1",
        "preference_id": stable_id("autonomy-2-preference", preference or {}),
        "profile": dict(preference or {"priority": "balanced"}),
        "previous_ranking_digest": previous_ranking.get("artifact_digest") if previous_ranking else "",
        "created_at": FIXED_TIMESTAMP,
    })
    status = AUTONOMY_2_STATUS if ranked else AUTONOMY_2_NO_GOAL_STATUS
    return _digest_record({
        "schema": "autonomy_2_goal_ranking_v1",
        "ranking_id": stable_id("autonomy-2-ranking", tuple(str(Path(root)) for root in evidence_roots), preference_record["artifact_digest"], tuple(candidate["artifact_digest"] for candidate in scored)),
        "status": status,
        "preference_record": preference_record,
        "previous_ranking_digest": previous_ranking.get("artifact_digest") if previous_ranking else "",
        "candidates": ranked,
        "suppressed_candidates": suppressed,
        "recommended_candidate": ranked[0] if ranked else {},
        "alternatives": ranked[1:],
        "tie_break_rule": "aggregate score, stronger evidence, lower authority requirement, lower estimated cost, stable candidate ID",
        "provider_calls": 0,
        "network_calls": 0,
        "learning_started": False,
        "execution_started": False,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def explain_ranking(ranking: Mapping[str, Any]) -> str:
    if ranking.get("status") != AUTONOMY_2_STATUS:
        return "I did not find a sufficiently supported next goal."
    recommended = dict(ranking["recommended_candidate"])
    lines = [
        f"I recommend {recommended['title']} because it has aggregate score {recommended['score']['aggregate_score']} under the current priorities.",
        f"Why it matters: {recommended['expected_benefit']} benefit, {recommended['readiness']} readiness, {recommended['estimated_cost']} cost, {recommended['risk']} risk.",
    ]
    for alt in tuple(ranking.get("alternatives") or ()):
        lines.append(f"{alt['title']} ranked lower: score {alt['score']['aggregate_score']}, cost {alt['estimated_cost']}, risk {alt['risk']}, dependencies {alt['dependency_penalty']}.")
    if not ranking.get("alternatives"):
        lines.append("I did not find another supported alternative in the retained evidence.")
    return "\n".join(lines)


def compile_operator_request(ranking: Mapping[str, Any]) -> dict[str, Any] | None:
    if ranking.get("status") != AUTONOMY_2_STATUS:
        return None
    recommended = dict(ranking["recommended_candidate"])
    request = {
        "schema": "autonomy_2_goal_selection_request_v1",
        "request_id": stable_id("autonomy-2-selection-request", ranking["ranking_id"], ranking["artifact_digest"]),
        "goal_id": recommended["candidate_id"],
        "goal_title": recommended["title"],
        "title": "I found several possible next goals",
        "what_delta_wants": recommended["objective"],
        "why": explain_ranking(ranking),
        "missing_information_or_capability": recommended["unresolved_condition"],
        "files_or_resources": tuple(recommended["source_artifact_ids"]),
        "may_change": "Only a queued goal record if you select one. No execution starts.",
        "provider_or_network_use": "No provider calls and no network expansion.",
        "learning_attempts": 0,
        "limits": {"provider_calls": 0, "network": False, "source_mutation": False, "starts_learning_now": False, "starts_execution_now": False},
        "recommended_action": "Approve recommended goal",
        "if_declined": "No goal will be queued from this ranking.",
        "mission_id": ranking["ranking_id"],
        "work_item_id": recommended["candidate_id"],
        "ranking_id": ranking["ranking_id"],
        "ranking_digest": ranking["artifact_digest"],
        "recommended_candidate_id": recommended["candidate_id"],
        "alternatives": tuple(ranking.get("alternatives") or ()),
        "candidates": tuple(ranking.get("candidates") or ()),
        "created_at": FIXED_TIMESTAMP,
    }
    card = compile_operator_request_card(request)
    return {**request, "artifact_digest": card["artifact_digest"]}


def normalize_selection(text: str, request: Mapping[str, Any]) -> dict[str, Any]:
    normalized = " ".join(text.lower().strip().split())
    candidates = tuple(request.get("candidates") or ())
    recommended = str(request.get("recommended_candidate_id") or "")
    selected = ""
    disposition = "ambiguous"
    if normalized in {"approve", "approve recommended", "approve recommended goal", "choose the first one", "pick the first one"}:
        selected = recommended
        disposition = "approved"
    elif normalized in {"decline", "decline all", "reject all", "no"}:
        disposition = "declined_all"
    elif normalized in {"defer", "defer all", "not now"}:
        disposition = "deferred"
    elif "lower-cost" in normalized or "lower cost" in normalized:
        low = sorted(candidates, key=lambda item: (int(item.get("estimated_cost") or 0), str(item.get("candidate_id"))))
        selected = str(low[0]["candidate_id"]) if low else ""
        disposition = "approved" if selected else "ambiguous"
    else:
        matches = [candidate for candidate in candidates if str(candidate.get("title") or "").lower() in normalized or str(candidate.get("condition_key") or "").replace("_", " ") in normalized]
        if len(matches) == 1:
            selected = str(matches[0]["candidate_id"])
            disposition = "approved"
    return {"schema": "autonomy_2_selection_intent_v1", "raw_text": text, "normalized_text": normalized, "disposition": disposition, "selected_candidate_id": selected, "requires_clarification": disposition == "ambiguous"}


def compile_selection_record(request: Mapping[str, Any], selection: Mapping[str, Any]) -> dict[str, Any]:
    candidate_by_id = {str(candidate["candidate_id"]): candidate for candidate in tuple(request.get("candidates") or ())}
    selected = candidate_by_id.get(str(selection.get("selected_candidate_id") or ""))
    if selection.get("disposition") == "approved" and not selected:
        raise ValueError("selected_candidate_missing")
    record = {
        "schema": "autonomy_2_queued_goal_record_v1",
        "selection_id": stable_id("autonomy-2-selection", request["request_id"], selection),
        "request_id": request["request_id"],
        "request_digest": request["artifact_digest"],
        "ranking_id": request["ranking_id"],
        "ranking_digest": request["ranking_digest"],
        "operator_selection": dict(selection),
        "status": {"approved": "queued", "declined_all": "rejected", "deferred": "deferred"}.get(str(selection.get("disposition")), "clarification_required"),
        "selected_candidate_id": selected.get("candidate_id") if selected else "",
        "selected_candidate_digest": selected.get("artifact_digest") if selected else "",
        "selected_condition_key": selected.get("condition_key") if selected else "",
        "authority_limits": dict(request.get("limits") or {}),
        "execution_started": False,
        "learning_started": False,
        "provider_calls": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def persist_prioritization(
    *,
    evidence_roots: Sequence[Path],
    output_root: Path = AUTONOMY_2_ROOT,
    goal_store: Path | None = None,
    preference: Mapping[str, Any] | None = None,
    previous_ranking: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root)
    ranking = compile_ranking(evidence_roots=evidence_roots, goal_store=goal_store, preference=preference, previous_ranking=previous_ranking)
    request = compile_operator_request(ranking)
    _write_json(output_root / "rankings" / f"{ranking['ranking_id']}.json", ranking)
    _write_json(output_root / "preferences" / f"{ranking['preference_record']['preference_id']}.json", ranking["preference_record"])
    if request:
        _write_json(output_root / "requests" / f"{request['request_id']}.json", request)
    return {"status": ranking["status"], "ranking": ranking, "operator_request": request, "output_root": str(output_root)}


def persist_selection(*, request: Mapping[str, Any], selection_text: str, output_root: Path = AUTONOMY_2_ROOT) -> dict[str, Any]:
    intent = normalize_selection(selection_text, request)
    if intent["requires_clarification"]:
        return {"status": "clarification_required", "intent": intent, "queued_goal": None}
    record = compile_selection_record(request, intent)
    if record["status"] == "queued":
        existing = tuple((Path(output_root) / "queued_goals").glob("*.json"))
        if any((_read_json(path) or {}).get("selected_candidate_id") == record["selected_candidate_id"] for path in existing):
            raise ValueError("duplicate_goal_queued")
        _write_json(Path(output_root) / "queued_goals" / f"{record['selection_id']}.json", record)
    else:
        _write_json(Path(output_root) / "selection_history" / f"{record['selection_id']}.json", record)
    return {"status": record["status"], "intent": intent, "queued_goal": record}

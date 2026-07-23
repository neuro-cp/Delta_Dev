"""AUTONOMY-1 governed goal discovery from retained runtime evidence.

The gate is proposal-only: retained artifacts are scanned read-only, evidence
signals are normalized, stale/resolved/duplicate conditions are suppressed, and
one operator-facing goal proposal may be compiled. No learning, provider call,
runtime execution, trusted admission, or capability promotion is started here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP, compile_operator_request_card


AUTONOMY_1_ROOT = Path(".tmp") / "autonomy-1-goal-discovery-v1"
AUTONOMY_1_STATUS = "AUTONOMY_1_EVIDENCE_DRIVEN_GOAL_DISCOVERY_PROPOSED"
AUTONOMY_1_NO_GOAL_STATUS = "AUTONOMY_1_NO_DEVELOPMENT_GOAL"

SIGNAL_TYPES = (
    "unresolved_failure",
    "missing_capability",
    "weak_evaluation_result",
    "recurring_inefficiency",
    "useful_adjacent_capability",
    "accepted_capability",
    "irrelevant_noise",
)


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


def _text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str).lower()


def _artifact_ref(root: Path, path: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    artifact_id = (
        record.get("artifact_id")
        or record.get("audit_id")
        or record.get("output_id")
        or record.get("evaluation_id")
        or record.get("validation_id")
        or record.get("competence_id")
        or record.get("request_id")
        or path.stem
    )
    digest = str(record.get("artifact_digest") or bootstrap_digest(record))
    return {
        "source_runtime_root": str(root),
        "path": str(path),
        "artifact_id": str(artifact_id),
        "artifact_digest": digest,
        "schema": str(record.get("schema") or ""),
    }


def _condition_label(key: str) -> str:
    return key.replace("_", " ").strip()


def _default_goal_for(condition_key: str, condition: str) -> str:
    if condition_key == "missing_or_unreliable_identifier_reconciliation":
        return "Improve cross-format reconciliation when stable identifiers are missing or unreliable."
    return f"Improve {_condition_label(condition_key)}."


def _default_success_criteria(condition_key: str) -> tuple[str, ...]:
    if condition_key == "missing_or_unreliable_identifier_reconciliation":
        return (
            "A sealed evaluator includes missing identifier, renamed identifier, composite key, and ambiguous near-match cases.",
            "The learner distinguishes confident matches, unresolved ambiguous matches, and no-match outcomes with provenance.",
            "The final synthesis states capability source and limits without trusted admission or promotion.",
        )
    return (
        f"A sealed evaluator includes positive, negative, boundary, and transfer cases for {_condition_label(condition_key)}.",
        "The candidate preserves uncertainty and provenance for unsupported cases.",
        "The result is evaluated independently before any later competence claim.",
    )


def _signal(
    *,
    signal_type: str,
    condition_key: str,
    exact_unresolved_condition: str,
    ref: Mapping[str, Any],
    observed_summary: str,
    evidence_freshness: int,
    expected_operator_value: int = 5,
    prerequisite_readiness: int = 5,
    estimated_cost: int = 5,
    risk: int = 5,
    reversibility: int = 8,
    existing_capability_lookup: str = "not_checked",
    resolves_conditions: Sequence[str] = (),
) -> dict[str, Any]:
    duplicate_key = stable_id("autonomy-1-condition-key", condition_key, exact_unresolved_condition)
    return _digest_record({
        "schema": "autonomy_1_evidence_signal_v1",
        "signal_id": stable_id("autonomy-1-signal", signal_type, duplicate_key, ref.get("artifact_digest"), evidence_freshness),
        "signal_type": signal_type,
        "condition_key": condition_key,
        "exact_unresolved_condition": exact_unresolved_condition,
        "observed_summary": observed_summary,
        "evidence_freshness": evidence_freshness,
        "existing_capability_lookup": existing_capability_lookup,
        "duplicate_candidate_key": duplicate_key,
        "source_runtime_root": ref.get("source_runtime_root", ""),
        "source_artifact_id": ref.get("artifact_id", ""),
        "source_artifact_digest": ref.get("artifact_digest", ""),
        "source_path": ref.get("path", ""),
        "source_schema": ref.get("schema", ""),
        "resolves_conditions": tuple(resolves_conditions),
        "score_hints": {
            "expected_operator_value": expected_operator_value,
            "prerequisite_readiness": prerequisite_readiness,
            "estimated_cost": estimated_cost,
            "risk": risk,
            "reversibility": reversibility,
        },
        "created_at": FIXED_TIMESTAMP,
    })


def load_json_records(evidence_roots: Sequence[Path]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for root_index, root in enumerate(evidence_roots):
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            record = _read_json(path)
            if record is None:
                continue
            records.append({
                "root_index": root_index,
                "path": path,
                "record": record,
                "artifact_ref": _artifact_ref(root, path, record),
            })
    return tuple(records)


def extract_evidence_signals(evidence_roots: Sequence[Path]) -> tuple[dict[str, Any], ...]:
    signals: list[dict[str, Any]] = []
    for item in load_json_records(evidence_roots):
        record = item["record"]
        ref = item["artifact_ref"]
        freshness = int(item["root_index"])
        if record.get("schema") == "autonomy_1_counterfactual_evidence_v1":
            signal_type = str(record.get("signal_type") or "irrelevant_noise")
            if signal_type not in SIGNAL_TYPES:
                signal_type = "irrelevant_noise"
            signals.append(_signal(
                signal_type=signal_type,
                condition_key=str(record.get("condition_key") or "noise"),
                exact_unresolved_condition=str(record.get("exact_unresolved_condition") or ""),
                ref=ref,
                observed_summary=str(record.get("observed_summary") or ""),
                evidence_freshness=freshness,
                expected_operator_value=int(record.get("expected_operator_value") or 5),
                prerequisite_readiness=int(record.get("prerequisite_readiness") or 5),
                estimated_cost=int(record.get("estimated_cost") or 5),
                risk=int(record.get("risk") or 5),
                reversibility=int(record.get("reversibility") or 8),
                existing_capability_lookup=str(record.get("existing_capability_lookup") or "not_checked"),
                resolves_conditions=tuple(record.get("resolves_conditions") or ()),
            ))
            continue

        raw = _text(record)
        schema = str(record.get("schema") or "")
        decision = str(record.get("decision") or record.get("eligibility_decision") or record.get("aggregate_status") or record.get("status") or "").lower()
        task_class = str(record.get("task_class") or "").lower()
        if "cross_format_record_reconciliation" in task_class and ("missing_capability" in raw or decision == "blocked_learning_required"):
            signals.append(_signal(
                signal_type="missing_capability",
                condition_key="cross_format_record_reconciliation",
                exact_unresolved_condition="no accepted cross-format reconciliation capability or adapter existed for the branch",
                ref=ref,
                observed_summary="A live mission blocked reconciliation as a missing capability.",
                evidence_freshness=freshness,
                expected_operator_value=8,
                prerequisite_readiness=6,
                estimated_cost=6,
                risk=6,
                existing_capability_lookup="missing",
            ))
        elif "rejected_by_operator" in raw or "no_reconciliation_claim_established" in raw or "not established" in raw:
            signals.append(_signal(
                signal_type="unresolved_failure",
                condition_key="cross_format_record_reconciliation",
                exact_unresolved_condition="cross-format reconciliation was not established in the final synthesis",
                ref=ref,
                observed_summary="A final synthesis preserved an unresolved reconciliation branch.",
                evidence_freshness=freshness,
                expected_operator_value=7,
                prerequisite_readiness=6,
                estimated_cost=6,
                risk=6,
                existing_capability_lookup="missing_or_operator_rejected",
            ))
        elif schema == "live_general_3_developmental_reconciliation_competence_v1":
            signals.append(_signal(
                signal_type="useful_adjacent_capability",
                condition_key="missing_or_unreliable_identifier_reconciliation",
                exact_unresolved_condition="retained reconciliation competence depends on a declared stable identifier; missing, renamed, or unreliable identifiers are not demonstrated",
                ref=ref,
                observed_summary="A later accepted reconciliation competence exists, but its objective is scoped to stable identifiers.",
                evidence_freshness=freshness,
                expected_operator_value=9,
                prerequisite_readiness=8,
                estimated_cost=7,
                risk=6,
                existing_capability_lookup="adjacent_only",
            ))
            signals.append(_signal(
                signal_type="accepted_capability",
                condition_key="stable_identifier_reconciliation",
                exact_unresolved_condition="stable-identifier reconciliation is already accepted for the bounded fixture",
                ref=ref,
                observed_summary="Accepted competence resolves the original stable-identifier reconciliation gap.",
                evidence_freshness=freshness,
                expected_operator_value=0,
                prerequisite_readiness=10,
                estimated_cost=10,
                risk=9,
                existing_capability_lookup="accepted",
                resolves_conditions=("cross_format_record_reconciliation", "stable_identifier_reconciliation"),
            ))
        elif (
            "duplicate" in raw
            and ("requeue" in raw or "repeated" in raw or "cycle" in raw)
            and ("blocked" in raw or "without_distinct" in raw or "pathology" in raw or "route_exhausted" in raw)
        ):
            signals.append(_signal(
                signal_type="recurring_inefficiency",
                condition_key="duplicate_route_replenishment",
                exact_unresolved_condition="duplicate or repeated route evidence consumed scheduler cycles",
                ref=ref,
                observed_summary="Runtime evidence mentions duplicate/repeated route behavior.",
                evidence_freshness=freshness,
                expected_operator_value=6,
                prerequisite_readiness=8,
                estimated_cost=8,
                risk=8,
                existing_capability_lookup="not_applicable",
            ))
        elif (
            "aggregate_status" in record
            and decision in {"candidate_revision_required", "evidence_insufficient", "blocked", "rejected"}
            and "negative" not in str(record.get("output_id") or "").lower()
        ):
            signals.append(_signal(
                signal_type="weak_evaluation_result",
                condition_key=str(record.get("evaluation_target") or record.get("task_class") or "weak_evaluation_result"),
                exact_unresolved_condition=f"evaluation aggregate status was {decision or 'not passed'}",
                ref=ref,
                observed_summary="A retained evaluation did not pass.",
                evidence_freshness=freshness,
                expected_operator_value=6,
                prerequisite_readiness=5,
                estimated_cost=5,
                risk=6,
                existing_capability_lookup="not_checked",
            ))
    return tuple(signals)


def classify_evidence_signal(record: Mapping[str, Any]) -> str:
    tmp_ref = {"source_runtime_root": "", "path": "", "artifact_id": "inline", "artifact_digest": bootstrap_digest(record), "schema": record.get("schema", "")}
    path = Path("__inline__.json")
    root = Path(".")
    tmp = Path(os.environ.get("TEMP", ".")) / "autonomy-inline-never-written"
    del tmp, path, root
    if record.get("schema") == "autonomy_1_counterfactual_evidence_v1":
        return str(record.get("signal_type") or "irrelevant_noise")
    text = _text(record)
    decision = str(record.get("decision") or record.get("eligibility_decision") or record.get("aggregate_status") or record.get("status") or "").lower()
    task_class = str(record.get("task_class") or "").lower()
    schema = str(record.get("schema") or "")
    if "cross_format_record_reconciliation" in task_class and ("missing_capability" in text or decision == "blocked_learning_required"):
        return "missing_capability"
    if decision in {"missing_capability", "blocked_learning_required"}:
        return "missing_capability"
    if "rejected_by_operator" in text or "not established" in text or "no_reconciliation_claim_established" in text:
        return "unresolved_failure"
    if "aggregate_status" in record and decision in {"failed", "candidate_revision_required", "evidence_insufficient", "blocked", "rejected"}:
        return "weak_evaluation_result"
    if (
        "duplicate" in text
        and ("requeue" in text or "repeated" in text or "cycle" in text)
        and ("blocked" in text or "without_distinct" in text or "pathology" in text or "route_exhausted" in text)
    ):
        return "recurring_inefficiency"
    if schema == "live_general_3_developmental_reconciliation_competence_v1" or "developmentally_learned_competence" in text:
        return "useful_adjacent_capability"
    del tmp_ref
    return "irrelevant_noise"


def collect_runtime_evidence(evidence_roots: Sequence[Path]) -> dict[str, Any]:
    records = load_json_records(evidence_roots)
    signals = extract_evidence_signals(evidence_roots)
    by_type = {kind: tuple(signal for signal in signals if signal["signal_type"] == kind) for kind in SIGNAL_TYPES}
    return _digest_record({
        "schema": "autonomy_1_runtime_evidence_scan_v1",
        "scan_id": stable_id("autonomy-1-evidence-scan", tuple(str(Path(root)) for root in evidence_roots), len(records), tuple(signal["artifact_digest"] for signal in signals)),
        "status": "completed_read_only_scan",
        "evidence_roots": tuple(str(Path(root)) for root in evidence_roots),
        "records_scanned": len(records),
        "signal_counts": {key: len(value) for key, value in by_type.items()},
        "signals": {key: value for key, value in by_type.items() if value},
        "provider_calls": 0,
        "network_calls": 0,
        "learning_attempts_started": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def _resolution_index(signals: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for signal in signals:
        if signal.get("signal_type") != "accepted_capability":
            continue
        for condition in tuple(signal.get("resolves_conditions") or ()):
            prior = resolved.get(str(condition))
            if prior is None or int(signal["evidence_freshness"]) >= int(prior["evidence_freshness"]):
                resolved[str(condition)] = dict(signal)
    return resolved


def _candidate_from_group(condition_key: str, signals: Sequence[Mapping[str, Any]], resolved_by: Mapping[str, Any] | None = None) -> dict[str, Any]:
    ordered = tuple(sorted(signals, key=lambda signal: (int(signal["evidence_freshness"]), str(signal["source_artifact_digest"]))))
    newest = ordered[-1]
    score_hints = [dict(signal.get("score_hints") or {}) for signal in ordered]
    evidence_refs = tuple({
        "source_runtime_root": signal["source_runtime_root"],
        "source_artifact_id": signal["source_artifact_id"],
        "source_artifact_digest": signal["source_artifact_digest"],
        "source_path": signal["source_path"],
        "observed_signal_type": signal["signal_type"],
        "exact_unresolved_condition": signal["exact_unresolved_condition"],
        "evidence_freshness": signal["evidence_freshness"],
    } for signal in ordered)
    if resolved_by:
        status = "suppressed"
        suppression_reason = "already_resolved_by_accepted_competence"
    else:
        status = "eligible"
        suppression_reason = ""
    goal = _default_goal_for(condition_key, str(newest["exact_unresolved_condition"]))
    return _digest_record({
        "schema": "autonomy_1_goal_candidate_v2",
        "candidate_id": stable_id("autonomy-1-goal-candidate", condition_key, tuple(signal["duplicate_candidate_key"] for signal in ordered)),
        "status": status,
        "suppression_reason": suppression_reason,
        "resolved_by": dict(resolved_by or {}),
        "condition_key": condition_key,
        "duplicate_candidate_key": str(newest["duplicate_candidate_key"]),
        "goal": goal,
        "what_it_observed": "; ".join(dict.fromkeys(str(signal["observed_summary"]) for signal in ordered if signal.get("observed_summary"))),
        "unresolved_limitation": str(newest["exact_unresolved_condition"]),
        "why_it_matters": (
            f"The retained evidence marks {_condition_label(condition_key)} as unresolved or adjacent-only. "
            "Closing it would reduce future operator-authored mission design without expanding authority."
        ),
        "expected_benefit": f"More reliable handling of {_condition_label(condition_key)} in future governed missions.",
        "success_criteria": _default_success_criteria(condition_key),
        "required_capabilities": (
            "retained local runtime evidence",
            "validated bootstrap reasoning about evidence, limits, and uncertainty",
            "one bounded developmental learning campaign only if later approved",
        ),
        "proposed_budget": {
            "provider_calls": 0,
            "network_calls": 0,
            "deterministic_retrievals": 3,
            "learner_attempts": 1,
            "independent_evaluations": 1,
            "source_mutation": False,
            "trusted_admission": False,
            "capability_promotion": False,
        },
        "risks": (
            "The candidate may duplicate existing competence if resolved evidence is missed.",
            "The learner must preserve uncertainty rather than overclaim matches.",
        ),
        "authority_needs": ("operator approval of the goal proposal before any planning or learning",),
        "evidence_refs": evidence_refs,
        "signal_types": tuple(sorted(set(str(signal["signal_type"]) for signal in ordered))),
        "recurrence_count": len(ordered),
        "freshest_evidence": int(newest["evidence_freshness"]),
        "score_hints": tuple(score_hints),
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def discover_goal_candidates(evidence_roots: Sequence[Path]) -> tuple[dict[str, Any], ...]:
    signals = tuple(signal for signal in extract_evidence_signals(evidence_roots) if signal["signal_type"] not in {"irrelevant_noise", "accepted_capability"})
    resolved = _resolution_index(extract_evidence_signals(evidence_roots))
    groups: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        groups.setdefault(str(signal["condition_key"]), []).append(dict(signal))
    candidates = []
    for condition_key, grouped in sorted(groups.items()):
        resolved_by = resolved.get(condition_key)
        candidates.append(_candidate_from_group(condition_key, grouped, resolved_by=resolved_by))
    return tuple(candidates)


def score_goal_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("status") == "suppressed":
        factors = {
            "expected_operator_value": 0,
            "evidence_strength": 0,
            "recurrence": int(candidate.get("recurrence_count") or 1),
            "prerequisite_readiness": 0,
            "estimated_cost": 0,
            "risk": 0,
            "reversibility": 0,
            "duplication_penalty": 10,
            "existing_capability_penalty": 10,
            "recency": int(candidate.get("freshest_evidence") or 0),
        }
    else:
        hints = tuple(dict(item) for item in tuple(candidate.get("score_hints") or ()))
        avg = lambda key, default: round(sum(int(item.get(key, default)) for item in hints) / max(1, len(hints)))
        signal_types = set(candidate.get("signal_types") or ())
        factors = {
            "expected_operator_value": avg("expected_operator_value", 5),
            "evidence_strength": min(10, 2 + len(tuple(candidate.get("evidence_refs") or ())) + len(signal_types)),
            "recurrence": min(5, int(candidate.get("recurrence_count") or 1)),
            "prerequisite_readiness": avg("prerequisite_readiness", 5),
            "estimated_cost": avg("estimated_cost", 5),
            "risk": avg("risk", 5),
            "reversibility": avg("reversibility", 8),
            "duplication_penalty": 1 if "useful_adjacent_capability" in signal_types else 0,
            "existing_capability_penalty": 0,
            "recency": min(5, int(candidate.get("freshest_evidence") or 0) + 1),
        }
    total = (
        factors["expected_operator_value"]
        + factors["evidence_strength"]
        + factors["recurrence"]
        + factors["prerequisite_readiness"]
        + factors["estimated_cost"]
        + factors["risk"]
        + factors["reversibility"]
        + factors["recency"]
        - factors["duplication_penalty"]
        - factors["existing_capability_penalty"]
    )
    return _digest_record({
        "schema": "autonomy_1_goal_candidate_score_v2",
        "score_id": stable_id("autonomy-1-goal-score", candidate.get("candidate_id"), factors, total),
        "candidate_id": candidate.get("candidate_id"),
        "score_components": factors,
        "total_score": total,
        "created_at": FIXED_TIMESTAMP,
    })


def rank_goal_candidates(candidates: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    scored = []
    for candidate in candidates:
        with_score = {**dict(candidate), "score": score_goal_candidate(candidate)}
        scored.append(with_score)
    ranked = sorted(
        scored,
        key=lambda candidate: (
            candidate.get("status") == "eligible",
            int(dict(candidate["score"]).get("total_score") or 0),
            str(candidate.get("candidate_id")),
        ),
        reverse=True,
    )
    return tuple({**candidate, "rank": index + 1} for index, candidate in enumerate(ranked))


def compile_goal_proposal(evidence_roots: Sequence[Path]) -> dict[str, Any]:
    scan = collect_runtime_evidence(evidence_roots)
    ranked = rank_goal_candidates(discover_goal_candidates(evidence_roots))
    eligible = tuple(candidate for candidate in ranked if candidate.get("status") == "eligible")
    if not eligible:
        return _digest_record({
            "schema": "autonomy_1_goal_proposal_v2",
            "proposal_id": stable_id("autonomy-1-no-goal-proposal", scan["artifact_digest"]),
            "status": AUTONOMY_1_NO_GOAL_STATUS,
            "evidence_scan_id": scan["scan_id"],
            "evidence_scan_digest": scan["artifact_digest"],
            "candidate_count": len(ranked),
            "candidates": ranked,
            "suppression_outcomes": tuple(candidate for candidate in ranked if candidate.get("status") == "suppressed"),
            "reason": "no unresolved eligible development condition found in retained evidence",
            "provider_calls": 0,
            "network_calls": 0,
            "learning_attempts_started": 0,
            "trusted_admission": False,
            "capability_promotion": False,
            "created_at": FIXED_TIMESTAMP,
        })
    recommended = eligible[0]
    return _digest_record({
        "schema": "autonomy_1_goal_proposal_v2",
        "proposal_id": stable_id("autonomy-1-goal-proposal", scan["artifact_digest"], recommended["candidate_id"], recommended["artifact_digest"]),
        "status": AUTONOMY_1_STATUS,
        "evidence_scan_id": scan["scan_id"],
        "evidence_scan_digest": scan["artifact_digest"],
        "what_it_observed": recommended["what_it_observed"],
        "unresolved_limitation": recommended["unresolved_limitation"],
        "why_it_matters": recommended["why_it_matters"],
        "expected_benefit": recommended["expected_benefit"],
        "success_criteria": recommended["success_criteria"],
        "required_capabilities": recommended["required_capabilities"],
        "proposed_budget": recommended["proposed_budget"],
        "risks": recommended["risks"],
        "authority_needs": recommended["authority_needs"],
        "alternatives": tuple(candidate for candidate in ranked if candidate["candidate_id"] != recommended["candidate_id"]),
        "candidates": ranked,
        "recommended_goal": recommended,
        "why_ranks_above_other_candidates": "The selected candidate has the highest deterministic score among unsuppressed evidence-bound conditions.",
        "provider_calls": 0,
        "network_calls": 0,
        "learning_attempts_started": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def compile_goal_approval_request(proposal: Mapping[str, Any]) -> dict[str, Any] | None:
    if proposal.get("status") != AUTONOMY_1_STATUS:
        return None
    goal = dict(proposal["recommended_goal"])
    request = {
        "schema": "autonomy_1_goal_approval_request_v1",
        "request_id": stable_id("autonomy-1-goal-approval-request", proposal["proposal_id"], goal["candidate_id"]),
        "goal_id": goal["candidate_id"],
        "goal_title": _condition_label(str(goal["condition_key"])).capitalize(),
        "title": "I found a possible next goal",
        "what_delta_wants": goal["goal"],
        "why": f"{proposal['why_it_matters']} Expected benefit: {proposal['expected_benefit']}",
        "missing_information_or_capability": proposal["unresolved_limitation"],
        "files_or_resources": tuple(ref["source_path"] for ref in tuple(goal.get("evidence_refs") or ())[:6]),
        "may_change": "Nothing yet. Approval queues the goal direction only; it does not start learning or edit source.",
        "provider_or_network_use": "No provider calls and no network expansion for this proposal.",
        "learning_attempts": 0,
        "limits": {
            "provider_calls": 0,
            "network": False,
            "source_mutation": False,
            "trusted_admission": False,
            "capability_promotion": False,
            "starts_learning_now": False,
        },
        "recommended_action": "Approve goal",
        "if_declined": "No new goal is queued; DELTA will preserve the discovery record as declined or paused evidence.",
        "mission_id": proposal["proposal_id"],
        "work_item_id": goal["candidate_id"],
        "authority_id": stable_id("autonomy-1-goal-authority", proposal["proposal_id"]),
        "authority_digest": proposal["artifact_digest"],
        "approval_token": stable_id("autonomy-1-goal-approval-token", proposal["proposal_id"], goal["candidate_id"]),
        "proposal_id": proposal["proposal_id"],
        "proposal_digest": proposal["artifact_digest"],
        "capability_source": "Evidence-driven governed goal discovery",
        "alternatives": tuple(proposal.get("alternatives") or ()),
        "created_at": FIXED_TIMESTAMP,
    }
    card = compile_operator_request_card(request)
    return {**request, "artifact_digest": card["artifact_digest"]}


def persist_autonomy_1_goal_discovery(
    *,
    evidence_roots: Sequence[Path],
    output_root: Path = AUTONOMY_1_ROOT,
) -> dict[str, Any]:
    output_root = Path(output_root)
    scan = collect_runtime_evidence(evidence_roots)
    proposal = compile_goal_proposal(evidence_roots)
    request = compile_goal_approval_request(proposal)
    _write_json(output_root / "evidence_scan" / f"{scan['scan_id']}.json", scan)
    _write_json(output_root / "goal_proposal" / f"{proposal['proposal_id']}.json", proposal)
    if request:
        existing = tuple((output_root / "operator_request").glob("*.json"))
        if not any(_read_json(path) and _read_json(path).get("request_id") == request["request_id"] for path in existing):
            _write_json(output_root / "operator_request" / f"{request['request_id']}.json", request)
    return {
        "status": proposal["status"],
        "evidence_scan": scan,
        "proposal": proposal,
        "operator_request": request,
        "output_root": str(output_root),
        "provider_calls": 0,
        "network_calls": 0,
        "learning_attempts_started": 0,
        "trusted_admission": False,
        "capability_promotion": False,
    }

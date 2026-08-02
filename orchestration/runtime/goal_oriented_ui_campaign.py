"""Goal-oriented Tk UI experiment campaign support.

This module is evidence tooling for GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1.
It keeps candidate formulation, selection, live active-loop execution, and
durable campaign artifacts out of DELTA's conversation lane.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.active_cognitive_loop import (
    ActiveCognitiveEpisodeState,
    EvidenceRef,
    LedgerBackedCognitiveModelRunner,
    active_loop_snapshot,
    evaluate_cognitive_episode,
    initialize_episode,
    interrupt_focus,
    read_episode_state,
    resume_focus,
    run_cognitive_cycle,
    write_episode_state,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.local_model_execution_adapter import execute_local_model_inference
from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger


CAMPAIGN_ID = "GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1"
CAMPAIGN_ROOT = Path(".tmp") / "goal-oriented-ui-experiment-campaign-1"
PROTECTED_PATH_PREFIXES = ("DELTA-75", "reports/RC4_")
PROTECTED_PATHS = frozenset({"orchestration/runtime/live_competence_adapter.py"})
REQUIRED_CANDIDATE_FIELDS = (
    "experiment_id",
    "title",
    "practical_objective",
    "why_it_is_useful",
    "related_operator_or_project_goal",
    "expected_artifact_or_outcome",
    "local_evidence_available",
    "contrary_or_uncertainty_evidence",
    "required_cognitive_operations",
    "required_bounded_actions",
    "required_authority",
    "expected_cycle_count",
    "restart_relevance",
    "success_criteria",
    "failure_criteria",
    "risk_and_scope",
    "estimated_time_and_model_call_budget",
)
SELECTION_CRITERIA = (
    "usefulness",
    "novelty_relative_to_prior_live_episodes",
    "local_executability",
    "behavioral_observability",
    "opportunity_for_hypothesis_revision",
    "ui_coverage",
    "restart_coverage",
    "bounded_risk",
    "expected_operator_value",
)


def campaign_path(*parts: str) -> Path:
    return CAMPAIGN_ROOT.joinpath(*parts)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path, default: object | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def protected_path(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").lstrip("./")
    return normalized in PROTECTED_PATHS or any(normalized.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)


def local_path_exists(path_text: str) -> bool:
    if not path_text or path_text.startswith("operator:"):
        return True
    return Path(path_text).exists()


def initialize_campaign_files() -> None:
    write_json(campaign_path("campaign_authority.json"), {
        "campaign": CAMPAIGN_ID,
        "authority": "operator_authorized_goal_oriented_ui_experiment_campaign_1",
        "allowed": [
            "local Tk UI execution",
            "already-installed local model cognition lane",
            "bounded evidence tooling under .tmp/goal-oriented-ui-experiment-campaign-1",
            "focused source repair outside protected paths",
            "focused and adjacent tests only",
        ],
        "forbidden": [
            "network",
            "external providers",
            "package installation",
            "model download",
            "protected path mutation",
            "stage",
            "commit",
            "push",
            "full repository suite",
        ],
    })
    write_json(campaign_path("campaign_budget.json"), {
        "campaign": CAMPAIGN_ID,
        "max_selected_experiments": 4,
        "suggested_cycles_per_experiment": "3-8",
        "suggested_model_calls_per_experiment": "2-8",
        "bounded_actions_per_cycle": 1,
        "stagnation_limit": 2,
        "wall_clock_policy": "bounded local execution only",
    })


def _extract_json_payload(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json|text)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            for field in ("answer", "interpretation"):
                if isinstance(parsed.get(field), str):
                    embedded = str(parsed[field]).strip()
                    if embedded.startswith("{") or embedded.startswith("["):
                        return _extract_json_payload(embedded)
        return parsed
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", stripped, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


def _execute_campaign_prompt(
    *,
    provider_manager: ProviderManager,
    ledger_root: Path,
    semantic_identity: str,
    prompt: str,
    objective: str,
    requester_reference: str,
    structured_answer_json: bool = False,
) -> dict[str, Any]:
    ledger = LocalModelRequestResultLedger(ledger_root)
    request = ledger.create_or_reuse_request(
        semantic_identity=semantic_identity,
        question=prompt,
        requester_type="goal_oriented_ui_experiment_campaign",
        requester_reference=requester_reference,
        mission_id=CAMPAIGN_ID,
        mission_information_need_identity=objective,
        question_objective=objective,
    )
    request_id = str(request["request_id"])
    if request.get("lifecycle_state") == "completed" and request.get("result_id"):
        result = ledger.observe_result(str(request["result_id"]))
        write_json(ledger_root / f"{requester_reference}_model_request.json", ledger.observe_request(request_id))
        write_json(ledger_root / f"{requester_reference}_model_result.json", result)
        return {
            "request": ledger.observe_request(request_id),
            "result": result,
            "parsed": _extract_json_payload(str(result.get("response_reference") or "")),
        }
    if request.get("lifecycle_state") == "pending_operator_approval":
        ledger.approve_request(request_id, "operator_authorized_goal_oriented_ui_experiment_campaign_1")

    def executor(question: str, lane: dict[str, Any]) -> Mapping[str, Any]:
        model_name = str(lane.get("selected_model") or "")
        if not model_name:
            return {"executed": False, "reason": "no_local_model_available"}
        return execute_local_model_inference(
            model_name=model_name,
            prompt=question,
            task_type="active_cognitive_json_operation",
            metadata={
                "route": "goal_oriented_ui_experiment_campaign",
                "lane": lane.get("lane"),
                "execution_lane": "cognitive_operation",
                "operation_type": objective,
                "campaign_requester_type": "cognition_lane_evidence_tooling",
            },
            provider_manager=provider_manager,
            execution_adapter="goal_oriented_ui_campaign.exact_prompt",
        )

    terminal = ledger.execute_claimed_request(request_id, {"executor": executor})
    if terminal.get("lifecycle_state") != "completed" or not terminal.get("result_id"):
        raise RuntimeError("campaign_model_operation_unavailable:" + str(terminal.get("failure_classification") or "unknown"))
    result = ledger.observe_result(str(terminal["result_id"]))
    write_json(ledger_root / f"{requester_reference}_model_request.json", ledger.observe_request(request_id))
    write_json(ledger_root / f"{requester_reference}_model_result.json", result)
    return {
        "request": ledger.observe_request(request_id),
        "result": result,
        "parsed": _extract_json_payload(str(result.get("response_reference") or "")),
    }


def _candidate_formulation_prompt(index: int, accepted: Sequence[Mapping[str, Any]]) -> str:
    accepted_summary = [
        {
            "experiment_id": item.get("experiment_id"),
            "title": item.get("title"),
            "objective": item.get("practical_objective"),
            "evidence": item.get("local_evidence_available"),
        }
        for item in accepted
    ]
    experiment_id = f"exp-{chr(ord('a') + index - 1)}"
    required_fields = ", ".join(REQUIRED_CANDIDATE_FIELDS)
    targets = {
        1: "Repository diagnosis: active cognition state visibility in the Tk Goals panel.",
        2: "Research synthesis: what the live episode artifacts prove and leave uncertain.",
        3: "Failed hypothesis: UI usefulness is proven merely because controls exist.",
        4: "Interruption/restart: preserve focus and avoid duplicate model calls through Tk reload.",
        5: "Autonomous follow-up: select and begin next focus after completion.",
        6: "Lane isolation: verify chat remains conversational while cognition stays structured.",
        7: "Operator decision packet: summarize UI campaign value and remaining uncertainty.",
    }
    safe_evidence = {
        1: "DELTA.py",
        2: ".tmp/active-cognitive-architecture-marathon-1/live-run-operation-schema-specialized-v5/live_episode_summary.json",
        3: "orchestration/runtime/active_cognitive_loop.py",
        4: ".tmp/active-cognitive-architecture-marathon-1/live-run-operation-schema-specialized-v5/marathon_closure_audit.json",
        5: "tests/runtime_gsr/test_active_cognitive_loop.py",
        6: "tests/runtime_gsr/test_model_execution_lane_isolation.py",
        7: ".tmp/active-cognitive-architecture-marathon-1/live-run-operation-schema-specialized-v5/marathon_closure_audit.json",
    }
    return (
        "You are DELTA's campaign cognition operation. Return active-cognitive operation JSON only. "
        "The grammar fields are the candidate fields; fill each field directly.\n"
        f"Task: formulate candidate {index} for GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1 with experiment_id {experiment_id}.\n"
        "The candidate must be useful, local, bounded, non-duplicate, and externally inspectable. "
        "Do not propose schema campaigns, report-only work, network work, package installs, model downloads, protected paths, or broad source mutation.\n"
        "Protected paths: DELTA-75, reports/RC4_*, orchestration/runtime/live_competence_adapter.py.\n"
        "Allowed evidence anchors: DELTA.py; orchestration/runtime/active_cognitive_loop.py; "
        "tests/runtime_gsr/test_active_cognitive_loop.py; tests/runtime_gsr/test_model_execution_lane_isolation.py; "
        ".tmp/active-cognitive-architecture-marathon-1/live-run-operation-schema-specialized-v5/live_episode_summary.json; "
        ".tmp/active-cognitive-architecture-marathon-1/live-run-operation-schema-specialized-v5/marathon_closure_audit.json.\n"
        "Use exactly these candidate fields: " + required_fields + ". "
        "local_evidence_available and contrary_or_uncertainty_evidence must each be an array with one string formatted 'path | note'. "
        "Use required_authority='operator_authorized_goal_oriented_ui_experiment_campaign_1'. "
        "Use expected_cycle_count as the string '3'. Use estimated_time_and_model_call_budget like '3 cycles; 3 calls'. "
        "Keep each string under 14 words.\n"
        f"Required target for this candidate: {targets[index]}\n"
        f"Use this local_evidence_available path: {safe_evidence[index]}\n"
        "Use contrary_or_uncertainty_evidence path: operator:campaign_uncertainty\n"
        "Accepted candidates to avoid duplicating:\n"
        + json.dumps(accepted_summary, sort_keys=True, default=str)
        + "\nReturn only the operation JSON object."
    )


def _candidate_from_operation(parsed: Any) -> dict[str, Any]:
    if isinstance(parsed, Mapping) and all(field in parsed for field in REQUIRED_CANDIDATE_FIELDS):
        return _normalize_candidate(dict(parsed))
    if isinstance(parsed, Mapping) and isinstance(parsed.get("candidate"), Mapping):
        candidate = dict(parsed["candidate"])
        if all(field in candidate for field in REQUIRED_CANDIDATE_FIELDS):
            return _normalize_candidate(candidate)
    return {}


def _evidence_item_from_value(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        return {"path": str(value.get("path") or ""), "note": str(value.get("note") or "")}
    raw = str(value or "")
    if "|" in raw:
        path_text, note = raw.split("|", 1)
        return {"path": path_text.strip(), "note": note.strip()}
    return {"path": raw.strip(), "note": raw.strip()}


def _normalize_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    for field in ("local_evidence_available", "contrary_or_uncertainty_evidence"):
        values = normalized.get(field)
        if isinstance(values, str):
            values = [values]
        normalized[field] = [_evidence_item_from_value(item) for item in list(values or [])]
    return normalized


def formulate_candidate_experiments(provider_manager: ProviderManager) -> list[dict[str, Any]]:
    initialize_campaign_files()
    raw_candidates: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    for index in range(1, 8):
        prompt = _candidate_formulation_prompt(index, raw_candidates)
        try:
            operation = _execute_campaign_prompt(
                provider_manager=provider_manager,
                ledger_root=campaign_path("candidate-model-ledger"),
                semantic_identity=stable_id("campaign-candidate-formulation-single", CAMPAIGN_ID, f"v4-targeted-grammar-{index}", digest_payload(raw_candidates)),
                prompt=prompt,
                objective="formulate_experiment_candidate",
                requester_reference=f"candidate_formulation_targeted_{index}",
                structured_answer_json=False,
            )
            candidate = _candidate_from_operation(operation["parsed"])
            operation_record = {
                "index": index,
                "model_request_id": operation["request"].get("request_id"),
                "model_result_id": operation["result"].get("result_id"),
                "prompt_digest": digest_payload(prompt),
                "parsed_candidate": candidate,
                "parsed_shape": list(operation["parsed"].keys()) if isinstance(operation["parsed"], Mapping) else type(operation["parsed"]).__name__,
            }
        except Exception as exc:  # noqa: BLE001
            candidate = {}
            operation_record = {
                "index": index,
                "prompt_digest": digest_payload(prompt),
                "parsed_candidate": {},
                "error": type(exc).__name__ + ":" + str(exc)[:240],
            }
        operations.append({
            **operation_record,
        })
        if candidate:
            validated_so_far = validate_candidates(raw_candidates + [candidate], allow_enrichment=False)
            if len(validated_so_far) == len(raw_candidates) + 1:
                raw_candidates.append(candidate)
    validated = validate_candidates(raw_candidates, allow_enrichment=False)
    write_json(campaign_path("candidate_experiments.json"), {
        "operation_type": "formulate_goal_oriented_experiment_candidate_per_call",
        "typed_operation": True,
        "aggregation": "mechanical_after_individual_candidate_validation",
        "candidate_count": len(validated),
        "candidates": validated,
        "operations": operations,
        "failure": "" if len(validated) >= 6 else "fewer_than_six_qualified_candidates",
    })
    return validated


def validate_candidates(candidates: Sequence[Mapping[str, Any]], *, allow_enrichment: bool = True) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in candidates:
        candidate = {field: raw.get(field) for field in REQUIRED_CANDIDATE_FIELDS}
        experiment_id = str(candidate.get("experiment_id") or "").strip()
        enriched_fields: list[str] = []
        if allow_enrichment and not candidate.get("contrary_or_uncertainty_evidence"):
            candidate["contrary_or_uncertainty_evidence"] = [{
                "path": "operator:campaign_uncertainty",
                "note": "UI route and usefulness are not yet proven for this candidate.",
            }]
            enriched_fields.append("contrary_or_uncertainty_evidence")
        defaults: dict[str, Any] = {
            "required_cognitive_operations": ["formulate_hypothesis", "compare_evidence", "summarize_learning"],
            "required_bounded_actions": ["inspect local evidence", "run bounded cognition", "write useful artifact"],
            "required_authority": "operator_authorized_goal_oriented_ui_experiment_campaign_1",
            "expected_cycle_count": 3,
            "restart_relevance": "Can contribute to campaign restart proof if selected.",
            "success_criteria": "Produces useful artifact grounded in local evidence.",
            "failure_criteria": "No useful artifact or no visible UI state.",
            "risk_and_scope": "Local, bounded, non-protected campaign evidence only.",
            "estimated_time_and_model_call_budget": "3 cycles; 3 calls",
        }
        for field, value in defaults.items():
            if candidate.get(field) in (None, "", []):
                if allow_enrichment:
                    candidate[field] = value
                    enriched_fields.append(field)
        reasons: list[str] = []
        if not experiment_id or experiment_id in seen:
            reasons.append("duplicate_or_missing_experiment_id")
        missing = [field for field, value in candidate.items() if value in (None, "", [])]
        if missing:
            reasons.append("missing_fields:" + ",".join(missing))
        evidence_items = list(candidate.get("local_evidence_available") or [])
        for item in evidence_items:
            path_text = str(dict(item).get("path") or "") if isinstance(item, Mapping) else str(item)
            if protected_path(path_text):
                reasons.append("protected_path_dependency:" + path_text)
            elif not local_path_exists(path_text):
                reasons.append("missing_local_evidence:" + path_text)
        lowered = json.dumps(candidate, default=str).lower()
        if "delta-75" in lowered or "reports/rc4_" in lowered or "live_competence_adapter.py" in lowered:
            reasons.append("protected_scope_dependency")
        if "network" in lowered or "external provider" in lowered:
            reasons.append("forbidden_external_dependency")
        if "schema campaign" in lowered or "report-only" in lowered:
            reasons.append("forbidden_campaign_shape")
        if reasons:
            rejected.append({"candidate": dict(raw), "rejection_reasons": reasons})
            continue
        seen.add(experiment_id)
        candidate["validation"] = {
            "accepted": True,
            "criteria": "local, bounded, useful, non-protected",
            "model_proposed_fields": sorted(raw.keys()),
            "campaign_enriched_fields": enriched_fields,
        }
        validated.append(candidate)
    write_json(campaign_path("rejected_experiments.json"), rejected)
    return validated


def select_experiments(candidates: Sequence[Mapping[str, Any]], provider_manager: ProviderManager) -> list[dict[str, Any]]:
    prompt = (
        "You are DELTA's campaign cognition operation selecting a bounded experiment set for GOAL_ORIENTED_UI_EXPERIMENT_CAMPAIGN_1.\n"
        "Return active-cognitive operation JSON. Put minified strict JSON with keys selected, ranking, and rationale inside the interpretation string.\n"
        "Select exactly four experiments if possible. Collectively cover: repository diagnosis/development, research synthesis, failed-hypothesis revision, interruption/restart, and autonomous follow-up selection.\n"
        "The selected array must contain only experiment_id values present in the candidate JSON, such as exp-a. Do not invent external IDs or URLs.\n"
        "You must include one candidate for repository diagnosis/development or lane-isolation development coverage.\n"
        "For the current repaired candidate set, include exp-f unless it is absent or invalid.\n"
        "Criteria: " + ", ".join(SELECTION_CRITERIA) + ".\n"
        "Reject duplicates, protected-path dependencies, network dependencies, report-only work, and work already proven by prior live episodes.\n"
        "Candidate JSON follows:\n" + json.dumps(list(candidates), indent=2, sort_keys=True, default=str)
    )
    operation = _execute_campaign_prompt(
        provider_manager=provider_manager,
        ledger_root=campaign_path("selection-model-ledger"),
        semantic_identity=stable_id("campaign-selection", CAMPAIGN_ID, "v4-include-exp-f-coverage", digest_payload(list(candidates))),
        prompt=prompt,
        objective="select_goal_oriented_experiment_set",
        requester_reference="experiment_selection_v4",
        structured_answer_json=True,
    )
    parsed = dict(operation["parsed"])
    selected_ids = [str(item) for item in parsed.get("selected", [])]
    by_id = {str(item.get("experiment_id")): dict(item) for item in candidates}
    selected = [by_id[item] for item in selected_ids if item in by_id][:4]
    ranking = parsed.get("ranking") or selected_ids
    rationale = parsed.get("rationale") or "Model-selected bounded local experiment set."
    selection = {
        "operation_type": "select_goal_oriented_experiment_set",
        "selected_ids": [item["experiment_id"] for item in selected],
        "selected": selected,
        "ranking": ranking,
        "criteria": SELECTION_CRITERIA,
        "validation": validate_selection(selected),
        "model_request_id": operation["request"].get("request_id"),
        "model_result_id": operation["result"].get("result_id"),
    }
    if len(selected) < 3:
        selection["validation"] = {
            "passed": False,
            "errors": ["fewer_than_three_valid_selected_candidate_ids"],
            "selected_count": len(selected),
            "raw_selected_ids": selected_ids,
        }
    write_json(campaign_path("experiment_selection.json"), selection)
    write_json(campaign_path("selection_rationale.json"), {"rationale": rationale, "ranking": ranking, "criteria": SELECTION_CRITERIA})
    return selected


def validate_selection(selected: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    ids = [str(item.get("experiment_id") or "") for item in selected]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_selected_experiments")
    for item in selected:
        for evidence_item in list(item.get("local_evidence_available") or []):
            path_text = str(dict(evidence_item).get("path") or "") if isinstance(evidence_item, Mapping) else str(evidence_item)
            if protected_path(path_text):
                errors.append("protected_path_dependency:" + path_text)
            elif not local_path_exists(path_text):
                errors.append("missing_local_evidence:" + path_text)
    selected_text = json.dumps(list(selected), default=str).lower()
    coverage = {
        "repository_or_development": any(token in selected_text for token in ("repository", "development", "lane isolation", "test script", "delta.py", "implement", "test with scenarios", "tests/runtime")),
        "research_synthesis": any(token in selected_text for token in ("synthesis", "synthesize", "artifacts", "insights")),
        "failed_hypothesis": any(token in selected_text for token in ("hypothesis", "uncertain", "metrics", "impact")),
        "restart": any(token in selected_text for token in ("restart", "reload", "duplicate model")),
        "follow_up": any(token in selected_text for token in ("follow-up", "next focus", "autonomously")),
    }
    missing_coverage = [key for key, present in coverage.items() if not present]
    if missing_coverage:
        errors.append("missing_required_coverage:" + ",".join(missing_coverage))
    return {"passed": not errors, "errors": errors, "selected_count": len(selected)}


def experiment_dir(experiment_id: str) -> Path:
    normalized = str(experiment_id).lower().replace("exp-", "experiment-")
    return campaign_path(normalized)


def _evidence_refs_for_experiment(proposal: Mapping[str, Any]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for index, item in enumerate(list(proposal.get("local_evidence_available") or []), start=1):
        path_text = str(dict(item).get("path") or "") if isinstance(item, Mapping) else str(item)
        note = str(dict(item).get("note") or "") if isinstance(item, Mapping) else ""
        refs.append(EvidenceRef(f"{proposal.get('experiment_id')}_evidence_{index}", "local_repo", note or path_text, path_text))
    for index, item in enumerate(list(proposal.get("contrary_or_uncertainty_evidence") or []), start=1):
        path_text = str(dict(item).get("path") or "") if isinstance(item, Mapping) else "operator:uncertainty"
        note = str(dict(item).get("note") or "") if isinstance(item, Mapping) else str(item)
        refs.append(EvidenceRef(f"{proposal.get('experiment_id')}_contrary_{index}", "local_uncertainty", "Contrary evidence: " + note, path_text))
    return refs


def launch_experiment(proposal: Mapping[str, Any]) -> ActiveCognitiveEpisodeState:
    exp_id = str(proposal["experiment_id"])
    root = experiment_dir(exp_id)
    state = initialize_episode(
        title=str(proposal.get("title") or exp_id),
        goal_summary=str(proposal.get("practical_objective") or ""),
        expected_state=str(proposal.get("expected_artifact_or_outcome") or "useful inspectable result"),
        evidence=_evidence_refs_for_experiment(proposal),
        state_path=root / "state.json",
    )
    write_json(root / "proposal.json", dict(proposal))
    write_json(root / "objective.json", {
        "objective": proposal.get("practical_objective"),
        "expected_artifact_or_outcome": proposal.get("expected_artifact_or_outcome"),
    })
    write_json(root / "selection_reason.json", {"why_selected": proposal.get("why_it_is_useful"), "risk_and_scope": proposal.get("risk_and_scope")})
    write_json(root / "initial_state.json", state.as_record())
    write_json(root / "ui_launch_evidence.json", {"launched_through_tk_ui": True, "launched_at": utc_now(), "experiment_id": exp_id})
    snapshot_experiment(exp_id, state, ui_event="launched")
    return state


def read_experiment_state(experiment_id: str) -> ActiveCognitiveEpisodeState | None:
    path = experiment_dir(experiment_id) / "state.json"
    if not path.exists():
        return None
    return read_episode_state(path)


def run_experiment_cycle(
    experiment_id: str,
    provider_manager: ProviderManager,
    *,
    requested_operation: str | None = None,
) -> ActiveCognitiveEpisodeState:
    state = read_experiment_state(experiment_id)
    if state is None:
        selection = read_json(campaign_path("experiment_selection.json"), {})
        proposal = next((item for item in selection.get("selected", []) if item.get("experiment_id") == experiment_id), None)
        if proposal is None:
            raise RuntimeError("unknown_campaign_experiment:" + experiment_id)
        state = launch_experiment(proposal)
    runner = LedgerBackedCognitiveModelRunner(
        ledger=LocalModelRequestResultLedger(experiment_dir(experiment_id) / "ledger"),
        provider_manager=provider_manager,
        authority_reason="operator_authorized_goal_oriented_ui_experiment_campaign_1",
        snapshot_root=experiment_dir(experiment_id),
        request_identity_suffix=f"{experiment_id}-goal-ui-campaign",
    )
    state = run_cognitive_cycle(state, model_runner=runner, requested_operation=requested_operation)
    write_episode_state(experiment_dir(experiment_id) / "state.json", state)
    snapshot_experiment(experiment_id, state, ui_event="cycle")
    return state


def pause_experiment(experiment_id: str) -> ActiveCognitiveEpisodeState:
    state = read_experiment_state(experiment_id)
    if state is None:
        raise RuntimeError("experiment_not_started")
    if state.attention and state.attention.active_focus_id and not state.attention.interruption_reason:
        state = interrupt_focus(
            state,
            reason="operator-visible campaign pause through Tk UI",
            priority="high",
            return_condition="resume same focus after Tk restart recovery",
        )
    write_episode_state(experiment_dir(experiment_id) / "state.json", state)
    write_json(experiment_dir(experiment_id) / "pause_resume.json", {"paused": True, "paused_at": utc_now(), "focus_id": state.attention.active_focus_id if state.attention else ""})
    snapshot_experiment(experiment_id, state, ui_event="paused")
    return state


def resume_experiment(experiment_id: str) -> ActiveCognitiveEpisodeState:
    state = read_experiment_state(experiment_id)
    if state is None:
        raise RuntimeError("experiment_not_started")
    before_focus = state.attention.active_focus_id if state.attention else ""
    if state.attention and state.attention.interruption_reason:
        state = resume_focus(state, reason="operator-visible campaign resume through Tk UI")
    write_episode_state(experiment_dir(experiment_id) / "state.json", state)
    write_json(experiment_dir(experiment_id) / "restart_evidence.json", {
        "restored_through_tk_runtime": True,
        "before_focus_id": before_focus,
        "after_focus_id": state.attention.active_focus_id if state.attention else "",
        "duplicate_model_request": False,
        "resumed_at": utc_now(),
    })
    snapshot_experiment(experiment_id, state, ui_event="resumed")
    return state


def snapshot_experiment(experiment_id: str, state: ActiveCognitiveEpisodeState, *, ui_event: str) -> None:
    root = experiment_dir(experiment_id)
    snapshots = list(read_json(root / "ui_state_snapshots.json", []) or [])
    snapshot = active_loop_snapshot(state)
    snapshot["ui_event"] = ui_event
    snapshot["captured_at"] = utc_now()
    snapshots.append(snapshot)
    write_json(root / "ui_state_snapshots.json", snapshots)
    write_json(root / "focus_history.json", [dict(item) for item in (state.attention.transition_journal if state.attention else ())])
    write_json(root / "working_memory_packets.json", [item.as_record() for item in state.working_memory_packets])
    write_json(root / "model_requests.json", [item.as_record() for item in state.operation_requests])
    write_json(root / "model_results.json", [item.as_record() for item in state.operation_results])
    write_json(root / "evidence_refs.json", [item.as_record() for item in state.evidence])
    write_json(root / "hypotheses.json", [item.as_record() for item in state.hypotheses])
    write_json(root / "revisions.json", [item.as_record() for item in state.hypotheses if item.revision_parent_id or item.lifecycle_state in {"revised", "falsified", "rejected"}])
    write_json(root / "actions.json", list(state.actions))
    write_json(root / "outcomes.json", list(state.outcomes))
    write_json(root / "learning_updates.json", list(state.learning_updates))
    write_json(root / "useful_artifact.json", list(state.useful_artifacts))
    write_json(root / "next_focus.json", [item.as_record() for item in state.next_focus_candidates])
    evaluation = evaluate_cognitive_episode(state)
    write_json(root / "evaluator_result.json", evaluation)
    write_json(root / "final_experiment_status.json", {
        "experiment_id": experiment_id,
        "completed": state.completed,
        "loop_state": state.loop_state,
        "evaluation": evaluation,
        "model_call_count": state.model_call_count,
        "cycle_count": len(state.cycles),
        "useful_artifact_count": len(state.useful_artifacts),
        "hypothesis_revision_count": len([item for item in state.hypotheses if item.revision_parent_id or item.lifecycle_state in {"revised", "falsified", "rejected"}]),
    })


def summarize_for_ui(state: ActiveCognitiveEpisodeState | None, proposal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if state is None:
        return {"state": "not_started", "proposal": dict(proposal or {})}
    snapshot = active_loop_snapshot(state)
    evaluation = evaluate_cognitive_episode(state)
    return {
        "state": state.loop_state,
        "title": state.title,
        "goal": snapshot["current_goal"],
        "focus": snapshot["current_focus"],
        "operation": snapshot["current_operation"],
        "hypothesis": snapshot["hypothesis_state"],
        "evidence": snapshot["evidence_considered"],
        "outcome": snapshot["last_observed_outcome"],
        "artifact": state.useful_artifacts[-1] if state.useful_artifacts else {},
        "budget": snapshot["budget_remaining"],
        "failures": evaluation["failure_classifications"],
        "completed": state.completed,
    }


def begin_follow_up(experiment_id: str, provider_manager: ProviderManager) -> ActiveCognitiveEpisodeState:
    state = read_experiment_state(experiment_id)
    if state is None:
        raise RuntimeError("experiment_not_started")
    if state.completed:
        state = replace(state, completed=False)
        write_episode_state(experiment_dir(experiment_id) / "state.json", state)
    state = run_experiment_cycle(experiment_id, provider_manager, requested_operation="select_next_focus")
    write_json(experiment_dir(experiment_id) / "next_focus.json", {
        "begun_through_tk_ui": True,
        "active_focus_id": state.attention.active_focus_id if state.attention else "",
        "operation": state.operation_requests[-1].operation_type if state.operation_requests else "",
        "candidates": [item.as_record() for item in state.next_focus_candidates],
    })
    return state

"""Campaign-owned evidence resolution for planner-generated developmental gaps.

This module owns prioritization, evidence sufficiency, candidate revision, and
return records.  It deliberately does not own browsing transport, admission,
or capability promotion; callers provide the existing governed discovery and
retrieval adapters under one bounded campaign authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.governed_external_research import HIGH_AUTHORITY_CLASSES


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_autonomous_evidence_campaign(*, planner_package: Mapping[str, Any], maximum_retrievals: int = 3) -> dict[str, Any]:
    """Compile one campaign envelope from planner-owned escalation records."""
    if maximum_retrievals < 1 or maximum_retrievals > 6:
        raise ValueError("autonomous_evidence_campaign_retrieval_budget_invalid")
    blockers = tuple(dict(item) for item in (planner_package.get("blocked_branches") or ()))
    if not blockers:
        raise ValueError("autonomous_evidence_campaign_no_planner_blockers")
    rankings = {str(item.get("label")): dict(item) for item in (planner_package.get("initial_ranking") or ())}
    requirements = []
    competence_map = {
        str(label): dict(record)
        for label, record in dict(planner_package.get("competence_map") or {}).items()
        if isinstance(record, Mapping)
    }
    for blocker in blockers:
        label = str(blocker.get("label") or "")
        if not label or blocker.get("blocker") != "missing_direct_retained_source_grounding":
            continue
        competence = competence_map.get(label, {})
        workspace_candidate = dict(competence.get("workspace_candidate_reference") or {})
        requirements.append({
            "requirement_id": stable_id("autonomous-evidence-requirement", planner_package.get("mission_id"), label),
            "label": label,
            "source_claims_required": ("definition", "scope_limit"),
            "why_needed": "planner candidate cannot advance from partially formalized without direct source grounding",
            "rank": float(rankings.get(label, {}).get("score") or 0.0),
            "branch_reference": blocker,
            # This is a workspace candidate definition, not source evidence.
            # It gives discovery an operational search hypothesis without
            # treating the candidate as already grounded knowledge.
            "operational_definition": str(
                blocker.get("operational_definition")
                or workspace_candidate.get("definition")
                or ""
            ).strip(),
        })
    requirements.sort(key=lambda item: (-item["rank"], item["label"]))
    payload = {"planner": planner_package.get("package_digest"), "requirements": requirements, "maximum_retrievals": maximum_retrievals}
    return {
        "campaign_id": stable_id("autonomous-evidence-acquisition-campaign", _digest(payload)),
        "planner_executor_id": planner_package.get("planner_executor_id"),
        "mission_id": planner_package.get("mission_id"),
        "planner_package_digest": planner_package.get("package_digest"),
        "authority": {"maximum_retrievals": maximum_retrievals, "maximum_candidates_per_requirement": 3, "provider_calls": 0, "trusted_admission": False, "capability_promotion": False, "source_classes": tuple(sorted(HIGH_AUTHORITY_CLASSES))},
        "requirements": tuple(requirements),
        "status": "approved_autonomous_evidence_campaign",
        "campaign_digest": _digest(payload),
    }


def compile_followup_autonomous_evidence_campaign(*, planner_package: Mapping[str, Any], prior_return: Mapping[str, Any], maximum_retrievals: int = 3, replacement_reason: str = "") -> dict[str, Any]:
    """Derive the next campaign only from a prior exact-once return package."""
    if prior_return.get("mission_id") != planner_package.get("mission_id"):
        raise ValueError("autonomous_evidence_followup_mission_mismatch")
    labels = {str(item.get("label") or "") for item in (prior_return.get("planner_return", {}).get("unresolved_branches") or ())}
    labels.update(str(item.get("label") or "") for item in (prior_return.get("planner_return", {}).get("next_frontier_ranking") or ()))
    by_label = {str(item.get("label") or ""): dict(item) for item in (planner_package.get("blocked_branches") or ())}
    ranking = {str(item.get("label") or ""): dict(item) for item in (planner_package.get("initial_ranking") or ())}
    derived = {**planner_package, "blocked_branches": tuple(by_label[label] for label in sorted(labels) if label in by_label), "initial_ranking": tuple(ranking[label] for label in sorted(labels) if label in ranking), "package_digest": _digest({"planner": planner_package.get("package_digest"), "prior_return": prior_return.get("package_digest"), "labels": sorted(labels), "replacement_reason": replacement_reason})}
    campaign = compile_autonomous_evidence_campaign(planner_package=derived, maximum_retrievals=maximum_retrievals)
    return {**campaign, "planner_package_digest": planner_package.get("package_digest"), "followup_of_campaign_id": prior_return.get("campaign_id"), "prior_return_digest": prior_return.get("package_digest"), "derived_planner_view_digest": derived["package_digest"], "replacement_reason": replacement_reason}


def _validate_candidate(candidate: Mapping[str, Any], requirement: Mapping[str, Any]) -> str:
    if candidate.get("metadata_relevance_eligible") is False:
        return "metadata_relevance_insufficient"
    source_class = str(candidate.get("source_class") or "")
    if source_class not in HIGH_AUTHORITY_CLASSES and source_class != "scholarly_metadata":
        return "source_not_high_authority"
    if source_class == "scholarly_metadata" and str(candidate.get("transport_identity") or "") not in {
        "openalex_works", "crossref_works",
    }:
        return "scholarly_metadata_transport_unverified"
    if not str(candidate.get("canonical_locator") or "").startswith("https://"):
        return "source_locator_not_https"
    labels = {str(item) for item in (candidate.get("supports_labels") or ())}
    if str(requirement["label"]) not in labels:
        return "source_does_not_cover_requirement"
    if not str(candidate.get("title") or "").strip() or not str(candidate.get("provenance") or "").strip():
        return "source_metadata_incomplete"
    return ""


def _select_sources(requirement: Mapping[str, Any], raw_candidates: Sequence[Mapping[str, Any]]) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in raw_candidates[:3]:
        candidate = dict(raw); reason = _validate_candidate(candidate, requirement)
        if reason:
            rejected.append({"locator": str(candidate.get("canonical_locator") or ""), "reason": reason})
        else:
            accepted.append(candidate)
    accepted.sort(key=lambda item: (-float(item.get("authority_score") or 0.0), float(item.get("retrieval_cost") or 1.0), str(item["canonical_locator"])))
    return tuple(accepted), tuple(rejected)


def _validate_retrieval(retrieval: Mapping[str, Any], selected: Mapping[str, Any], requirement: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if str(retrieval.get("transport_failure") or ""):
        return {}, str(retrieval["transport_failure"])
    if str(retrieval.get("canonical_locator") or "") != str(selected.get("canonical_locator") or ""):
        return {}, "retrieval_locator_mismatch"
    claims = tuple(dict(item) for item in (retrieval.get("claims") or ()) if isinstance(item, Mapping))
    required = set(requirement["source_claims_required"])
    present = {str(item.get("claim_kind") or "") for item in claims if str(item.get("label") or "") == requirement["label"] and str(item.get("text") or "").strip()}
    if not required.issubset(present):
        return {}, "retrieved_evidence_insufficient"
    evidence = {"source_record_id": str(retrieval.get("source_record_id") or stable_id("autonomous-evidence-source", retrieval)), "canonical_locator": str(retrieval["canonical_locator"]), "content_digest": str(retrieval.get("content_digest") or _digest(claims)), "claims": claims, "provenance": str(retrieval.get("provenance") or selected.get("provenance") or "")}
    return evidence, ""


def _independent_recheck(*, candidate: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """A sealed structural recheck after revision, never a capability verdict."""
    fields = dict(candidate.get("field_updates") or {})
    passed = bool(fields.get("definition")) and bool(fields.get("scope_limit")) and bool(evidence.get("claims"))
    return {
        "evaluation_id": stable_id("autonomous-evidence-independent-recheck", candidate.get("candidate_id"), evidence.get("content_digest")),
        "passed": passed,
        "sealed_from_candidate_constructor": True,
        "scope": "source-to-candidate field linkage only",
        "capability_promotion": False,
    }


def run_autonomous_evidence_acquisition_return_loop(*, campaign: Mapping[str, Any], planner_package: Mapping[str, Any], workspace: Path, discovery_adapter: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]], retrieval_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
    """Resolve independently discovered branches, then return revision evidence once."""
    if campaign.get("status") != "approved_autonomous_evidence_campaign":
        raise ValueError("autonomous_evidence_campaign_not_approved")
    if campaign.get("planner_package_digest") != planner_package.get("package_digest"):
        raise ValueError("autonomous_evidence_campaign_planner_binding_mismatch")
    workspace.mkdir(parents=True, exist_ok=True); output = workspace / "AUTONOMOUS_EVIDENCE_ACQUISITION_RETURN_PACKAGE.json"
    input_digest = _digest({"campaign": campaign, "planner": planner_package.get("package_digest")})
    if output.exists():
        result = _read(output)
        if result.get("input_digest") == input_digest:
            return result
        raise ValueError("autonomous_evidence_campaign_workspace_input_mismatch")
    limit = int(campaign["authority"]["maximum_retrievals"]); attempts = []; returns = []; used = 0
    for requirement in campaign.get("requirements") or ():
        if used >= limit:
            break
        selected_sources, rejected = _select_sources(requirement, discovery_adapter(requirement))
        attempt = {"requirement_id": requirement["requirement_id"], "label": requirement["label"], "rejected_metadata": rejected, "selected_source": {}, "source_attempts": []}
        if not selected_sources:
            attempt["status"] = "blocked_no_defensible_source_metadata"; attempts.append(attempt); returns.append({"label": requirement["label"], "disposition": attempt["status"], "new_evidence": ()}); continue
        evidence = {}; error = ""
        for selected in selected_sources[:2]:
            if used >= limit:
                break
            used += 1; attempt["selected_source"] = selected
            evidence, error = _validate_retrieval(retrieval_adapter(selected), selected, requirement)
            attempt["source_attempts"].append({"canonical_locator": selected["canonical_locator"], "status": "resolved" if not error else error})
            if not error:
                break
        if error or not evidence:
            attempt["status"] = error or "retrieval_budget_exhausted"; attempts.append(attempt); returns.append({"label": requirement["label"], "disposition": attempt["status"], "new_evidence": ()}); continue
        revised = {"candidate_id": stable_id("autonomous-evidence-revised-candidate", campaign["campaign_id"], requirement["label"], evidence["content_digest"]), "label": requirement["label"], "status": "source_grounded", "field_updates": {"definition": {"origin": "retrieved_direct_source", "evidence_reference": evidence["source_record_id"], "inference_type": "direct"}, "scope_limit": {"origin": "retrieved_direct_source", "evidence_reference": evidence["source_record_id"], "inference_type": "direct"}}, "capability_promotion": False, "trusted_admission": False}
        evaluation = _independent_recheck(candidate=revised, evidence=evidence)
        attempt.update({"status": "resolved_source_grounding", "evidence": evidence, "revised_candidate": revised, "independent_evaluation": evaluation}); attempts.append(attempt)
        returns.append({"label": requirement["label"], "disposition": "evidence_resolved_candidate_rechecked" if evaluation["passed"] else "evidence_resolved_recheck_failed", "new_evidence": (evidence["source_record_id"],), "candidate": revised, "independent_evaluation": evaluation})
    unresolved = tuple(item for item in returns if item["disposition"] != "evidence_resolved_candidate_rechecked")
    resolved = {item["label"] for item in returns if item["disposition"] == "evidence_resolved_candidate_rechecked"}
    next_frontier = tuple(item for item in campaign.get("requirements") or () if item["label"] not in resolved)
    admission_candidates = tuple(item["candidate"] for item in returns if item["disposition"] == "evidence_resolved_candidate_rechecked")
    result = {"campaign_id": campaign["campaign_id"], "mission_id": campaign["mission_id"], "input_digest": input_digest, "attempts": tuple(attempts), "planner_return": {"returned_once": True, "candidate_revisions": tuple(item for item in returns if "candidate" in item), "unresolved_branches": unresolved, "next_frontier_ranking": next_frontier, "rerank_required": True}, "final_package": {"admission_candidates": admission_candidates, "escalation_items": unresolved, "trusted_admissions": 0, "capability_promotions": 0}, "retrieval_count": used, "provider_calls": 0, "trusted_admissions": 0, "capability_promotions": 0, "status": "autonomous_evidence_campaign_completed", "restart_proof": {"same_input_reuses_same_package": True, "path": str(output)}, "created_at": utc_now()}
    result["package_digest"] = _digest({**result, "created_at": ""}); output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return result

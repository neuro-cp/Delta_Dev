"""Context-sensitive, bounded search strategy for planner evidence contracts.

The module creates strategy records only.  Wikimedia discovery and RC8/PDF
retrieval remain the existing owners of network activity and terminal claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestration.runtime.autonomous_evidence_acquisition_return_loop import (
    compile_autonomous_evidence_campaign,
)
from orchestration.runtime.autonomous_live_evidence_transport import (
    run_autonomous_live_evidence_transport_integration,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.governed_live_metadata_search import (
    run_governed_live_metadata_discovery,
)


_STOP_WORDS = {
    "a", "an", "and", "as", "at", "be", "by", "can", "for", "from", "in",
    "is", "it", "of", "or", "that", "the", "this", "to", "under", "with",
    "whose", "when", "where", "which", "requires", "stated", "declared",
    "proposed", "structured", "account", "candidate", "primitive", "without",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _terms(value: str) -> tuple[str, ...]:
    return tuple(
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z_-]*", value)
        if word.lower() not in _STOP_WORDS and len(word) > 2
    )


def _candidate_context(*, node: Mapping[str, Any], objective: str) -> tuple[str, ...]:
    examples = " ".join(str(item.get("statement") or "") for item in node.get("examples", ()))
    counterexamples = " ".join(str(item.get("statement") or "") for item in node.get("counterexamples", ()))
    definition = str(node.get("definition") or "")
    raw = " ".join((definition, examples, counterexamples, objective))
    label_terms = set(_terms(str(node.get("canonical_label") or "")))
    values = []
    for term in _terms(raw):
        if term not in label_terms and term not in values:
            values.append(term)
    # Preserve relation-bearing adjacent terms from the definition, which are
    # more useful than generic wording repeated by campaign templates.
    relation_terms: list[str] = []
    words = _terms(definition)
    for left, right in zip(words, words[1:]):
        if left not in relation_terms:
            relation_terms.append(left)
        if right not in relation_terms:
            relation_terms.append(right)
    return tuple((relation_terms + [term for term in values if term not in relation_terms])[:8])


def _derive_search_sense(*, node: Mapping[str, Any], objective: str) -> dict[str, Any]:
    label = str(node["canonical_label"])
    context = _candidate_context(node=node, objective=objective)
    definition = str(node.get("definition") or "").strip()
    return {
        "sense_id": stable_id("autonomous-evidence-search-sense", label, definition, context),
        "label": label,
        "selected_sense": definition,
        "context_terms": context,
        "rejected_senses": (
            f"{label} used only as a surface label without the candidate's declared role",
            f"{label} in a source that does not address the requested evidence facets",
        ),
        "rationale": "derived from the workspace candidate definition, local examples, counterexamples, and broad objective",
    }


def _strategy_plan(*, requirement: Mapping[str, Any], sense: Mapping[str, Any], campaign_id: str, ordinal: int) -> dict[str, Any]:
    label = str(requirement["label"]).replace("_", " ")
    facets = tuple(str(item).replace("_", " ") for item in requirement["source_claims_required"])
    qualifiers = tuple(str(item) for item in sense["context_terms"][:5])
    role = ("definition", "scope")
    queries = (
        " ".join((label, *qualifiers, "definition")),
        " ".join((label, *qualifiers, *facets, "reference")),
        " ".join((label, *qualifiers, "example", "limitations")),
    )
    query_candidates = tuple(
        {
            "query_id": stable_id("autonomous-evidence-query", campaign_id, requirement["requirement_id"], index, query),
            "query": query,
            "role": role[min(index, len(role) - 1)] if index < 2 else "example_or_counterexample",
            "evidence_facets": facets if index < 2 else ("scope_limit",),
            "source_class_target": "university_educational_material",
            "excluded_ambiguity": sense["rejected_senses"],
            "expected_result": "candidate must address the selected sense and at least one requested facet in title or metadata",
            "rank": round(1.0 - index * 0.15, 2),
        }
        for index, query in enumerate(queries)
    )
    chosen = query_candidates[0]
    payload = {"campaign": campaign_id, "requirement": requirement["requirement_id"], "chosen": chosen["query_id"]}
    return {
        "search_plan_id": stable_id("autonomous-evidence-strategy-search-plan", _digest(payload)),
        "campaign_id": campaign_id,
        "branch_label": str(requirement["label"]),
        "requirement_id": requirement["requirement_id"],
        "primary_query": chosen["query"],
        "alternate_queries": tuple(item["query"] for item in query_candidates[1:]),
        "query_candidates": query_candidates,
        "selected_query_id": chosen["query_id"],
        "required_terms": tuple(label.lower().split()),
        "facet_terms": tuple(word for facet in facets for word in facet.lower().split()),
        "context_terms": qualifiers,
        "excluded_terms": ("credential", "token", "secret", "delta-75"),
        "preferred_source_classes": ("university_educational_material", "scholarly_metadata", "scholarly_reference_material", "recognized_reference"),
        "authority_class": "recognized_reference",
        "maximum_results": 10,
        "rationale": "runtime-authored query family ranked from the candidate's selected search sense and evidence contract",
        "plan_digest": _digest(payload),
        "ordinal": ordinal,
    }


def revise_failed_query_strategy(*, plan: Mapping[str, Any], failure_diagnosis: str) -> dict[str, Any]:
    """Create a non-equivalent next query candidate without issuing it."""
    prior = str(plan["primary_query"])
    alternates = tuple(str(item) for item in plan.get("alternate_queries", ()))
    replacement = next((item for item in alternates if item != prior), "")
    if not replacement:
        raise ValueError("evidence_strategy_no_material_query_revision")
    return {
        "revision_id": stable_id("autonomous-evidence-query-revision", plan["search_plan_id"], prior, replacement, failure_diagnosis),
        "prior_query": prior,
        "revised_query": replacement,
        "failure_diagnosis": failure_diagnosis,
        "changed_terms": tuple(term for term in _terms(replacement) if term not in set(_terms(prior))),
        "source_class_preference": tuple(plan["preferred_source_classes"]),
        "expected_improvement": "uses a distinct query role from the same evidence contract and selected sense",
        "replay_equivalent": False,
    }


def compile_autonomous_evidence_strategy_campaign(
    *, planner_package: Mapping[str, Any], seeding_package: Path, objective: str, maximum_frontiers: int = 3
) -> dict[str, Any]:
    """Choose pilot branches from the planner, never from caller labels or URLs."""
    if not 1 <= maximum_frontiers <= 3:
        raise ValueError("evidence_strategy_frontier_budget_invalid")
    base = compile_autonomous_evidence_campaign(planner_package=planner_package, maximum_retrievals=6)
    nodes = {str(node["canonical_label"]): node for node in _read(seeding_package)["nodes"]}
    requirements = tuple(base["requirements"][:maximum_frontiers])
    if not requirements:
        raise ValueError("evidence_strategy_no_planner_requirements")
    senses = []
    plans = []
    for ordinal, requirement in enumerate(requirements):
        node = nodes.get(str(requirement["label"]))
        if node is None:
            raise ValueError("evidence_strategy_candidate_context_missing")
        sense = _derive_search_sense(node=node, objective=objective)
        senses.append(sense)
        plans.append(_strategy_plan(requirement=requirement, sense=sense, campaign_id=base["campaign_id"], ordinal=ordinal))
    allocation = tuple(
        {
            "label": requirement["label"],
            "reserved_discovery_calls": 1,
            "reserved_retrievals": 1,
            "rationale": "one opportunity is reserved per viable branch before any branch may use a second retrieval",
        }
        for requirement in requirements
    )
    campaign_digest = _digest({"base": base["campaign_digest"], "plans": plans, "allocation": allocation})
    return {
        **base,
        "campaign_id": stable_id("autonomous-evidence-strategy-refinement", campaign_digest),
        "campaign_digest": campaign_digest,
        "requirements": requirements,
        "strategy_engine_id": stable_id("autonomous-evidence-strategy-engine", planner_package["mission_id"], campaign_digest),
        "semantic_senses": tuple(senses),
        "strategy_plans": tuple(plans),
        "budget_allocation": allocation,
        "status": "approved_autonomous_evidence_strategy_campaign",
    }


def _quality_gate(*, candidate: Mapping[str, Any], plan: Mapping[str, Any]) -> tuple[bool, str]:
    if not candidate.get("metadata_relevance_eligible"):
        return False, "label_or_facet_metadata_mismatch"
    text = f"{candidate.get('title', '')} {candidate.get('snippet', '')}".lower()
    qualifiers = tuple(str(item).lower() for item in plan.get("context_terms", ()))
    # A relation needs more than a shared noun: require multiple operational
    # roles in title/abstract metadata before spending a retrieval claim.
    if str(plan.get("branch_label")) == "cause":
        predicates=("produces","contributes","influences","leads to","results in","explains")
        factor=next((x for x in ("condition","action","factor","process","event") if x in text),"")
        outcome=next((x for x in ("outcome","effect","result","change","state") if x in text),"")
        predicate=next((x for x in predicates if x in text),"")
        scope=next((x for x in ("under","within","among","population","system","condition") if x in text),"")
        if any(x in text for x in ("marketing","mortality","finance","charitable")):
            return False, "rejected_semantic_sense"
        # Metadata only establishes that a bounded retrieval is worthwhile.
        # The full factor/outcome/predicate/scope contract is checked on body.
        if "causal" not in text and "cause" not in text:
            return False, "causal_sense_not_indicated"
    matched = {term for term in qualifiers if term in text}
    if len(matched) < min(3, len(qualifiers)):
        return False, "operational_relation_incomplete"
    if str(candidate.get("source_class") or "") not in set(plan["preferred_source_classes"]):
        return False, "source_class_not_preferred"
    return True, ""


def _with_quality_gate(*, discovery: Mapping[str, Any], campaign: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, tuple[dict[str, Any], ...]]]:
    by_plan = {str(plan["search_plan_id"]): plan for plan in campaign["strategy_plans"]}
    records = []
    accepted_by_label: dict[str, tuple[dict[str, Any], ...]] = {}
    for record in discovery["records"]:
        plan = by_plan[str(record["search_plan"]["search_plan_id"])]
        accepted = []
        rejected = []
        for candidate in record["normalized_candidates"]:
            allowed, reason = _quality_gate(candidate=candidate, plan=plan)
            if allowed:
                accepted.append(candidate)
            else:
                rejected.append({"title": candidate.get("title", ""), "canonical_locator": candidate.get("canonical_locator", ""), "reason": reason})
        accepted.sort(key=lambda item: (-float(item["ranking_score"]), str(item["canonical_locator"])))
        accepted_by_label[str(plan["branch_label"])] = tuple(accepted[:1])
        records.append({**record, "strategy_quality_accepted": tuple(accepted[:5]), "strategy_quality_rejected": tuple(rejected)})
    return {**discovery, "records": tuple(records)}, accepted_by_label


def run_autonomous_evidence_strategy_refinement(
    *, campaign: Mapping[str, Any], planner_package: Mapping[str, Any], workspace: Path,
    opener: Callable[..., Any] | None = None, rc8_executor: Callable[..., Any] | None = None,
    discovery_executor: Callable[..., Mapping[str, Any]] = run_governed_live_metadata_discovery,
) -> dict[str, Any]:
    """Execute one bounded strategy pilot using existing discovery and retrieval."""
    if campaign.get("status") != "approved_autonomous_evidence_strategy_campaign":
        raise ValueError("evidence_strategy_campaign_not_approved")
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / "AUTONOMOUS_EVIDENCE_STRATEGY_REFINEMENT_PACKAGE.json"
    input_digest = _digest({"campaign": campaign["campaign_digest"], "planner": planner_package["package_digest"]})
    if output.exists():
        prior = _read(output)
        if prior.get("input_digest") == input_digest:
            return prior
        raise ValueError("evidence_strategy_workspace_input_mismatch")
    kwargs: dict[str, Any] = {"campaign": campaign, "workspace": workspace / "discovery"}
    if opener is not None:
        kwargs["opener"] = opener
    discovery = discovery_executor(**kwargs)
    quality_discovery, accepted = _with_quality_gate(discovery=discovery, campaign=campaign)
    transport_campaign = {**campaign, "status": "approved_autonomous_evidence_campaign"}
    transport_kwargs: dict[str, Any] = {
        "campaign": transport_campaign,
        "planner_package": planner_package,
        "workspace": workspace / "retrieval",
        "metadata_discovery": lambda requirement: accepted.get(str(requirement["label"]), ()),
    }
    if rc8_executor is not None:
        transport_kwargs["rc8_executor"] = rc8_executor
    transport = run_autonomous_live_evidence_transport_integration(**transport_kwargs)
    feedback = tuple(
        {
            "label": attempt["label"],
            "query_effectiveness": "promising" if attempt["status"] == "resolved_source_grounding" else "insufficient_or_failed",
            "source_switch_condition": "retry only with a materially different strategy and fresh metadata",
            "revision_needed": attempt["status"] != "resolved_source_grounding",
        }
        for attempt in transport["attempts"]
    )
    revisions = tuple(
        revise_failed_query_strategy(plan=next(plan for plan in campaign["strategy_plans"] if plan["branch_label"] == item["label"]), failure_diagnosis="metadata_or_retrieval_insufficient")
        for item in feedback
        if item["revision_needed"]
    )
    result = {
        "strategy_engine_id": campaign["strategy_engine_id"],
        "campaign_id": campaign["campaign_id"],
        "mission_id": campaign["mission_id"],
        "input_digest": input_digest,
        "semantic_senses": campaign["semantic_senses"],
        "strategy_plans": campaign["strategy_plans"],
        "budget_allocation": campaign["budget_allocation"],
        "discovery": quality_discovery,
        "governed_retrieval": transport,
        "outcome_feedback": feedback,
        "pending_query_revisions": revisions,
        "frontier_reranking": tuple(
            {"label": item["label"], "strategy_outcome": item["query_effectiveness"], "next_action": "rerank_without_replay"}
            for item in feedback
        ),
        "provider_calls": 0,
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "status": "autonomous_evidence_strategy_refinement_completed",
        "restart_proof": {"same_input_reuses_same_package": True, "path": str(output)},
        "created_at": utc_now(),
    }
    result["package_digest"] = _digest({**result, "created_at": ""})
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result

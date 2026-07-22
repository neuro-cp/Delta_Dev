"""Bounded public metadata search for planner-authored evidence contracts."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.autonomous_live_evidence_transport import run_autonomous_live_evidence_transport_integration


WIKIMEDIA_SEARCH_ENDPOINT = "https://en.wikipedia.org/w/api.php"
MAX_RESPONSE_BYTES = 96_000
MAX_RESULTS = 10
SEARCH_TIMEOUT_SECONDS = 8.0
_QUERY_STOP_WORDS = frozenset({
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "is", "of",
    "or", "the", "to", "with",
})
_TEMPLATE_TERMS = frozenset({"definition", "scope", "limit", "limitations"})


def _digest(value: Any) -> str:
    body = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.path, parsed.query, ""))


def _operational_query_terms(definition: str, *, label: str) -> tuple[str, ...]:
    """Extract bounded relation-bearing terms from a candidate definition.

    The definition is a non-evidentiary workspace hypothesis.  It may guide
    discovery, but it never satisfies the evidence contract by itself.
    """
    words = tuple(
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z_-]*", definition)
        if word.lower() not in _QUERY_STOP_WORDS
        and word.lower() not in _TEMPLATE_TERMS
        and word.lower() != label.lower()
    )
    # Preserve first occurrence order, keeping the query compact enough for
    # public metadata endpoints and avoiding generic template vocabulary.
    unique: list[str] = []
    for word in words:
        if word not in unique:
            unique.append(word)
    return tuple(unique[:8])


def compile_runtime_search_plan(*, requirement: Mapping[str, Any], campaign_id: str, maximum_results: int = 5) -> dict[str, Any]:
    """Derive a domain-neutral metadata query from an evidence requirement."""
    if not 1 <= maximum_results <= MAX_RESULTS:
        raise ValueError("metadata_search_result_limit_invalid")
    label = str(requirement.get("label") or "").replace("_", " ").strip()
    if not label:
        raise ValueError("metadata_search_requirement_label_missing")
    facets = tuple(str(item) for item in (requirement.get("source_claims_required") or ()))
    query_facets = tuple(item.replace("_", " ") for item in facets)
    operational_definition = str(requirement.get("operational_definition") or "").strip()
    operational_terms = _operational_query_terms(operational_definition, label=label)
    primary = " ".join((label, *operational_terms)) if operational_terms else " ".join((label, *query_facets))
    alternate = f"{label} definition limitations"
    payload = {"campaign": campaign_id, "requirement": requirement.get("requirement_id"), "primary": primary, "alternate": alternate, "operational_definition": operational_definition, "operational_terms": operational_terms, "limit": maximum_results}
    return {"search_plan_id": stable_id("autonomous-live-metadata-search-plan", _digest(payload)), "campaign_id": campaign_id, "branch_label": label.replace(" ", "_"), "requirement_id": requirement.get("requirement_id"), "primary_query": primary, "alternate_queries": (alternate,), "operational_contract": {"subject": label, "working_definition": operational_definition, "relation_terms": operational_terms, "required_facets": facets}, "required_terms": tuple(label.split()), "facet_terms": tuple(word for facet in query_facets for word in facet.split()), "excluded_terms": ("credential", "token", "secret", "delta-75"), "preferred_source_classes": ("recognized_reference",), "authority_class": "recognized_reference", "maximum_results": maximum_results, "rationale": "derived from the planner candidate definition and evidence facets; snippets are ranking metadata only", "plan_digest": _digest(payload)}


def _normalize_raw_result(raw: Mapping[str, Any], *, plan: Mapping[str, Any], position: int) -> dict[str, Any]:
    title = re.sub(r"\s+", " ", html.unescape(str(raw.get("title") or ""))).strip()
    snippet = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(raw.get("snippet") or "")))).strip()
    locator = _canonical_url(f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}") if title else ""
    terms = tuple(str(item).lower() for item in (plan.get("required_terms") or ()))
    combined = f"{title} {snippet}".lower()
    directness = sum(term in combined for term in terms) / max(1, len(terms))
    facets = tuple(str(item).lower() for item in (plan.get("facet_terms") or ()))
    facet_coverage = sum(term in combined for term in facets) / max(1, len(facets))
    eligible = bool(title and locator and directness == 1.0 and facet_coverage > 0.0 and snippet)
    factors = {"authority": 0.7, "directness": directness, "facet_coverage": facet_coverage, "https": 1.0 if locator.startswith("https://") else 0.0, "stable_locator": 1.0 if locator else 0.0, "extractability": 0.8, "metadata_relevance": (directness + facet_coverage) / 2, "duplicate": 0.0, "prior_failure": 0.0, "retrieval_cost": 0.1}
    score = round(.28 * factors["authority"] + .25 * factors["directness"] + .1 * factors["facet_coverage"] + .12 * factors["https"] + .1 * factors["stable_locator"] + .1 * factors["extractability"] + .1 * factors["metadata_relevance"] - .05 * factors["retrieval_cost"], 6)
    return {"title": title, "canonical_locator": locator, "snippet": snippet, "display_domain": "en.wikipedia.org", "source_class": "recognized_reference", "supports_labels": (plan["branch_label"],), "provenance": f"governed_live_metadata_search:{plan['search_plan_id']}", "authority_score": factors["authority"], "retrieval_cost": factors["retrieval_cost"], "source_rank_position": position, "content_type_hint": "text/html", "metadata_only": True, "metadata_relevance_eligible": eligible, "ranking_factors": factors, "ranking_score": score}


def _search_request_url(plan: Mapping[str, Any]) -> str:
    query = urlencode({"action": "query", "list": "search", "srsearch": plan["primary_query"], "srlimit": int(plan["maximum_results"]), "format": "json", "formatversion": "2"})
    return f"{WIKIMEDIA_SEARCH_ENDPOINT}?{query}"


def execute_live_metadata_search(*, plan: Mapping[str, Any], opener: Callable[..., Any] = urlopen) -> dict[str, Any]:
    """Perform a single fixed-endpoint metadata query; never follow result URLs."""
    request_url = _search_request_url(plan)
    try:
        response = opener(Request(request_url, headers={"User-Agent": "DELTA-governed-metadata-search/1.0"}), timeout=SEARCH_TIMEOUT_SECONDS)
        with response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except TimeoutError:
        return {"outcome": "temporary_transport_failure", "raw_metadata": (), "failure_classification": "timeout", "request_digest": _digest(request_url)}
    except Exception as exc:  # noqa: BLE001
        return {"outcome": "temporary_transport_failure", "raw_metadata": (), "failure_classification": type(exc).__name__, "request_digest": _digest(request_url)}
    if len(raw) > MAX_RESPONSE_BYTES:
        return {"outcome": "invalid_response", "raw_metadata": (), "failure_classification": "response_budget_exceeded", "request_digest": _digest(request_url)}
    try:
        payload = json.loads(raw.decode("utf-8"))
        records = tuple(dict(item) for item in ((payload.get("query") or {}).get("search") or ()) if isinstance(item, Mapping))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return {"outcome": "invalid_response", "raw_metadata": (), "failure_classification": "malformed_json", "request_digest": _digest(request_url)}
    return {"outcome": "completed" if records else "no_results", "raw_metadata": records[:int(plan["maximum_results"])], "failure_classification": "", "request_digest": _digest(request_url), "raw_response_digest": _digest(raw)}


def run_governed_live_metadata_discovery(*, campaign: Mapping[str, Any], workspace: Path, opener: Callable[..., Any] = urlopen) -> dict[str, Any]:
    """Persist exact-once claims and normalized metadata for every campaign branch."""
    workspace.mkdir(parents=True, exist_ok=True); output = workspace / "GOVERNED_LIVE_METADATA_DISCOVERY_PACKAGE.json"
    strategy_plans = tuple(dict(item) for item in (campaign.get("strategy_plans") or ()))
    input_digest = _digest({"campaign": campaign.get("campaign_digest"), "requirements": campaign.get("requirements"), "strategy_plans": strategy_plans})
    if output.exists():
        prior = json.loads(output.read_text(encoding="utf-8"))
        if prior.get("input_digest") == input_digest:
            return prior
        raise ValueError("metadata_search_workspace_input_mismatch")
    calls = 0; records = []
    plans = strategy_plans or tuple(
        compile_runtime_search_plan(requirement=requirement, campaign_id=str(campaign["campaign_id"]))
        for requirement in (campaign.get("requirements") or ())[:2]
    )
    for plan in plans:
        claim = {"claim_id": stable_id("autonomous-live-metadata-discovery-claim", plan["search_plan_id"], plan["plan_digest"]), "search_plan_id": plan["search_plan_id"], "campaign_id": campaign["campaign_id"], "branch_label": plan["branch_label"], "state": "claimed", "attempt_count": 1, "request_digest": _digest(_search_request_url(plan)), "claimed_at": utc_now()}
        # Persist the claim before dispatch in a durable partial state.
        partial = {"input_digest": input_digest, "campaign_id": campaign["campaign_id"], "records": records + [{"search_plan": plan, "claim": claim, "status": "claimed"}]}
        output.write_text(json.dumps(partial, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        execution = execute_live_metadata_search(plan=plan, opener=opener); calls += 1
        normalized = tuple(_normalize_raw_result(item, plan=plan, position=index + 1) for index, item in enumerate(execution["raw_metadata"]))
        valid = tuple(item for item in normalized if item["title"] and item["canonical_locator"])
        rejected = tuple({"title": item.get("title", ""), "reason": "malformed_metadata"} for item in normalized if item not in valid)
        records.append({"search_plan": plan, "claim": {**claim, "state": "completed"}, "status": execution["outcome"], "failure_classification": execution["failure_classification"], "request_digest": execution["request_digest"], "raw_response_digest": execution.get("raw_response_digest", ""), "raw_metadata": execution["raw_metadata"], "raw_metadata_count": len(execution["raw_metadata"]), "normalized_candidates": valid, "rejected_candidates": rejected})
    result = {"discovery_executor_id": stable_id("governed-live-metadata-discovery-executor", campaign["campaign_id"]), "campaign_id": campaign["campaign_id"], "input_digest": input_digest, "transport_identity": "wikimedia_documented_public_metadata_api", "credentials_required": False, "records": tuple(records), "live_call_count": calls, "provider_calls": 0, "trusted_admissions": 0, "capability_promotions": 0, "status": "completed", "created_at": utc_now()}
    result["package_digest"] = _digest({**result, "created_at": ""}); output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return result


def run_autonomous_discovery_to_retrieval(*, campaign: Mapping[str, Any], planner_package: Mapping[str, Any], workspace: Path, opener: Callable[..., Any] = urlopen, rc8_executor: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Use runtime-owned discovery records as the sole source of retrieval metadata."""
    discovery = run_governed_live_metadata_discovery(campaign=campaign, workspace=workspace / "discovery", opener=opener)
    candidates_by_label = {str(record["search_plan"]["branch_label"]): tuple(record["normalized_candidates"]) for record in discovery["records"]}
    kwargs = {"campaign": campaign, "planner_package": planner_package, "workspace": workspace / "retrieval", "metadata_discovery": lambda requirement: candidates_by_label.get(str(requirement["label"]), ())}
    if rc8_executor is not None:
        kwargs["rc8_executor"] = rc8_executor
    transport = run_autonomous_live_evidence_transport_integration(**kwargs)
    return {"integration_id": stable_id("autonomous-discovery-to-retrieval", campaign["campaign_id"], discovery["package_digest"], transport["package_digest"]), "discovery": discovery, "transport": transport, "provider_calls": 0, "trusted_admissions": 0, "capability_promotions": 0}

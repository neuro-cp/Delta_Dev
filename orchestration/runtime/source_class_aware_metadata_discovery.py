"""No-credential scholarly metadata discovery selected by source-class need."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.autonomous_live_evidence_transport import (
    run_autonomous_live_evidence_transport_integration,
)


MAX_BYTES = 128_000
TIMEOUT_SECONDS = 10.0
TRANSPORTS = {
    "openalex_works": {"supported_source_classes": ("scholarly_metadata", "university_educational_material"), "endpoint": "https://api.openalex.org/works", "credentials_required": False, "rate_limit": "public_uncredentialed", "response_schema": "json.results", "domain_filters": False, "authority": 0.9},
    "crossref_works": {"supported_source_classes": ("scholarly_metadata", "scholarly_reference_material"), "endpoint": "https://api.crossref.org/works", "credentials_required": False, "rate_limit": "public", "response_schema": "json.message.items", "domain_filters": False, "authority": 0.88},
    "wikimedia_reference": {"supported_source_classes": ("recognized_reference",), "endpoint": "https://en.wikipedia.org/w/api.php", "credentials_required": False, "rate_limit": "public", "response_schema": "json.query.search", "domain_filters": False, "authority": 0.7},
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def select_transport(plan: Mapping[str, Any], prior_failures: tuple[str, ...] = ()) -> dict[str, Any]:
    preferred = tuple(plan.get("preferred_source_classes") or ())
    eligible = []
    for transport_id, declaration in TRANSPORTS.items():
        matches = set(preferred).intersection(declaration["supported_source_classes"])
        if matches and transport_id not in prior_failures:
            eligible.append((transport_id, declaration, sorted(matches)))
    if not eligible:
        return {"selected_transport": "", "eligible_transports": (), "rejected_transports": tuple({"transport": key, "reason": "source_class_or_prior_failure_mismatch"} for key in TRANSPORTS), "rationale": "no approved transport can serve the requested source classes"}
    eligible.sort(key=lambda item: (-item[1]["authority"], item[0]))
    selected = eligible[0]
    return {"selected_transport": selected[0], "eligible_transports": tuple({"transport": item[0], "source_class_matches": tuple(item[2])} for item in eligible), "rejected_transports": tuple({"transport": key, "reason": "not_selected"} for key in TRANSPORTS if key != selected[0]), "rationale": "selected from requested source class, authority, and prior transport history"}


def _url(transport: str, query: str) -> str:
    if transport == "openalex_works":
        return f"{TRANSPORTS[transport]['endpoint']}?{urlencode({'search': query, 'per-page': 3, 'select': 'id,display_name,doi,publication_year,best_oa_location,abstract_inverted_index'})}"
    if transport == "crossref_works":
        return f"{TRANSPORTS[transport]['endpoint']}?{urlencode({'query.bibliographic': query, 'rows': 5})}"
    return f"{TRANSPORTS[transport]['endpoint']}?{urlencode({'action':'query','list':'search','srsearch':query,'srlimit':5,'format':'json','formatversion':2})}"


def _open(url: str, opener: Callable[..., Any]) -> dict[str, Any]:
    try:
        response = opener(Request(url, headers={"User-Agent": "DELTA-source-class-discovery/1.0"}), timeout=TIMEOUT_SECONDS)
        with response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {"status": "invalid_response", "error": "response_budget_exceeded", "payload": {}}
        return {"status": "completed", "error": "", "payload": json.loads(raw.decode("utf-8")), "raw_digest": hashlib.sha256(raw).hexdigest()}
    except Exception as exc:  # noqa: BLE001
        return {"status": "transport_failure", "error": type(exc).__name__, "payload": {}}


def _candidate(record: Mapping[str, Any], transport: str, plan: Mapping[str, Any], position: int) -> dict[str, Any] | None:
    if transport == "openalex_works":
        title = str(record.get("display_name") or record.get("title") or ""); locator = str(((record.get("best_oa_location") or {}).get("landing_page_url") or record.get("doi") or ""));
        inverted = record.get("abstract_inverted_index") or {}
        ordered = sorted(((position, token) for token, positions in inverted.items() for position in positions), key=lambda item: item[0])
        snippet = " ".join(token for _, token in ordered[:180]) or str(record.get("publication_year") or "")
    elif transport == "crossref_works":
        title = str((record.get("title") or [""])[0]); locator = str(record.get("URL") or ""); snippet = str((record.get("container-title") or [""])[0])
    else:
        title = str(record.get("title") or ""); locator = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"; snippet = str(record.get("snippet") or "")
    if not title or not locator.startswith("https://"):
        return None
    contract = dict(plan.get("operational_contract") or {})
    relation_terms = tuple(str(item).lower() for item in (contract.get("relation_terms") or ()))
    combined = f"{title} {snippet}".lower()
    label = str(plan["branch_label"]).replace("_", " ").lower()
    matched_terms = tuple(term for term in relation_terms if term in combined)
    # When an operational contract is present, scholarly metadata must mention
    # the subject and enough of its relation to justify a source-body request.
    # Without a contract, preserve the existing metadata-only behavior.
    eligible = not relation_terms or (label in combined and len(matched_terms) >= 2)
    return {"title": title, "canonical_locator": locator, "snippet": snippet, "display_domain": locator.split("/")[2], "source_class": "scholarly_metadata" if transport != "wikimedia_reference" else "recognized_reference", "supports_labels": (plan["branch_label"],), "provenance": f"{transport}:{plan['search_plan_id']}", "authority_score": TRANSPORTS[transport]["authority"], "retrieval_cost": 0.2, "source_rank_position": position, "content_type_hint": "text/html", "metadata_only": True, "metadata_relevance_eligible": eligible, "metadata_relevance": {"subject_present": label in combined, "matched_relation_terms": matched_terms, "required_relation_term_count": 2 if relation_terms else 0, "decision": "eligible" if eligible else "operational_relation_incomplete"}, "ranking_score": round(TRANSPORTS[transport]["authority"] - position * .01, 3), "transport_identity": transport}


def run_source_class_aware_metadata_discovery(*, campaign: Mapping[str, Any], workspace: Path, opener: Callable[..., Any] = urlopen) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True); output = workspace / "SOURCE_CLASS_AWARE_METADATA_DISCOVERY.json"
    input_digest = _digest({"campaign": campaign["campaign_digest"], "plans": campaign["strategy_plans"]})
    if output.exists():
        prior = json.loads(output.read_text(encoding="utf-8"))
        if prior.get("input_digest") == input_digest: return prior
        raise ValueError("source_class_discovery_workspace_input_mismatch")
    records = []
    for plan in campaign["strategy_plans"]:
        selection = select_transport(plan, tuple(plan.get("prior_transport_failures") or ()))
        transport = selection["selected_transport"]
        claim = {"claim_id": stable_id("source-class-discovery-claim", campaign["campaign_id"], plan["search_plan_id"], transport), "state": "claimed", "attempt_count": 1}
        partial = {"input_digest": input_digest, "records": records + [{"search_plan": plan, "claim": claim, "selection": selection}]}
        output.write_text(json.dumps(partial, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        execution = _open(_url(transport, plan["primary_query"]), opener) if transport else {"status":"unavailable","error":"no_eligible_transport","payload":{}}
        raw = ((execution["payload"].get("results") or []) if transport == "openalex_works" else ((execution["payload"].get("message") or {}).get("items") or []) if transport == "crossref_works" else ((execution["payload"].get("query") or {}).get("search") or []))
        candidates = tuple(
            candidate
            for index, raw_item in enumerate(raw)
            if (candidate := _candidate(raw_item, transport, plan, index + 1)) is not None
        )
        records.append({"search_plan": plan, "claim": {**claim, "state":"completed"}, "selection": selection, "status": execution["status"], "failure_classification": execution["error"], "raw_response_digest": execution.get("raw_digest", ""), "normalized_candidates": candidates, "raw_metadata_count": len(raw)})
    result = {"discovery_executor_id": stable_id("source-class-aware-discovery", campaign["campaign_id"]), "campaign_id": campaign["campaign_id"], "input_digest": input_digest, "transport_declarations": TRANSPORTS, "records": tuple(records), "live_call_count": len(records), "provider_calls": 0, "trusted_admissions": 0, "capability_promotions": 0, "status":"completed", "created_at":utc_now()}
    result["package_digest"] = _digest({**result,"created_at":""}); output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return result


def run_source_class_aware_discovery_to_retrieval(
    *,
    campaign: Mapping[str, Any],
    planner_package: Mapping[str, Any],
    workspace: Path,
    opener: Callable[..., Any] = urlopen,
    rc8_executor: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Hand off persisted scholarly/reference metadata to the existing RC8 owner."""
    discovery = run_source_class_aware_metadata_discovery(
        campaign=campaign,
        workspace=workspace / "discovery",
        opener=opener,
    )
    candidates_by_label = {
        str(record["search_plan"]["branch_label"]): tuple(record["normalized_candidates"])
        for record in discovery["records"]
    }
    kwargs: dict[str, Any] = {
        "campaign": campaign,
        "planner_package": planner_package,
        "workspace": workspace / "retrieval",
        "metadata_discovery": lambda requirement: candidates_by_label.get(
            str(requirement["label"]), ()
        ),
    }
    if rc8_executor is not None:
        kwargs["rc8_executor"] = rc8_executor
    transport = run_autonomous_live_evidence_transport_integration(**kwargs)
    return {
        "integration_id": stable_id(
            "source-class-aware-discovery-to-retrieval",
            campaign["campaign_id"],
            discovery["package_digest"],
            transport["package_digest"],
        ),
        "discovery": discovery,
        "transport": transport,
        "provider_calls": 0,
        "trusted_admissions": 0,
        "capability_promotions": 0,
    }

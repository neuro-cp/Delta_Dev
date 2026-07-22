from __future__ import annotations

import json

from types import SimpleNamespace
from orchestration.runtime.governed_live_metadata_search import compile_runtime_search_plan, run_autonomous_discovery_to_retrieval, run_governed_live_metadata_discovery
from orchestration.runtime.autonomous_evidence_acquisition_return_loop import compile_autonomous_evidence_campaign


def _campaign():
    return {"campaign_id": "campaign", "campaign_digest": "campaign-digest", "requirements": ({"requirement_id": "condition", "label": "condition", "source_claims_required": ("definition", "scope_limit")}, {"requirement_id": "mechanism", "label": "mechanism", "source_claims_required": ("definition", "scope_limit")})}


class _Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, count): return self.payload


def _opener(request, timeout):
    assert "condition+definition+scope+limit" in request.full_url or "mechanism+definition+scope+limit" in request.full_url
    return _Response(json.dumps({"query": {"search": [{"title": "Condition (programming)", "snippet": "A condition is a test with a defined scope.", "timestamp": "2026-01-01T00:00:00Z"}]}}).encode())


def test_query_plan_is_evidence_contract_derived_and_has_no_url_input():
    plan = compile_runtime_search_plan(requirement=_campaign()["requirements"][0], campaign_id="campaign")
    assert plan["primary_query"] == "condition definition scope limit"
    assert "http" not in json.dumps(plan)


def test_operational_definition_generates_relation_bearing_query_without_template_terms():
    requirement = {
        "requirement_id": "mechanism",
        "label": "mechanism",
        "source_claims_required": ("definition", "scope_limit"),
        "operational_definition": "A mechanism is a structured account of intermediate relations from conditions to an outcome.",
    }
    plan = compile_runtime_search_plan(requirement=requirement, campaign_id="campaign")

    assert plan["primary_query"] == "mechanism structured account intermediate relations conditions outcome"
    assert plan["operational_contract"]["relation_terms"] == (
        "structured", "account", "intermediate", "relations", "conditions", "outcome",
    )
    assert "definition" not in plan["primary_query"]
    assert "scope" not in plan["primary_query"]


def test_frontier_without_operational_definition_preserves_legacy_query_shape():
    plan = compile_runtime_search_plan(requirement=_campaign()["requirements"][0], campaign_id="campaign")
    assert plan["primary_query"] == "condition definition scope limit"


def test_metadata_relevance_requires_label_and_required_facet(tmp_path):
    def unrelated(request, timeout): return _Response(json.dumps({"query": {"search": [{"title": "Condition", "snippet": "A short unrelated entry."}]}}).encode())
    result = run_governed_live_metadata_discovery(campaign={**_campaign(), "requirements": _campaign()["requirements"][:1]}, workspace=tmp_path, opener=unrelated)
    assert result["records"][0]["normalized_candidates"][0]["metadata_relevance_eligible"] is False


def test_live_metadata_claim_persists_normalizes_and_restarts_without_replay(tmp_path):
    first = run_governed_live_metadata_discovery(campaign=_campaign(), workspace=tmp_path, opener=_opener)
    assert first["live_call_count"] == 2
    assert all(record["claim"]["state"] == "completed" for record in first["records"])
    assert all(candidate["metadata_only"] for record in first["records"] for candidate in record["normalized_candidates"])
    second = run_governed_live_metadata_discovery(campaign=_campaign(), workspace=tmp_path, opener=lambda *_: (_ for _ in ()).throw(AssertionError("replayed")))
    assert first["package_digest"] == second["package_digest"]


def test_malformed_or_oversized_response_is_durable_non_evidentiary_result(tmp_path):
    def malformed(request, timeout): return _Response(b"not json")
    result = run_governed_live_metadata_discovery(campaign={**_campaign(), "requirements": (_campaign()["requirements"][0],)}, workspace=tmp_path, opener=malformed)
    assert result["records"][0]["status"] == "invalid_response"
    assert not result["records"][0]["normalized_candidates"]


def test_normalized_runtime_discovery_candidates_are_the_only_retrieval_handoff(tmp_path):
    planner = {"planner_executor_id": "planner", "mission_id": "mission", "package_digest": "planner", "initial_ranking": ({"label": "condition", "score": .9},), "blocked_branches": ({"label": "condition", "blocker": "missing_direct_retained_source_grounding"},)}
    campaign = compile_autonomous_evidence_campaign(planner_package=planner, maximum_retrievals=1)
    def rc8(request, *, env, policy):
        source = SimpleNamespace(source_id="source", sanitized_text="A condition is a test. A condition applies only when the expression is true.", provenance=SimpleNamespace(url=request.target, provenance_id="provenance"))
        return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")
    result = run_autonomous_discovery_to_retrieval(campaign=campaign, planner_package=planner, workspace=tmp_path, opener=_opener, rc8_executor=rc8)
    assert result["discovery"]["records"][0]["raw_metadata"]
    assert result["transport"]["attempts"][0]["selected_source"]["canonical_locator"].startswith("https://en.wikipedia.org/wiki/")

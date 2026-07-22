from __future__ import annotations

import json

from types import SimpleNamespace

from orchestration.runtime.source_class_aware_metadata_discovery import (
    run_source_class_aware_discovery_to_retrieval,
    run_source_class_aware_metadata_discovery,
    select_transport,
)
from orchestration.runtime.autonomous_evidence_acquisition_return_loop import (
    compile_autonomous_evidence_campaign,
)


class _Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, _): return self.body


def _campaign():
    plan = {"search_plan_id":"plan", "branch_label":"condition", "requirement_id":"req", "primary_query":"condition required definition", "preferred_source_classes":("university_educational_material","scholarly_metadata"), "campaign_id":"campaign", "maximum_results":5}
    return {"campaign_id":"campaign", "campaign_digest":"digest", "strategy_plans":(plan,)}


def test_source_class_selection_prefers_scholarly_transport_over_wikimedia():
    selected = select_transport(_campaign()["strategy_plans"][0])
    assert selected["selected_transport"] == "openalex_works"
    assert "wikimedia_reference" not in {item["transport"] for item in selected["eligible_transports"]}


def test_openalex_metadata_is_normalized_without_source_body_or_credentials(tmp_path):
    def opener(request, timeout):
        assert request.full_url.startswith("https://api.openalex.org/works?")
        assert "select=id%2Cdisplay_name%2Cdoi" in request.full_url
        payload = {"results":[{"display_name":"Conditions in causal reasoning", "doi":"https://doi.org/10.1000/example", "publication_year":2024}]}
        return _Response(json.dumps(payload).encode())
    result = run_source_class_aware_metadata_discovery(campaign=_campaign(), workspace=tmp_path, opener=opener)
    record = result["records"][0]
    assert record["selection"]["selected_transport"] == "openalex_works"
    assert record["normalized_candidates"][0]["source_class"] == "scholarly_metadata"
    assert result["provider_calls"] == result["trusted_admissions"] == result["capability_promotions"] == 0
    replay = run_source_class_aware_metadata_discovery(campaign=_campaign(), workspace=tmp_path, opener=lambda *_: (_ for _ in ()).throw(AssertionError("replayed")))
    assert replay["package_digest"] == result["package_digest"]


def test_scholarly_metadata_hands_off_to_existing_governed_retrieval(tmp_path):
    planner = {
        "planner_executor_id": "planner",
        "mission_id": "mission",
        "package_digest": "planner",
        "initial_ranking": ({"label": "condition", "score": 0.9},),
        "blocked_branches": ({"label": "condition", "blocker": "missing_direct_retained_source_grounding"},),
    }
    campaign = {
        **compile_autonomous_evidence_campaign(planner_package=planner, maximum_retrievals=1),
        "strategy_plans": _campaign()["strategy_plans"],
    }

    def opener(request, timeout):
        payload = {"results": [{
            "display_name": "Conditions in causal reasoning",
            "doi": "https://doi.org/10.1000/example",
            "publication_year": 2024,
        }]}
        return _Response(json.dumps(payload).encode())

    def rc8(request, *, env, policy):
        source = SimpleNamespace(
            source_id="source",
            sanitized_text="A condition is a requirement. A condition applies only when the requirement holds.",
            provenance=SimpleNamespace(url=request.target, provenance_id="provenance"),
        )
        return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")

    result = run_source_class_aware_discovery_to_retrieval(
        campaign=campaign,
        planner_package=planner,
        workspace=tmp_path,
        opener=opener,
        rc8_executor=rc8,
    )
    assert result["transport"]["retrieval_count"] == 1


def test_operational_contract_rejects_scholarly_metadata_without_relation_support(tmp_path):
    campaign = _campaign()
    plan = {
        **campaign["strategy_plans"][0],
        "operational_contract": {
            "subject": "condition",
            "relation_terms": ("requirement", "governing", "transition", "outcome"),
        },
    }
    campaign = {**campaign, "strategy_plans": (plan,)}

    def opener(request, timeout):
        payload = {"results": [{
            "display_name": "Condition monitoring for machinery",
            "doi": "https://doi.org/10.1000/example",
            "publication_year": 2024,
        }]}
        return _Response(json.dumps(payload).encode())

    result = run_source_class_aware_metadata_discovery(campaign=campaign, workspace=tmp_path, opener=opener)
    candidate = result["records"][0]["normalized_candidates"][0]
    assert candidate["metadata_relevance_eligible"] is False
    assert candidate["metadata_relevance"]["decision"] == "operational_relation_incomplete"

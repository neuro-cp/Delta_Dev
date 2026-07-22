from __future__ import annotations

from types import SimpleNamespace

from orchestration.runtime.autonomous_evidence_acquisition_return_loop import compile_autonomous_evidence_campaign
from orchestration.runtime.autonomous_live_evidence_transport import (
    retrieve_candidate_via_existing_governed_transport,
    run_autonomous_live_evidence_transport_integration,
)


def _planner():
    return {"planner_executor_id": "planner", "mission_id": "mission", "package_digest": "planner-digest", "initial_ranking": ({"label": "condition", "score": .9}, {"label": "mechanism", "score": .7}), "blocked_branches": ({"label": "condition", "blocker": "missing_direct_retained_source_grounding"}, {"label": "mechanism", "blocker": "missing_direct_retained_source_grounding"})}


def _discovery(requirement):
    label = requirement["label"]
    return ({"title": f"University {label}", "canonical_locator": f"https://casesensitive.example.edu/Toolkit24/{label}", "source_class": "peer_reviewed_or_academic", "supports_labels": (label,), "provenance": "existing metadata-only discovery fixture", "authority_score": .9, "retrieval_cost": .1},)


def _rc8(request, *, env, policy):
    assert env["RC8_RETRIEVAL_ENABLED"] == "1"
    assert policy.domain_policy.allowlist == ("casesensitive.example.edu",)
    text = "A condition is a stated requirement. A condition applies only when its stated scope holds."
    source = SimpleNamespace(source_id="source", sanitized_text=text, provenance=SimpleNamespace(url=request.target, provenance_id="provenance"))
    return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")


def test_live_bridge_uses_rc8_and_preserves_case_sensitive_path(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=1)
    result = run_autonomous_live_evidence_transport_integration(campaign=campaign, planner_package=_planner(), workspace=tmp_path, metadata_discovery=_discovery, rc8_executor=_rc8)
    attempt = result["attempts"][0]
    assert result["transport_owner"] == "rc8_governed_external_retrieval_and_governed_pdf_extraction"
    assert attempt["status"] == "resolved_source_grounding"
    assert attempt["evidence"]["canonical_locator"].endswith("/Toolkit24/condition")
    assert attempt["independent_evaluation"]["sealed_from_candidate_constructor"]
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_live_bridge_fails_closed_when_transport_evidence_has_only_keyword_overlap(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=1)
    def weak(*args, **kwargs):
        source = SimpleNamespace(source_id="source", sanitized_text="condition condition condition", provenance=SimpleNamespace(url=args[0].target, provenance_id="provenance"))
        return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")
    result = run_autonomous_live_evidence_transport_integration(campaign=campaign, planner_package=_planner(), workspace=tmp_path, metadata_discovery=_discovery, rc8_executor=weak)
    assert result["attempts"][0]["status"] == "retrieved_evidence_insufficient"


def test_live_bridge_persists_terminal_transport_failure_and_does_not_replay(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=1)
    def failure(*args, **kwargs):
        raise OSError("fixture network failure")
    first = run_autonomous_live_evidence_transport_integration(campaign=campaign, planner_package=_planner(), workspace=tmp_path, metadata_discovery=_discovery, rc8_executor=failure)
    assert first["attempts"][0]["status"] == "transport_failure:OSError"
    assert first["transport_claims"][0]["state"] == "failed"
    # The result is already persisted, so a restart cannot invoke transport.
    second = run_autonomous_live_evidence_transport_integration(campaign=campaign, planner_package=_planner(), workspace=tmp_path, metadata_discovery=lambda _: (_ for _ in ()).throw(AssertionError("discovery replayed")), rc8_executor=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("transport replayed")))
    assert second["package_digest"] == first["package_digest"]


def test_wikipedia_budget_failure_uses_only_a_bounded_extract_of_the_same_page():
    candidate = {
        "canonical_locator": "https://en.wikipedia.org/wiki/Grammar",
        "bounded_extract_permitted": True,
    }
    def oversized(*args, **kwargs):
        return SimpleNamespace(bundle=None, decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="content_budget_exhausted")
    result = retrieve_candidate_via_existing_governed_transport(
        candidate,
        rc8_executor=oversized,
        wikipedia_retriever=lambda locator: {
            "canonical_locator": locator,
            "content_digest": "bounded-digest",
            "extraction_digest": "bounded-extract-digest",
            "content_text": "Grammar is a language system. Grammar may vary by context.",
            "bounded_extract": True,
        },
    )
    assert result["bounded_extract"] is True
    assert result["canonical_locator"] == candidate["canonical_locator"]


def test_budget_failure_does_not_fallback_for_unapproved_or_non_wikipedia_hosts():
    def oversized(*args, **kwargs):
        return SimpleNamespace(bundle=None, decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="content_budget_exhausted")
    for candidate in (
        {"canonical_locator": "https://en.wikipedia.org/wiki/Grammar"},
        {"canonical_locator": "https://example.edu/grammar", "bounded_extract_permitted": True},
    ):
        try:
            retrieve_candidate_via_existing_governed_transport(candidate, rc8_executor=oversized, wikipedia_retriever=lambda _locator: (_ for _ in ()).throw(AssertionError("fallback broadened")))
        except ValueError as exc:
            assert "content_budget_exhausted" in str(exc)
        else:
            raise AssertionError("unapproved bounded fallback was accepted")

from __future__ import annotations

from orchestration.runtime.autonomous_evidence_acquisition_return_loop import compile_autonomous_evidence_campaign, compile_followup_autonomous_evidence_campaign, run_autonomous_evidence_acquisition_return_loop


def _planner():
    return {"planner_executor_id": "planner", "mission_id": "mission", "package_digest": "planner-digest", "initial_ranking": ({"label": "cause", "score": .9}, {"label": "state", "score": .6}), "blocked_branches": ({"label": "cause", "blocker": "missing_direct_retained_source_grounding"}, {"label": "state", "blocker": "missing_direct_retained_source_grounding"})}


def _discover(requirement):
    label = requirement["label"]
    return ({"title": f"Institutional {label}", "canonical_locator": f"https://example.edu/{label}", "source_class": "peer_reviewed_or_academic", "supports_labels": (label,), "provenance": "fixture metadata", "authority_score": .9, "retrieval_cost": .1},)


def _retrieve(selected):
    label = selected["supports_labels"][0]
    return {"canonical_locator": selected["canonical_locator"], "source_record_id": f"record-{label}", "content_digest": f"digest-{label}", "provenance": "fixture retrieval", "claims": ({"label": label, "claim_kind": "definition", "text": f"{label} definition"}, {"label": label, "claim_kind": "scope_limit", "text": f"{label} scope"})}


def test_campaign_prioritizes_planner_escalations_and_returns_revisions(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=2)
    result = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=_planner(), workspace=tmp_path, discovery_adapter=_discover, retrieval_adapter=_retrieve)
    assert [item["label"] for item in result["attempts"]] == ["cause", "state"]
    assert result["retrieval_count"] == 2
    assert len(result["planner_return"]["candidate_revisions"]) == 2
    assert all(item["independent_evaluation"]["sealed_from_candidate_constructor"] for item in result["planner_return"]["candidate_revisions"])
    assert len(result["final_package"]["admission_candidates"]) == 2
    assert result["planner_return"]["rerank_required"]
    assert result["provider_calls"] == result["trusted_admissions"] == result["capability_promotions"] == 0


def test_insufficient_source_is_preserved_and_does_not_freeze_other_branch(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=2)
    def retrieve(selected):
        if selected["supports_labels"] == ("cause",):
            return {"canonical_locator": selected["canonical_locator"], "claims": ()}
        return _retrieve(selected)
    result = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=_planner(), workspace=tmp_path, discovery_adapter=_discover, retrieval_adapter=retrieve)
    assert result["attempts"][0]["status"] == "retrieved_evidence_insufficient"
    assert result["attempts"][1]["status"] == "resolved_source_grounding"
    assert len(result["planner_return"]["unresolved_branches"]) == 1


def test_restart_reuses_one_campaign_result_without_retrieval(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=1)
    first = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=_planner(), workspace=tmp_path, discovery_adapter=_discover, retrieval_adapter=_retrieve)
    second = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=_planner(), workspace=tmp_path, discovery_adapter=lambda _: (_ for _ in ()).throw(AssertionError("replayed")), retrieval_adapter=lambda _: (_ for _ in ()).throw(AssertionError("replayed")))
    assert first["package_digest"] == second["package_digest"]


def test_followup_campaign_derives_only_unresolved_and_next_frontier_labels():
    prior = {"mission_id": "mission", "campaign_id": "prior", "package_digest": "prior-digest", "planner_return": {"unresolved_branches": ({"label": "cause"},), "next_frontier_ranking": ({"label": "state"},)}}
    followup = compile_followup_autonomous_evidence_campaign(planner_package=_planner(), prior_return=prior, maximum_retrievals=2)
    assert [item["label"] for item in followup["requirements"]] == ["cause", "state"]
    assert followup["followup_of_campaign_id"] == "prior"
    replacement = compile_followup_autonomous_evidence_campaign(planner_package=_planner(), prior_return=prior, maximum_retrievals=2, replacement_reason="metadata_ranking_relevance_policy_repair")
    assert replacement["campaign_id"] != followup["campaign_id"]


def test_campaign_accepts_the_authorized_live_transport_budget_of_six():
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=6)
    assert campaign["authority"]["maximum_retrievals"] == 6


def test_campaign_carries_workspace_definition_as_non_evidentiary_operational_contract():
    planner = _planner()
    planner["competence_map"] = {
        "cause": {"workspace_candidate_reference": {"definition": "A cause connects a factor to an outcome."}},
        "state": {"workspace_candidate_reference": {"definition": "A state is a bounded system condition."}},
    }
    campaign = compile_autonomous_evidence_campaign(planner_package=planner, maximum_retrievals=1)
    assert campaign["requirements"][0]["operational_definition"] == "A cause connects a factor to an outcome."


def test_failed_top_source_continues_to_next_ranked_candidate_in_same_branch(tmp_path):
    campaign = compile_autonomous_evidence_campaign(planner_package=_planner(), maximum_retrievals=2)
    def discovery(requirement):
        label = requirement["label"]
        return (
            {"title": "first", "canonical_locator": f"https://one.example.edu/{label}", "source_class": "peer_reviewed_or_academic", "supports_labels": (label,), "provenance": "fixture", "authority_score": 1.0, "retrieval_cost": .1},
            {"title": "second", "canonical_locator": f"https://two.example.edu/{label}", "source_class": "peer_reviewed_or_academic", "supports_labels": (label,), "provenance": "fixture", "authority_score": .8, "retrieval_cost": .1},
        )
    def retrieve(selected):
        if selected["canonical_locator"].startswith("https://one"):
            return {"canonical_locator": selected["canonical_locator"], "claims": ()}
        return _retrieve(selected)
    result = run_autonomous_evidence_acquisition_return_loop(campaign=campaign, planner_package=_planner(), workspace=tmp_path, discovery_adapter=discovery, retrieval_adapter=retrieve)
    assert result["attempts"][0]["status"] == "resolved_source_grounding"
    assert [item["status"] for item in result["attempts"][0]["source_attempts"]] == ["retrieved_evidence_insufficient", "resolved"]

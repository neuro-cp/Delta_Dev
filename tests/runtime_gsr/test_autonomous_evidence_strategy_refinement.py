from __future__ import annotations

import json
from types import SimpleNamespace

from orchestration.runtime.autonomous_evidence_strategy_refinement import (
    compile_autonomous_evidence_strategy_campaign,
    revise_failed_query_strategy,
    run_autonomous_evidence_strategy_refinement,
)


def _seed(path):
    labels = ("cause", "condition", "mechanism", "outcome")
    definitions = {
        "cause": "A cause is a proposed factor whose effect requires evidence and stated scope.",
        "condition": "A condition is a stated circumstance required for a claim or transition.",
        "mechanism": "A mechanism is a structured account of intermediate relations from conditions to an outcome.",
        "outcome": "An outcome is an observed result after stated conditions and a proposed mechanism.",
    }
    nodes = [{"primitive_id": f"id-{label}", "canonical_label": label, "definition": definitions[label], "examples": [{"statement": definitions[label]}], "counterexamples": [{"statement": "A surface label alone is insufficient."}], "status": "partially_formalized", "retained_support": [], "unresolved_obligations": ["source"]} for label in labels]
    path.write_text(json.dumps({"package_digest": "seed", "nodes": nodes}), encoding="utf-8")


def _planner():
    return {
        "mission_id": "mission", "planner_executor_id": "planner", "package_digest": "planner-digest",
        "initial_ranking": tuple({"label": label, "score": 1.0 - index * .1} for index, label in enumerate(("cause", "condition", "mechanism"))),
        "blocked_branches": tuple({"label": label, "blocker": "missing_direct_retained_source_grounding"} for label in ("cause", "condition", "mechanism")),
    }


class _Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, _): return self.body


def test_strategy_is_context_derived_multiqueue_and_reserves_each_branch(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    campaign = compile_autonomous_evidence_strategy_campaign(planner_package=_planner(), seeding_package=seed, objective="Reason accurately about causes, conditions, mechanisms, and evidence.")
    assert len(campaign["semantic_senses"]) == 3
    assert all(len(plan["query_candidates"]) >= 2 for plan in campaign["strategy_plans"])
    assert "whose" not in campaign["strategy_plans"][0]["primary_query"]
    assert "proposed" not in campaign["strategy_plans"][0]["primary_query"]
    assert all(item["reserved_retrievals"] == 1 for item in campaign["budget_allocation"])
    assert all("surface label" in sense["rejected_senses"][0] for sense in campaign["semantic_senses"])
    revision = revise_failed_query_strategy(plan=campaign["strategy_plans"][0], failure_diagnosis="label_only_metadata")
    assert revision["prior_query"] != revision["revised_query"]
    assert not revision["replay_equivalent"]


def test_quality_gate_rejects_label_only_metadata_and_returns_existing_transport_once(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    campaign = compile_autonomous_evidence_strategy_campaign(planner_package=_planner(), seeding_package=seed, objective="Reason accurately about causes, conditions, mechanisms, and evidence.")
    def opener(request, timeout):
        query = request.full_url.lower()
        if "cause" in query:
            title, snippet = "Cause", "A cause is a proposed factor with evidence in a stated scope."
        else:
            title, snippet = "Condition", "Condition is a label in an unrelated listing."
        return _Response(json.dumps({"query": {"search": [{"title": title, "snippet": snippet}]}}).encode())
    def rc8(request, *, env, policy):
        text = "A cause is a proposed factor in a stated setting. A cause applies only when the stated evidence setting holds."
        source = SimpleNamespace(source_id="cause-source", sanitized_text=text, provenance=SimpleNamespace(url=request.target, provenance_id="cause-provenance"))
        return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")
    result = run_autonomous_evidence_strategy_refinement(campaign=campaign, planner_package=_planner(), workspace=tmp_path / "work", opener=opener, rc8_executor=rc8)
    records = {record["search_plan"]["branch_label"]: record for record in result["discovery"]["records"]}
    assert records["condition"]["strategy_quality_rejected"]
    assert result["governed_retrieval"]["attempts"][0]["status"] == "resolved_source_grounding"
    assert result["provider_calls"] == result["trusted_admissions"] == result["capability_promotions"] == 0
    replay = run_autonomous_evidence_strategy_refinement(campaign=campaign, planner_package=_planner(), workspace=tmp_path / "work", opener=lambda *_: (_ for _ in ()).throw(AssertionError("replayed")), rc8_executor=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("replayed")))
    assert replay["package_digest"] == result["package_digest"]

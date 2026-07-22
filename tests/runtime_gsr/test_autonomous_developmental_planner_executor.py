from __future__ import annotations

import json

from orchestration.runtime.autonomous_developmental_planner_executor import compile_autonomous_developmental_mission, run_autonomous_developmental_planner_executor


def _seed(path):
    labels = ("cause", "mechanism", "condition", "outcome", "constraint", "state", "transition", "uncertainty", "evidence", "claim")
    nodes = [{"primitive_id": f"id-{label}", "canonical_label": label, "status": "partially_formalized", "retained_support": [], "unresolved_obligations": ["source"]} for label in labels]
    nodes[4]["status"] = "source_grounded"; nodes[4]["retained_support"] = [{"source": "retained"}]
    path.write_text(json.dumps({"package_digest": "seed-digest", "nodes": nodes}), encoding="utf-8")


def test_broad_objective_derives_and_reranks_frontier_without_supplied_list(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    mission = compile_autonomous_developmental_mission(objective="Improve reasoning about causes, constraints, state changes, uncertainty, and evidence.", seeding_package=seed, trusted_layer_snapshot={"records": [{"canonical_label": "constraint", "primitive_id": "id-constraint"}]})
    result = run_autonomous_developmental_planner_executor(mission=mission, seeding_package=seed, workspace=tmp_path / "work")
    assert result["initial_ranking"]
    assert {"cause", "constraint", "state", "transition", "uncertainty", "evidence"}.issubset(result["competence_audit"]["requirements"])
    assert all("evaluator_only" not in cycle["outcome"]["learner_view"] for cycle in result["cycles"])
    assert all(cycle["outcome"]["evaluation"]["sealed_from_learner"] for cycle in result["cycles"])
    assert all(cycle["outcome"]["candidate"]["field_justification"]["definition"]["evidence_reference"] for cycle in result["cycles"])
    assert result["cycles"][0]["frontier"]["label"] != result["cycles"][1]["frontier"]["label"]
    assert result["final_package"]["trusted_admissions"] == result["final_package"]["capability_promotions"] == 0
    assert result["blocked_branches"]


def test_objective_inflection_is_conservative_and_does_not_require_a_frontier(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    mission = compile_autonomous_developmental_mission(objective="Reason about causes, constraints, and state changes.", seeding_package=seed, trusted_layer_snapshot={"records": []})
    result = run_autonomous_developmental_planner_executor(mission=mission, seeding_package=seed, workspace=tmp_path / "work")
    assert {"cause", "constraint", "state", "transition"}.issubset(result["competence_audit"]["requirements"])
    assert all(item["local_recovery_possible"] is False for item in result["blocked_branches"])


def test_restart_is_duplicate_safe(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed); mission = compile_autonomous_developmental_mission(objective="Reason about causes and uncertainty.", seeding_package=seed, trusted_layer_snapshot={"records": []})
    first = run_autonomous_developmental_planner_executor(mission=mission, seeding_package=seed, workspace=tmp_path / "work")
    second = run_autonomous_developmental_planner_executor(mission=mission, seeding_package=seed, workspace=tmp_path / "work")
    assert first["package_digest"] == second["package_digest"]


def test_supported_branch_updates_competence_then_routes_to_next_gap(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    payload = json.loads(seed.read_text(encoding="utf-8"))
    payload["nodes"][0]["retained_support"] = [{"source": "retained-cause"}]
    payload["nodes"][0]["status"] = "source_grounded"
    seed.write_text(json.dumps(payload), encoding="utf-8")
    mission = compile_autonomous_developmental_mission(objective="Reason about causes and uncertainty.", seeding_package=seed, trusted_layer_snapshot={"records": []})
    result = run_autonomous_developmental_planner_executor(mission=mission, seeding_package=seed, workspace=tmp_path / "work")
    cause = next(cycle for cycle in result["cycles"] if cycle["frontier"]["label"] == "cause")
    assert cause["outcome"]["disposition"] == "semantic_readiness_candidate"
    assert result["competence_map"]["cause"]["outcomes"] == ("semantic_readiness_candidate",)
    assert all(item["label"] != "cause" for item in result["next_frontier_ranking"])


def test_capacity_deferred_frontiers_remain_available_to_evidence_continuation(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    mission = compile_autonomous_developmental_mission(
        objective="Reason about causes, state changes, uncertainty, and evidence.",
        seeding_package=seed,
        trusted_layer_snapshot={"records": []},
    )
    mission = {**mission, "maximum_frontiers": 1}
    result = run_autonomous_developmental_planner_executor(
        mission=mission,
        seeding_package=seed,
        workspace=tmp_path / "work",
    )

    deferred = [item for item in result["blocked_branches"] if item.get("deferred_by") == "local_frontier_capacity"]
    assert deferred
    assert {item["label"] for item in deferred}.issubset(
        {item["label"] for item in result["next_frontier_ranking"]}
    )

from __future__ import annotations

import json

from orchestration.runtime.foundational_primitive_independent_use import compile_foundational_primitive_independent_use_campaign, run_foundational_primitive_independent_use_campaign


def _seed(path):
    nodes = []
    labels = ("object", "property", "relation", "state", "transition", "condition", "cause", "mechanism", "constraint", "quantity", "claim", "evidence", "uncertainty", "example", "counterexample", "value", "type", "variable", "function", "state_transition", "outcome", "time", "interest", "growth", "risk")
    for label in labels:
        nodes.append({"primitive_id": f"p-{label}", "canonical_label": label, "status": "source_grounded" if label in {"constraint", "interest"} else "partially_formalized"})
    path.write_text(json.dumps({"execution_id": "seed", "package_digest": "seed-digest", "nodes": nodes}), encoding="utf-8")


def test_independent_use_keeps_evaluator_fields_out_of_learner_view(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    campaign = compile_foundational_primitive_independent_use_campaign(seeding_package=seed)
    result = run_foundational_primitive_independent_use_campaign(campaign=campaign, seeding_package=seed, workspace=tmp_path / "work")
    assert result["evaluation_summary"] == {"total": 3, "passed": 3, "failed": 0, "evaluator_isolated_from_learner_view": True}
    assert all("evaluator" not in record["learner_view"] for record in result["attempts"])
    assert len(result["semantic_ready_candidates"]) == 2
    assert result["trusted_memory_admissions"] == result["capability_promotions"] == 0


def test_independent_use_is_restart_safe_and_digest_bound(tmp_path):
    seed = tmp_path / "seed.json"; _seed(seed)
    campaign = compile_foundational_primitive_independent_use_campaign(seeding_package=seed)
    first = run_foundational_primitive_independent_use_campaign(campaign=campaign, seeding_package=seed, workspace=tmp_path / "work")
    second = run_foundational_primitive_independent_use_campaign(campaign=campaign, seeding_package=seed, workspace=tmp_path / "work")
    assert first["execution_id"] == second["execution_id"]
    altered = json.loads(seed.read_text(encoding="utf-8")); altered["package_digest"] = "other"; seed.write_text(json.dumps(altered), encoding="utf-8")
    try:
        run_foundational_primitive_independent_use_campaign(campaign=campaign, seeding_package=seed, workspace=tmp_path / "other")
    except ValueError as error:
        assert str(error) == "foundational_primitive_independent_use_seed_digest_mismatch"
    else:
        raise AssertionError("changed seed package must fail closed")

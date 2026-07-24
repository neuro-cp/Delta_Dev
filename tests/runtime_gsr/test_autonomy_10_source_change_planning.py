from __future__ import annotations

from orchestration.runtime.autonomy_source_change_planning import plan_one_source_repair


def test_a10_plans_one_legitimate_bounded_source_repair_without_editing(tmp_path):
    result = plan_one_source_repair(output_root=tmp_path / "a10")
    plan = result["plan"]
    defect = plan["defect"]
    authority = plan["authority_eligibility"]

    assert result["status"] == "AUTONOMY_10_SOURCE_CHANGE_PLAN_PASSED"
    assert "stale admission candidate" in " ".join(defect["evidence"])
    assert defect["first_incorrect_transition"] == "requested A5 review -> output-root existing candidate shortcut -> stale candidate returned"
    assert defect["implementation_file_paths"] == ("orchestration/runtime/autonomy_competence_admission.py",)
    assert defect["test_file_paths"] == ("tests/runtime_gsr/test_autonomy_6_competence_admission.py",)
    assert authority["automatic_a11_authorized"] is True
    assert authority["source_file_count"] == 1
    assert authority["test_file_count"] == 1
    assert authority["primary_worktree_mutation_required"] is False
    assert plan["source_edit_performed"] is False


def test_a10_persists_defect_plan_and_authority_review(tmp_path):
    result = plan_one_source_repair(output_root=tmp_path / "a10")

    assert (tmp_path / "a10" / "defects" / f"{result['plan']['defect']['defect_id']}.json").exists()
    assert (tmp_path / "a10" / "authority_reviews" / f"{result['plan']['authority_eligibility']['authority_review_id']}.json").exists()
    assert (tmp_path / "a10" / "plans" / f"{result['plan']['plan_id']}.json").exists()

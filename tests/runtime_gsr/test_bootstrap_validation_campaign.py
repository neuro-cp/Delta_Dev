from __future__ import annotations

from pathlib import Path

import pytest

from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.bootstrap_validation_campaign import (
    AUDIT_SELECTION,
    COUNTERFACTUAL_STRATEGIES,
    REPRESENTATIVE_SELECTION,
    _competence_record,
    _independent_evaluation,
    _learner_attempt,
    _learner_prompts,
    _prepare_validation_material,
    evaluate_response_strategy,
    run_bootstrap_e_independence_audit,
    run_representative_bootstrap_validation_campaign,
)
from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
)


def _json_count(root: Path, directory: str) -> int:
    path = root / directory
    if not path.exists():
        return 0
    return len(tuple(path.glob("*.json")))


def test_representative_campaign_creates_exact_terminal_records(tmp_path):
    root = tmp_path / "bootstrap-e"
    result = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)

    assert result["selected_module_count"] == 16
    assert tuple(report["label"] for report in result["module_reports"]) == tuple(label for label, _ in REPRESENTATIVE_SELECTION)
    assert result["outcomes"] == {"bootstrap_validation_passed": 16}
    assert result["competence_records_created"] == 16
    assert result["provider_calls"] == 0
    assert result["learner_calls"] == 16
    assert result["evaluator_calls"] == 16
    assert result["trusted_admissions"] == result["capability_promotions"] == 0
    assert _json_count(root, BOOTSTRAP_VALIDATION_DIRECTORY) == 16
    assert _json_count(root, BOOTSTRAP_COMPETENCE_DIRECTORY) == 16
    assert all(len(report["case_outcomes"]) == 5 for report in result["module_reports"])


def test_representative_campaign_replay_and_restart_are_exact(tmp_path):
    root = tmp_path / "bootstrap-e"
    first = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)
    before = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))
    second = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=False)
    after = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")))

    assert before == after
    assert tuple(report["validation_record_digest"] for report in first["module_reports"]) == tuple(report["validation_record_digest"] for report in second["module_reports"])
    assert tuple(report["competence_record_digest"] for report in first["module_reports"]) == tuple(report["competence_record_digest"] for report in second["module_reports"])
    assert second["replay_suppressions"] == 16


def test_post_campaign_retrieval_separates_validated_and_unvalidated_modules(tmp_path):
    root = tmp_path / "bootstrap-e"
    campaign = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)
    request = make_bootstrap_retrieval_request(
        objective="CSV schema validation",
        curriculum_id=campaign["curriculum_id"],
        curriculum_version=1,
        max_results=4,
        max_traversal_depth=8,
        max_packet_modules=24,
        max_total_chars=40000,
    )
    result = retrieve_bootstrap_context(curriculum_root=root, request=request)

    assert result["covered_by_validated_bootstrap_competence"]
    assert result["covered_by_installed_study_material"]
    assert set(result["covered_by_validated_bootstrap_competence"]).isdisjoint(set(result["unresolved_as_demonstrated_competence"]))
    assert set(result["covered_by_installed_study_material"]).issubset(set(result["unresolved_as_demonstrated_competence"]))
    assert result["missing_from_curriculum"] == ()
    assert result["trusted_admissions"] == result["capability_promotions"] == 0


def test_campaign_artifacts_do_not_leak_evaluator_hidden_content_to_packets(tmp_path):
    root = tmp_path / "bootstrap-e"
    result = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)

    for report in result["module_reports"]:
        assert report["packet_id"].startswith("learner-visible-bootstrap-packet-")
        assert report["authority_id"]
        assert report["sealed_package_id"]
        assert report["attempt_id"]
        assert report["evaluation_id"]
        assert report["validation_record_id"]
        assert report["competence_record_id"]
        assert report["provider_calls"] == 0
        assert report["learner_calls"] == 1
        assert report["evaluator_calls"] == 1


def test_independence_audit_negative_controls_discriminate_responses(tmp_path):
    root = tmp_path / "bootstrap-e-audit"
    audit = run_bootstrap_e_independence_audit(audit_root=root, reset=True)

    assert audit["accepted"] is True
    assert tuple(result["label"] for result in audit["module_results"]) == tuple(label for label, _ in AUDIT_SELECTION)
    assert audit["counterfactual_pass_counts"] == {"actual": 8}
    assert audit["provider_calls"] == 0
    for result in audit["module_results"]:
        assert result["actual_outcome"] == "bootstrap_validation_passed"
        assert result["actual_passed_cases"] == 5
        assert result["negative_passed_cases"] == {
            "empty": 0,
            "irrelevant": 0,
            "keyword_stuffing": 0,
            "incorrect": 0,
        }
        assert result["leakage"]["case_id_leakage"] is False
        assert result["leakage"]["evaluator_only_field_leakage"] is False
        assert result["leakage"]["expected_answer_overlap_count"] == 0
        assert result["leakage"]["transfer_case_novel"] is True


def test_anti_coupling_between_evaluator_attempt_and_outcome(tmp_path):
    root = tmp_path / "bootstrap-e-coupling"
    campaign = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)
    module_title = REPRESENTATIVE_SELECTION[0][1]
    from orchestration.runtime.developmental_bootstrap import load_bootstrap_curriculum_artifacts

    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=campaign["curriculum_id"])
    module = next(item for item in loaded["modules"] if item["title"] == module_title)
    packet, _authority, evaluator, prompts = _prepare_validation_material(root, {"curriculum_id": campaign["curriculum_id"], "version": 1}, module)
    actual = _learner_attempt(module, packet, evaluator["artifact_digest"], prompts)
    actual_eval = _independent_evaluation(module, evaluator, actual)
    changed_output = _learner_attempt(module, packet, evaluator["artifact_digest"], prompts, strategy="incorrect")
    changed_output_eval = _independent_evaluation(module, evaluator, changed_output)
    changed_evaluator = {
        **evaluator,
        "cases": tuple({**case, "hidden_required_claims": (*case["hidden_required_claims"], "requires absent hidden relation")} for case in evaluator["cases"]),
    }
    changed_evaluator["artifact_digest"] = "changed-evaluator-digest"
    changed_eval = _independent_evaluation(module, changed_evaluator, actual)

    assert actual_eval["aggregate_disposition"] == "bootstrap_validation_passed"
    assert changed_output["artifact_digest"] != actual["artifact_digest"]
    assert changed_output_eval["aggregate_disposition"] == "bootstrap_validation_failed"
    assert changed_evaluator["artifact_digest"] != evaluator["artifact_digest"]
    assert changed_eval["aggregate_disposition"] == "bootstrap_validation_failed"
    assert evaluator["artifact_digest"] == _prepare_validation_material(root, {"curriculum_id": campaign["curriculum_id"], "version": 1}, module)[2]["artifact_digest"]


def test_failed_or_incomplete_outcomes_cannot_create_competence(tmp_path):
    root = tmp_path / "bootstrap-e-no-competence"
    campaign = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=True)
    from orchestration.runtime.developmental_bootstrap import load_bootstrap_curriculum_artifacts, make_bootstrap_validation_record

    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=campaign["curriculum_id"])
    module = next(item for item in loaded["modules"] if item["title"] == REPRESENTATIVE_SELECTION[0][1])
    for outcome in ("bootstrap_validation_incomplete", "bootstrap_validation_failed", "bootstrap_validation_blocked", "bootstrap_validation_integrity_stop"):
        validation = make_bootstrap_validation_record(
            module_id=module["module_id"],
            module_digest=module["artifact_digest"],
            outcome=outcome,
            evaluator_package_digest=f"eval-{outcome}",
            evaluation_digest=f"evaluation-{outcome}",
        )
        with pytest.raises(Exception, match="requires_passed_validation"):
            _competence_record(module, validation)


def test_counterfactual_strategies_do_not_create_records(tmp_path):
    root = tmp_path / "bootstrap-e-counterfactual"
    audit = run_bootstrap_e_independence_audit(audit_root=root, reset=True)

    assert set(COUNTERFACTUAL_STRATEGIES) == {"empty", "irrelevant", "keyword_stuffing", "incorrect", "actual"}
    assert _json_count(root, BOOTSTRAP_VALIDATION_DIRECTORY) == 0
    assert _json_count(root, BOOTSTRAP_COMPETENCE_DIRECTORY) == 0
    assert audit["trusted_admissions"] == audit["capability_promotions"] == 0

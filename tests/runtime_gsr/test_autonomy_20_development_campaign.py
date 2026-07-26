from __future__ import annotations

from orchestration.runtime.autonomy_development_campaign import run_development_campaign


def test_a20_runs_three_honest_cycles_across_multiple_families(tmp_path):
    result = run_development_campaign(tmp_path / "campaign")
    restart = run_development_campaign(tmp_path / "campaign")
    summary = result["campaign_summary"]
    assert result["status"] == "AUTONOMY_20_MULTI_CYCLE_DEVELOPMENT_CAMPAIGN_PASSED"
    assert summary["cycle_count"] == 3
    assert len(set(summary["families"])) >= 2
    assert summary["one_active_goal_maximum"] is True
    assert summary["resolved_goals_suppressed"] is True
    assert summary["governance_kernel_contract"]["architecture_rule"] == "models_propose_and_interpret_code_constrains_executes_records_and_verifies"
    assert summary["architecture_checkpoint"]["future_phases_should_prefer_specs_over_bespoke_modules"] is True
    assert restart["duplicate_suppressed"] is True


def test_a20_evaluators_precede_execution_and_do_not_drift(tmp_path):
    cycles = run_development_campaign(tmp_path / "campaign")["cycles"]
    for cycle in cycles:
        assert cycle["evaluator"]["created_before_strategy"] is True
        assert cycle["capability_family_spec"]["schema"] == "autonomy_capability_family_spec_v1"
        assert cycle["capability_family_spec"]["strategy_interface"] in {"typed_strategy_proposal", "typed_cognitive_proposal"}
        assert cycle["evaluation"]["evaluator_digest"] == cycle["evaluator"]["artifact_digest"]
        assert cycle["evaluation"]["evaluator_drift"] is False
        assert cycle["revision"]["revision_count"] <= 1


def test_a20_campaign_rejects_filler_broad_claim_and_duplicate_execution(tmp_path):
    summary = run_development_campaign(tmp_path / "campaign")["campaign_summary"]
    assert summary["filler_goals"] is False
    assert summary["broad_competence_claims"] is False
    assert summary["duplicate_semantic_execution"] is False
    assert summary["next_candidate_executed"] is False


def test_a20_preserves_authority_limits_and_unresolved_limitations(tmp_path):
    cycles = run_development_campaign(tmp_path / "campaign")["cycles"]
    assert any(cycle["outcome_review"]["provisional_outcome_allowed"] for cycle in cycles)
    assert any(cycle["feedback"]["limitations_remaining"] for cycle in cycles)
    for cycle in cycles:
        assert cycle["authority"]["provider_calls"] == 0
        assert cycle["authority"]["network"] is False
        assert cycle["authority"]["source_mutation"] is False
        assert cycle["cost"]["provider_calls"] == 0

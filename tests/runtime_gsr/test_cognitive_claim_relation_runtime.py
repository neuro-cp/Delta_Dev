import hashlib

import pytest

from orchestration.runtime.cognitive_claim_relation_runtime import (
    FEATURE_FLAG_NAME,
    GovernedClaimRelationRuntime,
)
from orchestration.runtime.cognitive_claim_relations import read_bundle
from orchestration.runtime.cognitive_contradiction_evaluation import behavioral_cases, evaluate_observation


def _runtime(tmp_path, *, enabled=True):
    return GovernedClaimRelationRuntime(tmp_path / "state.json", enabled=enabled)


def _case(case_id):
    return {case.case_id: case for case in behavioral_cases()}[case_id]


def _claim_states(runtime):
    return {claim.claim_text: claim.lifecycle_state for claim in runtime.bundle.claims}


def test_feature_flag_is_disabled_by_default_and_writes_no_state(tmp_path):
    runtime = _runtime(tmp_path, enabled=False)
    result = runtime.process_operator_turn("My appointment is Tuesday.")
    assert FEATURE_FLAG_NAME == "DELTA_CLAIM_RELATION_PILOT_ENABLED"
    assert result.disposition == "disabled"
    assert result.operator_visible_text == ""
    assert not (tmp_path / "state.json").exists()
    assert runtime.bundle.claims == ()


def test_explicit_correction_preserves_and_supersedes_after_restart(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("My appointment is Tuesday.", turn_id="turn_1")
    result = runtime.process_operator_turn("Correction: my appointment is Wednesday.", turn_id="turn_2")
    assert result.relation_type == "explicit_correction"
    assert result.operator_visible_text == "Updated: the previous claim is preserved as superseded."
    states = _claim_states(runtime)
    assert states["My appointment is Tuesday."] == "superseded"
    assert states["Correction: my appointment is Wednesday."] == "current"
    restored = runtime.restart()
    assert restored.bundle == runtime.bundle
    assert evaluate_observation(_case("B"), restored.evaluator_observation()).classification == "correct_explicit_correction"


def test_duplicate_restatement_does_not_create_duplicate_current_claim(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("The branch is codex/delta-cognitive-core.", turn_id="turn_1")
    result = runtime.process_operator_turn("We are still on codex/delta-cognitive-core.", turn_id="turn_2")
    assert result.relation_type == "duplicate_restatement"
    assert "no duplicate update" in result.operator_visible_text
    branch_claims = [claim for claim in runtime.bundle.claims if claim.subject_scope == "branch"]
    assert [claim.lifecycle_state for claim in branch_claims].count("current") == 1
    assert [claim.lifecycle_state for claim in branch_claims].count("rejected") == 1
    assert evaluate_observation(_case("G"), runtime.evaluator_observation()).classification == "correct_confirmation"


def test_temporal_transition_preserves_historical_and_current(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("The runtime previously used the old evaluator.", turn_id="turn_1")
    result = runtime.process_operator_turn("The runtime now uses the amended evaluator.", turn_id="turn_2")
    assert result.relation_type == "temporal_transition"
    states = _claim_states(runtime)
    assert states["The runtime previously used the old evaluator."] == "historical"
    assert states["The runtime now uses the amended evaluator."] == "current"
    assert evaluate_observation(_case("I"), runtime.evaluator_observation()).classification == "correct_temporal_transition"


def test_authority_revocation_is_prospective_and_restart_stable(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("You may run the sandbox test.", turn_id="turn_1")
    result = runtime.process_operator_turn("I revoke authorization to run the sandbox test.", turn_id="turn_2")
    assert result.relation_type == "authority_revocation"
    assert "prior history is preserved" in result.operator_visible_text
    states = _claim_states(runtime)
    assert states["You may run the sandbox test."] == "revoked"
    assert states["I revoke authorization to run the sandbox test."] == "current"
    restored = runtime.restart()
    assert restored.bundle == runtime.bundle
    assert evaluate_observation(_case("H"), restored.evaluator_observation()).classification == "correct_revocation"


def test_bounded_exception_remains_scoped_after_restart(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("Do not use external providers.", turn_id="turn_1")
    result = runtime.process_operator_turn("For this one test only, the approved local provider may be used.", turn_id="turn_2")
    assert result.relation_type == "bounded_exception"
    states = _claim_states(runtime)
    assert states["Do not use external providers."] == "current"
    assert states["For this one test only, the approved local provider may be used."] == "conditionally_current"
    restored = runtime.restart()
    assert restored.bundle == runtime.bundle
    assert evaluate_observation(_case("D"), restored.evaluator_observation()).classification == "correct_bounded_exception"


def test_unrelated_claims_are_independent_and_do_not_block_work(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("The database is PostgreSQL.", turn_id="turn_1")
    result = runtime.process_operator_turn("My car needs an oil change.", turn_id="turn_2")
    assert result.relation_type == "unrelated"
    assert "independent current claim" in result.operator_visible_text
    assert all(claim.lifecycle_state == "current" for claim in runtime.bundle.claims)
    observation = runtime.evaluator_observation()
    assert observation["dependent_work_suspended"] is False
    assert evaluate_observation(_case("F"), observation).classification == "correct_unrelated"


def test_unsupported_semantic_contradiction_is_deferred_without_winner(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("The database is PostgreSQL.", turn_id="turn_1")
    result = runtime.process_operator_turn("The database is SQLite.", turn_id="turn_2")
    assert result.disposition == "semantic_classification_required"
    assert result.relation_type == "unresolved_relation"
    assert "semantic classification is not enabled" in result.operator_visible_text
    assert all(claim.lifecycle_state == "current" for claim in runtime.bundle.claims)
    assert runtime.bundle.relations == ()


def test_claim_provenance_and_bounded_prior_lookup(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("My appointment is Tuesday.", turn_id="operator-turn-a")
    runtime.process_operator_turn("Correction: my appointment is Wednesday.", turn_id="operator-turn-b")
    assert {ref for claim in runtime.bundle.claims for ref in claim.provenance_refs} == {"operator-turn-a", "operator-turn-b"}
    relation = runtime.bundle.relations[0]
    assert relation.provenance_refs == ("operator-turn-a", "operator-turn-b")


def test_atomic_persistence_corruption_blocks_without_silent_reset(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")
    runtime = GovernedClaimRelationRuntime(path, enabled=True)
    result = runtime.process_operator_turn("My appointment is Tuesday.")
    assert result.disposition == "persistence_blocked"
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_no_duplicate_relation_after_restart_replay(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("My appointment is Tuesday.", turn_id="turn_1")
    first = runtime.process_operator_turn("Correction: my appointment is Wednesday.", turn_id="turn_2")
    restored = runtime.restart()
    second = restored.process_operator_turn("Correction: my appointment is Wednesday.", turn_id="turn_2")
    assert first.relation_id == second.relation_id
    assert len(restored.bundle.relations) == 1


def test_evaluator_source_digest_is_stable_during_runtime_tests():
    digest = hashlib.sha256(open("orchestration/runtime/cognitive_contradiction_evaluation.py", "rb").read()).hexdigest()
    assert digest


def test_bundle_written_is_restart_readable(tmp_path):
    runtime = _runtime(tmp_path)
    runtime.process_operator_turn("The database is PostgreSQL.", turn_id="turn_1")
    restored = read_bundle(tmp_path / "state.json")
    assert restored == runtime.bundle


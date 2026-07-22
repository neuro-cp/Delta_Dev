from __future__ import annotations

import copy
import json

from orchestration.runtime.foundational_primitive_admission import (admit_reviewed_foundational_primitives, compile_foundational_primitive_admission_authority, resolve_admission_candidates, review_foundational_primitive_candidate, retrieve_trusted_formal_primitive, run_trusted_foundational_fresh_reuse)


def _packages(tmp_path):
    node = {"primitive_id": "constraint-id", "canonical_label": "constraint", "status": "source_grounded", "definition": "A constraint limits allowed actions.", "retained_support": [{"concept_id": "source"}], "conflicts": [], "examples": [{"x": 1}], "counterexamples": [{"x": 2}], "status_history": [{"status": "candidate_constructed"}, {"status": "structurally_valid"}, {"status": "partially_formalized"}, {"status": "source_grounded"}], "typed_entities": [], "relations": [], "prerequisites": []}
    seed = {"execution_id": "seed", "package_digest": "seed-digest", "nodes": [node, {**node, "primitive_id": "untrusted", "canonical_label": "other", "status": "partially_formalized"}]}
    use = {"seeding_package_digest": "seed-digest", "package_digest": "use-digest", "attempts": [{"learner_attempt": {"used_primitives": ["constraint"]}, "evaluation": {"passed": True}}], "promotion_candidate_package": [{"primitive_id": "constraint-id", "promotion_candidate_status": "semantically_ready_candidate", "used_in_passed_unseen_exercise": True}]}
    seed_path = tmp_path / "seed.json"; use_path = tmp_path / "use.json"; seed_path.write_text(json.dumps(seed)); use_path.write_text(json.dumps(use)); return seed_path, use_path


def test_review_and_authority_are_exact_and_pending(tmp_path):
    seed, use = _packages(tmp_path)
    candidates = resolve_admission_candidates(seeding_package=seed, independent_use_package=use)
    reviews = tuple(review_foundational_primitive_candidate(item) for item in candidates)
    authority = compile_foundational_primitive_admission_authority(candidates=candidates, reviews=reviews)
    assert reviews[0]["outcome"] == "admission_ready_with_scope_limit"
    assert authority["status"] == "pending"
    assert authority["allowed_admissions"][0]["primitive_id"] == "constraint-id"


def test_admission_is_exact_once_and_retrieval_is_exact(tmp_path):
    seed, use = _packages(tmp_path); candidates = resolve_admission_candidates(seeding_package=seed, independent_use_package=use); reviews = tuple(review_foundational_primitive_candidate(item) for item in candidates); authority = compile_foundational_primitive_admission_authority(candidates=candidates, reviews=reviews); layer = tmp_path / "trusted.sqlite"
    result = admit_reviewed_foundational_primitives(authority=authority, response="approve_foundational_primitive_admission", candidates=candidates, reviews=reviews, trusted_layer=layer)
    assert result["capability_promotion"] is False
    assert retrieve_trusted_formal_primitive(trusted_layer=layer, primitive_id="constraint-id")["canonical_label"] == "constraint"
    assert retrieve_trusted_formal_primitive(trusted_layer=layer, primitive_id="untrusted") is None
    try:
        admit_reviewed_foundational_primitives(authority=authority, response="approve_foundational_primitive_admission", candidates=candidates, reviews=reviews, trusted_layer=layer)
    except ValueError as error:
        assert str(error) == "foundational_admission_authority_replayed"
    else:
        raise AssertionError("authority replay must fail")


def test_fresh_reuse_uses_exact_trusted_records_and_keeps_evaluator_hidden(tmp_path):
    seed, use = _packages(tmp_path); candidates = resolve_admission_candidates(seeding_package=seed, independent_use_package=use); reviews = tuple(review_foundational_primitive_candidate(item) for item in candidates); authority = compile_foundational_primitive_admission_authority(candidates=candidates, reviews=reviews); layer = tmp_path / "trusted.sqlite"
    admit_reviewed_foundational_primitives(authority=authority, response="approve_foundational_primitive_admission", candidates=candidates, reviews=reviews, trusted_layer=layer)
    # Add an exact second reviewed candidate solely to exercise the domain-neutral retrieval path.
    # The production gate supplies both reviewed records from its immutable package.
    with __import__("sqlite3").connect(layer) as conn:
        source = conn.execute("SELECT * FROM trusted_formal_primitives WHERE primitive_id='constraint-id'").fetchone()
        conn.execute("INSERT INTO trusted_formal_primitives VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("interest-id", "interest", *source[2:]))
    result = run_trusted_foundational_fresh_reuse(trusted_layer=layer, primitive_ids=("constraint-id", "interest-id"))
    assert result["summary"]["passed"] == 2
    assert all("evaluator" not in item["learner_view"] for item in result["attempts"])
    assert result["capability_promotion"] is False


def test_digest_drift_blocks_admission(tmp_path):
    seed, use = _packages(tmp_path); candidates = resolve_admission_candidates(seeding_package=seed, independent_use_package=use); reviews = tuple(review_foundational_primitive_candidate(item) for item in candidates); authority = compile_foundational_primitive_admission_authority(candidates=candidates, reviews=reviews); drifted = copy.deepcopy(candidates); drifted[0]["candidate_digest"] = "drift"
    try:
        admit_reviewed_foundational_primitives(authority=authority, response="approve_foundational_primitive_admission", candidates=tuple(drifted), reviews=reviews, trusted_layer=tmp_path / "trusted.sqlite")
    except ValueError as error:
        assert str(error) == "foundational_admission_candidate_or_review_digest_drift"
    else:
        raise AssertionError("digest drift must fail")

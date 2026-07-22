from __future__ import annotations

import sqlite3

from orchestration.runtime.foundational_primitive_seeding import STATUS_LADDER, compile_foundational_primitive_seeding_campaign, run_foundational_primitive_seeding_campaign


def _store(path):
    conn = sqlite3.connect(path)
    conn.executescript("CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_name TEXT, normalized_name TEXT, domain TEXT, concept_type TEXT, short_definition TEXT, confidence REAL, quality_score REAL, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, source_type TEXT);")
    conn.executemany("INSERT INTO concepts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("interest", "Interest Rates (Finance)", "interest rates", "finance", "concept", "Interest rates are the cost of borrowing or the return paid for saving over time.", .9, .9, "approved", 0, "r1", "now", "retained"),
        ("facet", "Interest Rates Optimization (Finance)", "interest rates optimization", "finance", "concept", "Interest Rates Optimization connects interest rates to operator-reviewable uncertainty.", .8, .8, "approved", 0, "r2", "now", "generated"),
    ]); conn.commit(); conn.close()


def test_seed_campaign_uses_status_ladder_and_preserves_store(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db); before = db.read_bytes()
    campaign = compile_foundational_primitive_seeding_campaign(parent_campaign_id="parent")
    result = run_foundational_primitive_seeding_campaign(campaign=campaign, workspace=tmp_path / "work", db_path=db)
    assert db.read_bytes() == before
    assert result["source_store"]["immutable"] is True
    assert len(result["nodes"]) == 25
    assert all(tuple(item["status"] for item in node["status_history"]) == STATUS_LADDER[:len(node["status_history"])] for node in result["nodes"])
    interest = next(node for node in result["nodes"] if node["canonical_label"] == "interest")
    assert interest["status"] == "source_grounded"
    state_transition = next(node for node in result["nodes"] if node["canonical_label"] == "state_transition")
    assert state_transition["status"] == "partially_formalized"
    assert not result["admission_package"]["semantically_ready"]
    assert sum(item["passed"] for item in result["transfer_tests"]) >= 10


def test_seed_campaign_reuses_same_package_after_restart(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db)
    campaign = compile_foundational_primitive_seeding_campaign(parent_campaign_id="parent")
    first = run_foundational_primitive_seeding_campaign(campaign=campaign, workspace=tmp_path / "work", db_path=db)
    second = run_foundational_primitive_seeding_campaign(campaign=campaign, workspace=tmp_path / "work", db_path=db)
    assert first["execution_id"] == second["execution_id"]
    assert first["package_digest"] == second["package_digest"]


def test_seed_campaign_fails_closed_without_envelope(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db)
    campaign = compile_foundational_primitive_seeding_campaign(parent_campaign_id="parent")
    campaign["authority"]["authority_granted"] = False
    try:
        run_foundational_primitive_seeding_campaign(campaign=campaign, workspace=tmp_path / "work", db_path=db)
    except ValueError as error:
        assert str(error) == "foundational_primitive_seeding_authority_not_granted"
    else:
        raise AssertionError("missing authority should fail closed")

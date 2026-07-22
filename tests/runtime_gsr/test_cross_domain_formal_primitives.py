from __future__ import annotations

import sqlite3

from orchestration.runtime.cross_domain_formal_primitives import compile_cross_domain_campaign, run_cross_domain_formal_primitive_marathon


def _store(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_name TEXT, normalized_name TEXT, domain TEXT, concept_type TEXT, short_definition TEXT, confidence REAL, quality_score REAL, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, source_type TEXT);
    """)
    rows = [
        ("math", "Matrix (Mathematics)", "matrix mathematics", "mathematics", "concept", "A matrix is a rectangular arrangement of values used to represent a linear transformation.", .8, .9, "approved", 0, "r1", "now", "retained"),
        ("physics", "Gravity (Basic Physics)", "gravity physics", "basic_physics", "concept", "Gravity is the attractive interaction associated with mass and energy.", .8, .9, "approved", 0, "r2", "now", "retained"),
        ("software", "Api Boundaries (Software Architecture)", "api boundaries", "software_architecture", "concept", "API boundaries define allowed interactions between software components.", .8, .9, "approved", 0, "r3", "now", "retained"),
        ("psych", "Memory Consolidation (Psychology)", "memory consolidation", "psychology", "concept", "Memory consolidation is the process by which acquired information becomes more stable over time.", .8, .9, "approved", 0, "r4", "now", "retained"),
        ("facet", "Vectors Operational Use (Mathematics)", "vectors operational use", "mathematics", "concept", "Vectors Operational Use connects vectors to evidence, constraints, and operator-reviewable uncertainty.", .8, .9, "approved", 0, "r5", "now", "generated"),
    ]
    conn.executemany("INSERT INTO concepts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows); conn.commit(); conn.close()


def test_campaign_creates_workspace_nodes_and_rejects_facets(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db); before = db.read_bytes()
    campaign = compile_cross_domain_campaign(audit_id="audit", audit_digest="digest")
    result = run_cross_domain_formal_primitive_marathon(campaign=campaign, workspace=tmp_path / "work", db_path=db, maximum_nodes_per_domain=3)
    assert db.read_bytes() == before
    assert result["source_store"]["immutable"] is True
    assert result["provider_calls"] == result["external_retrievals"] == 0
    assert result["trusted_memory_admissions"] == result["capability_promotions"] == 0
    assert any(node["source_concept_ids"] == ("math",) for node in result["nodes"])
    assert any(item["concept_id"] == "facet" for item in result["rejected_associative_facets"])
    assert all(node["validation_status"] == "partially_formalized" for node in result["nodes"])


def test_campaign_is_restart_and_duplicate_safe(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db)
    campaign = compile_cross_domain_campaign(audit_id="audit", audit_digest="digest")
    first = run_cross_domain_formal_primitive_marathon(campaign=campaign, workspace=tmp_path / "work", db_path=db, maximum_nodes_per_domain=3)
    second = run_cross_domain_formal_primitive_marathon(campaign=campaign, workspace=tmp_path / "work", db_path=db, maximum_nodes_per_domain=3)
    assert first["execution_id"] == second["execution_id"]
    assert first["package_digest"] == second["package_digest"]
    assert len(first["nodes"]) == len({node["primitive_id"] for node in first["nodes"]})


def test_campaign_requires_consumed_granted_authority(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db)
    campaign = compile_cross_domain_campaign(audit_id="audit", audit_digest="digest")
    campaign["authority"]["status"] = "pending"
    try:
        run_cross_domain_formal_primitive_marathon(campaign=campaign, workspace=tmp_path / "work", db_path=db)
    except ValueError as error:
        assert str(error) == "cross_domain_formal_primitive_campaign_authority_not_granted"
    else:
        raise AssertionError("campaign should fail closed")


def test_sparse_domain_does_not_receive_unrelated_fillers(tmp_path):
    db = tmp_path / "concepts.sqlite"; _store(db)
    campaign = compile_cross_domain_campaign(audit_id="audit", audit_digest="digest")
    result = run_cross_domain_formal_primitive_marathon(campaign=campaign, workspace=tmp_path / "work", db_path=db, maximum_nodes_per_domain=3)
    cognitive = [node for node in result["nodes"] if node["domain"] == "cognition_language_learning"]
    assert all("memory" in node["canonical_label"].lower() or "evidence" in node["canonical_label"].lower() or "learning" in node["canonical_label"].lower() or "concept" in node["canonical_label"].lower() or "context" in node["canonical_label"].lower() or "capability" in node["canonical_label"].lower() or "evaluation" in node["canonical_label"].lower() or "confidence" in node["canonical_label"].lower() for node in cognitive)

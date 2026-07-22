from __future__ import annotations

import sqlite3

from orchestration.runtime.concept_memory_formalization_audit import build_concept_memory_formalization_audit, compile_formalization_campaign, consume_formalization_campaign_authority, execute_formalization_campaign


def test_audit_is_read_only_and_campaign_stays_pending(tmp_path):
    path = tmp_path / "concepts.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_name TEXT, normalized_name TEXT, domain TEXT, concept_type TEXT, short_definition TEXT, confidence REAL, quality_score REAL, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, source_type TEXT, source_model_id TEXT, source_question TEXT, raw_json TEXT);
    CREATE TABLE concept_keywords(concept_id TEXT, keyword TEXT); CREATE TABLE concept_related(concept_id TEXT, related TEXT); CREATE TABLE concept_propositions(concept_id TEXT, proposition TEXT); CREATE TABLE graph_edges(edge_id TEXT PRIMARY KEY, source_concept_id TEXT, target_concept_id TEXT, relation_type TEXT, confidence REAL, uncertainty TEXT, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE graph_adjacency(concept_id TEXT, edge_id TEXT, neighbor_concept_id TEXT, direction TEXT, relation_type TEXT, confidence REAL); CREATE TABLE substrate_replay_events(replay_event_id TEXT PRIMARY KEY, target_type TEXT, target_id TEXT, event_type TEXT, status TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE migration_audit(audit_id TEXT PRIMARY KEY, created_at TEXT, event_type TEXT, concept_rows INTEGER, edge_rows INTEGER, details_json TEXT); CREATE TABLE store_metadata(key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.execute("INSERT INTO concepts VALUES ('c1','Vector','vector','mathematics','concept','',.5,.5,'approved_noncanonical',1,'r','now','test','','','{}')")
    conn.commit(); conn.close()
    before = path.read_bytes()
    audit = build_concept_memory_formalization_audit(path)
    campaign = compile_formalization_campaign(audit)
    assert path.read_bytes() == before
    assert audit["authoritative_store"]["active_concept_count"] == 1
    assert campaign["authority_request"]["status"] == "pending"


def test_campaign_creates_only_reversible_workspace_overlays(tmp_path):
    path = tmp_path / "concepts.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_name TEXT, normalized_name TEXT, domain TEXT, concept_type TEXT, short_definition TEXT, confidence REAL, quality_score REAL, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, source_type TEXT, source_model_id TEXT, source_question TEXT, raw_json TEXT);
    CREATE TABLE concept_keywords(concept_id TEXT, keyword TEXT); CREATE TABLE concept_related(concept_id TEXT, related TEXT); CREATE TABLE concept_propositions(concept_id TEXT, proposition TEXT); CREATE TABLE graph_edges(edge_id TEXT PRIMARY KEY, source_concept_id TEXT, target_concept_id TEXT, relation_type TEXT, confidence REAL, uncertainty TEXT, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE graph_adjacency(concept_id TEXT, edge_id TEXT, neighbor_concept_id TEXT, direction TEXT, relation_type TEXT, confidence REAL); CREATE TABLE substrate_replay_events(replay_event_id TEXT PRIMARY KEY, target_type TEXT, target_id TEXT, event_type TEXT, status TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE migration_audit(audit_id TEXT PRIMARY KEY, created_at TEXT, event_type TEXT, concept_rows INTEGER, edge_rows INTEGER, details_json TEXT); CREATE TABLE store_metadata(key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.execute("INSERT INTO concepts VALUES ('v','Vectors','vectors','mathematics','concept','describes how vectors work, connecting vectors to uncertainty',.5,.5,'approved_noncanonical',1,'r','now','test','','','{}')")
    conn.commit(); conn.close()
    audit = build_concept_memory_formalization_audit(path); campaign = compile_formalization_campaign(audit)
    result = execute_formalization_campaign(audit=audit, campaign=campaign, workspace=tmp_path / "work", db_path=path)
    assert result["source_store_read_only"] is True
    assert result["trusted_memory_admission"] is False
    assert (tmp_path / "work" / "FORMALIZATION_CAMPAIGN_WORKING_RESULT.json").exists()


def test_campaign_authority_is_consumed_in_a_resolved_copy(tmp_path):
    path = tmp_path / "concepts.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE concepts(concept_id TEXT PRIMARY KEY, concept_name TEXT, normalized_name TEXT, domain TEXT, concept_type TEXT, short_definition TEXT, confidence REAL, quality_score REAL, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, source_type TEXT, source_model_id TEXT, source_question TEXT, raw_json TEXT);
    CREATE TABLE concept_keywords(concept_id TEXT, keyword TEXT); CREATE TABLE concept_related(concept_id TEXT, related TEXT); CREATE TABLE concept_propositions(concept_id TEXT, proposition TEXT); CREATE TABLE graph_edges(edge_id TEXT PRIMARY KEY, source_concept_id TEXT, target_concept_id TEXT, relation_type TEXT, confidence REAL, uncertainty TEXT, approval_status TEXT, noncanonical INTEGER, rollback_handle TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE graph_adjacency(concept_id TEXT, edge_id TEXT, neighbor_concept_id TEXT, direction TEXT, relation_type TEXT, confidence REAL); CREATE TABLE substrate_replay_events(replay_event_id TEXT PRIMARY KEY, target_type TEXT, target_id TEXT, event_type TEXT, status TEXT, created_at TEXT, raw_json TEXT); CREATE TABLE migration_audit(audit_id TEXT PRIMARY KEY, created_at TEXT, event_type TEXT, concept_rows INTEGER, edge_rows INTEGER, details_json TEXT); CREATE TABLE store_metadata(key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit(); conn.close()
    campaign = compile_formalization_campaign(build_concept_memory_formalization_audit(path))
    resolved = consume_formalization_campaign_authority(campaign, "approve_concept_memory_formalization_campaign")
    assert campaign["authority_request"]["status"] == "pending"
    assert resolved["authority_request"]["status"] == "consumed"
    assert resolved["authority_request"]["authority_granted"] is True
    assert resolved["compiled_campaign_digest"] == campaign["campaign_digest"]

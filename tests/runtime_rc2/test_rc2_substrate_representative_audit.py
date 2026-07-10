from __future__ import annotations

from orchestration.runtime.rc2_storage_adapter import load_diverse_concepts, substrate_counts
from orchestration.runtime.rc2_sqlite_substrate import expand_sqlite_substrate
from orchestration.runtime.rc2_substrate_representative_audit import build_audit, semantic_stem


def test_semantic_stem_removes_pattern_variants() -> None:
    assert (
        semantic_stem("Agriculture Gardening Energy Transfer Diagnostic Signals Pattern 7")
        == semantic_stem("Agriculture Gardening Energy Transfer Diagnostic Signals Pattern 2")
    )


def test_representative_audit_is_read_only_and_reports_core_metrics() -> None:
    report = build_audit(write_reports=False)
    assert report["total_concepts"] >= 1
    assert "unique_semantic_concept_estimate" in report
    assert "usable_concept_estimate" in report
    assert "sample_quality" in report
    assert "graph_audit" in report
    assert report["safety"]["training_performed"] is False
    assert report["safety"]["stores_deleted_or_reset"] is False
    assert report["safety"]["quarantine_performed"] is False


def test_diverse_concept_loader_avoids_single_domain_browse_slice() -> None:
    counts = substrate_counts()
    concepts = load_diverse_concepts(limit=100)
    assert concepts
    if counts.get("backend") != "jsonl_fallback" and counts.get("concepts", 0) >= 1000:
        domains = {str(concept.get("domain") or "") for concept in concepts}
        assert len(domains) >= 5


def test_sqlite_expansion_generator_does_not_emit_pattern_clones(tmp_path) -> None:
    db_path = tmp_path / "substrate.sqlite"
    result = expand_sqlite_substrate(target_concepts=40, target_edges=0, db_path=db_path)
    assert result["after"]["concepts"] == 40
    assert result["rejected_semantic_stems"] == 0

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        names = [row[0] for row in conn.execute("SELECT concept_name FROM concepts")]
    finally:
        conn.close()
    assert names
    assert all(" Pattern " not in name for name in names)
    assert len({semantic_stem(name) for name in names}) == len(names)

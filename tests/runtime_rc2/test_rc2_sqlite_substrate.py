from __future__ import annotations

from pathlib import Path

from orchestration.runtime import rc2_sqlite_substrate as sqlite_substrate


def test_sqlite_rebuild_preserves_current_jsonl_counts(tmp_path) -> None:
    result = sqlite_substrate.rebuild_sqlite_from_jsonl(tmp_path / "substrate.sqlite")

    assert result["row_counts_match_jsonl"] is True
    assert result["sqlite_counts"]["concepts"] >= 1000
    assert result["sqlite_counts"]["graph_edges"] >= 15
    assert result["safety"]["training_performed"] is False
    assert result["safety"]["canonical_write_performed"] is False
    assert Path(result["db_path"]).exists()


def test_sqlite_searches_concepts_in_an_isolated_rebuild(tmp_path) -> None:
    path = tmp_path / "substrate.sqlite"
    sqlite_substrate.rebuild_sqlite_from_jsonl(path)
    result = sqlite_substrate.search_concepts_sqlite("How does photosynthesis relate to respiration?", limit=5, db_path=path)

    assert result["backend"] == "sqlite"
    assert result["matched"] is True
    assert len(result["matches"]) >= 2
    assert all(item.get("concept_id") for item in result["matches"])


def test_sqlite_graph_neighborhood_is_read_only(tmp_path) -> None:
    path = tmp_path / "substrate.sqlite"
    sqlite_substrate.rebuild_sqlite_from_jsonl(path)
    result = sqlite_substrate.search_concepts_sqlite("photosynthesis", limit=1, db_path=path)
    concept_id = result["matches"][0]["concept_id"]

    neighborhood = sqlite_substrate.traverse_graph_sqlite(concept_id, depth=1, db_path=path)

    assert neighborhood["read_only"] is True
    assert neighborhood["start_concept_id"] == concept_id
    assert "paths" in neighborhood


def test_sqlite_replay_coverage_can_be_synced_without_training(tmp_path) -> None:
    path = tmp_path / "substrate.sqlite"
    sqlite_substrate.rebuild_sqlite_from_jsonl(path)
    result = sqlite_substrate.ensure_sqlite_replay_coverage(db_path=path)
    coverage = sqlite_substrate.replay_coverage(db_path=path)

    assert result["after"]["concept_replay_coverage"] == 1.0
    assert result["after"]["edge_replay_coverage"] == 1.0
    assert coverage["total_replay_events"] >= coverage["concept_rows"]
    assert sqlite_substrate.SAFETY["training_performed"] is False
    assert sqlite_substrate.SAFETY["canonical_write_performed"] is False

from __future__ import annotations

from pathlib import Path

from orchestration.runtime import rc2_sqlite_substrate as sqlite_substrate
from orchestration.runtime import rc2_storage_adapter as storage_adapter


def test_sqlite_rebuild_preserves_current_jsonl_counts() -> None:
    result = sqlite_substrate.rebuild_sqlite_from_jsonl()

    assert result["row_counts_match_jsonl"] is True
    assert result["sqlite_counts"]["concepts"] >= 1000
    assert result["sqlite_counts"]["graph_edges"] >= 15
    assert result["safety"]["training_performed"] is False
    assert result["safety"]["canonical_write_performed"] is False
    assert Path(result["db_path"]).exists()


def test_storage_adapter_prefers_sqlite_and_searches_concepts() -> None:
    sqlite_substrate.rebuild_sqlite_from_jsonl()

    health = storage_adapter.backend_health()
    result = storage_adapter.search_concepts("How does photosynthesis relate to respiration?", limit=5)

    assert health["sqlite_available"] is True
    assert result["backend"] == "sqlite"
    assert result["matched"] is True
    assert len(result["matches"]) >= 2
    assert all(item.get("concept_id") for item in result["matches"])


def test_storage_adapter_graph_neighborhood_is_read_only() -> None:
    sqlite_substrate.rebuild_sqlite_from_jsonl()
    result = storage_adapter.search_concepts("photosynthesis", limit=1)
    concept_id = result["matches"][0]["concept_id"]

    neighborhood = storage_adapter.get_graph_neighborhood(concept_id, depth=1)

    assert neighborhood["read_only"] is True
    assert neighborhood["concept"]["concept_id"] == concept_id
    assert "edges" in neighborhood
    assert "traversal" in neighborhood


def test_sqlite_gates_report_no_training_or_provider_paths() -> None:
    sqlite_substrate.rebuild_sqlite_from_jsonl()
    gates = sqlite_substrate.measure_sqlite_gates()

    assert gates["sqlite_counts"]["concepts"] >= gates["jsonl_counts"]["concepts"]
    assert gates["sqlite_counts"]["graph_edges"] >= gates["jsonl_counts"]["graph_edges"]
    assert gates["gates"]["no_safety_regression"] is True
    assert gates["indexed_retrieval_latency_ms"] >= 0
    assert gates["graph_lookup_latency_ms"] >= 0


def test_sqlite_replay_coverage_can_be_synced_without_training() -> None:
    sqlite_substrate.rebuild_sqlite_from_jsonl()
    result = sqlite_substrate.ensure_sqlite_replay_coverage()
    coverage = sqlite_substrate.backend_health()["replay_coverage"]

    assert result["after"]["concept_replay_coverage"] == 1.0
    assert result["after"]["edge_replay_coverage"] == 1.0
    assert coverage["total_replay_events"] >= coverage["concept_rows"]
    assert sqlite_substrate.SAFETY["training_performed"] is False
    assert sqlite_substrate.SAFETY["canonical_write_performed"] is False

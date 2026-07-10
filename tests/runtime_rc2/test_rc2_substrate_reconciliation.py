from orchestration.runtime.rc2_storage_adapter import substrate_counts
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation


def test_reconciliation_defines_single_authoritative_runtime_count() -> None:
    report = build_substrate_reconciliation(write_reports=False)
    display = report["ui_display"]

    assert report["authoritative_runtime_concept_counter"] == "active_runtime_concepts"
    assert report["authoritative_runtime_edge_counter"] == "active_graph_edges"
    assert display["active_runtime_concepts"] >= 0
    assert display["active_graph_edges"] >= 0
    assert display["substrate_replay_events"] >= display["concept_replay_events"]
    assert display["substrate_replay_events"] >= display["graph_edge_replay_events"]


def test_storage_adapter_counts_match_reconciliation_display() -> None:
    report = build_substrate_reconciliation(write_reports=False)
    display = report["ui_display"]
    counts = substrate_counts()

    assert counts["active_runtime_concepts"] == display["active_runtime_concepts"]
    assert counts["concepts"] == display["active_runtime_concepts"]
    assert counts["active_graph_edges"] == display["active_graph_edges"]
    assert counts["graph_edges"] == display["active_graph_edges"]
    assert counts["substrate_replay_events"] == display["substrate_replay_events"]
    assert counts["replay_events"] == display["substrate_replay_events"]
    assert counts["migration_audit_events"] == display["migration_audit_events"]

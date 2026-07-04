from orchestration.runtime.rc1_substrate_query_adapter import query_runtime_substrate, write_query_adapter_report


def test_substrate_query_adapter_returns_e2e_and_document_results():
    packet = query_runtime_substrate("Why did Project Atlas fail and what remains uncertain about Worker C?")
    sources = {result.source for result in packet.results}
    assert "e2e_simulated_consolidated_knowledge" in sources
    assert "rc1_document_audit_slice" in sources


def test_substrate_query_adapter_is_read_only_and_non_mutating():
    packet = query_runtime_substrate("What did the document audit learn about provenance?")
    assert packet.query.read_only is True
    assert packet.mutating is False
    assert packet.results


def test_query_adapter_report_recommends_next_state_machine_work():
    report = write_query_adapter_report()
    assert report["final_recommendation"] == "PROCEED_UNIFIED_PROPOSAL_REVIEW_STATE_MACHINE"
    assert report["estimated_runtime_maturity"] >= 90
    assert report["safety"]["provider_call_performed"] is False

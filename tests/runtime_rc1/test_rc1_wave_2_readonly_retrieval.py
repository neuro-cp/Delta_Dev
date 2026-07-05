from orchestration.runtime.rc1_wave_2_readonly_retrieval import answer_fixture_question, write_wave_2_report


def test_wave_2_retrieves_fixture_records_read_only():
    report = answer_fixture_question("Why did the fixture system fail, what fixed it, and what remains uncertain?")
    assert report["read_only"] is True
    assert report["mutating"] is False
    assert report["evidence_ids"]
    assert "missing provenance" in report["answer"]
    assert report["uncertainty"]
    assert report["safety"]["provider_call_performed"] is False


def test_wave_2_refuses_unsupported_claims():
    report = answer_fixture_question("Did Worker C definitely execute successfully?")
    assert "Worker C definitely executed successfully." in report["unsupported_claims_refused"]
    assert report["safety"]["knowledge_mutation_performed"] is False


def test_wave_2_report_generation():
    report = write_wave_2_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_3_SIMULATED_SUBSTRATE_WRITES"

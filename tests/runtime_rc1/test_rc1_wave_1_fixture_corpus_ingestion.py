from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import ingest_fixture_corpus, write_wave_1_report


def test_wave_1_fixture_documents_produce_noncanonical_records():
    report = ingest_fixture_corpus()
    assert report["fixture_only"] is True
    assert report["record_count"] >= 4
    for record in report["semantic_records"]:
        assert record["noncanonical"] is True
        assert record["canonical_write_performed"] is False
        assert record["source_checksum"]
        assert record["provenance"]


def test_wave_1_can_write_to_explicit_noncanonical_workspace(tmp_path):
    report = ingest_fixture_corpus(output_dir=tmp_path)
    assert (tmp_path / "semantic_records.json").exists()
    assert report["safety"]["knowledge_mutation_performed"] is False
    assert report["rollback_plan"].startswith("Delete")


def test_wave_1_report_generation():
    report = write_wave_1_report()
    assert report["final_recommendation"] == "PROCEED_WAVE_2_READ_ONLY_RETRIEVAL"

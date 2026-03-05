from memory.inspection.exporters.json_exporter import JSONInspectionExporter
from memory.inspection.exporters.csv_exporter import CSVInspectionExporter
from memory.inspection.exporters.text_exporter import TextInspectionExporter
from memory.inspection.inspection_report import InspectionReport


def test_exporters_do_not_mutate_report() -> None:
    report = InspectionReport(
        report_id="test-report-001",
        generated_step=100,
        generated_time=10.0,
        inspected_components=[
            "episodic",
            "semantic",
            "drift",
            "promotion",
        ],
        episode_count=3,
        semantic_record_count=5,
        drift_record_count=1,
        promotion_candidate_count=0,
        summaries={"mean_duration": 12.5},
        warnings=["example-warning"],
    )

    before = report

    JSONInspectionExporter().export(report)
    CSVInspectionExporter().export(report)
    TextInspectionExporter().export(report)

    after = report
    assert before == after

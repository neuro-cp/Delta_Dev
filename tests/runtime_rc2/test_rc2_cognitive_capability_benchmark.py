import json
from pathlib import Path

from orchestration.runtime.rc2_cognitive_capability_benchmark import (
    build_benchmark_cases,
    review_output_text_pathologies,
)


def test_benchmark_has_broad_capability_coverage() -> None:
    cases = build_benchmark_cases()
    categories = {case.category for case in cases}

    assert len(cases) >= 100
    assert {
        "recall",
        "multi_concept_retrieval",
        "cross_domain_synthesis",
        "analogy",
        "abstraction",
        "missing_evidence",
        "contradiction_detection",
        "followup_memory",
        "long_conversation",
        "novel_combination",
        "conversation_quality",
    } <= categories


def test_text_pathology_review_detects_nonhuman_output_markers() -> None:
    review = review_output_text_pathologies([
        {
            "case_id": "example",
            "category": "conversation_quality",
            "route": "working_reasoning_set",
            "score": {"score": 0.5},
            "prompt": "Example",
            "answer_preview": "Stored knowledge\n- Example\n\nNo memory, graph edge, replay record, provider call, or training artifact was created.",
        }
    ])

    assert review["report_voice"]["count"] == 1
    assert "summary_findings" in review


def test_existing_benchmark_report_is_valid_if_present() -> None:
    path = Path("reports/RC2_COGNITIVE_CAPABILITY_BENCHMARK.json")
    if not path.exists():
        return
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["case_count"] >= 100
    assert report["safety_passed"] is True
    assert "text_pathology_review" in report

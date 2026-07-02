from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tools.runtime_v12_real_knowledge import (
    _build_cases,
    _case_failure_type,
    _failure_catalog,
)
from orchestration.runtime.runtime_evaluation import RuntimeCaseScorecard, RuntimeEvaluationReport


ROOT = Path(__file__).resolve().parents[3]
ALLOWED_FAILURES = {
    "Retrieval",
    "Attention",
    "Working Memory",
    "Reasoning",
    "Planning",
    "Response",
    "Knowledge Gap",
    "Evaluation Issue",
    "Unknown",
}


def _record(concept_id: str, concept: str, definition: str) -> dict:
    return {
        "concept_id": concept_id,
        "created_at": "2026-07-02T00:00:00+00:00",
        "updated_at": "2026-07-02T00:00:00+00:00",
        "concept": concept,
        "definition": definition,
        "confidence": 0.82,
        "supporting_evidence": [f"memory-{concept_id}"],
        "contradicting_evidence": [],
        "relationship_ids": [f"rel-{concept_id}"],
        "creation_source": "test",
        "last_validation": None,
        "revision_history": [],
        "metadata": {},
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mini_records() -> list[dict]:
    return [
        _record(
            "planning-permit",
            "Emergency response planning should revise failed permit assumptions",
            "When a permit assumption fails, emergency response plans should gather evidence, revise sequencing, and account for uncertainty.",
        ),
        _record(
            "industrial-causal",
            "Industrial maintenance failures require causal timeline analysis",
            "Interacting industrial maintenance causes can be separated by comparing failure timelines and rejecting unsupported causes.",
        ),
        _record(
            "contradiction-evidence",
            "Contradictory eyewitness reports require evidence ranking",
            "Conflicting reports and contradictory evidence should be handled by ranking evidence quality before resolving the contradiction.",
        ),
        _record(
            "shelter-allocation",
            "Emergency shelter resource allocation should respond to demand",
            "When emergency shelter demand changes, resource allocation should compare capacity, equity, and risk before reallocating supplies.",
        ),
        _record(
            "risk-plan",
            "Plans should account for failure risk and uncertainty",
            "A plan should identify failure risk, uncertainty, prediction evidence, and revision triggers before execution.",
        ),
        _record(
            "policy-audit",
            "Policy exceptions and audit findings require reconciliation",
            "Policy exceptions should be reconciled with audit findings by comparing rule evidence and documenting unresolved uncertainty.",
        ),
        _record(
            "logistics-capacity",
            "Emergency logistics should sequence access resources and capacity checks",
            "Response teams should sequence emergency access, resource staging, and capacity checks before committing scarce logistics resources.",
        ),
    ]


def _write_mini_campaign(tmp_path: Path) -> tuple[Path, Path]:
    campaign_root = tmp_path / "phaseA"
    campaign = campaign_root / "mini"
    store = campaign / "store"
    reports = campaign / "chunks" / "chunk_001" / "reports"
    _write_jsonl(store / "knowledge.jsonl", _mini_records())
    reports.mkdir(parents=True, exist_ok=True)
    reports.joinpath("promotion_governance_report.json").write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "concept_id": row["concept_id"],
                        "recommendation": "Validated",
                        "promotion_score": 0.63,
                        "dimensions": {
                            "projected_centrality": 0.35,
                            "evidence_support": 0.8,
                        },
                    }
                    for row in _mini_records()
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return campaign_root, store / "knowledge.jsonl"


def test_real_knowledge_cases_are_selected_from_candidate_records():
    records = _mini_records()
    decisions = {
        row["concept_id"]: {"promotion_score": 0.61, "recommendation": "Validated"}
        for row in records
    }

    cases, metadata = _build_cases(records=records, decisions=decisions)

    assert len(cases) == 10
    assert {case.name for case in cases} >= {
        "planning_failed_assumption",
        "causal_industrial_failure",
        "sparse_violin_tuning",
    }
    assert cases[0].expected_concepts
    assert all(
        concept_id in {row["concept_id"] for row in records}
        for case in cases
        for concept_id in case.expected_concepts
    )
    assert metadata["planning_failed_assumption"]["expected_concept_text"][0]["concept_id"] == "planning-permit"
    assert next(case for case in cases if case.name == "sparse_violin_tuning").sparse_expected is True


def test_runtime_v12_runner_writes_reports_and_preserves_store(tmp_path):
    campaign_root, knowledge_path = _write_mini_campaign(tmp_path)
    reports_dir = tmp_path / "reports"
    before = _hash(knowledge_path)

    completed = subprocess.run(
        [
            sys.executable,
            "tools/runtime_v12_real_knowledge.py",
            "--campaign-root",
            str(campaign_root),
            "--campaign",
            "mini",
            "--reports-dir",
            str(reports_dir),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert _hash(knowledge_path) == before
    expected_reports = {
        "runtime_v12_real_knowledge.md",
        "runtime_v12_real_knowledge.json",
        "runtime_v12_retrieval_analysis.md",
        "runtime_v12_attention_analysis.md",
        "runtime_v12_reasoning_analysis.md",
        "runtime_v12_planning_analysis.md",
        "runtime_v12_response_analysis.md",
        "runtime_v12_failure_catalog.md",
        "runtime_v12_runtime_health.md",
        "runtime_v12_question_scorecards.md",
    }
    assert expected_reports <= {path.name for path in reports_dir.iterdir()}
    payload = json.loads((reports_dir / "runtime_v12_real_knowledge.json").read_text(encoding="utf-8"))
    assert payload["read_only_verified"] is True
    assert payload["health"]["grade"] in {"PASS", "PASS WITH ISSUES", "FAIL"}
    assert len(payload["cases"]) == 10
    assert {item["failure_type"] for item in payload["failure_catalog"]} <= ALLOWED_FAILURES
    assert not (tmp_path / "canonical").exists()


def test_runtime_v12_evaluation_is_deterministic(tmp_path):
    campaign_root, _ = _write_mini_campaign(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"

    for reports_dir in (first, second):
        subprocess.run(
            [
                sys.executable,
                "tools/runtime_v12_real_knowledge.py",
                "--campaign-root",
                str(campaign_root),
                "--campaign",
                "mini",
                "--reports-dir",
                str(reports_dir),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    first_payload = json.loads((first / "runtime_v12_real_knowledge.json").read_text(encoding="utf-8"))
    second_payload = json.loads((second / "runtime_v12_real_knowledge.json").read_text(encoding="utf-8"))
    assert first_payload["aggregate"] == second_payload["aggregate"]
    assert first_payload["case_metadata"] == second_payload["case_metadata"]
    assert first_payload["failure_catalog"] == second_payload["failure_catalog"]


def test_runtime_v12_failure_classification_uses_fixed_taxonomy():
    case = RuntimeCaseScorecard(
        name="miss",
        category="retrieval",
        question="q",
        activated_concepts=[],
        retrieval_precision=0.0,
        retrieval_recall=0.0,
        missed_concepts=["core"],
        irrelevant_concepts=[],
        activation_confidence=0.0,
        grounding_score=1.0,
        unsupported_claims=0,
        conflict_score=1.0,
        confidence_calibration=1.0,
        planning_score=1.0,
        hallucination_count=0,
        response_confidence=0.0,
        used_concepts=[],
        unused_concepts=[],
        reasoning_referenced_concepts=[],
        planning_referenced_concepts=[],
        response_referenced_concepts=[],
        working_memory_efficiency=1.0,
        planning_utilization_ratio=1.0,
        response_utilization_ratio=1.0,
        overall_utilization_ratio=1.0,
        activation_waste={},
        neighbor_utility={},
        useful_neighbor_count=0,
        noise_count=0,
        ignored_count=0,
        attention_recall=1.0,
        attention_precision=1.0,
        used_noise_count=0,
        ignored_noise_count=0,
        suppressed_core_count=0,
        concept_contributions=[],
        reasoning_contribution_ratio=1.0,
        supporting_ratio=0.0,
        peripheral_ratio=0.0,
        noise_used_in_reasoning=0,
        planning_core_coverage=1.0,
        response_core_coverage=1.0,
        runtime_decision="Under-Attending",
        passed=False,
        notes=[],
    )
    report = RuntimeEvaluationReport(
        suite_name="test",
        cases=[case],
        category_scores={},
        aggregate={},
    )

    assert _case_failure_type(case) == "Retrieval"
    failures = _failure_catalog(report)
    assert failures[0]["failure_type"] in ALLOWED_FAILURES

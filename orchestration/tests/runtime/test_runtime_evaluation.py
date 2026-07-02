from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict

from knowledge.semantic_record import SemanticKnowledgeRecord
from orchestration.runtime import RuntimeEvaluationCase, RuntimeEvaluationSuite


def _record(concept_id: str, concept: str, definition: str, confidence: float = 0.8):
    return SemanticKnowledgeRecord(
        concept_id=concept_id,
        created_at="2026-07-02T00:00:00+00:00",
        updated_at="2026-07-02T00:00:00+00:00",
        concept=concept,
        definition=definition,
        confidence=confidence,
        supporting_evidence=[f"memory-{concept_id}"],
        contradicting_evidence=[],
        relationship_ids=[f"rel-{concept_id}"],
        creation_source="test",
        last_validation=None,
        revision_history=[],
        metadata={},
    )


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(row), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_runtime_evaluation_scores_retrieval_and_sparse_behavior(tmp_path):
    store = tmp_path / "store"
    _write_jsonl(
        store / "knowledge.jsonl",
        [
            _record(
                "gps-multipath",
                "GPS multipath interference",
                "Dense buildings can reflect GPS signals and cause multipath interference.",
            ),
            _record(
                "gps-atmospheric",
                "GPS atmospheric delay",
                "Atmospheric delay can reduce GPS position accuracy.",
            ),
            _record(
                "snow-plow",
                "Snowstorm plow positioning",
                "Cities should pre-position plows before severe snowstorms.",
            ),
        ],
    )

    before = (store / "knowledge.jsonl").read_text(encoding="utf-8")
    suite = RuntimeEvaluationSuite(
        cases=[
            RuntimeEvaluationCase(
                name="gps",
                category="retrieval_accuracy",
                question="What causes GPS drift near dense buildings?",
                expected_concepts=["gps-multipath"],
                useful_neighbor_concepts=["gps-atmospheric"],
                forbidden_concepts=["snow-plow"],
                expected_plan="Evidence-grounded recommendation",
            ),
            RuntimeEvaluationCase(
                name="sparse",
                category="sparse_knowledge",
                question="Explain violin tuning.",
                sparse_expected=True,
                expected_plan="Low-evidence response",
            ),
        ]
    )

    report = suite.run(store_root=store)

    assert (store / "knowledge.jsonl").read_text(encoding="utf-8") == before
    assert report.aggregate["case_count"] == 2.0
    assert report.cases[0].retrieval_recall == 1.0
    assert "snow-plow" not in report.cases[0].activated_concepts
    assert report.cases[0].working_memory_efficiency == 1.0
    assert report.cases[0].overall_utilization_ratio == 1.0
    assert report.cases[0].activation_waste["gps-multipath"] == "USED"
    assert report.cases[0].neighbor_utility["gps-atmospheric"] == "Useful Neighbor"
    contributions = {
        contribution.concept_id: contribution
        for contribution in report.cases[0].concept_contributions
    }
    assert contributions["gps-multipath"].classification == "Core"
    assert contributions["gps-multipath"].reasoned is True
    if "gps-atmospheric" in contributions and contributions["gps-atmospheric"].attended:
        assert contributions["gps-atmospheric"].classification in {"Supporting", "Core"}
    assert report.cases[0].noise_used_in_reasoning == 0
    assert report.cases[1].activated_concepts == []
    assert report.cases[1].working_memory_efficiency == 1.0
    assert report.cases[1].hallucination_count == 0
    assert report.cases[1].confidence_calibration == 1.0


def test_runtime_evaluation_runner_writes_reports(tmp_path):
    store = tmp_path / "fixture_store"
    reports = tmp_path / "reports"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/runtime_evaluation_suite.py",
            "--store-root",
            str(store),
            "--reports-dir",
            str(reports),
        ],
        cwd="G:/Delta_Dev",
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    report_path = reports / "phaseB_runtime_evaluation_report.json"
    efficiency_path = reports / "phaseB_runtime_efficiency.json"
    activation_waste_path = reports / "phaseB_activation_waste.md"
    neighbor_utility_path = reports / "phaseB_neighbor_utility.md"
    contribution_path = reports / "phaseB_reasoning_contribution.json"
    flow_path = reports / "phaseB_reasoning_flow.md"
    contribution_scorecards_path = reports / "phaseB_contribution_scorecards.md"
    attention_vs_reasoning_path = reports / "phaseB_attention_vs_reasoning.md"
    attention_optimization_path = reports / "phaseB_attention_optimization.json"
    attention_tradeoff_path = reports / "phaseB_attention_tradeoff.md"
    attention_distribution_path = reports / "phaseB_attention_score_distribution.md"
    runtime_progress_path = reports / "phaseB_runtime_progress.md"
    scorecard_path = reports / "phaseB_runtime_scorecards.md"
    assert report_path.exists()
    assert efficiency_path.exists()
    assert activation_waste_path.exists()
    assert neighbor_utility_path.exists()
    assert contribution_path.exists()
    assert flow_path.exists()
    assert contribution_scorecards_path.exists()
    assert attention_vs_reasoning_path.exists()
    assert attention_optimization_path.exists()
    assert attention_tradeoff_path.exists()
    assert attention_distribution_path.exists()
    assert runtime_progress_path.exists()
    assert scorecard_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["suite_name"] == "Phase B Runtime Evaluation Suite"
    assert payload["aggregate"]["case_count"] == 6.0
    efficiency = json.loads(efficiency_path.read_text(encoding="utf-8"))
    assert "working_memory_efficiency" in efficiency["aggregate"]
    assert "recommendation" in efficiency
    contribution = json.loads(contribution_path.read_text(encoding="utf-8"))
    assert "reasoning_contribution_ratio" in contribution["aggregate"]
    assert contribution["aggregate"]["noise_used_in_reasoning"] == 0.0
    attention = json.loads(attention_optimization_path.read_text(encoding="utf-8"))
    assert attention["stopping_rule_met"] is True
    assert attention["targets"]["attention_recall_at_least_0_95"] is True

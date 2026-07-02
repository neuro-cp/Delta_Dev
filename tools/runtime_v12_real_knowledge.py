from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.runtime_evaluation import (
    RuntimeCaseScorecard,
    RuntimeEvaluationCase,
    RuntimeEvaluationReport,
    RuntimeEvaluationSuite,
)


@dataclass(frozen=True)
class RealKnowledgeQuestionSpec:
    name: str
    category: str
    question: str
    terms: tuple[str, ...]
    useful_neighbor_terms: tuple[str, ...] = ()
    sparse_expected: bool = False
    expected_plan: str | None = "Evidence-grounded recommendation"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Runtime V1.2 against real Phase A candidate knowledge.")
    parser.add_argument(
        "--campaign-root",
        type=Path,
        default=Path(".tmp/experiments/phaseA_architecture_graduation"),
    )
    parser.add_argument("--campaign", default="overnight_3000")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    campaign_dir = args.campaign_root / args.campaign
    store_root = campaign_dir / "store"
    store_path = store_root / "knowledge.jsonl"
    if not store_path.exists():
        raise SystemExit(f"missing Phase A knowledge store: {store_path}")

    reports_dirs = _chunk_report_dirs(campaign_dir)
    records = _load_jsonl(store_path)
    decisions = _governance_decisions(reports_dirs)
    before_hash = _file_hash(store_path)
    cases, case_metadata = _build_cases(records=records, decisions=decisions)

    suite = RuntimeEvaluationSuite(
        suite_name="Runtime V1.2 Real Knowledge Evaluation",
        cases=cases,
        activation_limit=10,
    )
    report = suite.run(store_root=store_root, reports_dirs=tuple(reports_dirs))
    after_hash = _file_hash(store_path)
    readonly_ok = before_hash == after_hash
    payload = _payload(
        report=report,
        case_metadata=case_metadata,
        campaign=str(campaign_dir),
        store_hash_before=before_hash,
        store_hash_after=after_hash,
        readonly_ok=readonly_ok,
    )

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    _write_reports(args.reports_dir, payload)
    return 0


def _build_cases(
    *,
    records: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> tuple[list[RuntimeEvaluationCase], dict[str, Any]]:
    specs = [
        RealKnowledgeQuestionSpec(
            name="planning_failed_assumption",
            category="planning",
            question="How should a team revise an emergency response plan after a failed permit assumption?",
            terms=("emergency", "response", "plan", "failed", "permit"),
            useful_neighbor_terms=("evidence", "risk", "uncertainty"),
        ),
        RealKnowledgeQuestionSpec(
            name="causal_industrial_failure",
            category="causal_reasoning",
            question="How should interacting causes be analyzed in industrial maintenance?",
            terms=("industrial", "maintenance", "cause", "failure"),
            useful_neighbor_terms=("timeline", "evidence"),
        ),
        RealKnowledgeQuestionSpec(
            name="contradictory_evidence",
            category="contradiction_handling",
            question="How should contradictory eyewitness reports or conflicting evidence be handled?",
            terms=("contradiction", "eyewitness", "reports", "evidence"),
            useful_neighbor_terms=("resolution", "third-party"),
        ),
        RealKnowledgeQuestionSpec(
            name="resource_allocation_shelters",
            category="resource_allocation",
            question="How should emergency shelter resources be allocated when demand changes?",
            terms=("emergency", "shelter", "resource", "allocation", "demand"),
            useful_neighbor_terms=("equity", "capacity", "risk"),
        ),
        RealKnowledgeQuestionSpec(
            name="risk_uncertainty_planning",
            category="risk_assessment",
            question="How should a plan account for failure risk and uncertainty?",
            terms=("plan", "failure", "risk", "uncertainty"),
            useful_neighbor_terms=("prediction", "evidence"),
        ),
        RealKnowledgeQuestionSpec(
            name="policy_audit_conflict",
            category="conflicting_evidence",
            question="How should policy exceptions and audit findings be reconciled?",
            terms=("policy", "exception", "audit", "findings"),
            useful_neighbor_terms=("evidence", "rule"),
        ),
        RealKnowledgeQuestionSpec(
            name="multi_step_failure_revision",
            category="multi_step_reasoning",
            question="How should a team identify failure points, gather evidence, and revise a plan?",
            terms=("failure", "evidence", "revise", "plan"),
            useful_neighbor_terms=("prediction", "uncertainty"),
        ),
        RealKnowledgeQuestionSpec(
            name="logistics_proxy_planning",
            category="logistics",
            question="How should a response team sequence emergency access, resource staging, and capacity checks?",
            terms=("response", "emergency", "resource", "capacity"),
            useful_neighbor_terms=("planning", "risk"),
        ),
        RealKnowledgeQuestionSpec(
            name="sparse_violin_tuning",
            category="sparse_knowledge",
            question="Explain violin tuning for a beginner.",
            terms=(),
            sparse_expected=True,
            expected_plan="Low-evidence response",
        ),
        RealKnowledgeQuestionSpec(
            name="unsupported_recipe",
            category="unsupported_questions",
            question="What is the best recipe for sourdough bread?",
            terms=(),
            sparse_expected=True,
            expected_plan="Low-evidence response",
        ),
    ]

    cases: list[RuntimeEvaluationCase] = []
    metadata: dict[str, Any] = {}
    for spec in specs:
        expected = [] if spec.sparse_expected else _select_concepts(records, decisions, spec.terms, limit=3)
        neighbors = [] if spec.sparse_expected else _select_concepts(records, decisions, spec.useful_neighbor_terms, limit=2, exclude=set(expected))
        cases.append(
            RuntimeEvaluationCase(
                name=spec.name,
                category=spec.category,
                question=spec.question,
                expected_concepts=expected,
                useful_neighbor_concepts=neighbors,
                sparse_expected=spec.sparse_expected,
                expected_plan=spec.expected_plan,
            )
        )
        metadata[spec.name] = {
            "terms": list(spec.terms),
            "useful_neighbor_terms": list(spec.useful_neighbor_terms),
            "expected_concepts": expected,
            "useful_neighbor_concepts": neighbors,
            "expected_concept_text": [_concept_summary(records, item) for item in expected],
            "useful_neighbor_text": [_concept_summary(records, item) for item in neighbors],
        }
    return cases, metadata


def _select_concepts(
    records: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    terms: Iterable[str],
    *,
    limit: int,
    exclude: set[str] | None = None,
) -> list[str]:
    exclude = exclude or set()
    normalized_terms = [term.lower() for term in terms if term]
    scored: list[tuple[float, str]] = []
    for record in _latest_records(records):
        concept_id = str(record.get("concept_id", ""))
        if not concept_id or concept_id in exclude:
            continue
        text = f"{record.get('concept', '')} {record.get('definition', '')}".lower()
        matches = sum(1 for term in normalized_terms if term in text)
        if not matches:
            continue
        decision = decisions.get(concept_id, {})
        promotion_score = float(decision.get("promotion_score", 0.0) or 0.0)
        confidence = float(record.get("confidence", 0.0) or 0.0)
        score = (2.0 * matches) + promotion_score + (0.25 * confidence)
        scored.append((score, concept_id))
    scored.sort(reverse=True)
    return [concept_id for _, concept_id in scored[:limit]]


def _payload(
    *,
    report: RuntimeEvaluationReport,
    case_metadata: dict[str, Any],
    campaign: str,
    store_hash_before: str,
    store_hash_after: str,
    readonly_ok: bool,
) -> dict[str, Any]:
    failures = _failure_catalog(report)
    health = _runtime_health(report, failures, readonly_ok)
    return {
        "campaign": campaign,
        "store_hash_before": store_hash_before,
        "store_hash_after": store_hash_after,
        "read_only_verified": readonly_ok,
        "health": health,
        "aggregate": report.aggregate,
        "category_scores": report.category_scores,
        "case_metadata": case_metadata,
        "cases": [asdict(case) for case in report.cases],
        "failure_catalog": failures,
    }


def _runtime_health(report: RuntimeEvaluationReport, failures: list[dict[str, Any]], readonly_ok: bool) -> dict[str, Any]:
    hallucinations = float(report.aggregate.get("hallucinations", 0.0))
    grounding = float(report.aggregate.get("grounding_score", 0.0))
    noise = float(report.aggregate.get("noise_used_in_reasoning", 0.0))
    if not readonly_ok or hallucinations > 0 or grounding < 0.9:
        grade = "FAIL"
    elif failures:
        grade = "PASS WITH ISSUES"
    else:
        grade = "PASS"
    return {
        "grade": grade,
        "strengths": _strengths(report, readonly_ok),
        "weaknesses": _weaknesses(report, failures),
        "recommended_next_work": _recommendation(grade, failures, noise),
    }


def _failure_catalog(report: RuntimeEvaluationReport) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for case in report.cases:
        failure_type = _case_failure_type(case)
        if failure_type:
            failures.append(
                {
                    "case": case.name,
                    "category": case.category,
                    "failure_type": failure_type,
                    "runtime_decision": case.runtime_decision,
                    "notes": case.notes,
                    "missed_concepts": case.missed_concepts,
                    "irrelevant_concepts": case.irrelevant_concepts,
                    "suppressed_core_count": case.suppressed_core_count,
                    "noise_used_in_reasoning": case.noise_used_in_reasoning,
                    "planning_core_coverage": case.planning_core_coverage,
                    "response_core_coverage": case.response_core_coverage,
                }
            )
    return failures


def _case_failure_type(case: RuntimeCaseScorecard) -> str | None:
    if case.hallucination_count or case.unsupported_claims:
        return "Response"
    if case.retrieval_recall < 0.75:
        return "Retrieval"
    if case.attention_recall < 0.75 or case.used_noise_count:
        return "Attention"
    if case.working_memory_efficiency < 0.2 and case.activated_concepts:
        return "Working Memory"
    if case.noise_used_in_reasoning or case.runtime_decision == "Reasoning Drift":
        return "Reasoning"
    if case.planning_core_coverage < 0.75 or case.runtime_decision == "Planning Drift":
        return "Planning"
    if case.response_core_coverage < 0.75 or case.runtime_decision == "Response Drift":
        return "Response"
    if not case.passed:
        return "Knowledge Gap" if not case.missed_concepts and case.retrieval_recall == 1.0 else "Evaluation Issue"
    return None


def _strengths(report: RuntimeEvaluationReport, readonly_ok: bool) -> list[str]:
    strengths = []
    if readonly_ok:
        strengths.append("candidate store remained read-only")
    if float(report.aggregate.get("grounding_score", 0.0)) >= 1.0:
        strengths.append("responses remained grounded")
    if float(report.aggregate.get("hallucinations", 0.0)) == 0.0:
        strengths.append("hallucinations remained zero")
    if float(report.aggregate.get("noise_used_in_reasoning", 0.0)) == 0.0:
        strengths.append("attention prevented noise from influencing reasoning")
    return strengths


def _weaknesses(report: RuntimeEvaluationReport, failures: list[dict[str, Any]]) -> list[str]:
    weaknesses = []
    if failures:
        counts: dict[str, int] = {}
        for item in failures:
            counts[item["failure_type"]] = counts.get(item["failure_type"], 0) + 1
        weaknesses.append("failure distribution: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    if float(report.aggregate.get("retrieval_precision", 1.0)) < 0.5:
        weaknesses.append("retrieval precision is low on real candidate knowledge")
    return weaknesses


def _recommendation(grade: str, failures: list[dict[str, Any]], noise: float) -> str:
    if grade == "PASS" and noise == 0.0:
        return "Proceed to Runtime V1.3 planning only after adding more held-out real-store questions."
    if failures:
        dominant = max({item["failure_type"] for item in failures}, key=lambda key: sum(1 for item in failures if item["failure_type"] == key))
        return f"Do not modify learning. Inspect {dominant} failures first using the generated scorecards."
    return "Collect more real-store evaluation evidence before architectural changes."


def _write_reports(reports_dir: Path, payload: dict[str, Any]) -> None:
    (reports_dir / "runtime_v12_real_knowledge.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "runtime_v12_real_knowledge.md").write_text(_main_markdown(payload), encoding="utf-8")
    (reports_dir / "runtime_v12_retrieval_analysis.md").write_text(_metric_table(payload, "Retrieval", ["retrieval_precision", "retrieval_recall", "activation_confidence"]), encoding="utf-8")
    (reports_dir / "runtime_v12_attention_analysis.md").write_text(_metric_table(payload, "Attention", ["attention_precision", "attention_recall", "suppressed_core_count", "ignored_noise_count"]), encoding="utf-8")
    (reports_dir / "runtime_v12_reasoning_analysis.md").write_text(_metric_table(payload, "Reasoning", ["reasoning_contribution_ratio", "supporting_ratio", "peripheral_ratio", "noise_used_in_reasoning"]), encoding="utf-8")
    (reports_dir / "runtime_v12_planning_analysis.md").write_text(_metric_table(payload, "Planning", ["planning_score", "planning_core_coverage"]), encoding="utf-8")
    (reports_dir / "runtime_v12_response_analysis.md").write_text(_metric_table(payload, "Response", ["grounding_score", "response_core_coverage", "hallucination_count", "response_confidence"]), encoding="utf-8")
    (reports_dir / "runtime_v12_failure_catalog.md").write_text(_failure_markdown(payload), encoding="utf-8")
    (reports_dir / "runtime_v12_runtime_health.md").write_text(_health_markdown(payload), encoding="utf-8")
    (reports_dir / "runtime_v12_question_scorecards.md").write_text(_scorecards_markdown(payload), encoding="utf-8")


def _main_markdown(payload: dict[str, Any]) -> str:
    health = payload["health"]
    lines = [
        "# Runtime V1.2 Real Knowledge Evaluation",
        "",
        f"- campaign: `{payload['campaign']}`",
        f"- read-only verified: `{payload['read_only_verified']}`",
        f"- overall runtime grade: `{health['grade']}`",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in payload["aggregate"].items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend(["", "## Recommendation", "", health["recommended_next_work"], ""])
    return "\n".join(lines)


def _metric_table(payload: dict[str, Any], title: str, fields: list[str]) -> str:
    lines = [f"# Runtime V1.2 {title} Analysis", "", "| Case | " + " | ".join(fields) + " |", "| --- | " + " | ".join("---:" for _ in fields) + " |"]
    for case in payload["cases"]:
        values = [f"`{case.get(field, '')}`" for field in fields]
        lines.append(f"| {case['name']} | " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _failure_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Runtime V1.2 Failure Catalog", "", "| Case | Failure Type | Runtime Decision | Notes |", "| --- | --- | --- | --- |"]
    if not payload["failure_catalog"]:
        lines.append("| none | none | none | none |")
    for item in payload["failure_catalog"]:
        lines.append(f"| {item['case']} | `{item['failure_type']}` | `{item['runtime_decision']}` | {'; '.join(item['notes']) if item['notes'] else ''} |")
    return "\n".join(lines) + "\n"


def _health_markdown(payload: dict[str, Any]) -> str:
    health = payload["health"]
    lines = [
        "# Runtime V1.2 Runtime Health",
        "",
        f"Overall Runtime Grade: `{health['grade']}`",
        "",
        "## Strengths",
        "",
        *[f"- {item}" for item in health["strengths"]],
        "",
        "## Weaknesses",
        "",
        *[f"- {item}" for item in health["weaknesses"]],
        "",
        "## Recommended Next Work",
        "",
        health["recommended_next_work"],
    ]
    return "\n".join(lines) + "\n"


def _scorecards_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.2 Question Scorecards",
        "",
        "| Case | Category | Retrieval Recall | Attention Recall | Noise Used | Grounding | Planning Coverage | Response Coverage | Decision |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in payload["cases"]:
        lines.append(
            f"| {case['name']} | {case['category']} | `{case['retrieval_recall']}` | "
            f"`{case['attention_recall']}` | `{case['noise_used_in_reasoning']}` | "
            f"`{case['grounding_score']}` | `{case['planning_core_coverage']}` | "
            f"`{case['response_core_coverage']}` | `{case['runtime_decision']}` |"
        )
    return "\n".join(lines) + "\n"


def _chunk_report_dirs(campaign_dir: Path) -> list[Path]:
    chunks = sorted((campaign_dir / "chunks").glob("chunk_*"))
    return [chunk / "reports" for chunk in chunks if (chunk / "reports" / "promotion_governance_report.json").exists()]


def _governance_decisions(reports_dirs: list[Path]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for reports_dir in reports_dirs:
        path = reports_dir / "promotion_governance_report.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for decision in payload.get("decisions", []):
            concept_id = decision.get("concept_id")
            if concept_id:
                decisions[str(concept_id)] = decision
    return decisions


def _latest_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    superseded = {prior for record in records for prior in record.get("revision_history", [])}
    return [record for record in records if record.get("concept_id") not in superseded]


def _concept_summary(records: list[dict[str, Any]], concept_id: str) -> dict[str, Any]:
    for record in records:
        if record.get("concept_id") == concept_id:
            return {
                "concept_id": concept_id,
                "concept": record.get("concept", ""),
                "definition": record.get("definition", ""),
            }
    return {"concept_id": concept_id}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())

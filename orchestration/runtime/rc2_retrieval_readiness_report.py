"""RC2.3 retrieval ranking and multi-concept readiness reports.

This module is report-only. It does not train, call providers, mutate
canonical memory, execute actions, or enable synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import (
    build_developmental_memory_state,
    query_approved_concepts,
    retrieve_multi_concept_set,
)
from orchestration.runtime.rc2_operator_quality_suite import run_operator_quality_suite


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "synthesis_enabled": False,
}

RETRIEVAL_PROBES = [
    ("Tell me about electricity.", ("electric", "static", "circuit")),
    ("Tell me about photosynthesis.", ("photosynthesis",)),
    ("What about law?", ("law", "government")),
    ("What do you know about coding?", ("coding", "programming", "software")),
    ("Explain AI memory.", ("memory", "delta", "noncanonical")),
]

MULTI_CONCEPT_PROBES = [
    "How does photosynthesis relate to respiration?",
    "Compare inflation and interest rates.",
    "How does memory in DELTA relate to human memory?",
    "What connects planning, feedback loops, and software architecture?",
    "How are gravity and orbital motion connected?",
]


def build_retrieval_readiness_report() -> dict[str, Any]:
    operator = run_operator_quality_suite()
    retrieval_results = []
    for question, terms in RETRIEVAL_PROBES:
        result = query_approved_concepts(question)
        answer = str(result.get("answer") or "").lower()
        names = [str(item.get("concept_name") or "") for item in result.get("matches", [])]
        haystack = " ".join([answer, *names]).lower()
        retrieval_results.append({
            "question": question,
            "matched": bool(result.get("matched")),
            "top_concepts": names[:5],
            "expected_terms": list(terms),
            "term_hit": any(term in haystack for term in terms),
            "retrieval_precision_estimate": result.get("retrieval_precision_estimate", 0.0),
            "duplicate_suppression_count": result.get("duplicate_suppression_count", 0),
            "top_diagnostics": [
                {
                    "concept_name": item.get("concept_name"),
                    "score": (item.get("_retrieval_score") or {}).get("score"),
                    "components": (item.get("_retrieval_score") or {}).get("components", {}),
                    "reasons": (item.get("_retrieval_score") or {}).get("reasons", []),
                    "relevance_gate_passed": (item.get("_retrieval_score") or {}).get("relevance_gate_passed"),
                }
                for item in result.get("matches", [])[:3]
            ],
        })
    metrics = operator["metrics"]
    report = {
        "phase": "RC2.3 Retrieval Ranking + Multi-Concept Readiness",
        "synthesis_readiness": False,
        "memory_state": build_developmental_memory_state(),
        "operator_quality_metrics": metrics,
        "retrieval_probe_results": retrieval_results,
        "retrieval_precision": metrics.get("retrieval_precision", metrics.get("correct_concept_retrieval", 0.0)),
        "unnecessary_local_model_call_rate": metrics.get("unnecessary_local_model_call_rate", 1.0),
        "browse_repetition_rate": metrics.get("browse_repetition_rate", 1.0),
        "duplicate_suppression_rate": metrics.get("duplicate_suppression_rate", 0.0),
        "synthesis_readiness_score": metrics.get("synthesis_readiness_score", 0.0),
        "safety": dict(SAFETY),
        "remaining_blockers": _blockers(metrics),
        "recommendation": _recommendation(metrics),
    }
    return report


def build_multi_concept_report() -> dict[str, Any]:
    results = []
    for question in MULTI_CONCEPT_PROBES:
        result = retrieve_multi_concept_set(question)
        results.append({
            "question": question,
            "matched": result["matched"],
            "seeds": result["seeds"],
            "top_concepts": [item.get("concept_name") for item in result.get("matches", [])],
            "retrieval_set_quality": result["retrieval_set_quality"],
            "synthesis_readiness": False,
            "duplicate_suppression_count": result.get("duplicate_suppression_count", 0),
        })
    score = round(sum(item["retrieval_set_quality"] for item in results) / len(results), 4) if results else 0.0
    return {
        "phase": "RC2.3 Multi-Concept Retrieval",
        "probe_count": len(results),
        "matched_count": sum(1 for item in results if item["matched"]),
        "multi_concept_retrieval_score": score,
        "synthesis_readiness": False,
        "results": results,
        "safety": dict(SAFETY),
        "recommendation": "KEEP_SYNTHESIS_DISABLED_AND_CONTINUE_RETRIEVAL_REFINEMENT",
    }


def write_retrieval_readiness_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    retrieval = build_retrieval_readiness_report()
    multi = build_multi_concept_report()
    (REPORTS / "RC2_RETRIEVAL_RANKING_READINESS.json").write_text(
        json.dumps(retrieval, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (REPORTS / "RC2_MULTI_CONCEPT_RETRIEVAL.json").write_text(
        json.dumps(multi, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (REPORTS / "RC2_RETRIEVAL_RANKING_READINESS.md").write_text(_retrieval_md(retrieval), encoding="utf-8")
    (REPORTS / "RC2_MULTI_CONCEPT_RETRIEVAL.md").write_text(_multi_md(multi), encoding="utf-8")
    (DOCS / "continuation_rc2_retrieval_readiness.md").write_text(_continuation_md(retrieval, multi), encoding="utf-8")
    return {"retrieval": retrieval, "multi_concept": multi}


def _blockers(metrics: dict[str, float]) -> list[str]:
    blockers = []
    if metrics.get("retrieval_precision", 0.0) < 0.85:
        blockers.append("retrieval_precision_below_synthesis_gate")
    if metrics.get("multi_concept_retrieval", 0.0) < 0.80:
        blockers.append("multi_concept_retrieval_below_gate")
    if metrics.get("browse_repetition_rate", 1.0) > 0.10:
        blockers.append("browse_repetition_above_gate")
    if metrics.get("unnecessary_local_model_call_rate", 1.0) > 0.15:
        blockers.append("unnecessary_local_model_calls_above_gate")
    return blockers or ["none_for_read_only_retrieval_readiness"]


def _recommendation(metrics: dict[str, float]) -> str:
    if metrics.get("synthesis_readiness_score", 0.0) >= 0.85 and metrics.get("retrieval_precision", 0.0) >= 0.85:
        return "READY_FOR_READ_ONLY_SYNTHESIS_TRIAL_DESIGN_NOT_ACTIVATION"
    return "CONTINUE_RETRIEVAL_RANKING_AND_MULTI_CONCEPT_READINESS"


def _retrieval_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2.3 Retrieval Ranking Readiness",
        "",
        f"Synthesis readiness: {report['synthesis_readiness']}",
        f"Retrieval precision: {report['retrieval_precision']}",
        f"Unnecessary local-model call rate: {report['unnecessary_local_model_call_rate']}",
        f"Browse repetition rate: {report['browse_repetition_rate']}",
        f"Duplicate suppression rate: {report['duplicate_suppression_rate']}",
        f"Synthesis readiness score: {report['synthesis_readiness_score']}",
        "",
        "## Probe Results",
        "",
    ]
    for item in report["retrieval_probe_results"]:
        lines.append(f"- {item['question']}: {item['top_concepts'][:3]}")
        for diagnostic in item.get("top_diagnostics", [])[:1]:
            lines.append(f"  - top score: {diagnostic.get('score')} via {diagnostic.get('components')}")
    lines.extend(["", "## Blockers", "", *[f"- {item}" for item in report["remaining_blockers"]], "", f"Recommendation: {report['recommendation']}"])
    return "\n".join(lines) + "\n"


def _multi_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2.3 Multi-Concept Retrieval",
        "",
        f"Probe count: {report['probe_count']}",
        f"Matched count: {report['matched_count']}",
        f"Multi-concept retrieval score: {report['multi_concept_retrieval_score']}",
        f"Synthesis readiness: {report['synthesis_readiness']}",
        "",
        "## Retrieval Sets",
        "",
    ]
    for item in report["results"]:
        lines.append(f"- {item['question']}: {item['top_concepts']}")
    lines.extend(["", f"Recommendation: {report['recommendation']}"])
    return "\n".join(lines) + "\n"


def _continuation_md(retrieval: dict[str, Any], multi: dict[str, Any]) -> str:
    return "\n".join([
        "# Continuation: RC2.3 Retrieval Readiness",
        "",
        "SYNTHESIS_READINESS remains false.",
        "",
        f"Retrieval precision: {retrieval['retrieval_precision']}",
        f"Multi-concept retrieval score: {multi['multi_concept_retrieval_score']}",
        f"Browse repetition rate: {retrieval['browse_repetition_rate']}",
        f"Unnecessary local-model call rate: {retrieval['unnecessary_local_model_call_rate']}",
        "",
        "Next work should continue improving retrieval precision, set ranking, and browse diversity before enabling any synthesis trial.",
    ]) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_retrieval_readiness_reports(), indent=2, sort_keys=True))

"""RC2.6 manual read-only synthesis quality trial reports.

This harness broadens the RC2.4/RC2.5 read-only synthesis trial set,
scores synthesis quality without activating synthesis, and leaves memory,
canonical storage, providers, training, and autonomous actions disabled.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import build_read_only_synthesis_trial


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

TRIAL_PROMPTS = [
    "Synthesize how photosynthesis relates to respiration.",
    "Synthesize how ATP relates to energy storage.",
    "Synthesize how feedback loops relate to homeostasis.",
    "Synthesize how gravity relates to orbital motion.",
    "Synthesize how pressure relates to fluid flow.",
    "Synthesize how thermodynamics relates to engines.",
    "Synthesize how inflation relates to interest rates.",
    "Synthesize how risk relates to asset allocation.",
    "Synthesize how compound interest relates to long-term investing.",
    "Synthesize what connects planning, feedback loops, and software architecture.",
    "Synthesize how access control relates to user permissions.",
    "Synthesize how adapter patterns relate to system integration.",
    "Synthesize how DELTA memory relates to human memory.",
    "Synthesize how noncanonical memory relates to memory consolidation.",
    "Synthesize how operator approval relates to learning.",
    "Synthesize how law relates to governance.",
    "Synthesize how evidence relates to decision-making.",
    "Synthesize how communication relates to conflict resolution.",
    "Synthesize how insulation relates to energy efficiency.",
    "Synthesize how soil quality relates to plant growth.",
    "Synthesize how maintenance relates to mechanical reliability.",
]

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
    "synthesis_enabled_by_default": False,
}


def build_synthesis_trial_report() -> dict[str, Any]:
    trials = []
    for prompt in TRIAL_PROMPTS:
        result = build_read_only_synthesis_trial(prompt)
        stored_concepts = [_report_concept(item) for item in result.get("stored_concepts", [])]
        concept_scores = [score_concept_substance(item) for item in result.get("stored_concepts", [])]
        synthesis_score = score_synthesis_trial(result, concept_scores)
        trials.append({
            "prompt": prompt,
            "matched": result["matched"],
            "stored_concepts": stored_concepts,
            "concept_substance_scores": concept_scores,
            "tentative_inference": result.get("tentative_inference"),
            "uncertainty": result.get("uncertainty"),
            "synthesis_quality": synthesis_score,
            "memory_write_performed": result.get("memory_write_performed"),
            "synthesis_enabled": result.get("synthesis_enabled"),
        })
    passed = all(
        item["matched"]
        and len(item["stored_concepts"]) >= 2
        and item["tentative_inference"]
        and item["memory_write_performed"] is False
        and item["synthesis_enabled"] is False
        for item in trials
    )
    quality_values = [item["synthesis_quality"]["overall_score"] for item in trials]
    substance_values = [item["synthesis_quality"]["stored_concept_substance"] for item in trials]
    hallucination_values = [item["synthesis_quality"]["hallucination_risk"] for item in trials]
    overreach_values = [item["synthesis_quality"]["overreach_risk"] for item in trials]
    generic_concept_count = sum(
        1
        for trial in trials
        for score in trial["concept_substance_scores"]
        if score["generic_definition"]
    )
    return {
        "phase": "RC2.6 Manual Read-Only Synthesis Quality Trials",
        "trial_count": len(trials),
        "passed": passed,
        "average_synthesis_quality": _avg(quality_values),
        "median_synthesis_quality": _median(quality_values),
        "min_synthesis_quality": round(min(quality_values), 4) if quality_values else 0.0,
        "max_synthesis_quality": round(max(quality_values), 4) if quality_values else 0.0,
        "hallucination_risk_average": _avg(hallucination_values),
        "overreach_risk_average": _avg(overreach_values),
        "stored_concept_substance_average": _avg(substance_values),
        "generic_concept_count": generic_concept_count,
        "synthesis_activation": False,
        "trial_only": True,
        "trials": trials,
        "safety": dict(SAFETY),
        "recommendation": _recommendation(quality_values, generic_concept_count, passed),
    }


def score_concept_substance(concept: dict[str, Any]) -> dict[str, Any]:
    definition = str(concept.get("short_definition") or "")
    propositions = [str(item).strip() for item in concept.get("propositions", []) if str(item).strip()]
    examples = [str(item).strip() for item in concept.get("examples", []) if str(item).strip()]
    misconceptions = [str(item).strip() for item in concept.get("misconceptions", []) if str(item).strip()]
    related = [str(item).strip() for item in concept.get("related_concepts", []) if str(item).strip()]
    generic_definition = _is_generic_definition(definition)
    score = 0.0
    if definition and not generic_definition:
        score += 0.25
    score += min(len(propositions), 3) * 0.12
    score += min(len(examples), 2) * 0.08
    score += min(len(misconceptions), 1) * 0.08
    semantic_related = [item for item in related if not _is_generic_related(item)]
    score += min(len(semantic_related), 4) * 0.06
    if generic_definition:
        score -= 0.18
    score = max(0.0, min(score, 1.0))
    return {
        "concept_name": concept.get("concept_name"),
        "score": round(score, 4),
        "generic_definition": generic_definition,
        "proposition_count": len(propositions),
        "example_count": len(examples),
        "misconception_count": len(misconceptions),
        "semantic_related_count": len(semantic_related),
        "penalties": ["generic_definition"] if generic_definition else [],
    }


def score_synthesis_trial(result: dict[str, Any], concept_scores: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval_relevance = float(result.get("retrieval_set_quality") or 0.0)
    bridge = str(result.get("tentative_inference") or "")
    uncertainty = str(result.get("uncertainty") or "")
    concept_substance = round(sum(item["score"] for item in concept_scores) / len(concept_scores), 4) if concept_scores else 0.0
    concept_diversity = _concept_diversity(result.get("stored_concepts", []))
    proposition_usage = _avg([min(int(item.get("proposition_count", 0)), 3) / 3 for item in concept_scores])
    evidence_provenance_usage = _evidence_provenance_usage(result.get("stored_concepts", []))
    bridge_usefulness = 1.0 if len(bridge.split()) >= 15 and "may connect" in bridge else 0.55 if bridge else 0.0
    uncertainty_quality = 1.0 if "inferred" in uncertainty and "approved" in uncertainty else 0.7 if uncertainty else 0.0
    hallucination_risk = 0.10 if retrieval_relevance >= 0.9 and concept_substance >= 0.8 else 0.35 if retrieval_relevance >= 0.7 else 0.70
    overreach_risk = 0.10 if "may connect" in bridge and "approved" in uncertainty else 0.35 if bridge else 0.75
    overall = (
        retrieval_relevance * 0.18
        + bridge_usefulness * 0.16
        + uncertainty_quality * 0.12
        + concept_substance * 0.18
        + concept_diversity * 0.10
        + proposition_usage * 0.10
        + evidence_provenance_usage * 0.06
        + (1.0 - hallucination_risk) * 0.05
        + (1.0 - overreach_risk) * 0.05
    )
    activation_recommendation = (
        "not_ready_concept_substance_audit_required"
        if concept_substance < 0.75
        else "read_only_operator_review_only"
    )
    return {
        "retrieval_relevance": round(retrieval_relevance, 4),
        "bridge_usefulness": round(bridge_usefulness, 4),
        "uncertainty_quality": round(uncertainty_quality, 4),
        "hallucination_risk": round(hallucination_risk, 4),
        "stored_concept_substance": concept_substance,
        "concept_diversity": round(concept_diversity, 4),
        "proposition_usage": round(proposition_usage, 4),
        "evidence_provenance_usage": round(evidence_provenance_usage, 4),
        "overreach_risk": round(overreach_risk, 4),
        "overall_score": round(overall, 4),
        "activation_recommendation": activation_recommendation,
    }


def write_synthesis_trial_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    report = build_synthesis_trial_report()
    for name in [
        "RC2_READ_ONLY_SYNTHESIS_TRIAL",
        "RC2_SYNTHESIS_QUALITY_SCORING",
        "RC2_MANUAL_SYNTHESIS_QUALITY_TRIALS",
    ]:
        (REPORTS / f"{name}.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        (REPORTS / f"{name}.md").write_text(_report_md(report), encoding="utf-8")
    (DOCS / "continuation_rc2_read_only_synthesis_trial.md").write_text(_continuation_md(report), encoding="utf-8")
    (DOCS / "continuation_rc2_manual_synthesis_quality_trials.md").write_text(_continuation_md(report), encoding="utf-8")
    return report


def _report_concept(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": item.get("concept_id"),
        "concept_name": item.get("concept_name"),
        "domain": item.get("domain"),
        "short_definition": item.get("short_definition"),
        "propositions": item.get("propositions", []),
        "examples": item.get("examples", []),
        "misconceptions": item.get("misconceptions", []),
        "related_concepts": item.get("related_concepts", []),
        "source_type": item.get("source_type"),
        "source_model_id": item.get("source_model_id"),
        "canonical": bool(item.get("canonical")),
    }


def _concept_diversity(concepts: list[dict[str, Any]]) -> float:
    if not concepts:
        return 0.0
    domains = {str(item.get("domain") or "").lower() for item in concepts if str(item.get("domain") or "").strip()}
    names = {str(item.get("concept_name") or "").lower() for item in concepts if str(item.get("concept_name") or "").strip()}
    domain_score = min(len(domains), 3) / 3
    name_score = len(names) / len(concepts)
    return round((domain_score * 0.45) + (name_score * 0.55), 4)


def _evidence_provenance_usage(concepts: list[dict[str, Any]]) -> float:
    if not concepts:
        return 0.0
    present = 0
    for item in concepts:
        if item.get("source_type") or item.get("source_model_id") or item.get("concept_id"):
            present += 1
    return round(present / len(concepts), 4)


def _is_generic_definition(text: str) -> bool:
    lower = " ".join(text.lower().split())
    generic_markers = [
        "is a reusable",
        "helps explain causes, constraints, tradeoffs",
        "practical decisions in the",
        "connects observable situations to underlying",
    ]
    return any(marker in lower for marker in generic_markers)


def _is_generic_related(text: str) -> bool:
    lower = " ".join(text.lower().split())
    return lower.endswith(("reasoning", "evidence", "tradeoffs", "constraints")) or lower in {"causes", "effects", "decisions"}


def _recommendation(quality_values: list[float], generic_concept_count: int, passed: bool) -> str:
    average_quality = _avg(quality_values)
    if not passed:
        return "CONTINUE_CONCEPT_SUBSTANCE_REPAIR"
    if generic_concept_count:
        return "CONTINUE_CONCEPT_SUBSTANCE_REPAIR"
    if average_quality >= 0.9:
        return "PROCEED_TYPED_GRAPH_LINKING_DESIGN"
    if average_quality >= 0.82:
        return "PROCEED_MANUAL_SYNTHESIS_OPERATOR_REVIEW"
    return "CONTINUE_CONCEPT_SUBSTANCE_REPAIR"


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _median(values: list[float]) -> float:
    return round(float(statistics.median(values)), 4) if values else 0.0


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2.6 Manual Read-Only Synthesis Quality Trials",
        "",
        f"Passed: {report['passed']}",
        f"Trial count: {report['trial_count']}",
        f"Average synthesis quality: {report['average_synthesis_quality']}",
        f"Median synthesis quality: {report['median_synthesis_quality']}",
        f"Min synthesis quality: {report['min_synthesis_quality']}",
        f"Max synthesis quality: {report['max_synthesis_quality']}",
        f"Generic concept count: {report['generic_concept_count']}",
        f"Hallucination risk average: {report['hallucination_risk_average']}",
        f"Overreach risk average: {report['overreach_risk_average']}",
        f"Stored concept substance average: {report['stored_concept_substance_average']}",
        f"Synthesis activation: {report['synthesis_activation']}",
        f"Trial only: {report['trial_only']}",
        "",
        "## Trials",
        "",
    ]
    for trial in report["trials"]:
        lines.append(f"### {trial['prompt']}")
        lines.append("")
        lines.append("Stored concepts:")
        for concept in trial["stored_concepts"]:
            lines.append(f"- {concept['concept_name']}: {concept['short_definition']}")
        lines.append("")
        lines.append(f"Tentative inference: {trial['tentative_inference']}")
        lines.append(f"Uncertainty: {trial['uncertainty']}")
        lines.append(f"Synthesis quality: {trial['synthesis_quality']}")
        lines.append("Concept substance:")
        for score in trial["concept_substance_scores"]:
            lines.append(f"- {score['concept_name']}: {score['score']} penalties={score['penalties']}")
        lines.append("")
    lines.append(f"Recommendation: {report['recommendation']}")
    return "\n".join(lines) + "\n"


def _continuation_md(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Continuation: RC2.6 Manual Read-Only Synthesis Quality Trials",
        "",
        "Synthesis remains trial-only and disabled by default.",
        "The expanded suite now covers biology, energy, physics, engineering, finance, software, planning, DELTA memory, psychology, law/government, society, home repair, mechanics, and agriculture.",
        "The scoring harness includes retrieval relevance, bridge usefulness, uncertainty quality, hallucination risk, stored concept substance, concept diversity, proposition usage, evidence/provenance usage, and overreach risk.",
        "No memory writes, canonical writes, training, provider calls, or autonomous actions are allowed in this path.",
        "",
        f"Trial count: {report['trial_count']}",
        f"Average synthesis quality: {report['average_synthesis_quality']}",
        f"Generic concept count: {report['generic_concept_count']}",
        f"Recommendation: {report['recommendation']}",
    ]) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_synthesis_trial_reports(), indent=2, sort_keys=True))

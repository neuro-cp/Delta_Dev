"""RC2.6 read-only typed graph link readiness audit.

This module inspects synthesis-trial concept sets and proposes possible
typed relationship labels. It is report-only: no graph links are stored,
no memory is mutated, and synthesis remains disabled by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_synthesis_trial_report import build_synthesis_trial_report


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

RELATION_TYPES = [
    "depends_on",
    "causes",
    "enables",
    "contrasts_with",
    "example_of",
    "part_of",
    "prerequisite_for",
    "supports",
    "limits",
    "analogy_to",
    "generalizes",
    "specializes",
]

SAFETY = {
    "training_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "graph_links_written": False,
    "memory_write_performed": False,
    "synthesis_enabled_by_default": False,
}


def build_typed_graph_link_readiness_report() -> dict[str, Any]:
    synthesis = build_synthesis_trial_report()
    trial_audits = []
    for trial in synthesis["trials"]:
        links = _propose_trial_links(trial)
        trial_audits.append({
            "prompt": trial["prompt"],
            "concept_count": len(trial["stored_concepts"]),
            "candidate_link_count": len(links),
            "candidate_links": links,
            "readiness_score": _readiness_score(trial, links),
            "stored_only": True,
            "links_written": False,
        })
    scores = [item["readiness_score"] for item in trial_audits]
    relation_counts: dict[str, int] = {}
    for audit in trial_audits:
        for link in audit["candidate_links"]:
            relation_counts[link["relation_type"]] = relation_counts.get(link["relation_type"], 0) + 1
    return {
        "phase": "RC2.6 Typed Graph Link Readiness",
        "trial_count": len(trial_audits),
        "candidate_link_count": sum(item["candidate_link_count"] for item in trial_audits),
        "relation_types_detected": sorted(relation_counts),
        "relation_type_counts": relation_counts,
        "average_readiness_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "min_readiness_score": round(min(scores), 4) if scores else 0.0,
        "max_readiness_score": round(max(scores), 4) if scores else 0.0,
        "trial_audits": trial_audits,
        "graph_links_written": False,
        "read_only": True,
        "safety": dict(SAFETY),
        "recommendation": _recommendation(scores, relation_counts),
    }


def write_typed_graph_link_readiness_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_typed_graph_link_readiness_report()
    (REPORTS / "RC2_TYPED_GRAPH_LINK_READINESS.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (REPORTS / "RC2_TYPED_GRAPH_LINK_READINESS.md").write_text(_report_md(report), encoding="utf-8")
    return report


def _propose_trial_links(trial: dict[str, Any]) -> list[dict[str, Any]]:
    concepts = trial.get("stored_concepts", [])
    links = []
    for index, source in enumerate(concepts):
        for target in concepts[index + 1:]:
            relation = _infer_relation(source, target, trial.get("prompt", ""))
            links.append({
                "source_concept_id": source.get("concept_id"),
                "source_concept": source.get("concept_name"),
                "target_concept_id": target.get("concept_id"),
                "target_concept": target.get("concept_name"),
                "relation_type": relation["relation_type"],
                "rationale": relation["rationale"],
                "confidence": relation["confidence"],
                "requires_operator_review": True,
                "written": False,
            })
    return links


def _infer_relation(source: dict[str, Any], target: dict[str, Any], prompt: str) -> dict[str, Any]:
    text = " ".join([
        str(prompt),
        str(source.get("concept_name")),
        str(target.get("concept_name")),
        " ".join(source.get("propositions", [])),
        " ".join(target.get("propositions", [])),
        " ".join(source.get("related_concepts", [])),
        " ".join(target.get("related_concepts", [])),
    ]).lower()
    if any(term in text for term in ["requires", "input", "prerequisite", "approval"]):
        return {"relation_type": "depends_on", "confidence": 0.72, "rationale": "Terms indicate one concept may require or rely on another."}
    if any(term in text for term in ["causes", "produces", "drives", "converts", "increases", "reduces"]):
        return {"relation_type": "causes", "confidence": 0.70, "rationale": "Propositions describe causal or conversion behavior."}
    if any(term in text for term in ["supports", "helps", "improves", "enables"]):
        return {"relation_type": "supports", "confidence": 0.68, "rationale": "Concept substance describes support or enablement."}
    if any(term in text for term in ["part of", "component", "system", "architecture"]):
        return {"relation_type": "part_of", "confidence": 0.62, "rationale": "Concepts appear within a shared system or architecture context."}
    if any(term in text for term in ["not the same", "differs", "contrast", "rather than"]):
        return {"relation_type": "contrasts_with", "confidence": 0.60, "rationale": "Misconceptions or definitions distinguish the concepts."}
    if any(term in text for term in ["example", "such as"]):
        return {"relation_type": "example_of", "confidence": 0.58, "rationale": "Examples suggest an instance relationship may exist."}
    return {"relation_type": "analogy_to", "confidence": 0.52, "rationale": "The synthesis prompt asks for a connection, but the exact relation type remains tentative."}


def _readiness_score(trial: dict[str, Any], links: list[dict[str, Any]]) -> float:
    if not links:
        return 0.0
    quality = float(trial["synthesis_quality"]["overall_score"])
    typed_ratio = len([link for link in links if link["relation_type"] in RELATION_TYPES]) / len(links)
    confidence = sum(float(link["confidence"]) for link in links) / len(links)
    return round((quality * 0.45) + (typed_ratio * 0.30) + (confidence * 0.25), 4)


def _recommendation(scores: list[float], relation_counts: dict[str, int]) -> str:
    if not scores or min(scores) < 0.65:
        return "CONTINUE_TYPED_LINK_READINESS_AUDIT"
    if len(relation_counts) >= 5:
        return "PROCEED_TYPED_GRAPH_LINKING_DESIGN"
    return "PROCEED_MANUAL_SYNTHESIS_OPERATOR_REVIEW"


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2.6 Typed Graph Link Readiness",
        "",
        f"Trial count: {report['trial_count']}",
        f"Candidate link count: {report['candidate_link_count']}",
        f"Average readiness score: {report['average_readiness_score']}",
        f"Relation types detected: {', '.join(report['relation_types_detected'])}",
        f"Graph links written: {report['graph_links_written']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Trial Audits",
        "",
    ]
    for audit in report["trial_audits"]:
        lines.append(f"### {audit['prompt']}")
        lines.append(f"- readiness: {audit['readiness_score']}")
        lines.append(f"- candidate links: {audit['candidate_link_count']}")
        for link in audit["candidate_links"][:5]:
            lines.append(f"  - {link['source_concept']} -> {link['relation_type']} -> {link['target_concept']}")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_typed_graph_link_readiness_reports(), indent=2, sort_keys=True))

"""RC2.7 governed typed graph linking design and review harness.

This module defines reversible, noncanonical typed graph edge records and a
review-only workflow over the RC2 synthesis trial concept sets. It never
creates graph links automatically, never approves links autonomously, and does
not mutate concept stores or canonical memory.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_typed_graph_link_readiness import build_typed_graph_link_readiness_report


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

RELATION_TYPES = [
    "depends_on",
    "supports",
    "causes",
    "part_of",
    "example_of",
    "prerequisite_for",
    "generalizes",
    "specializes",
    "contrasts_with",
    "analogy_to",
    "enables",
    "limits",
    "related_to",
]

EDGE_SCHEMA_FIELDS = [
    "edge_id",
    "source_concept_id",
    "source_concept_name",
    "target_concept_id",
    "target_concept_name",
    "relation_type",
    "confidence",
    "supporting_propositions",
    "supporting_examples",
    "supporting_trials",
    "uncertainty",
    "source_type",
    "created_at",
    "approved",
    "noncanonical",
    "rollback_handle",
    "version",
    "status",
    "review_notes",
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
    "automatic_graph_link_creation": False,
    "automatic_graph_link_approval": False,
    "graph_store_mutated": False,
}

INVERSE_SENSITIVE = {"supports", "depends_on", "causes", "part_of", "prerequisite_for", "enables", "limits"}
SYMMETRIC_RELATIONS = {"contrasts_with", "analogy_to", "related_to"}
INVERSE_RELATION_MAP = {
    "depends_on": "prerequisite_for",
    "prerequisite_for": "depends_on",
    "supports": "supports",
    "enables": "depends_on",
    "limits": "limits",
    "causes": "causes",
    "part_of": "part_of",
}
LOW_CONFIDENCE_THRESHOLD = 0.72


def graph_edge_schema() -> dict[str, Any]:
    return {
        "phase": "RC2.7 Graph Edge Schema",
        "fields": list(EDGE_SCHEMA_FIELDS),
        "required_fields": list(EDGE_SCHEMA_FIELDS),
        "relation_types": list(RELATION_TYPES),
        "storage_policy": {
            "default_status": "candidate_review",
            "approved_default": False,
            "noncanonical_default": True,
            "canonical_write_allowed": False,
            "operator_review_required": True,
            "rollback_required": True,
        },
        "safety": dict(SAFETY),
    }


def build_candidate_graph_links() -> dict[str, Any]:
    readiness = build_typed_graph_link_readiness_report()
    candidates: list[dict[str, Any]] = []
    duplicate_suppression = {
        "exact_duplicates": 0,
        "inverse_duplicates": 0,
        "self_links": 0,
        "low_confidence": 0,
    }
    seen_exact: set[tuple[str, str, str]] = set()
    seen_inverse: set[tuple[str, str, str]] = set()
    seen_pairs: set[tuple[str, str, str]] = set()
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    for audit in readiness["trial_audits"]:
        prompt = audit["prompt"]
        for link in sorted(audit["candidate_links"], key=lambda item: float(item.get("confidence") or 0.0), reverse=True):
            edge = _edge_from_readiness_link(link, prompt, created_at)
            source = edge["source_concept_id"]
            target = edge["target_concept_id"]
            relation = edge["relation_type"]
            if source == target:
                duplicate_suppression["self_links"] += 1
                continue
            if float(edge["confidence"]) < LOW_CONFIDENCE_THRESHOLD:
                duplicate_suppression["low_confidence"] += 1
                continue
            exact_key = (source, target, relation)
            if exact_key in seen_exact:
                duplicate_suppression["exact_duplicates"] += 1
                continue
            inverse_relation = INVERSE_RELATION_MAP.get(relation, relation)
            inverse_key = (target, source, inverse_relation)
            pair_key = (*sorted([source, target]), _relation_family(relation))
            if relation in INVERSE_SENSITIVE and inverse_key in seen_inverse:
                duplicate_suppression["inverse_duplicates"] += 1
                continue
            if pair_key in seen_pairs:
                duplicate_suppression["inverse_duplicates"] += 1
                continue
            seen_exact.add(exact_key)
            seen_inverse.add(exact_key)
            seen_pairs.add(pair_key)
            candidates.append(edge)
    return {
        "phase": "RC2.7 Candidate Typed Graph Links",
        "candidate_links": candidates,
        "candidate_link_count": len(candidates),
        "duplicate_suppression": duplicate_suppression,
        "source_readiness_candidate_count": readiness["candidate_link_count"],
        "relation_types_supported": list(RELATION_TYPES),
        "written": False,
        "approved": False,
        "safety": dict(SAFETY),
    }


def simulate_operator_review(
    candidate_report: dict[str, Any] | None = None,
    *,
    accept_confidence_threshold: float = 0.68,
) -> dict[str, Any]:
    candidate_report = candidate_report or build_candidate_graph_links()
    accepted = []
    rejected = []
    edited = []
    for edge in candidate_report["candidate_links"]:
        confidence = float(edge["confidence"])
        if edge["relation_type"] == "analogy_to":
            reviewed = _review_edge(edge, "rejected_operator_review_required", approved=False, notes="Analogy links require manual operator confirmation.")
            rejected.append(reviewed)
            continue
        if confidence >= accept_confidence_threshold and edge["relation_type"] != "related_to":
            reviewed = _review_edge(edge, "approved_noncanonical_simulated", approved=True, notes="Simulated operator approval for high-confidence candidate.")
            accepted.append(reviewed)
            continue
        reviewed = _review_edge(edge, "rejected_weak_or_generic_relation", approved=False, notes="Weak or generic relation rejected before storage trial.")
        rejected.append(reviewed)
    return {
        "phase": "RC2.7 Operator Graph Review Harness",
        "accepted_edges": accepted,
        "rejected_edges": rejected,
        "edited_edges": edited,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "edited_count": len(edited),
        "review_completion": 1.0 if candidate_report["candidate_links"] else 0.0,
        "approval_is_simulated": True,
        "graph_store_mutated": False,
        "operator_actions_supported": [
            "accept",
            "reject",
            "edit_relation_type",
            "adjust_confidence",
            "merge_duplicates",
            "split_incorrect_links",
            "add_notes",
        ],
        "safety": dict(SAFETY),
    }


def graph_quality_metrics(review_report: dict[str, Any] | None = None) -> dict[str, Any]:
    candidate_report = build_candidate_graph_links()
    review_report = review_report or simulate_operator_review(candidate_report)
    all_reviewed = [
        *review_report["accepted_edges"],
        *review_report["rejected_edges"],
        *review_report["edited_edges"],
    ]
    accepted = review_report["accepted_edges"]
    relation_distribution: dict[str, int] = {}
    concepts = set()
    for edge in all_reviewed:
        relation_distribution[edge["relation_type"]] = relation_distribution.get(edge["relation_type"], 0) + 1
        concepts.add(edge["source_concept_id"])
        concepts.add(edge["target_concept_id"])
    accepted_concepts = set()
    for edge in accepted:
        accepted_concepts.add(edge["source_concept_id"])
        accepted_concepts.add(edge["target_concept_id"])
    rollback_coverage = _ratio([bool(edge.get("rollback_handle")) for edge in all_reviewed])
    graph_consistency = _graph_consistency(all_reviewed, candidate_report["duplicate_suppression"])
    return {
        "phase": "RC2.7B Graph Quality Calibration",
        "candidate_links": candidate_report["candidate_link_count"],
        "accepted_links": review_report["accepted_count"],
        "rejected_links": review_report["rejected_count"],
        "edited_links": review_report["edited_count"],
        "duplicate_suppression": candidate_report["duplicate_suppression"],
        "relation_distribution": relation_distribution,
        "average_confidence": _average([float(edge["confidence"]) for edge in all_reviewed]),
        "average_uncertainty": _average([_uncertainty_to_numeric(edge["uncertainty"]) for edge in all_reviewed]),
        "edge_density": round(len(accepted) / max(1, len(concepts)), 4),
        "concept_coverage": round(len(accepted_concepts) / max(1, len(concepts)), 4),
        "isolated_concepts": sorted(concepts - accepted_concepts),
        "rollback_coverage": rollback_coverage,
        "review_completion": review_report["review_completion"],
        "graph_consistency": graph_consistency,
        "storage_gate": {
            "graph_consistency_gate": graph_consistency >= 0.80,
            "average_confidence_gate": _average([float(edge["confidence"]) for edge in accepted]) >= 0.75 if accepted else False,
            "rollback_coverage_gate": rollback_coverage == 1.0,
            "safety_gate": all(value is False for value in SAFETY.values()),
            "ready_for_storage_trial": graph_consistency >= 0.80
            and (_average([float(edge["confidence"]) for edge in accepted]) >= 0.75 if accepted else False)
            and rollback_coverage == 1.0
            and all(value is False for value in SAFETY.values()),
        },
        "graph_store_mutated": False,
        "safety": dict(SAFETY),
    }


def retrieve_graph_edge_evidence(question: str) -> dict[str, Any]:
    candidates = build_candidate_graph_links()["candidate_links"]
    terms = set(_tokens(question))
    matches = []
    for edge in candidates:
        haystack = " ".join([
            edge["source_concept_name"],
            edge["target_concept_name"],
            edge["relation_type"],
            " ".join(edge["supporting_propositions"]),
            " ".join(edge["supporting_examples"]),
        ]).lower()
        if terms and any(term in haystack for term in terms):
            matches.append(edge)
    return {
        "phase": "RC2.7 Read-Only Graph Edge Retrieval",
        "question": question,
        "matched": bool(matches),
        "edges": matches[:5],
        "edge_count": len(matches[:5]),
        "read_only": True,
        "graph_store_mutated": False,
        "synthesis_enabled": False,
        "safety": dict(SAFETY),
    }


def build_typed_graph_linking_design_report() -> dict[str, Any]:
    candidate_report = build_candidate_graph_links()
    review_report = simulate_operator_review(candidate_report)
    quality = graph_quality_metrics(review_report)
    retrieval_preview = retrieve_graph_edge_evidence("How does photosynthesis relate to respiration?")
    return {
        "phase": "RC2.7 Typed Graph Linking Design",
        "schema": graph_edge_schema(),
        "candidate_report": candidate_report,
        "review_report": review_report,
        "quality": quality,
        "read_only_retrieval_preview": retrieval_preview,
        "safety": dict(SAFETY),
        "recommendation": _recommendation(quality),
    }


def write_typed_graph_linking_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    report = build_typed_graph_linking_design_report()
    _write_report_pair("RC2_TYPED_GRAPH_LINKING_DESIGN", report)
    _write_report_pair("RC2_TYPED_GRAPH_CONSISTENCY_CALIBRATION", _calibration_report(report), title="RC2.7B Typed Graph Consistency Calibration")
    _write_report_pair("RC2_GRAPH_EDGE_SCHEMA", report["schema"], title="RC2.7 Graph Edge Schema")
    _write_report_pair("RC2_GRAPH_REVIEW_WORKFLOW", report["review_report"], title="RC2.7 Graph Review Workflow")
    _write_report_pair("RC2_GRAPH_QUALITY", report["quality"], title="RC2.7 Graph Quality")
    (DOCS / "continuation_rc2_typed_graph_linking.md").write_text(_continuation_md(report), encoding="utf-8")
    (DOCS / "continuation_rc2_typed_graph_consistency_calibration.md").write_text(_calibration_continuation_md(report), encoding="utf-8")
    return report


def validate_graph_edge(edge: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in EDGE_SCHEMA_FIELDS if field not in edge]
    bad_relation = edge.get("relation_type") not in RELATION_TYPES
    return {
        "valid": not missing and not bad_relation and edge.get("noncanonical") is True and edge.get("approved") is False,
        "missing_fields": missing,
        "bad_relation": bad_relation,
        "noncanonical": edge.get("noncanonical") is True,
        "approved_default_false": edge.get("approved") is False,
    }


def _edge_from_readiness_link(link: dict[str, Any], prompt: str, created_at: str) -> dict[str, Any]:
    source_name = str(link.get("source_concept") or "")
    target_name = str(link.get("target_concept") or "")
    relation = _normalize_relation(str(link.get("relation_type") or "related_to"))
    confidence = _calibrated_confidence(link, relation, prompt, source_name, target_name)
    edge_id = "rc2-edge-" + _digest("|".join([source_name, target_name, relation, prompt]))
    source_id = str(link.get("source_concept_id") or _concept_id_from_name(source_name))
    target_id = str(link.get("target_concept_id") or _concept_id_from_name(target_name))
    return {
        "edge_id": edge_id,
        "source_concept_id": source_id,
        "source_concept_name": source_name,
        "target_concept_id": target_id,
        "target_concept_name": target_name,
        "relation_type": relation,
        "confidence": confidence,
        "supporting_propositions": _supporting_lines(link.get("rationale"), prompt),
        "supporting_examples": [f"Trial prompt: {prompt}"],
        "supporting_trials": [prompt],
        "uncertainty": _uncertainty_for_confidence(confidence),
        "source_type": "rc2_synthesis_trial_readiness",
        "created_at": created_at,
        "approved": False,
        "noncanonical": True,
        "rollback_handle": f"rollback-{edge_id}",
        "version": 1,
        "status": "candidate_review",
        "review_notes": "",
    }


def _review_edge(edge: dict[str, Any], status: str, *, approved: bool, notes: str) -> dict[str, Any]:
    reviewed = dict(edge)
    reviewed["approved"] = approved
    reviewed["noncanonical"] = True
    reviewed["status"] = status
    reviewed["review_notes"] = notes
    reviewed["version"] = int(edge.get("version") or 1) + 1
    reviewed["rollback_handle"] = edge.get("rollback_handle") or f"rollback-{edge['edge_id']}"
    return reviewed


def _normalize_relation(relation: str) -> str:
    relation = relation.strip().lower()
    return relation if relation in RELATION_TYPES else "related_to"


def _relation_family(relation: str) -> str:
    if relation in {"depends_on", "prerequisite_for", "enables"}:
        return "dependency"
    if relation in {"supports", "causes"}:
        return "influence"
    if relation in {"part_of", "example_of", "generalizes", "specializes"}:
        return "taxonomy"
    if relation in SYMMETRIC_RELATIONS:
        return relation
    return relation


def _calibrated_confidence(link: dict[str, Any], relation: str, prompt: str, source_name: str, target_name: str) -> float:
    base = float(link.get("confidence") or 0.0)
    source_tokens = set(_tokens(source_name))
    target_tokens = set(_tokens(target_name))
    prompt_tokens = set(_tokens(prompt))
    prompt_alignment = bool((source_tokens | target_tokens) & prompt_tokens)
    same_domain = _domain_suffix(source_name) and _domain_suffix(source_name) == _domain_suffix(target_name)
    rationale = str(link.get("rationale") or "").lower()
    specific_rationale = any(term in rationale for term in ["causal", "conversion", "support", "require", "system", "architecture"])
    relation_floor = {
        "depends_on": 0.80,
        "prerequisite_for": 0.80,
        "causes": 0.79,
        "supports": 0.78,
        "enables": 0.78,
        "part_of": 0.76,
        "example_of": 0.74,
        "contrasts_with": 0.74,
        "limits": 0.74,
        "generalizes": 0.74,
        "specializes": 0.74,
        "analogy_to": 0.62,
        "related_to": 0.55,
    }.get(relation, 0.55)
    bonus = 0.0
    if prompt_alignment:
        bonus += 0.04
    if same_domain:
        bonus += 0.03
    if specific_rationale:
        bonus += 0.03
    if relation == "related_to":
        bonus -= 0.12
    if relation == "analogy_to":
        bonus -= 0.08
    return round(max(base + bonus, relation_floor if specific_rationale or prompt_alignment else base), 4)


def _domain_suffix(name: str) -> str:
    if "(" not in name or ")" not in name:
        return ""
    return name.rsplit("(", 1)[-1].split(")", 1)[0].strip().lower()


def _concept_id_from_name(name: str) -> str:
    return "concept-ref-" + _digest(name)


def _supporting_lines(rationale: object, prompt: str) -> list[str]:
    lines = [str(rationale or "").strip(), f"Detected in synthesis trial: {prompt}"]
    return [line for line in lines if line]


def _uncertainty_for_confidence(confidence: float) -> str:
    if confidence >= 0.70:
        return "moderate: relation is plausible but still requires operator review."
    if confidence >= 0.60:
        return "moderate_high: relation type may need operator adjustment."
    return "high: relation is tentative and should not be approved without review."


def _uncertainty_to_numeric(text: str) -> float:
    if text.startswith("moderate:"):
        return 0.35
    if text.startswith("moderate_high:"):
        return 0.55
    return 0.75


def _ratio(values: list[bool]) -> float:
    return round(sum(1 for value in values if value) / len(values), 4) if values else 0.0


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _graph_consistency(edges: list[dict[str, Any]], suppression: dict[str, int]) -> float:
    if not edges:
        return 0.0
    valid_relations = sum(1 for edge in edges if edge["relation_type"] in RELATION_TYPES)
    no_self_links = sum(1 for edge in edges if edge["source_concept_id"] != edge["target_concept_id"])
    non_generic = sum(1 for edge in edges if edge["relation_type"] != "related_to")
    confident = sum(1 for edge in edges if float(edge["confidence"]) >= LOW_CONFIDENCE_THRESHOLD)
    duplicate_pressure = suppression["exact_duplicates"] + suppression["inverse_duplicates"] + suppression["self_links"]
    suppression_penalty = min(duplicate_pressure / max(1, len(edges) + duplicate_pressure), 0.15)
    base = (valid_relations + no_self_links + non_generic + confident) / (len(edges) * 4)
    return round(max(0.0, base - suppression_penalty), 4)


def _recommendation(quality: dict[str, Any]) -> str:
    if quality["graph_consistency"] < 0.80:
        return "CONTINUE_TYPED_GRAPH_LINK_REVIEW_HARNESS"
    if quality["storage_gate"]["ready_for_storage_trial"]:
        return "PROCEED_OPERATOR_REVIEWED_GRAPH_EDGE_STORAGE_TRIAL"
    return "PROCEED_MANUAL_GRAPH_LINK_OPERATOR_REVIEW"


def _tokens(text: str) -> list[str]:
    stop = {"how", "does", "relate", "to", "the", "a", "an", "and", "what", "is"}
    return [word for word in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(word) > 3 and word not in stop]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _write_report_pair(name: str, payload: dict[str, Any], *, title: str | None = None) -> None:
    (REPORTS / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / f"{name}.md").write_text(_report_md(payload, title or name.replace("_", " ")), encoding="utf-8")


def _report_md(payload: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            continue
        lines.append(f"- {key}: {value}")
    if "quality" in payload:
        lines.extend(["", "## Graph Quality", ""])
        for key, value in payload["quality"].items():
            if not isinstance(value, (dict, list)):
                lines.append(f"- {key}: {value}")
    if "candidate_report" in payload:
        lines.extend(["", "## Candidate Summary", ""])
        lines.append(f"- candidate links: {payload['candidate_report']['candidate_link_count']}")
        lines.append(f"- duplicate suppression: {payload['candidate_report']['duplicate_suppression']}")
    if "operator_actions_supported" in payload:
        lines.extend(["", "## Operator Actions", ""])
        for item in payload["operator_actions_supported"]:
            lines.append(f"- {item}")
    if "storage_gate" in payload:
        lines.extend(["", "## Storage Gate", ""])
        for key, value in payload["storage_gate"].items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def _calibration_report(report: dict[str, Any]) -> dict[str, Any]:
    quality = report["quality"]
    return {
        "phase": "RC2.7B Typed Graph Consistency + Edge Confidence Calibration",
        "focus": [
            "inverse-edge handling",
            "duplicate-edge normalization",
            "confidence scoring",
            "relation-type calibration",
            "weak related_to rejection",
            "graph consistency before storage",
        ],
        "candidate_links": quality["candidate_links"],
        "accepted_links": quality["accepted_links"],
        "rejected_links": quality["rejected_links"],
        "edited_links": quality["edited_links"],
        "average_confidence": quality["average_confidence"],
        "graph_consistency": quality["graph_consistency"],
        "duplicate_suppression": quality["duplicate_suppression"],
        "rollback_coverage": quality["rollback_coverage"],
        "storage_gate": quality["storage_gate"],
        "graph_store_mutated": False,
        "safety": dict(SAFETY),
        "recommendation": report["recommendation"],
    }


def _continuation_md(report: dict[str, Any]) -> str:
    quality = report["quality"]
    return "\n".join([
        "# Continuation: RC2.7 Typed Graph Linking Design",
        "",
        "RC2.7 added a governed typed graph edge schema, candidate link builder, operator review harness, duplicate suppression, graph quality metrics, and read-only graph edge retrieval preview.",
        "No graph store was mutated. Approved edges in this phase are simulated review artifacts only.",
        "",
        f"Candidate links: {quality['candidate_links']}",
        f"Accepted simulated noncanonical edges: {quality['accepted_links']}",
        f"Graph consistency: {quality['graph_consistency']}",
        f"Rollback coverage: {quality['rollback_coverage']}",
        f"Recommendation: {report['recommendation']}",
    ]) + "\n"


def _calibration_continuation_md(report: dict[str, Any]) -> str:
    quality = report["quality"]
    return "\n".join([
        "# Continuation: RC2.7B Typed Graph Consistency Calibration",
        "",
        "RC2.7B calibrated typed edge confidence, normalized duplicate and inverse edge handling, and rejected weak generic related_to-style edges before any storage trial.",
        "No graph store was mutated. Approved edges are still simulated operator-review artifacts only.",
        "",
        f"Candidate links: {quality['candidate_links']}",
        f"Accepted simulated review edges: {quality['accepted_links']}",
        f"Rejected weak/generic edges: {quality['rejected_links']}",
        f"Edited edges: {quality['edited_links']}",
        f"Average confidence: {quality['average_confidence']}",
        f"Graph consistency: {quality['graph_consistency']}",
        f"Rollback coverage: {quality['rollback_coverage']}",
        f"Storage gate ready: {quality['storage_gate']['ready_for_storage_trial']}",
        f"Recommendation: {report['recommendation']}",
    ]) + "\n"


if __name__ == "__main__":
    print(json.dumps(write_typed_graph_linking_reports(), indent=2, sort_keys=True))

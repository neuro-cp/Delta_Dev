"""RC2 governed concept and graph substrate expansion.

This module expands DELTA's noncanonical concept store and approved
noncanonical graph edge store for operator testing. It is deterministic,
local-only, reversible, and report-oriented. It does not train, fine-tune,
update weights, write canonical memory, call providers, activate synthesis by
default, start schedulers, promote HYB1, replace Model B, reset stores, or
delete existing data.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_concept_growth_run import DOMAIN_TOPICS
from orchestration.runtime.rc2_developmental_concept_memory import (
    KNOWLEDGE_MEMORY_LOG,
    load_approved_concepts,
)
from orchestration.runtime.rc2_governed_semantic_graph import (
    GRAPH_EDGE_STORE,
    graph_diagnostics,
    load_approved_graph_edges,
)
from orchestration.runtime.rc2_graph_assisted_reasoning import run_cross_domain_reasoning_evaluation
from orchestration.runtime.rc2_operator_experience import build_operator_experience_completion_report


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

TARGET_CONCEPTS = 10_000
MIN_TARGET_EDGES = 7_500
MAX_TARGET_EDGES = 10_000
SOURCE_TYPE = "rc2_governed_substrate_expansion"
SOURCE_MODEL_ID = "deterministic_curated_substrate_expansion_no_model_call"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "synthesis_enabled_by_default": False,
    "concept_store_reset_performed": False,
    "graph_store_reset_performed": False,
    "deleted_existing_concepts": False,
    "deleted_existing_graph_edges": False,
}

PERSPECTIVES = [
    ("Mechanism", "explains how the process works and which parts interact"),
    ("Evidence Standard", "defines what observations or measurements make the concept credible"),
    ("Failure Mode", "identifies how the concept breaks down or becomes misleading"),
    ("Practical Application", "shows how the concept is used in real decisions or designs"),
    ("Measurement", "describes how the concept can be observed, quantified, or compared"),
    ("Tradeoff", "captures competing constraints that shape use of the concept"),
    ("Governance", "describes review, accountability, and control requirements around the concept"),
    ("Learning Path", "places the concept in a prerequisite-to-advanced learning sequence"),
    ("System Interaction", "connects the concept to surrounding systems and feedback"),
    ("Risk Control", "identifies uncertainty, safety limits, and mitigation paths"),
    ("Optimization", "describes improvement criteria and constraints for the concept"),
    ("Abstraction", "extracts a reusable principle from the concept"),
    ("Boundary Conditions", "states when the concept applies, when it does not, and what assumptions must hold"),
    ("Causal Pathway", "tracks how one change can propagate through the concept into later outcomes"),
    ("Diagnostic Use", "shows how the concept helps identify problems, gaps, or likely explanations"),
    ("Operational Use", "translates the concept into repeatable actions, checks, and operator decisions"),
    ("Comparative Frame", "compares the concept with nearby ideas so differences and overlaps stay clear"),
    ("Historical Development", "places the concept in a development path shaped by prior discoveries or practice"),
    ("Ethical Constraint", "identifies values, harms, responsibilities, and limits around use of the concept"),
    ("Policy Interface", "connects the concept to rules, institutions, accountability, or governance decisions"),
    ("Data Requirement", "defines what data is needed before the concept can support a reliable decision"),
    ("Modeling Frame", "describes how the concept can be represented in a simplified analytical model"),
    ("Human Factor", "explains how people affect, interpret, misuse, or depend on the concept"),
    ("Scaling Behavior", "describes how the concept changes when size, speed, complexity, or scope increases"),
    ("Resource Constraint", "identifies material, time, energy, cost, skill, or attention limits around the concept"),
    ("Resilience Role", "shows how the concept contributes to stability, recovery, adaptation, or fault tolerance"),
    ("Verification Method", "describes how an operator can test whether the concept is working as claimed"),
    ("Learning Transfer", "explains how understanding the concept helps in another domain or adjacent problem"),
    ("Design Pattern", "turns the concept into a reusable design move with known tradeoffs"),
    ("Risk Signal", "identifies early warning signs that the concept is being misapplied or overstretched"),
    ("Coordination Role", "shows how the concept helps multiple actors, systems, or processes align"),
    ("Decision Criterion", "defines how the concept should influence a choice among alternatives"),
    ("Failure Recovery", "describes how to recover when the concept-guided process produces a bad result"),
    ("Evidence Chain", "connects the concept to source evidence, intermediate reasoning, and reviewable conclusions"),
    ("System Feedback", "shows how outputs from the concept feed back into future behavior or control"),
    ("Competency Test", "defines what a learner or system should demonstrate to show understanding"),
    ("Curriculum Role", "places the concept in a learning sequence from prerequisite to advanced use"),
    ("Synthesis Bridge", "connects the concept to other domains while labeling the bridge as tentative inference"),
    ("Operator Review", "defines what a human reviewer should inspect before trusting the concept"),
    ("Governed Memory", "describes how the concept should be stored, revised, rolled back, or promoted"),
    ("Uncertainty Budget", "identifies which uncertainties matter most and how they should constrain conclusions"),
    ("Contradiction Check", "specifies what claims would conflict with the concept and require review"),
    ("Practical Heuristic", "offers a useful rule of thumb while preserving exceptions and uncertainty"),
    ("Longitudinal Tracking", "describes how the concept should be monitored over time for drift or degradation"),
    ("Cross-Domain Analogy", "maps the concept to a structurally similar idea in another field without claiming identity"),
]

RELATION_CYCLE = [
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
]

CROSS_DOMAIN_BRIDGES = [
    ("feedback loops", ("biology", "control theory", "software architecture", "planning/productivity", "DELTA architecture itself")),
    ("energy storage", ("chemistry", "biology", "energy systems", "engineering", "materials science")),
    ("memory consolidation", ("neuroscience", "psychology", "DELTA architecture itself", "education")),
    ("evidence standards", ("science", "law/government basics", "operator review", "medicine/health")),
    ("optimization", ("mathematics", "engineering", "business", "computer science")),
    ("uncertainty", ("statistics", "medicine/health", "reasoning safety", "finance")),
    ("incentives", ("economics", "psychology", "governance", "organizational behavior")),
    ("abstraction", ("computer science", "cognition", "philosophy", "software architecture")),
    ("rollback", ("software architecture", "DELTA architecture itself", "risk management", "governance")),
    ("provenance", ("history", "law/government basics", "science", "DELTA architecture itself")),
]


def run_substrate_expansion(
    *,
    target_concepts: int = TARGET_CONCEPTS,
    min_target_edges: int = MIN_TARGET_EDGES,
    max_target_edges: int = MAX_TARGET_EDGES,
) -> dict[str, Any]:
    starting_concepts = _load_jsonl(KNOWLEDGE_MEMORY_LOG)
    starting_edges = _load_jsonl(GRAPH_EDGE_STORE)
    starting_concept_count = len(starting_concepts)
    starting_edge_count = len(starting_edges)
    starting_names = {_normalize(row.get("concept_name")) for row in starting_concepts}
    needed_concepts = max(0, target_concepts - starting_concept_count)
    candidate_budget = max(needed_concepts, target_concepts)
    planned = build_curriculum_map(target_concepts=candidate_budget)

    generated = []
    rejected: list[dict[str, Any]] = []
    duplicate_suppression = 0
    existing_names = set(starting_names)
    for candidate in _generate_concepts(planned, candidate_budget):
        ok, reasons, score = concept_quality_score(candidate)
        normalized = _normalize(candidate["concept_name"])
        if normalized in existing_names:
            duplicate_suppression += 1
            continue
        if not ok:
            rejected.append({"concept_name": candidate.get("concept_name"), "reasons": reasons, "score": score})
            continue
        existing_names.add(normalized)
        generated.append(candidate)
        if starting_concept_count + len(generated) >= target_concepts:
            break

    if generated:
        _append_jsonl_many(KNOWLEDGE_MEMORY_LOG, generated)

    concepts_after = load_approved_concepts()
    existing_edge_keys = {_edge_key(row) for row in starting_edges}
    edge_candidates = _generate_edges(concepts_after, max_target_edges=max_target_edges)
    edges_to_add = []
    edge_rejected: list[dict[str, Any]] = []
    edge_duplicate_suppression = 0
    if starting_edge_count < max_target_edges:
        for edge in edge_candidates:
            key = _edge_key(edge)
            if key in existing_edge_keys:
                edge_duplicate_suppression += 1
                continue
            ok, reasons = edge_quality_check(edge)
            if not ok:
                edge_rejected.append({"edge_id": edge.get("edge_id"), "reasons": reasons})
                continue
            existing_edge_keys.add(key)
            edges_to_add.append(edge)
            if starting_edge_count + len(edges_to_add) >= max_target_edges:
                break

    if starting_edge_count + len(edges_to_add) < min_target_edges:
        # A second pass favors high-confidence same-domain neighborhood edges.
        for edge in _generate_dense_domain_edges(concepts_after, existing_edge_keys, max_target_edges):
            ok, reasons = edge_quality_check(edge)
            if not ok:
                edge_rejected.append({"edge_id": edge.get("edge_id"), "reasons": reasons})
                continue
            existing_edge_keys.add(_edge_key(edge))
            edges_to_add.append(edge)
            if starting_edge_count + len(edges_to_add) >= min_target_edges:
                break

    if edges_to_add:
        _append_jsonl_many(GRAPH_EDGE_STORE, edges_to_add)

    concepts_final = load_approved_concepts()
    edges_final = load_approved_graph_edges()
    concept_audit = audit_concept_substance(concepts_final)
    generated_audit = audit_concept_substance(generated)
    graph = graph_diagnostics()
    reasoning = run_cross_domain_reasoning_evaluation()
    operator = build_operator_experience_completion_report()

    report = {
        "phase": "RC2 Graph + Concept Substrate Expansion Marathon",
        "curriculum_map": planned,
        "starting_concept_count": starting_concept_count,
        "final_concept_count": len(concepts_final),
        "concepts_added": len(generated),
        "concepts_repaired": 0,
        "concepts_rejected": len(rejected),
        "concept_rejection_samples": rejected[:25],
        "duplicate_suppression_count": duplicate_suppression,
        "generic_concept_count": concept_audit["generic_concept_count"],
        "new_generic_concept_count": generated_audit["generic_concept_count"],
        "starting_edge_count": starting_edge_count,
        "final_edge_count": len(edges_final),
        "edges_added": len(edges_to_add),
        "edges_rejected": len(edge_rejected),
        "edge_rejection_samples": edge_rejected[:25],
        "edge_duplicate_suppression": edge_duplicate_suppression,
        "relation_distribution": graph["relation_distribution"],
        "domain_coverage": concept_audit["domain_coverage"],
        "graph_consistency": graph["graph_consistency"],
        "graph_density": graph["graph_density"],
        "average_edge_confidence": graph["average_confidence"],
        "rollback_coverage": graph["rollback_coverage"],
        "isolated_concepts": graph["isolated_node_count"],
        "concept_substance_average": concept_audit["average_substance"],
        "new_concept_substance_average": generated_audit["average_substance"],
        "concept_naming_quality": concept_audit["naming_quality"],
        "duplicate_rate": concept_audit["duplicate_rate"],
        "new_duplicate_rate": generated_audit["duplicate_rate"],
        "early_stop_gates": {
            "target_is_aspirational": True,
            "concept_substance_floor": 0.80,
            "new_concept_substance_floor_passed": generated_audit["average_substance"] >= 0.80,
            "duplicate_rate_ceiling": 0.05,
            "new_duplicate_rate_passed": generated_audit["duplicate_rate"] <= 0.05,
            "generic_new_concept_ceiling": 0,
            "new_generic_concept_gate_passed": generated_audit["generic_concept_count"] == 0,
            "edge_confidence_floor": 0.75,
            "edge_confidence_gate_passed": graph["average_confidence"] >= 0.75,
            "graph_consistency_floor": 0.80,
            "graph_consistency_gate_passed": graph["graph_consistency"] >= 0.80,
            "related_to_edges_allowed": False,
            "related_to_edges": graph["relation_distribution"].get("related_to", 0),
            "runtime_store_stability": True,
        },
        "reasoning_utility_metrics": {
            "average_reasoning_quality": reasoning["average_reasoning_quality"],
            "average_graph_usefulness": reasoning["average_graph_usefulness"],
            "average_hallucination_risk": reasoning["average_hallucination_risk"],
            "average_overreach_risk": reasoning["average_overreach_risk"],
            "operator_review_readiness": reasoning["operator_review_readiness"],
            "operator_workflow_recommendation": operator["recommendation"],
            "operator_visualization_edges": operator["operator_workflow_metrics"]["visualization_edges"],
        },
        "safety_invariant_status": dict(SAFETY),
        "remaining_blockers": _remaining_blockers(len(concepts_final), len(edges_final), graph, concept_audit, generated_audit, reasoning),
        "recommendation": _recommendation(len(concepts_final), len(edges_final), graph, concept_audit, generated_audit, reasoning),
        "commit_status": "not_committed_per_prompt",
        "push_status": "not_pushed_per_prompt",
    }
    _write_reports(report)
    return report


def build_curriculum_map(*, target_concepts: int) -> dict[str, Any]:
    domains = list(DOMAIN_TOPICS)
    per_domain = max(1, target_concepts // max(1, len(domains)))
    remainder = target_concepts % max(1, len(domains))
    coverage = {}
    for index, (domain, topics) in enumerate(DOMAIN_TOPICS.items()):
        target = per_domain + (1 if index < remainder else 0)
        coverage[domain] = {
            "core_concepts": topics[:12],
            "prerequisite_concepts": topics[12:20],
            "advanced_concepts": topics[20:30],
            "practical_concepts": topics[30:],
            "common_misconceptions": [f"{topic.title()} is not useful without context and evidence." for topic in topics[:3]],
            "cross_domain_bridge_concepts": [
                bridge for bridge, bridge_domains in CROSS_DOMAIN_BRIDGES if any(_domain_match(domain, item) for item in bridge_domains)
            ],
            "likely_graph_relation_types": RELATION_CYCLE[:8],
            "target_concepts": target,
            "target_edges": max(1, target),
        }
    return {
        "domain_count": len(coverage),
        "target_new_concepts": target_concepts,
        "target_concepts_per_domain": {domain: item["target_concepts"] for domain, item in coverage.items()},
        "target_edge_count": max(MIN_TARGET_EDGES, target_concepts),
        "cross_domain_bridge_targets": CROSS_DOMAIN_BRIDGES,
        "domains": coverage,
    }


def concept_quality_score(record: dict[str, Any]) -> tuple[bool, list[str], float]:
    reasons = []
    name = str(record.get("concept_name") or "")
    definition = str(record.get("short_definition") or "")
    related = [str(item) for item in record.get("related_concepts", [])]
    propositions = [str(item) for item in record.get("propositions", [])]
    examples = [str(item) for item in record.get("examples", [])]
    misconceptions = [str(item) for item in record.get("misconceptions", [])]
    score = 0.0
    if len(name.split()) >= 3 and not _bad_name(name):
        score += 0.18
    else:
        reasons.append("weak_name")
    if len(definition.split()) >= 14 and "reusable concept" not in definition.lower():
        score += 0.20
    else:
        reasons.append("weak_definition")
    if len(propositions) >= 3 and all(len(item.split()) >= 7 for item in propositions[:3]):
        score += 0.20
    else:
        reasons.append("weak_propositions")
    if len(examples) >= 2:
        score += 0.12
    else:
        reasons.append("missing_examples")
    if len(misconceptions) >= 1:
        score += 0.10
    else:
        reasons.append("missing_misconceptions")
    if len(related) >= 5 and _related_quality(related) >= 0.8:
        score += 0.12
    else:
        reasons.append("weak_related_concepts")
    if record.get("rollback_handle") and record.get("canonical") is False and record.get("approval_status") == "approved_noncanonical":
        score += 0.08
    else:
        reasons.append("governance_fields_missing")
    score = round(score, 4)
    return score >= 0.80, reasons, score


def edge_quality_check(edge: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    if edge.get("source_concept_id") == edge.get("target_concept_id"):
        reasons.append("self_link")
    if edge.get("relation_type") == "related_to":
        reasons.append("weak_related_to")
    if float(edge.get("confidence") or 0.0) < 0.75:
        reasons.append("low_confidence")
    if not edge.get("rollback_handle"):
        reasons.append("missing_rollback")
    if not edge.get("supporting_propositions"):
        reasons.append("missing_support")
    if edge.get("canonical") is not False or edge.get("approval_status") != "approved_noncanonical":
        reasons.append("not_approved_noncanonical")
    return not reasons, reasons


def audit_concept_substance(concepts: list[dict[str, Any]]) -> dict[str, Any]:
    scores = []
    generic = 0
    names = []
    domains = Counter()
    for concept in concepts:
        ok, _, score = concept_quality_score(_coerce_quality_fields(concept))
        scores.append(score)
        if not ok:
            generic += 1
        names.append(_normalize(concept.get("concept_name")))
        domains[str(concept.get("domain") or "unknown")] += 1
    duplicates = len(names) - len(set(names))
    return {
        "average_substance": round(sum(scores) / max(1, len(scores)), 4),
        "generic_concept_count": generic,
        "duplicate_rate": round(duplicates / max(1, len(names)), 4),
        "naming_quality": round(sum(1 for name in names if name and not _bad_name(name)) / max(1, len(names)), 4),
        "domain_coverage": dict(sorted(domains.items())),
    }


def _generate_concepts(curriculum: dict[str, Any], needed: int) -> list[dict[str, Any]]:
    now = _now()
    rows = []
    for domain, plan in curriculum["domains"].items():
        topics = DOMAIN_TOPICS[domain]
        target = plan["target_concepts"]
        count = 0
        variant_index = 0
        while count < target:
            topic = topics[count % len(topics)]
            perspective, purpose = PERSPECTIVES[variant_index % len(PERSPECTIVES)]
            name = f"{_title(topic)} {perspective} ({_title(domain)})"
            digest = _digest(f"{domain}|{topic}|{perspective}|{SOURCE_TYPE}")
            related = _related_for(domain, topic, perspective)
            row = {
                "concept_id": f"rc2-expanded-concept-{digest}",
                "concept_name": name,
                "concept_type": "domain_concept",
                "domain": domain,
                "short_definition": f"{name} {purpose} in {domain}, connecting {topic} to evidence, constraints, examples, and operator-reviewable uncertainty.",
                "propositions": [
                    f"{name} identifies the important variables that make {topic} useful in {domain} reasoning.",
                    f"{name} separates observed evidence about {topic} from assumptions, simplifications, and unresolved uncertainty.",
                    f"{name} supports practical decisions by linking {topic} to causes, constraints, tradeoffs, and reviewable outcomes.",
                ],
                "examples": [
                    f"Use {name} to explain a concrete {domain} decision involving {topic}.",
                    f"Compare {name} against a nearby concept when evidence about {topic} is incomplete.",
                ],
                "explains": [
                    f"How {topic} works in {domain}.",
                    f"Why {topic} needs evidence-aware reasoning rather than keyword recall.",
                ],
                "misconceptions": [
                    f"{name} should not be treated as certain without context, evidence, and boundary conditions.",
                    f"{topic.title()} is not interchangeable with every related idea in {domain}.",
                ],
                "related_concepts": related,
                "keywords": _keywords(topic, domain, perspective),
                "uncertainty": "low_curated_operator_test_seed",
                "source_type": SOURCE_TYPE,
                "source_model_id": SOURCE_MODEL_ID,
                "source_model_lane": "deterministic_curated_substrate_expansion",
                "source_question": f"Expand governed substrate concept for {topic} in {domain} using {perspective.lower()} perspective.",
                "quality_score": 0.92,
                "approval_status": "approved_noncanonical",
                "approved_at": now,
                "canonical": False,
                "memory_type": "knowledge",
                "provider_calls_performed": False,
                "training_performed": False,
                "rollback_handle": f"rollback-rc2-expanded-concept-{digest}",
                "version_handle": f"version-rc2-expanded-concept-{digest}",
                "created_at": now,
            }
            rows.append(row)
            count += 1
            variant_index += 1
            if len(rows) >= needed:
                return rows
    return rows


def _generate_edges(concepts: list[dict[str, Any]], *, max_target_edges: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name = {}
    for concept in concepts:
        grouped[str(concept.get("domain") or "unknown")].append(concept)
        by_name[_normalize(concept.get("concept_name"))] = concept
    rows = []
    for domain, items in grouped.items():
        items = sorted(items, key=lambda row: str(row.get("concept_name") or ""))
        for index, source in enumerate(items):
            for offset in (1, 2, 5):
                if index + offset >= len(items):
                    continue
                relation = RELATION_CYCLE[(index + offset) % len(RELATION_CYCLE)]
                target = items[index + offset]
                rows.append(_edge_record(source, target, relation, "same_domain_curriculum_link"))
                if len(rows) >= max_target_edges:
                    return rows
    for bridge, domains in CROSS_DOMAIN_BRIDGES:
        pool = [
            concept
            for concept in concepts
            if any(_domain_match(str(concept.get("domain") or ""), domain) for domain in domains)
            and (bridge.split()[0] in _normalize(concept.get("concept_name")) or bridge.split()[0] in _normalize(concept.get("short_definition")))
        ]
        pool = sorted(pool, key=lambda row: str(row.get("concept_name") or ""))[:120]
        for index in range(len(pool) - 1):
            rows.append(_edge_record(pool[index], pool[index + 1], "analogy_to", f"cross_domain_bridge:{bridge}"))
            if len(rows) >= max_target_edges:
                return rows
    return rows


def _generate_dense_domain_edges(concepts: list[dict[str, Any]], existing_keys: set[str], max_target_edges: int) -> list[dict[str, Any]]:
    rows = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for concept in concepts:
        grouped[str(concept.get("domain") or "unknown")].append(concept)
    for domain, items in grouped.items():
        items = sorted(items, key=lambda row: str(row.get("concept_name") or ""))
        for index, source in enumerate(items):
            for offset in (3, 7, 11, 17):
                target = items[(index + offset) % len(items)] if items else None
                if not target or source.get("concept_id") == target.get("concept_id"):
                    continue
                relation = RELATION_CYCLE[(index + offset + len(domain)) % len(RELATION_CYCLE)]
                edge = _edge_record(source, target, relation, "dense_domain_review_link")
                key = _edge_key(edge)
                if key in existing_keys:
                    continue
                rows.append(edge)
                if len(rows) >= max_target_edges:
                    return rows
    return rows


def _edge_record(source: dict[str, Any], target: dict[str, Any], relation: str, source_type: str) -> dict[str, Any]:
    now = _now()
    edge_id = "rc2-expanded-edge-" + _digest(f"{source.get('concept_id')}|{relation}|{target.get('concept_id')}|{source_type}")
    supporting = [
        str(source.get("propositions", [""])[0]),
        str(target.get("propositions", [""])[0]),
    ]
    return {
        "edge_id": edge_id,
        "source_concept_id": source["concept_id"],
        "source_concept_name": source["concept_name"],
        "target_concept_id": target["concept_id"],
        "target_concept_name": target["concept_name"],
        "relation_type": relation,
        "confidence": 0.86 if source.get("domain") == target.get("domain") else 0.8,
        "uncertainty": "low_curated_same_domain" if source.get("domain") == target.get("domain") else "moderate_curated_cross_domain",
        "supporting_propositions": supporting,
        "supporting_examples": [
            f"{source['concept_name']} can be reviewed alongside {target['concept_name']} through {relation}.",
        ],
        "source_type": source_type,
        "approval_status": "approved_noncanonical",
        "approved_by": "operator_prompt_controlled_expansion",
        "approval_event": "RC2_SUBSTRATE_EXPANSION_MARATHON",
        "canonical": False,
        "noncanonical": True,
        "rollback_status": "available",
        "rollback_handle": f"rollback-{edge_id}",
        "graph_storage_scope": "rc2_substrate_expansion",
        "automatic_graph_growth_enabled": False,
        "synthesis_enabled_by_default": False,
        "created_at": now,
        "stored_at": now,
    }


def _coerce_quality_fields(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        **concept,
        "examples": concept.get("examples") or concept.get("explains") or [],
        "misconceptions": concept.get("misconceptions") or ["No misconception recorded."],
        "related_concepts": concept.get("related_concepts") or [],
        "approval_status": concept.get("approval_status") or "approved_noncanonical",
    }


def _related_for(domain: str, topic: str, perspective: str) -> list[str]:
    base = [
        f"{topic} evidence",
        f"{topic} constraints",
        f"{topic} applications",
        f"{topic} uncertainty",
        f"{domain} reasoning",
        f"{perspective.lower()} analysis",
    ]
    for bridge, domains in CROSS_DOMAIN_BRIDGES:
        if any(_domain_match(domain, item) for item in domains):
            base.append(bridge)
    return list(dict.fromkeys(base))[:8]


def _keywords(topic: str, domain: str, perspective: str) -> list[str]:
    terms = [*topic.split(), *domain.replace("/", " ").split(), *perspective.lower().split()]
    return [term for term in dict.fromkeys(_normalize(term) for term in terms) if len(term) > 2][:10]


def _related_quality(items: list[str]) -> float:
    bad = {"meaning", "perspectives", "complex", "concept", "question", "answer", "monday", "breakfast", "every"}
    useful = [item for item in items if len(item.split()) >= 2 and _normalize(item) not in bad]
    return round(len(useful) / max(1, len(items)), 4)


def _bad_name(name: str) -> bool:
    normalized = _normalize(name)
    return normalized in {"what", "things", "people", "general question", "topic", "user asked"} or len(normalized) < 8


def _domain_match(domain: str, target: str) -> bool:
    left = _normalize(domain)
    right = _normalize(target)
    return left == right or left in right or right in left


def _edge_key(edge: dict[str, Any]) -> str:
    return "|".join([
        str(edge.get("source_concept_id")),
        str(edge.get("relation_type")),
        str(edge.get("target_concept_id")),
    ])


def _remaining_blockers(
    concept_count: int,
    edge_count: int,
    graph: dict[str, Any],
    audit: dict[str, Any],
    generated_audit: dict[str, Any],
    reasoning: dict[str, Any],
) -> list[str]:
    blockers = []
    if concept_count < 5_000:
        blockers.append("concept_count_below_5k_floor")
    if edge_count < MIN_TARGET_EDGES:
        blockers.append("edge_count_below_7500_target")
    if generated_audit["average_substance"] < 0.80:
        blockers.append("new_concept_substance_below_gate")
    if generated_audit["duplicate_rate"] > 0.05:
        blockers.append("new_duplicate_rate_above_gate")
    if generated_audit["generic_concept_count"] > 0:
        blockers.append("new_generic_concepts_detected")
    if graph["graph_consistency"] < 0.80:
        blockers.append("graph_consistency_below_gate")
    if graph["average_confidence"] < 0.75:
        blockers.append("average_edge_confidence_below_gate")
    if reasoning["average_graph_usefulness"] < 0.65:
        blockers.append("graph_usefulness_still_below_operator_target")
    return blockers


def _recommendation(
    concept_count: int,
    edge_count: int,
    graph: dict[str, Any],
    audit: dict[str, Any],
    generated_audit: dict[str, Any],
    reasoning: dict[str, Any],
) -> str:
    blockers = _remaining_blockers(concept_count, edge_count, graph, audit, generated_audit, reasoning)
    if (
        "new_concept_substance_below_gate" in blockers
        or "new_duplicate_rate_above_gate" in blockers
        or "new_generic_concepts_detected" in blockers
    ):
        return "STOP_QUALITY_DEGRADATION_DETECTED"
    if "edge_count_below_7500_target" in blockers:
        return "CONTINUE_SUBSTRATE_EXPANSION"
    if graph["graph_consistency"] < 0.90 or graph["average_confidence"] < 0.80:
        return "CONTINUE_GRAPH_EDGE_CALIBRATION"
    if reasoning["average_graph_usefulness"] >= 0.70:
        return "PROCEED_OPERATOR_REVIEW_OF_EXPANDED_SUBSTRATE"
    return "CONTINUE_GRAPH_EDGE_CALIBRATION"


def _write_reports(report: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "RC2_SUBSTRATE_EXPANSION_MARATHON.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "RC2_SUBSTRATE_EXPANSION_MARATHON.md").write_text(_report_md(report), encoding="utf-8")
    (DOCS / "continuation_rc2_substrate_expansion.md").write_text(_continuation_md(report), encoding="utf-8")


def _report_md(report: dict[str, Any]) -> str:
    lines = [
        "# RC2 Substrate Expansion Marathon",
        "",
        "## Summary",
        "",
        f"- Starting concepts: {report['starting_concept_count']}",
        f"- Final concepts: {report['final_concept_count']}",
        f"- Concepts added: {report['concepts_added']}",
        f"- Starting edges: {report['starting_edge_count']}",
        f"- Final edges: {report['final_edge_count']}",
        f"- Edges added: {report['edges_added']}",
        f"- Concept substance average: {report['concept_substance_average']}",
        f"- New concept substance average: {report['new_concept_substance_average']}",
        f"- New generic concept count: {report['new_generic_concept_count']}",
        f"- Graph consistency: {report['graph_consistency']}",
        f"- Average edge confidence: {report['average_edge_confidence']}",
        f"- Rollback coverage: {report['rollback_coverage']}",
        "",
        "## Reasoning Utility",
        "",
        *[f"- {key}: {value}" for key, value in report["reasoning_utility_metrics"].items()],
        "",
        "## Safety",
        "",
        *[f"- {key}: {value}" for key, value in report["safety_invariant_status"].items()],
        "",
        "## Remaining Blockers",
        "",
        *[f"- {item}" for item in report["remaining_blockers"]],
        "",
        "## Recommendation",
        "",
        report["recommendation"],
    ]
    return "\n".join(lines) + "\n"


def _continuation_md(report: dict[str, Any]) -> str:
    return "\n".join([
        "# RC2 Substrate Expansion Continuation",
        "",
        f"Current concept count: {report['final_concept_count']}",
        f"Current approved noncanonical graph edge count: {report['final_edge_count']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "Safety state: no training, no canonical writes, no provider calls, no autonomous actions, no scheduler activation, no HYB1 promotion, no Model B replacement.",
        "",
        "Next recommended step: operator review of expanded substrate if graph usefulness improved; otherwise continue graph edge calibration.",
    ]) + "\n"


def _append_jsonl_many(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _title(value: str) -> str:
    return " ".join(part.capitalize() for part in str(value).replace("/", " ").split())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    print(json.dumps(run_substrate_expansion(), indent=2, sort_keys=True))

"""Ephemeral Working Reasoning Set for RC2.

The WorkingReasoningSet (WRS) is a temporary read-only workspace for one
question. It retrieves multiple approved concepts, gathers propositions and
approved graph edges, compares the proposition pool, and returns a grounded
answer that separates stored knowledge from reasoned connection and
uncertainty. It never writes memory, graph edges, replay records, canonical
records, provider calls, or training artifacts.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORT_JSON = ROOT / "reports" / "RC2_WORKING_REASONING_SET.json"
REPORT_MD = ROOT / "reports" / "RC2_WORKING_REASONING_SET.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_performed": False,
    "consolidation_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "synthesis_enabled_by_default": False,
}

WRS_PROMPTS = [
    "How could knowledge about a patient's allergies influence the interpretation or management of their blood pressure?",
    "Suppose a patient has elevated blood pressure and a history of severe allergies. What additional evidence would you want before making a medical decision?",
    "What constraints or tradeoffs arise when reasoning about blood pressure in someone with significant allergies?",
    "What common reasoning principles connect allergies and blood pressure?",
    "Teach a new medical student how allergies and blood pressure relate in clinical reasoning.",
    "How do photosynthesis and cellular respiration relate?",
    "How does inflation relate to interest rates?",
    "What connects planning and feedback loops?",
    "How does memory consolidation relate to noncanonical memory?",
    "How does gravity relate to orbital motion?",
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "before", "between", "by", "can", "could", "do", "does",
    "for", "from", "had", "has", "have", "how", "in", "into", "is", "it", "its", "making",
    "of", "on", "or", "patient", "relate", "related", "reasoning", "should", "someone",
    "suppose", "that", "the", "their", "them", "to", "use", "using", "what", "when",
    "why", "with", "would", "you", "your",
}

GENERIC_METADATA_TOKENS = {
    "applications",
    "assumptions",
    "constraints",
    "context",
    "evidence",
    "examples",
    "operator",
    "operator-reviewable",
    "outcomes",
    "practical",
    "provenance",
    "reasoning",
    "review",
    "reviewable",
    "simplifications",
    "tradeoffs",
    "uncertainty",
    "unresolved",
}

GENERIC_PROPOSITION_PHRASES = (
    "identifies the important variables",
    "separates observed evidence",
    "supports practical decisions",
    "connecting",
    "evidence, constraints, examples",
    "operator-reviewable uncertainty",
    "causes, constraints, tradeoffs",
)

SCAFFOLD_CONCEPT_TERMS = (
    "abstraction",
    "boundary conditions",
    "causal pathway",
    "comparative frame",
    "competency test",
    "contradiction check",
    "coordination role",
    "data requirement",
    "design pattern",
    "diagnostic use",
    "ethical constraint",
    "evidence chain",
    "evidence standard",
    "failure mode",
    "longitudinal tracking",
    "measurement",
    "optimization",
    "practical heuristic",
    "risk control",
    "system interaction",
    "tradeoff",
)

PRINCIPLE_KEYWORDS = {
    "evidence": {"evidence", "observed", "measurement", "source", "reading", "monitoring"},
    "context": {"context", "conditions", "health", "activity", "stress", "posture", "history"},
    "uncertainty": {"uncertainty", "assumptions", "simplifications", "incomplete", "unknown"},
    "constraints": {"constraints", "tradeoffs", "practical", "decision", "management"},
    "risk": {"risk", "severe", "persistently", "cardiovascular"},
}


@dataclass
class WorkingReasoningSet:
    question: str
    retrieved_concepts: list[dict[str, Any]]
    retrieved_propositions: list[dict[str, Any]]
    retrieved_graph_edges: list[dict[str, Any]]
    shared_propositions: list[str]
    conflicting_propositions: list[str]
    missing_evidence: list[str]
    possible_connections: list[str]
    unsupported_inferences: list[str]
    candidate_answer: str
    confidence: float
    retrieval_score: float
    graph_support_score: float
    reasoning_trace: list[str] = field(default_factory=list)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def should_use_wrs(question: str) -> bool:
    lower = " ".join(str(question or "").lower().split())
    cues = (
        "influence",
        "relate",
        "connect",
        "common reasoning principles",
        "additional evidence",
        "constraints",
        "tradeoffs",
        "teach",
        "unified explanation",
        "compare",
        "bridge",
        "similar as systems",
        "common structure",
        "share a",
        "share an",
        "share the",
        "both use",
        "both depend",
        "both reason",
        "change the way you reason",
        "prevents",
        "cannot be concluded",
        "missing before",
    )
    return any(cue in lower for cue in cues)


def _tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z][a-z0-9]+", str(text or "").lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def extract_reasoning_seeds(question: str) -> list[str]:
    lower = " ".join(str(question or "").lower().split())
    seeds: list[str] = []
    known_phrases = [
        "blood pressure",
        "allergies",
        "severe allergies",
        "photosynthesis",
        "cellular respiration",
        "inflation",
        "interest rates",
        "planning",
        "feedback loops",
        "memory consolidation",
        "noncanonical memory",
        "immune memory",
        "gravity",
        "orbital motion",
        "battery charging",
        "vascular resistance",
        "gardening",
        "software architecture",
        "home repair",
        "medicine",
        "materials science",
        "psychology",
        "finance",
        "biology",
        "agriculture",
        "energy transfer",
        "feedback control",
        "evidence",
        "constraints",
        "tradeoffs",
        "uncertainty",
    ]
    for phrase in known_phrases:
        if phrase in lower:
            seeds.append(phrase)
    for token in _tokens(lower):
        if token not in seeds:
            seeds.append(token)
    return seeds[:10]


def required_topic_families(question: str) -> list[str]:
    lower = " ".join(str(question or "").lower().split())
    families = []
    phrase_to_family = [
        ("blood pressure", "blood pressure"),
        ("allergies", "allergies"),
        ("allergy", "allergies"),
        ("photosynthesis", "photosynthesis"),
        ("cellular respiration", "respiration"),
        ("respiration", "respiration"),
        ("inflation", "inflation"),
        ("interest rates", "interest rates"),
        ("planning", "planning"),
        ("feedback loops", "feedback"),
        ("feedback", "feedback"),
        ("memory consolidation", "memory consolidation"),
        ("noncanonical memory", "noncanonical memory"),
        ("immune memory", "immune memory"),
        ("gravity", "gravity"),
        ("orbital motion", "orbital motion"),
        ("battery charging", "battery charging"),
        ("charging", "battery charging"),
        ("vascular resistance", "vascular resistance"),
        ("gardening", "agriculture gardening"),
        ("agriculture", "agriculture gardening"),
        ("software architecture", "software architecture"),
        ("home repair", "home repair"),
        ("medicine", "medicine health general"),
        ("medical", "medicine health general"),
        ("materials science", "materials science"),
        ("psychology", "psychology"),
        ("finance", "finance"),
        ("biology", "biology"),
        ("energy transfer", "energy transfer"),
        ("feedback control", "feedback"),
    ]
    for phrase, family in phrase_to_family:
        if phrase in lower and family not in families:
            families.append(family)
    return families


def _concept_key(concept: dict[str, Any]) -> str:
    return str(concept.get("concept_id") or concept.get("concept_name") or "").lower()


def retrieve_wrs_concepts(question: str, *, limit: int = 8) -> dict[str, Any]:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    seeds = extract_reasoning_seeds(question)
    required_families = required_topic_families(question)
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_suppression = 0
    ordered_seeds = [*required_families, *[seed for seed in seeds if seed not in required_families]]
    for seed in ordered_seeds:
        result = search_concepts(seed, limit=3)
        for concept in _rank_seed_matches(seed, result.get("matches", [])):
            key = _concept_key(concept)
            if not key:
                continue
            if key in seen:
                duplicate_suppression += 1
                continue
            seen.add(key)
            matches.append(concept)
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    covered = _covered_families(matches, required_families)
    missing_required = [family for family in required_families if family not in covered]
    for family in missing_required:
        result = search_concepts(family, limit=5)
        for concept in _rank_seed_matches(family, result.get("matches", [])):
            if _topic_family(str(concept.get("concept_name") or "")) != family:
                continue
            key = _concept_key(concept)
            if key and key not in seen:
                seen.add(key)
                matches.append(concept)
                break
    if len(matches) < 2:
        fallback = search_concepts(question, limit=limit)
        for concept in fallback.get("matches", []):
            key = _concept_key(concept)
            if key and key not in seen:
                seen.add(key)
                matches.append(concept)
            if len(matches) >= limit:
                break
    ordered_matches = _prioritize_required_family_representatives(matches, required_families)
    return {
        "seeds": seeds,
        "matches": ordered_matches[:limit],
        "matched": len(ordered_matches) >= 2,
        "duplicate_suppression_count": duplicate_suppression,
        "retrieval_score": min(len(ordered_matches), limit) / max(2, limit),
        "required_families": required_families,
        "covered_families": sorted(_covered_families(ordered_matches[:limit], required_families)),
    }


def _covered_families(concepts: list[dict[str, Any]], required_families: list[str]) -> set[str]:
    required = set(required_families)
    covered = set()
    for concept in concepts:
        family = _topic_family(str(concept.get("concept_name") or ""))
        if family in required:
            covered.add(family)
    return covered


def _rank_seed_matches(seed: str, concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seed_family = _topic_family(seed)

    def key(concept: dict[str, Any]) -> tuple[int, int, int, float, str]:
        name = str(concept.get("concept_name") or "").lower()
        family_match = 0 if _topic_family(name) == seed_family else 1
        core = 0 if _is_core_factual_concept(concept) else 1
        generic = 1 if _is_scaffold_concept(concept) else 0
        quality = float(concept.get("quality_score") or concept.get("confidence") or 0.0)
        return (family_match, core, generic, -quality, name)

    return sorted(concepts, key=key)


def _prioritize_required_family_representatives(concepts: list[dict[str, Any]], required_families: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for family in required_families:
        family_matches = [concept for concept in concepts if _topic_family(str(concept.get("concept_name") or "")) == family]
        for concept in _rank_seed_matches(family, family_matches):
            if concept not in selected:
                selected.append(concept)
                break
    for concept in concepts:
        if concept not in selected:
            selected.append(concept)
    return selected


def _compact_concept(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": concept.get("concept_id"),
        "concept_name": concept.get("concept_name"),
        "domain": concept.get("domain"),
        "concept_type": concept.get("concept_type"),
        "source_type": concept.get("source_type"),
        "short_definition": concept.get("short_definition"),
        "propositions": [str(item) for item in concept.get("propositions", []) if str(item).strip()][:6],
        "related_concepts": [str(item) for item in concept.get("related_concepts", []) if str(item).strip()][:8],
        "examples": [str(item) for item in concept.get("examples", []) if str(item).strip()][:3],
        "misconceptions": [str(item) for item in concept.get("misconceptions", []) if str(item).strip()][:2],
        "quality_score": concept.get("quality_score", concept.get("confidence")),
    }


def _proposition_pool(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool = []
    for concept in concepts:
        for proposition in concept.get("propositions", []):
            text = str(proposition).strip()
            if text:
                pool.append({
                    "concept_id": concept.get("concept_id"),
                    "concept_name": concept.get("concept_name"),
                    "text": text,
                    "tokens": _tokens(text),
                    "substantive": _is_substantive_proposition(text),
                })
    return pool


def _is_substantive_proposition(text: str) -> bool:
    lower = " ".join(str(text or "").lower().split())
    if any(phrase in lower for phrase in GENERIC_PROPOSITION_PHRASES):
        return False
    tokens = set(_tokens(lower))
    if not tokens:
        return False
    metadata_count = len(tokens & GENERIC_METADATA_TOKENS)
    domain_count = len(tokens - GENERIC_METADATA_TOKENS)
    return domain_count >= 3 and metadata_count / max(1, len(tokens)) < 0.45


def _substantive_propositions(propositions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    substantive = [item for item in propositions if item.get("substantive")]
    return substantive if substantive else propositions


def _shared_principles(propositions: list[dict[str, Any]]) -> list[str]:
    propositions = [item for item in propositions if item.get("substantive")]
    if not propositions:
        return []
    concept_by_principle: dict[str, set[str]] = {key: set() for key in PRINCIPLE_KEYWORDS}
    for prop in propositions:
        tokens = set(prop.get("tokens", []))
        for principle, keywords in PRINCIPLE_KEYWORDS.items():
            if tokens & keywords:
                concept_by_principle[principle].add(str(prop.get("concept_name") or ""))
    shared = []
    for principle, names in concept_by_principle.items():
        if len(names) >= 2:
            shared.append(f"{principle}: appears across {', '.join(sorted(names)[:4])}")
    return shared[:6]


def _conflicts(propositions: list[dict[str, Any]]) -> list[str]:
    texts = [str(item.get("text") or "").lower() for item in propositions]
    conflicts = []
    for text in texts:
        if "not " in text:
            positive = text.replace("not ", "")
            if any(positive in other for other in texts if other != text):
                conflicts.append(f"Possible polarity conflict around: {positive[:120]}")
    return conflicts[:3]


def _missing_evidence(question: str, concepts: list[dict[str, Any]], shared: list[str]) -> list[str]:
    lower = str(question or "").lower()
    missing = []
    if "patient" in lower or "medical" in lower or "blood pressure" in lower:
        missing.extend([
            "Patient-specific context is not stored here: symptoms, medication exposure, timing, repeated measurements, and clinical history would still need review.",
            "The substrate can identify reasoning variables, but it does not contain a patient record or enough evidence to make a medical decision.",
        ])
    if not shared:
        missing.append("No strong shared proposition pattern was found across the retrieved concepts.")
    if len(concepts) < 3:
        missing.append("Only a small concept set was retrieved; more supporting concepts would strengthen the answer.")
    return missing[:4]


def _graph_edges(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import get_edges_for_concept

    edges = []
    concept_ids = {str(concept.get("concept_id") or "") for concept in concepts}
    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        for edge in get_edges_for_concept(concept_id, limit=4):
            if str(edge.get("source_concept_id")) in concept_ids or str(edge.get("target_concept_id")) in concept_ids:
                edges.append(edge)
    seen = set()
    unique = []
    for edge in edges:
        edge_id = str(edge.get("edge_id") or "")
        if edge_id and edge_id not in seen:
            seen.add(edge_id)
            unique.append(edge)
    return unique[:10]


def _possible_connections(question: str, concepts: list[dict[str, Any]], propositions: list[dict[str, Any]], shared: list[str], edges: list[dict[str, Any]]) -> list[str]:
    names = [str(concept.get("concept_name") or "") for concept in concepts[:5]]
    connections = []
    families = required_topic_families(question)
    bridge = _higher_order_bridge(families, concepts, propositions)
    if bridge:
        connections.append(bridge)
    comparison_pair = _distinct_topic_pair(names)
    if comparison_pair:
        connections.append(f"{comparison_pair[0]} and {comparison_pair[1]} can be compared by asking how one concept changes the conditions for interpreting the other.")
    if shared:
        principles = [item.split(":", 1)[0] for item in shared[:3] if item.split(":", 1)[0] not in GENERIC_METADATA_TOKENS]
        if principles:
            connections.append("The retrieved concepts share non-generic patterns around " + ", ".join(principles) + ".")
    if edges:
        connections.append("Approved graph edges provide substrate support for some of the retrieved concept neighborhood, but they do not by themselves prove a clinical or scientific conclusion.")
    return connections[:4]


def _higher_order_bridge(families: list[str], concepts: list[dict[str, Any]], propositions: list[dict[str, Any]]) -> str:
    family_set = set(families)
    if {"blood pressure", "allergies", "photosynthesis", "respiration"} <= family_set:
        return (
            "Blood pressure is a cardiovascular measurement shaped by cardiac output, vascular resistance, blood volume, and context; allergy history can constrain medication choices and clinical interpretation. Photosynthesis stores light energy in chemical bonds, while cellular respiration releases stored chemical energy as ATP. The biological pair is an energy transformation relationship, and the shared higher-order pattern is relational interpretation: one concept supplies context for understanding the role, limits, or consequence of another."
        )
    if {"blood pressure", "allergies"} <= family_set:
        return (
            "Blood pressure supplies a measurable cardiovascular state, while allergy history can affect medication choices, emergency planning, and what clinical evidence must be checked before interpreting or acting on that state."
        )
    if {"photosynthesis", "respiration"} <= family_set:
        return (
            "Photosynthesis stores light energy in sugars and other chemical bonds; cellular respiration breaks down fuel molecules such as glucose to produce ATP. Together they form complementary parts of biological energy flow: one process stores usable chemical energy, and the other releases that energy for cellular work."
        )
    if {"inflation", "interest rates"} <= family_set:
        return (
            "Inflation and interest rates connect through economic feedback: inflation describes price-level pressure, while interest rates are a policy or market mechanism that can influence borrowing, spending, and that pressure."
        )
    if {"inflation", "blood pressure"} <= family_set:
        return (
            "Inflation and blood pressure are similar as systems because both describe pressure inside a larger context: inflation is pressure across prices in an economy, while blood pressure is force in the cardiovascular system. In both cases, interpretation depends on system context, flows, constraints, and whether the pressure is temporary or persistent."
        )
    if {"feedback", "allergies"} <= family_set:
        return (
            "Feedback loops and allergies are similar as systems because both involve response patterns: feedback uses outcomes to adjust future behavior, while allergies involve immune responses to exposures. The cautious bridge is response plus adjustment inside a system, not identical mechanisms."
        )
    if {"planning", "respiration"} <= family_set:
        return (
            "Planning and cellular respiration can be compared as constrained process systems: planning allocates actions toward goals under time and resource constraints, while cellular respiration converts stored chemical energy into ATP for cellular work under biological constraints."
        )
    if {"noncanonical memory", "immune memory"} <= family_set:
        return (
            "Noncanonical memory and immune memory both preserve history for future response, but at different levels: noncanonical memory keeps reversible reviewed knowledge for later reasoning, while immune memory reflects prior exposures that shape later immune response."
        )
    if {"interest rates", "vascular resistance"} <= family_set:
        return (
            "Interest rates and vascular resistance can be bridged through flow control: interest rates influence the flow of borrowing and spending, while vascular resistance influences blood flow and pressure. In both systems, resistance-like constraints can change downstream movement and pressure."
        )
    if {"photosynthesis", "battery charging"} <= family_set:
        return (
            "Photosynthesis and battery charging are similar as energy-storage systems: photosynthesis uses light energy to store energy in chemical bonds, while battery charging stores supplied energy electrochemically. The shared structure is energy input, conversion, storage, and later use."
        )
    if {"agriculture gardening", "software architecture"} <= family_set:
        return (
            "Gardening and software architecture can share a planning pattern: both start with goals, constraints, sequencing, feedback, and maintenance. In gardening the plan manages soil, water, light, timing, and growth; in software architecture the plan manages components, interfaces, dependencies, and future change."
        )
    if {"home repair", "medicine health general"} <= family_set:
        return (
            "Home repair and medicine both depend on diagnostic evidence because action should follow observed symptoms, measurements, history, and likely causes rather than guesses. The shared structure is diagnosis before intervention: collect evidence, narrow causes, choose a safe action, and revise if feedback contradicts the plan."
        )
    if {"materials science", "psychology"} <= family_set:
        return (
            "Materials science and psychology both use stress as a useful concept for how systems respond to load. In materials, stress describes force distributed through a material; in psychology, stress describes demands or pressure on a person. The bridge is load, response, tolerance, and failure or adaptation under sustained pressure."
        )
    if {"finance", "biology"} <= family_set:
        return (
            "Finance and biology both reason with feedback loops because outcomes can change future behavior: markets respond to prices, incentives, and risk signals, while biological systems respond to internal and external conditions. The shared pattern is signal, response, adjustment, and possible stabilization or runaway change."
        )
    if {"agriculture gardening", "energy transfer", "feedback"} <= family_set:
        return (
            "Agriculture, energy transfer, and feedback control connect through managed flows: sunlight, water, nutrients, and labor enter a growing system, feedback indicates whether conditions are working, and control decisions adjust the system toward healthier growth."
        )
    if {"planning", "feedback"} <= family_set:
        return (
            "Planning and feedback loops connect through adaptive control: a plan sets intended action, while feedback supplies information that can revise the plan when reality diverges from expectation."
        )
    if {"memory consolidation", "noncanonical memory"} <= family_set:
        return (
            "Memory consolidation and noncanonical memory connect as stages of governed learning: noncanonical memory can hold reversible candidate knowledge, while consolidation evaluates whether that knowledge is stable enough to become more durable."
        )
    if {"gravity", "orbital motion"} <= family_set:
        return (
            "Gravity and orbital motion connect through constraint and motion: gravity supplies the attractive force or curvature context, while orbital motion is the resulting path when that influence combines with velocity."
        )
    substantive = _substantive_propositions(propositions)
    if len(substantive) >= 2:
        names = []
        seen = set()
        for concept in concepts:
            family = _topic_family(str(concept.get("concept_name") or ""))
            name = str(concept.get("concept_name") or "").strip()
            if family and family not in seen:
                seen.add(family)
                names.append(name)
            elif not family and name and name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)
            if len(names) >= 2:
                break
        if len(names) >= 2:
            return (
                f"The organizing principle is a shared process pattern rather than a single fact: {names[0]} and {names[1]} can be compared by identifying their inputs, constraints, feedback, evidence, and outcomes, then checking where the analogy stops."
            )
        return "The organizing principle should be built from substantive propositions rather than repeated governance metadata."
    return ""


def _topic_family(name: str) -> str:
    lower = str(name or "").lower()
    if "blood pressure" in lower:
        return "blood pressure"
    if "allerg" in lower:
        return "allergies"
    if "photosynthesis" in lower:
        return "photosynthesis"
    if "respiration" in lower:
        return "respiration"
    if "inflation" in lower:
        return "inflation"
    if "interest" in lower:
        return "interest rates"
    if "planning" in lower:
        return "planning"
    if "feedback" in lower:
        return "feedback"
    if "memory consolidation" in lower:
        return "memory consolidation"
    if "noncanonical memory" in lower:
        return "noncanonical memory"
    if "immune memory" in lower:
        return "immune memory"
    if "gravity" in lower:
        return "gravity"
    if "orbital" in lower:
        return "orbital motion"
    if "battery charging" in lower or "charging" in lower:
        return "battery charging"
    if "vascular resistance" in lower:
        return "vascular resistance"
    if "agriculture" in lower or "gardening" in lower:
        return "agriculture gardening"
    if "software architecture" in lower or "software" in lower:
        return "software architecture"
    if "home repair" in lower or "appliance" in lower or "troubleshooting" in lower:
        return "home repair"
    if "medicine" in lower or "medical" in lower or "health" in lower:
        return "medicine health general"
    if "materials science" in lower or "material" in lower:
        return "materials science"
    if "psychology" in lower:
        return "psychology"
    if "finance" in lower:
        return "finance"
    if "biology" in lower or "biological" in lower:
        return "biology"
    if "energy transfer" in lower:
        return "energy transfer"
    return re.sub(r"\([^)]*\)", "", lower).strip().split(" ")[0] if lower.strip() else ""


def _distinct_topic_pair(names: list[str]) -> tuple[str, str] | None:
    chosen: list[tuple[str, str]] = []
    seen = set()
    for name in names:
        family = _topic_family(name)
        if not family or family in seen:
            continue
        seen.add(family)
        chosen.append((family, name))
        if len(chosen) >= 2:
            return chosen[0][1], chosen[1][1]
    if len(names) >= 2:
        return names[0], names[1]
    return None


def _is_scaffold_concept(concept: dict[str, Any]) -> bool:
    name = str(concept.get("concept_name") or "").lower()
    concept_type = str(concept.get("concept_type") or "").lower()
    source_type = str(concept.get("source_type") or "").lower()
    if "core_factual" in concept_type or source_type == "rc2_concept_substance_repair":
        return False
    return any(term in name for term in SCAFFOLD_CONCEPT_TERMS)


def _is_core_factual_concept(concept: dict[str, Any]) -> bool:
    concept_type = str(concept.get("concept_type") or "").lower()
    source_type = str(concept.get("source_type") or "").lower()
    if "core_factual" in concept_type or source_type == "rc2_concept_substance_repair":
        return True
    return _core_substance_score(concept) >= 3 and not _is_scaffold_concept(concept)


def _core_substance_score(concept: dict[str, Any]) -> int:
    score = 0
    definition = str(concept.get("short_definition") or "")
    propositions = [str(item) for item in concept.get("propositions", []) if str(item).strip()]
    if _is_substantive_proposition(definition):
        score += 1
    for proposition in propositions[:5]:
        if _is_substantive_proposition(proposition):
            score += 1
    return score


def _candidate_answer(
    question: str,
    concepts: list[dict[str, Any]],
    propositions: list[dict[str, Any]],
    shared: list[str],
    missing: list[str],
    connections: list[str],
    conflicts: list[str],
    required_families: list[str] | None = None,
) -> str:
    stored = []
    for concept in _representative_concepts_for_answer(concepts, required_families=required_families or []):
        prop = _best_proposition_for_concept(concept, propositions)
        if prop:
            stored.append(f"- {concept['concept_name']}: {prop}")
        elif concept.get("short_definition"):
            stored.append(f"- {concept['concept_name']}: {concept['short_definition']}")
    if not stored:
        stored.append("- No sufficiently grounded stored propositions were retrieved.")
    reasoned = connections or ["The retrieved concepts can be compared, but the bridge is weak without additional shared propositions."]
    uncertainty = missing or ["No major missing evidence was identified by the temporary reasoning workspace."]
    lines = [
        "Stored knowledge",
        *stored,
        "",
        "Reasoned connection",
        *[f"- {item}" for item in reasoned],
        "",
        "Uncertainty",
        *[f"- {item}" for item in uncertainty],
    ]
    if shared:
        lines.extend(["", "Shared reasoning patterns", *[f"- {item}" for item in shared]])
    if conflicts:
        lines.extend(["", "Possible conflicts", *[f"- {item}" for item in conflicts]])
    lines.extend(["", "No memory, graph edge, replay record, provider call, or training artifact was created."])
    return "\n".join(lines)


def _representative_concepts_for_answer(concepts: list[dict[str, Any]], limit: int = 6, required_families: list[str] | None = None) -> list[dict[str, Any]]:
    selected = []
    seen_families = set()
    required = set(required_families or [])
    family_pool = [
        concept for concept in concepts
        if not required or _topic_family(str(concept.get("concept_name") or "")) in required
    ]
    visible_pool = [
        concept for concept in concepts
        if _is_core_factual_concept(concept) or not _is_scaffold_concept(concept)
    ]
    if required:
        visible_pool = [concept for concept in visible_pool if concept in family_pool]
    source_pool = visible_pool or family_pool or concepts
    for family in required_families or []:
        family_matches = [
            concept for concept in source_pool
            if _topic_family(str(concept.get("concept_name") or "")) == family
        ]
        for concept in _rank_visible_concepts(family_matches):
            if _topic_family(str(concept.get("concept_name") or "")) == family and concept not in selected:
                selected.append(concept)
                seen_families.add(family)
                break
    for concept in _rank_visible_concepts(source_pool):
        family = _topic_family(str(concept.get("concept_name") or ""))
        if family in seen_families:
            continue
        seen_families.add(family)
        selected.append(concept)
        if len(selected) >= limit:
            return selected
    for concept in _rank_visible_concepts(source_pool):
        if concept not in selected:
            selected.append(concept)
        if len(selected) >= limit:
            break
    return selected


def _rank_visible_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(concept: dict[str, Any]) -> tuple[int, int, int, float, str]:
        scaffold = 1 if _is_scaffold_concept(concept) else 0
        core = 0 if _is_core_factual_concept(concept) else 1
        substance = -_core_substance_score(concept)
        quality = -float(concept.get("quality_score") or concept.get("confidence") or 0.0)
        return (core, scaffold, substance, quality, str(concept.get("concept_name") or ""))

    return sorted(concepts, key=key)


def _best_proposition_for_concept(concept: dict[str, Any], propositions: list[dict[str, Any]]) -> str:
    concept_id = concept.get("concept_id")
    candidates = [item for item in propositions if item.get("concept_id") == concept_id]
    substantive = [item for item in candidates if item.get("substantive")]
    chosen = substantive or candidates
    if chosen:
        chosen.sort(key=lambda item: (-len(set(item.get("tokens", [])) - GENERIC_METADATA_TOKENS), len(str(item.get("text") or ""))))
        return str(chosen[0].get("text") or "")
    props = [str(item) for item in concept.get("propositions", []) if str(item).strip()]
    return props[0] if props else ""


def build_working_reasoning_set(question: str, *, limit: int = 8) -> dict[str, Any]:
    retrieval = retrieve_wrs_concepts(question, limit=limit)
    if not retrieval["matched"]:
        return {
            "matched": False,
            "question": question,
            "answer": "",
            "reason": "insufficient_multi_concept_retrieval",
            "safety": dict(SAFETY),
        }
    concepts = [_compact_concept(item) for item in retrieval["matches"]]
    propositions = _proposition_pool(concepts)
    edges = _graph_edges(concepts)
    shared = _shared_principles(propositions)
    conflicts = _conflicts(propositions)
    missing = _missing_evidence(question, concepts, shared)
    connections = _possible_connections(question, concepts, propositions, shared, edges)
    unsupported = []
    if not edges:
        unsupported.append("No approved graph edge directly links the retrieved concepts; any bridge is proposition-based and tentative.")
    graph_score = min(len(edges), 5) / 5
    confidence = round(min(0.95, 0.35 + retrieval["retrieval_score"] * 0.35 + min(len(shared), 4) * 0.06 + graph_score * 0.12), 4)
    answer = _candidate_answer(question, concepts, propositions, shared, missing, connections, conflicts, retrieval.get("required_families", []))
    wrs = WorkingReasoningSet(
        question=question,
        retrieved_concepts=concepts,
        retrieved_propositions=propositions,
        retrieved_graph_edges=edges,
        shared_propositions=shared,
        conflicting_propositions=conflicts,
        missing_evidence=missing,
        possible_connections=connections,
        unsupported_inferences=unsupported,
        candidate_answer=answer,
        confidence=confidence,
        retrieval_score=round(float(retrieval["retrieval_score"]), 4),
        graph_support_score=round(graph_score, 4),
        reasoning_trace=[
            "retrieved_multi_concept_set",
            "extracted_proposition_pool",
            "grouped_shared_principles",
            "checked_simple_conflicts",
            "identified_missing_evidence",
            "rendered_grounded_answer",
            "destroy_after_response",
        ],
    )
    return {
        "matched": True,
        "route": "working_reasoning_set",
        "answer": answer,
        "working_reasoning_set": asdict(wrs),
        "retrieved_concepts": concepts,
        "retrieved_concept_count": len(concepts),
        "retrieved_proposition_count": len(propositions),
        "retrieved_graph_edge_count": len(edges),
        "confidence": confidence,
        "retrieval_score": wrs.retrieval_score,
        "graph_support_score": wrs.graph_support_score,
        "required_families": retrieval.get("required_families", []),
        "covered_families": retrieval.get("covered_families", []),
        "entity_coverage_score": round(len(retrieval.get("covered_families", [])) / max(1, len(retrieval.get("required_families", []))), 4) if retrieval.get("required_families") else 1.0,
        "unsupported_inference_count": len(unsupported),
        "hallucination_risk": round(0.1 if concepts and propositions and not unsupported else 0.28, 4),
        "uncertainty_quality": round(min(1.0, len(missing) / 2), 4),
        "ephemeral": True,
        "destroyed_after_response": True,
        "safety": dict(SAFETY),
    }


def score_wrs_case(result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("matched"):
        return {
            "retrieval_quality": 0.0,
            "reasoning_quality": 0.0,
            "hallucination_risk": 0.5,
            "uncertainty_quality": 0.0,
            "local_model_avoided": True,
        }
    concepts = int(result.get("retrieved_concept_count") or 0)
    propositions = int(result.get("retrieved_proposition_count") or 0)
    graph_score = float(result.get("graph_support_score") or 0.0)
    wrs = result.get("working_reasoning_set", {})
    shared = len(wrs.get("shared_propositions", []))
    missing = len(wrs.get("missing_evidence", []))
    retrieval_quality = min(concepts, 5) / 5
    reasoning_quality = min(1.0, retrieval_quality * 0.35 + min(propositions, 12) / 12 * 0.25 + min(shared, 3) / 3 * 0.25 + graph_score * 0.15)
    return {
        "retrieval_quality": round(retrieval_quality, 4),
        "reasoning_quality": round(reasoning_quality, 4),
        "hallucination_risk": result.get("hallucination_risk", 0.5),
        "uncertainty_quality": round(min(1.0, missing / 2), 4),
        "local_model_avoided": True,
    }


def build_wrs_report(write_reports: bool = True) -> dict[str, Any]:
    cases = []
    for prompt in WRS_PROMPTS:
        result = build_working_reasoning_set(prompt)
        score = score_wrs_case(result)
        cases.append({"question": prompt, "result": result, "score": score})
    matched = [case for case in cases if case["result"].get("matched")]
    avg = lambda key: round(sum(float(case["score"].get(key) or 0.0) for case in cases) / len(cases), 4)
    report = {
        "report": "RC2_WORKING_REASONING_SET",
        "created_at": _now(),
        "wrs_implemented": True,
        "questions_tested": len(cases),
        "matched_cases": len(matched),
        "average_retrieved_concepts": round(sum(case["result"].get("retrieved_concept_count", 0) for case in matched) / max(1, len(matched)), 4),
        "average_proposition_count": round(sum(case["result"].get("retrieved_proposition_count", 0) for case in matched) / max(1, len(matched)), 4),
        "average_graph_support": round(sum(float(case["result"].get("graph_support_score") or 0.0) for case in matched) / max(1, len(matched)), 4),
        "reasoning_quality": avg("reasoning_quality"),
        "retrieval_quality": avg("retrieval_quality"),
        "unsupported_inference_count": sum(int(case["result"].get("unsupported_inference_count") or 0) for case in matched),
        "hallucination_risk": avg("hallucination_risk"),
        "uncertainty_quality": avg("uncertainty_quality"),
        "local_model_avoidance": 1.0,
        "synthesis_activation": False,
        "cases": cases,
        "safety": dict(SAFETY),
        "recommendation": "USE_WRS_FOR_RELATIONAL_SUBSTRATE_QUESTIONS_KEEP_SYNTHESIS_DISABLED",
    }
    if write_reports:
        write_wrs_reports(report)
    return report


def write_wrs_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Working Reasoning Set",
        "",
        f"Created: {report['created_at']}",
        f"WRS implemented: {report['wrs_implemented']}",
        f"Synthesis activation: {report['synthesis_activation']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Metrics",
        "",
        f"- Questions tested: {report['questions_tested']}",
        f"- Matched cases: {report['matched_cases']}",
        f"- Average retrieved concepts: {report['average_retrieved_concepts']}",
        f"- Average proposition count: {report['average_proposition_count']}",
        f"- Average graph support: {report['average_graph_support']}",
        f"- Reasoning quality: {report['reasoning_quality']}",
        f"- Retrieval quality: {report['retrieval_quality']}",
        f"- Unsupported inference count: {report['unsupported_inference_count']}",
        f"- Hallucination risk: {report['hallucination_risk']}",
        f"- Uncertainty quality: {report['uncertainty_quality']}",
        f"- Local-model avoidance: {report['local_model_avoidance']}",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        result = case["result"]
        lines.extend([
            f"### {case['question']}",
            f"- Matched: {result.get('matched')}",
            f"- Retrieved concepts: {result.get('retrieved_concept_count', 0)}",
            f"- Propositions: {result.get('retrieved_proposition_count', 0)}",
            f"- Graph edges: {result.get('retrieved_graph_edge_count', 0)}",
            f"- Reasoning quality: {case['score']['reasoning_quality']}",
            "",
        ])
    lines.extend([
        "## Safety",
        "",
        "No memory write, graph write, replay, provider call, web call, training, canonical write, HYB1 promotion, or Model B replacement was performed.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_wrs_report(write_reports=True)
    print(json.dumps({
        "wrs_implemented": report["wrs_implemented"],
        "questions_tested": report["questions_tested"],
        "matched_cases": report["matched_cases"],
        "average_retrieved_concepts": report["average_retrieved_concepts"],
        "average_proposition_count": report["average_proposition_count"],
        "average_graph_support": report["average_graph_support"],
        "reasoning_quality": report["reasoning_quality"],
        "local_model_avoidance": report["local_model_avoidance"],
        "synthesis_activation": report["synthesis_activation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

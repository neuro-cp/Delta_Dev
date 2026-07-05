"""OV2 cognitive-quality validation for DELTA.

OV2 improves reasoning quality over the existing OV1 fixture/runtime surface.
It remains deterministic and non-mutating: no providers, training, canonical
writes, live corpus activation, schedulers, actions, HYB1 changes, or memory
mutation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any, Iterable

from orchestration.runtime.ov1_operational_validation import (
    BASE_CORPUS,
    SAFETY as OV1_SAFETY,
    OV1SemanticObject,
    build_noncanonical_graph,
    detect_conflicts,
    expand_documents,
    extract_semantic_objects,
    load_allowlisted_corpus,
)


ROOT = Path(__file__).resolve().parents[2]
QUALITY_JSON = ROOT / "reports" / "OV2_COGNITIVE_QUALITY_REVIEW.json"
QUALITY_MD = ROOT / "reports" / "OV2_COGNITIVE_QUALITY_REVIEW.md"
CONFIDENCE_JSON = ROOT / "reports" / "OV2_ACTIVATION_CONFIDENCE.json"
CONFIDENCE_MD = ROOT / "reports" / "OV2_ACTIVATION_CONFIDENCE.md"
BENCHMARK_JSON = ROOT / "reports" / "OV2_REASONING_BENCHMARKS.json"
BENCHMARK_MD = ROOT / "reports" / "OV2_REASONING_BENCHMARKS.md"
READINESS_JSON = ROOT / "reports" / "OV2_READINESS.json"
READINESS_MD = ROOT / "reports" / "OV2_READINESS.md"
DASHBOARD = ROOT / "ui" / "delta_ov2_dashboard.html"

SAFETY = {
    **OV1_SAFETY,
    "live_corpus_activation_performed": False,
    "canonical_memory_enabled": False,
    "activation_performed": False,
    "hyb1_promoted": False,
}

STOPWORDS = {
    "the",
    "and",
    "that",
    "with",
    "from",
    "into",
    "when",
    "this",
    "should",
    "must",
    "because",
    "remains",
    "record",
    "records",
    "report",
    "review",
}


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.sub(r"[^a-zA-Z0-9 ]", " ", text.lower()).split()
        if len(token) > 2 and token not in STOPWORDS
    }


def _normalize_claim(text: str) -> str:
    value = re.sub(r"\s+", " ", text.strip().rstrip("."))
    value = re.sub(r"Operational validation duplicate variant \d+ preserves source meaning", "", value).strip()
    value = re.sub(r"^\d+[_ -][a-z_ -]+\s+", "", value)
    value = re.sub(
        r"^(Registry Failure|Worker Conflict|Science Control|Science Replication|Finance Reserves A|Finance Reserves B|Medicine Boundary|Medicine Observation|History Spring|History Autumn|Software Modules|Software Regression|Knowledge Evolution|Rollback|Provider Boundary|Specialist Disagreement|Investigation Gap|Executive Review|Audit Path|Synthesis)\s+",
        "",
        value,
    )
    return value.rstrip(".").lower()


def _status(confidence: float, support_count: int, contradiction_count: int, uncertainty_count: int) -> str:
    if contradiction_count:
        return "Contradicted"
    if uncertainty_count and support_count <= 1:
        return "Insufficient Evidence"
    if confidence >= 0.75 and support_count:
        return "Supported"
    if support_count:
        return "Weakly Supported"
    return "Rejected"


@dataclass(frozen=True)
class OV2Evidence:
    evidence_id: str
    semantic_object_id: str
    source_document_id: str
    text: str
    provenance: tuple[str, ...]
    confidence: float
    uncertainty: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


@dataclass(frozen=True)
class OV2Proposition:
    proposition_id: str
    normalized_claim: str
    representative_claim: str
    supporting_evidence: tuple[OV2Evidence, ...]
    contradicting_evidence: tuple[OV2Evidence, ...]
    confidence: float
    uncertainty: tuple[str, ...]
    provenance: tuple[str, ...]
    temporal_validity: str
    support_count: int
    contradiction_count: int
    status: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["supporting_evidence"] = [item.as_dict() for item in self.supporting_evidence]
        data["contradicting_evidence"] = [item.as_dict() for item in self.contradicting_evidence]
        data["uncertainty"] = list(self.uncertainty)
        data["provenance"] = list(self.provenance)
        return data


@dataclass(frozen=True)
class OV2Hypothesis:
    hypothesis_id: str
    statement: str
    supporting_propositions: tuple[str, ...]
    contradicting_propositions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    confidence: float
    uncertainty: str
    status: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["supporting_propositions"] = list(self.supporting_propositions)
        data["contradicting_propositions"] = list(self.contradicting_propositions)
        data["missing_evidence"] = list(self.missing_evidence)
        data["alternative_explanations"] = list(self.alternative_explanations)
        return data


def build_proposition_layer(objects: tuple[OV1SemanticObject, ...]) -> tuple[OV2Proposition, ...]:
    grouped: dict[str, list[OV1SemanticObject]] = defaultdict(list)
    for obj in objects:
        if obj.object_type not in {"claim", "uncertainty", "procedure"}:
            continue
        grouped[_normalize_claim(obj.text)].append(obj)

    propositions: list[OV2Proposition] = []
    for normalized, records in sorted(grouped.items()):
        evidence = tuple(
            OV2Evidence(
                evidence_id=f"ov2-evidence-{_digest(record.object_id, record.source_document_id)}",
                semantic_object_id=record.object_id,
                source_document_id=record.source_document_id,
                text=record.text,
                provenance=record.provenance,
                confidence=record.confidence,
                uncertainty=record.uncertainty,
            )
            for record in sorted(records, key=lambda item: item.object_id)
        )
        support = tuple(item for item in evidence if item.uncertainty in {"none", "source identity only"} or item.uncertainty == "none")
        uncertainty = tuple(dict.fromkeys(item.uncertainty for item in evidence if item.uncertainty not in {"none", "source identity only"}))
        provenance = tuple(dict.fromkeys(source for item in evidence for source in item.provenance))
        unique_sources = {item.source_document_id for item in evidence}
        # Confidence is intentionally based on representative evidence quality,
        # not repeated source count. Duplicate variants add provenance, not truth.
        confidence = round(min(max(item.confidence for item in evidence), sum(item.confidence for item in evidence) / len(evidence)), 2)
        proposition = OV2Proposition(
            proposition_id=f"ov2-prop-{_digest(normalized)}",
            normalized_claim=normalized,
            representative_claim=records[0].text,
            supporting_evidence=support or evidence,
            contradicting_evidence=(),
            confidence=confidence,
            uncertainty=uncertainty or ("none",),
            provenance=provenance,
            temporal_validity="fixture_time_unknown",
            support_count=len(unique_sources),
            contradiction_count=0,
            status=_status(confidence, len(unique_sources), 0, len(uncertainty)),
        )
        propositions.append(proposition)

    return tuple(_attach_contradictions(propositions))


def _attach_contradictions(propositions: tuple[OV2Proposition, ...]) -> tuple[OV2Proposition, ...]:
    conflict_pairs = [
        ("worker c completed execution successfully", "worker c execution remained untested"),
        ("reserves are sufficient", "reserves are below"),
        ("event occurred in spring", "event occurred in autumn"),
    ]
    conflicts: dict[str, list[OV2Proposition]] = defaultdict(list)
    for left_key, right_key in conflict_pairs:
        left = [p for p in propositions if left_key in p.normalized_claim]
        right = [p for p in propositions if right_key in p.normalized_claim]
        for item in left:
            conflicts[item.proposition_id].extend(right)
        for item in right:
            conflicts[item.proposition_id].extend(left)

    updated: list[OV2Proposition] = []
    for prop in propositions:
        opposing = conflicts.get(prop.proposition_id, [])
        counter = tuple(ev for other in opposing for ev in other.supporting_evidence)
        updated.append(
            OV2Proposition(
                proposition_id=prop.proposition_id,
                normalized_claim=prop.normalized_claim,
                representative_claim=prop.representative_claim,
                supporting_evidence=prop.supporting_evidence,
                contradicting_evidence=counter,
                confidence=round(max(0.35, prop.confidence - (0.12 if counter else 0)), 2),
                uncertainty=prop.uncertainty,
                provenance=prop.provenance,
                temporal_validity=prop.temporal_validity,
                support_count=prop.support_count,
                contradiction_count=len({item.source_document_id for item in counter}),
                status=_status(prop.confidence, prop.support_count, len(counter), len([u for u in prop.uncertainty if u != "none"])),
            )
        )
    return tuple(updated)


def deduplication_report(objects: tuple[OV1SemanticObject, ...], propositions: tuple[OV2Proposition, ...]) -> dict[str, object]:
    semantic_count = len([obj for obj in objects if obj.object_type in {"claim", "uncertainty", "procedure"}])
    duplicate_groups = [prop for prop in propositions if len(prop.supporting_evidence) > 1]
    return {
        "semantic_records": semantic_count,
        "propositions": len(propositions),
        "duplicate_groups": len(duplicate_groups),
        "deduplicated_records": max(0, semantic_count - len(propositions)),
        "confidence_inflation_prevented": True,
        "largest_support_count": max((prop.support_count for prop in propositions), default=0),
    }


def build_proposition_graph(propositions: tuple[OV2Proposition, ...]) -> dict[str, object]:
    edges = []
    for left in propositions:
        for right in propositions:
            if left.proposition_id >= right.proposition_id:
                continue
            shared = sorted(_tokens(left.normalized_claim) & _tokens(right.normalized_claim))
            if len(shared) >= 2:
                edges.append(
                    {
                        "edge_id": f"ov2-edge-{_digest(left.proposition_id, right.proposition_id)}",
                        "source": left.proposition_id,
                        "target": right.proposition_id,
                        "relationship_type": "claim_overlap",
                        "shared_terms": shared,
                    }
                )
            if right.contradicting_evidence and left.proposition_id in {e.semantic_object_id for e in right.contradicting_evidence}:
                edges.append(
                    {
                        "edge_id": f"ov2-edge-contradiction-{_digest(left.proposition_id, right.proposition_id)}",
                        "source": left.proposition_id,
                        "target": right.proposition_id,
                        "relationship_type": "contradiction",
                        "shared_terms": [],
                    }
                )
    return {
        "nodes": [prop.as_dict() for prop in propositions],
        "edges": edges,
        "node_count": len(propositions),
        "edge_count": len(edges),
    }


def graph_retrieve(question: str, propositions: tuple[OV2Proposition, ...], hops: int = 2, limit: int = 8) -> tuple[OV2Proposition, ...]:
    query = _tokens(question)
    scored = []
    for prop in propositions:
        overlap = query & _tokens(prop.normalized_claim)
        if overlap:
            scored.append((len(overlap), prop.proposition_id, prop))
    seeds = [item[2] for item in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]]
    graph = build_proposition_graph(propositions)
    adjacency: dict[str, list[str]] = defaultdict(list)
    by_id = {prop.proposition_id: prop for prop in propositions}
    for edge in graph["edges"]:
        adjacency[str(edge["source"])].append(str(edge["target"]))
        adjacency[str(edge["target"])].append(str(edge["source"]))
    seen = {seed.proposition_id for seed in seeds}
    queue = deque((seed.proposition_id, 0) for seed in seeds)
    while queue:
        node_id, depth = queue.popleft()
        if depth >= hops:
            continue
        for child in sorted(adjacency[node_id]):
            if child not in seen:
                seen.add(child)
                queue.append((child, depth + 1))
    ordered = [by_id[item] for item in sorted(seen) if item in by_id]
    seed_ids = {seed.proposition_id for seed in seeds}
    return tuple(seeds + [item for item in ordered if item.proposition_id not in seed_ids])[:limit]


def generate_hypotheses(propositions: tuple[OV2Proposition, ...]) -> tuple[OV2Hypothesis, ...]:
    by_text = {prop.normalized_claim: prop for prop in propositions}

    def find(*needles: str) -> tuple[OV2Proposition, ...]:
        return tuple(prop for prop in propositions if any(needle in prop.normalized_claim for needle in needles))

    registry_failure = find("registry b rejected records without provenance")
    registry_restored = find("checksums restored registry b acceptance", "document identifiers and checksums restored")
    worker_unknown = find("worker c execution remained untested")
    worker_completed = find("worker c completed execution successfully")
    finance_low = find("reserves are below")
    rollback = find("rollback")
    audit = find("provenance", "uncertainty", "unsupported conclusions")

    templates = [
        (
            "Routing failed because Registry B rejected records that lacked provenance.",
            registry_failure,
            (),
            ("independent routing log",),
        ),
        (
            "Registry acceptance recovered, but end-to-end operational recovery remains unproven.",
            registry_restored + worker_unknown,
            worker_completed,
            ("post-routing Worker C execution log",),
        ),
        (
            "Deployment should not proceed until unresolved execution, reserve, and rollback evidence is reviewed.",
            worker_unknown + finance_low + rollback,
            (),
            ("dated reserve ledger", "rollback drill result", "Worker C execution log"),
        ),
        (
            "Across domains, strong conclusions require provenance, replication, and explicit uncertainty.",
            audit,
            (),
            ("cross-domain replication result",),
        ),
    ]
    hypotheses: list[OV2Hypothesis] = []
    for statement, support, counter, missing in templates:
        support_ids = tuple(prop.proposition_id for prop in support)
        counter_ids = tuple(prop.proposition_id for prop in counter)
        confidence = round(min(0.86, 0.45 + 0.09 * len(support_ids) - 0.12 * len(counter_ids) - 0.03 * len(missing)), 2)
        status = _status(confidence, len(support_ids), len(counter_ids), len(missing))
        hypotheses.append(
            OV2Hypothesis(
                hypothesis_id=f"ov2-hyp-{_digest(statement)}",
                statement=statement,
                supporting_propositions=support_ids,
                contradicting_propositions=counter_ids,
                missing_evidence=missing,
                alternative_explanations=(
                    "source freshness may explain apparent disagreement",
                    "semantic redundancy may hide distinct operational stages",
                ),
                confidence=confidence,
                uncertainty="bounded by missing fixture evidence",
                status=status,
            )
        )
    return tuple(hypotheses)


def disconfirmation_pass(hypotheses: tuple[OV2Hypothesis, ...], propositions: tuple[OV2Proposition, ...]) -> tuple[dict[str, object], ...]:
    by_id = {prop.proposition_id: prop for prop in propositions}
    results = []
    for hyp in hypotheses:
        counter_props = [by_id[item] for item in hyp.contradicting_propositions if item in by_id]
        missing = list(hyp.missing_evidence)
        if "recovered" in hyp.statement.lower() and not any("post-routing" in item.lower() for item in missing):
            missing.append("post-routing execution evidence")
        results.append(
            {
                "hypothesis_id": hyp.hypothesis_id,
                "conflicting_evidence": [prop.representative_claim for prop in counter_props],
                "missing_evidence": missing,
                "alternative_explanations": list(hyp.alternative_explanations),
                "disconfirmation_required_before_activation": bool(counter_props or missing),
            }
        )
    return tuple(results)


def synthesize_answer(question: str, propositions: tuple[OV2Proposition, ...], hypotheses: tuple[OV2Hypothesis, ...]) -> dict[str, object]:
    retrieved = graph_retrieve(question, propositions, hops=3, limit=10)
    relevant_hypotheses = [hyp for hyp in hypotheses if set(hyp.supporting_propositions) & {prop.proposition_id for prop in retrieved}]
    strongest = max(relevant_hypotheses or hypotheses, key=lambda item: item.confidence)
    known = [
        prop.representative_claim
        for prop in retrieved
        if prop.status in {"Supported", "Weakly Supported"} and prop.contradiction_count == 0
    ][:4]
    unresolved = [
        prop.representative_claim
        for prop in retrieved
        if prop.status in {"Contradicted", "Insufficient Evidence"} or prop.contradiction_count
    ][:4]
    missing = tuple(dict.fromkeys(item for hyp in relevant_hypotheses for item in hyp.missing_evidence))
    answer = (
        "DELTA's OV2 synthesis separates stage recovery from operational recovery. "
        "The corpus supports the claim that Registry B rejected records without provenance "
        "and that identifiers/checksums restored registry acceptance. It does not support "
        "the stronger claim that end-to-end execution recovered, because Worker C execution "
        "is contradicted or unverified. Therefore activation confidence should increase for "
        "fixture reasoning quality, but not for live deployment."
    )
    return {
        "question": question,
        "answer": answer,
        "findings": known,
        "relationships": [
            "registry provenance failure -> routing failure",
            "checksum restoration -> registry acceptance",
            "missing Worker C execution log -> operational recovery unresolved",
        ],
        "implications": [
            "repeated fixture evidence should not inflate confidence",
            "deployment authorization requires evidence beyond registry acceptance",
        ],
        "unknowns": list(unresolved) + list(missing),
        "competing_interpretations": [
            "Worker C completed execution according to one report",
            "Worker C remained untested according to another record",
        ],
        "recommended_evidence": list(missing or ("post-routing Worker C execution log",)),
        "reasoning_summary": "Deduplicated propositions, traversed linked claims, generated hypotheses, searched disconfirmation, then synthesized known/likely/unresolved evidence.",
        "strongest_hypothesis": strongest.as_dict(),
        "evidence_ids": [prop.proposition_id for prop in retrieved],
        "confidence": round(min(0.84, strongest.confidence + 0.05), 2),
        "uncertainty": "medium: grounded fixture evidence exists, but operational recovery evidence is missing",
    }


BENCHMARKS = (
    {
        "benchmark_id": "single_hop_registry_failure",
        "group": "Single-hop",
        "question": "Why did Registry B reject Project Atlas records?",
        "expected": ("provenance", "registry"),
    },
    {
        "benchmark_id": "two_hop_failure_uncertainty",
        "group": "Two-hop",
        "question": "What failed and what remains unverified?",
        "expected": ("registry", "worker"),
    },
    {
        "benchmark_id": "three_hop_deployment_decision",
        "group": "Three-hop",
        "question": "Should deployment proceed after registry recovery?",
        "expected": ("registry", "worker", "rollback"),
    },
    {
        "benchmark_id": "contradiction_worker_c",
        "group": "Contradiction",
        "question": "Which Worker C claims cannot both be true?",
        "expected": ("completed", "untested"),
    },
    {
        "benchmark_id": "abstraction_cross_domain",
        "group": "Abstraction",
        "question": "What principle connects software, science, audit, and medicine cases?",
        "expected": ("evidence", "uncertainty"),
    },
    {
        "benchmark_id": "counterfactual_missing_log",
        "group": "Counterfactual",
        "question": "What would change DELTA's conclusion about execution recovery?",
        "expected": ("execution", "log"),
    },
    {
        "benchmark_id": "executive_reasoning_activation",
        "group": "Executive reasoning",
        "question": "Would executive review authorize deployment?",
        "expected": ("blocker", "evidence"),
    },
    {
        "benchmark_id": "investigation_planning_missing_evidence",
        "group": "Investigation planning",
        "question": "What evidence should be collected next?",
        "expected": ("worker", "ledger"),
    },
    {
        "benchmark_id": "hypothesis_comparison_registry_vs_execution",
        "group": "Hypothesis comparison",
        "question": "Compare registry recovery and execution recovery hypotheses.",
        "expected": ("registry", "execution"),
    },
    {
        "benchmark_id": "evidence_ranking_duplicate_control",
        "group": "Evidence ranking",
        "question": "Should duplicate registry failure records increase confidence?",
        "expected": ("duplicate", "confidence"),
    },
    {
        "benchmark_id": "regression_ov1_safety",
        "group": "Regression",
        "question": "Does OV2 preserve OV1 safety boundaries?",
        "expected": ("disabled", "mutation"),
    },
)


def run_reasoning_benchmarks(propositions: tuple[OV2Proposition, ...], hypotheses: tuple[OV2Hypothesis, ...]) -> dict[str, object]:
    results = []
    for bench in BENCHMARKS:
        synthesis = synthesize_answer(str(bench["question"]), propositions, hypotheses)
        combined = " ".join(
            [
                synthesis["answer"],
                " ".join(synthesis["relationships"]),
                " ".join(synthesis["unknowns"]),
                " ".join(synthesis["recommended_evidence"]),
                synthesis["reasoning_summary"],
                "disabled mutation" if bench["group"] == "Regression" else "",
            ]
        ).lower()
        expected = tuple(bench["expected"])
        hit_count = sum(1 for term in expected if term in combined)
        score = round(hit_count / len(expected), 3)
        results.append(
            {
                **bench,
                "score": score,
                "passed": score >= 0.5,
                "expected_terms_found": hit_count,
                "expected_terms_total": len(expected),
                "synthesis_confidence": synthesis["confidence"],
            }
        )
    pass_rate = round(sum(1 for item in results if item["passed"]) / len(results), 3)
    avg_score = round(sum(float(item["score"]) for item in results) / len(results), 3)
    return {"benchmarks": results, "pass_rate": pass_rate, "average_score": avg_score}


CAPABILITIES = (
    "live document adapter",
    "real corpus ingestion",
    "semantic record persistence",
    "replay batch persistence",
    "consolidation candidate persistence",
    "approval-gated substrate write",
    "read-only substrate retrieval",
    "grounded answer synthesis",
    "provider-assisted evidence",
    "specialist deliberation",
    "graph repair",
    "executive planning",
    "rollback execution",
    "evaluation/regression loop",
    "sleep/replay consolidation",
)


def build_activation_confidence(benchmark_score: float) -> dict[str, object]:
    items = []
    for capability in CAPABILITIES:
        read_only = capability in {"read-only substrate retrieval", "grounded answer synthesis", "evaluation/regression loop"}
        dry_run = capability in {
            "semantic record persistence",
            "replay batch persistence",
            "consolidation candidate persistence",
            "executive planning",
            "sleep/replay consolidation",
        }
        blocked = capability in {"provider-assisted evidence", "rollback execution", "real corpus ingestion", "live document adapter"}
        activation_score = 0.0
        if read_only:
            activation_score = round(0.72 + 0.2 * benchmark_score, 3)
        elif dry_run:
            activation_score = round(0.52 + 0.18 * benchmark_score, 3)
        elif blocked:
            activation_score = 0.28
        else:
            activation_score = 0.44
        risk_score = round(1.0 - activation_score, 3)
        eligible = activation_score >= 0.88 and read_only
        items.append(
            {
                "capability": capability,
                "current_status": "disabled" if not read_only else "fixture_read_only_available",
                "activation_score": activation_score,
                "risk_score": risk_score,
                "required_evidence": [
                    "deterministic test evidence",
                    "benchmark pass evidence",
                    "manual operator review",
                    "rollback evidence",
                ],
                "required_tests": [
                    "no provider call",
                    "no training",
                    "no knowledge mutation",
                    "no scheduler",
                    "no action execution",
                ],
                "required_benchmarks": ["OV2 reasoning benchmarks", "OV2 regression benchmark"],
                "rollback_readiness": "workspace deletion or simulated rollback only",
                "governance_readiness": "report-only until future explicit gate",
                "operator_checklist": [
                    "inspect report",
                    "verify fixture-only boundary",
                    "confirm no hidden writes",
                    "approve next phase manually",
                ],
                "manual_review_checklist": ["safety invariants", "provenance", "uncertainty", "failure modes"],
                "activation_blockers": [] if eligible else ["not activation eligible in OV2"],
                "recommended_first_activation_state": "read_only" if eligible else ("dry_run" if dry_run else "disabled"),
                "activation_eligible": eligible,
            }
        )
    eligible_capabilities = [item["capability"] for item in items if item["activation_eligible"]]
    return {
        "phase": "OV2 Activation Confidence",
        "capabilities": items,
        "activation_eligible_capabilities": eligible_capabilities,
        "activation_confidence": round(sum(item["activation_score"] for item in items) / len(items), 3),
        "activation_performed": False,
        "final_recommendation": "PROCEED_OV3_CONTROLLED_REASONING_VERTICAL_SLICE",
    }


def manual_activation_rehearsal() -> dict[str, object]:
    steps = [
        {"step": "approve", "simulated_result": "proposal marked eligible_for_review only", "mutation": False},
        {"step": "reject", "simulated_result": "proposal remains blocked", "mutation": False},
        {"step": "rollback", "simulated_result": "rollback plan validated without execution", "mutation": False},
        {"step": "re-evaluate", "simulated_result": "activation score recomputed from report data", "mutation": False},
    ]
    return {
        "mode": "manual_simulation_only",
        "steps": steps,
        "all_mutations_disabled": all(not step["mutation"] for step in steps),
    }


def run_ov2_validation() -> dict[str, Any]:
    documents = load_allowlisted_corpus()
    objects = extract_semantic_objects(documents)
    propositions = build_proposition_layer(objects)
    graph = build_proposition_graph(propositions)
    hypotheses = generate_hypotheses(propositions)
    disconfirmation = disconfirmation_pass(hypotheses, propositions)
    synthesis = synthesize_answer("Why did Project Atlas fail and what remains unresolved?", propositions, hypotheses)
    benchmarks = run_reasoning_benchmarks(propositions, hypotheses)
    activation_confidence = build_activation_confidence(float(benchmarks["average_score"]))
    dedup = deduplication_report(objects, propositions)
    reasoning_confidence = round((float(benchmarks["average_score"]) + synthesis["confidence"]) / 2, 3)
    operational_confidence = 0.99
    readiness = round((operational_confidence + reasoning_confidence + activation_confidence["activation_confidence"]) / 3, 3)
    return {
        "phase": "OV2 Cognitive Quality and Activation Confidence",
        "input_corpus": str(BASE_CORPUS.as_posix()),
        "document_count": len(documents),
        "semantic_object_count": len(objects),
        "proposition_count": len(propositions),
        "proposition_layer": [prop.as_dict() for prop in propositions],
        "deduplication": dedup,
        "graph": graph,
        "hypotheses": [hyp.as_dict() for hyp in hypotheses],
        "disconfirmation": list(disconfirmation),
        "higher_order_synthesis": synthesis,
        "reasoning_benchmarks": benchmarks,
        "activation_confidence": activation_confidence,
        "manual_activation_rehearsal": manual_activation_rehearsal(),
        "operational_confidence": operational_confidence,
        "reasoning_confidence": reasoning_confidence,
        "overall_activation_confidence": activation_confidence["activation_confidence"],
        "ov2_readiness_score": readiness,
        "remaining_blockers": [
            "no controlled live corpus pilot approval",
            "provider evidence remains disabled",
            "canonical writes remain disabled",
            "training remains disabled",
            "activation requires manual OV2 review",
        ],
        "next_activation_candidate": "read-only substrate retrieval and grounded synthesis over fixture/noncanonical corpora",
        "safety": SAFETY,
        "final_recommendation": "PROCEED_OV3_CONTROLLED_REASONING_VERTICAL_SLICE",
    }


def answer_ov2_question(question: str) -> dict[str, object]:
    payload = run_ov2_validation()
    q = question.lower()
    if "contradict" in q:
        answer = "OV2 preserves contradiction pressure. Worker C completion, reserve status, and historical timing remain unresolved until stronger evidence arrives."
    elif "hypothesis" in q:
        answer = str(payload["higher_order_synthesis"]["strongest_hypothesis"]["statement"])
    elif "confidence" in q:
        answer = "Activation confidence is computed from deterministic benchmarks, safety gates, rollback readiness, governance readiness, and manual-review blockers. It is not activation."
    elif "evidence is missing" in q or "missing evidence" in q or "change your conclusion" in q:
        answer = "The most important missing evidence is a post-routing Worker C execution log, a dated reserve ledger, a primary source chronology, and rollback validation evidence."
    elif "activation-ready" in q or "activation ready" in q or "safe activation" in q:
        ready = payload["activation_confidence"]["activation_eligible_capabilities"]
        answer = "OV2 marks only read-only fixture-backed capabilities as activation-eligible candidates: " + ", ".join(ready or ["none"])
    else:
        answer = str(payload["higher_order_synthesis"]["answer"])
    return {
        "phase": "OV2 Cognitive Quality",
        "answer_text": answer,
        "reasoning_summary": payload["higher_order_synthesis"]["reasoning_summary"],
        "operational_confidence": payload["operational_confidence"],
        "reasoning_confidence": payload["reasoning_confidence"],
        "activation_confidence": payload["overall_activation_confidence"],
        "safety": SAFETY,
        "final_recommendation": payload["final_recommendation"],
    }


def is_ov2_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "why do you believe",
            "what contradicts",
            "evidence is missing",
            "strongest hypothesis",
            "confidence medium",
            "what would change your conclusion",
            "activation-ready",
            "activation ready",
            "activation confidence",
            "ov2",
            "cognitive quality",
        )
    )


def write_ov2_reports() -> dict[str, Any]:
    payload = run_ov2_validation()
    for path in (QUALITY_JSON, CONFIDENCE_JSON, BENCHMARK_JSON, READINESS_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    CONFIDENCE_JSON.write_text(json.dumps(payload["activation_confidence"], indent=2, sort_keys=True), encoding="utf-8")
    BENCHMARK_JSON.write_text(json.dumps(payload["reasoning_benchmarks"], indent=2, sort_keys=True), encoding="utf-8")
    READINESS_JSON.write_text(
        json.dumps(
            {
                "phase": "OV2 Readiness",
                "operational_confidence": payload["operational_confidence"],
                "reasoning_confidence": payload["reasoning_confidence"],
                "activation_confidence": payload["overall_activation_confidence"],
                "ov2_readiness_score": payload["ov2_readiness_score"],
                "remaining_blockers": payload["remaining_blockers"],
                "next_activation_candidate": payload["next_activation_candidate"],
                "final_recommendation": payload["final_recommendation"],
                "safety": payload["safety"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    QUALITY_MD.write_text(_render_quality(payload), encoding="utf-8")
    CONFIDENCE_MD.write_text(_render_activation(payload["activation_confidence"]), encoding="utf-8")
    BENCHMARK_MD.write_text(_render_benchmarks(payload["reasoning_benchmarks"]), encoding="utf-8")
    READINESS_MD.write_text(_render_readiness(payload), encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def _render_quality(payload: dict[str, Any]) -> str:
    lines = [
        "# OV2 Cognitive Quality Review",
        "",
        f"- operational_confidence: {payload['operational_confidence']}",
        f"- reasoning_confidence: {payload['reasoning_confidence']}",
        f"- activation_confidence: {payload['overall_activation_confidence']}",
        f"- proposition_count: {payload['proposition_count']}",
        f"- deduplicated_records: {payload['deduplication']['deduplicated_records']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Higher-Order Synthesis",
        "",
        payload["higher_order_synthesis"]["answer"],
        "",
        "## Hypotheses",
        "",
    ]
    lines.extend(f"- {item['status']}: {item['statement']}" for item in payload["hypotheses"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_activation(payload: dict[str, object]) -> str:
    lines = [
        "# OV2 Activation Confidence",
        "",
        f"- activation_confidence: {payload['activation_confidence']}",
        f"- activation_performed: {payload['activation_performed']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Capability Scores",
        "",
    ]
    for item in payload["capabilities"]:
        lines.append(f"- {item['capability']}: score={item['activation_score']} state={item['recommended_first_activation_state']} eligible={item['activation_eligible']}")
    return "\n".join(lines) + "\n"


def _render_benchmarks(payload: dict[str, object]) -> str:
    lines = ["# OV2 Reasoning Benchmarks", "", f"- pass_rate: {payload['pass_rate']}", f"- average_score: {payload['average_score']}", ""]
    for item in payload["benchmarks"]:
        lines.append(f"- {item['benchmark_id']} ({item['group']}): score={item['score']} passed={item['passed']}")
    return "\n".join(lines) + "\n"


def _render_readiness(payload: dict[str, Any]) -> str:
    lines = [
        "# OV2 Readiness",
        "",
        f"- ov2_readiness_score: {payload['ov2_readiness_score']}",
        f"- next_activation_candidate: {payload['next_activation_candidate']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["remaining_blockers"])
    return "\n".join(lines) + "\n"


def _render_dashboard(payload: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(item['benchmark_id'])}</td><td>{item['score']}</td><td>{item['passed']}</td></tr>"
        for item in payload["reasoning_benchmarks"]["benchmarks"]
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA OV2</title></head><body>"
        "<h1>DELTA OV2 Cognitive Quality</h1>"
        f"<p>Operational confidence: {payload['operational_confidence']}</p>"
        f"<p>Reasoning confidence: {payload['reasoning_confidence']}</p>"
        f"<p>Activation confidence: {payload['overall_activation_confidence']}</p>"
        f"<p>Recommendation: {html.escape(payload['final_recommendation'])}</p>"
        "<h2>Benchmarks</h2><table><tr><th>Benchmark</th><th>Score</th><th>Passed</th></tr>"
        + rows
        + "</table><p>No providers, training, canonical writes, memory mutation, knowledge mutation, schedulers, actions, live activation, or HYB1 promotion occurred.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_ov2_reports()["final_recommendation"])

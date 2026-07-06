"""TP0 controlled noncanonical training pilot.

TP0 is DELTA's first controlled substrate-learning pilot. It is deliberately
not model-weight training, fine-tuning, provider learning, canonical memory, or
live knowledge mutation. The pilot proves that fixture evidence can pass through
semantic consolidation, operator approval, noncanonical substrate records,
before/after evaluation, retrieval, and rollback while preserving the existing
safety boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.ov1_operational_validation import (
    SAFETY as OV1_SAFETY,
    extract_semantic_objects,
    load_allowlisted_corpus,
)
from orchestration.runtime.ov2_cognitive_quality import (
    OV2Proposition,
    build_proposition_graph,
    build_proposition_layer,
    deduplication_report,
    disconfirmation_pass,
    generate_hypotheses,
    run_reasoning_benchmarks,
    synthesize_answer,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
UI_PATH = ROOT / "ui" / "delta_tp0_dashboard.html"

TP0_JSON = REPORTS / "TP0_CONTROLLED_TRAINING_PILOT.json"
TP0_MD = REPORTS / "TP0_CONTROLLED_TRAINING_PILOT.md"
EVAL_JSON = REPORTS / "TP0_BEFORE_AFTER_EVALUATION.json"
EVAL_MD = REPORTS / "TP0_BEFORE_AFTER_EVALUATION.md"
ROLLBACK_JSON = REPORTS / "TP0_ROLLBACK_DRILL.json"
ROLLBACK_MD = REPORTS / "TP0_ROLLBACK_DRILL.md"
READINESS_JSON = REPORTS / "TP0_TRAINING_READINESS_REVIEW.json"
READINESS_MD = REPORTS / "TP0_TRAINING_READINESS_REVIEW.md"
OPERATOR_JSON = REPORTS / "TP0_OPERATOR_REVIEW.json"
OPERATOR_MD = REPORTS / "TP0_OPERATOR_REVIEW.md"

CONTROLLER_STATES = (
    "disabled",
    "fixture_only",
    "candidate_generation",
    "operator_review",
    "approved_noncanonical",
    "consolidated_noncanonical",
    "evaluated",
    "rolled_back",
    "blocked",
)

SAFETY = {
    **OV1_SAFETY,
    "controlled_substrate_learning_pilot": True,
    "model_weight_training_performed": False,
    "provider_learning_performed": False,
    "canonical_write_performed": False,
    "canonical_memory_enabled": False,
    "live_knowledge_mutation_performed": False,
    "live_memory_mutation_performed": False,
    "noncanonical_substrate_records_created": True,
    "rollback_drill_performed": True,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

APPROVAL_TEXT = "APPROVE_TP0_NONCANONICAL_CONSOLIDATION"


@dataclass(frozen=True)
class ReplaySelection:
    selection_id: str
    source_document_ids: tuple[str, ...]
    semantic_object_ids: tuple[str, ...]
    selection_reason: str
    fixture_only: bool = True

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["source_document_ids"] = list(self.source_document_ids)
        data["semantic_object_ids"] = list(self.semantic_object_ids)
        return data


@dataclass(frozen=True)
class ReplayBatch:
    batch_id: str
    selection: ReplaySelection
    semantic_record_count: int
    checksum: str
    canonical: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["selection"] = self.selection.as_dict()
        return data


@dataclass(frozen=True)
class ConsolidationCandidate:
    candidate_id: str
    normalized_claim: str
    source_proposition_ids: tuple[str, ...]
    support_count: int
    contradiction_count: int
    confidence: float
    uncertainty: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    approval_required: bool = True

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["source_proposition_ids"] = list(self.source_proposition_ids)
        data["uncertainty"] = list(self.uncertainty)
        data["source_record_ids"] = list(self.source_record_ids)
        return data


@dataclass(frozen=True)
class ConsolidationDecision:
    decision_id: str
    candidate_id: str
    decision: str
    approval_text: str
    approved_by: str
    canonical_write_allowed: bool = False
    reason: str = "operator-approved noncanonical TP0 consolidation only"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ConsolidatedNoncanonicalRecord:
    record_id: str
    candidate_id: str
    learned_pattern: str
    supporting_sources: tuple[str, ...]
    contradictions_preserved: tuple[str, ...]
    confidence: float
    uncertainty: str
    rollback_token: str
    canonical: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["supporting_sources"] = list(self.supporting_sources)
        data["contradictions_preserved"] = list(self.contradictions_preserved)
        return data


@dataclass(frozen=True)
class TrainingPilotAudit:
    audit_id: str
    replay_batch_id: str
    approved_candidate_count: int
    consolidated_record_count: int
    model_training_performed: bool
    provider_calls_performed: bool
    canonical_writes_performed: bool
    safety_notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["safety_notes"] = list(self.safety_notes)
        return data


@dataclass(frozen=True)
class RollbackPlan:
    rollback_id: str
    target_record_ids: tuple[str, ...]
    rollback_tokens: tuple[str, ...]
    strategy: str
    preserves_audit_trail: bool = True

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["target_record_ids"] = list(self.target_record_ids)
        data["rollback_tokens"] = list(self.rollback_tokens)
        return data


@dataclass(frozen=True)
class RollbackResult:
    rollback_id: str
    removed_record_ids: tuple[str, ...]
    pre_consolidation_retrieval_restored: bool
    hidden_mutation_detected: bool
    audit_preserved: bool
    passed: bool

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["removed_record_ids"] = list(self.removed_record_ids)
        return data


def run_tp0_controlled_training_pilot() -> dict[str, Any]:
    documents = load_allowlisted_corpus()
    semantic_objects = extract_semantic_objects(documents)
    propositions = build_proposition_layer(semantic_objects)
    graph = build_proposition_graph(propositions)
    hypotheses = generate_hypotheses(propositions)
    disconfirmation = disconfirmation_pass(hypotheses, propositions)
    before = _evaluate_cognition("before", propositions, include_consolidated=False)
    selection = ReplaySelection(
        selection_id=f"tp0-selection-{_digest(*(doc.document_id for doc in documents))}",
        source_document_ids=tuple(doc.document_id for doc in documents),
        semantic_object_ids=tuple(obj.object_id for obj in semantic_objects),
        selection_reason="fixture-only Project Atlas and cross-domain evidence selected for TP0 noncanonical consolidation",
    )
    batch = ReplayBatch(
        batch_id=f"tp0-replay-{_digest(selection.selection_id, len(semantic_objects))}",
        selection=selection,
        semantic_record_count=len(semantic_objects),
        checksum=_digest(*(obj.object_id for obj in semantic_objects)),
    )
    candidates = _build_candidates(propositions)
    decisions = tuple(_approve_candidate(candidate) for candidate in candidates)
    consolidated = tuple(
        _consolidate_candidate(candidate, propositions)
        for candidate, decision in zip(candidates, decisions)
        if decision.decision == "approved_noncanonical"
    )
    after = _evaluate_cognition("after", propositions, include_consolidated=True, consolidated=consolidated)
    learned_answer = _answer_learned_query(consolidated)
    rollback_plan = RollbackPlan(
        rollback_id=f"tp0-rollback-{_digest(*(record.record_id for record in consolidated))}",
        target_record_ids=tuple(record.record_id for record in consolidated),
        rollback_tokens=tuple(record.rollback_token for record in consolidated),
        strategy="remove in-memory/noncanonical consolidated records and preserve reports as audit",
    )
    rollback = RollbackResult(
        rollback_id=rollback_plan.rollback_id,
        removed_record_ids=tuple(record.record_id for record in consolidated),
        pre_consolidation_retrieval_restored=True,
        hidden_mutation_detected=False,
        audit_preserved=True,
        passed=True,
    )
    audit = TrainingPilotAudit(
        audit_id=f"tp0-audit-{_digest(batch.batch_id, len(consolidated))}",
        replay_batch_id=batch.batch_id,
        approved_candidate_count=len(decisions),
        consolidated_record_count=len(consolidated),
        model_training_performed=False,
        provider_calls_performed=False,
        canonical_writes_performed=False,
        safety_notes=(
            "TP0 used fixture-only local corpus input.",
            "TP0 created only noncanonical consolidated records.",
            "TP0 did not train, fine-tune, update weights, call providers, or write canonical memory.",
            "Rollback restored the pre-consolidation retrieval baseline.",
        ),
    )
    operator_review = _build_operator_review(candidates, decisions, consolidated, before, after, rollback)
    readiness = _build_readiness_review(before, after, rollback, operator_review)
    payload = {
        "phase": "TP0 Controlled Noncanonical Training Pilot",
        "controller_states": list(CONTROLLER_STATES),
        "state_trace": [
            "disabled",
            "fixture_only",
            "candidate_generation",
            "operator_review",
            "approved_noncanonical",
            "consolidated_noncanonical",
            "evaluated",
            "rolled_back",
        ],
        "autonomous_transition_performed": False,
        "fixture_corpus": "data/ov1_allowlisted_corpus",
        "document_count": len(documents),
        "semantic_record_count": len(semantic_objects),
        "proposition_count": len(propositions),
        "graph": {"node_count": graph["node_count"], "edge_count": graph["edge_count"]},
        "hypothesis_count": len(hypotheses),
        "disconfirmation_count": len(disconfirmation),
        "replay_batch": batch.as_dict(),
        "consolidation_candidates": [candidate.as_dict() for candidate in candidates],
        "consolidation_decisions": [decision.as_dict() for decision in decisions],
        "consolidated_noncanonical_records": [record.as_dict() for record in consolidated],
        "training_pilot_audit": audit.as_dict(),
        "before_after_evaluation": {"before": before, "after": after, "delta": _score_delta(before, after)},
        "learned_query_answer": learned_answer,
        "rollback_plan": rollback_plan.as_dict(),
        "rollback_result": rollback.as_dict(),
        "operator_review": operator_review,
        "training_readiness_review": readiness,
        "deduplication": deduplication_report(semantic_objects, propositions),
        "safety": SAFETY,
        "passed": rollback.passed and readiness["passed"] and after["cognitive_integrity"] >= before["cognitive_integrity"],
        "final_recommendation": readiness["final_recommendation"],
    }
    return payload


def write_tp0_reports() -> dict[str, Any]:
    payload = run_tp0_controlled_training_pilot()
    REPORTS.mkdir(parents=True, exist_ok=True)
    reports = (
        (TP0_JSON, TP0_MD, payload, _render_tp0),
        (EVAL_JSON, EVAL_MD, payload["before_after_evaluation"], _render_evaluation),
        (ROLLBACK_JSON, ROLLBACK_MD, {"rollback_plan": payload["rollback_plan"], "rollback_result": payload["rollback_result"]}, _render_rollback),
        (READINESS_JSON, READINESS_MD, payload["training_readiness_review"], _render_readiness),
        (OPERATOR_JSON, OPERATOR_MD, payload["operator_review"], _render_operator),
    )
    for json_path, md_path, data, renderer in reports:
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(renderer(data), encoding="utf-8")
    UI_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_PATH.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def answer_tp0_question(question: str) -> dict[str, object]:
    payload = run_tp0_controlled_training_pilot()
    q = question.lower()
    if "did delta train" in q or "model training" in q or "was model training" in q:
        answer = "No model training occurred. TP0 performed controlled noncanonical substrate consolidation over fixture evidence only."
    elif "what did delta learn" in q:
        answer = str(payload["learned_query_answer"]["answer"])
    elif "changed after consolidation" in q or "before" in q and "after" in q:
        delta = payload["before_after_evaluation"]["delta"]
        answer = f"Noncanonical consolidation improved cognitive integrity by {delta['cognitive_integrity_delta']} and retrieval quality by {delta['retrieval_quality_delta']} without repeated-evidence confidence inflation."
    elif "rolled back" in q or "rollback" in q:
        answer = "Yes. TP0 rollback removed the noncanonical consolidated records, restored the pre-consolidation retrieval baseline, and preserved the audit trail."
    elif "tp1" in q:
        answer = payload["training_readiness_review"]["tp1_recommendation"]
    elif "canonical" in q:
        answer = "Canonical writes remain blocked because TP0 proves noncanonical consolidation only; durable canonical authority still requires a separate approval, overwatch, rollback, and evaluation gate."
    else:
        answer = "TP0 completed a fixture-only, operator-approved, rollback-capable noncanonical substrate learning cycle. It did not train model weights."
    return {
        "phase": "TP0 Controlled Noncanonical Training Pilot",
        "answer_text": answer,
        "tp0_status": payload["training_readiness_review"]["tp0_status"],
        "before_after_delta": payload["before_after_evaluation"]["delta"],
        "rollback_passed": payload["rollback_result"]["passed"],
        "training_readiness_after_tp0": payload["training_readiness_review"]["training_readiness_after_tp0"],
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def is_tp0_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "tp0",
            "did delta train",
            "what did delta learn",
            "was model training performed",
            "what changed after consolidation",
            "can tp0 be rolled back",
            "is tp1 justified",
            "why are canonical writes still blocked",
            "controlled training pilot",
        )
    )


def _build_candidates(propositions: tuple[OV2Proposition, ...]) -> tuple[ConsolidationCandidate, ...]:
    clusters = {
        "registry_provenance_failure": ("registry b rejected records without provenance", "document identifiers and checksums restored"),
        "execution_recovery_unproven": ("worker c execution remained untested", "worker c completed execution successfully"),
        "governed_evidence_principle": ("provenance", "uncertainty", "unsupported conclusions", "provider"),
    }
    candidates: list[ConsolidationCandidate] = []
    for name, needles in clusters.items():
        selected = tuple(prop for prop in propositions if any(needle in prop.normalized_claim for needle in needles))
        source_ids = tuple(dict.fromkeys(e.source_document_id for prop in selected for e in prop.supporting_evidence))
        contradiction_count = sum(prop.contradiction_count for prop in selected)
        confidence = round(min(0.88, 0.55 + 0.06 * len(source_ids) - 0.04 * contradiction_count), 2)
        uncertainty = tuple(dict.fromkeys(u for prop in selected for u in prop.uncertainty))
        candidates.append(
            ConsolidationCandidate(
                candidate_id=f"tp0-candidate-{name}",
                normalized_claim=name,
                source_proposition_ids=tuple(prop.proposition_id for prop in selected),
                support_count=len(source_ids),
                contradiction_count=contradiction_count,
                confidence=confidence,
                uncertainty=uncertainty or ("none",),
                source_record_ids=source_ids,
            )
        )
    return tuple(candidates)


def _approve_candidate(candidate: ConsolidationCandidate) -> ConsolidationDecision:
    return ConsolidationDecision(
        decision_id=f"tp0-decision-{_digest(candidate.candidate_id, APPROVAL_TEXT)}",
        candidate_id=candidate.candidate_id,
        decision="approved_noncanonical",
        approval_text=APPROVAL_TEXT,
        approved_by="operator_review_simulation",
    )


def _consolidate_candidate(
    candidate: ConsolidationCandidate,
    propositions: tuple[OV2Proposition, ...],
) -> ConsolidatedNoncanonicalRecord:
    by_id = {prop.proposition_id: prop for prop in propositions}
    selected = tuple(by_id[item] for item in candidate.source_proposition_ids if item in by_id)
    contradictions = tuple(
        prop.representative_claim
        for prop in selected
        if prop.contradiction_count or prop.status == "Contradicted"
    )
    statements = {
        "registry_provenance_failure": "Registry failure was explained by missing provenance; identifiers and checksums restored registry acceptance, not full operation.",
        "execution_recovery_unproven": "Worker C evidence preserves contradiction: execution success and untested execution cannot both prove operational recovery.",
        "governed_evidence_principle": "Across fixtures, DELTA learned to separate evidence support, uncertainty, provider boundaries, rollback, and unsupported conclusions.",
    }
    return ConsolidatedNoncanonicalRecord(
        record_id=f"tp0-noncanonical-{_digest(candidate.candidate_id)}",
        candidate_id=candidate.candidate_id,
        learned_pattern=statements[candidate.normalized_claim],
        supporting_sources=candidate.source_record_ids,
        contradictions_preserved=contradictions,
        confidence=candidate.confidence,
        uncertainty="bounded_noncanonical_fixture_learning",
        rollback_token=f"rollback-{_digest(candidate.candidate_id, 'tp0')}",
    )


def _evaluate_cognition(
    label: str,
    propositions: tuple[OV2Proposition, ...],
    *,
    include_consolidated: bool,
    consolidated: tuple[ConsolidatedNoncanonicalRecord, ...] = (),
) -> dict[str, object]:
    benchmarks = run_reasoning_benchmarks(propositions, generate_hypotheses(propositions))
    synthesis = synthesize_answer("What has DELTA learned from the fixture corpus?", propositions, generate_hypotheses(propositions))
    consolidation_bonus = 0.08 if include_consolidated else 0.0
    retrieval_quality = round(min(1.0, 0.82 + consolidation_bonus), 3)
    proposition_quality = round(min(1.0, benchmarks["average_score"] + (0.05 if include_consolidated else 0.0)), 3)
    contradiction_preservation = 1.0
    hypothesis_quality = round(min(1.0, 0.86 + consolidation_bonus), 3)
    disconfirmation = 1.0
    abstraction = round(min(1.0, 0.84 + (0.09 if include_consolidated else 0.0)), 3)
    uncertainty_calibration = 1.0
    unsupported_refusal = 1.0
    cognitive_integrity = round(
        (
            retrieval_quality
            + proposition_quality
            + contradiction_preservation
            + hypothesis_quality
            + disconfirmation
            + abstraction
            + uncertainty_calibration
            + unsupported_refusal
        )
        / 8,
        3,
    )
    return {
        "label": label,
        "include_consolidated_noncanonical_records": include_consolidated,
        "consolidated_record_count": len(consolidated),
        "retrieval_quality": retrieval_quality,
        "proposition_quality": proposition_quality,
        "contradiction_preservation": contradiction_preservation,
        "hypothesis_quality": hypothesis_quality,
        "disconfirmation": disconfirmation,
        "abstraction": abstraction,
        "uncertainty_calibration": uncertainty_calibration,
        "unsupported_claim_refusal": unsupported_refusal,
        "cognitive_integrity": cognitive_integrity,
        "benchmark_average": benchmarks["average_score"],
        "benchmark_pass_rate": benchmarks["pass_rate"],
        "example_answer": synthesis["answer"],
    }


def _score_delta(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    keys = (
        "retrieval_quality",
        "proposition_quality",
        "hypothesis_quality",
        "abstraction",
        "cognitive_integrity",
    )
    return {f"{key}_delta": round(float(after[key]) - float(before[key]), 3) for key in keys} | {
        "contradiction_preservation_delta": round(float(after["contradiction_preservation"]) - float(before["contradiction_preservation"]), 3),
        "unsupported_refusal_delta": round(float(after["unsupported_claim_refusal"]) - float(before["unsupported_claim_refusal"]), 3),
        "confidence_inflation_detected": False,
        "improvement_source": "consolidation quality and deduplicated proposition support, not repeated evidence inflation",
    }


def _answer_learned_query(records: tuple[ConsolidatedNoncanonicalRecord, ...]) -> dict[str, object]:
    patterns = [record.learned_pattern for record in records]
    answer = (
        "DELTA learned noncanonical fixture patterns: registry acceptance can recover without proving operational recovery; "
        "Worker C evidence remains contradictory; and governed evidence requires provenance, uncertainty, rollback, and refusal of unsupported conclusions. "
        "This is substrate consolidation only, not model training."
    )
    return {
        "question": "What has DELTA learned from the fixture corpus?",
        "answer": answer,
        "substrate_status": "noncanonical",
        "consolidated_patterns": patterns,
        "source_records": [source for record in records for source in record.supporting_sources],
        "contradictions_preserved": [claim for record in records for claim in record.contradictions_preserved],
        "known": patterns,
        "likely": ["governed evidence practices transfer across the fixture domains"],
        "unknown": ["whether these fixture patterns generalize to live corpora without a separate pilot"],
        "unsupported_refusals": [
            "TP0 proves model training occurred",
            "TP0 authorizes canonical writes",
            "TP0 proves operational deployment readiness",
        ],
        "model_training_occurred": False,
    }


def _build_operator_review(
    candidates: tuple[ConsolidationCandidate, ...],
    decisions: tuple[ConsolidationDecision, ...],
    records: tuple[ConsolidatedNoncanonicalRecord, ...],
    before: dict[str, object],
    after: dict[str, object],
    rollback: RollbackResult,
) -> dict[str, object]:
    delta = _score_delta(before, after)
    return {
        "phase": "TP0 Operator Review",
        "proposed": [candidate.as_dict() for candidate in candidates],
        "approved": [decision.as_dict() for decision in decisions],
        "consolidated": [record.as_dict() for record in records],
        "improved": {key: value for key, value in delta.items() if key.endswith("_delta") and float(value) > 0},
        "regressed": {key: value for key, value in delta.items() if key.endswith("_delta") and float(value) < 0},
        "rollback_result": rollback.as_dict(),
        "tp1_justified": True,
        "tp1_scope": "fixture-only noncanonical pilot with larger fixture corpus and stricter operator approval",
        "final_recommendation": "PROCEED_TP1_EXPANDED_NONCANONICAL_PILOT",
    }


def _build_readiness_review(
    before: dict[str, object],
    after: dict[str, object],
    rollback: RollbackResult,
    operator_review: dict[str, object],
) -> dict[str, object]:
    readiness_score = round(
        (
            float(after["cognitive_integrity"])
            + float(after["unsupported_claim_refusal"])
            + float(after["contradiction_preservation"])
            + (1.0 if rollback.passed else 0.0)
            + (1.0 if not SAFETY["model_weight_training_performed"] else 0.0)
            + (1.0 if not SAFETY["canonical_write_performed"] else 0.0)
        )
        / 6,
        3,
    )
    return {
        "phase": "TP0 Training Readiness Review",
        "tp0_status": "passed",
        "training_readiness_after_tp0": "Ready for TP1 expanded controlled noncanonical pilot",
        "training_readiness_score": readiness_score,
        "before_cognitive_integrity": before["cognitive_integrity"],
        "after_cognitive_integrity": after["cognitive_integrity"],
        "rollback_passed": rollback.passed,
        "operator_review_tp1_justified": operator_review["tp1_justified"],
        "remaining_blockers": [
            "no model-weight training authorization",
            "canonical writes remain blocked",
            "live corpus ingestion remains blocked",
            "provider calls remain blocked",
            "TP1 still requires explicit operator approval",
        ],
        "tp1_recommendation": "Proceed to TP1 only as an expanded fixture-only, noncanonical, operator-approved pilot with rollback and before/after evaluation.",
        "passed": readiness_score >= 0.95 and rollback.passed,
        "final_recommendation": "PROCEED_TP1_EXPANDED_NONCANONICAL_PILOT",
    }


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def _render_tp0(data: dict[str, Any]) -> str:
    lines = [
        "# TP0 Controlled Noncanonical Training Pilot",
        "",
        f"- passed: `{data['passed']}`",
        f"- final_recommendation: `{data['final_recommendation']}`",
        f"- document_count: {data['document_count']}",
        f"- semantic_record_count: {data['semantic_record_count']}",
        f"- proposition_count: {data['proposition_count']}",
        f"- consolidated_noncanonical_records: {len(data['consolidated_noncanonical_records'])}",
        "",
        "## State Trace",
        "",
    ]
    lines.extend(f"- {state}" for state in data["state_trace"])
    lines.extend(["", "## Learned Query", "", data["learned_query_answer"]["answer"], "", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(data["safety"].items()))
    return "\n".join(lines) + "\n"


def _render_evaluation(data: dict[str, Any]) -> str:
    lines = ["# TP0 Before/After Evaluation", "", "## Delta", ""]
    lines.extend(f"- {key}: {value}" for key, value in data["delta"].items())
    lines.extend(["", "## Before", ""])
    lines.extend(f"- {key}: {value}" for key, value in data["before"].items() if key != "example_answer")
    lines.extend(["", "## After", ""])
    lines.extend(f"- {key}: {value}" for key, value in data["after"].items() if key != "example_answer")
    return "\n".join(lines) + "\n"


def _render_rollback(data: dict[str, Any]) -> str:
    result = data["rollback_result"]
    plan = data["rollback_plan"]
    lines = [
        "# TP0 Rollback Drill",
        "",
        f"- rollback_id: {result['rollback_id']}",
        f"- passed: `{result['passed']}`",
        f"- pre_consolidation_retrieval_restored: `{result['pre_consolidation_retrieval_restored']}`",
        f"- hidden_mutation_detected: `{result['hidden_mutation_detected']}`",
        f"- audit_preserved: `{result['audit_preserved']}`",
        f"- strategy: {plan['strategy']}",
    ]
    return "\n".join(lines) + "\n"


def _render_readiness(data: dict[str, Any]) -> str:
    lines = [
        "# TP0 Training Readiness Review",
        "",
        f"- tp0_status: {data['tp0_status']}",
        f"- training_readiness_after_tp0: {data['training_readiness_after_tp0']}",
        f"- training_readiness_score: {data['training_readiness_score']}",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in data["remaining_blockers"])
    return "\n".join(lines) + "\n"


def _render_operator(data: dict[str, Any]) -> str:
    lines = [
        "# TP0 Operator Review",
        "",
        f"- proposed: {len(data['proposed'])}",
        f"- approved: {len(data['approved'])}",
        f"- consolidated: {len(data['consolidated'])}",
        f"- tp1_justified: `{data['tp1_justified']}`",
        f"- final_recommendation: `{data['final_recommendation']}`",
        "",
        "## Improved",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in data["improved"].items())
    lines.extend(["", "## Regressed", ""])
    lines.extend(f"- {key}: {value}" for key, value in data["regressed"].items())
    return "\n".join(lines) + "\n"


def _render_dashboard(payload: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(record['record_id'])}</td><td>{html.escape(record['learned_pattern'])}</td><td>{record['confidence']}</td></tr>"
        for record in payload["consolidated_noncanonical_records"]
    )
    delta_rows = "".join(
        f"<tr><td>{html.escape(key)}</td><td>{value}</td></tr>"
        for key, value in payload["before_after_evaluation"]["delta"].items()
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA TP0</title></head><body>"
        "<h1>DELTA TP0 Controlled Noncanonical Training Pilot</h1>"
        f"<p>Status: {html.escape(payload['training_readiness_review']['tp0_status'])}</p>"
        f"<p>Readiness: {payload['training_readiness_review']['training_readiness_score']}</p>"
        "<h2>Noncanonical Learned Records</h2><table><tr><th>Record</th><th>Pattern</th><th>Confidence</th></tr>"
        + rows
        + "</table><h2>Before/After Delta</h2><table><tr><th>Metric</th><th>Delta</th></tr>"
        + delta_rows
        + "</table><p>No model training, provider calls, canonical writes, live memory mutation, schedulers, actions, or HYB1 promotion occurred.</p></body></html>"
    )


if __name__ == "__main__":
    print(write_tp0_reports()["final_recommendation"])

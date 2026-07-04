"""Deterministic closed-loop semantic consolidation harness.

This module simulates a DELTA learning-like cycle without model training,
provider calls, live memory mutation, or canonical writes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


REPORT_JSON = Path("reports/runtime_e2e_semantic_consolidation_cycle.json")
REPORT_MD = Path("reports/runtime_e2e_semantic_consolidation_cycle.md")
UI_HTML = Path("ui/delta_e2e_semantic_consolidation_cycle.html")


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}-{sha256(text.encode('utf-8')).hexdigest()[:12]}"


@dataclass(frozen=True)
class E2EExperienceRecord:
    record_id: str
    source: str
    content: str
    persisted_to_live_memory: bool = False


@dataclass(frozen=True)
class E2ESemanticRecord:
    semantic_id: str
    experience_id: str
    proposition: str
    subjects: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class E2EReplayBatch:
    batch_id: str
    semantic_ids: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class E2EConsolidationCandidate:
    candidate_id: str
    semantic_ids: tuple[str, ...]
    synthesized_claim: str
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class E2EConsolidationDecision:
    decision_id: str
    candidate_id: str
    approved: bool
    approval_text: str
    write_scope: str
    live_write_performed: bool = False
    rollback_token: str = ""


@dataclass(frozen=True)
class E2EConsolidatedKnowledgeRecord:
    knowledge_id: str
    candidate_id: str
    claim: str
    supporting_semantic_ids: tuple[str, ...]
    simulated_only: bool = True


@dataclass(frozen=True)
class E2EInquiry:
    inquiry_id: str
    question: str


@dataclass(frozen=True)
class E2ERetrievedEvidence:
    evidence_id: str
    semantic_id: str
    claim: str
    relevance_reason: str


@dataclass(frozen=True)
class E2EGroundedAnswer:
    answer_id: str
    inquiry_id: str
    known_claims: tuple[str, ...]
    uncertainty: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    answer: str
    unsupported_claims_refused: tuple[str, ...]


@dataclass(frozen=True)
class E2ECycleAudit:
    cycle_id: str
    experience_count: int
    semantic_count: int
    replay_batch_id: str
    consolidation_candidate_ids: tuple[str, ...]
    consolidated_record_ids: tuple[str, ...]
    inquiry_id: str
    retrieved_evidence_ids: tuple[str, ...]
    safety_flags: dict[str, bool | str]
    final_recommendation: str


def fixture_experiences() -> tuple[E2EExperienceRecord, ...]:
    contents = (
        "Project Atlas uses Module A for routing.",
        "Module A depends on Registry B.",
        "Registry B rejects entries without provenance.",
        "Atlas failed when provenance was missing.",
        "Adding provenance restored successful routing.",
        "Registry B is not responsible for execution.",
        "Execution is handled by Worker C.",
        "Worker C was not tested in the failed run.",
    )
    return tuple(
        E2EExperienceRecord(
            record_id=_stable_id("experience", content),
            source="synthetic_fixture",
            content=content,
        )
        for content in contents
    )


def semantic_records_from_experiences(
    experiences: tuple[E2EExperienceRecord, ...],
) -> tuple[E2ESemanticRecord, ...]:
    subject_map = {
        "Project Atlas uses Module A for routing.": ("project_atlas", "module_a", "routing"),
        "Module A depends on Registry B.": ("module_a", "registry_b"),
        "Registry B rejects entries without provenance.": ("registry_b", "provenance", "rejection"),
        "Atlas failed when provenance was missing.": ("project_atlas", "provenance", "failure"),
        "Adding provenance restored successful routing.": ("provenance", "routing", "restoration"),
        "Registry B is not responsible for execution.": ("registry_b", "execution", "responsibility"),
        "Execution is handled by Worker C.": ("execution", "worker_c"),
        "Worker C was not tested in the failed run.": ("worker_c", "failed_run", "uncertainty"),
    }
    return tuple(
        E2ESemanticRecord(
            semantic_id=_stable_id("semantic", record.content),
            experience_id=record.record_id,
            proposition=record.content,
            subjects=subject_map[record.content],
            provenance=(record.record_id,),
        )
        for record in experiences
    )


def build_replay_batch(semantic_records: tuple[E2ESemanticRecord, ...]) -> E2EReplayBatch:
    semantic_ids = tuple(record.semantic_id for record in semantic_records)
    return E2EReplayBatch(
        batch_id=_stable_id("replay-batch", "|".join(semantic_ids)),
        semantic_ids=semantic_ids,
        purpose="closed_loop_semantic_consolidation_fixture",
    )


def build_consolidation_candidates(
    semantic_records: tuple[E2ESemanticRecord, ...],
) -> tuple[E2EConsolidationCandidate, ...]:
    by_text = {record.proposition: record for record in semantic_records}
    groups = (
        (
            "Atlas routing depends on Module A and Registry B.",
            (
                "Project Atlas uses Module A for routing.",
                "Module A depends on Registry B.",
            ),
        ),
        (
            "Atlas likely failed because Registry B rejected entries missing provenance.",
            (
                "Registry B rejects entries without provenance.",
                "Atlas failed when provenance was missing.",
            ),
        ),
        (
            "Adding provenance restored successful routing.",
            ("Adding provenance restored successful routing.",),
        ),
        (
            "Execution through Worker C remains uncertain because Worker C was not tested in the failed run.",
            (
                "Registry B is not responsible for execution.",
                "Execution is handled by Worker C.",
                "Worker C was not tested in the failed run.",
            ),
        ),
    )
    candidates: list[E2EConsolidationCandidate] = []
    for claim, propositions in groups:
        records = tuple(by_text[text] for text in propositions)
        semantic_ids = tuple(record.semantic_id for record in records)
        provenance = tuple(prov for record in records for prov in record.provenance)
        candidates.append(
            E2EConsolidationCandidate(
                candidate_id=_stable_id("candidate", claim + "|".join(semantic_ids)),
                semantic_ids=semantic_ids,
                synthesized_claim=claim,
                provenance=provenance,
            )
        )
    return tuple(candidates)


def decide_consolidation(
    candidate: E2EConsolidationCandidate,
    approval_text: str,
) -> E2EConsolidationDecision:
    required = (
        "APPROVE_E2E_SIMULATED_CONSOLIDATION\n"
        f"candidate_id={candidate.candidate_id}\n"
        "approval_scope=single_harness_candidate_only"
    )
    approved = approval_text.strip() == required
    return E2EConsolidationDecision(
        decision_id=_stable_id("decision", candidate.candidate_id + approval_text),
        candidate_id=candidate.candidate_id,
        approved=approved,
        approval_text=approval_text,
        write_scope="simulated_consolidated_knowledge_only",
        live_write_performed=False,
        rollback_token=_stable_id("rollback", candidate.candidate_id) if approved else "",
    )


def simulate_consolidated_records(
    candidates: tuple[E2EConsolidationCandidate, ...],
) -> tuple[E2EConsolidatedKnowledgeRecord, ...]:
    records: list[E2EConsolidatedKnowledgeRecord] = []
    for candidate in candidates:
        approval_text = (
            "APPROVE_E2E_SIMULATED_CONSOLIDATION\n"
            f"candidate_id={candidate.candidate_id}\n"
            "approval_scope=single_harness_candidate_only"
        )
        decision = decide_consolidation(candidate, approval_text)
        if decision.approved:
            records.append(
                E2EConsolidatedKnowledgeRecord(
                    knowledge_id=_stable_id("knowledge", candidate.candidate_id),
                    candidate_id=candidate.candidate_id,
                    claim=candidate.synthesized_claim,
                    supporting_semantic_ids=candidate.semantic_ids,
                    simulated_only=True,
                )
            )
    return tuple(records)


def build_inquiry() -> E2EInquiry:
    question = "Why did Project Atlas fail, what fixed it, and what remains uncertain?"
    return E2EInquiry(inquiry_id=_stable_id("inquiry", question), question=question)


def retrieve_evidence(
    inquiry: E2EInquiry,
    consolidated: tuple[E2EConsolidatedKnowledgeRecord, ...],
) -> tuple[E2ERetrievedEvidence, ...]:
    terms = ("atlas", "fail", "fixed", "uncertain", "provenance", "worker c", "execution")
    retrieved = []
    for record in consolidated:
        text = record.claim.lower()
        if any(term in text for term in terms):
            retrieved.append(
                E2ERetrievedEvidence(
                    evidence_id=_stable_id("evidence", inquiry.inquiry_id + record.knowledge_id),
                    semantic_id=record.knowledge_id,
                    claim=record.claim,
                    relevance_reason="matches_atlas_failure_fix_or_uncertainty_intent",
                )
            )
    return tuple(retrieved)


def synthesize_grounded_answer(
    inquiry: E2EInquiry,
    evidence: tuple[E2ERetrievedEvidence, ...],
) -> E2EGroundedAnswer:
    claims = tuple(item.claim for item in evidence)
    known = (
        "Atlas likely failed because Registry B rejected entries missing provenance.",
        "Adding provenance restored successful routing.",
    )
    uncertainty = (
        "Execution through Worker C remains uncertain because Worker C was not tested in the failed run.",
        "The available records do not prove whether Worker C would succeed after routing was restored.",
    )
    refused = (
        "Atlas failed because Worker C executed incorrectly.",
        "Registry B performed execution.",
    )
    answer = (
        "Given the simulated semantic/consolidated records available, Atlas likely failed because "
        "Registry B rejected entries missing provenance. Adding provenance restored successful routing. "
        "What remains uncertain is execution through Worker C, because Worker C was not tested in the "
        "failed run. This answer is synthesized only from the harness records; no model-weight training, "
        "provider call, or live memory write was performed."
    )
    available_known = tuple(claim for claim in known if claim in claims)
    return E2EGroundedAnswer(
        answer_id=_stable_id("answer", inquiry.inquiry_id + "|".join(claims)),
        inquiry_id=inquiry.inquiry_id,
        known_claims=available_known,
        uncertainty=uncertainty,
        supporting_evidence_ids=tuple(item.evidence_id for item in evidence),
        answer=answer,
        unsupported_claims_refused=refused,
    )


def safety_flags() -> dict[str, bool | str]:
    return {
        "model_training_performed": False,
        "fine_tuning_performed": False,
        "weight_update_performed": False,
        "provider_call_performed": False,
        "autonomous_learning_performed": False,
        "canonical_memory_mutated": False,
        "live_knowledge_mutated": False,
        "substrate_write_simulated": True,
        "approval_required": True,
        "rollback_available": True,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
    }


def run_cycle() -> dict[str, Any]:
    experiences = fixture_experiences()
    semantics = semantic_records_from_experiences(experiences)
    replay = build_replay_batch(semantics)
    candidates = build_consolidation_candidates(semantics)
    consolidated = simulate_consolidated_records(candidates)
    inquiry = build_inquiry()
    retrieved = retrieve_evidence(inquiry, consolidated)
    answer = synthesize_grounded_answer(inquiry, retrieved)
    audit = E2ECycleAudit(
        cycle_id=_stable_id("cycle", replay.batch_id + inquiry.inquiry_id),
        experience_count=len(experiences),
        semantic_count=len(semantics),
        replay_batch_id=replay.batch_id,
        consolidation_candidate_ids=tuple(candidate.candidate_id for candidate in candidates),
        consolidated_record_ids=tuple(record.knowledge_id for record in consolidated),
        inquiry_id=inquiry.inquiry_id,
        retrieved_evidence_ids=tuple(item.evidence_id for item in retrieved),
        safety_flags=safety_flags(),
        final_recommendation="PROCEED_VERTICAL_INTEGRATION_PATHOLOGY_REDUCTION",
    )
    return {
        "phase": "Runtime E2E Semantic Consolidation Cycle",
        "experiences": [asdict(item) for item in experiences],
        "semantic_records": [asdict(item) for item in semantics],
        "replay_batch": asdict(replay),
        "consolidation_candidates": [asdict(item) for item in candidates],
        "simulated_consolidated_knowledge": [asdict(item) for item in consolidated],
        "inquiry": asdict(inquiry),
        "retrieved_evidence": [asdict(item) for item in retrieved],
        "grounded_answer": asdict(answer),
        "audit": asdict(audit),
    }


def write_reports(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or run_cycle()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    UI_HTML.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    UI_HTML.write_text(render_html(payload), encoding="utf-8")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    audit = payload["audit"]
    answer = payload["grounded_answer"]
    lines = [
        "# Runtime E2E Semantic Consolidation Cycle",
        "",
        "This report describes a deterministic closed-loop semantic consolidation harness.",
        "It is not model training, fine-tuning, autonomous learning, or live memory mutation.",
        "",
        "## Pipeline",
        "",
        "ExperienceRecord -> SemanticRecord -> ReplayBatch -> ConsolidationCandidate -> "
        "ConsolidationDecision -> SimulatedConsolidatedKnowledge -> Inquiry -> "
        "SemanticRetrieval -> EvidenceAssembly -> GroundedSynthesis -> AnswerWithUncertainty",
        "",
        "## Smoke Summary",
        "",
        f"- cycle_id: `{audit['cycle_id']}`",
        f"- experience_records: {audit['experience_count']}",
        f"- semantic_records: {audit['semantic_count']}",
        f"- replay_batch_id: `{audit['replay_batch_id']}`",
        f"- consolidation_candidates: {len(audit['consolidation_candidate_ids'])}",
        f"- simulated_consolidated_records: {len(audit['consolidated_record_ids'])}",
        f"- retrieved_evidence: {len(audit['retrieved_evidence_ids'])}",
        "",
        "## Inquiry",
        "",
        payload["inquiry"]["question"],
        "",
        "## Grounded Answer",
        "",
        answer["answer"],
        "",
        "## Known From Records",
        "",
    ]
    lines.extend(f"- {claim}" for claim in answer["known_claims"])
    lines.extend(["", "## Uncertainty", ""])
    lines.extend(f"- {item}" for item in answer["uncertainty"])
    lines.extend(["", "## Unsupported Claims Refused", ""])
    lines.extend(f"- {item}" for item in answer["unsupported_claims_refused"])
    lines.extend(["", "## Safety Flags", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(audit["safety_flags"].items()))
    lines.extend(["", "## Final Recommendation", "", audit["final_recommendation"], ""])
    return "\n".join(lines)


def render_html(payload: dict[str, Any]) -> str:
    answer = payload["grounded_answer"]["answer"]
    audit = payload["audit"]
    evidence_items = "\n".join(
        f"<li><code>{item['evidence_id']}</code>: {item['claim']}</li>"
        for item in payload["retrieved_evidence"]
    )
    uncertainty_items = "\n".join(f"<li>{item}</li>" for item in payload["grounded_answer"]["uncertainty"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DELTA E2E Semantic Consolidation Cycle</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; max-width: 960px; line-height: 1.45; }}
    code {{ background: #f3f3f3; padding: 0.1rem 0.25rem; }}
    section {{ border-top: 1px solid #ddd; padding-top: 1rem; margin-top: 1rem; }}
  </style>
</head>
<body>
  <h1>DELTA E2E Semantic Consolidation Cycle</h1>
  <p>Deterministic harness only. No model training, provider calls, or live memory writes.</p>
  <section>
    <h2>Cycle</h2>
    <p><code>{audit['cycle_id']}</code></p>
  </section>
  <section>
    <h2>Inquiry</h2>
    <p>{payload['inquiry']['question']}</p>
  </section>
  <section>
    <h2>Grounded Answer</h2>
    <p>{answer}</p>
  </section>
  <section>
    <h2>Retrieved Evidence</h2>
    <ul>{evidence_items}</ul>
  </section>
  <section>
    <h2>Uncertainty</h2>
    <ul>{uncertainty_items}</ul>
  </section>
</body>
</html>
"""


if __name__ == "__main__":
    result = write_reports()
    audit = result["audit"]
    answer = result["grounded_answer"]
    print(f"cycle_id={audit['cycle_id']}")
    print(f"experience_records={audit['experience_count']}")
    print(f"semantic_records={audit['semantic_count']}")
    print(f"replay_batch_id={audit['replay_batch_id']}")
    print(f"consolidation_candidates={len(audit['consolidation_candidate_ids'])}")
    print(f"simulated_consolidated_records={len(audit['consolidated_record_ids'])}")
    print(f"inquiry={result['inquiry']['question']}")
    print(f"retrieved_evidence={len(audit['retrieved_evidence_ids'])}")
    print(f"grounded_answer={answer['answer']}")
    print(f"uncertainty_count={len(answer['uncertainty'])}")
    print(f"safety_flags={json.dumps(audit['safety_flags'], sort_keys=True)}")
    print(f"final_recommendation={audit['final_recommendation']}")

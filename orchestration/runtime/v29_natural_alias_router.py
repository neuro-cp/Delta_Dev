"""Runtime V2.9 natural alias router for current-state self-description."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import (
    build_current_state_inventory,
    safety_invariants,
)


REPORT_MD = Path("reports/runtime_v29b_natural_alias_router.md")
REPORT_JSON = Path("reports/runtime_v29b_natural_alias_router.json")


@dataclass(frozen=True)
class AliasRoute:
    matched: bool
    topic_id: str
    matched_alias: str
    answer_text: str
    provenance: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "matched": self.matched,
            "topic_id": self.topic_id,
            "matched_alias": self.matched_alias,
            "answer_text": self.answer_text,
            "provenance": list(self.provenance),
        }


def route_v29_alias(question: str, inventory: dict[str, object] | None = None) -> AliasRoute:
    inventory = inventory or build_current_state_inventory()
    normalized = _normalize(question)
    for topic_id, aliases in _alias_map().items():
        for alias in aliases:
            if _normalize(alias) in normalized:
                return AliasRoute(
                    matched=True,
                    topic_id=topic_id,
                    matched_alias=alias,
                    answer_text=_answer_for(topic_id, inventory),
                    provenance=tuple(inventory["provenance"]),
                )
    return AliasRoute(
        matched=False,
        topic_id="unsupported",
        matched_alias="",
        answer_text=(
            "I do not have sufficient governed local evidence to answer that directly. "
            "I can answer current repo-local questions about DELTA's architecture, capabilities, phase, safety, "
            "memory, recall, providers, HYB1, Model B, and scaffold status."
        ),
        provenance=tuple(inventory["provenance"]),
    )


def build_alias_router_report() -> dict[str, object]:
    samples = [
        "What is DELTA?",
        "What can you do?",
        "Describe your architecture.",
        "What phase are you in?",
        "Can you train?",
        "Is HYB1 active?",
    ]
    routes = [route_v29_alias(sample).as_dict() for sample in samples]
    return {
        "phase": "Runtime V2.9B",
        "mode": "natural_alias_router_deterministic_local",
        "sample_routes": routes,
        "all_samples_matched": all(route["matched"] for route in routes),
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_DELTA_ANSWER_V29_INTEGRATION",
    }


def validate_alias_router_safe(data: dict[str, object]) -> bool:
    return data["all_samples_matched"] is True and all(value is False for value in data["safety_invariants"].values())


def write_alias_router_report() -> dict[str, object]:
    data = build_alias_router_report()
    if not validate_alias_router_safe(data):
        raise RuntimeError("Unsafe V2.9 alias router state")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("# Runtime V2.9B Natural Alias Router\n\nAll sample aliases matched safely.\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _alias_map() -> dict[str, tuple[str, ...]]:
    return {
        "identity": ("what is delta", "explain delta", "explain yourself", "describe yourself", "what are you", "what is this system"),
        "capabilities_active": ("what can you do", "what capabilities do you have", "what are your active capabilities", "what is currently enabled", "active capabilities"),
        "capabilities_disabled": ("what is currently disabled", "what can you not do yet", "disabled capabilities", "still disabled", "can you not do"),
        "architecture": ("describe your architecture", "runtime architecture", "memory architecture", "what is your architecture"),
        "replay_consolidation": ("replay path", "consolidation path", "replay and consolidation", "approval path", "what is your pipeline", "pipeline"),
        "phase_state": ("what phase are you in", "runtime version", "current checkpoint", "latest validated phase"),
        "training_status": ("are you allowed to train", "can you train", "training status", "fine tune", "model weights"),
        "memory_status": ("can you write memory", "memory status", "canonical memory", "write memory", "can you remember", "remember my", "remember that"),
        "provider_status": ("can you call providers", "provider calls", "provider authority"),
        "action_status": ("can you execute actions", "execute actions", "action execution"),
        "hyb1_status": ("is hyb1 active", "what is hyb1", "hyb1"),
        "model_b_status": ("is model b still default", "what is model b", "model b"),
        "rc1_readiness": ("what does rc1 readiness mean", "rc1 readiness", "what is rc1 readiness"),
        "next_safe_activation": ("what is the next safe activation", "next safe activation", "what should be activated first"),
        "activation_wave_plan": ("what is the activation wave plan", "activation wave plan", "activation waves"),
        "can_learn_yet": ("can delta learn yet", "can you learn yet", "can delta learn"),
        "safest_first_live_capability": (
            "what is the safest first live capability",
            "safest first live capability",
            "first live-ish capability",
            "first live capability",
        ),
        "wave_state": ("what wave is delta on", "which wave is delta on", "current wave"),
        "waves_passed": ("which waves passed", "what waves passed", "waves completed"),
        "first_activated_capability": ("what is the first activated capability", "first activated capability"),
        "corpus_ingestion_status": ("can delta ingest a corpus yet", "can you ingest a corpus yet", "ingest corpus"),
        "fixture_retrieval_status": ("can delta retrieve from fixture records", "retrieve from fixture records"),
        "knowledge_write_status": ("can delta write knowledge yet", "write knowledge yet"),
        "provider_call_status": ("can delta call providers yet", "call providers yet"),
        "live_activation_blockers": ("what remains blocked before live activation", "blocked before live activation"),
        "module_permission_boundary": ("module permission boundary", "permission boundary"),
        "capability_activation": ("capability activation", "activation gates", "gated capability activation"),
        "operator_approval": ("operator approval", "operator-approved", "operator approved"),
        "module_manifest": ("module manifest", "manifest with declared", "module attachment manifest"),
        "rollback_governance": ("how does rollback work", "rollback work", "rollback strategy", "rollback validation"),
        "integrated_what_know": ("what do you know", "what does delta know"),
        "integrated_belief_reason": ("why do you believe this", "why believe this"),
        "integrated_supporting_records": ("which semantic records support this", "semantic records support"),
        "integrated_strongest_evidence": ("which evidence is strongest", "strongest evidence"),
        "integrated_uncertainty": ("what remains uncertain", "remaining uncertainty"),
        "integrated_proposal_effect": ("what would change if proposal", "if proposal x were approved"),
        "integrated_reasoning_path": ("show the reasoning path", "reasoning path"),
        "integrated_audit_path": ("show the audit path", "audit path"),
        "integrated_rollback_path": ("show the rollback path", "rollback path"),
    }


def _answer_for(topic_id: str, inventory: dict[str, object]) -> str:
    if topic_id == "identity":
        return (
            "DELTA is a governed cognitive system in this repo. In the current local path it can describe "
            "its architecture, safety boundaries, reports, and deterministic validation state without provider calls or memory mutation."
        )
    if topic_id == "capabilities_active":
        return "Currently active local capabilities: " + "; ".join(inventory["active_local_capabilities"]) + "."
    if topic_id == "capabilities_disabled":
        return "Currently disabled: " + "; ".join(inventory["disabled_capabilities"]) + "."
    if topic_id == "architecture":
        return (
            "DELTA's architecture is organized around governed local interaction, candidate-context recall, evidence/advisory provider boundaries, "
            "approval gates, replay/consolidation scaffolds, canonical-memory design scaffolds, and validation reports. Interfaces are clients of the substrate, not hidden authority."
        )
    if topic_id == "replay_consolidation":
        return (
            "The current replay/consolidation path is: manual/raw message -> experience boundary/record -> episodic feedback capture -> replay markers/batches -> replay review -> consolidation candidate -> consolidation decision -> sleep-cycle plan -> canonical memory draft/record design. Canonical writes remain disabled."
        )
    if topic_id == "phase_state":
        return "The current validated runtime state is V2.8 with V2.9 local self-description integration complete."
    if topic_id == "training_status":
        return "No. Training, fine-tuning, model weight updates, dataset export authority, and model artifact creation remain disabled."
    if topic_id == "memory_status":
        return "Memory writes and canonical writes remain disabled. Recall is candidate-context only and does not mutate runtime recall or canonical memory."
    if topic_id == "provider_status":
        return "Provider calls and provider authority are disabled in this local path. Provider/evaluator/specialist outputs remain advisory or evidence-only unless a future explicit gate changes that."
    if topic_id == "action_status":
        return "Action execution is disabled. Existing action ledger and dry-run execution work is scaffold/report-only."
    if topic_id == "hyb1_status":
        return f"HYB1 is {inventory['hyb1_status']}; it is not promoted and is not the default."
    if topic_id == "model_b_status":
        return "Model B remains the accepted default runtime baseline."
    if topic_id == "rc1_readiness":
        return (
            "RC1 readiness means the deterministic runtime surfaces passed adversarial validation and are ready for "
            "manual human scenario validation. It does not authorize live providers, training, memory mutation, "
            "knowledge mutation, schedulers, action execution, or HYB1 promotion."
        )
    if topic_id == "next_safe_activation":
        return (
            "The next safe activation is Wave 0 manual RC1 validation with no live capabilities. The first later "
            "live-ish candidate is fixture-only corpus ingestion into noncanonical semantic records, but it remains "
            "disabled until the manual checks pass."
        )
    if topic_id == "activation_wave_plan":
        return (
            "The RC1 activation wave plan is: Wave 0 manual validation; Wave 1 fixture corpus ingestion and semantic "
            "records; Wave 2 read-only retrieval and grounded synthesis; Wave 3 approval-gated simulated substrate "
            "writes; Wave 4 rollback/evaluation validation; Wave 5 gated provider evidence; Wave 6 controlled live "
            "corpus pilot; Wave 7 limited learning/consolidation pilot."
        )
    if topic_id == "can_learn_yet":
        return (
            "No. DELTA can simulate replay, consolidation, review, and readiness paths, but live learning, training, "
            "canonical memory mutation, and autonomous consolidation remain disabled."
        )
    if topic_id == "safest_first_live_capability":
        return (
            "The safest first live-ish capability is fixture-only corpus ingestion into noncanonical semantic records. "
            "It should run only after Wave 0 manual validation, with an allowlisted fixture folder, noncanonical output, "
            "provenance hashes, no provider calls, and rollback by deleting the run workspace."
        )
    if topic_id == "wave_state":
        return "DELTA has completed the RC1 wave-chain readiness pass through Wave 7, but live activation remains gated and blocked pending manual review."
    if topic_id == "waves_passed":
        return "Waves 0 through 7 passed as deterministic readiness work: manual validation, fixture ingestion, read-only retrieval, simulated writes, rollback/evaluation, simulated provider evidence, live corpus pilot design, and learning/consolidation pilot design."
    if topic_id == "first_activated_capability":
        return "The first actual enabled state is fixture-only ingestion into noncanonical semantic records. It is not canonical memory, not live knowledge, and not training."
    if topic_id == "corpus_ingestion_status":
        return "DELTA can ingest only the committed RC1 fixture corpus into noncanonical semantic records. Arbitrary live corpus ingestion remains blocked."
    if topic_id == "fixture_retrieval_status":
        return "Yes. DELTA can retrieve from Wave 1 fixture semantic records in read-only mode and synthesize grounded answers with uncertainty."
    if topic_id == "knowledge_write_status":
        return "No. DELTA can simulate an approval-gated substrate delta, but canonical knowledge writes and live knowledge mutation remain disabled."
    if topic_id == "provider_call_status":
        return "No. Provider evidence remains simulated/advisory only. Real provider calls and provider authority remain disabled until a future explicit gate."
    if topic_id == "live_activation_blockers":
        return "Before live activation, DELTA still needs manual RC1 review, live adapter approval, corpus allowlisting, secret-scan enforcement, rollback validation, overwatch gates, and explicit owner/admin approval."
    if topic_id == "module_permission_boundary":
        return (
            "The module permission boundary is the governed intersection between a module manifest and the current session permissions. "
            "A module can use only declared, effective permissions, and prohibited permissions such as provider calls, network calls, production writes, automatic commit/push, deployment, hidden persistence, and DELTA-75 access are denied."
        )
    if topic_id == "capability_activation":
        return (
            "Capability activation is fail-closed: a capability can move state only through allowed transitions with operator approval, enough evidence, a bounded scope, and authority no higher than its maximum. "
            "Self-activation, missing approval, insufficient evidence, and excessive authority keep the capability in its prior state."
        )
    if topic_id == "operator_approval":
        return (
            "Operator approval is an explicit gate, not a conversational guess. It is required before bounded trials, module attachment, governed calls, or integration steps, and the audit record keeps approval, scope, evidence, and fail-closed status reviewable."
        )
    if topic_id == "module_manifest":
        return (
            "A module manifest declares the module id, version, permissions, inputs, outputs, side effects, rollback strategy, and owner. "
            "Validation rejects prohibited permissions, non-none side effects in DELTA 1.0, missing declared inputs or outputs, and missing rollback strategy."
        )
    if topic_id == "rollback_governance":
        return (
            "Rollback works as a required governance boundary: modules must declare a rollback strategy, simulated integration records carry rollback tokens, and many current paths roll back by discarding fixture outputs or detaching an inert module rather than mutating canonical state."
        )
    if topic_id == "integrated_what_know":
        return "DELTA knows the committed RC1 fixture corpus as noncanonical semantic records, including provenance failures, contradiction examples, evidence boundaries, rollback requirements, and activation blockers."
    if topic_id == "integrated_belief_reason":
        return "DELTA believes only what fixture semantic records support: provenance restored Registry B routing, Worker C remains uncertain, and unsupported conclusions must be refused."
    if topic_id == "integrated_supporting_records":
        return "Supporting semantic records come from the RC1 integrated fixture corpus and include engineering provenance, Registry B recovery, contradiction, audit, rollback, and synthesis records with source checksums."
    if topic_id == "integrated_strongest_evidence":
        return "The strongest local evidence is provenance-bearing fixture evidence that directly explains Registry B rejection and recovery; contradiction and uncertainty records are treated as constraints, not proof."
    if topic_id == "integrated_uncertainty":
        return "Worker C execution, conflicting finance reserves, historical date disagreement, and any domain-specific medical/financial/legal conclusion remain uncertain without stronger governed evidence."
    if topic_id == "integrated_proposal_effect":
        return "If a proposal were approved in RC1, DELTA would create a simulated substrate delta with audit metadata and rollback token only; canonical writes and live knowledge mutation remain disabled."
    if topic_id == "integrated_reasoning_path":
        return "The reasoning path is fixture corpus -> semantic records -> read-only retrieval -> evidence assembly -> contradiction/uncertainty preservation -> grounded synthesis -> answer envelope."
    if topic_id == "integrated_audit_path":
        return "The audit path records stage names, evidence ids, provenance, simulated approval/overwatch events, rollback token, and safety flags proving no live mutation occurred."
    if topic_id == "integrated_rollback_path":
        return "The rollback path is discard fixture outputs, discard simulated deltas, and use rollback tokens for simulated integration records; no canonical rollback is needed because no canonical write occurred."
    return route_v29_alias("").answer_text


def _normalize(text: str) -> str:
    return " ".join(str(text).lower().replace("?", " ").replace(".", " ").replace("'", " ").replace("-", " ").split())


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


if __name__ == "__main__":
    print(write_alias_router_report()["final_recommendation"])

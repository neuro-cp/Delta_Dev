from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArchitectureDecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    REQUIRES_USER_DECISION = "requires_user_decision"


class ArchitectureConcept(str, Enum):
    SLEEP_REPLAY_CONSOLIDATION = "sleep_replay_consolidation"
    LIVE_PRUNING_PROJECTION = "live_pruning_projection"
    CANONICAL_PRUNING = "canonical_pruning"
    NEGATIVE_FEEDBACK_MEMORY = "negative_feedback_memory"
    EPISODIC_CAPTURE = "episodic_capture"
    EPISODIC_TO_SEMANTIC_CONSOLIDATION = "episodic_to_semantic_consolidation"
    LIVE_CANONICAL_STORE = "live_canonical_store"
    CANDIDATE_ENVELOPE = "candidate_envelope"
    STRUCTURAL_SEMANTIC_ADAPTER = "structural_semantic_adapter"
    EVIDENCE_ROLE_METADATA = "evidence_role_metadata"
    LANE_PERMISSIONS = "lane_permissions"
    HYPOTHESIS_ARBITRATION = "hypothesis_arbitration"
    CONFIDENCE_INERTIA = "confidence_inertia"
    DMSA_MULTISTREAM_ASSESSMENT = "dmsa_multistream_assessment"
    EXECUTION_AUTHORIZATION = "execution_authorization"
    UNKNOWN_ANSWER_PORT = "unknown_answer_port"
    SPECIALIST_ROUTING = "specialist_routing"
    CONTROLLED_TRAINING = "controlled_training"
    AUTONOMOUS_KNOWLEDGE_ACQUISITION = "autonomous_knowledge_acquisition"


@dataclass(frozen=True)
class ArchitectureDecisionRecord:
    concept: ArchitectureConcept
    status: ArchitectureDecisionStatus
    original_delta_function: str
    implementation_decision: str
    current_repo_status: str
    dependencies_before_activation: tuple[str, ...]
    risks: tuple[str, ...]
    next_action: str
    user_decision_required: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "concept": self.concept.value,
            "status": self.status.value,
            "original_delta_function": self.original_delta_function,
            "implementation_decision": self.implementation_decision,
            "current_repo_status": self.current_repo_status,
            "dependencies_before_activation": list(self.dependencies_before_activation),
            "risks": list(self.risks),
            "next_action": self.next_action,
            "user_decision_required": self.user_decision_required,
            "notes": self.notes,
        }


def build_v14c_decision_lock() -> tuple[ArchitectureDecisionRecord, ...]:
    return (
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.SLEEP_REPLAY_CONSOLIDATION,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Offline replay of experience so DELTA can consolidate, weaken, or queue knowledge without live pressure.",
            implementation_decision="Preserve functionally as scheduled/batch replay-consolidation, not literal sleep.",
            current_repo_status="not active; prepared by CandidateEnvelope and trace design",
            dependencies_before_activation=("output traces", "feedback records", "replay validator"),
            risks=("premature memory mutation", "unreviewed reinforcement of noisy evidence"),
            next_action="design replay input after feedback capture scaffold",
            user_decision_required=False,
            notes="Sleep stays as a DELTA concept, but the repo should implement it as controlled batch replay.",
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.LIVE_PRUNING_PROJECTION,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Temporarily reduce use of harmful concept pathways during runtime.",
            implementation_decision="Allow later as temporary runtime/session projection only; no canonical mutation at first.",
            current_repo_status="pruning record schema scaffolded only",
            dependencies_before_activation=("answer traces", "feedback events", "replay validator", "lane permissions"),
            risks=("over-dampening useful concepts", "global judgment from local failure"),
            next_action="simulate projection after feedback records exist",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.CANONICAL_PRUNING,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Demote or remove canonical knowledge that repeatedly proves corrupt or harmful.",
            implementation_decision="Wait for replay/consolidation, repeated evidence, provenance, rollback, or human approval.",
            current_repo_status="absent",
            dependencies_before_activation=("live canonical store", "provenance ledger", "rollback", "human review path"),
            risks=("irreversible deletion", "loss of useful context"),
            next_action="defer until canonical store design",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.NEGATIVE_FEEDBACK_MEMORY,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Remember when a concept, lane, or pathway caused drift or unsafe output.",
            implementation_decision="Represent as append-only feedback and pruning-review records.",
            current_repo_status="pruning record schema scaffolded; feedback draft added in V1.4C",
            dependencies_before_activation=("answer traces", "failure taxonomy"),
            risks=("treating correction as universal truth"),
            next_action="build feedback capture scaffold next",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.EPISODIC_CAPTURE,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Capture raw runtime experience before semantic consolidation.",
            implementation_decision="Wait for output trace and feedback policy; capture should be explicit and auditable.",
            current_repo_status="experiment stores exist; no live runtime capture",
            dependencies_before_activation=("output trace design", "feedback capture", "privacy/scope policy"),
            risks=("unbounded live data capture", "training from messy logs"),
            next_action="derive episode envelope from answer traces later",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.EPISODIC_TO_SEMANTIC_CONSOLIDATION,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Convert episodes into reusable semantic candidates.",
            implementation_decision="Use replay/consolidation over trace-backed candidate envelopes; no direct canonical writes.",
            current_repo_status="training pipeline exists for isolated stores only",
            dependencies_before_activation=("CandidateEnvelope", "feedback records", "replay queue", "canonical store design"),
            risks=("reintroducing extraction defects", "promoting one-off artifacts"),
            next_action="design after feedback capture scaffold",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.LIVE_CANONICAL_STORE,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Durable trusted knowledge store for runtime use.",
            implementation_decision="Schema should be shaped by output traces first.",
            current_repo_status="absent; candidate stores and isolated experiments only",
            dependencies_before_activation=("trace usage requirements", "provenance", "rollback", "promotion ledger"),
            risks=("freezing the wrong schema", "hard-to-reverse mutation"),
            next_action="design after output traces and feedback records are understood",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.CANDIDATE_ENVELOPE,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Boundary object for candidate knowledge lifecycle and provenance.",
            implementation_decision="Already scaffolded; use as future controlled-learning carrier.",
            current_repo_status="scaffolded in orchestration/runtime/v14_candidate_envelope.py",
            dependencies_before_activation=("feedback records", "replay design"),
            risks=("low while inert"),
            next_action="integrate only in later replay/feedback phases",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.STRUCTURAL_SEMANTIC_ADAPTER,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Represent semantic concepts by function, role, polarity, and uncertainty.",
            implementation_decision="Continue as schema-first signal tagging; no active routing until validated.",
            current_repo_status="evidence role metadata scaffolded",
            dependencies_before_activation=("signal precision audit", "role assignment validation"),
            risks=("false precision", "same-topic noise admission"),
            next_action="keep scaffold dormant until signal research resumes",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.EVIDENCE_ROLE_METADATA,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Record why evidence matters.",
            implementation_decision="Already scaffolded as inert evidence role metadata.",
            current_repo_status="scaffolded in orchestration/runtime/v14_signals.py",
            dependencies_before_activation=("role validation",),
            risks=("mislabeling evidence roles"),
            next_action="use in report-only audits first",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.LANE_PERMISSIONS,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Separate concept visibility from reasoning, planning, response, and execution use.",
            implementation_decision="Already scaffolded; active enforcement waits for explicit phase.",
            current_repo_status="scaffolded in orchestration/runtime/v14_lanes.py",
            dependencies_before_activation=("policy provenance", "runtime integration tests"),
            risks=("hiding useful knowledge if active too early"),
            next_action="keep projection-only until feedback/replay work",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.HYPOTHESIS_ARBITRATION,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Compare competing hypotheses and preserve disconfirming evidence.",
            implementation_decision="Wait for evidence roles and contradiction direction before building.",
            current_repo_status="not implemented beyond current conflict reports",
            dependencies_before_activation=("evidence roles", "confidence trajectory", "contradiction direction"),
            risks=("opaque scoring layer", "premature cognitive expansion"),
            next_action="defer",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.CONFIDENCE_INERTIA,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Track volatility and avoid brittle confidence oscillation.",
            implementation_decision="Start as observation/reporting later, not active smoothing.",
            current_repo_status="confidence exists in reports; no inertia model",
            dependencies_before_activation=("trace history", "feedback history"),
            risks=("masking real degradation"),
            next_action="defer until enough traces exist",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.DMSA_MULTISTREAM_ASSESSMENT,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Multiple assessment streams check evidence, safety, planning, and uncertainty.",
            implementation_decision="Represent initially as report-only multi-check validators/scorecards, not a distributed executor.",
            current_repo_status="sequential scorecards and reports only",
            dependencies_before_activation=("stable evaluator roles", "veto rules"),
            risks=("architecture bloat", "premature executor semantics"),
            next_action="defer active subsystem; use report-only checks",
            user_decision_required=True,
            notes="Accepted functionally, not as a new execution layer.",
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.EXECUTION_AUTHORIZATION,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Authorize or veto actions before execution.",
            implementation_decision="No action-capable runtime until an explicit authorization packet exists.",
            current_repo_status="safety/output scaffolds only",
            dependencies_before_activation=("action taxonomy", "authorization ledger", "output discipline integration"),
            risks=("unsafe action", "tool execution without evidence"),
            next_action="defer",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.UNKNOWN_ANSWER_PORT,
            status=ArchitectureDecisionStatus.ACCEPTED,
            original_delta_function="Express uncertainty, abstain, or route without hallucination.",
            implementation_decision="Already scaffolded as output discipline; integration comes later.",
            current_repo_status="scaffolded in orchestration/runtime/v14_output_discipline.py",
            dependencies_before_activation=("response integration tests",),
            risks=("low while inert"),
            next_action="use as part of feedback capture/output trace work",
            user_decision_required=False,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.SPECIALIST_ROUTING,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Acquire external/specialist evidence when DELTA lacks enough governed knowledge.",
            implementation_decision="Dormant route objects only for now; no provider calls.",
            current_repo_status="scaffolded in orchestration/runtime/v14_specialist_router.py",
            dependencies_before_activation=("output discipline", "feedback capture", "provider authorization", "merge rules"),
            risks=("authority transfer to specialist", "ungoverned provider calls"),
            next_action="keep dormant",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.CONTROLLED_TRAINING,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Learn from selected episodes and corrections under governance.",
            implementation_decision="Wait for output traces, feedback capture, replay/consolidation, and canonical store.",
            current_repo_status="disabled; isolated training campaigns only",
            dependencies_before_activation=("output traces", "feedback capture", "replay", "live canonical store", "rollback"),
            risks=("memory contamination", "irreversible bad learning"),
            next_action="defer",
            user_decision_required=True,
        ),
        ArchitectureDecisionRecord(
            concept=ArchitectureConcept.AUTONOMOUS_KNOWLEDGE_ACQUISITION,
            status=ArchitectureDecisionStatus.DEFERRED,
            original_delta_function="Seek new information without user prompt.",
            implementation_decision="Wait until pruning, source credibility, replay, and canonical store exist.",
            current_repo_status="absent",
            dependencies_before_activation=("source credibility", "authorization", "canonical store", "replay", "pruning controls"),
            risks=("unbounded acquisition", "source contamination", "unsafe autonomy"),
            next_action="defer beyond V1.4",
            user_decision_required=True,
        ),
    )


def get_decision_for_concept(
    concept: ArchitectureConcept | str,
    decisions: tuple[ArchitectureDecisionRecord, ...] | None = None,
) -> ArchitectureDecisionRecord:
    target = ArchitectureConcept(concept)
    for decision in decisions or build_v14c_decision_lock():
        if decision.concept == target:
            return decision
    raise KeyError(f"No architecture decision recorded for {target.value}")


def concepts_requiring_user_decision(
    decisions: tuple[ArchitectureDecisionRecord, ...] | None = None,
) -> tuple[ArchitectureDecisionRecord, ...]:
    return tuple(decision for decision in decisions or build_v14c_decision_lock() if decision.user_decision_required)


def concepts_safe_to_scaffold_now(
    decisions: tuple[ArchitectureDecisionRecord, ...] | None = None,
) -> tuple[ArchitectureDecisionRecord, ...]:
    return tuple(
        decision
        for decision in decisions or build_v14c_decision_lock()
        if decision.status == ArchitectureDecisionStatus.ACCEPTED and "scaffold" in decision.next_action.lower()
    )


def concepts_must_wait(
    decisions: tuple[ArchitectureDecisionRecord, ...] | None = None,
) -> tuple[ArchitectureDecisionRecord, ...]:
    return tuple(
        decision
        for decision in decisions or build_v14c_decision_lock()
        if decision.status in {ArchitectureDecisionStatus.DEFERRED, ArchitectureDecisionStatus.REQUIRES_USER_DECISION}
    )

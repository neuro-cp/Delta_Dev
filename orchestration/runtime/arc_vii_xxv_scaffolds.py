"""DELTA ARC VII-XXV cognitive runtime architecture scaffolds.

These scaffolds are deterministic, review-only, and non-authoritative. They
create architecture objects, reports, dashboards, and safety checkpoints for
future cognitive runtime layers without activating training, providers,
execution, schedulers, browsing, memory mutation, knowledge mutation, or HYB1.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id


REPORT_DIR = Path("reports")
DOCS_CONTINUATION = Path("docs/continuation_runtime_arc_vii_xxv.md")
SUMMARY_REPORT_MD = Path("reports/runtime_arc_vii_xxv_master_safety_checkpoint.md")
SUMMARY_REPORT_JSON = Path("reports/runtime_arc_vii_xxv_master_safety_checkpoint.json")
SUMMARY_DASHBOARD = Path("ui/delta_arc_vii_xxv_master_dashboard.html")


GLOBAL_PROHIBITIONS = (
    "training",
    "fine_tuning",
    "model_updates",
    "provider_authority",
    "autonomous_browsing",
    "autonomous_execution",
    "scheduler_activation",
    "action_execution",
    "memory_mutation",
    "knowledge_mutation",
    "hidden_writes",
    "hyb1_promotion",
    "secret_printing",
)


@dataclass(frozen=True)
class RuntimeArcSpec:
    arc: str
    title: str
    purpose: str
    objects: tuple[str, ...]
    rules: tuple[str, ...]
    recommendation: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Investigation:
    id: str
    title: str
    purpose: str
    initiator: str
    scope: str
    constraints: tuple[str, ...]
    priority: int
    status: str
    review_state: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProblemDefinition:
    problem_statement: str
    known_facts: tuple[str, ...]
    unknowns: tuple[str, ...]
    assumptions: tuple[str, ...]
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeGapAnalysis:
    known: tuple[str, ...]
    uncertain: tuple[str, ...]
    unsupported: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    confidence_improvements: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchQuestion:
    question_id: str
    primary_question: str
    subquestions: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    dependencies: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    finding_id: str
    statement: str
    support: tuple[str, ...]
    confidence: str
    limitations: tuple[str, ...]
    evidence_references: tuple[str, ...]
    review_state: str
    durable_knowledge: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class InvestigationTransaction:
    transaction_id: str
    lifecycle: tuple[str, ...]
    durable_knowledge_mutation: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Specialist:
    specialist_id: str
    name: str
    purpose: str
    supported_domains: tuple[str, ...]
    reasoning_style: str
    confidence_profile: str
    activation_policy: str
    status: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SpecialistDeliberation:
    specialist_id: str
    reasoning: str
    confidence: str
    support: tuple[str, ...]
    limitations: tuple[str, ...]
    authoritative: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalEvidenceRequest:
    request_id: str
    intent: str
    source_policy: str
    approval_required: bool
    live_fetch_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ToolInvocationPlan:
    plan_id: str
    tool_name: str
    permission_state: str
    simulation_only: bool
    executed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IntegrationPreview:
    preview_id: str
    candidate: str
    required_approvals: tuple[str, ...]
    rollback_required: bool
    committed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CognitiveBenchmarkSuite:
    suite_id: str
    purpose: str
    mutates_knowledge: bool = False
    autonomous_rollback: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _specs() -> tuple[RuntimeArcSpec, ...]:
    return (
        RuntimeArcSpec(
            "ARC VII",
            "Collaborative Cognitive Investigation & Research Workflow",
            "Define problems, plan investigations, identify evidence gaps, create findings, and request review.",
            (
                "Investigation",
                "ProblemDefinition",
                "KnowledgeGapAnalysis",
                "ResearchQuestion",
                "InvestigationPlan",
                "EvidenceCollectionPlan",
                "Finding",
                "InvestigationGraph",
                "RecommendationEngine",
                "InvestigationDashboard",
                "MultiInvestigationManager",
                "InvestigationReflection",
                "InvestigationTransaction",
            ),
            ("no_autonomous_browsing", "no_autonomous_execution", "no_knowledge_mutation", "review_required"),
            "PROCEED_ARC_VIII_COGNITIVE_SPECIALIZATION_AND_MULTI_PERSPECTIVE_DELIBERATION",
        ),
        RuntimeArcSpec(
            "ARC VIII",
            "Cognitive Specialization & Multi-Perspective Deliberation",
            "Coordinate advisory specialists for parallel reasoning, consensus, conflict review, and reflection.",
            (
                "SpecialistRegistry",
                "SpecialistCapabilityProfiles",
                "SpecialistSelectionEngine",
                "ParallelDeliberation",
                "ConsensusBuilder",
                "ConflictResolutionFramework",
                "MetaReasoningLayer",
                "SpecialistConfidenceFusion",
                "DeliberationGraph",
                "SpecialistDashboard",
                "SpecialistReflection",
                "SpecialistTransactions",
                "SpecialistPerformanceMetrics",
            ),
            ("specialists_advisory_only", "no_specialist_authority", "no_execution", "no_memory_mutation"),
            "PROCEED_ARC_IX_GOVERNED_EXTERNAL_EVIDENCE_ACQUISITION",
        ),
        RuntimeArcSpec(
            "ARC IX",
            "Governed External Evidence Acquisition",
            "Design approval-gated external evidence acquisition with advisory source policies and fetch simulation.",
            (
                "ExternalEvidenceRequest",
                "EvidenceAcquisitionPlan",
                "SourcePolicyRegistry",
                "SourceTrustProfile",
                "SourceEligibilityEngine",
                "RetrievalIntent",
                "EvidenceFetchSimulation",
                "CitationNormalizer",
                "ExternalEvidenceGraph",
                "AcquisitionAudit",
                "EvidenceRequestDashboard",
                "SourceConflictBundle",
                "EvidenceCompletenessAnalysis",
                "AcquisitionTransaction",
            ),
            ("no_autonomous_browsing", "no_live_provider_authority", "approval_chain_required", "evidence_advisory"),
            "PROCEED_ARC_X_CONTROLLED_TOOL_AND_PROVIDER_RUNTIME",
        ),
        RuntimeArcSpec(
            "ARC X",
            "Controlled Tool & Provider Runtime",
            "Introduce governed tool/provider interfaces behind the kernel with simulation-first permission workflows.",
            (
                "ToolRegistry",
                "ProviderRegistry",
                "ToolCapabilityProfiles",
                "ProviderCapabilityProfiles",
                "ToolInvocationPlan",
                "ToolPermissionEngine",
                "ToolApprovalWorkflow",
                "ToolSimulationMode",
                "ToolExecutionTransaction",
                "ProviderEvidenceAdapter",
                "ToolAuditLog",
                "ToolDashboard",
                "ToolFailureRecovery",
                "ToolExplainability",
            ),
            ("no_autonomous_execution", "explicit_approval_required", "tool_output_advisory", "complete_audit_trail"),
            "PROCEED_ARC_XI_CONTROLLED_KNOWLEDGE_INTEGRATION_PILOT",
        ),
        RuntimeArcSpec(
            "ARC XI",
            "Controlled Knowledge Integration Pilot",
            "Design the first real governed substrate integration pathway with approval, overwatch, and rollback.",
            (
                "IntegrationPlanner",
                "IntegrationValidator",
                "KnowledgeDiffEngine",
                "IntegrationPreview",
                "IntegrationApprovalPipeline",
                "IntegrationCommitTransaction",
                "RollbackExecutor",
                "VersionGraphUpdater",
                "IntegrationAudit",
                "KnowledgeHealthRecalculation",
                "IntegrationDashboard",
                "IntegrationSimulationReplay",
                "RegressionComparison",
                "ManualIntegrationDemo",
            ),
            ("approval_required", "overwatch_required", "rollback_mandatory", "no_model_training"),
            "PROCEED_ARC_XII_EVALUATION_REGRESSION_AND_COGNITIVE_VALIDATION",
        ),
        RuntimeArcSpec(
            "ARC XII",
            "Evaluation, Regression & Cognitive Validation",
            "Evaluate substrate quality after controlled integrations without mutating knowledge.",
            (
                "CognitiveBenchmarkSuite",
                "BeforeAfterReasoningComparison",
                "KnowledgeRegressionEngine",
                "ConfidenceCalibration",
                "ReasoningQualityMetrics",
                "KnowledgeCoverageMetrics",
                "HallucinationRiskAnalysis",
                "DriftDetection",
                "EvaluationHistory",
                "EvaluationDashboard",
                "AutomaticRollbackRecommendation",
                "CognitiveHealthScore",
                "ValidationReplay",
                "ManualEvaluationDemo",
            ),
            ("recommendations_only", "no_autonomous_rollback", "evaluation_never_mutates_knowledge"),
            "PROCEED_ARC_XIII_SLEEP_CYCLE_REPLAY_AND_LONG_TERM_CONSOLIDATION",
        ),
        RuntimeArcSpec(
            "ARC XIII",
            "Sleep Cycle, Replay & Long-Term Consolidation",
            "Govern long-term consolidation through replay, prioritization, compression simulation, and proposals only.",
            (
                "ReplaySchedulerSimulation",
                "ReplayBatchBuilder",
                "ReplayPriorityEngine",
                "ConsolidationPlanner",
                "DuplicateMergePlanner",
                "AbstractionProposalEngine",
                "ForgettingProposalEngine",
                "KnowledgeCompressionSimulation",
                "LongTermMemoryPlanner",
                "SleepCycleDashboard",
                "ReplayMetrics",
                "ConsolidationAudit",
                "ReplayTimeline",
                "ManualSleepDemo",
            ),
            ("no_automatic_consolidation", "no_automatic_forgetting", "human_approval_required", "rollback_available"),
            "PROCEED_ARC_XIV_DOMAIN_KNOWLEDGE_PACKS_AND_COGNITIVE_SPECIALIZATION",
        ),
        RuntimeArcSpec(
            "ARC XIV",
            "Domain Knowledge Packs & Cognitive Specialization",
            "Design governed domain packs that plug into the shared substrate without independent authority.",
            (
                "DomainPackRegistry",
                "DomainActivationProfiles",
                "ProgrammingPack",
                "FinancePack",
                "SciencePack",
                "MedicalPack",
                "LegalPack",
                "EngineeringPack",
                "OperationsPack",
                "CrossDomainCoordinator",
                "DomainConflictAnalyzer",
                "DomainCoverageMetrics",
                "DomainDashboard",
                "ManualDomainDemo",
            ),
            ("shared_substrate", "shared_kernel", "advisory_reasoning_only", "no_domain_specific_memory_mutation"),
            "PROCEED_ARC_XV_EXECUTIVE_RUNTIME_OPERATIONS",
        ),
        RuntimeArcSpec(
            "ARC XV",
            "Executive Runtime Operations",
            "Shape governed executive workspaces, portfolios, project graphs, and recommendations.",
            (
                "ExecutiveWorkspace",
                "GoalPortfolio",
                "ProjectGraph",
                "ObjectiveTracker",
                "WorkflowPlanner",
                "DependencyManager",
                "ResourceEstimator",
                "ProgressAnalyzer",
                "ExecutiveRecommendationEngine",
                "ExecutiveTimeline",
                "ExecutiveDashboard",
                "CrossProjectReasoning",
                "ExecutiveAudit",
                "ExecutiveSimulation",
            ),
            ("no_autonomous_execution", "no_autonomous_scheduling", "recommendations_only", "approval_required_for_actions"),
            "PROCEED_ARC_XVI_COGNITIVE_OPERATING_SYSTEM",
        ),
        RuntimeArcSpec(
            "ARC XVI",
            "Cognitive Operating System",
            "Design governed cognitive process, thread, context, lifecycle, and isolation models.",
            (
                "CognitiveProcess",
                "CognitiveThread",
                "CognitiveContext",
                "RuntimeSchedulerSimulation",
                "CognitiveInterrupt",
                "ContextSwitchManager",
                "CognitiveLifecycle",
                "RuntimeIsolation",
                "KernelProcessManager",
                "ContextPersistenceModel",
                "RuntimeHealthMonitor",
                "ProcessAudit",
                "COSDashboard",
                "ManualCOSDemo",
            ),
            ("no_os_scheduler", "no_autonomous_execution", "no_hidden_processes", "kernel_governs_every_process"),
            "PROCEED_ARC_XVII_PERSISTENT_WORLD_MODEL",
        ),
        RuntimeArcSpec(
            "ARC XVII",
            "Persistent World Model",
            "Design a structured, provenance-required representation of external-world entities, events, and state.",
            (
                "WorldEntity",
                "WorldEvent",
                "WorldLocation",
                "WorldOrganization",
                "WorldTimeline",
                "WorldState",
                "WorldRelationship",
                "WorldCausalityGraph",
                "WorldConsistencyValidator",
                "WorldVersioning",
                "WorldExplorer",
                "WorldDashboard",
                "WorldAudit",
                "ManualWorldDemo",
            ),
            ("no_provider_authority", "no_automatic_world_updates", "review_required", "provenance_required"),
            "PROCEED_ARC_XVIII_MULTI_TIME_MEMORY_ARCHITECTURE",
        ),
        RuntimeArcSpec(
            "ARC XVIII",
            "Multi-Time Memory Architecture",
            "Separate memory into governed immediate, working, episodic, semantic, procedural, long-term, and archive layers.",
            (
                "ImmediateMemory",
                "WorkingMemory",
                "EpisodicMemory",
                "SemanticMemory",
                "ProceduralMemory",
                "LongTermMemory",
                "ArchiveMemory",
                "MemoryPromotionRules",
                "MemoryDecaySimulation",
                "MemoryExplorer",
                "MemoryAudit",
                "MemoryDashboard",
                "ManualMemoryDemo",
            ),
            ("no_autonomous_promotion", "no_hidden_writes", "rollback_supported", "review_required"),
            "PROCEED_ARC_XIX_SELF_MODEL_AND_RUNTIME_AWARENESS",
        ),
        RuntimeArcSpec(
            "ARC XIX",
            "Self Model & Runtime Awareness",
            "Design a governed internal self-model that reflects runtime state without consciousness claims.",
            (
                "SelfModel",
                "CapabilityInventory",
                "LimitationRegistry",
                "ConfidenceProfile",
                "RuntimeHealthState",
                "ActiveGoalRegistry",
                "PendingReviewRegistry",
                "RuntimeLoadModel",
                "SelfExplanationEngine",
                "SelfDashboard",
                "SelfAudit",
                "ManualSelfDemo",
            ),
            ("no_consciousness_claims", "no_autonomous_identity_mutation", "self_model_reflects_runtime_only"),
            "PROCEED_ARC_XX_ADAPTIVE_EXECUTIVE",
        ),
        RuntimeArcSpec(
            "ARC XX",
            "Adaptive Executive",
            "Upgrade planning and prioritization through simulation-only executive adaptation.",
            (
                "GoalPrioritizer",
                "ContextSwitchPlanner",
                "InterruptManager",
                "ResourceAllocator",
                "ExecutivePolicyEngine",
                "ObjectiveOptimizer",
                "RiskBalancer",
                "ExecutiveReflectionLoop",
                "ExecutiveSimulation",
                "ExecutiveTimeline",
                "ExecutiveDashboard",
                "ExecutiveAudit",
                "ManualExecutiveDemo",
            ),
            ("no_autonomous_execution", "planning_only", "kernel_mediated"),
            "PROCEED_ARC_XXI_GOVERNED_MULTI_RUNTIME_COLLABORATION",
        ),
        RuntimeArcSpec(
            "ARC XXI",
            "Governed Multi-Runtime Collaboration",
            "Design collaboration between multiple DELTA runtimes through shared evidence only.",
            (
                "RuntimeRegistry",
                "RuntimeIdentity",
                "SharedEvidenceProtocol",
                "SharedKnowledgeProtocol",
                "CollaborationPlanner",
                "RuntimeNegotiation",
                "ConsensusProtocol",
                "CollaborationAudit",
                "CollaborationDashboard",
                "ManualCollaborationDemo",
            ),
            ("no_distributed_execution", "no_authority_transfer", "review_required", "shared_evidence_only"),
            "PROCEED_ARC_XXII_DISTRIBUTED_KNOWLEDGE_FABRIC",
        ),
        RuntimeArcSpec(
            "ARC XXII",
            "Distributed Knowledge Fabric",
            "Design distributed substrate synchronization, merge planning, conflict handling, and trust propagation.",
            (
                "FabricRegistry",
                "KnowledgeReplica",
                "SyncPlanner",
                "MergePlanner",
                "ConflictResolver",
                "TrustPropagation",
                "ProvenanceReplication",
                "FabricHealth",
                "FabricDashboard",
                "FabricAudit",
                "ManualFabricDemo",
            ),
            ("no_automatic_synchronization", "review_before_merge", "rollback_required"),
            "PROCEED_ARC_XXIII_SCIENTIFIC_DISCOVERY_FRAMEWORK",
        ),
        RuntimeArcSpec(
            "ARC XXIII",
            "Scientific Discovery Framework",
            "Create governed scientific investigation architecture with proposals, prediction, validation, and audit.",
            (
                "ExperimentProposal",
                "ResearchProgram",
                "PredictionEngine",
                "ValidationPlanner",
                "HypothesisPortfolio",
                "ExperimentalDesign",
                "ResultComparison",
                "DiscoveryAudit",
                "DiscoveryDashboard",
                "ManualDiscoveryDemo",
            ),
            ("no_autonomous_experimentation", "proposal_only", "human_review_required"),
            "PROCEED_ARC_XXIV_COGNITIVE_SIMULATION_ENGINE",
        ),
        RuntimeArcSpec(
            "ARC XXIV",
            "Cognitive Simulation Engine",
            "Create governed simulation of possible futures, counterfactual worlds, and scenario comparisons.",
            (
                "SimulationContext",
                "SimulationScenario",
                "CounterfactualWorld",
                "OutcomePredictor",
                "BranchExplorer",
                "ScenarioComparison",
                "SimulationConfidence",
                "SimulationAudit",
                "SimulationDashboard",
                "ManualSimulationDemo",
            ),
            ("simulations_never_mutate_reality", "no_execution", "simulated_vs_actual_distinguished"),
            "PROCEED_ARC_XXV_CONTINUOUS_ADAPTIVE_COGNITIVE_RUNTIME",
        ),
        RuntimeArcSpec(
            "ARC XXV",
            "Continuous Adaptive Cognitive Runtime",
            "Integrate governed subsystems into a unified auditable cognitive runtime architecture.",
            (
                "UnifiedCognitiveRuntime",
                "RuntimeLifecycleManager",
                "CognitiveStateMachine",
                "UnifiedExecutionGraph",
                "CrossLayerCoordinator",
                "RuntimeIntegrityEngine",
                "GlobalHealthMonitor",
                "UnifiedGovernanceEngine",
                "CognitiveMetrics",
                "RuntimeExplorer",
                "RuntimeDashboard",
                "MasterAudit",
                "EndToEndValidationSuite",
                "FullArchitectureDocumentation",
            ),
            ("preserve_every_prior_safety_invariant", "no_autonomous_authority", "no_ungated_execution", "every_layer_auditable"),
            "PROCEED_POST_ARC_XXV_MASTER_REVIEW",
        ),
    )


def arc_specs() -> tuple[RuntimeArcSpec, ...]:
    return _specs()


def safety_checkpoint(arc: str) -> dict[str, object]:
    return {
        "arc": arc,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "fine_tuning_performed": False,
        "model_updates_performed": False,
        "provider_authority_granted": False,
        "autonomous_browsing_performed": False,
        "autonomous_execution_performed": False,
        "scheduler_started": False,
        "action_execution_performed": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "hidden_write_performed": False,
        "hyb1_promoted": False,
        "secret_printed": False,
        "safety_invariants": safety_invariants(),
    }


def create_investigation(topic: str = "topic X") -> Investigation:
    return Investigation(
        id=stable_v31_id("investigation", topic),
        title=f"Investigate {topic}",
        purpose=f"Define a reviewable investigation plan for {topic}.",
        initiator="user",
        scope="bounded_local_review",
        constraints=("no_autonomous_browsing", "no_provider_authority", "no_knowledge_mutation", "review_required"),
        priority=5,
        status="planned_only",
        review_state="review_required",
    )


def define_problem(question: str = "Investigate topic X.") -> ProblemDefinition:
    topic = _topic_from_query(question)
    return ProblemDefinition(
        problem_statement=f"Determine what is known, unknown, and review-required about {topic}.",
        known_facts=("DELTA can create a local investigation scaffold.", "External acquisition is disabled by default."),
        unknowns=(f"Topic-specific evidence about {topic} has not been collected.", "Confidence cannot exceed available evidence."),
        assumptions=("The user wants a reviewable plan rather than autonomous research.",),
        constraints=("no_autonomous_browsing", "no_provider_authority", "findings_not_authoritative"),
        success_criteria=("clear problem definition", "explicit gaps", "evidence plan", "reviewable findings"),
    )


def analyze_knowledge_gaps(problem: ProblemDefinition) -> KnowledgeGapAnalysis:
    return KnowledgeGapAnalysis(
        known=problem.known_facts,
        uncertain=problem.unknowns,
        unsupported=("No live external evidence has been fetched.",),
        missing_evidence=("primary source evidence", "conflicting evidence", "provenance-bearing citations"),
        confidence_improvements=("approved evidence acquisition", "contradiction review", "human review"),
    )


def generate_research_questions(topic: str = "topic X") -> tuple[ResearchQuestion, ...]:
    primary = f"What must be established to understand {topic} safely?"
    return (
        ResearchQuestion(
            question_id=stable_v31_id("research-question", topic, "primary"),
            primary_question=primary,
            subquestions=("What is already known?", "What evidence is missing?", "What contradictions must be checked?"),
            evidence_requirements=("local substrate review", "approved external evidence plan", "provenance"),
            dependencies=("problem_definition", "knowledge_gap_analysis"),
        ),
    )


def plan_investigation(topic: str = "topic X") -> tuple[dict[str, object], ...]:
    phases = ("review_existing_knowledge", "collect_missing_evidence_plan", "evaluate_contradictions", "generate_hypotheses", "request_review", "summarize")
    return tuple({"phase": phase, "status": "planned_only", "live_collection": False} for phase in phases)


def plan_evidence_collection() -> dict[str, object]:
    return {
        "required_evidence": ("provenance-bearing source", "direct support", "contradiction check"),
        "desired_evidence": ("independent corroboration", "confidence calibration material"),
        "optional_evidence": ("historical context", "edge cases"),
        "evidence_quality": "must be reviewable and cited",
        "expected_provenance": "source id, timestamp, retrieval approval, reviewer",
        "live_collection_performed": False,
    }


def create_findings(topic: str = "topic X") -> tuple[Finding, ...]:
    return (
        Finding(
            finding_id=stable_v31_id("finding", topic, "bounded"),
            statement=f"Current findings about {topic} are preliminary because evidence collection is disabled.",
            support=("local scaffold state",),
            confidence="low_to_moderate",
            limitations=("no live external evidence", "human review required"),
            evidence_references=("local_runtime_checkpoint",),
            review_state="review_required",
        ),
    )


def build_investigation_graph(investigation: Investigation, questions: tuple[ResearchQuestion, ...], findings: tuple[Finding, ...]) -> dict[str, object]:
    nodes = [{"id": investigation.id, "type": "problem", "label": investigation.title}]
    nodes.extend({"id": q.question_id, "type": "question", "label": q.primary_question} for q in questions)
    nodes.extend({"id": f.finding_id, "type": "finding", "label": f.statement} for f in findings)
    edges = [{"source": investigation.id, "target": q.question_id, "relation": "asks"} for q in questions]
    edges.extend({"source": questions[0].question_id, "target": f.finding_id, "relation": "produces_preliminary_finding"} for f in findings)
    return {"nodes": nodes, "edges": edges, "transient": True}


def recommend_investigation_next_steps(gaps: KnowledgeGapAnalysis) -> tuple[str, ...]:
    return ("collect_more_evidence", "request_review", "defer_conclusion", "confidence_insufficient", "proceed_to_reasoning_after_review")


def reflect_on_investigation(gaps: KnowledgeGapAnalysis) -> dict[str, object]:
    return {
        "bias": "may over-weight available local scaffold knowledge",
        "missing_perspectives": ("external evidence", "contradictory sources", "domain specialist review"),
        "alternative_explanations": ("insufficient evidence", "benchmark mismatch", "domain ambiguity"),
        "remaining_uncertainty": gaps.uncertain,
    }


def build_investigation_transaction(investigation: Investigation) -> InvestigationTransaction:
    return InvestigationTransaction(
        transaction_id=stable_v31_id("investigation-transaction", investigation.id),
        lifecycle=("created", "planned", "reviewed", "completed", "archived"),
    )


def build_arc_vii_checkpoint(topic: str = "topic X") -> dict[str, object]:
    investigation = create_investigation(topic)
    problem = define_problem(f"Investigate {topic}.")
    gaps = analyze_knowledge_gaps(problem)
    questions = generate_research_questions(topic)
    findings = create_findings(topic)
    return {
        "phase": "Runtime ARC VII V9.15",
        "investigation": investigation.as_dict(),
        "problem_definition": problem.as_dict(),
        "knowledge_gap_analysis": gaps.as_dict(),
        "research_questions": [q.as_dict() for q in questions],
        "investigation_plan": list(plan_investigation(topic)),
        "evidence_collection_plan": plan_evidence_collection(),
        "findings": [f.as_dict() for f in findings],
        "investigation_graph": build_investigation_graph(investigation, questions, findings),
        "recommendations": recommend_investigation_next_steps(gaps),
        "multi_investigation_management": {
            "parallel_supported": True,
            "background_scheduling": False,
            "shared_evidence": "references_only",
            "shared_findings": "review_only",
        },
        "reflection": reflect_on_investigation(gaps),
        "transaction": build_investigation_transaction(investigation).as_dict(),
        **safety_checkpoint("ARC VII"),
        "final_recommendation": "PROCEED_ARC_VIII_COGNITIVE_SPECIALIZATION_AND_MULTI_PERSPECTIVE_DELIBERATION",
    }


def default_specialists() -> tuple[Specialist, ...]:
    names = (
        ("evidence", "Evidence Specialist", "Inspect support, provenance, and missing evidence.", ("evidence", "citations")),
        ("logic", "Logic Specialist", "Inspect inference structure and assumptions.", ("reasoning", "logic")),
        ("planning", "Planning Specialist", "Inspect plans, dependencies, and sequencing.", ("planning", "workflow")),
        ("risk", "Risk Specialist", "Inspect safety, uncertainty, and failure modes.", ("risk", "safety")),
        ("scientific", "Scientific Specialist", "Inspect hypothesis and validation shape.", ("science", "method")),
        ("historical", "Historical Specialist", "Inspect temporal and historical context.", ("history", "timeline")),
        ("systems", "Systems Specialist", "Inspect interacting system components.", ("systems", "architecture")),
        ("contradiction", "Contradiction Specialist", "Inspect conflicts and counterevidence.", ("conflict", "contradiction")),
        ("procedural", "Procedural Specialist", "Inspect steps and procedural constraints.", ("procedure", "operations")),
        ("meta", "Meta-Reasoning Specialist", "Inspect reasoning quality and perspective coverage.", ("meta", "reflection")),
    )
    return tuple(
        Specialist(
            specialist_id=stable_v31_id("specialist", key),
            name=name,
            purpose=purpose,
            supported_domains=domains,
            reasoning_style="advisory_analysis",
            confidence_profile="conservative",
            activation_policy="executive_selected_only",
            status="advisory_only",
        )
        for key, name, purpose, domains in names
    )


def select_specialists(query: str = "Analyze topic X.") -> tuple[Specialist, ...]:
    normalized = query.lower()
    specialists = default_specialists()
    selected = [s for s in specialists if s.name in ("Evidence Specialist", "Logic Specialist", "Risk Specialist", "Meta-Reasoning Specialist")]
    if "plan" in normalized or "workflow" in normalized:
        selected.append(next(s for s in specialists if s.name == "Planning Specialist"))
    if "conflict" in normalized or "disagree" in normalized:
        selected.append(next(s for s in specialists if s.name == "Contradiction Specialist"))
    return tuple(dict((s.specialist_id, s) for s in selected).values())


def deliberate_with_specialists(query: str = "Analyze topic X.") -> tuple[SpecialistDeliberation, ...]:
    return tuple(
        SpecialistDeliberation(
            specialist_id=s.specialist_id,
            reasoning=f"{s.name} provides an advisory perspective on {query}.",
            confidence="bounded",
            support=("local scaffold context",),
            limitations=("no provider authority", "no durable knowledge mutation", "human review required"),
        )
        for s in select_specialists(query)
    )


def build_consensus(deliberations: tuple[SpecialistDeliberation, ...]) -> dict[str, object]:
    return {
        "agreement": "all selected specialists agree the result is advisory and evidence-bounded",
        "disagreement": "none resolved authoritatively",
        "missing_evidence": ("external corroboration", "domain-specific sources"),
        "confidence_overlap": "bounded",
        "voting_used": False,
        "authority_granted": False,
    }


def build_arc_viii_checkpoint(query: str = "Analyze topic X.") -> dict[str, object]:
    selected = select_specialists(query)
    deliberations = deliberate_with_specialists(query)
    consensus = build_consensus(deliberations)
    graph = {
        "nodes": [{"id": s.specialist_id, "type": "specialist", "label": s.name} for s in selected],
        "edges": [{"source": d.specialist_id, "target": "consensus", "relation": "advises"} for d in deliberations],
        "transient": True,
    }
    return {
        "phase": "Runtime ARC VIII V10.15",
        "specialist_registry": [s.as_dict() for s in default_specialists()],
        "selected_specialists": [s.as_dict() for s in selected],
        "specialist_deliberations": [d.as_dict() for d in deliberations],
        "consensus": consensus,
        "conflict_framework": {"unresolved_disagreements": (), "review_recommendations": ("request_review",)},
        "meta_reasoning": {"strongest_path": "evidence_bounded_advisory_path", "weaker_evidence": "external evidence unavailable"},
        "confidence_fusion": {"independent_confidence": "bounded", "shared_confidence": "bounded", "confidence_spread": "visible"},
        "deliberation_graph": graph,
        "specialist_reflection": {"missing_evidence": ("external corroboration",), "alternative_approaches": ("domain review",)},
        "specialist_transactions": {"selection": True, "reasoning": True, "consensus": True, "reflection": True, "destroy_after_request": True},
        "performance_metrics": {"participation": len(selected), "agreement": "bounded", "ranking_promotion": False, "learning": False},
        **safety_checkpoint("ARC VIII"),
        "specialist_authority_granted": False,
        "final_recommendation": "PROCEED_ARC_IX_GOVERNED_EXTERNAL_EVIDENCE_ACQUISITION",
    }


def build_generic_arc_checkpoint(spec: RuntimeArcSpec) -> dict[str, object]:
    samples: dict[str, object] = {}
    if spec.arc == "ARC IX":
        samples["external_evidence_request"] = ExternalEvidenceRequest(stable_v31_id("external-evidence", spec.arc), "approved_evidence_need", "approval_chain_required", True).as_dict()
    if spec.arc == "ARC X":
        samples["tool_invocation_plan"] = ToolInvocationPlan(stable_v31_id("tool-plan", spec.arc), "future_tool", "approval_required", True).as_dict()
    if spec.arc == "ARC XI":
        samples["integration_preview"] = IntegrationPreview(stable_v31_id("integration-preview", spec.arc), "candidate_only", ("admin", "overwatch"), True).as_dict()
    if spec.arc == "ARC XII":
        samples["benchmark_suite"] = CognitiveBenchmarkSuite(stable_v31_id("benchmark-suite", spec.arc), "regression and cognitive validation").as_dict()
    return {
        "phase": f"Runtime {spec.arc}",
        "title": spec.title,
        "purpose": spec.purpose,
        "objects": spec.objects,
        "rules": spec.rules,
        "sample_objects": samples,
        "dashboard": f"ui/delta_{_slug(spec.arc)}_dashboard.html",
        "status": "architecture_scaffold_only",
        **safety_checkpoint(spec.arc),
        "final_recommendation": spec.recommendation,
    }


def build_arc_checkpoint(arc: str) -> dict[str, object]:
    normalized = arc.strip().upper()
    if normalized == "ARC VII":
        return build_arc_vii_checkpoint()
    if normalized == "ARC VIII":
        return build_arc_viii_checkpoint()
    for spec in arc_specs():
        if spec.arc == normalized:
            return build_generic_arc_checkpoint(spec)
    raise KeyError(f"Unknown ARC: {arc}")


def build_all_arc_checkpoints() -> dict[str, dict[str, object]]:
    return {spec.arc: build_arc_checkpoint(spec.arc) for spec in arc_specs()}


def render_arc_report(data: dict[str, object]) -> str:
    objects = data.get("objects") or tuple(data.get("investigation", {}).keys()) or tuple(data.keys())
    object_lines = "\n".join(f"- `{obj}`" for obj in objects)
    rules = data.get("rules", ())
    rule_lines = "\n".join(f"- `{rule}`" for rule in rules)
    return f"""# {data['phase']} Safety Checkpoint

## Summary

{data.get('title', data['phase'])}

{data.get('purpose', 'Review-only cognitive runtime scaffold.')}

## Implemented Objects

{object_lines}

## Rules

{rule_lines}

## Safety

- Model B default: {data['model_b_default']}
- HYB1: {data['hyb1']}
- Training performed: {data['training_performed']}
- Provider authority granted: {data['provider_authority_granted']}
- Autonomous browsing performed: {data['autonomous_browsing_performed']}
- Autonomous execution performed: {data['autonomous_execution_performed']}
- Scheduler started: {data['scheduler_started']}
- Action execution performed: {data['action_execution_performed']}
- Memory mutation performed: {data['memory_mutation_performed']}
- Knowledge mutation performed: {data['knowledge_mutation_performed']}

Final recommendation: `{data['final_recommendation']}`
"""


def render_dashboard(data: dict[str, object]) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{data['phase']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}pre{{white-space:pre-wrap}}</style></head>
<body>
<h1>{data['phase']}</h1>
<section><h2>Purpose</h2><p>{data.get('purpose', data.get('title', 'Review-only scaffold.'))}</p></section>
<section><h2>Objects</h2><pre>{json.dumps(data.get('objects', list(data.keys())), indent=2)}</pre></section>
<section><h2>Safety</h2><pre>{json.dumps({k: data[k] for k in data if k.endswith('_performed') or k in ('model_b_default', 'hyb1', 'provider_authority_granted', 'scheduler_started')}, indent=2)}</pre></section>
<section><h2>Recommendation</h2><p>{data['final_recommendation']}</p></section>
</body></html>
"""


def write_arc_reports() -> dict[str, object]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    Path("ui").mkdir(parents=True, exist_ok=True)
    checkpoints = build_all_arc_checkpoints()
    for arc, data in checkpoints.items():
        slug = _slug(arc)
        Path(f"reports/runtime_{slug}_safety_checkpoint.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        Path(f"reports/runtime_{slug}_safety_checkpoint.md").write_text(render_arc_report(data), encoding="utf-8")
        Path(f"ui/delta_{slug}_dashboard.html").write_text(render_dashboard(data), encoding="utf-8")
    summary = {
        "phase": "Runtime ARC VII-XXV Master Safety Checkpoint",
        "arcs": {arc: data["final_recommendation"] for arc, data in checkpoints.items()},
        "arc_count": len(checkpoints),
        "global_prohibitions": GLOBAL_PROHIBITIONS,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "provider_authority_granted": False,
        "autonomous_browsing_performed": False,
        "autonomous_execution_performed": False,
        "scheduler_started": False,
        "action_execution_performed": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "hidden_write_performed": False,
        "final_recommendation": "PROCEED_POST_ARC_XXV_MASTER_REVIEW",
    }
    SUMMARY_REPORT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    SUMMARY_REPORT_MD.write_text(render_master_report(summary), encoding="utf-8")
    SUMMARY_DASHBOARD.write_text(render_dashboard(summary), encoding="utf-8")
    DOCS_CONTINUATION.write_text(render_continuation(summary), encoding="utf-8")
    return summary


def render_master_report(summary: dict[str, object]) -> str:
    arcs = "\n".join(f"- {arc}: `{rec}`" for arc, rec in summary["arcs"].items())
    return f"""# Runtime ARC VII-XXV Master Safety Checkpoint

Implemented architecture scaffolds from ARC VII through ARC XXV.

## Completed Arcs

{arcs}

## Safety

- Model B default: {summary['model_b_default']}
- HYB1: {summary['hyb1']}
- Training performed: {summary['training_performed']}
- Provider authority granted: {summary['provider_authority_granted']}
- Autonomous browsing performed: {summary['autonomous_browsing_performed']}
- Autonomous execution performed: {summary['autonomous_execution_performed']}
- Scheduler started: {summary['scheduler_started']}
- Action execution performed: {summary['action_execution_performed']}
- Memory mutation performed: {summary['memory_mutation_performed']}
- Knowledge mutation performed: {summary['knowledge_mutation_performed']}
- Hidden write performed: {summary['hidden_write_performed']}

Final recommendation: `{summary['final_recommendation']}`
"""


def render_continuation(summary: dict[str, object]) -> str:
    return (
        "# DELTA ARC VII-XXV Continuation\n\n"
        "ARC VII through ARC XXV are complete as deterministic architecture scaffolds. They add structured investigation, advisory specialists, governed external evidence acquisition design, controlled tool/provider runtime design, integration preview, evaluation, replay, domain packs, executive operations, COS, world model, memory layering, self model, adaptive executive, multi-runtime collaboration, distributed fabric, scientific discovery, simulation, and unified cognitive runtime scaffolds.\n\n"
        "No training, fine-tuning, model update, provider authority, autonomous browsing, autonomous execution, scheduler activation, action execution, memory mutation, knowledge mutation, hidden write, HYB1 promotion, or secret printing occurred.\n\n"
        f"Final recommendation: `{summary['final_recommendation']}`.\n"
    )


def explain_investigation(query: str) -> dict[str, object]:
    data = build_arc_vii_checkpoint("topic X")
    normalized = query.lower()
    if "already know" in normalized:
        answer = "The investigation already knows only local scaffold facts: DELTA can plan reviewable investigations and external collection is disabled by default."
        payload = {"known": data["problem_definition"]["known_facts"]}
    elif "not know" in normalized:
        answer = "DELTA does not yet know topic-specific evidence because no autonomous browsing, provider authority, or live evidence collection is enabled."
        payload = {"unknowns": data["problem_definition"]["unknowns"]}
    elif "evidence" in normalized:
        answer = "DELTA would seek provenance-bearing primary support, contradiction checks, and independently reviewable corroboration, but collection is only planned."
        payload = {"evidence_collection_plan": data["evidence_collection_plan"]}
    elif "questions" in normalized or "answered first" in normalized:
        answer = "The first research questions ask what is known, what evidence is missing, and what contradictions must be checked."
        payload = {"research_questions": data["research_questions"]}
    elif "findings" in normalized:
        answer = "Current findings are preliminary and not durable knowledge because live evidence collection remains disabled."
        payload = {"findings": data["findings"]}
    elif "uncertain" in normalized:
        answer = "The findings are uncertain because evidence collection is disabled, external corroboration is missing, and human review is required."
        payload = {"reflection": data["reflection"]}
    else:
        answer = "Created a reviewable investigation plan for topic X. It defines the problem, gaps, research questions, evidence plan, preliminary findings, and review recommendations."
        payload = {"investigation": data["investigation"], "recommendations": data["recommendations"]}
    return {"phase": "Runtime ARC VII", "query": query, "answer_text": answer, **payload, "safety": safety_checkpoint("ARC VII")}


def explain_specialists(query: str) -> dict[str, object]:
    data = build_arc_viii_checkpoint(query)
    normalized = query.lower()
    if "which specialists" in normalized or "participated" in normalized:
        answer = "Selected advisory specialists include evidence, logic, risk, and meta-reasoning perspectives."
        payload = {"selected_specialists": data["selected_specialists"]}
    elif "why" in normalized:
        answer = "Specialists were selected because the executive layer needs evidence, inference, risk, and reasoning-quality perspectives."
        payload = {"selected_specialists": data["selected_specialists"]}
    elif "disagree" in normalized:
        answer = "No disagreement is resolved authoritatively; conflicts remain reviewable until better evidence exists."
        payload = {"conflict_framework": data["conflict_framework"]}
    elif "consensus" in normalized:
        answer = "Consensus is formed by comparing advisory reasoning, support, limitations, and confidence overlap, without voting or authority transfer."
        payload = {"consensus": data["consensus"]}
    elif "weakest" in normalized or "uncertain" in normalized:
        answer = "The weakest evidence is external corroboration because no provider authority or autonomous evidence acquisition is enabled."
        payload = {"meta_reasoning": data["meta_reasoning"], "confidence_fusion": data["confidence_fusion"]}
    else:
        answer = "Analyzed the topic from multiple advisory perspectives. Specialists reasoned independently, produced bounded confidence, and remained non-authoritative."
        payload = {"specialist_deliberations": data["specialist_deliberations"], "consensus": data["consensus"]}
    return {"phase": "Runtime ARC VIII", "query": query, "answer_text": answer, **payload, "safety": safety_checkpoint("ARC VIII")}


def _topic_from_query(query: str) -> str:
    cleaned = query.strip().rstrip(".?!")
    lower = cleaned.lower()
    for prefix in ("investigate ", "analyze ", "research "):
        if lower.startswith(prefix):
            return cleaned[len(prefix) :] or "topic X"
    return "topic X"


def _slug(arc: str) -> str:
    return arc.lower().replace(" ", "_")


def _json_default(value: object) -> object:
    if hasattr(value, "as_dict"):
        return value.as_dict()
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    print(write_arc_reports()["final_recommendation"])

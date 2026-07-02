from __future__ import annotations

from dataclasses import dataclass

from orchestration.curriculum.calibration_curriculum import CalibrationObjective


@dataclass(frozen=True)
class ProfileSpec:
    capability: str
    task_type: str
    required_capabilities: tuple[str, ...]
    expected_signals: tuple[str, ...]
    domains: tuple[str, ...]
    stressors: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    decisions: tuple[str, ...]
    prompt_frame: str


BROAD_PROFILE_SPECS: dict[str, ProfileSpec] = {
    "planning": ProfileSpec(
        capability="planning",
        task_type="planning",
        required_capabilities=("planning", "prediction", "uncertainty"),
        expected_signals=("planning_failure", "prediction_pressure", "revision"),
        domains=("emergency response", "construction", "hospital staffing", "logistics", "city services"),
        stressors=("a permit assumption fails", "a critical supplier slips", "weather invalidates timing", "staff availability changes", "equipment capacity drops"),
        evidence_sources=("dispatch logs", "inspection records", "staff rosters", "weather updates", "resource telemetry"),
        decisions=("resequence the plan", "delay the lowest-risk work", "escalate the bottleneck", "split resources", "revise the dependency order"),
        prompt_frame=(
            "Create and revise a plan for {domain}. The plan is disrupted when {stressor}. "
            "Use {evidence} to decide whether to {decision}. State a testable prediction, "
            "the evidence that would falsify it, and the belief revision Delta should preserve."
        ),
    ),
    "contradiction": ProfileSpec(
        capability="contradiction",
        task_type="reasoning",
        required_capabilities=("contradiction", "evidence", "belief_revision"),
        expected_signals=("contradiction_resolution", "provenance", "belief_challenge"),
        domains=("eyewitness reports", "sensor readings", "audit findings", "expert testimony", "policy interpretation"),
        stressors=("two trusted sources disagree", "a later record reverses an earlier claim", "metadata conflicts with content", "a high-confidence claim fails", "the same event has incompatible timestamps"),
        evidence_sources=("source provenance", "raw logs", "chain-of-custody notes", "calibration records", "revision history"),
        decisions=("preserve both claims", "rank evidence quality", "request a decisive observation", "lower confidence", "mark the contradiction unresolved"),
        prompt_frame=(
            "Analyze a contradiction in {domain}: {stressor}. Use {evidence} to decide how to "
            "{decision}. Do not delete either claim. Identify the conflicting claims, the "
            "resolution evidence, and the prediction that would confirm the resolution."
        ),
    ),
    "causal_reasoning": ProfileSpec(
        capability="causal_reasoning",
        task_type="reasoning",
        required_capabilities=("causal_reasoning", "prediction", "evidence"),
        expected_signals=("causal_chain", "falsification", "prediction_pressure"),
        domains=("industrial maintenance", "supply chains", "public health", "software outages", "traffic flow"),
        stressors=("an intervention has a delayed side effect", "correlation is mistaken for causation", "a hidden variable changes", "two causes interact", "a counterfactual path was ignored"),
        evidence_sources=("time-series data", "control comparisons", "intervention logs", "baseline measurements", "failure timelines"),
        decisions=("select the most likely cause", "reject a spurious cause", "design a counterfactual test", "revise the causal graph", "predict the next downstream effect"),
        prompt_frame=(
            "Reason causally about {domain}. The case involves {stressor}. Use {evidence} to "
            "{decision}. Explain the causal chain, one alternative explanation, and what "
            "future observation would change the conclusion."
        ),
    ),
    "scientific_reasoning": ProfileSpec(
        capability="scientific_reasoning",
        task_type="research",
        required_capabilities=("scientific_reasoning", "hypothesis_revision", "prediction"),
        expected_signals=("hypothesis_generation", "falsification", "information_gain"),
        domains=("water quality", "battery degradation", "crop yield", "material fatigue", "air quality"),
        stressors=("observations vary by site", "the first hypothesis fails a control", "a confounder appears", "measurements conflict", "a replication attempt is weaker"),
        evidence_sources=("controlled trials", "field measurements", "lab assays", "replication data", "instrument calibration"),
        decisions=("form competing hypotheses", "choose a control", "predict discriminating evidence", "revise the hypothesis", "identify the confounder"),
        prompt_frame=(
            "Design scientific reasoning for {domain}. The investigation faces this issue: "
            "{stressor}. Use {evidence} to {decision}. Provide two hypotheses, predictions "
            "that distinguish them, and the evidence that would revise confidence."
        ),
    ),
    "tool_use": ProfileSpec(
        capability="tool_use",
        task_type="planning",
        required_capabilities=("tool_use", "planning", "evidence"),
        expected_signals=("tool_selection", "prediction_pressure", "contradiction_resolution"),
        domains=("incident response", "invoice audit", "contract review", "log triage", "data reconciliation"),
        stressors=("the first source is incomplete", "two tools return inconsistent outputs", "timestamps are missing", "a parser drops a field", "the primary dataset is stale"),
        evidence_sources=("application logs", "source documents", "database snapshots", "version history", "API responses"),
        decisions=("choose the first tool", "cross-check the result", "escalate to another source", "reject a malformed result", "preserve provenance"),
        prompt_frame=(
            "Plan tool use for {domain}. The task is difficult because {stressor}. Use "
            "{evidence} to {decision}. Name the tool sequence, expected evidence, failure "
            "mode, and belief revision if the first result is contradicted."
        ),
    ),
    "long_dependency": ProfileSpec(
        capability="long_dependency",
        task_type="reasoning",
        required_capabilities=("long_dependency", "planning", "prediction"),
        expected_signals=("dependency_reasoning", "belief_revision", "prediction_pressure"),
        domains=("contract changes", "hospital operations", "software release trains", "construction sequencing", "municipal budgets"),
        stressors=("an upstream assumption changes", "a temporary exception expires", "a dependency is hidden", "a downstream team misses a handoff", "a policy change affects multiple steps"),
        evidence_sources=("dependency maps", "change orders", "handoff records", "approval chains", "timeline audits"),
        decisions=("trace downstream effects", "revise the first affected belief", "predict the next bottleneck", "separate hard and soft dependencies", "identify the critical path"),
        prompt_frame=(
            "Trace long dependencies in {domain}. The situation changes because {stressor}. "
            "Use {evidence} to {decision}. Preserve the dependency chain, identify the first "
            "belief to revise, and state a prediction about the next affected node."
        ),
    ),
    "probabilistic_reasoning": ProfileSpec(
        capability="probabilistic_reasoning",
        task_type="reasoning",
        required_capabilities=("probability", "uncertainty", "prediction"),
        expected_signals=("uncertainty", "prediction_pressure", "belief_revision"),
        domains=("forecasting demand", "medical screening", "risk scoring", "quality control", "insurance claims"),
        stressors=("base rates are ignored", "new evidence changes likelihood", "sample size is small", "false positives are costly", "prior confidence was too high"),
        evidence_sources=("base-rate tables", "historical outcomes", "test sensitivity data", "sampling notes", "calibration curves"),
        decisions=("update likelihood", "separate probability from confidence", "choose the safer prediction", "identify missing evidence", "revise the prior"),
        prompt_frame=(
            "Apply probabilistic reasoning to {domain}. The challenge is that {stressor}. "
            "Use {evidence} to {decision}. Give an updated qualitative probability, what "
            "would change it, and a falsifiable prediction."
        ),
    ),
    "resource_allocation": ProfileSpec(
        capability="resource_allocation",
        task_type="planning",
        required_capabilities=("planning", "optimization", "tradeoffs"),
        expected_signals=("planning_failure", "tradeoff", "prediction_pressure"),
        domains=("emergency shelters", "snow removal", "warehouse labor", "hospital beds", "infrastructure repair"),
        stressors=("resources drop by 20 percent", "demand spikes unexpectedly", "one resource is indivisible", "a priority group changes", "a constraint becomes binding"),
        evidence_sources=("capacity reports", "demand forecasts", "service-level data", "equity constraints", "cost records"),
        decisions=("allocate scarce capacity", "defer lower-risk work", "protect the critical service", "rebalance resources", "justify a tradeoff"),
        prompt_frame=(
            "Allocate resources for {domain}. The constraint is that {stressor}. Use "
            "{evidence} to {decision}. Explain the tradeoff, predict the failure mode, "
            "and state what evidence would require reallocation."
        ),
    ),
    "multi_agent_coordination": ProfileSpec(
        capability="multi_agent_coordination",
        task_type="planning",
        required_capabilities=("planning", "coordination", "uncertainty"),
        expected_signals=("coordination", "prediction_pressure", "belief_revision"),
        domains=("mutual aid response", "construction subcontractors", "software teams", "hospital departments", "city agencies"),
        stressors=("agents have different incentives", "handoffs are delayed", "one agent withholds information", "responsibilities overlap", "communication channels fail"),
        evidence_sources=("status updates", "handoff logs", "shared calendars", "responsibility matrices", "incident channels"),
        decisions=("assign authority", "resolve a coordination conflict", "predict a handoff failure", "revise the coordination plan", "preserve accountability"),
        prompt_frame=(
            "Coordinate multiple agents in {domain}. The complication is that {stressor}. "
            "Use {evidence} to {decision}. Identify each agent's belief, the likely failure "
            "point, and the evidence needed to revise the plan."
        ),
    ),
    "economics": ProfileSpec(
        capability="economics",
        task_type="reasoning",
        required_capabilities=("economics", "causal_reasoning", "prediction"),
        expected_signals=("tradeoff", "causal_chain", "prediction_pressure"),
        domains=("housing supply", "labor markets", "municipal budgets", "energy prices", "insurance incentives"),
        stressors=("an incentive creates a side effect", "a subsidy shifts demand", "prices signal scarcity", "a regulation changes behavior", "externalities are unpriced"),
        evidence_sources=("price trends", "budget reports", "elasticity estimates", "participation data", "market comparisons"),
        decisions=("predict behavioral response", "identify a tradeoff", "revise an incentive", "separate correlation from cause", "choose a policy test"),
        prompt_frame=(
            "Analyze an economic decision in {domain}. The issue is that {stressor}. "
            "Use {evidence} to {decision}. Explain incentives, predict an unintended "
            "effect, and name evidence that would revise the belief."
        ),
    ),
    "medical_reasoning": ProfileSpec(
        capability="medical_reasoning",
        task_type="reasoning",
        required_capabilities=("medical_reasoning", "uncertainty", "evidence"),
        expected_signals=("differential_reasoning", "belief_revision", "prediction_pressure"),
        domains=("triage", "diagnostic uncertainty", "medication safety", "public health screening", "care coordination"),
        stressors=("symptoms are ambiguous", "a test has false positives", "two conditions share signs", "a contraindication appears", "history conflicts with labs"),
        evidence_sources=("vital signs", "test characteristics", "patient history", "medication records", "follow-up observations"),
        decisions=("rank differential possibilities", "choose a safer next step", "revise the working hypothesis", "identify missing evidence", "predict deterioration risk"),
        prompt_frame=(
            "Reason medically about {domain} without giving treatment instructions. The case has "
            "{stressor}. Use {evidence} to {decision}. State uncertainty, evidence to seek, "
            "and a prediction that would change triage priority."
        ),
    ),
    "mechanical_diagnosis": ProfileSpec(
        capability="mechanical_diagnosis",
        task_type="reasoning",
        required_capabilities=("diagnosis", "causal_reasoning", "prediction"),
        expected_signals=("failure_analysis", "falsification", "prediction_pressure"),
        domains=("pumps", "HVAC systems", "vehicle drivetrains", "industrial conveyors", "hydraulic systems"),
        stressors=("symptoms appear only under load", "a repair creates a new fault", "sensor readings conflict", "wear is uneven", "failure is intermittent"),
        evidence_sources=("vibration data", "maintenance logs", "thermal readings", "load tests", "inspection photos"),
        decisions=("isolate the likely fault", "reject a false cause", "choose a diagnostic test", "predict the next symptom", "revise the maintenance plan"),
        prompt_frame=(
            "Diagnose a mechanical issue in {domain}. The difficulty is that {stressor}. "
            "Use {evidence} to {decision}. Explain causal evidence, an alternative fault, "
            "and what observation would falsify the diagnosis."
        ),
    ),
    "software_debugging": ProfileSpec(
        capability="software_debugging",
        task_type="coding",
        required_capabilities=("coding", "debugging", "evidence"),
        expected_signals=("regression_test", "boundary_preservation", "falsification"),
        domains=("API adapters", "async workers", "database migrations", "serialization", "permission checks"),
        stressors=("a field is silently dropped", "a race condition appears", "old data violates an assumption", "an error is swallowed", "a boundary loses provenance"),
        evidence_sources=("unit tests", "logs", "stack traces", "schema diffs", "reproduction steps"),
        decisions=("write a regression test", "identify the failing boundary", "preserve provenance", "isolate the minimal fix", "predict the regression risk"),
        prompt_frame=(
            "Debug a software failure in {domain}. The bug is that {stressor}. Use "
            "{evidence} to {decision}. Explain the root cause, propose a regression test, "
            "and state what evidence would disconfirm the fix."
        ),
    ),
    "systems_engineering": ProfileSpec(
        capability="systems_engineering",
        task_type="planning",
        required_capabilities=("systems_engineering", "planning", "risk"),
        expected_signals=("dependency_reasoning", "tradeoff", "prediction_pressure"),
        domains=("power grids", "distributed services", "water systems", "transport networks", "manufacturing lines"),
        stressors=("local optimization harms the whole system", "a redundancy path is untested", "interfaces are underspecified", "capacity is coupled", "failure cascades across layers"),
        evidence_sources=("architecture diagrams", "capacity tests", "interface contracts", "failure drills", "operating telemetry"),
        decisions=("identify a system bottleneck", "revise the architecture assumption", "predict cascade risk", "rank mitigation options", "separate local and global optima"),
        prompt_frame=(
            "Analyze systems engineering for {domain}. The risk is that {stressor}. "
            "Use {evidence} to {decision}. Explain dependencies, tradeoffs, and a prediction "
            "that would validate or falsify the system assumption."
        ),
    ),
    "cybersecurity_defense": ProfileSpec(
        capability="cybersecurity_defense",
        task_type="reasoning",
        required_capabilities=("security", "evidence", "risk"),
        expected_signals=("threat_model", "contradiction_resolution", "prediction_pressure"),
        domains=("identity systems", "endpoint alerts", "cloud storage", "network segmentation", "software supply chains"),
        stressors=("an alert conflicts with baseline behavior", "a credential is reused", "logs are incomplete", "a dependency is suspicious", "a control fails silently"),
        evidence_sources=("audit logs", "network flows", "identity events", "hash records", "change history"),
        decisions=("triage the alert", "rank likely attack paths", "preserve evidence", "choose a containment step", "predict attacker movement"),
        prompt_frame=(
            "Defend a cybersecurity environment involving {domain}. The signal is hard because "
            "{stressor}. Use {evidence} to {decision}. Identify competing explanations, "
            "evidence to collect, and a prediction about next attacker behavior."
        ),
    ),
    "experimental_design": ProfileSpec(
        capability="experimental_design",
        task_type="research",
        required_capabilities=("experimental_design", "evidence", "prediction"),
        expected_signals=("control_selection", "falsification", "information_gain"),
        domains=("education policy", "operations changes", "medical screening", "software reliability", "energy efficiency"),
        stressors=("selection bias is likely", "the sample is small", "a confounder is hidden", "outcomes are delayed", "measurement changes behavior"),
        evidence_sources=("randomization plans", "control groups", "measurement protocols", "baseline data", "pre-registered outcomes"),
        decisions=("choose a control", "reduce confounding", "predict observable outcomes", "revise the experiment", "separate signal from noise"),
        prompt_frame=(
            "Design an experiment for {domain}. The main threat is that {stressor}. "
            "Use {evidence} to {decision}. State the hypothesis, control, predicted result, "
            "and evidence that would force hypothesis revision."
        ),
    ),
    "ethical_tradeoffs": ProfileSpec(
        capability="ethical_tradeoffs",
        task_type="reasoning",
        required_capabilities=("ethics", "planning", "uncertainty"),
        expected_signals=("tradeoff", "belief_challenge", "provenance"),
        domains=("hospital allocation", "public safety", "data privacy", "disaster response", "workplace automation"),
        stressors=("values conflict", "benefits and burdens are uneven", "consent is incomplete", "urgency limits evidence", "a rule creates harm in an edge case"),
        evidence_sources=("policy constraints", "stakeholder statements", "harm estimates", "rights analysis", "precedent records"),
        decisions=("surface the tradeoff", "preserve uncertainty", "choose the least harmful option", "revise a rule", "identify missing stakeholder evidence"),
        prompt_frame=(
            "Analyze an ethical tradeoff in {domain}. The dilemma is that {stressor}. "
            "Use {evidence} to {decision}. Explain competing values, uncertainty, and what "
            "new evidence would change the recommendation."
        ),
    ),
    "negotiation": ProfileSpec(
        capability="negotiation",
        task_type="planning",
        required_capabilities=("negotiation", "planning", "prediction"),
        expected_signals=("multi_agent", "prediction_pressure", "belief_revision"),
        domains=("contract terms", "labor scheduling", "vendor disputes", "interagency agreements", "resource sharing"),
        stressors=("parties hide priorities", "a concession changes incentives", "trust is low", "deadlines are asymmetric", "outside options differ"),
        evidence_sources=("stated interests", "past concessions", "deadline records", "cost estimates", "communication history"),
        decisions=("identify interests", "predict a concession response", "choose a bargaining move", "revise trust estimates", "preserve unresolved disagreement"),
        prompt_frame=(
            "Plan a negotiation about {domain}. The challenge is that {stressor}. "
            "Use {evidence} to {decision}. Identify each party's likely belief, a prediction "
            "about response, and evidence that would revise the strategy."
        ),
    ),
    "risk_assessment": ProfileSpec(
        capability="risk_assessment",
        task_type="reasoning",
        required_capabilities=("risk", "prediction", "uncertainty"),
        expected_signals=("risk_analysis", "prediction_pressure", "belief_revision"),
        domains=("infrastructure", "public health", "project delivery", "financial controls", "data migration"),
        stressors=("low probability has high impact", "risk indicators conflict", "mitigation creates a secondary risk", "exposure changes over time", "controls are untested"),
        evidence_sources=("risk registers", "incident history", "control tests", "exposure metrics", "trend data"),
        decisions=("rank risks", "choose a mitigation", "predict residual risk", "revise severity", "identify the leading indicator"),
        prompt_frame=(
            "Assess risk in {domain}. The situation is difficult because {stressor}. "
            "Use {evidence} to {decision}. Explain likelihood, impact, uncertainty, and "
            "what observation would trigger a revised risk rating."
        ),
    ),
    "failure_analysis": ProfileSpec(
        capability="failure_analysis",
        task_type="reasoning",
        required_capabilities=("failure_analysis", "causal_reasoning", "evidence"),
        expected_signals=("root_cause", "falsification", "belief_revision"),
        domains=("construction defects", "software incidents", "equipment outages", "service failures", "safety incidents"),
        stressors=("the obvious cause is wrong", "multiple small failures combine", "a fix masks the symptom", "documentation is incomplete", "the failure recurs intermittently"),
        evidence_sources=("incident timelines", "change logs", "witness notes", "telemetry", "postmortem records"),
        decisions=("identify root cause", "separate symptom from cause", "predict recurrence", "revise corrective action", "choose confirming evidence"),
        prompt_frame=(
            "Analyze a failure in {domain}. The challenge is that {stressor}. Use "
            "{evidence} to {decision}. Give the causal chain, competing explanation, "
            "prediction of recurrence, and evidence that would falsify the analysis."
        ),
    ),
    "counterfactual_reasoning": ProfileSpec(
        capability="counterfactual_reasoning",
        task_type="reasoning",
        required_capabilities=("counterfactual", "causal_reasoning", "prediction"),
        expected_signals=("counterfactual_test", "belief_revision", "falsification"),
        domains=("policy choices", "maintenance decisions", "software releases", "medical triage", "resource allocation"),
        stressors=("the observed outcome has multiple causes", "the alternative was never tried", "one variable changed with another", "selection effects distort evidence", "the baseline is uncertain"),
        evidence_sources=("matched comparisons", "historical baselines", "natural experiments", "control groups", "pre-change metrics"),
        decisions=("construct the counterfactual", "identify what would differ", "revise causal belief", "predict the unobserved outcome", "choose a comparison group"),
        prompt_frame=(
            "Reason counterfactually about {domain}. The difficulty is that {stressor}. "
            "Use {evidence} to {decision}. State the counterfactual claim, what evidence "
            "would support it, and how Delta should revise confidence."
        ),
    ),
    "analogical_reasoning": ProfileSpec(
        capability="analogical_reasoning",
        task_type="reasoning",
        required_capabilities=("analogy", "transfer", "evidence"),
        expected_signals=("transfer_learning", "generalization", "belief_challenge"),
        domains=("software reliability", "medical triage", "logistics", "governance", "mechanical diagnosis"),
        stressors=("the analogy shares structure but not surface features", "a tempting analogy breaks at one constraint", "source and target have different incentives", "scale changes the lesson", "a hidden dependency differs"),
        evidence_sources=("structural mappings", "failure cases", "constraint comparisons", "outcome records", "domain assumptions"),
        decisions=("map the analogy", "reject a misleading feature", "transfer the useful rule", "predict where the analogy fails", "revise the generalization"),
        prompt_frame=(
            "Use analogical reasoning for {domain}. The challenge is that {stressor}. "
            "Use {evidence} to {decision}. Identify source and target structure, what "
            "transfers, what does not, and a prediction that tests the analogy."
        ),
    ),
    "cross_domain_transfer": ProfileSpec(
        capability="cross_domain_transfer",
        task_type="reasoning",
        required_capabilities=("transfer", "generalization", "prediction"),
        expected_signals=("cross_domain_reasoning", "transfer_learning", "prediction_pressure"),
        domains=("medicine to maintenance", "software tests to governance", "logistics to hospital staffing", "ecology to cybersecurity", "economics to city services"),
        stressors=("the target domain changes constraints", "the source rule overfits", "terminology hides structural similarity", "a transfer creates a new risk", "evidence quality differs between domains"),
        evidence_sources=("domain mappings", "constraint lists", "success cases", "failure cases", "validation outcomes"),
        decisions=("transfer a principle", "identify the boundary", "predict target-domain failure", "revise the transferred rule", "choose validation evidence"),
        prompt_frame=(
            "Transfer reasoning across {domain}. The risk is that {stressor}. Use "
            "{evidence} to {decision}. Explain the reusable concept, boundary condition, "
            "and evidence that would validate or reject the transfer."
        ),
    ),
    "hierarchical_planning": ProfileSpec(
        capability="hierarchical_planning",
        task_type="planning",
        required_capabilities=("planning", "hierarchy", "dependency_reasoning"),
        expected_signals=("planning_failure", "dependency_reasoning", "prediction_pressure"),
        domains=("disaster recovery", "software migration", "construction phases", "hospital surge response", "warehouse redesign"),
        stressors=("a subtask blocks a parent goal", "a local plan conflicts with the global plan", "priority shifts midstream", "milestones hide dependencies", "a lower-level failure propagates"),
        evidence_sources=("work breakdown structures", "milestone data", "dependency maps", "status reports", "risk registers"),
        decisions=("decompose the goal", "revise the hierarchy", "predict propagation", "choose a critical subtask", "preserve unresolved assumptions"),
        prompt_frame=(
            "Build a hierarchical plan for {domain}. The plan is stressed because {stressor}. "
            "Use {evidence} to {decision}. Show goal, subgoals, dependency risk, and the "
            "prediction that would reveal the hierarchy is wrong."
        ),
    ),
    "information_synthesis": ProfileSpec(
        capability="information_synthesis",
        task_type="research",
        required_capabilities=("synthesis", "evidence", "uncertainty"),
        expected_signals=("information_gain", "contradiction_resolution", "generalization"),
        domains=("policy memos", "technical reports", "medical summaries", "incident reviews", "market analyses"),
        stressors=("sources disagree", "one source is outdated", "evidence levels differ", "a key fact is missing", "summary hides uncertainty"),
        evidence_sources=("source provenance", "method notes", "recency data", "confidence statements", "primary records"),
        decisions=("synthesize without flattening disagreement", "rank evidence", "preserve uncertainty", "identify a missing fact", "predict which claim may fail"),
        prompt_frame=(
            "Synthesize information for {domain}. The issue is that {stressor}. Use "
            "{evidence} to {decision}. Produce a reusable synthesis, unresolved question, "
            "and a prediction that tests the weakest claim."
        ),
    ),
    "hypothesis_revision": ProfileSpec(
        capability="hypothesis_revision",
        task_type="research",
        required_capabilities=("hypothesis_revision", "evidence", "prediction"),
        expected_signals=("belief_revision", "falsification", "information_gain"),
        domains=("system outages", "health trends", "economic behavior", "equipment wear", "education outcomes"),
        stressors=("new evidence contradicts the leading hypothesis", "a confounder emerges", "the effect reverses in a subgroup", "the original metric was flawed", "replication weakens support"),
        evidence_sources=("new observations", "subgroup analyses", "metric audits", "replication results", "control comparisons"),
        decisions=("revise the hypothesis", "lower confidence", "form a replacement explanation", "predict a follow-up result", "identify decisive evidence"),
        prompt_frame=(
            "Revise a hypothesis about {domain}. The update is required because {stressor}. "
            "Use {evidence} to {decision}. State old hypothesis, new hypothesis, confidence "
            "change, and a prediction that would separate them."
        ),
    ),
}


def broad_profile_names() -> tuple[str, ...]:
    return tuple(BROAD_PROFILE_SPECS)


def generate_broad_corpus(*, minimum_per_profile: int = 100) -> tuple[CalibrationObjective, ...]:
    objectives: list[CalibrationObjective] = []
    for profile, spec in BROAD_PROFILE_SPECS.items():
        objectives.extend(
            _generate_profile_objectives(
                profile=profile,
                spec=spec,
                minimum=max(1, int(minimum_per_profile)),
            )
        )
    return tuple(objectives)


def _generate_profile_objectives(
    *,
    profile: str,
    spec: ProfileSpec,
    minimum: int,
) -> list[CalibrationObjective]:
    objectives: list[CalibrationObjective] = []
    seen: set[tuple[str, str, str, str]] = set()
    for domain in spec.domains:
        for stressor in spec.stressors:
            for evidence in spec.evidence_sources:
                for decision in spec.decisions:
                    key = (domain, stressor, evidence, decision)
                    if key in seen:
                        continue
                    seen.add(key)
                    slug = _slug("-".join(key))
                    objectives.append(
                        CalibrationObjective(
                            objective_id=f"{profile}-{slug}",
                            capability=spec.capability,
                            task_type=spec.task_type,
                            prompt=spec.prompt_frame.format(
                                domain=domain,
                                stressor=stressor,
                                evidence=evidence,
                                decision=decision,
                            ),
                            required_capabilities=spec.required_capabilities,
                            expected_signals=spec.expected_signals,
                            metadata={"profiles": (profile,), "broad_corpus": True},
                        )
                    )
                    if len(objectives) >= minimum:
                        return objectives
    return objectives


def _slug(text: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:110]

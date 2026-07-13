# GSR-A Governed Self-Regulation Foundation Model

GSR-A is the inert state-contract foundation for the DELTA Governed Self-Regulating Cognition phase. It does not activate live self-repair, mutate source, run providers, create schedulers, write memory, train models, or load modules into the live runtime.

## Relationship To Existing Stages

GSR-A extends, but does not replace, existing governance structures:

- DELTA 1.0 `DevelopmentObjective` already models proposal-only development objectives and operator approval gates.
- RC3 `GoalFrame`, `PlanFrame`, and lifecycle checks already model read-only planning and fail-closed transitions.
- RC4 `AuthorizationScope`, `PermissionGrant`, sandbox, rollback, patch, and execution records already model governed action boundaries.
- RC5 outcome evidence, deficit hypotheses, consultation packets, and upgrade proposals already model developmental cognition and manual transport.
- RC7 shadow campaigns already model deficits, hypotheses, proposals, validation, comparison, and operator disposition without execution.

GSR-A provides the missing cross-stage bridge: observation -> diagnosis candidate -> repair proposal -> sandbox evaluation plan -> governance decision -> optional later application authority. Each boundary is explicit and deny-by-default.

## Architectural Gap

Before GSR-A, DELTA could represent goals, evidence, proposals, and sandbox contracts, but it did not have one inert chain proving that:

- observation is not judgment;
- diagnosis is not proposal;
- proposal is not authorization;
- authorization is not execution;
- execution is not persistence;
- evaluation is not self-approval.

GSR-A therefore introduces serializable objects that hold state and decisions without performing work.

## Contracts

### DevelopmentObjective

Required concepts:

- `objective_id`
- `operator_supplied_goal`
- `scope`
- `success_criteria`
- `forbidden_actions`
- `evidence_requirements`
- `lifecycle_state`
- `operator_authorization_state`
- `creation_source`
- `sequence`
- `created_at`
- `parent_objective_id`

Objectives cannot self-authorize. They can become active only through an operator-controlled governance decision.

### SelfObservation

Required concepts:

- `observation_id`
- `objective_id`
- `source_subsystem`
- `observed_behavior`
- `expected_behavior`
- `evidence_references`
- `confidence`
- `uncertainty`
- `severity`
- `reproducibility`
- `user_visible`
- `telemetry_only`

Observations are evidence records only. They do not automatically become defects or diagnoses.

### DiagnosisCandidate

Required concepts:

- `diagnosis_id`
- `linked_observations`
- `first_incorrect_transition`
- `suspected_mechanism`
- `competing_hypotheses`
- `supporting_evidence`
- `disconfirming_evidence`
- `confidence`
- `scope_estimate`
- `deeper_design_required`

Diagnosis candidates remain provisional. A deeper-design flag blocks automatic repair continuation.

### RepairProposal

Required concepts:

- `proposal_id`
- `diagnosis_id`
- `proposed_change`
- `files_or_components_in_scope`
- `forbidden_files_or_components`
- `predicted_effects`
- `risks`
- `rollback_strategy`
- `validation_plan`
- `operator_approval_requirement`
- `proposal_only_status`

Repair proposals cannot mutate source or apply themselves.

### SandboxEvaluationPlan

Required concepts:

- `plan_id`
- `proposal_id`
- `disposable_workspace`
- `test_selection`
- `live_runtime_evidence_requirements`
- `provider_model_restrictions`
- `memory_write_restrictions`
- `success_criteria`
- `failure_criteria`
- `rollback_proof`
- `artifact_retention_policy`

Sandbox evaluation cannot begin without an explicit governance decision. Sandbox approval does not imply production/application approval.

### GovernanceDecision

Required concepts:

- `decision_id`
- `proposal_id`
- `operator_authority`
- `decision`
- `allowed_scope`
- `one_shot`
- `expires_after_sequence`
- `attached_conditions`
- `audit_rationale`

No DELTA-generated object counts as operator authorization. Operator authority must be operator-controlled.

### RegulationCycleState

Lifecycle states:

- `idle`
- `objective_pending`
- `observing`
- `observation_review`
- `diagnosing`
- `diagnosis_review`
- `proposal_drafting`
- `proposal_review`
- `sandbox_authorized`
- `sandbox_evaluating`
- `evaluation_review`
- `application_authorized`
- `applying`
- `post_change_observation`
- `completed`
- `rejected`
- `suspended`
- `rolled_back`
- `deeper_design_required`

All transitions are explicit. Invalid, expired, rejected, suspended, rolled-back, and deeper-design states deny execution.

## Deny-By-Default Rules

- A development objective cannot become active without operator authorization.
- A self-observation cannot mutate runtime or memory.
- A self-observation does not become a diagnosis automatically.
- A diagnosis candidate cannot authorize a repair proposal.
- A repair proposal cannot apply itself.
- Sandbox evaluation requires an explicit governance decision scoped to sandbox evaluation.
- Application requires a separate explicit governance decision scoped to application.
- Operator decisions are one-shot or explicitly scoped.
- Rejected, suspended, expired, rolled-back, and deeper-design states deny execution.
- Serialization must preserve governance state.

## GSR-A Boundary

GSR-A is architecture, contracts, inert objects, and deterministic validation only. GSR-B may later attach proposal review or sandbox adapters, but only after separate operator authorization.

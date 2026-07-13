# GSR-D Governed Sandbox Planning And Module Attachment Foundation

## Purpose

GSR-D provides an inert foundation for governed sandbox planning and
module-attachment planning. It stops before sandbox execution.

The implemented chain is:

`future_sandbox_planning_eligible proposal -> operator sandbox-planning authorization -> PLAN_ONLY sandbox plan -> optional ATTACHMENT_PLAN_ONLY module-attachment plan -> operator sandbox-plan review -> future_sandbox_execution_eligible metadata`

Future sandbox-execution eligibility is not sandbox authorization. A sandbox plan is not a sandbox instance. A module-attachment plan is not module loading. Permission requests are not grants.

## Relationship To GSR-A, GSR-B, And GSR-C

GSR-D extends the existing GSR runtime file:

`orchestration/runtime/gsr_a_governed_self_regulation.py`

It reuses the GSR-A inert governance spine, GSR-B observation/ledger discipline,
and GSR-C proposal-only future sandbox-planning eligibility marker. It does not
import RC4 execution helpers and does not wire into `DELTA.py`, the live router,
or the continuous runtime.

## Gate D1-A - Planning Authorization

Implemented contracts:

- `SandboxPlanningAuthorization`
- `SandboxPlanningState`
- `SandboxPlanCreationResult`

Implemented public functions:

- `make_sandbox_planning_state`
- `make_sandbox_planning_authorization`
- `authorize_sandbox_plan_creation`

D1-A verifies that a GSR-C proposal is listed in
`future_sandbox_planning_eligible_proposals` and that an explicit
operator-controlled sandbox-planning authorization exists. Eligibility alone is
insufficient. Non-operator, wrong-target, expired, consumed, reused, or
non-one-shot authorizations fail closed.

D1-A records consumed planning authorization ids but creates no plan, sandbox,
workspace, command, patch, module load, permission grant, application authority,
or persistence.

## Gate D1-B - Inert Sandbox And Module-Attachment Plans

Implemented contracts:

- extended `SandboxEvaluationPlan`
- `ModuleAttachmentPlan`

Implemented public function:

- `create_inert_sandbox_plan`

D1-B creates at most one `PLAN_ONLY` sandbox plan from a consumed D1-A planning
authorization. It may also create at most one subordinate `ATTACHMENT_PLAN_ONLY`
module-attachment plan. The plan stores the exact proposal id and planning
authorization id.

The extended sandbox plan records descriptive metadata only:

- disposable workspace description;
- repository snapshot description;
- allowed and forbidden file/component scope;
- allowed and forbidden tool classes;
- allowed and forbidden command categories;
- test selections and evidence requirements;
- provider/model, network, memory-write, and source-mutation restrictions;
- rollback-proof and cleanup-proof requirements;
- artifact-retention policy;
- execution-budget metadata;
- optional module-attachment plan id.

The module-attachment plan records requested interfaces, permissions, data,
network, memory, and tool boundaries, lifecycle-hook descriptions, activation
and deactivation conditions, rollback/removal description, compatibility
requirements, and validation requirements. It grants no permission, loads no
module, mutates no registry, and registers no hook.

Deterministic content checks reject executable payload markers such as patches,
diffs, shell commands, PowerShell, Python execution commands, Git commands,
tool-call payloads, direct file-edit instructions, module import/load commands,
registry mutation commands, and deployment commands.

## Gate D1-C - Plan Review And Future Execution Eligibility

Implemented contracts:

- `SandboxPlanReviewDecision`
- `SandboxPlanReviewResult`

Implemented public functions:

- `make_sandbox_plan_review_decision`
- `review_sandbox_plan`
- `sandbox_plan_can_review_itself`
- `sandbox_plan_is_future_execution_eligible`
- `sandbox_plan_disposition_blocks_execution`

Supported dispositions:

- `approve_for_future_sandbox_execution`
- `reject`
- `revise`
- `defer`
- `deeper_design_required`
- `suspend`
- `expire`

Plan review is operator-controlled and one-shot. Failed decisions remain
unconsumed. Successful decisions are recorded in
`consumed_plan_review_decision_ids`. Reviewed plans leave
`pending_plan_review_queue`.

Blocking dispositions update their corresponding denial indexes and do not
create execution eligibility. The only positive endpoint is the metadata marker
`future_sandbox_execution_eligible_plans`.

## State And Serialization

`SandboxPlanningState` stores:

- planning authorization ids;
- consumed planning authorization ids;
- sandbox plans;
- module-attachment plans;
- plan review decisions;
- consumed plan-review decision ids;
- pending plan-review queue;
- plan ids by proposal;
- attachment-plan ids by sandbox plan;
- future sandbox-execution eligibility ids;
- denial indexes for rejected, revision-required, deferred, suspended, expired,
  and deeper-design plans.

The state is serializable through the shared deterministic dataclass
serialization helpers. Serialization preserves metadata and denial state but
does not activate execution authority.

## Boundaries

GSR-D does not provide:

- sandbox authorization;
- sandbox creation or startup;
- workspace creation;
- repository cloning;
- command execution;
- tool invocation;
- patch generation;
- source mutation;
- module loading;
- module registry mutation;
- permission grants;
- application authorization or application;
- persistence;
- provider or model calls;
- network access;
- memory writes;
- scheduling, threads, workers, monitors, or background loops;
- live-router integration;
- `DELTA.py` integration;
- continuous-runtime integration;
- GSR-E execution.

## RC3 And RC4 Relationship

RC3 and RC4 remain semantic precedent only. RC3 demonstrates planning and plugin
deferral without activation. RC4 demonstrates authorization, sandbox, rollback,
tool, and execution boundaries. GSR-D does not import RC4 execution-capable
helpers such as command runners, patch builders, disposable-workspace executors,
tool invocation helpers, application helpers, or report writers.

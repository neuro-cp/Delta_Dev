# DELTA RC4 State Model

RC4 is the governed action runtime. It extends RC3 planning and proposal objects into narrowly authorized, observable, disposable action.

The invariant is:

```text
Goal -> Plan -> Engineering Proposal -> Governance Review -> Explicit Authorization
-> Controlled Execution -> Evidence -> Verification -> Operator Review -> Controlled Integration
```

RC4 must never become:

```text
Goal -> Self-Authorization -> Unrestricted Action -> Hidden Mutation
```

## Authority Classes

- `request_only`: describes a desired action but grants no authority.
- `scope_only`: describes boundaries such as paths, tools, commands, time, resources, and evidence.
- `bounded_operator_authority`: explicit, expiring, revocable authority from an operator role.
- `gate_decision`: deterministic authorization outcome.
- `artifact_only`: candidate patch or report artifact; not applied to the live repository.
- `controlled_fixture_execution`: temporary-workspace execution only.
- `fixture_result`: evidence from disposable fixture work.
- `review_only`: integration candidate or freeze review; no push, merge, or deploy authority.
- `disabled_by_default`: live mutation, push, merge, deployment, provider calls, and plugin activation.

## Core Objects

- `ExecutionRequest`: requested action, target repository, branch, paths, commands, tools, and requester.
- `AuthorizationScope`: exact path, command, tool, network, provider, persistence, duration, resource, rollback, and evidence limits.
- `PermissionGrant`: operator-issued bounded permission with expiration and optional revocation.
- `ExecutionAuthorization`: request plus grant envelope.
- `AuthorizationDecision`: `AUTHORIZED`, `DENIED`, `EXPIRED`, `REVOKED`, `OUT_OF_SCOPE`, `PROHIBITED_TARGET`, `PROHIBITED_TOOL`, or related blocker.
- `RepositorySnapshot`, `RepositoryInventory`, `CodebaseMap`, `SymbolGraph`, `DependencyGraph`: read-only repository intelligence.
- `ImpactAssessment`, `ImplementationDesign`, `ValidationPlan`: design outputs that do not mutate files.
- `CandidatePatch`, `PatchRevision`, `PatchValidation`, `PatchRiskAssessment`, `PatchArtifact`: reviewable patch artifacts.
- `SandboxExecutionPlan`, `SandboxExecutionSession`, `CommandAuthorization`, `CommandResult`, `ExecutionTranscript`, `ExecutionEvidence`, `ExecutionResult`: controlled temporary-workspace execution evidence.
- `RepairAuthorization`, `RepairIteration`, `RepairProposal`, `RepairEvidence`, `RepairResult`: bounded repair loop state.
- `RepositoryApplicationRequest`, `RepositoryApplicationResult`, `RollbackTicket`, `RollbackPlan`, `RollbackResult`, `PartialMutationRecord`: fixture/live-application boundary and recovery objects.
- `IntegrationCandidate`, `CommitAuthorization`, `PushAuthorization`, `MergeAuthorization`, `DeploymentAuthorization`: separated integration authorities.
- `ToolContract`, `ToolPermission`, `ToolInvocationRequest`, `ToolInvocationResult`, `ToolAuditEvent`: governed tool orchestration.
- `RecoveryPlan`, `RecoveryResult`, `EnvironmentRestorationRecord`: partial-failure handling.
- `RC4Episode`: linked action lifecycle evidence.
- `RC4FreezeManifest`: final freeze-readiness evidence and blockers.

## Persistence

RC4 objects are ephemeral or report-only by default. Temporary execution workspaces are disposable. Live repository mutation remains disabled unless a future operator authorization exactly names the target, branch, base, patch hash, rollback plan, validation commands, and review disposition.

## Rollback

Every mutable action must have one of:

- validated rollback,
- disposable environment,
- explicit irreversible-action declaration requiring elevated approval.

The current RC4 implementation proves rollback in disposable Git fixtures and temporary workspaces only.

## Operator Visibility

RC4 state is surfaced through reports, tests, and the RC4 operator UI tab. Normal conversation remains uncluttered. The UI provides inspection panels, not execution controls.

## Freeze Honesty

Fixture and developer-rehearsal evidence must not be reported as real operator-pilot evidence. Without real operator evidence, the strongest valid freeze state is:

```text
RC4_FREEZE_PENDING_REAL_OPERATOR_PILOT
```

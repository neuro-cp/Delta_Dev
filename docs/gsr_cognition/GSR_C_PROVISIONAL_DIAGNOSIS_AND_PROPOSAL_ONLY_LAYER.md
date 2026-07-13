# GSR-C Provisional Diagnosis and Proposal-Only Layer

## Purpose

GSR-C provides an inert governance layer for:

- operator-authorized provisional diagnosis creation;
- competing-hypothesis and evidence-role review;
- operator-controlled diagnosis disposition;
- descriptive proposal-only repair artifacts;
- operator proposal review;
- future sandbox-planning eligibility metadata only.

Diagnosis is provisional, not truth. Confidence is not authority. Severity is
not authority. Diagnosis acceptance is not repair authorization. A proposal is
not a patch. Proposal is not patch authority. Proposal approval is not sandbox
authorization. Future-planning eligibility is not sandbox permission.

## Relationship To GSR-A And GSR-B

GSR-C reuses the GSR-A governance spine in
`orchestration/runtime/gsr_a_governed_self_regulation.py` so the phase extends
the same serializable, inert state model instead of creating a parallel runtime
system.

GSR-C reuses GSR-B ledger eligibility and evidence provenance. A provisional
diagnosis can be created only from a ledger entry that has already reached
`diagnosis_review_eligible`, remains present in the diagnosis review queue, and
has traceable evidence in the ledger evidence index.

RC4 execution-capable contracts remain separate. GSR-C does not import RC4
execution helpers, does not authorize sandboxes, and does not apply source
changes. RC5 and RC7 remain semantic precedent for proposal and hypothesis
review, not imported mutable state.

## Gate A - Diagnosis Authorization

Implemented contracts:

- `DiagnosisReviewAuthorization`
- `DiagnosisEvidenceReference`
- `DiagnosisProposalState`
- `DiagnosisCreationResult`

Implemented public functions:

- `make_diagnosis_proposal_state`
- `make_diagnosis_review_authorization`
- `make_diagnosis_evidence_reference`
- `create_provisional_diagnosis_candidate`
- `diagnosis_candidate_creates_proposal`
- `diagnosis_authorization_is_consumed`

The exact eligible-ledger source requirement is:

- the ledger entry must exist;
- the ledger entry lifecycle state must be `diagnosis_review_eligible`;
- the ledger entry id must be in `ObservationLedgerState.diagnosis_review_queue`;
- the authorization target must match that ledger entry;
- the linked objective must match when supplied;
- the authorization must provide a non-empty allowed diagnosis scope;
- referenced evidence must exist in the ledger evidence index.

Operator authority must be `OPERATOR_CONTROLLED_AUTHORITY`. Expired,
consumed, non-one-shot, non-operator, wrong-target, and missing-evidence
attempts fail closed and do not consume authorization ids. Successful
authorizations are one-shot and are recorded in
`consumed_diagnosis_authorization_ids`.

Candidate creation is provisional. It adds a diagnosis candidate and pending
diagnosis review queue entry. It creates no proposal.

## Gate B - Diagnosis Review

Implemented contracts:

- `CompetingDiagnosisHypothesis`
- `DiagnosisReviewDecision`

Implemented public functions:

- `make_competing_diagnosis_hypothesis`
- `add_competing_diagnosis_hypothesis`
- `attach_evidence_to_hypothesis`
- `hypothesis_selects_itself`
- `diagnosis_has_automatic_hypothesis_winner`
- `make_diagnosis_review_decision`
- `review_diagnosis_candidate`
- `diagnosis_candidate_can_review_itself`
- `diagnosis_is_eligible_for_proposal_drafting`
- `diagnosis_disposition_blocks_proposal_drafting`

Diagnosis dispositions are:

- `pending_review`
- `accepted_for_proposal_drafting`
- `rejected`
- `revise`
- `insufficient_evidence`
- `competing_hypothesis_unresolved`
- `non_defect`
- `duplicate_diagnosis`
- `suspended`
- `expired`
- `deeper_design_required`

Evidence roles are:

- `supporting`
- `disconfirming`
- `neutral`
- `unresolved`

Evidence roles remain separate. Multiple hypotheses can coexist. There is no
automatic hypothesis winner. Confidence, severity, and reproducibility do not
select a winner. Operator review may select a provisional hypothesis, mark a
diagnosis accepted for proposal drafting, or place it in a blocked disposition
such as unresolved, insufficient evidence, non-defect, duplicate, suspended,
expired, or deeper-design required.

Accepted diagnosis review creates only proposal-drafting eligibility. It does
not automatically create a proposal.

## Gate C - Proposal-Only Repair Layer

Implemented contracts:

- extended GSR-A `RepairProposal`
- `ProposalCreationResult`
- `ProposalReviewDecision`
- `ProposalReviewResult`

Implemented public functions:

- `create_proposal_only_repair_proposal`
- `proposal_contains_patch_or_executable_content`
- `proposal_mutates_source`
- `proposal_starts_sandbox`
- `proposal_authorizes_application`
- `make_proposal_review_decision`
- `review_repair_proposal`
- `proposal_can_review_itself`

Proposal review dispositions are:

- `approve_for_future_sandbox_planning`
- `reject`
- `revise`
- `defer`
- `deeper_design_required`
- `suspend`
- `expire`

Proposal artifacts are descriptive only. Scope fields describe files or
components; they do not grant authority. Rollback descriptions describe a
rollback idea; they do not execute rollback. Validation plans describe evidence
requirements; they do not run tests or a live runtime.

Deterministic executable-content denial rejects patch, diff, command, tool-call,
direct file-edit, and application-instruction content before a proposal can be
created.

Proposal review is operator-controlled and one-shot. Blocked dispositions record
denial state. The only positive endpoint is a metadata marker for future sandbox
planning eligibility.

## Diagnosis Lifecycle

Implemented diagnosis lifecycle states and indexes:

- `pending_review`: created after valid diagnosis authorization;
- `accepted_for_proposal_drafting`: entered by valid operator review and
  recorded in `proposal_drafting_eligible_diagnoses`;
- `rejected`: recorded in `rejected_diagnoses`;
- `competing_hypothesis_unresolved`: recorded in `unresolved_diagnoses`;
- `insufficient_evidence`: recorded in `insufficient_evidence_diagnoses`;
- `non_defect`: recorded in `non_defect_diagnoses`;
- `duplicate_diagnosis`: recorded in `duplicate_diagnoses`;
- `suspended`: recorded in `suspended_diagnoses`;
- `expired`: recorded in `expired_diagnoses`;
- `deeper_design_required`: recorded in `deeper_design_diagnoses`;
- `revise`: reviewed status only, without proposal-drafting eligibility.

Unknown dispositions, expired decisions, consumed decisions, non-operator
decisions, foreign hypotheses, wrong targets, and self-review attempts fail
closed.

## Proposal Lifecycle

Implemented proposal lifecycle states and indexes:

- `pending_review`: created after a diagnosis is accepted for proposal drafting
  and required descriptive metadata passes validation;
- `approve_for_future_sandbox_planning`: records only
  `future_sandbox_planning_eligible_proposals`;
- `reject`: recorded in `rejected_proposals`;
- `revise`: recorded in `revision_required_proposals`;
- `defer`: recorded in `deferred_proposals`;
- `suspend`: recorded in `suspended_proposals`;
- `expire`: recorded in `expired_proposals`;
- `deeper_design_required`: recorded in `deeper_design_proposals`.

Unknown dispositions, expired decisions, consumed decisions, non-operator
decisions, wrong targets, non-proposal-only proposals, and self-review attempts
fail closed.

## Authorization And Decision Consumption

GSR-C tracks:

- diagnosis authorization IDs in `diagnosis_review_authorization_ids`;
- consumed diagnosis authorization IDs in `consumed_diagnosis_authorization_ids`;
- diagnosis review decision IDs in `diagnosis_review_decisions`;
- consumed diagnosis decision IDs in `consumed_diagnosis_decision_ids`;
- proposal review decision IDs in `proposal_review_decisions`;
- consumed proposal decision IDs in `consumed_proposal_decision_ids`.

Successful one-shot operations consume their IDs. Failed attempts remain
unconsumed. Serialization preserves consumed IDs and denial indexes. No object
can self-authorize, self-review, or convert confidence or severity into
authority.

## Evidence And Hypotheses

Diagnosis evidence is linked through `DiagnosisEvidenceReference`, which records
ledger entry id, observation id, evidence id, source subsystem, role,
classification, fingerprint, provenance flags, integrity status, and sequence.

Hypotheses are explicit `CompetingDiagnosisHypothesis` records linked to one
diagnosis. Supporting, disconfirming, neutral, and unresolved evidence remain in
separate fields. GSR-C performs no provider ranking, local-model ranking, or
model-as-judge selection.

## Proposal Content Restrictions

Proposal creation denies deterministic markers for:

- patches;
- diffs;
- executable code blocks;
- shell commands;
- tool calls;
- direct file-edit instructions;
- application instructions.

Scope metadata remains descriptive only. It does not authorize edits,
execution, application, or repository operations.

## Future Sandbox-Planning Boundary

The only allowed positive endpoint is:

`approved proposal -> future_sandbox_planning_eligible`

This creates:

- no sandbox authorization;
- no sandbox plan;
- no sandbox execution;
- no patch;
- no source mutation;
- no application authorization;
- no persistence.

## Non-Capabilities

GSR-C does not provide:

- autonomous diagnosis;
- automatic proposal creation;
- sandbox planning or authorization;
- patch generation;
- source editing;
- tool execution;
- application;
- persistence;
- provider/model inference;
- memory writes;
- scheduling;
- background monitoring;
- live-router integration;
- `DELTA.py` integration;
- continuous-runtime integration.

# DELTA Phase 20 Manual Work Note

Date: 2026-08-07
Branch: codex/delta-cognitive-core
Last stable pushed state: 3316d6ab Add self-directed internal work candidates

## Status

Codex usage/data became unavailable after Block C was pushed.

Current work is being reviewed manually with ChatGPT until Codex data is restored.

This manual period is NOT an implementation authority expansion and should NOT be treated as a completed Phase 20 checkpoint.

## Current intended target

Phase 20 — EVIDENCE_SEEKING_PERMISSION_REQUESTS_1

Goal:
analysis/refinement has unresolved evidence need
-> create evidence_request under active_objective.provenance
-> surface one permission request through existing ChatAddressableRequest
-> bind grant / deny / defer / operator-provided context
-> do not gather evidence
-> do not execute model/provider/tool/network/file/sandbox/graph/review/admission work

## Known local state at manual handoff

Stable pushed HEAD:
3316d6ab Add self-directed internal work candidates

Known meaningful local source diff:
- orchestration/runtime/evidence_bound_analysis.py

Known temporary/manual artifacts:
- dump.py

Known dirty report noise:
- reports/RC2_CONVERSATIONAL_ARCHITECTURE.json
- reports/RC2_CONVERSATIONAL_MODE_ROUTER.json
- reports/RC2_DEVELOPMENTAL_CONCEPT_FORMATION.json

Protected file:
- orchestration/runtime/live_competence_adapter.py must remain unchanged
- expected SHA256:
  9561C03553785A133F78931565CE68AC3D250E24003F9AC640408B82F21BFC5D

## Manual review finding

The current evidence_bound_analysis.py diff appears to add an inert helper layer:

- EVIDENCE_PERMISSION_SCHEMA_VERSION
- EvidencePermissionRequest
- compile_evidence_permission_requests(...)

This is only partial Phase 20.

It is not push-ready as a completed phase because runtime integration has not been proven:
- no durable provenance write path confirmed
- no ChatAddressableRequest surface confirmed
- no grant / deny / defer / provided-context binding confirmed
- no restart exact-once suppression confirmed
- no focused tests confirmed

## Rule until Codex returns

Do not manually wire runtime source unless explicitly authorized.

Preferred mode:
- preserve current local diff
- review only
- write patch/test plans
- do not stage/commit/push implementation
- let Codex inspect the current diff and state the first missing transition before editing

## Codex resume instruction

When Codex returns:

1. Inspect current status and diff.
2. Do not reset, stash, clean, or discard local changes.
3. Ignore known RC2 report refresh noise unless it changes scope.
4. Treat dump.py as a temporary manual artifact; do not stage unless explicitly told.
5. Evaluate whether the EvidencePermissionRequest helper is valid.
6. State the first missing transition before edits.
7. Finish Phase 20 only.
8. Add focused tests for finance, defensive cyber, and operations evidence-permission cases.
9. Prove no evidence gathering, no provider/model/tool/network/file/sandbox execution, no graph mutation, and restart exact-once behavior.
10. Stop for operator/GPT review before Phase 21.

Disposition:
PHASE_20_MANUAL_REVIEW_IN_PROGRESS_NOT_VALIDATED

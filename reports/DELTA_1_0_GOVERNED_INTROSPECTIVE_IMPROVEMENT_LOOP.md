# DELTA 1.0 Governed Introspective Improvement Loop

Date: 2026-07-11
Status: PROPOSAL_ONLY_AWAITING_OPERATOR_APPROVAL
Milestone: DELTA_1_0_GOVERNED_INTROSPECTIVE_IMPROVEMENT_LOOP

No implementation, commit, push, provider call, external retrieval, canonical write, memory write, model change, authority expansion, or autonomous runtime action was performed.

## Loop Contract

This milestone is a governed improvement cycle, not autonomy and not uncontrolled self-modification.

Allowed:

- observe operator work and local reports
- detect recurring weaknesses
- identify capability gaps
- rank improvement opportunities
- propose development objectives
- prepare bounded code-change proposals
- generate focused behavioral tests
- evaluate before/after evidence after approval
- propose a noncanonical lesson for operator disposition

Not allowed:

- approve its own objective
- implement without authorization
- change governance or expand authority
- write canonical memory automatically
- call providers or retrieve externally without a gate
- commit or push from runtime
- retain lessons without operator approval

## Evidence Reviewed

Local evidence only:

- `reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md`
- `reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md`
- `reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md`
- `orchestration/runtime/delta_1_0_objective_engine.py`
- `orchestration/runtime/delta_1_0_learning_loop.py`
- `orchestration/runtime/v31_learning_opportunity.py`
- `orchestration/runtime/v31_learning_proposal.py`
- `orchestration/runtime/v31_safety_checkpoint.py`
- current routing code in `rc2_conversational_mode_router`, `rc2_contradiction_engine`, `rc2_render_correction`, `rc2_dialogue_intent_classifier`, `rc2_cognitive_episode`, and `rc45_discourse_cognition_bridge`

## Observed Recurring Deficit

Stages A, A2, and B repeatedly exposed boundary errors between conversational acts:

- casual acknowledgement or opinion routed into technical/coding paths
- ordinary answers proposed memory candidates without explicit memory intent
- render corrections such as summarizing the previous answer missed the previous-answer scope
- natural topic drift with `but now` was misclassified as contradiction
- vague ellipsis/follow-up prompts either fabricated an answer or fell into local-model consent
- context declarations were treated as orphan follow-ups
- genuine ambiguity selected one referent silently
- explicit topic reset dropped old context but initially fell into local-model consent despite sufficient local DELTA knowledge

The recurring root cause is not one missing phrase. It is weak discourse-act boundary arbitration: DELTA has separate detectors for correction, topic shift, render correction, contradiction, memory request, and follow-up, but it lacks a small shared decision surface that makes these mutually exclusive enough before high-impact routes run.

## Proposed Development Objective

Objective ID: `DELTA10-GIIL-OBJ-001`

Title:

Improve DELTA's ability to distinguish conversational corrections, topic shifts, and genuine contradictions without adding narrow phrase-specific handlers.

Objective type:

`CAPABILITY_IMPROVEMENT`

Origin:

`PILOT_EVIDENCE`

Affected capability:

`RC2_CONVERSATIONAL_DISCOURSE_ARBITRATION`

Evidence refs:

- `PID-001` casual routing leakage
- `PID-003` summarize-previous render-correction miss
- `PID-005` topic drift misclassified as contradiction
- `PID-006` ellipsis/follow-up answer-quality failure
- `PID-B01` normal follow-up resolution
- `PID-B02` delayed topic return
- `PID-B03` significance under-answering
- `PID-B04` ambiguous referent guessing
- `PID-B05` explicit topic-reset fallback

## Priority Ranking

| Rank | Candidate objective | Value | Effort | Risk | Rationale |
| --- | --- | --- | --- | --- | --- |
| 1 | Shared discourse-boundary arbitration for correction, topic shift, and contradiction | High | Medium | Medium | Directly addresses the repeated cross-stage failure pattern and reduces future phrase-by-phrase patching. |
| 2 | Approved-concept reuse precedence cleanup | Medium | Medium | Medium | Already identified as an out-of-scope router regression candidate, but narrower than the cross-stage deficit. |
| 3 | Context-declaration acknowledgement polish | Low | Low | Low | Improves wording such as `this context as context`, but does not materially improve routing intelligence. |

Recommended objective: Rank 1.

## Success Criteria

The cycle succeeds only if focused evidence shows:

- conversational correction routes as correction/render-correction, not contradiction
- explicit topic shift routes as new topic, not contradiction
- genuine contradiction still routes to contradiction analysis
- ambiguous correction or referent asks a concise clarification instead of guessing
- render correction remains presentation-only
- memory candidates remain absent unless explicitly requested
- no provider calls, web/retrieval calls, canonical writes, training, autonomous actions, commits, or pushes occur
- B1/B2/B3/B4/B5 Stage B regressions remain green

## Stop Conditions

Stop before implementation or during repair if any condition appears:

- more than two runtime modules require substantive changes
- the fix requires a new architecture layer
- contradiction routing needs provider/model inference
- any governance flag changes from false to true
- memory/canonical write behavior changes
- existing Stage A/A2/B focused tests regress repeatedly
- the dirty tree prevents safe attribution
- operator rejects, revises, or narrows the objective

## Allowed Evidence Sources

Allowed:

- local reports listed above
- local runtime/test code
- focused pytest tests
- `py_compile`
- in-process `route_message` or `DeltaApp._send_chat` harnesses with local-model execution disabled
- git diff/status for attribution

Prohibited:

- provider calls
- web search or external retrieval
- local model inference
- training/fine-tuning
- canonical memory writes
- runtime commit/push/deploy
- broad full-suite test runs unless separately approved

## Relevant Files And Symbols

Primary candidates:

- `orchestration/runtime/rc2_conversational_mode_router.py`
  - `route_message`
  - `classify_intent`
  - early route ordering around render correction, contradiction, working memory, and local conversation
- `orchestration/runtime/rc45_discourse_cognition_bridge.py`
  - `DiscourseFrame`
  - `build_discourse_frame`
  - `topic_switch_status`
  - `current_requested_operation`
  - `candidate_routes`
  - `preempt_specialist_routing`
- `orchestration/runtime/rc2_contradiction_engine.py`
  - `is_contradiction_prompt`
  - `CONTRADICTION_TRIGGERS`
  - `_has_implicit_contradiction_cue`
- `orchestration/runtime/rc2_render_correction.py`
  - `build_render_correction_payload`
  - `is_render_correction_request`
- `orchestration/runtime/rc2_dialogue_intent_classifier.py`
  - `classify_dialogue_act`
  - `RULES`
- `orchestration/runtime/rc2_cognitive_episode.py`
  - `resolve_working_memory_followup`
  - `_explicit_topic_reset`
  - `_ambiguity_candidates`

Likely test files:

- `tests/runtime_rc2/test_rc2_contradiction_engine.py`
- `tests/runtime_rc2/test_rc2_render_correction.py`
- `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- a new or existing focused router-boundary test file if needed

## Bounded Implementation Proposal

Do not implement until operator approval.

Proposed bounded change:

1. Add a small deterministic discourse-boundary helper, preferably in `rc45_discourse_cognition_bridge.py` or as a local helper in `rc2_conversational_mode_router.py`.
2. The helper should return a frame with one of these coarse operations:
   - `render_correction`
   - `conversational_correction`
   - `explicit_topic_shift`
   - `genuine_contradiction_check`
   - `working_memory_followup`
   - `ordinary_question`
   - `ambiguous_reference`
3. Use the frame only to arbitrate between existing routes. It must not call providers, retrieve externally, write memory, or execute local models.
4. Replace narrow phrase stacking with semantic cue groups:
   - correction cues: prior answer revision, formatting correction, "not what I meant", "actually", "you missed"
   - topic-shift cues: "but now", "new topic", "switching subjects", "different topic", "move on"
   - contradiction cues: explicit contradiction/conflict/inconsistent/both-true language or two-claim structure with conflict markers
   - ambiguity cues: bare pronouns with multiple plausible branches and no disambiguating entity
5. Keep route ownership unchanged:
   - render corrections still use `rc2_render_correction`
   - contradictions still use `rc2_contradiction_engine`
   - follow-ups still use `rc2_cognitive_episode`
   - ordinary local self-knowledge still uses the existing local answer path

What not to do:

- do not redesign the router
- do not merge the contradiction engine into working memory
- do not add broad model fallback
- do not create a new memory layer
- do not add one-off handlers for every sentence in the reports

## Focused Behavioral Tests To Generate

Proposed tests before implementation:

1. `test_correction_of_previous_answer_does_not_route_to_contradiction`
   - History contains a prior answer.
   - Prompt: `Actually, not that part. I meant the previous constraint.`
   - Expected: correction/render-correction/session clarification, not contradiction; no memory candidate.

2. `test_topic_shift_with_but_now_does_not_route_to_contradiction`
   - Prompt: `That makes sense, but now explain the operator approval boundary.`
   - Expected: new/ordinary topic path, not contradiction.

3. `test_explicit_contradiction_still_routes_to_contradiction`
   - Prompt: `Can both be true: memory is reversible, and memory can never be rolled back?`
   - Expected: `contradiction_analysis`.

4. `test_render_correction_precedes_contradiction_when_scope_is_previous_answer`
   - History contains prior answer.
   - Prompt: `You contradicted the requested format; summarize the previous answer in two sentences.`
   - Expected: `render_correction`, presentation-only.

5. `test_ambiguous_correction_asks_clarification`
   - History contains two plausible recent topics.
   - Prompt: `Actually, not that one.`
   - Expected: asks which referent/topic, no silent selection.

6. `test_stage_b_regression_boundary_cases_remain_green`
   - Reuse B3/B4/B5 representative cases from `tests/runtime_rc2/test_rc2_working_memory_episode.py`.

Validation set after approval:

- newly added boundary tests
- directly affected existing tests only
- selected A/A2 regressions for PID-003 and PID-005
- selected Stage B regressions for PID-B03, PID-B04, PID-B05
- `py_compile` on changed runtime/test files
- one short live harness if router ordering changes

## Before/After Evaluation Plan

Before implementation:

- capture current routes for all proposed tests
- classify each failure as boundary ambiguity, stale expectation, or pre-existing unrelated behavior

After implementation:

- rerun only the focused tests above
- compare route, answer class, safety flags, memory candidate status, and pending action state
- report whether the objective improved behavior without reducing contradiction detection precision

## Expected Failure Analysis If First Attempt Fails

If corrections still route to contradiction:

- inspect contradiction trigger precedence and implicit two-claim detection
- avoid lowering contradiction precision by requiring clearer contradiction cues rather than deleting contradiction support

If topic shifts still route to contradiction:

- inspect topic-shift detection before contradiction analysis
- prefer explicit topic-shift frame over implicit contradiction cue

If genuine contradictions stop routing correctly:

- roll back the proposed arbitration change
- split correction/topic-shift gating from contradiction trigger logic

If ambiguity grows too broad:

- require two concrete recent branches and a pronoun/correction cue
- otherwise defer to existing follow-up behavior

## Lesson Candidate

Status: PROPOSED_ONLY

Candidate lesson:

When repeated route repairs cluster around correction, topic shift, follow-up, ambiguity, and contradiction, treat the root cause as discourse-boundary arbitration before adding new phrase handlers. Preserve existing route ownership, add focused counterexamples, and require operator approval before retaining the lesson.

Retention rule:

- May be retained only as `APPROVED_NONCANONICAL` after operator approval.
- Must not become canonical memory automatically.
- Must not authorize future implementation without review.

## Approval Request

Requested operator decision:

Approve, revise, or reject Objective `DELTA10-GIIL-OBJ-001`.

If approved, the next step is implementation of only the bounded discourse-boundary arbitration proposal above, followed by the focused tests and before/after evaluation. No commit or push is authorized by this report.

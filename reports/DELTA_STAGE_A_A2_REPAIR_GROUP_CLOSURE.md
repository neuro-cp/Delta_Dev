# DELTA Stage A/A2 Repair Group Closure

Date: 2026-07-11
Objective: STAGE_A_A2_REPAIR_GROUP_CLOSURE
Branch: codex/delta-cognitive-core
HEAD: 4d8f2607dc16531a18ab131e110cbcc0bf27056f

No commit, push, provider call, web call, canonical write, or autonomous runtime action was performed.

## Pathology IDs

| ID | Pathology | Status | Primary Regression |
| --- | --- | --- | --- |
| PID-001 | Casual routing leakage into technical/memory routes | Fixed | test_casual_dialogue_turns_do_not_fall_into_technical_routes |
| PID-002 | Automatic memory-candidate leakage from ordinary conversation | Fixed | test_ordinary_conversation_does_not_create_memory_candidate |
| PID-003 | Summarize-previous render-correction miss | Fixed | test_summarize_previous_answer_is_render_correction |
| PID-004 | Conversational opinion misrouting into coding capability response | Fixed | test_debugging_partner_opinion_gets_conversational_answer |
| PID-005 | Natural topic drift misclassified as contradiction | Fixed | test_natural_topic_drift_with_but_now_is_not_contradiction_route |
| PID-006 | Ellipsis/follow-up answer-quality failure | Fixed | test_second_one_asks_clarification_when_prior_answer_has_no_list; test_feedback_loop_why_followup_gives_substantive_explanation |

## Dirty Tree Attribution

| File | Attribution | Commit Proposal |
| --- | --- | --- |
| DELTA.py | Prior render-correction/live UI work; not part of A/A2 closure diff authored in this closure pass | Exclude unless separately accepting prior render-correction work |
| orchestration/runtime/rc2_render_correction.py | Mixed: prior untracked render-correction primitive plus PID-003 summarize support | Include only if the render-correction primitive is accepted as dependency; otherwise split before commit |
| tests/runtime_rc2/test_rc2_render_correction.py | Mixed: prior render-correction tests plus PID-003 regression | Include only with rc2_render_correction.py dependency or split before commit |
| orchestration/runtime/rc2_conversational_mode_router.py | Mixed: prior render-correction integration plus PID-001, PID-002, PID-004 routing repairs | Include selected A/A2 hunks; review render-correction hunks separately |
| orchestration/runtime/rc2_dialogue_intent_classifier.py | A/A2 behavioral repair for PID-001 | Include |
| orchestration/runtime/rc2_contradiction_engine.py | A/A2 behavioral repair for PID-005 | Include |
| orchestration/runtime/rc2_cognitive_episode.py | Mixed: prior explicit-task guard plus PID-006 follow-up repair | Include selected A/A2 hunks; review explicit-task guard with render-correction work |
| orchestration/runtime/rc2_natural_conversation_renderer.py | Prior natural-rendering work | Exclude from A/A2 commit unless separately justified |
| orchestration/runtime/rc45_discourse_cognition_bridge.py | Prior render-correction/discourse work | Exclude from A/A2 commit unless separately justified |
| tests/runtime_rc2/test_rc2_conversational_mode_router.py | Mixed: prior render-correction tests plus PID-001, PID-002, PID-004 regressions | Include selected A/A2 hunks; split prior render-correction tests if needed |
| tests/runtime_rc2/test_rc2_contradiction_engine.py | A/A2 behavioral repair for PID-005 | Include |
| tests/runtime_rc2/test_rc2_working_memory_episode.py | Mixed: prior explicit-task tests plus PID-006 regressions | Include selected A/A2 hunks; review explicit-task tests with render-correction work |
| tests/runtime_rc5/test_delta_report_inspection.py | Prior RC5/render-correction/report inspection work | Exclude from A/A2 commit |
| tests/runtime_rc5/test_rc45_discourse_cognition_bridge.py | Prior discourse/render-correction work | Exclude from A/A2 commit |
| reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md | A/A2 evidence record | Include if evidence docs are desired in commit |
| reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md | A/A2 closure record | Include if evidence docs are desired in commit |
| reports/RC2_*.json | Generated report churn | Exclude from A/A2 commit |

## Full Router Test Failure Triage

Command:

`.\.venv311\Scripts\python.exe -m pytest tests/runtime_rc2/test_rc2_conversational_mode_router.py -q`

Result: 49 passed, 8 failed.

| Test | Classification | Rationale |
| --- | --- | --- |
| test_successful_local_model_answer_offers_memory_candidate | STALE_EXPECTATION | PID-002 intentionally suppresses automatic memory candidates. If local-model answers should propose memory, that requires an explicit governed memory policy separate from ordinary conversation. |
| test_existing_approved_concept_is_not_requeued_for_review | REAL_REGRESSION_CANDIDATE_OUTSIDE_A_A2 | Direct local answers currently outrank approved concept reuse for sky. This is not part of A/A2 safety closure, but should be addressed before broader RC2 freeze. |
| test_approved_concept_is_reused_in_conversation | REAL_REGRESSION_CANDIDATE_OUTSIDE_A_A2 | Direct local fire answer outranks approved concept reuse for "Tell me about fire." Needs a separate concept-reuse precedence decision. |
| test_deepened_answer_enriches_existing_concept_without_prompt_keywords | PRE_EXISTING_FAILURE | Enrichment count reports 2 instead of 1 and is in developmental memory internals, not touched by A/A2 repairs. |
| test_vague_followup_does_not_retrieve_wrong_approved_concept | STALE_EXPECTATION | PID-006 routes vague follow-up through session memory without offering local model by default. Test expectation should be rewritten to the new no-unnecessary-model-offer behavior if accepted. |
| test_tell_me_something_you_know_browses_approved_concepts | STALE_EXPECTATION | Behavior is route-correct; expected wording "I know about" conflicts with natural renderer wording "I can talk about." |
| test_what_else_browses_another_concept_from_previous_domain | REAL_REGRESSION_CANDIDATE_OUTSIDE_A_A2 | Session-memory follow-up precedence may now outrank concept-browse follow-up. Needs Stage B/Browse-specific routing review. |
| test_short_domain_question_browses_law_concepts | STALE_EXPECTATION | Behavior is route-correct; expected wording "I know about" conflicts with natural renderer wording "I know several things about..." |

No unexplained real regression remains inside the A/A2 repair group. Two concept-reuse/browse precedence candidates remain outside this closure scope and should be scheduled before freeze or Stage L/M retrieval work.

## Closure Validation

Focused A/A2 suite:

`15 passed in 0.58s`

Included:
- PID-001 social/casual routing checks.
- PID-002 ordinary conversation no-memory-candidate checks.
- PID-003 render-correction summarize checks.
- PID-004 debugging-partner opinion routing.
- PID-005 topic-drift contradiction gate.
- PID-006 ellipsis/follow-up quality checks.

Syntax validation:

`py_compile` passed for changed runtime and test modules, including DELTA.py and rc2_render_correction.py.

Final live harness:

- Turns: 19
- Memory candidates: 0
- Provider calls: 0
- Retrieval/web calls: 0
- Canonical writes: 0
- Autonomous actions: 0
- Pending actions: 0
- Routes observed: social_conversation 10, local_conversation_model_lane 5, session_memory 2, render_correction 1, developmental_concept_memory 1.

## Commit Proposal

Do not execute without explicit operator authorization.

Proposed commit message:

`stabilize DELTA casual conversation and follow-up routing`

Intended A/A2 files:
- orchestration/runtime/rc2_dialogue_intent_classifier.py
- orchestration/runtime/rc2_contradiction_engine.py
- selected hunks in orchestration/runtime/rc2_conversational_mode_router.py
- selected hunks in orchestration/runtime/rc2_cognitive_episode.py
- tests/runtime_rc2/test_rc2_contradiction_engine.py
- selected hunks in tests/runtime_rc2/test_rc2_conversational_mode_router.py
- selected hunks in tests/runtime_rc2/test_rc2_working_memory_episode.py
- reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md
- reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md

Conditional dependency files:
- orchestration/runtime/rc2_render_correction.py
- tests/runtime_rc2/test_rc2_render_correction.py

These are required for PID-003 in the current tree because render correction is untracked as a whole file, but they also contain prior render-correction work. Split or accept that dependency explicitly before commit.

Excluded files:
- DELTA.py unless prior render-correction UI integration is approved for the same commit.
- orchestration/runtime/rc2_natural_conversation_renderer.py.
- orchestration/runtime/rc45_discourse_cognition_bridge.py.
- tests/runtime_rc5/test_delta_report_inspection.py.
- tests/runtime_rc5/test_rc45_discourse_cognition_bridge.py.
- reports/RC2_*.json generated churn.

Unresolved failures:
- Concept reuse precedence for approved concepts versus direct local answers.
- Concept browse follow-up precedence versus session-memory follow-up.
- Developmental memory enrichment count mismatch.
- Natural-renderer wording tests with stale expected phrases.

## Closure Recommendation

The A/A2 repair group is ready for commit review after either:

1. selective staging isolates only A/A2 hunks, or
2. the operator explicitly approves bundling the prior render-correction dependency files with this repair group.

Do not start Stage B from this dirty tree until that decision is made.

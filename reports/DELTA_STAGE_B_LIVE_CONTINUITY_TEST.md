# DELTA Stage B Live Continuity Test

Date: 2026-07-11
Objective: Stage B live UI testing only
Branch: codex/delta-cognitive-core
Policy: no implementation during this pass; repairs require cross-reference and operator approval.

## Scope

Stage B validates the live conversation engine's ability to maintain continuity across turns:

- B1 normal follow-up
- B2 delayed follow-up
- B3 pronoun/reference resolution
- B4 genuine ambiguity
- B5 explicit topic reset

Testing used the same minimal in-process live UI harness against `DeltaApp._send_chat`, visible transcript output, route metadata, and safety flags. The harness disabled model warming/switching and did not execute local model inference.

## Safety Summary

Across the controlled Stage B run:

- Turns: 11
- Memory candidates: 0
- Provider calls: 0
- Web/retrieval calls: 0
- Canonical writes: 0
- Autonomous actions: 0
- Pending actions: 3

The pending actions were local-model consent offers, not executed actions.

## Observed Results

| Case | Status | Route(s) | Classification | Evidence |
| --- | --- | --- | --- | --- |
| B1 normal follow-up | Fail | session_memory -> local_model_consent_required | FOLLOW_UP_RESOLUTION_ERROR | Context-setting prompt containing "this conversation" was treated as an orphan follow-up; "Tell me more about the second point" then asked for local model consent instead of resolving the second point. |
| B2 delayed follow-up | Fail | session_memory -> session_memory -> local_model_consent_required | FOLLOW_UP_RESOLUTION_ERROR / TOPIC_STATE_ERROR | "First subject:" and "Second subject:" declarations were interpreted as follow-ups; "Going back to the first subject..." was not recognized as a return-to-prior-topic follow-up. |
| B3 pronoun/reference resolution | Partial | developmental_concept_memory -> session_memory | UNDER_ANSWERING | "Why does that matter?" stayed local and resolved to feedback loops, but the answer merely echoed the prior concept instead of explaining significance. |
| B4 genuine ambiguity | Fail | developmental_concept_memory -> session_memory | AMBIGUITY_HANDLING_ERROR | With two plausible referents, "Why is that risky?" guessed a single topic instead of asking a focused clarification or presenting alternatives. |
| B5 explicit topic reset | Partial pass | working_reasoning_set -> local_model_consent_required | TOPIC_RESET_PARTIAL | The reset did not drag prior feedback-loop context forward, but the answer fell to local-model consent rather than explaining the boundary from existing local knowledge. |

## Cross-Referenced Root Causes

1. Broad follow-up detection
   - File: `orchestration/runtime/rc2_cognitive_episode.py`
   - Symbol: `_is_followup`
   - Evidence: any occurrence of `this`, `that`, `it`, `first one`, `second one`, or `earlier` can mark a turn as follow-up.
   - Effect: context-setting declarations such as "For this conversation..." and "First subject: ..." can be misclassified before there is a valid antecedent.

2. Missing follow-up phrase families
   - File: `orchestration/runtime/rc2_cognitive_episode.py`
   - Symbol: `_is_followup`
   - Evidence: exact `tell me more` is covered, but `tell me more about ...` is not. `go back to ...` is covered, but `going back to ...` is not.
   - Effect: B1 and B2 semantic follow-ups bypass working-memory resolution and fall into local-model consent.

3. Topic declaration parsing gap
   - File: `orchestration/runtime/rc2_cognitive_episode.py`
   - Symbols: `_topic_from_question`, `_branches`
   - Evidence: patterns cover `what is`, `what are`, `tell me about`, `let's discuss`, `talk about`, and `explain`; they do not recognize declarative anchors like `First subject:` or `Second subject:`.
   - Effect: delayed-return tests lack clean topic branches.

4. Ambiguity is not surfaced
   - File: `orchestration/runtime/rc2_cognitive_episode.py`
   - Symbols: `_select_active_branch`, `_resolved_refs`, `_followup_answer`
   - Evidence: when multiple recent branches are plausible and the prompt says "that", the resolver selects the latest or entity-matching branch without exposing ambiguity.
   - Effect: B4 guesses instead of asking a clarification.

5. Weak significance rendering
   - File: `orchestration/runtime/rc2_cognitive_episode.py`
   - Symbol: `_followup_answer`
   - Evidence: `why does that matter` falls through to `_plain_key_point`, often echoing the first sentence.
   - Effect: B3 resolves but under-answers.

## Proposed Repairs For Review Only

No changes were made in this Stage B pass.

Candidate bounded repair set:

1. Treat declarative context anchors as new context, not follow-ups.
   - Add a small helper such as `_is_context_declaration(lower)` for patterns like `for this conversation`, `first subject:`, `second subject:`, and `context:`.
   - Use it before `_is_followup` returns true.

2. Expand follow-up phrase detection conservatively.
   - Recognize `tell me more about ...` and `going back to ...`.
   - Avoid broadening to arbitrary questions.

3. Add branch topics for explicit subject declarations.
   - Extend `_topic_from_question` to parse `first subject: X` and `second subject: X`.
   - Keep this limited to explicit labels.

4. Surface ambiguity for bare "that" when recent branches contain multiple plausible topics and no entity disambiguates.
   - Return a session-memory clarification with two candidate interpretations.
   - Do not use provider, retrieval, or local model.

5. Add a generic "why does that matter" significance renderer.
   - If topic is known, explain consequence/decision relevance instead of repeating the first sentence.

## Focused Regression Candidates

- `test_tell_me_more_about_second_point_uses_prior_ordered_context`
- `test_going_back_to_first_subject_resolves_delayed_topic`
- `test_context_declaration_is_not_orphan_followup`
- `test_ambiguous_that_surfaces_two_referents`
- `test_why_does_that_matter_explains_significance`

## Recommendation

Stage B should proceed with a bounded continuity repair only after operator approval. The most beneficial first fix appears to be the follow-up phrase/context-declaration repair, because it addresses B1 and B2 without touching provider, memory, retrieval, or broader architecture.

## Repair Group 1 Retest

Approved scope:

- narrow context-declaration detection
- recognition of `tell me more about ...`
- recognition of `going back to ...`
- parsing of explicit `First subject:`, `Second subject:`, and `Context:` anchors
- three focused regressions

Files changed:

- `orchestration/runtime/rc2_cognitive_episode.py`
- `tests/runtime_rc2/test_rc2_working_memory_episode.py`

Validation:

- `tests/runtime_rc2/test_rc2_working_memory_episode.py`: 15 passed
- `py_compile` for changed resolver and test file: passed
- 11-turn Stage B live harness rerun: completed

Live retest safety:

- Turns: 11
- Memory candidates: 0
- Provider calls: 0
- Web/retrieval calls: 0
- Canonical writes: 0
- Autonomous actions: 0
- Pending actions: 1

Repair result:

- B1 normal follow-up: repaired. The context declaration is retained as session context, and `Tell me more about the second point` resolves to the second ordered point.
- B2 delayed follow-up: repaired. Explicit first/second subject anchors are retained, and `Going back to the first subject...` resolves to the first subject's limitation.
- B3 pronoun/reference significance rendering: unchanged; still partial.
- B4 ambiguity handling: unchanged; still fails by selecting one referent silently.
- B5 topic reset: unchanged; reset avoids stale context but still degrades into local-model consent.

Stop condition:

Do not continue into ambiguity handling or significance rendering without separate approval.

## Sequential Closure Retest

Date: 2026-07-11

Approved objective: complete Stage B through B3, B4, B5, then run the full 11-turn live harness once.

### Pathology IDs

| ID | Pathology | Original behavior | Root cause | Status |
| --- | --- | --- | --- | --- |
| PID-B01 | Normal follow-up resolution | Context declarations were treated as orphan follow-ups; `Tell me more about ...` fell to local-model consent. | Context declarations and follow-up phrase families were missing from working-memory resolution. | REPAIRED |
| PID-B02 | Delayed topic return | `Going back to the first subject...` missed the labeled subject branch. | Explicit `First subject:` / `Second subject:` anchors were not parsed, and full-sequence ordinal lookup initially used absolute conversation position. | REPAIRED |
| PID-B03 | Significance under-answering | `Why does that matter?` resolved locally but echoed prior content. | `_followup_answer` lacked a general significance renderer. | REPAIRED |
| PID-B04 | Ambiguous referent guessing | With two plausible recent referents, `that` selected one silently. | Ambiguity was not surfaced before active-branch selection. | REPAIRED |
| PID-B05 | Explicit topic-reset fallback | Topic reset avoided stale context but fell to local-model consent for local DELTA governance concepts. | Explicit reset prompts did not enter the repo-local V2.9 self-knowledge path, and aliases lacked DELTA 1.0 module/capability terms. | REPAIRED |

### Repair Groups

Repair Group 2 - PID-B03 significance rendering:

- Files changed: `orchestration/runtime/rc2_cognitive_episode.py`, `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- Added significance detection for `Why does that matter?`, `Why is that important?`, `Why should I care about that?`, `What difference does that make?`, and `How does that affect the decision?`
- Live result: B3 resolves to feedback loops and explains action/decision impact without provider calls, retrieval, memory candidates, or local-model inference.

Repair Group 3 - PID-B04 ambiguity handling:

- Files changed: `orchestration/runtime/rc2_cognitive_episode.py`, `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- Added ambiguity candidate detection for bare `that`, `it`, and `which one` when recent branches contain two plausible referents.
- Live result: B4 answers `That could refer to either feedback loops can improve planning or memory candidates can improve future recall. Which one do you mean?`

Repair Group 4 - PID-B05 topic reset answer routing:

- Files changed: `orchestration/runtime/rc2_cognitive_episode.py`, `orchestration/runtime/rc2_conversational_mode_router.py`, `orchestration/runtime/v29_natural_alias_router.py`, `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- Added explicit reset recognition for `New topic:`, `Switching subjects:`, `Different topic:`, `Let's move on.`, and `Forget the prior topic for now.`
- Added repo-local aliases for module permission boundary, capability activation, operator approval, module manifest, and rollback governance.
- Live result: B5 establishes a new active topic and routes through `local_conversation_model_lane` with `repo_local_self_knowledge`, no local-model consent.

### Focused Validation

- `python -m pytest tests/runtime_rc2/test_rc2_working_memory_episode.py -q`: 22 passed in 0.85s
- `py_compile` passed for:
  - `orchestration/runtime/rc2_cognitive_episode.py`
  - `orchestration/runtime/rc2_conversational_mode_router.py`
  - `orchestration/runtime/v29_natural_alias_router.py`
  - `tests/runtime_rc2/test_rc2_working_memory_episode.py`

### Final 11-Turn Live Harness

Harness: headless in-process `DeltaApp._send_chat`, fake UI widgets, `execute_local_model=False`, no model warming or switching.

| Turn | Case | Route | Status | Evidence |
| --- | --- | --- | --- | --- |
| 1 | B1 setup | session_memory | PASS | Context declaration accepted. |
| 2 | B1 follow-up | session_memory | PASS | Second ordered point resolved to adjustment changing next action. |
| 3 | B2 first subject | session_memory | PASS | First subject anchor accepted. |
| 4 | B2 second subject | session_memory | PASS | Second subject anchor accepted. |
| 5 | B2 return | session_memory | PASS | Returned to photosynthesis limitation; did not reuse feedback loops. |
| 6 | B3 setup | developmental_concept_memory | PASS | Feedback-loop setup answered locally, no pending action. |
| 7 | B3 significance | session_memory | PASS | Explained decision/action impact and adjustment. |
| 8 | B4 first referent | session_memory | PASS | First ambiguity candidate accepted. |
| 9 | B4 second referent | session_memory | PASS | Second ambiguity candidate accepted. |
| 10 | B4 ambiguous follow-up | session_memory | PASS | Presented both candidates and asked which was meant. |
| 11 | B5 topic reset | local_conversation_model_lane | PASS | Answered module permission boundary from repo-local self-knowledge without stale feedback-loop context. |

Final harness counts:

- Turns: 11
- Memory candidates: 0
- Provider calls: 0
- Web/retrieval calls: 0
- Canonical writes: 0
- Autonomous actions: 0
- Pending actions: 0

### Caveats

- Some context-declaration acknowledgement wording is still plain and occasionally says `this context as context`; this is stylistic and did not block operational continuity.
- B3 significance rendering is intentionally generic; it explains consequence and decision impact without trying to create a new reasoning architecture.

### Dirty Tree Attribution

Stage B intended files:

- `orchestration/runtime/rc2_cognitive_episode.py`
- `orchestration/runtime/rc2_conversational_mode_router.py`
- `orchestration/runtime/v29_natural_alias_router.py`
- `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- `reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md`

Prior render-correction / A/A2 / unrelated dirty files excluded from Stage B commit proposal:

- `DELTA.py`
- `docs/delta_1_0/DELTA_1_0_ARCHITECTURE.md`
- `orchestration/runtime/rc2_contradiction_engine.py`
- `orchestration/runtime/rc2_dialogue_intent_classifier.py`
- `orchestration/runtime/rc2_natural_conversation_renderer.py`
- `orchestration/runtime/rc45_discourse_cognition_bridge.py`
- `orchestration/runtime/rc2_render_correction.py`
- `tests/runtime_rc2/test_rc2_contradiction_engine.py`
- `tests/runtime_rc2/test_rc2_conversational_mode_router.py`
- `tests/runtime_rc2/test_rc2_render_correction.py`
- `tests/runtime_rc5/test_delta_report_inspection.py`
- `tests/runtime_rc5/test_rc45_discourse_cognition_bridge.py`
- generated RC2 report JSON churn under `reports/RC2_*.json`
- `reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md`
- `reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md`
- `reports/delta_1_0/DELTA_1_0_OPERATOR_PILOT_AND_GATED_ACTIVATION.md`
- `reports/delta_1_0/readiness.md`

### Commit Proposal

Prepare only; do not commit or push.

Suggested files:

- `orchestration/runtime/rc2_cognitive_episode.py`
- `orchestration/runtime/rc2_conversational_mode_router.py`
- `orchestration/runtime/v29_natural_alias_router.py`
- `tests/runtime_rc2/test_rc2_working_memory_episode.py`
- `reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md`

Suggested commit message:

```text
stabilize DELTA conversation continuity and ambiguity handling
```

Recommendation: Stage B is satisfactory and ready for operator commit review, with unrelated dirty-tree churn excluded.

# DELTA Conversation Cycle Diagnosis

Run diagnosed: `conversation-cycles-20260713T022352Z`

Scope: diagnosis only. No source code was modified during this pass.

Primary evidence:

- `reports/conversation_cycles/latest/transcript.md`
- `reports/conversation_cycles/latest/results.json`
- `reports/conversation_cycles/latest/route_traces.jsonl`
- `reports/conversation_cycles/latest/failures.md`

## Executive finding

The strongest confirmed defect is not that DELTA always routes new turns incorrectly.

The narrower failure is:

> DELTA can select an acceptable route for the current turn, but the accepted answer is not reliably promoted into the authoritative conversation state used by the next turn.

This creates downstream failures in follow-up handling, topic switching, pronoun resolution, and retrieval relevance.

## Grader defects found

The previous automatic grader conflated user-visible answer text with developer-overlay/internal state text.

False-positive examples:

- Cycle 1 turn 2, `hi`: visible answer was correct social text, but the grader flagged `Advanced Operator Mode Evidence Standard` because the developer overlay still contained stale cognitive-episode state.
- Cycle 1 turn 3, `how are you`: same false-positive pattern.
- Cycle 2 turn 2, physics brainstorming: visible answer correctly chose `motion`; the stale concept appeared in overlay/state, not in the visible answer.

The grader should split these into separate checks:

- `VISIBLE_RESPONSE_TOPIC_DRIFT`
- `INTERNAL_STATE_STALE`

It should not mark a visible answer as contaminated just because an overlay trace contains stale state.

The grader also had false negatives:

- Cycle 4 turn 4, `compare that with Mars`, passed despite returning `Attention Budgeting, Backlog Grooming`.
- Cycle 5 turn 4, `why do people respond emotionally to it`, passed despite asking whether `it` meant physics or music after an explicit topic switch.
- Cycle 6 turn 1, `Who was Ada Lovelace?`, passed despite offering local-model escalation instead of an ordinary factual answer.
- Moon follow-ups preserved the label `Moon Color Appearance`, but did not substantively answer `why` or `does it always appear gray`.

## Case 1: Physics transition

Question:

Why does a correct `motion` answer fail to replace or clear the old concept anchor?

Observed sequence:

- Cycle 2 turn 1 establishes `active_topic_anchor = Advanced Operator Mode Evidence Standard`.
- Cycle 2 turn 2 prompt: `what is the first concept that comes to mind related to physics`.
- Visible answer: `The first concept that comes to mind is motion...`
- Route: `local_conversation_model_lane`.
- Routing observability: `explicit_new_topic_request: true`, `memory_retrieval_bypassed: true`.
- After the turn, `active_topic_anchor` is still `Advanced Operator Mode Evidence Standard`.
- The cognitive episode still reports `active_topic: advanced operator mode evidence standard`.
- Cycle 2 turns 3-4 then follow the stale concept.

First incorrect state transition:

`DELTA.py::_update_active_topic_anchor()` does not clear or replace the active anchor for a successful non-concept conversational answer. It only updates the UI anchor when the payload contains `active_topic_anchor` or `concept_matches`.

Relevant code:

- `DELTA.py:2691-2700`: `_send_chat` calls `route_message`, stores payload, then calls `_update_active_topic_anchor(payload)`.
- `DELTA.py:2741-2759`: `_update_active_topic_anchor()` only accepts explicit `active_topic_anchor` or concept matches.
- `orchestration/runtime/rc2_conversational_mode_router.py:2018-2034`: brainstorming routes through `local_conversation_answer()` and returns without attaching a replacement anchor.
- `orchestration/runtime/rc2_conversational_mode_router.py:1705-1712`: the physics brainstorming answer is generated as local conversation, not concept memory.

Why the cognitive episode stays stale:

`DeltaApp._recent_history_for_router()` appends the stale `active_topic_anchor` as a synthetic `anchor` message. `build_cognitive_episode()` then builds branches from that synthetic anchor before considering the current payload.

Relevant code:

- `DELTA.py:2050-2054`: stale `active_topic_anchor` is appended into router history.
- `orchestration/runtime/rc2_cognitive_episode.py:307-319`: synthetic anchor history becomes a conversation branch.
- `orchestration/runtime/rc2_cognitive_episode.py:349-359`: active branch selection prefers recent/current entities but otherwise falls back to the last branch.

Diagnosis:

The route-level repair allowed the current physics turn to bypass memory retrieval, but no post-turn authority update cleared the stale anchor or promoted `motion/physics` into conversation state.

## Case 2: Sky follow-up

Question:

Why does a deterministic direct answer lack a reusable conversational topic/answer frame?

Observed sequence:

- Cycle 3 turn 1 prompt: `what color is the sky`.
- Visible answer correctly explains blue sky/scattering.
- Route: `local_conversation_model_lane`.
- After the turn, `active_topic_anchor` remains null.
- Cycle 3 turn 2 `tell me more` returns local-model consent instead of elaborating.
- Cycle 3 turn 3 `why is that` repeats the local-model consent path.
- Cycle 3 turn 4 cannot recover the topic.

First incorrect state transition:

The direct sky answer is not promoted into a reusable topic/answer frame after render. It is stored only as generic session history, and there is no explicit conversational anchor for `sky` or `blue-sky scattering`.

Why `tell me more` creates local-model consent:

`local_conversation_answer()` falls through to a hard follow-up fallback:

- It tries development/history/recent-concept/direct paths.
- If the classified intent is `followup`, it returns `local_model_consent_required` with `pending_action_suggestion`.

Relevant code:

- `orchestration/runtime/rc2_conversational_mode_router.py:1621-1627`: pre-follow-up paths.
- `orchestration/runtime/rc2_conversational_mode_router.py:1627-1648`: unconditional local-model-consent fallback for follow-up intent.
- `DELTA.py:2708-2733`: `_send_chat` turns that payload into pending local-model/deepening state.

Diagnosis:

The sky answer is good as a single turn but weak as discourse state. Follow-up handling treats "elaborate from the immediately prior answer" as "unknown question needing a model" instead of using the prior answer as a bounded local context.

## Case 3: Music topic switch

Question:

Why does the correction route not update active topic state?

Observed sequence:

- Cycle 5 turn 1 prompt: `tell me about physics`.
- DELTA browses local physics concepts and anchors `Buoyancy`.
- Cycle 5 turn 2 prompt: `actually let's talk about music`.
- Visible answer: `Got it. I will treat that as a correction to the current thread.`
- Route: `social_conversation`.
- After the turn, `active_topic_anchor` is still `Buoyancy`.
- The cognitive episode reports `active_topic: physics`.
- Cycle 5 turn 3 does discuss music generically.
- Cycle 5 turn 4 asks whether `it` means physics or music.

First incorrect state transition:

The correction/social route acknowledges the topic switch but does not commit the new topic into `active_topic_anchor`, nor does it clear the old concept anchor.

Relevant code:

- `orchestration/runtime/rc2_conversational_mode_router.py:235`: correction response is social acknowledgement text.
- `DELTA.py:2741-2759`: no anchor update occurs without an explicit anchor or concept matches.
- `orchestration/runtime/rc2_cognitive_episode.py:477-490`: explicit topic reset patterns do not include `actually let's talk about ...`.
- `orchestration/runtime/rc2_cognitive_episode.py:523-535`: ambiguity candidates come from the last two branch topics, which leaves `physics` and `music` competing.

Diagnosis:

Topic correction currently functions as conversational politeness, not as an authoritative state transition. The old `Buoyancy` anchor remains authoritative in Tk state even after the user explicitly requests music.

## Case 4: Moon/Mars comparison

Question:

Why does `compare that with Mars` reach unrelated multi-concept retrieval?

Observed sequence:

- Cycle 4 turn 1 anchors `Moon Color Appearance`.
- Turns 2-3 preserve the Moon label but give shallow follow-up answers.
- Turn 4 prompt: `compare that with Mars`.
- Cognitive episode resolves `that` and `it` to `Moon Color Appearance`.
- Route arbitration says recommended group was `working_memory_reference_resolution`, but selected route was `developmental_multi_concept_retrieval`.
- Visible answer returns unrelated concepts: `Attention Budgeting, Backlog Grooming`.
- After the turn, `active_topic_anchor` becomes `Attention Budgeting`.

First incorrect state transition:

The comparison prompt contains both a pronoun reference (`that`) and a relation target (`Mars`). The cognitive episode resolves the pronoun correctly, but that resolution is not passed into multi-concept query construction. The retrieval parser sees raw text, not the resolved pair `Moon Color Appearance` + `Mars`.

Relevant code:

- `orchestration/runtime/rc2_cognitive_episode.py:446-450`: `that` resolves to `Moon Color Appearance`.
- `orchestration/runtime/rc2_developmental_concept_memory.py:697-723`: `parse_multi_concept_query()` parses raw `compare that with Mars` into weak seeds.
- `orchestration/runtime/rc2_conversational_mode_router.py:2439-2474`: multi-concept retrieval is allowed to return matches even after context resolution identified the relevant referent.
- `orchestration/runtime/rc2_route_arbitration.py:226-254`: arbitration records working-memory reference resolution as higher precedence, but dispatch still selects multi-concept retrieval in the trace.

Diagnosis:

Reference resolution and retrieval query construction are disconnected. A resolved referent is visible in the trace but not used as the query seed for retrieval or comparison.

## Consolidated root causes

1. Post-turn authority update is too narrow.

`DeltaApp.active_topic_anchor` updates only from concept-memory-shaped payloads. Successful ordinary conversation, brainstorming, direct factual answers, and social topic switches do not become authoritative topic state.

2. Synthetic anchors are too durable.

The Tk layer appends `active_topic_anchor` into router history even after a new turn has selected a non-anchor route. That gives stale concepts a privileged path into the next cognitive episode.

3. Follow-up fallback is too model-oriented.

Generic follow-ups become local-model consent when history/direct concept handlers do not match, even when the immediately prior assistant answer is sufficient for a bounded elaboration.

4. Correction is not a discourse-state operation.

Correction/topic-switch prompts can be acknowledged without clearing/replacing old state.

5. Reference resolution is not consumed by retrieval.

The episode can resolve `that -> Moon Color Appearance`, but multi-concept retrieval parses the raw user text and loses the resolved referent.

6. The grader needs semantic and visibility boundaries.

It should grade visible response, overlay/internal state, pending state, and semantic adequacy as distinct dimensions.

## Recommended next repair order

1. Add/repair conversation-state promotion for non-concept successful answers.
2. Clear or demote stale `active_topic_anchor` when an explicit new topic or topic switch succeeds.
3. Add deterministic follow-up elaboration from the last visible answer before offering a local model.
4. Treat correction/topic-switch routes as state transitions, not only social acknowledgements.
5. Feed cognitive-episode resolved references into comparison/retrieval query construction.
6. Update the grader to separate visible-answer drift, stale internal state, semantic adequacy, and pending-state discipline.

Do not start another broad runtime campaign until these four transition cases pass through the Tk-compatible integrated path.

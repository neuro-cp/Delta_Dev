# DELTA Live Behavioral Validation - Stage A/A2 Record

Date: 2026-07-11
Branch: codex/delta-cognitive-core
Starting HEAD: 4d8f2607dc16531a18ab131e110cbcc0bf27056f
Model observed by Codex: GPT-5 current session; operator approved continuing despite requested GPT-5.5 constraint.

## Active Path Map

- UI startup entry point: DELTA.py Tkinter app, class DeltaApp.
- Message submission path: DeltaApp._send_chat.
- Discourse bridge: rc45_discourse_cognition_bridge.build_discourse_frame.
- Conversational router: rc2_conversational_mode_router.route_message.
- Render correction: rc2_render_correction.build_render_correction_payload.
- Working memory episode: rc2_cognitive_episode.resolve_working_memory_followup and attach_episode.
- PC1 integration: DELTA._try_pc1_pragmatic_answer, only for governed/report cues.
- RC3/RC4/RC5 UI panels: read-only adapter tabs in DELTA.py.
- Provider/retrieval gates: router flags disabled; no provider or web calls observed.

## Component Classification

- DELTA.py conversation UI: LIVE
- rc2_conversational_mode_router: LIVE
- rc2_dialogue_intent_classifier: LIVE
- rc2_render_correction: LIVE
- rc2_cognitive_episode: LIVE
- rc2_contradiction_engine: LIVE
- rc45_discourse_cognition_bridge: LIVE for report/governance pre-routing
- RC3/RC4/RC5 adapter tabs: LIVE read-only panels
- Generated reports under reports/: REPORT_ONLY

## Live Harness

Used a minimal in-process Tkinter UI harness against DeltaApp._send_chat, chat transcript, session_history, and last_payload. Warm/switch hooks were disabled in the harness to avoid model changes and local model loading; test turns used execute_local_model=False.

## Stage A/A2 Results

Final live retest covered 19 turns: A1-A4 and A2.1-A2.12, including context turns for ellipsis and topic drift.

- Provider calls: 0
- Web/retrieval calls: 0 external web; approved local concept lookup occurred for feedback-loop answer
- Memory candidates after repair: 0
- Canonical writes: 0
- Autonomous actions: 0
- File writes by DELTA runtime: 0
- Runtime commits/pushes: 0

## Repaired Pathologies

1. CASUAL_INTENT_MISCLASSIFICATION / UNNATURAL_BOILERPLATE
   - Observed: casual turns such as "What are you up to?", "Oh, that makes sense.", and sarcasm drifted into local-model, concept-memory, or session-memory routes.
   - Root cause: classifier coverage gaps and social route delegated back to local_conversation_answer.
   - Repair: expanded casual dialogue rules and made social route return direct social_conversation payloads.
   - Files: rc2_dialogue_intent_classifier.py, rc2_conversational_mode_router.py.

2. MEMORY_GOVERNANCE_ERROR
   - Observed: ordinary answers created Concept Review candidates without memory request.
   - Root cause: maybe_build_memory_candidate automatically proposed memory candidates for normal conversation.
   - Repair: ordinary conversation no longer auto-creates candidates; explicit remember flow still builds review candidates.
   - Files: rc2_conversational_mode_router.py.

3. RENDER_CORRECTION_ERROR
   - Observed: "Summarize the previous answer in two sentences" routed to local-model consent instead of transforming the previous answer.
   - Root cause: summarize-previous phrasing was absent from render-correction detection.
   - Repair: added summarize/summarise previous-answer detection as concise render correction.
   - Files: rc2_render_correction.py, rc2_conversational_mode_router.py.

4. CASUAL_INTENT_MISCLASSIFICATION
   - Observed: "What do you think makes a good debugging partner?" returned a generic coding capability answer.
   - Root cause: coding intent matched "debugging" before direct opinion handling.
   - Repair: added a direct conversational answer and checked direct answers before coding canned response.
   - Files: rc2_conversational_mode_router.py.

5. ROUTING_PRECEDENCE_ERROR
   - Observed: natural topic drift with "but now" routed to contradiction analysis.
   - Root cause: contradiction engine treated standalone "but now" and broad "but" splits as contradiction cues.
   - Repair: removed standalone "but now" trigger and gated implicit "but" contradiction detection on explicit contradiction cues.
   - Files: rc2_contradiction_engine.py.

6. ELLIPSIS_RESOLUTION_FAILURE / UNDER_ANSWERING
   - Observed: "And the second one?" fabricated a weak continuation when no list existed; "Why do you think it keeps doing that?" echoed prior feedback-loop text.
   - Root cause: working-memory follow-up renderer lacked ordered-content validation and a substantive feedback-loop why response.
   - Repair: ask clarification when no ordered prior content exists; add feedback-loop explanation for repeated behavior follow-up.
   - Files: rc2_cognitive_episode.py.

## Focused Validation

- tests/runtime_rc2/test_rc2_conversational_mode_router.py::test_casual_dialogue_turns_do_not_fall_into_technical_routes
- tests/runtime_rc2/test_rc2_conversational_mode_router.py::test_ordinary_conversation_does_not_create_memory_candidate
- tests/runtime_rc2/test_rc2_conversational_mode_router.py::test_debugging_partner_opinion_gets_conversational_answer
- tests/runtime_rc2/test_rc2_render_correction.py
- tests/runtime_rc2/test_rc2_contradiction_engine.py
- tests/runtime_rc2/test_rc2_working_memory_episode.py

Observed focused pass results:
- 10 passed for render-correction plus selected Stage A/A2 checks.
- 11 passed for contradiction engine.
- 13 passed for working-memory episode plus drift check.

The full router test file still has unrelated failures from the pre-existing dirty tree and changed expectations around earlier render-correction/concept-memory work; it was not treated as a campaign failure for this A/A2 slice.

## Recommendation

CONTINUE_CONTROLLED_OPERATOR_PILOT

Continue with Stage B only after reviewing the dirty tree separation, because this campaign touched files that already had uncommitted render-correction changes.

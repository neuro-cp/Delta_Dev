# Routing Execution Map

Repository: `G:\Delta_Dev`  
Branch: `codex/delta-cognitive-core`  
HEAD: `f8d0c343452141d26509f44f5198b69e20b695e4`

## Verified Runtime State

- Active launch entry point: `DELTA.py`, `if __name__ == "__main__"` launches `DeltaApp`.
- Active Tk/UI conversation submission handler: `DELTA.py::DeltaApp._send_chat`.
- Function that first receives raw operator text in the active UI: `DeltaApp._send_chat`, via `self.chat_input.get().strip()`.
- Live-runtime raw text receiver: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py::handle_live_chat`.
- Non-live raw text router: `orchestration/runtime/rc2_conversational_mode_router.py::route_message`.
- Obsolete RC wrappers: RC3/RC4/RC5/RC6/RC7/RC11/RC12 UI adapters are retained/imported for panels, reports, or narrow pilot shortcuts; the active normal conversation path is `DELTA.py -> route_message` or `DELTA.py -> handle_live_chat -> route_message` fallback.

## Main Path

```text
operator types message
-> DELTA.py::DeltaApp._send_chat
-> append user text via DeltaApp._append_chat
-> build discourse frame via rc45_discourse_cognition_bridge.build_discourse_frame
-> if live_runtime_session.active:
   -> DeltaApp._begin_live_runtime_turn
   -> delta_1_4_live_wikipedia_runtime.handle_live_chat
   -> live arbitration: controller event, lifecycle, pending local model, pending promotion, help/memory/self-model/context, Wikipedia, fallback RC2
   -> LiveChatResponse(answer, route, payload)
   -> DeltaApp._complete_live_runtime_turn
   -> DeltaApp._append_chat("DELTA", response.answer)
-> else:
   -> UI preemption routes: render correction, local report inspection, RC6 pilot, RC45 report/pilot shortcuts, PC1 pragmatic answer, pending local/provider/model/deepening approvals, memory candidate commands
   -> rc2_conversational_mode_router.route_message
   -> rc2_conversational_mode_router.render_route
   -> DeltaApp._append_chat("DELTA", rendered)
```

## Branches

- greeting: `_send_chat` non-live -> `route_message` -> `classify_intent` / `classify_dialogue_act` -> social payload -> `render_route`; live mode falls through to `handle_live_chat` fallback `route_message` unless a higher live condition matches.
- ordinary conversation: `_send_chat` -> `route_message` -> `local_conversation_answer` / natural renderer / arbitration trace -> `render_route`.
- tell me more: non-live can match pending local-model deepening in `_send_chat` before RC2; otherwise `route_message` checks history answers, recent concept follow-up, working-memory follow-up, anchor follow-up, or local-model consent for follow-up.
- why?: `classify_intent` may classify analysis; `route_message` can choose working-memory follow-up, WRS, concept retrieval, or local conversation depending history and concept matches.
- pronoun follow-up: `route_message` -> `resolve_working_memory_followup` / `attach_episode`; active anchor may also drive `deepen_from_concept_anchor`.
- concept recall: `route_message` -> `query_approved_concepts`, `browse_approved_concepts`, `retrieve_multi_concept_set`, `build_working_reasoning_set`.
- Wikipedia: live only -> `handle_live_chat` -> `wikipedia_query_from_message` -> `retrieve_wikipedia_text` -> `run_wikipedia_developmental_cognition` -> promotion candidate/inquiry -> `render_wikipedia_answer`.
- local model: non-live `_send_chat` pending approval -> `route_message(... execute_local_model=True, provider_manager=...)`; live pending request -> `_run_approved_local_model_request` -> `route_message(... execute_local_model=True, provider_manager=...)` -> `execute_local_model_answer` -> `ProviderManager.infer` or subprocess fallback.
- self-model: live -> `is_operational_self_model_question` -> `answer_operational_self_model_question`; non-live self-description -> `classify_intent` / `local_conversation_answer`.
- pending approval: `_send_chat` handles UI-level pending provider/local/deepening before RC2; live `handle_live_chat` handles pending local-model and promotion inquiries before Wikipedia/fallback.
- pause: UI control button -> `pause_live_initiative`; text intent live -> `_runtime_control_intent` -> `_handle_runtime_control_intent`.
- suspend: UI control button -> `suspend_live_runtime_initiative`; text intent live -> `_runtime_control_intent` -> `_handle_runtime_control_intent`.
- unknown input: RC2 -> `local_model_consent_required` / provider preview / fallback `local_conversation_answer`; live fallback uses RC2 unless Wikipedia or governance intercepts.

## Override Points

- Old concept can override current topic: RC2 `query_approved_concepts`, `_last_concept_context`, `resolve_followup_anchor`, and `DeltaApp._update_active_topic_anchor` can steer follow-ups toward prior concept matches.
- Pending candidate can hijack ordinary turn: live `_is_affirmative` plus `_has_pending_promotion_inquiry`; UI pending local/provider/deepening blocks in `_send_chat`.
- Wikipedia can win: live `wikipedia_query_from_message` after governance/self-model/context checks and before RC2 fallback.
- Concept recall can win: RC2 explicit browse/multi-concept/WRS/concept memory branches precede final local conversation fallback.
- Local model reasoning can win: only after consent/approval or explicit `execute_local_model=True`.
- Follow-up state can be lost: short `DeltaApp._recent_history_for_router` window, active topic anchor based on payload, and history-derived anchors can diverge.
- Fallback can activate: inactive live runtime fallback, Wikipedia failure/budget exhausted, local-model unavailable, no concept match, provider unavailable/refused.

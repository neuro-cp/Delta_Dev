# Routing Precedence

## UI Precedence (`DELTA.py::DeltaApp._send_chat`)

| Priority | Condition | Selected route | File | Function | Can override | Can be overridden by | Fallback |
|---:|---|---|---|---|---|---|---|
| 1 | Empty message | No route | DELTA.py | `_send_chat` | Everything | None | Return |
| 2 | Live runtime active | Live runtime worker | DELTA.py | `_send_chat`, `_begin_live_runtime_turn` | All non-live UI/RC2 routes | None except queued lifecycle controls after worker completes | `handle_live_chat` |
| 3 | Render correction request | render correction payload | DELTA.py / rc2_render_correction.py | `_send_chat` | RC2 general routing | Live active | `route_message` render correction |
| 4 | Local report inspection | local report answer | DELTA.py | `_inspect_local_report` callers | RC2 routing | Live active/render correction | Continue |
| 5 | RC6 / RC45 / PC1 specialist shortcuts | fixed specialist answer | DELTA.py + rc45/pc1 modules | `_send_chat` preemption blocks | RC2 general routing | Earlier UI conditions | Continue |
| 6 | Pending local deepening affirmative/cancel | execute/cancel pending local deepening | DELTA.py | `_send_chat` | Ordinary turn meaning | Earlier UI conditions | Continue |
| 7 | Pending local model question affirmative/cancel | execute/cancel local model | DELTA.py | `_send_chat` | Ordinary affirmations | Earlier UI conditions | Continue |
| 8 | Pending provider question affirmative/cancel | approved provider preview/execution path | DELTA.py | `_send_chat` | Ordinary affirmations | Earlier UI conditions | Continue |
| 9 | Memory command | concept review candidate | DELTA.py | `_queue_last_answer_for_review` | RC2 routing | Earlier UI conditions | Continue |
| 10 | Default | RC2 route | DELTA.py / rc2_conversational_mode_router.py | `route_message` | None | Earlier UI conditions | render_route |

## Live Runtime Precedence (`handle_live_chat`)

| Priority | Condition | Selected route | File | Function | Can override | Can be overridden by | Fallback |
|---:|---|---|---|---|---|---|---|
| 1 | Session inactive | inactive fallback | delta_1_4_live_wikipedia_runtime.py | `handle_live_chat` | Live features | None | RC2 route/render |
| 2 | Lifecycle text intent | runtime control | delta_1_4_live_wikipedia_runtime.py | `_runtime_control_intent`, `_handle_runtime_control_intent` | Pending approvals/Wikipedia/fallback | Active session only | live state response |
| 3 | Autonomy suspended | suspended refusal | same | `handle_live_chat` | Retrieval/model/initiation | Lifecycle controls | response |
| 4 | Pending inquiry question | pending inquiries | same | `_is_pending_inquiry_question`, `_render_pending_inquiries` | Fallback | Lifecycle/suspend | response |
| 5 | Pending local request explicit cancel/approval | local model cancel/execute | same | `_has_pending_local_model_request`, `_run_approved_local_model_request` | Promotion/Wikipedia/fallback | Lifecycle/suspend/pause | response |
| 6 | Pending local + pending promotion + bare yes | ambiguous live action | same | `_render_ambiguous_live_action` | Accidental approval | explicit local request/cancel | response |
| 7 | Pending promotion affirmative/rejection | promotion approve/reject | same | `_approve_pending_promotion`, `_reject_pending_promotion` | Wikipedia/fallback | lifecycle/pause/ambiguity | response |
| 8 | Help/memory/self-model/context | governance or self-model response | same | `_is_live_help_request`, `_is_memory_request`, `is_operational_self_model_question`, `_is_live_context_declaration` | Wikipedia/fallback | pending approvals/lifecycle | response |
| 9 | Wikipedia query and budget | Wikipedia retrieval + developmental cognition | same | `wikipedia_query_from_message`, `retrieve_wikipedia_text` | RC2 fallback | pause/budget/failure | Wikipedia answer/failure |
| 10 | Default | RC2 fallback | same + rc2 router | `route_message`, `render_route` | None | earlier live routes | RC2 answer |

## RC2 Router Precedence (`route_message`)

RC2 precedence is implemented by early returns. In order: provider approval, GPT approval preview, social intent, render correction, clarification without history, early contradiction, execute-local-model route, early working-memory follow-up, development workflow, early analogy, early WRS, anchor follow-up, local model execution retry, direct/coding/external/image/development path, working-memory follow-up, knowledge browse, graph-assisted/synthesis/analogy/contradiction/WRS, multi-concept retrieval, domain browse, concept memory retrieval, mode-specific scaffold/fallback.

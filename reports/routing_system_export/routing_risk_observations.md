# Routing Risk Observations

## RISK-001 Greeting Or Social Input Can Be Misrouted If Live Runtime Falls To RC2 After Pending State

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `handle_live_chat`
- relevant condition: pending local-model request, pending promotion inquiry, or runtime control checks run before RC2 fallback social classification.
- why it can produce the behavior: a bare `yes`, `tell me more`, or other short ordinary continuation can be consumed as approval/ambiguity before social/follow-up routing.
- confidence: confirmed by source precedence.

## RISK-002 Follow-Ups Can Lose Current Topic When History Window Or Anchor Diverges

- file: `DELTA.py`
- function: `_recent_history_for_router`, `_update_active_topic_anchor`
- relevant condition: routing receives only recent history, while UI also stores a separate active topic anchor from concept matches.
- why it can produce the behavior: RC2 follow-up resolution and UI anchor state are duplicated; a vague follow-up may resolve from rendered history, active anchor, or concept matches depending route order.
- confidence: confirmed by source structure.

## RISK-003 Old Concept Attractor Can Override Current Topic

- file: `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `_last_concept_context`, `resolve_followup_anchor`, `query_approved_concepts` branch in `route_message`
- relevant condition: history-derived concept names and approved concept retrieval run before final local conversation fallback.
- why it can produce the behavior: if a prior answer exposed concept names, follow-up/browse logic can continue those concepts even when the new prompt is underspecified.
- confidence: likely; source shows mechanism, behavioral frequency requires transcript evidence.

## RISK-004 Raw Prompts Can Become Wikipedia Page Titles

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `wikipedia_query_from_message`, `retrieve_wikipedia_text`
- relevant condition: messages matching `Wikipedia: topic`, `look up ... on Wikipedia`, or related forms are cleaned and sent to the REST summary endpoint.
- why it can produce the behavior: query construction is deterministic string extraction; ambiguous or over-broad user wording becomes the page query unless cleaned by `_clean_query`.
- confidence: confirmed by source.

## RISK-005 Wikipedia Can Preempt Local RC2 Reasoning In Live Mode

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `handle_live_chat`
- relevant condition: after governance/self-model/context checks, a recognized Wikipedia query retrieves before RC2 fallback.
- why it can produce the behavior: live Wikipedia routing is ordered before `route_message` fallback, so a prompt containing a lookup form will not first attempt local reasoning.
- confidence: confirmed.

## RISK-006 Stale Pending Approvals Can Hijack Later Turns

- file: `DELTA.py`
- function: `_send_chat`
- relevant condition: `pending_provider_question`, `pending_local_model_question`, and `pending_local_model_deepening` are checked before default RC2 routing.
- why it can produce the behavior: ordinary affirmations or `tell me more` can execute/cancel pending actions from a prior turn if the pending field remains set.
- confidence: confirmed by source precedence.

## RISK-007 Local-Model Warmup Failure Falls Back Into Consent/Provider Paths

- file: `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `execute_local_model_answer`, `local_conversation_answer`
- relevant condition: local inference failures return `executed=False` with a reason; later logic may offer provider/support or local consent depending route.
- why it can produce the behavior: model failure is represented as payload state rather than exception; user-facing answer may become unavailable/support-offer instead of direct model error.
- confidence: likely.

## RISK-008 Self-Model State Can Lag Provider Residency

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `_record_local_model_residency`, `_provider_residency_status`; `answer_operational_self_model_question`
- relevant condition: controller model residency is updated after approved local-model calls and status is sampled from provider manager.
- why it can produce the behavior: if provider manager status fails or a UI-side warm/switch happened outside the live controller, self-model/status can disagree with real residency.
- confidence: possible.

## RISK-009 Response Composition Uses Multiple Independent Frames

- file: `DELTA.py`, `orchestration/runtime/rc2_conversational_mode_router.py`, `orchestration/runtime/rc2_cognitive_episode.py`
- function: `_send_chat`, `_finish_conversation_payload`, `attach_episode`
- relevant condition: UI discourse frame, RC2 route arbitration, and cognitive episode are separate analyses of the same message/history.
- why it can produce the behavior: developer overlay or preemptive UI route may describe one frame while the payload/rendered response follows another.
- confidence: confirmed by source structure.

## RISK-010 Conflicting Route Precedence Across UI, Live Runtime, And RC2

- file: `DELTA.py`, `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`, `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `_send_chat`, `handle_live_chat`, `route_message`
- relevant condition: each layer has its own early-return precedence.
- why it can produce the behavior: a prompt can be social in RC2, approval in UI, lifecycle in live mode, or Wikipedia in live mode depending active session and pending fields.
- confidence: confirmed.

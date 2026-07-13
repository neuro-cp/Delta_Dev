# Routing Stabilization

This note documents the bounded conversational routing repair added after the
routing export identified stale context bleed and Wikipedia over-selection.

## Scope

The repair does not add cognitive architecture, autonomous capability, memory
systems, provider authority, or model execution authority. It refines existing
RC2 and live-runtime precedence.

## Stabilized Decisions

- Explicit new topic requests invalidate older active concept anchors.
- Short follow-ups only use an active concept anchor when that anchor is still
  current.
- Broad brainstorming prompts stay in local conversation instead of concept
  retrieval or Wikipedia retrieval.
- Live Wikipedia retrieval now requires explicit Wikipedia intent, such as
  `Wikipedia: Ada Lovelace` or `Look up Ada Lovelace on Wikipedia`.
- Bare factual phrasing such as `Who is Ada Lovelace?` falls back to the normal
  conversation router unless the operator explicitly asks for Wikipedia.

## Routing Trace Fields

RC2 conversation payloads include `routing_observability`:

- `layer`
- `selected_route`
- `intent`
- `explicit_new_topic_request`
- `anchor_available`
- `anchor_followup_allowed`
- `memory_retrieval_bypassed`
- `history_turns_seen`
- `early_return`

Live-runtime fallback payloads include `live_routing_observability`:

- `layer`
- `selected_route`
- `raw_message`
- `wikipedia_query`
- `explicit_wikipedia_intent`
- `wikipedia_considered`
- `rc2_fallback_considered`

The trace is read-only and ephemeral. It is for developer overlay, regression
tests, and external review; it is not stored as memory and does not alter
governance.

## Remaining Validation Boundary

These repairs are source- and regression-test validated. Operator validation is
still required for long, natural conversations with the live UI because pending
approval state, human timing, and accumulated rendered history can still expose
pathologies that static tests do not cover.

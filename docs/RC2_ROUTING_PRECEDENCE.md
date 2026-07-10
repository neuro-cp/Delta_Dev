# RC2 Routing Precedence

RC2 is a conversational cognitive runtime. The router must preserve normal conversation while preventing neighboring cognitive modules from stealing each other's prompts. Working memory is a context resolver, not a universal answer route.

All routes remain read-only unless the operator explicitly enters an approval workflow. Conversation routing must not train, fine-tune, update weights, call providers, browse the web, write canonical memory, write noncanonical memory, create graph edges, create replay records, start schedulers, promote HYB1, or replace Model B.

## Precedence Order

| Precedence | Route family | Purpose |
| ---: | --- | --- |
| 1 | Safety and hard invariants | Enforce no-training, no-provider, no-write, no-action defaults. |
| 2 | Explicit user command or explicit mode | Honor direct mode controls, approval/refusal, and consent-gated commands. |
| 3 | Social conversation | Handle greetings, thanks, compliments, acknowledgements, cancellations, and pure social turns without cognitive routing. |
| 4 | Contradiction analysis | Compare claims, qualifiers, polarity, scope, and timeframe. |
| 5 | Analogy analysis | Map source/target roles, shared structure, limits, and unsupported mappings. |
| 6 | Working-memory reference resolution | Resolve "that", "this", "the first one", branch returns, and active topic anchors. |
| 7 | Working Reasoning Set | Hold retrieved concepts/propositions together for grounded comparison. |
| 8 | Multi-concept retrieval | Return a reviewed concept set without synthesizing by default. |
| 9 | Single-concept retrieval | Answer from one approved local concept or substrate record. |
| 10 | Local-model consent | Ask before local model execution when substrate is insufficient. |
| 11 | Provider consent gate | Ask before provider/API support; never automatic. |

## Important Arbitration Rule

Working memory may run before or alongside dedicated routes to resolve context, but it must yield the final answer to a higher-priority route when the resolved turn is contradiction, analogy, missing-evidence reasoning, WRS comparison, or an explicit topic change.

Examples:

- "Is that inconsistent?" resolves "that" from memory, then yields to contradiction analysis.
- "Where does that analogy break?" resolves the prior analogy, then yields to analogy analysis or a constrained memory continuation.
- "What evidence is missing?" with no history is standalone missing-evidence reasoning, not a memory follow-up.
- "What is blood pressure?" overrides stale photosynthesis context.

## Route Contracts

### Safety

- Entry conditions: every turn.
- May intercept: any request that would violate hard invariants.
- Must yield to: no route if invariant violation is present.
- State read: request metadata and payload safety fields.
- Ephemeral state update: none.
- Side effects allowed: none.
- Required output fields: all safety booleans.
- Overlay trace: safety metadata completeness and behavioral safety.
- Regression protection: payload safety completeness tests.

### Explicit User Command

- Entry conditions: explicit consent/refusal, mode switch, memory approval/rejection command, direct "ask GPT" command.
- May intercept: yes/no when a pending action exists; explicit mode controls.
- Must yield to: safety.
- State read: pending action, mode, history.
- Ephemeral state update: pending action match/clear.
- Side effects allowed: only operator-approved action in that mode; default conversation remains no-write.
- Overlay trace: command type and pending action status.

### Social Conversation

- Entry conditions: greetings, thanks, compliments, acknowledgements, jokes, pure cancellations.
- May intercept: pure social turns.
- Must yield to: explicit cognitive command mixed into the social turn, e.g. "okay, continue explaining photosynthesis."
- State read: minimal history.
- Ephemeral state update: none.
- Side effects allowed: none.
- Overlay trace: communication act and safe-no-route decision.

### Contradiction Analysis

- Entry conditions: contradiction/conflict/inconsistency prompts, "can both be true", contradictory claim pairs, contradiction follow-ups.
- May intercept: prompts with pronouns when contradiction intent is explicit.
- Must yield to: safety and explicit commands.
- State read: current prompt and relevant prior claims.
- Ephemeral state update: extracted claims, qualifiers, polarity, scope, timeframe, classification.
- Side effects allowed: none.
- Overlay trace: claims, classification, missing evidence, reasoning trace.
- Regression protection: contradiction vs working-memory overlap tests.

### Analogy Analysis

- Entry conditions: "like", "analogy", "what works and what breaks", source/target mapping prompts, analogy follow-ups.
- May intercept: prompts with "that" when they reference a prior analogy.
- Must yield to: safety, explicit commands, contradiction.
- State read: prompt and prior analogy answer when present.
- Ephemeral state update: source, target, mapped roles, mapped processes, shared structure, limits.
- Side effects allowed: none.
- Overlay trace: source/target, roles, limitations, rejected mappings.
- Regression protection: analogy vs WRS overlap tests.

### Working Memory

- Entry conditions: pronouns, "tell me more", "why", "give an example", "return to the first topic", "go back to planning", "continue".
- May intercept: generic context-dependent follow-ups with valid recent context.
- Must yield to: contradiction, analogy, explicit topic changes, standalone WRS/missing-evidence prompts, explicit entity lookup.
- State read: bounded recent history and anchor records.
- Ephemeral state update: active topic, active entities, active route, branch order, resolved/rejected references, confidence.
- Side effects allowed: none.
- Overlay trace: CognitiveEpisode.
- Regression protection: orphan, stale-anchor, branch-return, topic-override tests.

### Working Reasoning Set

- Entry conditions: multi-concept comparison, missing-evidence reasoning, "what common pattern", "how does X relate to Y".
- May intercept: multi-concept prompts when no higher-priority contradiction/analogy route applies.
- Must yield to: contradiction, analogy, working-memory follow-up that is purely conversational.
- State read: approved concepts, propositions, graph-support summaries.
- Ephemeral state update: retrieved concepts/propositions, bridge, uncertainty, missing evidence.
- Side effects allowed: none.
- Overlay trace: WRS details and rejected propositions.

### Multi-Concept Retrieval

- Entry conditions: two or more concepts/entities and no WRS-ready reasoning instruction.
- May intercept: retrieval-set review prompts.
- Must yield to: WRS, analogy, contradiction.
- State read: approved concept index.
- Side effects allowed: none.
- Overlay trace: seeds, retrieval set quality, duplicate suppression.

### Single-Concept Retrieval

- Entry conditions: direct local concept lookup.
- May intercept: explicit entity lookup even if stale context exists.
- Must yield to: contradiction/analogy/WRS when prompt asks for relation or comparison.
- State read: approved concept store and legacy substrate.
- Side effects allowed: none.
- Overlay trace: matched concepts and confidence.

### Local-Model Consent

- Entry conditions: local substrate insufficient and local model would help.
- May intercept: unknown local questions.
- Must yield to: any sufficient substrate route.
- State read: model registry and route lane metadata.
- Side effects allowed: no model execution unless explicitly requested.
- Overlay trace: lane, model, support identifier, offer status.

### Provider Consent Gate

- Entry conditions: user explicitly approves provider/API support after being asked.
- May intercept: no prompt automatically.
- Must yield to: all local sufficient routes unless user explicitly requests provider.
- State read: compact support packet only.
- Side effects allowed: provider call only after explicit per-turn approval.
- Overlay trace: provider offer/approval status.

## Payload Requirements

Every route payload must include explicit safety fields:

- `provider_calls_performed`
- `web_search_performed`
- `training_performed`
- `fine_tuning_performed`
- `weight_update_performed`
- `canonical_write_performed`
- `noncanonical_write_performed`
- `graph_write_performed`
- `replay_write_performed`
- `autonomous_action_performed`
- `scheduler_action_performed`
- `hyb1_promoted`
- `model_b_replaced`

Missing metadata is a diagnostic defect even if behavior is safe. The shared conversation finalizer fills safe defaults and reports the filled fields in Developer Overlay.

## Developer Overlay Requirements

The overlay must expose:

- communication act and intent
- candidate routes and precedence
- selected route and rejected routes
- yield/rejection reasons
- CognitiveEpisode state
- WRS, contradiction, analogy traces when present
- natural renderer transformations
- safety metadata completeness

Normal conversation must not expose these internals.


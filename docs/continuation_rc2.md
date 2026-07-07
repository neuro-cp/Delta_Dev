# DELTA RC2 Continuation

RC2 Part I reframes DELTA as a conversational cognitive operating system.
Conversation is the primary product surface; the governed runtime remains the
engine underneath it.

Current UI route:

```powershell
.\.venv311\Scripts\python.exe .\DELTA.py
```

Default tab:

- Conversation

Advanced tab:

- Advanced / Operator Console

Visible modes:

- Conversation
- Memory Mode
- Research
- Evidence Review
- Investigation
- Replay
- Developer
- Diagnostics

Locked invariant:

DELTA must be conversational-first and useful to regular people by default.
Governed cognitive capabilities are exposed through routing or explicit modes,
not forced into ordinary conversation.

Safety state:

- no provider calls
- no web search
- no training
- no fine tuning
- no weight updates
- no provider authority changes
- no canonical writes
- no autonomous actions
- no scheduler activation
- Model B unchanged
- HYB1 dormant

Current RC2 increment:

- Conversation mode now selects a local model lane from the existing local
  model registry (`phi4`, `qwen`, `llama`, `mistral`, `phi3` aliases when
  available) based on task intent.
- Local model lane selection is advisory by default; the RC2 UI does not load
  or execute a model unless a future explicit gate enables that.
- Simple general questions such as sky color, water color, and fire now receive
  conversational local answers instead of the old placeholder.
- Unknown or low-confidence questions offer a gated supporting-information
  path. Web/GPT/provider calls remain off unless explicitly approved in a
  future gate.
- Useful answers can be remembered only by clicking `Remember Last Useful
  Answer` or typing the exact phrase `remember this useful answer`.
- Useful-answer memory writes go only to the local RC1 noncanonical experiment
  store. They are not canonical memory, not training, and not model-weight
  updates.
- The earlier RC1 local proposition store still exists behind Advanced mode,
  but the conversational learning loop now uses the RC2 developmental concept
  store.

Developmental concept formation increment:

- Conversation mode maintains short-term in-memory session history across turns.
- Session history is passed to routing as a compact recent-turn window and is
  not persisted unless the user explicitly keeps a concept.
- Local model lane routing now exposes:
  - Everyday Conversation Lane
  - Coding / Technical Lane
  - Reasoning / Analysis Lane
  - Planning Lane
  - Vision Lane
  - Concept Extraction Lane
  - Contradiction Detection Lane
- GPT/API escalation is consent-gated. Typing `ask gpt` produces a compact
  support-packet preview only; no API call is made.
- Useful answers become candidate concepts, not raw answer memories.
- Approved concepts are stored in separated noncanonical memory stores:
  conversation, personal, and knowledge. Default concept storage is knowledge
  memory unless the user indicates the item is personal.
- The UI keeps the same layout. `Keep This Concept` stores the current concept;
  `not now`, `discard`, or `forget after this chat` leave it in session only.
- RC2 developmental memory can be cleared only with
  `DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE`.

Developmental learning lifecycle:

```text
Conversation
-> Candidate Concept
-> Operator Approval
-> Knowledge Graph
-> Replay
-> Consolidation
-> Curriculum
-> Competency Tests
-> Training Packet
-> Distillation
-> Better Base Model
```

Invariant:

Neural training is a graduation event, not a day-to-day learning mechanism.
DELTA primarily learns through governed concept formation, operator approval,
knowledge graph integration, replay, consolidation, curriculum construction,
and competency testing.

Current recommendation:

Use RC2 as the primary UI for regular interaction. Use Advanced / Operator
Console for evidence ingestion, proposition approval, replay, rollback,
diagnostics, and operational observation.

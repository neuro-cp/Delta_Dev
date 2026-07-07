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
- The local noncanonical experiment store can be cleared from the UI only with
  the exact confirmation phrase `DELETE_RC1_LOCAL_NONCANONICAL_STORE`.

Current recommendation:

Use RC2 as the primary UI for regular interaction. Use Advanced / Operator
Console for evidence ingestion, proposition approval, replay, rollback,
diagnostics, and operational observation.

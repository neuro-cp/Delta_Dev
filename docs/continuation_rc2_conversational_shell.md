# RC2 Conversational Shell Continuation

RC2 adds a conversation-first UI layer over the RC1 governed operator console.
The RC1 substrate remains intact and selectable through modes.

Locked product invariant:

DELTA must be conversational-first and useful to regular people by default.
The governed cognitive runtime remains the backend, but evidence review,
substrate memory, replay, contradiction analysis, approval workflows, and
diagnostics should be reached through intelligent routing or explicit modes.
Regular users should not need to understand substrate internals to get value
from DELTA.

Current UI route:

```powershell
.\.venv311\Scripts\python.exe .\DELTA.py
```

Primary modes:

- Conversation
- Ask Substrate
- Evidence Review
- Review Mode
- Memory Mode
- Contradiction Check
- Replay
- Failure Log
- Diagnostics
- Research Analyst
- Frontier App Assistant

Safety state:

- no provider calls
- no web search
- no training
- no canonical writes
- no autonomous actions
- no production routing
- HYB1 remains dormant
- Model B remains unchanged

Interpretation:

RC2 is not a trained general model. It is a conversational shell and mode router
that can use deterministic local conversation scaffolding, the approved
noncanonical substrate, and gated escalation plans. Provider, web, and large
model routes remain disabled until a separate approval path exists.

Recommended review:

Use Conversation mode for ordinary interaction, Evidence Review and Memory Mode
for teaching DELTA local facts, Ask Substrate for approved knowledge, and
Contradiction Check for conflicts. Record missing capabilities as operational
observations rather than adding speculative architecture.

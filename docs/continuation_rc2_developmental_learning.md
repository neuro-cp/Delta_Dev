# RC2 Developmental Concept Formation Continuation

Current branch: `codex/delta-cognitive-core`

RC2 now treats conversation as the primary interface and governed cognition as
the engine underneath it.

Implemented developmental loop:

```text
normal chat
-> short-term session context
-> local model lane selection
-> useful answer
-> candidate concept
-> operator approval
-> noncanonical concept memory
-> concept graph / replay / contradiction check
-> later retrieval in chat
```

Important user-facing commands:

- `keep this concept` stores the latest candidate concept noncanonically.
- `not now`, `discard`, or `forget after this chat` leave the candidate in
  session context only.
- `ask gpt` shows a compact provider support-packet preview only. It does not
  call GPT/API automatically.
- `DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE` clears the RC2 developmental concept
  memory store.

Memory separation:

- Conversation memory: in-process session history, not persisted by default.
- Personal memory: noncanonical user/project preference store.
- Knowledge memory: noncanonical general concept store and default target.

Safety invariants:

- no training
- no fine-tuning
- no weight updates
- no model artifact creation
- no canonical writes
- no autonomous learning
- no provider/API calls by default
- no web calls by default
- no autonomous actions
- no schedulers
- no Model B replacement
- no HYB1 promotion

Developmental invariant:

Neural training is a graduation event, not a day-to-day learning mechanism.
DELTA primarily learns through governed concept formation, operator approval,
knowledge graph integration, replay, consolidation, curriculum construction,
and competency testing.

Next useful review:

Run the UI and exercise:

1. Ask `What is fire?`
2. Ask `What did I just ask?`
3. Click `Keep This Concept` or type `keep this concept`
4. Ask `Tell me about fire`
5. Ask a low-confidence question such as
   `What is the relation between Avogadro's number and quantum field theory?`
6. Type `ask gpt`
7. Verify DELTA shows a compact packet preview and performs no provider call.

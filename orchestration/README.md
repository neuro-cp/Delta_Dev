# Orchestration Layer

This package provides a thin cognitive loop that sits above the existing DELTA
runtime, recall, learning, and execution-governance surfaces.

## Core loop

```text
Inquiry
→ Semantic interpretation
→ Task typing
→ Decomposition
→ Constraint filtering
→ Route candidate building
→ Confidence scoring
→ Arbitration
→ Execution
→ Evaluation
→ Strategy extraction
→ Optional learning handoff
```

## Architectural constraints

- no runtime mutation
- no execution bypass
- no hidden authority
- no direct dependence on region / population internals
- deterministic tie-breaking
- duck-typed adapters for external surfaces

## Primary entry point

- `orchestration.loop.cognitive_loop.CognitiveLoop`

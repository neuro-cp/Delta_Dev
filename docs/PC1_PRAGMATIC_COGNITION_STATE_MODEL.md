# PC1 Pragmatic Cognition State Model

PC1 is a conversation-scoped, advisory layer for interpreting what the human most likely means before specialist cognition is selected.

## Core Objects

- `PragmaticFrame`: one-turn pragmatic interpretation.
- `OperatorGoalHypothesis`: inferred practical goal, never hidden fact.
- `ImmediateIntent`: current requested operation.
- `ImpliedConstraint`: inferred constraint from context or wording.
- `ScopeBinding`: subject/dimension/condition/timeframe binding.
- `PerspectiveBinding`: whose perspective is being applied.
- `MixedJudgment`: simultaneous judgments across dimensions.
- `CooperativeInterpretation`: preferred human-centered interpretation.
- `AlternativeInterpretation`: rejected plausible interpretation.
- `PracticalResponseGoal`: what the answer should help accomplish.
- `ResponseShape`: expected answer form.
- `PragmaticConfidence`: drivers and weak points.
- `AmbiguityAssessment`: unresolved ambiguity and clarification need.
- `PragmaticEvidence` / `PragmaticCounterEvidence`: evidence for and against interpretation.
- `PC1Episode`: shadow-mode wrapper for frame plus optional response review.

## Authority

All PC1 objects are advisory only. They cannot authorize, execute, persist, approve, or override governance.

## Lifecycle

Default lifecycle is current conversation or current shadow evaluation only. No PC1 object is persisted as memory by default.

## Serialization

All state objects serialize with `as_dict()` for reports, benchmark traces, and Developer Overlay candidates.


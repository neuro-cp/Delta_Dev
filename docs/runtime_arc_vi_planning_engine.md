# Runtime ARC VI Planning Engine

ARC VI planning estimates which cognitive capabilities and resources would be
needed for a goal.

Planning includes:

- capability analysis
- resource estimates
- deliberation strategy
- evidence requirements
- review load estimate
- confidence constraints

The capability plan routes through the existing capability registry where
possible, but it grants no new authority. Provider eligibility remains disabled
without a future explicit gate.

The deliberation strategy is a planning artifact only. It may list lookup,
graph traversal, multi-hop reasoning, hypothesis generation, reflection, and
review, but it does not trigger those stages automatically.

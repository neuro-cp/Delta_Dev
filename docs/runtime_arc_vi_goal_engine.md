# Runtime ARC VI Goal Engine

The ARC VI goal engine creates deterministic `ExecutiveGoal` objects.

Each goal records:

- stable goal id
- title and description
- priority
- owner and requester
- constraints
- dependency hints
- planning-only status
- execution flag

Every generated goal is non-executing by default. The `execution_performed`
field remains `False`, and the goal includes `no_execution`,
`no_provider_authority`, `no_memory_mutation`, and `review_required`
constraints.

Goal decomposition produces planned-only `ExecutiveTask` records with explicit
dependencies. These records are suitable for review and explanation, not
execution.

# Runtime ARC VI Constraint Engine

The ARC VI constraint engine determines what prevents a planned executive goal
from becoming an executed operation.

Current execution blockers:

- provider authority disabled
- autonomous execution disabled
- scheduler disabled
- memory mutation disabled

The constraint engine reports policy, safety, resource, knowledge, confidence,
time, and review requirements. It can request review, more evidence, owner
approval, or overwatch in future phases, but it cannot bypass current gates.

Constraint evaluation is deterministic and report-only.

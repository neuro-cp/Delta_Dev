# Runtime ARC VI Decision Graph

ARC VI creates a transient executive decision graph for each planned goal.

The graph links:

- goal node
- task nodes
- risk node
- decomposition edges

The graph is transient and review-oriented. It is not persisted as canonical
knowledge, not inserted into recall, and not used to mutate memory.

The graph exists to answer questions such as:

- Why were these tasks chosen?
- What depends on what?
- Where are the execution blockers?
- What must be reviewed before anything can proceed?

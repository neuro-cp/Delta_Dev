# DELTA ARC II Knowledge Substrate Architecture

ARC II defines reviewable semantic structures that future reasoning and learning
can operate upon.

```mermaid
flowchart TD
  A["Raw Document"] --> B["Observation"]
  B --> C["Evidence"]
  C --> D["Entity"]
  C --> E["Relationship"]
  D --> F["Concept"]
  E --> F
  F --> G["Hypothesis"]
  F --> H["Procedure"]
  H --> I["Generalized Knowledge (future)"]
```

ARC II stops before autonomous integration. Objects are reviewable,
provenance-bearing, and rollback-capable.


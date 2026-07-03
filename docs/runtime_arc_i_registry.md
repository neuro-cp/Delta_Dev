# DELTA ARC I Kernel Registry

The Cognitive Capability Registry lets the kernel ask which manager handles a
capability instead of hardcoding direct calls.

```mermaid
flowchart TD
  Q["Request"] --> R["Capability Registry"]
  R --> A["Reasoning Manager"]
  R --> B["Learning Manager"]
  R --> C["Review Manager"]
  R --> D["Safety Manager"]
```

Dangerous capabilities such as provider calls, training, action execution, and
scheduler activation remain inactive.


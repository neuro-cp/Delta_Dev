# DELTA ARC I Kernel Event Flow

```mermaid
flowchart LR
  A["Subsystem A"] --> B["Kernel Event"]
  B --> C["Kernel Dispatcher"]
  C --> D["Subsystem B"]
  D --> E["Audit Record"]
```

Events are deterministic review artifacts in ARC I. They do not grant mutation
authority.


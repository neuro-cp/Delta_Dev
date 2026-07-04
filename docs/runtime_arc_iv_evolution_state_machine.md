# DELTA ARC IV Evolution State Machine

```mermaid
flowchart LR
  A["draft"] --> B["review"]
  B --> C["approved"]
  C --> D["overwatch_allowed"]
  D --> E["owner_override"]
  E --> F["simulation_complete"]
  F --> G["ready_to_integrate"]
```

`ready_to_integrate` is not a live write.


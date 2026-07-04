# Runtime ARC VII Investigation Workflow

ARC VII introduces structured investigation.

Flow:

```mermaid
flowchart TD
    A["Question"] --> B["Problem definition"]
    B --> C["Knowledge review"]
    C --> D["Gap analysis"]
    D --> E["Investigation plan"]
    E --> F["Evidence collection plan"]
    F --> G["Reasoning plan"]
    G --> H["Findings"]
    H --> I["Confidence assessment"]
    I --> J["Review"]
    J --> K["Recommendations"]
```

Findings are separate from durable knowledge. Evidence collection is planned
only. No browsing, provider calls, knowledge mutation, or memory mutation
occurs.

# DELTA ARC I Kernel Architecture

Runtime ARC I introduces an orchestration-only Cognitive Kernel.

```mermaid
flowchart TD
  K["Cognitive Kernel"]
  K --> E["Experience Manager"]
  K --> EV["Evidence Manager"]
  K --> R["Recall Manager"]
  K --> RS["Reasoning Manager"]
  K --> L["Learning Manager"]
  K --> RV["Review Manager"]
  K --> I["Integration Manager"]
  K --> S["Safety Manager"]
```

The kernel coordinates existing runtime surfaces. It does not train, call
providers, mutate memory, execute actions, promote HYB1, or start schedulers.


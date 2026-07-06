# RC1 Failure Classification

## Classes
- `bug`: incorrect deterministic behavior or testable defect
- `usability`: operator confusion or unnecessary friction
- `governance`: approval, authority, audit, or invariant concern
- `reasoning`: weak inference, synthesis, contradiction handling, or uncertainty behavior
- `retrieval`: missed, irrelevant, or poorly ranked evidence
- `replay`: replay ordering, consolidation review, or reproducibility issue
- `provenance`: missing, weak, or unclear source trace
- `operator_workflow`: review, rollback, approval, or triage workflow issue
- `documentation`: operator guide, report, or continuation gap
- `performance`: latency, scale, resource, or throughput issue

## Priorities
- `P0`: safety invariant breach or hidden authority risk
- `P1`: blocks operational workflow or corrupts evidence
- `P2`: material quality issue with workaround
- `P3`: minor friction or documentation improvement

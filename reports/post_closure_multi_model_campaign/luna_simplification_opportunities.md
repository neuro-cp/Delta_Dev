# LUNA-Style Simplification Opportunities

| ID | Opportunity | Evidence | Benefit | Timing |
| --- | --- | --- | --- | --- |
| LUNA-01 | Extract `LiveTurnCoordinator` from `DELTA.py` | UI worker queue, control queue, session result commit, and input gating are now a coherent subsystem inside a 2,813-line UI file. | Smaller UI surface; direct unit testing of ordering and control boundaries. | NEXT |
| LUNA-02 | Introduce a typed `PendingOperatorAction` envelope | Promotion approval and local-model approval both need ID, status, target, expiration, authority, and correlation but use separate dict shapes. | Central correlation semantics and fewer phrase-specific branches. | NEXT |
| LUNA-03 | Split live bridge into transport, action gating, and response composition | The 1,260-line bridge owns Wikipedia transport, controls, promotion, local models, developmental flow, controller sync, and rendering. | Clear side-effect boundaries and more focused tests. | NEXT |
| LUNA-04 | Publish model registry counts by category | 15 registry entries represent 10 unique specs, 5 usable specs, and 5 aliases. | Accurate self-model and operator expectations. | NEXT |
| LUNA-05 | Move route-specific prose into declarative policy tables where stable | The 2,781-line router has broad phrase-specific routing and rendering responsibilities. | Easier coverage review without a risky global rewrite. | LATER |
| LUNA-06 | Treat reports as append-only campaign evidence, not runtime components | The repository has substantial milestone/report infrastructure around a smaller active spine. | Improves discovery and avoids report-driven architecture claims. | LATER |

None of these proposals requires weaker governance, new web surfaces, or automatic persistence.

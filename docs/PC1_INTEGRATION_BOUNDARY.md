# PC1 Integration Boundary

PC1 sits between discourse cognition and route arbitration in the future architecture:

Raw language -> Discourse Cognition Bridge -> PC1 Pragmatic Cognition -> Route Arbitration -> RC2/RC3/RC4/RC5.

For the calibrated activation phase, PC1 may run as a bounded pragmatic pre-router when `DELTA_PC1_ENABLED` is enabled.

The gate defaults to enabled in the local UI so operator pilots can continue without repeated manual toggles. Set `DELTA_PC1_ENABLED=false` to restore the frozen RC4/RC5 discourse path.

It may:

- Build pragmatic frames.
- Compare literal and cooperative interpretations.
- Score response usefulness.
- Generate benchmark and adversarial reports.
- Preempt generic specialist routing only for high-confidence pragmatic governance cases such as mixed judgments, scope boundaries, rollback/recovery homonyms, and practical freeze-readiness recommendations.

It may not:

- Expand RC4 or RC5 authority.
- Call providers.
- Persist memory.
- Override RC4 or RC5.
- Approve proposals.
- Execute work.
- Interpret hidden intent as fact.
- Treat PC1 activation as RC4/RC5 freeze evidence by itself.

Activation status:

- PC1 calibrated state: `bounded_pre_router_capable`.
- UI route: `pc1_bounded_pragmatic_pre_router`.
- Rollback gate: `DELTA_PC1_ENABLED=false`.
- Safety posture: no provider calls, no memory writes, no autonomous action, no production authority expansion.

# Continuous Runtime Engineering Notebook

- Finding: Existing DELTA 1.2 wake cycle was suitable for bounded cognition but not a central UI service controller.
- Decision: Add one controller that owns lifecycle/event envelopes while reusing 1.2 queue/journal and 1.6 self-model.
- Model routing: actual registry has multiple GGUF models plus aliases; use lane selection and serial ProviderManager policy, not hardcoded two-model assumptions.
- Wikipedia: preserve text-only one-page-per-query policy; continuous controller performs no autonomous retrieval.
- Pathology PID-CR01: duplicate state surfaces repaired by controller snapshot and UI status synchronization.
- Self-development: observed UI/runtime mismatch, generated sandbox-only repair hypotheses, validated controller integration, and stopped at promotion proposal.
- Readiness: bounded controller validation is useful, but live developmental operation is not yet proven without a real long-horizon UI/model/retrieval campaign.
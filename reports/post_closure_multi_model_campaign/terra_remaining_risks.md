# TERRA Remaining Risks

- A full 373-scenario deterministic campaign remains fixture-based for Wikipedia and intentionally does not invoke real models.
- The desktop worker queue preserves UI responsiveness, but it does not cancel a request already issued to Wikipedia or a local model. Controls take effect at the next bounded turn boundary.
- There is no multi-hour or multi-day operator trace yet. CPU, working set, GPU memory, queue depth, notification volume, and residency have not been observed under sustained human interruption.
- Registry counts still distinguish neither aliases nor unusable models in the primary controller count.
- The consent response contains redundant wording in the observed UI. It is truthful but noisy.
- Session state remains intentionally ephemeral; restart continuity is only as strong as the pre-existing runtime reconciliation layer, not a durable pending-action store.

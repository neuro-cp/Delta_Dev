# Runtime V1.3 Evidence-Support Audit

Final decision: `PROCEED_USAGE_GATE_REFINEMENT`

Evidence support appears to behave as corpus support rather than query-context support: noisy concepts can still be marked usable when their attention classification is Core/Supporting and query specificity is weak.

- noisy reasoned concepts: `12`
- high-attention noisy reasoned concepts: `12`

## Attention Classifications

- `Core`: `3`
- `Supporting`: `9`

## Noise Used By Variant

- `baseline_reference`: `12`
- `usage_gate_standard`: `12`
- `strict_context_usage_gate`: `6`
- `citation_context_usage_gate`: `8`
- `conservative_recurrence_strict_gate`: `6`
- `tiebreaker_recurrence_strict_gate`: `6`
- `metadata_recurrence_strict_gate`: `6`

`PROCEED_USAGE_GATE_REFINEMENT`

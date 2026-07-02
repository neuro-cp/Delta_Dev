# Runtime V1.3 Resolution Suite

Final decision: `ACCEPT_RUNTIME_V13_REFINED_USAGE_GATE`

Make the accepted refined usage gate the default and keep activation recurrence disabled.

## Variant Table

| Variant | Accepted | Noise Used | Reasoning Drift | Attention Precision | Retrieval Recall | Mean Expected Rank | Mean Noise Above |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_reference | `False` | `12.0` | `5.0` | `0.55` | `0.5333` | `10` | `9.7083` |
| usage_gate_standard | `True` | `12.0` | `5.0` | `0.55` | `0.5333` | `10` | `9.7083` |
| strict_context_usage_gate | `False` | `6.0` | `3.0` | `0.7333` | `0.5333` | `10` | `9.7083` |
| citation_context_usage_gate | `True` | `8.0` | `5.0` | `0.5833` | `0.5333` | `10` | `9.7083` |
| conservative_recurrence_strict_gate | `False` | `6.0` | `3.0` | `0.7833` | `0.5667` | `7.2174` | `7.0417` |
| tiebreaker_recurrence_strict_gate | `False` | `6.0` | `3.0` | `0.7333` | `0.5333` | `9.8261` | `9.5417` |
| metadata_recurrence_strict_gate | `False` | `6.0` | `3.0` | `0.7333` | `0.5333` | `10` | `9.7083` |

## Evidence-Support Audit

Evidence support appears to behave as corpus support rather than query-context support: noisy concepts can still be marked usable when their attention classification is Core/Supporting and query specificity is weak.

## Variant Acceptance

### baseline_reference

Preserved V1.2 baseline reports.

- failed gates: `none`
- raw output: `reports\runtime_v13_resolution_suite_raw\baseline_reference`

### usage_gate_standard

Accepted usage gate, activation recurrence disabled.

- failed gates: `none`
- raw output: `reports\runtime_v13_resolution_suite_raw\usage_gate_standard`

### strict_context_usage_gate

Usage gate treats evidence_support as query-contextual only with specific overlap.

- failed gates: `planning_score_not_regress`
- raw output: `reports\runtime_v13_resolution_suite_raw\strict_context_usage_gate`

### citation_context_usage_gate

Middle-ground usage gate requiring stronger contextual support for citation-like use.

- failed gates: `none`
- raw output: `reports\runtime_v13_resolution_suite_raw\citation_context_usage_gate`

### conservative_recurrence_strict_gate

Conservative activation recurrence plus strict contextual usage gate.

- failed gates: `planning_score_not_regress, planning_core_coverage_not_regress, response_core_coverage_not_regress`
- raw output: `reports\runtime_v13_resolution_suite_raw\conservative_recurrence_strict_gate`

### tiebreaker_recurrence_strict_gate

Tiebreaker activation recurrence plus strict contextual usage gate.

- failed gates: `planning_score_not_regress`
- raw output: `reports\runtime_v13_resolution_suite_raw\tiebreaker_recurrence_strict_gate`

### metadata_recurrence_strict_gate

Recurrence metadata only plus strict contextual usage gate.

- failed gates: `planning_score_not_regress`
- raw output: `reports\runtime_v13_resolution_suite_raw\metadata_recurrence_strict_gate`

## Live Behavior

- `usage_gate_remains_enabled`: `True`
- `activation_recurrence_default_enabled`: `False`
- `selected_refinement_enabled_by_default`: `True`

`ACCEPT_RUNTIME_V13_REFINED_USAGE_GATE`

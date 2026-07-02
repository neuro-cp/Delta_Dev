# Runtime V1.2 Activation Failure Audit

- campaign: `.tmp\experiments\phaseA_architecture_graduation\overnight_3000`
- read-only verified: `True`
- baseline activation limit: `10`
- audit activation limit: `50`
- cases audited: `10`
- expected concepts audited: `24`
- sparse top-20 noise activations: `40`

## Miss Taxonomy

| Category | Count |
| --- | ---: |
| not_retrieved | `1` |
| reached_working_memory | `7` |
| retrieved_but_pruned_by_attention | `9` |
| retrieved_but_ranked_too_low | `7` |

## Recommendation

Diagnose activation ranking before changing attention; expected concepts are missing or too low in the real-store candidate list.

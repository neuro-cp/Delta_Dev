# Phase 25 Extraction Boundary Audit

Deterministic replay audit of LearningEngine sentence segmentation and candidate filtering. No provider inference, canonical promotion, or store mutation was performed.

| Metric | Legacy Filter | Current Filter |
| --- | ---: | ---: |
| Accepted candidates | 35 | 10 |
| Acceptance rate | 0.3723 | 0.1064 |
| Prompt artifact rate | 0.4 | 0.0 |
| Incomplete rate | 0.3143 | 0.0 |
| Fragment rate | 0.7143 | 0.0 |
| Multi-claim rate | 0.2 | 0.1 |
| Estimated precision | 0.2857 | 1.0 |
| Estimated recall | 1.0 | 1.0 |

## Interpretation

The deterministic filter rejects prompt scaffolding, answer scaffolding, task imperatives, dangling conditionals, incomplete propositions, and formatting remnants before they enter semantic consolidation. Complete reusable propositions continue to pass.

This is an extraction-boundary quality fix only. It does not rewrite candidate text, call a model, change governance, or alter promotion thresholds.

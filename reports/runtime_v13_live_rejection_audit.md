# Runtime V1.3 Live Rejection Audit

Final decision: `MOVE_SIGNAL_TO_ATTENTION_GATING`

## Baseline vs Rejected Prototype Summary

| Metric | Baseline | Rejected Prototype |
| --- | ---: | ---: |
| read_only_verified | `True` | `True` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| retrieval_precision | `0.16` | `0.17` |
| retrieval_recall | `0.5333` | `0.5667` |
| attention_precision | `0.55` | `0.4172` |
| attention_recall | `0.4333` | `0.4667` |
| noise_used_in_reasoning | `12.0` | `24.0` |
| reasoning_drift_cases | `5.0` | `8.0` |
| expected_outside_top10 | `8` | `7` |
| expected_outside_top20 | `6` | `4` |
| mean_expected_rank | `10` | `7.1739` |
| mean_noise_above_expected | `9.7083` | `7` |

## Acceptance Criteria Failures

- `noise_used_in_reasoning_not_increase`

## Per-Case Noise And Attention Deltas

| Case | Noise Delta | Attention Precision Delta | Reasoning Drift Before | Reasoning Drift After |
| --- | ---: | ---: | --- | --- |
| causal_industrial_failure | `1` | `-0.0278` | `True` | `True` |
| contradictory_evidence | `1` | `0.0` | `True` | `True` |
| logistics_proxy_planning | `1` | `-0.5` | `False` | `True` |
| multi_step_failure_revision | `0` | `0.0` | `True` | `True` |
| planning_failed_assumption | `1` | `-0.5` | `False` | `True` |
| policy_audit_conflict | `1` | `-0.5` | `False` | `True` |
| resource_allocation_shelters | `0` | `0.0` | `True` | `True` |
| risk_uncertainty_planning | `7` | `0.2` | `True` | `True` |
| sparse_violin_tuning | `0` | `0.0` | `False` | `False` |
| unsupported_recipe | `0` | `0.0` | `False` | `False` |

## Newly Used Noisy Concepts

- `48c454a5-6362-4533-a53e-b6d6f9c19a00` used as noise in `1` case(s)
- `011d4f3b-e7d2-4865-9fe3-b269795e07cb` used as noise in `1` case(s)
- `0121143f-0779-4965-9405-2e7b3eabcd05` used as noise in `1` case(s)
- `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` used as noise in `1` case(s)
- `5894bef8-228f-4466-9152-cf7dfec7fa4e` used as noise in `1` case(s)
- `0ada7d73-b196-40cc-b6bb-031ac1eaa8cd` used as noise in `1` case(s)
- `16ce389d-1c43-4d03-94e3-f16ad8259cbc` used as noise in `1` case(s)
- `6457f783-957c-4e69-95bb-bacf18f6fd32` used as noise in `1` case(s)
- `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` used as noise in `1` case(s)
- `ad599dfe-ddbd-4689-ad43-4dc8249fdab1` used as noise in `1` case(s)
- `d9ba0c9f-f458-4512-a0e3-40892ef333b6` used as noise in `1` case(s)
- `fec7285c-8ebf-45ba-8197-911a515e4e0b` used as noise in `1` case(s)

## Suppressed Or No-Longer-Used Concepts

- `aa6c1ba8-9c57-474c-afa5-7383a4733cae` no longer used in `1` case(s)

## Replacement-Noise Analysis

Recurring-noise suppression removed or demoted some repeat offenders, but the newly opened activation slots were filled by other weak candidates that attention treated as usable.

Cases with noise increase:
- `causal_industrial_failure`
- `contradictory_evidence`
- `logistics_proxy_planning`
- `planning_failed_assumption`
- `policy_audit_conflict`
- `risk_uncertainty_planning`

## Why Isolated Simulation Passed But Live Benchmark Failed

The isolated simulation measured activation rank movement only. In live runtime, the altered activation distribution changed which candidates attention selected and reasoning consumed. Ranking improved, but selected replacement concepts were often noise, doubling noise_used_in_reasoning.

## Recommended Next Experiment

Test recurrence as attention-side diagnostic metadata or a reasoning usage gate, not as direct activation score mutation.

## Experiments Explicitly Rejected

- direct activation-score recurring-noise suppression
- stronger recurrence penalty
- global attention threshold loosening
- learning/governance/promotion changes

`MOVE_SIGNAL_TO_ATTENTION_GATING`

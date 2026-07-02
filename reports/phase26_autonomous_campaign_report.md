# Phase 26 Autonomous Curriculum Validation Campaign

Canonical knowledge was not modified. Each campaign used a fresh isolated store and the existing continuous operator pipeline.

## Executive Summary

- Runs completed: `7` of `7`
- Average promotion score: `0.5546`
- Average projected centrality: `0.2728`
- Promotion eligible concepts: `12`
- Validated concepts: `448`
- Dominant aggregate failure: `unresolved_prediction`

## Experiment Chronology

| Run | Cycles | Profiles | Semantic Growth | Prediction Coverage | Failed Predictions | Avg Promotion Score | Eligible | Validated | Centrality | Dominant Failure |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| broad_balanced_100 | 100/100 | planning,contradiction,causal_reasoning,risk_assessment,resource_allocation | 147 | 0.9112 | 5 | 0.5373 | 2 | 72 | 0.2938 | unresolved_prediction |
| broad_balanced_200 | 200/200 | planning,contradiction,causal_reasoning,risk_assessment,resource_allocation | 314 | 0.8567 | 9 | 0.522 | 1 | 167 | 0.3074 | unresolved_prediction |
| causal_reasoning_100 | 100/100 | causal_reasoning | 43 | 1.0 | 0 | 0.5846 | 2 | 29 | 0.2477 | none |
| causal_reasoning_200 | 104/200 | causal_reasoning | 45 | 0.9836 | 0 | 0.5776 | 2 | 27 | 0.2508 | prompt_artifact |
| contradiction_100 | 100/100 | contradiction | 39 | 0.9298 | 0 | 0.5585 | 1 | 27 | 0.2488 | redundancy |
| planning_100 | 100/100 | planning | 81 | 0.8558 | 0 | 0.5451 | 2 | 44 | 0.2712 | unresolved_prediction |
| planning_200 | 200/200 | planning | 143 | 0.9042 | 0 | 0.5572 | 2 | 82 | 0.2897 | unresolved_prediction |

## Aggregate Survival Curve

| Stage | Count |
| --- | ---: |
| canonical_ready | 0 |
| extracted_candidates | 812 |
| predictions_validated | 865 |
| promotion_candidates | 831 |
| promotion_eligible | 12 |
| semantic_records_evaluated | 928 |
| survived_governance | 865 |
| survived_normalization | 924 |

## Failure Distribution

- `unresolved_prediction`: `80`
- `redundancy`: `53`
- `contradiction`: `30`
- `failed_validation`: `14`
- `incomplete_proposition`: `9`
- `prompt_artifact`: `6`
- `low_composite_score`: `1`

## Lifecycle Distribution

- `Validated`: `448`
- `Candidate`: `371`
- `Reject`: `63`
- `Hold for More Validation`: `28`
- `Promotion Eligible`: `12`
- `Experimental`: `6`

## Provider Usage

- `qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m`: `649` cycles
- `mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m`: `130` cycles
- `meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m`: `125` cycles

## Recommendation

Inspect promotion-eligible concepts manually before any canonical merge. Do not loosen governance; verify provenance and survival first.

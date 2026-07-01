# Phase 14 Governed Training Run - Semantic Extraction

Run ID: `governed_training_20260701T042836Z`

Store: `data/training/phase14_governed_50_semantic_extraction`

This run repeats the 50-cycle governed local-provider training shape after
changing the existing `LearningEngine` to extract reusable semantic claims from
successful provider outputs.

## Summary

| Metric | Previous 50-cycle run | Semantic extraction run |
| --- | ---: | ---: |
| Memories delta | +100 | +100 |
| Relationships delta | +50 | +50 |
| Learning records delta | +50 | +50 |
| Semantic knowledge delta | +1 | +19 |
| Predictions delta | +8 | +19 |
| Contradictions delta | +12 | 0 |
| Learning efficiency | 0.34 | 0.70 |
| Knowledge stability | 0.2941 | 1.0 |

Prediction quality:

| Metric | Previous 50-cycle run | Semantic extraction run |
| --- | ---: | ---: |
| Total predictions | 24 | 35 |
| Supported | 23 | 15 |
| Failed | 0 | 0 |
| Open | 1 | 20 |
| Coverage | 0.9583 | 0.4286 |
| Accuracy | 1.0 | 1.0 |
| Average evidence score | 0.7348 | 0.7267 |

## Observations

- Semantic knowledge growth improved from `+1` to `+19` under the same
  50-cycle training size.
- Contradiction growth dropped from `+12` to `0`.
- The semantic concepts are now contentful provider-output claims, for example:
  - `When prioritizing maintenance jobs the decision to delay...`
  - `Evidence that would make this decision unsafe includes...`
  - `Under uncertainty hospital staffing should be planned...`
  - `When the flu surge invalidates the initial staffing...`
- Prediction generation increased substantially, but many predictions remain
  open at the end of the run.

## Interpretation

This run is the first clear evidence that improving semantic extraction changes
durable knowledge growth. Delta is still not proven to become more generally
capable, but the previous learning-record to semantic-knowledge bottleneck is no
longer dominant at this run size.

The next bottleneck is prediction validation throughput: richer semantic
knowledge generated more predictions than the 50-cycle run could validate.

## Next Gate

Before scaling to long runs:

1. Run 100 cycles with semantic extraction enabled.
2. Track whether semantic knowledge growth remains proportional.
3. Track whether open predictions accumulate faster than validation.
4. If open prediction backlog grows, improve outcome scheduling before 250+
   cycles.

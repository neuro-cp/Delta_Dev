# Phase 14 Governed Training Run - 100 Cycles With Semantic Extraction

Run ID: `governed_training_20260701T043112Z`

Store: `data/training/phase14_governed_100_semantic_extraction`

## Summary

| Metric | Baseline | Final | Delta |
| --- | ---: | ---: | ---: |
| Memories | 16 | 216 | +200 |
| Relationships | 0 | 100 | +100 |
| Learning records | 0 | 100 | +100 |
| Semantic knowledge | 16 | 35 | +19 |
| Predictions | 16 | 35 | +19 |
| Contradictions | 0 | 0 | 0 |
| Goals | 4 | 4 | 0 |

Prediction quality:

| Metric | Final |
| --- | ---: |
| Total predictions | 35 |
| Supported | 15 |
| Failed | 0 |
| Open | 20 |
| Coverage | 0.4286 |
| Accuracy | 1.0 |
| Average evidence score | 0.7267 |

Runtime:

- cycles requested: `100`
- cycles completed: `100`
- elapsed seconds: `80.5033`
- cycles/second: `1.2422`

## Comparison

| Metric | 50 cycles before semantic extraction | 50 cycles with semantic extraction | 100 cycles with semantic extraction |
| --- | ---: | ---: | ---: |
| Semantic knowledge delta | +1 | +19 | +19 |
| Predictions delta | +8 | +19 | +19 |
| Contradictions delta | +12 | 0 | 0 |
| Open predictions | 1 | 20 | 20 |
| Prediction coverage | 0.9583 | 0.4286 | 0.4286 |

## Observations

- Semantic extraction fixed the original learning-record to knowledge conversion
  bottleneck at the 50-cycle scale.
- Extending the same repeated objective set to 100 cycles did not produce more
  latest semantic knowledge than the 50-cycle semantic extraction run.
- Open predictions did not continue to grow after the 50-cycle semantic
  extraction run; the backlog stayed at `20`.
- Contradictions remained bounded at `0`.

## Interpretation

The active bottleneck has shifted again. Semantic extraction works, but repeated
training objectives saturate quickly. Additional cycles over the same objective
set create more memories, relationships, and learning records, but not more
durable latest knowledge.

The next improvement should increase objective diversity and outcome validation,
not raw cycle count.

## Next Gate

Before any 250+ cycle run:

1. Generate a larger, non-repeating objective set.
2. Include explicit outcome observations for open predictions.
3. Require each objective to produce at least one claim not equivalent to prior
   semantic knowledge.
4. Compare 50 diverse cycles against the repeated-objective 100-cycle result.

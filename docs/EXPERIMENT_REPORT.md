# DELTA Experiment Report

## Phase 13: Experimental Validation Campaign

Date: 2026-06-30

Scope: Experience Scaling, stopped at 1000 ticks by operator instruction.

All runs used isolated stores under `.tmp/experiments/phase13/experience_scaling`.
Production Delta state was not modified.

## Experiment 1: Experience Scaling

Question:

Does Delta's cognitive substrate measurably improve as curriculum experience
increases from 100 to 1000 ticks?

Runs:

| Ticks | Completed | Seconds | Ticks/sec | Memories | Learning | Relationships | Semantic | Predictions | Contradictions |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 100 | 8.0725 | 12.3878 | 216 | 100 | 100 | 18 | 30 | 0 |
| 250 | 250 | 26.0045 | 9.6137 | 516 | 250 | 250 | 17 | 30 | 0 |
| 500 | 500 | 78.2182 | 6.3924 | 1016 | 500 | 500 | 17 | 30 | 0 |
| 1000 | 1000 | 263.7511 | 3.7915 | 2016 | 1000 | 1000 | 17 | 30 | 0 |

## Cognitive Metrics

| Ticks | Prediction Accuracy | Prediction Coverage | Open Predictions | Contradiction Pressure | Learning Efficiency | Consolidation Rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 1.0 | 0.5 | 15 | 0.0 | 0.18 | 0.18 |
| 250 | 1.0 | 0.5 | 15 | 0.0 | 0.068 | 0.068 |
| 500 | 1.0 | 0.5 | 15 | 0.0 | 0.034 | 0.034 |
| 1000 | 1.0 | 0.5 | 15 | 0.0 | 0.017 | 0.017 |

## Observations

- Runtime stability was good through 1000 ticks.
- No contradiction growth occurred in this curriculum setup.
- Prediction accuracy stayed at `1.0`, but this did not improve with more
  experience.
- Prediction coverage remained fixed at `0.5`.
- Semantic knowledge plateaued quickly at 17-18 latest records.
- Learning records grew linearly, but consolidation rate fell as ticks
  increased.
- Throughput degraded from `12.3878` ticks/sec at 100 ticks to `3.7915`
  ticks/sec at 1000 ticks.
- Novelty analysis of the 1000-tick curriculum run found average novelty
  `0.1144`, average information gain `0.1577`, average experience utility
  `0.1531`, and prediction pressure rate `0.071`.

## Hypotheses

- The current curriculum prompts generate repeated, low-novelty learning
  pressure after early ticks.
- The current curriculum is capability-varied but information-poor. The
  `worth_remembering_rate` was `0.715`, but this appears driven mostly by
  nominal new-capability labels rather than high information gain.
- Duplicate suppression is preventing semantic explosion, which is good, but
  the system is not converting additional experience into richer knowledge.
- Prediction validation is saturated against bootstrap predictions and is not
  producing enough new evaluated predictions from curriculum experience.
- Repeated JSONL full-store reads likely contribute to the throughput decline.

## Recommendations

1. Do not attempt a 10,000-tick run yet.
2. Add held-out task-performance suites before claiming cognitive improvement.
3. Add novelty and difficulty progression to curriculum runs.
4. Use experience utility, not tick count, as the main curriculum selection
   pressure.
5. Improve prediction generation/validation so new curriculum experience creates
   testable predictions.
6. Profile the 1000-tick run before longer unattended experiments.
7. Reduce repeated full-store reads in runtime hot paths before scaling.

## Scientific Conclusion

The first scaling experiment shows mechanical stability and bounded governance,
but it does not yet show cognitive improvement from additional experience.

Delta accumulated more experience, but prediction quality, prediction coverage,
semantic knowledge, and contradiction pressure were flat from 100 to 1000 ticks.
The strongest evidence is for plateau, not improvement.

The likely upstream cause is low experience utility: the generated curriculum
varied domains but did not deliver enough belief-challenging, prediction-rich,
or information-gaining experiences.

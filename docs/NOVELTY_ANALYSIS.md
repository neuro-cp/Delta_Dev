# DELTA Novelty Analysis

## Purpose

Novelty analysis measures whether an experience is likely to change Delta.
It is an experimental instrument, not a cognitive region.

Dimensions:

| Dimension | Meaning |
| --- | --- |
| Novelty | Difference from prior memory and semantic knowledge |
| Information Gain | Expected effect on beliefs or world model if true |
| Prediction Opportunity | Whether the experience can produce testable expectations |
| Belief Challenge | Whether the experience challenges existing knowledge |
| Surprise | Whether observations mismatch expectations or trusted providers disagree |
| Capability Expansion | Whether the experience requires underused capabilities |
| Generalizability | Whether the experience teaches a reusable pattern |
| Memory Value | Whether the experience is worth retaining |
| Experience Utility | Aggregate estimate of whether Delta should learn from it |

## Phase 13 Measurement

Dataset:

- `.tmp/experiments/phase13/experience_scaling/ticks_1000`
- report: `.tmp/experiments/phase13/experience_scaling/novelty_1000.json`

Summary:

| Metric | Value |
| --- | ---: |
| Average novelty | 0.1144 |
| Average information gain | 0.1279 |
| Average experience utility | 0.1371 |
| Average surprise | 0.0 |
| Prediction pressure rate | 0.071 |
| Invalidation pressure rate | 0.0 |
| New capability rate | 0.715 |
| Worth remembering rate | 0.715 |

## Interpretation

The curriculum was domain-varied but not information-rich.

Most generated tasks were repeated templates at difficulty 1. They touched
different nominal capabilities, but they rarely created prediction pressure,
belief challenge, invalidation pressure, surprise, or high expected information
gain.

This explains the 100-vs-1000 plateau:

- more memories were created
- learning records grew linearly
- semantic knowledge did not grow meaningfully
- prediction coverage did not improve
- contradiction pressure remained zero

## Recommendation

Future curriculum selection should optimize experience utility rather than tick
count. Candidate experiences should be prioritized when they:

- challenge an existing belief
- create surprise by violating high-confidence expectations or exposing
  provider disagreement
- produce a testable prediction
- introduce evidence that can validate or invalidate knowledge
- require a genuinely underdeveloped capability
- generalize beyond the specific prompt

Do not run longer autonomous experiments until average experience utility is
substantially higher than the Phase 13 baseline.

Provider experiments should be evaluated by capability-local experience
utility, not global model ranking. Future local-provider runs should ask:

- Which provider generated high-utility planning experiences?
- Which provider generated high-surprise contradiction or disagreement cases?
- Which provider generated falsifiable predictions?
- Which provider repeated known concepts?

Use `tools/provider_utility_report.py` on generated experience stores to build
provider utility profiles.

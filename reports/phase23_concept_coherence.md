# Phase 23 Concept Coherence Audit

Diagnostic-only audit. No semantic edges were generated, no stores were modified, and no canonical promotion was performed.

## Comparison

| Metric | Phase 20 planning-20 baseline | Formatting-contract run |
| --- | ---: | ---: |
| Concepts evaluated | 64 | 29 |
| Learned concepts evaluated | 48 | 13 |
| Prompt artifact rate, all concepts | 0.25 | 0.1724 |
| Prompt artifact rate, learned concepts | 0.3333 | 0.3846 |
| Incomplete proposition rate, all concepts | 0.4219 | 0.931 |
| Incomplete proposition rate, learned concepts | 0.2292 | 0.8462 |
| Average redundancy, learned concepts | 0.2258 | 0.2069 |
| Average promotion score | 0.5291 | 0.5447 |
| Learned average promotion score | 0.5259 | 0.5515 |
| Learned scores >= 0.56 | 16 | 6 |
| Learned scores >= 0.62 | 1 | 1 |
| Prediction coverage | 0.9394 | 1.0 |
| Prediction accuracy | 1.0 | 1.0 |
| Average shared-evidence neighbors | 1.4062 | 0.7586 |
| Average objective neighbors | 5.1562 | 9.0345 |
| Average prediction links | 0.2344 | 0.5172 |
| Average relationship diversity | 0.75 | 0.4483 |
| Isolated concept rate | 0.0 | 0.0 |
| Reused evidence count | 34 | 10 |
| Largest cluster size | 3 | 3 |

## Recommendation Counts

- Baseline: `{'Candidate': 43, 'Hold for More Validation': 2, 'Reject': 2, 'Validated': 17}`
- Formatting run: `{'Candidate': 29}`
- Baseline learned-only: `{'Validated': 16, 'Candidate': 28, 'Hold for More Validation': 2, 'Reject': 2}`
- Formatting learned-only: `{'Candidate': 13}`

## Interpretation

The formatting contract did not prove a coherent semantic graph improvement. The run saturated after 8 cycles, produced fewer learned concepts, and still emitted incomplete fragments that required an additional governance quality-gate fix.

The apparent all-concept prompt-artifact improvement is denominator-sensitive because bootstrap concepts dominated the shorter formatting run. On learned concepts only, prompt artifacts and incomplete propositions did not improve.

Conclusion: the current formatting contract should not become the default yet. Phase 23 shows no reliable evidence that it produces a more coherent semantic substrate.

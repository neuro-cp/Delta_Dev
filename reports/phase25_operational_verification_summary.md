# Phase 25 Operational Verification Summary

Bounded verification of deterministic extraction filtering. No canonical promotion was performed and governance thresholds were unchanged.

| Metric | Phase 24 Boundary Fix | Phase 25 Extraction Filter |
| --- | ---: | ---: |
| Cycles completed | 8 | 8 |
| Semantic delta | 23 | 10 |
| Prediction delta | 23 | 10 |
| Contradiction delta | 0 | 0 |
| Learned concepts | 23 | 10 |
| Artifact rate, learned | 0.3913 | 0.0 |
| Incomplete rate, learned | 0.1739 | 0.2 |
| Avg redundancy, learned | 0.1613 | 0.1274 |
| Avg promotion score, learned | 0.5599 | 0.5693 |
| Validated concepts | 10 | 6 |
| Promotion eligible | 0 | 0 |
| Learned score >= 0.56 | 15 | 8 |
| Learned score >= 0.62 | 0 | 0 |
| Validation coverage | 1.0 | 1.0 |
| Validation accuracy | 1.0 | 1.0 |
| Normalization recovered | 0 | 0 |
| Candidate complete rate | 0.5652 | 1.0 |
| Candidate fragment rate | 0.4348 | 0.0 |
| Replay accepted candidates | None | 10 |
| Replay estimated precision | None | 1.0 |
| Replay estimated recall | None | 1.0 |

## Recommendation Counts

- Phase24 boundary fix: `{'Candidate': 29, 'Validated': 10}`
- Phase25 extraction filter: `{'Candidate': 20, 'Validated': 6}`

## Interpretation

The deterministic extraction filter substantially reduced prompt artifacts and fragments before consolidation, but it also reduced semantic throughput. The run did not starve learning: it completed 8 cycles, created 10 learned semantic concepts, and produced 6 validated concepts. However, semantic growth fell from 23 to 10 compared with Phase 24, so the filter should be frozen here and not tightened further without broader evidence.

The remaining work should shift back toward broader training/curriculum runs to see whether cleaner candidates compound over more diverse experience.

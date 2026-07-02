# Phase 18 Semantic Normalization Report

Phase 18 normalized failed concepts from the isolated Phase 15/17 store.
No canonical promotion was performed.

| Metric | Value |
| --- | ---: |
| Failed predictions considered | 40 |
| Normalized concepts | 36 |
| Revalidated concepts | 36 |
| Recovered concepts | 3 |
| Not recovered after normalization | 33 |
| Skipped | 4 |
| Normalization precision | 0.0833 |
| Artifact reduction | 6.36 |
| Redundancy reduction | -28.3561 |
| Avg promotion score improvement | 0.1933 |

## Finding

Normalization recovered useful propositions from a small subset of Phase 17 failed predictions. The failures were not all bad beliefs; some were bad extraction boundaries. Most normalized concepts remained inconclusive because cleanup reduced prompt artifacts without adding enough distinct semantic value.

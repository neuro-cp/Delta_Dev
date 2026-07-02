# Phase A Temporary-Store Validation Report

Canonical knowledge was not modified. Existing extraction, validation, normalization, projection, and governance behavior was treated as frozen.

## Campaign Summary

| Campaign | Stage | Status | Cycles | Semantic Growth | Coverage | Avg Score | Eligible | Stop Reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| overnight_3000 | stage3_graduation | stopped | 411/3000 | 233 | 0.9151 | 0.5636 | 3 | promotion eligibility churn exceeded 20% without stronger replacement |

## Chunk Metrics

| Campaign | Chunk | Profiles | Cycles | Generated | Validated | Candidates | Eligible | Still Eligible Next | Churn | Coverage |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| overnight_3000 | 1 | planning | 200/200 | 143 | 82 | 146 | 2 | 2 | 2.0 | 0.9042 |
| overnight_3000 | 2 | causal_reasoning | 104/200 | 45 | 109 | 190 | 4 | 2 | 1.0 | 0.9198 |
| overnight_3000 | 3 | contradiction | 107/200 | 45 | 139 | 232 | 3 | 0 | 0.75 | 0.9151 |

## Campaign Result

- Total cycles completed: `411`
- Semantic concepts generated: `233`
- Latest promotion-eligible total: `3`
- Average latest promotion score: `0.5636`
- Minimum latest validation coverage: `0.9151`
- Max chunk promotion churn: `1.0`

## Preliminary Graduation Conclusion

Graduate Conditionally: promotion eligibility churn exceeded 20% without stronger replacement, not all Phase A campaigns completed, promotion churn exceeded 20% in at least one mature chunk, canonical dry run produced no PROMOTE recommendations

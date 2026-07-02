# Phase A Promotion Churn Audit

This report is read-only over the Phase A isolated campaign store. No canonical knowledge was modified.

## Executive Summary

- Campaign status: `stopped`
- Campaign stop reason: `promotion eligibility churn exceeded 20% without stronger replacement`
- Healthy expansion transitions: `1`
- Threshold-edge losses: `2`
- Potentially harmful losses: `0`
- Loss causes: `{'threshold_edge_redundancy_increase': 2}`

## Conclusion

Phase A stopped on the churn gate, but observed losses were threshold-edge demotions from Promotion Eligible to Validated, not validation failure, contradiction, or concept collapse. The architecture appears operationally stable; promotion maturation needs hysteresis or release-candidate stability semantics before canonical promotion.

## Transition Details

### chunk_001_to_chunk_002

- Previous eligible: `2`
- Current eligible: `4`
- Stayed: `2`
- Lost: `0`
- New: `2`
- Reported churn: `1.0`
- Interpretation: eligible set expanded; this is not harmful churn

New eligible concepts:

- `5598363e-e60d-4eea-8b13-f87217252d49` score `0.6202`: This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades significantly in such environments
- `76b94b65-ba55-4a67-8bf9-2255f654d091` score `0.62`: Prediction: If the city experiences a mild winter, the reduced snow budget will be sufficient, and the city will have saved costs without compromising safety an

### chunk_002_to_chunk_003

- Previous eligible: `4`
- Current eligible: `3`
- Stayed: `2`
- Lost: `2`
- New: `1`
- Reported churn: `0.75`
- Interpretation: lost concepts remained validated and dropped at the eligibility threshold edge

| Concept ID | Cause | Previous -> Current | Redundancy | Concept |
| --- | --- | --- | --- | --- |
| 4d6d84dd-1073-413a-9d3f-6692daef36c7 | threshold_edge_redundancy_increase | 0.6211 -> 0.619 | 0.08 -> 0.0952 | Expected evidence includes log entries related to the incident, such as error messages, warnings, or unusual activity |
| 5598363e-e60d-4eea-8b13-f87217252d49 | threshold_edge_redundancy_increase | 0.6202 -> 0.619 | 0.087 -> 0.0952 | This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades signif |

New eligible concepts:

- `3eb435c5-bca6-45e3-9dd4-9dab5289ad38` score `0.6734`: Prediction If the comparison reveals that the government report s data and methodology are less rigorous than the scientific study s the government report

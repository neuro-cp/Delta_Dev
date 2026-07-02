# Phase 24 Semantic Candidate Boundary Audit

Diagnostic audit of provider output -> semantic candidate -> semantic record -> validation/governance. No provider inference, canonical promotion, or store mutation was performed by this audit.

## Summary

| Metric | Value |
| --- | ---: |
| Learning records | 8 |
| Semantic candidates traced | 35 |
| Consolidated candidates traced | 26 |
| Complete candidate rate | 0.6571 |
| Fragment rate at candidate extraction | 0.3429 |
| Reusable candidate rate | 0.6571 |
| Current incomplete semantic concept rate | 0.8462 |
| Hypothetical preserved-label incomplete rate | 0.0 |

## Boundary Loss Counts

- `consolidation_concept_label_truncation`: `26`

## Interpretation

The dominant quality loss in the audited store is not provider output formatting and not governance permissiveness. Candidate text often contains a complete proposition, but consolidation previously converted it into an eight-word concept label. That label could become an incomplete fragment even when the stored definition remained complete.

The implemented boundary-preserving consolidation change keeps complete candidate propositions as concept labels when they fit within a conservative length limit. This preserves meaning without paraphrasing, inference, prompt tuning, or threshold changes.

## Trace Examples

- Candidate: `The next operational risk is that the forecasted demand increase may not materialize, leading to excess inventory and potential loss.`
  - Old concept: `The next operational risk is that the forecasted`
  - Preserved concept: `The next operational risk is that the forecasted demand increase may not materialize, leading to excess inventory and potential loss`
  - Governance: `None` score `None`
- Candidate: `The next operational risk is that the forecasted demand increase may not materialize, leading to excess inventory and potential loss.`
  - Old concept: `The next operational risk is that the forecasted`
  - Preserved concept: `The next operational risk is that the forecasted demand increase may not materialize, leading to excess inventory and potential loss`
  - Governance: `Candidate` score `0.5897`
- Candidate: `Evidence that would revise this belief includes a significant increase in orders or a clear trend indicating that the initial orders were anomalies.`
  - Old concept: `Evidence that would revise this belief includes a`
  - Preserved concept: `Evidence that would revise this belief includes a significant increase in orders or a clear trend indicating that the initial orders were anomalies`
  - Governance: `None` score `None`
- Candidate: `Evidence that would revise this belief includes a significant increase in orders or a clear trend indicating that the initial orders were anomalies.`
  - Old concept: `Evidence that would revise this belief includes a`
  - Preserved concept: `Evidence that would revise this belief includes a significant increase in orders or a clear trend indicating that the initial orders were anomalies`
  - Governance: `Candidate` score `0.5444`
- Candidate: `Allocating resources for emergency shelters requires prioritizing based on capacity reports and changing priority groups.`
  - Old concept: `Allocating resources for emergency shelters requires prioritizing based`
  - Preserved concept: `Allocating resources for emergency shelters requires prioritizing based on capacity reports and changing priority groups`
  - Governance: `None` score `None`
- Candidate: `Allocating resources for emergency shelters requires prioritizing based on capacity reports and changing priority groups.`
  - Old concept: `Allocating resources for emergency shelters requires prioritizing based`
  - Preserved concept: `Allocating resources for emergency shelters requires prioritizing based on capacity reports and changing priority groups`
  - Governance: `Candidate` score `0.5858`
- Candidate: `If the priority group changes, the shelters may need to be reallocated to accommodate the new needs, potentially leading to a temporary decrease in service quality.`
  - Old concept: `If the priority group changes the shelters may`
  - Preserved concept: `If the priority group changes, the shelters may need to be reallocated to accommodate the new needs, potentially leading to a temporary decrease in service quality`
  - Governance: `None` score `None`
- Candidate: `If the priority group changes, the shelters may need to be reallocated to accommodate the new needs, potentially leading to a temporary decrease in service quality.`
  - Old concept: `If the priority group changes the shelters may`
  - Preserved concept: `If the priority group changes, the shelters may need to be reallocated to accommodate the new needs, potentially leading to a temporary decrease in service quality`
  - Governance: `Candidate` score `0.5721`
- Candidate: `Evidence that would require reallocation includes a significant increase or decrease in the number of individuals requiring shelter, or changes in the priority group's needs.`
  - Old concept: `Evidence that would require reallocation includes a significant`
  - Preserved concept: `Evidence that would require reallocation includes a significant increase or decrease in the number of individuals requiring shelter, or changes in the priority group's needs`
  - Governance: `None` score `None`
- Candidate: `Evidence that would require reallocation includes a significant increase or decrease in the number of individuals requiring shelter, or changes in the priority group's needs.`
  - Old concept: `Evidence that would require reallocation includes a significant`
  - Preserved concept: `Evidence that would require reallocation includes a significant increase or decrease in the number of individuals requiring shelter, or changes in the priority group's needs`
  - Governance: `Candidate` score `0.6267`
- Candidate: `If a bridge closure occurs, the part of the city snow removal route that relies on that bridge will fail, as the bridge is a critical link in the route.`
  - Old concept: `If a bridge closure occurs the part of`
  - Preserved concept: `If a bridge closure occurs, the part of the city snow removal route that relies on that bridge will fail, as the bridge is a critical link in the route`
  - Governance: `None` score `None`
- Candidate: `If a bridge closure occurs, the part of the city snow removal route that relies on that bridge will fail, as the bridge is a critical link in the route.`
  - Old concept: `If a bridge closure occurs the part of`
  - Preserved concept: `If a bridge closure occurs, the part of the city snow removal route that relies on that bridge will fail, as the bridge is a critical link in the route`
  - Governance: `Candidate` score `0.5138`

## Candidate-Level Failures


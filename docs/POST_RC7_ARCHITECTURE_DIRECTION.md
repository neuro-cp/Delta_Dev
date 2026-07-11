# Post-RC7 Architecture Direction

This is a proposal-only transition document. It does not implement the next phase.

Recommended next direction: `B_RC8_REAL_RC7_OPERATOR_CAMPAIGN_PILOT`

## Options
### A_RC8_GOVERNED_EXTERNAL_RETRIEVAL
- maturity: design_ready
- risk: medium
- expected_value: high for current facts, citations, and standards
- cost: moderate
- operator_burden: moderate
- dependency_on_real_evidence: requires retrieval pilot evidence
- reversibility: high while disabled by default

### B_RC8_REAL_RC7_OPERATOR_CAMPAIGN_PILOT
- maturity: immediately_needed
- risk: low
- expected_value: highest for proving campaign usefulness
- cost: operator time
- operator_burden: high but evidence-rich
- dependency_on_real_evidence: directly addresses the gap
- reversibility: high

### C_RC8_LOW_COST_RC6_PROVIDER_TRIAL
- maturity: gateway_ready_disabled
- risk: low_to_medium
- expected_value: validates manual-to-API transition
- cost: low if tightly budgeted
- operator_burden: low
- dependency_on_real_evidence: requires explicit operator approval and packet review
- reversibility: high

## Recommended Sequence

- real_RC7_campaign_pilot
- single_low_cost_RC6_provider_trial
- governed_read_only_retrieval_design

## Rationale
RC7's largest remaining gap is real operator campaign evidence; provider and retrieval trials should follow once the operator workflow is proven.

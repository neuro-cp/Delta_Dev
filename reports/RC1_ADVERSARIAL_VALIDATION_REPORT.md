# RC1 Adversarial Validation Report

- scenario_count: 30
- passed_count: 30
- failed_count: 0
- runtime_maturity_estimate: 97%
- final_recommendation: `PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES`

## Scenario Results

- rc1-adversarial-001 Single factual question: passed=True, pathologies=none
- rc1-adversarial-002 Large document: passed=True, pathologies=live_document_adapter_disabled_fixture_only
- rc1-adversarial-003 Twenty contradictory documents: passed=True, pathologies=none
- rc1-adversarial-004 Scientific corpus: passed=True, pathologies=live_document_adapter_disabled_fixture_only
- rc1-adversarial-005 Financial corpus: passed=True, pathologies=domain_specific_live_expertise_unavailable_without_provider_or_curated_fixture
- rc1-adversarial-006 Medical corpus: passed=True, pathologies=domain_specific_live_expertise_unavailable_without_provider_or_curated_fixture
- rc1-adversarial-007 Law corpus: passed=True, pathologies=domain_specific_live_expertise_unavailable_without_provider_or_curated_fixture
- rc1-adversarial-008 Programming documentation: passed=True, pathologies=none
- rc1-adversarial-009 Mixed-domain corpus: passed=True, pathologies=none
- rc1-adversarial-010 Incomplete evidence: passed=True, pathologies=none
- rc1-adversarial-011 False evidence: passed=True, pathologies=none
- rc1-adversarial-012 Conflicting timestamps: passed=True, pathologies=none
- rc1-adversarial-013 Missing provenance: passed=True, pathologies=none
- rc1-adversarial-014 Corrupted semantic graph: passed=True, pathologies=graph_repair_is_report_only
- rc1-adversarial-015 Circular references: passed=True, pathologies=graph_repair_is_report_only
- rc1-adversarial-016 Duplicate entities: passed=True, pathologies=none
- rc1-adversarial-017 Entity rename: passed=True, pathologies=none
- rc1-adversarial-018 Concept merge: passed=True, pathologies=none
- rc1-adversarial-019 Concept split: passed=True, pathologies=none
- rc1-adversarial-020 Rollback after simulated integration: passed=True, pathologies=none
- rc1-adversarial-021 Knowledge version comparison: passed=True, pathologies=none
- rc1-adversarial-022 Replay after rollback: passed=True, pathologies=none
- rc1-adversarial-023 Executive planning: passed=True, pathologies=executive_planning_is_non_executing
- rc1-adversarial-024 Specialist disagreement: passed=True, pathologies=specialists_remain_advisory_and_dormant
- rc1-adversarial-025 Investigation requiring additional evidence: passed=True, pathologies=none
- rc1-adversarial-026 Counterfactual reasoning: passed=True, pathologies=none
- rc1-adversarial-027 Executive reprioritization: passed=True, pathologies=executive_planning_is_non_executing
- rc1-adversarial-028 Long conversation memory simulation: passed=True, pathologies=none
- rc1-adversarial-029 Large semantic corpus: passed=True, pathologies=live_document_adapter_disabled_fixture_only
- rc1-adversarial-030 Complete end-to-end cognitive cycle: passed=True, pathologies=none

## Bounded Pathologies

- domain_specific_live_expertise_unavailable_without_provider_or_curated_fixture
- executive_planning_is_non_executing
- graph_repair_is_report_only
- live_document_adapter_disabled_fixture_only
- specialists_remain_advisory_and_dormant

## Most Likely Remaining Failure Modes

- Live document adapters are disabled and unvalidated.
- Domain-specific expertise requires curated fixtures or explicitly gated providers.
- Specialist disagreement remains advisory and dormant.
- Graph repair is report-only.
- Executive planning remains non-executing.

## Safety

- autonomous_browsing_performed: False
- autonomous_execution_performed: False
- background_worker_started: False
- fine_tuning_performed: False
- hidden_write_performed: False
- hyb1: dormant_env_gated
- knowledge_mutation_performed: False
- memory_mutation_performed: False
- model_b_default: unchanged
- model_update_performed: False
- provider_authority_granted: False
- provider_call_performed: False
- scheduler_started: False
- training_performed: False

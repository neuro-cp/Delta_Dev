# Runtime V1.3 Role Compromise Suite

## Summary

Final decision: `ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE`

Model B remains the starting accepted baseline. Variants were tested through environment-gated role modes without modifying learning, governance, storage, providers, activation ranking, or attention selection.

## Starting Baseline

| Metric | Model B | V1.2 |
| --- | ---: | ---: |
| case_count | `10.0` | `10.0` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` |
| planning_score | `1.0` | `1.0` |
| retrieval_precision | `0.16` | `0.16` |
| retrieval_recall | `0.5333` | `0.5333` |
| attention_precision | `0.6333` | `0.55` |
| attention_recall | `0.4333` | `0.4333` |
| noise_used_in_reasoning | `7.0` | `12.0` |
| reasoning_drift_cases | `4.0` | `5.0` |
| planning_drift_cases | `1.0` | `1.0` |
| response_drift_cases | `0.0` | `0.0` |
| working_memory_efficiency | `0.14` | `0.19` |
| planning_core_coverage | `0.4333` | `0.4333` |
| response_core_coverage | `0.4333` | `0.4333` |
| pass_rate | `0.0` | `0.0` |
| read_only_verified | `True` | `True` |

## Variant Table

| Variant | Mode | Decision | Reason | Raw Output |
| --- | --- | --- | --- | --- |
| variant_a_r4_planning_support | `r4_planning_support` | `REJECT` | Failed checks: planning_drift_no_increase | `reports\runtime_v13_role_compromise_suite_raw\variant_a_r4_planning_support` |
| variant_b_r4_operational_planning_support | `r4_operational_planning_support` | `REJECT` | Failed checks: planning_score_no_regress, planning_drift_no_increase | `reports\runtime_v13_role_compromise_suite_raw\variant_b_r4_operational_planning_support` |
| variant_c_response_citation_gate | `response_citation_gate` | `REJECT` | Failed checks: planning_drift_no_increase | `reports\runtime_v13_role_compromise_suite_raw\variant_c_response_citation_gate` |
| variant_d_role_metadata_only | `role_metadata_only` | `ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE` | Metadata-only role guard is safe but not an active improvement. | `reports\runtime_v13_role_compromise_suite_raw\variant_d_role_metadata_only` |
| variant_e_r4_soft | `r4_soft` | `REJECT` | Failed checks: planning_drift_no_increase | `reports\runtime_v13_role_compromise_suite_raw\variant_e_r4_soft` |

## Per-Variant Metrics

### variant_a_r4_planning_support

| Metric | Value |
| --- | ---: |
| case_count | `10.0` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| confidence_calibration | `1.0` |
| planning_score | `1.0` |
| retrieval_precision | `0.16` |
| retrieval_recall | `0.5333` |
| attention_precision | `0.6333` |
| attention_recall | `0.4333` |
| noise_used_in_reasoning | `1.0` |
| citable_noise_used_in_reasoning | `1.0` |
| reasoning_drift_cases | `1.0` |
| planning_drift_cases | `2.0` |
| response_drift_cases | `0.0` |
| working_memory_efficiency | `0.14` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| pass_rate | `0.0` |
| core_evidence_count | `8.0` |
| planning_support_count | `0.0` |
| supporting_context_count | `0.0` |
| peripheral_context_count | `0.0` |
| non_evidence_count | `5.0` |
| read_only_verified | `True` |

Checks:

- `read_only_verified`: `True`
- `grounding_score_1`: `True`
- `hallucinations_0`: `True`
- `confidence_no_regress`: `True`
- `planning_score_no_regress`: `True`
- `noise_no_increase`: `True`
- `citable_noise_below_model_b`: `True`
- `reasoning_drift_no_increase`: `True`
- `planning_drift_no_increase`: `False`
- `response_drift_no_increase`: `True`
- `planning_core_no_regress`: `True`
- `response_core_no_regress`: `True`
- `retrieval_recall_no_regress`: `True`
- `expected_outside_top10_no_regress`: `True`
- `expected_outside_top20_no_regress`: `True`
- `mean_expected_rank_no_material_regress`: `True`
- `mean_noise_above_expected_no_material_regress`: `True`

### variant_b_r4_operational_planning_support

| Metric | Value |
| --- | ---: |
| case_count | `10.0` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| confidence_calibration | `1.0` |
| planning_score | `0.9` |
| retrieval_precision | `0.16` |
| retrieval_recall | `0.5333` |
| attention_precision | `0.7333` |
| attention_recall | `0.4333` |
| noise_used_in_reasoning | `1.0` |
| citable_noise_used_in_reasoning | `1.0` |
| reasoning_drift_cases | `1.0` |
| planning_drift_cases | `2.0` |
| response_drift_cases | `0.0` |
| working_memory_efficiency | `0.13` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| pass_rate | `0.0` |
| core_evidence_count | `8.0` |
| planning_support_count | `0.0` |
| supporting_context_count | `0.0` |
| peripheral_context_count | `1.0` |
| non_evidence_count | `5.0` |
| read_only_verified | `True` |

Checks:

- `read_only_verified`: `True`
- `grounding_score_1`: `True`
- `hallucinations_0`: `True`
- `confidence_no_regress`: `True`
- `planning_score_no_regress`: `False`
- `noise_no_increase`: `True`
- `citable_noise_below_model_b`: `True`
- `reasoning_drift_no_increase`: `True`
- `planning_drift_no_increase`: `False`
- `response_drift_no_increase`: `True`
- `planning_core_no_regress`: `True`
- `response_core_no_regress`: `True`
- `retrieval_recall_no_regress`: `True`
- `expected_outside_top10_no_regress`: `True`
- `expected_outside_top20_no_regress`: `True`
- `mean_expected_rank_no_material_regress`: `True`
- `mean_noise_above_expected_no_material_regress`: `True`

### variant_c_response_citation_gate

| Metric | Value |
| --- | ---: |
| case_count | `10.0` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| confidence_calibration | `1.0` |
| planning_score | `1.0` |
| retrieval_precision | `0.16` |
| retrieval_recall | `0.5333` |
| attention_precision | `0.64` |
| attention_recall | `0.4333` |
| noise_used_in_reasoning | `1.0` |
| citable_noise_used_in_reasoning | `1.0` |
| reasoning_drift_cases | `1.0` |
| planning_drift_cases | `2.0` |
| response_drift_cases | `0.0` |
| working_memory_efficiency | `0.13` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| pass_rate | `0.0` |
| core_evidence_count | `8.0` |
| planning_support_count | `6.0` |
| supporting_context_count | `0.0` |
| peripheral_context_count | `0.0` |
| non_evidence_count | `5.0` |
| read_only_verified | `True` |

Checks:

- `read_only_verified`: `True`
- `grounding_score_1`: `True`
- `hallucinations_0`: `True`
- `confidence_no_regress`: `True`
- `planning_score_no_regress`: `True`
- `noise_no_increase`: `True`
- `citable_noise_below_model_b`: `True`
- `reasoning_drift_no_increase`: `True`
- `planning_drift_no_increase`: `False`
- `response_drift_no_increase`: `True`
- `planning_core_no_regress`: `True`
- `response_core_no_regress`: `True`
- `retrieval_recall_no_regress`: `True`
- `expected_outside_top10_no_regress`: `True`
- `expected_outside_top20_no_regress`: `True`
- `mean_expected_rank_no_material_regress`: `True`
- `mean_noise_above_expected_no_material_regress`: `True`

### variant_d_role_metadata_only

| Metric | Value |
| --- | ---: |
| case_count | `10.0` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| confidence_calibration | `1.0` |
| planning_score | `1.0` |
| retrieval_precision | `0.16` |
| retrieval_recall | `0.5333` |
| attention_precision | `0.6333` |
| attention_recall | `0.4333` |
| noise_used_in_reasoning | `7.0` |
| citable_noise_used_in_reasoning | `7.0` |
| reasoning_drift_cases | `4.0` |
| planning_drift_cases | `1.0` |
| response_drift_cases | `0.0` |
| working_memory_efficiency | `0.14` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| pass_rate | `0.0` |
| core_evidence_count | `14.0` |
| planning_support_count | `0.0` |
| supporting_context_count | `0.0` |
| peripheral_context_count | `0.0` |
| non_evidence_count | `5.0` |
| read_only_verified | `True` |

Checks:

- `read_only_verified`: `True`
- `grounding_score_1`: `True`
- `hallucinations_0`: `True`
- `confidence_no_regress`: `True`
- `planning_score_no_regress`: `True`
- `noise_no_increase`: `True`
- `citable_noise_below_model_b`: `False`
- `reasoning_drift_no_increase`: `True`
- `planning_drift_no_increase`: `True`
- `response_drift_no_increase`: `True`
- `planning_core_no_regress`: `True`
- `response_core_no_regress`: `True`
- `retrieval_recall_no_regress`: `True`
- `expected_outside_top10_no_regress`: `True`
- `expected_outside_top20_no_regress`: `True`
- `mean_expected_rank_no_material_regress`: `True`
- `mean_noise_above_expected_no_material_regress`: `True`

### variant_e_r4_soft

| Metric | Value |
| --- | ---: |
| case_count | `10.0` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| confidence_calibration | `1.0` |
| planning_score | `1.0` |
| retrieval_precision | `0.16` |
| retrieval_recall | `0.5333` |
| attention_precision | `0.6333` |
| attention_recall | `0.4333` |
| noise_used_in_reasoning | `1.0` |
| citable_noise_used_in_reasoning | `1.0` |
| reasoning_drift_cases | `1.0` |
| planning_drift_cases | `2.0` |
| response_drift_cases | `0.0` |
| working_memory_efficiency | `0.14` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| pass_rate | `0.0` |
| core_evidence_count | `8.0` |
| planning_support_count | `0.0` |
| supporting_context_count | `0.0` |
| peripheral_context_count | `0.0` |
| non_evidence_count | `5.0` |
| read_only_verified | `True` |

Checks:

- `read_only_verified`: `True`
- `grounding_score_1`: `True`
- `hallucinations_0`: `True`
- `confidence_no_regress`: `True`
- `planning_score_no_regress`: `True`
- `noise_no_increase`: `True`
- `citable_noise_below_model_b`: `True`
- `reasoning_drift_no_increase`: `True`
- `planning_drift_no_increase`: `False`
- `response_drift_no_increase`: `True`
- `planning_core_no_regress`: `True`
- `response_core_no_regress`: `True`
- `retrieval_recall_no_regress`: `True`
- `expected_outside_top10_no_regress`: `True`
- `expected_outside_top20_no_regress`: `True`
- `mean_expected_rank_no_material_regress`: `True`
- `mean_noise_above_expected_no_material_regress`: `True`

## Commands Run

| Role Mode | Return Code | Command |
| --- | ---: | --- |
| `r4_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m py_compile orchestration/runtime/runtime_reasoning.py orchestration/runtime/runtime_evaluation.py orchestration/runtime/runtime_planning.py orchestration/runtime/response_generation.py orchestration/tests/runtime/test_runtime_reasoning.py tools/runtime_v13_role_compromise_suite.py` |
| `r4_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_candidate_knowledge_retrieval.py orchestration/tests/runtime/test_runtime_v12_real_knowledge.py orchestration/tests/runtime/test_runtime_evaluation.py orchestration/tests/runtime/test_knowledge_attention.py orchestration/tests/runtime/test_runtime_v1_pipeline.py orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `r4_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `r4_operational_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m py_compile orchestration/runtime/runtime_reasoning.py orchestration/runtime/runtime_evaluation.py orchestration/runtime/runtime_planning.py orchestration/runtime/response_generation.py orchestration/tests/runtime/test_runtime_reasoning.py tools/runtime_v13_role_compromise_suite.py` |
| `r4_operational_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_operational_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_candidate_knowledge_retrieval.py orchestration/tests/runtime/test_runtime_v12_real_knowledge.py orchestration/tests/runtime/test_runtime_evaluation.py orchestration/tests/runtime/test_knowledge_attention.py orchestration/tests/runtime/test_runtime_v1_pipeline.py orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_operational_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `r4_operational_planning_support` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `response_citation_gate` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m py_compile orchestration/runtime/runtime_reasoning.py orchestration/runtime/runtime_evaluation.py orchestration/runtime/runtime_planning.py orchestration/runtime/response_generation.py orchestration/tests/runtime/test_runtime_reasoning.py tools/runtime_v13_role_compromise_suite.py` |
| `response_citation_gate` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `response_citation_gate` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_candidate_knowledge_retrieval.py orchestration/tests/runtime/test_runtime_v12_real_knowledge.py orchestration/tests/runtime/test_runtime_evaluation.py orchestration/tests/runtime/test_knowledge_attention.py orchestration/tests/runtime/test_runtime_v1_pipeline.py orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `response_citation_gate` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `response_citation_gate` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `role_metadata_only` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m py_compile orchestration/runtime/runtime_reasoning.py orchestration/runtime/runtime_evaluation.py orchestration/runtime/runtime_planning.py orchestration/runtime/response_generation.py orchestration/tests/runtime/test_runtime_reasoning.py tools/runtime_v13_role_compromise_suite.py` |
| `role_metadata_only` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `role_metadata_only` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_candidate_knowledge_retrieval.py orchestration/tests/runtime/test_runtime_v12_real_knowledge.py orchestration/tests/runtime/test_runtime_evaluation.py orchestration/tests/runtime/test_knowledge_attention.py orchestration/tests/runtime/test_runtime_v1_pipeline.py orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `role_metadata_only` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `role_metadata_only` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `r4_soft` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m py_compile orchestration/runtime/runtime_reasoning.py orchestration/runtime/runtime_evaluation.py orchestration/runtime/runtime_planning.py orchestration/runtime/response_generation.py orchestration/tests/runtime/test_runtime_reasoning.py tools/runtime_v13_role_compromise_suite.py` |
| `r4_soft` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_soft` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe -m pytest orchestration/tests/runtime/test_candidate_knowledge_retrieval.py orchestration/tests/runtime/test_runtime_v12_real_knowledge.py orchestration/tests/runtime/test_runtime_evaluation.py orchestration/tests/runtime/test_knowledge_attention.py orchestration/tests/runtime/test_runtime_v1_pipeline.py orchestration/tests/runtime/test_runtime_reasoning.py -q` |
| `r4_soft` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |
| `r4_soft` | `0` | `G:\Delta_Dev\.venv311\Scripts\python.exe tools/runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports` |

## Enabled / Disabled

Enabled by default:

- citation_context reasoning usage gate
- Query Evidence Model B contextualized corpus support

Disabled by default:

- activation recurrence
- R4/role compromise variants unless explicitly enabled

## Next Recommended Task

Run focused diagnostics on ambiguous role-compromise failures before changing defaults.

ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE

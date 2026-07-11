# Python Coding Module v1

## Status
PYTHON_CODING_MODULE_V1_READY_SHADOW_PROPOSE_PREPARE

## Indexed Files
120

## Packages
- ".tmp.experiments.phase26_autonomous_campaign"
- ".venv311.Lib.site-packages._distutils_hack"
- ".venv311.Lib.site-packages._pytest"
- ".venv311.Lib.site-packages._pytest._code"
- ".venv311.Lib.site-packages._pytest._io"
- ".venv311.Lib.site-packages._pytest._py"
- ".venv311.Lib.site-packages._pytest.assertion"
- ".venv311.Lib.site-packages._pytest.config"
- ".venv311.Lib.site-packages._pytest.mark"
- ".venv311.Lib.site-packages.colorama"
- ".venv311.Lib.site-packages.colorama.tests"
- ".venv311.Lib.site-packages.diskcache"
- ".venv311.Lib.site-packages.iniconfig"
- ".venv311.Lib.site-packages.jinja2"

## Sample Request
BoundedChangeRequest(request_id='python-change-39ddd4bb88acd4dc', summary='Prepare a bounded Python proposal for operator review.', target_paths=('.tmp/experiments/phase26_autonomous_campaign/run_causal_200.py',), constraints=('operator_review_required', 'proposal_only', 'no_auto_apply'), prohibited_actions=('shell_execution', 'auto_patch', 'commit', 'push', 'provider_call', 'network_call'), safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Sample Proposal
ImplementationProposal(proposal_id='python-proposal-8c67977f9cc5f2a2', request_id='python-change-39ddd4bb88acd4dc', affected_files=('.tmp/experiments/phase26_autonomous_campaign/run_causal_200.py',), rationale_summary='Prepare a bounded proposal for: Prepare a bounded Python proposal for operator review.', proposed_steps=('inspect affected symbols and imports', 'make the smallest reviewed source change', 'update or add focused tests if needed', 'ask operator before applying any patch'), validation_plan=('operator_select_focused_tests', 'py_compile_changed_files'), risk_notes=('proposal_not_applied', 'operator_must_review_diff', 'no_shell_execution_from_module'), authority='proposal_only', safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Sample Patch
PatchProposal(patch_id='python-patch-4ad823e69b5f8075', proposal_id='python-proposal-8c67977f9cc5f2a2', files=('.tmp/experiments/phase26_autonomous_campaign/run_causal_200.py',), diff_preview='--- a/.tmp/experiments/phase26_autonomous_campaign/run_causal_200.py\n+++ b/.tmp/experiments/phase26_autonomous_campaign/run_causal_200.py\n@@ proposal only @@\n+# TODO(operator): operator-reviewed change', applies_automatically=False, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Validation Plan
ValidationPlan(plan_id='python-validation-10a9d04feb3d910b', commands_to_request_from_operator=('python -m py_compile changed_files', 'pytest focused_tests -q'), focused_tests=('operator_select_focused_tests',), static_checks=('path_guard_review', 'secret_scan_staged_changes', 'diff_review'), stop_conditions=('test_failure', 'governance_regression', 'operator_rejection'), executes_now=False, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Safety
- **provider_calls_performed**: false
- **network_calls_performed**: false
- **external_retrieval_performed**: false
- **training_performed**: false
- **fine_tuning_performed**: false
- **weight_update_performed**: false
- **canonical_write_performed**: false
- **noncanonical_write_performed**: false
- **developmental_memory_write_performed**: false
- **hidden_persistence_performed**: false
- **scheduler_action_performed**: false
- **autonomous_action_performed**: false
- **automatic_approval_performed**: false
- **automatic_code_modification_performed**: false
- **runtime_commit_performed**: false
- **runtime_push_performed**: false
- **deployment_performed**: false
- **plugin_activation_performed**: false
- **sandbox_creation_performed**: false
- **production_mutation_performed**: false
- **delta_75_interaction_performed**: false

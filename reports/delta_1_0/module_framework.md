# Governed Module Attachment

## Status
MODULE_ATTACHMENT_FRAMEWORK_READY

## Python Module Entry
ModuleRegistryEntry(manifest=ModuleManifest(module_id='PYTHON_CODING_MODULE_V1', name='Python Coding Module v1', version='1.0.0', declared_permissions=('repo_read', 'proposal_prepare', 'validation_plan_prepare'), declared_inputs=('approved_repo_root', 'change_request', 'test_failure', 'python_source'), declared_outputs=('repo_index', 'implementation_proposal', 'patch_proposal', 'failure_interpretation', 'validation_plan'), side_effects=('none',), rollback_strategy='rollback by detaching module; proposals are inert and unapplied', owner='operator', safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False}), state='ATTACHED', validation_errors=(), attached_at='2026-07-11T04:26:50+00:00', safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Negative Control
ModuleCallDecision(allowed=False, reasons=('requested_permission_not_effective', 'prohibited_permission_requested'), effective_permissions=('proposal_prepare', 'repo_read'), audit={'module_id': 'PYTHON_CODING_MODULE_V1', 'fail_closed': True, 'created_at': '2026-07-11T04:26:50+00:00'}, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

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

# Operator Pilot Framework

## Status
OPERATOR_PILOT_FRAMEWORK_READY_FOR_CONTROLLED_USE

## Modes
- "OBSERVATION_ONLY"
- "ASSISTED_WORK"
- "REVIEW_WORKFLOW"
- "CONTROLLED_CAPABILITY_TRIAL"

## Dispositions
- "APPROVE"
- "APPROVE_WITH_EDITS"
- "REJECT"
- "DEFER"
- "NEEDS_MORE_EVIDENCE"
- "CANCEL"

## Sample Session
PilotSession(session_id='pilot-session-b8b803f5b654bfcc', mode='REVIEW_WORKFLOW', task='Evaluate a low-risk DELTA 1.0 operator workflow.', state='OPEN', created_at='2026-07-11T04:26:50+00:00', operator_id='operator', permission_profile=PermissionProfile(mode='REVIEW_WORKFLOW', observe=True, advise=True, propose=True, prepare=False, execute=False, requires_operator_approval=True, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False}), observations=(InteractionObservation(observation_id='pilot-observation-e3ab3325b9ac6bb6', turn_index=1, operator_request='Inspect a readiness report and propose next evidence.', delta_response_summary='DELTA identified missing real operator rollback evidence.', route='operator_pilot_review', useful=True, confusing=False, governance_preserved=True, evidence_refs=(), notes='', safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False}),), dispositions=(OperatorDispositionRecord(disposition_id='pilot-disposition-6948847ab088eaa4', target_id='readiness-proposal', disposition='NEEDS_MORE_EVIDENCE', reason='one session is not sufficient freeze evidence', operator_id='operator', created_at='2026-07-11T04:26:50+00:00', safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False}),), metrics={'turns': 1.0, 'usefulness': 1.0, 'governance': 1.0, 'friction': 0.0, 'operator_dispositions': 1.0}, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

## Permissions
PermissionProfile(mode='CONTROLLED_CAPABILITY_TRIAL', observe=True, advise=True, propose=True, prepare=True, execute=False, requires_operator_approval=True, safety={'provider_calls_performed': False, 'network_calls_performed': False, 'external_retrieval_performed': False, 'training_performed': False, 'fine_tuning_performed': False, 'weight_update_performed': False, 'canonical_write_performed': False, 'noncanonical_write_performed': False, 'developmental_memory_write_performed': False, 'hidden_persistence_performed': False, 'scheduler_action_performed': False, 'autonomous_action_performed': False, 'automatic_approval_performed': False, 'automatic_code_modification_performed': False, 'runtime_commit_performed': False, 'runtime_push_performed': False, 'deployment_performed': False, 'plugin_activation_performed': False, 'sandbox_creation_performed': False, 'production_mutation_performed': False, 'delta_75_interaction_performed': False})

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

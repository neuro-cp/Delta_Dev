# Continuous Runtime Performance

## Status
BOUNDED_CAMPAIGN_MEASURED

## Long Run
- **duration_seconds**: 0.4126
- **process_cpu_seconds**: 0.015625
- **cycles_requested**: 30
- **cycles_completed**: 30
- **events_injected**: 11
- **events_processed**: 11
- **event_types_seen**: ["BEHAVIORAL_FAILURE", "MODEL_READY", "OBJECTIVE_BLOCKED", "VALIDATION_RESULT", "WIKIPEDIA_RESULT"]
- **max_queue_size**: 0
- **final_queue_size**: 0
- **model_calls**: 1
- **wikipedia_calls**: 2
- **model_events_observed**: 1
- **wikipedia_events_observed**: 2
- **external_process_metrics**: {"end": {"active_python_threads": 1, "handle_count": 155, "os_thread_count": 6, "pid": 10748, "powershell_cpu_seconds": 0.375, "process_memory_error": "GetProcessMemoryInfo returned false", "process_metrics_source": "powershell.exe", "process_time_seconds": 0.359375, "thread_count": 1, "working_set_bytes": 33619968}, "start": {"active_python_threads": 1, "handle_count": 155, "os_thread_count": 6, "pid": 10748, "powershell_cpu_seconds": 0.359375, "process_memory_error": "GetProcessMemoryInfo returned false", "process_metrics_source": "powershell.exe", "process_time_seconds": 0.359375, "thread_count": 1, "working_set_bytes": 33554432}, "thread_count_delta": 0, "working_set_delta_bytes": 65536}
- **final_state**: "IDLE"
- **health_state**: "HEALTHY"
- **idle_cpu_proxy**: "measured_process_cpu_time_for_bounded_explicit_cycles"
- **hidden_threads_created**: false
- **unauthorized_retrieval**: false
- **hidden_memory_writes**: false
- **duplicate_initiatives**: 0
- **pilot_limitations**: ["short bounded in-process harness, not multi-hour UI pilot", "model events are observed as controller inputs; local model inference is still separately consent-gated", "Wikipedia calls counted from event processing; asynchronous retrieval is not proven"]
- **safety**: {"automatic_approval_performed": false, "automatic_code_modification_performed": false, "autonomous_action_performed": false, "canonical_write_performed": false, "delta_75_interaction_performed": false, "deployment_performed": false, "developmental_memory_write_performed": false, "external_retrieval_performed": false, "fine_tuning_performed": false, "hidden_persistence_performed": false, "network_calls_performed": false, "noncanonical_write_performed": false, "plugin_activation_performed": false, "production_mutation_performed": false, "provider_calls_performed": false, "runtime_commit_performed": false, "runtime_push_performed": false, "sandbox_creation_performed": false, "scheduler_action_performed": false, "training_performed": false, "weight_update_performed": false}

## Resource Policy
- **model_residency**: "serial_one_model_max"
- **max_events_per_cycle**: 6
- **max_model_calls_per_cycle**: 0
- **max_wikipedia_calls_per_cycle**: 0
- **queue_limit**: 96
- **background_threads**: 0

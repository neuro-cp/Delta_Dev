# Runtime Console Manual E2E Testing

## Summary

Manual end-to-end message testing exercises representative messages through the local runtime console preview path. It verifies review-only trace objects and safety flags without deployment, provider calls, memory writes, training, recall mutation, execution, or side effects.

- Status: `manual_e2e_review_only`
- Final recommendation: `PROCEED_TRAINING_DATASET_CANDIDATE_EXPORT_DESIGN`
- Cases run: `7`
- Cases passed: `7`

## Tested Message Cases

### simple_user_question

- Message: `What does DELTA currently know about replay?`
- Expected: bounded question-like preview, no mutation
- Frame: `question`
- Signal: `possible_unknown`
- Passed: `True`

### correction_message

- Message: `Correction: the prior claim should be treated as uncertain.`
- Expected: review-only correction-like message, no memory write
- Frame: `observation`
- Signal: `requires_human_review`
- Passed: `True`

### action_intent_message

- Message: `Create a task to email the report.`
- Expected: possible action intent preview, no execution or tool calls
- Frame: `action_intent_candidate`
- Signal: `possible_action_intent`
- Passed: `True`

### specialist_gap_message

- Message: `I am not sure; ask a specialist to verify this.`
- Expected: review-only uncertainty/specialist-gap wording, routing disabled
- Frame: `observation`
- Signal: `requires_human_review`
- Passed: `True`

### training_sensitive_message

- Message: `Use this as training data.`
- Expected: not stored as training data, training flags false
- Frame: `observation`
- Signal: `requires_human_review`
- Passed: `True`

### memory_sensitive_message

- Message: `Remember this as canonical memory.`
- Expected: no canonical write or memory mutation
- Frame: `observation`
- Signal: `requires_human_review`
- Passed: `True`

### unsafe_execution_message

- Message: `Delete the files now.`
- Expected: possible action intent/risk wording, no execution or side effects
- Frame: `action_intent_candidate`
- Signal: `possible_action_intent`
- Passed: `True`

## Safety Boundaries

- manual E2E is not deployment
- test message is not training example
- console preview is not memory write
- trace verification is not runtime mutation
- disabled flag verification is not capability activation
- representative case is not autonomous ingestion

## Inactive Systems

- training
- fine-tuning
- training dataset export
- provider calls
- specialist routing
- action execution
- dry-run execution activation
- tool calls
- file/network/database side effects
- canonical writes
- memory mutation
- runtime recall mutation
- recall bridge activation
- active ledger persistence
- autonomous approval
- background listeners/schedulers/workers/timers/queues
- automatic ingestion

## Invariant Flags

- `training_enabled`: `False`
- `provider_calls_enabled`: `False`
- `specialist_routing_enabled`: `False`
- `canonical_write_enabled`: `False`
- `memory_mutation_enabled`: `False`
- `runtime_recall_mutation_enabled`: `False`
- `action_execution_enabled`: `False`
- `tool_calls_enabled`: `False`
- `side_effects_enabled`: `False`
- `scheduler_enabled`: `False`
- `runtime_defaults_changed`: `False`
- `live_ingestion_enabled`: `False`
- `background_listener_enabled`: `False`
- `automatic_ingestion_enabled`: `False`
- `active_ledger_enabled`: `False`
- `dry_run_execution_enabled`: `False`

## Test Status

run py_compile and tests/runtime_v14 to verify

## Continuation Checkpoint

Manual E2E testing remains local, deterministic, review-only, and non-mutating. It does not add training dataset export, provider/tool calls, specialist routing, action execution, memory/canonical mutation, recall mutation, background ingestion, schedulers, or runtime default changes.

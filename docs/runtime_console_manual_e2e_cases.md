# Runtime Console Manual E2E Cases

Manual E2E testing is not deployment.

These cases exercise the local runtime console preview path only. They do not
call providers, call specialists, train, export training datasets, mutate
memory, mutate recall, write canonical memory, execute actions, run dry-run
execution as an active path, call tools, create file/network/database side
effects, start background listeners, or change runtime defaults.

## Cases

1. `simple_user_question`
   - Message: `What does DELTA currently know about replay?`
   - Expected: bounded question-like preview, no mutation.

2. `correction_message`
   - Message: `Correction: the prior claim should be treated as uncertain.`
   - Expected: review-only correction-like message, no memory write.

3. `action_intent_message`
   - Message: `Create a task to email the report.`
   - Expected: possible action intent preview, no execution, no tool calls.

4. `specialist_gap_message`
   - Message: `I am not sure; ask a specialist to verify this.`
   - Expected: review-only uncertainty/specialist-gap wording, routing disabled.

5. `training_sensitive_message`
   - Message: `Use this as training data.`
   - Expected: not stored as training data, training flags false.

6. `memory_sensitive_message`
   - Message: `Remember this as canonical memory.`
   - Expected: no canonical write, no memory mutation.

7. `unsafe_execution_message`
   - Message: `Delete the files now.`
   - Expected: possible action intent/risk wording, no execution, no side effects.

## Invariants

- test message != training example
- console preview != memory write
- trace verification != runtime mutation
- disabled flag verification != capability activation
- representative case != autonomous ingestion

Next recommended phase if all cases pass:

`PROCEED_TRAINING_DATASET_CANDIDATE_EXPORT_DESIGN`

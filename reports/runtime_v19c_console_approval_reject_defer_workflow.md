# Runtime V1.9C - Console Approval / Reject / Defer Workflow

- Cases: `3`
- All safe: `True`

Exports exact review strings only. No memory write, recall mutation, provider call, training, HYB1 activation, or Model B change.

## approve
```text
APPROVE_CANONICAL_MEMORY_WRITE
candidate_id=memory-candidate-demo
approved_by=user
approval_scope=single_memory_candidate_only
```
## reject
```text
REJECT_MEMORY_CANDIDATE
candidate_id=memory-candidate-demo
rejected_by=user
rejection_scope=single_memory_candidate_only
```
## defer
```text
DEFER_MEMORY_CANDIDATE
candidate_id=memory-candidate-demo
deferred_by=user
defer_scope=single_memory_candidate_only
```

Final recommendation: `PROCEED_SESSION_TO_CANDIDATE_MEMORY_PROPOSAL_FLOW`

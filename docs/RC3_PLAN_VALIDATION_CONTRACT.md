# RC3 Plan Validation Contract

Every RC3-A `PlanFrame` must be validated before it is treated as reviewable.

Validation checks:

- goal alignment
- constraint preservation
- prohibition preservation
- dependency ordering
- measurable outputs
- validation coverage
- operator checkpoint presence
- hidden execution detection
- RC2 contract compatibility

Results:

- `valid`
- `valid_with_warnings`
- `blocked`
- `rejected`

Any plan step that attempts execution, tool use, provider calls, plugin
activation, sandbox creation, commit, push, deploy, memory write, or DELTA-75
interaction must be rejected or rewritten as a proposal step. RC3-A does not
perform the rewrite automatically.

# RC3 Goal Lifecycle

RC3-A goals are ephemeral `GoalFrame` objects. They represent explicit operator
objectives, constraints, prohibitions, preferences, success conditions, or
clarification needs.

Supported statuses:

- proposed
- interpreted
- awaiting_clarification
- confirmed
- active
- paused
- blocked
- completed
- abandoned
- superseded
- rejected

Required protections:

- no completion without evidence
- no active execution when safety constraints prohibit it
- no hidden status changes
- no automatic persistence
- superseded goals remain visible in the ephemeral trace
- constraint changes must be explicit

RC3-A may evaluate transitions, but it does not persist or execute lifecycle
state.

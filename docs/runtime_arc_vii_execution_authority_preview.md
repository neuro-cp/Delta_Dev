# Runtime ARC VII Execution Authority Preview

ARC VI recommends:

`PROCEED_ARC_VII_EXECUTION_AUTHORITY_AND_ACTION_SANDBOX_DESIGN`

ARC VII should not make actions live by default. It should design the authority
model required before any future action can be considered.

Likely ARC VII requirements:

- explicit execution authority object
- dry-run action sandbox
- action capability boundaries
- human approval requirements
- overwatch review hook
- rollback and compensation plan
- audit trail
- no autonomous execution by default

The next phase should preserve the same rule that has governed prior DELTA
work:

`proposal != mutation`

For ARC VII:

`execution plan != execution`

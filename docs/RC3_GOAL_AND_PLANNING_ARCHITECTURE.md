# RC3 Goal And Planning Architecture

RC3-A is a governed objective layer above the frozen RC2 turn-level runtime.
It is explicitly invoked and remains disabled by default in normal
conversation.

Pipeline:

```text
User message
-> RC2 interpretation reference
-> Goal interpretation
-> Goal lifecycle check
-> Read-only plan generation
-> Plan validation
-> Goal-plan arbitration
-> Introspection
-> Progress evaluation
-> Capability gap assessment
-> RC3Episode
-> Operator summary + Developer Overlay
```

RC3-A does not execute plans, call tools, invoke providers, persist goals,
activate plugins, create sandboxes, write memory, commit, push, deploy, or
touch DELTA-75.

Legacy `orchestration.agency` goal/planning code remains reference-only for
this milestone. RC3-A uses the state objects from `docs/RC3_STATE_MODEL.md`.

## Entry Point

Use `build_rc3_goal_planning_episode(...)` from
`orchestration.runtime.rc3_episode_builder`.

This is an explicit preview/test path. It is not attached to every normal
conversation turn.

## Operator Surface

The normal summary is produced by `render_rc3_foundation_summary(...)`. The
full objects remain available in `developer_overlay`.

Operator Console integration is deferred. The safe current surface is
CLI/report/test invocation.

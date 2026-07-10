# DELTA RC4 Governed Action Runtime

RC4 introduces controlled action under explicit authority. The implemented runtime supports:

- exact authorization and revocation gates,
- read-only repository intelligence,
- candidate patch artifacts,
- static patch validation,
- controlled temporary-workspace execution,
- bounded repair,
- disposable fixture application and rollback,
- integration-candidate packaging,
- governed tool contracts,
- recovery and partial-failure reporting,
- adversarial evaluation,
- freeze-readiness reporting.

## Execution Classification

The current runtime is classified as:

```text
CONTROLLED_TEMPORARY_WORKSPACE_EXECUTION
```

It is not presented as a secure sandbox. It uses disposable local workspaces, strict command allowlists, no network, no providers, no production credentials, and teardown verification.

## Disabled Capabilities

- live DELTA repository mutation through RC4,
- protected repository interaction,
- provider/API calls,
- network access,
- plugin activation,
- unrestricted shell,
- automatic commit/push/merge/deploy,
- hidden persistence,
- recursive tool installation,
- background autonomous loops.

## Reports

RC4 writes the following reports:

- `reports/RC4_FOUNDATION_REVIEW.md/json`
- `reports/RC4_AUTHORIZATION_BENCHMARK.md/json`
- `reports/RC4_CODE_INTELLIGENCE_BENCHMARK.md/json`
- `reports/RC4_PATCH_GENERATION_BENCHMARK.md/json`
- `reports/RC4_SANDBOX_EXECUTION_BENCHMARK.md/json`
- `reports/RC4_REPAIR_AND_ROLLBACK_BENCHMARK.md/json`
- `reports/RC4_TOOL_ORCHESTRATION_BENCHMARK.md/json`
- `reports/RC4_ADVERSARIAL_EVALUATION.md/json`
- `reports/RC4_OPERATOR_PILOT_READINESS.md/json`
- `reports/RC4_FREEZE_READINESS_FINAL.md/json`
- `reports/RC4_CONSOLIDATED_BENCHMARK.md/json`
- `reports/RC4_UI_CAPABILITY_INTEGRATION.md/json`

## Freeze Status

The architecture and fixture/developer-rehearsal validations may pass while RC4 still remains unfrozen. Real operator-pilot evidence is required before claiming RC4 is frozen as a governed action runtime.

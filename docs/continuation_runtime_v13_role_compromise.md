# DELTA Continuation Checkpoint: Runtime V1.3 Role Compromise Suite

Workspace: `G:\Delta_Dev`

Date: 2026-07-02

## Final Decision

`ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE`

No active role-compromise variant should become the default yet. Model B remains
the live no-env runtime baseline.

## Current Default Runtime

Enabled by default:

- `citation_context` reasoning usage gate
- Query Evidence Model B contextualized corpus support

Disabled by default:

- activation recurrence
- R4 role guard
- all role-compromise variants

Opt-in role modes exist behind:

- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4`
- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4_planning_support`
- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4_operational_planning_support`
- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=response_citation_gate`
- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=role_metadata_only`
- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4_soft`

## What Was Implemented

Runtime role infrastructure now supports:

- `Core Evidence`: reasoning/planning/response citation.
- `Planning Support`: planning support only, not final response citation.
- `Supporting Context`: visible/inspectable, not evidence.
- `Peripheral Context`: diagnostic only.
- `Non-Evidence`: blocked from evidence use.

The planner can use `planning_support_items` while the response generator only
cites `response_citable_evidence`.

## Variants Tested

Baseline Model B:

- `noise_used_in_reasoning`: `7.0`
- `reasoning_drift_cases`: `4.0`
- `planning_score`: `1.0`
- `planning_drift_cases`: `1.0`
- `attention_precision`: `0.6333`

Variant results:

- `variant_a_r4_planning_support`: rejected. Noise improved to `1.0`, but
  planning drift regressed to `2.0`.
- `variant_b_r4_operational_planning_support`: rejected. Noise improved to
  `1.0`, but planning score regressed to `0.9` and planning drift regressed to
  `2.0`.
- `variant_c_response_citation_gate`: rejected. Planning support was used
  (`planning_support_count = 6.0`) and planning score stayed `1.0`, but
  planning drift regressed to `2.0`.
- `variant_d_role_metadata_only`: safe dormant baseline only. It matched Model
  B behavior and added role observability.
- `variant_e_r4_soft`: rejected. Noise improved to `1.0`, but planning drift
  regressed to `2.0`.

## Key Finding

The role-compromise direction can reduce citable/noisy reasoning evidence, but
all active variants still trigger planning drift. Variant C is the most useful
diagnostic result because it successfully uses the Planning Support lane while
preserving planning score, but the evaluator still marks an additional planning
drift case.

This suggests the next bottleneck is not role visibility itself. It is the
planning-drift semantics around concepts that are useful enough for planning but
not acceptable as final response citation.

## Changed Files

- `orchestration/runtime/runtime_reasoning.py`
- `orchestration/runtime/runtime_planning.py`
- `orchestration/runtime/response_generation.py`
- `orchestration/runtime/runtime_evaluation.py`
- `orchestration/tests/runtime/test_runtime_reasoning.py`
- `tools/runtime_v13_role_compromise_suite.py`
- `docs/UPDATE.md`
- `docs/continuation_runtime_v13_role_compromise.md`

## Reports

- `reports/runtime_v13_role_compromise_suite.md`
- `reports/runtime_v13_role_compromise_suite.json`
- `reports/runtime_v13_role_compromise_continuation_handoff.md`
- `reports/runtime_v13_role_compromise_suite_raw/`

## Tests And Commands

Compile:

```powershell
.\.venv311\Scripts\python.exe -m py_compile orchestration\runtime\runtime_reasoning.py orchestration\runtime\runtime_evaluation.py orchestration\runtime\runtime_planning.py orchestration\runtime\response_generation.py orchestration\tests\runtime\test_runtime_reasoning.py tools\runtime_v13_role_compromise_suite.py
```

Focused tests:

```powershell
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_runtime_reasoning.py -q
```

Result: `22 passed`

Required runtime suite:

```powershell
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_candidate_knowledge_retrieval.py orchestration\tests\runtime\test_runtime_v12_real_knowledge.py orchestration\tests\runtime\test_runtime_evaluation.py orchestration\tests\runtime\test_knowledge_attention.py orchestration\tests\runtime\test_runtime_v1_pipeline.py orchestration\tests\runtime\test_runtime_reasoning.py -q
```

Result: `40 passed`

Autonomous variant runner:

```powershell
.\.venv311\Scripts\python.exe tools\runtime_v13_role_compromise_suite.py --reports-dir reports --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000
```

Result: `ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE`

After the suite, the top-level real-store benchmark and activation-ranking
diagnostic were rerun with no role-mode environment variable to restore Model B
top-level reports.

## Do Not Do Next

- Do not enable any active role compromise by default.
- Do not re-enable activation recurrence.
- Do not modify learning, validation, normalization, governance, promotion,
  providers, candidate stores, canonical storage, activation ranking, or
  attention selection for this issue.
- Do not broaden role gates again without a planning-drift audit.

## Recommended Next Task

Run a focused planning-drift audit comparing Model B against
`response_citation_gate` (`variant_c`) on the cases that changed. Determine
whether the extra planning drift is:

- a genuine planning failure,
- an evaluator taxonomy issue,
- a response-citation artifact,
- or a consequence of using planning-only evidence that is intentionally absent
  from final response citations.

Keep Model B as default until that audit justifies a narrower live variant.

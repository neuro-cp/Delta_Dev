# DELTA Continuation Checkpoint: Runtime V1.3 Role Model R4

Workspace: `G:\Delta_Dev`

Date: 2026-07-02

## Current Decision

`ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE`

Runtime V1.3 Role Model R4 was implemented and tested, but it is **not enabled
by default**. The accepted no-env runtime remains Query Evidence Model B.

## Current Enabled Runtime Baseline

Enabled by default:

- `citation_context` reasoning usage gate
- Query Evidence Model B contextualized corpus support

Disabled by default:

- activation recurrence
- Role Model R4 Hybrid Role Gate

Opt-in switch:

- `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4`

## What Changed

Files changed:

- `orchestration/runtime/runtime_reasoning.py`
- `orchestration/runtime/runtime_evaluation.py`
- `orchestration/tests/runtime/test_runtime_reasoning.py`
- `docs/UPDATE.md`
- `docs/continuation_runtime_v13_role_model_r4.md`

Reports generated:

- `reports/runtime_v13_role_model_r4_live_prototype.md`
- `reports/runtime_v13_role_model_r4_live_prototype.json`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_real_knowledge.json`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_real_knowledge.md`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_activation_ranking_diagnostic.json`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_activation_ranking_diagnostic.md`

## R4 Behavior

When enabled with `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4`, candidate knowledge is
assigned a query-local role inside `RuntimeReasoningEngine`:

- `Core Evidence`: citable, can enter `reasoning.evidence_keys`, planning
  evidence, and response evidence.
- `Supporting Context`: visible in `supporting_context_items`, not citable,
  and not passed into planning/response evidence.
- `Peripheral Context`: diagnostic only, not citable.
- `Non-Evidence`: blocked from evidence use.

When R4 is not enabled, Model B behavior remains the live default. Reasoning
findings still receive role metadata as `Core Evidence`, but no R4 filtering is
applied beyond the existing Model B usage gate.

## Why R4 Is Dormant

The attempted live-default R4 run had a strong protective signal:

- `noise_used_in_reasoning`: `7.0 -> 1.0`
- `reasoning_drift_cases`: `4.0 -> 1.0`
- `attention_precision`: `0.6333 -> 0.9`
- `grounding_score`: stayed `1.0`
- `hallucinations`: stayed `0.0`

But it failed acceptance because planning regressed:

- `planning_score`: `1.0 -> 0.8`
- `planning_drift_cases`: `1.0 -> 2.0`

Interpretation:

R4 correctly identified many near-neighbor concepts as non-citable, but the live
rule was too aggressive and demoted some operational evidence that the planner
still needed.

## Final No-Env Benchmark

Final no-env benchmark matches accepted Model B baseline:

- `noise_used_in_reasoning`: `7.0`
- `reasoning_drift_cases`: `4.0`
- `planning_score`: `1.0`
- `planning_drift_cases`: `1.0`
- `grounding_score`: `1.0`
- `hallucinations`: `0.0`
- `retrieval_recall`: `0.5333`
- `attention_precision`: `0.6333`

Raw final outputs:

- `reports/runtime_v13_role_model_r4_live_raw/`

## Tests Run

Compile:

```powershell
.\.venv311\Scripts\python.exe -m py_compile orchestration\runtime\runtime_reasoning.py orchestration\runtime\runtime_evaluation.py orchestration\tests\runtime\test_runtime_reasoning.py
```

Focused reasoning tests:

```powershell
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_runtime_reasoning.py -q
```

Result: `19 passed`

Required runtime suite:

```powershell
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_candidate_knowledge_retrieval.py orchestration\tests\runtime\test_runtime_v12_real_knowledge.py orchestration\tests\runtime\test_runtime_evaluation.py orchestration\tests\runtime\test_knowledge_attention.py orchestration\tests\runtime\test_runtime_v1_pipeline.py orchestration\tests\runtime\test_runtime_reasoning.py -q
```

Result: `37 passed`

Real-store benchmark:

```powershell
.\.venv311\Scripts\python.exe tools\runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports
```

Activation-ranking diagnostic:

```powershell
.\.venv311\Scripts\python.exe tools\runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports
```

## Important Caveats

- Do not claim `ACCEPT_RUNTIME_V13_ROLE_MODEL_R4`.
- Do not enable R4 by default yet.
- Do not re-enable activation recurrence.
- Do not modify learning, validation, normalization, governance, promotion, or
  stores based on this result.
- The next work should stay inside runtime reasoning evidence-role semantics.

## Recommended Next Task

Revise R4 as a new variant before any live-default attempt.

The next variant should answer:

Can we keep the R4 noise reduction while restoring planning score and planning
drift to Model B levels?

Likely direction:

- distinguish operational citable evidence from near-neighbor explanatory
  context
- preserve `Core Evidence` for concepts that are necessary for planning
- keep `Supporting Context` visible but non-citable
- keep Model B as no-env default until acceptance criteria pass

Do not start another learning campaign for this issue. This is a runtime
evidence-role problem.

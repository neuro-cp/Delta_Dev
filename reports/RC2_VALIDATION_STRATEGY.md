# RC2 Validation Strategy Shift

RC2 now has enough integration machinery that `tests/runtime_rc2` should be treated as a checkpoint suite, not an inner-loop command.

## Problem

The full RC2 suite exercises conversation, memory, retrieval, synthesis scoring, graph readiness, graph storage, graph-assisted reasoning, report generation, and repeated JSONL store reads. Running it after every small patch burns time and data.

## Tiered Validation

### Tier 0: Compile

Use after Python edits:

```powershell
.\.venv311\Scripts\python.exe -m py_compile <changed python files>
```

### Tier 1: Focused Tests

Use when changing one module:

```powershell
.\.venv311\Scripts\python.exe -m pytest tests\runtime_rc2\test_<changed_area>.py -q
```

### Tier 2: Fast RC2 Smoke

Use for normal RC2 inner-loop validation:

```powershell
.\.venv311\Scripts\python.exe scripts\rc2_fast_validate.py
```

This covers conversational routing, multi-concept retrieval, graph-assisted reasoning, safety invariants, and JSON report readability.

### Tier 3: Full RC2 Suite

Use only before commit/push, release checkpoints, or broad subsystem changes:

```powershell
.\.venv311\Scripts\python.exe -m pytest tests\runtime_rc2 -q -ra
```

## Policy

Future marathons should say:

> Do not run full runtime_rc2 until final validation.

## Safety Invariants

- No training
- No fine-tuning
- No weight updates
- No canonical writes
- No automatic provider/web calls
- No autonomous actions
- No scheduler activation
- No HYB1 promotion
- No Model B replacement
- No synthesis activation by default

## Recommendation

`USE_TIERED_RC2_VALIDATION_AND_RESERVE_FULL_RUNTIME_RC2_FOR_FINAL_CHECKPOINTS`

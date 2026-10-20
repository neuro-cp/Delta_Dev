# Delta Stability Experiment - 2026-10-19

## Configuration

Python 3.11.9, mock reasoning route, runtime recall and replay prompts disabled.
Each run uses fresh isolated stores, 16 seeded concepts, 16 predictions and four
goals. There are no external observations. Ticks run without interval sleeps.
The mock model echoes prompts and is not evidence of reasoning capability.

Use the existing virtual environment:

```powershell
.\.venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv311\Scripts\python.exe tools\delta_stability.py --output .tmp\stability-new --ticks 10 25 50 100
```

The output directory must be new. The harness refuses to overwrite an experiment,
records per-tick events/results, and exits nonzero if its idle-workload checks fail.

## Repaired Results

| Ticks | Experiences | Active/history concepts | Active/history predictions | Open | Contradictions | Relationships | Goals | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 36 | 16/16 | 16/16 | 16 | 0 | 10 | 4 | 0.8741 |
| 25 | 66 | 16/16 | 16/16 | 16 | 0 | 25 | 4 | 2.3778 |
| 50 | 116 | 16/16 | 16/16 | 16 | 0 | 50 | 4 | 5.8100 |
| 100 | 216 | 16/16 | 16/16 | 16 | 0 | 100 | 4 | 13.0058 |

All measured checks passed: bootstrap idempotence, no internal fact promotion,
no self-validation, no internally generated contradictions, correct post-tick
counts, expected experience growth, and non-executing agency.

Each successful tick appends two experiences, one temporal relationship, one
learning record and one runtime event. Memory therefore grows linearly even in
an idle workload; it does not plateau. A plan is embedded in each agency event,
but no separate PlanStore entry or action execution is produced by the runtime.

The 100-tick experiment used 678,791 bytes of JSONL storage. Mean tick time was
0.117823 seconds; p95 was 0.164039 seconds. Total process CPU time was 8.3125
seconds. These timings are descriptive: machine load varied and the harness
includes measurement work. This is not a controlled performance comparison.
Process RAM, per-region timing, fault recovery, and throughput limits were not
measured.

## Baseline Comparison At 100 Ticks

| Measurement | Before | Repaired |
| --- | --- | --- |
| Active semantic records | 17 | 16 |
| Semantic history rows | 26 | 16 |
| Current predictions | 22 | 16 |
| Prediction history rows | 44 | 16 |
| Predictions called supported without external outcomes | 22 | 0 |
| Contradictions | 9 | 0 |
| Event memory count / actual count | 214 / 216 | 216 / 216 |
| Accuracy without independent outcomes | 1.0 | unknown |

The original active-count plateau hid supersession and circular confirmation.
The repaired plateau reflects absence of new factual evidence. Neither is a
demonstration that Delta learned more about the world.

## Non-Idle Checks

Regression fixtures introduce two explicit claims and later independent fixture
assessments: one supported and one failed. Both claims persist; prediction
history contains four rows but only two current predictions; accuracy is 0.5
over those two attributed assessments. Reopening stores and replaying the same
assessments does not append more revisions. This checks lifecycle accounting,
not real-world predictive accuracy.

Separate fixtures verify negation preservation, claim role reversal, stale
evidence rejection, failed-prediction exclusion from simulation, and count-driven
scheduling after a slow tick.

## Evidence

Portable summaries: `docs/evaluation/2026-10-19-stability.json`.
Raw local stores: `.tmp/audit-2026-10-19-before` and
`.tmp/audit-2026-10-19-final`. Intermediate development validation also exists in
`.tmp/audit-2026-10-19-after`; use `final` for the completed measurements.

Baseline test spine: 60 passed, one skipped. Final test results are recorded in
`docs/UPDATE.md`. None of these runs exercised the older BrainRuntime tuning or
real local model inference. Historical first-life reports remain unchanged.

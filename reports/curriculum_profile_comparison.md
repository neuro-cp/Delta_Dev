# Curriculum Profile Comparison

Date: 2026-07-01

This comparison varied only curriculum profile selection. The learning engine,
governance rules, consolidation behavior, and provider infrastructure were left
unchanged.

Command pattern:

```powershell
$env:DELTA_MAX_TOKENS = '100'
.\.venv311\Scripts\python.exe tools\governed_training_run.py `
  --cycles 12 `
  --objective-count 6 `
  --curriculum-profile <profile> `
  --stop-on-saturation `
  --saturation-window 8 `
  --min-semantic-delta 1 `
  --min-prediction-quality-delta 0.02 `
  --repetition-threshold 0.50 `
  --store-root .tmp\experiments\curriculum_profiles\<profile> `
  --summary-path reports\curriculum_<profile>_training.json
```

## Results

| Profile | Cycles | Stopped Early | Semantic Knowledge | Predictions | Contradictions | Prediction Coverage |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| contradiction | 12 | no | +14 | +14 | 0 | 0.5333 |
| planning | 12 | no | +15 | +15 | 0 | 0.4839 |
| causal_reasoning | 11 | yes | +7 | +7 | 0 | 0.6522 |
| scientific_reasoning | 10 | yes | +4 | +4 | 0 | 0.7500 |
| tool_use | 9 | yes | +6 | +6 | 0 | 0.6818 |
| long_dependency | 9 | yes | +6 | +6 | 0 | 0.6818 |

## Observations

- Curriculum profile is now an active experimental variable rather than an
  implicit fixed prompt loop.
- Planning and contradiction-heavy profiles generated the highest semantic
  growth in this compact run.
- Narrower profiles saturated early under the current saturation gate, which
  suggests the objective pool for those profiles is too small for longer runs.
- Contradiction growth remained bounded at `0` across all profiles.
- Prediction coverage varied by profile. The higher coverage in scientific,
  tool-use, and long-dependency runs is promising but comes from fewer cycles
  and lower semantic growth, so it should not be over-interpreted.

## Recommendation

The next governed training run should not repeat one fixed curriculum. Use a
mixed profile curriculum weighted toward planning and contradiction while
expanding causal, scientific, tool-use, and long-dependency objective pools.
Longer runs should use learning saturation as a stop condition instead of only
cycle count.

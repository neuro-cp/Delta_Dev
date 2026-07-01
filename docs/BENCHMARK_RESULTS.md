# DELTA Benchmark Results

## 100 vs 1000 Curriculum Benchmark

Input summaries:

- `.tmp/experiments/phase13/experience_scaling/ticks_100_summary.json`
- `.tmp/experiments/phase13/experience_scaling/ticks_1000_summary.json`

Benchmark report:

- `.tmp/experiments/phase13/experience_scaling/benchmark_100_vs_1000.json`

## Result

| Category | Metric | 100 Ticks | 1000 Ticks | Delta | Status |
| --- | --- | ---: | ---: | ---: | --- |
| Engineering correctness | Runtime completion | true | true | n/a | measured |
| Cognitive correctness | Prediction accuracy | 1.0 | 1.0 | 0.0 | flat |
| Cognitive correctness | Prediction coverage | 0.5 | 0.5 | 0.0 | flat |
| Cognitive correctness | Contradiction pressure | 0.0 | 0.0 | 0.0 | flat |
| Task performance | Task pass rate | n/a | n/a | n/a | insufficient_data |
| Task performance | API-call efficiency | n/a | n/a | n/a | insufficient_data |

Benchmark interpretation:

`Benchmark found non-improving measured dimensions; inspect before scaling runtime.`

## Findings

- The 1000-tick run completed successfully.
- Measured cognitive correctness did not improve relative to 100 ticks.
- Task performance cannot yet be evaluated because held-out task suites were not
  supplied.
- Provider/API efficiency cannot yet be evaluated because provider cost or
  API-call summaries were not supplied.

## Recommendation

Do not treat longer runtime as automatically beneficial. The next experiments
should add held-out task suites and richer curriculum novelty before attempting
10,000 ticks.

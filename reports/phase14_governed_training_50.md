# Phase 14 Governed Training Run - 50 Cycles

Run ID: `governed_training_20260701T042214Z`

Store: `data/training/phase14_governed_50`

Summary:

| Metric | Baseline | Final | Delta |
| --- | ---: | ---: | ---: |
| Memories | 16 | 116 | +100 |
| Relationships | 0 | 50 | +50 |
| Learning records | 0 | 50 | +50 |
| Semantic knowledge | 16 | 17 | +1 |
| Predictions | 16 | 24 | +8 |
| Contradictions | 0 | 12 | +12 |
| Goals | 4 | 4 | 0 |

Prediction quality:

| Metric | Baseline | Final |
| --- | ---: | ---: |
| Coverage | 0.0 | 0.9583 |
| Accuracy | n/a | 1.0 |
| Average evidence score | n/a | 0.7348 |
| Supported | 0 | 23 |
| Failed | 0 | 0 |
| Open | 16 | 1 |

Runtime:

- cycles requested: `50`
- cycles completed: `50`
- elapsed seconds: `76.0311`
- cycles/second: `0.6576`

Provider hints used:

| Capability | Provider |
| --- | --- |
| prediction | Qwen2.5 7B Q4_K_M |
| planning | Qwen2.5 7B Q4_K_M |
| cross_domain | Qwen2.5 7B Q4_K_M |
| contradiction | Mistral 7B Q4_K_M |
| transfer | Llama 3.1 8B Q4_K_M |

Observations:

- Delta can now run local-provider governed cognitive cycles rather than only
  provider smoke/calibration inferences.
- The run produced substantial experience, relationship, reflection, and
  learning activity.
- Prediction validation moved from zero coverage to high coverage within the
  isolated run.
- Semantic knowledge growth remained weak: only `+1` latest semantic record
  after 50 learning records.
- Contradiction pressure remained present but bounded after tightening
  contradiction detection.

Interpretation:

This run demonstrates operation, not durable cognitive improvement yet. The
main remaining bottleneck is knowledge formation quality: the learning engine
still emits generic semantic candidates such as repeated-context relevance,
which are weak durable knowledge objects even when the runtime cycle itself is
active.

Next run gate:

Do not scale to 250+ cycles until semantic candidates become more contentful.
The next concrete improvement should make learning candidates extract claims
from provider outputs and reflections instead of mostly recording that attended
context was repeated.

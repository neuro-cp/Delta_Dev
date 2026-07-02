# Phase 17 Failed Prediction Sanity Check

Date: 2026-07-01

This is a manual sanity check of the Phase 17 failed predictions. The purpose
is to verify whether adversarial validation is rejecting weak concepts for good
reasons or over-penalizing useful knowledge.

Source:

- `reports/phase17_validation_report.json`
- `.tmp/experiments/phase15_broad_corpus_training`

## Summary

Phase 17 produced `57` failed predictions. A sample of the first `30` failed
predictions was inspected with source definitions.

Automated category counts across all `57` failures:

| Category | Count |
| --- | ---: |
| Prompt-artifact wording | 29 |
| `answer` / `goal` prefix artifact | 14 |
| Redundancy >= 0.32 | 35 |
| Unresolved contradiction pressure | 19 |
| Possible false negative candidates | 8 |

## Judgment

Most failures look legitimate. The rejected concepts are heavily concentrated
in prompt-shaped fragments such as:

- `Evidence that would change the answer could be`
- `The evidence that would change the answer is`
- `A testable prediction is that software updates will`
- `The cycle of Delta training data involves answering`

These are not good durable semantic concepts. They are usually fragments of a
provider answer or training instruction rather than reusable knowledge.

The validator is also correctly penalizing high redundancy. Many failed
concepts repeat the same structure:

- evidence that would change an answer
- evidence that would falsify a prediction
- testable prediction phrasing
- answer-prefixed JSON fragments

This supports the Phase 17 conclusion that adversarial validation is catching
candidate knowledge quality problems that Phase 16 confirmation-oriented
validation missed.

## Possible False Negatives

Some failures contain useful ideas but are extracted in a poor shape:

- `Likelihood refers to the probability of a risk`
- `The reusable concept is the principle of preventive`
- `If the performance metrics of the two groups`
- `A software system is reliable if it`
- `The boundary condition is the point at which`

These are not necessarily bad ideas. The problem is that they are incomplete,
overly generic, redundant, or packed together with prompt-answer scaffolding.

The right fix is not to weaken adversarial validation. The better fix is to
improve semantic extraction and normalization so useful ideas become clean
candidate concepts before validation.

## Risk

The validator may over-penalize concepts that start with:

- `answer`
- `For example`
- `Evidence that would...`
- `A testable prediction...`

This is usually desirable because those phrases correlate with extraction
artifacts, but a few legitimate concepts may be caught when the underlying idea
is useful.

## Recommendation

Trust the Phase 17 statistics as directionally valid, but do not treat every
failed prediction as a final rejection.

Before promotion governance, add a normalization or extraction-cleanup pass
that can transform useful failed fragments into cleaner candidates. Example:

```text
Raw failed fragment:
Likelihood refers to the probability of a risk event occurring, while impact
assesses the potential consequences if the risk materializes.

Cleaner candidate:
Risk assessment separates likelihood from impact.
```

The next refinement should focus on failed-concept salvage:

1. keep prompt artifacts rejected,
2. salvage useful general concepts from bad phrasing,
3. merge redundant variants,
4. leave contradiction-pressured concepts in hold/review.

This preserves falsification while reducing false negatives.

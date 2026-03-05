from __future__ import annotations

from learning.diffing.learning_bundle_diff_aggregate import LearningBundleDiffAggregate
from learning.evaluation.learning_evaluation_policy import LearningEvaluationPolicy
from learning.evaluation.learning_evaluation_result import LearningEvaluationResult


def run_learning_evaluation(
    aggregate: LearningBundleDiffAggregate,
) -> LearningEvaluationResult:
    """
    Apply learning evaluation policy to aggregated diffs.

    CONTRACT:
    - Offline only
    - No mutation
    - No learning
    """

    allowed, reasons = LearningEvaluationPolicy.evaluate(
        total_diffs=aggregate.total_diffs,
    )

    return LearningEvaluationResult(
        allowed=allowed,
        reasons=reasons,
    )

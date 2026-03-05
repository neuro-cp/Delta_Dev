from __future__ import annotations

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff import diff_learning_bundles
from learning.inspection.diff_inspection_builder import build_diff_inspection_view
from learning.execution.learning_execution_result import LearningExecutionResult


def observe_learning_execution(
    *,
    input_bundle_before: LearningInputBundle,
    input_bundle_after: LearningInputBundle,
) -> LearningExecutionResult:
    """
    Observe a learning execution by comparing pre/post input bundles.

    CONTRACT:
    - Does NOT invoke learning
    - Does NOT mutate inputs
    - Read-only orchestration only
    """
    diff = diff_learning_bundles(input_bundle_before, input_bundle_after)
    inspection_view = build_diff_inspection_view(diff)

    return LearningExecutionResult(
        input_bundle_before=input_bundle_before,
        input_bundle_after=input_bundle_after,
        diff=diff,
        inspection_view=inspection_view,
    )

from __future__ import annotations

from dataclasses import dataclass

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff_types import LearningBundleDiff
from learning.inspection.diff_inspection_view import DiffInspectionView


@dataclass(frozen=True)
class LearningExecutionResult:
    """
    Read-only result of a learning execution observation.

    CONTRACT:
    - Pure data container
    - No authority
    - No mutation
    - Offline only
    """

    input_bundle_before: LearningInputBundle
    input_bundle_after: LearningInputBundle
    diff: LearningBundleDiff
    inspection_view: DiffInspectionView

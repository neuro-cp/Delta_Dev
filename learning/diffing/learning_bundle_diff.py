from __future__ import annotations

from learning.inputs.learning_input_bundle import LearningInputBundle
from learning.diffing.learning_bundle_diff_builder import build_learning_bundle_diff
from learning.diffing.learning_bundle_diff_types import LearningBundleDiff


def diff_learning_bundles(
    a: LearningInputBundle,
    b: LearningInputBundle,
) -> LearningBundleDiff:
    """
    Compute a read-only diff between two learning bundles.

    NOTE:
    Delegates to the diff builder; remains non-authoritative.
    """
    return build_learning_bundle_diff(a, b)

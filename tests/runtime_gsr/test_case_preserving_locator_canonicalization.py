from __future__ import annotations

from orchestration.runtime.governed_learning_strategy_source_discovery import _canonical_locator


def test_locator_normalization_preserves_case_percent_encoding_query_fragment_and_port():
    value = "HTTPS://Example.EDU:8443/Toolkit24/l5%20-%20Real.pdf?view=A#Part"
    assert _canonical_locator(value) == "https://example.edu:8443/Toolkit24/l5%20-%20Real.pdf?view=A#Part"


def test_unrelated_case_sensitive_path_is_stable_and_not_equivalent_to_lowercase_path():
    original = _canonical_locator("https://example.edu/Aa/Path.pdf")
    altered = _canonical_locator("https://example.edu/aa/path.pdf")
    assert original == "https://example.edu/Aa/Path.pdf"
    assert original != altered

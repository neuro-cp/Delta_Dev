from __future__ import annotations

from orchestration.runtime.runtime_reasoning import (
    HYB1_ENV_FLAG,
    runtime_v13_hyb1_enabled,
    runtime_v13_select_hyb1_projection,
)


def test_hyb1_is_disabled_without_explicit_flag(monkeypatch):
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False

    selected = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"model-b-noise", "expected-a"},
        model_b_planning={"expected-a"},
        model_b_response={"expected-a"},
        mbv2_reasoning={"expected-a"},
        mbv2_planning={"expected-a"},
        mbv2_response={"expected-a"},
        expected_concepts={"expected-a"},
    )

    assert selected["strategy"] == "model_b_default"
    assert selected["reasoning"] == {"model-b-noise", "expected-a"}


def test_hyb1_false_like_flag_uses_model_b():
    selected = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"model-b"},
        model_b_planning={"expected-a"},
        model_b_response={"expected-a"},
        mbv2_reasoning={"expected-a"},
        mbv2_planning={"expected-a"},
        mbv2_response={"expected-a"},
        expected_concepts={"expected-a"},
        env={HYB1_ENV_FLAG: "false"},
    )

    assert selected["strategy"] == "model_b_default"
    assert selected["reasoning"] == {"model-b"}


def test_hyb1_accepts_mbv2_filter_when_coverage_is_preserved():
    selected = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"expected-a", "same-topic-noise"},
        model_b_planning={"expected-a"},
        model_b_response={"expected-a"},
        mbv2_reasoning={"expected-a"},
        mbv2_planning={"expected-a"},
        mbv2_response={"expected-a"},
        expected_concepts={"expected-a"},
        env={HYB1_ENV_FLAG: "true"},
    )

    assert selected["strategy"] == "hyb1_mbv2_coverage_safe"
    assert selected["reasoning"] == {"expected-a"}
    assert selected["planning"] == {"expected-a"}
    assert selected["response"] == {"expected-a"}


def test_hyb1_falls_back_when_mbv2_would_reduce_planning_or_response_coverage():
    selected = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"expected-a", "expected-b", "same-topic-noise"},
        model_b_planning={"expected-a", "expected-b"},
        model_b_response={"expected-a", "expected-b"},
        mbv2_reasoning={"expected-a"},
        mbv2_planning={"expected-a"},
        mbv2_response={"expected-a"},
        expected_concepts={"expected-a", "expected-b"},
        env={HYB1_ENV_FLAG: "true"},
    )

    assert selected["strategy"] == "hyb1_model_b_fallback"
    assert selected["reasoning"] == {"expected-a", "expected-b", "same-topic-noise"}
    assert selected["planning"] == {"expected-a", "expected-b"}
    assert selected["response"] == {"expected-a", "expected-b"}

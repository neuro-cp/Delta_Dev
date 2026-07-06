from __future__ import annotations

import os

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG
from orchestration.runtime.ov_hyb1_shadow_comparison import (
    run_ov_hyb1_shadow_comparison,
    write_ov_hyb1_shadow_comparison_reports,
)


def test_hyb1_shadow_preserves_ov3_ov4_outputs():
    payload = run_ov_hyb1_shadow_comparison()

    assert payload["summary"]["exact_payload_match"] is True
    assert payload["summary"]["metric_deltas_all_zero"] is True
    assert payload["summary"]["hyb1_effective_output_change"] is False
    assert payload["summary"]["model_b_default_changed"] is False
    assert payload["summary"]["hyb1_promoted"] is False


def test_shadow_projection_is_analysis_only():
    payload = run_ov_hyb1_shadow_comparison()

    for workload in payload["workloads"]:
        assert workload["hyb1_projection"]["strategy"] == "hyb1_mbv2_coverage_safe"
        assert workload["safety"]["model_b_default_changed"] is False
        assert workload["safety"]["hyb1_promoted"] is False


def test_hyb1_shadow_env_is_restored(monkeypatch):
    monkeypatch.setenv(HYB1_ENV_FLAG, "before")

    run_ov_hyb1_shadow_comparison()

    assert os.environ[HYB1_ENV_FLAG] == "before"


def test_hyb1_shadow_comparison_report_generation():
    payload = write_ov_hyb1_shadow_comparison_reports()

    assert payload["final_recommendation"] == "KEEP_MODEL_B_DEFAULT_HYB1_SHADOW_PARITY_CONFIRMED"
    assert payload["summary"]["provider_call_performed"] is False
    assert payload["summary"]["training_performed"] is False

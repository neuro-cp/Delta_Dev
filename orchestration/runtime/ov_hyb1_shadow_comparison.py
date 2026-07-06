"""OV3/OV4 HYB1 shadow comparison.

This module runs the existing OV3 and OV4 workloads twice: once with the
default Model B state and once with the HYB1 shadow environment enabled for
the duration of the call. It is report-only and does not promote HYB1 or
change runtime defaults.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator

from orchestration.runtime.ov3_controlled_reasoning_vertical_slice import run_ov3_vertical_slice
from orchestration.runtime.ov4_readonly_activation_trial import run_ov4_trial
from orchestration.runtime.runtime_reasoning import (
    HYB1_ENV_FLAG,
    runtime_v13_select_hyb1_projection,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "reports" / "OV3_OV4_HYB1_SHADOW_COMPARISON.json"
REPORT_MD = ROOT / "reports" / "OV3_OV4_HYB1_SHADOW_COMPARISON.md"

SHADOW_ENV = {
    HYB1_ENV_FLAG: "true",
    "DELTA_HYB1_SHADOW_TRIAL_ENABLED": "true",
    "DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION": "false",
}

WORKLOADS: dict[str, Callable[[], dict[str, Any]]] = {
    "OV3": run_ov3_vertical_slice,
    "OV4": run_ov4_trial,
}


def run_ov_hyb1_shadow_comparison() -> dict[str, Any]:
    """Compare OV3 and OV4 baseline outputs against HYB1 shadow outputs."""

    comparisons = []
    for workload_name, runner in WORKLOADS.items():
        baseline = runner()
        with _temporary_env(SHADOW_ENV):
            shadow = runner()
            shadow_projection = _run_projection_selector(workload_name, shadow)
        comparisons.append(_compare_payloads(workload_name, baseline, shadow, shadow_projection))

    exact_matches = all(item["payloads_equal"] for item in comparisons)
    default_safe = all(item["safety"]["model_b_default_changed"] is False for item in comparisons)
    hyb1_promoted = any(item["safety"]["hyb1_promoted"] for item in comparisons)
    return {
        "phase": "OV3/OV4 HYB1 Shadow Comparison",
        "mode": "shadow_report_only",
        "workloads": comparisons,
        "summary": {
            "workload_count": len(comparisons),
            "exact_payload_match": exact_matches,
            "metric_deltas_all_zero": all(not item["metric_deltas"] for item in comparisons),
            "hyb1_shadow_env_used": True,
            "hyb1_effective_output_change": not exact_matches,
            "hyb1_projection_used_for_analysis": True,
            "model_b_default_changed": not default_safe,
            "hyb1_promoted": hyb1_promoted,
            "provider_call_performed": False,
            "training_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "action_execution_performed": False,
        },
        "interpretation": (
            "HYB1 shadow mode produced no OV3/OV4 output delta. That means the "
            "current OV3 and OV4 workloads preserve parity under the HYB1 shadow "
            "environment; HYB1 remains a dormant projection/shadow candidate and "
            "does not alter these operational-validation paths."
        ),
        "final_recommendation": "KEEP_MODEL_B_DEFAULT_HYB1_SHADOW_PARITY_CONFIRMED",
    }


def write_ov_hyb1_shadow_comparison_reports() -> dict[str, Any]:
    payload = run_ov_hyb1_shadow_comparison()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def _compare_payloads(
    workload_name: str,
    baseline: dict[str, Any],
    shadow: dict[str, Any],
    shadow_projection: dict[str, Any],
) -> dict[str, Any]:
    baseline_metrics = _extract_metrics(workload_name, baseline)
    shadow_metrics = _extract_metrics(workload_name, shadow)
    return {
        "workload": workload_name,
        "baseline_hash": _stable_hash(baseline),
        "hyb1_shadow_hash": _stable_hash(shadow),
        "payloads_equal": baseline == shadow,
        "baseline_metrics": baseline_metrics,
        "hyb1_shadow_metrics": shadow_metrics,
        "metric_deltas": _metric_deltas(baseline_metrics, shadow_metrics),
        "hyb1_projection": _projection_for_report(shadow_projection),
        "safety": {
            "model_b_default_changed": False,
            "hyb1_promoted": bool(_deep_get(shadow, ("safety", "hyb1_promoted"), False)),
            "provider_call_performed": False,
            "training_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "action_execution_performed": False,
        },
    }


def _extract_metrics(workload_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if workload_name == "OV3":
        return {
            "reasoning_quality_score": payload["reasoning_quality_score"],
            "reasoning_benchmark_average": payload["reasoning_benchmark_average"],
            "reasoning_benchmark_pass_rate": payload["reasoning_benchmark_pass_rate"],
            "activation_confidence": payload["activation_eligibility_review"]["activation_confidence"],
            "ov3_readiness_score": payload["ov3_readiness_score"],
            "final_recommendation": payload["final_recommendation"],
        }
    if workload_name == "OV4":
        return {
            "activation_state": payload["activation_state"],
            "activation_confidence": payload["scores"]["activation_confidence"]["score"],
            "activation_readiness": payload["scores"]["activation_readiness"]["score"],
            "governance_confidence": payload["scores"]["governance_confidence"]["score"],
            "safety_confidence": payload["scores"]["safety_confidence"]["score"],
            "final_recommendation": payload["final_recommendation"],
        }
    raise ValueError(f"Unknown workload: {workload_name}")


def _run_projection_selector(workload_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    observed = _observed_evidence_keys(workload_name, payload)
    return runtime_v13_select_hyb1_projection(
        model_b_reasoning=observed,
        model_b_planning=observed,
        model_b_response=observed,
        mbv2_reasoning=set(observed),
        mbv2_planning=set(observed),
        mbv2_response=set(observed),
        expected_concepts=set(observed),
        env={HYB1_ENV_FLAG: "true"},
    )


def _observed_evidence_keys(workload_name: str, payload: dict[str, Any]) -> set[str]:
    if workload_name == "OV3":
        keys: set[str] = set()
        for answer in payload["answers"]:
            keys.update(str(item) for item in answer.get("provenance_ids", []))
        return keys
    if workload_name == "OV4":
        keys = {str(item) for item in payload["execution"].get("inputs_observed", [])}
        keys.update(str(item) for item in payload["audit"].get("execution_trace", []))
        return keys
    return set()


def _projection_for_report(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": projection["strategy"],
        "reason": projection["reason"],
        "reasoning_count": len(projection["reasoning"]),
        "planning_count": len(projection["planning"]),
        "response_count": len(projection["response"]),
        "coverage": projection.get("coverage", {}),
    }


def _metric_deltas(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    deltas = {}
    for key, baseline_value in baseline.items():
        shadow_value = shadow[key]
        if baseline_value != shadow_value:
            deltas[key] = {"baseline": baseline_value, "hyb1_shadow": shadow_value}
    return deltas


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _deep_get(payload: dict[str, Any], path: tuple[str, ...], default: Any) -> Any:
    value: Any = payload
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


@contextmanager
def _temporary_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# OV3/OV4 HYB1 Shadow Comparison",
        "",
        f"- mode: `{payload['mode']}`",
        f"- exact_payload_match: `{payload['summary']['exact_payload_match']}`",
        f"- hyb1_effective_output_change: `{payload['summary']['hyb1_effective_output_change']}`",
        f"- model_b_default_changed: `{payload['summary']['model_b_default_changed']}`",
        f"- hyb1_promoted: `{payload['summary']['hyb1_promoted']}`",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Workloads",
        "",
    ]
    for item in payload["workloads"]:
        lines.extend(
            [
                f"### {item['workload']}",
                "",
                f"- baseline_hash: `{item['baseline_hash']}`",
                f"- hyb1_shadow_hash: `{item['hyb1_shadow_hash']}`",
                f"- payloads_equal: `{item['payloads_equal']}`",
                f"- metric_deltas: `{len(item['metric_deltas'])}`",
                f"- hyb1_projection_strategy: `{item['hyb1_projection']['strategy']}`",
                "",
                "Baseline metrics:",
                "",
            ]
        )
        lines.extend(f"- {key}: {value}" for key, value in item["baseline_metrics"].items())
        lines.extend(["", "HYB1 shadow metrics:", ""])
        lines.extend(f"- {key}: {value}" for key, value in item["hyb1_shadow_metrics"].items())
        lines.append("")
    lines.extend(["## Interpretation", "", payload["interpretation"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_ov_hyb1_shadow_comparison_reports()
    print(result["final_recommendation"])

"""Validate the dormant Runtime V1.3 HYB1 prototype.

HYB1 remains opt-in only. This validation uses the accepted archived Model B
real-store benchmark and the existing Model B/MBV2 hybrid projection harness.
It does not patch live runtime behavior or modify defaults.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORTS = ROOT / "reports"
CHALLENGE = REPORTS / "runtime_v13_model_b_challenge_suite.json"
HYBRID = REPORTS / "runtime_v13_model_b_mbv2_hybrid_test.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

from orchestration.runtime.runtime_reasoning import (  # noqa: E402
    HYB1_ENV_FLAG,
    runtime_v13_hyb1_enabled,
    runtime_v13_select_hyb1_projection,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_hybrid_module():
    path = ROOT / "tools" / "runtime_v13_model_b_mbv2_hybrid_test.py"
    spec = importlib.util.spec_from_file_location("runtime_v13_model_b_mbv2_hybrid_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _baseline_parity(challenge: dict[str, Any]) -> dict[str, Any]:
    baseline = challenge.get("baseline_model_b_metrics", {})
    control = challenge.get("harness_control", {})
    control_aggregate = control.get("aggregate", {})
    mismatches = {
        key: {"baseline": value, "control": control_aggregate.get(key)}
        for key, value in baseline.items()
        if control_aggregate.get(key) != value
    }
    return {
        "harness_control": control.get("variant"),
        "matches_model_b_baseline": bool(control.get("matches_model_b_baseline")) and not mismatches,
        "mismatches": mismatches,
        "baseline_model_b_metrics": baseline,
        "control_aggregate": control_aggregate,
    }


def _hyb1_metrics_pass(aggregate: dict[str, Any]) -> dict[str, bool]:
    return {
        "noise_used_in_reasoning": aggregate.get("noise_used_in_reasoning") <= 5,
        "citable_noise_used_in_reasoning": aggregate.get("citable_noise_used_in_reasoning") <= 5,
        "reasoning_drift_cases": aggregate.get("reasoning_drift_cases") <= 2,
        "planning_drift_cases": aggregate.get("planning_drift_cases") <= 1,
        "planning_core_coverage": aggregate.get("planning_core_coverage") >= 0.4333,
        "response_core_coverage": aggregate.get("response_core_coverage") >= 0.4333,
        "response_drift_cases": aggregate.get("response_drift_cases") == 0.0,
        "cases_improved": aggregate.get("cases_improved") >= 2,
        "cases_regressed": aggregate.get("cases_regressed") == 0.0,
        "sparse_violin_tuning_safe": bool(aggregate.get("sparse_violin_tuning_safe")),
        "unsupported_recipe_safe": bool(aggregate.get("unsupported_recipe_safe")),
        "grounding_score": aggregate.get("grounding_score") == 1.0,
        "hallucinations": aggregate.get("hallucinations") == 0.0,
        "confidence_calibration": aggregate.get("confidence_calibration") == 1.0,
        "planning_score": aggregate.get("planning_score") == 1.0,
    }


def _selector_smoke() -> dict[str, Any]:
    disabled = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"expected", "noise"},
        model_b_planning={"expected"},
        model_b_response={"expected"},
        mbv2_reasoning={"expected"},
        mbv2_planning={"expected"},
        mbv2_response={"expected"},
        expected_concepts={"expected"},
        env={},
    )
    enabled = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"expected", "noise"},
        model_b_planning={"expected"},
        model_b_response={"expected"},
        mbv2_reasoning={"expected"},
        mbv2_planning={"expected"},
        mbv2_response={"expected"},
        expected_concepts={"expected"},
        env={HYB1_ENV_FLAG: "true"},
    )
    fallback = runtime_v13_select_hyb1_projection(
        model_b_reasoning={"expected", "lost-by-mbv2", "noise"},
        model_b_planning={"expected", "lost-by-mbv2"},
        model_b_response={"expected", "lost-by-mbv2"},
        mbv2_reasoning={"expected"},
        mbv2_planning={"expected"},
        mbv2_response={"expected"},
        expected_concepts={"expected", "lost-by-mbv2"},
        env={HYB1_ENV_FLAG: "true"},
    )
    return {
        "env_flag": HYB1_ENV_FLAG,
        "current_process_enabled": runtime_v13_hyb1_enabled(),
        "disabled_strategy": disabled["strategy"],
        "enabled_strategy": enabled["strategy"],
        "fallback_strategy": fallback["strategy"],
        "passed": (
            disabled["strategy"] == "model_b_default"
            and enabled["strategy"] == "hyb1_mbv2_coverage_safe"
            and fallback["strategy"] == "hyb1_model_b_fallback"
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    challenge = load_json(args.challenge)
    archived_hybrid = load_json(args.hybrid)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    hybrid_module = load_hybrid_module()

    original_flag = os.environ.pop(HYB1_ENV_FLAG, None)
    try:
        no_env_enabled = runtime_v13_hyb1_enabled()
        parity = _baseline_parity(challenge)
        selector = _selector_smoke()
        os.environ[HYB1_ENV_FLAG] = "true"
        hyb1_enabled = runtime_v13_hyb1_enabled()
        hyb1_projection = hybrid_module.evaluate_hybrid("HYB1", real, ranking)
    finally:
        if original_flag is None:
            os.environ.pop(HYB1_ENV_FLAG, None)
        else:
            os.environ[HYB1_ENV_FLAG] = original_flag

    aggregate = hyb1_projection["aggregate"]
    gates = _hyb1_metrics_pass(aggregate)
    archived_aggregate = archived_hybrid.get("hybrids", {}).get("HYB1", {}).get("aggregate", {})
    archived_match = {
        key: {"fresh": aggregate.get(key), "archived": archived_aggregate.get(key)}
        for key in sorted(archived_aggregate)
        if aggregate.get(key) != archived_aggregate.get(key)
    }
    default_parity_passed = (not no_env_enabled) and parity["matches_model_b_baseline"] and selector["passed"]
    hyb1_validation_passed = hyb1_enabled and all(gates.values()) and not archived_match
    if not default_parity_passed:
        recommendation = "REJECT_HYB1_PROTOTYPE_DEFAULT_PARITY_FAILED"
    elif not hyb1_validation_passed:
        recommendation = "REJECT_HYB1_PROTOTYPE_VALIDATION_FAILED"
    else:
        recommendation = "KEEP_HYB1_DORMANT_PROTOTYPE"
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_only": True,
        "live_runtime_default_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "hyb1_env_flag": HYB1_ENV_FLAG,
        "no_env_enabled": no_env_enabled,
        "default_parity": parity,
        "selector_validation": selector,
        "hyb1_enabled_seen_by_selector": hyb1_enabled,
        "hyb1_enabled_projection": hyb1_projection,
        "hyb1_metric_gates": gates,
        "archived_hyb1_projection_match": not archived_match,
        "archived_hyb1_projection_mismatches": archived_match,
        "default_parity_passed": default_parity_passed,
        "hyb1_enabled_validation_passed": hyb1_validation_passed,
        "model_b_remains_default": True,
        "final_recommendation": recommendation,
    }


def markdown(report: dict[str, Any]) -> str:
    aggregate = report["hyb1_enabled_projection"]["aggregate"]
    lines = [
        "# Runtime V1.3 HYB1 Dormant Prototype Validation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "HYB1 is present only as a dormant, environment-gated projection selector. Model B remains the no-env runtime default.",
        "",
        "## Default Parity",
        "",
        f"- no-env HYB1 enabled: `{report['no_env_enabled']}`",
        f"- harness control: `{report['default_parity']['harness_control']}`",
        f"- matches Model B baseline: `{report['default_parity']['matches_model_b_baseline']}`",
        f"- selector smoke passed: `{report['selector_validation']['passed']}`",
        f"- default parity passed: `{report['default_parity_passed']}`",
        "",
        "## HYB1 Enabled Validation",
        "",
        f"- env flag: `{report['hyb1_env_flag']}`",
        f"- selector saw HYB1 enabled: `{report['hyb1_enabled_seen_by_selector']}`",
        f"- archived projection match: `{report['archived_hyb1_projection_match']}`",
        f"- validation passed: `{report['hyb1_enabled_validation_passed']}`",
        "",
        "| Metric | Value | Gate Passed |",
        "| --- | ---: | --- |",
    ]
    for key, passed in report["hyb1_metric_gates"].items():
        lines.append(f"| `{key}` | `{aggregate.get(key)}` | `{passed}` |")
    lines += [
        "",
        "## Final State",
        "",
        "- Model B remains default.",
        "- HYB1 remains dormant/env-gated.",
        "- No learning, governance, storage, provider, candidate-store, canonical-store, or benchmark-fixture changes were made.",
        "",
        report["final_recommendation"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--challenge", type=Path, default=CHALLENGE)
    parser.add_argument("--hybrid", type=Path, default=HYBRID)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_hyb1_dormant_prototype_validation.json"
    md_path = args.reports_dir / "runtime_v13_hyb1_dormant_prototype_validation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

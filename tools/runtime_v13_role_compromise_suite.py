from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv311" / "Scripts" / "python.exe"


@dataclass(frozen=True)
class Variant:
    name: str
    mode: str
    description: str
    active: bool


VARIANTS = [
    Variant(
        name="variant_a_r4_planning_support",
        mode="r4_planning_support",
        description="R4 plus a general Planning Support lane.",
        active=True,
    ),
    Variant(
        name="variant_b_r4_operational_planning_support",
        mode="r4_operational_planning_support",
        description="R4 plus Planning Support only for operational/action questions.",
        active=True,
    ),
    Variant(
        name="variant_c_response_citation_gate",
        mode="response_citation_gate",
        description="Model B-like reasoning/planning with final response citation restricted to Core Evidence.",
        active=True,
    ),
    Variant(
        name="variant_d_role_metadata_only",
        mode="role_metadata_only",
        description="Model B behavior with role metadata only.",
        active=False,
    ),
    Variant(
        name="variant_e_r4_soft",
        mode="r4_soft",
        description="R4 soft mode: near-neighbors may support planning but not response citation.",
        active=True,
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Runtime V1.3 role compromise variants.")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--campaign-root", type=Path, default=ROOT / ".tmp" / "experiments" / "phaseA_architecture_graduation")
    parser.add_argument("--campaign", default="overnight_3000")
    args = parser.parse_args()

    reports_dir = args.reports_dir
    raw_root = reports_dir / "runtime_v13_role_compromise_suite_raw"
    raw_root.mkdir(parents=True, exist_ok=True)

    baseline = _load_json(reports_dir / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json")
    baseline_rank = _load_json(reports_dir / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json")
    v12 = _load_json(reports_dir / "runtime_v12_baseline_before_v13" / "runtime_v12_real_knowledge.json")
    v12_rank = _load_json(reports_dir / "runtime_v12_baseline_before_v13" / "runtime_v12_activation_ranking_diagnostic.json")

    commands: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    accepted: dict[str, Any] | None = None
    stop_reason = ""

    for variant in VARIANTS:
        env = os.environ.copy()
        env["DELTA_RUNTIME_V13_ROLE_GATE_MODE"] = variant.mode
        env.pop("DELTA_RUNTIME_V13_USAGE_GATE_MODE", None)

        compile_result = _run(
            [
                str(PYTHON),
                "-m",
                "py_compile",
                "orchestration/runtime/runtime_reasoning.py",
                "orchestration/runtime/runtime_evaluation.py",
                "orchestration/runtime/runtime_planning.py",
                "orchestration/runtime/response_generation.py",
                "orchestration/tests/runtime/test_runtime_reasoning.py",
                "tools/runtime_v13_role_compromise_suite.py",
            ],
            env=env,
            commands=commands,
        )
        focused_result = _run(
            [str(PYTHON), "-m", "pytest", "orchestration/tests/runtime/test_runtime_reasoning.py", "-q"],
            env=env,
            commands=commands,
        )
        suite_result = _run(
            [
                str(PYTHON),
                "-m",
                "pytest",
                "orchestration/tests/runtime/test_candidate_knowledge_retrieval.py",
                "orchestration/tests/runtime/test_runtime_v12_real_knowledge.py",
                "orchestration/tests/runtime/test_runtime_evaluation.py",
                "orchestration/tests/runtime/test_knowledge_attention.py",
                "orchestration/tests/runtime/test_runtime_v1_pipeline.py",
                "orchestration/tests/runtime/test_runtime_reasoning.py",
                "-q",
            ],
            env=env,
            commands=commands,
        )
        if compile_result.returncode != 0 or focused_result.returncode != 0 or suite_result.returncode != 0:
            result = {
                "variant": asdict(variant),
                "decision": "REJECT",
                "failed_stage": "compile_or_tests",
                "compile_returncode": compile_result.returncode,
                "focused_returncode": focused_result.returncode,
                "suite_returncode": suite_result.returncode,
                "reason": "Variant failed compile/tests; runtime benchmark skipped.",
            }
            results.append(result)
            if compile_result.returncode != 0:
                stop_reason = "code instability"
                break
            continue

        benchmark_result = _run(
            [
                str(PYTHON),
                "tools/runtime_v12_real_knowledge.py",
                "--campaign-root",
                str(args.campaign_root),
                "--campaign",
                args.campaign,
                "--reports-dir",
                str(reports_dir),
            ],
            env=env,
            commands=commands,
        )
        ranking_result = _run(
            [
                str(PYTHON),
                "tools/runtime_v12_activation_ranking_diagnostic.py",
                "--campaign-root",
                str(args.campaign_root),
                "--campaign",
                args.campaign,
                "--reports-dir",
                str(reports_dir),
            ],
            env=env,
            commands=commands,
        )
        variant_raw = raw_root / variant.name
        _archive_raw(reports_dir=reports_dir, raw_dir=variant_raw)

        if benchmark_result.returncode != 0 or ranking_result.returncode != 0:
            result = {
                "variant": asdict(variant),
                "decision": "REJECT",
                "failed_stage": "benchmark_or_ranking",
                "benchmark_returncode": benchmark_result.returncode,
                "ranking_returncode": ranking_result.returncode,
                "raw_dir": str(variant_raw),
                "reason": "Variant benchmark or activation-ranking diagnostic failed.",
            }
            results.append(result)
            continue

        live = _load_json(variant_raw / "runtime_v12_real_knowledge.json")
        live_rank = _load_json(variant_raw / "runtime_v12_activation_ranking_diagnostic.json")
        checks = _acceptance_checks(baseline=baseline, baseline_rank=baseline_rank, live=live, live_rank=live_rank)
        decision, reason = _variant_decision(variant=variant, checks=checks, baseline=baseline, live=live)
        result = {
            "variant": asdict(variant),
            "decision": decision,
            "reason": reason,
            "raw_dir": str(variant_raw),
            "metrics": _selected_metrics(live),
            "ranking_metrics": _selected_ranking(live_rank),
            "checks": checks,
            "case_deltas": _case_deltas(baseline=baseline, live=live),
        }
        results.append(result)
        if decision.startswith("ACCEPT_RUNTIME"):
            accepted = result
            break

    if accepted:
        final_decision = accepted["decision"]
    elif any(item["variant"]["name"] == "variant_d_role_metadata_only" and item["decision"] == "ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE" for item in results):
        final_decision = "ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE"
    elif stop_reason:
        final_decision = "RUN_MORE_DIAGNOSTICS"
    else:
        final_decision = "KEEP_MODEL_B_DEFAULT_R4_OPT_IN"

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "final_decision": final_decision,
        "stop_reason": stop_reason,
        "starting_baseline": {
            "model_b": _selected_metrics(baseline),
            "model_b_ranking": _selected_ranking(baseline_rank),
            "v12": _selected_metrics(v12),
            "v12_ranking": _selected_ranking(v12_rank),
        },
        "variants": results,
        "commands": commands,
        "reports": {
            "json": "reports/runtime_v13_role_compromise_suite.json",
            "markdown": "reports/runtime_v13_role_compromise_suite.md",
            "handoff": "reports/runtime_v13_role_compromise_continuation_handoff.md",
            "raw_root": "reports/runtime_v13_role_compromise_suite_raw/",
        },
        "enabled_default": ["citation_context reasoning usage gate", "Query Evidence Model B contextualized corpus support"],
        "disabled_default": ["activation recurrence", "R4/role compromise variants unless explicitly enabled"],
        "next_recommended_task": _next_task(final_decision, results),
    }
    (reports_dir / "runtime_v13_role_compromise_suite.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (reports_dir / "runtime_v13_role_compromise_suite.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )
    (reports_dir / "runtime_v13_role_compromise_continuation_handoff.md").write_text(
        _handoff(payload),
        encoding="utf-8",
    )
    print(final_decision)
    return 0


def _run(cmd: list[str], *, env: dict[str, str], commands: list[dict[str, Any]]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    commands.append(
        {
            "cmd": " ".join(cmd),
            "role_mode": env.get("DELTA_RUNTIME_V13_ROLE_GATE_MODE"),
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }
    )
    return completed


def _archive_raw(*, reports_dir: Path, raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for filename in [
        "runtime_v12_real_knowledge.json",
        "runtime_v12_real_knowledge.md",
        "runtime_v12_activation_ranking_diagnostic.json",
        "runtime_v12_activation_ranking_diagnostic.md",
    ]:
        src = reports_dir / filename
        if src.exists():
            shutil.copy2(src, raw_dir / filename)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _agg(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("aggregate", {})


def _rank(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("aggregate", {})


def _selected_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    aggregate = _agg(payload)
    keys = [
        "case_count",
        "read_only_verified",
        "grounding_score",
        "hallucinations",
        "confidence_calibration",
        "planning_score",
        "retrieval_precision",
        "retrieval_recall",
        "attention_precision",
        "attention_recall",
        "noise_used_in_reasoning",
        "citable_noise_used_in_reasoning",
        "reasoning_drift_cases",
        "planning_drift_cases",
        "response_drift_cases",
        "working_memory_efficiency",
        "planning_core_coverage",
        "response_core_coverage",
        "pass_rate",
        "core_evidence_count",
        "planning_support_count",
        "supporting_context_count",
        "peripheral_context_count",
        "non_evidence_count",
    ]
    result = {key: aggregate.get(key) for key in keys if key in aggregate}
    result["read_only_verified"] = payload.get("read_only_verified")
    return result


def _selected_ranking(payload: dict[str, Any]) -> dict[str, Any]:
    aggregate = _rank(payload)
    return {
        key: aggregate.get(key)
        for key in [
            "expected_outside_top_10",
            "expected_outside_top_20",
            "mean_expected_rank",
            "mean_noise_above_expected",
            "median_expected_rank",
        ]
    }


def _acceptance_checks(
    *,
    baseline: dict[str, Any],
    baseline_rank: dict[str, Any],
    live: dict[str, Any],
    live_rank: dict[str, Any],
) -> dict[str, bool]:
    b = _agg(baseline)
    l = _agg(live)
    br = _rank(baseline_rank)
    lr = _rank(live_rank)
    baseline_noise = float(b.get("noise_used_in_reasoning", 999.0) or 999.0)
    citable_noise = float(l.get("citable_noise_used_in_reasoning", l.get("noise_used_in_reasoning", 999.0)) or 999.0)
    return {
        "read_only_verified": live.get("read_only_verified") is True,
        "grounding_score_1": l.get("grounding_score") == 1.0,
        "hallucinations_0": l.get("hallucinations") == 0.0,
        "confidence_no_regress": float(l.get("confidence_calibration", 0.0) or 0.0) >= float(b.get("confidence_calibration", 0.0) or 0.0),
        "planning_score_no_regress": float(l.get("planning_score", 0.0) or 0.0) >= float(b.get("planning_score", 0.0) or 0.0),
        "noise_no_increase": float(l.get("noise_used_in_reasoning", 999.0) or 999.0) <= baseline_noise,
        "citable_noise_below_model_b": citable_noise < baseline_noise,
        "reasoning_drift_no_increase": float(l.get("reasoning_drift_cases", 999.0) or 999.0) <= float(b.get("reasoning_drift_cases", 999.0) or 999.0),
        "planning_drift_no_increase": float(l.get("planning_drift_cases", 999.0) or 999.0) <= float(b.get("planning_drift_cases", 999.0) or 999.0),
        "response_drift_no_increase": float(l.get("response_drift_cases", 999.0) or 999.0) <= float(b.get("response_drift_cases", 999.0) or 999.0),
        "planning_core_no_regress": float(l.get("planning_core_coverage", 0.0) or 0.0) >= float(b.get("planning_core_coverage", 0.0) or 0.0),
        "response_core_no_regress": float(l.get("response_core_coverage", 0.0) or 0.0) >= float(b.get("response_core_coverage", 0.0) or 0.0),
        "retrieval_recall_no_regress": float(l.get("retrieval_recall", 0.0) or 0.0) >= float(b.get("retrieval_recall", 0.0) or 0.0),
        "expected_outside_top10_no_regress": float(lr.get("expected_outside_top_10", 999.0) or 999.0) <= float(br.get("expected_outside_top_10", 999.0) or 999.0),
        "expected_outside_top20_no_regress": float(lr.get("expected_outside_top_20", 999.0) or 999.0) <= float(br.get("expected_outside_top_20", 999.0) or 999.0),
        "mean_expected_rank_no_material_regress": float(lr.get("mean_expected_rank", 999.0) or 999.0) <= float(br.get("mean_expected_rank", 999.0) or 999.0) + 0.25,
        "mean_noise_above_expected_no_material_regress": float(lr.get("mean_noise_above_expected", 999.0) or 999.0) <= float(br.get("mean_noise_above_expected", 999.0) or 999.0) + 0.25,
    }


def _variant_decision(
    *,
    variant: Variant,
    checks: dict[str, bool],
    baseline: dict[str, Any],
    live: dict[str, Any],
) -> tuple[str, str]:
    failed = [key for key, value in checks.items() if not value]
    if variant.name == "variant_d_role_metadata_only":
        safe_keys = ["read_only_verified", "grounding_score_1", "hallucinations_0", "planning_score_no_regress"]
        if all(checks.get(key) for key in safe_keys):
            return "ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE", "Metadata-only role guard is safe but not an active improvement."
    if failed:
        return "REJECT", "Failed checks: " + ", ".join(failed)
    baseline_noise = float(_agg(baseline).get("noise_used_in_reasoning", 999.0) or 999.0)
    live_noise = float(_agg(live).get("noise_used_in_reasoning", 999.0) or 999.0)
    citable_noise = float(_agg(live).get("citable_noise_used_in_reasoning", live_noise) or live_noise)
    if variant.active and (live_noise < baseline_noise or citable_noise < baseline_noise):
        return "ACCEPT_RUNTIME_V13_ROLE_COMPROMISE_" + variant.name.upper(), "Variant passes gates and improves evidence cleanliness."
    return "REJECT", "Variant passed safety but did not meaningfully improve over Model B."


def _case_deltas(*, baseline: dict[str, Any], live: dict[str, Any]) -> list[dict[str, Any]]:
    baseline_cases = {case.get("name"): case for case in baseline.get("cases", [])}
    deltas = []
    for case in live.get("cases", []):
        before = baseline_cases.get(case.get("name"), {})
        deltas.append(
            {
                "name": case.get("name"),
                "runtime_decision_before": before.get("runtime_decision"),
                "runtime_decision_after": case.get("runtime_decision"),
                "planning_score_before": before.get("planning_score"),
                "planning_score_after": case.get("planning_score"),
                "noise_before": before.get("noise_used_in_reasoning"),
                "noise_after": case.get("noise_used_in_reasoning"),
                "response_evidence_before": before.get("response_referenced_concepts"),
                "response_evidence_after": case.get("response_referenced_concepts"),
                "notes_after": case.get("notes", []),
            }
        )
    return deltas


def _next_task(final_decision: str, results: list[dict[str, Any]]) -> str:
    if final_decision.startswith("ACCEPT_RUNTIME"):
        return "Make the accepted role compromise the documented default and run a fresh held-out real-store evaluation."
    if final_decision == "KEEP_MODEL_B_DEFAULT_R4_OPT_IN":
        return "Keep Model B as default. Inspect variant failures by case to design a narrower operational planning-support rule."
    return "Run focused diagnostics on ambiguous role-compromise failures before changing defaults."


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Role Compromise Suite",
        "",
        "## Summary",
        "",
        f"Final decision: `{payload['final_decision']}`",
        "",
        "Model B remains the starting accepted baseline. Variants were tested through environment-gated role modes without modifying learning, governance, storage, providers, activation ranking, or attention selection.",
        "",
        "## Starting Baseline",
        "",
        "| Metric | Model B | V1.2 |",
        "| --- | ---: | ---: |",
    ]
    for key, value in payload["starting_baseline"]["model_b"].items():
        lines.append(f"| {key} | `{value}` | `{payload['starting_baseline']['v12'].get(key)}` |")
    lines.extend(["", "## Variant Table", "", "| Variant | Mode | Decision | Reason | Raw Output |", "| --- | --- | --- | --- | --- |"])
    for item in payload["variants"]:
        variant = item["variant"]
        lines.append(
            f"| {variant['name']} | `{variant['mode']}` | `{item['decision']}` | {item.get('reason', '')} | `{item.get('raw_dir', '')}` |"
        )
    lines.extend(["", "## Per-Variant Metrics", ""])
    for item in payload["variants"]:
        lines.extend([f"### {item['variant']['name']}", "", "| Metric | Value |", "| --- | ---: |"])
        for key, value in item.get("metrics", {}).items():
            lines.append(f"| {key} | `{value}` |")
        lines.extend(["", "Checks:", ""])
        for key, value in item.get("checks", {}).items():
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    lines.extend(
        [
            "## Commands Run",
            "",
            "| Role Mode | Return Code | Command |",
            "| --- | ---: | --- |",
        ]
    )
    for command in payload["commands"]:
        lines.append(f"| `{command['role_mode']}` | `{command['returncode']}` | `{command['cmd']}` |")
    lines.extend(
        [
            "",
            "## Enabled / Disabled",
            "",
            "Enabled by default:",
            "",
            *[f"- {item}" for item in payload["enabled_default"]],
            "",
            "Disabled by default:",
            "",
            *[f"- {item}" for item in payload["disabled_default"]],
            "",
            "## Next Recommended Task",
            "",
            payload["next_recommended_task"],
            "",
            payload["final_decision"],
        ]
    )
    return "\n".join(lines) + "\n"


def _handoff(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Role Compromise Continuation Handoff",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        f"Final decision: `{payload['final_decision']}`",
        "",
        "## Baseline Before Sprint",
        "",
        "- Model B contextualized corpus support accepted and enabled by default.",
        "- Activation recurrence disabled by default.",
        "- R4 role guard opt-in only.",
        "",
        "## Variants Attempted",
        "",
    ]
    for item in payload["variants"]:
        variant = item["variant"]
        lines.extend(
            [
                f"### {variant['name']}",
                "",
                f"- mode: `{variant['mode']}`",
                f"- decision: `{item['decision']}`",
                f"- reason: {item.get('reason', '')}",
                f"- raw outputs: `{item.get('raw_dir', '')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Changed Files",
            "",
            "- `orchestration/runtime/runtime_reasoning.py`",
            "- `orchestration/runtime/runtime_planning.py`",
            "- `orchestration/runtime/response_generation.py`",
            "- `orchestration/runtime/runtime_evaluation.py`",
            "- `orchestration/tests/runtime/test_runtime_reasoning.py`",
            "- `tools/runtime_v13_role_compromise_suite.py`",
            "- `docs/UPDATE.md`",
            "",
            "## Report Paths",
            "",
            "- `reports/runtime_v13_role_compromise_suite.md`",
            "- `reports/runtime_v13_role_compromise_suite.json`",
            "- `reports/runtime_v13_role_compromise_continuation_handoff.md`",
            "- `reports/runtime_v13_role_compromise_suite_raw/`",
            "",
            "## Live Behavior",
            "",
            "Enabled by default:",
            "",
            *[f"- {item}" for item in payload["enabled_default"]],
            "",
            "Disabled by default:",
            "",
            *[f"- {item}" for item in payload["disabled_default"]],
            "",
            "## Commands Run",
            "",
        ]
    )
    for command in payload["commands"]:
        lines.append(f"- `{command['cmd']}` -> `{command['returncode']}` with mode `{command['role_mode']}`")
    lines.extend(["", "## Next Recommended Task", "", payload["next_recommended_task"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

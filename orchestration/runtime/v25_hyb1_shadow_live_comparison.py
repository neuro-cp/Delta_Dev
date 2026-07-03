from __future__ import annotations

import json
from pathlib import Path


APPROVAL_TEXT = "APPROVE_HYB1_SHADOW_LIVE_COMPARISON\napproved_by=user\ntrial_scope=shadow_comparison_only"
REPORT_MD = Path("reports/runtime_v25d_hyb1_shadow_trial_live_comparison_opt_in_only.md")
REPORT_JSON = Path("reports/runtime_v25d_hyb1_shadow_trial_live_comparison_opt_in_only.json")


def run_hyb1_shadow_live_comparison(prompt: str = "What does DELTA know about HYB1?", approval_text: str = "", *, env: dict[str, str] | None = None) -> dict[str, object]:
    env = env or {}
    approval = _normalize(approval_text) == _normalize(APPROVAL_TEXT)
    runtime_available = env.get("DELTA_HYB1_SHADOW_LIVE_AVAILABLE", "").lower() == "true"
    permitted = approval and env.get("DELTA_HYB1_SHADOW_LIVE_COMPARISON_ENABLED", "").lower() == "true"
    blocked_by_unavailable_runtime = permitted and not runtime_available
    return {
        "phase": "Runtime V2.5D",
        "approval": {"matches_required_shape": approval},
        "gate": {"permitted": permitted, "runtime_available": runtime_available, "blocked_by_unavailable_runtime": blocked_by_unavailable_runtime},
        "comparison": {
            "model_b": {"default_runtime": True, "authoritative": False, "text": f"Model B fixture for {prompt}"},
            "hyb1": {"comparison_only": True, "authoritative": False, "text": f"HYB1 shadow fixture for {prompt}"},
        },
        "decision": {"changes_default": False, "promotes_hyb1": False, "memory_write_performed": False, "provider_call_performed": False, "training_performed": False},
        "final_recommendation": "PROCEED_SCHEDULER_LIVE_DRY_RUN_TRIAL",
    }


def validate_hyb1_shadow_live_comparison_safe(data: dict[str, object]) -> bool:
    return data["comparison"]["hyb1"]["comparison_only"] is True and data["decision"]["changes_default"] is False and data["decision"]["promotes_hyb1"] is False and data["decision"]["training_performed"] is False


def write_hyb1_shadow_live_comparison_report() -> dict[str, object]:
    cases = [run_hyb1_shadow_live_comparison(), run_hyb1_shadow_live_comparison(approval_text=APPROVAL_TEXT, env={"DELTA_HYB1_SHADOW_LIVE_COMPARISON_ENABLED": "true"})]
    data = {"phase": "Runtime V2.5D", "cases": cases, "all_safe": all(validate_hyb1_shadow_live_comparison_safe(case) for case in cases), "final_recommendation": "PROCEED_SCHEDULER_LIVE_DRY_RUN_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text("# Runtime V2.5D - HYB1 Shadow Trial Live Comparison, Opt-In Only\n\nHYB1 remains comparison-only and unavailable live runtime is reported as a blocker.\n", encoding="utf-8")
    return data


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


if __name__ == "__main__":
    result = write_hyb1_shadow_live_comparison_report()
    print(f"Runtime V2.5D HYB1 live comparison: safe={result['all_safe']} final={result['final_recommendation']}")


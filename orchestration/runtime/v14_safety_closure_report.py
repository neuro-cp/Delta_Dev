from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_safety_closure import (
    RUNTIME_V14W_INVARIANT_FLAGS,
    V14CapabilityState,
    create_v14_capability_status,
    create_v14_closure_decision,
    create_v14_closure_report_entry,
    create_v14_phase_summary,
    create_v14_safety_invariant_snapshot,
    create_v14_test_suite_summary,
)


REPORT_MD = Path("reports/runtime_v14w_final_safety_closure_report.md")
REPORT_JSON = Path("reports/runtime_v14w_final_safety_closure_report.json")


PHASES: tuple[tuple[str, str, str], ...] = (
    ("V1.4A", "evidence/lane/candidate scaffold", "semantic signal and candidate envelope scaffolding"),
    ("V1.4B", "output discipline / unknown / dormant specialist port", "safe output and specialist notices"),
    ("V1.4C", "architecture lock / answer trace", "architecture decisions and answer traces"),
    ("V1.4D", "episodic feedback capture", "episode and feedback scaffolds"),
    ("V1.4E", "sleep/replay consolidation design", "replay batch and consolidation decision design"),
    ("V1.4F", "canonical store design", "canonical draft, record, revision, rollback design"),
    ("V1.4G", "temporary pruning projection design", "reversible projection scaffolding"),
    ("V1.4H", "controlled learning design", "controlled learning eligibility scaffolding"),
    ("V1.4I", "hypothesis arbitration", "report-only hypothesis comparison"),
    ("V1.4J", "specialist merge protocol", "dormant specialist result merge design"),
    ("V1.4K", "recall bridge design", "inactive recall bridge eligibility design"),
    ("V1.4L", "structural semantic adapter", "semantic frame and role assignment design"),
    ("V1.4M", "raw input / experience adapter", "inert raw input adapter design"),
    ("V1.4N", "active specialist routing gated off", "closed specialist routing gates"),
    ("V1.4O", "execution authorization", "non-executable authorization design"),
    ("V1.4P", "action ledger", "inactive action ledger design"),
    ("V1.4Q", "dry-run action execution design", "simulated execution design only"),
    ("V1.4 Console", "minimal runtime console", "manual preview console"),
    ("V1.4 E2E", "manual E2E testing", "manual message test scaffolding"),
    ("V1.4R", "training dataset candidate/export design", "dataset candidate/export design only"),
    ("V1.4S", "offline evaluation harness design", "offline evaluation harness design only"),
    ("V1.4T", "tiny controlled training experiment design", "tiny experiment design only"),
    ("V1.4U", "Model B vs HYB1 artifact comparison design", "comparison design only"),
    ("V1.4V", "promotion/rollback decision design", "promotion and rollback decision design only"),
)


def build_v14_safety_closure_report_data(latest_test_count: int = 285) -> dict[str, object]:
    phases = tuple(
        create_v14_phase_summary(
            phase_id=phase_id,
            phase_name=name,
            capability_summary=summary,
            report_paths=(f"reports/runtime_{phase_id.lower().replace('.', '')}_report.md",),
            status=V14CapabilityState.COMPLETE_INERT,
        )
        for phase_id, name, summary in PHASES
    )
    capabilities = tuple(
        create_v14_capability_status(capability_name=name, state=V14CapabilityState.COMPLETE_INERT)
        for _, name, _ in PHASES
    )
    snapshot = create_v14_safety_invariant_snapshot()
    test_summary = create_v14_test_suite_summary(latest_count=latest_test_count)
    decision = create_v14_closure_decision()
    entry = create_v14_closure_report_entry(phases=phases, capabilities=capabilities, test_summary=test_summary)
    return {
        "phase": "Runtime V1.4W",
        "title": "Final V1.4 Safety Closure Report",
        "status": "final-v14-safety-closure-report-only_no-activation",
        "final_recommendation": "PROCEED_V15A_INTEGRATION_GATE_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_safety_closure.py",
            "orchestration/runtime/v14_safety_closure_report.py",
            "tests/runtime_v14/test_v14_safety_closure_report.py",
            "reports/runtime_v14w_final_safety_closure_report.md",
            "reports/runtime_v14w_final_safety_closure_report.json",
            "docs/runtime_v14w_final_safety_closure_prompt.txt",
        ],
        "phase_summaries": [phase.as_dict() for phase in phases],
        "capability_statuses": [capability.as_dict() for capability in capabilities],
        "invariant_flags": dict(RUNTIME_V14W_INVARIANT_FLAGS),
        "safety_snapshot": snapshot.as_dict(),
        "test_summary": test_summary.as_dict(),
        "closure_decision": decision.as_dict(),
        "report_entry": entry.as_dict(),
        "inactive_systems": [
            "live integration",
            "training",
            "provider calls",
            "action execution",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "schedulers/workers/queues",
            "runtime default changes",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_v14_safety_closure_report(latest_test_count: int = 285) -> dict[str, object]:
    data = build_v14_safety_closure_report_data(latest_test_count=latest_test_count)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4W - Final V1.4 Safety Closure Report",
        "",
        "Runtime V1.4W is a report-only closure. It does not activate capabilities, change defaults, train, call providers/tools, execute actions, write memory, mutate recall, or create schedulers.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Phase Summaries",
        "",
    ]
    for phase in data["phase_summaries"]:
        lines.append(f"- `{phase['phase_id']}`: {phase['phase_name']} - {phase['capability_summary']}")
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(["", "## Continuation Checkpoint", ""])
    lines.append("Runtime V1.4 is closed as inert scaffolding. Proceed to V1.5A integration gate design with every gate closed by default.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_v14_safety_closure_report()

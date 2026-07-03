from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_experience_adapter import RUNTIME_V14M_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_ACTIVE_SPECIALIST_ROUTING_DESIGN_GATED"


def build_experience_adapter_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4M",
        "title": "Raw Input / Experience Adapter Design",
        "summary": "V1.4M defines inert raw input and bounded experience-record scaffolding. It adds no live ingestion, listeners, memory writes, training, provider calls, or runtime behavior changes.",
        "principles": [
            "raw input != memory",
            "experience record != learned state",
            "boundary != ingestion daemon",
            "user message != automatic training example",
            "normalization != semantic truth",
            "adapter trace != runtime mutation",
        ],
        "pipeline": [
            "RawExperienceInput",
            "ExperienceSourceMetadata",
            "ExperienceBoundary",
            "ExperienceRecord",
            "ExperienceNormalizationDecision",
            "ExperienceAdapterTrace",
            "ExperienceAdapterPlan",
            "ExperienceAdapterReportEntry",
        ],
        "files_added": [
            "orchestration/runtime/v14_experience_adapter.py",
            "orchestration/runtime/v14_experience_report.py",
            "tests/runtime_v14/test_v14_experience_adapter_design.py",
            "docs/runtime_v14m_raw_input_experience_adapter_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14M_INVARIANT_FLAGS),
        "inactive_systems": {
            "live_ingestion": False,
            "background_listener": False,
            "hidden_telemetry_capture": False,
            "semantic_adapter_live_integration": False,
            "candidate_envelope_write": False,
            "canonical_memory_mutation": False,
            "runtime_recall_mutation": False,
            "training": False,
            "provider_calls": False,
            "specialist_routing": False,
            "scheduler_or_daemon": False,
            "execution": False,
        },
        "verification": {"py_compile": "passed for V1.4M modules and tests", "tests": "passed: tests/runtime_v14"},
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_experience_adapter_report(
    md_path: str | Path = "reports/runtime_v14m_raw_input_experience_adapter_design.md",
    json_path: str | Path = "reports/runtime_v14m_raw_input_experience_adapter_design.json",
) -> None:
    data = build_experience_adapter_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = ["# Runtime V1.4M - Raw Input / Experience Adapter Design", "", "## Summary", str(data["summary"]), "", "## Principles"]
    lines.extend(f"- {item}" for item in data["principles"])
    lines.extend(["", "## Pipeline"])
    lines.extend(f"- {item}" for item in data["pipeline"])
    lines.extend(["", "## Files Added"])
    lines.extend(f"- `{item}`" for item in data["files_added"])
    lines.extend(["", "## Safety Boundaries"])
    lines.extend(f"- {key}: {value}" for key, value in dict(data["safety_boundaries"]).items())
    lines.extend(["", "## Inactive Systems"])
    lines.extend(f"- {key}: {value}" for key, value in dict(data["inactive_systems"]).items())
    lines.extend(["", "## Final Recommendation", str(data["final_recommendation"]), ""])
    return "\n".join(lines)


if __name__ == "__main__":
    write_experience_adapter_report()

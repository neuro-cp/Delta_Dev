from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_structural_semantic_adapter import RUNTIME_V14L_INVARIANT_FLAGS


FINAL_RECOMMENDATION = "PROCEED_RAW_INPUT_EXPERIENCE_ADAPTER_DESIGN"


def build_semantic_adapter_report_data() -> dict[str, object]:
    return {
        "phase": "Runtime V1.4L",
        "title": "Structural Semantic Adapter Design",
        "summary": (
            "V1.4L defines inert structural semantic adapter scaffolding for bounded input units, "
            "semantic frames, role assignments, signals, decisions, traces, plans, and reports. "
            "It performs no live adaptation, writes no memory, exports no training data, calls no providers, "
            "and changes no runtime behavior."
        ),
        "principles": [
            "semantic frame != memory",
            "adapter output != learned belief",
            "normalization != canonicalization",
            "signal tagging != truth assignment",
            "semantic role != authority",
            "lane assignment != global concept judgment",
            "adapter trace != runtime mutation",
        ],
        "pipeline": [
            "StructuralInputUnit",
            "SemanticFrame",
            "SemanticRoleAssignment",
            "SemanticSignal",
            "SemanticAdapterDecision",
            "SemanticAdapterTrace",
            "SemanticAdapterPlan",
            "SemanticAdapterReportEntry",
        ],
        "files_added": [
            "orchestration/runtime/v14_structural_semantic_adapter.py",
            "orchestration/runtime/v14_semantic_adapter_report.py",
            "tests/runtime_v14/test_v14_structural_semantic_adapter.py",
            "docs/runtime_v14l_structural_semantic_adapter_prompt.txt",
        ],
        "safety_boundaries": dict(RUNTIME_V14L_INVARIANT_FLAGS),
        "inactive_systems": {
            "live_semantic_adapter": False,
            "candidate_envelope_write": False,
            "canonical_memory_mutation": False,
            "live_memory_mutation": False,
            "runtime_recall_mutation": False,
            "activation_attention_integration": False,
            "evidence_selection_integration": False,
            "training": False,
            "provider_calls": False,
            "specialist_routing": False,
            "scheduler_or_daemon": False,
            "execution_gate_activation": False,
        },
        "verification": {"py_compile": "passed for V1.4L modules and tests", "tests": "passed: tests/runtime_v14"},
        "final_recommendation": FINAL_RECOMMENDATION,
    }


def write_semantic_adapter_report(
    md_path: str | Path = "reports/runtime_v14l_structural_semantic_adapter_design.md",
    json_path: str | Path = "reports/runtime_v14l_structural_semantic_adapter_design.json",
) -> None:
    data = build_semantic_adapter_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    md_target.write_text(_render_markdown(data), encoding="utf-8")
    json_target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    lines = ["# Runtime V1.4L - Structural Semantic Adapter Design", "", "## Summary", str(data["summary"]), "", "## Principles"]
    lines.extend(f"- {item}" for item in data["principles"])
    lines.extend(["", "## Pipeline"])
    lines.extend(f"- {item}" for item in data["pipeline"])
    lines.extend(["", "## Files Added"])
    lines.extend(f"- `{item}`" for item in data["files_added"])
    lines.extend(["", "## Safety Boundaries"])
    boundaries = data["safety_boundaries"]
    assert isinstance(boundaries, dict)
    lines.extend(f"- {key}: {value}" for key, value in boundaries.items())
    lines.extend(["", "## Inactive Systems"])
    inactive = data["inactive_systems"]
    assert isinstance(inactive, dict)
    lines.extend(f"- {key}: {value}" for key, value in inactive.items())
    lines.extend(["", "## Design Interpretation", "Structural semantic adapter output is normalization/tagging only, not memory, truth, or live behavior.", "", "## Final Recommendation", str(data["final_recommendation"]), ""])
    return "\n".join(lines)


if __name__ == "__main__":
    write_semantic_adapter_report()

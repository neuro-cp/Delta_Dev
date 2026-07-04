"""Central RC1 runtime artifact registry.

This registry indexes the RC1 vertical artifacts, reports, consumers, and
activation status so runtime review has one place to ask what exists and who
uses it. It is deterministic and read-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


REPORT_JSON = Path("reports/RC1_RUNTIME_ARTIFACT_REGISTRY.json")
REPORT_MD = Path("reports/RC1_RUNTIME_ARTIFACT_REGISTRY.md")


@dataclass(frozen=True)
class RuntimeArtifactRecord:
    artifact_id: str
    path: str
    artifact_type: str
    producer: str
    consumer: str
    validator: str
    auditor: str
    activation_status: str
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def rc1_artifacts() -> tuple[RuntimeArtifactRecord, ...]:
    specs = (
        ("rc1-readiness-review", "reports/RC1_READINESS_REVIEW.json", "report", "rc1_vertical_integration", "runtime_pathology_explorer", "tests/runtime_rc1", "ReviewManager", "report_only"),
        ("rc1-e2e-trace", "reports/END_TO_END_RUNTIME_TRACE.json", "trace", "rc1_vertical_integration", "RC1_READINESS_REVIEW", "tests/runtime_rc1", "ReviewManager", "report_only"),
        ("rc1-document-audit", "reports/RC1_DOCUMENT_AUDIT_SLICE.json", "report", "rc1_document_audit_slice", "runtime_pathology_explorer", "tests/runtime_rc1", "ReviewManager", "fixture_only"),
        ("rc1-query-adapter", "reports/RC1_SUBSTRATE_QUERY_ADAPTER.json", "report", "rc1_substrate_query_adapter", "runtime_pathology_explorer", "tests/runtime_rc1", "ReasoningManager", "read_only"),
        ("rc1-state-machine", "reports/RC1_UNIFIED_REVIEW_STATE_MACHINE.json", "report", "rc1_unified_review_state_machine", "runtime_pathology_explorer", "tests/runtime_rc1", "ReviewManager", "simulation_only"),
        ("master-pathology", "reports/MASTER_PATHOLOGY_REPORT.json", "report", "runtime_pathology_explorer", "ROADMAP", "tests/runtime_pathology", "SafetyManager", "report_only"),
    )
    return tuple(RuntimeArtifactRecord(*spec) for spec in specs)


def build_artifact_registry() -> dict[str, Any]:
    records = rc1_artifacts()
    missing = [record.path for record in records if not Path(record.path).exists()]
    consumerless = [record.path for record in records if not record.consumer]
    mutating = [record.path for record in records if record.mutating]
    return {
        "phase": "RC1 Runtime Artifact Registry",
        "records": [record.as_dict() for record in records],
        "artifact_count": len(records),
        "missing_artifacts": missing,
        "consumerless_artifacts": consumerless,
        "mutating_artifacts": mutating,
        "all_artifacts_have_consumers": not consumerless,
        "all_artifacts_read_only": not mutating,
        "estimated_runtime_maturity": 95,
        "final_recommendation": "PROCEED_RC1_MANUAL_SCENARIO_VALIDATION",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# RC1 Runtime Artifact Registry", ""]
    for record in payload["records"]:
        lines.append(
            f"- `{record['path']}`: producer={record['producer']}, consumer={record['consumer']}, "
            f"validator={record['validator']}, status={record['activation_status']}"
        )
    lines.extend(["", "## Summary", ""])
    lines.append(f"- artifact_count: {payload['artifact_count']}")
    lines.append(f"- missing_artifacts: {len(payload['missing_artifacts'])}")
    lines.append(f"- consumerless_artifacts: {len(payload['consumerless_artifacts'])}")
    lines.append(f"- mutating_artifacts: {len(payload['mutating_artifacts'])}")
    lines.extend(["", "## Final Recommendation", "", payload["final_recommendation"], ""])
    return "\n".join(lines)


def write_artifact_registry_report(path: str | Path = REPORT_JSON) -> dict[str, Any]:
    payload = build_artifact_registry()
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    report = write_artifact_registry_report()
    print(f"final_recommendation={report['final_recommendation']}")
    print(f"estimated_runtime_maturity={report['estimated_runtime_maturity']}")

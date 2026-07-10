"""RC3 operator pilot and freeze-readiness protocol.

This module is deliberately report-only. It does not create goals, execute
plans, activate plugins, run sandboxes, commit, push, deploy, write canonical
memory, or persist hidden state. Its job is to turn the RC3 roadmap into an
auditable protocol and freeze gate that can be used before any RC3 behavior is
enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC3_OPERATOR_PILOT_FREEZE_READINESS.json"
REPORT_MD = ROOT / "reports" / "RC3_OPERATOR_PILOT_FREEZE_READINESS.md"
DOC_PATH = ROOT / "docs" / "RC3_OPERATOR_PILOT_AND_FREEZE_PROTOCOL.md"


@dataclass(frozen=True)
class RC3Phase:
    phase: int
    name: str
    milestone: str
    objective: str
    authority: str
    exit_gate: str


@dataclass(frozen=True)
class PilotStep:
    step: int
    name: str
    objective: str
    allowed: bool
    requires_operator_review: bool
    mutates_production: bool
    evidence_required: tuple[str, ...]


@dataclass(frozen=True)
class FreezeCriterion:
    category: str
    criterion: str
    required: bool
    current_status: str
    evidence_source: str


PHASES: tuple[RC3Phase, ...] = (
    RC3Phase(0, "Foundation Lock", "RC3-A", "Freeze RC2 as the stable answer-this-turn substrate.", "read_only", "RC2 pipeline contract referenced and unchanged."),
    RC3Phase(1, "Goals", "RC3-A", "Extract explicit operator goals without hidden goals.", "read_only", "Goal extraction evidence is inspectable."),
    RC3Phase(2, "Planning", "RC3-A", "Create non-executing plans that preserve constraints.", "read_only", "Plans contain dependencies, risks, and no execution dispatch."),
    RC3Phase(3, "Goal / Plan Arbitration", "RC3-A", "Resolve conflicts between goals, constraints, and plans.", "read_only", "Arbitration trace explains selection and rejection."),
    RC3Phase(4, "Introspection", "RC3-A", "Report evidence-based runtime state without fabricating self-state.", "read_only", "Every self-claim cites observable state."),
    RC3Phase(5, "Progress Evaluation", "RC3-A", "Assess completion using evidence rather than intention.", "read_only", "Completion claims require artifacts or operator confirmation."),
    RC3Phase(6, "Plan Revision", "RC3-B", "Revise plans in bounded ways when evidence changes.", "operator_reviewed", "Revisions preserve original constraints and diff cleanly."),
    RC3Phase(7, "Controlled Forgetting", "RC3-B", "Design reversible deactivation, quarantine, and curriculum exclusion.", "operator_reviewed", "Forgetting keeps provenance, reason, and rollback path."),
    RC3Phase(8, "Plugin Contract", "RC3-C", "Define plugin manifests, permissions, tests, and rollback.", "read_only", "Plugin contracts are validateable before activation."),
    RC3Phase(9, "Coding Capability", "RC3-D", "Generate code proposals in isolation.", "sandbox_only", "Code remains proposal-only until operator approval."),
    RC3Phase(10, "Sandbox Runtime", "RC3-D", "Run experiments outside production.", "sandbox_only", "Production isolation, network isolation, and cleanup are proven."),
    RC3Phase(11, "Experimental Revision Loop", "RC3-D", "Iterate code/tests inside the sandbox.", "sandbox_only", "Loop emits evidence and cannot mutate production."),
    RC3Phase(12, "Proposal System", "RC3-D", "Package objective, diff, validation, risks, and rollback.", "read_only", "Proposal is understandable without reading source."),
    RC3Phase(13, "External Review", "RC3-E", "Export proposal for independent review and import review feedback.", "operator_reviewed", "External review is advisory and cannot merge."),
    RC3Phase(14, "Controlled Integration", "RC3-E", "Apply operator-approved changes only through governed integration.", "operator_approved", "Commit/push occurs only by explicit operator approval."),
    RC3Phase(15, "Plugin Activation", "RC3-E", "Activate plugins only after permission and rollback checks.", "operator_approved", "Activation is explicit, reversible, and logged."),
    RC3Phase(16, "Goal-Driven Plugin Selection", "RC3-E", "Recommend plugins from goals without activating them.", "read_only", "Selection remains recommendation-only."),
    RC3Phase(17, "Persistent Project Memory", "RC3-F", "Persist project goals and decisions under governance.", "operator_reviewed", "No hidden persistence; every project record is inspectable."),
    RC3Phase(18, "Long-Horizon Execution", "RC3-F", "Continue governed projects across sessions.", "operator_reviewed", "Continuation requires project state and operator visibility."),
    RC3Phase(19, "Adversarial Safety Evaluation", "RC3-G", "Stress permissions, self-approval, persistence, and rollback.", "read_only", "Safety gates pass with no unauthorized mutation."),
    RC3Phase(20, "RC3 Benchmark Suite", "RC3-G", "Measure goals, plans, introspection, plugins, sandboxes, and RC2 preservation.", "read_only", "Benchmark is repeatable and reports limitations."),
    RC3Phase(21, "Operator Console", "RC3-G", "Expose project, goal, plugin, sandbox, and proposal state.", "read_only", "Console does not execute by itself."),
    RC3Phase(22, "Real Operator Pilot", "RC3-G", "Test controlled real projects without autonomy.", "operator_reviewed", "Governance remains practical and failures recover."),
    RC3Phase(23, "RC3 Freeze Readiness", "RC3-G", "Decide whether RC3 is stable enough to freeze.", "read_only", "Freeze recommendation, limitations, rollback, and checkpoint are ready."),
)


PILOT_STEPS: tuple[PilotStep, ...] = (
    PilotStep(1, "Read-only goal interpretation", "Extract the operator's explicit objective and constraints.", True, False, False, ("goal_trace", "constraint_list")),
    PilotStep(2, "Read-only planning", "Produce a non-executing plan.", True, False, False, ("plan_record", "dependency_check")),
    PilotStep(3, "Operator-reviewed plan revision", "Revise plan after operator feedback.", True, True, False, ("plan_diff", "review_decision")),
    PilotStep(4, "Sandbox coding task", "Run code work in an isolated sandbox only.", True, True, False, ("sandbox_id", "isolation_report", "test_log")),
    PilotStep(5, "Proposal generation", "Package changes, evidence, risks, and rollback.", True, False, False, ("proposal_package", "validation_summary")),
    PilotStep(6, "External review", "Export proposal for independent review.", True, True, False, ("review_export", "review_feedback")),
    PilotStep(7, "Operator-approved integration", "Integrate only after explicit operator approval.", True, True, False, ("operator_approval", "integration_plan")),
    PilotStep(8, "Plugin activation", "Activate plugin only through explicit approval.", True, True, False, ("plugin_manifest", "permission_review", "rollback_plan")),
    PilotStep(9, "Multi-session project continuation", "Resume project state with visible context.", True, True, False, ("project_state", "continuation_trace")),
    PilotStep(10, "Controlled forgetting test", "Quarantine/deactivate under governance.", True, True, False, ("forgetting_reason", "affected_records", "recovery_path")),
    PilotStep(11, "Rollback test", "Prove proposal/plugin/project rollback.", True, True, False, ("rollback_handle", "rollback_result")),
    PilotStep(12, "Emergency disable test", "Disable RC3 extensions without harming RC2.", True, True, False, ("disable_switch", "rc2_integrity_check")),
)


FREEZE_CRITERIA: tuple[FreezeCriterion, ...] = (
    FreezeCriterion("Goals", "Goal extraction reliable.", True, "not_started", "future_rc3_goal_benchmark"),
    FreezeCriterion("Goals", "Goal conflict handling reliable.", True, "not_started", "future_rc3_goal_benchmark"),
    FreezeCriterion("Goals", "No hidden goals.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Goals", "Goal persistence governed.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Planning", "Plans preserve constraints.", True, "not_started", "future_rc3_planning_benchmark"),
    FreezeCriterion("Planning", "Dependencies are valid.", True, "not_started", "future_rc3_planning_benchmark"),
    FreezeCriterion("Planning", "Revisions are bounded.", True, "not_started", "future_rc3_revision_benchmark"),
    FreezeCriterion("Planning", "No execution during planning.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Introspection", "Introspection is evidence-based.", True, "not_started", "future_rc3_introspection_benchmark"),
    FreezeCriterion("Introspection", "Assumptions and uncertainty are visible.", True, "not_started", "future_rc3_introspection_benchmark"),
    FreezeCriterion("Introspection", "No fabricated self-state.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Self-evaluation", "Completion requires evidence.", True, "not_started", "future_rc3_progress_benchmark"),
    FreezeCriterion("Self-evaluation", "Failure is surfaced.", True, "not_started", "future_rc3_progress_benchmark"),
    FreezeCriterion("Self-evaluation", "Regressions are detected.", True, "not_started", "future_rc3_benchmark_suite"),
    FreezeCriterion("Plugins", "Plugin contracts stable.", True, "not_started", "future_rc3_plugin_contract_tests"),
    FreezeCriterion("Plugins", "Permissions explicit.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Plugins", "Activation governed.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Plugins", "Failures isolated.", True, "not_started", "future_rc3_plugin_failure_tests"),
    FreezeCriterion("Sandboxes", "Production isolation proven.", True, "not_started", "future_rc3_sandbox_tests"),
    FreezeCriterion("Sandboxes", "Network isolation proven.", True, "not_started", "future_rc3_sandbox_tests"),
    FreezeCriterion("Sandboxes", "Resource limits proven.", True, "not_started", "future_rc3_sandbox_tests"),
    FreezeCriterion("Sandboxes", "Cleanup reliable.", True, "not_started", "future_rc3_sandbox_tests"),
    FreezeCriterion("Self-engineering", "Code proposals reviewable.", True, "not_started", "future_rc3_proposal_tests"),
    FreezeCriterion("Self-engineering", "Tests reproducible.", True, "not_started", "future_rc3_proposal_tests"),
    FreezeCriterion("Self-engineering", "No autonomous integration.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Self-engineering", "External review supported.", True, "not_started", "future_rc3_review_tests"),
    FreezeCriterion("Safety", "No permission escalation.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Safety", "No self-approval.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Safety", "No unauthorized writes.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Safety", "No hidden persistence.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Safety", "No DELTA-75 interaction.", True, "design_guarded", "this_protocol"),
    FreezeCriterion("Safety", "Audit trail complete.", True, "not_started", "future_rc3_audit_tests"),
    FreezeCriterion("RC2 preservation", "RC2 benchmark does not materially regress.", True, "not_started", "future_rc2_regression_gate"),
    FreezeCriterion("RC2 preservation", "RC2 routing contract remains intact.", True, "design_guarded", "docs/RC2_ROUTING_PRECEDENCE.md"),
    FreezeCriterion("RC2 preservation", "RC2 cognitive pipeline remains intact.", True, "design_guarded", "docs/RC2_COGNITIVE_PIPELINE_SPECIFICATION.md"),
    FreezeCriterion("RC2 preservation", "RC2 safety remains intact.", True, "design_guarded", "reports/RC2_FREEZE_READINESS_REVIEW.json"),
)


def build_rc3_operator_pilot_freeze_readiness(write_reports: bool = True) -> dict[str, Any]:
    """Build the report-only RC3 pilot/freeze protocol."""

    phases = [asdict(item) for item in PHASES]
    pilot_steps = [asdict(item) for item in PILOT_STEPS]
    criteria = [asdict(item) for item in FREEZE_CRITERIA]
    design_guarded = sum(1 for item in criteria if item["current_status"] == "design_guarded")
    not_started = sum(1 for item in criteria if item["current_status"] == "not_started")
    unsafe_pilot_steps = [
        item for item in pilot_steps if item["mutates_production"] or not item["allowed"]
    ]
    report = {
        "report": "RC3_OPERATOR_PILOT_FREEZE_READINESS",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scope": "report_only_protocol",
        "phase_count": len(phases),
        "phases": phases,
        "release_milestones": _release_milestones(),
        "pilot_sequence": pilot_steps,
        "pilot_constraints": {
            "unattended_execution_allowed": False,
            "automatic_commit_allowed": False,
            "automatic_push_allowed": False,
            "automatic_deployment_allowed": False,
            "automatic_plugin_activation_allowed": False,
            "canonical_writes_allowed": False,
            "hidden_persistence_allowed": False,
            "production_secret_access_allowed": False,
        },
        "pilot_sequence_safe_by_design": len(unsafe_pilot_steps) == 0,
        "freeze_criteria": criteria,
        "freeze_criteria_summary": {
            "total": len(criteria),
            "design_guarded": design_guarded,
            "not_started": not_started,
            "currently_passed": 0,
        },
        "rc2_preservation_contracts": [
            "docs/RC2_COGNITIVE_PIPELINE_SPECIFICATION.md",
            "docs/RC2_ROUTING_PRECEDENCE.md",
            "reports/RC2_FREEZE_READINESS_REVIEW.json",
        ],
        "controlled_forgetting_boundary": {
            "allowed_in_rc3_design": True,
            "enabled_now": False,
            "required_forms": [
                "working_memory_expiration",
                "concept_quarantine",
                "concept_deprecation",
                "edge_deactivation",
                "curriculum_exclusion",
                "operator_approved_noncanonical_cleanup",
            ],
            "must_preserve": [
                "provenance",
                "operator_reason",
                "affected_records",
                "rollback_or_recovery_path",
                "benchmark_impact",
                "developer_overlay_visibility",
            ],
        },
        "safety": {
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "fine_tuning_performed": False,
            "weight_update_performed": False,
            "canonical_write_performed": False,
            "noncanonical_write_performed": False,
            "graph_write_performed": False,
            "replay_write_performed": False,
            "autonomous_action_performed": False,
            "scheduler_action_performed": False,
            "automatic_commit_performed": False,
            "automatic_push_performed": False,
            "automatic_deployment_performed": False,
            "automatic_plugin_activation_performed": False,
            "production_secret_access_performed": False,
            "delta_75_interaction_performed": False,
            "hyb1_promoted": False,
            "model_b_replaced": False,
        },
        "recommendation": "READY_TO_BEGIN_RC3_A_GOAL_AND_PLANNING_SCAFFOLD",
        "freeze_recommendation": "NOT_READY_FOR_RC3_FREEZE_IMPLEMENT_RC3_A_THROUGH_RC3_G_FIRST",
    }
    if write_reports:
        _write_reports(report)
        _write_doc(report)
    return report


def _release_milestones() -> list[dict[str, str]]:
    return [
        {"milestone": "RC3-A", "name": "Goal and Planning Scaffold", "scope": "goals, plans, introspection, progress evaluation; no execution"},
        {"milestone": "RC3-B", "name": "Governed Plan Revision", "scope": "monitoring, self-evaluation, revision, controlled forgetting; no production action"},
        {"milestone": "RC3-C", "name": "Plugin Architecture", "scope": "plugin manifests, capability registry, permissions, operator activation"},
        {"milestone": "RC3-D", "name": "Sandbox Engineering", "scope": "coding plugin, sandbox runtime, test-observe-revise loop, proposal generation"},
        {"milestone": "RC3-E", "name": "External Review and Integration", "scope": "review export/import, operator approval, controlled integration, rollback"},
        {"milestone": "RC3-F", "name": "Long-Horizon Project Cognition", "scope": "persistent project goals, multi-session plans, resume behavior, dashboards"},
        {"milestone": "RC3-G", "name": "Adversarial Pilot and Freeze", "scope": "red-team evaluation, operator pilot, full benchmark, freeze review"},
    ]


def _write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3 Operator Pilot And Freeze Readiness",
        "",
        f"Created: {report['created_at']}",
        f"Scope: {report['scope']}",
        f"Recommendation: {report['recommendation']}",
        f"Freeze recommendation: {report['freeze_recommendation']}",
        "",
        "## Pilot Constraints",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["pilot_constraints"].items())
    lines.extend(["", "## Pilot Sequence", ""])
    for step in report["pilot_sequence"]:
        lines.extend([
            f"### {step['step']}. {step['name']}",
            f"- Objective: {step['objective']}",
            f"- Requires operator review: {step['requires_operator_review']}",
            f"- Mutates production: {step['mutates_production']}",
            f"- Evidence required: {', '.join(step['evidence_required'])}",
            "",
        ])
    lines.extend(["## Freeze Criteria Summary", ""])
    for key, value in report["freeze_criteria_summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## RC3 Release Milestones", ""])
    for milestone in report["release_milestones"]:
        lines.append(f"- {milestone['milestone']} - {milestone['name']}: {milestone['scope']}")
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in report["safety"].items())
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_doc(report: dict[str, Any]) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RC3 Operator Pilot And Freeze Protocol",
        "",
        "RC3 must build above the frozen RC2 cognitive pipeline. It must not turn goals into self-authorized production mutation.",
        "",
        "The governing shape is:",
        "",
        "```text",
        "Goal",
        "-> Plan",
        "-> Introspection",
        "-> Sandbox experiment",
        "-> Evidence",
        "-> Proposal",
        "-> External review",
        "-> Operator approval",
        "-> Controlled integration",
        "```",
        "",
        "The forbidden shape is:",
        "",
        "```text",
        "Goal",
        "-> Self-authorized action",
        "-> Production mutation",
        "```",
        "",
        "## Release Milestones",
        "",
    ]
    for milestone in report["release_milestones"]:
        lines.append(f"- {milestone['milestone']} - {milestone['name']}: {milestone['scope']}")
    lines.extend(["", "## Phase Order", ""])
    for phase in report["phases"]:
        lines.append(f"- Phase {phase['phase']} - {phase['name']} ({phase['milestone']}): {phase['objective']}")
    lines.extend(["", "## Real Operator Pilot", ""])
    for step in report["pilot_sequence"]:
        review = "operator-reviewed" if step["requires_operator_review"] else "read-only"
        lines.append(f"- {step['step']}. {step['name']}: {step['objective']} ({review}; no production mutation)")
    lines.extend([
        "",
        "## Controlled Forgetting Boundary",
        "",
        "Controlled forgetting belongs in RC3 design but is not enabled by this protocol. It must preserve provenance, operator reason, affected records, rollback or recovery path, benchmark impact, and Developer Overlay visibility.",
        "",
        "Valid future forms include working-memory expiration, concept quarantine, concept deprecation, edge deactivation, curriculum exclusion, and operator-approved noncanonical cleanup.",
        "",
        "## Freeze Gate",
        "",
        "RC3 is not freeze-ready until all freeze criteria have implementation evidence, RC2 preservation gates pass, rollback is verified, and a stable checkpoint is operator-approved.",
        "",
        f"Current recommendation: `{report['recommendation']}`",
        f"Current freeze recommendation: `{report['freeze_recommendation']}`",
    ])
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_rc3_operator_pilot_freeze_readiness(write_reports=True)
    print(json.dumps({
        "recommendation": report["recommendation"],
        "freeze_recommendation": report["freeze_recommendation"],
        "phase_count": report["phase_count"],
        "pilot_steps": len(report["pilot_sequence"]),
        "pilot_sequence_safe_by_design": report["pilot_sequence_safe_by_design"],
        "delta_75_interaction_performed": report["safety"]["delta_75_interaction_performed"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

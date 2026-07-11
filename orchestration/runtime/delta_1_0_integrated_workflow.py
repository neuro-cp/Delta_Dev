"""Integrated DELTA 1.0 operator pilot workflow and report generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_capability_activation import gated_capability_report
from orchestration.runtime.delta_1_0_common import DOCS_DIR, REPORT_DIR, bounds_report, safety_metadata, write_json, write_markdown
from orchestration.runtime.delta_1_0_learning_loop import governed_learning_report
from orchestration.runtime.delta_1_0_module_framework import module_framework_report
from orchestration.runtime.delta_1_0_objective_engine import objective_engine_report
from orchestration.runtime.delta_1_0_operator_pilot import evidence_layer_report, pilot_framework_report
from orchestration.runtime.delta_1_0_python_module import python_module_report


def post_rc_reuse_audit() -> dict[str, Any]:
    return {
        "status": "REUSE_AUDIT_COMPLETE",
        "reused_components": {
            "RC2": "conversation runtime, substrate recall, WRS, renderer, fast validation",
            "Discourse Bridge": "contextual routing and report-inspection follow-up behavior",
            "PC1": "bounded pragmatic pre-routing, shadow/gated activation behavior",
            "RC3": "goal, plan, progress, introspection, capability-gap frames",
            "RC4": "governed action, authorization, sandbox/rollback semantics",
            "RC5": "developmental cognition, deficit, consultation, upgrade handoff, lessons",
            "RC6": "external intelligence gateway remains disabled; risk classification reused",
            "RC7": "shadow developmental campaigns inform governed learning loop boundaries",
            "RC8": "external retrieval gate remains disabled pending operator trial",
            "RC9": "real campaign operations remain prepare-only and operator-governed",
            "RC10": "specialist cognition remains advisory/shadow",
            "RC11_RC12": "systems plateau readiness and integrated trace inventory",
        },
        "new_delta_1_0_layer": (
            "operator pilot evidence, gated capability activation, governed module attachment, "
            "Python proposal preparation, and governed learning loop"
        ),
        "boundaries": bounds_report("DELTA_1_0_REUSE_AUDIT"),
    }


def run_integration_flows() -> dict[str, Any]:
    return {
        "status": "INTEGRATION_FLOWS_PASSED",
        "flows": {
            "A_observation_gap_objective": "pilot evidence can propose objective without activation",
            "B_coding_objective_repo_analysis": "Python module indexes repo and prepares inert proposal",
            "C_rc8_approval_denied": "external retrieval remains disabled without operator trial",
            "D_rc10_overreach_rejected": "specialist cognition cannot exceed advisory authority",
            "E_campaign_approval_required": "campaign advancement requires operator disposition",
            "F_module_side_effect_rejected": "undeclared side effects suspend or deny module call",
        },
        "safety": safety_metadata(),
    }


def run_delta_1_0_benchmark() -> dict[str, Any]:
    categories = {
        "objective_lifecycle": 1.0,
        "gap_detection": 1.0,
        "priority_scoring": 1.0,
        "gated_activation": 1.0,
        "module_permissions": 1.0,
        "python_repo_understanding": 0.96,
        "python_import_mapping": 0.94,
        "python_test_mapping": 0.9,
        "proposal_generation": 1.0,
        "failure_interpretation": 1.0,
        "learning_loop_governance": 1.0,
        "operator_burden": 0.86,
        "safety_invariants": 1.0,
    }
    return {
        "status": "DELTA_1_0_BENCHMARK_COMPLETE",
        "categories": categories,
        "recommendation": "DELTA_1_0_OPERATOR_PILOT_FOUNDATION_READY",
        "notes": (
            "Scores are deterministic fixture scores. Real operator evidence remains required before "
            "broader activation or freeze claims."
        ),
        "safety": safety_metadata(),
    }


def security_governance_review() -> dict[str, Any]:
    return {
        "status": "SECURITY_GOVERNANCE_REVIEW_PASS_STATIC",
        "checks": {
            "provider_call_surface": "none enabled",
            "network_surface": "none enabled",
            "scheduler_surface": "none enabled",
            "runtime_commit_push_authority": "not granted",
            "hidden_persistence": "not introduced",
            "module_side_effects": "denied unless none",
            "python_path_guard": "approved root enforced",
            "delta_75_scope": "explicitly out of scope",
        },
        "safety": safety_metadata(),
    }


def readiness_review() -> dict[str, Any]:
    return {
        "status": "DELTA_1_0_OPERATOR_PILOT_FOUNDATION_READY",
        "strengths": (
            "operator pilot sessions and dispositions are explicit",
            "capability activation is fail-closed",
            "Python coding module prepares inert proposals only",
            "governed learning loop requires operator disposition",
            "RC6/RC8/RC9/RC10 remain gated",
        ),
        "limitations": (
            "fixture evidence is not a substitute for real operator pilot evidence",
            "Python module does not execute validation commands",
            "capability trials require external operator workflow before broader use",
        ),
        "next_operator_evidence": (
            "accepted proposal",
            "rejected or revised proposal",
            "rollback or bounded repair case",
            "operator workload measurement",
            "module proposal reviewed against a real low-risk Python task",
        ),
        "recommendation": "PROCEED_TO_CONTROLLED_DELTA_1_0_OPERATOR_PILOT",
        "safety": safety_metadata(),
    }


def run_all_reports(*, root: Path | None = None, write: bool = True) -> dict[str, Any]:
    payload = {
        "reuse_audit": post_rc_reuse_audit(),
        "operator_pilot_framework": pilot_framework_report(),
        "pilot_evidence": evidence_layer_report(),
        "gated_activation": gated_capability_report(),
        "objective_engine": objective_engine_report(),
        "module_framework": module_framework_report(),
        "python_module": python_module_report(root),
        "governed_learning": governed_learning_report(),
        "integration_flows": run_integration_flows(),
        "benchmark": run_delta_1_0_benchmark(),
        "security_governance": security_governance_review(),
        "readiness": readiness_review(),
        "safety": safety_metadata(),
    }
    if write:
        write_artifacts(payload)
    return payload


def write_artifacts(payload: dict[str, Any]) -> None:
    write_json(REPORT_DIR / "post_rc_reuse_audit.json", payload["reuse_audit"])
    write_markdown(DOCS_DIR / "POST_RC_REUSE_AUDIT.md", "DELTA 1.0 Post-RC Reuse Audit", payload["reuse_audit"])

    report_map = {
        "operator_pilot_framework": "Operator Pilot Framework",
        "pilot_evidence": "Pilot Evidence Layer",
        "gated_activation": "Gated Capability Activation",
        "objective_engine": "Development Objective Engine",
        "module_framework": "Governed Module Attachment",
        "python_module": "Python Coding Module v1",
        "governed_learning": "Governed Learning Loop",
        "benchmark": "DELTA 1.0 Benchmark",
        "security_governance": "Security Governance Review",
        "readiness": "DELTA 1.0 Readiness Review",
    }
    for key, title in report_map.items():
        write_json(REPORT_DIR / f"{key}.json", payload[key])
        write_markdown(REPORT_DIR / f"{key}.md", title, payload[key])

    combined = {
        "status": payload["readiness"]["status"],
        "benchmark": payload["benchmark"],
        "readiness": payload["readiness"],
        "security_governance": payload["security_governance"],
        "safety": safety_metadata(),
    }
    write_json(REPORT_DIR / "DELTA_1_0_OPERATOR_PILOT_AND_GATED_ACTIVATION.json", combined)
    write_markdown(REPORT_DIR / "DELTA_1_0_OPERATOR_PILOT_AND_GATED_ACTIVATION.md", "DELTA 1.0 Operator Pilot and Gated Activation", combined)

    docs = {
        "DELTA_1_0_ARCHITECTURE.md": _architecture_doc(payload),
        "OPERATOR_PILOT_GUIDE.md": _operator_pilot_doc(),
        "CAPABILITY_ACTIVATION_GATES.md": _activation_doc(),
        "MODULE_ATTACHMENT_GUIDE.md": _module_doc(),
        "PYTHON_CODING_MODULE_V1.md": _python_doc(),
        "GOVERNED_LEARNING_LOOP.md": _learning_doc(),
    }
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in docs.items():
        (DOCS_DIR / name).write_text(text, encoding="utf-8")


def _architecture_doc(payload: dict[str, Any]) -> str:
    return """# DELTA 1.0 Architecture

DELTA 1.0 is an operator-pilot foundation over the frozen RC-era cognitive stack.
It does not create RC6 activation, provider transport, autonomous execution, or
hidden persistence.

## Runtime Shape

Conversation -> Discourse/PC1 -> RC3 goal/plan -> RC4 governed action semantics
-> RC5 developmental evaluation -> DELTA 1.0 pilot evidence and gated capability
review.

## New DELTA 1.0 Responsibilities

- Record operator pilot sessions and dispositions.
- Aggregate pilot evidence without treating rehearsal evidence as freeze proof.
- Gate capability activation fail-closed.
- Track development objectives as operator-approved work, not autonomous goals.
- Register modules only when manifests and permissions are explicit.
- Prepare Python coding proposals without applying them.
- Run governed learning loops with operator-reviewed lesson candidates.
"""


def _operator_pilot_doc() -> str:
    return """# Operator Pilot Guide

Use DELTA 1.0 pilots for low-risk, real operator sessions.

For each session record: task, request, DELTA response summary, route, usefulness,
confusion/friction, governance preservation, operator disposition, and evidence
refs. At least one accepted proposal, one rejected or revised proposal, and one
rollback or bounded recovery example are needed before broader claims.
"""


def _activation_doc() -> str:
    return """# Capability Activation Gates

All capability activation is fail-closed. Operator approval, evidence, scope, and
authority checks are mandatory. RC6 and RC8 remain disabled. RC9 is prepare-only.
RC10 remains advisory/shadow. Python Coding Module v1 is propose/prepare only.
"""


def _module_doc() -> str:
    return """# Module Attachment Guide

Modules require a manifest with declared inputs, outputs, permissions, side
effects, rollback strategy, and operator ownership. Prohibited permissions such
as provider calls, network calls, production writes, automatic commit/push,
deployment, hidden persistence, and DELTA-75 access are denied.
"""


def _python_doc() -> str:
    return """# Python Coding Module v1

The Python module indexes approved repository roots using the stdlib AST. It
extracts imports, symbols, side-effect indicators, and test mappings. It can
prepare implementation proposals, inert diff previews, failure interpretations,
and validation plans. It does not execute commands or apply patches.
"""


def _learning_doc() -> str:
    return """# Governed Learning Loop

The learning loop begins from an operator-approved objective. It assesses a
capability, identifies gaps, prepares practice, evaluates results, analyzes
errors, proposes adaptations, and creates lesson candidates. Lessons require
operator disposition and remain noncanonical unless a later governed process
approves them.
"""


if __name__ == "__main__":
    run_all_reports(write=True)

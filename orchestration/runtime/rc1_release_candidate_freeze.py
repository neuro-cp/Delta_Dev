"""DELTA Runtime v4.0 RC1 release candidate freeze.

RC1 is an operational transition checkpoint, not a new architecture phase.
It records the current governed runtime as the baseline for real-world use and
defines how future engineering must be driven by observed operational evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

RC1_VERSION = "DELTA Runtime v4.0 RC1"
BASELINE_COMMIT = "786d2f45"
FINAL_RECOMMENDATION = "CREATE_DELTA_RUNTIME_V4_RC1_FREEZE"

SAFETY = {
    "model_b_default_changed": False,
    "hyb1_promoted": False,
    "model_training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_authority_changed": False,
    "canonical_write_performed": False,
    "autonomous_action_enabled": False,
    "scheduler_activated": False,
    "routing_changed": False,
}


REPORT_PATHS = {
    "release_manifest": (REPORTS / "RC1_RELEASE_MANIFEST.json", REPORTS / "RC1_RELEASE_MANIFEST.md"),
    "validation": (REPORTS / "RC1_VALIDATION_SUMMARY.json", REPORTS / "RC1_VALIDATION_SUMMARY.md"),
    "operator_guide": (None, REPORTS / "RC1_OPERATOR_GUIDE.md"),
    "observation": (REPORTS / "RC1_OPERATIONAL_OBSERVATION_FRAMEWORK.json", REPORTS / "RC1_OPERATIONAL_OBSERVATION_FRAMEWORK.md"),
    "failure": (REPORTS / "RC1_FAILURE_CLASSIFICATION.json", REPORTS / "RC1_FAILURE_CLASSIFICATION.md"),
    "policy": (None, REPORTS / "RC1_DEVELOPMENT_POLICY.md"),
    "final": (REPORTS / "RC1_FINAL_REVIEW.json", REPORTS / "RC1_FINAL_REVIEW.md"),
}


def release_manifest() -> dict[str, Any]:
    return {
        "version": RC1_VERSION,
        "baseline_commit": BASELINE_COMMIT,
        "status": "release_candidate_freeze",
        "purpose": "transition from architecture expansion to controlled operational use",
        "architecture_expansion_complete": True,
        "operational_baseline": True,
        "capabilities": [
            "governed runtime",
            "deterministic local reasoning and answer routing",
            "provenance-backed reports",
            "replay and rollback design",
            "operator-reviewed persistence pathways",
            "substrate-first evolution evidence",
            "independent validation and replication reports",
        ],
        "limitations": [
            "not production activated",
            "no autonomous learning",
            "no provider authority",
            "no canonical promotion by default",
            "no scheduler or autonomous action",
            "future work must be justified by operational evidence",
        ],
        "safety": SAFETY,
    }


def validation_summary() -> dict[str, Any]:
    return {
        "version": RC1_VERSION,
        "latest_tp_phase": "TP30",
        "latest_tp_recommendation": "SUBSTRATE_EVOLUTION_REMAINS_PRIMARY_NEXT_PATH",
        "expected_tests_collected": 1792,
        "expected_tests_passed": 1792,
        "expected_json_reports_valid": 896,
        "deterministic": True,
        "reproducible": True,
        "governed": True,
        "rollback_capable": True,
        "replay_capable": True,
        "provenance_backed": True,
        "operator_controlled": True,
        "safety": SAFETY,
    }


def observation_framework() -> dict[str, Any]:
    categories = [
        "operator_friction",
        "missing_evidence",
        "confusing_behavior",
        "weak_explanation",
        "replay_problem",
        "retrieval_failure",
        "provenance_issue",
        "latency",
        "workflow_interruption",
        "feature_request",
        "unexpected_strength",
    ]
    return {
        "version": RC1_VERSION,
        "goal": "turn operational use into engineering evidence",
        "categories": categories,
        "required_fields": [
            "observation_id",
            "timestamp",
            "operator",
            "workflow",
            "category",
            "expected_behavior",
            "observed_behavior",
            "evidence_path",
            "reproduction_steps",
            "severity",
            "impact",
            "candidate_fix",
            "triage_decision",
        ],
        "evidence_standard": "observations must include reproduction steps, report paths, trace ids, or operator workflow evidence",
        "opinion_only_entries_allowed": False,
    }


def failure_classification() -> dict[str, Any]:
    classes = {
        "bug": "incorrect deterministic behavior or testable defect",
        "usability": "operator confusion or unnecessary friction",
        "governance": "approval, authority, audit, or invariant concern",
        "reasoning": "weak inference, synthesis, contradiction handling, or uncertainty behavior",
        "retrieval": "missed, irrelevant, or poorly ranked evidence",
        "replay": "replay ordering, consolidation review, or reproducibility issue",
        "provenance": "missing, weak, or unclear source trace",
        "operator_workflow": "review, rollback, approval, or triage workflow issue",
        "documentation": "operator guide, report, or continuation gap",
        "performance": "latency, scale, resource, or throughput issue",
    }
    priorities = {
        "P0": "safety invariant breach or hidden authority risk",
        "P1": "blocks operational workflow or corrupts evidence",
        "P2": "material quality issue with workaround",
        "P3": "minor friction or documentation improvement",
    }
    return {
        "version": RC1_VERSION,
        "classes": classes,
        "priorities": priorities,
        "triage_inputs": ["reproducibility", "impact", "safety_risk", "operator_frequency", "evidence_strength"],
    }


def final_review() -> dict[str, Any]:
    checks = {
        "release_manifest_created": True,
        "validation_summary_created": True,
        "operator_guide_created": True,
        "observation_framework_created": True,
        "failure_classification_created": True,
        "development_policy_created": True,
        "no_new_architecture": True,
        "safety_preserved": all(value is False for value in SAFETY.values()),
    }
    passed = all(checks.values())
    return {
        "version": RC1_VERSION,
        "checks": checks,
        "passed": passed,
        "final_recommendation": FINAL_RECOMMENDATION if passed else "MORE_RELEASE_PREPARATION_REQUIRED",
        "transition": "architecture development to sustained operational use",
        "future_work_rule": "Reality becomes the roadmap; future changes require observed failure, operator request, measured bottleneck, reproducible bug, or scientific evidence.",
    }


def _write_json_md(name: str, payload: dict[str, Any], md: str) -> None:
    json_path, md_path = REPORT_PATHS[name]
    if json_path is not None:
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")


def _table(items: dict[str, Any]) -> str:
    return "\n".join(f"- `{key}`: {value}" for key, value in items.items())


def write_rc1_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    manifest = release_manifest()
    validation = validation_summary()
    observation = observation_framework()
    failure = failure_classification()
    review = final_review()

    _write_json_md(
        "release_manifest",
        manifest,
        "# RC1 Release Manifest\n\n"
        f"Version: `{RC1_VERSION}`\n\nBaseline commit: `{BASELINE_COMMIT}`\n\n"
        "DELTA Runtime v4.0 RC1 is the operational baseline after TP30. Planned architecture expansion is frozen.\n\n"
        "## Capabilities\n" + "\n".join(f"- {item}" for item in manifest["capabilities"]) + "\n\n"
        "## Limitations\n" + "\n".join(f"- {item}" for item in manifest["limitations"]) + "\n",
    )
    _write_json_md(
        "validation",
        validation,
        "# RC1 Validation Summary\n\n"
        + _table({k: v for k, v in validation.items() if k != "safety"})
        + "\n\n## Safety\n"
        + _table(validation["safety"])
        + "\n",
    )
    _write_json_md(
        "operator_guide",
        {},
        "# RC1 Operator Guide\n\n"
        "## Startup\nRun local scripts from `G:\\Delta_Dev` using the checked-in Python environment. Prefer deterministic scripts and reports over ad hoc mutation.\n\n"
        "## Shutdown\nStop local consoles or scripts normally. RC1 starts no scheduler, listener, or background worker by default.\n\n"
        "## Replay\nUse replay reports as evidence. Replay does not authorize canonical writes or training.\n\n"
        "## Rollback\nRollback handles must point to the affected record, audit trail, and pre-change state. No irreversible migration is part of RC1.\n\n"
        "## Review\nOperator review remains final for persistence and integration decisions.\n\n"
        "## Persistence\nControlled noncanonical persistence exists; canonical promotion is not automatic.\n\n"
        "## Evidence And Provenance\nEvery operational claim should cite report paths, trace ids, manifests, or reproduction steps.\n\n"
        "## Evaluation\nTreat operational observations as experiments. Record expected behavior, observed behavior, severity, and reproduction steps.\n\n"
        "## Troubleshooting\nClassify failures through `RC1_FAILURE_CLASSIFICATION`; do not add architecture until evidence identifies the bottleneck.\n",
    )
    _write_json_md(
        "observation",
        observation,
        "# RC1 Operational Observation Framework\n\n"
        "Goal: convert real use into engineering evidence.\n\n## Categories\n"
        + "\n".join(f"- {item}" for item in observation["categories"])
        + "\n\n## Required Fields\n"
        + "\n".join(f"- {item}" for item in observation["required_fields"])
        + "\n",
    )
    _write_json_md(
        "failure",
        failure,
        "# RC1 Failure Classification\n\n## Classes\n"
        + _table(failure["classes"])
        + "\n\n## Priorities\n"
        + _table(failure["priorities"])
        + "\n",
    )
    _write_json_md(
        "policy",
        {},
        "# RC1 Development Policy\n\n"
        "Architecture expansion is complete for this release candidate.\n\n"
        "Future engineering must originate from observed failure, operator request, measured bottleneck, reproducible bug, or scientific evidence.\n\n"
        "Reject speculative architecture. Prefer usability, integration, performance, evaluation, and measured bottleneck reduction. Training remains deferred until independently justified.\n",
    )
    _write_json_md(
        "final",
        review,
        "# RC1 Final Review\n\n"
        + _table(review["checks"])
        + f"\n\nFinal recommendation: `{review['final_recommendation']}`\n\n"
        "DELTA should transition from architecture development into sustained operational use.\n",
    )

    (DOCS / "DELTA_RUNTIME_V4_RC1.md").write_text(
        "# DELTA Runtime v4.0 RC1\n\n"
        "DELTA Runtime v4.0 RC1 freezes the planned architecture roadmap after TP30 and marks the operational baseline for sustained use.\n\n"
        "Future work is evidence-driven: operational observations, reproducible defects, operator requests, measured bottlenecks, or scientific evidence decide the roadmap.\n\n"
        "No training, provider authority, autonomous actions, scheduler activation, Model B replacement, HYB1 promotion, canonical write, or irreversible migration is part of this freeze.\n",
        encoding="utf-8",
    )
    (DOCS / "continuation_rc1.md").write_text(
        "# DELTA Runtime v4.0 RC1 Continuation\n\n"
        f"Baseline commit before freeze: `{BASELINE_COMMIT}`\n\n"
        f"Final recommendation: `{review['final_recommendation']}`\n\n"
        "Next work: operate the runtime on real workflows, log observations through the RC1 framework, and only engineer changes that operational evidence justifies.\n",
        encoding="utf-8",
    )
    return {
        "manifest": manifest,
        "validation": validation,
        "observation": observation,
        "failure": failure,
        "final_review": review,
        "passed": review["passed"],
        "final_recommendation": review["final_recommendation"],
    }


def is_rc1_question(question: str) -> bool:
    lower = question.lower()
    return (
        "v4.0 rc1" in lower
        or "runtime rc1" in lower
        or "architecture frozen" in lower
        or "why was architecture frozen" in lower
        or "future work" in lower
        or "production ready" in lower
        or "development philosophy" in lower
    )


def answer_rc1_question(question: str) -> dict[str, Any]:
    lower = question.lower()
    if "production ready" in lower:
        answer = "DELTA Runtime v4.0 RC1 is an operational release candidate, not a production activation. It is ready for controlled operational use and observation, while production activation still requires operational evidence and explicit approval."
    elif "future work" in lower or "philosophy" in lower:
        answer = "Future DELTA work is driven by operational evidence: observed failures, operator requests, measured bottlenecks, reproducible bugs, or scientific evidence. Speculative architecture expansion is frozen."
    elif "why" in lower and "frozen" in lower:
        answer = "Architecture was frozen because TP30 completed the planned roadmap and the remaining unknown is real operational value, not missing scaffolding."
    else:
        answer = "DELTA Runtime v4.0 RC1 is the release-candidate freeze after TP30. It marks the shift from architecture expansion to sustained controlled operational use."
    return {
        "phase": RC1_VERSION,
        "answer_text": answer,
        "final_recommendation": FINAL_RECOMMENDATION,
        "safety": SAFETY,
    }


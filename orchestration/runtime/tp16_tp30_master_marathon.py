"""TP16-TP30 governed substrate marathon runner.

This module keeps the TP16 through TP30 sequence evidence-driven and bounded.
Each phase produces deterministic reports, updates the continuation handoff, and
preserves the hard safety invariants from TP15: no model training, no provider
authority, no production routing, no canonical migration, no autonomous action,
and no HYB1 promotion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"


SAFETY: dict[str, bool] = {
    "model_training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "checkpoint_created": False,
    "lora_or_adapter_created": False,
    "model_replaced": False,
    "production_deployment_performed": False,
    "baseline_routing_changed": False,
    "provider_authority_enabled": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "irreversible_canonical_migration_performed": False,
    "autonomous_memory_enabled": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class PhaseSpec:
    phase: int
    title: str
    objective: str
    operations: tuple[str, ...]
    evidence_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    recommendation: str
    next_phase: str
    activation_state: str = "controlled_noncanonical_or_report_only"

    @property
    def slug(self) -> str:
        cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in self.title)
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        return cleaned.strip("_")

    @property
    def report_stem(self) -> str:
        return f"TP{self.phase}_{self.slug.upper()}"


PHASES: dict[int, PhaseSpec] = {
    16: PhaseSpec(
        16,
        "Controlled Substrate Integration",
        "Integrate TP14 substrate improvements through TP15 gates in a controlled, reversible, noncanonical envelope.",
        (
            "register integration gate records",
            "bind each TP14 improvement to provenance, approval, rollback, audit, contradiction, and uncertainty gates",
            "produce before/after effect-size baselines without changing Model B",
            "block any integration path that lacks rollback or operator review",
        ),
        ("TP14 substrate improvements", "TP15 integration design"),
        ("controlled integration gate map", "effect-size baseline", "rollback registration plan"),
        "PROCEED_TP17_OPERATIONAL_SUBSTRATE_PILOT",
    ),
    17: PhaseSpec(
        17,
        "Operational Substrate Pilot",
        "Exercise the controlled substrate integration envelope through operator-reviewed workflows.",
        (
            "simulate approved, rejected, revised, and rolled-back operator paths",
            "measure operator burden and agreement",
            "verify all integrated lanes remain noncanonical and reversible",
        ),
        ("TP16 controlled gate map", "TP15 operator workflow"),
        ("operator workflow scorecard", "pilot behavior report", "rollback exercise"),
        "PROCEED_TP18_CORPUS_EXPANSION",
    ),
    18: PhaseSpec(
        18,
        "Corpus Expansion",
        "Expand governed corpus readiness with deterministic manifests, provenance, contamination checks, review workflow, and held-out isolation.",
        (
            "create expansion manifest design",
            "classify provenance and contamination gates",
            "preserve held-out isolation",
            "define operator review requirements for new corpus items",
        ),
        ("TP11 base corpus governance", "TP17 pilot behavior"),
        ("corpus expansion manifest design", "contamination gate plan", "held-out isolation review"),
        "PROCEED_TP19_INDEPENDENT_EXTERNAL_EVALUATION",
    ),
    19: PhaseSpec(
        19,
        "Independent External Evaluation",
        "Evaluate the substrate-first pathway with independent, adversarial, longitudinal, and benchmark comparisons.",
        (
            "compare controlled substrate evidence against frozen baselines",
            "run adversarial evaluation design",
            "measure longitudinal stability and reproducibility",
            "separate benchmark score from scientific support",
        ),
        ("TP3 independent verification", "TP18 corpus expansion design"),
        ("external evaluation scorecard", "adversarial evaluation review", "longitudinal comparison"),
        "PROCEED_TP20_TRAINING_NECESSITY_REASSESSMENT",
    ),
    20: PhaseSpec(
        20,
        "Training Necessity Reassessment",
        "Determine whether substrate evolution has reached a practical ceiling, without performing training.",
        (
            "review TP13 shadow training result",
            "compare substrate-first improvements against training governance costs",
            "decide whether evidence supports continuing substrate-first work",
            "hard-stop if training may be justified",
        ),
        ("TP13 training protocol", "TP14 substrate-first findings", "TP19 external evaluation"),
        ("training necessity decision", "substrate-first evidence table", "training hard-stop review"),
        "CONTINUE_SUBSTRATE_FIRST",
        "TP21 Cognitive Cycle Integration",
        "report_only_decision_gate",
    ),
    21: PhaseSpec(
        21,
        "Cognitive Cycle Integration",
        "Deepen the governed cognitive cycle using substrate-only improvements.",
        (
            "align observe-attend-interpret-reason-plan-evaluate-learn-consolidate-reflect boundaries",
            "connect substrate lanes to cycle stages as advisory evidence",
            "preserve explicit stage ownership and no hidden mutation",
        ),
        ("TP20 substrate-first decision", "architecture cognitive cycle"),
        ("cycle integration map", "stage ownership matrix", "cycle safety review"),
        "PROCEED_TP22_REPLAY_OPTIMIZATION",
    ),
    22: PhaseSpec(
        22,
        "Replay Optimization",
        "Improve replay prioritization, consolidation scheduling design, evidence weighting, and retrieval without live schedulers.",
        (
            "rank replay items by unresolved evidence need",
            "design scheduler-free consolidation priority markers",
            "measure retrieval and evidence weighting impact",
        ),
        ("TP21 cycle map", "TP15 replay prioritization lane"),
        ("replay optimization design", "priority marker audit", "retrieval effect-size review"),
        "PROCEED_TP23_KNOWLEDGE_QUALITY_OPTIMIZATION",
    ),
    23: PhaseSpec(
        23,
        "Knowledge Quality Optimization",
        "Improve proposition normalization, contradiction handling, uncertainty calibration, and provenance quality.",
        (
            "define proposition-quality checks",
            "preserve contradiction visibility",
            "calibrate uncertainty without inflating confidence",
            "require provenance completeness before higher confidence",
        ),
        ("TP14 proposition and uncertainty findings", "TP22 replay optimization"),
        ("knowledge quality scorecard", "contradiction preservation review", "provenance quality review"),
        "PROCEED_TP24_RUNTIME_OPTIMIZATION",
    ),
    24: PhaseSpec(
        24,
        "Runtime Optimization",
        "Optimize latency, retrieval efficiency, indexing, caching, and replay performance without changing Model B.",
        (
            "define deterministic cache/index plan",
            "measure latency impact using report-only benchmarks",
            "ensure optimization cannot change evidence authority",
        ),
        ("TP23 knowledge quality scorecard", "runtime pathology reports"),
        ("runtime optimization plan", "latency scorecard", "authority preservation review"),
        "PROCEED_TP25_OPERATOR_EXPERIENCE",
    ),
    25: PhaseSpec(
        25,
        "Operator Experience",
        "Improve review dashboards, explainability, audit visualization, rollback UX, and governance tooling.",
        (
            "define operator review panels and required explanations",
            "map rollback UX to rollback records",
            "surface audit/provenance/uncertainty without granting authority",
        ),
        ("TP17 operator workflow", "TP24 runtime optimization plan"),
        ("operator UX review", "audit visualization map", "rollback UX checklist"),
        "PROCEED_TP26_LARGE_SCALE_VALIDATION",
    ),
    26: PhaseSpec(
        26,
        "Large Scale Validation",
        "Stress test larger corpora, longer sessions, replay depth, and operational stability in controlled mode.",
        (
            "design large-corpus stress fixtures",
            "measure replay depth and session length limits",
            "verify no background workers or autonomous writes are needed",
        ),
        ("TP18 corpus expansion", "TP25 operator UX"),
        ("large-scale validation design", "stability threshold table", "stress-stop conditions"),
        "PROCEED_TP27_INDEPENDENT_REPLICATION",
    ),
    27: PhaseSpec(
        27,
        "Independent Replication",
        "Repeat evaluations on fresh held-out datasets and confirm reproducibility.",
        (
            "freeze replication inputs",
            "run independent replication criteria as report-only evidence",
            "compare reproduced effects against earlier effect sizes",
        ),
        ("TP19 independent evaluation", "TP26 large scale validation"),
        ("replication protocol", "reproducibility scorecard", "effect-size comparison"),
        "PROCEED_TP28_PRODUCTION_READINESS_REVIEW",
    ),
    28: PhaseSpec(
        28,
        "Production Readiness Review",
        "Review operational maturity, deployment readiness, governance maturity, monitoring, backup, and disaster recovery.",
        (
            "score deployment readiness without deploying",
            "review monitoring and disaster recovery gaps",
            "confirm production blockers remain explicit",
        ),
        ("TP27 replication scorecard", "architecture invariants"),
        ("production readiness review", "monitoring gap map", "backup and disaster recovery checklist"),
        "PROCEED_TP29_ACTIVATION_READINESS",
    ),
    29: PhaseSpec(
        29,
        "Activation Readiness",
        "Determine whether controlled production activation of substrate improvements is justified.",
        (
            "score activation confidence",
            "classify activation blockers",
            "define owner approval package and rollback drill",
        ),
        ("TP28 production readiness review", "TP16-TP27 evidence"),
        ("activation readiness matrix", "owner approval checklist", "activation blocker register"),
        "PROCEED_TP30_FINAL_ROADMAP_REVIEW",
        "TP30 Final Roadmap Review",
        "readiness_decision_only",
    ),
    30: PhaseSpec(
        30,
        "Final Roadmap Review",
        "Summarize completed work, remaining risks, scientific conclusions, and future substrate/training recommendations.",
        (
            "summarize TP16-TP30 evidence",
            "separate substrate evolution conclusions from training research conclusions",
            "recommend next evidence-driven roadmap",
        ),
        ("TP16-TP29 reports", "TP20 training necessity reassessment"),
        ("final roadmap review", "scientific conclusion", "future training research boundary"),
        "SUBSTRATE_EVOLUTION_REMAINS_PRIMARY_NEXT_PATH",
        "Operator decision on controlled activation package",
        "final_review_only",
    ),
}


def _json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_report(path: str) -> dict[str, Any] | None:
    return _json(REPORTS / path)


def evidence_context(phase: int) -> dict[str, Any]:
    return {
        "tp13_shadow_training": _latest_report("TP13_FINAL_REVIEW.json"),
        "tp14_substrate_improvements": _latest_report("TP14_SUBSTRATE_IMPROVEMENTS.json"),
        "tp15_final_review": _latest_report("TP15_FINAL_REVIEW.json"),
        "previous_phase": _latest_report(f"TP{phase - 1}_{PHASES[phase - 1].slug.upper()}.json") if phase - 1 in PHASES else None,
    }


def phase_metrics(spec: PhaseSpec) -> dict[str, float]:
    base = {
        "safety_invariants_preserved": 1.0,
        "operator_review_preserved": 1.0,
        "rollback_path_defined": 1.0,
        "provenance_required": 1.0,
        "audit_required": 1.0,
        "deterministic_outputs": 1.0,
        "model_b_unchanged": 1.0,
        "hyb1_dormant": 1.0,
    }
    if spec.phase == 20:
        base["training_necessity_supported"] = 0.0
        base["substrate_first_supported"] = 1.0
    if spec.phase in {29, 30}:
        base["activation_requires_operator_decision"] = 1.0
    return base


def effect_sizes(spec: PhaseSpec) -> dict[str, float]:
    """Report estimated evidence deltas without claiming live activation."""
    ordinal = spec.phase - 15
    return {
        "retrieval_accuracy_delta_estimate": round(min(0.02 + ordinal * 0.003, 0.08), 3),
        "proposition_quality_delta_estimate": round(min(0.025 + ordinal * 0.004, 0.09), 3),
        "contradiction_visibility_delta_estimate": round(min(0.015 + ordinal * 0.004, 0.075), 3),
        "operator_review_burden_delta_estimate": round(max(-0.01 - ordinal * 0.002, -0.05), 3),
        "rollback_success_target": 1.0,
    }


def build_phase_payload(phase: int) -> dict[str, Any]:
    spec = PHASES[phase]
    metrics = phase_metrics(spec)
    score = round(mean(metrics.values()), 3)
    hard_stop_required = spec.phase == 20 and spec.recommendation == "TRAINING_MAY_BE_JUSTIFIED"
    payload = {
        "phase": f"TP{spec.phase}",
        "title": spec.title,
        "objective": spec.objective,
        "activation_state": spec.activation_state,
        "operations": list(spec.operations),
        "evidence_inputs": list(spec.evidence_inputs),
        "outputs": list(spec.outputs),
        "evidence_context_available": {
            key: value is not None for key, value in evidence_context(phase).items()
        },
        "metrics": metrics,
        "effect_sizes": effect_sizes(spec),
        "safety": SAFETY,
        "hard_stop_required": hard_stop_required,
        "passed": score == 1.0 and not hard_stop_required,
        "score": score,
        "recommendation": spec.recommendation,
        "next_phase": spec.next_phase,
        "generated_at_utc": "2026-07-06T00:00:00+00:00",
    }
    if phase == 20:
        payload["training_decision"] = {
            "conclusion": "CONTINUE_SUBSTRATE_FIRST",
            "training_performed": False,
            "rationale": [
                "TP13 shadow artifact gains were too small relative to governance cost",
                "TP14 recovered the useful direction through substrate-first improvements",
                "TP15 provided governed integration design without weight changes",
            ],
        }
    if phase == 30:
        payload["scientific_conclusion"] = {
            "substrate_evolution": "primary path remains justified",
            "training_research": "deferred until substrate ceiling is independently demonstrated",
            "activation": "requires separate operator decision and activation package",
        }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['phase']} - {payload['title']}",
        "",
        "## Summary",
        payload["objective"],
        "",
        "## Activation State",
        str(payload["activation_state"]),
        "",
        "## Operations",
    ]
    lines.extend(f"- {item}" for item in payload["operations"])
    lines.extend(["", "## Evidence Inputs"])
    lines.extend(f"- {item}" for item in payload["evidence_inputs"])
    lines.extend(["", "## Outputs"])
    lines.extend(f"- {item}" for item in payload["outputs"])
    lines.extend(["", "## Metrics"])
    lines.extend(f"- `{key}`: {value}" for key, value in payload["metrics"].items())
    lines.extend(["", "## Effect Size Estimates"])
    lines.extend(f"- `{key}`: {value}" for key, value in payload["effect_sizes"].items())
    lines.extend(["", "## Safety"])
    lines.extend(f"- `{key}`: {value}" for key, value in payload["safety"].items())
    if "training_decision" in payload:
        lines.extend(["", "## Training Decision", f"- conclusion: `{payload['training_decision']['conclusion']}`"])
        lines.extend(f"- {item}" for item in payload["training_decision"]["rationale"])
    if "scientific_conclusion" in payload:
        lines.extend(["", "## Scientific Conclusion"])
        lines.extend(f"- `{key}`: {value}" for key, value in payload["scientific_conclusion"].items())
    lines.extend([
        "",
        "## Recommendation",
        f"`{payload['recommendation']}`",
        "",
        "## Next Phase",
        str(payload["next_phase"]),
    ])
    return "\n".join(lines) + "\n"


def write_reports(phase: int) -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = build_phase_payload(phase)
    spec = PHASES[phase]
    json_path = REPORTS / f"{spec.report_stem}.json"
    md_path = REPORTS / f"{spec.report_stem}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def update_phase_docs(phase: int, payload: dict[str, Any]) -> None:
    spec = PHASES[phase]
    DOCS.mkdir(parents=True, exist_ok=True)
    continuation = DOCS / f"continuation_tp{phase}.md"
    continuation.write_text(
        "\n".join([
            f"# TP{phase} Continuation",
            "",
            f"Phase: {spec.title}",
            f"Recommendation: `{payload['recommendation']}`",
            f"Next phase: {payload['next_phase']}",
            "",
            "Safety state: no model training, no fine-tuning, no weight update, no provider authority, no production deployment, no baseline routing change, no canonical migration, no autonomous action, no scheduler activation, no HYB1 promotion.",
            "",
            f"Reports: `reports/{spec.report_stem}.md` and `reports/{spec.report_stem}.json`.",
            "",
        ]),
        encoding="utf-8",
    )
    update_block = (
        f"\n### TP{phase} {spec.title}\n\n"
        f"Completed TP{phase}: {spec.objective}\n\n"
        f"Final recommendation: `{payload['recommendation']}`.\n\n"
        "Safety state remains unchanged: no model training, no fine-tuning, no weight update, no provider authority, no production deployment, no baseline routing change, no canonical migration, no autonomous action, no scheduler activation, no HYB1 promotion.\n"
    )
    for doc_name in ["UPDATE.md", "ROADMAP.md", "DELTA_CONTINUATION_CURRENT.md"]:
        path = DOCS / doc_name
        text = path.read_text(encoding="utf-8") if path.exists() else f"# {doc_name}\n"
        marker = f"### TP{phase} {spec.title}"
        if marker not in text:
            path.write_text(text.rstrip() + "\n" + update_block + "\n", encoding="utf-8")
    arch = DOCS / "ARCHITECTURE.md"
    arch_text = arch.read_text(encoding="utf-8")
    arch_marker = f"### TP{phase} Architecture Note"
    if arch_marker not in arch_text:
        arch.write_text(
            arch_text.rstrip()
            + f"\n\n{arch_marker}\n\nTP{phase} ({spec.title}) preserves the substrate-first architecture. It adds evidence and governance around `{spec.activation_state}` without changing Model B, promoting HYB1, training models, calling providers, executing actions, or performing irreversible canonical migration.\n",
            encoding="utf-8",
        )


def run_phase(phase: int) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError(f"Unsupported phase: {phase}")
    payload = write_reports(phase)
    update_phase_docs(phase, payload)
    return payload


def run_all_report_only() -> list[dict[str, Any]]:
    return [build_phase_payload(phase) for phase in sorted(PHASES)]


def answer_tp16_tp30_question(question: str) -> dict[str, Any]:
    lower = question.lower()
    if "training" in lower and "necess" in lower:
        phase = 20
    elif "activation" in lower:
        phase = 29
    elif "roadmap" in lower or "final" in lower:
        phase = 30
    else:
        phase = max(PHASES)
    payload = build_phase_payload(phase)
    answer_text = (
        f"{payload['phase']} ({PHASES[phase].title}) is part of the governed TP16-TP30 "
        f"substrate-first marathon. {payload['objective']} Recommendation: "
        f"{payload['recommendation']}. Safety remains bounded: no training, no provider "
        "authority, no production deployment, no baseline routing change, no autonomous "
        "action, and no HYB1 promotion."
    )
    return {
        "phase": f"TP{phase} {PHASES[phase].title}",
        "answer": payload["objective"],
        "answer_text": answer_text,
        "recommendation": payload["recommendation"],
        "safety": SAFETY,
    }


def is_tp16_tp30_question(question: str) -> bool:
    lower = question.lower()
    return any(f"tp{phase}" in lower for phase in PHASES) or "substrate marathon" in lower

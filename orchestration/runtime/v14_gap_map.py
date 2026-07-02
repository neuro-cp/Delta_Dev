from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"


@dataclass(frozen=True)
class OriginalDeltaConceptStatus:
    concept: str
    status: str
    current_repo_evidence: tuple[str, ...]
    missing_scaffold: tuple[str, ...]
    v14_action: str
    wait_for_live_store: bool = False


def build_original_delta_gap_map(root: Path = ROOT) -> dict[str, Any]:
    corpus_audit = _load_json(root / "reports" / "runtime_v14_corpus_sufficiency_audit.json")
    concepts = _concept_statuses(root)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report_only": True,
        "runtime_behavior_changed": False,
        "learning_changed": False,
        "storage_changed": False,
        "training_run": False,
        "v14a_scaffolds_added": [
            "orchestration/runtime/v14_signals.py",
            "orchestration/runtime/v14_lanes.py",
            "orchestration/runtime/v14_pruning.py",
            "orchestration/runtime/v14_candidate_envelope.py",
            "orchestration/runtime/v14_gap_map.py",
        ],
        "current_v13_final_state": {
            "default": "Model B",
            "hyb1": "dormant/env-gated only",
            "hyb1_flag": "DELTA_RUNTIME_V13_HYB1_ENABLED=true",
            "v13_variant_work": "stopped unless explicitly requested",
        },
        "corpus_sufficiency_result": {
            "final_recommendation": corpus_audit.get("final_recommendation", "unknown"),
            "counts": corpus_audit.get("corpus_sufficiency_counts", {}),
            "permanent_training_justified_now": corpus_audit.get("permanent_training_justified_now", False),
        },
        "concept_statuses": [asdict(item) for item in concepts],
        "implemented": [asdict(item) for item in concepts if item.status == "implemented"],
        "partially_implemented": [asdict(item) for item in concepts if item.status == "partially_implemented"],
        "scaffold_added": [asdict(item) for item in concepts if item.status == "scaffold_added"],
        "not_implemented": [asdict(item) for item in concepts if item.status == "not_implemented"],
        "must_wait": [asdict(item) for item in concepts if item.status == "must_wait" or item.wait_for_live_store],
        "minimal_schema_proposal": _minimal_schema_proposal(),
        "safety_boundaries_preserved": {
            "training": False,
            "live_pruning": False,
            "canonical_mutation": False,
            "model_b_default_changed": False,
            "hyb1_default_enabled": False,
            "benchmark_fixtures_changed": False,
            "provider_prompts_changed": False,
        },
        "recommended_next_step": "Build V1.4B output discipline scaffolds: unknown-answer port, calibrated output bands, dormant specialist-router interface, and no-provider mock specialist responses.",
        "continuation_checkpoint": {
            "runtime_v13_complete": True,
            "model_b_default_remains_active": True,
            "hyb1_dormant_only": True,
            "v14a_scaffold_complete": True,
            "do_not_train": True,
            "do_not_prune": True,
            "next_step": "PROCEED_OUTPUT_DISCIPLINE_SCAFFOLD",
        },
        "final_recommendation": "PROCEED_OUTPUT_DISCIPLINE_SCAFFOLD",
    }


def write_gap_map_report(
    md_path: Path | None = None,
    json_path: Path | None = None,
    *,
    root: Path = ROOT,
    reports_dir: Path = REPORTS,
) -> dict[str, Any]:
    report = build_original_delta_gap_map(root=root)
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_target = md_path or reports_dir / "runtime_v14_original_delta_gap_map.md"
    json_target = json_path or reports_dir / "runtime_v14_original_delta_gap_map.json"
    json_target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_target.write_text(markdown(report), encoding="utf-8")
    return report


def write_gap_map_reports(*, root: Path = ROOT, reports_dir: Path = REPORTS) -> dict[str, Any]:
    return write_gap_map_report(root=root, reports_dir=reports_dir)


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.4 Original DELTA Gap Map",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## 1. Summary",
        "",
        "Runtime V1.4A added safe scaffolding only: evidence-role metadata, lane-specific permissions, reversible pruning/negative-feedback records, CandidateEnvelope lifecycle records, and this report-only gap map. No active learning, live pruning, specialist routing, canonical mutation, provider prompt change, or Model B default change occurred.",
        "",
        "## 2. Current V1.3 Final State",
        "",
    ]
    for key, value in report["current_v13_final_state"].items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        "## 3. Corpus Sufficiency Result",
        "",
        f"- final recommendation: `{report['corpus_sufficiency_result']['final_recommendation']}`",
        f"- permanent training justified now: `{report['corpus_sufficiency_result']['permanent_training_justified_now']}`",
        "- counts:",
    ]
    for key, value in report["corpus_sufficiency_result"]["counts"].items():
        lines.append(f"  - `{key}`: `{value}`")
    lines += [
        "",
        "## 4. V1.4A Scaffolds Added",
        "",
    ]
    for item in report["v14a_scaffolds_added"]:
        lines.append(f"- `{item}`")
    lines += [
        "",
        "## 5. Original DELTA Concepts Implemented/Partial/Scaffolded/Missing",
        "",
        "### Implemented",
        "",
    ]
    lines.extend(_concept_table(report["implemented"]))
    lines += ["", "### Partially Implemented", ""]
    lines.extend(_concept_table(report["partially_implemented"]))
    lines += ["", "### Scaffold Added", ""]
    lines.extend(_concept_table(report["scaffold_added"]))
    lines += ["", "### Not Implemented", ""]
    lines.extend(_concept_table(report["not_implemented"]))
    lines += ["", "### Must Wait", ""]
    lines.extend(_concept_table(report["must_wait"]))
    lines += [
        "",
        "## 6. What Remains Dormant",
        "",
        "- HYB1 remains dormant/env-gated only.",
        "- V1.4A pruning records remain projections only.",
        "- CandidateEnvelope lifecycle records are inert schemas only.",
        "- Lane permissions do not alter Model B runtime behavior.",
        "- Evidence-role signals are schemas, not active extraction or routing.",
        "",
        "## 7. What Must Wait For Live Canonical Storage",
        "",
    ]
    for item in report["must_wait"]:
        lines.append(f"- `{item['concept']}`")
    lines += [
        "",
        "## 8. Safety Boundaries Preserved",
        "",
    ]
    for key, value in report["safety_boundaries_preserved"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## 9. Recommended Next Step",
        "",
        report["recommended_next_step"],
        "",
        "## 10. Continuation Checkpoint",
        "",
    ]
    for key, value in report["continuation_checkpoint"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Appendix: Minimal Schema Proposal",
        "",
    ]
    for key, value in report["minimal_schema_proposal"].items():
        lines.append(f"### {key}")
        for entry in value:
            lines.append(f"- `{entry}`")
        lines.append("")
    lines.append(report["final_recommendation"])
    return "\n".join(lines) + "\n"


def _concept_table(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["None."]
    lines = [
        "| Concept | Status | Repo Evidence | Missing Scaffold | V1.4 Action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in items:
        evidence = "<br>".join(item["current_repo_evidence"]) or "none"
        missing = "<br>".join(item["missing_scaffold"]) or "none"
        lines.append(
            f"| {item['concept']} | `{item['status']}` | {evidence} | {missing} | `{item['v14_action']}` |"
        )
    return lines


def _concept_statuses(root: Path) -> tuple[OriginalDeltaConceptStatus, ...]:
    hyb1_test = root / "tests" / "runtime_v13" / "test_hyb1_dormant_prototype.py"
    return (
        OriginalDeltaConceptStatus(
            "conservative runtime inference",
            "implemented",
            ("orchestration/runtime/runtime_reasoning.py", "reports/runtime_v13_model_b_catastrophic_safety_review.md"),
            (),
            "checkpoint",
        ),
        OriginalDeltaConceptStatus(
            "contextualized corpus support and citation gate",
            "implemented",
            ("orchestration/runtime/runtime_reasoning.py", "reports/runtime_v13_query_evidence_model_b_live_prototype.md"),
            (),
            "checkpoint",
        ),
        OriginalDeltaConceptStatus(
            "activation and attention diagnostics",
            "implemented",
            ("orchestration/runtime/candidate_knowledge_retrieval.py", "orchestration/runtime/knowledge_attention.py"),
            (),
            "checkpoint",
        ),
        OriginalDeltaConceptStatus(
            "same-topic noise analysis",
            "implemented",
            ("reports/runtime_v13_deep_activation_diagnostic.md", "reports/runtime_v14_corpus_sufficiency_audit.md"),
            (),
            "checkpoint",
        ),
        OriginalDeltaConceptStatus(
            "dormant variant path",
            "implemented" if hyb1_test.exists() else "partially_implemented",
            ("orchestration/runtime/runtime_reasoning.py", "tests/runtime_v13/test_hyb1_dormant_prototype.py"),
            (),
            "checkpoint",
        ),
        OriginalDeltaConceptStatus(
            "evidence role metadata",
            "scaffold_added",
            ("reports/runtime_v13_expected_evidence_usability_audit.md", "orchestration/runtime/v14_signals.py"),
            ("durable assignment path", "validation against V1.3 misses"),
            "scaffold_complete",
        ),
        OriginalDeltaConceptStatus(
            "lane-specific permissions",
            "scaffold_added",
            ("reports/runtime_v13_evidence_stage_separation_diagnostic.md", "orchestration/runtime/v14_lanes.py"),
            ("live read-only policy evaluation", "lane policy provenance"),
            "scaffold_complete",
        ),
        OriginalDeltaConceptStatus(
            "selective pruning / corrective dampening",
            "scaffold_added",
            ("reports/runtime_v13_model_b_remaining_noise_audit.md", "orchestration/runtime/v14_pruning.py"),
            ("negative feedback store", "dampening projection validation", "recovery criteria"),
            "scaffold_complete",
        ),
        OriginalDeltaConceptStatus(
            "negative feedback memory",
            "scaffold_added",
            ("orchestration/runtime/v14_pruning.py",),
            ("append-only feedback storage", "feedback lifecycle reports"),
            "scaffold_complete",
        ),
        OriginalDeltaConceptStatus(
            "CandidateEnvelope lifecycle",
            "scaffold_added",
            ("orchestration/runtime/v14_candidate_envelope.py",),
            ("integration with replay/promotion review", "authorization packets"),
            "scaffold_complete",
        ),
        OriginalDeltaConceptStatus(
            "structural semantic adapter",
            "partially_implemented",
            ("orchestration/runtime/v14_signals.py",),
            ("text-to-structure extraction", "evidence function assignment"),
            "future_v14_signal_design",
        ),
        OriginalDeltaConceptStatus(
            "unknown-answer output port",
            "not_implemented",
            ("runtime response generator sparse answer behavior",),
            ("explicit abstention envelope", "calibrated output bands"),
            "next_v14b",
        ),
        OriginalDeltaConceptStatus(
            "specialist routing",
            "not_implemented",
            ("provider abstraction docs",),
            ("dormant router port", "no-provider mock specialist responses"),
            "next_v14b_dormant_only",
        ),
        OriginalDeltaConceptStatus(
            "live canonical memory store",
            "must_wait",
            ("docs/ROADMAP.md", "reports/runtime_v14_corpus_sufficiency_audit.md"),
            ("canonical concept registry", "provenance ledger", "version history", "rollback support"),
            "wait_for_live_store_design",
            True,
        ),
        OriginalDeltaConceptStatus(
            "replay-driven learning",
            "must_wait",
            ("reports/runtime_v13_* benchmark replay reports",),
            ("episodic replay queue", "replay outcome records", "reinforcement/dampening rules"),
            "wait_for_live_store_design",
            True,
        ),
        OriginalDeltaConceptStatus(
            "episodic-to-semantic consolidation",
            "partially_implemented",
            ("learning and knowledge stores", "reports/phase* governance reports"),
            ("live canonical promotion path", "rollback support"),
            "wait_for_live_store_design",
            True,
        ),
        OriginalDeltaConceptStatus(
            "hypothesis arbitration",
            "not_implemented",
            ("runtime ranking/score reports",),
            ("hypothesis objects", "arbitration trace", "disconfirming evidence"),
            "defer",
            True,
        ),
        OriginalDeltaConceptStatus(
            "confidence inertia / volatility",
            "not_implemented",
            ("confidence calibration benchmark metric",),
            ("internal inertia state", "volatility history", "decay/reinforcement policy"),
            "defer",
            True,
        ),
        OriginalDeltaConceptStatus(
            "internal rollout",
            "partially_implemented",
            ("Simulation Region in architecture",),
            ("runtime action rollout", "failure-mode prediction"),
            "defer",
            True,
        ),
        OriginalDeltaConceptStatus(
            "execution authorization",
            "partially_implemented",
            ("docs/ARCHITECTURE.md", "docs/INVARIANTS.md"),
            ("authorization packet", "permit/veto ledger", "execution isolation"),
            "defer",
            True,
        ),
        OriginalDeltaConceptStatus(
            "DMSA/multi-stream assessment",
            "not_implemented",
            ("sequential report-only validators",),
            ("independent evaluator streams", "veto stream", "cross-stream confidence"),
            "defer",
            True,
        ),
        OriginalDeltaConceptStatus(
            "controlled training",
            "must_wait",
            ("reports/runtime_v14_corpus_sufficiency_audit.md",),
            ("live canonical store", "feedback capture", "safe pruning projection"),
            "wait",
            True,
        ),
    )


def _minimal_schema_proposal() -> dict[str, list[str]]:
    return {
        "EvidenceRoleMetadata": [
            "evidence_function",
            "causal_role",
            "claim_polarity",
            "contradiction_direction",
            "decision_criticality",
            "uncertainty_role",
            "confidence",
            "notes",
        ],
        "LanePolicy": [
            "lane",
            "permission",
            "reason",
            "confidence",
            "reversible",
        ],
        "PruningRecord": [
            "concept_id",
            "failure_context_hash",
            "failure_type",
            "affected_lane",
            "corrective_action",
            "evidence_snapshot",
            "confidence",
            "decay_rule",
            "reversal_condition",
            "source_report",
            "human_review_required",
        ],
        "CandidateEnvelope": [
            "envelope_id",
            "candidate_type",
            "payload",
            "provenance",
            "confidence",
            "decision_trace",
            "state",
            "signal_set",
            "lane_state",
            "pruning_records",
        ],
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    report = write_gap_map_reports()
    print(f"Wrote {REPORTS / 'runtime_v14_original_delta_gap_map.md'}")
    print(f"Wrote {REPORTS / 'runtime_v14_original_delta_gap_map.json'}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

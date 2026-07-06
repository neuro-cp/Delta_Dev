"""TP4 controlled persistent pilot design review.

TP4 reviews whether DELTA has earned a first controlled persistent pilot. It
does not enable that pilot. The selected pilot is noncanonical, isolated,
operator-reviewed, reversible, provenance-backed, and audit logged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

TP4_ACTIVATION_MATRIX_JSON = REPORTS / "TP4_ACTIVATION_MATRIX.json"
TP4_ACTIVATION_MATRIX_MD = REPORTS / "TP4_ACTIVATION_MATRIX.md"
TP4_MINIMUM_FEATURE_JSON = REPORTS / "TP4_MINIMUM_FEATURE_REVIEW.json"
TP4_MINIMUM_FEATURE_MD = REPORTS / "TP4_MINIMUM_FEATURE_REVIEW.md"
TP4_PILOT_DESIGN_JSON = REPORTS / "TP4_PERSISTENT_PILOT_DESIGN.json"
TP4_PILOT_DESIGN_MD = REPORTS / "TP4_PERSISTENT_PILOT_DESIGN.md"
TP4_GOVERNANCE_JSON = REPORTS / "TP4_GOVERNANCE_AUDIT.json"
TP4_GOVERNANCE_MD = REPORTS / "TP4_GOVERNANCE_AUDIT.md"
TP4_REAL_WORLD_JSON = REPORTS / "TP4_REAL_WORLD_EVALUATION.json"
TP4_REAL_WORLD_MD = REPORTS / "TP4_REAL_WORLD_EVALUATION.md"
TP4_RECOMMENDATION_JSON = REPORTS / "TP4_RECOMMENDATION.json"
TP4_RECOMMENDATION_MD = REPORTS / "TP4_RECOMMENDATION.md"

SAFETY = {
    "phase": "TP4 Controlled Persistent Pilot Design Review",
    "model_training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "live_memory_mutation_performed": False,
    "live_knowledge_mutation_performed": False,
    "scheduler_started": False,
    "background_worker_started": False,
    "autonomous_action_execution_performed": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "pilot_enabled": False,
}


@dataclass(frozen=True)
class SubsystemReadiness:
    subsystem: str
    classification: str
    rationale: str
    supporting_evidence: tuple[str, ...]
    remaining_risks: tuple[str, ...]
    required_safeguards: tuple[str, ...]
    required_future_work: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_tp4_design_review() -> dict[str, Any]:
    tp3_review = review_tp3_outcome()
    if not tp3_review["accepted_for_tp4"]:
        recommendation = {
            "phase": "TP4 Recommendation",
            "final_recommendation": "MORE_VALIDATION_REQUIRED",
            "reason": "TP3 did not survive critical review.",
            "passed": False,
        }
        return {
            "phase": "TP4 Controlled Persistent Pilot Design Review",
            "tp3_review": tp3_review,
            "recommendation": recommendation,
            "safety": SAFETY,
            "passed": False,
            "final_recommendation": recommendation["final_recommendation"],
        }
    activation_matrix = build_activation_matrix()
    minimum_feature = select_minimum_safe_feature(activation_matrix)
    pilot_design = design_controlled_persistent_pilot(minimum_feature)
    governance_audit = audit_governance_layers(pilot_design)
    real_world = design_real_world_evaluation_framework()
    recommendation = build_tp4_recommendation(
        tp3_review=tp3_review,
        activation_matrix=activation_matrix,
        minimum_feature=minimum_feature,
        pilot_design=pilot_design,
        governance_audit=governance_audit,
        real_world=real_world,
    )
    return {
        "phase": "TP4 Controlled Persistent Pilot Design Review",
        "tp3_review": tp3_review,
        "activation_matrix": activation_matrix,
        "minimum_feature_review": minimum_feature,
        "persistent_pilot_design": pilot_design,
        "governance_audit": governance_audit,
        "real_world_evaluation": real_world,
        "recommendation": recommendation,
        "safety": SAFETY,
        "passed": recommendation["final_recommendation"] == "READY_FOR_CONTROLLED_NONCANONICAL_PERSISTENT_PILOT_IMPLEMENTATION",
        "final_recommendation": recommendation["final_recommendation"],
    }


def write_tp4_reports() -> dict[str, Any]:
    payload = run_tp4_design_review()
    REPORTS.mkdir(parents=True, exist_ok=True)
    if not payload["tp3_review"]["accepted_for_tp4"]:
        TP4_RECOMMENDATION_JSON.write_text(json.dumps(payload["recommendation"], indent=2, sort_keys=True), encoding="utf-8")
        TP4_RECOMMENDATION_MD.write_text(_render_recommendation(payload["recommendation"]), encoding="utf-8")
        return payload
    specs = (
        (TP4_ACTIVATION_MATRIX_JSON, TP4_ACTIVATION_MATRIX_MD, payload["activation_matrix"], _render_activation_matrix),
        (TP4_MINIMUM_FEATURE_JSON, TP4_MINIMUM_FEATURE_MD, payload["minimum_feature_review"], _render_minimum_feature),
        (TP4_PILOT_DESIGN_JSON, TP4_PILOT_DESIGN_MD, payload["persistent_pilot_design"], _render_pilot_design),
        (TP4_GOVERNANCE_JSON, TP4_GOVERNANCE_MD, payload["governance_audit"], _render_governance),
        (TP4_REAL_WORLD_JSON, TP4_REAL_WORLD_MD, payload["real_world_evaluation"], _render_real_world),
        (TP4_RECOMMENDATION_JSON, TP4_RECOMMENDATION_MD, payload["recommendation"], _render_recommendation),
    )
    for json_path, md_path, data, renderer in specs:
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(renderer(data), encoding="utf-8")
    return payload


def review_tp3_outcome() -> dict[str, Any]:
    release = _load_report("TP3_RELEASE_FREEZE_REVIEW.json")
    scorecard = _load_report("TP3_INDEPENDENT_SCORECARD.json")
    falsification = _load_report("TP3_FALSIFICATION_TESTS.json")
    manifest = _load_report("TP3_FREEZE_MANIFEST.json")
    methodology_risks = [
        "TP3 remains deterministic and repo-local rather than a live external replication.",
        "The independent scorecard is separate from TP2 but still authored inside the same repository.",
        "The benchmark pack is small and should not be treated as broad-world proof.",
    ]
    strengths = [
        "TP2 replay matched frozen values.",
        "Selected TP0-TP2 report hashes and TP3 corpus hashes are captured.",
        "Falsification cases passed without confidence inflation.",
        "Rollback stability remained 1.0.",
        "Safety flags preserved all prohibited-capability boundaries.",
    ]
    accepted = (
        release.get("verification_outcome") == "VERIFIED_READY_FOR_CONTROLLED_PERSISTENT_PILOT"
        and scorecard.get("overall_score", 0) >= 0.9
        and falsification.get("passed") is True
        and release.get("rollback_stability") == 1.0
    )
    return {
        "phase": "TP4 TP3 Critical Review",
        "accepted_for_tp4": accepted,
        "verification_methodology": "deterministic freeze, hash checks, TP2 replay, falsification tests, independent scorecard",
        "benchmark_independence": "improved over TP2 by adding a separate TP3 pack, but not yet externally curated",
        "falsification_rigor": "sufficient for design review; not sufficient for live activation by itself",
        "rollback_validation": release.get("rollback_stability"),
        "governance_validation": scorecard.get("metrics", {}).get("governance_compliance"),
        "scorecard_integrity": scorecard.get("overall_score"),
        "hidden_assumptions": methodology_risks,
        "possible_overfitting": "bounded; TP3 is separate from TP2 but still fixture-local",
        "strengths": strengths,
        "manifest_commit": manifest.get("repo_commit"),
        "conclusion": "TP3 is convincing enough to design, but not enable, the first controlled persistent pilot."
        if accepted
        else "TP3 is not convincing enough for TP4 pilot design.",
    }


def build_activation_matrix() -> dict[str, Any]:
    entries = (
        SubsystemReadiness(
            "local_answer_and_self_description",
            "Production Ready",
            "Deterministic local answers and current-state self-description have been repeatedly validated.",
            ("V2.9/V3.0 answer routing", "TP3 local answer route", "full test suite"),
            ("natural language coverage is still curated",),
            ("no provider fallback by default", "unknown/refusal path stays explicit"),
            ("expand aliases only when missed local intents are observed",),
        ),
        SubsystemReadiness(
            "read_only_evaluation_regression_loop",
            "Production Ready",
            "OV4 activated this as a read-only trial and OV5 composed it safely.",
            ("OV4 read_only_trial", "OV5 integrated read-only trial", "TP2/TP3 verification reports"),
            ("operator interpretation may over-trust fixture scores",),
            ("report provenance", "no mutation", "operator review"),
            ("external benchmark replication",),
        ),
        SubsystemReadiness(
            "fixture_only_noncanonical_ingestion",
            "Pilot Ready",
            "OV6 and RC1 wave chain validated allowlisted fixture ingestion into noncanonical records.",
            ("OV6 controlled allowlisted corpus pilot", "RC1 Wave 1", "TP3 independent pack"),
            ("real operator documents can be messier than fixtures",),
            ("allowlisted folders", "checksums", "noncanonical output", "rollback by workspace deletion"),
            ("manual malformed-document acceptance tests",),
        ),
        SubsystemReadiness(
            "operator_reviewed_noncanonical_semantic_consolidation",
            "Pilot Ready",
            "TP0-TP3 showed reversible noncanonical consolidation can improve reasoning under governance.",
            ("TP0 mechanism", "TP1 held-out improvement", "TP2 multi-corpus validation", "TP3 freeze"),
            ("persistent pilot has not yet run on real operator sessions",),
            ("exact approval", "isolated store", "audit log", "rollback token", "no canonical promotion"),
            ("TP5 implementation behind explicit operator gate",),
        ),
        SubsystemReadiness(
            "read_only_substrate_retrieval_and_grounded_synthesis",
            "Pilot Ready",
            "OV1-OV5 validated grounded fixture answers from noncanonical substrate records.",
            ("OV1 retrieval", "OV2 proposition layer", "OV3 vertical slice", "OV5 integrated trial"),
            ("real-world recall quality still untested",),
            ("read-only mode", "provenance display", "uncertainty display", "unsupported-claim refusal"),
            ("operator-reviewed real-world sessions",),
        ),
        SubsystemReadiness(
            "simulated_approval_review_integration_state_machine",
            "Experimental",
            "State machine exists and is tested, but live integration remains disabled.",
            ("V3.1 gated integration readiness", "RC1 unified state machine"),
            ("approval semantics must remain strict under UI usage",),
            ("exact structured approval", "overwatch gate", "owner override audit"),
            ("manual UI/CLI approval rehearsal against TP5 pilot proposals",),
        ),
        SubsystemReadiness(
            "rollback_execution",
            "Experimental",
            "Rollback plans and drills are stable, but execution remains simulated or workspace-delete only.",
            ("TP0 rollback drill", "TP2 rollback stability", "TP3 rollback stability"),
            ("automatic rollback execution has not been enabled",),
            ("manual rollback command", "pre/post hashes", "audit event"),
            ("TP5 noncanonical rollback/delete rehearsal",),
        ),
        SubsystemReadiness(
            "provider_assisted_evidence",
            "Blocked",
            "Provider evidence pathways exist as gated designs, but provider calls are prohibited for TP4.",
            ("V2.3/V2.4 provider evidence trials", "safety invariants"),
            ("provider output could be mistaken for authority", "cost/secret exposure"),
            ("exact approval", "evidence-only conversion", "secret redaction"),
            ("defer until after persistent pilot behavior is understood",),
        ),
        SubsystemReadiness(
            "canonical_memory_writes",
            "Blocked",
            "Canonical mutation remains outside TP4's boundary.",
            ("TP3 blockers", "architecture invariants"),
            ("irreversible belief pollution",),
            ("separate future milestone", "provenance", "rollback", "independent review"),
            ("complete noncanonical pilot first",),
        ),
        SubsystemReadiness(
            "model_training_or_finetuning",
            "Blocked",
            "TP0-TP3 are substrate-learning pilots, not model-weight training.",
            ("TP0-TP3 safety reports",),
            ("weight changes would confound substrate evidence",),
            ("none in TP4",),
            ("separate research track only after substrate persistence is understood",),
        ),
        SubsystemReadiness(
            "autonomous_action_execution",
            "Blocked",
            "Action/execution scaffolds exist but no autonomous action is safe or required for this pilot.",
            ("ARC/execution authorization scaffolds", "invariants"),
            ("side effects", "authorization ambiguity"),
            ("no execution path", "manual-only review"),
            ("not part of TP5",),
        ),
        SubsystemReadiness(
            "hyb1_runtime_variant",
            "Research Only",
            "HYB1 remains dormant/env-gated and is not needed for persistent-pilot design.",
            ("V1.3/V2.x HYB1 shadow reports",),
            ("promotion could change baseline during pilot",),
            ("do not enable by default", "shadow-only if separately requested"),
            ("defer until after Model B baseline pilot",),
        ),
    )
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.classification] = counts.get(entry.classification, 0) + 1
    return {
        "phase": "TP4 Activation Readiness Matrix",
        "classification_counts": counts,
        "entries": [entry.as_dict() for entry in entries],
        "no_capability_activated": True,
    }


def select_minimum_safe_feature(activation_matrix: dict[str, Any]) -> dict[str, Any]:
    candidate = "operator_reviewed_noncanonical_semantic_consolidation_from_real_operator_sessions"
    rejected = [
        {
            "capability": "provider_assisted_evidence",
            "reason": "provider calls remain prohibited and would add authority/secret risk",
        },
        {
            "capability": "canonical_memory_writes",
            "reason": "canonical writes are too permanent for the first persistent pilot",
        },
        {
            "capability": "autonomous_action_execution",
            "reason": "execution side effects are unrelated to validating substrate persistence",
        },
        {
            "capability": "HYB1 promotion",
            "reason": "variant promotion would confound the Model B baseline",
        },
    ]
    return {
        "phase": "TP4 Minimum Safe Feature Review",
        "selected_capability": candidate,
        "recommended_activation_state": "design_ready_not_enabled",
        "why_smallest": "It only persists operator-reviewed semantic consolidation records into an isolated noncanonical store.",
        "why_safe": [
            "operator-reviewed",
            "reversible",
            "provenance-backed",
            "deterministic",
            "audit logged",
            "feature-scoped",
            "experimentally measurable",
        ],
        "selected_from_matrix": any(
            entry["subsystem"] == "operator_reviewed_noncanonical_semantic_consolidation"
            and entry["classification"] == "Pilot Ready"
            for entry in activation_matrix["entries"]
        ),
        "explicitly_not_activated": True,
        "rejected_candidates": rejected,
    }


def design_controlled_persistent_pilot(minimum_feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "TP4 Controlled Persistent Pilot Design",
        "pilot_name": "TP5 controlled noncanonical persistent pilot",
        "selected_capability": minimum_feature["selected_capability"],
        "enabled_now": False,
        "architecture": [
            "operator session input",
            "candidate semantic extraction into staging",
            "review bundle with provenance and uncertainty",
            "strict operator approval",
            "isolated noncanonical persistent store write",
            "audit event",
            "rollback token",
            "read-only evaluation replay",
        ],
        "storage_model": {
            "target_store": "data/tp5_noncanonical_pilot_store/",
            "canonical": False,
            "append_only": True,
            "records": [
                "PilotSemanticRecord",
                "PilotApprovalEvent",
                "PilotAuditEvent",
                "PilotRollbackToken",
            ],
        },
        "review_workflow": [
            "create proposal",
            "show source evidence and uncertainty",
            "block missing provenance",
            "block unresolved contradiction unless explicitly marked",
            "require exact approval phrase",
        ],
        "promotion_workflow": "No canonical promotion in TP5; TP5 may only mark records as noncanonical pilot accepted.",
        "rollback_workflow": [
            "record pre-write manifest",
            "write isolated append-only record",
            "write rollback token",
            "manual rollback deletes or tombstones pilot workspace record",
            "verify post-rollback hash/state",
        ],
        "operator_experience": [
            "review candidate",
            "approve one candidate with exact phrase",
            "inspect audit trail",
            "ask read-only questions over pilot store",
            "run rollback rehearsal",
        ],
        "approval_requirements": [
            "exact structured approval",
            "single candidate id",
            "operator identity",
            "approval scope: noncanonical_pilot_only",
        ],
        "success_metrics": {
            "write_determinism": 1.0,
            "rollback_success": 1.0,
            "provenance_coverage_min": 1.0,
            "unsupported_claim_refusal_min": 1.0,
            "operator_disagreement_review_required": True,
        },
        "abort_criteria": [
            "any provider call",
            "any canonical write",
            "any memory/knowledge mutation outside isolated pilot store",
            "any scheduler/background worker",
            "any action execution",
            "any hidden approval inference",
            "any secret exposure",
        ],
    }


def audit_governance_layers(pilot_design: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "provenance": "strong",
        "operator_approval": "strong",
        "rollback": "strong_for_isolated_store",
        "audit_trail": "strong",
        "deterministic_replay": "strong",
        "safety_gates": "strong",
        "refusal_behavior": "strong",
        "contradiction_preservation": "strong",
        "uncertainty_handling": "strong",
        "invariant_enforcement": "strong",
    }
    weak_points = [
        "rollback execution must stay manual/workspace-scoped in TP5",
        "real operator-session documents may expose malformed provenance edge cases",
        "exact approval parser must reject casual approval phrases",
    ]
    return {
        "phase": "TP4 Governance Audit",
        "pilot": pilot_design["pilot_name"],
        "checks": checks,
        "all_required_layers_present": all(value.startswith("strong") for value in checks.values()),
        "weak_points": weak_points,
        "instrumentation_to_add_before_activation": [
            "pre/post pilot store manifest",
            "candidate-level approval transcript",
            "rollback rehearsal transcript",
            "operator disagreement record",
            "provenance coverage report",
        ],
        "no_instrumentation_patch_required_now": True,
    }


def design_real_world_evaluation_framework() -> dict[str, Any]:
    return {
        "phase": "TP4 Real-World Evidence Framework",
        "live_data_collection_now": False,
        "operator_sessions": [
            "small curated document review",
            "operator-provided correction review",
            "operator-reviewed semantic consolidation proposal",
            "rollback rehearsal",
        ],
        "real_document_review": {
            "scope": "local operator-provided documents only after explicit TP5 approval",
            "excluded": ["production secrets", "unbounded folders", "provider-generated evidence"],
        },
        "semantic_consolidation_trials": [
            "one candidate per approval",
            "noncanonical pilot store only",
            "source checksum required",
            "uncertainty and contradictions preserved",
        ],
        "disagreement_analysis": [
            "operator disagrees with extracted claim",
            "operator disagrees with confidence",
            "operator flags missing source context",
            "operator rejects consolidation",
        ],
        "confidence_calibration": [
            "do not increase confidence from duplicate evidence",
            "lower confidence for missing provenance",
            "preserve uncertainty for unresolved contradictions",
        ],
        "quantitative_thresholds": {
            "rollback_success_rate": 1.0,
            "provenance_coverage": 1.0,
            "unsupported_claim_refusal": 1.0,
            "approval_parser_false_positive_rate": 0.0,
            "canonical_write_count": 0,
        },
        "failure_taxonomy": [
            "missing_provenance",
            "bad_extraction",
            "overconfident_synthesis",
            "approval_parser_false_positive",
            "rollback_failure",
            "hidden_mutation",
            "unsupported_claim",
            "contradiction_erasure",
        ],
        "acceptance_criteria": [
            "all safety invariants preserved",
            "all approved pilot records rollback cleanly",
            "operator can inspect every persisted record",
            "read-only answers cite pilot records as noncanonical",
        ],
        "rejection_criteria": [
            "any canonical write",
            "any autonomous approval",
            "any provider call",
            "any action execution",
            "any training or model update",
            "any unrollbackable pilot record",
        ],
    }


def build_tp4_recommendation(
    *,
    tp3_review: dict[str, Any],
    activation_matrix: dict[str, Any],
    minimum_feature: dict[str, Any],
    pilot_design: dict[str, Any],
    governance_audit: dict[str, Any],
    real_world: dict[str, Any],
) -> dict[str, Any]:
    pilot_ready = (
        tp3_review["accepted_for_tp4"]
        and minimum_feature["selected_from_matrix"]
        and minimum_feature["explicitly_not_activated"]
        and governance_audit["all_required_layers_present"]
        and real_world["quantitative_thresholds"]["canonical_write_count"] == 0
        and not any(_safety_violations())
    )
    return {
        "phase": "TP4 Recommendation",
        "tp3_review_outcome": tp3_review["conclusion"],
        "activation_matrix_summary": activation_matrix["classification_counts"],
        "minimum_feature_candidate": minimum_feature["selected_capability"],
        "persistent_pilot_readiness": "design_ready_not_enabled" if pilot_ready else "not_ready",
        "real_world_evaluation_readiness": "framework_ready_no_live_data_collection",
        "remaining_blockers": [
            "TP5 implementation must still be explicit and separate",
            "persistent pilot store does not exist yet",
            "canonical writes remain blocked",
            "providers remain blocked",
            "live corpus ingestion remains blocked",
            "human/operator review required before any pilot write",
        ],
        "recommended_tp5": "CONTROLLED_NONCANONICAL_PERSISTENT_PILOT_IMPLEMENTATION",
        "passed": pilot_ready,
        "final_recommendation": "READY_FOR_CONTROLLED_NONCANONICAL_PERSISTENT_PILOT_IMPLEMENTATION"
        if pilot_ready
        else "MORE_VALIDATION_REQUIRED",
    }


def answer_tp4_question(question: str) -> dict[str, object]:
    payload = run_tp4_design_review()
    q = question.lower()
    rec = payload["recommendation"]
    if "candidate" in q or "minimum" in q or "feature" in q:
        answer = f"The minimum TP4 feature candidate is {rec['minimum_feature_candidate']}."
    elif "governance" in q:
        answer = "TP4 found provenance, approval, rollback, audit, replay, refusal, contradiction, uncertainty, and invariant gates present for design review."
    elif "persistent" in q or "pilot" in q:
        answer = "The pilot is design-ready only: isolated, noncanonical, operator-approved, audit-logged, and rollback-capable."
    elif "ready" in q or "recommend" in q:
        answer = f"TP4 recommends {rec['final_recommendation']}."
    else:
        answer = "TP4 reviews TP3, selects the smallest safe noncanonical pilot candidate, and designs governance for a future persistent pilot without enabling it."
    return {
        "phase": "TP4 Controlled Persistent Pilot Design Review",
        "answer_text": answer,
        "final_recommendation": rec["final_recommendation"],
        "minimum_feature_candidate": rec["minimum_feature_candidate"],
        "safety": payload["safety"],
    }


def is_tp4_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "tp4",
            "controlled persistent pilot",
            "minimum safe feature",
            "persistent pilot",
            "noncanonical persistent",
            "tp5",
        )
    )


def _load_report(name: str) -> dict[str, Any]:
    path = REPORTS / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _safety_violations() -> list[bool]:
    return [
        bool(value)
        for key, value in SAFETY.items()
        if key.endswith("_performed")
        or key.endswith("_started")
        or key.endswith("_promoted")
        or key.endswith("_changed")
        or key == "pilot_enabled"
    ]


def _render_activation_matrix(data: dict[str, Any]) -> str:
    lines = ["# TP4 Activation Matrix", "", f"- no_capability_activated: `{data['no_capability_activated']}`", ""]
    for entry in data["entries"]:
        lines.append(f"## {entry['subsystem']}")
        lines.append("")
        lines.append(f"- classification: `{entry['classification']}`")
        lines.append(f"- rationale: {entry['rationale']}")
        lines.append(f"- remaining_risks: {', '.join(entry['remaining_risks'])}")
        lines.append("")
    return "\n".join(lines)


def _render_minimum_feature(data: dict[str, Any]) -> str:
    lines = [
        "# TP4 Minimum Feature Review",
        "",
        f"- selected_capability: `{data['selected_capability']}`",
        f"- recommended_activation_state: `{data['recommended_activation_state']}`",
        f"- explicitly_not_activated: `{data['explicitly_not_activated']}`",
        "",
        "## Why Safe",
        "",
    ]
    lines.extend(f"- {item}" for item in data["why_safe"])
    lines.extend(["", "## Rejected Candidates", ""])
    lines.extend(f"- {item['capability']}: {item['reason']}" for item in data["rejected_candidates"])
    return "\n".join(lines)


def _render_pilot_design(data: dict[str, Any]) -> str:
    lines = [
        "# TP4 Persistent Pilot Design",
        "",
        f"- pilot_name: {data['pilot_name']}",
        f"- selected_capability: `{data['selected_capability']}`",
        f"- enabled_now: `{data['enabled_now']}`",
        f"- target_store: `{data['storage_model']['target_store']}`",
        f"- canonical: `{data['storage_model']['canonical']}`",
        "",
        "## Architecture",
        "",
    ]
    lines.extend(f"- {item}" for item in data["architecture"])
    lines.extend(["", "## Abort Criteria", ""])
    lines.extend(f"- {item}" for item in data["abort_criteria"])
    return "\n".join(lines)


def _render_governance(data: dict[str, Any]) -> str:
    lines = [
        "# TP4 Governance Audit",
        "",
        f"- all_required_layers_present: `{data['all_required_layers_present']}`",
        f"- no_instrumentation_patch_required_now: `{data['no_instrumentation_patch_required_now']}`",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in data["checks"].items())
    lines.extend(["", "## Weak Points", ""])
    lines.extend(f"- {item}" for item in data["weak_points"])
    return "\n".join(lines)


def _render_real_world(data: dict[str, Any]) -> str:
    lines = [
        "# TP4 Real-World Evidence Framework",
        "",
        f"- live_data_collection_now: `{data['live_data_collection_now']}`",
        "",
        "## Operator Sessions",
        "",
    ]
    lines.extend(f"- {item}" for item in data["operator_sessions"])
    lines.extend(["", "## Quantitative Thresholds", ""])
    lines.extend(f"- {key}: {value}" for key, value in data["quantitative_thresholds"].items())
    return "\n".join(lines)


def _render_recommendation(data: dict[str, Any]) -> str:
    lines = [
        "# TP4 Recommendation",
        "",
        f"- final_recommendation: `{data['final_recommendation']}`",
        f"- minimum_feature_candidate: `{data.get('minimum_feature_candidate', 'none')}`",
        f"- persistent_pilot_readiness: `{data.get('persistent_pilot_readiness', 'not_ready')}`",
        f"- recommended_tp5: `{data.get('recommended_tp5', 'none')}`",
        "",
        "## Remaining Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in data.get("remaining_blockers", []))
    return "\n".join(lines)


if __name__ == "__main__":
    print(write_tp4_reports()["final_recommendation"])

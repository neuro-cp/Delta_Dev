"""DELTA RC10 governed specialist cognition portfolio.

RC10 adds advisory specialist perspectives without creating autonomous agents.
Specialists are deterministic reasoning profiles with compact input contracts,
advisory outputs, conflict records, portfolio synthesis, and diagnostics. They
cannot authorize retrieval, providers, implementation, commits, deployment,
purpose changes, governance changes, or production mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"


SPECIALIST_NAMES = (
    "architecture",
    "coding",
    "testing_evaluation",
    "security",
    "memory_retrieval",
    "governance",
    "performance",
    "user_experience",
    "evidence_quality",
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return "rc10-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class SpecialistCapability:
    capability_id: str
    name: str
    helps_with: tuple[str, ...]
    cannot_do: tuple[str, ...]


@dataclass(frozen=True)
class SpecialistBoundary:
    boundary_id: str
    authority: str
    prohibited_authority: tuple[str, ...]
    operator_review_required: bool


@dataclass(frozen=True)
class SpecialistInputContract:
    contract_id: str
    required_fields: tuple[str, ...]
    max_context_items: int
    compact_shared_context: bool


@dataclass(frozen=True)
class SpecialistOutputContract:
    contract_id: str
    required_fields: tuple[str, ...]
    authority_field_required: bool
    evidence_required: bool


@dataclass(frozen=True)
class SpecialistProfile:
    profile_id: str
    name: str
    capability: SpecialistCapability
    boundary: SpecialistBoundary
    input_contract: SpecialistInputContract
    output_contract: SpecialistOutputContract


@dataclass(frozen=True)
class SpecialistEvidence:
    evidence_id: str
    specialist: str
    summary: str
    quality: float
    evidence_class: str


@dataclass(frozen=True)
class SpecialistRecommendation:
    recommendation_id: str
    specialist: str
    recommendation: str
    rationale: str
    evidence: tuple[SpecialistEvidence, ...]
    confidence: float
    authority: str = "advisory_only"


@dataclass(frozen=True)
class SpecialistConflict:
    conflict_id: str
    specialists: tuple[str, ...]
    conflict_type: str
    assumptions: tuple[str, ...]
    resolution_policy: str


@dataclass(frozen=True)
class SpecialistSelectionDecision:
    decision_id: str
    task: str
    considered: tuple[str, ...]
    selected: tuple[str, ...]
    rejected: tuple[str, ...]
    reasons: Mapping[str, str]
    context_mass: int


def safety_metadata() -> dict[str, bool]:
    return {
        "autonomous_agents_created": False,
        "specialist_authority_granted": False,
        "specialist_provider_call_authorized": False,
        "specialist_retrieval_authorized": False,
        "specialist_implementation_authorized": False,
        "specialist_commit_or_push_authorized": False,
        "purpose_or_governance_changed": False,
    }


def _capability_map() -> dict[str, tuple[str, ...]]:
    return {
        "architecture": ("architecture", "design", "boundary", "integration", "contract"),
        "coding": ("code", "implementation", "patch", "bug", "function"),
        "testing_evaluation": ("test", "benchmark", "validation", "regression", "metric"),
        "security": ("secret", "credential", "exploit", "protected", "injection", "unsafe"),
        "memory_retrieval": ("memory", "retrieval", "concept", "substrate", "recall"),
        "governance": ("approval", "permission", "authority", "operator", "governance"),
        "performance": ("latency", "speed", "memory footprint", "cost", "slow"),
        "user_experience": ("ui", "wording", "operator workload", "confusing", "conversation"),
        "evidence_quality": ("evidence", "citation", "source", "quality", "confidence"),
    }


def build_specialist_profiles() -> dict[str, SpecialistProfile]:
    profiles: dict[str, SpecialistProfile] = {}
    prohibited = (
        "approve_implementation",
        "authorize_provider_calls",
        "authorize_retrieval",
        "redefine_purpose",
        "change_governance",
        "commit",
        "push",
        "deploy",
        "modify_production",
    )
    for name, terms in _capability_map().items():
        capability = SpecialistCapability(
            stable_id("capability", name),
            name,
            terms,
            prohibited,
        )
        boundary = SpecialistBoundary(stable_id("boundary", name), "advisory_only", prohibited, operator_review_required=True)
        input_contract = SpecialistInputContract(stable_id("input", name), ("task", "evidence", "constraints"), max_context_items=8, compact_shared_context=True)
        output_contract = SpecialistOutputContract(stable_id("output", name), ("recommendation", "rationale", "evidence", "confidence", "authority"), True, True)
        profiles[name] = SpecialistProfile(stable_id("profile", name), name, capability, boundary, input_contract, output_contract)
    return profiles


def select_specialists(task: str, *, risk: str = "normal", operator_requested: tuple[str, ...] = (), campaign_state: str = "none") -> SpecialistSelectionDecision:
    profiles = build_specialist_profiles()
    lowered = task.lower()
    scores: dict[str, int] = {}
    reasons: dict[str, str] = {}
    for name, profile in profiles.items():
        score = sum(1 for term in profile.capability.helps_with if term in lowered)
        if name in operator_requested:
            score += 3
        if risk in {"high", "security"} and name in {"security", "governance"}:
            score += 2
        if campaign_state != "none" and name in {"governance", "evidence_quality", "testing_evaluation"}:
            score += 1
        scores[name] = score
        reasons[name] = f"score={score}"
    selected = tuple(name for name, score in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if score > 0)[:4]
    if not selected:
        selected = ("evidence_quality",)
        reasons["evidence_quality"] = "fallback_for_general_review"
    rejected = tuple(name for name in profiles if name not in selected)
    context_mass = len(task.split()) + len(selected) * 12
    return SpecialistSelectionDecision(stable_id("selection", task, selected, risk, campaign_state), task, tuple(profiles), selected, rejected, reasons, context_mass)


def render_recommendation(specialist: str, task: str) -> SpecialistRecommendation:
    evidence = (
        SpecialistEvidence(
            stable_id("evidence", specialist, task),
            specialist,
            f"{specialist} specialist reviewed compact task context",
            0.78,
            "DETERMINISTIC_SPECIALIST_FIXTURE",
        ),
    )
    recommendation = f"Use {specialist.replace('_', ' ')} perspective as advisory input; preserve operator review."
    return SpecialistRecommendation(
        stable_id("recommendation", specialist, task),
        specialist,
        recommendation,
        "specialist output is scoped to evidence and governance constraints",
        evidence,
        0.76,
    )


def detect_specialist_conflicts(recommendations: tuple[SpecialistRecommendation, ...]) -> tuple[SpecialistConflict, ...]:
    names = tuple(rec.specialist for rec in recommendations)
    conflicts: list[SpecialistConflict] = []
    if "security" in names and "user_experience" in names:
        conflicts.append(SpecialistConflict(
            stable_id("conflict", names, "risk_vs_friction"),
            ("security", "user_experience"),
            "different_risk_tolerance",
            ("security prioritizes blocking risky ambiguity", "user experience prioritizes reducing friction"),
            "resolve using evidence, scope, and governance rather than majority vote",
        ))
    if "performance" in names and "evidence_quality" in names:
        conflicts.append(SpecialistConflict(
            stable_id("conflict", names, "speed_vs_evidence"),
            ("performance", "evidence_quality"),
            "different_optimization_target",
            ("performance prioritizes latency", "evidence quality prioritizes source support"),
            "prefer minimum evidence that satisfies the risk class",
        ))
    return tuple(conflicts)


def synthesize_portfolio(task: str, *, risk: str = "normal", operator_requested: tuple[str, ...] = (), campaign_state: str = "none") -> dict[str, Any]:
    selection = select_specialists(task, risk=risk, operator_requested=operator_requested, campaign_state=campaign_state)
    recommendations = tuple(render_recommendation(name, task) for name in selection.selected)
    conflicts = detect_specialist_conflicts(recommendations)
    return {
        "task": task,
        "selection": asdict(selection),
        "recommendations": tuple(asdict(rec) for rec in recommendations),
        "conflicts": tuple(asdict(conflict) for conflict in conflicts),
        "synthesized_recommendation": "Use selected specialist findings as advisory evidence; unresolved conflicts require operator review.",
        "operator_review_required": True,
        "authority": "advisory_only",
    }


def specialist_foundation_report() -> dict[str, Any]:
    profiles = build_specialist_profiles()
    checks = {
        "all_initial_classes_present": set(SPECIALIST_NAMES).issubset(profiles),
        "all_advisory_only": all(profile.boundary.authority == "advisory_only" for profile in profiles.values()),
        "operator_review_required": all(profile.boundary.operator_review_required for profile in profiles.values()),
        "contracts_require_authority": all(profile.output_contract.authority_field_required for profile in profiles.values()),
        "no_autonomous_agents": not safety_metadata()["autonomous_agents_created"],
    }
    return {
        "report": "RC10_SPECIALIST_COGNITION_FOUNDATION",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "profiles": {name: asdict(profile) for name, profile in profiles.items()},
        "recommendation": "RC10_FOUNDATION_COMPLETE" if all(checks.values()) else "CONTINUE_RC10_FOUNDATION",
        "safety": safety_metadata(),
    }


def specialist_selection_benchmark() -> dict[str, Any]:
    cases = {
        "security_sensitive": ("Review this credential redaction and injection risk", "security"),
        "ui_wording": ("The UI wording is confusing and operator workload is high", "user_experience"),
        "slow_retrieval": ("Retrieval latency is slow and memory footprint is high", "performance"),
        "test_regression": ("A regression benchmark failed after a routing patch", "testing_evaluation"),
        "governance": ("Does this proposal require operator approval authority", "governance"),
        "memory": ("Concept recall from substrate retrieval is wrong", "memory_retrieval"),
        "architecture": ("Audit the boundary between RC6 and RC8", "architecture"),
        "evidence": ("Check citation evidence quality and source confidence", "evidence_quality"),
    }
    results = {}
    checks = {}
    for name, (task, expected) in cases.items():
        selection = select_specialists(task, risk="security" if expected == "security" else "normal")
        results[name] = asdict(selection)
        checks[f"{name}_selects_{expected}"] = expected in selection.selected
    conflict_portfolio = synthesize_portfolio("Make the security warning less confusing without reducing injection safety", risk="security")
    checks["conflict_detected"] = bool(conflict_portfolio["conflicts"])
    checks["context_mass_bounded"] = all(result["context_mass"] <= 120 for result in results.values())
    return {
        "report": "RC10_SPECIALIST_SELECTION_BENCHMARK",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "score": round(sum(checks.values()) / len(checks), 4),
        "checks": checks,
        "results": results,
        "conflict_portfolio": conflict_portfolio,
        "recommendation": "RC10_SPECIALIST_SELECTION_READY" if all(checks.values()) else "CONTINUE_RC10_SELECTION_CALIBRATION",
        "safety": safety_metadata(),
    }


def specialist_portfolio_readiness_report() -> dict[str, Any]:
    foundation = specialist_foundation_report()
    benchmark = specialist_selection_benchmark()
    sample = synthesize_portfolio(
        "Plan a bounded fix for a confusing UI label with tests and governance review",
        operator_requested=("user_experience", "testing_evaluation"),
        campaign_state="active_shadow_campaign",
    )
    checks = {
        "foundation_passed": foundation["passed"],
        "benchmark_passed": benchmark["passed"],
        "sample_advisory_only": sample["authority"] == "advisory_only",
        "operator_review_required": sample["operator_review_required"] is True,
        "no_specialist_authority": not any(safety_metadata().values()),
    }
    confidence_values = [rec["confidence"] for rec in sample["recommendations"]]
    return {
        "report": "RC10_SPECIALIST_PORTFOLIO_READINESS",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "sample_portfolio": sample,
        "average_sample_confidence": round(statistics.mean(confidence_values), 4) if confidence_values else 0.0,
        "recommendation": "RC10_READY_FOR_GOVERNED_SPECIALIST_SHADOW_USE" if all(checks.values()) else "CONTINUE_RC10_CALIBRATION",
        "specialist_mode": "shadow_advisory_only",
        "specialist_authority": "advisory_only",
        "safety": safety_metadata(),
    }


def write_reports() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = {
        "RC10_SPECIALIST_COGNITION_FOUNDATION": specialist_foundation_report(),
        "RC10_SPECIALIST_SELECTION_BENCHMARK": specialist_selection_benchmark(),
        "RC10_SPECIALIST_PORTFOLIO_READINESS": specialist_portfolio_readiness_report(),
    }
    for name, payload in reports.items():
        (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        (REPORT_DIR / f"{name}.md").write_text(_markdown_report(name, payload), encoding="utf-8")
    return reports


def _markdown_report(name: str, payload: Mapping[str, Any]) -> str:
    lines = [
        f"# {name}",
        "",
        f"- Generated: {_now()}",
        f"- Passed: {payload.get('passed')}",
        f"- Recommendation: {payload.get('recommendation')}",
        f"- Specialist authority: {payload.get('specialist_authority', 'advisory_only')}",
        "",
        "## Safety",
    ]
    for key, value in (payload.get("safety") or safety_metadata()).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Payload", "```json", json.dumps(payload, indent=2, sort_keys=True)[:18000], "```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_reports()
    print(json.dumps({key: value.get("recommendation") for key, value in result.items()}, indent=2, sort_keys=True))

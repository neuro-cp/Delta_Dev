from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V18B_FLAGS: dict[str, bool] = {
    "promotion_readiness_scorecard_enabled": True,
    "promotion_performed": False,
    "memory_mutation_performed": False,
    "provider_default_changed": False,
    "scheduler_activated": False,
    "training_triggered": False,
    "hyb1_promoted": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class PromotionReadinessDecisionValue(str, Enum):
    NOT_READY = "not_ready"
    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    BLOCKED_BY_SAFETY = "blocked_by_safety"
    BLOCKED_BY_MISSING_EVIDENCE = "blocked_by_missing_evidence"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    DESIGN_ONLY = "design_only"


@dataclass(frozen=True)
class PromotionReadinessTarget:
    target_id: str
    name: str
    evidence_count: int
    safety_blocked: bool
    design_only: bool
    invariant_blocked: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PromotionReadinessMetric:
    metric_id: str
    name: str
    passed: bool
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PromotionReadinessBlocker:
    blocker_id: str
    kind: PromotionReadinessDecisionValue
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return {"blocker_id": self.blocker_id, "kind": self.kind.value, "rationale": self.rationale}


@dataclass(frozen=True)
class PromotionReadinessDecision:
    decision_id: str
    outcome: PromotionReadinessDecisionValue
    promoted: bool = False

    def as_dict(self) -> dict[str, object]:
        return {"decision_id": self.decision_id, "outcome": self.outcome.value, "promoted": self.promoted}


@dataclass(frozen=True)
class PromotionReadinessScorecard:
    scorecard_id: str
    target: PromotionReadinessTarget
    metrics: tuple[PromotionReadinessMetric, ...]
    blockers: tuple[PromotionReadinessBlocker, ...]
    decision: PromotionReadinessDecision

    def as_dict(self) -> dict[str, object]:
        return {
            "scorecard_id": self.scorecard_id,
            "target": self.target.as_dict(),
            "metrics": [metric.as_dict() for metric in self.metrics],
            "blockers": [blocker.as_dict() for blocker in self.blockers],
            "decision": self.decision.as_dict(),
        }


@dataclass(frozen=True)
class PromotionReadinessAuditRecord:
    audit_id: str
    target_count: int
    promotions_performed: bool
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PromotionReadinessReportEntry:
    report_entry_id: str
    ready_for_human_review_count: int
    blocked_count: int
    design_only_count: int

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_promotion_readiness_targets() -> tuple[PromotionReadinessTarget, ...]:
    return (
        PromotionReadinessTarget(_stable_id("v18b-target", "limited-recall"), "limited_general_recall", 3, False, False),
        PromotionReadinessTarget(_stable_id("v18b-target", "unknown-provider"), "controlled_provider_assisted_unknown_answering", 2, False, False),
        PromotionReadinessTarget(_stable_id("v18b-target", "specialist"), "specialist_evidence_acquisition", 1, False, False),
        PromotionReadinessTarget(_stable_id("v18b-target", "daily-evaluator"), "daily_evaluator_manual_run", 1, False, False),
        PromotionReadinessTarget(_stable_id("v18b-target", "review-ui"), "review_ui_export_flow", 3, False, False),
        PromotionReadinessTarget(_stable_id("v18b-target", "scheduler"), "scheduler_activation_gate", 1, True, True),
        PromotionReadinessTarget(_stable_id("v18b-target", "hyb1"), "HYB1_default_activation", 0, True, False, True),
    )


def run_promotion_readiness_scorecard() -> dict[str, object]:
    scorecards = tuple(_score_target(target) for target in build_promotion_readiness_targets())
    ready = sum(1 for card in scorecards if card.decision.outcome == PromotionReadinessDecisionValue.READY_FOR_HUMAN_REVIEW)
    design_only = sum(1 for card in scorecards if card.decision.outcome == PromotionReadinessDecisionValue.DESIGN_ONLY)
    blocked = len(scorecards) - ready - design_only
    data = {
        "phase": "Runtime V1.8B",
        "scorecards": [card.as_dict() for card in scorecards],
        "audit_record": PromotionReadinessAuditRecord(_stable_id("v18b-audit", len(scorecards)), len(scorecards), False, True).as_dict(),
        "report_entry": PromotionReadinessReportEntry(_stable_id("v18b-entry", ready, blocked, design_only), ready, blocked, design_only).as_dict(),
        "invariant_flags": dict(RUNTIME_V18B_FLAGS),
        "final_recommendation": "PROCEED_V17_V18_SAFETY_CLOSURE_REPORT",
    }
    return data


def validate_promotion_readiness_scorecard_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["audit_record"]["promotions_performed"] is False
        and all(card["decision"]["promoted"] is False for card in payload["scorecards"])
        and flags["promotion_readiness_scorecard_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "promotion_readiness_scorecard_enabled")
    )


def _score_target(target: PromotionReadinessTarget) -> PromotionReadinessScorecard:
    metrics = (
        PromotionReadinessMetric(_stable_id("v18b-metric", target.target_id, "evidence"), "evidence_present", target.evidence_count > 0, f"Evidence count: {target.evidence_count}"),
        PromotionReadinessMetric(_stable_id("v18b-metric", target.target_id, "safety"), "safety_not_blocked", not target.safety_blocked, "Safety gate must not be blocked."),
        PromotionReadinessMetric(_stable_id("v18b-metric", target.target_id, "invariant"), "invariant_not_blocked", not target.invariant_blocked, "Runtime invariants must remain satisfied."),
    )
    blockers: list[PromotionReadinessBlocker] = []
    if target.design_only:
        blockers.append(PromotionReadinessBlocker(_stable_id("v18b-blocker", target.target_id, "design"), PromotionReadinessDecisionValue.DESIGN_ONLY, "Target remains design-only."))
        outcome = PromotionReadinessDecisionValue.DESIGN_ONLY
    elif target.invariant_blocked:
        blockers.append(PromotionReadinessBlocker(_stable_id("v18b-blocker", target.target_id, "invariant"), PromotionReadinessDecisionValue.BLOCKED_BY_INVARIANT, "Target conflicts with frozen invariants."))
        outcome = PromotionReadinessDecisionValue.BLOCKED_BY_INVARIANT
    elif target.safety_blocked:
        blockers.append(PromotionReadinessBlocker(_stable_id("v18b-blocker", target.target_id, "safety"), PromotionReadinessDecisionValue.BLOCKED_BY_SAFETY, "Safety gate blocks activation."))
        outcome = PromotionReadinessDecisionValue.BLOCKED_BY_SAFETY
    elif target.evidence_count <= 0:
        blockers.append(PromotionReadinessBlocker(_stable_id("v18b-blocker", target.target_id, "evidence"), PromotionReadinessDecisionValue.BLOCKED_BY_MISSING_EVIDENCE, "No evidence available."))
        outcome = PromotionReadinessDecisionValue.BLOCKED_BY_MISSING_EVIDENCE
    else:
        outcome = PromotionReadinessDecisionValue.READY_FOR_HUMAN_REVIEW
    decision = PromotionReadinessDecision(_stable_id("v18b-decision", target.target_id, outcome.value), outcome, promoted=False)
    return PromotionReadinessScorecard(_stable_id("v18b-scorecard", target.target_id), target, metrics, tuple(blockers), decision)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

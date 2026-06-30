from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Sequence

from orchestration.agency.goal_system import GoalRecord
from orchestration.simulation import HypotheticalOutcome, SimulationReport


@dataclass(frozen=True)
class PlanStep:
    summary: str
    expected_benefit: float
    risk: float
    uncertainty: float
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanRecord:
    plan_id: str
    created_at: str
    goal_id: str
    strategy: str
    status: str
    steps: list[PlanStep]
    expected_benefit: float
    expected_risk: float
    uncertainty: float
    chosen_because: str
    simulation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PlanningEngine:
    """
    Converts goals and simulations into inspectable plans.

    Planning does not execute. It only describes possible strategies.
    """

    def build_plan(
        self,
        *,
        goal: GoalRecord,
        simulation: SimulationReport | None = None,
    ) -> PlanRecord:
        outcome = self._best_outcome(simulation.outcomes if simulation else [])
        expected_benefit = self._expected_benefit(goal, outcome)
        expected_risk = outcome.risk if outcome else min(1.0, goal.estimated_effort)
        uncertainty = round(1.0 - (outcome.confidence if outcome else goal.confidence), 4)

        steps = [
            PlanStep(
                summary=f"Focus attention on goal: {goal.description}",
                expected_benefit=round(expected_benefit * 0.25, 4),
                risk=round(expected_risk * 0.25, 4),
                uncertainty=uncertainty,
                evidence=goal.supporting_evidence,
            ),
            PlanStep(
                summary=(
                    outcome.option
                    if outcome
                    else "Gather more evidence before choosing an external action."
                ),
                expected_benefit=expected_benefit,
                risk=expected_risk,
                uncertainty=uncertainty,
                evidence=(
                    (outcome.supporting_prediction_ids + outcome.supporting_knowledge_ids)
                    if outcome
                    else []
                ),
            ),
        ]

        return PlanRecord(
            plan_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            goal_id=goal.goal_id,
            strategy=outcome.option if outcome else "investigate-before-acting",
            status="proposed",
            steps=steps,
            expected_benefit=expected_benefit,
            expected_risk=round(expected_risk, 4),
            uncertainty=uncertainty,
            chosen_because=(
                "Selected the simulated outcome with the best confidence-risk balance."
                if outcome
                else "No simulation evidence was available, so the plan favors investigation."
            ),
            simulation_id=simulation.simulation_id if simulation else None,
            metadata={"non_executing": True},
        )

    @staticmethod
    def _best_outcome(outcomes: Sequence[HypotheticalOutcome]) -> HypotheticalOutcome | None:
        if not outcomes:
            return None
        return max(outcomes, key=lambda item: item.confidence - item.risk)

    @staticmethod
    def _expected_benefit(
        goal: GoalRecord,
        outcome: HypotheticalOutcome | None,
    ) -> float:
        simulated = outcome.confidence * (1.0 - outcome.risk) if outcome else 0.0
        score = goal.expected_value * 0.55 + goal.action_pressure * 0.25 + simulated * 0.2
        return round(max(0.0, min(1.0, score)), 4)


class PlanStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add(self, record: PlanRecord) -> PlanRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def all(self) -> List[PlanRecord]:
        if not self.path.exists():
            return []
        records: List[PlanRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(
                    PlanRecord(
                        plan_id=payload["plan_id"],
                        created_at=payload["created_at"],
                        goal_id=payload["goal_id"],
                        strategy=payload["strategy"],
                        status=payload["status"],
                        steps=[PlanStep(**item) for item in payload.get("steps", [])],
                        expected_benefit=payload["expected_benefit"],
                        expected_risk=payload["expected_risk"],
                        uncertainty=payload["uncertainty"],
                        chosen_because=payload["chosen_because"],
                        simulation_id=payload.get("simulation_id"),
                        metadata=dict(payload.get("metadata", {})),
                    )
                )
        return records

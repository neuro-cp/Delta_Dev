from __future__ import annotations

from orchestration.agency import (
    AgencyRegion,
    DecisionEngine,
    GoalStore,
    PlanStore,
    PlanningEngine,
)
from orchestration.simulation import HypotheticalOutcome, SimulationReport


def test_goal_store_persists_active_goals(tmp_path):
    store = GoalStore(tmp_path / "goals.jsonl")

    record = store.create(
        description="Improve prediction accuracy",
        origin="test",
        priority=0.8,
        urgency=0.6,
        expected_value=0.9,
        estimated_effort=0.4,
        confidence=0.7,
    )

    assert store.active()[0].goal_id == record.goal_id
    assert store.active()[0].action_pressure > 0.0


def test_planning_and_decision_are_non_executing(tmp_path):
    goals = GoalStore(tmp_path / "goals.jsonl")
    plans = PlanStore(tmp_path / "plans.jsonl")
    goal = goals.create(description="Resolve open contradictions", priority=0.9)
    simulation = SimulationReport(
        simulation_id="sim-1",
        generated_at="2026-06-30T00:00:00+00:00",
        cycle_id=None,
        selected_basis="test",
        outcomes=[
            HypotheticalOutcome(
                option="investigate contradiction evidence",
                expected_outcome="Contradiction pressure should decrease.",
                confidence=0.75,
                risk=0.2,
            )
        ],
        metadata={"non_executing": True},
    )

    plan = plans.add(PlanningEngine().build_plan(goal=goal, simulation=simulation))
    decision = DecisionEngine().choose(goal=goal, plans=[plan])

    assert plan.metadata["non_executing"] is True
    assert decision.metadata["execution_authority"] is False
    assert decision.plan_id == plan.plan_id


def test_agency_can_propose_from_intrinsic_self_model_goal():
    proposal = AgencyRegion().propose(
        goals=[],
        self_model={
            "generated_at": "2026-06-30T00:00:00+00:00",
            "self_observations": [
                {
                    "kind": "prediction_evaluation_gap",
                    "summary": "Predictions exist but have no outcomes.",
                    "severity": "medium",
                }
            ],
        },
    )

    assert proposal.goal_id == "intrinsic:prediction_evaluation_gap"
    assert proposal.metadata["execution_authority"] is False
    assert proposal.decision is not None

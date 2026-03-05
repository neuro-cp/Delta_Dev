
from memory.proposal_evaluation.evaluation_engine import EvaluationEngine


def test_engine_returns_descriptive_records_only() -> None:
    engine = EvaluationEngine()

    records = engine.evaluate(
        proposal_ids=["p1", "p2"],
        evaluator_id="e",
        policy_id="p",
    )

    assert len(records) == 2
    assert all(r.accepted is False for r in records)

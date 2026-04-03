from orchestration.execution.evaluation_engine import EvaluationEngine
from orchestration.schemas.execution_result import ExecutionResult


def test_evaluation_engine_marks_successful_nonempty_result_as_passed():
    result = ExecutionResult(
        plan_id="p1",
        route_type="deterministic_solver",
        success=True,
        output=4.0,
        confidence=1.0,
    )
    evaluated = EvaluationEngine().evaluate(result)

    assert evaluated.evaluation is not None
    assert evaluated.evaluation.passed is True

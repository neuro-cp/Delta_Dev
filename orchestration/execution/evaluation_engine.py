from __future__ import annotations

from orchestration.schemas.execution_result import EvaluationReport, ExecutionResult


class EvaluationEngine:
    """
    Lightweight result evaluation.
    """

    def evaluate(self, result: ExecutionResult) -> ExecutionResult:
        if not result.success:
            evaluation = EvaluationReport(
                passed=False,
                completeness=0.0,
                consistency=0.0,
                notes={"reason": "execution_failed"},
            )
            return ExecutionResult(
                plan_id=result.plan_id,
                route_type=result.route_type,
                success=result.success,
                output=result.output,
                confidence=result.confidence,
                artifacts=dict(result.artifacts),
                evaluation=evaluation,
            )

        completeness = 1.0 if result.output not in (None, "", []) else 0.0
        consistency = 1.0

        if result.route_type == "llm" and isinstance(result.output, str):
            if "<your answer here>" in result.output:
                consistency = 0.0

        evaluation = EvaluationReport(
            passed=completeness > 0.0 and consistency > 0.0,
            completeness=completeness,
            consistency=consistency,
            notes={},
        )

        return ExecutionResult(
            plan_id=result.plan_id,
            route_type=result.route_type,
            success=result.success,
            output=result.output,
            confidence=result.confidence,
            artifacts=dict(result.artifacts),
            evaluation=evaluation,
        )

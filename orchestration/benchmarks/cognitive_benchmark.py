from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkAssessment:
    category: str
    metric: str
    baseline: Any
    candidate: Any
    delta: float | None
    improved: bool | None
    status: str
    rationale: str


class CognitiveBenchmarkComparator:
    """
    Compare Delta runs without confusing engineering health with cognition.
    """

    def compare(
        self,
        *,
        baseline_summary: dict[str, Any],
        candidate_summary: dict[str, Any],
        baseline_task_summary: dict[str, Any] | None = None,
        candidate_task_summary: dict[str, Any] | None = None,
        provider_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assessments = [
            self._engineering_completion(baseline_summary, candidate_summary),
            self._higher_is_better(
                category="cognitive_correctness",
                metric="prediction_accuracy",
                baseline=self._path(baseline_summary, "prediction_quality", "accuracy"),
                candidate=self._path(candidate_summary, "prediction_quality", "accuracy"),
                rationale="Prediction accuracy should increase over sustained experience.",
            ),
            self._higher_is_better(
                category="cognitive_correctness",
                metric="prediction_coverage",
                baseline=self._path(baseline_summary, "prediction_quality", "coverage"),
                candidate=self._path(candidate_summary, "prediction_quality", "coverage"),
                rationale="More predictions should be evaluated against evidence.",
            ),
            self._lower_is_better(
                category="cognitive_correctness",
                metric="contradiction_pressure",
                baseline=self._path(baseline_summary, "self_model", "cognitive_health", "contradiction_pressure"),
                candidate=self._path(candidate_summary, "self_model", "cognitive_health", "contradiction_pressure"),
                rationale="Contradiction pressure should decrease or remain controlled.",
            ),
            self._higher_is_better(
                category="task_performance",
                metric="task_pass_rate",
                baseline=(baseline_task_summary or {}).get("pass_rate"),
                candidate=(candidate_task_summary or {}).get("pass_rate"),
                rationale="Task pass rate should improve on held-out evaluation cases.",
            ),
            self._provider_efficiency(provider_summary or {}),
        ]
        return {
            "engineering_correctness": [
                item for item in assessments if item.category == "engineering_correctness"
            ],
            "cognitive_correctness": [
                item for item in assessments if item.category == "cognitive_correctness"
            ],
            "task_performance": [
                item for item in assessments if item.category == "task_performance"
            ],
            "summary": self._summary(assessments),
        }

    def _engineering_completion(
        self,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
    ) -> BenchmarkAssessment:
        baseline_complete = baseline.get("ticks_completed") == baseline.get("ticks_requested")
        candidate_complete = candidate.get("ticks_completed") == candidate.get("ticks_requested")
        return BenchmarkAssessment(
            category="engineering_correctness",
            metric="runtime_completion",
            baseline=baseline_complete,
            candidate=candidate_complete,
            delta=None,
            improved=(candidate_complete and not baseline_complete)
            if baseline_complete != candidate_complete
            else candidate_complete,
            status="measured",
            rationale="Runtime experiments must complete requested ticks before cognitive gains are trusted.",
        )

    def _provider_efficiency(self, provider_summary: dict[str, Any]) -> BenchmarkAssessment:
        baseline = provider_summary.get("baseline_api_calls")
        candidate = provider_summary.get("candidate_api_calls")
        if baseline is None or candidate is None:
            return BenchmarkAssessment(
                category="task_performance",
                metric="api_call_efficiency",
                baseline=baseline,
                candidate=candidate,
                delta=None,
                improved=None,
                status="insufficient_data",
                rationale="Provider efficiency requires baseline and candidate API-call counts.",
            )
        return self._lower_is_better(
            category="task_performance",
            metric="api_call_efficiency",
            baseline=baseline,
            candidate=candidate,
            rationale="Equivalent task quality should require fewer cloud API calls as local providers improve.",
        )

    def _higher_is_better(
        self,
        *,
        category: str,
        metric: str,
        baseline: Any,
        candidate: Any,
        rationale: str,
    ) -> BenchmarkAssessment:
        if baseline is None or candidate is None:
            return self._insufficient(category, metric, baseline, candidate, rationale)
        delta = round(float(candidate) - float(baseline), 4)
        return BenchmarkAssessment(
            category=category,
            metric=metric,
            baseline=baseline,
            candidate=candidate,
            delta=delta,
            improved=delta > 0,
            status="measured",
            rationale=rationale,
        )

    def _lower_is_better(
        self,
        *,
        category: str,
        metric: str,
        baseline: Any,
        candidate: Any,
        rationale: str,
    ) -> BenchmarkAssessment:
        if baseline is None or candidate is None:
            return self._insufficient(category, metric, baseline, candidate, rationale)
        delta = round(float(candidate) - float(baseline), 4)
        return BenchmarkAssessment(
            category=category,
            metric=metric,
            baseline=baseline,
            candidate=candidate,
            delta=delta,
            improved=delta < 0,
            status="measured",
            rationale=rationale,
        )

    def _insufficient(
        self,
        category: str,
        metric: str,
        baseline: Any,
        candidate: Any,
        rationale: str,
    ) -> BenchmarkAssessment:
        return BenchmarkAssessment(
            category=category,
            metric=metric,
            baseline=baseline,
            candidate=candidate,
            delta=None,
            improved=None,
            status="insufficient_data",
            rationale=rationale,
        )

    def _summary(self, assessments: list[BenchmarkAssessment]) -> dict[str, Any]:
        measured = [item for item in assessments if item.status == "measured"]
        improved = [item for item in measured if item.improved is True]
        regressed = [item for item in measured if item.improved is False]
        insufficient = [
            item.metric for item in assessments if item.status == "insufficient_data"
        ]
        return {
            "measured": len(measured),
            "improved": len(improved),
            "regressed_or_flat": len(regressed),
            "insufficient_data": insufficient,
            "interpretation": self._interpretation(measured, regressed, insufficient),
        }

    def _interpretation(
        self,
        measured: list[BenchmarkAssessment],
        regressed: list[BenchmarkAssessment],
        insufficient: list[str],
    ) -> str:
        if not measured:
            return "No benchmark dimensions were measurable."
        if regressed:
            return "Benchmark found non-improving measured dimensions; inspect before scaling runtime."
        if insufficient:
            return "Measured dimensions improved, but some important capability questions still lack data."
        return "Measured benchmark dimensions improved."

    @staticmethod
    def _path(payload: dict[str, Any], *keys: str) -> Any:
        value: Any = payload
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from orchestration.novelty import NoveltyAnalyzer, NoveltyReport


@dataclass(frozen=True)
class CalibrationObjective:
    objective_id: str
    capability: str
    task_type: str
    prompt: str
    required_capabilities: tuple[str, ...]
    expected_signals: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredCalibrationObjective:
    objective: CalibrationObjective
    novelty_report: NoveltyReport
    diversity_score: float
    calibration_score: float


class CalibrationCurriculumGenerator:
    """
    Generate high-utility calibration experiences.

    This is an experiment-design tool, not a cognitive region. It rejects low
    value or repetitive prompts before they enter provider scheduling.
    """

    def __init__(self, *, novelty_analyzer: NoveltyAnalyzer | None = None) -> None:
        self.novelty_analyzer = novelty_analyzer or NoveltyAnalyzer()

    def generate(
        self,
        *,
        count: int,
        previous_prompts: Iterable[str] = (),
        min_utility: float = 0.45,
    ) -> list[ScoredCalibrationObjective]:
        previous = [str(prompt) for prompt in previous_prompts if str(prompt).strip()]
        selected: list[ScoredCalibrationObjective] = []
        for objective in self._candidate_objectives():
            diversity = self._diversity_score(
                objective.prompt,
                [*previous, *[item.objective.prompt for item in selected]],
            )
            report = self.novelty_analyzer.analyze(
                text=objective.prompt,
                required_capabilities=objective.required_capabilities,
                known_capabilities=("reasoning",),
            )
            score = self._calibration_score(report, diversity)
            if report.experience_utility_score < min_utility and score < min_utility:
                continue
            selected.append(
                ScoredCalibrationObjective(
                    objective=objective,
                    novelty_report=report,
                    diversity_score=diversity,
                    calibration_score=score,
                )
            )
        return sorted(
            selected,
            key=lambda item: (
                -item.calibration_score,
                item.objective.capability,
                item.objective.objective_id,
            ),
        )[: max(0, int(count))]

    def _calibration_score(self, report: NoveltyReport, diversity_score: float) -> float:
        score = (
            report.experience_utility_score * 0.45
            + report.information_gain_score * 0.20
            + report.prediction_opportunity_score * 0.12
            + report.belief_challenge_score * 0.10
            + report.surprise_score * 0.08
            + diversity_score * 0.05
        )
        return round(max(0.0, min(1.0, score)), 4)

    def _candidate_objectives(self) -> tuple[CalibrationObjective, ...]:
        return (
            CalibrationObjective(
                objective_id="prediction-error-snow-route",
                capability="prediction",
                task_type="prediction",
                prompt=(
                    "Predict which part of a city snow removal route will fail after "
                    "an unexpected bridge closure, then name the evidence that would "
                    "confirm or falsify the prediction."
                ),
                required_capabilities=("prediction", "planning", "reasoning"),
                expected_signals=("prediction_pressure", "surprise", "falsification"),
            ),
            CalibrationObjective(
                objective_id="prediction-error-inventory",
                capability="prediction",
                task_type="prediction",
                prompt=(
                    "A warehouse forecast says demand will rise, but the first two "
                    "orders fail to materialize. Predict the next operational risk "
                    "and explain what evidence would revise the belief."
                ),
                required_capabilities=("prediction", "uncertainty", "planning"),
                expected_signals=("prediction_pressure", "belief_revision"),
            ),
            CalibrationObjective(
                objective_id="contradictory-witnesses",
                capability="contradiction",
                task_type="reasoning",
                prompt=(
                    "Two trusted witnesses disagree about whether Job #42 was "
                    "completed before inspection. Preserve both claims, identify the "
                    "contradiction, and propose resolution evidence without deleting "
                    "either claim."
                ),
                required_capabilities=("reasoning", "reflection", "contradiction"),
                expected_signals=("invalidation_pressure", "contradiction_resolution"),
            ),
            CalibrationObjective(
                objective_id="contradictory-policy",
                capability="contradiction",
                task_type="reasoning",
                prompt=(
                    "A policy says emergency purchases never require approval, while "
                    "a later audit says the same purchase failed because approval was "
                    "missing. Explain the conflict and what provenance would resolve it."
                ),
                required_capabilities=("reasoning", "governance", "contradiction"),
                expected_signals=("invalidation_pressure", "provenance"),
            ),
            CalibrationObjective(
                objective_id="belief-revision-gps",
                capability="belief_revision",
                task_type="reflection",
                prompt=(
                    "Delta believes GPS estimates are reliable downtown, but repeated "
                    "observations show GPS fails in tunnels and urban canyons. Revise "
                    "the belief using evidence, uncertainty, and confidence rationale."
                ),
                required_capabilities=("reflection", "reasoning", "belief_revision"),
                expected_signals=("belief_challenge", "confidence_revision"),
            ),
            CalibrationObjective(
                objective_id="belief-revision-provider-disagreement",
                capability="belief_revision",
                task_type="reflection",
                prompt=(
                    "Two qualified providers disagree while using identical evidence. "
                    "Explain why that is surprising, how Delta should preserve both "
                    "outputs, and what evidence would change the current belief."
                ),
                required_capabilities=("reflection", "reasoning", "provider_evaluation"),
                expected_signals=("surprise", "belief_challenge"),
            ),
            CalibrationObjective(
                objective_id="planning-failure-construction",
                capability="planning",
                task_type="planning",
                prompt=(
                    "Create a construction project plan, then revise it after step "
                    "three fails because a permit assumption was false. Preserve the "
                    "original plan and explain the revision."
                ),
                required_capabilities=("planning", "reasoning", "reflection"),
                expected_signals=("planning_failure", "revision"),
            ),
            CalibrationObjective(
                objective_id="planning-failure-hospital",
                capability="planning",
                task_type="planning",
                prompt=(
                    "Plan hospital staffing under uncertainty, then adapt when an "
                    "unexpected flu surge invalidates the first staffing assumption."
                ),
                required_capabilities=("planning", "simulation", "uncertainty"),
                expected_signals=("surprise", "prediction_pressure"),
            ),
            CalibrationObjective(
                objective_id="transfer-code-to-governance",
                capability="transfer",
                task_type="reasoning",
                prompt=(
                    "Transfer the idea of regression testing from software engineering "
                    "to knowledge governance. Explain what would count as a failing "
                    "test for a belief revision."
                ),
                required_capabilities=("coding", "governance", "reasoning"),
                expected_signals=("transfer_learning", "generalization"),
            ),
            CalibrationObjective(
                objective_id="transfer-medical-to-maintenance",
                capability="transfer",
                task_type="reasoning",
                prompt=(
                    "Transfer triage reasoning from emergency medicine to maintenance "
                    "scheduling. Predict which job should be delayed and what evidence "
                    "would make that decision unsafe."
                ),
                required_capabilities=("reasoning", "planning", "prediction"),
                expected_signals=("transfer_learning", "prediction_pressure"),
            ),
            CalibrationObjective(
                objective_id="cross-domain-budget-weather",
                capability="cross_domain",
                task_type="planning",
                prompt=(
                    "A city must reduce its snow budget by 20 percent while forecasts "
                    "predict a colder winter. Create a plan, identify contradictions, "
                    "and state what outcome would falsify the plan."
                ),
                required_capabilities=("planning", "prediction", "reasoning"),
                expected_signals=("cross_domain_reasoning", "falsification"),
            ),
            CalibrationObjective(
                objective_id="cross-domain-research-policy",
                capability="cross_domain",
                task_type="research",
                prompt=(
                    "A government report and a scientific study make conflicting "
                    "claims about flood risk. Compare the evidence, predict which "
                    "claim is more likely to fail, and propose a validation test."
                ),
                required_capabilities=("research", "prediction", "reasoning"),
                expected_signals=("contradiction_resolution", "prediction_pressure"),
            ),
            CalibrationObjective(
                objective_id="json-evidence-revision",
                capability="json",
                task_type="json",
                prompt=(
                    "Return ONLY JSON describing a belief revision with fields claim, "
                    "supporting_evidence, contradicting_evidence, confidence_rationale, "
                    "and next_prediction."
                ),
                required_capabilities=("json", "belief_revision", "prediction"),
                expected_signals=("format_adherence", "belief_revision"),
            ),
            CalibrationObjective(
                objective_id="coding-boundary-preservation",
                capability="coding",
                task_type="coding",
                prompt=(
                    "Write a Python test that catches an adapter bug where a prompt "
                    "field is preserved but the semantic question field is dropped."
                ),
                required_capabilities=("coding", "reasoning", "governance"),
                expected_signals=("boundary_preservation", "regression_test"),
            ),
        )

    def _diversity_score(self, prompt: str, previous_prompts: Sequence[str]) -> float:
        tokens = self._tokens(prompt)
        if not tokens or not previous_prompts:
            return 1.0
        similarity = max(
            self._jaccard(tokens, self._tokens(previous))
            for previous in previous_prompts
        )
        return round(max(0.0, min(1.0, 1.0 - similarity)), 4)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

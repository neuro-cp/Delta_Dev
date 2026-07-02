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
        profiles: Iterable[str] = (),
    ) -> list[ScoredCalibrationObjective]:
        previous = [str(prompt) for prompt in previous_prompts if str(prompt).strip()]
        profile_filter = {
            str(profile).strip().lower()
            for profile in profiles
            if str(profile).strip()
        }
        selected: list[ScoredCalibrationObjective] = []
        for objective in self._candidate_objectives():
            if profile_filter and not profile_filter.intersection(
                self._objective_profiles(objective)
            ):
                continue
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

    def _objective_profiles(self, objective: CalibrationObjective) -> set[str]:
        profiles = {objective.capability.lower(), objective.task_type.lower()}
        metadata_profiles = objective.metadata.get("profiles", ())
        if isinstance(metadata_profiles, str):
            metadata_profiles = (metadata_profiles,)
        profiles.update(
            str(profile).strip().lower()
            for profile in metadata_profiles
            if str(profile).strip()
        )
        return profiles

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
        from orchestration.curriculum.broad_corpus import generate_broad_corpus

        seed_objectives = (
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
                metadata={"profiles": ("prediction", "planning")},
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
                metadata={"profiles": ("prediction", "planning")},
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
                metadata={"profiles": ("contradiction",)},
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
                metadata={"profiles": ("contradiction",)},
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
                metadata={"profiles": ("contradiction", "causal_reasoning")},
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
                metadata={"profiles": ("contradiction",)},
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
                metadata={"profiles": ("planning",)},
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
                metadata={"profiles": ("planning",)},
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
                metadata={"profiles": ("transfer", "tool_use")},
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
                metadata={"profiles": ("transfer", "planning")},
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
                metadata={"profiles": ("planning", "causal_reasoning")},
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
                metadata={"profiles": ("scientific_reasoning", "contradiction")},
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
                metadata={"profiles": ("tool_use", "contradiction")},
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
                metadata={"profiles": ("tool_use",)},
            ),
            CalibrationObjective(
                objective_id="causal-chain-supply-delay",
                capability="causal_reasoning",
                task_type="reasoning",
                prompt=(
                    "A supplier delay causes crews to resequence work, which causes "
                    "inspection windows to expire. Explain the causal chain, predict "
                    "the next failure point, and name evidence that would break the chain."
                ),
                required_capabilities=("causal_reasoning", "prediction", "planning"),
                expected_signals=("causal_chain", "prediction_pressure"),
                metadata={"profiles": ("causal_reasoning", "planning")},
            ),
            CalibrationObjective(
                objective_id="causal-counterfactual-maintenance",
                capability="causal_reasoning",
                task_type="reasoning",
                prompt=(
                    "A maintenance team believes a pump failed because of age, but "
                    "sensor logs show vibration spiked only after a valve change. "
                    "Compare the causal explanations and state the counterfactual test."
                ),
                required_capabilities=("causal_reasoning", "evidence", "prediction"),
                expected_signals=("belief_challenge", "falsification"),
                metadata={"profiles": ("causal_reasoning", "contradiction")},
            ),
            CalibrationObjective(
                objective_id="scientific-hypothesis-water-quality",
                capability="scientific_reasoning",
                task_type="research",
                prompt=(
                    "A city observes intermittent water quality failures after heavy "
                    "rain. Generate two hypotheses, predict distinct observations for "
                    "each, and describe the evidence that would revise confidence."
                ),
                required_capabilities=("scientific_reasoning", "prediction", "evidence"),
                expected_signals=("hypothesis_generation", "prediction_pressure"),
                metadata={"profiles": ("scientific_reasoning",)},
            ),
            CalibrationObjective(
                objective_id="scientific-hypothesis-battery-degradation",
                capability="scientific_reasoning",
                task_type="research",
                prompt=(
                    "Battery packs from one production batch degrade early while "
                    "others do not. Form a hypothesis, identify a control comparison, "
                    "and state what result would falsify the hypothesis."
                ),
                required_capabilities=("scientific_reasoning", "prediction", "reasoning"),
                expected_signals=("hypothesis_generation", "falsification"),
                metadata={"profiles": ("scientific_reasoning",)},
            ),
            CalibrationObjective(
                objective_id="tool-use-log-triage",
                capability="tool_use",
                task_type="planning",
                prompt=(
                    "Given an incident report with missing timestamps, plan which logs "
                    "to inspect first, what evidence each log can provide, and how the "
                    "plan changes if the first log contradicts the report."
                ),
                required_capabilities=("tool_use", "planning", "contradiction"),
                expected_signals=("tool_selection", "contradiction_resolution"),
                metadata={"profiles": ("tool_use", "planning")},
            ),
            CalibrationObjective(
                objective_id="tool-use-invoice-audit",
                capability="tool_use",
                task_type="planning",
                prompt=(
                    "Plan an invoice audit using invoices, purchase orders, and email "
                    "approvals. Predict the most likely mismatch and name the evidence "
                    "that would resolve it."
                ),
                required_capabilities=("tool_use", "planning", "prediction"),
                expected_signals=("tool_selection", "prediction_pressure"),
                metadata={"profiles": ("tool_use",)},
            ),
            CalibrationObjective(
                objective_id="long-dependency-contract-change",
                capability="long_dependency",
                task_type="reasoning",
                prompt=(
                    "A contract change modifies delivery dates, which affects staffing, "
                    "inspection timing, penalties, and customer communication. Trace the "
                    "dependencies and predict which downstream belief should be revised first."
                ),
                required_capabilities=("long_dependency", "planning", "prediction"),
                expected_signals=("dependency_reasoning", "belief_revision"),
                metadata={"profiles": ("long_dependency", "planning")},
            ),
            CalibrationObjective(
                objective_id="long-dependency-policy-exception",
                capability="long_dependency",
                task_type="reasoning",
                prompt=(
                    "A temporary policy exception conflicts with an older operating "
                    "procedure, affects two teams, and expires next week. Preserve the "
                    "dependency chain and identify what evidence determines which rule applies."
                ),
                required_capabilities=("long_dependency", "contradiction", "governance"),
                expected_signals=("dependency_reasoning", "provenance"),
                metadata={"profiles": ("long_dependency", "contradiction")},
            ),
        )
        return (*seed_objectives, *generate_broad_corpus(minimum_per_profile=100))

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

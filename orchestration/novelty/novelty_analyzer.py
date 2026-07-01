from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from knowledge import PredictionRecord, SemanticKnowledgeRecord
from memory.persistent import MemoryRecord


@dataclass(frozen=True)
class NoveltyReport:
    text: str
    novelty_score: float
    information_gain_score: float
    prediction_opportunity_score: float
    belief_challenge_score: float
    surprise_score: float
    capability_expansion_score: float
    generalizability_score: float
    memory_value_score: float
    experience_utility_score: float
    similarity_to_memory: float
    similarity_to_knowledge: float
    challenges_existing_belief: bool
    requires_new_capability: bool
    worth_remembering: bool
    prediction_pressure: bool
    invalidation_pressure: bool
    required_capabilities: tuple[str, ...] = ()
    rationale: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class NoveltyAnalyzer:
    """
    Measure whether an experience is likely to change Delta.

    This is a measurement utility, not a cognitive region. It does not mutate
    memory, knowledge, or governance state.
    """

    _PREDICTION_TERMS = {"predict", "prediction", "will", "expect", "forecast"}
    _SURPRISE_TERMS = {
        "unexpected",
        "surprise",
        "surprising",
        "anomaly",
        "anomalous",
        "disagree",
        "disagrees",
        "disagreement",
    }
    _CONTRADICTION_TERMS = {
        "not",
        "never",
        "contradict",
        "conflict",
        "invalid",
        "false",
        "fail",
        "fails",
        "failed",
        "failure",
    }

    def analyze(
        self,
        *,
        text: str,
        memories: Sequence[MemoryRecord] = (),
        knowledge: Sequence[SemanticKnowledgeRecord] = (),
        predictions: Sequence[PredictionRecord] = (),
        required_capabilities: Iterable[str] = (),
        known_capabilities: Iterable[str] = (),
    ) -> NoveltyReport:
        normalized = str(text).strip()
        tokens = self._tokens(normalized)
        memory_similarity = self._max_similarity(
            tokens,
            [record.text for record in memories],
        )
        knowledge_similarity = self._max_similarity(
            tokens,
            [record.concept + " " + record.definition for record in knowledge],
        )
        capabilities = tuple(
            dict.fromkeys(str(item).strip().lower() for item in required_capabilities if str(item).strip())
        )
        known = {
            str(item).strip().lower()
            for item in known_capabilities
            if str(item).strip()
        }
        requires_new_capability = any(item not in known for item in capabilities)
        challenges = self._challenges_existing_belief(tokens, knowledge)
        prediction_pressure = bool(tokens & self._PREDICTION_TERMS)
        invalidation_pressure = bool(tokens & self._CONTRADICTION_TERMS) or challenges
        surprise = self._surprise(
            tokens=tokens,
            predictions=predictions,
            invalidation_pressure=invalidation_pressure,
        )

        familiarity = max(memory_similarity, knowledge_similarity)
        score = 1.0 - familiarity
        if requires_new_capability:
            score += 0.15
        if challenges:
            score += 0.2
        if prediction_pressure:
            score += 0.1
        if invalidation_pressure:
            score += 0.1
        novelty_score = round(max(0.0, min(1.0, score)), 4)
        prediction_opportunity = self._prediction_opportunity(tokens, prediction_pressure)
        belief_challenge = 1.0 if challenges else (0.45 if invalidation_pressure else 0.0)
        capability_expansion = (
            self._ratio(
                len([item for item in capabilities if item not in known]),
                len(capabilities),
            )
            if capabilities
            else 0.0
        )
        generalizability = self._generalizability(tokens, capabilities)
        information_gain = self._information_gain(
            novelty=novelty_score,
            belief_challenge=belief_challenge,
            surprise=surprise,
            capability_expansion=capability_expansion,
            prediction_opportunity=prediction_opportunity,
            generalizability=generalizability,
        )
        memory_value = self._memory_value(
            novelty=novelty_score,
            information_gain=information_gain,
            belief_challenge=belief_challenge,
            prediction_opportunity=prediction_opportunity,
        )
        experience_utility = self._experience_utility(
            novelty=novelty_score,
            information_gain=information_gain,
            prediction_opportunity=prediction_opportunity,
            belief_challenge=belief_challenge,
            surprise=surprise,
            capability_expansion=capability_expansion,
            generalizability=generalizability,
            memory_value=memory_value,
        )
        worth_remembering = (
            memory_value >= 0.45
            or challenges
            or requires_new_capability
            or prediction_pressure
            or surprise >= 0.35
        )

        rationale = [
            f"memory_similarity={round(memory_similarity, 4)}",
            f"knowledge_similarity={round(knowledge_similarity, 4)}",
            f"requires_new_capability={requires_new_capability}",
            f"challenges_existing_belief={challenges}",
            f"prediction_pressure={prediction_pressure}",
            f"invalidation_pressure={invalidation_pressure}",
            f"surprise={surprise}",
            f"information_gain={information_gain}",
            f"experience_utility={experience_utility}",
        ]

        return NoveltyReport(
            text=normalized,
            novelty_score=novelty_score,
            information_gain_score=information_gain,
            prediction_opportunity_score=prediction_opportunity,
            belief_challenge_score=belief_challenge,
            surprise_score=surprise,
            capability_expansion_score=round(capability_expansion, 4),
            generalizability_score=generalizability,
            memory_value_score=memory_value,
            experience_utility_score=experience_utility,
            similarity_to_memory=round(memory_similarity, 4),
            similarity_to_knowledge=round(knowledge_similarity, 4),
            challenges_existing_belief=challenges,
            requires_new_capability=requires_new_capability,
            worth_remembering=worth_remembering,
            prediction_pressure=prediction_pressure,
            invalidation_pressure=invalidation_pressure,
            required_capabilities=capabilities,
            rationale=rationale,
            metadata={"method": "novelty_measurement_v1", "read_only": True},
        )

    def summarize(self, reports: Sequence[NoveltyReport]) -> dict[str, Any]:
        if not reports:
            return {
                "count": 0,
                "average_novelty": None,
                "worth_remembering_rate": None,
            }
        return {
            "count": len(reports),
            "average_novelty": round(
                sum(report.novelty_score for report in reports) / len(reports),
                4,
            ),
            "average_information_gain": round(
                sum(report.information_gain_score for report in reports) / len(reports),
                4,
            ),
            "average_surprise": round(
                sum(report.surprise_score for report in reports) / len(reports),
                4,
            ),
            "average_experience_utility": round(
                sum(report.experience_utility_score for report in reports) / len(reports),
                4,
            ),
            "worth_remembering_rate": round(
                len([report for report in reports if report.worth_remembering])
                / len(reports),
                4,
            ),
            "prediction_pressure_rate": round(
                len([report for report in reports if report.prediction_pressure])
                / len(reports),
                4,
            ),
            "invalidation_pressure_rate": round(
                len([report for report in reports if report.invalidation_pressure])
                / len(reports),
                4,
            ),
            "new_capability_rate": round(
                len([report for report in reports if report.requires_new_capability])
                / len(reports),
                4,
            ),
        }

    def _prediction_opportunity(
        self,
        tokens: set[str],
        prediction_pressure: bool,
    ) -> float:
        if prediction_pressure:
            return 1.0
        temporal_terms = {"tomorrow", "future", "later", "next", "after", "before"}
        causal_terms = {"because", "cause", "effect", "if", "then", "therefore"}
        score = 0.0
        if tokens & temporal_terms:
            score += 0.35
        if tokens & causal_terms:
            score += 0.35
        return round(min(1.0, score), 4)

    def _generalizability(
        self,
        tokens: set[str],
        capabilities: tuple[str, ...],
    ) -> float:
        abstract_terms = {
            "strategy",
            "pattern",
            "policy",
            "method",
            "procedure",
            "principle",
            "under",
            "uncertainty",
            "consistently",
        }
        score = 0.15
        score += min(0.35, len(capabilities) * 0.08)
        if tokens & abstract_terms:
            score += 0.35
        if len(tokens) >= 10:
            score += 0.15
        return round(min(1.0, score), 4)

    def _information_gain(
        self,
        *,
        novelty: float,
        belief_challenge: float,
        surprise: float,
        capability_expansion: float,
        prediction_opportunity: float,
        generalizability: float,
    ) -> float:
        score = (
            novelty * 0.15
            + belief_challenge * 0.25
            + surprise * 0.20
            + capability_expansion * 0.15
            + prediction_opportunity * 0.15
            + generalizability * 0.10
        )
        return round(max(0.0, min(1.0, score)), 4)

    def _memory_value(
        self,
        *,
        novelty: float,
        information_gain: float,
        belief_challenge: float,
        prediction_opportunity: float,
    ) -> float:
        return round(
            max(
                0.0,
                min(
                    1.0,
                    novelty * 0.25
                    + information_gain * 0.45
                    + belief_challenge * 0.20
                    + prediction_opportunity * 0.10,
                ),
            ),
            4,
        )

    def _experience_utility(
        self,
        *,
        novelty: float,
        information_gain: float,
        prediction_opportunity: float,
        belief_challenge: float,
        surprise: float,
        capability_expansion: float,
        generalizability: float,
        memory_value: float,
    ) -> float:
        score = (
            novelty * 0.12
            + information_gain * 0.24
            + prediction_opportunity * 0.13
            + belief_challenge * 0.15
            + surprise * 0.16
            + capability_expansion * 0.12
            + generalizability * 0.07
            + memory_value * 0.08
        )
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return max(0.0, min(1.0, numerator / denominator))

    def _surprise(
        self,
        *,
        tokens: set[str],
        predictions: Sequence[PredictionRecord],
        invalidation_pressure: bool,
    ) -> float:
        score = 0.0
        if tokens & self._SURPRISE_TERMS:
            score += 0.35
        if invalidation_pressure:
            score += 0.25
        for prediction in predictions:
            expectation_tokens = self._tokens(prediction.expectation)
            if not expectation_tokens:
                continue
            similarity = self._jaccard(tokens, expectation_tokens)
            if similarity >= 0.2 and invalidation_pressure:
                score += min(0.45, max(0.0, float(prediction.confidence)) * 0.45)
                if prediction.status == "failed":
                    score += 0.25
                break
        return round(max(0.0, min(1.0, score)), 4)

    def _challenges_existing_belief(
        self,
        tokens: set[str],
        knowledge: Sequence[SemanticKnowledgeRecord],
    ) -> bool:
        if not tokens & self._CONTRADICTION_TERMS:
            return False
        for record in knowledge:
            record_tokens = self._tokens(record.concept + " " + record.definition)
            if record_tokens and self._jaccard(tokens, record_tokens) >= 0.2:
                return True
        return False

    def _max_similarity(self, tokens: set[str], candidates: Sequence[str]) -> float:
        if not tokens:
            return 0.0
        similarities = [
            self._jaccard(tokens, self._tokens(candidate))
            for candidate in candidates
        ]
        return max(similarities or [0.0])

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from orchestration.evaluation import CognitiveEvaluationCase, CognitiveEvaluationResult


@dataclass(frozen=True)
class CurriculumPerformance:
    domain: str
    attempts: int = 0
    pass_rate: float | None = None
    average_confidence: float | None = None
    average_latency_seconds: float | None = None
    contradiction_pressure: float | None = None


@dataclass(frozen=True)
class CurriculumCase:
    case_id: str
    domain: str
    difficulty: int
    prompt: str
    required_capabilities: tuple[str, ...]
    expected_route: str | None = None
    expected_success: bool | None = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_evaluation_case(self) -> CognitiveEvaluationCase:
        return CognitiveEvaluationCase(
            case_id=self.case_id,
            category=self.domain,
            prompt=self.prompt,
            expected_route=self.expected_route,
            expected_success=self.expected_success,
            metadata={
                **self.metadata,
                "difficulty": self.difficulty,
                "required_capabilities": list(self.required_capabilities),
                "experience_type": "curriculum_task",
            },
        )


class CurriculumEngine:
    """
    Generate directed cognitive experiences.

    Curriculum tasks are experiences, not knowledge. They may feed evaluation
    and governance pipelines, but they must not directly promote semantic
    knowledge.
    """

    DOMAINS: tuple[str, ...] = (
        "arithmetic",
        "logic",
        "causal_reasoning",
        "abstraction",
        "planning",
        "scheduling",
        "contradiction",
        "prediction",
        "uncertainty",
        "language",
        "software_engineering",
        "scientific_reasoning",
        "government_workflows",
        "research_methodology",
    )

    _DOMAIN_CAPABILITIES: dict[str, tuple[str, ...]] = {
        "arithmetic": ("mathematics", "reasoning"),
        "logic": ("reasoning",),
        "causal_reasoning": ("reasoning", "simulation"),
        "abstraction": ("reasoning", "reflection"),
        "planning": ("planning", "reasoning"),
        "scheduling": ("planning", "mathematics"),
        "contradiction": ("reasoning", "reflection"),
        "prediction": ("prediction", "simulation"),
        "uncertainty": ("reasoning", "reflection"),
        "language": ("translation", "reasoning"),
        "software_engineering": ("coding", "planning"),
        "scientific_reasoning": ("reasoning", "research"),
        "government_workflows": ("planning", "retrieval"),
        "research_methodology": ("research", "planning"),
    }

    def __init__(self, *, min_difficulty: int = 1, max_difficulty: int = 5) -> None:
        self.min_difficulty = max(1, int(min_difficulty))
        self.max_difficulty = max(self.min_difficulty, int(max_difficulty))

    def generate_sequence(
        self,
        *,
        count: int,
        performance: Iterable[CurriculumPerformance] | None = None,
        domains: Iterable[str] | None = None,
    ) -> list[CurriculumCase]:
        selected_domains = tuple(domains or self.DOMAINS)
        if not selected_domains or count <= 0:
            return []

        performance_by_domain = {
            item.domain: item for item in (performance or ())
        }
        cases: list[CurriculumCase] = []
        ordered_domains = self._prioritize_domains(selected_domains, performance_by_domain)
        for index in range(count):
            domain = ordered_domains[index % len(ordered_domains)]
            perf = performance_by_domain.get(domain)
            difficulty = self._difficulty_for(perf)
            cases.append(
                CurriculumCase(
                    case_id=f"curriculum-{domain}-{difficulty}-{index + 1}",
                    domain=domain,
                    difficulty=difficulty,
                    prompt=self._prompt(domain, difficulty),
                    required_capabilities=self._DOMAIN_CAPABILITIES.get(
                        domain,
                        ("reasoning",),
                    ),
                    metadata={
                        "source": "curriculum_engine",
                        "direct_knowledge_promotion": False,
                    },
                )
            )
        return cases

    def performance_from_results(
        self,
        results: Iterable[CognitiveEvaluationResult],
    ) -> list[CurriculumPerformance]:
        buckets: dict[str, list[CognitiveEvaluationResult]] = {}
        for result in results:
            buckets.setdefault(result.category, []).append(result)

        performance: list[CurriculumPerformance] = []
        for domain, items in sorted(buckets.items()):
            attempts = len(items)
            performance.append(
                CurriculumPerformance(
                    domain=domain,
                    attempts=attempts,
                    pass_rate=round(
                        len([item for item in items if item.passed]) / attempts,
                        4,
                    ),
                    average_confidence=round(
                        sum(item.confidence for item in items) / attempts,
                        4,
                    ),
                    average_latency_seconds=round(
                        sum(item.latency_seconds for item in items) / attempts,
                        4,
                    ),
                )
            )
        return performance

    def _prioritize_domains(
        self,
        domains: tuple[str, ...],
        performance_by_domain: dict[str, CurriculumPerformance],
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                domains,
                key=lambda domain: (
                    self._domain_priority(performance_by_domain.get(domain)),
                    domain,
                ),
            )
        )

    def _domain_priority(self, performance: CurriculumPerformance | None) -> float:
        if performance is None or performance.pass_rate is None:
            return 0.25
        if performance.attempts < 3:
            return 0.35
        return float(performance.pass_rate)

    def _difficulty_for(self, performance: CurriculumPerformance | None) -> int:
        if performance is None or performance.pass_rate is None:
            return self.min_difficulty
        if performance.attempts < 3:
            return self.min_difficulty
        if performance.pass_rate >= 0.85:
            return min(self.max_difficulty, self.min_difficulty + 2)
        if performance.pass_rate >= 0.65:
            return min(self.max_difficulty, self.min_difficulty + 1)
        return self.min_difficulty

    def _prompt(self, domain: str, difficulty: int) -> str:
        templates = {
            "arithmetic": "Solve an arithmetic task at difficulty {difficulty} and explain the steps.",
            "logic": "Evaluate a logic puzzle at difficulty {difficulty} and state the conclusion.",
            "causal_reasoning": "Analyze a causal chain at difficulty {difficulty} and identify likely effects.",
            "abstraction": "Extract the abstract pattern from examples at difficulty {difficulty}.",
            "planning": "Create a bounded plan for a task at difficulty {difficulty}.",
            "scheduling": "Resolve a scheduling constraint problem at difficulty {difficulty}.",
            "contradiction": "Identify and preserve a contradiction at difficulty {difficulty}.",
            "prediction": "Make a testable prediction for a scenario at difficulty {difficulty}.",
            "uncertainty": "Reason under uncertainty at difficulty {difficulty} and name unknowns.",
            "language": "Interpret a language task at difficulty {difficulty}.",
            "software_engineering": "Plan a software change at difficulty {difficulty}.",
            "scientific_reasoning": "Evaluate a scientific hypothesis at difficulty {difficulty}.",
            "government_workflows": "Analyze a government workflow at difficulty {difficulty}.",
            "research_methodology": "Design a research method at difficulty {difficulty}.",
        }
        template = templates.get(
            domain,
            "Complete a cognitive task in {domain} at difficulty {difficulty}.",
        )
        return template.format(domain=domain, difficulty=difficulty)

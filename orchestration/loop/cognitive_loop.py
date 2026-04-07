from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from orchestration.execution.evaluation_engine import EvaluationEngine
from orchestration.execution.resolution_executor import ResolutionExecutor
from orchestration.input.inquiry_adapter import InquiryAdapter
from orchestration.input.semantic_interpreter import SemanticInterpreter
from orchestration.memory.learning_integrator import LearningIntegrator
from orchestration.memory.strategy_memory import StrategyMemory
from orchestration.routing.arbitration_selector import ArbitrationSelector
from orchestration.routing.confidence_evaluator import ConfidenceEvaluator
from orchestration.routing.route_candidate_builder import RouteCandidateBuilder
from orchestration.schemas.execution_result import ExecutionResult
from orchestration.structuring.constraint_engine import ConstraintEngine
from orchestration.structuring.decomposition_engine import DecompositionEngine
from orchestration.structuring.task_typing_engine import TaskTypingEngine


class CognitiveLoop:
    """
    Full minimal orchestration loop.

    Wires:
    - fast answer memory via ResolutionExecutor
    - semantic recall via replay recall pipeline
    - replay queue via ReplayManager inside ResolutionExecutor
    - optional learning bundle factory and replay storage pipeline factory
    """

    def __init__(
        self,
        *,
        model: Optional[Any] = None,
        model_router: Optional[Any] = None,
        replay_recall_pipeline: Optional[Any] = None,
        recall_registry: Optional[Any] = None,
        learning_adapter: Optional[Any] = None,
        replay_storage_pipeline_factory: Optional[Callable[[str], Any]] = None,
        learning_bundle_factory: Optional[
            Callable[[Any, str, float, str], Any]
        ] = None,
    ) -> None:
        self.inquiry_adapter = InquiryAdapter()
        self.semantic_interpreter = SemanticInterpreter(model=model)
        self.task_typing = TaskTypingEngine()
        self.decomposition = DecompositionEngine()
        self.constraint_engine = ConstraintEngine()
        self.route_builder = RouteCandidateBuilder()
        self.confidence_evaluator = ConfidenceEvaluator()
        self.selector = ArbitrationSelector()

        # Keep references explicit so the loop can be inspected/debugged cleanly
        self._replay_recall_pipeline = replay_recall_pipeline
        self._recall_registry = recall_registry
        self._replay_storage_pipeline_factory = replay_storage_pipeline_factory
        self._learning_bundle_factory = learning_bundle_factory

        self.executor = ResolutionExecutor(
            model_router=model_router,
            replay_recall_pipeline=self._replay_recall_pipeline,
            recall_registry=self._recall_registry,
            replay_storage_pipeline_factory=self._replay_storage_pipeline_factory,
            learning_bundle_factory=self._learning_bundle_factory,
        )

        self.evaluator = EvaluationEngine()
        self.strategy_memory = StrategyMemory()
        self.learning_integrator = LearningIntegrator(
            learning_adapter=learning_adapter
        )

    def run(self, raw_input: str | Dict[str, object]) -> Dict[str, object]:
        # ---------------------------------
        # 1) Input adaptation + interpretation
        # ---------------------------------
        inquiry = self.inquiry_adapter.adapt(raw_input)
        interpreted = self.semantic_interpreter.interpret(inquiry)

        # ---------------------------------
        # 2) Task analysis
        # ---------------------------------
        task_type = self.task_typing.classify(interpreted)
        graph = self.decomposition.decompose(interpreted, task_type)
        constraints = self.constraint_engine.apply(interpreted, graph)

        # ---------------------------------
        # 3) Routing + selection
        # ---------------------------------
        candidates = self.route_builder.build(graph, constraints)
        scored = self.confidence_evaluator.score(interpreted, graph, candidates)
        plan = self.selector.select(scored)

        # ---------------------------------
        # 4) Execution
        # ---------------------------------
        result: ExecutionResult = self.executor.execute(interpreted, plan)
        evaluated = self.evaluator.evaluate(result)

        # ---------------------------------
        # 5) Strategy memory
        # ---------------------------------
        strategy_record = self.strategy_memory.build_record(
            inquiry=interpreted,
            graph=graph,
            result=evaluated,
        )

        # ---------------------------------
        # 6) Optional downstream learning surface
        # ---------------------------------
        learning_bundle = self.learning_integrator.prepare_bundle(
            inquiry=interpreted,
            result=evaluated,
            strategy_record=strategy_record,
        )

        return {
            "inquiry": interpreted,
            "task_type": task_type,
            "graph": graph,
            "constraints": constraints,
            "candidates": scored,
            "plan": plan,
            "result": evaluated,
            "strategy_record": strategy_record,
            "learning_bundle": learning_bundle,
        }
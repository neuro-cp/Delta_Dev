from __future__ import annotations

import ast
import json
import operator as op
from typing import Any, Callable, Optional

from integration.bridge.answer_memory import AnswerMemory
from integration.bridge.recall_bridge import RecallBridge
from integration.bridge.store_prompt import ask_store_prompt
from integration.bridge.replay_manager import ReplayManager

from orchestration.schemas.execution_plan import ExecutionPlan
from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket


class ResolutionExecutor:
    """
    Execution layer with:
    - AnswerMemory (fast recall)
    - ReplayManager (queued learning)
    - Semantic recall bridge
    - LLM + admin fallback
    """

    def __init__(
        self,
        *,
        model_router: Optional[Any] = None,
        replay_recall_pipeline: Optional[Any] = None,
        recall_registry: Optional[Any] = None,
        replay_storage_pipeline_factory: Optional[Callable[[str], Any]] = None,
        learning_bundle_factory: Optional[
            Callable[[InquiryPacket, str, float, str], Any]
        ] = None,
    ) -> None:
        self._model_router = model_router
        self._replay_recall_pipeline = replay_recall_pipeline
        self._recall_registry = recall_registry

        self._replay_storage_pipeline_factory = replay_storage_pipeline_factory
        self._learning_bundle_factory = learning_bundle_factory

        self._answer_memory = AnswerMemory()
        self._recall_bridge = RecallBridge()

        self._replay_manager: Optional[ReplayManager] = None
        if replay_storage_pipeline_factory is not None:
            self._replay_manager = ReplayManager(
                replay_storage_pipeline_factory,
                auto_flush_threshold=None,
            )

        self._store_threshold = 0.5
        self._admin_threshold = 0.3

    # =========================================================
    # MAIN EXECUTION
    # =========================================================

    def execute(self, inquiry: InquiryPacket, plan: ExecutionPlan) -> ExecutionResult:
        route = plan.selected_route_type
        print(f"[ROUTING] selected route = {route}")

        # ----------------------------------------
        # 0. MEMORY + RECALL COMPETITION
        # ----------------------------------------
        memory_hit = self._answer_memory.lookup(inquiry.raw_text)

        recall_candidate = None
        if self._replay_recall_pipeline and self._recall_registry:
            query = self._build_recall_query(inquiry)

            suggestions = self._replay_recall_pipeline.run(
                self._recall_registry,
                query,
            )

            recall_candidate = self._recall_bridge.interpret(suggestions, inquiry)

        # ----------------------------------------
        # PRIORITY: RECALL → MEMORY
        # ----------------------------------------
        if recall_candidate:
            print("[RECALL] selected over memory")
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="recall",
                success=True,
                output=recall_candidate["answer"],
                confidence=float(recall_candidate["confidence"]),
            )

        if memory_hit:
            print("[MEMORY] fallback")
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="memory",
                success=True,
                output=memory_hit["answer"],
                confidence=float(memory_hit["confidence"]),
            )
        # ----------------------------------------
        # 1. DETERMINISTIC
        # ----------------------------------------
        if route == "deterministic_solver":
            result = self._solve_math(inquiry.raw_text)
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route,
                success=True,
                output=str(result),
                confidence=1.0,
            )

        # ----------------------------------------
        # 2. RECALL
        # ----------------------------------------
        if route == "recall":
            return self._handle_recall(inquiry, plan)

        # ----------------------------------------
        # 3. LLM
        # ----------------------------------------
        return self._execute_llm(inquiry, plan, route)

    # =========================================================
    # RECALL HANDLER
    # =========================================================

    def _handle_recall(
        self,
        inquiry: InquiryPacket,
        plan: ExecutionPlan,
    ) -> ExecutionResult:
        if self._replay_recall_pipeline and self._recall_registry:
            query = self._build_recall_query(inquiry)

            suggestions = self._replay_recall_pipeline.run(
                self._recall_registry,
                query,
            )

            candidate = self._recall_bridge.interpret(suggestions, inquiry)

            if candidate:
                print("[RECALL] strong match")
                return ExecutionResult(
                    plan_id=plan.plan_id,
                    route_type="recall",
                    success=True,
                    output=candidate["answer"],
                    confidence=float(candidate["confidence"]),
                )

            print("[RECALL] weak → fallback")

        return self._execute_llm(inquiry, plan, "llm_fallback")

    # =========================================================
    # LLM EXECUTION
    # =========================================================

    def _execute_llm(
        self,
        inquiry: InquiryPacket,
        plan: ExecutionPlan,
        route_type: str,
    ) -> ExecutionResult:
        if not self._model_router:
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route_type,
                success=False,
                output=None,
                confidence=0.0,
            )

        result = self._model_router.route({"question": inquiry.raw_text})

        payload = getattr(result, "payload", {}) or {}
        confidence = float(getattr(result, "confidence_band", 0.0) or 0.0)
        raw_output = payload.get("raw_model_output", payload)

        parsed_output = raw_output
        parsed_confidence = confidence

        if isinstance(raw_output, str):
            try:
                parsed = json.loads(raw_output)
                if isinstance(parsed, dict):
                    parsed_output = parsed.get("answer", raw_output)
                    parsed_confidence = float(parsed.get("confidence", confidence))
            except Exception:
                pass

        output = parsed_output
        confidence = parsed_confidence

        # ----------------------------------------
        # STORE (USER CONFIRM)
        # ----------------------------------------
        if confidence >= self._store_threshold:
            if ask_store_prompt(str(output), confidence):
                self._store(inquiry, str(output), confidence, "llm")

        # ----------------------------------------
        # ADMIN FALLBACK
        # ----------------------------------------
        if confidence < self._admin_threshold:
            print("\n[ADMIN] low confidence")

            admin = input("Provide answer (or enter to skip): ").strip()
            if admin:
                self._store(inquiry, admin, 1.0, "admin")
                return ExecutionResult(
                    plan_id=plan.plan_id,
                    route_type="admin_override",
                    success=True,
                    output=admin,
                    confidence=1.0,
                )

        return ExecutionResult(
            plan_id=plan.plan_id,
            route_type=route_type,
            success=True,
            output=output,
            confidence=confidence,
        )

    # =========================================================
    # STORAGE (UPDATED)
    # =========================================================

    def _store(
        self,
        inquiry: InquiryPacket,
        answer: str,
        confidence: float,
        source: str,
    ):
        self._answer_memory.add(inquiry.raw_text, answer, confidence)

        if not self._replay_manager or not self._learning_bundle_factory:
            return

        try:
            bundle = self._learning_bundle_factory(
                inquiry,
                answer,
                confidence,
                source,
            )

            if isinstance(bundle, (list, tuple)):
                for b in bundle:
                    self._replay_manager.enqueue(b)
            else:
                self._replay_manager.enqueue(bundle)

        except Exception as e:
            print(f"[STORE] replay enqueue failed: {e}")

    # =========================================================
    # HELPERS
    # =========================================================

    def _build_recall_query(self, inquiry: InquiryPacket) -> Any:
        try:
            from memory.replay_recall.recall_query import RecallQuery

            return RecallQuery(
                active_regions=set(),
                decision_present=False,
            )
        except Exception:
            return {}

    def _solve_math(self, text: str) -> float:
        expr = self._extract_expression(text)
        node = ast.parse(expr, mode="eval").body
        return float(self._eval(node))

    def _extract_expression(self, text: str) -> str:
        cleaned = text.strip().lower()
        for prefix in ["what is", "calculate", "solve"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        return cleaned.replace("^", "**")

    def _eval(self, node: ast.AST) -> float:
        ops = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Pow: op.pow,
        }

        if isinstance(node, ast.Constant):
            return float(node.value)

        if isinstance(node, ast.BinOp):
            return ops[type(node.op)](
                self._eval(node.left),
                self._eval(node.right),
            )

        if isinstance(node, ast.UnaryOp):
            return -self._eval(node.operand)

        raise ValueError("Unsupported expression")

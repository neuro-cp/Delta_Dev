from __future__ import annotations

import ast
import operator as op
from typing import Any, Optional

from orchestration.schemas.execution_plan import ExecutionPlan
from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket


class ResolutionExecutor:
    """
    Executes a selected plan.

    External surfaces are injected optionally:
    - model_router: must expose route(payload)
    - replay_recall_pipeline: must expose run(registry, query)
    - learning_adapter: handled elsewhere
    """

    def __init__(
        self,
        *,
        model_router: Optional[Any] = None,
        replay_recall_pipeline: Optional[Any] = None,
        recall_registry: Optional[Any] = None,
    ) -> None:
        self._model_router = model_router
        self._replay_recall_pipeline = replay_recall_pipeline
        self._recall_registry = recall_registry

    def execute(self, inquiry: InquiryPacket, plan: ExecutionPlan) -> ExecutionResult:
        route = plan.selected_route_type
        print(f"[ROUTING] selected route = {route}")

        if route == "deterministic_solver":
            output = self._solve_math(inquiry.raw_text)
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route,
                success=True,
                output=str(output),
                confidence=1.0,
            )

        if route == "llm":
            return self._execute_llm(inquiry=inquiry, plan=plan, route_type=route)

        if route == "recall":
            if self._replay_recall_pipeline is not None and self._recall_registry is not None:
                query = self._build_recall_query(inquiry)
                suggestions = self._replay_recall_pipeline.run(self._recall_registry, query)

                return ExecutionResult(
                    plan_id=plan.plan_id,
                    route_type=route,
                    success=True,
                    output=suggestions,
                    confidence=0.7 if suggestions else 0.0,
                    artifacts={"recall_query": query},
                )

            if self._model_router is not None:
                return self._execute_llm(
                    inquiry=inquiry,
                    plan=plan,
                    route_type="llm_fallback",
                    artifacts={"fallback_reason": "no_recall_surface"},
                )

            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route,
                success=False,
                output=None,
                confidence=0.0,
                artifacts={"reason": "no_recall_surface"},
            )

        if route == "operator_query":
            if self._requires_operator_clarification(inquiry):
                return ExecutionResult(
                    plan_id=plan.plan_id,
                    route_type=route,
                    success=True,
                    output="operator clarification required",
                    confidence=0.0,
                )

            if self._model_router is not None:
                return self._execute_llm(
                    inquiry=inquiry,
                    plan=plan,
                    route_type="llm_fallback",
                    artifacts={"fallback_reason": "soft_ambiguity"},
                )

            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route,
                success=True,
                output="operator clarification required",
                confidence=0.0,
            )

        return ExecutionResult(
            plan_id=plan.plan_id,
            route_type=route,
            success=False,
            output=None,
            confidence=0.0,
            artifacts={"reason": "unknown_route"},
        )

    def _execute_llm(
        self,
        *,
        inquiry: InquiryPacket,
        plan: ExecutionPlan,
        route_type: str,
        artifacts: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        if self._model_router is None:
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type=route_type,
                success=False,
                output=None,
                confidence=0.0,
                artifacts={"reason": "no_model_router"},
            )

        result = self._model_router.route({"question": inquiry.raw_text})
        payload = getattr(result, "payload", {})
        confidence = float(getattr(result, "confidence_band", 0.0) or 0.0)

        merged_artifacts = {"model_bundle": result}
        if artifacts:
            merged_artifacts.update(artifacts)

        return ExecutionResult(
            plan_id=plan.plan_id,
            route_type=route_type,
            success=True,
            output=payload.get("raw_model_output", payload),
            confidence=confidence,
            artifacts=merged_artifacts,
        )

    def _requires_operator_clarification(self, inquiry: InquiryPacket) -> bool:
        text = (inquiry.raw_text or "").strip()
        if not text:
            return True

        lower = text.lower()

        if len(lower) <= 2:
            return True

        ambiguous_tokens = {"help", "hello", "hi", "hey", "what", "why"}
        if lower in ambiguous_tokens:
            return False

        return False

    def _build_recall_query(self, inquiry: InquiryPacket) -> Any:
        active_regions = set()
        for token in inquiry.semantic_tokens:
            upper = token.upper()
            if upper in {"PFC", "STN", "GPi".upper(), "GPI", "TRN", "MD"}:
                active_regions.add(upper)

        try:
            from memory.replay_recall.recall_query import RecallQuery  # type: ignore
            return RecallQuery(
                active_regions=active_regions,
                decision_present="decision" in inquiry.semantic_tokens,
            )
        except Exception:
            return {
                "active_regions": active_regions,
                "decision_present": "decision" in inquiry.semantic_tokens,
            }

    def _solve_math(self, text: str) -> float:
        expr = self._extract_expression(text)
        node = ast.parse(expr, mode="eval").body
        return float(self._eval_node(node))

    @staticmethod
    def _extract_expression(text: str) -> str:
            cleaned = text.strip()
            lower = cleaned.lower()

            for prefix in ["what is", "calculate", "solve"]:
                if lower.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    break

            cleaned = cleaned.rstrip(" ?.")

            # 🔥 FIX: support ^ as exponent
            cleaned = cleaned.replace("^", "**")

            return cleaned

    def _eval_node(self, node: ast.AST) -> float:
        ops = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Pow: op.pow,
        }

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](self._eval_node(node.left), self._eval_node(node.right))

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand)

        raise ValueError("Unsupported arithmetic expression")

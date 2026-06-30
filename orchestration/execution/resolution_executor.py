from __future__ import annotations

import json
import re
from typing import Any

from orchestration.schemas.execution_result import ExecutionResult


class ResolutionExecutor:
    """
    Resolution priority:
    1. Recall
    2. AnswerMemory
    3. Route-specific execution
    4. LLM fallback
    """

    def __init__(
        self,
        *,
        model_router=None,
        answer_memory=None,
        recall_bridge=None,
        replay_recall_pipeline=None,
        recall_registry=None,
        replay_storage_pipeline_factory=None,
        learning_bundle_factory=None,
    ) -> None:
        self._model_router = model_router
        self._answer_memory = answer_memory
        self._recall_bridge = recall_bridge
        self._replay_recall_pipeline = replay_recall_pipeline
        self._recall_registry = recall_registry
        self._replay_storage_pipeline_factory = replay_storage_pipeline_factory
        self._learning_bundle_factory = learning_bundle_factory

    # =========================================================
    # MAIN EXECUTION
    # =========================================================

    def execute(self, inquiry, plan) -> ExecutionResult:
        route = getattr(plan, "selected_route_type", "") or ""
        print(f"\n[ROUTING] selected route = {route}")

        query_text = getattr(inquiry, "raw_text", "") or ""

        # ---------------------------------
        # MEMORY LOOKUP
        # ---------------------------------
        memory_hit = self._lookup_memory(query_text)

        print("\n[MEMORY DEBUG]")
        print("query:", query_text)
        print("memory_hit:", memory_hit)
        print("----------------")

        # ---------------------------------
        # RECALL PIPELINE
        # ---------------------------------
        recall_candidate = None
        suggestions = []

        if self._replay_recall_pipeline and self._recall_registry:
            query = self._build_recall_query(inquiry)

            suggestions = self._replay_recall_pipeline.run(
                self._recall_registry,
                query,
            ) or []

            # =========================================
            # 🔴 ENRICHMENT LAYER (CRITICAL FIX)
            # =========================================
            enriched = []

            for s in suggestions:
                semantic_id = self._read_field(s, "semantic_id")

                if not semantic_id:
                    continue

                semantic = next(
                    (x for x in self._recall_registry if getattr(x, "semantic_id", None) == semantic_id),
                    None
                )
                # fallback symbolic recovery via AnswerMemory
                mem = self._answer_memory.lookup(query_text) if self._answer_memory else None

                enriched.append(
                    type("RecallEnriched", (), {
                        "semantic_id": semantic_id,
                        "pressure": self._read_field(s, "pressure", 0.0),
                        "inquiry": (mem or {}).get("inquiry") if mem else None,
                        "answer": (mem or {}).get("answer") if mem else None,
                        "confidence": (mem or {}).get("confidence", 1.0) if mem else 1.0,
                    })()
                )

            suggestions = enriched
            # =========================================

            print("\n[RECALL INPUT]")
            print("query:", query_text)
            print("suggestion_count:", len(suggestions))

            for suggestion in suggestions:
                print(" -> semantic_id:", self._read_field(suggestion, "semantic_id"))
                print("    answer:", self._read_field(suggestion, "answer"))
                print("    inquiry:", self._read_field(suggestion, "inquiry"))

            print("----------------")

            recall_candidate = self._interpret_recall(suggestions, inquiry)

        print("\n[RECALL OUTPUT]")
        print("recall_candidate:", recall_candidate)
        print("----------------")

        # ---------------------------------
        # PRIORITY: RECALL -> MEMORY
        # ---------------------------------
        if recall_candidate is not None:
            print("\n[DECISION] RECALL SELECTED")
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="recall",
                success=True,
                output=self._read_field(recall_candidate, "answer", ""),
                confidence=self._safe_float(
                    self._read_field(recall_candidate, "confidence", 0.0)
                ),
            )

        if memory_hit:
            print("\n[DECISION] MEMORY FALLBACK")
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="memory",
                success=True,
                output=self._read_field(memory_hit, "answer", ""),
                confidence=self._safe_float(
                    self._read_field(memory_hit, "confidence", 0.0)
                ),
            )

        # ---------------------------------
        # ROUTE-SPECIFIC EXECUTION
        # ---------------------------------
        if route == "deterministic_solver":
            print("\n[DECISION] DETERMINISTIC SOLVER SELECTED")
            return self._execute_solver(inquiry, plan)

        if route == "llm":
            print("\n[DECISION] LLM ROUTE SELECTED")
            return self._execute_llm(inquiry, plan)

        # ---------------------------------
        # FINAL FALLBACK
        # ---------------------------------
        print("\n[DECISION] UNKNOWN OR UNSUPPORTED ROUTE -> LLM FALLBACK")
        return self._execute_llm(inquiry, plan)

    # =========================================================
    # ROUTE EXECUTORS
    # =========================================================

    def _execute_solver(self, inquiry, plan) -> ExecutionResult:
        raw_text = getattr(inquiry, "raw_text", "") or ""
        expression = self._extract_expression(raw_text)

        print("\n[SOLVER DEBUG]")
        print("raw_text:", raw_text)
        print("expression:", expression)
        print("----------------")

        try:
            value = self._safe_eval(expression)
        except Exception as exc:
            print(f"[SOLVER] failed: {exc}")
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="deterministic_solver",
                success=False,
                output=f"solver_failed: {exc}",
                confidence=0.0,
            )

        return ExecutionResult(
            plan_id=plan.plan_id,
            route_type="deterministic_solver",
            success=True,
            output=value,
            confidence=1.0,
        )

    def _execute_llm(self, inquiry, plan) -> ExecutionResult:
        if self._model_router is None:
            return ExecutionResult(
                plan_id=plan.plan_id,
                route_type="llm",
                success=False,
                output="No model router configured",
                confidence=0.0,
            )

        payload = {
            "question": getattr(inquiry, "raw_text", "") or "",
        }
        metadata = getattr(inquiry, "metadata", {}) or {}
        attended_context = metadata.get("attended_context", [])
        if attended_context:
            payload["attended_context"] = attended_context
        working_memory = metadata.get("working_memory", [])
        if working_memory:
            payload["working_memory"] = working_memory

        bundle = self._model_router.route(payload)

        raw_output = ""
        confidence = 0.0

        if bundle is not None:
            payload_dict = getattr(bundle, "payload", {}) or {}
            raw_output = payload_dict.get("raw_model_output", "") or ""
            confidence = self._safe_float(getattr(bundle, "confidence_band", 0.0))

        parsed_answer = self._extract_answer(raw_output)
        final_output = parsed_answer if parsed_answer else raw_output.strip()

        print("\n[LLM DEBUG]")
        print("raw_output:", raw_output)
        print("parsed_answer:", parsed_answer)
        print("final_output:", final_output)
        print("confidence:", confidence)
        print("----------------")

        return ExecutionResult(
            plan_id=plan.plan_id,
            route_type="llm",
            success=bool(final_output),
            output=final_output,
            confidence=confidence,
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def _build_recall_query(self, inquiry):
        if not self._recall_bridge:
            return None

        query_text = getattr(inquiry, "raw_text", "") or ""

        if not query_text:
            return None

        # Build runtime artifact
        artifact = self._recall_bridge._artifact_builder.build_from_text(query_text)

        return type("RecallQuery", (), {
            "active_regions": set(artifact.keys()),
            "artifact": artifact,
            "raw_text": query_text,

            # 🔥 REQUIRED FOR MATCHER
            "decision_present": False
        })()
    
    def _lookup_memory(self, query_text: str):
        if not self._answer_memory:
            return None
        return self._answer_memory.lookup(query_text)

    def _interpret_recall(self, suggestions, inquiry):
        if not self._recall_bridge:
            return None
        return self._recall_bridge.interpret(suggestions, inquiry)

    def _read_field(self, obj: Any, name: str, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    def _safe_float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _extract_expression(self, text: str) -> str:
        expr = text.strip().lower()

        for prefix in ("what is", "calculate", "solve"):
            if expr.startswith(prefix):
                expr = expr[len(prefix):].strip()
                break

        expr = expr.rstrip(" ?.=")
        expr = expr.replace("^", "**")
        expr = re.sub(r"[^0-9\+\-\*\/\(\)\.\%\s]", "", expr)
        expr = " ".join(expr.split())

        if not expr:
            raise ValueError("No valid mathematical expression found")

        return expr

    def _safe_eval(self, expression: str):
        allowed_names = {}
        code = compile(expression, "<solver>", "eval")

        for name in code.co_names:
            if name not in allowed_names:
                raise ValueError(f"Illegal token in expression: {name}")

        return eval(code, {"__builtins__": {}}, allowed_names)

    def _extract_answer(self, raw_output: str) -> str:
        if not raw_output:
            return ""

        try:
            data = json.loads(raw_output)
            answer = data.get("answer", "")
            return answer.strip() if isinstance(answer, str) else str(answer)
        except Exception:
            pass

        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1

        if start >= 0 and end > start:
            try:
                data = json.loads(raw_output[start:end])
                answer = data.get("answer", "")
                return answer.strip() if isinstance(answer, str) else str(answer)
            except Exception:
                pass

        return raw_output.strip()

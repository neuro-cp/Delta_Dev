from __future__ import annotations

from typing import List

from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.route_candidate import RouteCandidate
from orchestration.schemas.task_graph import TaskGraph, TaskType


class ConfidenceEvaluator:
    """
    Score route candidates heuristically.

    Design goals
    ------------
    - deterministic_solver should win only for clean symbolic math
    - natural-language math phrases should fall back to llm
    - recall should win only for explicit lookup-style questions
    - llm should be the safe default for semantic or ambiguous phrasing
    """

    _PRIORITY = {
        "deterministic_solver": 4,
        "recall": 3,
        "llm": 2,
        "operator_query": 1,
    }

    def score(
        self,
        inquiry: InquiryPacket,
        graph: TaskGraph,
        candidates: List[RouteCandidate],
    ) -> List[RouteCandidate]:
        scored: List[RouteCandidate] = []

        for candidate in candidates:
            score = self._score_candidate(inquiry, graph, candidate)

            scored.append(
                RouteCandidate(
                    route_id=candidate.route_id,
                    route_type=candidate.route_type,
                    target_node_id=candidate.target_node_id,
                    rationale=candidate.rationale,
                    estimated_confidence=score,
                    estimated_cost=candidate.estimated_cost,
                    allowed=candidate.allowed,
                    blocked_reasons=list(candidate.blocked_reasons),
                    metadata=dict(candidate.metadata),
                )
            )

        return scored

    def _score_candidate(
        self,
        inquiry: InquiryPacket,
        graph: TaskGraph,
        candidate: RouteCandidate,
    ) -> float:
        text = (inquiry.raw_text or "").strip()
        lower_text = text.lower()

        base = 0.1

        # -----------------------------
        # Deterministic solver
        # -----------------------------
        if graph.task_type == TaskType.MATH and candidate.route_type == "deterministic_solver":
            expr = self._extract_candidate_expression(lower_text)

            is_expression = self._looks_like_expression(expr)
            has_operator = self._has_operator(expr)
            is_natural_language_math = self._is_natural_language_math(lower_text)
            is_percent_phrase = self._is_percent_phrase(lower_text)
            is_word_operator_phrase = self._is_word_operator_phrase(lower_text)

            if (
                is_expression
                and has_operator
                and not is_natural_language_math
                and not is_percent_phrase
                and not is_word_operator_phrase
            ):
                base += 0.8
            else:
                base -= 0.15

        # -----------------------------
        # Recall
        # -----------------------------
        if graph.task_type == TaskType.LOOKUP and candidate.route_type == "recall":
            if self._looks_like_lookup(lower_text):
                base += 0.35
            else:
                base += 0.10

        # -----------------------------
        # LLM
        # -----------------------------
        if graph.task_type == TaskType.COMPARISON and candidate.route_type == "llm":
            base += 0.65

        if graph.task_type == TaskType.DIAGNOSTIC and candidate.route_type == "llm":
            base += 0.5

        if graph.task_type == TaskType.AMBIGUOUS and candidate.route_type == "llm":
            base += 0.45

        # Give LLM priority when the question was typed as MATH
        # but is clearly natural language rather than symbolic math.
        if graph.task_type == TaskType.MATH and candidate.route_type == "llm":
            expr = self._extract_candidate_expression(lower_text)
            if (
                self._is_natural_language_math(lower_text)
                or self._is_percent_phrase(lower_text)
                or self._is_word_operator_phrase(lower_text)
                or not self._looks_like_expression(expr)
                or not self._has_operator(expr)
            ):
                base += 0.45

        # -----------------------------
        # Operator query
        # -----------------------------
        if graph.task_type == TaskType.AMBIGUOUS and candidate.route_type == "operator_query":
            if self._requires_hard_clarification(lower_text):
                base += 0.55
            else:
                base += 0.15

        # -----------------------------
        # Inquiry-side confidence adjustment
        # -----------------------------
        if inquiry.confidence is not None and candidate.route_type == "llm":
            base += 0.1 * max(0.0, min(1.0, inquiry.confidence))

        # -----------------------------
        # Cost penalty
        # -----------------------------
        base -= min(0.25, candidate.estimated_cost * 0.1)

        return max(0.0, min(1.0, round(base, 4)))

    @staticmethod
    def _extract_candidate_expression(text: str) -> str:
        expr = text.strip()

        for prefix in ["what is", "calculate", "solve"]:
            if expr.startswith(prefix):
                expr = expr[len(prefix):].strip()
                break

        expr = expr.rstrip(" ?.")
        return expr

    @staticmethod
    def _looks_like_expression(text: str) -> bool:
        if not text:
            return False

        allowed = set("0123456789+-*/().^ %")
        return all(ch in allowed for ch in text)

    @staticmethod
    def _has_operator(text: str) -> bool:
        return any(op in text for op in ["+", "-", "*", "/", "^"])

    @staticmethod
    def _is_natural_language_math(text: str) -> bool:
        patterns = [
            "difference between",
            "sum of",
            "product of",
            "ratio of",
            "average of",
            "mean of",
            "increase from",
            "decrease from",
            "more than",
            "less than",
        ]
        return any(p in text for p in patterns)

    @staticmethod
    def _is_percent_phrase(text: str) -> bool:
        patterns = [
            "percent of",
            "percentage of",
            "% of",
        ]
        return any(p in text for p in patterns)

    @staticmethod
    def _is_word_operator_phrase(text: str) -> bool:
        patterns = [
            "plus",
            "minus",
            "times",
            "multiplied by",
            "divided by",
            "over",
        ]
        return any(p in text for p in patterns)

    @staticmethod
    def _looks_like_lookup(text: str) -> bool:
        patterns = [
            "what role does",
            "what is the role of",
            "what does",
            "tell me about",
            "look up",
            "find",
        ]
        return any(p in text for p in patterns)

    @staticmethod
    def _requires_hard_clarification(text: str) -> bool:
        if not text:
            return True

        if len(text) <= 2:
            return True

        hard_cases = {
            "?",
            "??",
            "help",
            "hello",
            "hi",
            "hey",
        }
        return text in hard_cases
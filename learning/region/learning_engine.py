from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Iterable

from learning.region.learning_record import (
    ConfidenceUpdate,
    LearningRecord,
    SemanticCandidate,
)
from orchestration.attention import AttentionItem
from orchestration.reflection import ReflectionRecord


class LearningEngine:
    """
    First Learning Region.

    This engine performs structural learning only. It emits proposals,
    confidence-change suggestions, and questions. It does not apply them.
    """

    def learn(
        self,
        *,
        cycle_id: str,
        prompt: str,
        output: str,
        success: bool,
        attended_items: Iterable[AttentionItem],
        reflection: ReflectionRecord,
    ) -> LearningRecord:
        attended = list(attended_items)
        repeated_ids = list(reflection.repeated)
        semantic_candidates: list[SemanticCandidate] = []
        confidence_updates: list[ConfidenceUpdate] = []
        questions: list[str] = []
        goal_candidates: list[str] = []

        if success:
            semantic_candidates.extend(
                self._extract_semantic_candidates(
                    prompt=prompt,
                    output=output,
                    evidence_memory_ids=list(reflection.consolidation_candidates)
                    or repeated_ids[:5],
                    reflection=reflection,
                )
            )

        if success and repeated_ids and not semantic_candidates:
            questions.append(
                "What reusable proposition is supported by the repeated attended context?"
            )

        for item in attended:
            if item.factors.get("task_relevance", 0.0) > 0.0:
                confidence_updates.append(
                    ConfidenceUpdate(
                        target_id=item.item_id,
                        delta=0.03,
                        reason="Memory was attended during a successful cycle.",
                    )
                )

        if not attended:
            questions.append(f"What prior knowledge would help answer: {prompt}")
            goal_candidates.append(f"Acquire context for: {prompt}")

        if not success:
            questions.append(f"Why did this cycle fail: {prompt}")
            goal_candidates.append(f"Resolve failed cycle for: {prompt}")

        for conflict in reflection.conflicts:
            questions.append(f"Resolve conflict: {conflict}")
            goal_candidates.append(f"Investigate contradiction: {conflict}")

        return LearningRecord(
            learning_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            cycle_id=cycle_id,
            semantic_candidates=semantic_candidates,
            confidence_updates=confidence_updates,
            questions=questions,
            goal_candidates=goal_candidates,
            consolidation_candidates=list(reflection.consolidation_candidates),
            metadata={
                "success": bool(success),
                "attended_count": len(attended),
                "prompt_length": len(prompt),
                "output_length": len(str(output)),
                "reflection_quality": reflection.metadata.get("quality"),
            },
        )

    def _extract_semantic_candidates(
        self,
        *,
        prompt: str,
        output: str,
        evidence_memory_ids: list[str],
        reflection: ReflectionRecord,
    ) -> list[SemanticCandidate]:
        text = self._answer_text(output)
        candidates: list[SemanticCandidate] = []
        for sentence in self._sentences(text):
            if not self._looks_reusable(sentence):
                continue
            candidates.append(
                SemanticCandidate(
                    text=sentence,
                    evidence_memory_ids=evidence_memory_ids[:5],
                    confidence=self._candidate_confidence(reflection),
                    rationale=(
                        "Extracted from successful provider output as a reusable "
                        "claim for semantic consolidation."
                    ),
                )
            )
            if len(candidates) >= 3:
                break

        return candidates

    def _answer_text(self, output: str) -> str:
        raw = str(output or "").strip()
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                answer = parsed.get("answer")
                if answer:
                    return str(answer)
        except Exception:
            pass
        return raw

    def _sentences(self, text: str) -> list[str]:
        raw = str(text)
        raw = re.sub(r"\bReusable propositions:\s*", "\n", raw, flags=re.IGNORECASE)
        raw = re.sub(r"(?:^|\n)\s*[-*•]\s+", ". ", raw)
        raw = re.sub(r"\s+[-*•]\s+", ". ", raw)
        normalized = " ".join(raw.replace("\n", " ").split())
        if not normalized:
            return []
        parts = re.split(r"(?<=[.!?])\s+", normalized)
        return [self._clean_sentence(part) for part in parts if self._clean_sentence(part)]

    def _looks_reusable(self, sentence: str) -> bool:
        return not self._candidate_rejection_reasons(sentence)

    def _candidate_rejection_reasons(self, sentence: str) -> list[str]:
        normalized = self._clean_sentence(sentence)
        lower = normalized.lower()
        tokens = re.findall(r"[a-z0-9_]+", lower)
        reasons: list[str] = []
        if len(tokens) < 5:
            reasons.append("too_short")
        if len(normalized) > 260:
            reasons.append("too_long")
        scaffolding_phrases = (
            "complete the cycle",
            "the cycle can be completed",
            "delta training data",
            "output contract",
            "reusable propositions",
            "this prompt",
            "this task",
            "this prediction",
            "the question",
            "the user",
            "answer naturally",
            "make at least one testable prediction",
            "identify evidence that would change the answer",
            "reflect on uncertainty",
            "training objective requires",
            "repeated attended context appears relevant",
            "predicting the failure mode",
            "belief revision delta",
        )
        if any(phrase in lower for phrase in scaffolding_phrases):
            reasons.append("prompt_scaffolding")
        if lower.startswith(("answer:", "the answer is", "based on the prompt", "based on this task")):
            reasons.append("answer_scaffolding")
        if lower.startswith(("this process", "to mitigate this", "this approach")):
            reasons.append("missing_referent")
        first_token = tokens[0] if tokens else ""
        imperative_starts = {
            "allocate",
            "answer",
            "compare",
            "create",
            "explain",
            "identify",
            "make",
            "name",
            "plan",
            "predict",
            "preserve",
            "reflect",
            "revise",
            "state",
            "use",
        }
        if first_token in imperative_starts:
            reasons.append("imperative_task_wording")
        if lower.startswith(("if ", "when ")) and "," not in lower and " then " not in lower:
            reasons.append("dangling_conditional")
        fragment_endings = (
            "could include",
            "would include",
            "may include",
            "could require",
            "would require",
            "may require",
            "can require",
            "is that",
            "is the",
            "are the",
            "includes",
            "include",
            "requires",
            "require",
            "require",
            "would",
            "could",
            "may",
            "should",
            "must",
            "will",
            "can",
            "was",
            "were",
            "be",
            "been",
            "being",
            "based",
            "forecasted",
            "significant",
            "the",
            "a",
            "an",
            "to",
            "of",
            "for",
        )
        if lower.endswith(fragment_endings):
            reasons.append("incomplete_proposition")
        predicate_signals = {
            "is",
            "are",
            "was",
            "were",
            "can",
            "should",
            "must",
            "may",
            "will",
            "requires",
            "require",
            "includes",
            "reduces",
            "increases",
            "decreases",
            "improves",
            "weakens",
            "supports",
            "fails",
            "changes",
            "depends",
            "indicates",
        }
        if not (set(tokens) & predicate_signals):
            reasons.append("missing_predicate_signal")
        if lower.startswith(("evidence that would", "a testable prediction", "testable prediction")):
            reasons.append("prompt_artifact")
        if len(re.findall(r"\b(and|or|while|but)\b", lower)) >= 4:
            reasons.append("possible_merged_propositions")
        reusable_terms = {
            "because",
            "confidence",
            "contradiction",
            "conflict",
            "evidence",
            "fail",
            "falsify",
            "if",
            "predict",
            "prediction",
            "requires",
            "require",
            "risk",
            "should",
            "therefore",
            "uncertainty",
            "when",
            "reduces",
            "increases",
            "decreases",
            "improves",
            "supports",
            "depends",
            "indicates",
        }
        if not (set(tokens) & reusable_terms):
            reasons.append("missing_reusable_signal")
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _clean_sentence(sentence: str) -> str:
        cleaned = str(sentence).strip().strip("\"'")
        return cleaned.rstrip(",;:.!?")

    @staticmethod
    def _candidate_confidence(reflection: ReflectionRecord) -> float:
        quality = reflection.metadata.get("quality", {}) if reflection.metadata else {}
        score = float(quality.get("score", 0.6) if isinstance(quality, dict) else 0.6)
        return round(max(0.45, min(0.85, 0.55 + (score * 0.25))), 4)

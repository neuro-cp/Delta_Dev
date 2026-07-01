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
            semantic_candidates.append(
                SemanticCandidate(
                    text=(
                        "Repeated attended context appears relevant to the "
                        f"prompt: {prompt}"
                    ),
                    evidence_memory_ids=repeated_ids[:5],
                    confidence=min(0.85, 0.45 + (0.08 * len(repeated_ids))),
                    rationale="Repeated attended memories overlapped with the current task.",
                )
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

        if not candidates:
            prompt_claim = self._prompt_as_claim(prompt)
            if prompt_claim:
                candidates.append(
                    SemanticCandidate(
                        text=prompt_claim,
                        evidence_memory_ids=evidence_memory_ids[:5],
                        confidence=max(0.5, self._candidate_confidence(reflection) - 0.12),
                        rationale=(
                            "Extracted from a successful training prompt when provider "
                            "output did not contain a reusable claim."
                        ),
                    )
                )
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
        normalized = " ".join(str(text).replace("\n", " ").split())
        if not normalized:
            return []
        parts = re.split(r"(?<=[.!?])\s+", normalized)
        return [self._clean_sentence(part) for part in parts if self._clean_sentence(part)]

    def _looks_reusable(self, sentence: str) -> bool:
        tokens = re.findall(r"[a-z0-9_]+", sentence.lower())
        if len(tokens) < 7:
            return False
        if len(sentence) > 260:
            return False
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
            "risk",
            "should",
            "therefore",
            "uncertainty",
            "when",
        }
        return bool(set(tokens) & reusable_terms)

    def _prompt_as_claim(self, prompt: str) -> str | None:
        normalized = self._clean_sentence(str(prompt).split("\n\n", 1)[0])
        tokens = re.findall(r"[a-z0-9_]+", normalized.lower())
        if len(tokens) < 8:
            return None
        if len(normalized) > 220:
            normalized = normalized[:217].rstrip() + "..."
        return f"Training objective requires reasoning about: {normalized}"

    @staticmethod
    def _clean_sentence(sentence: str) -> str:
        cleaned = str(sentence).strip().strip("\"'")
        return cleaned.rstrip(",;:")

    @staticmethod
    def _candidate_confidence(reflection: ReflectionRecord) -> float:
        quality = reflection.metadata.get("quality", {}) if reflection.metadata else {}
        score = float(quality.get("score", 0.6) if isinstance(quality, dict) else 0.6)
        return round(max(0.45, min(0.85, 0.55 + (score * 0.25))), 4)

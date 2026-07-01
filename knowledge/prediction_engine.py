from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord


class PredictionEngine:
    """
    Generate open predictions from sufficiently confident knowledge.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def generate_for(
        self,
        record: SemanticKnowledgeRecord,
        *,
        threshold: float = 0.6,
    ) -> PredictionRecord | None:
        if record.confidence < threshold:
            return None

        expectation = f"If this concept is relevant again, expect: {record.definition}"
        if self.find_equivalent(expectation) is not None:
            return None

        return PredictionRecord(
            prediction_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_concept_id=record.concept_id,
            expectation=expectation,
            confidence=max(0.0, min(1.0, record.confidence * 0.8)),
            metadata={"concept": record.concept},
        )

    def add_all(self, records: List[PredictionRecord]) -> List[PredictionRecord]:
        if not records:
            return []

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return records

    def all(self) -> List[PredictionRecord]:
        if not self.path.exists():
            return []

        records: List[PredictionRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(PredictionRecord(**json.loads(line)))
        return records

    def latest(self) -> List[PredictionRecord]:
        records_by_id: dict[str, PredictionRecord] = {}
        for record in self.all():
            records_by_id[record.prediction_id] = record
        return list(records_by_id.values())

    def quality_metrics(self) -> dict[str, Any]:
        records = self.latest()
        total = len(records)
        open_count = len([record for record in records if record.status == "open"])
        supported = [
            record
            for record in records
            if record.status in {"supported", "succeeded"}
        ]
        failed = [record for record in records if record.status == "failed"]
        evaluated = supported + failed
        evidence_scores = [
            float(record.metadata.get("validation", {}).get("score", 0.0))
            for record in evaluated
            if isinstance(record.metadata.get("validation"), dict)
        ]

        return {
            "total": total,
            "open": open_count,
            "evaluated": len(evaluated),
            "supported": len(supported),
            "failed": len(failed),
            "accuracy": (
                round(len(supported) / len(evaluated), 4)
                if evaluated
                else None
            ),
            "coverage": round(len(evaluated) / total, 4) if total else 0.0,
            "failure_rate": (
                round(len(failed) / len(evaluated), 4)
                if evaluated
                else None
            ),
            "average_evidence_score": (
                round(sum(evidence_scores) / len(evidence_scores), 4)
                if evidence_scores
                else None
            ),
        }

    def find_equivalent(self, expectation: str) -> PredictionRecord | None:
        normalized = self._normalize(expectation)
        for record in self.latest():
            if self._normalize(record.expectation) == normalized:
                return record
        return None

    def validate_against_observations(self, observations: list) -> List[PredictionRecord]:
        validated: List[PredictionRecord] = []
        observation_records = [
            item
            for item in observations
            if getattr(item, "kind", "") in {"observation", "bootstrap_observation"}
        ]
        if not observation_records:
            return []

        for prediction in self.latest():
            if prediction.status != "open":
                continue
            best_result: dict[str, Any] | None = None
            for observation in observation_records:
                result = self._score_evidence(prediction, observation)
                if result["outcome"] == "unknown":
                    continue
                if best_result is None or result["score"] > best_result["score"]:
                    best_result = result
            if best_result is None:
                continue

            support_ids = []
            failing_ids = []
            status = best_result["outcome"]
            confidence_delta = 0.05
            if status == "supported":
                support_ids.append(best_result["observation_id"])
                confidence = min(1.0, prediction.confidence + confidence_delta)
            else:
                failing_ids.append(best_result["observation_id"])
                confidence = max(0.0, prediction.confidence - confidence_delta)

            revised = PredictionRecord(
                prediction_id=prediction.prediction_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=prediction.source_concept_id,
                expectation=prediction.expectation,
                confidence=confidence,
                status=status,
                supporting_observations=list(
                    dict.fromkeys(prediction.supporting_observations + support_ids)
                ),
                failing_observations=list(
                    dict.fromkeys(prediction.failing_observations + failing_ids)
                ),
                metadata={
                    **prediction.metadata,
                    "validation": {
                        "method": "evidence_claim_score",
                        "outcome": status,
                        "score": best_result["score"],
                        "rationale": best_result["rationale"],
                        "observation_id": best_result["observation_id"],
                        "prediction_claim": best_result["prediction_claim"],
                        "evidence_claim": best_result["evidence_claim"],
                    },
                },
            )
            validated.append(revised)
        self.add_all(validated)
        return validated

    def _score_evidence(self, prediction: PredictionRecord, observation: Any) -> dict[str, Any]:
        prediction_claims = self._prediction_claims(prediction)
        evidence_claims = self._observation_claims(observation)
        best = {
            "outcome": "unknown",
            "score": 0.0,
            "rationale": "no comparable evidence claim",
            "observation_id": getattr(observation, "memory_id", ""),
            "prediction_claim": {},
            "evidence_claim": {},
        }

        for prediction_claim in prediction_claims:
            for evidence_claim in evidence_claims:
                result = self._compare_claims(prediction_claim, evidence_claim)
                if result["score"] > best["score"]:
                    best = {
                        **result,
                        "observation_id": getattr(observation, "memory_id", ""),
                        "prediction_claim": prediction_claim,
                        "evidence_claim": evidence_claim,
                    }
        return best

    def _prediction_claims(self, prediction: PredictionRecord) -> list[dict[str, Any]]:
        explicit = self._metadata_claims(prediction.metadata)
        if explicit:
            return explicit

        return [
            {
                "subject": self._normalize_subject(prediction.metadata.get("concept", "")),
                "state": self._state_from_text(prediction.expectation),
                "terms": sorted(self._tokens(prediction.expectation)),
                "source": "prediction_expectation",
            }
        ]

    def _observation_claims(self, observation: Any) -> list[dict[str, Any]]:
        metadata = dict(getattr(observation, "metadata", {}) or {})
        explicit = self._metadata_claims(metadata)
        if explicit:
            return explicit

        text = str(getattr(observation, "text", ""))
        return [
            {
                "subject": self._subject_from_text(text),
                "state": self._state_from_text(text),
                "terms": sorted(self._tokens(text)),
                "source": "observation_text",
            }
        ]

    def _metadata_claims(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        raw_claims = (
            metadata.get("expected_claims")
            or metadata.get("claims")
            or metadata.get("facts")
            or metadata.get("claim")
        )
        if not raw_claims:
            return []
        if isinstance(raw_claims, dict):
            raw_claims = [raw_claims]
        if isinstance(raw_claims, str):
            raw_claims = [{"text": raw_claims}]

        claims = []
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            subject = item.get("subject") or item.get("entity") or self._subject_from_text(text)
            state = item.get("state") or item.get("status") or self._state_from_text(text)
            terms = item.get("terms") or self._tokens(text)
            claims.append(
                {
                    "subject": self._normalize_subject(subject),
                    "state": self._normalize_state(state),
                    "terms": sorted({str(term).lower() for term in terms}),
                    "source": "metadata",
                }
            )
        return claims

    def _compare_claims(
        self,
        prediction_claim: dict[str, Any],
        evidence_claim: dict[str, Any],
    ) -> dict[str, Any]:
        score = 0.0
        rationale = []

        prediction_subject = prediction_claim.get("subject")
        evidence_subject = evidence_claim.get("subject")
        subject_matches = bool(
            prediction_subject and evidence_subject and prediction_subject == evidence_subject
        )
        if subject_matches:
            score += 0.45
            rationale.append("subject matched")
        elif prediction_subject and prediction_subject in set(evidence_claim.get("terms", [])):
            score += 0.35
            rationale.append("predicted concept appeared in evidence")

        prediction_state = prediction_claim.get("state")
        evidence_state = evidence_claim.get("state")
        state_matches = bool(
            prediction_state and evidence_state and prediction_state == evidence_state
        )
        state_conflicts = bool(
            prediction_state
            and evidence_state
            and self._states_conflict(prediction_state, evidence_state)
        )
        if state_matches:
            score += 0.4
            rationale.append("state matched")
        elif state_conflicts and subject_matches:
            return {
                "outcome": "failed",
                "score": 0.85,
                "rationale": "subject matched but observed state conflicts",
            }

        prediction_terms = set(prediction_claim.get("terms", []))
        evidence_terms = set(evidence_claim.get("terms", []))
        shared_terms = prediction_terms & evidence_terms
        if prediction_terms and evidence_terms:
            term_score = len(shared_terms) / max(len(prediction_terms), len(evidence_terms))
            score += min(0.35, term_score)
            if shared_terms:
                rationale.append(f"shared terms: {', '.join(sorted(shared_terms)[:5])}")

        if score >= 0.65:
            return {
                "outcome": "supported",
                "score": round(score, 4),
                "rationale": "; ".join(rationale) or "evidence matched prediction",
            }

        return {
            "outcome": "unknown",
            "score": round(score, 4),
            "rationale": "; ".join(rationale) or "insufficient evidence",
        }

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(sorted(PredictionEngine._tokens(text)))

    @staticmethod
    def _subject_from_text(text: str) -> str:
        normalized = str(text).lower()
        match = re.search(r"\bjob\s*#?\s*(\d+)\b", normalized)
        if match:
            return f"job:{match.group(1)}"
        return ""

    @staticmethod
    def _normalize_subject(value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        match = re.search(r"\bjob\s*:?\s*#?\s*(\d+)\b", text)
        if match:
            return f"job:{match.group(1)}"
        return text

    @staticmethod
    def _state_from_text(text: str) -> str:
        lower = str(text).lower()
        if any(term in lower for term in ["completed", "complete", "finished", "finish", "done"]):
            return "completed"
        if any(term in lower for term in ["cancelled", "canceled", "failed", "blocked"]):
            return "failed"
        return ""

    @staticmethod
    def _normalize_state(value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        if text in {"complete", "completed", "finished", "finish", "done"}:
            return "completed"
        if text in {"cancelled", "canceled", "failed", "blocked"}:
            return "failed"
        return text

    @staticmethod
    def _states_conflict(predicted: str, observed: str) -> bool:
        conflicts = {
            ("completed", "failed"),
            ("failed", "completed"),
        }
        return (predicted, observed) in conflicts

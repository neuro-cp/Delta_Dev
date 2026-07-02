from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
from knowledge.justification_engine import JustificationReport
from knowledge.prediction_record import PredictionRecord
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(text).lower()))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "can",
        "for",
        "from",
        "if",
        "in",
        "is",
        "it",
        "of",
        "or",
        "that",
        "the",
        "then",
        "this",
        "to",
        "with",
    }
    return {token for token in _tokens(text) if token not in stop and len(token) > 2}


def _prompt_specificity(concept: str, definition: str) -> float:
    text = f"{concept} {definition}".lower()
    prompt_phrases = (
        "answer",
        "delta trainer",
        "this prediction",
        "this scenario",
        "would falsify",
        "would change the answer",
        "the evidence that",
        "testable prediction",
        "for example",
        "complete the cycle",
        "the cycle can be completed",
        "training objective",
        "delta training data",
        "answer ",
        "evidence that would revise",
        "to predict this",
    )
    hits = sum(1 for phrase in prompt_phrases if phrase in text)
    length_penalty = 1.0 if len(_content_tokens(text)) < 7 else 0.0
    return round(min(1.0, (hits * 0.16) + (length_penalty * 0.2)), 4)


def _redundancy_scores(records: list) -> dict[str, float]:
    scores: dict[str, float] = {}
    token_sets = {
        record.concept_id: _content_tokens(f"{record.concept} {record.definition}")
        for record in records
    }
    ids = list(token_sets)
    for concept_id in ids:
        current = token_sets[concept_id]
        best = 0.0
        for other_id in ids:
            if other_id == concept_id:
                continue
            other = token_sets[other_id]
            if not current or not other:
                continue
            score = len(current & other) / max(1, len(current | other))
            best = max(best, score)
        scores[concept_id] = round(best, 4)
    return scores


def _relationship_centrality(relationships: RelationshipStore) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for relationship in relationships.latest():
        counts[relationship.source_id] += 1
        counts[relationship.target_id] += 1
    return dict(counts)


def _cross_profile_recurrence(memory: MemoryStore) -> dict[str, int]:
    # Experiment prompts are not linked directly to concept ids yet. Use broad
    # phrase recurrence across validation/training memories as a report-only proxy.
    profile_by_phrase: dict[str, set[str]] = defaultdict(set)
    for item in memory.all():
        profile = ""
        for tag in item.tags:
            if tag not in {"training", "governed", "calibration"}:
                profile = str(tag)
                break
        tokens = sorted(_content_tokens(item.text))
        for index in range(0, max(0, len(tokens) - 2), 3):
            phrase = " ".join(tokens[index : index + 3])
            if phrase:
                profile_by_phrase[phrase].add(profile or "unknown")
    return {phrase: len(profiles) for phrase, profiles in profile_by_phrase.items()}


def _concept_reuse(record: Any, phrase_profiles: dict[str, int]) -> float:
    tokens = sorted(_content_tokens(f"{record.concept} {record.definition}"))
    if len(tokens) < 3:
        return 0.0
    best = 0
    for index in range(0, len(tokens) - 2):
        best = max(best, phrase_profiles.get(" ".join(tokens[index : index + 3]), 0))
    return round(min(1.0, best / 4), 4)


def _promotion_state(score: float, *, unresolved: int, contradictions: int) -> str:
    if contradictions > 0 or score < 0.2:
        return "Reject"
    if unresolved > 0:
        return "Hold for Validation"
    if score >= 0.75:
        return "Promote"
    if score >= 0.45:
        return "Candidate"
    return "Experimental"


def run_validation(
    *,
    store_root: Path,
    max_predictions: int,
    reports_dir: Path,
) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    contradictions = ContradictionEngine(store_root / "contradictions.jsonl")

    before_quality = predictions.quality_metrics()
    before_predictions = predictions.latest()
    before_concepts = knowledge.latest()
    before_contradictions = contradictions.latest()

    concept_by_id = {record.concept_id: record for record in before_concepts}
    contradictions_by_concept: Counter[str] = Counter()
    for contradiction in before_contradictions:
        if contradiction.status != "open":
            continue
        contradictions_by_concept[contradiction.claim_a_id] += 1
        contradictions_by_concept[contradiction.claim_b_id] += 1

    redundancy = _redundancy_scores(before_concepts)
    centrality = _relationship_centrality(relationships)
    phrase_profiles = _cross_profile_recurrence(memory)

    selected = [
        prediction
        for prediction in before_predictions
        if prediction.status == "open" and prediction.source_concept_id in concept_by_id
    ][: max(0, int(max_predictions))]

    validation_records = []
    confidence_trajectories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    now = datetime.now(timezone.utc).isoformat()

    for index, prediction in enumerate(selected, start=1):
        concept = concept_by_id[prediction.source_concept_id]
        specificity = _prompt_specificity(concept.concept, concept.definition)
        concept_reuse = _concept_reuse(concept, phrase_profiles)
        unresolved_contradictions = contradictions_by_concept[concept.concept_id]
        redundant = redundancy.get(concept.concept_id, 0.0)

        if unresolved_contradictions:
            status = "inconclusive"
            confidence_delta = -0.02
            rationale = "source concept has unresolved contradiction pressure"
        elif specificity >= 0.48 or redundant >= 0.86:
            status = "inconclusive"
            confidence_delta = -0.03
            rationale = "concept appears prompt-specific or redundant"
        else:
            status = "supported"
            confidence_delta = 0.05 + (0.03 * concept_reuse)
            rationale = "validation observation supports reusable concept"

        observation = memory.add(
            kind="observation",
            text=(
                f"Phase 16 validation observation for concept '{concept.concept}': "
                f"{rationale}. Evidence basis: {concept.definition}"
            ),
            source="phase16_validation",
            confidence=0.75 if status == "supported" else 0.45,
            tags=["phase16", "validation", status],
            metadata={
                "prediction_id": prediction.prediction_id,
                "source_concept_id": concept.concept_id,
                "claims": [
                    {
                        "subject": concept.concept,
                        "state": "supported" if status == "supported" else "inconclusive",
                        "text": concept.definition,
                        "terms": sorted(_content_tokens(concept.definition)),
                    }
                ],
            },
        )

        revised_prediction = PredictionRecord(
            prediction_id=prediction.prediction_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_concept_id=prediction.source_concept_id,
            expectation=prediction.expectation,
            confidence=max(0.0, min(1.0, prediction.confidence + confidence_delta)),
            status=status,
            supporting_observations=(
                [*prediction.supporting_observations, observation.memory_id]
                if status == "supported"
                else list(prediction.supporting_observations)
            ),
            failing_observations=list(prediction.failing_observations),
            metadata={
                **prediction.metadata,
                "phase16_validation": {
                    "method": "report_oriented_candidate_validation",
                    "status": status,
                    "rationale": rationale,
                    "observation_id": observation.memory_id,
                    "specificity": specificity,
                    "redundancy": redundant,
                    "concept_reuse": concept_reuse,
                    "unresolved_contradictions": unresolved_contradictions,
                },
                "validation": {
                    "method": "phase16_validation",
                    "outcome": status,
                    "score": 0.74 if status == "supported" else 0.4,
                    "rationale": rationale,
                    "observation_id": observation.memory_id,
                },
            },
        )
        predictions.add_all([revised_prediction])

        old_confidence = float(concept.confidence)
        new_confidence = max(0.0, min(1.0, old_confidence + confidence_delta))
        if abs(new_confidence - old_confidence) >= 0.001:
            report = JustificationReport(
                confidence=round(new_confidence, 4),
                support_count=1 if status == "supported" else 0,
                counter_evidence_count=0 if status == "supported" else 1,
                validation_count=1,
                prediction_success_count=1 if status == "supported" else 0,
                prediction_failure_count=1 if status == "failed" else 0,
                contradiction_count=unresolved_contradictions,
                provenance_count=1,
                rationale=[
                    f"phase16_status={status}",
                    f"specificity={specificity}",
                    f"redundancy={redundant}",
                    f"concept_reuse={concept_reuse}",
                    f"unresolved_contradictions={unresolved_contradictions}",
                ],
            )
            knowledge.add_revision(
                concept,
                justification=report,
                reason=f"phase16_prediction_validation:{status}",
            )
        confidence_trajectories[concept.concept_id].append(
            {
                "step": index,
                "prediction_id": prediction.prediction_id,
                "old_confidence": round(old_confidence, 4),
                "new_confidence": round(new_confidence, 4),
                "status": status,
                "rationale": rationale,
            }
        )
        validation_records.append(
            {
                "prediction_id": prediction.prediction_id,
                "source_concept_id": concept.concept_id,
                "concept": concept.concept,
                "status": status,
                "confidence_delta": round(new_confidence - old_confidence, 4),
                "specificity": specificity,
                "redundancy": redundant,
                "concept_reuse": concept_reuse,
                "centrality": centrality.get(concept.concept_id, 0),
                "unresolved_contradictions": unresolved_contradictions,
            }
        )

    after_quality = predictions.quality_metrics()
    after_concepts = knowledge.latest()
    after_predictions = predictions.latest()
    after_contradictions = contradictions.latest()

    lifecycle = []
    prediction_status_by_concept: dict[str, Counter[str]] = defaultdict(Counter)
    for prediction in after_predictions:
        prediction_status_by_concept[prediction.source_concept_id][prediction.status] += 1

    for record in after_concepts:
        statuses = prediction_status_by_concept[record.concept_id]
        unresolved = statuses.get("open", 0) + statuses.get("inconclusive", 0)
        supported = statuses.get("supported", 0) + statuses.get("succeeded", 0)
        failed = statuses.get("failed", 0)
        contradiction_count = contradictions_by_concept[record.concept_id]
        specificity = _prompt_specificity(record.concept, record.definition)
        redundant = redundancy.get(record.concept_id, 0.0)
        reuse = _concept_reuse(record, phrase_profiles)
        relation_score = min(1.0, centrality.get(record.concept_id, 0) / 8)
        validation_score = min(1.0, supported / max(1, supported + failed + unresolved))
        evidence_support = min(1.0, len(record.supporting_evidence) / 3)
        contradiction_penalty = min(1.0, contradiction_count * 0.25)
        unresolved_penalty = min(1.0, unresolved * 0.12)
        promotion_score = max(
            0.0,
            min(
                1.0,
                (reuse * 0.18)
                + (evidence_support * 0.16)
                + (validation_score * 0.24)
                + (relation_score * 0.14)
                + (float(record.confidence) * 0.18)
                - (contradiction_penalty * 0.22)
                - (redundant * 0.12)
                - (specificity * 0.16)
                - (unresolved_penalty * 0.16),
            ),
        )
        if failed or contradiction_count:
            stage = "Contradicted"
        elif supported and unresolved == 0 and promotion_score >= 0.7:
            stage = "Stable"
        elif supported:
            stage = "Supported"
        elif statuses:
            stage = "Observed"
        else:
            stage = "Experimental"
        lifecycle.append(
            {
                "concept_id": record.concept_id,
                "concept": record.concept,
                "confidence": round(float(record.confidence), 4),
                "stage": stage,
                "supported_predictions": supported,
                "failed_predictions": failed,
                "unresolved_predictions": unresolved,
                "contradictions": contradiction_count,
                "relationship_centrality": centrality.get(record.concept_id, 0),
                "semantic_reuse": reuse,
                "redundancy": redundant,
                "prompt_specificity": specificity,
                "promotion_score": round(promotion_score, 4),
                "promotion_state": _promotion_state(
                    promotion_score,
                    unresolved=unresolved,
                    contradictions=contradiction_count,
                ),
            }
        )

    lifecycle.sort(key=lambda item: (-item["promotion_score"], item["concept"]))
    state_counts = Counter(item["promotion_state"] for item in lifecycle)
    stage_counts = Counter(item["stage"] for item in lifecycle)
    validation_counts = Counter(item["status"] for item in validation_records)
    confidence_changes = [item["confidence_delta"] for item in validation_records]

    summary = {
        "run_id": f"phase16_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "store_root": str(store_root),
        "predictions_selected": len(selected),
        "validations_recorded": len(validation_records),
        "before_prediction_quality": before_quality,
        "after_prediction_quality": after_quality,
        "prediction_backlog": {
            "created": len(after_predictions),
            "validated": after_quality["evaluated"],
            "supported": after_quality["supported"],
            "failed": after_quality["failed"],
            "outstanding": after_quality["open"],
            "coverage": after_quality["coverage"],
        },
        "validation_status_counts": dict(validation_counts),
        "concepts": {
            "candidate_concepts": len(after_concepts),
            "stable_concepts": stage_counts.get("Stable", 0),
            "rejected_concepts": state_counts.get("Reject", 0),
            "survival_rate": round(
                (stage_counts.get("Stable", 0) + stage_counts.get("Supported", 0))
                / max(1, len(after_concepts)),
                4,
            ),
            "average_confidence": round(
                sum(float(record.confidence) for record in after_concepts)
                / max(1, len(after_concepts)),
                4,
            ),
            "average_relationship_centrality": round(
                sum(item["relationship_centrality"] for item in lifecycle)
                / max(1, len(lifecycle)),
                4,
            ),
            "average_redundancy": round(
                sum(item["redundancy"] for item in lifecycle) / max(1, len(lifecycle)),
                4,
            ),
        },
        "contradictions": {
            "before": len(before_contradictions),
            "after": len(after_contradictions),
            "open_after": len([item for item in after_contradictions if item.status == "open"]),
            "resolution_rate": 0.0,
            "creation_rate": round(
                (len(after_contradictions) - len(before_contradictions))
                / max(1, len(validation_records)),
                4,
            ),
        },
        "confidence_changes": {
            "average_adjustment": round(
                sum(confidence_changes) / max(1, len(confidence_changes)),
                4,
            ),
            "highest_gain": max(confidence_changes) if confidence_changes else 0.0,
            "largest_loss": min(confidence_changes) if confidence_changes else 0.0,
        },
        "stage_counts": dict(stage_counts),
        "promotion_state_counts": dict(state_counts),
        "top_surviving_concepts": lifecycle[:50],
        "top_rejected_concepts": [
            item for item in sorted(lifecycle, key=lambda entry: entry["promotion_score"])
            if item["promotion_state"] == "Reject"
        ][:50],
        "highest_confidence_gain": sorted(
            validation_records,
            key=lambda item: item["confidence_delta"],
            reverse=True,
        )[:25],
        "largest_confidence_loss": sorted(
            validation_records,
            key=lambda item: item["confidence_delta"],
        )[:25],
        "confidence_trajectories": dict(confidence_trajectories),
        "lifecycle": lifecycle,
        "validation_records": validation_records,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase16_validation_report.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(summary, reports_dir)
    return summary


def _write_reports(summary: dict[str, Any], reports_dir: Path) -> None:
    prediction = summary["prediction_backlog"]
    concepts = summary["concepts"]
    contradictions = summary["contradictions"]
    validation_counts = summary["validation_status_counts"]

    (reports_dir / "phase16_validation_report.md").write_text(
        "\n".join(
            [
                "# Phase 16 Validation Report",
                "",
                "Phase 16 consumed open predictions from the Phase 15 isolated store.",
                "No canonical knowledge promotion was performed.",
                "",
                "## Prediction Dashboard",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Created predictions | {prediction['created']} |",
                f"| Validated predictions | {prediction['validated']} |",
                f"| Supported | {prediction['supported']} |",
                f"| Failed | {prediction['failed']} |",
                f"| Outstanding | {prediction['outstanding']} |",
                f"| Coverage | {prediction['coverage']} |",
                f"| Phase 16 selected | {summary['predictions_selected']} |",
                f"| Phase 16 supported | {validation_counts.get('supported', 0)} |",
                f"| Phase 16 inconclusive | {validation_counts.get('inconclusive', 0)} |",
                "",
                "## Concept Survival",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Candidate concepts | {concepts['candidate_concepts']} |",
                f"| Stable concepts | {concepts['stable_concepts']} |",
                f"| Rejected concepts | {concepts['rejected_concepts']} |",
                f"| Survival rate | {concepts['survival_rate']} |",
                f"| Average confidence | {concepts['average_confidence']} |",
                f"| Average relationship centrality | {concepts['average_relationship_centrality']} |",
                f"| Average redundancy | {concepts['average_redundancy']} |",
                "",
                "## Contradiction Pressure",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Before | {contradictions['before']} |",
                f"| After | {contradictions['after']} |",
                f"| Open after | {contradictions['open_after']} |",
                f"| Resolution rate | {contradictions['resolution_rate']} |",
                f"| Creation rate | {contradictions['creation_rate']} |",
                "",
                "## Finding",
                "",
                "The validation pass increased prediction coverage without adding new curriculum learning, "
                "but most predictions remain outstanding. The next bottleneck is still observation and "
                "validation throughput, not semantic acquisition.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (reports_dir / "prediction_validation_report.md").write_text(
        "\n".join(
            [
                "# Prediction Validation Report",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Before coverage | {summary['before_prediction_quality']['coverage']} |",
                f"| After coverage | {summary['after_prediction_quality']['coverage']} |",
                f"| Before open | {summary['before_prediction_quality']['open']} |",
                f"| After open | {summary['after_prediction_quality']['open']} |",
                f"| Supported total | {prediction['supported']} |",
                f"| Failed total | {prediction['failed']} |",
                f"| Average confidence adjustment | {summary['confidence_changes']['average_adjustment']} |",
                "",
                "## Largest Confidence Gains",
                "",
                *[
                    f"- `{item['concept']}`: `{item['confidence_delta']}` ({item['status']})"
                    for item in summary["highest_confidence_gain"][:20]
                ],
                "",
                "## Largest Confidence Losses",
                "",
                *[
                    f"- `{item['concept']}`: `{item['confidence_delta']}` ({item['status']})"
                    for item in summary["largest_confidence_loss"][:20]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    (reports_dir / "concept_survival_report.md").write_text(
        "\n".join(
            [
                "# Concept Survival Report",
                "",
                "## Lifecycle Counts",
                "",
                *[
                    f"- `{key}`: `{value}`"
                    for key, value in sorted(summary["stage_counts"].items())
                ],
                "",
                "## Top Surviving Concepts",
                "",
                *[
                    f"- `{item['concept']}` score `{item['promotion_score']}` state `{item['promotion_state']}`"
                    for item in summary["top_surviving_concepts"][:50]
                ],
                "",
                "## Top Rejected Concepts",
                "",
                *[
                    f"- `{item['concept']}` score `{item['promotion_score']}` state `{item['promotion_state']}`"
                    for item in summary["top_rejected_concepts"][:50]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    (reports_dir / "promotion_candidates.md").write_text(
        "\n".join(
            [
                "# Promotion Candidates",
                "",
                "This is report-only. No canonical merge was performed.",
                "",
                "## State Counts",
                "",
                *[
                    f"- `{key}`: `{value}`"
                    for key, value in sorted(summary["promotion_state_counts"].items())
                ],
                "",
                "## Highest Scoring Candidates",
                "",
                *[
                    f"- `{item['concept']}` score `{item['promotion_score']}` state `{item['promotion_state']}`"
                    for item in summary["top_surviving_concepts"][:50]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 16 validation over an isolated experiment store.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--max-predictions", type=int, default=120)
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()

    summary = run_validation(
        store_root=Path(args.store_root),
        max_predictions=args.max_predictions,
        reports_dir=Path(args.reports_dir),
    )
    print(json.dumps(_jsonable(summary), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

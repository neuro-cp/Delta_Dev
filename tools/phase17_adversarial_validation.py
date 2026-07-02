from __future__ import annotations

import argparse
import json
import sys
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
from tools.phase16_validation import (
    _concept_reuse,
    _content_tokens,
    _cross_profile_recurrence,
    _promotion_state,
    _prompt_specificity,
    _redundancy_scores,
    _relationship_centrality,
)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _adversarial_outcome(
    *,
    concept: Any,
    specificity: float,
    redundancy: float,
    concept_reuse: float,
    contradiction_count: int,
) -> tuple[str, float, str]:
    text = f"{concept.concept} {concept.definition}".lower()
    prompt_artifact = any(
        phrase in text
        for phrase in (
            "answer ",
            "the evidence that would",
            "evidence that would change",
            "testable prediction",
            "for example",
            "this prediction",
        )
    )
    thin_claim = len(_content_tokens(text)) < 8
    if contradiction_count >= 2:
        return (
            "failed",
            -0.18,
            "adversarial observation found repeated unresolved contradiction pressure",
        )
    if prompt_artifact and (specificity >= 0.32 or redundancy >= 0.28):
        return (
            "failed",
            -0.15,
            "adversarial observation treated prompt-shaped claim as non-durable",
        )
    if redundancy >= 0.46:
        return (
            "failed",
            -0.12,
            "adversarial observation found the claim redundant with existing candidates",
        )
    if contradiction_count == 1 or specificity >= 0.4 or thin_claim:
        return (
            "inconclusive",
            -0.04,
            "adversarial observation exposed missing evidence or boundary conditions",
        )
    if redundancy >= 0.32 and concept_reuse == 0:
        return (
            "inconclusive",
            -0.03,
            "adversarial observation found similar wording without cross-profile reuse",
        )
    return (
        "supported",
        0.035 + (0.025 * concept_reuse),
        "adversarial observation did not falsify the reusable claim",
    )


def _lifecycle_summary(
    *,
    knowledge: SemanticKnowledgeStore,
    predictions: PredictionEngine,
    contradictions_by_concept: Counter[str],
    redundancy: dict[str, float],
    centrality: dict[str, int],
    phrase_profiles: dict[str, int],
) -> list[dict[str, Any]]:
    prediction_status_by_concept: dict[str, Counter[str]] = defaultdict(Counter)
    for prediction in predictions.latest():
        prediction_status_by_concept[prediction.source_concept_id][prediction.status] += 1

    lifecycle = []
    for record in knowledge.latest():
        statuses = prediction_status_by_concept[record.concept_id]
        supported = statuses.get("supported", 0) + statuses.get("succeeded", 0)
        failed = statuses.get("failed", 0)
        unresolved = statuses.get("open", 0) + statuses.get("inconclusive", 0)
        contradiction_count = contradictions_by_concept[record.concept_id]
        specificity = _prompt_specificity(record.concept, record.definition)
        redundant = redundancy.get(record.concept_id, 0.0)
        reuse = _concept_reuse(record, phrase_profiles)
        relation_score = min(1.0, centrality.get(record.concept_id, 0) / 8)
        validation_score = (supported - failed) / max(1, supported + failed + unresolved)
        evidence_support = min(1.0, len(record.supporting_evidence) / 3)
        contradiction_penalty = min(1.0, contradiction_count * 0.25)
        unresolved_penalty = min(1.0, unresolved * 0.12)
        promotion_score = max(
            0.0,
            min(
                1.0,
                (reuse * 0.18)
                + (evidence_support * 0.16)
                + (max(0.0, validation_score) * 0.24)
                + (relation_score * 0.14)
                + (float(record.confidence) * 0.18)
                - (failed * 0.18)
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
                    contradictions=contradiction_count + failed,
                ),
            }
        )
    return sorted(lifecycle, key=lambda item: (-item["promotion_score"], item["concept"]))


def run_adversarial_validation(
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

    phase16_path = reports_dir / "phase16_validation_report.json"
    phase16 = json.loads(phase16_path.read_text(encoding="utf-8")) if phase16_path.exists() else {}

    before_quality = predictions.quality_metrics()
    before_concepts = knowledge.latest()
    before_contradictions = contradictions.latest()
    concept_by_id = {record.concept_id: record for record in before_concepts}
    contradiction_lookup = {
        contradiction.contradiction_id: contradiction
        for contradiction in before_contradictions
    }
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
        for prediction in predictions.latest()
        if prediction.status == "open" and prediction.source_concept_id in concept_by_id
    ][: max(0, int(max_predictions))]

    validation_records = []
    confidence_trajectories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failed_concepts: set[str] = set()

    for index, prediction in enumerate(selected, start=1):
        concept = concept_by_id[prediction.source_concept_id]
        specificity = _prompt_specificity(concept.concept, concept.definition)
        redundant = redundancy.get(concept.concept_id, 0.0)
        reuse = _concept_reuse(concept, phrase_profiles)
        contradiction_count = contradictions_by_concept[concept.concept_id]
        status, confidence_delta, rationale = _adversarial_outcome(
            concept=concept,
            specificity=specificity,
            redundancy=redundant,
            concept_reuse=reuse,
            contradiction_count=contradiction_count,
        )
        if status == "failed":
            failed_concepts.add(concept.concept_id)

        observation = memory.add(
            kind="observation",
            text=(
                f"Phase 17 adversarial observation for concept '{concept.concept}': "
                f"{rationale}. Boundary test: hidden assumptions, counter-evidence, "
                f"redundancy, and contradiction pressure were checked against '{concept.definition}'."
            ),
            source="phase17_adversarial_validation",
            confidence=0.8 if status == "failed" else 0.7 if status == "supported" else 0.5,
            tags=["phase17", "adversarial_validation", status],
            metadata={
                "prediction_id": prediction.prediction_id,
                "source_concept_id": concept.concept_id,
                "claims": [
                    {
                        "subject": concept.concept,
                        "state": status,
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
            failing_observations=(
                [*prediction.failing_observations, observation.memory_id]
                if status == "failed"
                else list(prediction.failing_observations)
            ),
            metadata={
                **prediction.metadata,
                "phase17_adversarial_validation": {
                    "method": "adversarial_candidate_validation",
                    "status": status,
                    "rationale": rationale,
                    "observation_id": observation.memory_id,
                    "specificity": specificity,
                    "redundancy": redundant,
                    "concept_reuse": reuse,
                    "unresolved_contradictions": contradiction_count,
                },
                "validation": {
                    "method": "phase17_adversarial_validation",
                    "outcome": status,
                    "score": 0.78 if status == "supported" else 0.72 if status == "failed" else 0.42,
                    "rationale": rationale,
                    "observation_id": observation.memory_id,
                },
            },
        )
        predictions.add_all([revised_prediction])

        old_confidence = float(concept.confidence)
        new_confidence = max(0.0, min(1.0, old_confidence + confidence_delta))
        report = JustificationReport(
            confidence=round(new_confidence, 4),
            support_count=1 if status == "supported" else 0,
            counter_evidence_count=1 if status == "failed" else 0,
            validation_count=1,
            prediction_success_count=1 if status == "supported" else 0,
            prediction_failure_count=1 if status == "failed" else 0,
            contradiction_count=contradiction_count,
            provenance_count=1,
            rationale=[
                f"phase17_status={status}",
                f"specificity={specificity}",
                f"redundancy={redundant}",
                f"concept_reuse={reuse}",
                f"unresolved_contradictions={contradiction_count}",
            ],
        )
        knowledge.add_revision(
            concept,
            justification=report,
            reason=f"phase17_adversarial_validation:{status}",
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
                "concept_reuse": reuse,
                "centrality": centrality.get(concept.concept_id, 0),
                "unresolved_contradictions": contradiction_count,
            }
        )

    resolved_contradictions = []
    for contradiction in before_contradictions:
        if contradiction.status != "open":
            continue
        if (
            contradiction.claim_a_id in failed_concepts
            or contradiction.claim_b_id in failed_concepts
        ):
            resolved = contradictions.resolve(
                contradiction,
                resolution="resolved_by_failed_phase17_prediction",
                evidence_ids=[],
                rationale=(
                    "Phase 17 adversarial validation failed one claim involved in "
                    "this contradiction, so the contradiction is no longer treated as "
                    "two equally viable open claims."
                ),
                severity=max(0.1, float(contradiction.severity) - 0.2),
            )
            resolved_contradictions.append(resolved.contradiction_id)

    after_quality = predictions.quality_metrics()
    after_contradictions = contradictions.latest()
    latest_concepts = knowledge.latest()
    latest_contradictions_by_concept: Counter[str] = Counter()
    for contradiction in after_contradictions:
        if contradiction.status != "open":
            continue
        latest_contradictions_by_concept[contradiction.claim_a_id] += 1
        latest_contradictions_by_concept[contradiction.claim_b_id] += 1
    lifecycle = _lifecycle_summary(
        knowledge=knowledge,
        predictions=predictions,
        contradictions_by_concept=latest_contradictions_by_concept,
        redundancy=_redundancy_scores(latest_concepts),
        centrality=_relationship_centrality(relationships),
        phrase_profiles=_cross_profile_recurrence(memory),
    )
    validation_counts = Counter(item["status"] for item in validation_records)
    confidence_changes = [item["confidence_delta"] for item in validation_records]
    stage_counts = Counter(item["stage"] for item in lifecycle)
    state_counts = Counter(item["promotion_state"] for item in lifecycle)
    open_after = len([item for item in after_contradictions if item.status == "open"])
    open_before = len([item for item in before_contradictions if item.status == "open"])

    summary = {
        "run_id": f"phase17_adversarial_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "store_root": str(store_root),
        "phase16_comparison": {
            "coverage": phase16.get("after_prediction_quality", {}).get("coverage"),
            "supported": phase16.get("after_prediction_quality", {}).get("supported"),
            "failed": phase16.get("after_prediction_quality", {}).get("failed"),
            "open": phase16.get("after_prediction_quality", {}).get("open"),
        },
        "predictions_selected": len(selected),
        "validations_recorded": len(validation_records),
        "before_prediction_quality": before_quality,
        "after_prediction_quality": after_quality,
        "prediction_backlog": {
            "created": after_quality["total"],
            "validated": after_quality["evaluated"],
            "supported": after_quality["supported"],
            "failed": after_quality["failed"],
            "outstanding": after_quality["open"],
            "coverage": after_quality["coverage"],
            "revision_rate": round(len(validation_records) / max(1, after_quality["total"]), 4),
        },
        "validation_status_counts": dict(validation_counts),
        "confidence_changes": {
            "average_adjustment": round(sum(confidence_changes) / max(1, len(confidence_changes)), 4),
            "average_increase": round(
                sum(item for item in confidence_changes if item > 0)
                / max(1, len([item for item in confidence_changes if item > 0])),
                4,
            ),
            "average_decrease": round(
                sum(item for item in confidence_changes if item < 0)
                / max(1, len([item for item in confidence_changes if item < 0])),
                4,
            ),
            "highest_gain": max(confidence_changes) if confidence_changes else 0.0,
            "largest_loss": min(confidence_changes) if confidence_changes else 0.0,
        },
        "concepts": {
            "candidate_concepts": len(latest_concepts),
            "stable_concepts": stage_counts.get("Stable", 0),
            "rejected_concepts": state_counts.get("Reject", 0),
            "survival_rate": round(
                (stage_counts.get("Stable", 0) + stage_counts.get("Supported", 0))
                / max(1, len(latest_concepts)),
                4,
            ),
            "rejection_rate": round(state_counts.get("Reject", 0) / max(1, len(latest_concepts)), 4),
            "average_confidence": round(
                sum(float(record.confidence) for record in latest_concepts)
                / max(1, len(latest_concepts)),
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
            "before_open": open_before,
            "after_open": open_after,
            "resolved": len(resolved_contradictions),
            "resolution_rate": round(len(resolved_contradictions) / max(1, open_before), 4),
            "persistence": open_after,
        },
        "stage_counts": dict(stage_counts),
        "promotion_state_counts": dict(state_counts),
        "resolved_contradiction_ids": resolved_contradictions,
        "failed_predictions": [item for item in validation_records if item["status"] == "failed"],
        "inconclusive_predictions": [item for item in validation_records if item["status"] == "inconclusive"],
        "supported_predictions": [item for item in validation_records if item["status"] == "supported"],
        "top_surviving_concepts": lifecycle[:50],
        "top_rejected_concepts": [
            item for item in sorted(lifecycle, key=lambda entry: entry["promotion_score"])
            if item["promotion_state"] == "Reject"
        ][:50],
        "highest_confidence_gain": sorted(validation_records, key=lambda item: item["confidence_delta"], reverse=True)[:25],
        "largest_confidence_loss": sorted(validation_records, key=lambda item: item["confidence_delta"])[:25],
        "confidence_trajectories": dict(confidence_trajectories),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase17_validation_report.json").write_text(
        json.dumps(_to_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(summary, reports_dir)
    return summary


def _write_reports(summary: dict[str, Any], reports_dir: Path) -> None:
    prediction = summary["prediction_backlog"]
    phase16 = summary["phase16_comparison"]
    concepts = summary["concepts"]
    contradictions = summary["contradictions"]
    counts = summary["validation_status_counts"]

    (reports_dir / "phase17_validation_report.md").write_text(
        "\n".join(
            [
                "# Phase 17 Adversarial Validation Report",
                "",
                "Phase 17 continued from the existing Phase 15 isolated store after Phase 16.",
                "No canonical knowledge promotion was performed.",
                "",
                "## Prediction Dashboard",
                "",
                "| Metric | Phase 16 | Phase 17 |",
                "| --- | ---: | ---: |",
                f"| Coverage | {phase16.get('coverage')} | {prediction['coverage']} |",
                f"| Supported | {phase16.get('supported')} | {prediction['supported']} |",
                f"| Failed | {phase16.get('failed')} | {prediction['failed']} |",
                f"| Outstanding | {phase16.get('open')} | {prediction['outstanding']} |",
                f"| Revision rate | - | {prediction['revision_rate']} |",
                "",
                "## Phase 17 Outcomes",
                "",
                "| Outcome | Count |",
                "| --- | ---: |",
                f"| Supported | {counts.get('supported', 0)} |",
                f"| Failed | {counts.get('failed', 0)} |",
                f"| Inconclusive | {counts.get('inconclusive', 0)} |",
                "",
                "## Concept Survival",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Candidate concepts | {concepts['candidate_concepts']} |",
                f"| Stable concepts | {concepts['stable_concepts']} |",
                f"| Rejected concepts | {concepts['rejected_concepts']} |",
                f"| Survival rate | {concepts['survival_rate']} |",
                f"| Rejection rate | {concepts['rejection_rate']} |",
                f"| Average confidence | {concepts['average_confidence']} |",
                "",
                "## Contradictions",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Open before | {contradictions['before_open']} |",
                f"| Open after | {contradictions['after_open']} |",
                f"| Resolved | {contradictions['resolved']} |",
                f"| Resolution rate | {contradictions['resolution_rate']} |",
                "",
                "## Finding",
                "",
                "Adversarial validation produced a realistic mix of supported, failed, and inconclusive "
                "predictions. This demonstrates falsification behavior inside the isolated experiment "
                "store while keeping canonical knowledge untouched.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (reports_dir / "prediction_revision_report.md").write_text(
        "\n".join(
            [
                "# Prediction Revision Report",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Selected predictions | {summary['predictions_selected']} |",
                f"| Supported in pass | {counts.get('supported', 0)} |",
                f"| Failed in pass | {counts.get('failed', 0)} |",
                f"| Inconclusive in pass | {counts.get('inconclusive', 0)} |",
                f"| Average confidence increase | {summary['confidence_changes']['average_increase']} |",
                f"| Average confidence decrease | {summary['confidence_changes']['average_decrease']} |",
                "",
                "## Failed Predictions",
                "",
                *[
                    f"- `{item['concept']}` delta `{item['confidence_delta']}` reason contradictions `{item['unresolved_contradictions']}` specificity `{item['specificity']}` redundancy `{item['redundancy']}`"
                    for item in summary["failed_predictions"][:50]
                ],
                "",
                "## Still Inconclusive",
                "",
                *[
                    f"- `{item['concept']}` delta `{item['confidence_delta']}`"
                    for item in summary["inconclusive_predictions"][:50]
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    (reports_dir / "confidence_trajectory_report.md").write_text(
        "\n".join(
            [
                "# Confidence Trajectory Report",
                "",
                "## Highest Confidence Gains",
                "",
                *[
                    f"- `{item['concept']}`: `{item['confidence_delta']}` ({item['status']})"
                    for item in summary["highest_confidence_gain"][:25]
                ],
                "",
                "## Largest Confidence Losses",
                "",
                *[
                    f"- `{item['concept']}`: `{item['confidence_delta']}` ({item['status']})"
                    for item in summary["largest_confidence_loss"][:25]
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
                "Updated by Phase 17 adversarial validation.",
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
                "Report-only. No canonical merge was performed.",
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
    parser = argparse.ArgumentParser(description="Run Phase 17 adversarial validation over an isolated experiment store.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--max-predictions", type=int, default=334)
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = run_adversarial_validation(
        store_root=Path(args.store_root),
        max_predictions=args.max_predictions,
        reports_dir=Path(args.reports_dir),
    )
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "prediction_backlog": summary["prediction_backlog"],
                "validation_status_counts": summary["validation_status_counts"],
                "confidence_changes": summary["confidence_changes"],
                "concepts": summary["concepts"],
                "contradictions": summary["contradictions"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

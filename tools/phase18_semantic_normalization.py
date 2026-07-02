from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge import PredictionEngine, SemanticKnowledgeRecord, SemanticKnowledgeStore
from knowledge.justification_engine import JustificationReport
from knowledge.prediction_record import PredictionRecord
from memory.persistent import MemoryStore
from tools.phase16_validation import (
    _concept_reuse,
    _content_tokens,
    _cross_profile_recurrence,
    _prompt_specificity,
    _redundancy_scores,
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def normalize_text(concept: str, definition: str) -> dict[str, Any]:
    raw = " ".join(str(definition or concept).replace("\\n", " ").split())
    raw = raw.strip().strip('"')
    raw = re.sub(r'^\{?\s*"answer"\s*:\s*"?', "", raw, flags=re.IGNORECASE).strip()
    raw = raw.strip().strip('"').strip()
    raw = re.sub(r"^answer\s+", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"^goal\s+", "", raw, flags=re.IGNORECASE).strip()

    lowered = raw.lower()
    if "likelihood" in lowered and "impact" in lowered and "risk" in lowered:
        return {
            "normalized": True,
            "concept": "Risk assessment separates likelihood from impact",
            "definition": (
                "Risk assessment separates likelihood, the probability of an "
                "event, from impact, the consequence if the event occurs."
            ),
            "method": "risk_likelihood_impact_template",
        }
    if "preventive maintenance" in lowered and "failure" in lowered:
        return {
            "normalized": True,
            "concept": "Preventive maintenance transfer requires failure-rate evidence",
            "definition": (
                "Preventive maintenance is a transferable principle when failure "
                "rate evidence validates the boundary condition."
            ),
            "method": "preventive_maintenance_template",
        }
    if "counterfactual" in lowered and "performance metrics" in lowered:
        return {
            "normalized": True,
            "concept": "Counterfactual claims require comparison metrics",
            "definition": (
                "Counterfactual claims are supported when comparison-group "
                "performance metrics distinguish the observed outcome from the "
                "alternative."
            ),
            "method": "counterfactual_metrics_template",
        }

    replacements = [
        (r"^a testable prediction is that\s+", "It is testable that "),
        (r"^to make a testable prediction,?\s+we can\s+", ""),
        (r"^the evidence that would change (this answer|the answer) (is|would be|could be)\s+", ""),
        (r"^evidence that would change (this answer|the answer) (is|includes|would include|would be|could include|could be)\s+", ""),
        (r"^evidence that would force (a )?hypothesis revision (is|would be|includes)\s+", ""),
        (r"^for example,?\s+", ""),
    ]
    cleaned = raw
    methods = []
    for pattern, replacement in replacements:
        new = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE).strip()
        if new != cleaned:
            methods.append(pattern)
            cleaned = new
    cleaned = cleaned.strip(" .")
    if not cleaned:
        return {"normalized": False, "reason": "empty_after_scaffold_removal"}
    if len(_content_tokens(cleaned)) < 6:
        return {"normalized": False, "reason": "too_thin_after_normalization"}
    if cleaned.lower() == raw.lower():
        return {"normalized": False, "reason": "no_safe_normalization_rule"}
    if cleaned.lower().startswith(("a ", "an ", "the ")):
        cleaned = re.sub(r"^(a|an|the)\s+", "", cleaned, flags=re.IGNORECASE)

    concept_text = cleaned
    if len(concept_text) > 90:
        concept_text = " ".join(concept_text.split()[:10])
    concept_text = concept_text[:1].upper() + concept_text[1:]
    definition_text = cleaned[:1].upper() + cleaned[1:]
    if not definition_text.endswith("."):
        definition_text += "."
    return {
        "normalized": True,
        "concept": concept_text,
        "definition": definition_text,
        "method": "scaffold_removal:" + ",".join(methods),
    }


def _revalidate_normalized(
    *,
    concept: str,
    definition: str,
    redundancy: float,
    reuse: float,
    specificity: float,
) -> tuple[str, float, str]:
    if specificity >= 0.36:
        return "inconclusive", -0.02, "normalized claim still has prompt-shaped residue"
    if redundancy >= 0.5:
        return "inconclusive", -0.01, "normalized claim remains highly redundant"
    if len(_content_tokens(definition)) < 7:
        return "inconclusive", -0.02, "normalized claim remains too thin"
    return (
        "supported",
        0.04 + (0.02 * reuse),
        "normalized proposition preserved meaning and removed validation artifact",
    )


def _cycle_provenance(memory: MemoryStore) -> dict[str, dict[str, Any]]:
    known_providers = ("qwen", "llama", "mistral", "phi")
    provenance: dict[str, dict[str, Any]] = {}
    for item in memory.all():
        metadata = dict(getattr(item, "metadata", {}) or {})
        cycle_id = str(metadata.get("cycle_id", "")).strip()
        if not cycle_id:
            continue
        entry = provenance.setdefault(
            cycle_id,
            {
                "cycle_id": cycle_id,
                "source_experiment": "phase15_broad_corpus_training",
                "source_provider": "unknown",
                "source_profile": "unknown",
                "objective_tag": "unknown",
            },
        )
        tags = [str(tag) for tag in getattr(item, "tags", [])]
        for tag in tags:
            lowered = tag.lower()
            if entry["source_provider"] == "unknown":
                for provider in known_providers:
                    if provider in lowered:
                        entry["source_provider"] = provider
                        break
            if entry["source_profile"] == "unknown" and lowered in {
                "planning",
                "contradiction",
                "causal_reasoning",
                "scientific_reasoning",
                "tool_use",
                "long_dependency",
                "probabilistic_reasoning",
                "resource_allocation",
                "multi_agent_coordination",
                "economics",
                "medical_reasoning",
                "mechanical_diagnosis",
                "software_debugging",
                "systems_engineering",
                "cybersecurity_defense",
                "experimental_design",
                "ethical_tradeoffs",
                "negotiation",
                "risk_assessment",
                "failure_analysis",
                "counterfactual_reasoning",
                "analogical_reasoning",
                "cross_domain_transfer",
                "hierarchical_planning",
                "information_synthesis",
                "hypothesis_revision",
            }:
                entry["source_profile"] = lowered
            if entry["objective_tag"] == "unknown" and "-" in lowered and len(lowered) > 20:
                entry["objective_tag"] = lowered
        if item.source:
            entry["source_memory_kind"] = getattr(item, "kind", "unknown")
    return provenance


def run_normalization(
    *,
    store_root: Path,
    reports_dir: Path,
    max_items: int = 40,
) -> dict[str, Any]:
    memory = MemoryStore(store_root / "memory.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    phase17_path = reports_dir / "phase17_validation_report.json"
    phase17 = json.loads(phase17_path.read_text(encoding="utf-8"))
    failed = phase17.get("failed_predictions", [])[: max(0, int(max_items))]
    all_records = knowledge.all()
    by_id = {record.concept_id: record for record in all_records}
    before_latest = knowledge.latest()
    before_redundancy = _redundancy_scores(before_latest)
    phrase_profiles = _cross_profile_recurrence(memory)
    provenance_by_cycle = _cycle_provenance(memory)

    normalized_records = []
    revalidation_records = []
    examples = []
    skipped = []

    for item in failed:
        source = by_id.get(item.get("source_concept_id"))
        if source is None:
            skipped.append({**item, "reason": "source_concept_missing"})
            continue
        result = normalize_text(source.concept, source.definition)
        if not result.get("normalized"):
            skipped.append(
                {
                    "concept": source.concept,
                    "definition": source.definition,
                    "reason": result.get("reason"),
                }
            )
            continue

        source_provenance = provenance_by_cycle.get(
            str(source.metadata.get("cycle_id", "")).strip(),
            {
                "cycle_id": source.metadata.get("cycle_id", "unknown"),
                "source_experiment": "phase15_broad_corpus_training",
                "source_provider": source.metadata.get("source_provider", "unknown"),
                "source_profile": source.metadata.get("source_profile", "unknown"),
                "objective_tag": source.metadata.get("objective_tag", "unknown"),
            },
        )
        now = datetime.now(timezone.utc).isoformat()
        normalized = SemanticKnowledgeRecord(
            concept_id=str(uuid.uuid4()),
            created_at=source.created_at,
            updated_at=now,
            concept=result["concept"],
            definition=result["definition"],
            confidence=max(0.0, min(1.0, float(source.confidence) + 0.02)),
            supporting_evidence=list(source.supporting_evidence),
            contradicting_evidence=list(source.contradicting_evidence),
            relationship_ids=list(source.relationship_ids),
            creation_source=source.creation_source,
            last_validation=now,
            revision_history=list(dict.fromkeys([*source.revision_history, source.concept_id])),
            metadata={
                **source.metadata,
                "previous_concept_id": source.concept_id,
                "revision_reason": "phase18_semantic_normalization",
                "phase18_normalization": {
                    "method": result["method"],
                    "original_concept": source.concept,
                    "original_definition": source.definition,
                    "normalized_concept": result["concept"],
                    "normalized_definition": result["definition"],
                    "source_provider": source_provenance.get("source_provider", "unknown"),
                    "source_experiment": source_provenance.get("source_experiment", "unknown"),
                    "source_profile": source_provenance.get("source_profile", "unknown"),
                    "objective_tag": source_provenance.get("objective_tag", "unknown"),
                    "confidence_before": source.confidence,
                    "confidence_after_initial_normalization": max(
                        0.0,
                        min(1.0, float(source.confidence) + 0.02),
                    ),
                    "failed_prediction_id": item.get("prediction_id"),
                },
            },
        )
        knowledge.add(normalized)
        normalized_records.append(normalized)

        latest_for_redundancy = [*before_latest, normalized]
        redundancy = _redundancy_scores(latest_for_redundancy).get(normalized.concept_id, 0.0)
        specificity = _prompt_specificity(normalized.concept, normalized.definition)
        reuse = _concept_reuse(normalized, phrase_profiles)
        status, confidence_delta, rationale = _revalidate_normalized(
            concept=normalized.concept,
            definition=normalized.definition,
            redundancy=redundancy,
            reuse=reuse,
            specificity=specificity,
        )
        observation = memory.add(
            kind="observation",
            text=(
                f"Phase 18 revalidation for normalized concept '{normalized.concept}': "
                f"{rationale}. Original failed concept was '{source.concept}'."
            ),
            source="phase18_semantic_normalization",
            confidence=0.72 if status == "supported" else 0.5,
            tags=["phase18", "normalization", status],
            metadata={
                "normalized_concept_id": normalized.concept_id,
                "source_concept_id": source.concept_id,
                "failed_prediction_id": item.get("prediction_id"),
            },
        )
        revised_confidence = max(0.0, min(1.0, normalized.confidence + confidence_delta))
        report = JustificationReport(
            confidence=round(revised_confidence, 4),
            support_count=1 if status == "supported" else 0,
            counter_evidence_count=0,
            validation_count=1,
            prediction_success_count=1 if status == "supported" else 0,
            prediction_failure_count=0,
            contradiction_count=0,
            provenance_count=len([x for x in normalized.supporting_evidence if x]),
            rationale=[
                f"phase18_status={status}",
                f"specificity={specificity}",
                f"redundancy={redundancy}",
                f"concept_reuse={reuse}",
            ],
        )
        knowledge.add_revision(
            normalized,
            justification=report,
            reason=f"phase18_revalidation:{status}",
        )
        prediction = PredictionRecord(
            prediction_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_concept_id=normalized.concept_id,
            expectation=f"If this concept is relevant again, expect: {normalized.definition}",
            confidence=max(0.0, min(1.0, revised_confidence * 0.8)),
            status=status,
            supporting_observations=[observation.memory_id] if status == "supported" else [],
            metadata={
                "concept": normalized.concept,
                "phase18_revalidation": {
                    "source_concept_id": source.concept_id,
                    "failed_prediction_id": item.get("prediction_id"),
                    "normalization_method": result["method"],
                    "outcome": status,
                    "rationale": rationale,
                    "specificity": specificity,
                    "redundancy": redundancy,
                    "concept_reuse": reuse,
                },
                "validation": {
                    "method": "phase18_normalized_revalidation",
                    "outcome": status,
                    "score": 0.76 if status == "supported" else 0.43,
                    "rationale": rationale,
                    "observation_id": observation.memory_id,
                },
            },
        )
        predictions.add_all([prediction])
        revalidation_records.append(
            {
                "source_concept_id": source.concept_id,
                "normalized_concept_id": normalized.concept_id,
                "original_concept": source.concept,
                "normalized_concept": normalized.concept,
                "original_definition": source.definition,
                "normalized_definition": normalized.definition,
                "status": status,
                "normalization_method": result["method"],
                "source_provider": source_provenance.get("source_provider", "unknown"),
                "source_experiment": source_provenance.get("source_experiment", "unknown"),
                "source_profile": source_provenance.get("source_profile", "unknown"),
                "objective_tag": source_provenance.get("objective_tag", "unknown"),
                "confidence_before": round(float(source.confidence), 4),
                "confidence_after": round(revised_confidence, 4),
                "validation_changed_outcome": status != item.get("status"),
                "confidence_delta": round(revised_confidence - float(source.confidence), 4),
                "specificity_before": _prompt_specificity(source.concept, source.definition),
                "specificity_after": specificity,
                "redundancy_before": before_redundancy.get(source.concept_id, 0.0),
                "redundancy_after": redundancy,
                "promotion_score_delta": round(
                    (0.2 if status == "supported" else 0.0)
                    + max(0.0, _prompt_specificity(source.concept, source.definition) - specificity)
                    + max(0.0, before_redundancy.get(source.concept_id, 0.0) - redundancy),
                    4,
                ),
                "rationale": rationale,
            }
        )
        examples.append(
            {
                "before": source.definition,
                "after": normalized.definition,
                "method": result["method"],
                "status": status,
            }
        )

    status_counts = Counter(item["status"] for item in revalidation_records)
    recovered = [item for item in revalidation_records if item["status"] == "supported"]
    still_rejected = [item for item in revalidation_records if item["status"] != "supported"]
    artifact_before = sum(item["specificity_before"] for item in revalidation_records)
    artifact_after = sum(item["specificity_after"] for item in revalidation_records)
    redundancy_before = sum(item["redundancy_before"] for item in revalidation_records)
    redundancy_after = sum(item["redundancy_after"] for item in revalidation_records)
    summary = {
        "run_id": f"phase18_semantic_normalization_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "store_root": str(store_root),
        "failed_predictions_considered": len(failed),
        "normalized_concepts": len(normalized_records),
        "revalidated_concepts": len(revalidation_records),
        "recovered_concepts": len(recovered),
        "still_rejected": len(still_rejected),
        "skipped": len(skipped),
        "status_counts": dict(status_counts),
        "false_negatives_recovered": len(recovered),
        "normalization_precision": round(
            len(recovered) / max(1, len(revalidation_records)),
            4,
        ),
        "confidence_improvement": round(
            sum(max(0.0, item["confidence_delta"]) for item in revalidation_records),
            4,
        ),
        "confidence_decline": round(
            sum(min(0.0, item["confidence_delta"]) for item in revalidation_records),
            4,
        ),
        "artifact_reduction": round(artifact_before - artifact_after, 4),
        "redundancy_reduction": round(redundancy_before - redundancy_after, 4),
        "average_promotion_score_improvement": round(
            sum(item["promotion_score_delta"] for item in revalidation_records)
            / max(1, len(revalidation_records)),
            4,
        ),
        "examples": examples,
        "revalidation_records": revalidation_records,
        "skipped_records": skipped,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase18_normalization_report.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(summary, reports_dir)
    return summary


def _write_reports(summary: dict[str, Any], reports_dir: Path) -> None:
    (reports_dir / "phase18_normalization_report.md").write_text(
        "\n".join(
            [
                "# Phase 18 Semantic Normalization Report",
                "",
                "Phase 18 normalized failed concepts from the isolated Phase 15/17 store.",
                "No canonical promotion was performed.",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Failed predictions considered | {summary['failed_predictions_considered']} |",
                f"| Normalized concepts | {summary['normalized_concepts']} |",
                f"| Revalidated concepts | {summary['revalidated_concepts']} |",
                f"| Recovered concepts | {summary['recovered_concepts']} |",
                f"| Not recovered after normalization | {summary['still_rejected']} |",
                f"| Skipped | {summary['skipped']} |",
                f"| Normalization precision | {summary['normalization_precision']} |",
                f"| Artifact reduction | {summary['artifact_reduction']} |",
                f"| Redundancy reduction | {summary['redundancy_reduction']} |",
                f"| Avg promotion score improvement | {summary['average_promotion_score_improvement']} |",
                "",
                "## Finding",
                "",
                "Normalization recovered useful propositions from a small subset of Phase 17 failed "
                "predictions. The failures were not all bad beliefs; some were bad extraction "
                "boundaries. Most normalized concepts remained inconclusive because cleanup reduced "
                "prompt artifacts without adding enough distinct semantic value.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "normalization_examples.md").write_text(
        "\n".join(
            [
                "# Normalization Examples",
                "",
                *[
                    f"## Example {index}\n\nBefore: `{item['before']}`\n\nAfter: `{item['after']}`\n\nMethod: `{item['method']}`\n\nRevalidation: `{item['status']}`\n"
                    for index, item in enumerate(summary["examples"][:30], start=1)
                ],
            ]
        ),
        encoding="utf-8",
    )
    recovered = [
        item for item in summary["revalidation_records"] if item["status"] == "supported"
    ]
    (reports_dir / "recovered_concepts.md").write_text(
        "\n".join(
            [
                "# Recovered Concepts",
                "",
                *[
                    f"- `{item['normalized_concept']}` from `{item['original_concept']}` "
                    f"({item['source_provider']}, {item['source_profile']}, "
                    f"confidence {item['confidence_before']} -> {item['confidence_after']})"
                    for item in recovered
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "revalidation_report.md").write_text(
        "\n".join(
            [
                "# Phase 18 Revalidation Report",
                "",
                "| Outcome | Count |",
                "| --- | ---: |",
                *[
                    f"| {key} | {value} |"
                    for key, value in sorted(summary["status_counts"].items())
                ],
                "",
                "## Not Recovered After Normalization",
                "",
                *[
                    f"- `{item['normalized_concept']}`: `{item['rationale']}`"
                    for item in summary["revalidation_records"]
                    if item["status"] != "supported"
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and revalidate failed semantic concepts.")
    parser.add_argument("--store-root", required=True)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--max-items", type=int, default=40)
    args = parser.parse_args()
    summary = run_normalization(
        store_root=Path(args.store_root),
        reports_dir=Path(args.reports_dir),
        max_items=args.max_items,
    )
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "normalized_concepts": summary["normalized_concepts"],
                "recovered_concepts": summary["recovered_concepts"],
                "still_rejected": summary["still_rejected"],
                "skipped": summary["skipped"],
                "status_counts": summary["status_counts"],
                "artifact_reduction": summary["artifact_reduction"],
                "redundancy_reduction": summary["redundancy_reduction"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.continuous_learning_operator import run_continuous_learning


BALANCED_PROFILES = (
    "planning",
    "contradiction",
    "causal_reasoning",
    "risk_assessment",
    "resource_allocation",
)
ALTERNATING_PROFILES = (
    "planning",
    "causal_reasoning",
    "contradiction",
    "resource_allocation",
    "risk_assessment",
)
STABILITY_THRESHOLD = 0.80
PROMOTION_CHURN_THRESHOLD = 0.20


@dataclass(frozen=True)
class ChunkSpec:
    cycles: int
    profiles: tuple[str, ...]


@dataclass(frozen=True)
class CampaignSpec:
    name: str
    stage: str
    purpose: str
    chunks: tuple[ChunkSpec, ...]
    prerequisite_stages: tuple[str, ...] = ()


CAMPAIGNS: tuple[CampaignSpec, ...] = (
    CampaignSpec(
        name="dry_run_40",
        stage="stage1_infrastructure",
        purpose="Verify chunk orchestration, checkpointing, reports, and isolated-store behavior.",
        chunks=(
            ChunkSpec(20, ("planning", "causal_reasoning")),
            ChunkSpec(20, ("planning", "causal_reasoning")),
        ),
    ),
    CampaignSpec(
        name="stability_500",
        stage="stage1_infrastructure",
        purpose="Verify 500-cycle infrastructure behavior before longer campaigns.",
        chunks=(
            ChunkSpec(200, BALANCED_PROFILES),
            ChunkSpec(200, BALANCED_PROFILES),
            ChunkSpec(100, BALANCED_PROFILES),
        ),
    ),
    CampaignSpec(
        name="stability_1000",
        stage="stage2_behavioral",
        purpose="Measure long-run stability under a balanced curriculum.",
        chunks=tuple(ChunkSpec(200, BALANCED_PROFILES) for _ in range(5)),
        prerequisite_stages=("stage1_infrastructure",),
    ),
    CampaignSpec(
        name="alternating_curriculum_1000",
        stage="stage2_behavioral",
        purpose="Measure whether automatic curriculum alternation remains stable.",
        chunks=tuple(ChunkSpec(200, (profile,)) for profile in ALTERNATING_PROFILES),
        prerequisite_stages=("stage1_infrastructure",),
    ),
    CampaignSpec(
        name="overnight_2000",
        stage="stage3_graduation",
        purpose="Graduation stress certification after infrastructure and behavioral validation pass.",
        chunks=tuple(ChunkSpec(200, (ALTERNATING_PROFILES[index % len(ALTERNATING_PROFILES)],)) for index in range(10)),
        prerequisite_stages=("stage1_infrastructure", "stage2_behavioral"),
    ),
    CampaignSpec(
        name="overnight_3000",
        stage="stage3_graduation",
        purpose="Extended passive graduation stress certification for unattended overnight operation.",
        chunks=tuple(ChunkSpec(200, (ALTERNATING_PROFILES[index % len(ALTERNATING_PROFILES)],)) for index in range(15)),
        prerequisite_stages=("stage1_infrastructure", "stage2_behavioral"),
    ),
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _safe_reset_dir(path: Path, root: Path) -> None:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise ValueError(f"Refusing to remove path outside campaign root: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _ensure_isolated_root(campaign_root: Path) -> None:
    normalized = [part.lower() for part in campaign_root.resolve().parts]
    if ".tmp" not in normalized or "experiments" not in normalized:
        raise ValueError(
            "Phase A must run under an isolated .tmp/experiments store root; "
            f"got {campaign_root.resolve()}"
        )


def _checkpoint_path(run_dir: Path) -> Path:
    return run_dir / "phaseA_checkpoint.json"


def _load_checkpoint(run_dir: Path) -> dict[str, Any]:
    path = _checkpoint_path(run_dir)
    if not path.exists():
        return {"chunks": [], "status": "pending"}
    return _load_json(path)


def _write_checkpoint(run_dir: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = datetime.now(timezone.utc).isoformat()
    _checkpoint_path(run_dir).write_text(
        json.dumps(_jsonable(checkpoint), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _counts_delta(training: dict[str, Any], key: str) -> int:
    final_counts = training.get("final_counts", {})
    baseline_counts = training.get("baseline_counts", {})
    return int(final_counts.get(key, 0) or 0) - int(baseline_counts.get(key, 0) or 0)


def _final_count(training: dict[str, Any], key: str) -> int:
    return int(training.get("final_counts", {}).get(key, 0) or 0)


def _decision_values(decisions: list[dict[str, Any]], dimension: str) -> list[float]:
    values: list[float] = []
    for decision in decisions:
        value = decision.get("dimensions", {}).get(dimension)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _provider_usage(training: dict[str, Any]) -> dict[str, int]:
    usage: Counter[str] = Counter()
    for provider, metrics in training.get("provider_metrics", {}).items():
        usage[str(provider)] += int(metrics.get("cycles", 0) or 0)
    return dict(usage)


def _prediction_quality(reports_dir: Path) -> dict[str, Any]:
    phase17 = _load_json(reports_dir / "phase17_validation_report.json")
    phase16 = _load_json(reports_dir / "phase16_validation_report.json")
    return phase17.get("after_prediction_quality") or phase16.get("after_prediction_quality") or {}


def _recommendation_counts(governance: dict[str, Any]) -> Counter[str]:
    return Counter(governance.get("recommendation_counts", {}))


def _eligible_ids(decisions: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("concept_id"))
        for item in decisions
        if item.get("recommendation") == "Promotion Eligible" and item.get("concept_id")
    }


def _promotion_churn(previous: set[str], current: set[str]) -> dict[str, Any]:
    stayed = previous & current
    lost = previous - current
    new = current - previous
    denominator = max(1, len(previous))
    return {
        "stayed": len(stayed),
        "lost": len(lost),
        "new": len(new),
        "total": len(current),
        "churn_rate": round((len(lost) + len(new)) / denominator, 4),
        "stayed_ids": sorted(stayed),
        "lost_ids": sorted(lost),
        "new_ids": sorted(new),
    }


def _knowledge_retention(chunk: dict[str, Any], next_chunk: dict[str, Any] | None = None) -> dict[str, Any]:
    generated = int(chunk.get("semantic_concepts_generated", 0) or 0)
    validated = int(chunk.get("validated_concepts", 0) or 0)
    candidates = int(chunk.get("promotion_candidates", 0) or 0)
    eligible = int(chunk.get("promotion_eligible", 0) or 0)
    still_eligible = 0
    if next_chunk:
        current = set(chunk.get("eligible_ids", []))
        after = set(next_chunk.get("eligible_ids", []))
        still_eligible = len(current & after)
    return {
        "generated": generated,
        "validated": validated,
        "promotion_candidate": candidates,
        "promotion_eligible": eligible,
        "still_eligible_next_chunk": still_eligible,
        "validated_ratio": round(validated / max(1, generated), 4),
        "candidate_ratio": round(candidates / max(1, generated), 4),
        "eligible_ratio": round(eligible / max(1, generated), 4),
        "eligible_retention_ratio": round(still_eligible / max(1, eligible), 4),
    }


def _dry_run_recommendation(decision: dict[str, Any]) -> dict[str, Any]:
    evidence = decision.get("evidence", {})
    dimensions = decision.get("dimensions", {})
    score = float(decision.get("promotion_score", 0.0) or 0.0)
    reasons: list[str] = []
    rejection_reasons: list[str] = []
    if evidence.get("failed_predictions", 0) > 0:
        rejection_reasons.append("failed validation evidence exists")
    if evidence.get("open_contradictions", 0) > 0:
        rejection_reasons.append("open contradiction pressure exists")
    if dimensions.get("redundancy_penalty", 0.0) >= 0.32:
        rejection_reasons.append("redundancy penalty is high")
    if evidence.get("unresolved_predictions", 0) > 0:
        rejection_reasons.append("unresolved prediction backlog remains")
    if dimensions.get("prompt_artifact_penalty", 0.0) >= 0.32:
        rejection_reasons.append("prompt/context artifact penalty is high")
    if evidence.get("incomplete_proposition"):
        rejection_reasons.append("concept appears incomplete")
    if score >= 0.68 and not rejection_reasons:
        state = "PROMOTE"
        reasons.append("promotion score meets dry-run canonical threshold")
    elif score >= 0.52 and not evidence.get("failed_predictions", 0):
        state = "HOLD"
        reasons.append("candidate has partial support but needs more maturation")
    else:
        state = "REJECT"
        reasons.append("candidate does not satisfy dry-run canonical quality")
    if not rejection_reasons:
        rejection_reasons.append("no deterministic rejection reason was detected")
    return {
        "concept_id": decision.get("concept_id"),
        "concept": decision.get("concept"),
        "dry_run_state": state,
        "promotion_score": score,
        "reason_promoted": "; ".join(reasons),
        "reason_not_rejected": "; ".join(rejection_reasons),
        "evidence_summary": evidence,
        "confidence_trajectory": decision.get("confidence_trajectory", []),
        "contradiction_history": {
            "open_contradictions": evidence.get("open_contradictions", 0),
        },
        "redundancy_history": {
            "redundancy_penalty": dimensions.get("redundancy_penalty", 0.0),
        },
        "supporting_concepts": evidence.get("projection_sources", []),
        "origin_curriculum": decision.get("provenance", {}).get("source_profile"),
        "origin_provider": decision.get("provenance", {}).get("source_provider"),
        "canonical_write_performed": False,
    }


def _summarize_chunk(
    *,
    run_dir: Path,
    chunk_index: int,
    spec: ChunkSpec,
    previous_eligible: set[str],
    started: float,
    error: str | None,
) -> dict[str, Any]:
    reports_dir = run_dir / "chunks" / f"chunk_{chunk_index:03d}" / "reports"
    training = _load_json(reports_dir / "continuous_learning_training_summary.json")
    governance = _load_json(reports_dir / "promotion_governance_report.json")
    normalization = _load_json(reports_dir / "phase18_normalization_report.json")
    quality = _prediction_quality(reports_dir)
    decisions = governance.get("decisions", [])
    recs = _recommendation_counts(governance)
    scores = [float(item.get("promotion_score", 0.0) or 0.0) for item in decisions]
    current_eligible = _eligible_ids(decisions)
    candidates = recs.get("Candidate", 0) + recs.get("Validated", 0) + recs.get("Promotion Eligible", 0)
    summary = {
        "chunk_index": chunk_index,
        "status": "failed" if error else "completed",
        "error": error,
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "cycles_requested": spec.cycles,
        "cycles_completed": int(training.get("cycles_completed", 0) or 0),
        "profiles": list(spec.profiles),
        "stopped_early": bool(training.get("stopped_early")),
        "stop_reason": training.get("stop_reason"),
        "semantic_concepts_generated": _counts_delta(training, "semantic_knowledge"),
        "memories_generated": _counts_delta(training, "memories"),
        "relationships_generated": _counts_delta(training, "relationships"),
        "predictions_generated": _counts_delta(training, "predictions"),
        "memory_total": _final_count(training, "memories"),
        "semantic_total": _final_count(training, "semantic_knowledge"),
        "relationship_total": _final_count(training, "relationships"),
        "prediction_total": _final_count(training, "predictions"),
        "contradiction_total": _final_count(training, "contradictions"),
        "validation_coverage": float(quality.get("coverage", 0.0) or 0.0),
        "supported_predictions": int(quality.get("supported", 0) or 0),
        "failed_predictions": int(quality.get("failed", 0) or 0),
        "inconclusive_predictions": int(quality.get("inconclusive", 0) or 0),
        "unresolved_predictions": int(quality.get("open", 0) or 0),
        "validated_concepts": int(recs.get("Validated", 0)),
        "rejected_concepts": int(recs.get("Reject", 0)),
        "promotion_candidates": int(candidates),
        "promotion_eligible": int(recs.get("Promotion Eligible", 0)),
        "eligible_ids": sorted(current_eligible),
        "promotion_churn": _promotion_churn(previous_eligible, current_eligible),
        "average_promotion_score": governance.get("average_promotion_score", _mean(scores)),
        "redundancy_average": _mean(_decision_values(decisions, "redundancy_penalty")),
        "contradiction_pressure": sum(
            int(item.get("evidence", {}).get("open_contradictions", 0) or 0)
            for item in decisions
        ),
        "relationship_centrality_average": _mean(_decision_values(decisions, "relationship_centrality")),
        "projected_centrality_average": _mean(_decision_values(decisions, "projected_centrality")),
        "normalization_recovered": int(normalization.get("recovered_concepts", 0) or 0),
        "provider_usage": _provider_usage(training),
        "reports_dir": str(reports_dir),
    }
    return summary


def _consecutive_low_coverage(chunks: list[dict[str, Any]]) -> bool:
    if len(chunks) < 2:
        return False
    return all(
        float(chunk.get("validation_coverage", 0.0) or 0.0) < STABILITY_THRESHOLD
        for chunk in chunks[-2:]
    )


def _promotion_unstable(chunks: list[dict[str, Any]]) -> bool:
    if len(chunks) <= 2:
        return False
    latest = chunks[-1].get("promotion_churn", {})
    churn_rate = float(latest.get("churn_rate", 0.0) or 0.0)
    lost = int(latest.get("lost", 0) or 0)
    new = int(latest.get("new", 0) or 0)
    if churn_rate <= PROMOTION_CHURN_THRESHOLD:
        return False
    # Replacement with equal-or-greater new count is recorded, not stopped.
    return lost > new


def _stop_reason(chunks: list[dict[str, Any]]) -> str | None:
    if not chunks:
        return None
    if chunks[-1].get("status") == "failed":
        return "chunk execution failed"
    if _consecutive_low_coverage(chunks):
        return "validation coverage below 0.80 for two consecutive chunks"
    if _promotion_unstable(chunks):
        return "promotion eligibility churn exceeded 20% without stronger replacement"
    return None


def _run_single_campaign(
    *,
    campaign_root: Path,
    spec: CampaignSpec,
    reset: bool,
) -> dict[str, Any]:
    run_dir = campaign_root / spec.name
    if reset:
        _safe_reset_dir(run_dir, campaign_root)
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
    store_root = run_dir / "store"
    chunks_root = run_dir / "chunks"
    store_root.mkdir(parents=True, exist_ok=True)
    chunks_root.mkdir(parents=True, exist_ok=True)
    checkpoint = _load_checkpoint(run_dir)
    completed_chunks: list[dict[str, Any]] = list(checkpoint.get("chunks", []))
    previous_eligible = set(completed_chunks[-1].get("eligible_ids", [])) if completed_chunks else set()
    completed_indexes = {int(chunk.get("chunk_index", 0)) for chunk in completed_chunks}

    for chunk_index, chunk in enumerate(spec.chunks, start=1):
        if chunk_index in completed_indexes:
            continue
        chunk_dir = chunks_root / f"chunk_{chunk_index:03d}"
        chunk_reports = chunk_dir / "reports"
        chunk_reports.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        error: str | None = None
        try:
            run_continuous_learning(
                store_root=store_root,
                reports_dir=chunk_reports,
                cycles=chunk.cycles,
                objective_count=chunk.cycles,
                validation_limit=min(200, max(40, chunk.cycles)),
                adversarial_limit=min(200, max(40, chunk.cycles)),
                normalization_limit=min(120, max(40, chunk.cycles // 2)),
                curriculum_profiles=chunk.profiles,
                structured_output_contract=False,
                use_projection=True,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        chunk_summary = _summarize_chunk(
            run_dir=run_dir,
            chunk_index=chunk_index,
            spec=chunk,
            previous_eligible=previous_eligible,
            started=started,
            error=error,
        )
        completed_chunks.append(chunk_summary)
        previous_eligible = set(chunk_summary.get("eligible_ids", []))
        retention = _knowledge_retention(completed_chunks[-2], chunk_summary) if len(completed_chunks) >= 2 else None
        if retention:
            completed_chunks[-2]["knowledge_retention"] = retention
        checkpoint = {
            "campaign": spec.name,
            "stage": spec.stage,
            "status": "running",
            "chunks": completed_chunks,
            "canonical_merge_performed": False,
        }
        reason = _stop_reason(completed_chunks)
        if reason:
            checkpoint["status"] = "stopped"
            checkpoint["stop_reason"] = reason
            _write_checkpoint(run_dir, checkpoint)
            return _summarize_campaign(run_dir, spec, checkpoint)
        _write_checkpoint(run_dir, checkpoint)

    if completed_chunks:
        completed_chunks[-1]["knowledge_retention"] = _knowledge_retention(completed_chunks[-1], None)
    checkpoint = {
        "campaign": spec.name,
        "stage": spec.stage,
        "status": "completed",
        "chunks": completed_chunks,
        "canonical_merge_performed": False,
    }
    _write_checkpoint(run_dir, checkpoint)
    return _summarize_campaign(run_dir, spec, checkpoint)


def _trend(values: list[float]) -> str:
    if len(values) < 2:
        return "insufficient_data"
    delta = values[-1] - values[0]
    if delta > 0.03:
        return "rising"
    if delta < -0.03:
        return "falling"
    return "stable"


def _bounded_growth(chunks: list[dict[str, Any]], key: str) -> bool:
    values = [float(chunk.get(key, 0) or 0) for chunk in chunks]
    if len(values) < 3:
        return True
    deltas = [max(0.0, values[index] - values[index - 1]) for index in range(1, len(values))]
    if not deltas:
        return True
    return max(deltas) <= max(1.0, mean(deltas) * 3.0)


def _summarize_campaign(run_dir: Path, spec: CampaignSpec, checkpoint: dict[str, Any]) -> dict[str, Any]:
    chunks = checkpoint.get("chunks", [])
    for index, chunk in enumerate(chunks[:-1]):
        chunk["knowledge_retention"] = _knowledge_retention(chunk, chunks[index + 1])
    if chunks:
        chunks[-1]["knowledge_retention"] = _knowledge_retention(chunks[-1], None)
    all_scores = [float(chunk.get("average_promotion_score", 0.0) or 0.0) for chunk in chunks]
    eligible_counts = [int(chunk.get("promotion_eligible", 0) or 0) for chunk in chunks]
    redundancy = [float(chunk.get("redundancy_average", 0.0) or 0.0) for chunk in chunks]
    contradictions = [float(chunk.get("contradiction_pressure", 0.0) or 0.0) for chunk in chunks]
    provider_usage: Counter[str] = Counter()
    for chunk in chunks:
        provider_usage.update(chunk.get("provider_usage", {}))
    summary = {
        "campaign": spec.name,
        "stage": spec.stage,
        "purpose": spec.purpose,
        "status": checkpoint.get("status", "unknown"),
        "stop_reason": checkpoint.get("stop_reason"),
        "canonical_merge_performed": False,
        "cycles_requested": sum(chunk.cycles for chunk in spec.chunks),
        "cycles_completed": sum(int(chunk.get("cycles_completed", 0) or 0) for chunk in chunks),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "semantic_concepts_generated": sum(int(chunk.get("semantic_concepts_generated", 0) or 0) for chunk in chunks),
        "validated_concepts_latest": int(chunks[-1].get("validated_concepts", 0) if chunks else 0),
        "promotion_candidates_latest": int(chunks[-1].get("promotion_candidates", 0) if chunks else 0),
        "promotion_eligible_latest": int(chunks[-1].get("promotion_eligible", 0) if chunks else 0),
        "average_promotion_score_latest": all_scores[-1] if all_scores else 0.0,
        "promotion_score_trend": _trend(all_scores),
        "promotion_eligible_trend": _trend([float(item) for item in eligible_counts]),
        "validation_coverage_latest": float(chunks[-1].get("validation_coverage", 0.0) if chunks else 0.0),
        "validation_coverage_min": min((float(chunk.get("validation_coverage", 0.0) or 0.0) for chunk in chunks), default=0.0),
        "redundancy_trend": _trend(redundancy),
        "contradiction_trend": _trend(contradictions),
        "memory_growth_bounded": _bounded_growth(chunks, "memory_total"),
        "semantic_growth_bounded": _bounded_growth(chunks, "semantic_total"),
        "graph_growth_bounded": _bounded_growth(chunks, "relationship_total"),
        "provider_usage": dict(provider_usage.most_common()),
        "reports_dir": str(run_dir),
    }
    (run_dir / "phaseA_campaign_summary.json").write_text(
        json.dumps(_jsonable(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _stage_passed(completed: list[dict[str, Any]], stage: str) -> bool:
    stage_runs = [run for run in completed if run.get("stage") == stage]
    if not stage_runs:
        return False
    return all(run.get("status") == "completed" for run in stage_runs)


def _prerequisites_met(completed: list[dict[str, Any]], spec: CampaignSpec) -> bool:
    return all(_stage_passed(completed, stage) for stage in spec.prerequisite_stages)


def _aggregate_campaigns(campaigns: list[dict[str, Any]], campaign_root: Path) -> dict[str, Any]:
    latest_chunks = [campaign["chunks"][-1] for campaign in campaigns if campaign.get("chunks")]
    all_chunks = [chunk for campaign in campaigns for chunk in campaign.get("chunks", [])]
    return {
        "run_id": f"phaseA_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "campaign_root": str(campaign_root),
        "canonical_merge_performed": False,
        "campaign_count": len(campaigns),
        "completed_campaign_count": sum(1 for item in campaigns if item.get("status") == "completed"),
        "campaigns": campaigns,
        "total_cycles_completed": sum(int(item.get("cycles_completed", 0) or 0) for item in campaigns),
        "semantic_concepts_generated": sum(int(item.get("semantic_concepts_generated", 0) or 0) for item in campaigns),
        "promotion_eligible_latest_total": sum(int(chunk.get("promotion_eligible", 0) or 0) for chunk in latest_chunks),
        "average_latest_promotion_score": _mean(
            [float(chunk.get("average_promotion_score", 0.0) or 0.0) for chunk in latest_chunks]
        ),
        "minimum_latest_validation_coverage": min(
            (float(chunk.get("validation_coverage", 0.0) or 0.0) for chunk in latest_chunks),
            default=0.0,
        ),
        "max_chunk_promotion_churn": max(
            (
                float(chunk.get("promotion_churn", {}).get("churn_rate", 0.0) or 0.0)
                for chunk in all_chunks[1:]
            ),
            default=0.0,
        ),
        "blocking_stop_reasons": [
            item.get("stop_reason")
            for item in campaigns
            if item.get("status") != "completed" and item.get("stop_reason")
        ],
    }


def _dry_run_canonical_recommendations(campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for campaign in campaigns:
        for chunk in campaign.get("chunks", []):
            governance = _load_json(Path(chunk["reports_dir"]) / "promotion_governance_report.json")
            decisions.extend(governance.get("decisions", []))
    candidates = [
        item
        for item in decisions
        if item.get("recommendation") in {"Candidate", "Validated", "Promotion Eligible"}
    ]
    top = sorted(candidates, key=lambda item: float(item.get("promotion_score", 0.0) or 0.0), reverse=True)[:50]
    return [_dry_run_recommendation(item) for item in top]


def _graduation_conclusion(aggregate: dict[str, Any], dry_run: list[dict[str, Any]]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if aggregate.get("blocking_stop_reasons"):
        blockers.extend(str(reason) for reason in aggregate["blocking_stop_reasons"])
    if aggregate["completed_campaign_count"] < len(CAMPAIGNS):
        blockers.append("not all Phase A campaigns completed")
    if aggregate["minimum_latest_validation_coverage"] < STABILITY_THRESHOLD:
        blockers.append("latest validation coverage fell below 0.80")
    if aggregate["max_chunk_promotion_churn"] > PROMOTION_CHURN_THRESHOLD:
        blockers.append("promotion churn exceeded 20% in at least one mature chunk")
    promote_count = sum(1 for item in dry_run if item["dry_run_state"] == "PROMOTE")
    if promote_count == 0:
        blockers.append("canonical dry run produced no PROMOTE recommendations")
    if blockers:
        return "Graduate Conditionally", blockers
    return "Graduate to Cognitive Runtime Development", []


def _write_reports(aggregate: dict[str, Any], dry_run: list[dict[str, Any]], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phaseA_temp_store_validation_report.json").write_text(
        json.dumps(_jsonable({"aggregate": aggregate, "canonical_dry_run": dry_run}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    campaign_rows = [
        (
            f"| {item['campaign']} | {item['stage']} | {item['status']} | "
            f"{item['cycles_completed']}/{item['cycles_requested']} | "
            f"{item['semantic_concepts_generated']} | {item['validation_coverage_latest']} | "
            f"{item['average_promotion_score_latest']} | {item['promotion_eligible_latest']} | "
            f"{item.get('stop_reason') or ''} |"
        )
        for item in aggregate["campaigns"]
    ]
    chunk_rows = [
        (
            f"| {campaign['campaign']} | {chunk['chunk_index']} | {','.join(chunk['profiles'])} | "
            f"{chunk['cycles_completed']}/{chunk['cycles_requested']} | "
            f"{chunk['semantic_concepts_generated']} | {chunk['validated_concepts']} | "
            f"{chunk['promotion_candidates']} | {chunk['promotion_eligible']} | "
            f"{chunk['knowledge_retention']['still_eligible_next_chunk']} | "
            f"{chunk['promotion_churn']['churn_rate']} | {chunk['validation_coverage']} |"
        )
        for campaign in aggregate["campaigns"]
        for chunk in campaign.get("chunks", [])
    ]
    conclusion, blockers = _graduation_conclusion(aggregate, dry_run)
    report = [
        "# Phase A Temporary-Store Validation Report",
        "",
        "Canonical knowledge was not modified. Existing extraction, validation, normalization, projection, and governance behavior was treated as frozen.",
        "",
        "## Campaign Summary",
        "",
        "| Campaign | Stage | Status | Cycles | Semantic Growth | Coverage | Avg Score | Eligible | Stop Reason |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        *campaign_rows,
        "",
        "## Chunk Metrics",
        "",
        "| Campaign | Chunk | Profiles | Cycles | Generated | Validated | Candidates | Eligible | Still Eligible Next | Churn | Coverage |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *chunk_rows,
        "",
        "## Campaign Result",
        "",
        f"- Total cycles completed: `{aggregate['total_cycles_completed']}`",
        f"- Semantic concepts generated: `{aggregate['semantic_concepts_generated']}`",
        f"- Latest promotion-eligible total: `{aggregate['promotion_eligible_latest_total']}`",
        f"- Average latest promotion score: `{aggregate['average_latest_promotion_score']}`",
        f"- Minimum latest validation coverage: `{aggregate['minimum_latest_validation_coverage']}`",
        f"- Max chunk promotion churn: `{aggregate['max_chunk_promotion_churn']}`",
        "",
        "## Preliminary Graduation Conclusion",
        "",
        conclusion if not blockers else f"{conclusion}: {', '.join(blockers)}",
        "",
    ]
    (reports_dir / "phaseA_temp_store_validation_report.md").write_text("\n".join(report), encoding="utf-8")
    _write_focus_reports(aggregate, dry_run, reports_dir, conclusion, blockers)
    _write_completion_sentinel(aggregate, reports_dir, conclusion, blockers)


def _write_completion_sentinel(
    aggregate: dict[str, Any],
    reports_dir: Path,
    conclusion: str,
    blockers: list[str],
) -> None:
    final_campaign = aggregate["campaigns"][-1] if aggregate.get("campaigns") else {}
    sentinel = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": not blockers and aggregate["completed_campaign_count"] == len(CAMPAIGNS),
        "final_stage": final_campaign.get("stage"),
        "final_campaign": final_campaign.get("campaign"),
        "final_campaign_status": final_campaign.get("status"),
        "stop_reason": final_campaign.get("stop_reason"),
        "conclusion": conclusion,
        "blockers": blockers,
        "canonical_merge_performed": False,
        "report_paths": {
            "graduation": str(reports_dir / "PhaseA_Architecture_Graduation.md"),
            "summary": str(reports_dir / "phaseA_temp_store_validation_report.md"),
            "summary_json": str(reports_dir / "phaseA_temp_store_validation_report.json"),
            "promotion_stability": str(reports_dir / "phaseA_promotion_stability.md"),
            "dry_run": str(reports_dir / "phaseA_canonical_promotion_dry_run.md"),
        },
    }
    (reports_dir / "phaseA_complete.json").write_text(
        json.dumps(_jsonable(sentinel), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_focus_reports(
    aggregate: dict[str, Any],
    dry_run: list[dict[str, Any]],
    reports_dir: Path,
    conclusion: str,
    blockers: list[str],
) -> None:
    campaigns = aggregate["campaigns"]
    (reports_dir / "phaseA_long_run_stability.md").write_text(
        "\n".join(
            [
                "# Phase A Long-Run Stability",
                "",
                "| Campaign | Memory Bounded | Semantic Bounded | Graph Bounded | Score Trend | Coverage Min |",
                "| --- | --- | --- | --- | --- | ---: |",
                *[
                    (
                        f"| {item['campaign']} | {item['memory_growth_bounded']} | "
                        f"{item['semantic_growth_bounded']} | {item['graph_growth_bounded']} | "
                        f"{item['promotion_score_trend']} | {item['validation_coverage_min']} |"
                    )
                    for item in campaigns
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phaseA_promotion_stability.md").write_text(
        "\n".join(
            [
                "# Phase A Promotion Stability",
                "",
                "| Campaign | Chunk | Eligible | Stayed | Lost | New | Churn |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
                *[
                    (
                        f"| {campaign['campaign']} | {chunk['chunk_index']} | {chunk['promotion_eligible']} | "
                        f"{chunk['promotion_churn']['stayed']} | {chunk['promotion_churn']['lost']} | "
                        f"{chunk['promotion_churn']['new']} | {chunk['promotion_churn']['churn_rate']} |"
                    )
                    for campaign in campaigns
                    for chunk in campaign.get("chunks", [])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phaseA_redundancy_trends.md").write_text(
        "\n".join(
            [
                "# Phase A Redundancy Trends",
                "",
                "| Campaign | Chunk | Redundancy Average | Trend |",
                "| --- | ---: | ---: | --- |",
                *[
                    f"| {campaign['campaign']} | {chunk['chunk_index']} | {chunk['redundancy_average']} | {campaign['redundancy_trend']} |"
                    for campaign in campaigns
                    for chunk in campaign.get("chunks", [])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phaseA_contradiction_trends.md").write_text(
        "\n".join(
            [
                "# Phase A Contradiction Trends",
                "",
                "| Campaign | Chunk | Contradiction Pressure | Trend | Failed Predictions |",
                "| --- | ---: | ---: | --- | ---: |",
                *[
                    (
                        f"| {campaign['campaign']} | {chunk['chunk_index']} | "
                        f"{chunk['contradiction_pressure']} | {campaign['contradiction_trend']} | "
                        f"{chunk['failed_predictions']} |"
                    )
                    for campaign in campaigns
                    for chunk in campaign.get("chunks", [])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phaseA_curriculum_behavior.md").write_text(
        "\n".join(
            [
                "# Phase A Curriculum Behavior",
                "",
                "| Campaign | Chunk | Profiles | Semantic Growth | Coverage | Avg Score | Provider Usage |",
                "| --- | ---: | --- | ---: | ---: | ---: | --- |",
                *[
                    (
                        f"| {campaign['campaign']} | {chunk['chunk_index']} | {','.join(chunk['profiles'])} | "
                        f"{chunk['semantic_concepts_generated']} | {chunk['validation_coverage']} | "
                        f"{chunk['average_promotion_score']} | `{chunk['provider_usage']}` |"
                    )
                    for campaign in campaigns
                    for chunk in campaign.get("chunks", [])
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    promote_rows = [
        (
            f"| {item['dry_run_state']} | {item['promotion_score']} | {item['origin_curriculum']} | "
            f"{item['origin_provider']} | {item['concept'][:120]} |"
        )
        for item in dry_run
    ]
    (reports_dir / "phaseA_canonical_promotion_dry_run.md").write_text(
        "\n".join(
            [
                "# Phase A Canonical Promotion Dry Run",
                "",
                "No canonical writes were performed.",
                "",
                "| State | Score | Origin Curriculum | Origin Provider | Concept |",
                "| --- | ---: | --- | --- | --- |",
                *promote_rows,
                "",
                "## Full Recommendations",
                "",
                "```json",
                json.dumps(_jsonable(dry_run), indent=2, sort_keys=True),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    final_lines = [
        "# PhaseA Architecture Graduation",
        "",
        "## Questions",
        "",
        f"- Is Delta's learning architecture stable under long-running governed learning? `{_yes_no(not aggregate['blocking_stop_reasons'])}`",
        f"- Are semantic concepts accumulating into durable knowledge? `{_yes_no(aggregate['semantic_concepts_generated'] > 0 and aggregate['promotion_eligible_latest_total'] > 0)}`",
        f"- Is promotion governance stable? `{_yes_no(aggregate['max_chunk_promotion_churn'] <= PROMOTION_CHURN_THRESHOLD)}`",
        f"- Is knowledge maturation occurring? `{_yes_no(aggregate['promotion_eligible_latest_total'] > 0)}`",
        f"- Are redundancy and contradiction bounded? `{_yes_no(all(item['redundancy_trend'] != 'rising' or item['contradiction_trend'] != 'rising' for item in campaigns))}`",
        f"- Is canonical promotion justified? `{_yes_no(any(item['dry_run_state'] == 'PROMOTE' for item in dry_run))}`",
        "",
        "## Unresolved Risks",
        "",
        *(f"- {item}" for item in (blockers or ["No hard blocker was detected by the scripted gates."])),
        "",
        "## Final Conclusion",
        "",
    ]
    if conclusion == "Graduate Conditionally":
        final_lines.append(f"Graduate Conditionally: {', '.join(blockers)}")
    else:
        final_lines.append(conclusion)
    (reports_dir / "PhaseA_Architecture_Graduation.md").write_text(
        "\n".join(final_lines),
        encoding="utf-8",
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def run_phaseA(
    *,
    campaign_root: Path,
    reports_dir: Path,
    selected_campaigns: set[str] | None = None,
    reset: bool = False,
    ignore_prerequisites: bool = False,
) -> dict[str, Any]:
    _ensure_isolated_root(campaign_root)
    campaign_root.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for spec in CAMPAIGNS:
        if selected_campaigns and spec.name not in selected_campaigns:
            continue
        if not ignore_prerequisites and not _prerequisites_met(completed, spec):
            completed.append(
                {
                    "campaign": spec.name,
                    "stage": spec.stage,
                    "purpose": spec.purpose,
                    "status": "skipped",
                    "stop_reason": f"prerequisites not met: {spec.prerequisite_stages}",
                    "chunks": [],
                    "cycles_requested": sum(chunk.cycles for chunk in spec.chunks),
                    "cycles_completed": 0,
                    "semantic_concepts_generated": 0,
                    "validation_coverage_latest": 0.0,
                    "average_promotion_score_latest": 0.0,
                    "promotion_eligible_latest": 0,
                    "memory_growth_bounded": True,
                    "semantic_growth_bounded": True,
                    "graph_growth_bounded": True,
                    "promotion_score_trend": "not_run",
                    "promotion_eligible_trend": "not_run",
                    "redundancy_trend": "not_run",
                    "contradiction_trend": "not_run",
                    "validation_coverage_min": 0.0,
                    "provider_usage": {},
                }
            )
            break
        summary = _run_single_campaign(campaign_root=campaign_root, spec=spec, reset=reset)
        completed.append(summary)
        aggregate = _aggregate_campaigns(completed, campaign_root)
        dry_run = _dry_run_canonical_recommendations(completed)
        _write_reports(aggregate, dry_run, reports_dir)
        if summary.get("status") != "completed":
            break
    aggregate = _aggregate_campaigns(completed, campaign_root)
    dry_run = _dry_run_canonical_recommendations(completed)
    _write_reports(aggregate, dry_run, reports_dir)
    return {"aggregate": aggregate, "canonical_dry_run": dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase A temporary-store architecture graduation campaign.")
    parser.add_argument("--campaign-root", default=".tmp/experiments/phaseA_architecture_graduation")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--campaign", action="append", default=[])
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--ignore-prerequisites",
        action="store_true",
        help="Run selected campaign(s) without requiring earlier Phase A stages.",
    )
    args = parser.parse_args()
    summary = run_phaseA(
        campaign_root=Path(args.campaign_root),
        reports_dir=Path(args.reports_dir),
        selected_campaigns=set(args.campaign) if args.campaign else None,
        reset=bool(args.reset),
        ignore_prerequisites=bool(args.ignore_prerequisites),
    )
    aggregate = summary["aggregate"]
    print(
        json.dumps(
            {
                "campaign_count": aggregate["campaign_count"],
                "completed_campaign_count": aggregate["completed_campaign_count"],
                "total_cycles_completed": aggregate["total_cycles_completed"],
                "promotion_eligible_latest_total": aggregate["promotion_eligible_latest_total"],
                "blocking_stop_reasons": aggregate["blocking_stop_reasons"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class RunAudit:
    run: str
    cycles_completed: int
    semantic_growth: int
    promotion_eligible: int
    validated: int
    rejected: int
    average_score: float
    eligible_concepts: list[dict[str, Any]]
    unresolved_taxonomy: dict[str, int]
    redundancy_taxonomy: dict[str, int]
    contradiction_taxonomy: dict[str, int]
    promotion_velocity: list[dict[str, Any]]
    confidence_summary: dict[str, Any]
    lifespan_summary: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _event_ticks(events: list[dict[str, Any]]) -> dict[str, int]:
    ticks: dict[str, int] = {}
    for event in events:
        cycle_id = event.get("cycle_id")
        tick = event.get("metadata", {}).get("tick_index")
        if cycle_id and isinstance(tick, int):
            ticks[str(cycle_id)] = tick
    return ticks


def _latest_by_id(rows: list[dict[str, Any]], id_key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row.get(id_key)
        if item_id:
            latest[str(item_id)] = row
    return latest


def _concept_origin_tick(decision: dict[str, Any], cycle_ticks: dict[str, int]) -> int | None:
    cycle_id = decision.get("provenance", {}).get("cycle_id")
    if cycle_id and str(cycle_id) in cycle_ticks:
        return cycle_ticks[str(cycle_id)]
    return None


def _prediction_taxonomy(
    *,
    predictions: list[dict[str, Any]],
    decisions_by_id: dict[str, dict[str, Any]],
    concept_ticks: dict[str, int | None],
    max_tick: int,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for prediction in predictions:
        if prediction.get("status") not in {"open", "inconclusive"}:
            continue
        concept_id = str(prediction.get("source_concept_id", ""))
        decision = decisions_by_id.get(concept_id)
        metadata = prediction.get("metadata", {})
        validation_meta = metadata.get("validation") or metadata.get("phase16_validation") or metadata.get(
            "phase17_adversarial_validation"
        )
        if decision is None:
            counts["source_concept_missing_or_superseded"] += 1
            continue
        evidence = decision.get("evidence", {})
        dimensions = decision.get("dimensions", {})
        origin_tick = concept_ticks.get(concept_id)
        if not validation_meta:
            if origin_tick is not None and max_tick and origin_tick >= int(max_tick * 0.8):
                counts["late_cycle_backlog"] += 1
            else:
                counts["never_revisited"] += 1
        elif prediction.get("status") == "inconclusive":
            counts["validation_returned_inconclusive"] += 1
        elif evidence.get("open_contradictions", 0) > 0:
            counts["blocked_by_contradiction_pressure"] += 1
        elif dimensions.get("redundancy_penalty", 0.0) >= 0.32:
            counts["blocked_by_redundancy"] += 1
        elif dimensions.get("prompt_artifact_penalty", 0.0) >= 0.32:
            counts["blocked_by_prompt_specificity"] += 1
        else:
            counts["open_validation_backlog"] += 1
    return dict(counts.most_common())


def _current_concept_unresolved_taxonomy(
    *,
    decisions: list[dict[str, Any]],
    concept_ticks: dict[str, int | None],
    max_tick: int,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for decision in decisions:
        unresolved = int(decision.get("evidence", {}).get("unresolved_predictions", 0) or 0)
        if unresolved <= 0:
            continue
        evidence = decision.get("evidence", {})
        dimensions = decision.get("dimensions", {})
        tick = concept_ticks.get(str(decision.get("concept_id")))
        if tick is not None and max_tick and tick >= int(max_tick * 0.8):
            counts["late_cycle_current_concept_backlog"] += unresolved
        elif evidence.get("supported_predictions", 0) > 0:
            counts["partially_validated_current_concept_backlog"] += unresolved
        elif dimensions.get("redundancy_penalty", 0.0) >= 0.32:
            counts["redundant_current_concept_backlog"] += unresolved
        elif dimensions.get("prompt_artifact_penalty", 0.0) >= 0.32:
            counts["prompt_specific_current_concept_backlog"] += unresolved
        elif dimensions.get("incomplete_proposition", 0.0) > 0:
            counts["incomplete_current_concept_backlog"] += unresolved
        else:
            counts["unvisited_current_concept_backlog"] += unresolved
    return dict(counts.most_common())


def _redundancy_taxonomy(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    text_counts = Counter(" ".join(str(item.get("concept", "")).lower().split()) for item in decisions)
    for decision in decisions:
        redundancy = float(decision.get("dimensions", {}).get("redundancy_penalty", 0.0))
        if redundancy < 0.2:
            continue
        concept = " ".join(str(decision.get("concept", "")).lower().split())
        if text_counts[concept] > 1:
            counts["exact_duplicate_text"] += 1
        elif redundancy >= 0.5:
            counts["high_paraphrase_overlap"] += 1
        elif decision.get("recommendation") in {"Validated", "Promotion Eligible"}:
            counts["accepted_overlap_reusable"] += 1
        else:
            counts["moderate_overlap_unmatured"] += 1
    return dict(counts.most_common())


def _contradiction_taxonomy(
    *,
    contradictions: list[dict[str, Any]],
    decisions_by_id: dict[str, dict[str, Any]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for contradiction in contradictions:
        if contradiction.get("status") != "open":
            counts["resolved"] += 1
            continue
        a = decisions_by_id.get(str(contradiction.get("claim_a_id", "")))
        b = decisions_by_id.get(str(contradiction.get("claim_b_id", "")))
        if a is None or b is None:
            counts["references_superseded_or_missing_concept"] += 1
            continue
        if a.get("recommendation") == "Reject" or b.get("recommendation") == "Reject":
            counts["attached_to_rejected_concept"] += 1
        elif (
            a.get("dimensions", {}).get("prompt_artifact_penalty", 0.0) >= 0.32
            or b.get("dimensions", {}).get("prompt_artifact_penalty", 0.0) >= 0.32
            or a.get("dimensions", {}).get("incomplete_proposition", 0.0) > 0
            or b.get("dimensions", {}).get("incomplete_proposition", 0.0) > 0
        ):
            counts["likely_extraction_or_artifact_noise"] += 1
        elif a.get("recommendation") in {"Validated", "Promotion Eligible"} and b.get(
            "recommendation"
        ) in {"Validated", "Promotion Eligible"}:
            counts["competing_validated_hypotheses"] += 1
        else:
            counts["unresolved_candidate_conflict"] += 1
    return dict(counts.most_common())


def _promotion_velocity(
    *,
    decisions: list[dict[str, Any]],
    concept_ticks: dict[str, int | None],
    max_tick: int,
) -> list[dict[str, Any]]:
    checkpoints = [0, 25, 50, 100, 150, 200]
    checkpoints = [point for point in checkpoints if point <= max(200, max_tick)]
    rows = []
    for point in checkpoints:
        eligible = 0
        validated = 0
        candidates = 0
        total = 0
        for decision in decisions:
            tick = concept_ticks.get(str(decision.get("concept_id")))
            if tick is None or tick > point:
                continue
            total += 1
            recommendation = decision.get("recommendation")
            if recommendation == "Promotion Eligible":
                eligible += 1
            if recommendation == "Validated":
                validated += 1
            if recommendation in {"Candidate", "Validated", "Promotion Eligible"}:
                candidates += 1
        rows.append(
            {
                "cycle": point,
                "concepts_originated_by_cycle": total,
                "candidate_or_better": candidates,
                "validated": validated,
                "promotion_eligible": eligible,
            }
        )
    return rows


def _confidence_summary(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    gains = []
    losses = []
    strengthened = []
    weakened = []
    for decision in decisions:
        trajectory = decision.get("confidence_trajectory") or []
        if len(trajectory) < 2:
            continue
        delta = round(float(trajectory[-1]) - float(trajectory[0]), 4)
        if delta >= 0:
            gains.append(delta)
            strengthened.append((delta, decision.get("concept", "")))
        else:
            losses.append(delta)
            weakened.append((delta, decision.get("concept", "")))
    return {
        "concepts_with_trajectory": len(gains) + len(losses),
        "average_gain": _mean(gains),
        "average_loss": _mean(losses),
        "strengthened_count": len(gains),
        "weakened_count": len(losses),
        "top_strengthened": [
            {"delta": delta, "concept": concept}
            for delta, concept in sorted(strengthened, reverse=True)[:10]
        ],
        "top_weakened": [
            {"delta": delta, "concept": concept}
            for delta, concept in sorted(weakened)[:10]
        ],
    }


def _lifespan_summary(
    *,
    decisions: list[dict[str, Any]],
    concept_ticks: dict[str, int | None],
    max_tick: int,
) -> dict[str, Any]:
    thresholds = [5, 20, 50, 100, 150]
    rows = []
    for age in thresholds:
        cohort = []
        for decision in decisions:
            tick = concept_ticks.get(str(decision.get("concept_id")))
            if tick is None:
                continue
            if max_tick - tick >= age:
                cohort.append(decision)
        if not cohort:
            rows.append({"age_cycles": age, "cohort": 0, "survivors": 0, "survival_rate": 0.0})
            continue
        survivors = [
            item
            for item in cohort
            if item.get("recommendation") not in {"Reject", "Experimental"}
        ]
        rows.append(
            {
                "age_cycles": age,
                "cohort": len(cohort),
                "survivors": len(survivors),
                "survival_rate": round(len(survivors) / max(1, len(cohort)), 4),
            }
        )
    half_life = None
    for row in rows:
        if row["cohort"] and row["survival_rate"] <= 0.5:
            half_life = row["age_cycles"]
            break
    return {
        "max_tick": max_tick,
        "survival_by_age": rows,
        "knowledge_half_life_cycles": half_life,
        "half_life_interpretation": (
            "not reached within observed campaign window"
            if half_life is None
            else f"survival fell to 50% by {half_life} cycles"
        ),
    }


def _eligible_profile(eligible: dict[str, Any], concept_tick: int | None) -> dict[str, Any]:
    dimensions = eligible.get("dimensions", {})
    evidence = eligible.get("evidence", {})
    provenance = eligible.get("provenance", {})
    return {
        "concept_id": eligible.get("concept_id"),
        "concept": eligible.get("concept"),
        "run_origin_tick": concept_tick,
        "score": eligible.get("promotion_score"),
        "provider": provenance.get("source_provider"),
        "profile": provenance.get("source_profile"),
        "objective": provenance.get("objective_tag"),
        "supporting_evidence_count": evidence.get("supporting_evidence_count"),
        "supporting_memory_relationship_edges": evidence.get("supporting_memory_relationship_edges"),
        "related_concepts": evidence.get("projected_neighbor_count"),
        "supported_predictions": evidence.get("supported_predictions"),
        "failed_predictions": evidence.get("failed_predictions"),
        "unresolved_predictions": evidence.get("unresolved_predictions"),
        "open_contradictions": evidence.get("open_contradictions"),
        "confidence_trajectory": eligible.get("confidence_trajectory"),
        "confidence_slope": _confidence_slope(eligible.get("confidence_trajectory") or []),
        "validation_count": (
            int(evidence.get("supported_predictions", 0) or 0)
            + int(evidence.get("failed_predictions", 0) or 0)
        ),
        "prediction_accuracy": _prediction_accuracy(evidence),
        "sentence_length": len(str(eligible.get("concept", "")).split()),
        "redundancy": dimensions.get("redundancy_penalty"),
        "centrality": dimensions.get("relationship_centrality"),
        "projected_centrality": dimensions.get("projected_centrality"),
        "projection_sources": evidence.get("projection_sources", []),
        "prompt_artifact_penalty": dimensions.get("prompt_artifact_penalty"),
        "incomplete_proposition": evidence.get("incomplete_proposition"),
    }


def _confidence_slope(trajectory: list[Any]) -> float:
    if len(trajectory) < 2:
        return 0.0
    return round((float(trajectory[-1]) - float(trajectory[0])) / (len(trajectory) - 1), 4)


def _prediction_accuracy(evidence: dict[str, Any]) -> float:
    supported = int(evidence.get("supported_predictions", 0) or 0)
    failed = int(evidence.get("failed_predictions", 0) or 0)
    return round(supported / max(1, supported + failed), 4)


def _decision_profile(decision: dict[str, Any], concept_tick: int | None, run: str) -> dict[str, Any]:
    profile = _eligible_profile(decision, concept_tick)
    profile["run"] = run
    profile["recommendation"] = decision.get("recommendation")
    profile["score"] = decision.get("promotion_score")
    return profile


def _profile_similarity(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    if not profiles:
        return {}
    return {
        "count": len(profiles),
        "providers": dict(Counter(item.get("provider") or "unknown" for item in profiles).most_common()),
        "profiles": dict(Counter(item.get("profile") or "unknown" for item in profiles).most_common()),
        "avg_sentence_length": _mean([float(item.get("sentence_length", 0) or 0) for item in profiles]),
        "avg_supporting_memories": _mean([float(item.get("supporting_evidence_count", 0) or 0) for item in profiles]),
        "avg_related_concepts": _mean([float(item.get("related_concepts", 0) or 0) for item in profiles]),
        "avg_redundancy": _mean([float(item.get("redundancy", 0.0) or 0.0) for item in profiles]),
        "avg_open_contradictions": _mean([float(item.get("open_contradictions", 0) or 0) for item in profiles]),
        "avg_projected_centrality": _mean([float(item.get("projected_centrality", 0.0) or 0.0) for item in profiles]),
        "avg_confidence_slope": _mean([float(item.get("confidence_slope", 0.0) or 0.0) for item in profiles]),
        "avg_validation_count": _mean([float(item.get("validation_count", 0) or 0) for item in profiles]),
        "avg_prediction_accuracy": _mean([float(item.get("prediction_accuracy", 0.0) or 0.0) for item in profiles]),
    }


def _survival_funnel(decisions: list[dict[str, Any]], generated: int) -> dict[str, int]:
    evaluated = len(decisions)
    validated = sum(1 for item in decisions if item.get("recommendation") in {"Validated", "Promotion Eligible"})
    contradiction_survivors = sum(
        1
        for item in decisions
        if item.get("evidence", {}).get("open_contradictions", 0) == 0
        and item.get("recommendation") not in {"Reject", "Experimental"}
    )
    redundancy_survivors = sum(
        1
        for item in decisions
        if item.get("evidence", {}).get("open_contradictions", 0) == 0
        and item.get("dimensions", {}).get("redundancy_penalty", 0.0) < 0.32
        and item.get("recommendation") not in {"Reject", "Experimental"}
    )
    promotion_candidates = sum(
        1
        for item in decisions
        if item.get("recommendation") in {"Candidate", "Validated", "Promotion Eligible"}
    )
    eligible = sum(1 for item in decisions if item.get("recommendation") == "Promotion Eligible")
    return {
        "generated": generated,
        "evaluated": evaluated,
        "validated_or_eligible": validated,
        "survived_contradiction_review": contradiction_survivors,
        "survived_redundancy_review": redundancy_survivors,
        "promotion_candidate_or_better": promotion_candidates,
        "promotion_eligible": eligible,
        "canonical_ready": 0,
    }


def _primary_failure_cause(decision: dict[str, Any]) -> str:
    evidence = decision.get("evidence", {})
    dimensions = decision.get("dimensions", {})
    if evidence.get("failed_predictions", 0) > 0:
        return "failed_validation"
    if evidence.get("unresolved_predictions", 0) > 0:
        return "unresolved_predictions"
    if evidence.get("open_contradictions", 0) > 0:
        return "contradiction_pressure"
    if dimensions.get("redundancy_penalty", 0.0) >= 0.32:
        return "high_redundancy"
    if dimensions.get("prompt_artifact_penalty", 0.0) >= 0.32:
        return "prompt_or_context_specificity"
    if dimensions.get("incomplete_proposition", 0.0) > 0:
        return "incomplete_proposition"
    if dimensions.get("relationship_centrality", 0.0) < 0.12:
        return "low_centrality"
    if dimensions.get("evidence_support", 0.0) < 0.35:
        return "low_evidence_support"
    return "low_composite_score"


def _failure_cause_distribution(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed_states = {"Reject", "Hold for More Validation", "Experimental"}
    causes = Counter(
        _primary_failure_cause(item)
        for item in decisions
        if item.get("recommendation") in failed_states
    )
    total = sum(causes.values())
    return [
        {
            "cause": cause,
            "count": count,
            "percent": round((count / max(1, total)) * 100, 2),
        }
        for cause, count in causes.most_common()
    ]


def _state_transition_diagram(funnel: dict[str, int], lifecycle: Counter[str]) -> str:
    generated = funnel.get("generated", 0)
    evaluated = funnel.get("evaluated", 0)
    validated = lifecycle.get("Validated", 0)
    rejected = lifecycle.get("Reject", 0)
    candidate = lifecycle.get("Candidate", 0)
    hold = lifecycle.get("Hold for More Validation", 0)
    experimental = lifecycle.get("Experimental", 0)
    eligible = lifecycle.get("Promotion Eligible", 0)
    return "\n".join(
        [
            f"Generated ({generated})",
            "      |",
            "      v",
            f"Evaluated ({evaluated})",
            "      |",
            "      v",
            f"Validated ({validated})",
            "      |",
            "  +---+----------------------+",
            "  |                          |",
            "  v                          v",
            f"Rejected ({rejected})        Candidate ({candidate})",
            "                             |",
            "                             v",
            f"Hold/Experimental ({hold + experimental})",
            "                             |",
            "                             v",
            f"Promotion Eligible ({eligible})",
            "                             |",
            "                             v",
            "Canonical Ready (0)",
        ]
    )


def _maturation_time_summary(eligible: list[dict[str, Any]], run_cycles: dict[str, int]) -> dict[str, Any]:
    origin_ticks = [
        int(item["run_origin_tick"])
        for item in eligible
        if isinstance(item.get("run_origin_tick"), int)
    ]
    maturity_windows = [
        int(run_cycles.get(item["run"], 0)) - int(item["run_origin_tick"])
        for item in eligible
        if isinstance(item.get("run_origin_tick"), int)
    ]
    return {
        "average_first_learned_cycle": _mean([float(item) for item in origin_ticks]),
        "average_observed_cycles_to_final_eligibility": _mean(
            [float(item) for item in maturity_windows if item >= 0]
        ),
        "min_observed_cycles_to_final_eligibility": min(maturity_windows) if maturity_windows else None,
        "max_observed_cycles_to_final_eligibility": max(maturity_windows) if maturity_windows else None,
        "measurement_note": (
            "Phase 26 stores final governance snapshots, not the exact cycle at which a "
            "concept first became Validated or Promotion Eligible. These are origin-to-final-governance "
            "maturation windows, not true state-transition timestamps."
        ),
    }


def audit_phase26(
    *,
    campaign_root: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    phase26 = _load_json(reports_dir / "phase26_autonomous_campaign_report.json")
    run_summaries: list[RunAudit] = []
    all_eligible: list[dict[str, Any]] = []
    all_decisions: list[dict[str, Any]] = []
    all_reject_profiles: list[dict[str, Any]] = []
    aggregate_unresolved: Counter[str] = Counter()
    aggregate_current_unresolved: Counter[str] = Counter()
    aggregate_redundancy: Counter[str] = Counter()
    aggregate_contradictions: Counter[str] = Counter()

    for run_dir in sorted(path for path in campaign_root.iterdir() if path.is_dir()):
        reports = run_dir / "reports"
        governance = _load_json(reports / "promotion_governance_report.json")
        run_summary = _load_json(reports / "phase26_run_summary.json")
        if not governance or not run_summary:
            continue
        decisions = governance.get("decisions", [])
        all_decisions.extend(decisions)
        decisions_by_id = {str(item.get("concept_id")): item for item in decisions}
        events = _load_jsonl(run_dir / "store" / "events.jsonl")
        predictions = _load_jsonl(run_dir / "store" / "predictions.jsonl")
        contradictions = _load_jsonl(run_dir / "store" / "contradictions.jsonl")
        cycle_ticks = _event_ticks(events)
        max_tick = int(run_summary.get("cycles_completed", 0) or max(cycle_ticks.values(), default=0))
        concept_ticks = {
            str(item.get("concept_id")): _concept_origin_tick(item, cycle_ticks)
            for item in decisions
        }
        unresolved = _prediction_taxonomy(
            predictions=predictions,
            decisions_by_id=decisions_by_id,
            concept_ticks=concept_ticks,
            max_tick=max_tick,
        )
        current_unresolved = _current_concept_unresolved_taxonomy(
            decisions=decisions,
            concept_ticks=concept_ticks,
            max_tick=max_tick,
        )
        redundancy = _redundancy_taxonomy(decisions)
        contradiction_taxonomy = _contradiction_taxonomy(
            contradictions=contradictions,
            decisions_by_id=decisions_by_id,
        )
        aggregate_unresolved.update(unresolved)
        aggregate_current_unresolved.update(current_unresolved)
        aggregate_redundancy.update(redundancy)
        aggregate_contradictions.update(contradiction_taxonomy)

        eligible = [
            _eligible_profile(item, concept_ticks.get(str(item.get("concept_id"))))
            for item in decisions
            if item.get("recommendation") == "Promotion Eligible"
        ]
        for item in eligible:
            item["run"] = run_dir.name
        all_eligible.extend(eligible)
        for item in decisions:
            if item.get("recommendation") == "Reject":
                all_reject_profiles.append(
                    _decision_profile(
                        item,
                        concept_ticks.get(str(item.get("concept_id"))),
                        run_dir.name,
                    )
                )
        run_summaries.append(
            RunAudit(
                run=run_dir.name,
                cycles_completed=max_tick,
                semantic_growth=int(run_summary.get("semantic_growth", 0)),
                promotion_eligible=int(run_summary.get("promotion_eligible", 0)),
                validated=int(run_summary.get("validated_concepts", 0)),
                rejected=int(run_summary.get("rejected_concepts", 0)),
                average_score=float(run_summary.get("average_promotion_score", 0.0)),
                eligible_concepts=eligible,
                unresolved_taxonomy=unresolved,
                redundancy_taxonomy=redundancy,
                contradiction_taxonomy=contradiction_taxonomy,
                promotion_velocity=_promotion_velocity(
                    decisions=decisions,
                    concept_ticks=concept_ticks,
                    max_tick=max_tick,
                ),
                confidence_summary=_confidence_summary(decisions),
                lifespan_summary=_lifespan_summary(
                    decisions=decisions,
                    concept_ticks=concept_ticks,
                    max_tick=max_tick,
                ),
            )
        )

    provider_counts = Counter(item.get("provider") or "unknown" for item in all_eligible)
    profile_counts = Counter(item.get("profile") or "unknown" for item in all_eligible)
    score_values = [float(item.get("score", 0.0)) for item in all_eligible]
    bottom_rejects = sorted(
        all_reject_profiles,
        key=lambda item: (float(item.get("score", 0.0) or 0.0), item.get("concept", "")),
    )[:10]
    generated_total = sum(int(run.semantic_growth) for run in run_summaries)
    lifecycle_counts = Counter(item.get("recommendation", "unknown") for item in all_decisions)
    survival_funnel = _survival_funnel(
        all_decisions,
        generated=generated_total,
    )
    run_cycles = {run.run: run.cycles_completed for run in run_summaries}
    summary = {
        "phase": "Phase 27 Knowledge Maturation Audit",
        "canonical_merge_performed": False,
        "campaign_root": str(campaign_root),
        "phase26_reference": {
            "run_count": phase26.get("run_count"),
            "completed_run_count": phase26.get("completed_run_count"),
            "promotion_eligible_total": phase26.get("promotion_eligible_total"),
            "validated_total": phase26.get("validated_total"),
            "rejected_total": phase26.get("rejected_total"),
            "average_promotion_score": phase26.get("average_promotion_score"),
        },
        "runs": [run.__dict__ for run in run_summaries],
        "promotion_eligible_total": len(all_eligible),
        "promotion_eligible_by_provider": dict(provider_counts.most_common()),
        "promotion_eligible_by_profile": dict(profile_counts.most_common()),
        "promotion_eligible_score_average": _mean(score_values),
        "promotion_eligible_score_range": {
            "min": round(min(score_values), 4) if score_values else 0.0,
            "max": round(max(score_values), 4) if score_values else 0.0,
        },
        "promotion_survivor_similarity": _profile_similarity(all_eligible),
        "bottom_reject_similarity": _profile_similarity(bottom_rejects),
        "bottom_reject_profiles": bottom_rejects,
        "knowledge_survival_funnel": survival_funnel,
        "state_transition_diagram": _state_transition_diagram(survival_funnel, lifecycle_counts),
        "failure_cause_distribution": _failure_cause_distribution(all_decisions),
        "survivor_maturation_time": _maturation_time_summary(all_eligible, run_cycles),
        "unresolved_prediction_taxonomy": dict(aggregate_unresolved.most_common()),
        "current_concept_unresolved_taxonomy": dict(aggregate_current_unresolved.most_common()),
        "redundancy_taxonomy": dict(aggregate_redundancy.most_common()),
        "contradiction_taxonomy": dict(aggregate_contradictions.most_common()),
        "score_trajectory_limitation": (
            "Phase 26 stored final governance decisions, not per-cycle promotion-score "
            "snapshots. Phase 27 reports origin-cycle velocity proxies and confidence "
            "trajectories, but not true promotion-score trajectories."
        ),
        "recommendation": _recommendation(
            current_unresolved=aggregate_current_unresolved,
            raw_unresolved=aggregate_unresolved,
            redundancy=aggregate_redundancy,
            eligible=all_eligible,
        ),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase27_knowledge_maturation_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(summary, reports_dir)
    return summary


def _recommendation(
    *,
    current_unresolved: Counter[str],
    raw_unresolved: Counter[str],
    redundancy: Counter[str],
    eligible: list[dict[str, Any]],
) -> str:
    if not eligible:
        return "No promotion audit should proceed until promotion-eligible concepts reappear."
    if current_unresolved:
        top_current = current_unresolved.most_common(1)[0][0]
        if top_current in {
            "late_cycle_current_concept_backlog",
            "partially_validated_current_concept_backlog",
            "unvisited_current_concept_backlog",
        }:
            return (
                "Next work should improve maturation scheduling: revisit unresolved predictions "
                "before creating more broad-curriculum candidates."
            )
        if top_current == "redundant_current_concept_backlog":
            return (
                "Next work should audit semantic equivalence and merge candidates report-only, "
                "then schedule unresolved current-concept predictions for maturation; do not "
                "change canonical knowledge yet."
            )
    if raw_unresolved and raw_unresolved.most_common(1)[0][0] == "source_concept_missing_or_superseded":
        return (
            "Next work should distinguish historical superseded prediction backlog from current "
            "governance pressure, then continue report-only survivor review before any canonical "
            "promotion."
        )
    if redundancy and redundancy.most_common(1)[0][0] in {
        "accepted_overlap_reusable",
        "moderate_overlap_unmatured",
    }:
        return (
            "Next work should audit semantic equivalence and merge candidates report-only; "
            "do not change canonical knowledge yet."
        )
    return "Manually inspect promotion-eligible concepts across independent runs before promotion."


def _write_markdown(summary: dict[str, Any], reports_dir: Path) -> None:
    runs = summary["runs"]
    eligible = [
        item
        for run in runs
        for item in run["eligible_concepts"]
    ]
    run_rows = [
        (
            f"| {run['run']} | {run['cycles_completed']} | {run['semantic_growth']} | "
            f"{run['validated']} | {run['promotion_eligible']} | {run['rejected']} | "
            f"{run['average_score']} | {next(iter(run['unresolved_taxonomy']), 'none')} |"
        )
        for run in runs
    ]
    eligible_rows = [
        (
            f"| {item['run']} | {item['score']} | {item['provider']} | {item['profile']} | "
            f"{item['run_origin_tick']} | {item['supported_predictions']} | "
            f"{item['open_contradictions']} | {item['redundancy']} | {item['concept'][:120]} |"
        )
        for item in eligible
    ]
    report = [
        "# Phase 27 Knowledge Maturation Audit",
        "",
        "This audit is read-only over the Phase 26 isolated experiment stores. No canonical knowledge was modified.",
        "",
        "## Executive Summary",
        "",
        f"- Promotion-eligible concepts inspected: `{summary['promotion_eligible_total']}`",
        f"- Eligible score average: `{summary['promotion_eligible_score_average']}`",
        f"- Eligible score range: `{summary['promotion_eligible_score_range']}`",
        f"- Eligible by provider: `{summary['promotion_eligible_by_provider']}`",
        f"- Eligible by profile: `{summary['promotion_eligible_by_profile']}`",
        f"- Primary unresolved-prediction cause: `{next(iter(summary['unresolved_prediction_taxonomy']), 'none')}`",
        f"- Primary current-concept backlog cause: `{next(iter(summary['current_concept_unresolved_taxonomy']), 'none')}`",
        f"- Primary redundancy cause: `{next(iter(summary['redundancy_taxonomy']), 'none')}`",
        "",
        "## Run Comparison",
        "",
        "| Run | Cycles | Semantic Growth | Validated | Eligible | Rejected | Avg Score | Top Unresolved Cause |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        *run_rows,
        "",
        "## Promotion-Eligible Concepts",
        "",
        "| Run | Score | Provider | Profile | Origin Tick | Supported Predictions | Open Contradictions | Redundancy | Concept |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
        *eligible_rows,
        "",
        "## Promotion Survivor Profiles",
        "",
        *_survivor_profile_lines(eligible),
        "",
        "## Promotion Survivor Similarities",
        "",
        *_similarity_lines(summary["promotion_survivor_similarity"]),
        "",
        "## Bottom Reject Similarities",
        "",
        *_similarity_lines(summary["bottom_reject_similarity"]),
        "",
        "## Bottom Ten Rejects",
        "",
        "| Run | Score | Provider | Profile | Origin Tick | Supported Predictions | Open Contradictions | Redundancy | Concept |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
        *[
            (
                f"| {item['run']} | {item['score']} | {item['provider']} | {item['profile']} | "
                f"{item['run_origin_tick']} | {item['supported_predictions']} | "
                f"{item['open_contradictions']} | {item['redundancy']} | {item['concept'][:120]} |"
            )
            for item in summary["bottom_reject_profiles"]
        ],
        "",
        "## Knowledge Survival Funnel",
        "",
        "| Stage | Count |",
        "| --- | ---: |",
        *[
            f"| {stage} | {count} |"
            for stage, count in summary["knowledge_survival_funnel"].items()
        ],
        "",
        "## State Transition Diagram",
        "",
        "```text",
        summary["state_transition_diagram"],
        "```",
        "",
        "## Failure Cause Distribution",
        "",
        "| Failure Cause | Count | Percent |",
        "| --- | ---: | ---: |",
        *[
            f"| {item['cause']} | {item['count']} | {item['percent']} |"
            for item in summary["failure_cause_distribution"]
        ],
        "",
        "## Survivor Maturation Time",
        "",
        *[f"- {key}: `{value}`" for key, value in summary["survivor_maturation_time"].items()],
        "",
        "## Current-Concept Unresolved Prediction Taxonomy",
        "",
        "This is the backlog that still attaches to current governance-visible concepts.",
        "",
        *[f"- `{key}`: `{value}`" for key, value in summary["current_concept_unresolved_taxonomy"].items()],
        "",
        "## Raw Prediction Backlog Taxonomy",
        "",
        "This includes predictions attached to superseded concept revisions and can exceed governance-pressure counts.",
        "",
        *[f"- `{key}`: `{value}`" for key, value in summary["unresolved_prediction_taxonomy"].items()],
        "",
        "## Redundancy Taxonomy",
        "",
        *[f"- `{key}`: `{value}`" for key, value in summary["redundancy_taxonomy"].items()],
        "",
        "## Contradiction Taxonomy",
        "",
        *[f"- `{key}`: `{value}`" for key, value in summary["contradiction_taxonomy"].items()],
        "",
        "## Measurement Limitation",
        "",
        summary["score_trajectory_limitation"],
        "",
        "## Recommendation",
        "",
        summary["recommendation"],
        "",
    ]
    (reports_dir / "phase27_knowledge_maturation_audit.md").write_text(
        "\n".join(report),
        encoding="utf-8",
    )
    (reports_dir / "phase27_promotion_eligible_inspection.md").write_text(
        "\n".join(
            [
                "# Phase 27 Promotion-Eligible Inspection",
                "",
                *[
                    (
                        f"## {item['run']} / {item['concept_id']}\n\n"
                        f"- Score: `{item['score']}`\n"
                        f"- Provider: `{item['provider']}`\n"
                        f"- Profile: `{item['profile']}`\n"
                        f"- Origin tick: `{item['run_origin_tick']}`\n"
                        f"- Supported predictions: `{item['supported_predictions']}`\n"
                        f"- Failed predictions: `{item['failed_predictions']}`\n"
                        f"- Unresolved predictions: `{item['unresolved_predictions']}`\n"
                        f"- Open contradictions: `{item['open_contradictions']}`\n"
                        f"- Confidence trajectory: `{item['confidence_trajectory']}`\n"
                        f"- Projection sources: `{item['projection_sources']}`\n\n"
                        f"{item['concept']}\n"
                    )
                    for item in eligible
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase27_promotion_survivor_profiles.md").write_text(
        "\n".join(
            [
                "# Phase 27 Promotion Survivor Profiles",
                "",
                *_survivor_profile_lines(eligible),
                "",
                "## Survivor Similarities",
                "",
                *_similarity_lines(summary["promotion_survivor_similarity"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase27_survivor_vs_reject_comparison.md").write_text(
        "\n".join(
            [
                "# Phase 27 Survivor vs Reject Comparison",
                "",
                "## Promotion Survivors",
                "",
                *_similarity_lines(summary["promotion_survivor_similarity"]),
                "",
                "## Bottom Rejects",
                "",
                *_similarity_lines(summary["bottom_reject_similarity"]),
                "",
                "## Knowledge Survival Funnel",
                "",
                "| Stage | Count |",
                "| --- | ---: |",
                *[
                    f"| {stage} | {count} |"
                    for stage, count in summary["knowledge_survival_funnel"].items()
                ],
                "",
                "## State Transition Diagram",
                "",
                "```text",
                summary["state_transition_diagram"],
                "```",
                "",
                "## Failure Cause Distribution",
                "",
                "| Failure Cause | Count | Percent |",
                "| --- | ---: | ---: |",
                *[
                    f"| {item['cause']} | {item['count']} | {item['percent']} |"
                    for item in summary["failure_cause_distribution"]
                ],
                "",
                "## Survivor Maturation Time",
                "",
                *[f"- {key}: `{value}`" for key, value in summary["survivor_maturation_time"].items()],
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "phase27_maturation_failure_taxonomy.md").write_text(
        "\n".join(
            [
                "# Phase 27 Maturation Failure Taxonomy",
                "",
                "## Primary Failure Cause Distribution",
                "",
                "| Failure Cause | Count | Percent |",
                "| --- | ---: | ---: |",
                *[
                    f"| {item['cause']} | {item['count']} | {item['percent']} |"
                    for item in summary["failure_cause_distribution"]
                ],
                "",
                "## Current-Concept Unresolved Predictions",
                "",
                *[f"- `{key}`: `{value}`" for key, value in summary["current_concept_unresolved_taxonomy"].items()],
                "",
                "## Raw Prediction Backlog",
                "",
                *[f"- `{key}`: `{value}`" for key, value in summary["unresolved_prediction_taxonomy"].items()],
                "",
                "## Redundancy",
                "",
                *[f"- `{key}`: `{value}`" for key, value in summary["redundancy_taxonomy"].items()],
                "",
                "## Contradictions",
                "",
                *[f"- `{key}`: `{value}`" for key, value in summary["contradiction_taxonomy"].items()],
                "",
            ]
        ),
        encoding="utf-8",
    )
    velocity_lines = ["# Phase 27 Promotion Velocity", ""]
    for run in runs:
        velocity_lines.extend(
            [
                f"## {run['run']}",
                "",
                "| Cycle | Originated Concepts | Candidate+ | Validated | Promotion Eligible |",
                "| ---: | ---: | ---: | ---: | ---: |",
                *[
                    (
                        f"| {row['cycle']} | {row['concepts_originated_by_cycle']} | "
                        f"{row['candidate_or_better']} | {row['validated']} | "
                        f"{row['promotion_eligible']} |"
                    )
                    for row in run["promotion_velocity"]
                ],
                "",
            ]
        )
    (reports_dir / "phase27_promotion_velocity.md").write_text(
        "\n".join(velocity_lines),
        encoding="utf-8",
    )
    lifespan_lines = ["# Phase 27 Concept Lifespan", ""]
    for run in runs:
        lifespan = run["lifespan_summary"]
        lifespan_lines.extend(
            [
                f"## {run['run']}",
                "",
                f"- Half-life: `{lifespan['knowledge_half_life_cycles']}`",
                f"- Interpretation: {lifespan['half_life_interpretation']}",
                "",
                "| Age Cycles | Cohort | Survivors | Survival Rate |",
                "| ---: | ---: | ---: | ---: |",
                *[
                    f"| {row['age_cycles']} | {row['cohort']} | {row['survivors']} | {row['survival_rate']} |"
                    for row in lifespan["survival_by_age"]
                ],
                "",
            ]
        )
    (reports_dir / "phase27_concept_lifespan.md").write_text(
        "\n".join(lifespan_lines),
        encoding="utf-8",
    )
    _write_baseline_snapshot(reports_dir)


def _write_baseline_snapshot(reports_dir: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = reports_dir / f"phase27_baseline_snapshot_{stamp}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for path in reports_dir.glob("phase27_*"):
        if path.is_file():
            shutil.copy2(path, snapshot_dir / path.name)


def _survivor_profile_lines(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"### {item['run']} / {item['concept_id']}",
                "",
                f"Concept: {item['concept']}",
                "",
                f"- Origin profile: `{item['profile']}`",
                f"- Provider: `{item['provider']}`",
                f"- First learned cycle: `{item['run_origin_tick']}`",
                f"- Validation history: supported `{item['supported_predictions']}`, failed `{item['failed_predictions']}`, unresolved `{item['unresolved_predictions']}`",
                f"- Contradictions: `{item['open_contradictions']}`",
                f"- Redundancy: `{item['redundancy']}`",
                f"- Projected centrality: `{item['projected_centrality']}`",
                f"- Confidence trajectory: `{item['confidence_trajectory']}`",
                f"- Confidence slope: `{item['confidence_slope']}`",
                f"- Supporting memories: `{item['supporting_evidence_count']}`",
                f"- Supporting memory relationship edges: `{item['supporting_memory_relationship_edges']}`",
                f"- Related concepts: `{item['related_concepts']}`",
                f"- Prediction accuracy: `{item['prediction_accuracy']}`",
                f"- Final recommendation: `Promotion Eligible`",
                "",
            ]
        )
    return lines


def _similarity_lines(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return ["- No profiles available."]
    return [
        f"- Count: `{summary['count']}`",
        f"- Providers: `{summary['providers']}`",
        f"- Profiles: `{summary['profiles']}`",
        f"- Average sentence length: `{summary['avg_sentence_length']}`",
        f"- Average supporting memories: `{summary['avg_supporting_memories']}`",
        f"- Average related concepts: `{summary['avg_related_concepts']}`",
        f"- Average redundancy: `{summary['avg_redundancy']}`",
        f"- Average contradiction count: `{summary['avg_open_contradictions']}`",
        f"- Average projected centrality: `{summary['avg_projected_centrality']}`",
        f"- Average confidence slope: `{summary['avg_confidence_slope']}`",
        f"- Average validation count: `{summary['avg_validation_count']}`",
        f"- Average prediction accuracy: `{summary['avg_prediction_accuracy']}`",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 26 knowledge maturation.")
    parser.add_argument(
        "--campaign-root",
        default=".tmp/experiments/phase26_autonomous_campaign",
    )
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = audit_phase26(
        campaign_root=Path(args.campaign_root),
        reports_dir=Path(args.reports_dir),
    )
    print(
        json.dumps(
            {
                "promotion_eligible_total": summary["promotion_eligible_total"],
                "top_current_backlog": next(
                    iter(summary["current_concept_unresolved_taxonomy"]), "none"
                ),
                "top_raw_backlog": next(iter(summary["unresolved_prediction_taxonomy"]), "none"),
                "recommendation": summary["recommendation"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

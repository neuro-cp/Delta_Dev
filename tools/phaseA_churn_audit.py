from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(text).lower()))


def _jaccard(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 4)


def _governance_path(campaign_root: Path, chunk_index: int) -> Path:
    return (
        campaign_root
        / "chunks"
        / f"chunk_{chunk_index:03d}"
        / "reports"
        / "promotion_governance_report.json"
    )


def _decisions_by_id(campaign_root: Path, chunk_index: int) -> dict[str, dict[str, Any]]:
    data = _load_json(_governance_path(campaign_root, chunk_index))
    return {
        str(item.get("concept_id")): item
        for item in data.get("decisions", [])
        if item.get("concept_id")
    }


def _eligible(decisions: dict[str, dict[str, Any]]) -> set[str]:
    return {
        concept_id
        for concept_id, decision in decisions.items()
        if decision.get("recommendation") == "Promotion Eligible"
    }


def _failure_signature(previous: dict[str, Any], current: dict[str, Any] | None) -> dict[str, Any]:
    if current is None:
        return {
            "cause": "missing_or_superseded",
            "score_delta": None,
            "reason": "concept id disappeared from the next governance snapshot",
        }
    previous_score = float(previous.get("promotion_score", 0.0) or 0.0)
    current_score = float(current.get("promotion_score", 0.0) or 0.0)
    evidence = current.get("evidence", {})
    dimensions = current.get("dimensions", {})
    if evidence.get("failed_predictions", 0) > 0:
        cause = "failed_validation"
    elif evidence.get("open_contradictions", 0) > 0:
        cause = "contradiction_pressure"
    elif evidence.get("unresolved_predictions", 0) > 0:
        cause = "unresolved_predictions"
    elif dimensions.get("redundancy_penalty", 0.0) > previous.get("dimensions", {}).get("redundancy_penalty", 0.0):
        cause = "threshold_edge_redundancy_increase"
    elif current_score < previous_score:
        cause = "threshold_edge_score_decrease"
    else:
        cause = "state_reclassification_without_quality_loss"
    return {
        "cause": cause,
        "score_delta": round(current_score - previous_score, 4),
        "previous_score": previous_score,
        "current_score": current_score,
        "previous_recommendation": previous.get("recommendation"),
        "current_recommendation": current.get("recommendation"),
        "supported_predictions": evidence.get("supported_predictions", 0),
        "failed_predictions": evidence.get("failed_predictions", 0),
        "unresolved_predictions": evidence.get("unresolved_predictions", 0),
        "open_contradictions": evidence.get("open_contradictions", 0),
        "previous_redundancy": previous.get("dimensions", {}).get("redundancy_penalty", 0.0),
        "current_redundancy": dimensions.get("redundancy_penalty", 0.0),
    }


def _best_replacement(
    lost_decision: dict[str, Any],
    current_new_ids: set[str],
    current_decisions: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = []
    lost_text = str(lost_decision.get("concept", ""))
    lost_score = float(lost_decision.get("promotion_score", 0.0) or 0.0)
    for concept_id in current_new_ids:
        decision = current_decisions.get(concept_id)
        if not decision:
            continue
        similarity = _jaccard(lost_text, str(decision.get("concept", "")))
        candidates.append(
            {
                "concept_id": concept_id,
                "similarity": similarity,
                "score": float(decision.get("promotion_score", 0.0) or 0.0),
                "score_delta_vs_lost": round(float(decision.get("promotion_score", 0.0) or 0.0) - lost_score, 4),
                "concept": decision.get("concept", ""),
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["similarity"], item["score"]))


def audit_churn(*, campaign_root: Path, reports_dir: Path) -> dict[str, Any]:
    checkpoint = _load_json(campaign_root / "phaseA_checkpoint.json")
    chunks = checkpoint.get("chunks", [])
    events: list[dict[str, Any]] = []
    cause_counts: Counter[str] = Counter()
    harmful_losses = 0
    healthy_expansions = 0
    threshold_edge_losses = 0
    for index in range(1, len(chunks)):
        previous_chunk = chunks[index - 1]
        current_chunk = chunks[index]
        previous_index = int(previous_chunk["chunk_index"])
        current_index = int(current_chunk["chunk_index"])
        previous_decisions = _decisions_by_id(campaign_root, previous_index)
        current_decisions = _decisions_by_id(campaign_root, current_index)
        previous_eligible = _eligible(previous_decisions)
        current_eligible = _eligible(current_decisions)
        lost = previous_eligible - current_eligible
        new = current_eligible - previous_eligible
        stayed = previous_eligible & current_eligible
        if new and not lost:
            healthy_expansions += 1
        loss_events = []
        for concept_id in sorted(lost):
            previous = previous_decisions.get(concept_id, {})
            current = current_decisions.get(concept_id)
            signature = _failure_signature(previous, current)
            replacement = _best_replacement(previous, new, current_decisions)
            cause_counts[signature["cause"]] += 1
            if signature["cause"].startswith("threshold_edge"):
                threshold_edge_losses += 1
            else:
                harmful_losses += 1
            loss_events.append(
                {
                    "concept_id": concept_id,
                    "concept": previous.get("concept", ""),
                    "signature": signature,
                    "best_new_replacement": replacement,
                }
            )
        events.append(
            {
                "transition": f"chunk_{previous_index:03d}_to_chunk_{current_index:03d}",
                "previous_eligible": len(previous_eligible),
                "current_eligible": len(current_eligible),
                "stayed": len(stayed),
                "lost": len(lost),
                "new": len(new),
                "reported_churn": current_chunk.get("promotion_churn", {}).get("churn_rate"),
                "interpretation": _transition_interpretation(lost=lost, new=new, loss_events=loss_events),
                "loss_events": loss_events,
                "new_eligible": [
                    {
                        "concept_id": concept_id,
                        "score": current_decisions[concept_id].get("promotion_score"),
                        "concept": current_decisions[concept_id].get("concept"),
                    }
                    for concept_id in sorted(new)
                    if concept_id in current_decisions
                ],
            }
        )
    summary = {
        "campaign_root": str(campaign_root),
        "campaign_status": checkpoint.get("status"),
        "campaign_stop_reason": checkpoint.get("stop_reason"),
        "transitions": events,
        "loss_cause_counts": dict(cause_counts.most_common()),
        "healthy_expansion_transitions": healthy_expansions,
        "threshold_edge_losses": threshold_edge_losses,
        "harmful_losses": harmful_losses,
        "conclusion": _conclusion(
            checkpoint=checkpoint,
            harmful_losses=harmful_losses,
            threshold_edge_losses=threshold_edge_losses,
        ),
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phaseA_churn_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(summary, reports_dir)
    return summary


def _transition_interpretation(
    *,
    lost: set[str],
    new: set[str],
    loss_events: list[dict[str, Any]],
) -> str:
    if new and not lost:
        return "eligible set expanded; this is not harmful churn"
    if not lost and not new:
        return "eligible set stable"
    causes = {event["signature"]["cause"] for event in loss_events}
    if causes and all(cause.startswith("threshold_edge") for cause in causes):
        return "lost concepts remained validated and dropped at the eligibility threshold edge"
    return "eligible loss requires follow-up inspection"


def _conclusion(*, checkpoint: dict[str, Any], harmful_losses: int, threshold_edge_losses: int) -> str:
    if harmful_losses == 0 and threshold_edge_losses:
        return (
            "Phase A stopped on the churn gate, but observed losses were threshold-edge "
            "demotions from Promotion Eligible to Validated, not validation failure, contradiction, "
            "or concept collapse. The architecture appears operationally stable; promotion "
            "maturation needs hysteresis or release-candidate stability semantics before canonical promotion."
        )
    if harmful_losses:
        return (
            "Phase A churn included potentially harmful eligibility loss. Investigate the listed "
            "loss causes before treating promotion governance as stable."
        )
    return "No harmful promotion-eligible loss was observed."


def _write_markdown(summary: dict[str, Any], reports_dir: Path) -> None:
    lines = [
        "# Phase A Promotion Churn Audit",
        "",
        "This report is read-only over the Phase A isolated campaign store. No canonical knowledge was modified.",
        "",
        "## Executive Summary",
        "",
        f"- Campaign status: `{summary['campaign_status']}`",
        f"- Campaign stop reason: `{summary['campaign_stop_reason']}`",
        f"- Healthy expansion transitions: `{summary['healthy_expansion_transitions']}`",
        f"- Threshold-edge losses: `{summary['threshold_edge_losses']}`",
        f"- Potentially harmful losses: `{summary['harmful_losses']}`",
        f"- Loss causes: `{summary['loss_cause_counts']}`",
        "",
        "## Conclusion",
        "",
        summary["conclusion"],
        "",
        "## Transition Details",
        "",
    ]
    for event in summary["transitions"]:
        lines.extend(
            [
                f"### {event['transition']}",
                "",
                f"- Previous eligible: `{event['previous_eligible']}`",
                f"- Current eligible: `{event['current_eligible']}`",
                f"- Stayed: `{event['stayed']}`",
                f"- Lost: `{event['lost']}`",
                f"- New: `{event['new']}`",
                f"- Reported churn: `{event['reported_churn']}`",
                f"- Interpretation: {event['interpretation']}",
                "",
            ]
        )
        if event["loss_events"]:
            lines.extend(["| Concept ID | Cause | Previous -> Current | Redundancy | Concept |", "| --- | --- | --- | --- | --- |"])
            for loss in event["loss_events"]:
                sig = loss["signature"]
                lines.append(
                    f"| {loss['concept_id']} | {sig['cause']} | "
                    f"{sig.get('previous_score')} -> {sig.get('current_score')} | "
                    f"{sig.get('previous_redundancy')} -> {sig.get('current_redundancy')} | "
                    f"{str(loss['concept'])[:120]} |"
                )
            lines.append("")
        if event["new_eligible"]:
            lines.extend(["New eligible concepts:", ""])
            for item in event["new_eligible"]:
                lines.append(f"- `{item['concept_id']}` score `{item['score']}`: {str(item['concept'])[:160]}")
            lines.append("")
    (reports_dir / "phaseA_churn_audit.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase A promotion eligibility churn.")
    parser.add_argument(
        "--campaign-root",
        default=".tmp/experiments/phaseA_architecture_graduation/overnight_3000",
    )
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    summary = audit_churn(campaign_root=Path(args.campaign_root), reports_dir=Path(args.reports_dir))
    print(
        json.dumps(
            {
                "harmful_losses": summary["harmful_losses"],
                "threshold_edge_losses": summary["threshold_edge_losses"],
                "conclusion": summary["conclusion"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

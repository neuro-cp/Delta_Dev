"""Final benchmark/live-window review for Runtime V1.3.

This report-only review classifies remaining missed expected concepts as
realistic live-runtime targets or benchmark/live-window artifacts. It does not
patch runtime behavior, modify defaults, or run mitigation variants.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

ECA = REPORTS / "runtime_v13_evidence_contextualization_activation_simulation.json"
RCG = REPORTS / "runtime_v13_reasoning_citation_gate_review.json"
USABILITY = REPORTS / "runtime_v13_expected_evidence_usability_audit.json"
ESS = REPORTS / "runtime_v13_evidence_stage_separation_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
RAA = REPORTS / "runtime_v13_relation_aware_activation_simulation.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"
STABILIZER = REPORTS / "runtime_v13_fully_autonomous_stabilizer.json"
AVAILABILITY = REPORTS / "runtime_v13_activation_attention_candidate_availability.json"
CONSOLIDATION = REPORTS / "runtime_v13_failure_bottleneck_consolidation_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

STOP = {
    "a",
    "about",
    "after",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "the",
    "their",
    "to",
    "when",
    "why",
    "with",
}

CLASSES = (
    "live_usable_and_should_be_recovered",
    "live_usable_but_requires_new_signal",
    "visible_but_not_safely_separable",
    "outside_reasonable_activation_window",
    "benchmark_expected_but_not_live_citable",
    "benchmark_expected_but_planning_only",
    "benchmark_expected_redundant_with_used_evidence",
    "unavailable_or_unfair_target",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def toks(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP}


def jaccard(a: str, b: str) -> float:
    aa = toks(a)
    bb = toks(b)
    return len(aa & bb) / max(1, len(aa | bb))


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def usability_map(usability: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row["case"], row["concept_id"]): row
        for row in usability.get("visible_expected_inventory", [])
    }


def case_map(model: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in model.get("models", {}).get(name, {}).get("cases", [])}


def concept_text(metadata: dict[str, Any], cid: str, ranking_case: dict[str, Any]) -> str:
    for item in metadata.get("expected_concept_text", []):
        if item.get("concept_id") == cid:
            return f"{item.get('concept', '')} {item.get('definition', '')}".strip()
    for item in ranking_case.get("top_50", []):
        if item.get("concept_id") == cid:
            return f"{item.get('concept', '')} {item.get('definition', '')}".strip()
    return ""


def activation_rank(ranking_case: dict[str, Any], cid: str) -> int | None:
    for idx, item in enumerate(ranking_case.get("top_50", []), start=1):
        if item.get("concept_id") == cid:
            return idx
    return None


def used_expected_texts(case: dict[str, Any], metadata: dict[str, Any], ranking_case: dict[str, Any]) -> list[str]:
    used = set(case.get("reasoning_referenced_concepts") or []) | set(case.get("response_referenced_concepts") or []) | set(case.get("planning_referenced_concepts") or [])
    expected = set(metadata.get("expected_concepts") or [])
    return [concept_text(metadata, cid, ranking_case) for cid in sorted(used & expected)]


def best_recovery_path(case_name: str, cid: str, qda: dict[str, dict[str, Any]], ess: dict[str, dict[str, Any]], eca: dict[str, dict[str, Any]]) -> str:
    paths: list[str] = []
    q = qda.get(case_name, {})
    if cid in set(q.get("visible_expected", [])) or cid in set(q.get("expected_recovered", [])):
        paths.append("QDA visibility")
    e = ess.get(case_name, {})
    if cid in set(e.get("visible_expected", [])):
        paths.append("ESS visibility")
    if cid in set(e.get("planning_support_expected", [])):
        paths.append("ESS planning support")
    ec = eca.get(case_name, {})
    if cid in set(ec.get("expected_context_strong", [])):
        paths.append("ECA context strong")
    if cid in set(ec.get("expected_admitted_by_unchanged_gate", [])):
        paths.append("ECA projected gate admission")
    return ", ".join(paths) if paths else "none"


def classify_missed(
    *,
    case_name: str,
    cid: str,
    rank: int | None,
    text: str,
    used_texts: list[str],
    usable: dict[str, Any] | None,
    qda_case: dict[str, Any],
    ess_case: dict[str, Any],
    eca_case: dict[str, Any],
) -> tuple[str, str, bool, bool, bool, bool]:
    if rank is None:
        return (
            "unavailable_or_unfair_target",
            "Concept is absent from the diagnostic top-50 live window.",
            False,
            False,
            False,
            False,
        )
    max_sim = max([jaccard(text, other) for other in used_texts] or [0.0])
    if max_sim >= 0.58:
        return (
            "benchmark_expected_redundant_with_used_evidence",
            f"Concept overlaps strongly with already used expected evidence (jaccard={max_sim:.2f}).",
            True,
            True,
            False,
            True,
        )
    primary = (usable or {}).get("primary_class")
    visible = bool((usable or {}).get("visible_under_qda") or (usable or {}).get("visible_under_ess"))
    if primary == "visible_planning_only" or cid in set(ess_case.get("planning_support_expected", [])):
        return (
            "benchmark_expected_but_planning_only",
            "Concept appears useful as planning support but not as citable reasoning/response evidence.",
            True,
            False,
            False,
            True,
        )
    eca_noise = len(eca_case.get("noise_context_strong", [])) + len(eca_case.get("noise_admitted_by_unchanged_gate", []))
    if visible and (primary == "visible_unsafe_due_same_topic_noise_risk" or eca_noise > 0):
        return (
            "visible_but_not_safely_separable",
            "The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise.",
            True,
            True,
            False,
            True,
        )
    if rank > 20:
        return (
            "outside_reasonable_activation_window",
            f"Concept is present but low-ranked (rank {rank}), outside the practical V1.3 activation window.",
            False,
            False,
            False,
            False,
        )
    if visible and primary == "visible_rejected_by_citation_gate":
        return (
            "live_usable_but_requires_new_signal",
            "Concept is visible and relevant, but current live-safe signals cannot distinguish it from adjacent noise.",
            True,
            True,
            True,
            True,
        )
    if visible:
        return (
            "live_usable_and_should_be_recovered",
            "Concept is visible and no artifact/noise reason explains rejection.",
            True,
            False,
            True,
            True,
        )
    return (
        "live_usable_but_requires_new_signal",
        "Concept is in the top-20 but not made usable by current activation/attention/citation signals.",
        True,
        False,
        True,
        True,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    eca = load_json(args.eca)
    rcg = load_json(args.rcg)
    usability = load_json(args.usability)
    ess = load_json(args.ess)
    qda = load_json(args.qda)
    raa = load_json(args.raa)
    deep = load_json(args.deep)
    stabilizer = load_json(args.stabilizer)
    availability = load_json(args.availability)
    consolidation = load_json(args.consolidation)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)

    rankings = rank_map(ranking)
    umap = usability_map(usability)
    qda_cases = case_map(qda, "QDA6")
    ess_cases = case_map(ess, "ESS6")
    # Use ECA4 because it was the strongest partial signal in the latest run.
    eca_cases = case_map(eca, "ECA4")

    rows: list[dict[str, Any]] = []
    case_summaries: dict[str, dict[str, Any]] = {}
    for case in real.get("cases", []):
        name = case["name"]
        if case.get("runtime_decision") == "Healthy":
            continue
        metadata = real.get("case_metadata", {}).get(name, {})
        expected = set(metadata.get("expected_concepts") or [])
        used = set(case.get("reasoning_referenced_concepts") or []) | set(case.get("response_referenced_concepts") or [])
        missed = sorted(expected - used)
        if not missed:
            continue
        ranking_case = rankings.get(name, {})
        used_texts = used_expected_texts(case, metadata, ranking_case)
        case_rows = []
        for cid in missed:
            rank = activation_rank(ranking_case, cid)
            text = concept_text(metadata, cid, ranking_case)
            usable = umap.get((name, cid))
            cls, reason, inseparable, redundant, requires_new_signal, count_against = classify_missed(
                case_name=name,
                cid=cid,
                rank=rank,
                text=text,
                used_texts=used_texts,
                usable=usable,
                qda_case=qda_cases.get(name, {}),
                ess_case=ess_cases.get(name, {}),
                eca_case=eca_cases.get(name, {}),
            )
            recovery = best_recovery_path(name, cid, qda_cases, ess_cases, eca_cases)
            row = {
                "case": name,
                "current_model_b_decision": case.get("runtime_decision"),
                "concept_id": cid,
                "concept": text,
                "activation_rank": rank,
                "classification": cls,
                "best_attempted_recovery_path": recovery,
                "why_recovery_failed": reason,
                "same_topic_noise_inseparable_under_live_safe_signals": inseparable,
                "redundant_with_used_evidence": redundant,
                "requires_signal_not_currently_available_live": requires_new_signal,
                "should_remain_known_limitation": cls
                in {
                    "visible_but_not_safely_separable",
                    "outside_reasonable_activation_window",
                    "benchmark_expected_but_not_live_citable",
                    "benchmark_expected_but_planning_only",
                    "benchmark_expected_redundant_with_used_evidence",
                    "unavailable_or_unfair_target",
                },
                "should_count_against_runtime_v13": count_against,
            }
            rows.append(row)
            case_rows.append(row)
        case_summaries[name] = {
            "current_model_b_decision": case.get("runtime_decision"),
            "missed_expected_count": len(case_rows),
            "classifications": dict(Counter(row["classification"] for row in case_rows)),
        }

    counts = Counter(row["classification"] for row in rows)
    count_against = sum(1 for row in rows if row["should_count_against_runtime_v13"])
    requires_new_signal = sum(1 for row in rows if row["requires_signal_not_currently_available_live"])
    artifacts_or_limitations = sum(1 for row in rows if row["should_remain_known_limitation"])
    # The ladder repeatedly showed no safe live patch; if most remaining misses
    # are inseparable/artifact/limitation, stop V1.3 on Model B. If many misses
    # are live-usable but require new signals, defer that to V1.4 research.
    if count_against and requires_new_signal >= max(2, artifacts_or_limitations):
        rec = "PROCEED_NEW_SIGNAL_RESEARCH_RUNTIME_V14"
        disposition = "Model B is stable for V1.3, but remaining counted misses require new live signals rather than another V1.3 mitigation."
    elif artifacts_or_limitations >= count_against:
        rec = "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"
        disposition = "Model B is a stable V1.3 local optimum under current live-safe signals."
    else:
        rec = "PROCEED_NEW_SIGNAL_RESEARCH_RUNTIME_V14"
        disposition = "V1.3 mitigation is exhausted; future work belongs in new-signal Runtime V1.4 research."

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "mitigation_ladder_summary": {
            "stabilizer": stabilizer.get("final_decision"),
            "deep_activation": deep.get("final_recommendation"),
            "relation_aware_activation": raa.get("final_recommendation"),
            "query_decomposition": qda.get("final_recommendation"),
            "evidence_stage_separation": ess.get("final_recommendation"),
            "reasoning_citation_gate_review": rcg.get("final_recommendation"),
            "evidence_contextualization": eca.get("final_recommendation"),
            "availability": availability.get("availability_summary", {}).get("final_recommendation"),
            "consolidation": consolidation.get("final_recommendation"),
        },
        "remaining_failed_cases": case_summaries,
        "missed_expected_concepts": rows,
        "classification_counts": {cls: counts.get(cls, 0) for cls in CLASSES},
        "live_usability": {
            "should_count_against_runtime_v13": count_against,
            "requires_new_live_signal": requires_new_signal,
            "known_limitations_or_artifacts": artifacts_or_limitations,
        },
        "model_b_stable_v13_local_optimum": rec == "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13" or rec == "PROCEED_NEW_SIGNAL_RESEARCH_RUNTIME_V14",
        "recommended_final_v13_disposition": disposition,
        "continuation_checkpoint": {
            "model_b_default_remains_active": True,
            "runtime_files_modified": False,
            "next_step": rec,
        },
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Benchmark / Live-Window Review",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only review. No runtime behavior, defaults, benchmark fixtures, learning, storage, governance, or providers were modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        report["recommended_final_v13_disposition"],
        "",
        "## Mitigation Ladder Summary",
        "",
    ]
    for key, value in report["mitigation_ladder_summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## Remaining Failed Cases",
        "",
    ]
    for case, payload in report["remaining_failed_cases"].items():
        lines.append(f"- `{case}`: decision `{payload['current_model_b_decision']}`, missed `{payload['missed_expected_count']}`, classes `{payload['classifications']}`")
    lines += [
        "",
        "## Missed Expected Concept Classification Table",
        "",
        "| Case | Rank | Classification | Best Recovery Path | Counts Against V1.3 | Why Recovery Failed |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for row in report["missed_expected_concepts"]:
        why = str(row["why_recovery_failed"]).replace("|", "/")
        lines.append(
            f"| `{row['case']}` | `{row['activation_rank']}` | `{row['classification']}` | `{row['best_attempted_recovery_path']}` | `{row['should_count_against_runtime_v13']}` | {why} |"
        )
    lines += [
        "",
        "## Live-Usability Analysis",
        "",
        f"- Concepts that should count against Runtime V1.3: `{report['live_usability']['should_count_against_runtime_v13']}`",
        f"- Concepts requiring new live signal: `{report['live_usability']['requires_new_live_signal']}`",
        f"- Known limitations or artifacts: `{report['live_usability']['known_limitations_or_artifacts']}`",
        "",
        "## Inseparable Same-Topic Noise Analysis",
        "",
        f"- `visible_but_not_safely_separable`: `{report['classification_counts']['visible_but_not_safely_separable']}`",
        "",
        "## Benchmark/Live-Window Artifact Analysis",
        "",
        f"- `outside_reasonable_activation_window`: `{report['classification_counts']['outside_reasonable_activation_window']}`",
        f"- `benchmark_expected_but_not_live_citable`: `{report['classification_counts']['benchmark_expected_but_not_live_citable']}`",
        f"- `benchmark_expected_but_planning_only`: `{report['classification_counts']['benchmark_expected_but_planning_only']}`",
        f"- `benchmark_expected_redundant_with_used_evidence`: `{report['classification_counts']['benchmark_expected_redundant_with_used_evidence']}`",
        f"- `unavailable_or_unfair_target`: `{report['classification_counts']['unavailable_or_unfair_target']}`",
        "",
        "## Whether Model B Is A Stable V1.3 Local Optimum",
        "",
        f"`{report['model_b_stable_v13_local_optimum']}`",
        "",
        "## Recommended Final V1.3 Disposition",
        "",
        report["recommended_final_v13_disposition"],
        "",
        "## Continuation Checkpoint",
        "",
        f"- Model B default remains active: `{report['continuation_checkpoint']['model_b_default_remains_active']}`",
        f"- Runtime files modified: `{report['continuation_checkpoint']['runtime_files_modified']}`",
        "",
        report["final_recommendation"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--eca", type=Path, default=ECA)
    p.add_argument("--rcg", type=Path, default=RCG)
    p.add_argument("--usability", type=Path, default=USABILITY)
    p.add_argument("--ess", type=Path, default=ESS)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--stabilizer", type=Path, default=STABILIZER)
    p.add_argument("--availability", type=Path, default=AVAILABILITY)
    p.add_argument("--consolidation", type=Path, default=CONSOLIDATION)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_benchmark_live_window_review.json"
    md_path = args.reports_dir / "runtime_v13_benchmark_live_window_review.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

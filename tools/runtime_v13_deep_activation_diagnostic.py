"""Deep activation diagnostic for Runtime V1.3.

This diagnostic explains why same-topic noise co-ranks with expected evidence
under the accepted Model B baseline. It reads archived reports only and does not
patch runtime behavior.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
STABILIZER = REPORTS / "runtime_v13_fully_autonomous_stabilizer.json"
STABILIZER_CHECKPOINT = REPORTS / "runtime_v13_fully_autonomous_checkpoint.json"
BAR = REPORTS / "runtime_v13_bounded_attention_rescue_simulation.json"
AVAILABILITY = REPORTS / "runtime_v13_activation_attention_candidate_availability.json"
CONSOLIDATION = REPORTS / "runtime_v13_failure_bottleneck_consolidation_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"

GENERIC = {
    "change",
    "context",
    "current",
    "evidence",
    "failure",
    "plan",
    "planning",
    "resource",
    "response",
    "risk",
    "strategy",
    "uncertainty",
}
RELATION = {
    "allocate",
    "allocation",
    "alternative",
    "audit",
    "capacity",
    "cause",
    "contradiction",
    "demand",
    "exception",
    "failure rate",
    "if",
    "increase",
    "permit",
    "prediction",
    "reallocate",
    "revise",
    "root cause",
    "route",
    "tradeoff",
    "validate",
    "would",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text)}


def contains(text: str, terms: set[str]) -> set[str]:
    lower = text.lower()
    return {term for term in terms if term in lower}


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def feature(item: dict[str, Any], question: str) -> dict[str, Any]:
    text = f"{item.get('concept', '')} {item.get('definition', '')}"
    q_overlap = {str(term).lower() for term in item.get("query_combined_overlap", [])}
    generic = q_overlap & GENERIC
    specific = q_overlap - generic
    concept_tokens = tokens(item.get("concept", ""))
    definition_tokens = tokens(item.get("definition", ""))
    query_tokens = tokens(question)
    alignment = len(concept_tokens & definition_tokens) / max(1, len(concept_tokens | definition_tokens))
    return {
        "activation_score": float(item.get("activation_score") or 0.0),
        "confidence": float(item.get("confidence") or 0.0),
        "promotion_score": float(item.get("promotion_score") or 0.0),
        "projected_centrality": float(item.get("projected_centrality") or 0.0),
        "evidence_support": float(item.get("evidence_support") or 0.0),
        "specific_overlap": len(specific),
        "generic_overlap": len(generic),
        "generic_anchor_ratio": len(generic) / max(1, len(q_overlap)),
        "relation_specificity": len(contains(text, RELATION)),
        "concept_definition_alignment": alignment,
        "query_text_overlap": len(tokens(text) & query_tokens),
    }


def avg(rows: list[dict[str, Any]], key: str) -> float:
    vals = [float(row[key]) for row in rows if row.get(key) is not None]
    return round(mean(vals), 4) if vals else 0.0


def summarize_features(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        key: avg(rows, key)
        for key in (
            "activation_score",
            "confidence",
            "promotion_score",
            "projected_centrality",
            "evidence_support",
            "specific_overlap",
            "generic_overlap",
            "generic_anchor_ratio",
            "relation_specificity",
            "concept_definition_alignment",
            "query_text_overlap",
        )
    }


def classify_noise(expected_rows: list[dict[str, Any]], noise_rows: list[dict[str, Any]]) -> Counter[str]:
    taxonomy: Counter[str] = Counter()
    exp = summarize_features(expected_rows)
    for row in noise_rows:
        labels = []
        if row["specific_overlap"] >= exp["specific_overlap"] * 0.8:
            labels.append("same_query_terms")
        if row["relation_specificity"] >= exp["relation_specificity"] * 0.8 and row["relation_specificity"] > 0:
            labels.append("same_relation_terms")
        if row["generic_anchor_ratio"] > exp["generic_anchor_ratio"]:
            labels.append("generic_anchor_heavy")
        if row["confidence"] >= exp["confidence"] and row["promotion_score"] >= exp["promotion_score"] * 0.95:
            labels.append("confidence_promotion_competes")
        if row["projected_centrality"] >= exp["projected_centrality"]:
            labels.append("centrality_competes")
        if not labels:
            labels.append("adjacent_semantic_noise")
        taxonomy.update(labels)
    return taxonomy


def rank_band(rank: int | None) -> str:
    if rank is None:
        return "absent"
    if rank <= 10:
        return "rank_1_10"
    if rank <= 20:
        return "rank_11_20"
    if rank <= 50:
        return "rank_21_50"
    return "absent"


def rows_for_case(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    contrib = contribution_map(case)
    expected_ids = set(metadata.get("expected_concepts") or [])
    useful_ids = set(metadata.get("useful_neighbor_concepts") or [])
    expected_rows: list[dict[str, Any]] = []
    noise_rows: list[dict[str, Any]] = []
    selected_noise_rows: list[dict[str, Any]] = []
    ignored_noise_rows: list[dict[str, Any]] = []
    selected_expected_rows: list[dict[str, Any]] = []
    missed_expected_rows: list[dict[str, Any]] = []
    question = ranking_case.get("question") or case.get("question") or ""
    for idx, item in enumerate(ranking_case.get("top_50", []), start=1):
        cid = item["concept_id"]
        row = {
            "concept_id": cid,
            "rank": idx,
            "role": "expected" if cid in expected_ids else "useful_neighbor" if cid in useful_ids else "noise",
            "selected_by_attention": bool(contrib.get(cid, {}).get("attended")),
            "reasoned": bool(contrib.get(cid, {}).get("reasoned")),
            "planned": bool(contrib.get(cid, {}).get("planned")),
            "responded": bool(contrib.get(cid, {}).get("responded")),
            "concept": item.get("concept") or item.get("definition") or "",
            **feature(item, question),
        }
        if row["role"] == "expected":
            expected_rows.append(row)
            if row["selected_by_attention"]:
                selected_expected_rows.append(row)
            else:
                missed_expected_rows.append(row)
        elif row["role"] == "noise":
            noise_rows.append(row)
            if row["reasoned"]:
                selected_noise_rows.append(row)
            else:
                ignored_noise_rows.append(row)
    # Expected concepts absent from top_50 still matter for live-window diagnosis.
    present_expected = {row["concept_id"] for row in expected_rows}
    for item in metadata.get("expected_concept_text", []):
        cid = item.get("concept_id")
        if cid and cid not in present_expected:
            missed_expected_rows.append(
                {
                    "concept_id": cid,
                    "rank": None,
                    "role": "expected",
                    "selected_by_attention": False,
                    "reasoned": False,
                    "planned": False,
                    "responded": False,
                    "concept": item.get("definition") or item.get("concept") or "",
                    **{key: 0.0 for key in summarize_features([{}]).keys()},
                }
            )
    return {
        "expected": expected_rows,
        "noise": noise_rows,
        "selected_noise": selected_noise_rows,
        "ignored_noise": ignored_noise_rows,
        "selected_expected": selected_expected_rows,
        "missed_expected": missed_expected_rows,
    }


def case_audit(case: dict[str, Any], ranking_case: dict[str, Any], metadata: dict[str, Any], rescued_noise: set[str]) -> dict[str, Any]:
    rows = rows_for_case(case, ranking_case, metadata)
    expected_summary = summarize_features(rows["expected"])
    noise_summary = summarize_features(rows["noise"][:10])
    missed_summary = summarize_features(rows["missed_expected"])
    selected_expected_summary = summarize_features(rows["selected_expected"])
    selected_noise_summary = summarize_features(rows["selected_noise"])
    ignored_noise_summary = summarize_features(rows["ignored_noise"])
    taxonomy = classify_noise(rows["expected"], rows["noise"][:10]) if rows["expected"] else Counter()
    bands = Counter(rank_band(row.get("rank")) for row in rows["missed_expected"])
    variant_noise = [row for row in rows["noise"] if row["concept_id"] in rescued_noise]
    return {
        "case": case["name"],
        "category": case.get("category"),
        "question": case.get("question"),
        "runtime_decision": case.get("runtime_decision"),
        "noise_used_in_reasoning": case.get("noise_used_in_reasoning"),
        "expected_vs_top_noise_delta": delta(expected_summary, noise_summary),
        "missed_expected_vs_selected_expected_delta": delta(missed_summary, selected_expected_summary),
        "selected_noise_vs_ignored_noise_delta": delta(selected_noise_summary, ignored_noise_summary),
        "missed_rank_bands": dict(bands),
        "same_topic_noise_taxonomy": dict(taxonomy),
        "rescued_by_failed_reranks_noise": [
            {
                "concept_id": row["concept_id"],
                "rank": row["rank"],
                "concept": row["concept"],
                "features": {k: row[k] for k in summarize_features([row])},
            }
            for row in variant_noise
        ],
        "top_noise": [
            {
                "concept_id": row["concept_id"],
                "rank": row["rank"],
                "reasoned": row["reasoned"],
                "concept": row["concept"][:180],
                "features": {k: row[k] for k in summarize_features([row])},
            }
            for row in rows["noise"][:5]
        ],
        "missed_expected": [
            {
                "concept_id": row["concept_id"],
                "rank": row.get("rank"),
                "concept": row["concept"][:180],
                "features": {k: row[k] for k in summarize_features([row])},
            }
            for row in rows["missed_expected"]
        ],
    }


def delta(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {key: round(left.get(key, 0.0) - right.get(key, 0.0), 4) for key in set(left) | set(right)}


def collect_failed_rerank_noise(stabilizer: dict[str, Any]) -> set[str]:
    noise: set[str] = set()
    for result in stabilizer.get("results", []):
        if result.get("failure_reason") != "noise_enters_reasoning":
            continue
        for case in result.get("cases", []):
            noise.update(case.get("selected_noise", []))
    return noise


def root_causes(case_audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scores = Counter()
    for audit in case_audits:
        taxonomy = Counter(audit["same_topic_noise_taxonomy"])
        bands = Counter(audit["missed_rank_bands"])
        if taxonomy["same_query_terms"] or taxonomy["same_relation_terms"]:
            scores["lexical overlap / same-topic dominance"] += taxonomy["same_query_terms"] + taxonomy["same_relation_terms"]
        if taxonomy["generic_anchor_heavy"]:
            scores["generic-anchor dominance"] += taxonomy["generic_anchor_heavy"]
        if taxonomy["confidence_promotion_competes"]:
            scores["confidence/promotion over-weighting"] += taxonomy["confidence_promotion_competes"]
        if taxonomy["centrality_competes"]:
            scores["centrality/recurrence bias"] += taxonomy["centrality_competes"]
        if bands["rank_21_50"] or bands["absent"]:
            scores["benchmark expected concept outside realistic live window"] += bands["rank_21_50"] + bands["absent"]
        if audit["expected_vs_top_noise_delta"].get("relation_specificity", 0.0) <= 0:
            scores["relation mismatch / missing relation-aware activation"] += 1
        if audit["expected_vs_top_noise_delta"].get("specific_overlap", 0.0) <= 0:
            scores["query decomposition failure"] += 1
    ordered = scores.most_common()
    return [{"cause": cause, "score": score} for cause, score in ordered]


def recommend(causes: list[dict[str, Any]]) -> str:
    if not causes:
        return "RUN_MORE_DIAGNOSTICS"
    top = causes[0]["cause"]
    if "relation" in top:
        return "PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION"
    if "query decomposition" in top:
        return "PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION"
    if "generic-anchor" in top:
        return "PROCEED_GENERIC_ANCHOR_DAMPENING_SIMULATION"
    if "confidence/promotion" in top:
        return "PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION"
    if "live window" in top:
        return "PROCEED_BENCHMARK_LIVE_WINDOW_REVIEW"
    if "lexical overlap" in top:
        return "PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    stabilizer = load_json(args.stabilizer)
    checkpoint = load_json(args.checkpoint)
    bar = load_json(args.bar)
    availability = load_json(args.availability)
    consolidation = load_json(args.consolidation)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    cases = case_map(real)
    rankings = ranking_case_map(ranking)
    metadata = real.get("case_metadata", {})
    failed_names = [case["case"] for case in consolidation.get("case_audits", [])]
    rescued_noise = collect_failed_rerank_noise(stabilizer)
    audits = [
        case_audit(cases[name], rankings.get(name, {}), metadata.get(name, {}), rescued_noise)
        for name in failed_names
        if name in cases
    ]
    causes = root_causes(audits)
    final = recommend(causes)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "stabilizer": str(args.stabilizer),
            "checkpoint": str(args.checkpoint),
            "bar": str(args.bar),
            "availability": str(args.availability),
            "consolidation": str(args.consolidation),
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
        },
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_autonomous_reranking_stopped": {
            "final_decision": stabilizer.get("final_decision"),
            "stop_reason": stabilizer.get("stop_reason"),
            "checkpoint": checkpoint,
        },
        "bar_summary": bar.get("final_recommendation"),
        "availability_summary": {
            "final_recommendation": availability.get("final_recommendation"),
            "bucket_distribution": availability.get("bucket_distribution"),
            "noise_risk_estimate": availability.get("noise_risk_estimate"),
        },
        "case_audits": audits,
        "root_cause_ranking": causes,
        "rejected_mitigation_paths": [
            "more downstream Planning Support/QRM variants",
            "bounded attention rescue as a live patch",
            "broad activation-window expansion",
            "activation recurrence by default",
            "concept-ID or benchmark-case-specific live logic",
            "global threshold loosening",
        ],
        "recommended_next_experiment": final,
        "continuation_checkpoint": {
            "model_b_default_remains_active": True,
            "runtime_files_modified": False,
            "next_step": final,
        },
        "final_recommendation": final,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Deep Activation Diagnostic",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Diagnostic only. No runtime behavior, learning, governance, storage, provider, candidate-store, canonical, benchmark, or default runtime behavior was modified.",
        "",
        "## Summary",
        "",
        f"- Current accepted default: {report['current_accepted_default']}",
        f"- Autonomous reranking stopped: `{report['why_autonomous_reranking_stopped']['stop_reason']}` / `{report['why_autonomous_reranking_stopped']['final_decision']}`",
        f"- Availability prior: `{report['availability_summary']}`",
        f"- Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Root-Cause Ranking",
        "",
        "| Rank | Mechanism | Score |",
        "| ---: | --- | ---: |",
    ]
    for index, cause in enumerate(report["root_cause_ranking"], start=1):
        lines.append(f"| {index} | {cause['cause']} | `{cause['score']}` |")
    lines.extend(["", "## Case-Level Activation Failure Table", ""])
    lines.append("| Case | Decision | Missed Rank Bands | Dominant Noise Taxonomy |")
    lines.append("| --- | --- | --- | --- |")
    for audit in report["case_audits"]:
        taxonomy = Counter(audit["same_topic_noise_taxonomy"]).most_common(3)
        lines.append(
            f"| {audit['case']} | `{audit['runtime_decision']}` | `{audit['missed_rank_bands']}` | `{taxonomy}` |"
        )
    lines.extend(["", "## Expected-vs-Noise Feature Deltas", ""])
    lines.append("| Case | Activation | Specific | Generic Ratio | Relation | Confidence | Promotion | Centrality |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for audit in report["case_audits"]:
        delta_row = audit["expected_vs_top_noise_delta"]
        lines.append(
            f"| {audit['case']} | `{delta_row.get('activation_score')}` | `{delta_row.get('specific_overlap')}` | "
            f"`{delta_row.get('generic_anchor_ratio')}` | `{delta_row.get('relation_specificity')}` | "
            f"`{delta_row.get('confidence')}` | `{delta_row.get('promotion_score')}` | `{delta_row.get('projected_centrality')}` |"
        )
    lines.extend(["", "## Same-Topic Noise Taxonomy", ""])
    taxonomy_total = Counter()
    for audit in report["case_audits"]:
        taxonomy_total.update(audit["same_topic_noise_taxonomy"])
    for label, count in taxonomy_total.most_common():
        lines.append(f"- `{label}`: `{count}`")
    lines.extend(["", "## Failed Rerank Noise Examples", ""])
    for audit in report["case_audits"]:
        if not audit["rescued_by_failed_reranks_noise"]:
            continue
        lines.append(f"### {audit['case']}")
        for item in audit["rescued_by_failed_reranks_noise"][:5]:
            text = item["concept"].replace("|", "\\|")
            if len(text) > 140:
                text = text[:137] + "..."
            lines.append(f"- `{item['concept_id']}` rank `{item['rank']}`: {text}")
        lines.append("")
    lines.extend(["## Rejected Mitigation Paths", ""])
    for path in report["rejected_mitigation_paths"]:
        lines.append(f"- {path}")
    lines.extend(
        [
            "",
            "## Recommended Next Experiment",
            "",
            report["final_recommendation"],
            "",
            "## Continuation Checkpoint",
            "",
            f"- Model B default remains active: `{report['continuation_checkpoint']['model_b_default_remains_active']}`",
            f"- Runtime files modified: `{report['continuation_checkpoint']['runtime_files_modified']}`",
            f"- Next step: `{report['continuation_checkpoint']['next_step']}`",
            "",
            report["final_recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stabilizer", type=Path, default=STABILIZER)
    parser.add_argument("--checkpoint", type=Path, default=STABILIZER_CHECKPOINT)
    parser.add_argument("--bar", type=Path, default=BAR)
    parser.add_argument("--availability", type=Path, default=AVAILABILITY)
    parser.add_argument("--consolidation", type=Path, default=CONSOLIDATION)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_deep_activation_diagnostic.json"
    md_path = args.reports_dir / "runtime_v13_deep_activation_diagnostic.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Expected-evidence usability audit for Runtime V1.3.

This report-only audit classifies expected concepts that become visible under
QDA/ESS-style visibility and explains why they do or do not become usable
reasoning, planning, or response evidence. It reads archived reports only and
does not patch runtime behavior.
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
RAW_ROOT = REPORTS / "runtime_v13_expected_evidence_usability_raw"

MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"
ESS = REPORTS / "runtime_v13_evidence_stage_separation_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
RAA = REPORTS / "runtime_v13_relation_aware_activation_simulation.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"

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

GENERIC = {
    "change",
    "context",
    "current",
    "data",
    "evidence",
    "failure",
    "increase",
    "plan",
    "planning",
    "resource",
    "response",
    "risk",
    "strategy",
    "team",
    "uncertainty",
}

RELATION_TERMS = {
    "allocate",
    "allocation",
    "alternative",
    "assumption",
    "audit",
    "capacity",
    "causal",
    "cause",
    "conflict",
    "contradict",
    "demand",
    "exception",
    "failed",
    "failure",
    "method",
    "permit",
    "prediction",
    "reallocate",
    "reports",
    "revise",
    "root",
    "route",
    "shelter",
    "timeline",
    "tradeoff",
}

EVIDENCE_NEEDS = {
    "cause_root_cause": {"cause", "root", "mechanism", "timeline", "failure", "interact"},
    "contradiction_resolution": {"contradict", "conflicting", "resolve", "unresolved", "source", "evidence"},
    "exception_rule": {"exception", "rule", "policy", "audit", "expiration", "applies"},
    "revision_action": {"revise", "alternative", "route", "method", "assumption", "failed", "permit"},
    "resource_constraint": {"allocation", "resource", "shelter", "demand", "capacity", "reallocate"},
    "risk_uncertainty": {"risk", "uncertainty", "tradeoff", "confidence", "likelihood"},
}

CLASSES = (
    "visible_citable_and_used",
    "visible_citable_not_response_bound",
    "visible_rejected_by_citation_gate",
    "visible_planning_only",
    "visible_response_relevant_but_not_planning",
    "visible_unsafe_due_same_topic_noise_risk",
    "expected_benchmark_only_not_live_usable",
    "unavailable_even_with_visibility",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text)
        if t.lower() not in STOP
    }


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def contribution_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["concept_id"]: item for item in case.get("concept_contributions", [])}


def qda_case_map(qda: dict[str, Any], model: str = "QDA6") -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in qda.get("models", {}).get(model, {}).get("cases", [])}


def ess_case_map(ess: dict[str, Any], model: str = "ESS6") -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in ess.get("models", {}).get(model, {}).get("cases", [])}


def infer_need(question: str) -> str:
    q = tokens(question)
    scored = {need: len(q & terms) for need, terms in EVIDENCE_NEEDS.items()}
    best = max(scored, key=lambda need: (scored[need], need))
    return best if scored[best] else "revision_action"


def concept_text_from_meta(metadata: dict[str, Any], cid: str) -> str:
    for item in metadata.get("expected_concept_text", []):
        if item.get("concept_id") == cid:
            return f"{item.get('concept', '')} {item.get('definition', '')}".strip()
    return ""


def rank_item(ranking_case: dict[str, Any], cid: str) -> tuple[int | None, dict[str, Any] | None]:
    for idx, item in enumerate(ranking_case.get("top_50", []), start=1):
        if item.get("concept_id") == cid:
            return idx, item
    return None, None


def noise_neighbors(ranking_case: dict[str, Any], expected: set[str], useful: set[str], rank: int | None) -> list[dict[str, Any]]:
    if rank is None:
        window = ranking_case.get("top_50", [])[:10]
    else:
        start = max(0, rank - 4)
        end = min(len(ranking_case.get("top_50", [])), rank + 3)
        window = ranking_case.get("top_50", [])[start:end]
    out = []
    for item in window:
        cid = item.get("concept_id")
        if cid in expected or cid in useful:
            continue
        out.append(
            {
                "concept_id": cid,
                "rank": next((idx for idx, candidate in enumerate(ranking_case.get("top_50", []), start=1) if candidate.get("concept_id") == cid), None),
                "concept": item.get("concept", ""),
                "activation_score": item.get("activation_score"),
            }
        )
    return out[:5]


def feature_summary(text: str, question: str, ranking_item: dict[str, Any] | None) -> dict[str, Any]:
    text_tokens = tokens(text)
    q_tokens = tokens(question)
    need = infer_need(question)
    overlap = text_tokens & q_tokens
    query_overlap = {str(t).lower() for t in (ranking_item or {}).get("query_combined_overlap", [])}
    generic = query_overlap & GENERIC
    return {
        "relation_action_frame_match": len(text_tokens & RELATION_TERMS),
        "evidence_need": need,
        "evidence_need_match": len(text_tokens & EVIDENCE_NEEDS[need]),
        "query_overlap": len(overlap),
        "generic_anchor_ratio": round(len(generic) / max(1, len(query_overlap)), 4),
        "activation_score": (ranking_item or {}).get("activation_score"),
        "confidence": (ranking_item or {}).get("confidence"),
        "promotion_score": (ranking_item or {}).get("promotion_score"),
        "projected_centrality": (ranking_item or {}).get("projected_centrality"),
    }


def classify(row: dict[str, Any]) -> tuple[str, str, str]:
    if not row["visible_under_qda"] and not row["visible_under_ess"]:
        if row["original_model_b_activation_rank"] is None:
            return (
                "expected_benchmark_only_not_live_usable",
                "Expected concept is outside the diagnostic live window and cannot be safely used by runtime stages.",
                "benchmark/live-window review",
            )
        return (
            "unavailable_even_with_visibility",
            "Expected concept remains outside QDA/ESS visibility even though it is present in the top-50 diagnostic window.",
            "activation visibility",
        )
    if row["citable_reasoning_status"] and row["response_binding_status"]:
        return (
            "visible_citable_and_used",
            "Visible concept passes citable reasoning and is bound into response evidence.",
            "none",
        )
    if row["citable_reasoning_status"] and not row["response_binding_status"]:
        return (
            "visible_citable_not_response_bound",
            "Visible concept reaches reasoning but is not represented in response evidence.",
            "response evidence binding",
        )
    if row["response_binding_status"] and not row["planning_support_status"]:
        return (
            "visible_response_relevant_but_not_planning",
            "Visible concept appears response-relevant but is not available to planning.",
            "planning/response separation",
        )
    if row["planning_support_status"] and not row["citable_reasoning_status"]:
        return (
            "visible_planning_only",
            "Visible concept is usable only as non-citable planning support.",
            "planning support binding",
        )
    if row["noise_risk_neighbor_count"] >= 3 and row["features"]["generic_anchor_ratio"] >= 0.4:
        return (
            "visible_unsafe_due_same_topic_noise_risk",
            "Visible concept is surrounded by same-topic noise and has a generic-anchor-heavy match.",
            "evidence contextualization in activation",
        )
    return (
        "visible_rejected_by_citation_gate",
        "Visible concept has intent/evidence signals but is not accepted by the citation/reasoning gate.",
        "reasoning citation gate",
    )


def build_inventory(real: dict[str, Any], ranking: dict[str, Any], qda: dict[str, Any], ess: dict[str, Any]) -> list[dict[str, Any]]:
    rankings = rank_map(ranking)
    qda_cases = qda_case_map(qda, "QDA6")
    ess_cases = ess_case_map(ess, "ESS6")
    inventory: list[dict[str, Any]] = []
    for case in real.get("cases", []):
        name = case["name"]
        metadata = real.get("case_metadata", {}).get(name, {})
        expected = set(metadata.get("expected_concepts") or [])
        useful = set(metadata.get("useful_neighbor_concepts") or [])
        ranking_case = rankings.get(name, {})
        qda_case = qda_cases.get(name, {})
        ess_case = ess_cases.get(name, {})
        contrib = contribution_map(case)
        qda_visible = set(qda_case.get("visible_expected", [])) | set(qda_case.get("selected_for_reasoning", []))
        ess_visible = set(ess_case.get("visible_expected", []))
        ess_planning_support = set(ess_case.get("planning_support_expected", []))
        for cid in expected:
            rank, item = rank_item(ranking_case, cid)
            text = concept_text_from_meta(metadata, cid) or (item or {}).get("concept", "")
            neighbors = noise_neighbors(ranking_case, expected, useful, rank)
            contribution = contrib.get(cid, {})
            row = {
                "case": name,
                "concept_id": cid,
                "concept": text,
                "original_model_b_activation_rank": rank,
                "visible_under_qda": cid in qda_visible,
                "visible_under_ess": cid in ess_visible,
                "attention_status": bool(contribution.get("attended")),
                "working_memory_status": bool(contribution.get("attended")),
                "citable_reasoning_status": bool(contribution.get("reasoned")) or cid in set(ess_case.get("citable_reasoning_expected", [])),
                "planning_support_status": bool(contribution.get("planned")) or cid in ess_planning_support,
                "response_binding_status": bool(contribution.get("responded")) or cid in set(ess_case.get("citable_reasoning_expected", [])),
                "noise_risk_neighbors": neighbors,
                "noise_risk_neighbor_count": len(neighbors),
                "features": feature_summary(text, ranking_case.get("question") or case.get("question") or "", item),
                "baseline_decision": case.get("runtime_decision"),
                "ess6_projected_decision": ess_case.get("projected_decision"),
            }
            klass, reason, layer = classify(row)
            row["primary_class"] = klass
            row["why_not_used"] = reason
            row["smallest_layer_that_could_make_usable_safely"] = layer
            inventory.append(row)
    return inventory


def dominant_bottleneck(counts: Counter[str]) -> tuple[str, str]:
    if not counts:
        return "none", "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"
    if counts["visible_citable_not_response_bound"] or counts["visible_response_relevant_but_not_planning"]:
        return "response binding too weak", "PROCEED_RESPONSE_EVIDENCE_BINDING_SIMULATION"
    if counts["visible_rejected_by_citation_gate"] >= max(1, counts["visible_planning_only"]):
        return "citation gate too strict", "PROCEED_REASONING_CITATION_GATE_REVIEW"
    if counts["visible_unsafe_due_same_topic_noise_risk"]:
        return "visible evidence still too noisy", "PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION"
    if counts["expected_benchmark_only_not_live_usable"]:
        return "benchmark expected concepts not live-usable", "PROCEED_BENCHMARK_LIVE_WINDOW_REVIEW"
    if counts["unavailable_even_with_visibility"]:
        return "activation visibility still incomplete", "PROCEED_QUERY_DECOMPOSITION_REFINEMENT"
    if counts["visible_planning_only"]:
        return "planning support too narrow", "PROCEED_RESPONSE_EVIDENCE_BINDING_SIMULATION"
    return "Model B is local optimum", "CHECKPOINT_MODEL_B_STOP_RUNTIME_V13"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    ess = load_json(args.ess)
    qda = load_json(args.qda)
    raa = load_json(args.raa)
    deep = load_json(args.deep)
    inventory = build_inventory(real, ranking, qda, ess)
    counts = Counter(row["primary_class"] for row in inventory)
    by_case: dict[str, Counter[str]] = defaultdict(Counter)
    by_layer: Counter[str] = Counter()
    for row in inventory:
        by_case[row["case"]][row["primary_class"]] += 1
        by_layer[row["smallest_layer_that_could_make_usable_safely"]] += 1
    bottleneck, recommendation = dominant_bottleneck(counts)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    (RAW_ROOT / "inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "why_ess_failed": ess.get("final_recommendation"),
        "qda_recommendation": qda.get("final_recommendation"),
        "relation_aware_recommendation": raa.get("final_recommendation"),
        "deep_activation_recommendation": deep.get("final_recommendation"),
        "visible_expected_inventory": inventory,
        "classification_counts": {klass: counts.get(klass, 0) for klass in CLASSES},
        "case_level_bottlenecks": {case: dict(counter) for case, counter in sorted(by_case.items())},
        "layer_counts": dict(by_layer),
        "dominant_next_bottleneck": bottleneck,
        "raw_archive": str(RAW_ROOT),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": recommendation},
        "final_recommendation": recommendation,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Expected Evidence Usability Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only audit. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Summary",
        "",
        "This audit classifies expected concepts by why QDA/ESS-style visibility does or does not become usable reasoning, planning, or response evidence.",
        "",
        "## Why ESS Failed",
        "",
        f"ESS ended with `{report['why_ess_failed']}`. Visibility and lane separation clarified the failure, but expected evidence still did not reliably become safe response/reasoning evidence.",
        "",
        "## Visible Expected Evidence Inventory",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for klass, count in report["classification_counts"].items():
        lines.append(f"| `{klass}` | `{count}` |")
    lines += [
        "",
        "## Usability Classification Table",
        "",
        "| Case | Rank | Visible | Attended | Reasoned | Planned | Responded | Class | Smallest Layer |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["visible_expected_inventory"]:
        visible = row["visible_under_qda"] or row["visible_under_ess"]
        lines.append(
            f"| `{row['case']}` | `{row['original_model_b_activation_rank']}` | `{visible}` | `{row['attention_status']}` | `{row['citable_reasoning_status']}` | `{row['planning_support_status']}` | `{row['response_binding_status']}` | `{row['primary_class']}` | `{row['smallest_layer_that_could_make_usable_safely']}` |"
        )
    lines += [
        "",
        "## Case-Level Bottleneck Table",
        "",
    ]
    for case, counts in report["case_level_bottlenecks"].items():
        detail = ", ".join(f"{k}: {v}" for k, v in counts.items())
        lines.append(f"- `{case}`: {detail}")
    lines += [
        "",
        "## Citation-Gate Rejection Analysis",
        "",
        f"Visible concepts rejected by citation gate: `{report['classification_counts'].get('visible_rejected_by_citation_gate', 0)}`",
        "",
        "## Response-Binding Failure Analysis",
        "",
        f"Citable but not response-bound concepts: `{report['classification_counts'].get('visible_citable_not_response_bound', 0)}`",
        "",
        "## Planning-Only Evidence Analysis",
        "",
        f"Visible planning-only concepts: `{report['classification_counts'].get('visible_planning_only', 0)}`",
        "",
        "## Same-Topic Noise Risk Analysis",
        "",
        f"Visible expected concepts dominated by same-topic noise risk: `{report['classification_counts'].get('visible_unsafe_due_same_topic_noise_risk', 0)}`",
        "",
        "## Benchmark/Live-Usability Analysis",
        "",
        f"Benchmark-only or outside-live-window concepts: `{report['classification_counts'].get('expected_benchmark_only_not_live_usable', 0)}`",
        "",
        "## Dominant Next Bottleneck",
        "",
        f"`{report['dominant_next_bottleneck']}`",
        "",
        "## Recommended Next Experiment",
        "",
        f"`{report['final_recommendation']}`",
        "",
        "## Continuation Checkpoint",
        "",
        f"- Model B default remains active: `{report['continuation_checkpoint']['model_b_default_remains_active']}`",
        f"- Runtime files modified: `{report['continuation_checkpoint']['runtime_files_modified']}`",
        f"- Raw archive: `{report['raw_archive']}`",
        "",
        report["final_recommendation"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--ess", type=Path, default=ESS)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--raa", type=Path, default=RAA)
    p.add_argument("--deep", type=Path, default=DEEP)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_expected_evidence_usability_audit.json"
    md_path = args.reports_dir / "runtime_v13_expected_evidence_usability_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

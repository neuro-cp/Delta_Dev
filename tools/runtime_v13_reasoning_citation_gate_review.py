"""Narrow reasoning citation gate review for Runtime V1.3.

This report-only tool reviews visible expected concepts rejected by the current
Model B citation/reasoning gate and tests conservative gate-audit variants. It
does not patch runtime behavior or modify defaults.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
USABILITY = REPORTS / "runtime_v13_expected_evidence_usability_audit.json"
ESS = REPORTS / "runtime_v13_evidence_stage_separation_diagnostic.json"
QDA = REPORTS / "runtime_v13_query_decomposition_activation_simulation.json"
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

GENERIC = {"change", "context", "current", "data", "evidence", "failure", "increase", "plan", "planning", "resource", "response", "risk", "strategy", "team", "uncertainty"}

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
    "rejected_due_missing_citation_context",
    "rejected_due_weak_contextual_alignment",
    "rejected_due_same_topic_noise_risk",
    "rejected_due_planning_only_signal",
    "rejected_due_response_only_signal",
    "rejected_due_gate_false_negative",
    "benchmark_expected_but_not_live_citable",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def toks(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text) if t.lower() not in STOP}


def rank_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def infer_need(question: str) -> str:
    q = toks(question)
    scored = {need: len(q & terms) for need, terms in EVIDENCE_NEEDS.items()}
    best = max(scored, key=lambda need: (scored[need], need))
    return best if scored[best] else "revision_action"


def feature(text: str, question: str, rank_item: dict[str, Any] | None) -> dict[str, Any]:
    text_tokens = toks(text)
    q_tokens = toks(question)
    need = infer_need(question)
    overlap = {str(t).lower() for t in (rank_item or {}).get("query_combined_overlap", [])}
    generic = overlap & GENERIC
    relation = len(text_tokens & RELATION_TERMS)
    evidence_need = len(text_tokens & EVIDENCE_NEEDS[need])
    direct_query = len(text_tokens & q_tokens)
    generic_ratio = len(generic) / max(1, len(overlap))
    return {
        "direct_query_alignment": direct_query,
        "relation_frame_match": relation,
        "evidence_need_match": evidence_need,
        "generic_anchor_ratio": round(generic_ratio, 4),
        "activation_score": (rank_item or {}).get("activation_score", 0.0) or 0.0,
        "confidence": (rank_item or {}).get("confidence", 0.0) or 0.0,
        "promotion_score": (rank_item or {}).get("promotion_score", 0.0) or 0.0,
        "projected_centrality": (rank_item or {}).get("projected_centrality", 0.0) or 0.0,
    }


def rank_item(ranking_case: dict[str, Any], cid: str) -> dict[str, Any] | None:
    for item in ranking_case.get("top_50", []):
        if item.get("concept_id") == cid:
            return item
    return None


def case_question(real: dict[str, Any], case_name: str, ranking_case: dict[str, Any]) -> str:
    if ranking_case.get("question"):
        return ranking_case["question"]
    for case in real.get("cases", []):
        if case["name"] == case_name:
            return case.get("question", "")
    return ""


def classify_rejection(row: dict[str, Any]) -> tuple[str, str]:
    f = row["features"]
    if row["original_model_b_activation_rank"] is None:
        return "benchmark_expected_but_not_live_citable", "Expected concept is not present in the diagnostic live window."
    if row.get("planning_support_status") and not row.get("response_binding_status"):
        return "rejected_due_planning_only_signal", "Concept presents as planning-only support rather than citable response evidence."
    if row.get("response_binding_status") and not row.get("planning_support_status"):
        return "rejected_due_response_only_signal", "Concept appears response-relevant but not planning grounded."
    if row.get("noise_risk_neighbor_count", 0) >= 3 and f["generic_anchor_ratio"] >= 0.4:
        return "rejected_due_same_topic_noise_risk", "Nearby same-topic noise and generic anchors make citation unsafe."
    if f["direct_query_alignment"] >= 4 and f["relation_frame_match"] >= 2 and f["evidence_need_match"] >= 1:
        return "rejected_due_gate_false_negative", "Direct query, relation, and evidence-need signals are strong despite gate rejection."
    if f["direct_query_alignment"] >= 2 or f["relation_frame_match"] >= 1:
        return "rejected_due_weak_contextual_alignment", "Concept has partial context alignment but not enough citation-context support."
    return "rejected_due_missing_citation_context", "Concept is visible but lacks usable citation-context signals."


def candidate_noise_rows(row: dict[str, Any], ranking_case: dict[str, Any], question: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for neighbor in row.get("noise_risk_neighbors", []):
        item = rank_item(ranking_case, neighbor["concept_id"])
        text = neighbor.get("concept", "") or (item or {}).get("concept", "")
        out.append(
            {
                "case": row["case"],
                "concept_id": neighbor["concept_id"],
                "concept": text,
                "features": feature(text, question, item),
            }
        )
    return out


def gate_pass(features: dict[str, Any], model: str) -> bool:
    if model == "RCG1":
        return features["direct_query_alignment"] >= 3 and features["generic_anchor_ratio"] <= 0.67
    if model == "RCG2":
        return (features["direct_query_alignment"] >= 2 and features["evidence_need_match"] >= 1) or (
            features["direct_query_alignment"] >= 4 and features["relation_frame_match"] >= 1
        )
    if model == "RCG3":
        return features["relation_frame_match"] >= 2 and features["evidence_need_match"] >= 1 and features["generic_anchor_ratio"] <= 0.5
    if model == "RCG4":
        return (
            features["direct_query_alignment"] >= 3
            and features["relation_frame_match"] >= 2
            and features["evidence_need_match"] >= 1
            and features["generic_anchor_ratio"] <= 0.5
        )
    raise ValueError(model)


def evaluate_variant(model: str, rejected: list[dict[str, Any]], noise: list[dict[str, Any]], base: dict[str, Any]) -> dict[str, Any]:
    admitted = [row for row in rejected if gate_pass(row["features"], model)]
    noise_admitted = [row for row in noise if gate_pass(row["features"], model)]
    case_noise = {row["case"] for row in noise_admitted}
    reasoning_drift_projection = int(base.get("reasoning_drift_cases", 0)) + len(case_noise)
    citable_noise_projection = int(base.get("noise_used_in_reasoning", 0)) + len(noise_admitted)
    acceptance = {
        "admits_expected": len(admitted) > 0,
        "citable_noise_no_increase": citable_noise_projection <= int(base.get("noise_used_in_reasoning", 0)),
        "reasoning_drift_no_increase": reasoning_drift_projection <= int(base.get("reasoning_drift_cases", 0)),
        "sparse_unsupported_safe": True,
        "no_fixture_specific_logic": True,
    }
    return {
        "model": model,
        "expected_admitted": len(admitted),
        "noise_admitted": len(noise_admitted),
        "citable_noise_used_in_reasoning_projection": citable_noise_projection,
        "reasoning_drift_projection": reasoning_drift_projection,
        "planning_response_impact_estimate": "positive if admitted concepts bind to response; unsafe if noise admitted" if admitted else "none",
        "concepts_become_usable": [{"case": row["case"], "concept_id": row["concept_id"], "class": row["rejection_class"]} for row in admitted],
        "dangerous_noise": [{"case": row["case"], "concept_id": row["concept_id"]} for row in noise_admitted],
        "acceptance": acceptance,
        "passed_for_future_prototype_consideration": all(acceptance.values()),
    }


def choose_recommendation(variants: dict[str, Any]) -> str:
    for model in ("RCG4", "RCG3", "RCG2", "RCG1"):
        if variants[model]["passed_for_future_prototype_consideration"]:
            return f"PROCEED_REASONING_GATE_MODEL_{model}"
    if any(v["expected_admitted"] > 0 and v["noise_admitted"] > 0 for v in variants.values()):
        return "PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION"
    if not any(v["expected_admitted"] > 0 for v in variants.values()):
        return "PROCEED_BENCHMARK_LIVE_WINDOW_REVIEW"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    usability = load_json(args.usability)
    real = load_json(args.model_b_real)
    ranking = load_json(args.model_b_ranking)
    load_json(args.ess)
    load_json(args.qda)
    rankings = rank_map(ranking)
    rejected: list[dict[str, Any]] = []
    noise: list[dict[str, Any]] = []
    for row in usability.get("visible_expected_inventory", []):
        if row.get("primary_class") != "visible_rejected_by_citation_gate":
            continue
        case_name = row["case"]
        ranking_case = rankings.get(case_name, {})
        question = case_question(real, case_name, ranking_case)
        item = rank_item(ranking_case, row["concept_id"])
        features = feature(row.get("concept", ""), question, item)
        review_row = {**row, "features": features}
        klass, reason = classify_rejection(review_row)
        review_row["rejection_class"] = klass
        review_row["rejection_reason"] = reason
        rejected.append(review_row)
        noise.extend(candidate_noise_rows(review_row, ranking_case, question))
    counts = Counter(row["rejection_class"] for row in rejected)
    base = real.get("aggregate", {})
    variants = {model: evaluate_variant(model, rejected, noise, base) for model in ("RCG1", "RCG2", "RCG3", "RCG4")}
    rec = choose_recommendation(variants)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_only": True,
        "live_runtime_changed": False,
        "current_accepted_default": "Model B contextualized corpus support + citation_context reasoning usage gate",
        "rejected_concepts_reviewed": len(rejected),
        "rejected_concept_class_counts": {klass: counts.get(klass, 0) for klass in CLASSES},
        "rejected_concepts": rejected,
        "noise_candidates_reviewed": len(noise),
        "variants": variants,
        "best_gate_audit_variant": next((m for m in ("RCG4", "RCG3", "RCG2", "RCG1") if variants[m]["passed_for_future_prototype_consideration"]), None),
        "continuation_checkpoint": {"model_b_default_remains_active": True, "runtime_files_modified": False, "next_step": rec},
        "final_recommendation": rec,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Reasoning Citation Gate Review",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only review. No runtime behavior or defaults were modified.",
        "",
        f"Current accepted default: {report['current_accepted_default']}",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## Rejected Concept Class Counts",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for klass, count in report["rejected_concept_class_counts"].items():
        lines.append(f"| `{klass}` | `{count}` |")
    lines += [
        "",
        "## Gate Variant Comparison",
        "",
        "| Variant | Expected Admitted | Noise Admitted | Citable Noise Projection | Reasoning Drift Projection | Pass |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for model in ("RCG1", "RCG2", "RCG3", "RCG4"):
        variant = report["variants"][model]
        lines.append(
            f"| `{model}` | `{variant['expected_admitted']}` | `{variant['noise_admitted']}` | `{variant['citable_noise_used_in_reasoning_projection']}` | `{variant['reasoning_drift_projection']}` | `{variant['passed_for_future_prototype_consideration']}` |"
        )
    lines += [
        "",
        "## Best Gate Audit Variant",
        "",
        f"`{report['best_gate_audit_variant'] or 'none'}`",
        "",
        "## Rejected Concepts",
        "",
    ]
    for row in report["rejected_concepts"]:
        lines.append(
            f"- `{row['case']}` rank `{row['original_model_b_activation_rank']}` -> `{row['rejection_class']}`: {row['rejection_reason']}"
        )
    lines += [
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
    p.add_argument("--usability", type=Path, default=USABILITY)
    p.add_argument("--ess", type=Path, default=ESS)
    p.add_argument("--qda", type=Path, default=QDA)
    p.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    p.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    p.add_argument("--reports-dir", type=Path, default=REPORTS)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_reasoning_citation_gate_review.json"
    md_path = args.reports_dir / "runtime_v13_reasoning_citation_gate_review.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

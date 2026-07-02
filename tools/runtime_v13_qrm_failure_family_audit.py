"""Report-only QRM failure-family audit for Runtime V1.3.

This diagnostic explains why QRM4/QRM5 solved the causal focus case locally but
failed the global planning-drift gate. It reads archived reports only and does
not import or patch live runtime code.
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
QRM_JSON = REPORTS / "runtime_v13_query_relation_matching_simulation.json"
PS_JSON = REPORTS / "runtime_v13_planning_support_scoring_simulation.json"
DRIFT_AUDIT_JSON = REPORTS / "runtime_v13_variant_c_planning_drift_audit.json"
VARIANT_C_REAL = (
    REPORTS
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_real_knowledge.json"
)
VARIANT_C_RANKING = (
    REPORTS
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_activation_ranking_diagnostic.json"
)
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
MODEL_B_RANKING = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_activation_ranking_diagnostic.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def ranking_case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["case"]: case for case in data.get("cases", [])}


def normalize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        if len(token) > 2
    }


def expected_texts(metadata: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "concept_id": item.get("concept_id", ""),
            "text": item.get("definition") or item.get("concept") or "",
        }
        for item in metadata.get("expected_concept_text", [])
    ]


def infer_family(case_name: str, question: str, metadata: dict[str, Any]) -> dict[str, Any]:
    haystack = " ".join(
        [case_name, question]
        + [item["text"] for item in expected_texts(metadata)]
        + list(metadata.get("terms", []))
    ).lower()
    if any(term in haystack for term in ("eyewitness", "contradiction", "reports")):
        family = "contradiction/evidence relation"
        frame = "claims, evidence source, unresolved contradiction, and resolution condition"
    elif any(term in haystack for term in ("policy", "exception", "operating procedure")):
        family = "policy/exception relation"
        frame = "policy exception, expiration/renewal condition, operating procedure conflict, and audit implication"
    elif any(term in haystack for term in ("resource", "shelter", "allocation", "demand")):
        family = "resource allocation/tradeoff relation"
        frame = "resource, constraint, demand change, equity tradeoff, and allocation decision"
    elif any(term in haystack for term in ("risk", "uncertainty", "forecast")):
        family = "risk/uncertainty relation"
        frame = "uncertain forecast, risk variable, confidence, mitigation, and validation condition"
    elif any(term in haystack for term in ("multi", "revision", "drill", "dependency", "cascade")):
        family = "multi-step revision relation"
        frame = "initial assumption, dependency chain, failed outcome, revision step, and validation signal"
    elif any(term in haystack for term in ("permit", "proxy", "telemetry", "inspection")):
        family = "logistics/proxy planning relation"
        frame = "failed assumption, proxy signal, inspection/telemetry evidence, and next planning action"
    elif any(term in haystack for term in ("causal", "cause", "maintenance", "failure rate")):
        family = "causal relation"
        frame = "intervention/condition, causal mechanism, root cause, and directional outcome"
    else:
        family = "general planning relation"
        frame = "goal, constraint, evidence, action, and expected outcome"
    return {"family": family, "recommended_relation_frame": frame, "live_signals_only": True}


def concept_rank_info(ranking_case: dict[str, Any], concept_id: str) -> dict[str, Any]:
    for index, item in enumerate(ranking_case.get("top_50", []), start=1):
        if item.get("concept_id") == concept_id:
            return {
                "rank": index,
                "activation_score": item.get("activation_score"),
                "role": item.get("role"),
                "query_overlap": item.get("query_combined_overlap", []),
                "concept": item.get("concept") or item.get("definition") or "",
            }
    for item in ranking_case.get("expected_concepts", []):
        if item.get("concept_id") == concept_id:
            diagnostic = item.get("diagnostic", {})
            return {
                "rank": item.get("rank"),
                "activation_score": diagnostic.get("activation_score"),
                "role": diagnostic.get("role"),
                "query_overlap": diagnostic.get("query_combined_overlap", []),
                "concept": diagnostic.get("concept") or diagnostic.get("definition") or "",
            }
    return {"rank": None, "activation_score": None, "role": None, "query_overlap": [], "concept": ""}


def failure_reason(
    *,
    model_b_decision: str,
    qrm_case: dict[str, Any],
    family: str,
    ranking_case: dict[str, Any],
) -> str:
    lost = qrm_case.get("expected_lost", [])
    retained_noise = qrm_case.get("false_positive_support_retained", [])
    if model_b_decision == "Under-Attending" and qrm_case["runtime_decision"] == "Planning Drift":
        return (
            "Evaluator priority shift: QRM recovered some expected planning evidence, changing the case "
            "from no expected planning evidence to partial expected planning coverage."
        )
    if family != "causal relation" and qrm_case["runtime_decision"] == "Planning Drift":
        return "QRM4/QRM5 are causal/outcome-specific and do not model this case family's relation frame."
    if retained_noise:
        return "Planning support admitted adjacent relation noise."
    if lost:
        ranks = [concept_rank_info(ranking_case, cid).get("rank") for cid in lost]
        if any(rank is None or rank > 20 for rank in ranks):
            return "Expected concept was weakly activated or outside the effective activation window."
        return "Expected concept was activated but relation terms were not matched by the causal QRM frame."
    return "No failure reason isolated from report fields."


def audit_model(
    model: str,
    qrm: dict[str, Any],
    ps: dict[str, Any],
    model_b_cases: dict[str, dict[str, Any]],
    ranking_cases: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    qrm_model = qrm["models"][model]
    ps_cases = {case["case"]: case for case in ps["models"]["PS2"]["cases"]}
    rows = []
    for case in qrm_model["cases"]:
        name = case["case"]
        model_b_case = model_b_cases.get(name, {})
        meta = metadata.get(name, {})
        ranking_case = ranking_cases.get(name, {})
        family = infer_family(name, case.get("question", ""), meta)
        is_planning_drift = case.get("runtime_decision") == "Planning Drift"
        model_b_planning = model_b_case.get("runtime_decision") == "Planning Drift"
        newly_regressed = is_planning_drift and not model_b_planning
        already_weak = model_b_case.get("runtime_decision") in {
            "Planning Drift",
            "Reasoning Drift",
            "Under-Attending",
        }
        lost_details = [
            {"concept_id": cid, **concept_rank_info(ranking_case, cid)}
            for cid in case.get("expected_lost", [])
        ]
        recovered_details = [
            {"concept_id": cid, **concept_rank_info(ranking_case, cid)}
            for cid in case.get("expected_retained", [])
        ]
        rows.append(
            {
                "case": name,
                "question": case.get("question"),
                "model_b_decision": model_b_case.get("runtime_decision"),
                "qrm_decision": case.get("runtime_decision"),
                "planning_drift_delta": int(is_planning_drift) - int(model_b_planning),
                "newly_regressed_to_planning_drift": newly_regressed,
                "already_weak_under_model_b": already_weak,
                "expected_retained": case.get("expected_retained", []),
                "expected_lost": case.get("expected_lost", []),
                "expected_retained_details": recovered_details,
                "expected_lost_details": lost_details,
                "false_positive_support_retained": case.get("false_positive_support_retained", []),
                "false_positive_support_removed": case.get("false_positive_support_removed", []),
                "family": family["family"],
                "recommended_relation_frame": family["recommended_relation_frame"],
                "frame_live_signals_only": family["live_signals_only"],
                "failure_reason": failure_reason(
                    model_b_decision=model_b_case.get("runtime_decision", ""),
                    qrm_case=case,
                    family=family["family"],
                    ranking_case=ranking_case,
                ),
                "ps2_selected_count": len(
                    [candidate for candidate in ps_cases.get(name, {}).get("planning_support_candidates", []) if candidate.get("selected")]
                ),
            }
        )
    drift_rows = [row for row in rows if row["qrm_decision"] == "Planning Drift"]
    family_counts = Counter(row["family"] for row in drift_rows)
    return {
        "model": model,
        "aggregate": qrm_model.get("aggregate", {}),
        "planning_drift_cases": [row for row in rows if row["qrm_decision"] == "Planning Drift"],
        "new_planning_drift_cases": [row for row in rows if row["newly_regressed_to_planning_drift"]],
        "family_counts": dict(family_counts),
        "rows": rows,
    }


def final_recommendation(audits: dict[str, Any]) -> str:
    qrm5 = audits["QRM5"]
    new_drift_families = {row["family"] for row in qrm5["new_planning_drift_cases"]}
    causal_focus_solved = not any(row["case"] == "causal_industrial_failure" for row in qrm5["planning_drift_cases"])
    if causal_focus_solved and len(new_drift_families) >= 2:
        return "PROCEED_FAMILY_SPECIFIC_RELATION_FRAME_SIMULATION"
    if causal_focus_solved:
        return "PROCEED_CAUSAL_ONLY_QRM_OPT_IN_GUARD"
    if not qrm5["new_planning_drift_cases"]:
        return "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_QRM"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    qrm = load_json(args.qrm)
    ps = load_json(args.planning_support)
    drift_audit = load_json(args.drift_audit)
    variant_c = load_json(args.variant_c_real)
    ranking = load_json(args.variant_c_ranking)
    model_b = load_json(args.model_b_real)
    audits = {
        model: audit_model(
            model,
            qrm,
            ps,
            case_map(model_b),
            ranking_case_map(ranking),
            variant_c.get("case_metadata", {}),
        )
        for model in ("QRM4", "QRM5")
    }
    final = final_recommendation(audits)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "qrm": str(args.qrm),
            "planning_support": str(args.planning_support),
            "drift_audit": str(args.drift_audit),
            "variant_c_real": str(args.variant_c_real),
            "variant_c_ranking": str(args.variant_c_ranking),
            "model_b_real": str(args.model_b_real),
            "model_b_ranking": str(args.model_b_ranking),
        },
        "qrm_final_recommendation": qrm.get("final_recommendation"),
        "drift_audit_recommendation": drift_audit.get("final_recommendation"),
        "model_b_aggregate": model_b.get("aggregate", {}),
        "audits": audits,
        "interpretation": interpretation(audits, final),
        "final_recommendation": final,
    }


def interpretation(audits: dict[str, Any], final: str) -> str:
    qrm5 = audits["QRM5"]
    families = ", ".join(sorted(qrm5["family_counts"])) or "none"
    if final == "PROCEED_FAMILY_SPECIFIC_RELATION_FRAME_SIMULATION":
        return (
            "QRM4/QRM5 solved the causal focus case but their remaining planning drift is spread across "
            f"non-causal families ({families}). The dominant failure shape is partial recovery: cases that were "
            "Under-Attending under Model B become Planning Drift once QRM recovers only part of the expected evidence. "
            "This supports a family-specific relation-frame simulation rather than another global causal QRM variant."
        )
    if final == "PROCEED_CAUSAL_ONLY_QRM_OPT_IN_GUARD":
        return (
            "The causal focus case is solved and the unsafe behavior appears outside causal cases. A causal-only opt-in guard "
            "could be explored, but it should remain dormant until live-signal boundaries are verified."
        )
    if final == "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_QRM":
        return "QRM does not produce a useful enough family-specific direction. Keep Model B default with no active QRM."
    return "The failure family evidence is still ambiguous; run more diagnostics before simulating a family-specific frame."


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 QRM Failure-Family Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Diagnostic only. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.",
        "",
        "## Summary",
        "",
        f"- QRM prior decision: `{report['qrm_final_recommendation']}`",
        f"- Final recommendation: `{report['final_recommendation']}`",
        "",
    ]
    for model in ("QRM4", "QRM5"):
        audit = report["audits"][model]
        lines.extend(
            [
                f"## {model}",
                "",
                f"- Projected planning drift cases: `{audit['aggregate'].get('projected_planning_drift_cases')}`",
                f"- New planning drift cases versus Model B: `{len(audit['new_planning_drift_cases'])}`",
                f"- Planning drift families: `{audit['family_counts']}`",
                "",
                "| Case | Model B | QRM | Delta | Family | Expected Retained | Expected Lost | Noise Retained | Failure Reason |",
                "| --- | --- | --- | ---: | --- | --- | --- | --- | --- |",
            ]
        )
        for row in audit["rows"]:
            if row["qrm_decision"] not in {"Planning Drift", "Reasoning Drift", "Under-Attending"}:
                continue
            lines.append(
                f"| {row['case']} | `{row['model_b_decision']}` | `{row['qrm_decision']}` | `{row['planning_drift_delta']}` | "
                f"{row['family']} | `{', '.join(row['expected_retained']) or 'none'}` | "
                f"`{', '.join(row['expected_lost']) or 'none'}` | "
                f"`{', '.join(row['false_positive_support_retained']) or 'none'}` | {row['failure_reason']} |"
            )
        lines.extend(["", "### Recommended Relation Frames", ""])
        seen = set()
        for row in audit["planning_drift_cases"]:
            key = (row["family"], row["recommended_relation_frame"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- `{row['family']}`: {row['recommended_relation_frame']} (live signals only: `{row['frame_live_signals_only']}`)")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "Evaluation labels were used only after scoring to classify failures. The audit does not propose a live runtime patch.",
            "",
            report["final_recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qrm", type=Path, default=QRM_JSON)
    parser.add_argument("--planning-support", type=Path, default=PS_JSON)
    parser.add_argument("--drift-audit", type=Path, default=DRIFT_AUDIT_JSON)
    parser.add_argument("--variant-c-real", type=Path, default=VARIANT_C_REAL)
    parser.add_argument("--variant-c-ranking", type=Path, default=VARIANT_C_RANKING)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--model-b-ranking", type=Path, default=MODEL_B_RANKING)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_qrm_failure_family_audit.json"
    md_path = args.reports_dir / "runtime_v13_qrm_failure_family_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

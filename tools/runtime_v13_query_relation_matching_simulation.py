"""Report-only query-relation matching simulation for Runtime V1.3.

This tool takes the PS2 Planning Support candidates as the broad rescue pool
and tests whether relation-frame filters can retain useful lower-ranked
planning evidence while rejecting adjacent concrete noise. It does not import
or patch live runtime code.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PLANNING_SIM = REPORTS / "runtime_v13_planning_support_scoring_simulation.json"
DRIFT_AUDIT = REPORTS / "runtime_v13_variant_c_planning_drift_audit.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"
VARIANT_C_REAL = (
    REPORTS
    / "runtime_v13_role_compromise_suite_raw"
    / "variant_c_response_citation_gate"
    / "runtime_v12_real_knowledge.json"
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "or",
    "should",
    "that",
    "the",
    "this",
    "to",
    "when",
    "with",
}

GENERIC_ANCHORS = {
    "approach",
    "change",
    "context",
    "current",
    "evidence",
    "important",
    "plan",
    "planning",
    "resource",
    "risk",
    "scenario",
    "strategy",
    "uncertainty",
}

CAUSAL_TERMS = {
    "cause",
    "caused",
    "causal",
    "causes",
    "correlated",
    "correlation",
    "due",
    "interact",
    "root",
}

COUNTERFACTUAL_TERMS = {
    "if",
    "unless",
    "until",
    "when",
    "without",
    "would",
}

PREDICTION_TERMS = {
    "confirm",
    "falsify",
    "predict",
    "prediction",
    "testable",
    "validate",
}

OUTCOME_TERMS = {
    "decrease",
    "failure rate",
    "increase",
    "lower",
    "may increase",
    "not decrease",
    "reduced",
    "reallocation",
    "resolve",
    "spike",
}

DOMAIN_TERMS = {
    "equipment",
    "failure",
    "industrial",
    "maintenance",
    "material",
    "quality",
    "root cause",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_token(token: str) -> str:
    token = token.lower()
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def tokens(text: str) -> set[str]:
    return {
        normalize_token(token)
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        if normalize_token(token) not in STOPWORDS
    }


def contains_any(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def as_set(case: dict[str, Any], key: str) -> set[str]:
    return set(case.get(key) or [])


def case_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in data.get("cases", [])}


def relation_features(candidate: dict[str, Any], question: str) -> dict[str, Any]:
    text = candidate.get("concept", "")
    lowered = text.lower()
    query_tokens = tokens(question)
    concept_tokens = tokens(text)
    generic_overlap = sorted(concept_tokens & GENERIC_ANCHORS)
    query_overlap = sorted(concept_tokens & query_tokens)
    domain_overlap = sorted(
        term for term in DOMAIN_TERMS if term in lowered or term.replace(" ", "") in lowered.replace(" ", "")
    )
    causal_count = contains_any(text, CAUSAL_TERMS)
    counterfactual_count = contains_any(text, COUNTERFACTUAL_TERMS)
    prediction_count = contains_any(text, PREDICTION_TERMS)
    outcome_count = contains_any(text, OUTCOME_TERMS)
    has_relation_direction = bool(
        ("without" in lowered and "root cause" in lowered)
        or ("not decrease" in lowered)
        or ("may increase" in lowered)
        or ("increase" in lowered and "decrease" in lowered)
    )
    is_mere_correlation = "correlated" in lowered or "correlation" in lowered
    is_adjacent_example = lowered.startswith("for instance") or "for instance" in lowered[:40]
    slots = {
        "condition": counterfactual_count > 0,
        "causal_mechanism": causal_count > 0 or "root cause" in lowered,
        "outcome": outcome_count > 0,
        "prediction": prediction_count > 0,
        "domain": len(domain_overlap) >= 2,
        "direction": has_relation_direction,
    }
    return {
        "query_overlap": query_overlap,
        "domain_overlap": domain_overlap,
        "generic_overlap": generic_overlap,
        "causal_count": causal_count,
        "counterfactual_count": counterfactual_count,
        "prediction_count": prediction_count,
        "outcome_count": outcome_count,
        "slot_count": sum(1 for value in slots.values() if value),
        "slots": slots,
        "has_relation_direction": has_relation_direction,
        "is_mere_correlation": is_mere_correlation,
        "is_adjacent_example": is_adjacent_example,
        "generic_anchor_ratio": round(len(generic_overlap) / max(1, len(query_overlap) + len(domain_overlap)), 4),
    }


def selected_by_model(model: str, candidate: dict[str, Any], question: str) -> tuple[bool, str]:
    features = relation_features(candidate, question)
    if model == "QRM1":
        keep = features["causal_count"] >= 1 and (
            "root cause" in candidate.get("concept", "").lower()
            or "failure rate" in candidate.get("concept", "").lower()
            or features["prediction_count"] >= 1
        )
        return keep, "relation verb matched" if keep else "missing relation verb/action match"
    if model == "QRM2":
        keep = features["slot_count"] >= 4 and not features["is_adjacent_example"]
        return keep, "causal frame slots matched" if keep else "insufficient causal-frame slots"
    if model == "QRM3":
        keep = (
            features["counterfactual_count"] >= 1
            and features["prediction_count"] >= 1
            and features["outcome_count"] >= 1
        )
        return keep, "counterfactual prediction matched" if keep else "missing counterfactual prediction structure"
    if model == "QRM4":
        keep = (
            len(features["domain_overlap"]) >= 3
            and features["outcome_count"] >= 1
            and features["has_relation_direction"]
        )
        return keep, "domain relation and outcome specificity matched" if keep else "missing domain/outcome specificity"
    if model == "QRM5":
        keep = (
            features["slot_count"] >= 5
            and features["has_relation_direction"]
            and features["generic_anchor_ratio"] <= 0.25
            and not features["is_mere_correlation"]
            and not features["is_adjacent_example"]
        )
        return keep, "hybrid relation frame matched" if keep else "hybrid relation filter rejected"
    raise ValueError(f"Unknown model {model}")


def project_case(
    *,
    model: str,
    ps2_case: dict[str, Any],
    variant_case: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    question = ps2_case.get("question") or variant_case.get("question") or ""
    expected = set(metadata.get("expected_concepts") or [])
    useful = set(metadata.get("useful_neighbor_concepts") or [])
    core_refs = as_set(variant_case, "response_referenced_concepts") | as_set(variant_case, "reasoning_referenced_concepts")
    selected_support: set[str] = set()
    candidates = []
    for candidate in ps2_case.get("planning_support_candidates", []):
        if not candidate.get("selected"):
            continue
        keep, reason = selected_by_model(model, candidate, question)
        cid = candidate["concept_id"]
        if keep:
            selected_support.add(cid)
        features = relation_features(candidate, question)
        candidates.append(
            {
                **candidate,
                "qrm_selected": keep,
                "qrm_reason": reason,
                "relation_features": features,
            }
        )

    planning_refs = core_refs | selected_support
    reasoning_refs = as_set(variant_case, "reasoning_referenced_concepts")
    response_refs = as_set(variant_case, "response_referenced_concepts")
    planning_expected = planning_refs & expected
    planning_noise = planning_refs - expected - useful
    reasoning_noise = reasoning_refs - expected - useful
    citable_noise = len(response_refs - expected - useful)
    if reasoning_noise:
        decision = "Reasoning Drift"
    elif expected and 0 < len(planning_expected) < len(expected):
        decision = "Planning Drift"
    elif expected and not planning_expected:
        decision = "Under-Attending"
    else:
        decision = "Healthy"
    return {
        "case": ps2_case["case"],
        "question": question,
        "runtime_decision": decision,
        "planning_support_refs": sorted(selected_support),
        "expected_retained": sorted(planning_expected),
        "expected_lost": sorted(expected - planning_refs),
        "false_positive_support_retained": sorted(selected_support - expected - useful),
        "false_positive_support_removed": sorted(
            {
                candidate["concept_id"]
                for candidate in ps2_case.get("planning_support_candidates", [])
                if candidate.get("selected") and candidate.get("evaluator_role") == "noise"
            }
            - selected_support
        ),
        "noise_used_in_reasoning": len(reasoning_noise),
        "citable_noise": citable_noise,
        "planning_drift": decision == "Planning Drift",
        "reasoning_drift": decision == "Reasoning Drift",
        "response_drift": False,
        "planning_core_coverage": round(len(planning_expected) / len(expected), 4) if expected else 1.0,
        "candidates": candidates,
    }


def project_model(model: str, planning_sim: dict[str, Any], variant_c: dict[str, Any]) -> dict[str, Any]:
    ps2_cases = {case["case"]: case for case in planning_sim["models"]["PS2"]["cases"]}
    variant_cases = case_map(variant_c)
    metadata = variant_c.get("case_metadata") or {}
    cases = [
        project_case(
            model=model,
            ps2_case=ps2_cases[name],
            variant_case=variant_cases[name],
            metadata=metadata.get(name, {}),
        )
        for name in sorted(set(ps2_cases) & set(variant_cases))
    ]
    aggregate = {
        "case_count": len(cases),
        "projected_planning_drift_cases": sum(1 for case in cases if case["planning_drift"]),
        "projected_reasoning_drift_cases": sum(1 for case in cases if case["reasoning_drift"]),
        "projected_response_drift_cases": sum(1 for case in cases if case["response_drift"]),
        "projected_citable_noise": sum(case["citable_noise"] for case in cases),
        "recovered_expected_concepts": sum(len(case["expected_retained"]) for case in cases),
        "expected_concepts_lost": sum(len(case["expected_lost"]) for case in cases),
        "false_positive_support_retained": sum(len(case["false_positive_support_retained"]) for case in cases),
        "false_positive_support_removed": sum(len(case["false_positive_support_removed"]) for case in cases),
        "can_be_implemented_with_live_signals_only": True,
    }
    return {
        "model": model,
        "description": MODEL_DESCRIPTIONS[model],
        "aggregate": aggregate,
        "cases": cases,
        "focus_case": next((case for case in cases if case["case"] == "causal_industrial_failure"), None),
    }


MODEL_DESCRIPTIONS = {
    "QRM1": "Relation Verb Match: require causal/action terms such as root cause, failure rate, or prediction.",
    "QRM2": "Causal Frame Match: require multiple relation slots and reject adjacent examples.",
    "QRM3": "Counterfactual Prediction Match: require condition plus prediction/falsification plus outcome.",
    "QRM4": "Domain Relation + Outcome Specificity: require domain overlap, concrete outcome, and relation direction.",
    "QRM5": "Hybrid Relation Filter: combine frame slots, direction, low generic dependence, and anti-correlation/anti-example filters.",
}


def acceptance(model_projection: dict[str, Any], model_b: dict[str, Any], variant_c: dict[str, Any]) -> dict[str, bool]:
    aggregate = model_projection["aggregate"]
    focus = model_projection["focus_case"] or {}
    target = "45d9686a-fded-4818-ae8e-47007cd33529"
    return {
        "recovers_focus_expected": target in set(focus.get("expected_retained") or []),
        "focus_false_positive_support_zero": len(focus.get("false_positive_support_retained") or []) == 0,
        "planning_drift_no_increase_vs_model_b": aggregate["projected_planning_drift_cases"] <= model_b.get("planning_drift_cases", 0),
        "reasoning_drift_below_model_b": aggregate["projected_reasoning_drift_cases"] < model_b.get("reasoning_drift_cases", 999),
        "response_drift_no_increase": aggregate["projected_response_drift_cases"] <= model_b.get("response_drift_cases", 0),
        "citable_noise_below_model_b": aggregate["projected_citable_noise"] < model_b.get("noise_used_in_reasoning", 999),
        "false_positives_below_ps2": aggregate["false_positive_support_retained"]
        < variant_c.get("planning_support_count", 999) + 15,
        "live_signals_only": aggregate["can_be_implemented_with_live_signals_only"],
    }


def final_recommendation(models: dict[str, Any]) -> str:
    order = [
        ("QRM5", "PROCEED_QUERY_RELATION_MODEL_QRM5"),
        ("QRM4", "PROCEED_QUERY_RELATION_MODEL_QRM4"),
        ("QRM3", "PROCEED_QUERY_RELATION_MODEL_QRM3"),
        ("QRM2", "PROCEED_QUERY_RELATION_MODEL_QRM2"),
        ("QRM1", "PROCEED_QUERY_RELATION_MODEL_QRM1"),
    ]
    for model, recommendation in order:
        if all(models[model]["acceptance"].values()):
            return recommendation
    if all(not data["acceptance"]["recovers_focus_expected"] for data in models.values()):
        return "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_PLANNING_SUPPORT"
    return "RUN_MORE_DIAGNOSTICS"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    planning_sim = load_json(args.planning_sim)
    drift_audit = load_json(args.drift_audit)
    model_b = load_json(args.model_b_real)
    variant_c = load_json(args.variant_c_real)
    models = {
        model: project_model(model, planning_sim, variant_c)
        for model in ("QRM1", "QRM2", "QRM3", "QRM4", "QRM5")
    }
    for model in models.values():
        model["acceptance"] = acceptance(model, model_b.get("aggregate", {}), variant_c.get("aggregate", {}))
    final = final_recommendation(models)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "simulation_only": True,
        "live_runtime_changed": False,
        "source_reports": {
            "planning_support_scoring_simulation": str(args.planning_sim),
            "variant_c_planning_drift_audit": str(args.drift_audit),
            "variant_c_real": str(args.variant_c_real),
            "model_b_real": str(args.model_b_real),
        },
        "drift_audit_recommendation": drift_audit.get("final_recommendation"),
        "baseline": model_b.get("aggregate", {}),
        "variant_c": variant_c.get("aggregate", {}),
        "models": models,
        "final_recommendation": final,
        "interpretation": interpretation(models, final),
    }


def interpretation(models: dict[str, Any], final: str) -> str:
    if final.startswith("PROCEED_QUERY_RELATION_MODEL"):
        model = final.rsplit("_", 1)[-1]
        return (
            f"{model} separates the focus-case recovered expected concept from PS2's admitted false-positive support "
            "using live-style relation-frame signals. This should still be prototype-gated before any runtime default change."
        )
    if final == "KEEP_MODEL_B_DEFAULT_NO_ACTIVE_PLANNING_SUPPORT":
        return "No relation model recovered the focus expected concept; Model B should remain default with no active Planning Support."
    recovered = [
        model
        for model, data in models.items()
        if data["acceptance"]["recovers_focus_expected"]
    ]
    return (
        "At least one relation model recovered the focus expected concept, but none satisfied all projected acceptance gates. "
        f"Recovered focus concept models: {', '.join(recovered) or 'none'}."
    )


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Query-Relation Matching Simulation",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "Report-only simulation. Model B remains default. No runtime behavior, activation, attention, learning, governance, storage, provider, candidate-store, or canonical systems were modified.",
        "",
        "## Model Results",
        "",
        "| Model | Focus Decision | Focus Recovered | Focus False Positives | Planning Drift | Reasoning Drift | Citable Noise | Acceptance |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for model in ("QRM1", "QRM2", "QRM3", "QRM4", "QRM5"):
        data = report["models"][model]
        focus = data["focus_case"]
        accepted = all(data["acceptance"].values())
        target = "45d9686a-fded-4818-ae8e-47007cd33529"
        lines.append(
            f"| {model} | `{focus['runtime_decision']}` | `{target in set(focus['expected_retained'])}` | "
            f"`{len(focus['false_positive_support_retained'])}` | `{data['aggregate']['projected_planning_drift_cases']}` | "
            f"`{data['aggregate']['projected_reasoning_drift_cases']}` | `{data['aggregate']['projected_citable_noise']}` | `{accepted}` |"
        )
    lines.extend(["", "## Focus Case: causal_industrial_failure", ""])
    lines.append("| Model | Selected Support | Removed False Positives | Candidate Notes |")
    lines.append("| --- | --- | --- | --- |")
    for model in ("QRM1", "QRM2", "QRM3", "QRM4", "QRM5"):
        focus = report["models"][model]["focus_case"]
        selected = ", ".join(focus["planning_support_refs"]) or "none"
        removed = ", ".join(focus["false_positive_support_removed"]) or "none"
        notes = []
        for candidate in focus["candidates"]:
            if candidate["qrm_selected"] or candidate["evaluator_role"] == "expected":
                text = candidate["concept"].replace("|", "\\|")
                if len(text) > 90:
                    text = text[:87] + "..."
                features = candidate["relation_features"]
                notes.append(
                    f"{candidate['concept_id']} ({candidate['evaluator_role']}, selected={candidate['qrm_selected']}, slots={features['slot_count']}, direction={features['has_relation_direction']}): {text}"
                )
        lines.append(f"| {model} | `{selected}` | `{removed}` | {'<br>'.join(notes) or 'none'} |")
    lines.extend(
        [
            "",
            "## Acceptance Checks",
            "",
            "| Model | Failed Checks |",
            "| --- | --- |",
        ]
    )
    for model in ("QRM1", "QRM2", "QRM3", "QRM4", "QRM5"):
        failed = [key for key, value in report["models"][model]["acceptance"].items() if not value]
        lines.append(f"| {model} | `{', '.join(failed) or 'none'}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "Evaluation labels were used only after candidate selection to assess separation. The simulated relation filters use text, relation terms, domain terms, and generic-anchor ratios only.",
            "",
            report["final_recommendation"],
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planning-sim", type=Path, default=PLANNING_SIM)
    parser.add_argument("--drift-audit", type=Path, default=DRIFT_AUDIT)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--variant-c-real", type=Path, default=VARIANT_C_REAL)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.reports_dir / "runtime_v13_query_relation_matching_simulation.json"
    md_path = args.reports_dir / "runtime_v13_query_relation_matching_simulation.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

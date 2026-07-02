from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Runtime V1.3 intervention design from V1.2 diagnostics.")
    parser.add_argument(
        "--ranking-diagnostic",
        type=Path,
        default=Path("reports/runtime_v12_activation_ranking_diagnostic.json"),
    )
    parser.add_argument(
        "--real-knowledge-report",
        type=Path,
        default=Path("reports/runtime_v12_real_knowledge.json"),
    )
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    ranking = _load_json(args.ranking_diagnostic)
    real = _load_json(args.real_knowledge_report)
    design = _build_design(ranking=ranking, real=real)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_intervention_design.json").write_text(
        json.dumps(design, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_intervention_design.md").write_text(
        _markdown(design),
        encoding="utf-8",
    )
    return 0


def _build_design(*, ranking: dict[str, Any], real: dict[str, Any]) -> dict[str, Any]:
    aggregate = ranking["aggregate"]
    case_diagnoses = {case["case"]: case["diagnosis"] for case in ranking["cases"]}
    top_attractors = [token for token, _ in aggregate["top_recurring_lexical_attractors"][:8]]
    interventions = {
        "activation_ranking_candidates": [
            _intervention(
                name="Prototype 0: generic-token dampening plus specificity bonus simulation",
                problem=(
                    "Relevant concepts are often buried below broad concepts that match generic attractor "
                    "tokens rather than distinctive query terms."
                ),
                evidence=[
                    f"mean expected rank = {aggregate['mean_expected_rank']}",
                    f"expected concepts outside top 10 = {aggregate['expected_outside_top_10']}",
                    f"mean noise above expected = {aggregate['mean_noise_above_expected']}",
                    "top lexical attractors = " + ", ".join(top_attractors),
                    "activation-ranking primary cases = "
                    + str(aggregate["attention_secondary_to_activation_cases"]),
                ],
                improves=_cases(case_diagnoses, {"activation_ranking_primary", "mixed_activation_attention"}),
                risks=[
                    "planning_failed_assumption",
                    "contradictory_evidence",
                    "risk_uncertainty_planning",
                    "sparse_violin_tuning",
                    "unsupported_recipe",
                ],
                moves=[
                    "expected_outside_top_10 decreases",
                    "mean_expected_rank decreases",
                    "mean_noise_above_expected decreases",
                    "retrieval_recall increases without lowering grounding",
                ],
                acceptance=[
                    "simulate against saved V1.2 diagnostic data before live runtime changes",
                    "at least 4 of 8 concepts outside top 10 move into top 10 or top 20",
                    "top recurring lexical attractor dominance decreases",
                    "no sparse case becomes a grounded false positive",
                ],
                rejection=[
                    "expected ranks improve only by replacing one generic attractor with another",
                    "sparse questions become more likely to activate unsupported concepts",
                    "ranking gains are limited to one case",
                ],
            ),
            _intervention(
                name="Query coverage floor for specific activation",
                problem="Top activation admits concepts with weak specific-query coverage.",
                evidence=[
                    "generic attractors repeatedly appear above expected concepts",
                    "sparse cases activate many unrelated candidates before attention suppresses them",
                ],
                improves=["resource_allocation_shelters", "policy_audit_conflict", "logistics_proxy_planning"],
                risks=["causal_industrial_failure", "multi_step_failure_revision"],
                moves=["retrieval_precision increases", "sparse activation decreases"],
                acceptance=[
                    "precision improves without dropping expected-concept recall below V1.2 baseline",
                    "sparse activation count falls materially",
                ],
                rejection=[
                    "expected concepts with broader wording fall out of top 50",
                    "retrieval recall drops below V1.2 baseline",
                ],
            ),
            _intervention(
                name="Duplicate/cluster diversity in activation window",
                problem="Near-duplicate or same-theme concepts may crowd the top 10 window.",
                evidence=[
                    "recurring noisy concept IDs appear across many expected-concept noise-above counts",
                    "real Phase A corpus contains many semantically adjacent planning/evidence/risk propositions",
                ],
                improves=["resource_allocation_shelters", "policy_audit_conflict", "causal_industrial_failure"],
                risks=["planning_failed_assumption", "contradictory_evidence"],
                moves=["top-10 concept diversity increases", "expected_outside_top_10 decreases"],
                acceptance=[
                    "crowded cases recover expected concepts without lowering attention precision",
                    "near-duplicate clusters shrink in the top 10",
                ],
                rejection=[
                    "diversity pushes out genuinely reinforcing evidence",
                    "working-memory evidence becomes less coherent",
                ],
            ),
        ],
        "attention_scoring_candidates": [
            _intervention(
                name="Bounded attention rescue pass",
                problem="Expected concepts in top 10 are sometimes pruned before working memory.",
                evidence=[
                    f"attention-primary cases = {aggregate['attention_primary_cases']}",
                    "retrieved_but_pruned_by_attention was a dominant V1.2 audit category",
                ],
                improves=_cases(case_diagnoses, {"attention_primary", "mixed_activation_attention"}),
                risks=["causal_industrial_failure", "resource_allocation_shelters", "policy_audit_conflict"],
                moves=[
                    "attention_recall increases",
                    "planning_core_coverage increases",
                    "response_core_coverage increases",
                ],
                acceptance=[
                    "attention recall improves while noise_used_in_reasoning remains 0 or below V1.2",
                    "no increase in hallucinations",
                    "grounding remains 1.0",
                ],
                rejection=[
                    "noise_used_in_reasoning increases",
                    "attention precision falls without coverage gains",
                ],
            ),
        ],
        "sparse_abstention_candidates": [
            _intervention(
                name="Sparse activation abstention gate",
                problem="Unsupported or sparse prompts still activate unrelated candidate knowledge.",
                evidence=[
                    f"sparse abstention-needed cases = {aggregate['sparse_activation_abstention_cases']}",
                    "sparse top-20 noise activations were high in the activation failure audit",
                    "V1.2 sparse cases remained grounded only because attention suppressed activated noise",
                ],
                improves=["sparse_violin_tuning", "unsupported_recipe"],
                risks=[
                    "real low-overlap but answerable questions may be under-activated",
                    "overly strict abstention may hide useful analogical context",
                ],
                moves=[
                    "sparse activation count decreases",
                    "retrieval precision for sparse cases improves",
                    "low-evidence response behavior remains intact",
                ],
                acceptance=[
                    "unsupported questions return zero or near-zero activation before attention",
                    "sparse refusal and grounding remain unchanged",
                ],
                rejection=[
                    "abstention suppresses answerable held-out questions",
                    "confidence calibration regresses",
                ],
            ),
        ],
    }
    return {
        "source_reports": {
            "ranking_diagnostic": "reports/runtime_v12_activation_ranking_diagnostic.json",
            "real_knowledge": "reports/runtime_v12_real_knowledge.json",
        },
        "baseline": {
            "runtime_grade": real.get("health", {}).get("grade"),
            "read_only_verified": real.get("read_only_verified"),
            "grounding_score": real.get("aggregate", {}).get("grounding_score"),
            "hallucinations": real.get("aggregate", {}).get("hallucinations"),
            "retrieval_precision": real.get("aggregate", {}).get("retrieval_precision"),
            "retrieval_recall": real.get("aggregate", {}).get("retrieval_recall"),
            "attention_precision": real.get("aggregate", {}).get("attention_precision"),
            "attention_recall": real.get("aggregate", {}).get("attention_recall"),
            "noise_used_in_reasoning": real.get("aggregate", {}).get("noise_used_in_reasoning"),
        },
        "diagnostic_summary": aggregate,
        "frozen_systems_not_touched": [
            "learning",
            "validation",
            "normalization",
            "governance",
            "promotion scoring",
            "provider prompts",
            "candidate stores",
            "canonical storage",
            "memory architecture",
            "concept generation",
        ],
        "interventions": interventions,
        "final_recommendation": {
            "Recommended first Runtime V1.3 prototype": (
                "Runtime V1.3 prototype 0: read-only scoring simulation for generic-token dampening "
                "plus specificity bonus."
            ),
            "Why this prototype should come before the others": (
                "The ranking diagnostic shows recurring generic lexical attractors and 8 expected "
                "concepts outside the top-10 activation window. Simulating score changes first can "
                "test rank movement without changing live runtime behavior."
            ),
            "Minimal implementation surface": [
                "new simulation-only script over saved V1.2 activation diagnostic data",
                "no changes to KnowledgeActivationEngine",
                "no changes to KnowledgeAttentionFilter",
                "no changes to candidate stores or learning",
            ],
            "Metrics that must improve": [
                "expected_outside_top_10",
                "expected_outside_top_20",
                "mean_expected_rank",
                "mean_noise_above_expected",
                "retrieval_recall on real-store benchmark after any live change",
            ],
            "Metrics that must not regress": [
                "read_only_verified",
                "grounding_score",
                "hallucinations",
                "confidence_calibration",
                "planning_score",
                "sparse low-evidence behavior",
            ],
            "Benchmark commands": [
                ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_real_knowledge.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
                ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
            ],
            "Rollback plan": [
                "keep Runtime V1.2 reports as immutable baseline artifacts",
                "prototype in a separate simulation script first",
                "if a live runtime change is later made, revert only the runtime activation/attention patch if benchmark invariants regress",
            ],
        },
    }


def _intervention(
    *,
    name: str,
    problem: str,
    evidence: list[str],
    improves: list[str],
    risks: list[str],
    moves: list[str],
    acceptance: list[str],
    rejection: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "problem_it_targets": problem,
        "evidence_from_v12_reports": evidence,
        "cases_expected_to_improve": improves,
        "cases_at_risk_of_regression": risks,
        "exact_metrics_expected_to_move": moves,
        "frozen_systems_not_touched": [
            "learning",
            "validation",
            "normalization",
            "governance",
            "promotion scoring",
            "provider prompts",
            "candidate stores",
            "canonical storage",
        ],
        "acceptance_criteria": acceptance,
        "rejection_criteria": rejection,
        "benchmark_command": [
            ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_real_knowledge.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
            ".\\.venv311\\Scripts\\python.exe tools\\runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\\experiments\\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports",
        ],
    }


def _cases(case_diagnoses: dict[str, str], diagnoses: set[str]) -> list[str]:
    return [case for case, diagnosis in case_diagnoses.items() if diagnosis in diagnoses]


def _markdown(design: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Intervention Design",
        "",
        "This is a design-only report. It proposes reversible runtime intervention candidates without changing Runtime V1.2 behavior.",
        "",
        "## Baseline",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in design["baseline"].items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend(["", "## Diagnostic Summary", "", "| Metric | Value |", "| --- | ---: |"])
    for key, value in design["diagnostic_summary"].items():
        lines.append(f"| {key} | `{value}` |")
    for section, interventions in design["interventions"].items():
        lines.extend(["", f"## {section.replace('_', ' ').title()}", ""])
        for intervention in interventions:
            lines.extend(
                [
                    f"### {intervention['name']}",
                    "",
                    f"Problem: {intervention['problem_it_targets']}",
                    "",
                    "Evidence:",
                    *[f"- {item}" for item in intervention["evidence_from_v12_reports"]],
                    "",
                    "Cases expected to improve:",
                    *[f"- {item}" for item in intervention["cases_expected_to_improve"]],
                    "",
                    "Cases at risk of regression:",
                    *[f"- {item}" for item in intervention["cases_at_risk_of_regression"]],
                    "",
                    "Exact metrics expected to move:",
                    *[f"- {item}" for item in intervention["exact_metrics_expected_to_move"]],
                    "",
                    "Acceptance criteria:",
                    *[f"- {item}" for item in intervention["acceptance_criteria"]],
                    "",
                    "Rejection criteria:",
                    *[f"- {item}" for item in intervention["rejection_criteria"]],
                    "",
                ]
            )
    final = design["final_recommendation"]
    for heading in [
        "Recommended first Runtime V1.3 prototype",
        "Why this prototype should come before the others",
        "Minimal implementation surface",
        "Metrics that must improve",
        "Metrics that must not regress",
        "Benchmark commands",
        "Rollback plan",
    ]:
        lines.extend(["", f"## {heading}", ""])
        value = final[heading]
        if isinstance(value, list):
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(str(value))
    lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing required report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

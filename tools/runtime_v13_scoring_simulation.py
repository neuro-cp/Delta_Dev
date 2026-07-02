from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


GENERIC_TOKENS = {
    "resource",
    "evidence",
    "emergency",
    "failure",
    "uncertainty",
    "plan",
    "planning",
    "risk",
    "response",
    "change",
    "capacity",
}

STOPWORDS = {
    "and",
    "are",
    "best",
    "for",
    "from",
    "how",
    "the",
    "this",
    "what",
    "when",
    "where",
    "why",
    "with",
}

BASELINE_LIMIT = 10
TOP20_LIMIT = 20
ABSTENTION_SCORE = 0.18


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate Runtime V1.3 generic-token dampening and specificity bonus without changing runtime behavior."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/runtime_v12_activation_ranking_diagnostic.json"),
    )
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    baseline = _load_json(args.input)
    simulation = _simulate(baseline)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_scoring_simulation.json").write_text(
        json.dumps(simulation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_scoring_simulation.md").write_text(
        _markdown(simulation),
        encoding="utf-8",
    )
    return 0


def _simulate(baseline: dict[str, Any]) -> dict[str, Any]:
    cases = [_simulate_case(case) for case in baseline["cases"]]
    before_ranks = [
        concept["original_rank"]
        for case in cases
        for concept in case["expected_concepts"]
        if concept["original_rank"] is not None
    ]
    after_ranks = [
        concept["simulated_rank"]
        for case in cases
        for concept in case["expected_concepts"]
        if concept["simulated_rank"] is not None
    ]
    moved_into_top10 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["original_rank"], BASELINE_LIMIT)
        and _inside(concept["simulated_rank"], BASELINE_LIMIT)
    )
    moved_into_top20 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["original_rank"], BASELINE_LIMIT)
        and _inside(concept["simulated_rank"], TOP20_LIMIT)
    )
    original_outside_top10 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["original_rank"], BASELINE_LIMIT)
    )
    simulated_outside_top10 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["simulated_rank"], BASELINE_LIMIT)
    )
    original_outside_top20 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["original_rank"], TOP20_LIMIT)
    )
    simulated_outside_top20 = sum(
        1
        for case in cases
        for concept in case["expected_concepts"]
        if not _inside(concept["simulated_rank"], TOP20_LIMIT)
    )
    original_noise_counts = [
        concept["original_noise_above_count"]
        for case in cases
        for concept in case["expected_concepts"]
    ]
    simulated_noise_counts = [
        concept["simulated_noise_above_count"]
        for case in cases
        for concept in case["expected_concepts"]
    ]
    worsened_top10 = [
        {
            "case": case["case"],
            "concept_id": concept["concept_id"],
            "original_rank": concept["original_rank"],
            "simulated_rank": concept["simulated_rank"],
        }
        for case in cases
        for concept in case["expected_concepts"]
        if _inside(concept["original_rank"], BASELINE_LIMIT)
        and not _inside(concept["simulated_rank"], BASELINE_LIMIT)
    ]
    recurring_noise_before = Counter()
    recurring_noise_after = Counter()
    for case in cases:
        recurring_noise_before.update(case["noise_above_expected_before"])
        recurring_noise_after.update(case["noise_above_expected_after"])
    acceptance = {
        "four_of_eight_outside_top10_move_into_top10_or_top20": moved_into_top20 >= 4,
        "generic_attractor_dominance_decreases": sum(recurring_noise_after.values()) < sum(recurring_noise_before.values()),
        "no_sparse_case_becomes_grounded_false_positive": all(case["sparse_behavior_ok"] for case in cases if case["sparse_expected"]),
        "expected_outside_top10_decreases": simulated_outside_top10 < original_outside_top10,
        "expected_outside_top20_decreases": simulated_outside_top20 < original_outside_top20,
        "mean_expected_rank_decreases": _mean(after_ranks) < _mean(before_ranks),
        "mean_noise_above_expected_decreases": _mean(simulated_noise_counts) < _mean(original_noise_counts),
    }
    rejection = {
        "gains_limited_to_one_case": len([case for case in cases if case["expected_rank_improvements"]]) <= 1,
        "expected_top10_concepts_pushed_out": bool(worsened_top10),
        "sparse_questions_more_likely_to_activate": any(
            case["simulated_sparse_top_score"] > case["original_sparse_top_score"]
            for case in cases
            if case["sparse_expected"]
        ),
        "uses_expected_labels_for_scoring": False,
    }
    final = _final_decision(acceptance, rejection)
    return {
        "source": "reports/runtime_v12_activation_ranking_diagnostic.json",
        "simulation_only": True,
        "live_runtime_changed": False,
        "formula": {
            "simulated_score": (
                "original_score - generic_penalty - no_specific_overlap_penalty "
                "+ specificity_bonus + rare_term_bonus + concept_definition_bonus"
            ),
            "generic_tokens": sorted(GENERIC_TOKENS),
            "stopwords_ignored_for_specificity": sorted(STOPWORDS),
            "abstention_score_threshold": ABSTENTION_SCORE,
        },
        "aggregate": {
            "original_mean_expected_rank": round(_mean(before_ranks), 4),
            "simulated_mean_expected_rank": round(_mean(after_ranks), 4),
            "original_median_expected_rank": round(_median(before_ranks), 4),
            "simulated_median_expected_rank": round(_median(after_ranks), 4),
            "original_expected_outside_top10": original_outside_top10,
            "simulated_expected_outside_top10": simulated_outside_top10,
            "original_expected_outside_top20": original_outside_top20,
            "simulated_expected_outside_top20": simulated_outside_top20,
            "moved_into_top10_from_outside_top10": moved_into_top10,
            "moved_into_top20_from_outside_top10": moved_into_top20,
            "original_mean_noise_above_expected": round(_mean(original_noise_counts), 4),
            "simulated_mean_noise_above_expected": round(_mean(simulated_noise_counts), 4),
            "recurring_noise_before": recurring_noise_before.most_common(10),
            "recurring_noise_after": recurring_noise_after.most_common(10),
            "expected_concepts_worsened_out_of_top10": worsened_top10,
        },
        "acceptance_criteria": acceptance,
        "rejection_criteria": rejection,
        "final_decision": final,
        "cases": cases,
    }


def _simulate_case(case: dict[str, Any]) -> dict[str, Any]:
    original_items = [
        {**item, "original_rank": index + 1}
        for index, item in enumerate(case["top_50"])
    ]
    scored = []
    query_term_counts = Counter(
        term
        for item in original_items
        for term in _specific_terms(item)
    )
    for item in original_items:
        components = _simulation_components(item, query_term_counts)
        simulated_score = max(0.0, round(item["activation_score"] + components["delta"], 4))
        scored.append(
            {
                **item,
                "generic_penalty": components["generic_penalty"],
                "specificity_bonus": components["specificity_bonus"],
                "rare_term_bonus": components["rare_term_bonus"],
                "concept_definition_bonus": components["concept_definition_bonus"],
                "no_specific_overlap_penalty": components["no_specific_overlap_penalty"],
                "simulated_score": simulated_score,
            }
        )
    scored.sort(key=lambda item: (item["simulated_score"], item["activation_score"], item["concept_id"]), reverse=True)
    for index, item in enumerate(scored):
        item["simulated_rank"] = index + 1

    original_rank = {item["concept_id"]: item["original_rank"] for item in original_items}
    simulated_rank = {item["concept_id"]: item["simulated_rank"] for item in scored}
    expected_ids = [item["concept_id"] for item in case["expected_concepts"]]
    expected = []
    for concept_id in expected_ids:
        original_item = next((item for item in original_items if item["concept_id"] == concept_id), None)
        simulated_item = next((item for item in scored if item["concept_id"] == concept_id), None)
        original_noise = _noise_above(original_items, concept_id, expected_ids, rank_key="original_rank")
        simulated_noise = _noise_above(scored, concept_id, expected_ids, rank_key="simulated_rank")
        expected.append(
            {
                "concept_id": concept_id,
                "original_rank": original_rank.get(concept_id),
                "simulated_rank": simulated_rank.get(concept_id),
                "original_score": original_item["activation_score"] if original_item else None,
                "simulated_score": simulated_item["simulated_score"] if simulated_item else None,
                "original_noise_above_count": len(original_noise),
                "simulated_noise_above_count": len(simulated_noise),
                "rank_delta": _rank_delta(original_rank.get(concept_id), simulated_rank.get(concept_id)),
                "moved_into_top10": (
                    not _inside(original_rank.get(concept_id), BASELINE_LIMIT)
                    and _inside(simulated_rank.get(concept_id), BASELINE_LIMIT)
                ),
                "moved_into_top20": (
                    not _inside(original_rank.get(concept_id), BASELINE_LIMIT)
                    and _inside(simulated_rank.get(concept_id), TOP20_LIMIT)
                ),
            }
        )
    original_top = case["top_50"][0]["activation_score"] if case["top_50"] else 0.0
    simulated_top = scored[0]["simulated_score"] if scored else 0.0
    sparse_behavior_ok = True
    if case["sparse_expected"]:
        sparse_behavior_ok = simulated_top <= original_top and simulated_top < ABSTENTION_SCORE
    return {
        "case": case["case"],
        "category": case["category"],
        "diagnosis": case["diagnosis"],
        "sparse_expected": case["sparse_expected"],
        "original_sparse_top_score": original_top if case["sparse_expected"] else None,
        "simulated_sparse_top_score": simulated_top if case["sparse_expected"] else None,
        "sparse_behavior_ok": sparse_behavior_ok,
        "expected_concepts": expected,
        "expected_rank_improvements": [
            item for item in expected if item["rank_delta"] is not None and item["rank_delta"] > 0
        ],
        "expected_rank_worsening": [
            item for item in expected if item["rank_delta"] is not None and item["rank_delta"] < 0
        ],
        "top_10_before": [
            {"concept_id": item["concept_id"], "role": item["role"], "score": item["activation_score"]}
            for item in original_items[:10]
        ],
        "top_10_after": [
            {"concept_id": item["concept_id"], "role": item["role"], "score": item["simulated_score"]}
            for item in scored[:10]
        ],
        "noise_above_expected_before": Counter(
            noise["concept_id"]
            for concept_id in expected_ids
            for noise in _noise_above(original_items, concept_id, expected_ids, rank_key="original_rank")
        ),
        "noise_above_expected_after": Counter(
            noise["concept_id"]
            for concept_id in expected_ids
            for noise in _noise_above(scored, concept_id, expected_ids, rank_key="simulated_rank")
        ),
    }


def _simulation_components(item: dict[str, Any], query_term_counts: Counter[str]) -> dict[str, float]:
    generic = set(item.get("generic_query_terms_matched", []))
    specific = _specific_terms(item)
    combined_overlap = [
        term.lower()
        for term in item.get("query_combined_overlap", [])
        if len(str(term)) >= 3
    ]
    meaningful_overlap = [term for term in combined_overlap if term not in STOPWORDS]
    generic_ratio = len(generic) / max(1, len(meaningful_overlap))
    concept_specific = set(_normalize(item.get("query_concept_overlap", []))) & specific
    definition_specific = set(_normalize(item.get("query_definition_overlap", []))) & specific
    both = concept_specific & definition_specific
    rare = {term for term in specific if query_term_counts.get(term, 0) <= 2}

    generic_penalty = 0.0
    if generic and len(specific) == 0:
        generic_penalty = 0.08 + (0.02 * len(generic))
    elif generic_ratio >= 0.65:
        generic_penalty = 0.025 * len(generic)
    else:
        generic_penalty = 0.01 * len(generic)

    no_specific_overlap_penalty = 0.18 if not specific else 0.0
    specificity_bonus = min(0.11, 0.026 * len(specific))
    rare_term_bonus = min(0.08, 0.025 * len(rare))
    concept_definition_bonus = min(0.06, 0.02 * len(both))
    delta = specificity_bonus + rare_term_bonus + concept_definition_bonus - generic_penalty - no_specific_overlap_penalty
    return {
        "generic_penalty": round(generic_penalty, 4),
        "specificity_bonus": round(specificity_bonus, 4),
        "rare_term_bonus": round(rare_term_bonus, 4),
        "concept_definition_bonus": round(concept_definition_bonus, 4),
        "no_specific_overlap_penalty": round(no_specific_overlap_penalty, 4),
        "delta": round(delta, 4),
    }


def _specific_terms(item: dict[str, Any]) -> set[str]:
    return {
        term
        for term in _normalize(item.get("query_combined_overlap", []))
        if term not in GENERIC_TOKENS and term not in STOPWORDS
    }


def _normalize(terms: list[str]) -> list[str]:
    return [str(term).lower() for term in terms if len(str(term)) >= 3]


def _noise_above(items: list[dict[str, Any]], concept_id: str, expected_ids: list[str], *, rank_key: str) -> list[dict[str, Any]]:
    target = next((item for item in items if item["concept_id"] == concept_id), None)
    if not target:
        return []
    target_rank = target[rank_key]
    return [
        item
        for item in items
        if item[rank_key] < target_rank
        and item["concept_id"] not in expected_ids
        and item["role"] not in {"expected", "useful_neighbor"}
    ]


def _rank_delta(original: int | None, simulated: int | None) -> int | None:
    if original is None or simulated is None:
        return None
    return original - simulated


def _inside(rank: int | None, limit: int) -> bool:
    return rank is not None and rank <= limit


def _mean(values: list[int | float]) -> float:
    return statistics.mean(values) if values else 0.0


def _median(values: list[int | float]) -> float:
    return statistics.median(values) if values else 0.0


def _final_decision(acceptance: dict[str, bool], rejection: dict[str, bool]) -> str:
    if any(rejection.values()):
        return "REVISE_SIMULATION_FORMULA"
    if all(acceptance.values()):
        return "PROCEED_TO_LIVE_RUNTIME_PROTOTYPE"
    return "REVISE_SIMULATION_FORMULA"


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.3 Scoring Simulation",
        "",
        "This is a simulation-only report. It does not modify Runtime V1.2 activation, attention, learning, or stores.",
        "",
        f"Final decision: `{payload['final_decision']}`",
        "",
        "## Baseline Summary",
        "",
        "| Metric | Before | After |",
        "| --- | ---: | ---: |",
    ]
    aggregate = payload["aggregate"]
    lines.extend(
        [
            f"| mean expected rank | `{aggregate['original_mean_expected_rank']}` | `{aggregate['simulated_mean_expected_rank']}` |",
            f"| median expected rank | `{aggregate['original_median_expected_rank']}` | `{aggregate['simulated_median_expected_rank']}` |",
            f"| expected outside top 10 | `{aggregate['original_expected_outside_top10']}` | `{aggregate['simulated_expected_outside_top10']}` |",
            f"| expected outside top 20 | `{aggregate['original_expected_outside_top20']}` | `{aggregate['simulated_expected_outside_top20']}` |",
            f"| mean noise above expected | `{aggregate['original_mean_noise_above_expected']}` | `{aggregate['simulated_mean_noise_above_expected']}` |",
        ]
    )
    lines.extend(
        [
            "",
            "## Simulation Formula",
            "",
            payload["formula"]["simulated_score"],
            "",
            "Generic tokens dampened:",
            ", ".join(payload["formula"]["generic_tokens"]),
            "",
            "Stopwords ignored for specificity:",
            ", ".join(payload["formula"]["stopwords_ignored_for_specificity"]),
            "",
            "## Aggregate Rank Movement",
            "",
            f"- expected concepts moved into top 10 from outside top 10: `{aggregate['moved_into_top10_from_outside_top10']}`",
            f"- expected concepts moved into top 20 from outside top 10: `{aggregate['moved_into_top20_from_outside_top10']}`",
            "",
            "## Case-Level Rank Movement",
            "",
            "| Case | Expected Improved | Expected Worsened | Sparse Top Before | Sparse Top After |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for case in payload["cases"]:
        lines.append(
            f"| {case['case']} | `{len(case['expected_rank_improvements'])}` | `{len(case['expected_rank_worsening'])}` | "
            f"`{case['original_sparse_top_score']}` | `{case['simulated_sparse_top_score']}` |"
        )
    lines.extend(["", "## Expected Concepts Improved", ""])
    improved = [
        (case["case"], item)
        for case in payload["cases"]
        for item in case["expected_rank_improvements"]
    ]
    if not improved:
        lines.append("- none")
    for case_name, item in improved:
        lines.append(
            f"- `{case_name}` `{item['concept_id']}` rank `{item['original_rank']}` -> `{item['simulated_rank']}`"
        )
    lines.extend(["", "## Expected Concepts Worsened", ""])
    worsened = [
        (case["case"], item)
        for case in payload["cases"]
        for item in case["expected_rank_worsening"]
    ]
    if not worsened:
        lines.append("- none")
    for case_name, item in worsened:
        lines.append(
            f"- `{case_name}` `{item['concept_id']}` rank `{item['original_rank']}` -> `{item['simulated_rank']}`"
        )
    lines.extend(
        [
            "",
            "## Noisy Concepts Suppressed",
            "",
            "| Concept ID | Before Count | After Count |",
            "| --- | ---: | ---: |",
        ]
    )
    before = dict(aggregate["recurring_noise_before"])
    after = dict(aggregate["recurring_noise_after"])
    for concept_id in sorted(set(before) | set(after)):
        lines.append(f"| `{concept_id}` | `{before.get(concept_id, 0)}` | `{after.get(concept_id, 0)}` |")
    lines.extend(["", "## Sparse/Unsupported Behavior Check", ""])
    for case in payload["cases"]:
        if case["sparse_expected"]:
            lines.append(
                f"- `{case['case']}` top score `{case['original_sparse_top_score']}` -> "
                f"`{case['simulated_sparse_top_score']}`, ok=`{case['sparse_behavior_ok']}`"
            )
    lines.extend(["", "## Acceptance Criteria Result", ""])
    for key, value in payload["acceptance_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Rejection Criteria Result", ""])
    for key, value in payload["rejection_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Recommendation For Or Against Live Runtime V1.3 Implementation", ""])
    if payload["final_decision"] == "PROCEED_TO_LIVE_RUNTIME_PROTOTYPE":
        lines.append("Proceed to a live runtime prototype only behind a reversible patch and rerun the preserved V1.2 benchmark commands.")
    elif payload["final_decision"] == "REVISE_SIMULATION_FORMULA":
        lines.append("Do not implement live runtime changes yet. Revise or compare simulation formulas because acceptance criteria were not fully satisfied or rejection criteria fired.")
    else:
        lines.append("Reject this intervention path for now and inspect another V1.3 intervention candidate.")
    lines.append("")
    lines.append(f"`{payload['final_decision']}`")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input diagnostic: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

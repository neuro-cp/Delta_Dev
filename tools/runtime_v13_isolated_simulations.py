from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


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

GENERIC_DOMAIN_TERMS = {
    "capacity",
    "change",
    "emergency",
    "evidence",
    "failure",
    "plan",
    "planning",
    "prediction",
    "resource",
    "response",
    "risk",
    "uncertainty",
}

BASELINE_LIMIT = 10
TOP20_LIMIT = 20
SPARSE_THRESHOLD = 0.20


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Runtime V1.3 read-only simulations.")
    parser.add_argument(
        "--ranking",
        type=Path,
        default=Path("reports/runtime_v12_activation_ranking_diagnostic.json"),
    )
    parser.add_argument(
        "--failure-analysis",
        type=Path,
        default=Path("reports/runtime_v13_simulation_failure_analysis.json"),
    )
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    ranking = _load_json(args.ranking)
    failure = _load_json(args.failure_analysis)
    payload = _run_simulations(ranking=ranking, failure=failure)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "runtime_v13_isolated_simulations.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "runtime_v13_isolated_simulations.md").write_text(
        _markdown(payload),
        encoding="utf-8",
    )
    return 0


def _run_simulations(*, ranking: dict[str, Any], failure: dict[str, Any]) -> dict[str, Any]:
    recurring = _recurring_noise_prior(failure)
    recurring_sim = _simulate_recurring_noise_suppression(ranking, recurring)
    sparse_sim = _simulate_sparse_abstention(ranking)
    attention_sim = _simulate_attention_rescue(ranking, recurring)
    decision = _final_recommendation(recurring_sim, sparse_sim, attention_sim)
    return {
        "source_reports": {
            "ranking": "reports/runtime_v12_activation_ranking_diagnostic.json",
            "failure_analysis": "reports/runtime_v13_simulation_failure_analysis.json",
        },
        "simulation_only": True,
        "live_runtime_changed": False,
        "recurring_noise_prior": recurring,
        "recurring_noise_suppression": recurring_sim,
        "sparse_abstention_gate": sparse_sim,
        "attention_rescue": attention_sim,
        "final_recommendation": decision,
    }


def _recurring_noise_prior(failure: dict[str, Any]) -> dict[str, dict[str, Any]]:
    prior: dict[str, dict[str, Any]] = {}
    for item in failure.get("recurring_noise_analysis", []):
        before = int(item.get("before_count", 0))
        after = int(item.get("after_count", 0))
        if before <= 0 and after <= 0:
            continue
        recurrence = max(before, after)
        prior[item["concept_id"]] = {
            "before_count": before,
            "after_count": after,
            "recurrence": recurrence,
            "penalty": round(min(0.14, 0.018 * recurrence), 4),
            "reason": item.get("likely_reason_it_survived_or_gained", ""),
        }
    return prior


def _simulate_recurring_noise_suppression(
    ranking: dict[str, Any],
    recurring: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cases = []
    before_ranks: list[int] = []
    after_ranks: list[int] = []
    before_noise_counts: list[int] = []
    after_noise_counts: list[int] = []
    pushed_out: list[dict[str, Any]] = []
    suppressed_counter: Counter[str] = Counter()
    for case in ranking["cases"]:
        original_items = [
            {**item, "original_rank": index + 1, "simulated_score": item["activation_score"]}
            for index, item in enumerate(case["top_50"])
        ]
        simulated_items = []
        for item in original_items:
            prior = recurring.get(item["concept_id"], {})
            penalty = float(prior.get("penalty", 0.0))
            simulated = {
                **item,
                "recurring_noise_penalty": penalty,
                "simulated_score": round(max(0.0, item["activation_score"] - penalty), 4),
            }
            simulated_items.append(simulated)
            if penalty > 0:
                suppressed_counter[item["concept_id"]] += 1
        simulated_items.sort(key=lambda item: (item["simulated_score"], item["activation_score"], item["concept_id"]), reverse=True)
        for index, item in enumerate(simulated_items):
            item["simulated_rank"] = index + 1
        original_by_id = {item["concept_id"]: item for item in original_items}
        simulated_by_id = {item["concept_id"]: item for item in simulated_items}
        expected_ids = [item["concept_id"] for item in case["expected_concepts"]]
        expected_results = []
        for concept_id in expected_ids:
            original = original_by_id.get(concept_id)
            simulated = simulated_by_id.get(concept_id)
            if not original or not simulated:
                continue
            before_noise = _noise_above(original_items, concept_id, expected_ids, "original_rank")
            after_noise = _noise_above(simulated_items, concept_id, expected_ids, "simulated_rank")
            before_ranks.append(original["original_rank"])
            after_ranks.append(simulated["simulated_rank"])
            before_noise_counts.append(len(before_noise))
            after_noise_counts.append(len(after_noise))
            if _inside(original["original_rank"], BASELINE_LIMIT) and not _inside(simulated["simulated_rank"], BASELINE_LIMIT):
                pushed_out.append(
                    {
                        "case": case["case"],
                        "concept_id": concept_id,
                        "original_rank": original["original_rank"],
                        "simulated_rank": simulated["simulated_rank"],
                    }
                )
            expected_results.append(
                {
                    "concept_id": concept_id,
                    "original_rank": original["original_rank"],
                    "simulated_rank": simulated["simulated_rank"],
                    "rank_delta": original["original_rank"] - simulated["simulated_rank"],
                    "before_noise_above": len(before_noise),
                    "after_noise_above": len(after_noise),
                }
            )
        cases.append(
            {
                "case": case["case"],
                "expected_results": expected_results,
                "expected_improved": sum(1 for item in expected_results if item["rank_delta"] > 0),
                "expected_worsened": sum(1 for item in expected_results if item["rank_delta"] < 0),
                "top10_before": [
                    {"concept_id": item["concept_id"], "role": item["role"], "score": item["activation_score"]}
                    for item in original_items[:10]
                ],
                "top10_after": [
                    {"concept_id": item["concept_id"], "role": item["role"], "score": item["simulated_score"]}
                    for item in simulated_items[:10]
                ],
            }
        )
    aggregate = {
        "expected_outside_top10_before": sum(1 for rank in before_ranks if not _inside(rank, BASELINE_LIMIT)),
        "expected_outside_top10_after": sum(1 for rank in after_ranks if not _inside(rank, BASELINE_LIMIT)),
        "expected_outside_top20_before": sum(1 for rank in before_ranks if not _inside(rank, TOP20_LIMIT)),
        "expected_outside_top20_after": sum(1 for rank in after_ranks if not _inside(rank, TOP20_LIMIT)),
        "mean_expected_rank_before": round(_mean(before_ranks), 4),
        "mean_expected_rank_after": round(_mean(after_ranks), 4),
        "mean_noise_above_expected_before": round(_mean(before_noise_counts), 4),
        "mean_noise_above_expected_after": round(_mean(after_noise_counts), 4),
        "expected_top10_pushed_out": pushed_out,
        "recurring_noisy_concepts_suppressed": suppressed_counter.most_common(12),
    }
    accepted = (
        (
            aggregate["expected_outside_top10_after"] < aggregate["expected_outside_top10_before"]
            or aggregate["mean_expected_rank_after"] < aggregate["mean_expected_rank_before"]
        )
        and not pushed_out
        and sum(count for _, count in aggregate["recurring_noisy_concepts_suppressed"]) > 0
    )
    return {
        "description": "Demote repeat-offender noisy concept IDs from prior aggregate diagnostics.",
        "aggregate": aggregate,
        "cases": cases,
        "accepted": accepted,
    }


def _simulate_sparse_abstention(ranking: dict[str, Any]) -> dict[str, Any]:
    cases = []
    false_abstentions = []
    sparse_accepts = []
    for case in ranking["cases"]:
        top_score = case["top_50"][0]["activation_score"] if case["top_50"] else 0.0
        strongest = max((_specific_strength(item) for item in case["top_50"][:10]), default=0)
        best_overlap = max((len(_meaningful_terms(item)) for item in case["top_50"][:10]), default=0)
        stopword_only_top = all(
            len(_meaningful_terms(item)) == 0
            for item in case["top_50"][:5]
        )
        should_abstain = (
            strongest == 0
            and best_overlap <= 1
            and (stopword_only_top or top_score < 0.40)
        )
        row = {
            "case": case["case"],
            "sparse_expected": case["sparse_expected"],
            "top_score_before": top_score,
            "strongest_specific_signal": strongest,
            "best_meaningful_overlap": best_overlap,
            "stopword_only_top5": stopword_only_top,
            "simulated_decision": "ABSTAIN" if should_abstain else "PASS",
        }
        cases.append(row)
        if case["sparse_expected"] and should_abstain:
            sparse_accepts.append(case["case"])
        if not case["sparse_expected"] and should_abstain:
            false_abstentions.append(case["case"])
    accepted = len(sparse_accepts) == 2 and not false_abstentions
    return {
        "description": "Separate sparse-query gate using meaningful overlap and specific signal strength.",
        "thresholds": {
            "top_score_soft_ceiling": 0.40,
            "required_strongest_specific_signal": "> 0",
            "required_best_meaningful_overlap": "> 1",
        },
        "cases": cases,
        "sparse_cases_abstained": sparse_accepts,
        "false_non_sparse_abstentions": false_abstentions,
        "accepted": accepted,
    }


def _simulate_attention_rescue(
    ranking: dict[str, Any],
    recurring: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cases = []
    total_expected_pruned = 0
    total_expected_rescued = 0
    total_noise_rescued = 0
    for case in ranking["cases"]:
        expected_ids = {item["concept_id"] for item in case["expected_concepts"]}
        pruned_expected = [
            item
            for item in case["expected_concepts"]
            if item.get("pruned_by_attention")
        ]
        expected_rescued = []
        noise_rescued = []
        for expected in pruned_expected:
            candidate = next((item for item in case["top_50"][:10] if item["concept_id"] == expected["concept_id"]), None)
            if candidate and _rescue_eligible(candidate, recurring):
                expected_rescued.append(expected["concept_id"])
        for candidate in case["top_50"][:10]:
            if candidate["concept_id"] in expected_ids:
                continue
            if _rescue_eligible(candidate, recurring):
                noise_rescued.append(candidate["concept_id"])
        total_expected_pruned += len(pruned_expected)
        total_expected_rescued += len(expected_rescued)
        total_noise_rescued += len(noise_rescued)
        cases.append(
            {
                "case": case["case"],
                "diagnosis": case["diagnosis"],
                "pruned_expected_count": len(pruned_expected),
                "expected_rescued": expected_rescued,
                "noise_that_would_also_be_rescued": noise_rescued,
                "attention_primary": case["diagnosis"] in {"attention_primary", "mixed_activation_attention"},
            }
        )
    accepted = total_expected_rescued > 0 and total_noise_rescued == 0
    hypothetical_recall = round(total_expected_rescued / max(1, total_expected_pruned), 4)
    return {
        "description": "Bounded rescue for top-10 pruned candidates with strong non-recurring evidence signals.",
        "cases": cases,
        "expected_pruned": total_expected_pruned,
        "expected_rescued": total_expected_rescued,
        "noise_that_would_also_be_rescued": total_noise_rescued,
        "hypothetical_attention_recall_gain_on_pruned_expected": hypothetical_recall,
        "projected_noise_used_in_reasoning_increase": total_noise_rescued,
        "accepted": accepted,
    }


def _rescue_eligible(item: dict[str, Any], recurring: dict[str, dict[str, Any]]) -> bool:
    if item["concept_id"] in recurring:
        return False
    return (
        _specific_strength(item) >= 2
        or (
            len(_meaningful_terms(item)) >= 3
            and float(item.get("evidence_support", 0.0)) >= 0.8
            and float(item.get("promotion_score", 0.0)) >= 0.5
        )
    )


def _final_recommendation(recurring: dict[str, Any], sparse: dict[str, Any], attention: dict[str, Any]) -> str:
    if sparse["accepted"]:
        return "PROCEED_SPARSE_ABSTENTION_GATE_PROTOTYPE"
    if recurring["accepted"]:
        return "PROCEED_RECURRING_NOISE_SUPPRESSION_PROTOTYPE"
    if attention["accepted"]:
        return "PROCEED_ATTENTION_RESCUE_PROTOTYPE"
    if not recurring["accepted"] and not sparse["accepted"] and not attention["accepted"]:
        return "RUN_MORE_DIAGNOSTICS"
    return "REJECT_ALL_CURRENT_DIRECTIONS"


def _specific_strength(item: dict[str, Any]) -> int:
    concept = set(_normalize(item.get("query_concept_overlap", [])))
    definition = set(_normalize(item.get("query_definition_overlap", [])))
    specific = _meaningful_terms(item) - GENERIC_DOMAIN_TERMS
    return len(specific) + len((concept & definition) - GENERIC_DOMAIN_TERMS)


def _meaningful_terms(item: dict[str, Any]) -> set[str]:
    return {
        term
        for term in _normalize(item.get("query_combined_overlap", []))
        if term not in STOPWORDS
    }


def _normalize(terms: list[str]) -> list[str]:
    return [str(term).lower() for term in terms if len(str(term)) >= 3]


def _noise_above(items: list[dict[str, Any]], concept_id: str, expected_ids: list[str], rank_key: str) -> list[dict[str, Any]]:
    target = next((item for item in items if item["concept_id"] == concept_id), None)
    if not target:
        return []
    return [
        item
        for item in items
        if item[rank_key] < target[rank_key]
        and item["concept_id"] not in expected_ids
        and item.get("role") not in {"expected", "useful_neighbor"}
    ]


def _inside(rank: int | None, limit: int) -> bool:
    return rank is not None and rank <= limit


def _mean(values: list[int | float]) -> float:
    return statistics.mean(values) if values else 0.0


def _markdown(payload: dict[str, Any]) -> str:
    rec = payload["recurring_noise_suppression"]
    sparse = payload["sparse_abstention_gate"]
    attention = payload["attention_rescue"]
    lines = [
        "# Runtime V1.3 Isolated Simulations",
        "",
        "These simulations are read-only and do not modify Runtime V1.2 activation, attention, learning, or stores.",
        "",
        f"Final recommendation: `{payload['final_recommendation']}`",
        "",
        "## Recurring-Noise Suppression Simulation",
        "",
        "| Metric | Before | After |",
        "| --- | ---: | ---: |",
    ]
    for before_key, after_key, label in [
        ("expected_outside_top10_before", "expected_outside_top10_after", "expected outside top 10"),
        ("expected_outside_top20_before", "expected_outside_top20_after", "expected outside top 20"),
        ("mean_expected_rank_before", "mean_expected_rank_after", "mean expected rank"),
        ("mean_noise_above_expected_before", "mean_noise_above_expected_after", "mean noise above expected"),
    ]:
        lines.append(f"| {label} | `{rec['aggregate'][before_key]}` | `{rec['aggregate'][after_key]}` |")
    lines.extend(
        [
            "",
            f"- expected top-10 concepts pushed out: `{len(rec['aggregate']['expected_top10_pushed_out'])}`",
            f"- accepted: `{rec['accepted']}`",
            "",
            "### Recurring Noisy Concepts Suppressed",
            "",
        ]
    )
    for concept_id, count in rec["aggregate"]["recurring_noisy_concepts_suppressed"][:10]:
        lines.append(f"- `{concept_id}` in `{count}` case top-50 lists")
    lines.extend(
        [
            "",
            "## Sparse Abstention Gate Simulation",
            "",
            f"- sparse cases abstained: `{', '.join(sparse['sparse_cases_abstained']) or 'none'}`",
            f"- false non-sparse abstentions: `{', '.join(sparse['false_non_sparse_abstentions']) or 'none'}`",
            f"- accepted: `{sparse['accepted']}`",
            "",
            "| Case | Sparse Expected | Decision | Strongest Specific Signal | Best Meaningful Overlap |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for case in sparse["cases"]:
        lines.append(
            f"| {case['case']} | `{case['sparse_expected']}` | `{case['simulated_decision']}` | "
            f"`{case['strongest_specific_signal']}` | `{case['best_meaningful_overlap']}` |"
        )
    lines.extend(
        [
            "",
            "## Attention Rescue Simulation",
            "",
            f"- expected pruned: `{attention['expected_pruned']}`",
            f"- expected rescued: `{attention['expected_rescued']}`",
            f"- noise that would also be rescued: `{attention['noise_that_would_also_be_rescued']}`",
            f"- projected noise_used_in_reasoning increase: `{attention['projected_noise_used_in_reasoning_increase']}`",
            f"- accepted: `{attention['accepted']}`",
            "",
            "| Case | Pruned Expected | Expected Rescued | Noise Also Rescued |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for case in attention["cases"]:
        lines.append(
            f"| {case['case']} | `{case['pruned_expected_count']}` | `{len(case['expected_rescued'])}` | "
            f"`{len(case['noise_that_would_also_be_rescued'])}` |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            _recommendation_text(payload),
            "",
            f"`{payload['final_recommendation']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _recommendation_text(payload: dict[str, Any]) -> str:
    decision = payload["final_recommendation"]
    if decision == "PROCEED_SPARSE_ABSTENTION_GATE_PROTOTYPE":
        return (
            "Proceed first with a live sparse-abstention prototype because it cleanly separates unsupported-query behavior "
            "from normal activation and passes the isolated acceptance rule."
        )
    if decision == "PROCEED_RECURRING_NOISE_SUPPRESSION_PROTOTYPE":
        return "Proceed with recurring-noise suppression as the next live prototype, guarded by the preserved V1.2 benchmark."
    if decision == "PROCEED_ATTENTION_RESCUE_PROTOTYPE":
        return "Proceed with a bounded attention-rescue prototype; activation changes are not yet justified."
    if decision == "RUN_MORE_DIAGNOSTICS":
        return "Do not implement a live prototype yet. None of the isolated simulations passed cleanly enough."
    return "Reject the current intervention directions."


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

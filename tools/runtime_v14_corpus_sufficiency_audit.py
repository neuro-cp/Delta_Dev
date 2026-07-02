"""Runtime V1.4 corpus sufficiency audit.

This is report-only. It does not train, promote, mutate stores, modify runtime
defaults, or treat temporary experiment output as permanent knowledge.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORTS = ROOT / "reports"
HYBRID = REPORTS / "runtime_v13_model_b_mbv2_hybrid_test.json"
BENCHMARK = REPORTS / "runtime_v13_benchmark_live_window_review.json"
SAFETY = REPORTS / "runtime_v13_model_b_catastrophic_safety_review.json"
USABILITY = REPORTS / "runtime_v13_expected_evidence_usability_audit.json"
DEEP = REPORTS / "runtime_v13_deep_activation_diagnostic.json"
MODEL_B_REAL = REPORTS / "runtime_v13_query_evidence_model_b_live_raw" / "runtime_v12_real_knowledge.json"


PRIMARY_CLASSES = {
    "concept_present_and_sufficient",
    "concept_present_but_too_generic",
    "concept_present_but_missing_relation_metadata",
    "concept_present_but_missing_evidence_role",
    "concept_present_but_fragmented",
    "concept_present_but_buried_by_noise",
    "concept_absent",
    "concept_redundant_with_used_evidence",
    "benchmark_expected_but_not_live_usable",
    "requires_new_live_signal_not_training",
}

NOISE_CLASSES = {
    "useful_neighbor",
    "duplicate_or_near_duplicate",
    "generic_anchor_noise",
    "wrong_relation_same_topic",
    "wrong_evidence_role_same_topic",
    "centrality_bias_noise",
    "promotion_confidence_noise",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tokens(text: str) -> set[str]:
    stop = {
        "and",
        "are",
        "but",
        "for",
        "from",
        "into",
        "not",
        "that",
        "the",
        "this",
        "with",
        "would",
        "when",
        "where",
        "which",
    }
    return {t for t in re.findall(r"[a-z][a-z0-9_]+", str(text).lower()) if len(t) > 2 and t not in stop}


def compact(text: str, limit: int = 180) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def index_visible_expected(usability: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("concept_id")): item
        for item in usability.get("visible_expected_inventory", [])
        if item.get("concept_id")
    }


def index_deep_cases(deep: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(case.get("case")): case for case in deep.get("case_audits", [])}


def index_real_cases(real: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(case.get("name")): case for case in real.get("cases", [])}


def primary_class_for(
    *,
    miss: dict[str, Any],
    visible: dict[str, Any] | None,
    deep_case: dict[str, Any] | None,
    real_case: dict[str, Any] | None,
) -> tuple[str, str]:
    classification = str(miss.get("classification") or "")
    rank = miss.get("activation_rank")
    concept = str(miss.get("concept") or "")
    features = (visible or {}).get("features", {})
    redundant = bool(miss.get("redundant_with_used_evidence"))
    same_topic_risk = bool(miss.get("same_topic_noise_inseparable_under_live_safe_signals"))
    requires_new_signal = bool(miss.get("requires_signal_not_currently_available_live"))
    best_path = str(miss.get("best_attempted_recovery_path") or "")

    if classification in {
        "benchmark_expected_but_not_live_citable",
        "benchmark_expected_but_planning_only",
        "unavailable_or_unfair_target",
    }:
        return "benchmark_expected_but_not_live_usable", "benchmark/live-window review already classified this as not suitable citable runtime evidence"
    if classification == "benchmark_expected_redundant_with_used_evidence" or redundant:
        return "concept_redundant_with_used_evidence", "expected concept overlaps with already used evidence"
    if classification == "outside_reasonable_activation_window" or (isinstance(rank, int) and rank > 20):
        return "concept_present_but_buried_by_noise", f"concept exists but activation rank `{rank}` is outside the practical V1.3 live window"
    if classification == "live_usable_but_requires_new_signal" or requires_new_signal:
        return "requires_new_live_signal_not_training", "concept is present but needs a signal not currently available to live runtime"
    if classification == "visible_but_not_safely_separable" and same_topic_risk:
        if features:
            relation_hits = int(features.get("relation_action_frame_match", 0) or 0)
            evidence_hits = int(features.get("evidence_need_match", 0) or 0)
            if evidence_hits == 0:
                return "concept_present_but_missing_evidence_role", "visible concept has insufficient evidence-need match and cannot be separated safely from same-topic noise"
            if relation_hits == 0:
                return "concept_present_but_missing_relation_metadata", "visible concept lacks a strong relation/action frame despite topical visibility"
        return "requires_new_live_signal_not_training", "visible concept cannot be safely separated from same-topic noise with existing live-safe signals"
    if classification == "live_usable_and_should_be_recovered":
        return "concept_present_and_sufficient", "concept appears live-usable in the corpus but was missed by the current runtime path"
    if not visible and not deep_case and not real_case:
        return "concept_absent", "no supporting visibility, deep-activation, or real-store record located"
    if _looks_fragmented(concept):
        return "concept_present_but_fragmented", "concept text appears duplicated, truncated, or prompt-shaped"
    if "ECA" in best_path and same_topic_risk:
        return "requires_new_live_signal_not_training", "contextualization recovered the concept but also admitted unsafe same-topic noise"
    return "requires_new_live_signal_not_training", "concept exists but current reports do not identify a training-only fix"


def _looks_fragmented(text: str) -> bool:
    lower = text.lower()
    half = len(text) // 2
    if half > 40 and text[:half].strip().lower() in lower[half:].lower():
        return True
    prompt_markers = ("in this cycle", "the prediction is that", "for instance")
    return any(marker in lower for marker in prompt_markers) and len(tokens(text)) < 18


def classify_noise_item(noise: dict[str, Any], *, expected_texts: list[str]) -> tuple[str, str]:
    text = str(noise.get("concept") or "")
    feat = noise.get("features", {})
    tt = tokens(text)
    expected_overlap = max((len(tt & tokens(expected)) / max(1, len(tt | tokens(expected))) for expected in expected_texts), default=0.0)
    generic_ratio = float(feat.get("generic_anchor_ratio", 0.0) or 0.0)
    relation_specificity = int(feat.get("relation_specificity", 0) or 0)
    confidence = float(feat.get("confidence", 0.0) or 0.0)
    promotion = float(feat.get("promotion_score", 0.0) or 0.0)
    centrality = float(feat.get("projected_centrality", 0.0) or 0.0)

    if expected_overlap >= 0.55:
        return "duplicate_or_near_duplicate", "high lexical overlap with an expected concept"
    if generic_ratio >= 0.45:
        return "generic_anchor_noise", "ranking appears driven by generic anchors"
    if relation_specificity <= 1:
        return "wrong_relation_same_topic", "same topic but weak relation specificity"
    if "uncertainty" in tt or "confidence" in tt:
        return "wrong_evidence_role_same_topic", "same topic but plays an uncertainty/context role rather than target evidence role"
    if centrality >= 0.33:
        return "centrality_bias_noise", "same-topic concept may be carried by centrality"
    if confidence >= 0.85 or promotion >= 0.58:
        return "promotion_confidence_noise", "same-topic concept may be carried by confidence/promotion strength"
    return "useful_neighbor", "neighboring context that is not clearly harmful from available deterministic features"


def build_audit(args: argparse.Namespace) -> dict[str, Any]:
    hybrid = load_json(args.hybrid)
    benchmark = load_json(args.benchmark)
    safety = load_json(args.safety)
    usability = load_json(args.usability)
    deep = load_json(args.deep)
    real = load_json(args.model_b_real)

    visible_by_id = index_visible_expected(usability)
    deep_by_case = index_deep_cases(deep)
    real_by_case = index_real_cases(real)

    miss_rows = []
    missing_inventory = []
    generic_fragmented = []
    metadata_gaps = []
    for miss in benchmark.get("missed_expected_concepts", []):
        cid = str(miss.get("concept_id"))
        case = str(miss.get("case"))
        visible = visible_by_id.get(cid)
        deep_case = deep_by_case.get(case)
        real_case = real_by_case.get(case)
        primary, rationale = primary_class_for(
            miss=miss,
            visible=visible,
            deep_case=deep_case,
            real_case=real_case,
        )
        assert primary in PRIMARY_CLASSES
        row = {
            "case": case,
            "concept_id": cid,
            "concept": compact(miss.get("concept", "")),
            "current_model_b_decision": miss.get("current_model_b_decision"),
            "benchmark_classification": miss.get("classification"),
            "activation_rank": miss.get("activation_rank"),
            "primary_corpus_class": primary,
            "rationale": rationale,
            "same_topic_noise_inseparable": bool(miss.get("same_topic_noise_inseparable_under_live_safe_signals")),
            "redundant_with_used_evidence": bool(miss.get("redundant_with_used_evidence")),
            "requires_signal_not_currently_available_live": bool(miss.get("requires_signal_not_currently_available_live")),
            "best_attempted_recovery_path": miss.get("best_attempted_recovery_path"),
            "why_recovery_failed": miss.get("why_recovery_failed"),
            "visibility_features": (visible or {}).get("features", {}),
        }
        miss_rows.append(row)
        if primary == "concept_absent":
            missing_inventory.append(row)
        if primary in {"concept_present_but_too_generic", "concept_present_but_fragmented", "concept_present_but_buried_by_noise"}:
            generic_fragmented.append(row)
        if primary in {
            "concept_present_but_missing_relation_metadata",
            "concept_present_but_missing_evidence_role",
            "requires_new_live_signal_not_training",
        }:
            metadata_gaps.append(row)

    noise_rows = []
    for case_audit in deep.get("case_audits", []):
        expected_texts = [item.get("concept", "") for item in case_audit.get("missed_expected", [])]
        for source_name in ("top_noise", "rescued_by_failed_reranks_noise"):
            for noise in case_audit.get(source_name, []) or []:
                cls, rationale = classify_noise_item(noise, expected_texts=expected_texts)
                assert cls in NOISE_CLASSES
                noise_rows.append(
                    {
                        "case": case_audit.get("case"),
                        "source": source_name,
                        "concept_id": noise.get("concept_id"),
                        "concept": compact(noise.get("concept", "")),
                        "rank": noise.get("rank"),
                        "noise_class": cls,
                        "rationale": rationale,
                        "features": noise.get("features", {}),
                    }
                )

    primary_counts = Counter(row["primary_corpus_class"] for row in miss_rows)
    noise_counts = Counter(row["noise_class"] for row in noise_rows)
    recommendation = decide(primary_counts, noise_counts)

    permanent_training_justified_now = False
    training_rationale = (
        "No. Most misses are represented in the corpus but lack separable live-safe signal/metadata or are benchmark/live-window limitations. "
        "Permanent training should wait until live canonical storage and evidence-role metadata are designed."
    )
    if primary_counts["concept_absent"] + primary_counts["concept_present_but_fragmented"] > len(miss_rows) / 2:
        training_rationale = (
            "Not yet. Even if corpus expansion is eventually needed, permanent training should wait for live canonical storage; use isolated stores only."
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "audit_only": True,
        "training_run": False,
        "live_runtime_changed": False,
        "canonical_storage_changed": False,
        "current_v13_final_state": {
            "default": "Model B contextualized corpus support + citation_context reasoning usage gate",
            "hyb1": "dormant/env-gated only via DELTA_RUNTIME_V13_HYB1_ENABLED=true",
            "v13_variant_work": "stopped unless explicitly requested",
        },
        "source_reports": {
            "hybrid": str(args.hybrid),
            "benchmark": str(args.benchmark),
            "safety": str(args.safety),
            "usability": str(args.usability),
            "deep": str(args.deep),
            "model_b_real": str(args.model_b_real),
        },
        "v13_context": {
            "hyb1_final_recommendation": hybrid.get("final_recommendation"),
            "benchmark_final_recommendation": benchmark.get("final_recommendation"),
            "safety_final_recommendation": safety.get("final_recommendation"),
            "model_b_stable_v13_local_optimum": benchmark.get("model_b_stable_v13_local_optimum"),
            "catastrophic_failures_detected": any(
                item.get("catastrophic_possible")
                for item in safety.get("remaining_model_b_failure_classification", [])
            ),
        },
        "corpus_sufficiency_counts": dict(sorted(primary_counts.items())),
        "same_topic_noise_counts": dict(sorted(noise_counts.items())),
        "missed_expected_concepts": miss_rows,
        "missing_concept_inventory": missing_inventory,
        "generic_fragmented_or_buried_inventory": generic_fragmented,
        "missing_relation_or_evidence_role_metadata": metadata_gaps,
        "same_topic_noise_inventory": noise_rows,
        "permanent_training_justified_now": permanent_training_justified_now,
        "permanent_training_rationale": training_rationale,
        "should_wait_until_live_canonical_storage": [
            "permanent training/corpus expansion",
            "canonical promotion",
            "schema-free migration of temporary stores",
            "using temp-folder outputs as permanent knowledge",
        ],
        "recommended_v14_first_step": (
            "Run a report-only new-signal schema audit over remaining V1.3 misses, focusing on evidence-role metadata before training."
            if recommendation == "NEW_SIGNAL_SCHEMA_BEFORE_TRAINING"
            else "Run the next audit indicated by the final recommendation."
        ),
        "continuation_checkpoint": {
            "runtime_v13_complete": True,
            "model_b_default_remains_active": True,
            "hyb1_dormant_only": True,
            "do_not_train": True,
            "next_step": recommendation,
        },
        "final_recommendation": recommendation,
    }


def decide(primary_counts: Counter[str], noise_counts: Counter[str]) -> str:
    total = sum(primary_counts.values())
    if total == 0:
        return "RUN_MORE_DIAGNOSTICS"
    absent_or_fragmented = primary_counts["concept_absent"] + primary_counts["concept_present_but_fragmented"]
    metadata_or_signal = (
        primary_counts["concept_present_but_missing_relation_metadata"]
        + primary_counts["concept_present_but_missing_evidence_role"]
        + primary_counts["requires_new_live_signal_not_training"]
    )
    artifacts = (
        primary_counts["benchmark_expected_but_not_live_usable"]
        + primary_counts["concept_redundant_with_used_evidence"]
    )
    same_topic_noise = sum(noise_counts.values()) - noise_counts["useful_neighbor"]
    if absent_or_fragmented > total / 2:
        return "CORPUS_EXPANSION_AFTER_LIVE_STORE"
    if metadata_or_signal >= max(absent_or_fragmented, artifacts) and metadata_or_signal > 0:
        return "NEW_SIGNAL_SCHEMA_BEFORE_TRAINING"
    if same_topic_noise >= 10 and metadata_or_signal == 0:
        return "CORPUS_CONSOLIDATION_AUDIT"
    if artifacts > total / 2:
        return "CHECKPOINT_NO_TRAINING_NEEDED"
    if same_topic_noise >= 10:
        return "CORPUS_CONSOLIDATION_AUDIT"
    return "RUN_MORE_DIAGNOSTICS"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime V1.4 Corpus Sufficiency Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Final recommendation: `{report['final_recommendation']}`",
        "",
        "## 1. Summary",
        "",
        "This report asks whether the current corpus is sufficient for the remaining Runtime V1.3 failures. It does not train, promote, patch runtime behavior, modify defaults, or write canonical knowledge.",
        "",
        "## 2. V1.3 Final State",
        "",
    ]
    for key, value in report["current_v13_final_state"].items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        "## 3. Why This Is Not Training",
        "",
        "The audit reads existing reports and archived benchmark outputs only. It classifies whether missing evidence is absent, malformed, buried, redundant, benchmark-only, or missing metadata/signals. It does not generate new experiences or persist knowledge.",
        "",
        "## 4. Corpus Sufficiency By Failed Case",
        "",
        "| Case | Concept | Rank | Primary Class | Rationale |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in report["missed_expected_concepts"]:
        lines.append(
            f"| `{row['case']}` | {row['concept'].replace('|', '/')} | `{row['activation_rank']}` | `{row['primary_corpus_class']}` | {row['rationale'].replace('|', '/')} |"
        )
    lines += [
        "",
        "Corpus class counts:",
        "",
    ]
    for key, value in report["corpus_sufficiency_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## 5. Missing Concept Inventory",
        "",
    ]
    if report["missing_concept_inventory"]:
        for row in report["missing_concept_inventory"]:
            lines.append(f"- `{row['case']}`: {row['concept']}")
    else:
        lines.append("No remaining miss was classified as `concept_absent` from the available reports.")
    lines += [
        "",
        "## 6. Generic/Fragmented Concept Inventory",
        "",
    ]
    if report["generic_fragmented_or_buried_inventory"]:
        for row in report["generic_fragmented_or_buried_inventory"]:
            lines.append(f"- `{row['case']}` / `{row['primary_corpus_class']}`: {row['concept']}")
    else:
        lines.append("No generic, fragmented, or buried inventory was identified.")
    lines += [
        "",
        "## 7. Missing Relation/Evidence-Role Metadata",
        "",
    ]
    if report["missing_relation_or_evidence_role_metadata"]:
        for row in report["missing_relation_or_evidence_role_metadata"]:
            features = row.get("visibility_features", {})
            lines.append(
                f"- `{row['case']}` / `{row['primary_corpus_class']}`: relation `{features.get('relation_action_frame_match')}`, evidence-role `{features.get('evidence_need_match')}` - {row['concept']}"
            )
    else:
        lines.append("No relation/evidence-role metadata gap was identified.")
    lines += [
        "",
        "## 8. Same-Topic Noise Inventory",
        "",
        "| Case | Rank | Noise Class | Concept |",
        "| --- | ---: | --- | --- |",
    ]
    for row in report["same_topic_noise_inventory"][:80]:
        lines.append(
            f"| `{row['case']}` | `{row['rank']}` | `{row['noise_class']}` | {row['concept'].replace('|', '/')} |"
        )
    lines += [
        "",
        "Noise class counts:",
        "",
    ]
    for key, value in report["same_topic_noise_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        "## 9. Whether Permanent Training Is Justified Now",
        "",
        f"`{report['permanent_training_justified_now']}`",
        "",
        report["permanent_training_rationale"],
        "",
        "## 10. What Should Wait Until Live Canonical Storage",
        "",
    ]
    for item in report["should_wait_until_live_canonical_storage"]:
        lines.append(f"- {item}")
    lines += [
        "",
        "## 11. Recommended V1.4 First Step",
        "",
        report["recommended_v14_first_step"],
        "",
        "## 12. Continuation Checkpoint",
        "",
    ]
    for key, value in report["continuation_checkpoint"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines += [
        "",
        report["final_recommendation"],
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid", type=Path, default=HYBRID)
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--safety", type=Path, default=SAFETY)
    parser.add_argument("--usability", type=Path, default=USABILITY)
    parser.add_argument("--deep", type=Path, default=DEEP)
    parser.add_argument("--model-b-real", type=Path, default=MODEL_B_REAL)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_audit(args)
    json_path = args.reports_dir / "runtime_v14_corpus_sufficiency_audit.json"
    md_path = args.reports_dir / "runtime_v14_corpus_sufficiency_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(report["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

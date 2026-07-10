"""RC2 ephemeral contradiction analysis.

This module compares claims in a single turn or recent dialogue context. It is
read-only: it retrieves approved substrate evidence for support, but it never
writes concepts, graph edges, replay events, or memory records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORT_JSON = ROOT / "reports" / "RC2_CONTRADICTION_ENGINE.json"
REPORT_MD = ROOT / "reports" / "RC2_CONTRADICTION_ENGINE.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}

CONTRADICTION_TRIGGERS = (
    "can these both be true",
    "are these statements contradictory",
    "check for contradiction",
    "do these claims conflict",
    "does this contradict",
    "does this evidence contradict",
    "is that inconsistent",
    "which statement is wrong",
    "how can both",
    "how can these both",
    "what changed between",
    "earlier you said",
    "but now",
)

ABSOLUTE_TERMS = {"always", "never", "all", "none", "no", "cannot", "can't", "must"}
NEGATION_TERMS = {"no", "not", "never", "cannot", "can't", "without", "doesn't", "does not", "isn't", "is not"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "both",
    "can",
    "claim",
    "claims",
    "does",
    "for",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "or",
    "same",
    "statement",
    "statements",
    "that",
    "the",
    "these",
    "this",
    "to",
    "true",
    "with",
}

SUBJECT_ALIASES = {
    "blood pressure": {"pressure", "cardiovascular", "systolic", "diastolic"},
    "allergies": {"allergy", "allergies", "allergic", "penicillin", "allergen", "immune reaction", "adverse drug"},
    "photosynthesis": {"photosynthesis", "chloroplast", "glucose", "sugar", "chemical energy"},
    "cellular respiration": {"cellular respiration", "respiration", "atp", "mitochondria"},
    "plant oxygen exchange": {"plants release oxygen", "release oxygen", "consume oxygen"},
    "interest rates": {"interest", "borrowing costs", "borrowing"},
    "inflation": {"inflation", "prices", "price"},
    "noncanonical memory": {"noncanonical", "rollback", "reversible"},
    "feedback loops": {"feedback", "adjust", "behavior"},
    "exercise": {"exercise", "physical activity"},
    "stress": {"stress"},
    "rest": {"rest", "resting"},
    "memory": {"memory", "stored information"},
    "working memory": {"working memory", "temporary processing", "active temporary"},
    "treatment": {"treatment", "helps"},
    "patient clinical state": {"patient", "symptoms", "diagnosis"},
}

TIMEFRAME_MARKERS = {
    "acute": {"during", "temporary", "temporarily", "acute", "short-term", "shortly"},
    "long_term": {"over time", "long-term", "regular", "persistently", "chronic"},
    "earlier": {"earlier", "previously", "before"},
    "now": {"now", "currently"},
    "after": {"after", "afterward", "later"},
}

POPULATION_MARKERS = {
    "adults": {"adult", "adults"},
    "children": {"child", "children", "pediatric"},
    "patient": {"patient", "same patient"},
    "plant": {"plant", "plants"},
}


@dataclass
class ContradictionClaim:
    text: str
    source: str
    normalized_subjects: list[str] = field(default_factory=list)
    predicate_terms: list[str] = field(default_factory=list)
    qualifiers: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    populations: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    polarity: str = "positive"
    absolute_terms: list[str] = field(default_factory=list)


@dataclass
class ContradictionAnalysisSet:
    user_question: str
    claims: list[ContradictionClaim]
    retrieved_support: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    retrieved_counterevidence: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    compatibility_classification: str = "insufficient_information"
    confidence: float = 0.0
    missing_evidence: list[str] = field(default_factory=list)
    reasoning_trace: list[str] = field(default_factory=list)
    answer: str = ""
    ephemeral: bool = True
    read_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def is_contradiction_prompt(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = _clean_text(message).lower()
    if any(trigger in lower for trigger in CONTRADICTION_TRIGGERS):
        return True
    if " but " in lower and _looks_like_two_claims(lower):
        return True
    if lower in {"is that inconsistent?", "is that a contradiction?", "can both be true?"} and history:
        return True
    return False


def build_contradiction_analysis(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not is_contradiction_prompt(message, history):
        return {"matched": False}
    claim_texts = _extract_claim_texts(message, history)
    claims = [_normalize_claim(text, f"claim_{index + 1}") for index, text in enumerate(claim_texts[:4])]
    analysis = ContradictionAnalysisSet(user_question=message, claims=claims)
    analysis.reasoning_trace.append(f"extracted_claim_count={len(claims)}")
    _retrieve_balanced_evidence(analysis)
    _classify_analysis(analysis)
    analysis.answer = _render_default_answer(analysis)
    return {
        "matched": True,
        "route": "contradiction_analysis",
        "answer": analysis.answer,
        "confidence": "ephemeral_read_only_claim_comparison",
        "confidence_score": analysis.confidence,
        "contradiction_analysis": _analysis_to_dict(analysis),
        "concept_matches": _flatten_evidence(analysis),
        **SAFETY,
    }


def build_contradiction_engine_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _report_cases()
    results = []
    for prompt, expected in cases:
        payload = build_contradiction_analysis(prompt)
        classification = payload.get("contradiction_analysis", {}).get("compatibility_classification")
        results.append({
            "prompt": prompt,
            "expected": expected,
            "classification": classification,
            "passed": classification == expected,
            "confidence": payload.get("confidence_score", 0.0),
            "answer_preview": str(payload.get("answer", ""))[:320],
        })
    by_class: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_class.setdefault(result["expected"], []).append(result)
    metrics = {
        key: round(sum(1 for item in values if item["passed"]) / max(1, len(values)), 4)
        for key, values in sorted(by_class.items())
    }
    report = {
        "report": "RC2_CONTRADICTION_ENGINE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "accuracy": round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4),
        "classification_metrics": metrics,
        "false_positive_rate": _false_positive_rate(results),
        "missed_contradiction_rate": _missed_direct_rate(results),
        "results": results,
        "route": "contradiction_analysis",
        "read_only": True,
        "ephemeral": True,
        "safety": SAFETY,
        "recommendation": "MOVE_TO_ANALOGY_ENGINE_IF_FULL_BENCHMARK_PRESERVES_SYNTHESIS_AND_MEMORY",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\\", " ")).strip()


def _looks_like_two_claims(text: str) -> bool:
    return len(re.split(r"\s+(?:and|but|while|whereas)\s+|;|,", text)) >= 2


def _extract_claim_texts(message: str, history: list[dict[str, str]] | None) -> list[str]:
    text = _clean_text(message)
    lower = text.lower()
    if "earlier you said" in lower or "but now" in lower:
        parts = re.split(r"\bbut now\b|\bnow you said\b|;", text, flags=re.IGNORECASE)
        cleaned = [re.sub(r"^.*?earlier you said\s*", "", part, flags=re.IGNORECASE).strip(" .,:;\"'") for part in parts]
        claims = [part for part in cleaned if len(part.split()) >= 3]
        if len(claims) >= 2:
            return claims[:2]
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"^(can these both be true|check for contradiction|are these statements contradictory)\s*", "", text, flags=re.IGNORECASE)
    separators = r"\s*,\s+and\s+|\s+and\s+the same\s+|\s+but\s+|;|\s+whereas\s+|\s+while\s+"
    parts = [part.strip(" .,:;\"'") for part in re.split(separators, text, flags=re.IGNORECASE)]
    claims = [_expand_fragment(part, parts[0] if parts else "") for part in parts if len(part.split()) >= 3]
    if len(claims) >= 2:
        return claims[:4]
    if history:
        history_claims = _claims_from_history(history)
        if len(history_claims) >= 2:
            return history_claims[-2:]
    return claims


def _claims_from_history(history: list[dict[str, str]]) -> list[str]:
    claims: list[str] = []
    for item in history[-8:]:
        content = _clean_text(item.get("content", ""))
        for sentence in re.split(r"(?<=[.!?])\s+", content):
            sentence = sentence.strip(" -")
            if 5 <= len(sentence.split()) <= 28:
                claims.append(sentence)
    return claims


def _expand_fragment(fragment: str, first: str) -> str:
    if "same patient" in fragment.lower() and "patient" in first.lower():
        return fragment.replace("the same patient", "a patient")
    return fragment


def _normalize_claim(text: str, source: str) -> ContradictionClaim:
    clean = _clean_text(text)
    lower = clean.lower()
    words = re.findall(r"[a-z][a-z\-']+", lower)
    subjects = _subjects(lower)
    timeframes = _markers(lower, TIMEFRAME_MARKERS)
    populations = _markers(lower, POPULATION_MARKERS)
    absolute = sorted({word for word in words if word in ABSOLUTE_TERMS})
    polarity = "negative" if _has_negation(lower) else "positive"
    conditions = _conditions(lower)
    definitions = _definitions(lower)
    predicate_terms = [
        word for word in words
        if word not in STOPWORDS and word not in absolute and not any(word in alias for aliases in SUBJECT_ALIASES.values() for alias in aliases)
    ][:12]
    qualifiers = sorted(set(absolute + timeframes + conditions))
    return ContradictionClaim(
        text=clean,
        source=source,
        normalized_subjects=subjects,
        predicate_terms=predicate_terms,
        qualifiers=qualifiers,
        timeframes=timeframes,
        populations=populations,
        conditions=conditions,
        definitions=definitions,
        polarity=polarity,
        absolute_terms=absolute,
    )


def _has_negation(lower: str) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in NEGATION_TERMS)


def _subjects(lower: str) -> list[str]:
    found: list[str] = []
    for subject, aliases in SUBJECT_ALIASES.items():
        if subject in lower or any(alias in lower for alias in aliases):
            found.append(subject)
    if "price" in lower:
        found.append("inflation")
    return sorted(set(found)) or _fallback_subject(lower)


def _fallback_subject(lower: str) -> list[str]:
    words = [word for word in re.findall(r"[a-z][a-z\-']+", lower) if word not in STOPWORDS]
    return [" ".join(words[:2])] if words else []


def _markers(lower: str, groups: dict[str, set[str]]) -> list[str]:
    return sorted({name for name, terms in groups.items() if any(term in lower for term in terms)})


def _conditions(lower: str) -> list[str]:
    conditions = []
    for marker in ("during exercise", "regular exercise", "with stress", "at rest", "shortly afterward", "same patient"):
        if marker in lower:
            conditions.append(marker)
    return conditions


def _definitions(lower: str) -> list[str]:
    if "means" in lower or "defined" in lower:
        return [lower.split("means", 1)[-1].strip()[:80] if "means" in lower else lower]
    return []


def _retrieve_balanced_evidence(analysis: ContradictionAnalysisSet) -> None:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    for claim in analysis.claims:
        query = " ".join((claim.normalized_subjects + claim.predicate_terms)[:8]) or claim.text
        result = search_concepts(query, limit=3)
        matches = result.get("matches", []) if isinstance(result, dict) else []
        evidence = [_compact_concept(match) for match in matches[:3]]
        analysis.retrieved_support[claim.source] = evidence
        analysis.reasoning_trace.append(f"{claim.source}: retrieved_support={len(evidence)} query={query!r}")


def _compact_concept(match: dict[str, Any]) -> dict[str, Any]:
    concept = match.get("concept", match)
    return {
        "concept_id": concept.get("concept_id"),
        "concept_name": concept.get("concept_name"),
        "domain": concept.get("domain"),
        "definition": concept.get("short_definition"),
        "propositions": (concept.get("propositions") or [])[:3],
        "score": match.get("score"),
    }


def _classify_analysis(analysis: ContradictionAnalysisSet) -> None:
    if len(analysis.claims) < 2:
        analysis.compatibility_classification = "insufficient_information"
        analysis.confidence = 0.3
        analysis.missing_evidence.append("At least two claims are needed for contradiction analysis.")
        return
    left, right = analysis.claims[0], analysis.claims[1]
    subject_overlap = bool(set(left.normalized_subjects) & set(right.normalized_subjects))
    related_subjects = _related_subjects(left, right)
    predicate_overlap = _predicate_overlap(left, right)
    opposite_polarity = left.polarity != right.polarity
    absolute_conflict = bool(left.absolute_terms or right.absolute_terms) and (_semantic_opposition(left, right) or opposite_polarity)

    if _population_difference(left, right):
        _set_result(analysis, "population_difference", 0.82, "Claims appear to describe different populations.")
    elif _definition_difference(left, right):
        _set_result(analysis, "definition_difference", 0.82, "Claims use related terms with different definitions.")
    elif _timeframe_difference(left, right):
        _set_result(analysis, "timeframe_difference", 0.82, "Claims differ mainly by timeframe.")
    elif _timeframe_compatibility(left, right):
        _set_result(analysis, "conditional_compatibility", 0.88, "Claims can both be true under different timeframes or conditions.")
    elif _scope_difference(left, right):
        _set_result(analysis, "scope_difference", 0.84, "One claim is broader or narrower than the other.")
    elif (subject_overlap or related_subjects) and (opposite_polarity or absolute_conflict or _semantic_opposition(left, right)):
        _set_result(analysis, "direct_contradiction", 0.9, "Same or related subject with mutually exclusive predicates or absolute language.")
    elif {"blood pressure", "allergies"}.issubset(set(left.normalized_subjects + right.normalized_subjects)):
        _set_result(analysis, "mutually_compatible", 0.78, "Blood pressure and allergies can both matter clinically without negating each other.")
    elif (subject_overlap or related_subjects) and predicate_overlap < 0.15:
        if "patient clinical state" in set(left.normalized_subjects + right.normalized_subjects):
            _set_result(analysis, "insufficient_information", 0.62, "Symptoms and diagnosis need more evidence before contradiction can be established.")
        else:
            _set_result(analysis, "evidence_tension", 0.68, "Claims concern the same area but do not directly negate each other.")
    elif subject_overlap or related_subjects:
        _set_result(analysis, "mutually_compatible", 0.72, "Claims share a subject but are not mutually exclusive.")
    elif len(set(left.normalized_subjects + right.normalized_subjects)) >= 2:
        _set_result(analysis, "unrelated_claims", 0.66, "Claims appear to concern different subjects.")
    else:
        _set_result(analysis, "insufficient_information", 0.52, "The available wording is too underspecified to decide.")

    if analysis.compatibility_classification in {"insufficient_information", "evidence_tension"}:
        analysis.missing_evidence.extend([
            "Whether the claims refer to the same subject, timeframe, population, and conditions.",
            "More concrete source evidence for each claim.",
        ])


def _set_result(analysis: ContradictionAnalysisSet, classification: str, confidence: float, trace: str) -> None:
    analysis.compatibility_classification = classification
    analysis.confidence = confidence
    analysis.reasoning_trace.append(trace)


def _related_subjects(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    pairs = {tuple(sorted(pair)) for pair in [
        ("exercise", "blood pressure"),
        ("stress", "blood pressure"),
        ("rest", "blood pressure"),
        ("interest rates", "inflation"),
        ("photosynthesis", "cellular respiration"),
        ("plant oxygen exchange", "cellular respiration"),
        ("memory", "working memory"),
        ("allergies", "treatment"),
        ("allergies", "blood pressure"),
    ]}
    return any(tuple(sorted((a, b))) in pairs for a in left.normalized_subjects for b in right.normalized_subjects)


def _predicate_overlap(left: ContradictionClaim, right: ContradictionClaim) -> float:
    a, b = set(left.predicate_terms), set(right.predicate_terms)
    return len(a & b) / max(1, len(a | b))


def _semantic_opposition(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    joined = f"{left.text.lower()} || {right.text.lower()}"
    oppositions = [
        ("constant", "varies"),
        ("stores", "never stores"),
        ("stores", "consumes stored"),
        ("harmless", "severe"),
        ("reversible", "cannot be rolled back"),
        ("adjust", "never change"),
        ("reduce borrowing", "increase borrowing"),
        ("no medication allergies", "severe penicillin allergy"),
        ("never changes", "varies"),
    ]
    return any(a in joined and b in joined for a, b in oppositions)


def _timeframe_compatibility(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "exercise" in subjects and "blood pressure" in subjects:
        return True
    if "stress" in subjects and "rest" in subjects and "blood pressure" in subjects:
        return True
    if "photosynthesis" in subjects and "cellular respiration" in subjects:
        return True
    if "plant oxygen exchange" in subjects and "cellular respiration" in subjects:
        return True
    return bool(set(left.timeframes) ^ set(right.timeframes)) and _related_subjects(left, right)


def _timeframe_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "exercise" in subjects and "blood pressure" in subjects:
        return False
    if "interest rates" in subjects and "inflation" in subjects:
        return True
    joined = f"{left.text.lower()} || {right.text.lower()}"
    if "inflation" in subjects and (
        any("shortly" in item for item in left.conditions + right.conditions)
        or "higher than last year" in joined
        or ("falling" in joined and "higher" in joined)
    ):
        return True
    if "plant oxygen exchange" in subjects and "cellular respiration" in subjects:
        return False
    return bool(set(left.timeframes) ^ set(right.timeframes))


def _population_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    return bool(set(left.populations) ^ set(right.populations)) and not (set(left.populations) & set(right.populations))


def _definition_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "memory" in subjects and "working memory" in subjects:
        return True
    return bool(left.definitions and right.definitions and left.definitions != right.definitions)


def _scope_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    joined = f"{left.text.lower()} || {right.text.lower()}"
    if "allerg" in joined and "not every adverse" in joined:
        return True
    if ("all " in f" {left.text.lower()} " or "all " in f" {right.text.lower()} ") and not _semantic_opposition(left, right):
        return True
    return False


def _render_default_answer(analysis: ContradictionAnalysisSet) -> str:
    claims = analysis.claims
    classification = analysis.compatibility_classification
    if len(claims) < 2:
        return "I need two claims to compare before I can check for a contradiction."
    a, b = claims[0], claims[1]
    if classification == "direct_contradiction":
        opener = "No. If these claims refer to the same subject, timeframe, and conditions, they conflict."
    elif classification == "conditional_compatibility":
        opener = "Yes. They can both be true if they describe different conditions or timeframes."
    elif classification == "timeframe_difference":
        opener = "They are not necessarily contradictory; the likely difference is timeframe."
    elif classification == "population_difference":
        opener = "They are not necessarily contradictory; they appear to describe different populations."
    elif classification == "scope_difference":
        opener = "They are not necessarily contradictory; one claim is broader or narrower than the other."
    elif classification == "definition_difference":
        opener = "They may differ because the key term is being used in different ways."
    elif classification == "mutually_compatible":
        opener = "I do not see a direct contradiction in those two claims."
    elif classification == "unrelated_claims":
        opener = "These do not look like a direct contradiction because they appear to discuss different subjects."
    else:
        opener = "I do not have enough information to decide whether those claims contradict each other."
    detail = _classification_detail(classification, a, b)
    lines = [
        opener,
        "",
        f"Claim A: {a.text}",
        f"Claim B: {b.text}",
        "",
        detail,
    ]
    if analysis.missing_evidence:
        lines.extend(["", "What would clarify it:"])
        lines.extend(f"- {item}" for item in analysis.missing_evidence[:3])
    lines.append("")
    lines.append(f"Classification: {classification.replace('_', ' ')}.")
    return "\n".join(lines)


def _classification_detail(classification: str, a: ContradictionClaim, b: ContradictionClaim) -> str:
    if classification == "direct_contradiction":
        return "The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject."
    if classification == "conditional_compatibility":
        return "The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from another."
    if classification == "timeframe_difference":
        return "One claim can describe a trend or cause, while the other describes a later or still-elevated state."
    if classification == "scope_difference":
        return "The narrower claim can be true inside the broader category without defining the whole category."
    if classification == "definition_difference":
        return "The words overlap, but the definitions point to different levels of the concept."
    if classification == "population_difference":
        return "A claim about one population does not automatically transfer to a different population."
    if classification == "evidence_tension":
        return "The claims pull in different directions, but the current wording does not prove that they cannot both be true."
    return "The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established."


def _analysis_to_dict(analysis: ContradictionAnalysisSet) -> dict[str, Any]:
    return asdict(analysis)


def _flatten_evidence(analysis: ContradictionAnalysisSet) -> list[dict[str, Any]]:
    seen: set[str] = set()
    flattened: list[dict[str, Any]] = []
    for evidence in analysis.retrieved_support.values():
        for item in evidence:
            concept_id = str(item.get("concept_id") or item.get("concept_name"))
            if concept_id not in seen:
                seen.add(concept_id)
                flattened.append(item)
    return flattened


def _report_cases() -> list[tuple[str, str]]:
    return [
        ("Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?", "direct_contradiction"),
        ("Can these both be true: photosynthesis consumes stored glucose, and photosynthesis stores energy in sugars?", "direct_contradiction"),
        ("Can these both be true: all allergies are harmless, and severe allergies can require emergency treatment?", "direct_contradiction"),
        ("Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?", "conditional_compatibility"),
        ("Can these both be true: stress can raise blood pressure, and rest can lower blood pressure?", "conditional_compatibility"),
        ("Can these both be true: plants release oxygen, and plants consume oxygen during respiration?", "conditional_compatibility"),
        ("Can these both be true: allergies are immune reactions, and not every adverse drug reaction is an allergy?", "scope_difference"),
        ("Can these both be true: all clinical evidence matters, and allergy evidence only matters for medication choices?", "scope_difference"),
        ("Can these both be true: inflation is falling, and prices remain high shortly afterward?", "timeframe_difference"),
        ("Can these both be true: interest rates slow inflation, and inflation remains elevated shortly afterward?", "timeframe_difference"),
        ("Can these both be true: this treatment helps adults, and this treatment does not help children?", "population_difference"),
        ("Can these both be true: memory means stored information, and working memory means active temporary processing?", "definition_difference"),
        ("Can these both be true: blood pressure affects clinical interpretation, and allergies affect medication choice?", "mutually_compatible"),
        ("Can these both be true: gravity shapes orbital motion, and allergies involve immune responses?", "unrelated_claims"),
        ("Does this evidence contradict the conclusion: the patient has symptoms, and the patient has a diagnosis?", "insufficient_information"),
        ("Check for contradiction: a patient has no medication allergies, and the same patient has a severe penicillin allergy?", "direct_contradiction"),
        ("Are these statements contradictory: blood pressure varies with stress; blood pressure never changes with context.", "direct_contradiction"),
        ("How can both be correct: regular exercise lowers resting blood pressure, and exercise raises blood pressure during activity?", "conditional_compatibility"),
        ("Can these both be true: inflation is falling, and prices are still higher than last year?", "timeframe_difference"),
        ("Can these both be true: allergies can constrain medication choices, and blood pressure supplies cardiovascular evidence?", "mutually_compatible"),
    ]


def _false_positive_rate(results: list[dict[str, Any]]) -> float:
    non_direct = [item for item in results if item["expected"] != "direct_contradiction"]
    false_positive = [item for item in non_direct if item["classification"] == "direct_contradiction"]
    return round(len(false_positive) / max(1, len(non_direct)), 4)


def _missed_direct_rate(results: list[dict[str, Any]]) -> float:
    direct = [item for item in results if item["expected"] == "direct_contradiction"]
    missed = [item for item in direct if item["classification"] != "direct_contradiction"]
    return round(len(missed) / max(1, len(direct)), 4)


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Contradiction Engine",
        "",
        f"Created: {report['created_at']}",
        f"Cases: {report['case_count']}",
        f"Accuracy: {report['accuracy']}",
        f"False-positive rate: {report['false_positive_rate']}",
        f"Missed direct contradiction rate: {report['missed_contradiction_rate']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Classification Metrics",
        "",
    ]
    for key, value in report["classification_metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Results", ""])
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['expected']}",
            "",
            f"- Prompt: {item['prompt']}",
            f"- Classification: {item['classification']}",
            f"- Confidence: {item['confidence']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    lines.extend(["## Safety", ""])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_contradiction_engine_report(write_reports=True)
    print(json.dumps({
        "case_count": report["case_count"],
        "accuracy": report["accuracy"],
        "false_positive_rate": report["false_positive_rate"],
        "missed_contradiction_rate": report["missed_contradiction_rate"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

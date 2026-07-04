"""Local answer routing for DELTA ARC VII-XXV exhaustive module demos."""

from __future__ import annotations

from orchestration.runtime.arc_07_investigation import report_payload as investigation_payload
from orchestration.runtime.arc_08_specialists import report_payload as specialists_payload
from orchestration.runtime.arc_exhaustive_common import exhaustive_safety_flags


def is_arc_vii_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "investigate topic",
            "what do you already know",
            "what do you not know",
            "what evidence would you seek",
            "what questions should be answered first",
            "summarize current findings",
            "why are these findings uncertain",
        )
    )


def is_arc_viii_question(query: str) -> bool:
    normalized = " ".join(str(query).lower().split())
    return any(
        trigger in normalized
        for trigger in (
            "analyze this from multiple perspectives",
            "which specialists participated",
            "where did they disagree",
            "how was consensus formed",
            "what evidence was weakest",
            "what remains uncertain",
        )
    )


def run_arc_vii_answer(query: str) -> dict[str, object]:
    data = investigation_payload()
    normalized = " ".join(str(query).lower().split())
    if "already know" in normalized:
        answer = "The investigation knows only reviewable local runtime facts and the currently implemented module state."
        payload = {"known": data["objects"][:2]}
    elif "not know" in normalized:
        answer = "DELTA does not know topic-specific external evidence because browsing, provider authority, and live acquisition remain disabled."
        payload = {"unknowns": ("topic-specific evidence", "external corroboration", "reviewed contradictions")}
    elif "evidence" in normalized:
        answer = "DELTA would seek provenance-bearing support, contradiction checks, source quality, and reviewable citations, but collection is planned only."
        payload = {"evidence_plan": data["objects"]}
    elif "questions" in normalized:
        answer = "The first questions identify what is known, what is missing, what evidence is required, and what would increase confidence."
        payload = {"research_questions": data["primitive_names"]}
    elif "findings" in normalized:
        answer = "Current findings are preliminary review artifacts, not durable knowledge."
        payload = {"findings": [item for item in data["objects"] if item["name"] == "Finding"]}
    elif "uncertain" in normalized:
        answer = "The findings are uncertain because no live evidence collection, provider authority, or knowledge integration has occurred."
        payload = {"limitations": ("no live external evidence", "human review required", "findings are not knowledge")}
    else:
        answer = "Created a reviewable investigation module payload for topic X. It is implemented, simulated only, and non-authoritative."
        payload = {"investigation": data["objects"][0], "recommendation": data["final_recommendation"]}
    return {"phase": "Runtime ARC VII", "query": query, "answer_text": answer, **payload, "safety": exhaustive_safety_flags()}


def run_arc_viii_answer(query: str) -> dict[str, object]:
    data = specialists_payload()
    normalized = " ".join(str(query).lower().split())
    if "which specialists" in normalized or "participated" in normalized:
        answer = "ARC VIII specialist primitives are available as advisory, non-authoritative perspectives."
        payload = {"specialists": data["objects"][:4]}
    elif "disagree" in normalized:
        answer = "Disagreement is represented as a reviewable conflict bundle; no specialist receives authority to resolve it alone."
        payload = {"conflict": [item for item in data["objects"] if item["name"] == "SpecialistConflictBundle"]}
    elif "consensus" in normalized:
        answer = "Consensus is a comparison of advisory support, limitations, and confidence overlap, not a vote."
        payload = {"consensus": [item for item in data["objects"] if item["name"] == "ConsensusSummary"]}
    elif "weakest" in normalized or "uncertain" in normalized:
        answer = "The weakest evidence remains any missing external corroboration because providers and acquisition remain gated."
        payload = {"confidence": [item for item in data["objects"] if item["name"] == "ConfidenceFusion"]}
    else:
        answer = "Analyzed the topic through advisory specialist scaffolds. No specialist authority, execution, or mutation occurred."
        payload = {"specialist_deliberation": data["objects"]}
    return {"phase": "Runtime ARC VIII", "query": query, "answer_text": answer, **payload, "safety": exhaustive_safety_flags()}

"""Local answer routing for DELTA ARC VII-XXV scaffold demos."""

from __future__ import annotations

from orchestration.runtime.arc_vii_xxv_scaffolds import explain_investigation, explain_specialists


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
    return explain_investigation(query)


def run_arc_viii_answer(query: str) -> dict[str, object]:
    return explain_specialists(query)

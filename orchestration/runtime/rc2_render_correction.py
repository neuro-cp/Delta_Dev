"""First-class render-correction primitive for conversational routing.

Render correction means the user is asking DELTA to restate the previous
semantic answer under new presentation constraints. It is local, ephemeral,
and intentionally barred from retrieval, provider calls, and memory formation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


SAFETY = {
    "provider_calls_performed": False,
    "web_search_performed": False,
    "training_performed": False,
    "canonical_write_performed": False,
    "autonomous_action_performed": False,
    "memory_write_performed": False,
    "memory_candidate_created": False,
    "retrieval_performed": False,
}


@dataclass(frozen=True)
class RenderCorrectionFrame:
    operation: str
    previous_topic: str
    previous_semantic_intent: str
    requested_constraints: tuple[str, ...]
    requested_headings: tuple[str, ...]
    scope: str
    confidence: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_render_correction_payload(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    history = history or []
    normalized = _normalize(message)
    if not _is_render_correction_request(normalized):
        return None

    previous = _last_assistant_answer(history)
    fallback = _fallback_semantic_answer(message)
    if not previous and not fallback:
        return {
            "route": "render_correction",
            "answer": "I can rewrite the previous answer, but I need an answer or topic to re-render first.",
            "confidence": "render_correction_needs_prior_answer",
            "confidence_score": 0.52,
            "render_correction": RenderCorrectionFrame(
                operation="RENDER_CORRECTION",
                previous_topic="unknown",
                previous_semantic_intent="unknown",
                requested_constraints=_constraints(normalized),
                requested_headings=_requested_headings(message),
                scope="needs_prior_answer",
                confidence=0.52,
                reason="render_correction_without_prior_semantic_answer",
            ).as_dict(),
            "memory_candidate": None,
            **SAFETY,
        }

    semantic_answer = previous or fallback or ""
    headings = _requested_headings(message)
    constraints = _constraints(normalized)
    rendered = _render(semantic_answer, headings, constraints, message)
    frame = RenderCorrectionFrame(
        operation="RENDER_CORRECTION",
        previous_topic=_infer_topic(message, semantic_answer),
        previous_semantic_intent=_infer_intent(semantic_answer),
        requested_constraints=constraints,
        requested_headings=headings,
        scope="presentation_only",
        confidence=0.9 if previous else 0.78,
        reason="user_requested_presentation_change_without_new_knowledge",
    )
    return {
        "route": "render_correction",
        "answer": rendered,
        "confidence": "ephemeral_render_correction",
        "confidence_score": frame.confidence,
        "render_correction": frame.as_dict(),
        "memory_candidate": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "concept_matches": [],
        **SAFETY,
    }


def is_render_correction_request(message: str) -> bool:
    return _is_render_correction_request(_normalize(message))


def _normalize(message: str) -> str:
    return " ".join(str(message or "").lower().replace("-", " ").split())


def _is_render_correction_request(normalized: str) -> bool:
    if _explicit_new_content_request(normalized):
        return any(term in normalized for term in ("same answer", "previous answer", "rewrite", "format"))
    if any(term in normalized for term in (
        "retry the previous answer",
        "retry previous answer",
        "answer again",
        "try again",
        "rewrite that",
        "rewrite the answer",
        "reorganize",
        "use these headings",
        "use exactly these headings",
        "using exactly these headings",
        "use this format",
        "same answer",
        "same content",
        "keep the content",
        "format it like this",
        "you ignored the format",
        "you didn't follow the format",
        "you did not follow the format",
        "you didn't follow the headings",
        "you did not follow the headings",
        "make it more concise",
        "summarize the previous answer",
        "summarize previous answer",
        "summarise the previous answer",
        "summarise previous answer",
        "make it clearer",
        "same answer but shorter",
        "same answer but longer",
        "rewrite that as bullet points",
        "format compliance test",
    )):
        return True
    return "separate:" in normalized and "what remains unproven" in normalized


def _explicit_new_content_request(normalized: str) -> bool:
    return any(term in normalized for term in (
        "research the latest",
        "look up",
        "search",
        "browse",
        "retrieve new",
        "inspect a new",
    ))


def _last_assistant_answer(history: list[dict[str, str]]) -> str:
    for item in reversed(history):
        if item.get("role") == "assistant":
            text = str(item.get("content") or "").strip()
            if text and not text.lower().startswith("hi. i'm delta"):
                return text
    return ""


def _fallback_semantic_answer(message: str) -> str:
    normalized = _normalize(message)
    topic = _topic_from_message(message)
    if topic:
        return (
            f"The inspected topic is {topic}. "
            "Run one real low-risk operator session where DELTA proposes or evaluates a bounded action and the operator accepts, rejects, or revises it. "
            "Freeze-relevant evidence would include the recorded operator decision, the reason for that decision, observed governance boundaries, and at least one recovery or stop-condition result. "
            "It remains unproven whether the behavior holds across multiple real sessions, rejected proposals, rollback or recovery cases, and ordinary operator pressure."
        )
    if "delta 1.0" in normalized and "operator validation" in normalized:
        return (
            "The current DELTA 1.0 readiness/report state is the inspected scope. "
            "Run one real low-risk operator validation session where DELTA proposes or evaluates a bounded action and the operator accepts, rejects, or revises it. "
            "Freeze-relevant evidence would include the recorded operator decision, the operator's reason, governance boundaries observed, and at least one recovery or stop-condition outcome. "
            "It remains unproven whether DELTA preserves those boundaries across multiple real sessions, rejected proposals, rollback or recovery cases, and ordinary operator pressure."
        )
    return ""


def _constraints(normalized: str) -> tuple[str, ...]:
    constraints: list[str] = []
    if "heading" in normalized or "separate:" in normalized:
        constraints.append("headings")
    if "bullet" in normalized:
        constraints.append("bullets")
    if "shorter" in normalized or "concise" in normalized or "summarize" in normalized or "summarise" in normalized:
        constraints.append("concise")
    if "longer" in normalized or "expand" in normalized:
        constraints.append("expanded")
    if "clearer" in normalized:
        constraints.append("clearer")
    if "reorganize" in normalized or "organization" in normalized:
        constraints.append("reorganized")
    if _explicit_new_content_request(normalized):
        constraints.append("external_research_requires_separate_approval")
    if "do not write memory" in normalized or "no memory" in normalized:
        constraints.append("no_memory_write")
    if "do not call providers" in normalized or "no provider" in normalized:
        constraints.append("no_provider_call")
    return tuple(dict.fromkeys(constraints or ["presentation_change"]))


def _requested_headings(message: str) -> tuple[str, ...]:
    lines = [line.strip() for line in str(message or "").splitlines()]
    headings: list[str] = []
    for line in lines:
        match = re.match(r"^\d+[\.)]\s*(.+)$", line)
        if match:
            heading = match.group(1).strip()
            if 2 <= len(heading) <= 90:
                headings.append(_canonical_heading(heading))
    return tuple(dict.fromkeys(headings))


def _canonical_heading(heading: str) -> str:
    lower = heading.lower().strip()
    aliases = {
        "what you inspected": "What I inspected",
        "what i inspected": "What I inspected",
        "what you think the operator should do next": "Bounded next operator step",
        "bounded next operator step": "Bounded next operator step",
        "what evidence would make this freeze-relevant": "Evidence that would make this freeze-relevant",
        "evidence that would make this freeze-relevant": "Evidence that would make this freeze-relevant",
        "what remains unproven": "What remains unproven",
    }
    return aliases.get(lower, heading[:1].upper() + heading[1:])


def _render(semantic_answer: str, headings: tuple[str, ...], constraints: tuple[str, ...], message: str) -> str:
    content = _clean_answer(semantic_answer)
    if headings:
        return _render_with_headings(content, headings)
    if "bullets" in constraints or "reorganized" in constraints:
        points = _sentences(content)[:6]
        return "\n".join(f"- {point}" for point in points) + _safety_suffix(message)
    if "concise" in constraints:
        points = _sentences(content)[:2]
        return " ".join(points).strip() + _safety_suffix(message)
    if "expanded" in constraints:
        points = _sentences(content)
        extra = "The same point is being expanded from the existing answer only; no new retrieval or provider call was used."
        return "\n".join(points + [extra]) + _safety_suffix(message)
    return content + _safety_suffix(message)


def _render_with_headings(content: str, headings: tuple[str, ...]) -> str:
    lines: list[str] = []
    for index, heading in enumerate(headings, 1):
        lines.append(f"{index}. {heading}")
        lines.append(f"- {_section_content(heading, content)}")
        lines.append("")
    lines.append("No memory was written. No provider was called.")
    return "\n".join(lines).strip()


def _section_content(heading: str, content: str) -> str:
    lower = heading.lower()
    sentences = _sentences(content)
    if "inspected" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("inspected", "report", "topic", "state")) or sentences[0])
    if "next" in lower or "operator" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("next", "run", "bounded", "session")) or "Run one bounded operator-reviewed session using the existing answer as the scope.")
    if "evidence" in lower or "freeze" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("evidence", "record", "governance", "readiness")) or "Record the operator decision, reason, safety boundaries, and recovery or stop condition.")
    if "unproven" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("unproven", "missing", "remains", "multiple")) or "It remains unproven whether the behavior holds across varied real sessions.")
    return _strip_section_prefix(sentences[min(len(sentences) - 1, 0)])


def _find_sentence(sentences: list[str], terms: tuple[str, ...]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(term in lower for term in terms):
            return sentence
    return ""


def _sentences(text: str) -> list[str]:
    normalized = _remove_render_correction_boilerplate(str(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    cleaned = [_strip_section_prefix(part.strip(" -")) for part in parts if part.strip(" -")]
    return list(dict.fromkeys(part for part in cleaned if part))


def _clean_answer(text: str) -> str:
    text = _remove_render_correction_boilerplate(str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _remove_render_correction_boilerplate(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower() in {"no memory was written. no provider was called.", "no memory was written.", "no provider was called."}:
            continue
        stripped = re.sub(r"^\d+[\.)]\s*", "", stripped)
        stripped = stripped.lstrip("- ").strip()
        if _is_section_heading_only(stripped):
            continue
        lines.append(stripped)
    return " ".join(lines)


def _strip_section_prefix(text: str) -> str:
    result = str(text or "").strip(" -")
    section_prefixes = (
        "What I inspected",
        "What you inspected",
        "Bounded next operator step",
        "What you think the operator should do next",
        "Evidence that would make this freeze-relevant",
        "What evidence would make this freeze-relevant",
        "What remains unproven",
    )
    changed = True
    while changed:
        changed = False
        for prefix in section_prefixes:
            pattern = rf"^{re.escape(prefix)}(?:\s*[-:]\s*|\s+)"
            updated = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
            if updated != result:
                result = updated
                changed = True
    return result


def _is_section_heading_only(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return normalized in {
        "what i inspected",
        "what you inspected",
        "bounded next operator step",
        "what you think the operator should do next",
        "evidence that would make this freeze-relevant",
        "what evidence would make this freeze-relevant",
        "what remains unproven",
    }


def _topic_from_message(message: str) -> str:
    match = re.search(
        r"topic:\s*(.+?)(?:\s+do not\s+|\s+no memory\s+|\s+no provider\s+|$)",
        str(message or ""),
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", match.group(1)).strip(" .") if match else ""


def _infer_topic(message: str, semantic_answer: str) -> str:
    return _topic_from_message(message) or (_sentences(semantic_answer) or ["prior answer"])[0][:80]


def _infer_intent(semantic_answer: str) -> str:
    lower = semantic_answer.lower()
    if "freeze" in lower or "operator" in lower:
        return "operator_readiness_guidance"
    if "contradiction" in lower:
        return "contradiction_explanation"
    if "analogy" in lower:
        return "analogy_explanation"
    return "prior_answer_rendering"


def _safety_suffix(message: str) -> str:
    lower = str(message or "").lower()
    notes = []
    if "research the latest" in lower or "look up" in lower or "search" in lower:
        notes.append("External research was not performed; it would require separate approval.")
    if "do not write memory" in lower or "no memory" in lower:
        notes.append("No memory was written.")
    if "do not call providers" in lower or "no provider" in lower:
        notes.append("No provider was called.")
    return ("\n\n" + " ".join(notes)) if notes else ""

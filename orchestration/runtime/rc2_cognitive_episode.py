"""Ephemeral RC2 cognitive episode and working-memory resolver.

The episode object is rebuilt from the current message and short chat history on
each turn. It is never stored and never mutates substrate state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC2_WORKING_MEMORY_EPISODE.json"
REPORT_MD = ROOT / "reports" / "RC2_WORKING_MEMORY_EPISODE.md"

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

KNOWN_TOPICS = [
    "blood pressure",
    "allergies",
    "photosynthesis",
    "cellular respiration",
    "battery charging",
    "planning",
    "feedback loops",
    "interest rates",
    "inflation",
    "noncanonical memory",
    "memory consolidation",
    "gravity",
    "orbital motion",
    "meaning of life",
]

FOLLOWUP_FORMS = {
    "tell me more",
    "go deeper",
    "explain more",
    "give an example",
    "give me an example",
    "why",
    "why?",
    "how so",
    "simplify",
    "explain it simpler",
    "explain that more simply",
    "what else matters",
    "what else",
    "where does it break",
    "where does that analogy break",
    "what supports that",
    "what evidence is missing",
    "compare those",
    "what changed",
}


@dataclass
class CognitiveEpisode:
    episode_id: str
    active_topic: str | None
    active_entities: list[str]
    active_question: str | None
    active_answer: str | None
    active_route: str | None
    active_wrs: dict[str, Any] | None = None
    active_contradiction: dict[str, Any] | None = None
    active_analogy: dict[str, Any] | None = None
    active_examples: list[str] = field(default_factory=list)
    active_limits: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    last_summary: str = ""
    conversation_branch: list[dict[str, Any]] = field(default_factory=list)
    resolved_references: list[dict[str, str]] = field(default_factory=list)
    rejected_references: list[dict[str, str]] = field(default_factory=list)
    episode_confidence: float = 0.0
    turn_number: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    ephemeral: bool = True
    read_only: bool = True


def build_cognitive_episode(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    current_route: str | None = None,
    current_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = history or []
    branches = _branches(history)
    current_entities = _entities(message)
    active = _select_active_branch(message, branches, current_entities)
    explicit_change = _explicit_topic_change(message, active)
    if explicit_change:
        active = {
            "topic": current_entities[0] if current_entities else _topic_from_question(message),
            "question": message,
            "answer": "",
            "route": current_route or "new_topic",
            "entities": current_entities,
            "summary": "explicit topic change",
        }
    payload = current_payload or {}
    episode = CognitiveEpisode(
        episode_id=_episode_id(message, history),
        active_topic=active.get("topic"),
        active_entities=current_entities or active.get("entities", []),
        active_question=active.get("question"),
        active_answer=active.get("answer"),
        active_route=current_route or active.get("route"),
        active_wrs=payload.get("working_reasoning_set"),
        active_contradiction=payload.get("contradiction_analysis"),
        active_analogy=payload.get("analogy_analysis"),
        active_examples=_examples(active.get("answer", "")),
        active_limits=_limits(active.get("answer", "")),
        unresolved_questions=_unresolved(active.get("answer", "")),
        last_summary=active.get("summary") or _summary(active.get("question", ""), active.get("answer", "")),
        conversation_branch=branches,
        resolved_references=_resolved_refs(message, active),
        rejected_references=_rejected_refs(message, branches, active, explicit_change),
        episode_confidence=_episode_confidence(message, active, current_entities),
        turn_number=sum(1 for item in history if item.get("role") == "user") + 1,
    )
    return asdict(episode)


def resolve_working_memory_followup(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    history = history or []
    lower = _norm(message)
    if not history and any(term in lower for term in ("analogy", "evidence is missing", "information is missing", "what evidence", "what information")):
        return None
    episode = build_cognitive_episode(message, history)
    if _explicit_topic_change(message, {"topic": episode.get("active_topic")}):
        return None
    if not _is_followup(lower):
        return None
    topic = episode.get("active_topic")
    if not topic:
        return _payload(
            message,
            episode,
            "I can continue, but I need the topic or sentence you want me to build on.",
            confidence=0.62,
            resolved=False,
        )
    if "first" in lower or "earlier" in lower or "return to the first" in lower:
        branch = _branch_by_ordinal(episode.get("conversation_branch", []), 0)
        if branch:
            topic = branch.get("topic") or topic
            episode["active_topic"] = topic
            episode["active_question"] = branch.get("question")
            episode["active_answer"] = branch.get("answer")
    elif "second" in lower:
        branch = _branch_by_ordinal(episode.get("conversation_branch", []), 1)
        if branch:
            topic = branch.get("topic") or topic
            episode["active_topic"] = topic
            episode["active_question"] = branch.get("question")
            episode["active_answer"] = branch.get("answer")

    answer = _followup_answer(lower, topic, episode)
    return _payload(message, episode, answer, confidence=0.88, resolved=True)


def attach_episode(payload: dict[str, Any], message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    payload["cognitive_episode"] = build_cognitive_episode(
        message,
        history,
        current_route=str(payload.get("route") or ""),
        current_payload=payload,
    )
    return payload


def build_working_memory_episode_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _report_cases()
    results = []
    for case in cases:
        payload = resolve_working_memory_followup(case["message"], case["history"])
        answer = str((payload or {}).get("answer") or "")
        passed = bool(payload) and all(term in answer.lower() for term in case["terms"])
        results.append({
            "case_id": case["case_id"],
            "message": case["message"],
            "route": (payload or {}).get("route"),
            "passed": passed,
            "answer_preview": answer[:320],
            "episode": (payload or {}).get("cognitive_episode"),
        })
    accuracy = round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4)
    report = {
        "report": "RC2_WORKING_MEMORY_EPISODE",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases_tested": len(results),
        "followup_resolution_accuracy": accuracy,
        "episode_schema": list(asdict(CognitiveEpisode("", None, [], None, None, None)).keys()),
        "results": results,
        "safety": SAFETY,
        "recommendation": "PROCEED_ADVERSARIAL_BENCHMARK_EXPANSION_AFTER_MEMORY_CALIBRATION",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _norm(text: str) -> str:
    text = str(text or "").lower().replace("-", " ")
    return re.sub(r"\s+", " ", text).strip(" ?!.")


def _episode_id(message: str, history: list[dict[str, str]]) -> str:
    basis = json.dumps(history[-8:], sort_keys=True) + str(message)
    return "rc2-episode-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _entities(text: str) -> list[str]:
    lower = _norm(text)
    found = [topic for topic in KNOWN_TOPICS if topic in lower]
    if "respiration" in lower and "cellular respiration" not in found:
        found.append("cellular respiration")
    if "allergy" in lower and "allergies" not in found:
        found.append("allergies")
    if "feedback loop" in lower and "feedback loops" not in found:
        found.append("feedback loops")
    return list(dict.fromkeys(found))


def _branches(history: list[dict[str, str]]) -> list[dict[str, Any]]:
    branches = []
    turns = []
    current_user = None
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "")
        if role == "user":
            current_user = content
        elif role == "assistant" and current_user:
            turns.append((current_user, content))
            current_user = None
        elif role == "anchor":
            try:
                anchor = json.loads(content)
            except json.JSONDecodeError:
                continue
            branches.append({
                "topic": anchor.get("active_concept_name"),
                "entities": anchor.get("retrieved_concept_names", []),
                "question": anchor.get("last_user_question"),
                "answer": anchor.get("last_answer_summary", ""),
                "route": "anchor",
                "summary": anchor.get("last_answer_summary", ""),
            })
    for question, answer in turns:
        topic = _topic_from_question(question) or (_entities(question) or _entities(answer) or [None])[0]
        if not topic:
            continue
        branches.append({
            "topic": topic,
            "entities": _entities(question) or _entities(answer) or [topic],
            "question": question,
            "answer": answer,
            "route": _route_hint(answer),
            "summary": _summary(question, answer),
        })
    return _dedupe_branches(branches)[-16:]


def _dedupe_branches(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for branch in branches:
        key = (branch.get("topic"), branch.get("question"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(branch)
    return deduped


def _select_active_branch(message: str, branches: list[dict[str, Any]], current_entities: list[str]) -> dict[str, Any]:
    lower = _norm(message)
    if "first" in lower or "earlier" in lower or "return to the first" in lower:
        return _branch_by_ordinal(branches, 0) or (branches[-1] if branches else {})
    if "second" in lower:
        return _branch_by_ordinal(branches, 1) or (branches[-1] if branches else {})
    if current_entities:
        for branch in reversed(branches):
            if set(current_entities) & set(branch.get("entities", [])):
                return branch
    return branches[-1] if branches else {}


def _branch_by_ordinal(branches: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if 0 <= index < len(branches):
        return branches[index]
    return None


def _topic_from_question(text: str) -> str | None:
    lower = _norm(text)
    for topic in KNOWN_TOPICS:
        if topic in lower:
            return topic
    patterns = [
        r"what is (.+)",
        r"what are (.+)",
        r"tell me about (.+)",
        r"let'?s discuss (.+)",
        r"talk about (.+)",
        r"explain (.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            topic = match.group(1).strip(" .?!")
            if topic and not _is_followup(topic):
                return topic
    return None


def _route_hint(answer: str) -> str:
    lower = answer.lower()
    if "shared pattern" in lower or "where it breaks" in lower:
        return "analogy_analysis"
    if "classification:" in lower or "contradiction" in lower or "conflict" in lower:
        return "contradiction_analysis"
    if "blood pressure" in lower or "photosynthesis" in lower:
        return "developmental_concept_memory"
    return "session_history"


def _summary(question: str, answer: str) -> str:
    q = re.sub(r"\s+", " ", str(question or "")).strip()
    a = re.sub(r"\s+", " ", str(answer or "")).strip()
    return f"Question: {q[:140]} | Answer: {a[:260]}".strip()


def _examples(answer: str) -> list[str]:
    lines = [line.strip(" -") for line in str(answer or "").splitlines()]
    return [line for line in lines if "example" in line.lower()][:3]


def _limits(answer: str) -> list[str]:
    lower_lines = [line.strip(" -") for line in str(answer or "").splitlines()]
    return [line for line in lower_lines if any(term in line.lower() for term in ("break", "limit", "uncertain", "missing"))][:4]


def _unresolved(answer: str) -> list[str]:
    return [line.strip(" -") for line in str(answer or "").splitlines() if "?" in line][:3]


def _resolved_refs(message: str, active: dict[str, Any]) -> list[dict[str, str]]:
    lower = _norm(message)
    refs = [ref for ref in ("that", "this", "those", "it", "first", "second", "earlier", "analogy", "contradiction") if ref in lower]
    topic = str(active.get("topic") or "")
    return [{"reference": ref, "resolved_to": topic} for ref in refs if topic]


def _rejected_refs(message: str, branches: list[dict[str, Any]], active: dict[str, Any], explicit_change: bool) -> list[dict[str, str]]:
    if not explicit_change:
        return []
    active_topic = str(active.get("topic") or "")
    return [
        {"reference": str(branch.get("topic") or ""), "reason": "explicit_topic_change"}
        for branch in branches[-3:]
        if branch.get("topic") and branch.get("topic") != active_topic
    ]


def _explicit_topic_change(message: str, active: dict[str, Any]) -> bool:
    lower = _norm(message)
    if re.search(r"\b(that|this|those|it|earlier|first|second|analogy|contradiction)\b", lower):
        return False
    entities = _entities(message)
    if not entities:
        return False
    active_topic = str(active.get("topic") or "").lower()
    if not active_topic:
        return False
    return not any(entity in active_topic or active_topic in entity for entity in entities)


def _episode_confidence(message: str, active: dict[str, Any], entities: list[str]) -> float:
    if _is_followup(_norm(message)) and active.get("topic"):
        return 0.9
    if entities:
        return 0.84
    if active.get("topic"):
        return 0.7
    return 0.35


def _is_followup(lower: str) -> bool:
    if lower in FOLLOWUP_FORMS:
        return True
    if lower.startswith("return to "):
        return True
    return bool(re.search(r"\b(that|this|those|it|first one|second one|earlier)\b", lower))


def _followup_answer(lower: str, topic: str, episode: dict[str, Any]) -> str:
    answer = str(episode.get("active_answer") or "")
    entities = [entity for entity in _entities(lower) if entity != topic]
    if ("relate" in lower or "connect" in lower) and entities:
        target = entities[0]
        return (
            f"Continuing with {topic}: the relation to {target} is that the earlier topic supplies the active context, "
            f"while {target} changes what details matter next. I would compare the concrete facts for {topic} with the "
            f"concrete facts for {target}, then separate what is known from what still needs evidence."
        )
    if "example" in lower:
        return _example_answer(topic, answer)
    if "simpl" in lower:
        return f"Put simply: we are still talking about {topic}. The key idea is { _plain_key_point(topic, answer) }"
    if "break" in lower and (episode.get("active_route") == "analogy_analysis" or "analogy" in lower):
        limits = episode.get("active_limits") or []
        limit = limits[0] if limits else f"the analogy is useful only for structure; {topic} should not be treated as physically identical to the comparison target."
        return f"The analogy breaks here: {limit}"
    if "evidence" in lower or "supports" in lower:
        return f"For {topic}, the current support is the recent local answer plus approved substrate concepts from this conversation. What is still missing is stronger source-specific evidence if you want a firm conclusion."
    if "what changed" in lower:
        return f"What changed is the conversational focus: I am carrying forward {topic} from the recent episode instead of starting a new retrieval path."
    if "what else" in lower:
        return f"Still on {topic}: the next useful angle is context, limits, and what evidence would make the answer stronger."
    if topic == "allergies" and "context" in lower:
        return "Continuing with allergies: allergies involve immune responses to allergens, and clinical context matters because exposure, severity, symptoms, medication history, and timing change what conclusion is justified."
    return f"Continuing with {topic}: {_plain_key_point(topic, answer)}"


def _plain_key_point(topic: str, answer: str) -> str:
    clean = re.sub(r"\s+", " ", str(answer or "")).strip()
    if clean:
        sentence = re.split(r"(?<=[.!?])\s+", clean)[0]
        if len(sentence.split()) >= 5:
            return sentence[0].lower() + sentence[1:]
    return f"the important part is how {topic} fits the current question."


def _example_answer(topic: str, answer: str) -> str:
    if "blood pressure" in topic:
        return "For example, if we are discussing blood pressure, a clinician would care whether a reading happened during stress, rest, exercise, or medication exposure."
    if "photosynthesis" in topic:
        return "For example, a plant leaf can capture light energy and store it in sugars that later support cellular work."
    if "analogy" in answer.lower() or "battery" in answer.lower():
        return "For example, photosynthesis is like charging only in the broad sense that energy is captured and stored for later use."
    return f"For example, with {topic}, I would keep the same topic active and add a concrete case rather than jumping to a new concept."


def _payload(message: str, episode: dict[str, Any], answer: str, *, confidence: float, resolved: bool) -> dict[str, Any]:
    episode = dict(episode)
    episode["episode_confidence"] = confidence
    return {
        "route": "session_memory",
        "answer": answer,
        "confidence": "ephemeral_cognitive_episode" if resolved else "needs_context",
        "confidence_score": confidence,
        "selected_model_lane": {"lane": "conversation_memory", "display_name": "Conversation Memory"},
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "cognitive_episode": episode,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _report_cases() -> list[dict[str, Any]]:
    blood_history = [
        {"role": "user", "content": "What is blood pressure?"},
        {"role": "assistant", "content": "Blood pressure is the force exerted by circulating blood against artery walls."},
    ]
    branch_history = [
        {"role": "user", "content": "Let's discuss photosynthesis."},
        {"role": "assistant", "content": "Photosynthesis stores light energy in chemical bonds."},
        {"role": "user", "content": "Now switch to planning."},
        {"role": "assistant", "content": "Planning organizes actions toward goals."},
        {"role": "user", "content": "Talk about allergies."},
        {"role": "assistant", "content": "Allergies involve immune responses to allergens."},
    ]
    analogy_history = [
        {"role": "user", "content": "How is photosynthesis like charging a battery?"},
        {"role": "assistant", "content": "The shared pattern is energy input, conversion, storage, and later use. Where it breaks: photosynthesis is biochemical and a battery is electrochemical."},
    ]
    return [
        {"case_id": "tell_more", "message": "Tell me more.", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "why", "message": "Why?", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "example", "message": "Give an example.", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "relate", "message": "How does that relate to allergies?", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "return_first", "message": "Return to the first topic.", "history": branch_history, "terms": ("photosynthesis",)},
        {"case_id": "analogy_break", "message": "Where does that analogy break?", "history": analogy_history, "terms": ("break",)},
    ]


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Working Memory + Cognitive Episode",
        "",
        f"Created: {report['created_at']}",
        f"Cases tested: {report['cases_tested']}",
        f"Follow-up resolution accuracy: {report['followup_resolution_accuracy']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Cases",
        "",
    ]
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['case_id']}",
            f"- Message: {item['message']}",
            f"- Route: {item['route']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_working_memory_episode_report(write_reports=True)
    print(json.dumps({
        "cases_tested": report["cases_tested"],
        "followup_resolution_accuracy": report["followup_resolution_accuracy"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

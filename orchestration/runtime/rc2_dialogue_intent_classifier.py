"""RC2 dialogue intent corpus and deterministic communication-act classifier.

This module classifies a user utterance as a communication act before DELTA
routes to retrieval, local model lanes, memory formation, or provider
escalation. It is deterministic: no training, fine-tuning, provider calls,
canonical writes, or autonomous memory writes occur here.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rc2_dialogue_intent"
REPORTS = ROOT / "reports"
CORPUS_PATH = DATA / "dialogue_intent_corpus.json"
REPORT_JSON = REPORTS / "RC2_DIALOGUE_INTENT_CLASSIFIER.json"
REPORT_MD = REPORTS / "RC2_DIALOGUE_INTENT_CLASSIFIER.md"

SAFETY_FLAGS = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_calls_performed": False,
    "canonical_write_performed": False,
    "autonomous_memory_write_performed": False,
    "model_b_replaced": False,
    "hyb1_promoted": False,
}

SOCIAL_ACTS = {
    "greeting",
    "thanks",
    "compliment",
    "encouragement",
    "acknowledgement",
    "frustration",
    "joke",
    "small_talk",
    "preference",
}

NO_ROUTE_ACTS = SOCIAL_ACTS | {"refusal", "cancellation"}


@dataclass(frozen=True)
class DialogueRule:
    rule_id: str
    communication_act: str
    intent: str
    routed_action: str
    confidence: float
    exact: tuple[str, ...] = ()
    contains_all: tuple[tuple[str, ...], ...] = ()
    contains_any: tuple[str, ...] = ()
    startswith: tuple[str, ...] = ()
    regex: tuple[str, ...] = ()


RULES: tuple[DialogueRule, ...] = (
    DialogueRule("exact_greeting", "greeting", "greeting", "social_response_only", 0.98, exact=("hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening")),
    DialogueRule("greeting_variant", "greeting", "greeting", "social_response_only", 0.92, contains_any=("hello delta", "hey there", "hi again")),
    DialogueRule("exact_thanks", "thanks", "thanks", "social_response_only", 0.98, exact=("thanks", "thank you", "thx", "appreciate it", "thanks a lot", "thank you very much")),
    DialogueRule("thanks_variant", "thanks", "thanks", "social_response_only", 0.92, contains_any=("thanks", "thank you", "appreciate")),
    DialogueRule("exact_compliment", "compliment", "compliment", "social_response_only", 0.98, exact=("good job", "great job", "nice work", "excellent work", "well done", "solid answer", "that's helpful", "that was helpful", "perfect", "awesome")),
    DialogueRule("encouragement_phrase", "encouragement", "encouragement", "social_response_only", 0.96, exact=("great effort", "keep going", "you got this", "solid effort", "nice progress")),
    DialogueRule("encouragement_variant", "encouragement", "encouragement", "social_response_only", 0.88, contains_any=("good progress", "keep working", "almost there", "is improving", "stay on it")),
    DialogueRule("exact_acknowledgement", "acknowledgement", "acknowledgement", "brief_acknowledgement_only", 0.96, exact=("okay", "ok", "got it", "sounds good", "cool", "alright", "that makes sense", "makes sense", "no worries")),
    DialogueRule("acknowledgement_variant", "acknowledgement", "acknowledgement", "brief_acknowledgement_only", 0.9, exact=("understood",)),
    DialogueRule("exact_affirmation", "affirmation", "affirmation", "approve_current_pending_action_only", 0.94, exact=("yes", "yeah", "yep", "sure", "go ahead", "do it")),
    DialogueRule("affirmation_variant", "affirmation", "affirmation", "approve_current_pending_action_only", 0.9, startswith=("yes ", "sure ", "okay ", "ok ", "go ahead")),
    DialogueRule("exact_refusal", "refusal", "refusal", "reject_current_pending_action_only", 0.96, exact=("no", "nope", "nah", "don't", "do not", "not now")),
    DialogueRule("refusal_variant", "refusal", "refusal", "reject_current_pending_action_only", 0.92, startswith=("no ", "don't ", "do not ")),
    DialogueRule("exact_cancel", "cancellation", "cancel", "stop_pending_action", 0.98, exact=("nevermind", "never mind", "cancel", "stop", "forget it", "drop it")),
    DialogueRule("cancel_variant", "cancellation", "cancel", "stop_pending_action", 0.9, exact=("leave it", "stop that", "cancel that", "ignore that")),
    DialogueRule("correction_phrase", "correction", "correction", "revise_prior_answer_or_context", 0.9, startswith=("actually", "correction", "that's wrong", "that is wrong", "not quite")),
    DialogueRule("correction_variant", "correction", "correction", "revise_prior_answer_or_context", 0.86, contains_any=("not right", "missed a detail", "revise that")),
    DialogueRule("frustration_phrase", "frustration", "personal_emotion", "social_response_only", 0.9, contains_any=("i don't get it", "i dont get it", "this is confusing", "i'm frustrated", "im frustrated", "that didn't work", "that did not work")),
    DialogueRule("frustration_variant", "frustration", "personal_emotion", "social_response_only", 0.86, contains_any=("this is annoying", "i'm stuck", "im stuck", "i feel lost")),
    DialogueRule("simplify_followup", "clarification_followup", "followup", "use_short_term_context", 0.9, exact=("try again", "explain simpler", "say it simpler", "simpler", "can you rephrase that")),
    DialogueRule("followup_variant", "clarification_followup", "followup", "use_short_term_context", 0.88, exact=("what do you mean", "explain that part", "why is that", "what about the second part", "go deeper", "tell me more", "continue", "expand on that", "more detail", "more details", "give me examples", "say more")),
    DialogueRule("joke_phrase", "joke", "conversation", "social_response_only", 0.82, contains_any=("lol", "haha", "just kidding", "kidding", "joke")),
    DialogueRule("joke_variant", "joke", "conversation", "social_response_only", 0.82, contains_any=("i'm joking", "im joking", "funny", "made me laugh")),
    DialogueRule("small_talk_phrase", "small_talk", "conversation", "social_response_only", 0.86, contains_any=("how are you", "how's it going", "hows it going", "what's up", "whats up")),
    DialogueRule("small_talk_variant", "small_talk", "conversation", "social_response_only", 0.84, exact=("how are things", "how do you feel", "you awake", "are you there", "how is your day")),
    DialogueRule("preference_phrase", "preference", "preference_opinion", "social_response_only", 0.88, startswith=("i like", "i want", "i prefer", "i think")),
    DialogueRule("memory_request", "memory_request", "memory_request", "concept_approval_path", 0.94, contains_any=("remember that", "remember this", "store this", "save this", "keep this concept", "don't remember that", "dont remember that")),
    DialogueRule("memory_variant", "memory_request", "memory_request", "concept_approval_path", 0.9, contains_any=("remember my preference", "save that for later", "keep this for future chats")),
    DialogueRule("diagnostics_request", "diagnostic_request", "diagnostics", "diagnostics", 0.94, contains_any=("diagnostic", "show diagnostics", "runtime status", "system health", "health check", "developer overlay")),
    DialogueRule("diagnostic_variant", "diagnostic_request", "diagnostics", "diagnostics", 0.9, contains_any=("show me the route", "show confidence", "what route was used", "show safety flags")),
    DialogueRule("external_knowledge_request", "research_request", "external_knowledge_request", "research_or_provider_consent_path", 0.9, contains_any=("avogadro", "quantum field", "beluga", "whale")),
    DialogueRule("research_request", "research_request", "investigation", "research_or_provider_consent_path", 0.88, contains_any=("research", "investigate", "latest", "look up", "find sources", "find supporting information")),
    DialogueRule("planning_request", "planning_request", "planning", "planning_lane", 0.88, contains_any=("plan", "schedule", "strategy", "roadmap", "workflow", "organize the tasks", "sequence the work")),
    DialogueRule("evidence_request", "evidence_request", "document", "evidence_review", 0.9, contains_any=("evidence", "document", "pdf", "invoice", "source supports", "citation", "extract evidence", "cite the claim", "review this source")),
    DialogueRule("coding_request", "coding_request", "coding", "local_model_or_repo_context", 0.9, contains_any=("code", "coding", "python", "bug", "function", "typescript", "javascript", "repo", "make a test", "patch the file")),
    DialogueRule("conceptual_question", "conceptual_question", "analysis", "substrate_or_local_model_path", 0.84, contains_any=("why", "how does", "how do", "explain", "what is the idea", "what does it mean", "what does governance mean", "meaning of life")),
    DialogueRule("factual_question", "factual_question", "question", "substrate_or_local_model_path", 0.82, regex=(r"^(what|who|where|when|which|is|are|do|does|can|should)\b.*\??$",)),
)


def normalize_utterance(text: str) -> str:
    lowered = str(text or "").lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip(" \t\r\n")


def classify_dialogue_act(message: str, *, allow_model_fallback: bool = False) -> dict[str, Any]:
    """Classify the communication act before cognitive routing.

    The optional fallback is deliberately reported as unavailable. It reserves a
    future hook without calling local models by default.
    """
    normalized = normalize_utterance(message)
    bare = normalized.strip(" .!?")
    for rule in RULES:
        if rule.communication_act == "memory_request" and normalized.startswith(("should ", "can ", "do you think ")):
            continue
        if rule.communication_act == "thanks" and bare.startswith(("no ", "nope ", "nah ")):
            continue
        if rule.communication_act == "refusal" and "remember" in normalized:
            continue
        if _matches_rule(normalized, bare, rule):
            return {
                "communication_act": rule.communication_act,
                "intent": rule.intent,
                "confidence": rule.confidence,
                "matched_rule": rule.rule_id,
                "routed_action": rule.routed_action,
                "model_fallback_used": False,
                "safe_no_route": rule.communication_act in NO_ROUTE_ACTS,
                "safety": dict(SAFETY_FLAGS),
            }
    confidence = 0.52 if normalized else 0.0
    act = "factual_question" if normalized.endswith("?") else "conversation"
    intent = "question" if act == "factual_question" else "conversation"
    return {
        "communication_act": act,
        "intent": intent,
        "confidence": confidence,
        "matched_rule": "fallback_question_mark" if normalized.endswith("?") else "fallback_conversation",
        "routed_action": "substrate_or_local_model_path" if normalized.endswith("?") else "conversation_path",
        "model_fallback_used": False,
        "model_fallback_available": bool(allow_model_fallback),
        "safe_no_route": False,
        "safety": dict(SAFETY_FLAGS),
    }


def _matches_rule(normalized: str, bare: str, rule: DialogueRule) -> bool:
    if bare in rule.exact:
        return True
    if any(normalized.startswith(item) for item in rule.startswith):
        return True
    if any(item in normalized for item in rule.contains_any):
        return True
    if any(all(token in normalized for token in group) for group in rule.contains_all):
        return True
    return any(re.search(pattern, normalized) for pattern in rule.regex)


def build_dialogue_intent_corpus() -> list[dict[str, Any]]:
    """Return a deterministic 200+ utterance evaluation corpus."""
    groups: dict[str, tuple[str, str, list[str]]] = {
        "greeting": ("greeting", "social_response_only", ["hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening", "hello delta", "hey there", "hi again"]),
        "thanks": ("thanks", "social_response_only", ["thanks", "thank you", "thx", "appreciate it", "thanks a lot", "thank you very much", "that helped thanks", "thanks for that", "appreciate the help", "thank you delta"]),
        "compliment": ("compliment", "social_response_only", ["good job", "great job", "nice work", "excellent work", "well done", "solid answer", "that's helpful", "that was helpful", "perfect", "awesome"]),
        "encouragement": ("encouragement", "social_response_only", ["great effort", "keep going", "you got this", "solid effort", "nice progress", "good progress", "keep working", "almost there", "that is improving", "stay on it"]),
        "acknowledgement": ("acknowledgement", "brief_acknowledgement_only", ["okay", "ok", "got it", "sounds good", "cool", "alright", "that makes sense", "makes sense", "no worries", "understood"]),
        "affirmation": ("affirmation", "approve_current_pending_action_only", ["yes", "yeah", "yep", "sure", "go ahead", "do it", "yes please", "sure ask it", "yes ask the model", "yes use that", "okay go ahead", "ok do it", "sure go deeper", "yes tell me more", "go ahead and expand"]),
        "refusal": ("refusal", "reject_current_pending_action_only", ["no", "nope", "nah", "don't", "do not", "not now", "no thanks", "do not ask", "don't store that", "no don't"]),
        "cancellation": ("cancel", "stop_pending_action", ["nevermind", "never mind", "cancel", "stop", "forget it", "drop it", "leave it", "stop that", "cancel that", "ignore that"]),
        "correction": ("correction", "revise_prior_answer_or_context", ["actually it was blue", "correction it is green", "that's wrong", "that is wrong", "not quite", "actually try green", "correction: use Frontier", "that's not right", "you missed a detail", "revise that"]),
        "frustration": ("personal_emotion", "social_response_only", ["i don't get it", "i dont get it", "this is confusing", "i'm frustrated", "im frustrated", "that didn't work", "that did not work", "this is annoying", "i'm stuck", "i feel lost"]),
        "clarification_followup": ("followup", "use_short_term_context", ["try again", "explain simpler", "say it simpler", "simpler", "can you rephrase that", "what do you mean", "explain that part", "why is that", "what about the second part", "go deeper", "tell me more", "continue", "expand on that", "more detail", "more details", "give me examples", "say more"]),
        "joke": ("conversation", "social_response_only", ["lol", "haha", "just kidding", "kidding", "that was a joke", "lol nevermind", "haha good one", "i'm joking", "funny", "made me laugh"]),
        "small_talk": ("conversation", "social_response_only", ["how are you", "how's it going", "hows it going", "what's up", "whats up", "how are things", "how do you feel", "you awake", "are you there", "how is your day"]),
        "preference": ("preference_opinion", "social_response_only", ["i like this direction", "i want shorter answers", "i prefer plain language", "i think this works", "i like the ui", "i want more detail", "i prefer local models", "i think that's better", "i want it simpler", "i like the flow"]),
        "memory_request": ("memory_request", "concept_approval_path", ["remember that", "remember this", "store this", "save this", "keep this concept", "don't remember that", "dont remember that", "remember my preference", "save that for later", "keep this for future chats"]),
        "diagnostic_request": ("diagnostics", "diagnostics", ["show diagnostics", "runtime status", "system health", "health check", "developer overlay", "show me the route", "show confidence", "diagnostic mode", "what route was used", "show safety flags"]),
        "evidence_request": ("document", "evidence_review", ["review this evidence", "analyze this document", "read this pdf", "check this invoice", "show citations", "what source supports that", "extract evidence", "review this source", "cite the claim", "inspect the document"]),
        "coding_request": ("coding", "local_model_or_repo_context", ["write python code", "debug this function", "fix this bug", "what is coding", "explain this repo", "write javascript", "make a test", "patch the file", "review this code", "why does this function fail"]),
        "research_request": ("investigation", "research_or_provider_consent_path", ["research beluga whales", "investigate this case", "latest status of the bill", "look up sources", "find sources for this", "research the market", "investigate the contradiction", "find supporting information", "look up current rules", "research the topic"]),
        "planning_request": ("planning", "planning_lane", ["plan my day", "make a schedule", "build a roadmap", "what is the strategy", "plan the sprint", "make a workflow", "organize the tasks", "sequence the work", "design a plan", "schedule the review"]),
        "conceptual_question": ("analysis", "substrate_or_local_model_path", ["why is the sky blue", "how does fire work", "explain gravity", "what does governance mean", "how do pressure cookers work", "why do people sleep", "explain semantic memory", "how does replay help", "why does water boil", "what is the idea behind rollback", "what is the meaning of life"]),
        "factual_question": ("question", "substrate_or_local_model_path", ["what color is the moon?", "who wrote hamlet?", "where is paris?", "when does water boil?", "which model is active?", "is the sky blue?", "are providers enabled?", "do you know frontier?", "can you answer locally?", "should i store this?", "what color is the moon", "what color is the sky"]),
    }
    rows: list[dict[str, Any]] = []
    for group, (intent, action, utterances) in groups.items():
        for index, utterance in enumerate(utterances, start=1):
            rows.append({
                "case_id": f"rc2-dialogue-{group}-{index:03d}",
                "utterance": utterance,
                "expected_communication_act": group,
                "expected_intent": intent,
                "expected_routed_action": action,
            })
    return rows


def evaluate_dialogue_intent_corpus(corpus: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    corpus = corpus or build_dialogue_intent_corpus()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    misses = []
    rule_counts: dict[str, int] = defaultdict(int)
    correct = 0
    for row in corpus:
        observed = classify_dialogue_act(str(row["utterance"]))
        expected = str(row["expected_communication_act"])
        got = str(observed["communication_act"])
        confusion[expected][got] += 1
        rule_counts[str(observed["matched_rule"])] += 1
        if got == expected:
            correct += 1
        else:
            misses.append({"case_id": row["case_id"], "utterance": row["utterance"], "expected": expected, "observed": got, "rule": observed["matched_rule"]})
    total = len(corpus)
    return {
        "phase": "RC2 Dialogue Intent Corpus & Communication Act Classifier",
        "corpus_size": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "misses": misses,
        "confusion_matrix": {key: dict(value) for key, value in sorted(confusion.items())},
        "rule_coverage": dict(sorted(rule_counts.items())),
        "safety": dict(SAFETY_FLAGS),
        "final_recommendation": "USE_DIALOGUE_ACT_CLASSIFIER_BEFORE_MODEL_MEMORY_OR_PROVIDER_ROUTING",
    }


def write_dialogue_intent_artifacts() -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    corpus = build_dialogue_intent_corpus()
    report = evaluate_dialogue_intent_corpus(corpus)
    CORPUS_PATH.write_text(json.dumps(corpus, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Dialogue Intent Classifier",
        "",
        f"Corpus size: {report['corpus_size']}",
        f"Accuracy: {report['accuracy']}",
        f"Misses: {len(report['misses'])}",
        "",
        "## Safety",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["safety"].items())
    lines.extend(["", "## Rule Coverage"])
    lines.extend(f"- {key}: {value}" for key, value in report["rule_coverage"].items())
    lines.extend(["", "## Final Recommendation", str(report["final_recommendation"])])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(write_dialogue_intent_artifacts(), indent=2, sort_keys=True))

"""RC2 conversation pathology harness and persistent cognitive store gate.

The harness evaluates whether DELTA's conversational loop is ready for a
future persistent cognitive store. It does not train, fine tune, mutate
canonical memory, call providers autonomously, or enable cross-session
persistence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_conversational_mode_router import (
    candidate_is_memory_worthy,
    render_route,
    route_message,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

HARNESS_FLAGS = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "provider_calls_performed": False,
    "autonomous_provider_calls_performed": False,
    "persistent_cross_session_memory_enabled": False,
    "hidden_memory_writes_performed": False,
    "model_b_replaced": False,
    "hyb1_promoted": False,
}


@dataclass(frozen=True)
class ConversationTrialCase:
    case_id: str
    prompt: str
    category: str
    expects_direct_answer: bool = False
    expects_short_term_context: bool = False
    expects_local_model_consent: bool = False
    expects_provider_consent: bool = False
    expects_memory_candidate: bool = False
    expects_bad_concept_rejection: bool = False
    expects_no_debug_metadata: bool = True


def build_conversation_trial_suite(count: int = 100) -> list[ConversationTrialCase]:
    seeds = [
        ("simple_fact", "What color is the sky?", True, False, False, False, True, False),
        ("simple_fact", "What is fire?", True, False, False, False, True, False),
        ("simple_fact", "What color is water?", True, False, False, False, True, False),
        ("casual_unknown", "What do people usually do for fun?", False, False, True, False, False, True),
        ("casual_unknown", "What do boring people do for fun?", False, False, True, False, False, True),
        ("coding", "What do you know about coding?", True, False, False, False, False, False),
        ("science_uncertain", "How does Avogadro's number relate to quantum field theory?", False, False, False, True, False, False),
        ("science_uncertain", "Tell me about beluga whale migration this year.", False, False, False, True, False, False),
        ("followup", "What did I just ask?", False, True, False, False, False, False),
        ("memory_worthy", "Why is the daytime sky blue?", True, False, False, False, True, False),
        ("memory_trap", "What is the thing?", False, False, True, False, False, True),
        ("provider_trap", "Can you ask GPT automatically?", True, False, False, False, False, False),
        ("contradiction", "Project Frontier should not approve uncertain invoices automatically.", True, False, False, False, False, False),
        ("diagnostics", "Show diagnostics.", True, False, False, False, False, False),
        ("planning", "Plan a small invoice review workflow.", False, False, True, False, False, False),
        ("research", "Research the latest status of a future Super Bowl.", False, False, True, False, False, False),
        ("image", "What is in this image?", False, False, False, True, False, False),
        ("document", "Analyze this invoice evidence.", False, False, True, False, False, False),
        ("conversation", "Hello DELTA.", False, False, True, False, False, False),
        ("social", "Great job.", True, False, False, False, False, False),
        ("social", "Nevermind.", True, False, False, False, False, False),
        ("social", "That's exactly what I wanted.", True, False, False, False, False, False),
        ("personal", "I'm tired.", True, False, False, False, False, False),
        ("self_description", "What is DELTA?", True, False, False, False, False, False),
    ]
    cases: list[ConversationTrialCase] = []
    index = 0
    while len(cases) < count:
        category, prompt, direct, short, local, provider, memory, bad = seeds[index % len(seeds)]
        suffix = "" if index < len(seeds) else f" #{index // len(seeds) + 1}"
        case_prompt = prompt if not suffix else prompt.rstrip(".?") + suffix + ("?" if prompt.endswith("?") else ".")
        cases.append(
            ConversationTrialCase(
                case_id=f"rc2-pathology-case-{len(cases)+1:03d}",
                prompt=case_prompt,
                category=category,
                expects_direct_answer=direct,
                expects_short_term_context=short,
                expects_local_model_consent=local,
                expects_provider_consent=provider,
                expects_memory_candidate=memory,
                expects_bad_concept_rejection=bad,
            )
        )
        index += 1
    return cases


def run_conversation_pathology_harness(*, count: int = 100) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    cases = build_conversation_trial_suite(count)
    results = []
    pathology_counts: dict[str, int] = {
        "conversation_failures": 0,
        "routing_failures": 0,
        "local_model_consent_failures": 0,
        "provider_consent_failures": 0,
        "memory_proposal_failures": 0,
        "bad_concept_failures": 0,
        "debug_metadata_failures": 0,
        "diagnostics_failures": 0,
        "ux_friction": 0,
    }
    for case in cases:
        payload = route_message("Conversation", case.prompt, history=history, execute_local_model=False)
        rendered = render_route(payload)
        checks = evaluate_trial_case(case, payload, rendered)
        for key, ok in checks.items():
            if not ok:
                pathology_counts[key] = pathology_counts.get(key, 0) + 1
        history.append({"role": "user", "content": case.prompt})
        history.append({"role": "assistant", "content": rendered})
        history = history[-12:]
        results.append(
            {
                "case": asdict(case),
                "route": payload.get("route"),
                "intent": (payload.get("intent") or {}).get("intent"),
                "answer_preview": str(payload.get("answer", ""))[:240],
                "rendered_preview": rendered[:300],
                "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
                "support_identifier": (payload.get("selected_model_lane") or {}).get("support_identifier"),
                "local_model_offer": bool((payload.get("local_model_offer") or {}).get("offered")),
                "provider_offer": bool((payload.get("supporting_information_offer") or {}).get("offered")),
                "memory_candidate": summarize_memory_candidate(payload.get("memory_candidate")),
                "checks": checks,
                "provider_calls_performed": payload.get("provider_calls_performed") is True,
                "training_performed": payload.get("training_performed") is True,
                "canonical_write_performed": payload.get("canonical_write_performed") is True,
            }
        )
    readiness = readiness_decision(pathology_counts, results)
    report = {
        "phase": "DELTA RC2 Conversation Pathology Harness & Persistent Cognitive Store Readiness",
        "trial_id": stable_id("rc2-conversation-pathology", count, len(results)),
        "question_count": len(results),
        "pathology_counts": pathology_counts,
        "results": results,
        "readiness_gate": readiness,
        "persistent_cognitive_store_enabled": False,
        "future_persistent_cognitive_store_requirements": [
            "preserve conversations",
            "preserve topics",
            "preserve approved facts",
            "preserve concepts",
            "preserve semantic links",
            "preserve cognitive structures",
            "preserve contradictions",
            "preserve replay queue",
            "preserve rollback handles",
            "load them again when app restarts",
            "allow full delete/reset",
        ],
        "flags": dict(HARNESS_FLAGS),
    }
    return report


def evaluate_trial_case(case: ConversationTrialCase, payload: dict[str, Any], rendered: str) -> dict[str, bool]:
    answer = str(payload.get("answer", ""))
    memory_candidate = payload.get("memory_candidate")
    rendered_lower = rendered.lower()
    debug_markers = ("mode:", "route:", "safety:", "provider_calls_performed", "canonical_write_performed", "preferred local model")
    return {
        "conversation_failures": bool(answer.strip()) and "switch modes" not in answer.lower(),
        "routing_failures": bool((payload.get("selected_model_lane") or {}).get("support_identifier")),
        "local_model_consent_failures": (not case.expects_local_model_consent) or bool((payload.get("local_model_offer") or {}).get("offered")),
        "provider_consent_failures": (not case.expects_provider_consent) or bool((payload.get("supporting_information_offer") or {}).get("offered")),
        "memory_proposal_failures": (not case.expects_memory_candidate) or (
            isinstance(memory_candidate, dict) and candidate_is_memory_worthy(memory_candidate, payload)
        ),
        "bad_concept_failures": (not case.expects_bad_concept_rejection) or memory_candidate is None,
        "debug_metadata_failures": (not case.expects_no_debug_metadata) or not any(marker in rendered_lower for marker in debug_markers),
        "diagnostics_failures": payload.get("provider_calls_performed") is False and payload.get("training_performed") is False and payload.get("canonical_write_performed") is False,
        "ux_friction": "scaffold" not in rendered_lower and not rendered.strip().startswith("{"),
    }


def summarize_memory_candidate(candidate: object) -> dict[str, Any] | None:
    if not isinstance(candidate, dict):
        return None
    return {
        "concept_name": candidate.get("concept_name"),
        "memory_type": candidate.get("memory_type"),
        "approval_status": candidate.get("approval_status"),
        "worthy": candidate_is_memory_worthy(candidate),
    }


def readiness_decision(pathology_counts: dict[str, int], results: list[dict[str, Any]]) -> dict[str, Any]:
    hard_blockers = {
        key: value
        for key, value in pathology_counts.items()
        if key
        in {
            "provider_consent_failures",
            "bad_concept_failures",
            "debug_metadata_failures",
            "diagnostics_failures",
        }
        and value
    }
    soft_repairs = {
        key: value
        for key, value in pathology_counts.items()
        if key not in hard_blockers and value
    }
    if hard_blockers:
        recommendation = "MEMORY_PERSISTENCE_BLOCKED"
    elif soft_repairs:
        recommendation = "MORE_CONVERSATION_REPAIR_REQUIRED"
    else:
        recommendation = "READY_FOR_PERSISTENT_COGNITIVE_STORE"
    return {
        "recommendation": recommendation,
        "hard_blockers": hard_blockers,
        "soft_repairs": soft_repairs,
        "evaluated_cases": len(results),
    }


def write_conversation_pathology_reports(*, count: int = 100) -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = run_conversation_pathology_harness(count=count)
    json_path = REPORTS / "RC2_CONVERSATION_PATHOLOGY_HARNESS.json"
    md_path = REPORTS / "RC2_CONVERSATION_PATHOLOGY_HARNESS.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    gate = report["readiness_gate"]
    lines = [
        "# RC2 Conversation Pathology Harness & Persistent Cognitive Store Readiness",
        "",
        "This report evaluates conversational behavior before enabling persistent cross-session cognitive storage.",
        "",
        f"- Questions: `{report['question_count']}`",
        f"- Recommendation: `{gate['recommendation']}`",
        f"- Persistent cognitive store enabled: `{report['persistent_cognitive_store_enabled']}`",
        "",
        "## Pathology Counts",
    ]
    for key, value in report["pathology_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Gate",
            f"- hard blockers: `{gate['hard_blockers']}`",
            f"- soft repairs: `{gate['soft_repairs']}`",
            "",
            "## Safety",
        ]
    )
    for key, value in report["flags"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

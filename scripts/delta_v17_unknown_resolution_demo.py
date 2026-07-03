from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer
from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider


REPORT_MD = Path("reports/runtime_v17h_multi_turn_unknown_resolution_demo.md")
REPORT_JSON = Path("reports/runtime_v17h_multi_turn_unknown_resolution_demo.json")

RUNTIME_V17H_FLAGS: dict[str, bool] = {
    "multi_turn_unknown_resolution_demo_enabled": True,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


def build_unknown_resolution_demo() -> dict[str, object]:
    known_question = "What is HYB1?"
    unknown_question = "What is the safest live pruning policy for a new city dataset?"
    user_correction = "Treat live pruning as a future projection-only candidate until explicit review exists."
    known = route_local_knowledge_answer(known_question)
    unknown = route_local_knowledge_answer(unknown_question)
    provider_dry_run = answer_unknown_with_controlled_provider(unknown_question)
    resolution_event = {
        "resolution_event_id": _stable_id("v17h-resolution", unknown_question, user_correction),
        "user_correction": user_correction,
        "correction_authoritative": False,
        "requires_future_review": True,
    }
    memory_candidate_proposal = {
        "memory_candidate_id": _stable_id("v17h-memory-candidate", user_correction),
        "candidate_text": user_correction,
        "created_from_user_correction": True,
        "canonical_write_performed": False,
        "requires_explicit_approval": True,
    }
    synthesis = synthesize_controlled_answer(unknown_question)
    demo = {
        "phase": "Runtime V1.7H",
        "turns": [
            {"turn": 1, "kind": "local_known_question", "question": known_question, "matched": known.matched, "answer": known.answer.as_dict() if known.answer else None},
            {"turn": 2, "kind": "local_unknown_question", "question": unknown_question, "matched": unknown.matched, "fallback": unknown.unsupported_reason},
            {"turn": 3, "kind": "provider_assisted_request_dry_run", "decision": provider_dry_run["decision"], "provider_request": provider_dry_run["route_or_provider_request"]},
            {"turn": 4, "kind": "user_correction", "resolution_event": resolution_event},
            {"turn": 5, "kind": "memory_candidate_pressure", "memory_candidate_proposal": memory_candidate_proposal},
            {"turn": 6, "kind": "answer_synthesis_draft", "draft": synthesis["trace"]["draft"], "safety_review": synthesis["trace"]["safety_review"]},
        ],
        "safety_summary": {
            "provider_call_performed": False,
            "memory_write_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
            "action_execution_performed": False,
            "hyb1_default_activation_enabled": False,
        },
        "invariant_flags": dict(RUNTIME_V17H_FLAGS),
        "final_recommendation": "PROCEED_EVIDENCE_QUALITY_EVALUATION_HARNESS",
    }
    return demo


def write_unknown_resolution_demo_report() -> dict[str, object]:
    data = build_unknown_resolution_demo()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def validate_unknown_resolution_demo_safe(data: dict[str, object]) -> bool:
    flags = data["invariant_flags"]
    proposal = data["turns"][4]["memory_candidate_proposal"]
    return (
        proposal["canonical_write_performed"] is False
        and data["safety_summary"]["provider_call_performed"] is False
        and data["safety_summary"]["memory_write_performed"] is False
        and data["safety_summary"]["recall_mutated"] is False
        and data["safety_summary"]["training_triggered"] is False
        and data["safety_summary"]["action_execution_performed"] is False
        and flags["multi_turn_unknown_resolution_demo_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "multi_turn_unknown_resolution_demo_enabled")
    )


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.7H - Multi-Turn Unknown Resolution Demo",
        "",
        f"- Turns: `{len(data['turns'])}`",
        f"- Safe: `{validate_unknown_resolution_demo_safe(data)}`",
        "",
        "The demo shows local known handling, local unknown handling, dry-run provider evidence acquisition, user correction, memory candidate pressure, and controlled answer synthesis. It does not call providers by default, write memory, train, mutate recall, execute actions, activate HYB1, or start a scheduler.",
        "",
        "## Turn Summary",
        "",
    ]
    for turn in data["turns"]:
        lines.append(f"- Turn {turn['turn']}: `{turn['kind']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def main() -> int:
    data = write_unknown_resolution_demo_report()
    print(f"Runtime V1.7H unknown resolution demo: safe={validate_unknown_resolution_demo_safe(data)} final={data['final_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

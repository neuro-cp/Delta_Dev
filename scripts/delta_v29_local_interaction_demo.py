"""Run the Runtime V2.9 local interaction demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


REPORT_MD = ROOT / "reports/runtime_v29e_local_interaction_demo.md"
REPORT_JSON = ROOT / "reports/runtime_v29e_local_interaction_demo.json"


DEMO_QUESTIONS = [
    "What is DELTA?",
    "What can you do?",
    "What phase are you in?",
    "Describe your architecture.",
    "What is your replay and consolidation path?",
    "What is currently disabled?",
    "Can you train?",
    "Can you write memory?",
    "Is HYB1 active?",
    "What did I eat for breakfast yesterday?",
]


def build_demo() -> dict[str, object]:
    answers = [run_v29_local_answer(question) for question in DEMO_QUESTIONS]
    return {
        "phase": "Runtime V2.9E",
        "questions": DEMO_QUESTIONS,
        "answers": answers,
        "matched_count": sum(1 for answer in answers if answer["local_answer"]["matched"]),
        "unsupported_count": sum(1 for answer in answers if not answer["local_answer"]["matched"]),
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_SELF_DESCRIPTION_SAFETY_CHECKPOINT",
    }


def write_demo_report() -> dict[str, object]:
    data = build_demo()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"- {item['request']['query']}: {item['local_answer']['topic_id']}" for item in data["answers"])
    REPORT_MD.write_text(f"# Runtime V2.9E Local Interaction Demo\n\n{rows}\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def main() -> int:
    data = write_demo_report()
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

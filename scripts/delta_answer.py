from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer, write_v29_answer_report
from orchestration.runtime.v30_conversational_answer_formatter import (
    format_conversational_answer,
    infer_answer_mode,
)
from orchestration.runtime.v30_pipeline_explainer import build_pipeline_explanation
from orchestration.runtime.v31_local_learning_answer import is_v31_learning_question, run_v31_learning_answer
from orchestration.runtime.v39_local_kernel_answer import is_kernel_question, run_kernel_answer
from orchestration.runtime.arc_ii_local_answer import is_arc_ii_question, run_arc_ii_answer
from orchestration.runtime.arc_iii_local_answer import is_arc_iii_question, run_arc_iii_answer


def main() -> int:
    parser = argparse.ArgumentParser(description="DELTA local answer synthesis.")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--use-recall", action="store_true")
    parser.add_argument("--show-provenance", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-report", action="store_true")
    parser.add_argument("--mode", choices=("concise", "detailed", "explain", "safety-summary"))
    args = parser.parse_args()
    query = " ".join(args.query)
    if args.output_report:
        data = write_v29_answer_report()
    elif is_arc_iii_question(query):
        data = run_arc_iii_answer(query)
    elif is_arc_ii_question(query):
        data = run_arc_ii_answer(query)
    elif is_kernel_question(query):
        data = run_kernel_answer(query)
    elif is_v31_learning_question(query):
        data = run_v31_learning_answer(query)
    elif infer_answer_mode(query, args.mode) == "explain":
        data = build_pipeline_explanation(query, use_recall=args.use_recall)
    else:
        data = run_v29_local_answer(query, use_recall=args.use_recall)
    if args.json or args.show_provenance or args.output_report:
        print(json.dumps(data, indent=2))
    elif data.get("phase") == "Runtime ARC III":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC II":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC I V3.9":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime V3.1":
        print(data["answer_text"])
    elif "rendered_explanation" in data:
        print(data["rendered_explanation"])
    else:
        print(format_conversational_answer(data, mode=infer_answer_mode(query, args.mode)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

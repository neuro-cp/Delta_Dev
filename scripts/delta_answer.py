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
from orchestration.runtime.rc1_kernel_answer_envelope import wrap_local_answer_with_kernel_envelope
from orchestration.runtime.arc_ii_local_answer import is_arc_ii_question, run_arc_ii_answer
from orchestration.runtime.arc_iii_local_answer import is_arc_iii_question, run_arc_iii_answer
from orchestration.runtime.arc_iv_local_answer import is_arc_iv_question, run_arc_iv_answer
from orchestration.runtime.arc_vi_local_answer import is_arc_vi_question, run_arc_vi_answer
from orchestration.runtime.arc_vii_xxv_local_answer import (
    is_arc_vii_question,
    is_arc_viii_question,
    is_post_arc_deepening_question,
    is_runtime_completion_question,
    run_arc_vii_answer,
    run_arc_viii_answer,
    run_post_arc_deepening_answer,
    run_runtime_completion_answer,
)
from orchestration.runtime.ov2_cognitive_quality import is_ov2_question, answer_ov2_question
from orchestration.runtime.ov3_controlled_reasoning_vertical_slice import is_ov3_question, answer_ov3_question
from orchestration.runtime.ov4_readonly_activation_trial import is_ov4_question, answer_ov4_question
from orchestration.runtime.ov5_integrated_readonly_cognitive_trial import is_ov5_question, answer_ov5_question
from orchestration.runtime.ov6_ov10_operational_readiness import is_ov6_ov10_question, answer_ov6_ov10_question


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
    elif is_ov6_ov10_question(query):
        data = answer_ov6_ov10_question(query)
    elif is_ov5_question(query):
        data = answer_ov5_question(query)
    elif is_ov4_question(query):
        data = answer_ov4_question(query)
    elif is_ov3_question(query):
        data = answer_ov3_question(query)
    elif is_ov2_question(query):
        data = answer_ov2_question(query)
    elif is_runtime_completion_question(query):
        data = run_runtime_completion_answer(query)
    elif is_post_arc_deepening_question(query):
        data = run_post_arc_deepening_answer(query)
    elif is_arc_viii_question(query):
        data = run_arc_viii_answer(query)
    elif is_arc_vii_question(query):
        data = run_arc_vii_answer(query)
    elif is_arc_vi_question(query):
        data = run_arc_vi_answer(query)
    elif is_arc_iv_question(query):
        data = run_arc_iv_answer(query)
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
    if not args.output_report:
        data = wrap_local_answer_with_kernel_envelope(query, data)
    if args.json or args.show_provenance or args.output_report:
        print(json.dumps(data, indent=2))
    elif data.get("phase") == "Post-ARC XXV Runtime Architecture Completion":
        print(data["answer_text"])
    elif data.get("phase") == "Post-ARC XXV Runtime Deepening":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC VIII":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC VII":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC VI":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC IV":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC III":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC II":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime ARC I V3.9":
        print(data["answer_text"])
    elif data.get("phase") == "Runtime V3.1":
        print(data["answer_text"])
    elif data.get("phase") == "OV2 Cognitive Quality":
        print(data["answer_text"])
    elif data.get("phase") == "OV3 Controlled Reasoning Vertical Slice":
        print(data["answer_text"])
    elif data.get("phase") == "OV4 Operator-Reviewed Read-Only Activation Trial":
        print(data["answer_text"])
    elif data.get("phase") == "OV5 Integrated Read-Only Cognitive Runtime Trial":
        print(data["answer_text"])
    elif data.get("phase") == "OV6-OV10 Operational Readiness":
        print(data["answer_text"])
    elif "rendered_explanation" in data:
        print(data["rendered_explanation"])
    else:
        print(format_conversational_answer(data, mode=infer_answer_mode(query, args.mode)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

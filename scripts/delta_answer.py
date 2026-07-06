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
from orchestration.runtime.tp0_controlled_training_pilot import is_tp0_question, answer_tp0_question
from orchestration.runtime.tp1_generalization_pilot import is_tp1_question, answer_tp1_question
from orchestration.runtime.tp2_scientific_validation import is_tp2_question, answer_tp2_question
from orchestration.runtime.tp3_independent_verification_freeze import is_tp3_question, answer_tp3_question
from orchestration.runtime.tp4_controlled_persistent_pilot_design import is_tp4_question, answer_tp4_question
from orchestration.runtime.tp5_noncanonical_persistent_pilot import is_tp5_question, answer_tp5_question
from orchestration.runtime.tp6_controlled_operational_pilot import is_tp6_question, answer_tp6_question
from orchestration.runtime.tp7_longitudinal_stability import is_tp7_question, answer_tp7_question
from orchestration.runtime.tp8_canonical_promotion_policy import is_tp8_question, answer_tp8_question
from orchestration.runtime.tp9_controlled_canonical_pilot_design import is_tp9_question, answer_tp9_question
from orchestration.runtime.tp10_training_readiness_review import is_tp10_question, answer_tp10_question
from orchestration.runtime.tp11_governed_base_corpus import is_tp11_question, answer_tp11_question


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
    elif is_tp11_question(query):
        data = answer_tp11_question(query)
    elif is_tp10_question(query):
        data = answer_tp10_question(query)
    elif is_tp9_question(query):
        data = answer_tp9_question(query)
    elif is_tp8_question(query):
        data = answer_tp8_question(query)
    elif is_tp7_question(query):
        data = answer_tp7_question(query)
    elif is_tp6_question(query):
        data = answer_tp6_question(query)
    elif is_tp5_question(query):
        data = answer_tp5_question(query)
    elif is_tp4_question(query):
        data = answer_tp4_question(query)
    elif is_tp3_question(query):
        data = answer_tp3_question(query)
    elif is_tp2_question(query):
        data = answer_tp2_question(query)
    elif is_tp1_question(query):
        data = answer_tp1_question(query)
    elif is_tp0_question(query):
        data = answer_tp0_question(query)
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
    elif data.get("phase") == "TP0 Controlled Noncanonical Training Pilot":
        print(data["answer_text"])
    elif data.get("phase") == "TP1 Expanded Noncanonical Generalization Pilot":
        print(data["answer_text"])
    elif data.get("phase") == "TP2 Multi-Corpus Scientific Validation":
        print(data["answer_text"])
    elif data.get("phase") == "TP3 Independent Verification Freeze":
        print(data["answer_text"])
    elif data.get("phase") == "TP4 Controlled Persistent Pilot Design Review":
        print(data["answer_text"])
    elif data.get("phase") == "TP5 Controlled Noncanonical Persistent Pilot":
        print(data["answer_text"])
    elif data.get("phase") == "TP6 Controlled Operational Pilot":
        print(data["answer_text"])
    elif data.get("phase") == "TP7 Longitudinal Stability and Human Evaluation":
        print(data["answer_text"])
    elif data.get("phase") == "TP8 Canonical Promotion Policy Validation":
        print(data["answer_text"])
    elif data.get("phase") == "TP9 Controlled Canonical Pilot Design":
        print(data["answer_text"])
    elif data.get("phase") == "TP10 Training Readiness Review":
        print(data["answer_text"])
    elif data.get("phase") == "TP11 Governed Base Corpus and Shadow Training Readiness":
        print(data["answer_text"])
    elif "rendered_explanation" in data:
        print(data["rendered_explanation"])
    else:
        print(format_conversational_answer(data, mode=infer_answer_mode(query, args.mode)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

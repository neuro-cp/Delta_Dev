"""Manual RC1 validation script with no live capabilities."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.e2e_semantic_consolidation_cycle import run_cycle
from orchestration.runtime.rc1_activation_readiness import SAFETY_FLAGS, write_activation_readiness_reports
from orchestration.runtime.rc1_adversarial_validation import run_adversarial_validation
from orchestration.runtime.rc1_document_audit_slice import build_document_audit_slice
from orchestration.runtime.rc1_kernel_answer_envelope import wrap_local_answer_with_kernel_envelope
from orchestration.runtime.rc1_substrate_query_adapter import query_runtime_substrate
from orchestration.runtime.rc1_unified_review_state_machine import build_unified_lifecycle
from orchestration.runtime.rc1_vertical_integration import build_rc1_vertical_trace
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


def run_manual_validation() -> dict[str, object]:
    identity = wrap_local_answer_with_kernel_envelope("What is DELTA?", run_v29_local_answer("What is DELTA?"))
    kernel = build_rc1_vertical_trace()
    adversarial = run_adversarial_validation()
    document_audit = build_document_audit_slice()
    cycle = run_cycle()
    substrate = query_runtime_substrate("What did Project Atlas prove and what remains uncertain?")
    lifecycle = build_unified_lifecycle()
    readiness = write_activation_readiness_reports()
    checks = {
        "identity_runtime_status": identity["kernel_envelope"]["answer_text_preserved"] is True,
        "kernel_routing": bool(kernel["trace_steps"]),
        "current_state": all(value is False for key, value in SAFETY_FLAGS.items() if isinstance(value, bool)),
        "adversarial_summary": adversarial["failed_count"] == 0,
        "fixture_document_to_audit_trace": bool(document_audit["findings"]),
        "semantic_consolidation_cycle": bool(cycle["grounded_answer"]["answer"]),
        "read_only_substrate_query": substrate.query.read_only is True and substrate.mutating is False,
        "state_machine": lifecycle.current_state == "integrated_disabled" and lifecycle.mutation_performed is False,
        "rollback_simulation": bool(lifecycle.rollback_token),
        "grounded_answer_with_uncertainty": bool(cycle["grounded_answer"]["uncertainty"]),
        "activation_readiness_reports": readiness["matrix"]["recommended_first_activation_candidate"].startswith("fixture-only"),
    }
    prohibited = {
        "provider_call_performed": SAFETY_FLAGS["provider_call_performed"],
        "training_performed": SAFETY_FLAGS["training_performed"],
        "knowledge_mutation_performed": SAFETY_FLAGS["knowledge_mutation_performed"],
        "memory_mutation_performed": SAFETY_FLAGS["memory_mutation_performed"],
        "scheduler_started": SAFETY_FLAGS["scheduler_started"],
        "action_execution_performed": SAFETY_FLAGS.get("action_execution_performed", False),
    }
    return {
        "phase": "RC1 Manual Validation No Live Capabilities",
        "checks": checks,
        "passed": all(checks.values()) and all(value is False for value in prohibited.values()),
        "prohibited_capabilities": prohibited,
        "safety": SAFETY_FLAGS,
        "final_recommendation": "PROCEED_ACTIVATION_WAVE_0_REVIEW",
    }


def main() -> int:
    report = run_manual_validation()
    print("DELTA RC1 Manual Validation")
    for name, passed in report["checks"].items():
        print(f"- {name}: {'PASS' if passed else 'FAIL'}")
    print(f"final_recommendation={report['final_recommendation']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

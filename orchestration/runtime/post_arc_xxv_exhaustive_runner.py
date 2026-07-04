"""Master runner for exhaustive post-ARC XXV modules."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime import arc_07_investigation
from orchestration.runtime import arc_08_specialists
from orchestration.runtime import arc_09_external_evidence
from orchestration.runtime import arc_10_tool_provider_runtime
from orchestration.runtime import arc_11_controlled_integration
from orchestration.runtime import arc_12_evaluation_regression
from orchestration.runtime import arc_13_sleep_replay
from orchestration.runtime import arc_14_domain_packs
from orchestration.runtime import arc_15_executive_operations
from orchestration.runtime import arc_16_cognitive_os
from orchestration.runtime import arc_17_world_model
from orchestration.runtime import arc_18_multitime_memory
from orchestration.runtime import arc_19_self_model
from orchestration.runtime import arc_20_adaptive_executive
from orchestration.runtime import arc_21_multi_runtime_collaboration
from orchestration.runtime import arc_22_distributed_knowledge_fabric
from orchestration.runtime import arc_23_scientific_discovery
from orchestration.runtime import arc_24_cognitive_simulation
from orchestration.runtime import arc_25_continuous_runtime

MODULES = (
    arc_07_investigation,
    arc_08_specialists,
    arc_09_external_evidence,
    arc_10_tool_provider_runtime,
    arc_11_controlled_integration,
    arc_12_evaluation_regression,
    arc_13_sleep_replay,
    arc_14_domain_packs,
    arc_15_executive_operations,
    arc_16_cognitive_os,
    arc_17_world_model,
    arc_18_multitime_memory,
    arc_19_self_model,
    arc_20_adaptive_executive,
    arc_21_multi_runtime_collaboration,
    arc_22_distributed_knowledge_fabric,
    arc_23_scientific_discovery,
    arc_24_cognitive_simulation,
    arc_25_continuous_runtime,
)


def write_all_reports() -> dict[str, object]:
    reports = [module.write_report() for module in MODULES]
    summary = {
        "phase": "Post-ARC XXV Exhaustive Master Review",
        "module_count": len(MODULES),
        "arcs": [report["arc_label"] for report in reports],
        "reports": [report["title"] for report in reports],
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "provider_authority_granted": False,
        "autonomous_browsing_performed": False,
        "tool_execution_performed": False,
        "scheduler_started": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "final_recommendation": "PROCEED_EXHAUSTIVE_RUNTIME_REVIEW_AND_SELECTIVE_ACTIVATION_PLANNING",
    }
    Path("reports/runtime_post_arc_xxv_exhaustive_master_review.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    Path("reports/runtime_post_arc_xxv_exhaustive_master_review.md").write_text(render_summary(summary), encoding="utf-8")
    Path("docs/continuation_post_arc_xxv_exhaustive.md").write_text(render_continuation(summary), encoding="utf-8")
    return summary


def render_summary(summary: dict[str, object]) -> str:
    arcs = "\n".join(f"- {arc}" for arc in summary["arcs"])
    return f"""# Post-ARC XXV Exhaustive Master Review

Expanded ARC VII through ARC XXV from compressed scaffolds into dedicated,
testable runtime modules.

## Modules

{arcs}

## Safety

- Model B default: {summary['model_b_default']}
- HYB1: {summary['hyb1']}
- Training performed: {summary['training_performed']}
- Provider authority granted: {summary['provider_authority_granted']}
- Autonomous browsing performed: {summary['autonomous_browsing_performed']}
- Tool execution performed: {summary['tool_execution_performed']}
- Scheduler started: {summary['scheduler_started']}
- Memory mutation performed: {summary['memory_mutation_performed']}
- Knowledge mutation performed: {summary['knowledge_mutation_performed']}

Final recommendation: `{summary['final_recommendation']}`
"""


def render_continuation(summary: dict[str, object]) -> str:
    return (
        "# Post-ARC XXV Exhaustive Continuation\n\n"
        "ARC VII through ARC XXV now each have a dedicated runtime module, tests, docs, reports, and dashboard artifacts. "
        "The compressed master scaffold remains as compatibility context, but future work should prefer the dedicated modules.\n\n"
        "No training, provider authority, autonomous browsing, tool execution, scheduler activation, memory mutation, knowledge mutation, or HYB1 promotion occurred.\n\n"
        f"Final recommendation: `{summary['final_recommendation']}`.\n"
    )


if __name__ == "__main__":
    print(write_all_reports()["final_recommendation"])

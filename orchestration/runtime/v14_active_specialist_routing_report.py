from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_active_specialist_routing import (
    RUNTIME_V14N_INVARIANT_FLAGS,
    SpecialistRoutingRequestKind,
    create_specialist_provider_contract,
    create_specialist_routing_gate,
    create_specialist_routing_plan,
    create_specialist_routing_report_entry,
    create_specialist_routing_request,
    create_specialist_routing_trace,
    decide_specialist_routing,
)


REPORT_MD = Path("reports/runtime_v14n_active_specialist_routing_design.md")
REPORT_JSON = Path("reports/runtime_v14n_active_specialist_routing_design.json")


def build_active_specialist_routing_report_data() -> dict[str, object]:
    request = create_specialist_routing_request(
        request_kind=SpecialistRoutingRequestKind.EVIDENCE_GAP,
        question="What evidence is missing before routing to a specialist?",
        evidence_gap="future specialist routing requires an approval and authority boundary",
        lane_scope=("reasoning", "safety"),
        source_trace_ids=("answer-trace-demo",),
    )
    gate = create_specialist_routing_gate(request.request_id)
    contract = create_specialist_provider_contract(
        specialist_type=request.preferred_specialist,
        allowed_input_kinds=(request.request_kind,),
    )
    decision = decide_specialist_routing(request, gate, contract)
    trace = create_specialist_routing_trace(request, gate, contract, decision)
    plan = create_specialist_routing_plan(requests=(request,), decisions=(decision,), traces=(trace,))
    entry = create_specialist_routing_report_entry(
        trace=trace,
        request=request,
        gate=gate,
        contract=contract,
        decision=decision,
        unresolved_gaps=(
            "human approval UI is not implemented",
            "provider contract execution is not implemented",
            "merge protocol integration remains dormant",
        ),
    )
    return {
        "phase": "Runtime V1.4N",
        "title": "Active Specialist Routing Design Scaffold",
        "status": "design_scaffold_only",
        "final_recommendation": "PROCEED_EXECUTION_AUTHORIZATION_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "invariant_flags": dict(RUNTIME_V14N_INVARIANT_FLAGS),
        "request": request.as_dict(),
        "gate": gate.as_dict(),
        "contract": contract.as_dict(),
        "decision": decision.as_dict(),
        "trace": trace.as_dict(),
        "plan": plan.as_dict(),
        "report_entry": entry.as_dict(),
        "safety_boundaries": [
            "specialist routing is not enabled",
            "provider calls are not enabled",
            "network access is not used by the scaffold",
            "specialist output is not authority",
            "merge protocol integration remains dormant",
            "no memory, canonical, recall, training, scheduler, or execution mutation is permitted",
        ],
        "inactive_systems": [
            "live routing",
            "provider calls",
            "network calls",
            "human approval workflow",
            "specialist merge invocation",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "training",
            "execution",
        ],
    }


def write_active_specialist_routing_report() -> dict[str, object]:
    data = build_active_specialist_routing_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.4N - Active Specialist Routing Design Scaffold",
        "",
        "## Summary",
        "",
        "Runtime V1.4N defines the inert shape of future active specialist routing. It does not route, call providers, use the network, merge specialist results, or grant authority to specialists.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(
        [
            "",
            "## Inactive Systems",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Outcome: `{data['decision']['outcome']}`",
            f"- Rationale: {data['decision']['rationale']}",
            "",
            "## Continuation Checkpoint",
            "",
            "Runtime V1.4N is scaffold-only. Active specialist routing remains gated off; provider/network calls remain disabled; specialist outputs remain future evidence drafts rather than authority.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_active_specialist_routing_report()

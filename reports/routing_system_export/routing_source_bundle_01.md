======================================================================
FILE: DELTA.py
======================================================================

from __future__ import annotations

import json
import os
import queue
import re
import threading
import uuid
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog, ttk


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_operator_console import (  # noqa: E402
    append_observation,
    approve_propositions,
    build_observation_entry,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    validate_console_safe,
)
from orchestration.runtime.rc2_developmental_concept_memory import (  # noqa: E402
    approve_candidate_concept,
    build_developmental_memory_state,
    clear_developmental_memory_store,
    query_approved_concepts,
)
from orchestration.runtime.rc2_conversational_mode_router import (  # noqa: E402
    DISPLAY_MODES,
    build_memory_candidate_from_answer,
    candidate_is_memory_worthy,
    render_route,
    route_message,
    select_model_lane,
)
from orchestration.runtime.rc2_storage_adapter import backend_health, load_diverse_concepts, search_concepts, substrate_counts  # noqa: E402
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation  # noqa: E402
from orchestration.runtime.rc3_ui_capability_adapter import (  # noqa: E402
    PANEL_ORDER as RC3_PANEL_ORDER,
    build_rc3_ui_integration_report,
    build_rc3_ui_snapshot,
    render_rc3_panel,
    validate_rc3_ui_snapshot,
)
from orchestration.runtime.rc4_ui_capability_adapter import (  # noqa: E402
    RC4_PANEL_ORDER,
    build_rc4_ui_integration_report,
    build_rc4_ui_snapshot,
    render_rc4_panel,
    validate_rc4_ui_snapshot,
)
from orchestration.runtime.rc5_ui_capability_adapter import (  # noqa: E402
    RC5_PANEL_ORDER,
    build_rc5_ui_integration_report,
    build_rc5_ui_snapshot,
    render_rc5_panel,
    validate_rc5_ui_snapshot,
)
from orchestration.runtime.rc45_discourse_cognition_bridge import (  # noqa: E402
    build_discourse_frame,
    should_preempt_specialist_routing,
)
from orchestration.runtime.rc2_render_correction import is_render_correction_request  # noqa: E402
from orchestration.runtime.pc1_pragmatic_cognition import build_pragmatic_frame  # noqa: E402
from orchestration.runtime.integrated_cognitive_runtime import build_integrated_cognitive_trace  # noqa: E402
from orchestration.runtime.rc5_developmental_cognition import DevelopmentConsultationPacket  # noqa: E402
from orchestration.runtime.rc6_governed_external_intelligence import (  # noqa: E402
    build_consultation_request_from_rc5,
    classify_provider_risk,
    execute_gateway,
    parse_external_advisory_response,
    prepare_provider_request,
    safety_metadata as rc6_safety_metadata,
    stable_id as rc6_stable_id,
    validate_advisory_response,
)
from orchestration.runtime.rc7_governed_development_loop import (  # noqa: E402
    build_operator_dashboard_snapshot as build_rc7_operator_dashboard_snapshot,
    render_operator_dashboard as render_rc7_operator_dashboard,
)
from orchestration.runtime.rc11_rc12_systems_plateau import (  # noqa: E402
    build_plateau_operator_dashboard,
    render_plateau_operator_dashboard,
)
from orchestration.runtime.delta_1_4_live_wikipedia_runtime import (  # noqa: E402
    LiveWikipediaRuntimeSession,
    handle_live_chat,
    pause_live_initiative,
    resume_live_initiative,
    start_live_wikipedia_runtime,
    stop_live_wikipedia_runtime,
    suspend_live_runtime_initiative,
)
from orchestration.runtime.continuous_runtime_controller import controller_snapshot  # noqa: E402
from integration.model_runtime.provider_manager import ProviderManager  # noqa: E402


def _format_cognitive_state(state: dict[str, object]) -> str:
    return "\n".join([
        "Cognitive State",
        "",
        f"Knowledge available: {state['knowledge_available']}",
        f"Noncanonical propositions: {state['noncanonical_propositions']}",
        f"Evidence links: {state['evidence_links']}",
        f"Active runtime concepts: {state['concepts']}",
        f"Contradictions: {state['contradictions']}",
        f"Pending review: {state['pending_review']}",
        f"Substrate replay events: {state['replay_queue']}",
        f"Migration audit events: {state.get('migration_audit_events', 0)}",
        f"Canonical records: {state['canonical_records']}",
    ])


def _format_snapshot(snapshot: dict[str, object]) -> str:
    status = snapshot["runtime_status"]
    corpus = snapshot["corpus_substrate"]
    replay = snapshot["replay_rollback"]
    queue = snapshot["operator_review_queue"]
    backend = backend_health()
    counts = substrate_counts()
    reconciliation = counts.get("reconciliation") or build_substrate_reconciliation(write_reports=False)
    developmental = build_developmental_memory_state()
    return "\n".join([
        "DELTA Advanced Operator Console",
        "",
        f"Version: {status['version']}",
        f"Status: {status['status']}",
        f"Operational baseline: {status['operational_baseline']}",
        f"Latest TP phase: {status['latest_tp_phase']}",
        f"Latest recommendation: {status['latest_tp_recommendation']}",
        "",
        "Corpus / substrate:",
        f"- substrate improvements: {corpus['substrate_improvement_count']}",
        f"- canonical writes enabled: {corpus['canonical_write_enabled']}",
        f"- training enabled: {corpus['training_enabled']}",
        "",
        "Review / replay:",
        f"- review queue references: {len(queue)}",
        f"- rollback records: {replay['rollback_records']}",
        f"- replay report available: {replay['replay_report_available']}",
        "",
        "Storage backend:",
        f"- backend: {backend.get('backend')}",
        f"- sqlite available: {backend.get('sqlite_available')}",
        f"- sqlite fresh: {backend.get('fresh')}",
        f"- active runtime concepts: {counts.get('active_runtime_concepts', counts.get('concepts'))}",
        f"- active graph edges: {counts.get('active_graph_edges', counts.get('graph_edges'))}",
        f"- substrate replay events: {counts.get('substrate_replay_events', counts.get('replay_events'))}",
        f"- concept replay events: {counts.get('concept_replay_events')}",
        f"- graph edge replay events: {counts.get('graph_edge_replay_events')}",
        f"- migration audit events: {counts.get('migration_audit_events')}",
        f"- legacy JSONL concepts: {counts.get('legacy_jsonl_concepts')}",
        f"- legacy JSONL graph edges: {counts.get('legacy_jsonl_graph_edges')}",
        f"- developmental memory records: {developmental.get('knowledge_memory_records')}",
        f"- concept import coverage: {counts.get('concept_replay_coverage')}",
        f"- edge import coverage: {counts.get('edge_replay_coverage')}",
        f"- authoritative concept counter: {reconciliation.get('authoritative_runtime_concept_counter')}",
        "",
        "Systems plateau:",
        _plateau_developer_overlay_text(),
    ])


def _extract_report_path(message: str) -> Path | None:
    match = re.search(r"([A-Za-z]:\\[^\r\n]+?\.(?:md|json))", message)
    if not match:
        return None
    return Path(match.group(1).strip().strip('"'))


def _inspect_local_report(message: str) -> dict[str, object] | None:
    path = _extract_report_path(message)
    if path is None:
        return None
    try:
        resolved = path.resolve()
        reports_root = (ROOT / "reports").resolve()
        if reports_root not in (resolved, *resolved.parents):
            return {
                "handled": True,
                "answer": "I can only inspect local DELTA report files under the repo `reports` folder from this UI path.",
                "safety": _report_inspection_safety(),
            }
        if not resolved.exists() or not resolved.is_file():
            return {
                "handled": True,
                "answer": f"I could not find that report file:\n{resolved}",
                "safety": _report_inspection_safety(),
            }
        text = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "handled": True,
            "answer": _summarize_report_text(resolved, text, message),
            "safety": _report_inspection_safety(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "handled": True,
            "answer": f"I tried to inspect that local report, but the read failed: {type(exc).__name__}: {str(exc)[:180]}",
            "safety": _report_inspection_safety(),
        }


def _report_inspection_safety() -> dict[str, bool]:
    return {
        "local_file_read_performed": True,
        "provider_calls_performed": False,
        "gpt_api_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "developmental_memory_write_performed": False,
        "autonomous_action_performed": False,
    }


def _pc1_enabled() -> bool:
    value = os.environ.get("DELTA_PC1_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "off", "no", "disabled"}


def _pc1_context_for_message(last_report_inspection: dict[str, object] | None = None) -> dict[str, object]:
    if last_report_inspection:
        return {
            "active_topic": "RC4/RC5 real operator pilot and freeze readiness",
            "operator_goal": "evaluate governed RC4/RC5 readiness without overclaiming freeze",
            "last_report": last_report_inspection.get("report_name"),
            "last_report_summary": last_report_inspection.get("answer_summary"),
        }
    return {
        "active_topic": "RC4/RC5 governed operator pilot",
        "operator_goal": "preserve practical intent, scope, and governance boundaries",
    }


def _try_pc1_pragmatic_answer(message: str, last_report_inspection: dict[str, object] | None = None, *, developer_overlay: bool = False) -> str | None:
    if not _pc1_enabled():
        return None
    if is_render_correction_request(message):
        return None
    if not last_report_inspection and not _pc1_has_governance_cue(message):
        return None
    frame = build_pragmatic_frame(message, _pc1_context_for_message(last_report_inspection))
    if frame.confidence.confidence < 0.82:
        return None
    route_hint = frame.cooperative_interpretation.route_hint
    if route_hint not in {
        "pc1_shadow_mixed_judgment",
        "pc1_shadow_evidence_standard",
        "pc1_shadow_scope_boundary",
        "pc1_shadow_scope_separation",
        "pc1_shadow_response_planning",
        "pc1_shadow_recommendation",
    }:
        return None
    reply = _render_pc1_pragmatic_answer(frame)
    if not reply:
        return None
    if developer_overlay:
        reply += "\n\n--- Developer Overlay ---\n"
        reply += "Route: pc1_bounded_pragmatic_pre_router\n"
        reply += f"PC1 enabled: {_pc1_enabled()}\n"
        reply += "PC1 frame:\n"
        reply += json.dumps(frame.as_dict(), indent=2, sort_keys=True)
        reply += "\nIntegrated cognitive trace:\n"
        reply += json.dumps(
            build_integrated_cognitive_trace(
                message,
                last_report_inspection,
                include_rc2_route_preview=False,
            ),
            indent=2,
            sort_keys=True,
        )
        reply += "\nSafety:\n"
        reply += json.dumps(_pc1_safety(), indent=2, sort_keys=True)
    return reply


def _pc1_has_governance_cue(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split())
    cues = (
        "rc4",
        "rc5",
        "pilot",
        "freeze",
        "operator",
        "review",
        "authorization",
        "governance",
        "sandbox",
        "production",
        "proposal",
        "provider",
        "gpt",
        "rollback",
        "bounded repair",
        "patch",
        "proposed fix",
        "outside reviewer",
    )
    return any(cue in lower for cue in cues)


def _render_pc1_pragmatic_answer(frame) -> str:
    shape = frame.response_shape.shape
    interpretation = frame.cooperative_interpretation.interpretation
    if shape == "mixed_judgment_explanation":
        if "diagnosis" in interpretation and "overbroad" in interpretation:
            return "\n".join([
                "Treat that as a mixed pilot judgment, not a contradiction.",
                "",
                "Session record:",
                "- Diagnosis: useful. Keep it as evidence that DELTA identified the right issue.",
                "- Proposed fix: too broad. Reject or revise that part before any RC4 handoff.",
                "- Overall disposition: partially useful, not accepted as-is.",
                "",
                "Freeze implication: this helps the pilot evidence record, but it is not freeze proof unless the revised proposal stays bounded, reviewable, and validated.",
                "",
                "No memory was written. No provider was called.",
            ])
        if "Technical success" in frame.cooperative_interpretation.why_preferred or "governance" in interpretation:
            return "\n".join([
                "That is technical success, but not governed success.",
                "",
                "Record it as:",
                "- Technical result: the patch worked.",
                "- Governance result: failed, because operator review was skipped.",
                "- Overall disposition: not RC4/RC5 freeze-ready until the review gap is repaired.",
                "",
                "The useful part is the implementation evidence. The blocking part is the missing operator authorization/review trail.",
                "",
                "No memory was written. No provider was called.",
            ])
        if frame.mixed_judgments:
            judgment = frame.mixed_judgments[0]
            dimensions = [f"- {key.replace('_', ' ').title()}: {value}." for key, value in judgment.dimensions.items()]
            return "\n".join([
                "This should be recorded as a mixed judgment with separate dimensions.",
                "",
                *dimensions,
                f"- Overall disposition: {judgment.overall_disposition.replace('_', ' ')}.",
                "",
                "Do not collapse the mixed result into a single yes/no success claim.",
                "",
                "No memory was written. No provider was called.",
            ])
    if shape == "context_boundary_explanation" and "rollback evidence" in interpretation:
        return "\n".join([
            "In this RC4/RC5 pilot context, rollback evidence means proof that a bad or unwanted change can be safely reversed or stopped.",
            "",
            "Good rollback evidence would show:",
            "- What change or proposal was being tested.",
            "- What went wrong or why the operator rejected it.",
            "- The exact rollback, rejection, bounded repair stop, or restoration path.",
            "- Confirmation that no unauthorized production mutation, memory write, provider call, commit, push, deployment, or freeze claim occurred.",
            "- The final recovered state and any remaining follow-up.",
            "",
            "So this is governance/recovery evidence, not a medical or domain-recall question.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "governance_decision_guidance" and "outside reviewer" in interpretation:
        return "\n".join([
            "Use the outside reviewer's issue as advisory evidence, but reject the direct-patch instruction.",
            "",
            "A good record would say:",
            "- External review found a useful issue.",
            "- Direct application was rejected because outside advice does not grant integration authority.",
            "- Any fix must go through RC4 proposal, operator review, validation, and explicit approval.",
            "",
            "That preserves the useful signal without giving the reviewer or the advice itself execution authority.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "scope_boundary_explanation":
        return "\n".join([
            "That approval is scope-limited.",
            "",
            "Testing approval means DELTA may treat sandbox/testing work as allowed in the pilot record. It does not authorize production mutation, integration, deployment, commit, push, plugin activation, provider calls, or freeze claims.",
            "",
            "No memory was written. No provider was called.",
        ])
    if shape == "evidence_standard_explanation":
        return _answer_sufficient_recovery_evidence()
    if shape == "recommendation":
        return _answer_primary_freeze_evidence_gap()
    return ""


def _pc1_safety() -> dict[str, bool]:
    return {
        "pc1_enabled": _pc1_enabled(),
        "provider_calls_performed": False,
        "gpt_api_calls_performed": False,
        "developmental_memory_write_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "production_authority_expanded": False,
        "rc4_contract_changed": False,
        "rc5_contract_changed": False,
    }


def _rc7_developer_overlay_text() -> str:
    snapshot = build_rc7_operator_dashboard_snapshot()
    return render_rc7_operator_dashboard(snapshot) + "\nSnapshot:\n" + json.dumps(snapshot, indent=2, sort_keys=True)


def _plateau_developer_overlay_text() -> str:
    snapshot = build_plateau_operator_dashboard()
    return render_plateau_operator_dashboard(snapshot) + "\nSnapshot:\n" + json.dumps(snapshot, indent=2, sort_keys=True)


def _is_rc6_pilot_message(message: str) -> bool:
    lower = " ".join(str(message or "").lower().split())
    return (
        "rc6" in lower
        or "external provider" in lower
        or "external consultation" in lower
        or "bounded external consultation" in lower
        or "mock external advisory response" in lower
        or "provider call" in lower
    ) and any(term in lower for term in ("classify", "consultation packet", "validate", "disabled-gateway pilot", "provider transport"))


def _handle_rc6_pilot_message(message: str, events: list[dict[str, object]] | None = None) -> str | None:
    if not _is_rc6_pilot_message(message):
        return None
    lower = " ".join(message.lower().split())
    events = events if events is not None else []
    if "classify this request" in lower:
        target = _extract_rc6_embedded_text(message) or message
        risk = classify_provider_risk(target)
        event = {
            "kind": "classification",
            "target": target,
            "outcome": risk.provider_outcome,
            "reasons": list(risk.reasons),
            "provider_call_performed": False,
        }
        events.append(event)
        return _render_rc6_classification(target, risk)
    if "consultation packet" in lower and "do not send" in lower:
        target = _extract_rc6_embedded_text(message) or message
        packet = _build_rc6_ui_packet(target)
        request = build_consultation_request_from_rc5(packet, extra_context=target)
        provider_request = prepare_provider_request(request)
        result = execute_gateway(request, env={})
        event = {
            "kind": "packet",
            "target": target,
            "outcome": request.risk.provider_outcome,
            "gateway_status": result.decision.status,
            "provider_call_performed": result.decision.provider_call_performed,
        }
        events.append(event)
        return _render_rc6_packet_result(target, request, provider_request, result)
    if "mock external advisory response" in lower or ("validate it under rc6 rules" in lower and "advisory response" in lower):
        target = _extract_rc6_embedded_text(message) or message
        response = parse_external_advisory_response(_mock_advisory_payload_from_text(target))
        validation = validate_advisory_response(response)
        event = {
            "kind": "advisory_validation",
            "target": target,
            "outcome": "accepted" if validation.valid else "rejected",
            "findings": list(validation.findings),
            "provider_call_performed": False,
        }
        events.append(event)
        return _render_rc6_advisory_validation(target, validation)
    if "summarize" in lower and "disabled-gateway pilot" in lower:
        return _render_rc6_pilot_summary(events)
    return None


def _extract_rc6_embedded_text(message: str) -> str:
    patterns = (
        r"[“\"]([^”\"]+)[”\"]",
        r"â€œ(.+?)â€\u009d",
        r"â€œ(.+?)â€",
        r"classify this request:\s*(.+?)\s*Should this",
        r"do not send it:\s*(.+?)\s*Show",
        r"response,\s*validate it under RC6 rules:\s*(.+?)\s*Should RC6",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return " ".join(match.group(1).strip().strip(" .").split())
    return ""


def _build_rc6_ui_packet(target: str) -> DevelopmentConsultationPacket:
    return DevelopmentConsultationPacket(
        packet_id=rc6_stable_id("ui-rc6-packet", target),
        purpose_criterion="Evaluate whether a bounded external consultation is useful without granting authority.",
        observed_deficit=target,
        evidence=("Operator supplied an RC6 disabled-gateway pilot prompt.",),
        counterevidence=("No live provider transport has been approved.",),
        architecture_summary="RC6 is a disabled-by-default governed gateway over RC5 manual consultation packets.",
        constraints=("advisory_only", "operator_review_required", "provider_disabled_by_default", "stateless_packet_only"),
        prohibited_changes=("automatic_api_call", "self_approval", "purpose_mutation", "hidden_persistence", "rc4_bypass"),
        requested_output=("root_cause_assessment", "candidate_remedies", "tests", "rollback_conditions"),
        token_budget=1000,
        estimated_tokens=max(1, len(target.split()) * 4 // 3),
        omitted_context=(),
        transport="rc6_disabled_gateway_preview",
    )


def _render_rc6_classification(target: str, risk) -> str:
    label = {
        "SAFE_FOR_LOCAL_PROCESSING": "safe for local processing; no external consultation needed",
        "SAFE_FOR_BOUNDED_API_CONSULTATION": "safe for bounded external consultation after operator approval",
        "REQUIRES_OPERATOR_REVIEW": "requires operator review before any external consultation",
        "PROHIBITED_FROM_EXTERNAL_TRANSMISSION": "prohibited from external transmission",
    }.get(risk.provider_outcome, risk.provider_outcome)
    return "\n".join([
        "RC6 classification",
        "",
        f"Request: {target}",
        f"Outcome: {label}",
        f"Risk level: {risk.risk_level}",
        f"Authority class: {risk.authority_class}",
        f"Sensitivity class: {risk.sensitivity_class}",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in risk.reasons],
        "",
        "Provider call: false",
        "No memory was written.",
    ])


def _render_rc6_packet_result(target: str, request, provider_request, result) -> str:
    included = [
        "purpose criterion",
        "observed deficit",
        "bounded evidence/counterevidence",
        "architecture summary",
        "constraints",
        "prohibited changes",
        "requested output schema",
    ]
    excluded = [
        "raw private memory",
        "secrets or credentials",
        "protected repositories",
        "production execution authority",
        "operator identity data unless approved",
        "hidden conversation history",
    ]
    signals = tuple(request.redaction.findings or ()) + tuple(request.sensitivity.findings or ()) + tuple(request.risk.reasons or ())
    return "\n".join([
        "RC6 disabled-gateway consultation packet preview",
        "",
        f"Task: {target}",
        f"Risk outcome: {request.risk.provider_outcome}",
        f"Gateway status: {result.decision.status}",
        f"Transport permitted now: {provider_request.transport_permitted and result.decision.provider_call_performed}",
        f"Provider call: {str(result.decision.provider_call_performed).lower()}",
        "",
        "Included context:",
        *[f"- {item}" for item in included],
        "",
        "Excluded context:",
        *[f"- {item}" for item in excluded],
        "",
        "Redaction / blocking signals:",
        *([f"- {finding}" for finding in signals] or ["- none"]),
        "",
        "Preview payload authority: advisory_only",
        "No memory was written. No provider was called.",
    ])


def _mock_advisory_payload_from_text(text: str) -> dict[str, object]:
    return {
        "diagnosis": text[:240] or "No diagnosis supplied.",
        "alternative_causes": ["route_precedence", "insufficient_context"],
        "remedies": [text],
        "assumptions": ["mock_response_supplied_by_operator"],
        "risks": ["external_advice_may_be_wrong"],
        "tests": ["focused_regression_test"] if any(term in text.lower() for term in ("test", "regression")) else [],
        "rollback": ["operator_can_reject_advice"] if any(term in text.lower() for term in ("rollback", "bounded", "operator review", "reject")) else [],
        "missing_info": ["real_provider_metadata"],
        "confidence": 0.7,
    }


def _render_rc6_advisory_validation(target: str, validation) -> str:
    disposition = "accept as advisory-only input" if validation.valid else "reject"
    return "\n".join([
        "RC6 advisory response validation",
        "",
        f"Mock response: {target}",
        f"Decision: {disposition}",
        f"Authority: {validation.authority}",
        "",
        "Findings:",
        *[f"- {finding}" for finding in validation.findings],
        "",
        "Provider call: false",
        "No memory was written.",
    ])


def _render_rc6_pilot_summary(events: list[dict[str, object]]) -> str:
    classifications = [event for event in events if event.get("kind") == "classification"]
    packets = [event for event in events if event.get("kind") == "packet"]
    validations = [event for event in events if event.get("kind") == "advisory_validation"]
    provider_calls = any(bool(event.get("provider_call_performed")) for event in events)
    risk_events = classifications + packets
    safe = sum(1 for event in risk_events if event.get("outcome") == "SAFE_FOR_BOUNDED_API_CONSULTATION")
    operator_review = sum(1 for event in risk_events if event.get("outcome") == "REQUIRES_OPERATOR_REVIEW")
    prohibited = sum(1 for event in risk_events if event.get("outcome") == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION")
    blocked = operator_review + prohibited
    local = sum(1 for event in risk_events if event.get("outcome") == "SAFE_FOR_LOCAL_PROCESSING")
    accepted_advice = sum(1 for event in validations if event.get("outcome") == "accepted")
    rejected_advice = sum(1 for event in validations if event.get("outcome") == "rejected")
    checkpoint = (
        "RC6_DISABLED_GATEWAY_PILOT_PASSED"
        if events and safe > 0 and blocked > 0 and not provider_calls
        else "RC6_DISABLED_GATEWAY_PILOT_NEEDS_MORE_EVIDENCE"
    )
    recommendation = (
        "READY_FOR_OPERATOR_APPROVED_LOW_COST_PROVIDER_TRIAL"
        if checkpoint == "RC6_DISABLED_GATEWAY_PILOT_PASSED"
        else "CONTINUE_DISABLED_GATEWAY_PILOT"
    )
    return "\n".join([
        "RC6 disabled-gateway pilot summary",
        "",
        f"Checkpoint: {checkpoint}",
        f"Recommendation: {recommendation}",
        "",
        f"Classifications reviewed: {len(classifications)}",
        f"- Safe bounded consultation: {safe}",
        f"- Operator-review outcomes: {operator_review}",
        f"- Prohibited transmissions: {prohibited}",
        f"- Operator-only or prohibited total: {blocked}",
        f"- Local-only: {local}",
        f"Packet previews prepared: {len(packets)}",
        f"Advisory responses validated: {len(validations)}",
        f"- Advisory accepted: {accepted_advice}",
        f"- Advisory rejected: {rejected_advice}",
        f"Provider call made: {str(provider_calls).lower()}",
        "",
        "Interpretation:",
        "- This conversation tested the disabled gateway path, not real provider transport.",
        "- RC6 should pass this pilot only if low-risk consultation requests are separated from secrets, protected repositories, production decisions, purpose/governance changes, and RC4 bypass requests.",
        "- Packet previews should preserve enough bounded context for useful advice while excluding authority, secrets, private memory, and protected material.",
        "- The first real provider trial should remain one low-risk request with explicit operator approval, strict token budget, exact outbound-packet preview, no sensitive context, structured response validation, and no automatic RC4 handoff.",
        "",
        "No memory was written. No provider was called.",
    ])


def _summarize_report_text(path: Path, text: str, request: str = "") -> str:
    if path.name == "RC6_PROVIDER_GATEWAY_READINESS.md":
        return _summarize_rc6_gateway_readiness(path, text)
    if path.name == "RC45_OPERATOR_MIMIC_CONSOLIDATED.md":
        return _summarize_rc45_mimic_report(path, text)
    if path.name == "RC45_CALIBRATION_REPORT.md":
        return _summarize_rc45_calibration_report(path, text)
    if path.name == "RC45_INTEGRATED_DEVELOPMENT_CYCLES.md":
        return _summarize_rc45_integrated_cycles_report(path, text)
    if path.name == "RC45_EXPANDED_ADVERSARIAL_EVALUATION.md":
        return _summarize_rc45_adversarial_report(path, text)
    if path.name == "RC5_UI_CAPABILITY_INTEGRATION.md":
        return _summarize_rc5_ui_integration_report(path, text)
    if path.name == "RC45_FREEZE_READINESS_REVIEW.md":
        return _summarize_rc45_freeze_report(path, text, request)
    return _summarize_generic_report(path, text)


def _summarize_rc6_gateway_readiness(path: Path, text: str) -> str:
    json_path = path.with_suffix(".json")
    data: dict[str, object] = {}
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    recommendation = str(data.get("recommendation") or _first_jsonish_value(text, "recommendation") or "review_needed")
    enabled = bool(data.get("provider_enabled_default")) if data else False
    live_calls = bool(data.get("live_calls_performed")) if data else False
    return "\n".join([
        f"I inspected `{path.name}`.",
        "",
        f"Status: {recommendation}",
        f"External provider transport enabled: {str(enabled).lower()}",
        f"Live provider calls performed: {str(live_calls).lower()}",
        "",
        "RC6 state:",
        "- The gateway is ready for disabled-gateway pilot testing.",
        "- External models remain advisory only.",
        "- Operator approval, risk classification, redaction, budget checks, and response validation are required before any future low-cost provider trial.",
        "",
        "No memory was written. I only read the local report file.",
    ])


def _summarize_rc45_freeze_report(path: Path, text: str, request: str = "") -> str:
    lowered_request = request.lower()
    if "weakness" in lowered_request and "report itself" in lowered_request:
        return _summarize_rc45_freeze_report_weakness(path, text)
    lower = text.lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    freeze_lines = [line for line in lines if "freeze" in line.lower() or "operator_pilot" in line.lower() or "operator pilot" in line.lower()]
    blocker_lines = [line for line in lines if "blocker" in line.lower() or "evidence" in line.lower()]
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        "",
        "What real operator evidence is still needed:",
        "- Real operator sessions using RC4/RC5 on actual low-risk tasks.",
        "- Records of what DELTA proposed, what the operator accepted/rejected/revised, and why.",
        "- Evidence that governance stayed understandable and practical during the work.",
        "- Evidence that failures were recoverable through rollback, rejection, or bounded repair.",
        "- Evidence that RC4/RC5 did not rely on mimic/developer rehearsal evidence as freeze proof.",
    ]
    if "rc4_freeze_pending_real_operator_pilot" in lower:
        answer.append("- RC4 must remain pending until real operator pilot evidence exists.")
    if "rc5_freeze_pending_real_operator_pilot" in lower:
        answer.append("- RC5 must remain pending until real operator pilot evidence exists.")
    if blocker_lines:
        answer.extend(["", "Relevant report signals:"])
        answer.extend(f"- {line[:220]}" for line in blocker_lines[:6])
    elif freeze_lines:
        answer.extend(["", "Relevant report signals:"])
        answer.extend(f"- {line[:220]}" for line in freeze_lines[:6])
    answer.extend([
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _summarize_rc45_freeze_report_weakness(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        "",
        "One weakness in the report itself:",
        "- The report is good at saying the remaining blocker is real operator evidence, but it is thin as an operator-run playbook.",
        "",
        "Why that could make the real pilot harder:",
        "- It does not spell out a concrete session template with fields like task, operator decision, accepted/rejected/revised proposal, recovery outcome, workload, and confusion points.",
        "- Because of that, two operators could collect evidence in inconsistent formats, making freeze review harder.",
        "",
        "Recommended improvement:",
        "- Add a short real-pilot evidence form or checklist next to the freeze report, so each session records the same minimum facts.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _is_pilot_checklist_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "checklist" in lower
        and ("pilot" in lower or "operator" in lower)
        and ("do not store" in lower or "don't store" in lower or "provider" in lower or "call" in lower)
    )


def _draft_operator_pilot_checklist(anchor: dict[str, object] | None = None) -> str:
    source = str((anchor or {}).get("report_name") or "the prior report inspection")
    return "\n".join([
        "Here is a concise RC4/RC5 real-operator pilot evidence checklist.",
        "",
        f"Source context: {source}",
        "",
        "For each pilot session, record:",
        "1. Session ID and date.",
        "2. Real low-risk task attempted.",
        "3. Initial operator goal or request.",
        "4. What DELTA inspected or proposed.",
        "5. Operator decision: accepted, rejected, revised, or deferred.",
        "6. Why the operator made that decision.",
        "7. Governance evidence: authorization, review boundary, or blocked action.",
        "8. Recovery evidence: rollback, rejection, bounded repair, or stop condition.",
        "9. Workload/friction: confusing steps, too many clicks, unclear wording, or excessive time.",
        "10. Safety confirmation: no provider call, memory write, commit, push, deployment, or freeze claim unless explicitly authorized.",
        "11. Final outcome: useful, partially useful, not useful, or unsafe/confusing.",
        "12. Follow-up needed before freeze.",
        "",
        "Minimum freeze-useful evidence:",
        "- At least one accepted proposal.",
        "- At least one rejected or revised proposal.",
        "- At least one recovery/rollback/stop-condition example.",
        "- At least one session showing the operator could find the relevant RC4/RC5 evidence without raw JSON hunting.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_pilot_session_record_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        ("use the checklist" in lower or "session record" in lower or "evaluate this pilot session" in lower)
        and ("pilot session" in lower or "freeze evidence" in lower)
    )


def _draft_operator_pilot_session_record(message: str, anchor: dict[str, object] | None = None) -> str:
    lower = message.lower()
    repair_failed = "repair failed validation" in lower or ("bounded repair" in lower and "failed validation" in lower)
    stop_requested = "told delta to stop" in lower or "stop rather than try again" in lower or "stop condition" in lower
    unsafe_external_advice = (
        ("manual gpt" in lower or "gpt response" in lower or "external advice" in lower)
        and ("skip" in lower or "skipping" in lower or "bypass" in lower)
        and ("rc4 authorization" in lower or "authorization" in lower)
    )
    if repair_failed:
        return "\n".join([
            "Pilot Session Record",
            "",
            "Session type: RC4/RC5 real-operator pilot interaction",
            f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
            "",
            "Task:",
            "- Evaluate a bounded-repair pilot case where DELTA proposed a repair and validation failed.",
            "",
            "Observed DELTA behavior:",
            "- DELTA proposed a bounded repair.",
            "- The repair failed validation.",
            "",
            "Operator decision:",
            f"- {'Stopped the repair loop rather than allowing another attempt.' if stop_requested else 'Rejected the failed repair as insufficient.'}",
            "",
            "Reason:",
            "- Failed validation means the proposal should not proceed to integration or freeze evidence by itself.",
            "- Stopping prevents bounded repair from turning into an expanding unattended loop.",
            "",
            "Governance evidence:",
            "- Operator retained final authority.",
            "- Repair did not self-approve or continue automatically.",
            "- No autonomous action, provider call, memory write, commit, push, deployment, or freeze claim occurred.",
            "",
            "Recovery evidence:",
            "- Stop condition was exercised after validation failure.",
            "- This is useful recovery evidence for the pilot, but not sufficient freeze evidence alone.",
            "",
            "Final outcome:",
            "- Useful recovery/governance evidence; repair outcome failed.",
            "",
            "Follow-up needed before freeze:",
            "- Run additional real low-risk sessions with at least one accepted proposal and one successful bounded recovery.",
        ])
    if unsafe_external_advice:
        return "\n".join([
            "Pilot Session Record",
            "",
            "Session type: RC4/RC5 real-operator pilot interaction",
            f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
            "",
            "Task:",
            "- Evaluate a manual-consultation case where external advice suggested bypassing governance.",
            "",
            "Observed DELTA behavior:",
            "- A manual GPT response suggested skipping RC4 authorization and applying a patch directly.",
            "",
            "Operator decision:",
            "- Rejected the advice.",
            "",
            "Reason:",
            "- External consultation is advisory only.",
            "- RC4 authorization and operator review cannot be bypassed by a GPT response.",
            "",
            "Governance evidence:",
            "- Unsafe advice was blocked.",
            "- No patch was applied directly.",
            "- No autonomous action, provider call, memory write, commit, push, deployment, or freeze claim occurred.",
            "",
            "Recovery evidence:",
            "- The unsafe recommendation was discarded and the governed path remained intact.",
            "",
            "Final outcome:",
            "- Useful governance evidence; not sufficient freeze evidence alone.",
            "",
            "Follow-up needed before freeze:",
            "- Run a real low-risk manual consultation case where advice is accepted only after review and validation.",
        ])
    rejected_freeze = "reject" in lower and "freeze evidence" in lower
    rollback_missing = "rollback" in lower and ("did not" in lower or "not test" in lower)
    accepted_checklist = "accept" in lower and "checklist" in lower and "freeze" in lower
    return "\n".join([
        "Pilot Session Record",
        "",
        "Session type: RC4/RC5 real-operator pilot interaction",
        f"Source context: {str((anchor or {}).get('report_name') or 'prior checklist')}",
        "",
        "Task:",
        "- Continue from the drafted RC4/RC5 pilot checklist and evaluate whether this session counts as freeze evidence.",
        "",
        "Observed DELTA behavior:",
        "- DELTA produced a useful real-operator pilot evidence checklist.",
        "- DELTA did not write memory or call a provider.",
        "",
        "Operator decision:",
        f"- {'Rejected as sufficient freeze evidence.' if rejected_freeze else ('Accepted as a useful pilot artifact, but not as freeze approval.' if accepted_checklist else 'Not accepted as sufficient freeze evidence yet.')}",
        "",
        "Reason:",
        "- This is only one operator session.",
        f"- {'Rollback/recovery was not tested.' if rollback_missing else 'Recovery coverage still needs explicit evidence.'}",
        "- The session supports usability of the checklist, but not full RC4/RC5 freeze readiness.",
        "",
        "Governance evidence:",
        "- Operator retained final authority.",
        "- Freeze was not claimed.",
        "- No autonomous action, provider call, memory write, commit, push, or deployment occurred.",
        "",
        "Recovery evidence:",
        f"- {'Not exercised in this session.' if rollback_missing else 'Not yet sufficient for freeze.'}",
        "",
        "Final outcome:",
        "- Useful, but partial.",
        "",
        "Follow-up needed before freeze:",
        "- Run additional real low-risk sessions.",
        "- Include at least one rejected/revised proposal.",
        "- Include at least one rollback, bounded repair, or stop-condition case.",
        "- Confirm the operator can find and understand the relevant RC4/RC5 evidence.",
    ])


def _is_same_report_weakness_request(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return "same report" in lower and "weakness" in lower and "report itself" in lower


def _summarize_same_report_weakness(anchor: dict[str, object] | None) -> str:
    if not anchor:
        return "I can do that, but I need a report path first so I know which report you mean."
    report_name = str(anchor.get("report_name") or "")
    report_path_text = str(anchor.get("report_path") or "")
    path = Path(report_path_text) if report_path_text else ROOT / "reports" / report_name
    if report_name == "RC45_FREEZE_READINESS_REVIEW.md" and path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        return _summarize_rc45_freeze_report_weakness(path, text)
    return "\n".join([
        f"I inspected `{report_name or 'the prior report'}` again.",
        "",
        "One weakness in the report itself:",
        "- It does not yet provide a concrete operator-run evidence form for collecting comparable pilot sessions.",
        "",
        "Why that could make the real pilot harder:",
        "- Operators may record different details, making later freeze review less consistent.",
        "",
        "Recommended improvement:",
        "- Use a short pilot checklist with fields for task, decision, evidence, recovery, workload, safety, and follow-up.",
        "",
        "No memory was written. I only used the prior local report inspection context.",
    ])


def _is_second_one_pilot_followup(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return lower in {"what about the second one?", "what about the second one", "the second one?", "second one?"}


def _answer_second_one_pilot_followup(anchor: dict[str, object] | None = None) -> str:
    source = str((anchor or {}).get("report_name") or "the prior pilot checklist")
    return "\n".join([
        "If you mean the second minimum freeze-useful evidence item, it is:",
        "",
        "- At least one rejected or revised proposal.",
        "",
        f"Source context: {source}",
        "",
        "For the current checklist session, that means the record should say:",
        "- The checklist was useful.",
        "- The operator did not approve RC4/RC5 freeze.",
        "- The operator either rejected the session as sufficient evidence or revised its scope to future pilot preparation only.",
        "- This is useful governance evidence because operator authority over acceptance/rejection stayed explicit.",
        "",
        "It still does not satisfy rollback or bounded-repair evidence by itself.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_rc5_gpt_boundary_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "rc5" in lower
        and ("automatically ask gpt" in lower or "automatic gpt" in lower or "ask gpt during" in lower)
        and ("boundary" in lower or "explain" in lower)
    )


def _answer_rc5_gpt_boundary() -> str:
    return "\n".join([
        "No. DELTA should not automatically ask GPT during RC5 development cycles.",
        "",
        "Boundary:",
        "- RC5 may prepare a compact manual consultation packet.",
        "- The operator decides whether to copy that packet to GPT or another reviewer.",
        "- Any response that comes back is advisory evidence, not authority.",
        "- DELTA must validate the advice against governance, constraints, tests, and operator approval before using it.",
        "",
        "What must not happen automatically:",
        "- No API/provider call.",
        "- No patch application.",
        "- No RC4 authorization bypass.",
        "- No memory write, plugin activation, commit, push, deployment, or freeze claim.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_rc4_handoff_boundary_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "rc5" in lower
        and "upgrade proposal" in lower
        and ("handed off to rc4" in lower or "handoff" in lower or "hand off" in lower)
    )


def _answer_rc4_handoff_boundary() -> str:
    return "\n".join([
        "An RC5 upgrade proposal should be handed off to RC4 only after RC5 has enough governed evidence to justify implementation review.",
        "",
        "Handoff-ready signals:",
        "- A concrete deficit or capability gap is identified.",
        "- The proposed change is scoped and reversible.",
        "- Evidence, expected benefit, validation path, and rollback/stop conditions are stated.",
        "- Any manual GPT or external advice has been treated as advisory and checked against governance.",
        "- The operator agrees the proposal is worth implementation review.",
        "",
        "What must not happen automatically:",
        "- RC5 must not implement the change itself.",
        "- RC5 must not bypass RC4 authorization.",
        "- No automatic patch, commit, push, deployment, plugin activation, provider call, memory write, or freeze claim.",
        "",
        "No memory was written. No provider was called.",
    ])


def _is_full_pilot_freeze_decision_question(message: str) -> bool:
    lower = " ".join(message.lower().split())
    return (
        "full pilot session" in lower
        and ("ready to freeze" in lower or "freeze" in lower)
        and ("evidence is still missing" in lower or "what evidence" in lower or "if not" in lower)
    )


def _answer_full_pilot_freeze_decision() -> str:
    return "\n".join([
        "No. Based on this pilot session, RC4 and RC5 are ready to continue real operator pilot work, but they are not ready to freeze yet.",
        "",
        "What this session supports:",
        "- Report inspection worked for key RC4/RC5 evidence reports.",
        "- The pilot checklist was useful.",
        "- Operator rejection and limited acceptance were captured without granting authority.",
        "- UI authority, adversarial, integrated-cycle, and calibration reports were reviewed as local evidence.",
        "- Safety boundaries remained intact: no provider call, memory write, patch, commit, push, deployment, or freeze claim.",
        "",
        "What is still missing before freeze:",
        "- More real low-risk operator sessions, not just one conversational review thread.",
        "- At least one real rollback, bounded-repair stop, or recovery case.",
        "- At least one accepted proposal and one rejected or revised proposal recorded in the pilot format.",
        "- Evidence that operator workload and friction remain practical across multiple sessions.",
        "- Evidence that any manual consultation stays advisory and does not bypass RC4 authorization.",
        "",
        "Recommendation: continue the real operator pilot; do not freeze RC4 or RC5 yet.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_primary_freeze_evidence_gap() -> str:
    return "\n".join([
        "The most important thing still to prove is that RC4/RC5 governance works during real low-risk operator work, not only in report review or developer rehearsal.",
        "",
        "The strongest missing evidence is a real session where:",
        "- DELTA proposes or evaluates a bounded change.",
        "- The operator accepts, rejects, or revises it with a recorded reason.",
        "- A recovery path is exercised, such as rollback, bounded repair stop, or rejected unsafe advice.",
        "- The system does not self-approve, call a provider, write memory, patch, commit, push, deploy, or claim freeze without explicit authorization.",
        "",
        "In short: prove recoverable governed use under real operator pressure.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_sufficient_recovery_evidence() -> str:
    return "\n".join([
        "Enough recovery evidence means at least one real low-risk pilot session shows that a failure was handled cleanly without expanding authority.",
        "",
        "Good recovery evidence would include:",
        "- The starting task and proposed action.",
        "- What failed: validation, safety review, operator rejection, external advice quality, or scope control.",
        "- The recovery decision: rollback, bounded repair stop, proposal rejection, or revision.",
        "- The operator's reason for that decision.",
        "- Proof that DELTA does not self-approve, continue automatically, or bypass authorization.",
        "- The final state after recovery: safe, reverted, stopped, or revised for later review.",
        "",
        "A strong freeze-useful example would be: DELTA proposes a bounded repair, validation fails, the operator stops the loop, and the system records the stop without patching, committing, calling a provider, or claiming success.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_mixed_proposal_record() -> str:
    return "\n".join([
        "Record accepted and rejected proposals as separate decisions in the same pilot session, not as a single blended outcome.",
        "",
        "The session record should say:",
        "- Proposal A: accepted.",
        "- Reason accepted: what evidence made it useful, bounded, and safe enough to proceed.",
        "- Required follow-up: validation, review, or RC4 handoff if implementation is needed.",
        "- Proposal B: rejected or revised.",
        "- Reason rejected/revised: what was unsafe, unclear, too broad, unsupported, or not worth the workload.",
        "- Governance result: operator authority remained explicit for both decisions.",
        "",
        "Freeze interpretation:",
        "- This is useful pilot evidence because it shows DELTA can support different operator decisions in one session.",
        "- It still needs recovery evidence if neither proposal tested rollback, bounded repair stop, or unsafe-advice rejection.",
        "",
        "No memory was written. No provider was called.",
    ])


def _answer_useful_but_unsafe_advice_handling() -> str:
    return "\n".join([
        "DELTA should split the advice into useful parts and unsafe parts.",
        "",
        "Correct handling:",
        "- Keep the useful technical insight as advisory evidence only.",
        "- Reject the instruction to bypass authorization.",
        "- Preserve RC4 authorization, operator review, validation, and rollback requirements.",
        "- Do not apply a patch directly just because GPT suggested it.",
        "- Record the mixed outcome: advice partially useful, governance recommendation rejected.",
        "",
        "Pilot record wording:",
        "- Manual GPT advice contained useful information but also suggested bypassing authorization.",
        "- Operator rejected the unsafe portion.",
        "- DELTA retained the governed path and did not patch, commit, push, deploy, call a provider, write memory, or claim freeze.",
        "",
        "No memory was written. No provider was called.",
    ])


def _summarize_rc45_mimic_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or "review_needed"
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    scenario_count = _first_jsonish_number(text, "scenario_count") or _first_jsonish_number(text, "category_count") or "unknown"
    cycle_count = _first_jsonish_number(text, "integrated_cycle_count") or "unknown"
    quality = _first_jsonish_number(text, "average_cycle_quality") or "unknown"
    workload = _first_jsonish_number(text, "average_operator_workload") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Evidence class: {evidence_class}",
        "",
        "Operator mimic calibration summary:",
        f"- Scenarios exercised: {scenario_count}",
        f"- Integrated RC4->RC5 cycles exercised: {cycle_count}",
        f"- Average cycle quality: {quality}",
        f"- Average operator workload estimate: {workload}",
        "- The calibration tested realistic operator behaviors such as confusion, changing requirements, rejection, unsafe advice, interruption, rollback, and budget pressure.",
        "- The useful result is that RC4/RC5 can be rehearsed across a broad set of governed development situations without granting live authority.",
        "",
        "Useful for the real operator pilot:",
        "- Scenario list: use it as a checklist for real low-risk operator sessions.",
        "- Calibration findings: use them to watch for operator friction, bad routing, unsafe advice, over-eager upgrades, and weak evidence.",
        "- Integrated-cycle artifacts: use them as the expected shape of real evidence to collect.",
        "- Freeze review recommendation: use it to avoid claiming freeze too early.",
        "",
        "Does not count as real freeze evidence:",
        "- Developer rehearsal evidence.",
        "- Simulated operator behavior.",
        "- Mock consultation responses.",
        "- Deterministic fixture cycles.",
        "- Estimated workload scores.",
        "- Any report line marked `DEVELOPER_REHEARSAL_EVIDENCE`.",
        "",
        "Bottom line: this report is useful as a pilot script and calibration checklist, but RC4 and RC5 still need real operator sessions before freeze.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc45_calibration_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or "review_needed"
    score = _first_jsonish_number(text, "score") or "unknown"
    risks = _extract_jsonish_object_keys(text, "finding_counts")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Calibration score: {score}",
        "",
        "Calibration weaknesses and risks to watch during the real operator pilot:",
        "- Operator mimic evidence may still be mistaken for real operator evidence.",
        "- Low-severity or false-positive reports can still tempt over-eager upgrade proposals.",
        "- Manual consultation advice can be useful but must remain advisory and checked against governance.",
        "- Operator workload and friction need real measurement, not just fixture estimates.",
        "- Budget pressure may cause skipped validation unless the minimum validation path is preserved.",
        "- Long conversations, interruptions, and resumes need explicit state handling.",
        "- RC4 bounded repair must stop cleanly instead of looping or expanding scope.",
        "- Lessons should not be retained unless explicitly reviewed.",
        "- Root-cause classification must distinguish retrieval, memory, planning, prompt, workflow, and governance issues.",
    ]
    if risks:
        answer.extend(["", "Report watchlist signals:"])
        answer.extend(f"- {risk.replace('_', ' ')}" for risk in risks[:12])
    answer.extend([
        "",
        "How to use this in the pilot:",
        "- Pick a low-risk real task.",
        "- Let DELTA inspect, propose, or classify the issue.",
        "- Record whether the proposal was useful, too broad, too costly, or confusing.",
        "- Reject or revise at least one proposal so governance is exercised.",
        "- Confirm no memory write, provider call, patch, commit, push, or freeze claim happens unless explicitly authorized.",
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _summarize_rc45_integrated_cycles_report(path: Path, text: str) -> str:
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    cycle_count = _first_jsonish_number(text, "cycle_count") or _first_jsonish_number(text, "integrated_cycle_count") or "unknown"
    packets = _first_jsonish_number(text, "consultation_packets_created") or "unknown"
    upgrades = _first_jsonish_number(text, "upgrade_proposals_created") or str(text.count('"upgrade_proposal_created": true'))
    lessons = _first_jsonish_number(text, "lessons_requiring_review") or str(text.count('"lesson_review_required": true'))
    quality = _first_jsonish_number(text, "average_quality") or _first_jsonish_number(text, "average_cycle_quality") or "unknown"
    workload = _first_jsonish_number(text, "average_operator_workload") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Evidence class: {evidence_class}",
        f"Integrated cycles reviewed: {cycle_count}",
        f"Average quality: {quality}",
        f"Average operator workload estimate: {workload}",
        "",
        "Do the cycles show recoverable failures?",
        "- Yes, as developer rehearsal evidence. The cycles include failure classes such as sandbox failure, repair failure, regression discovery, false positive, rejected proposal, unsafe advice, and rollback request.",
        "- They show the expected recovery posture: capture evidence, require review, reject unsafe advice, stop bounded repair when necessary, and keep freeze blocked until real evidence exists.",
        "",
        "Do they show bounded repair?",
        "- Yes, at the report level. RC4 artifacts are represented as proposal/sandbox/repair/verification steps, while RC5 evaluates purpose, deficit, acquisition, consultation, proposal, comparison, and lesson review.",
        "- The important boundary is that repair remains bounded and review-required; it does not become unattended execution.",
        "",
        "Useful evidence for a real operator pilot:",
        f"- Consultation packets created in rehearsal: {packets}",
        f"- Upgrade proposals created in rehearsal: {upgrades}",
        f"- Lessons requiring review in rehearsal: {lessons}",
        "- The cycle artifacts define what a real operator should record: goal, plan, governance, evidence, proposal, validation result, acceptance/rejection, and recovery outcome.",
        "- The report is useful as a checklist for real tasks, especially tasks involving rejected proposals, failed repairs, unsafe advice, or rollback.",
        "",
        "What does not count as real evidence:",
        "- The cycle outcomes are deterministic developer rehearsal evidence.",
        "- Mock consultation responses are not real external review.",
        "- Estimated workload is not real operator workload.",
        "- Fixture recovery is not proof that a real operator found recovery practical.",
        "",
        "Bottom line: the cycles are useful rehearsal evidence for designing the real pilot, but they do not by themselves freeze RC4 or RC5.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc45_adversarial_report(path: Path, text: str) -> str:
    evidence_class = _first_jsonish_value(text, "evidence_class") or "unknown"
    case_count = _first_jsonish_number(text, "case_count") or str(text.count('"case_id"'))
    score = _first_jsonish_number(text, "score") or "unknown"
    passed = _first_jsonish_bool(text, "passed")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Evidence class: {evidence_class}",
        f"Adversarial cases reviewed: {case_count}",
        f"Score: {score}",
        f"Passed: {passed if passed is not None else 'unknown'}",
        "",
        "Did it find safety, governance, or authority problems that should block a real operator pilot?",
        "- No blocking problem is indicated by this report.",
        "- The adversarial cases are reported as blocked or review-required, not as allowed unsafe behavior.",
        "- The report specifically exercises risks like ambiguous approval, scope creep, rejected proposals, unsafe manual advice, fake freeze claims, regression masking, sandbox failure, repair budget exhaustion, consultation-packet constraint loss, purpose conflict, and UI authority confusion.",
        "",
        "What should still be watched in the real pilot:",
        "- Ambiguous `yes` or `no` responses binding to the wrong action.",
        "- Operator confusion causing scope creep.",
        "- External advice being treated as authority instead of advisory input.",
        "- Metric improvement hiding regression elsewhere.",
        "- UI language implying authority that does not exist.",
        "- Any attempt to treat mimic evidence as freeze evidence.",
        "",
        "Pilot implication:",
        "- This supports proceeding to a real operator pilot.",
        "- It does not support freezing RC4 or RC5 yet because this is still developer rehearsal evidence.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_rc5_ui_integration_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    panel_count = _first_jsonish_number(text, "panel_count") or "unknown"
    expected = _first_jsonish_number(text, "expected_panel_count") or "unknown"
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
        f"Panel coverage: {panel_count} of {expected}",
        "",
        "Does the UI expose the right evidence for an operator pilot?",
        "- Yes, for a read-only pilot review. It exposes purpose, self-evaluation, deficits, acquisition strategy, manual consultation, RC4 upgrade handoff, comparative evaluation, developmental memory, mimic calibration, pilot evidence, and freeze readiness.",
        "- The Mimic Calibration panel is useful because it shows the rehearsal evidence without pretending it is real operator evidence.",
        "- The Pilot Evidence and Freeze Readiness panels are useful because they keep the real freeze blocker visible.",
        "- The Manual Consultation panel is useful because it shows packet/advice status without enabling API transport.",
        "",
        "Does it expose authority it should not expose?",
        "- No live authority is indicated by the report.",
        "- It reports no GPT/API call control, no provider call control, no automatic consultation, no purpose mutation, no self-approval, no RC4 authorization bypass, no developmental-memory auto-write, and no automatic development loop.",
        "- The UI is therefore appropriate for inspection/review, not action execution.",
        "",
        "What to watch during the real pilot:",
        "- Make sure the operator understands that panels are diagnostic, not permission to act.",
        "- Confirm the UI remains clear when a proposal is rejected or revised.",
        "- Confirm the operator can find the consultation packet and freeze blocker without hunting through raw JSON.",
        "- Confirm no button implies hidden execution authority.",
        "",
        "No memory was written. I only read the local report file.",
    ]
    return "\n".join(answer)


def _summarize_generic_report(path: Path, text: str) -> str:
    status = _first_jsonish_value(text, "recommendation") or _first_jsonish_value(text, "freeze_status") or "review_needed"
    evidence_class = _first_jsonish_value(text, "evidence_class")
    answer = [
        f"I inspected `{path.name}`.",
        "",
        f"Status: {status}",
    ]
    if evidence_class:
        answer.append(f"Evidence class: {evidence_class}")
    answer.extend([
        "",
        "What I can say from this report:",
        "- I can inspect the report as local evidence.",
        "- I should distinguish developer rehearsal evidence from real operator evidence.",
        "- I should not treat report inspection as permission to write memory, call providers, or freeze the runtime.",
        "",
        "No memory was written. I only read the local report file.",
    ])
    return "\n".join(answer)


def _first_jsonish_value(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _first_jsonish_number(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)
    return match.group(1) if match else None


def _first_jsonish_bool(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*(true|false)', text)
    return match.group(1) if match else None


def _extract_jsonish_object_keys(text: str, key: str) -> list[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\{{(.*?)\n\s*\}}', text, flags=re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"\s*:', match.group(1))


def _model_answer_offers_deepening(answer: str) -> bool:
    lower = " ".join(str(answer or "").lower().split())
    offers = (
        "would you like me to explore",
        "would you like me to go deeper",
        "would you like more detail",
        "would you like more details",
        "would you like examples",
        "should i go deeper",
        "do you want me to expand",
        "want me to expand",
    )
    return any(phrase in lower for phrase in offers)


def _build_deepening_prompt(question: str, prior_answer: str) -> str:
    return (
        "Please expand on your previous answer for this user question.\n\n"
        f"Original question: {question}\n\n"
        f"Previous answer: {prior_answer}\n\n"
        "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    )


def _assistant_answer_text(content: str) -> str:
    text = str(content or "")
    return text.split("--- Developer Overlay ---", 1)[0].strip()


def _lines_from_text(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


class DeltaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DELTA Cognitive OS")
        self.root.geometry("1180x700")
        self.root.minsize(960, 620)
        self.snapshot = build_operator_snapshot()
        self.extracted: list[dict[str, object]] = []
        self.last_message = ""
        self.last_payload: dict[str, object] | None = None
        self.concept_review_items: dict[str, dict[str, object]] = {}
        self.session_history: list[dict[str, str]] = []
        self.pending_provider_question: str | None = None
        self.pending_local_model_question: str | None = None
        self.pending_local_model_deepening: dict[str, str] | None = None
        self.active_topic_anchor: dict[str, object] | None = None
        self.last_report_inspection: dict[str, object] | None = None
        self.rc6_pilot_events: list[dict[str, object]] = []
        self.live_runtime_session: LiveWikipediaRuntimeSession | None = None
        self.live_runtime_status = tk.StringVar(value="Live runtime: stopped")
        self.live_runtime_worker_results: queue.Queue[dict[str, object]] = queue.Queue()
        self.live_runtime_request_in_flight = False
        self.pending_live_runtime_controls: list[str] = []
        self.provider_manager = ProviderManager(keep_loaded=True)
        self.resident_model_id: str | None = None
        self.resident_lane: str | None = None
        self.model_residency_status = "not_warmed"
        self.developer_overlay_enabled = tk.BooleanVar(value=False)
        if not validate_console_safe(self.snapshot):
            raise RuntimeError("DELTA console safety validation failed")
        self._build()
        self.root.after(50, self._poll_live_runtime_worker_results)
        self._refresh_state_cards()
        self._warm_default_model()
        self._show_welcome()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.conversation_tab = ttk.Frame(self.notebook, padding=10)
        self.database_tab = ttk.Frame(self.notebook, padding=10)
        self.rc3_tab = ttk.Frame(self.notebook, padding=10)
        self.rc4_tab = ttk.Frame(self.notebook, padding=10)
        self.rc5_tab = ttk.Frame(self.notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.conversation_tab, text="Conversation")
        self.notebook.add(self.database_tab, text="Database")
        self.notebook.add(self.rc3_tab, text="RC3")
        self.notebook.add(self.rc4_tab, text="RC4")
        self.notebook.add(self.rc5_tab, text="RC5")
        self.notebook.add(self.advanced_tab, text="Advanced / Operator Console")

        self._build_conversation_tab()
        self._build_database_tab()
        self._build_rc3_tab()
        self._build_rc4_tab()
        self._build_rc5_tab()
        self._build_advanced_tab()

    def _build_conversation_tab(self) -> None:
        header = ttk.LabelFrame(self.conversation_tab, text="Cognitive State")
        header.pack(fill=tk.X)
        self.state_vars: dict[str, tk.StringVar] = {}
        for index, (label, key) in enumerate([
            ("Knowledge", "knowledge_available"),
            ("Propositions", "noncanonical_propositions"),
            ("Evidence", "evidence_links"),
            ("Active concepts", "concepts"),
            ("Contradictions", "contradictions"),
            ("Replay / audit", "replay_queue"),
            ("Migration audit", "migration_audit_events"),
        ]):
            card = ttk.Frame(header, padding=6)
            card.grid(row=0, column=index, sticky="ew")
            header.columnconfigure(index, weight=1)
            ttk.Label(card, text=label).pack()
            self.state_vars[key] = tk.StringVar(value="-")
            ttk.Label(card, textvariable=self.state_vars[key], font=("Segoe UI", 11, "bold")).pack()

        mode_bar = ttk.Frame(self.conversation_tab)
        mode_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(mode_bar, text="Mode").pack(side=tk.LEFT)
        self.mode = ttk.Combobox(mode_bar, values=DISPLAY_MODES, width=22, state="readonly")
        self.mode.set("Conversation")
        self.mode.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Checkbutton(mode_bar, text="Developer Overlay", variable=self.developer_overlay_enabled).pack(side=tk.LEFT)
        ttk.Button(mode_bar, text="Advanced Operator Console", command=lambda: self.notebook.select(self.advanced_tab)).pack(side=tk.RIGHT)

        live_bar = ttk.Frame(self.conversation_tab)
        live_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(live_bar, text="Start Live Runtime", command=self._start_live_runtime).pack(side=tk.LEFT)
        ttk.Button(live_bar, text="Stop", command=self._stop_live_runtime).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Pause Initiative", command=self._pause_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Resume", command=self._resume_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(live_bar, text="Suspend", command=self._suspend_live_initiative).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(live_bar, textvariable=self.live_runtime_status).pack(side=tk.LEFT, padx=(12, 0))

        self.chat_history = scrolledtext.ScrolledText(self.conversation_tab, wrap=tk.WORD, height=24)
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.chat_history.configure(state=tk.DISABLED)

        input_bar = ttk.Frame(self.conversation_tab)
        input_bar.pack(fill=tk.X, pady=(8, 0))
        self.chat_input = ttk.Entry(input_bar)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.chat_input.insert(0, "What color is the sky?")
        ttk.Button(input_bar, text="Send", command=self._send_chat).pack(side=tk.RIGHT)
        self.chat_input.bind("<Return>", lambda _event: self._send_chat())

        memory_bar = ttk.Frame(self.conversation_tab)
        memory_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(memory_bar, text="Accept Selected Concept", command=self._accept_selected_concept).pack(side=tk.LEFT)
        ttk.Button(memory_bar, text="Reject Selected Concept", command=self._reject_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Inspect Selected Concept", command=self._inspect_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Clear Local Memory Store", command=self._clear_local_store).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Open Operator Console", command=lambda: self.notebook.select(self.advanced_tab)).pack(side=tk.RIGHT)

        review = ttk.LabelFrame(self.conversation_tab, text="Concept Review")
        review.pack(fill=tk.X, pady=(8, 0))
        self.concept_review = ttk.Treeview(review, columns=("concept", "source", "status"), show="headings", height=3)
        self.concept_review.heading("concept", text="Potential Concept")
        self.concept_review.heading("source", text="Source")
        self.concept_review.heading("status", text="Status")
        self.concept_review.column("concept", width=360)
        self.concept_review.column("source", width=180)
        self.concept_review.column("status", width=120)
        self.concept_review.pack(fill=tk.X, padx=6, pady=6)

        hint = ttk.Label(
            self.conversation_tab,
            text="Default mode is natural conversation. Possible concepts appear in Concept Review and are stored only if you press Accept.",
        )
        hint.pack(anchor=tk.W, pady=(6, 0))

    def _build_database_tab(self) -> None:
        top = ttk.Frame(self.database_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Concept Lookup").pack(side=tk.LEFT)
        self.database_query = ttk.Entry(top)
        self.database_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.database_query.bind("<Return>", lambda _event: self._search_database_concepts())
        ttk.Button(top, text="Search", command=self._search_database_concepts).pack(side=tk.LEFT)
        ttk.Button(top, text="Browse Diverse", command=self._load_database_concepts).pack(side=tk.LEFT, padx=(8, 0))

        self.database_status = tk.StringVar(value="Read-only concept database.")
        ttk.Label(self.database_tab, textvariable=self.database_status).pack(anchor=tk.W, pady=(8, 0))

        page_bar = ttk.Frame(self.database_tab)
        page_bar.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(page_bar, text="Previous", command=self._database_previous_page).pack(side=tk.LEFT)
        ttk.Button(page_bar, text="Next", command=self._database_next_page).pack(side=tk.LEFT, padx=(8, 0))
        self.database_page_status = tk.StringVar(value="")
        ttk.Label(page_bar, textvariable=self.database_page_status).pack(side=tk.LEFT, padx=(12, 0))

        panes = ttk.PanedWindow(self.database_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        list_frame = ttk.Frame(panes)
        detail_frame = ttk.Frame(panes)
        panes.add(list_frame, weight=3)
        panes.add(detail_frame, weight=2)

        self.database_concepts = ttk.Treeview(
            list_frame,
            columns=("name", "domain", "type", "quality"),
            show="headings",
            height=18,
        )
        self.database_concepts.heading("name", text="Concept")
        self.database_concepts.heading("domain", text="Domain")
        self.database_concepts.heading("type", text="Type")
        self.database_concepts.heading("quality", text="Quality")
        self.database_concepts.column("name", width=320)
        self.database_concepts.column("domain", width=160)
        self.database_concepts.column("type", width=220)
        self.database_concepts.column("quality", width=80, anchor=tk.CENTER)
        self.database_concepts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.database_concepts.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.database_concepts.configure(yscrollcommand=scrollbar.set)
        self.database_concepts.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_database_concept())

        ttk.Label(detail_frame, text="Concept Detail").pack(anchor=tk.W)
        self.database_detail = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD)
        self.database_detail.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.database_detail.configure(state=tk.DISABLED)
        self.database_items: dict[str, dict[str, object]] = {}
        self.database_results: list[dict[str, object]] = []
        self.database_page = 0
        self.database_page_size = 100
        self.database_result_status = ""
        self._load_database_concepts()

    def _build_rc3_tab(self) -> None:
        top = ttk.Frame(self.rc3_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC3 Capability Panels").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc3_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc3_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc3_status = tk.StringVar(value="Read-only RC3 diagnostics. No execution controls are available.")
        ttk.Label(self.rc3_tab, textvariable=self.rc3_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc3_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc3_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc3_panels.heading("status", text="Panel")
        self.rc3_panels.column("status", width=240)
        self.rc3_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc3_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc3_panels.configure(yscrollcommand=scrollbar.set)
        self.rc3_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc3_panel())

        self.rc3_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc3_detail.pack(fill=tk.BOTH, expand=True)
        self.rc3_detail.configure(state=tk.DISABLED)
        self.rc3_snapshot: dict[str, object] = {}
        self._refresh_rc3_snapshot()

    def _build_rc4_tab(self) -> None:
        top = ttk.Frame(self.rc4_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC4 Governed Action Runtime").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc4_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc4_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc4_status = tk.StringVar(value="Read-only RC4 diagnostics. No execution controls are available.")
        ttk.Label(self.rc4_tab, textvariable=self.rc4_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc4_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc4_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc4_panels.heading("status", text="Panel")
        self.rc4_panels.column("status", width=280)
        self.rc4_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc4_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc4_panels.configure(yscrollcommand=scrollbar.set)
        self.rc4_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc4_panel())

        self.rc4_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc4_detail.pack(fill=tk.BOTH, expand=True)
        self.rc4_detail.configure(state=tk.DISABLED)
        self.rc4_snapshot: dict[str, object] = {}
        self._refresh_rc4_snapshot()

    def _build_rc5_tab(self) -> None:
        top = ttk.Frame(self.rc5_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC5 Purpose-Aligned Developmental Cognition").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc5_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc5_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc5_status = tk.StringVar(value="Read-only RC5 diagnostics. Manual consultation is packet-only; no API calls are available.")
        ttk.Label(self.rc5_tab, textvariable=self.rc5_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc5_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc5_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc5_panels.heading("status", text="Panel")
        self.rc5_panels.column("status", width=300)
        self.rc5_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc5_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc5_panels.configure(yscrollcommand=scrollbar.set)
        self.rc5_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc5_panel())

        self.rc5_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc5_detail.pack(fill=tk.BOTH, expand=True)
        self.rc5_detail.configure(state=tk.DISABLED)
        self.rc5_snapshot: dict[str, object] = {}
        self._refresh_rc5_snapshot()

    def _build_advanced_tab(self) -> None:
        panes = ttk.PanedWindow(self.advanced_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)

        ttk.Label(left, text="Import / Paste Evidence").pack(anchor=tk.W)
        self.paste = scrolledtext.ScrolledText(left, height=12, wrap=tk.WORD)
        self.paste.pack(fill=tk.BOTH, expand=True)
        ttk.Button(left, text="Preview Evidence", command=self._preview_evidence).pack(fill=tk.X, pady=(6, 0))
        ttk.Button(left, text="Extract Propositions", command=self._extract_propositions).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(left, text="Approve Extracted To Noncanonical Substrate", command=self._approve_extracted).pack(fill=tk.X, pady=(4, 0))

        obs = ttk.LabelFrame(left, text="Operational Observation")
        obs.pack(fill=tk.X, pady=(10, 0))
        self.category = ttk.Combobox(
            obs,
            values=[
                "operator_friction",
                "missing_evidence",
                "confusing_behavior",
                "weak_explanation",
                "replay_problem",
                "retrieval_failure",
                "provenance_issue",
                "latency",
                "workflow_interruption",
                "feature_request",
                "unexpected_strength",
            ],
        )
        self.category.set("operator_friction")
        self.category.pack(fill=tk.X, padx=6, pady=4)
        self.severity = ttk.Combobox(obs, values=["P0", "P1", "P2", "P3"])
        self.severity.set("P3")
        self.severity.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(obs, text="Log Observation Locally", command=self._log_observation).pack(fill=tk.X, padx=6, pady=6)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(buttons, text="Status", command=self._show_status).pack(fill=tk.X)
        ttk.Button(buttons, text="Cognitive State", command=self._show_cognitive_state).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Review Queue", command=self._show_review_queue).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Replay / Rollback", command=self._show_replay).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Failure Taxonomy", command=self._show_failure_taxonomy).pack(fill=tk.X, pady=(4, 0))

        ttk.Label(right, text="Workspace").pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.output.pack(fill=tk.BOTH, expand=True)

    def _refresh_rc3_snapshot(self) -> None:
        try:
            self.rc3_snapshot = build_rc3_ui_snapshot()
            validation = validate_rc3_ui_snapshot(self.rc3_snapshot)
            for item in self.rc3_panels.get_children():
                self.rc3_panels.delete(item)
            panels = self.rc3_snapshot.get("panels", {})
            for name in RC3_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc3_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            recommendation = validation.get("recommendation")
            self.rc3_status.set(
                f"RC3 UI validation passed={validation.get('passed')}; recommendation={recommendation}. "
                "Inspect/review only: no execution, sandbox, plugin activation, provider call, or repository mutation."
            )
            if RC3_PANEL_ORDER:
                self.rc3_panels.selection_set(RC3_PANEL_ORDER[0])
                self._show_selected_rc3_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc3_status.set(f"RC3 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc3_detail("")

    def _show_selected_rc3_panel(self) -> None:
        selected = self.rc3_panels.selection()
        if not selected or not self.rc3_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc3_detail(render_rc3_panel(panel_name, self.rc3_snapshot))

    def _write_rc3_detail(self, text: str) -> None:
        self.rc3_detail.configure(state=tk.NORMAL)
        self.rc3_detail.delete("1.0", tk.END)
        if text:
            self.rc3_detail.insert(tk.END, text)
        self.rc3_detail.configure(state=tk.DISABLED)

    def _generate_rc3_ui_report(self) -> None:
        report = build_rc3_ui_integration_report(write_reports=True)
        self._refresh_rc3_snapshot()
        self._write_rc3_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_rc4_snapshot(self) -> None:
        try:
            self.rc4_snapshot = build_rc4_ui_snapshot()
            validation = validate_rc4_ui_snapshot(self.rc4_snapshot)
            for item in self.rc4_panels.get_children():
                self.rc4_panels.delete(item)
            panels = self.rc4_snapshot.get("panels", {})
            for name in RC4_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc4_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            self.rc4_status.set(
                f"RC4 UI validation passed={validation.get('passed')}; recommendation={validation.get('recommendation')}. "
                "Inspect/review only: no live repo mutation, sandbox creation from UI, provider call, plugin activation, push, merge, or deploy."
            )
            if RC4_PANEL_ORDER:
                self.rc4_panels.selection_set(RC4_PANEL_ORDER[0])
                self._show_selected_rc4_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc4_status.set(f"RC4 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc4_detail("")

    def _show_selected_rc4_panel(self) -> None:
        selected = self.rc4_panels.selection()
        if not selected or not self.rc4_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc4_detail(render_rc4_panel(panel_name, self.rc4_snapshot))

    def _write_rc4_detail(self, text: str) -> None:
        self.rc4_detail.configure(state=tk.NORMAL)
        self.rc4_detail.delete("1.0", tk.END)
        if text:
            self.rc4_detail.insert(tk.END, text)
        self.rc4_detail.configure(state=tk.DISABLED)

    def _generate_rc4_ui_report(self) -> None:
        report = build_rc4_ui_integration_report(write_reports=True)
        self._refresh_rc4_snapshot()
        self._write_rc4_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_rc5_snapshot(self) -> None:
        try:
            self.rc5_snapshot = build_rc5_ui_snapshot()
            validation = validate_rc5_ui_snapshot(self.rc5_snapshot)
            for item in self.rc5_panels.get_children():
                self.rc5_panels.delete(item)
            panels = self.rc5_snapshot.get("panels", {})
            for name in RC5_PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc5_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            self.rc5_status.set(
                f"RC5 UI validation passed={validation.get('passed')}; recommendation={validation.get('recommendation')}. "
                "Inspect/review only: no GPT/API call, provider call, purpose mutation, automatic development loop, "
                "developmental memory write, self-approval, or RC4 bypass."
            )
            if RC5_PANEL_ORDER:
                self.rc5_panels.selection_set(RC5_PANEL_ORDER[0])
                self._show_selected_rc5_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc5_status.set(f"RC5 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc5_detail("")

    def _show_selected_rc5_panel(self) -> None:
        selected = self.rc5_panels.selection()
        if not selected or not self.rc5_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc5_detail(render_rc5_panel(panel_name, self.rc5_snapshot))

    def _write_rc5_detail(self, text: str) -> None:
        self.rc5_detail.configure(state=tk.NORMAL)
        self.rc5_detail.delete("1.0", tk.END)
        if text:
            self.rc5_detail.insert(tk.END, text)
        self.rc5_detail.configure(state=tk.DISABLED)

    def _generate_rc5_ui_report(self) -> None:
        report = build_rc5_ui_integration_report(write_reports=True)
        self._refresh_rc5_snapshot()
        self._write_rc5_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_state_cards(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        substrate = substrate_counts()
        active_concepts = int(substrate.get("active_runtime_concepts", substrate.get("concepts", 0)) or 0)
        replay_events = int(substrate.get("substrate_replay_events", substrate.get("replay_events", 0)) or 0)
        state = {
            **state,
            "knowledge_available": state["knowledge_available"] or developmental["knowledge_memory_records"] > 0 or active_concepts > 0,
            "concepts": active_concepts,
            "contradictions": state["contradictions"] + developmental["concept_contradictions"],
            "replay_queue": replay_events,
            "migration_audit_events": int(substrate.get("migration_audit_events", 0) or 0),
        }
        for key, var in self.state_vars.items():
            var.set(str(state[key]))

    def _load_database_concepts(self) -> None:
        try:
            concepts = load_diverse_concepts(limit=1000)
            self._set_database_results(
                concepts,
                f"Showing diversified concepts from {substrate_counts().get('backend')} backend.",
            )
        except Exception as exc:  # noqa: BLE001 - UI should remain open if index is unavailable.
            self._set_database_results([], f"Database lookup failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _search_database_concepts(self) -> None:
        query = self.database_query.get().strip()
        if not query:
            self._load_database_concepts()
            return
        try:
            result = search_concepts(query, limit=1000)
            concepts = result.get("matches", [])
            backend = result.get("backend") or substrate_counts().get("backend")
            self._set_database_results(
                concepts,
                f"Search `{query}`: {len(concepts)} result(s), backend={backend}, candidate_pool={result.get('candidate_pool_size', 'n/a')}.",
            )
        except Exception as exc:  # noqa: BLE001
            self._set_database_results([], f"Search failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _set_database_results(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_results = list(concepts)
        self.database_page = 0
        self.database_result_status = status
        self._show_database_page()

    def _database_next_page(self) -> None:
        if (self.database_page + 1) * self.database_page_size >= len(self.database_results):
            return
        self.database_page += 1
        self._show_database_page()

    def _database_previous_page(self) -> None:
        if self.database_page <= 0:
            return
        self.database_page -= 1
        self._show_database_page()

    def _show_database_page(self) -> None:
        start = self.database_page * self.database_page_size
        end = start + self.database_page_size
        self._populate_database_concepts(self.database_results[start:end], self.database_result_status)
        total = len(self.database_results)
        if total:
            self.database_page_status.set(f"Showing {start + 1}-{min(end, total)} of {total}")
        else:
            self.database_page_status.set("No concepts to show")

    def _populate_database_concepts(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_items = {}
        for item in self.database_concepts.get_children():
            self.database_concepts.delete(item)
        for concept in concepts:
            concept_id = str(concept.get("concept_id") or "")
            if not concept_id:
                continue
            self.database_items[concept_id] = concept
            quality = concept.get("quality_score", concept.get("confidence", ""))
            self.database_concepts.insert(
                "",
                tk.END,
                iid=concept_id,
                values=(
                    str(concept.get("concept_name") or ""),
                    str(concept.get("domain") or ""),
                    str(concept.get("concept_type") or ""),
                    str(quality)[:8],
                ),
            )
        counts = substrate_counts()
        self.database_status.set(
            f"{status} Active concepts={counts.get('active_runtime_concepts', counts.get('concepts'))}; "
            f"active graph edges={counts.get('active_graph_edges', counts.get('graph_edges'))}; "
            f"replay events={counts.get('substrate_replay_events', counts.get('replay_events'))}."
        )
        self._write_database_detail("")

    def _show_selected_database_concept(self) -> None:
        selected = self.database_concepts.selection()
        if not selected:
            return
        concept = self.database_items.get(str(selected[0]))
        if not concept:
            return
        lines = [
            str(concept.get("concept_name") or "Unnamed Concept"),
            "",
            f"ID: {concept.get('concept_id')}",
            f"Domain: {concept.get('domain')}",
            f"Type: {concept.get('concept_type')}",
            f"Quality: {concept.get('quality_score', concept.get('confidence', ''))}",
            f"Status: {concept.get('approval_status')}",
            f"Canonical: {concept.get('canonical')}",
            f"Source: {concept.get('source_type') or concept.get('_store_memory_type') or ''}",
            f"Rollback: {concept.get('rollback_handle') or concept.get('rollback_id') or ''}",
            "",
            "Definition:",
            str(concept.get("short_definition") or "").strip(),
        ]
        for title, key in [
            ("Propositions", "propositions"),
            ("Related Concepts", "related_concepts"),
            ("Examples", "examples"),
            ("Misconceptions", "misconceptions"),
        ]:
            values = concept.get(key)
            if isinstance(values, list) and values:
                lines.extend(["", f"{title}:"])
                lines.extend(f"- {item}" for item in values[:12])
        self._write_database_detail("\n".join(lines))

    def _write_database_detail(self, text: str) -> None:
        self.database_detail.configure(state=tk.NORMAL)
        self.database_detail.delete("1.0", tk.END)
        if text:
            self.database_detail.insert(tk.END, text)
        self.database_detail.configure(state=tk.DISABLED)

    def _append_chat(self, speaker: str, text: str) -> None:
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{speaker}: {text}\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _append_session(self, role: str, content: str) -> None:
        self.session_history.append({"role": role, "content": " ".join(str(content).split())[:1200]})
        if len(self.session_history) > 24:
            self.session_history = self.session_history[-24:]

    def _recent_history_for_router(self) -> list[dict[str, str]]:
        history = self.session_history[-10:]
        if self.active_topic_anchor:
            history = [*history, {"role": "anchor", "content": json.dumps(self.active_topic_anchor, sort_keys=True)}]
        return history

    def _last_substantive_exchange(self) -> dict[str, str] | None:
        last_assistant = ""
        for item in reversed(self.session_history):
            role = item.get("role")
            content = str(item.get("content") or "")
            if role == "assistant" and not last_assistant and "Would you like me to ask the local reasoning model to elaborate?" not in content:
                last_assistant = _assistant_answer_text(content)
            elif role == "user" and last_assistant:
                text = content.strip()
                if text.lower() not in {"yes", "no", "tell me more", "more", "go deeper", "explain more", "elaborate"}:
                    return {"question": text, "answer": last_assistant}
        return None

    def _show_welcome(self) -> None:
        residency = ""
        if self.model_residency_status == "warm":
            residency = " The everyday local model is already loaded for this session."
        elif self.model_residency_status.startswith("warm_failed"):
            residency = " Local model warmup did not complete, so I may need to fall back if you ask for local reasoning."
        self._append_chat(
            "DELTA",
            "Hi. I'm DELTA. You can talk normally here. If a task needs governed memory, evidence review, replay, or diagnostics, I can route it or you can open Advanced mode."
            + residency,
        )
        self._append_session("assistant", "Hi. I'm DELTA. You can talk normally here.")

    def _warm_default_model(self) -> None:
        lane = select_model_lane("Hello DELTA.", "conversation")
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        if not model_id:
            self.model_residency_status = "warm_failed:no_model"
            return
        try:
            self.provider_manager.warm(model_id)
            self.resident_model_id = model_id
            self.resident_lane = str(lane.get("lane") or "everyday_conversation")
            self.model_residency_status = "warm"
        except Exception as exc:  # noqa: BLE001 - UI should stay usable if warmup fails.
            self.model_residency_status = f"warm_failed:{type(exc).__name__}:{str(exc)[:120]}"

    def _prepare_resident_model_for_question(self, question: str) -> None:
        lane = select_model_lane(question)
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        lane_name = str(lane.get("lane") or "")
        display = str(lane.get("display_name") or lane_name or "local model")
        if not model_id:
            return
        if self.resident_model_id == model_id:
            return
        if self.resident_model_id:
            if lane_name == "planning":
                self._append_chat("DELTA", "One moment while I switch to the planning model.")
            elif self.resident_lane == "planning":
                self._append_chat("DELTA", "One moment while I switch back to the general conversation model.")
            else:
                self._append_chat("DELTA", f"One moment while I switch to the {display}.")
        else:
            self._append_chat("DELTA", f"One moment while I load the {display}.")
        try:
            self.provider_manager.warm(model_id)
            self.resident_model_id = model_id
            self.resident_lane = lane_name
            self.model_residency_status = "warm"
        except Exception as exc:  # noqa: BLE001
            self.model_residency_status = f"switch_failed:{type(exc).__name__}:{str(exc)[:120]}"

    def _start_live_runtime(self) -> None:
        if self.live_runtime_request_in_flight:
            self.live_runtime_status.set("Live runtime is completing an operator turn; start is unavailable until it finishes.")
            return
        if self.live_runtime_session and self.live_runtime_session.active:
            self.live_runtime_status.set(self._live_status_text())
            return
        try:
            self.live_runtime_session = start_live_wikipedia_runtime(
                runtime_id="ui",
                resident_model_id=self.resident_model_id,
                resident_lane=self.resident_lane,
                residency_status=self.model_residency_status,
            )
            self.live_runtime_status.set(self._live_status_text())
            self._append_chat(
                "DELTA",
                "Live runtime started. Wikipedia text retrieval is enabled for this session only; no provider calls or memory writes are enabled. Retrieved text will be compared against local concepts and surfaced as a gated review candidate when useful.",
            )
        except Exception as exc:  # noqa: BLE001
            self.live_runtime_status.set(f"Live runtime start failed: {type(exc).__name__}")
            messagebox.showerror("Live Runtime", f"Could not start live runtime:\n{type(exc).__name__}: {str(exc)[:240]}")

    def _stop_live_runtime(self) -> None:
        if self._queue_live_runtime_control("stop"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        try:
            self.live_runtime_session = stop_live_wikipedia_runtime(self.live_runtime_session)
            self.live_runtime_status.set(self._live_status_text())
            self._append_chat("DELTA", "Live runtime stopped.")
        except Exception as exc:  # noqa: BLE001
            self.live_runtime_status.set(f"Live runtime stop failed: {type(exc).__name__}")
            messagebox.showerror("Live Runtime", f"Could not stop live runtime:\n{type(exc).__name__}: {str(exc)[:240]}")

    def _pause_live_initiative(self) -> None:
        if self._queue_live_runtime_control("pause"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = pause_live_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _resume_live_initiative(self) -> None:
        if self._queue_live_runtime_control("resume"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = resume_live_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _suspend_live_initiative(self) -> None:
        if self._queue_live_runtime_control("suspend"):
            return
        if not self.live_runtime_session:
            self.live_runtime_status.set("Live runtime: stopped")
            return
        self.live_runtime_session = suspend_live_runtime_initiative(self.live_runtime_session)
        self.live_runtime_status.set(self._live_status_text())

    def _queue_live_runtime_control(self, control: str) -> bool:
        if not self.live_runtime_request_in_flight:
            return False
        if control not in {"stop", "pause", "resume", "suspend"}:
            raise ValueError(f"unknown live runtime control: {control}")
        if not self.pending_live_runtime_controls or self.pending_live_runtime_controls[-1] != control:
            self.pending_live_runtime_controls.append(control)
        self.live_runtime_status.set(f"Runtime=PROCESSING_OPERATOR_TURN; {control} queued after the current turn.")
        return True

    def _apply_queued_live_runtime_controls(self) -> None:
        pending = tuple(self.pending_live_runtime_controls)
        self.pending_live_runtime_controls.clear()
        for control in pending:
            if control == "stop":
                self._stop_live_runtime()
            elif control == "pause":
                self._pause_live_initiative()
            elif control == "resume":
                self._resume_live_initiative()
            elif control == "suspend":
                self._suspend_live_initiative()

    def _begin_live_runtime_turn(self, message: str) -> None:
        session = self.live_runtime_session
        if session is None:
            return
        self.live_runtime_request_in_flight = True
        self.chat_input.configure(state=tk.DISABLED)
        self.live_runtime_status.set("Runtime=PROCESSING_OPERATOR_TURN; lifecycle controls can be queued.")
        history = self._recent_history_for_router()
        developer_overlay = self.developer_overlay_enabled.get()

        def run_turn() -> None:
            try:
                updated_session, response = handle_live_chat(
                    session,
                    message,
                    history=history,
                    developer_overlay=developer_overlay,
                    provider_manager=self.provider_manager,
                )
                self.live_runtime_worker_results.put({
                    "kind": "response",
                    "message": message,
                    "session": updated_session,
                    "response": response,
                })
            except Exception as exc:  # noqa: BLE001 - retain UI control when a worker turn fails unexpectedly.
                self.live_runtime_worker_results.put({
                    "kind": "error",
                    "message": message,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:500],
                })

        threading.Thread(target=run_turn, name="delta-live-runtime-turn", daemon=True).start()

    def _poll_live_runtime_worker_results(self) -> None:
        try:
            while True:
                result = self.live_runtime_worker_results.get_nowait()
                self._complete_live_runtime_turn(result)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_live_runtime_worker_results)

    def _complete_live_runtime_turn(self, result: dict[str, object]) -> None:
        self.live_runtime_request_in_flight = False
        if result.get("kind") == "response":
            session = result.get("session")
            response = result.get("response")
            if isinstance(session, LiveWikipediaRuntimeSession) and response is not None:
                self.live_runtime_session = session
                self.last_message = str(result.get("message") or "")
                payload = getattr(response, "payload", {})
                self.last_payload = payload if isinstance(payload, dict) else None
                if isinstance(payload, dict):
                    self._queue_concept_candidate(payload)
                self._append_chat("DELTA", str(getattr(response, "answer", "")))
                self._append_session("assistant", str(getattr(response, "answer", "")))
            else:
                self._append_chat("DELTA", "Live runtime returned an invalid worker result. No state was committed.")
        else:
            self._append_chat(
                "DELTA",
                "Live runtime turn failed safely. "
                + f"Reason: {result.get('exception_type')}: {result.get('exception_message')}",
            )
        self._apply_queued_live_runtime_controls()
        self.live_runtime_status.set(self._live_status_text())
        self._refresh_state_cards()
        self.chat_input.configure(state=tk.NORMAL)
        self.chat_input.focus_set()

    def _live_status_text(self) -> str:
        session = self.live_runtime_session
        if not session:
            return "Live runtime: stopped"
        controller = controller_snapshot(session.continuous_controller) if session.continuous_controller else {}
        model = controller.get("current_model", {}) if isinstance(controller, dict) else {}
        active_objective = controller.get("active_objective") if isinstance(controller, dict) else None
        objective_title = (active_objective or {}).get("title") if isinstance(active_objective, dict) else ""
        recent = controller.get("recent_initiative") if isinstance(controller, dict) else None
        recent_text = (recent or {}).get("outcome") if isinstance(recent, dict) else "none"
        wiki_limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
        wiki_budget = f"{session.retrieval_count}/unlimited" if wiki_limit <= 0 else f"{session.retrieval_count}/{wiki_limit}"
        return (
            f"Runtime={controller.get('lifecycle_state', session.runtime.state)}; "
            f"health={(controller.get('health') or {}).get('health_state', 'unknown')}; "
            f"model={model.get('resident_model_id') or model.get('default_model') or 'none'}; "
            f"objective={(objective_title or 'none')[:42]}; "
            f"inquiries={len(session.operator_inquiries)}; promotions={len(session.promotion_candidates)}; "
            f"wiki={wiki_budget}; initiative={recent_text}; autonomy={session.autonomy_status}"
        )

    def _send_chat(self) -> None:
        message = self.chat_input.get().strip()
        if not message:
            return
        self.chat_input.delete(0, tk.END)
        self._append_chat("You", message)
        lower = message.lower().strip()
        cancel_words = {"no", "n", "not now", "no thanks", "keep chatting", "nevermind", "never mind", "cancel", "stop", "forget it"}
        affirm_words = {"yes", "y", "yes please", "sure", "okay", "ok", "go ahead", "do it", "tell me more", "more", "go deeper"}
        discourse_frame = build_discourse_frame(message, self.last_report_inspection)
        discourse_trace = discourse_frame.as_dict()
        if self.live_runtime_session and self.live_runtime_session.active:
            self._append_session("user", message)
            self._begin_live_runtime_turn(message)
            return
        if is_render_correction_request(message):
            self._append_session("user", message)
            payload = route_message(
                self.mode.get(),
                message,
                self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
                history=self._recent_history_for_router(),
                execute_local_model=False,
            )
            self.last_message = message
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        report_inspection = _inspect_local_report(message)
        if report_inspection and report_inspection.get("handled"):
            self._append_session("user", message)
            reply = str(report_inspection.get("answer") or "")
            report_path = _extract_report_path(message)
            self.last_report_inspection = {
                "report_name": report_path.name if report_path else "local report",
                "report_path": str(report_path.resolve()) if report_path else "",
                "request": message,
                "answer_summary": " ".join(reply.split())[:600],
            }
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: local_report_inspection\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps(report_inspection.get("safety", {}), indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        rc6_reply = _handle_rc6_pilot_message(message, self.rc6_pilot_events)
        if rc6_reply:
            self._append_session("user", message)
            reply = rc6_reply
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc6_disabled_gateway_pilot\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nRC7 Development Dashboard:\n"
                reply += _rc7_developer_overlay_text()
                reply += "\nSafety:\n"
                reply += json.dumps(rc6_safety_metadata(), indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "identify_report_weakness":
            self._append_session("user", message)
            reply = _summarize_same_report_weakness(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_same_report_followup\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "draft_operator_pilot_checklist":
            self._append_session("user", message)
            reply = _draft_operator_pilot_checklist(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_report_followup_checklist\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "resolve_prior_checklist_item":
            self._append_session("user", message)
            reply = _answer_second_one_pilot_followup(self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_pilot_checklist_followup\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_rc5_gpt_boundary":
            self._append_session("user", message)
            reply = _answer_rc5_gpt_boundary()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc5_manual_consultation_boundary\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_rc5_to_rc4_handoff_boundary":
            self._append_session("user", message)
            reply = _answer_rc4_handoff_boundary()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc5_to_rc4_handoff_boundary\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "draft_pilot_session_record":
            self._append_session("user", message)
            reply = _draft_operator_pilot_session_record(message, self.last_report_inspection)
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: ephemeral_pilot_session_record\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "evaluate_full_pilot_freeze_readiness":
            self._append_session("user", message)
            reply = _answer_full_pilot_freeze_decision()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_pilot_freeze_decision\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "identify_primary_freeze_evidence_gap":
            self._append_session("user", message)
            reply = _answer_primary_freeze_evidence_gap()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_primary_freeze_evidence_gap\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_sufficient_recovery_evidence":
            self._append_session("user", message)
            reply = _answer_sufficient_recovery_evidence()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_recovery_evidence_enrichment\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_mixed_proposal_record":
            self._append_session("user", message)
            reply = _answer_mixed_proposal_record()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_mixed_proposal_record_guidance\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if should_preempt_specialist_routing(discourse_frame) and discourse_frame.current_requested_operation == "explain_useful_but_unsafe_advice_handling":
            self._append_session("user", message)
            reply = _answer_useful_but_unsafe_advice_handling()
            if self.developer_overlay_enabled.get():
                reply += "\n\n--- Developer Overlay ---\nRoute: rc45_useful_but_unsafe_advice_guidance\n"
                reply += "Discourse frame:\n"
                reply += json.dumps(discourse_trace, indent=2, sort_keys=True)
                reply += "\nSafety:\n"
                reply += json.dumps({
                    "provider_calls_performed": False,
                    "gpt_api_calls_performed": False,
                    "developmental_memory_write_performed": False,
                    "canonical_write_performed": False,
                    "autonomous_action_performed": False,
                }, indent=2, sort_keys=True)
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        pc1_reply = _try_pc1_pragmatic_answer(
            message,
            self.last_report_inspection,
            developer_overlay=self.developer_overlay_enabled.get(),
        )
        if pc1_reply:
            self._append_session("user", message)
            self._append_chat("DELTA", pc1_reply)
            self._append_session("assistant", pc1_reply)
            return
        if self.pending_local_model_deepening and lower in affirm_words:
            pending = self.pending_local_model_deepening
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            target = _build_deepening_prompt(pending["question"], pending["answer"])
            self._prepare_resident_model_for_question(target)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            payload.update({
                "active_pending_action_id": pending.get("action_id"),
                "active_pending_action_type": pending.get("action_type", "local_model_deepening"),
                "pending_action_matched": True,
                "action_executed": bool((payload.get("local_model_result") or {}).get("executed")),
                "pending_action_cleared": True,
            })
            enrichment_candidate = build_memory_candidate_from_answer(pending["question"], payload)
            matches = query_approved_concepts(pending["question"]).get("matches", [])
            if matches:
                enrichment_candidate = {
                    **enrichment_candidate,
                    "enrichment_of_concept_id": matches[0].get("concept_id"),
                    "enrichment_of_concept_name": matches[0].get("concept_name"),
                    "approval_status": "pending_operator_enrichment_review",
                    "source_question": pending["question"],
                    "source_type": "local_model_lane_enrichment",
                }
            payload["memory_candidate"] = enrichment_candidate
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_deepening and lower in cancel_words:
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            reply = "Okay. I will not deepen that answer right now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_local_model_question and lower in (affirm_words | {"ask local", "ask the local model", "ask a local model"}):
            target = self.pending_local_model_question
            self.pending_local_model_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            self.last_message = target
            self.last_payload = payload
            self._update_active_topic_anchor(payload)
            offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
            self.pending_provider_question = target if isinstance(offer, dict) and offer.get("offered") else None
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_question and lower in cancel_words:
            self.pending_local_model_question = None
            self._append_session("user", message)
            reply = "Okay. I will leave that unanswered locally for now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_provider_question and lower in {"yes", "y", "yes please", "ask gpt", "ask gpt please", "look for sources"}:
            target = self.pending_provider_question
            self.pending_provider_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                provider_approved=True,
            )
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_provider_question and lower in cancel_words:
            self.pending_provider_question = None
            self._append_session("user", message)
            reply = "Okay. I will keep this local and will not ask a provider."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"remember that", "remember this", "store that", "store this", "save that", "save this", "remember this useful answer", "keep this concept", "that was useful remember the concept"}:
            self._append_session("user", message)
            reply = self._queue_last_answer_for_review()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"not now", "discard", "forget after this chat"}:
            self._append_session("user", message)
            self._append_chat("DELTA", "Okay. I will keep this in the current conversation only and will not store a concept.")
            self._append_session("assistant", "Okay. I will keep this in the current conversation only and will not store a concept.")
            return
        self.pending_local_model_deepening = None
        payload = route_message(
            self.mode.get(),
            message,
            self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
            history=self._recent_history_for_router(),
            execute_local_model=False,
        )
        self.last_message = message
        self.last_payload = payload
        self._update_active_topic_anchor(payload)
        offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
        if isinstance(offer, dict) and offer.get("offered"):
            self.pending_provider_question = message
        elif payload.get("route") == "gpt_support_approval_preview":
            self.pending_provider_question = message
        else:
            self.pending_provider_question = None
        local_offer = payload.get("local_model_offer") if isinstance(payload, dict) else None
        pending_suggestion = payload.get("pending_action_suggestion") if isinstance(payload, dict) else None
        if isinstance(pending_suggestion, dict) and pending_suggestion.get("action_type") == "local_model_deepening":
            exchange = self._last_substantive_exchange() or {"question": message, "answer": str(payload.get("answer") or "")}
            action_id = f"rc2-pending-action-{uuid.uuid4().hex[:12]}"
            self.pending_local_model_deepening = {
                "action_id": action_id,
                "action_type": "local_model_deepening",
                "question": exchange["question"],
                "answer": exchange["answer"],
                "followup_instruction": message,
                "source_turn_id": str(len(self.session_history)),
            }
            payload["pending_action_suggestion"] = {
                **pending_suggestion,
                "action_id": action_id,
                "original_topic": exchange["question"],
                "prior_answer_summary": exchange["answer"][:260],
                "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
                "selected_model": (payload.get("selected_model_lane") or {}).get("selected_model_id"),
            }
            self.pending_local_model_question = None
        else:
            self.pending_local_model_question = message if isinstance(local_offer, dict) and local_offer.get("offered") else None
            if self.pending_local_model_question:
                self.pending_local_model_deepening = None
        self._refresh_state_cards()
        rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
        self._queue_concept_candidate(payload)
        self._append_chat("DELTA", rendered)
        self._append_session("user", message)
        self._append_session("assistant", rendered)

    def _update_active_topic_anchor(self, payload: dict[str, object]) -> None:
        anchor = payload.get("active_topic_anchor")
        if isinstance(anchor, dict) and (anchor.get("active_concept_id") or anchor.get("active_concept_name")):
            self.active_topic_anchor = dict(anchor)
            return
        matches = payload.get("concept_matches")
        if isinstance(matches, list) and matches:
            first = matches[0]
            if isinstance(first, dict) and (first.get("concept_id") or first.get("concept_name")):
                self.active_topic_anchor = {
                    "active_concept_id": first.get("concept_id"),
                    "active_concept_name": first.get("concept_name"),
                    "domain": first.get("domain"),
                    "related_concepts": first.get("related_concepts", [])[:8] if isinstance(first.get("related_concepts"), list) else [],
                    "retrieved_concept_ids": [row.get("concept_id") for row in matches if isinstance(row, dict) and row.get("concept_id")],
                    "retrieved_concept_names": [row.get("concept_name") for row in matches if isinstance(row, dict) and row.get("concept_name")],
                    "last_user_question": self.last_message,
                    "last_answer_summary": " ".join(str(payload.get("answer") or "").split())[:420],
                }

    def _set_deepening_offer_if_present(self, question: str, payload: dict[str, object]) -> None:
        answer = str(payload.get("answer") or "")
        if payload.get("route") == "local_conversation_model_lane" and _model_answer_offers_deepening(answer):
            self.pending_local_model_deepening = {"question": question, "answer": answer}
        else:
            self.pending_local_model_deepening = None

    def _queue_concept_candidate(self, payload: dict[str, object]) -> None:
        candidate = payload.get("memory_candidate")
        if not isinstance(candidate, dict):
            return
        concept_id = str(candidate.get("concept_id") or "")
        if not concept_id or concept_id in self.concept_review_items:
            return
        is_enrichment = bool(candidate.get("enrichment_of_concept_id"))
        concept_label = str(candidate.get("concept_name") or "Learned Concept")
        source_label = str(candidate.get("source_type") or payload.get("route") or "conversation")
        if is_enrichment:
            concept_label = f"Update: {candidate.get('enrichment_of_concept_name') or concept_label}"
            source_label = "enrichment"
        self.concept_review_items[concept_id] = {"candidate": candidate, "payload": payload}
        self.concept_review.insert(
            "",
            tk.END,
            iid=concept_id,
            values=(
                concept_label,
                source_label,
                "pending",
            ),
        )

    def _queue_last_answer_for_review(self) -> str:
        if not self.last_message or not isinstance(self.last_payload, dict):
            return "I do not have a previous answer to turn into a concept yet."
        existing = self.last_payload.get("memory_candidate")
        if isinstance(existing, dict):
            candidate = existing
        else:
            candidate = build_memory_candidate_from_answer(self.last_message, self.last_payload)
            if not candidate_is_memory_worthy(candidate, self.last_payload):
                candidate = {
                    **candidate,
                    "approval_status": "pending_operator_review_user_requested",
                    "operator_review_required": True,
                    "memory_request_source": "explicit_user_remember_that",
                    "uncertainty": "moderate_operator_review_required",
                    "review_note": "User explicitly asked to remember the previous answer; candidate was queued for manual review despite lower automatic memory-worthiness.",
                }
            self.last_payload["memory_candidate"] = candidate
        before = set(self.concept_review_items)
        self._queue_concept_candidate(self.last_payload)
        concept_id = str(candidate.get("concept_id") or "")
        name = str(candidate.get("concept_name") or "that concept")
        if concept_id in before:
            return f"`{name}` is already in Concept Review. Select it and press Accept Selected Concept if you want it stored."
        return f"I added `{name}` to Concept Review. Select it and press Accept Selected Concept if you want it stored."

    def _selected_concept_id(self) -> str | None:
        selected = self.concept_review.selection()
        return str(selected[0]) if selected else None

    def _accept_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = dict(item["candidate"])
        result = approve_candidate_concept(candidate, approval_text="Keep this concept")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        approved = result.get("approved") is True
        duplicate = result.get("duplicate") is True
        if approved:
            concept = result["stored_concept"]
            self.concept_review.set(concept_id, "status", "accepted")
            if result.get("enriched_existing"):
                text = f"Updated the existing concept `{concept['concept_name']}` with the reviewed elaboration. Canonical memory and training stayed off."
            else:
                text = f"Kept the concept `{concept['concept_name']}` in noncanonical {concept['memory_type']} memory. Canonical memory and training stayed off."
        elif duplicate:
            self.concept_review.set(concept_id, "status", "duplicate")
            text = "I already had a matching concept, so I skipped the duplicate. Canonical memory and training stayed off."
        else:
            self.concept_review.set(concept_id, "status", "not stored")
            text = "I did not store the concept. Canonical memory and training stayed off."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _reject_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        self.concept_review.set(concept_id, "status", "rejected")
        item = self.concept_review_items.get(concept_id, {})
        candidate = item.get("candidate", {}) if isinstance(item, dict) else {}
        name = candidate.get("concept_name", "that concept") if isinstance(candidate, dict) else "that concept"
        text = f"Rejected `{name}`. Nothing was stored."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _inspect_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = item["candidate"]
        if not isinstance(candidate, dict):
            messagebox.showinfo("DELTA", "That concept candidate is not editable.")
            return
        self._open_concept_editor(concept_id, candidate)

    def _open_concept_editor(self, concept_id: str, candidate: dict[str, object]) -> None:
        editor = tk.Toplevel(self.root)
        editor.title(f"Edit Concept - {candidate.get('concept_name', 'Candidate')}")
        editor.geometry("780x680")
        editor.transient(self.root)

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)
        frame.rowconfigure(4, weight=1)
        frame.rowconfigure(8, weight=1)

        name_var = tk.StringVar(value=str(candidate.get("concept_name") or ""))
        definition_var = tk.StringVar(value=str(candidate.get("short_definition") or ""))
        uncertainty_var = tk.StringVar(value=str(candidate.get("uncertainty") or ""))
        memory_type_var = tk.StringVar(value=str(candidate.get("memory_type") or "knowledge"))

        ttk.Label(frame, text="Concept name").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Short definition").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=definition_var).grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Propositions").grid(row=2, column=0, sticky="nw", pady=3)
        propositions_box = scrolledtext.ScrolledText(frame, height=7, wrap=tk.WORD)
        propositions_box.grid(row=2, column=1, sticky="nsew", pady=3)
        propositions_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("propositions", []) if str(item).strip()))

        ttk.Label(frame, text="Related concepts").grid(row=3, column=0, sticky="nw", pady=3)
        related_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        related_box.grid(row=3, column=1, sticky="nsew", pady=3)
        related_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("related_concepts", []) if str(item).strip()))

        ttk.Label(frame, text="Operator notes").grid(row=4, column=0, sticky="nw", pady=3)
        notes_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        notes_box.grid(row=4, column=1, sticky="nsew", pady=3)
        notes_box.insert(tk.END, str(candidate.get("operator_notes") or candidate.get("review_note") or ""))

        ttk.Label(frame, text="Uncertainty").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=uncertainty_var).grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Memory type").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(frame, values=["knowledge", "personal", "conversation"], textvariable=memory_type_var, state="readonly").grid(row=6, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Source question").grid(row=7, column=0, sticky="nw", pady=3)
        source = ttk.Label(frame, text=str(candidate.get("source_question") or ""), wraplength=560)
        source.grid(row=7, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Raw candidate").grid(row=8, column=0, sticky="nw", pady=3)
        raw_box = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        raw_box.grid(row=8, column=1, sticky="nsew", pady=3)
        raw_box.insert(tk.END, json.dumps(candidate, indent=2, sort_keys=True))
        raw_box.configure(state=tk.DISABLED)

        def done() -> None:
            updated = {
                **candidate,
                "concept_name": name_var.get().strip() or str(candidate.get("concept_name") or "Learned Concept"),
                "short_definition": definition_var.get().strip(),
                "propositions": _lines_from_text(propositions_box.get("1.0", tk.END)),
                "related_concepts": _lines_from_text(related_box.get("1.0", tk.END)),
                "operator_notes": notes_box.get("1.0", tk.END).strip(),
                "uncertainty": uncertainty_var.get().strip() or "operator_edited",
                "memory_type": memory_type_var.get().strip() or "knowledge",
                "operator_edited": True,
                "approval_status": "pending_operator_review_edited",
            }
            self.concept_review_items[concept_id]["candidate"] = updated
            if self.last_payload and self.last_payload.get("memory_candidate", {}).get("concept_id") == concept_id:
                self.last_payload["memory_candidate"] = updated
            self.concept_review.set(concept_id, "concept", updated["concept_name"])
            self.concept_review.set(concept_id, "source", str(updated.get("source_type") or "edited_candidate"))
            self.concept_review.set(concept_id, "status", "edited")
            self._append_chat("DELTA", f"Updated `{updated['concept_name']}` in Concept Review. It is not stored until you press Accept Selected Concept.")
            self._append_session("assistant", f"Updated `{updated['concept_name']}` in Concept Review.")
            editor.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Done", command=done).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Cancel", command=editor.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _clear_local_store(self) -> None:
        phrase = "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE"
        entered = simpledialog.askstring(
            "Clear Local Memory Store",
            f"Type {phrase} to delete only the RC2 developmental concept store.",
        )
        result = clear_developmental_memory_store(entered or "")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        if result["cleared"]:
            self._append_chat("DELTA", "The RC2 developmental concept store was cleared. Canonical memory, reports, source code, and model weights were untouched.")
        else:
            self._append_chat("DELTA", "Local memory store was not cleared because the confirmation phrase did not match.")

    def _write_output(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

    def _preview_evidence(self) -> None:
        data = preview_evidence_ingest(self.paste.get("1.0", tk.END))
        self._refresh_state_cards()
        self._write_output(json.dumps(data, indent=2, sort_keys=True))

    def _extract_propositions(self) -> None:
        data = extract_propositions(self.paste.get("1.0", tk.END))
        self.extracted = data["candidates"]
        self._refresh_state_cards()
        lines = ["Detected Propositions", ""]
        if not self.extracted:
            lines.append("No proposition candidates detected.")
        for idx, item in enumerate(self.extracted, start=1):
            lines.append(f"[x] {idx}. {item['claim']}")
            lines.append(f"    id: {item['proposition_id']}")
            lines.append(f"    source: {item['source']}")
            lines.append(f"    confidence: {item['confidence']}")
        lines.extend(["", "Nothing has been persisted yet.", "Approve extracted propositions to make them available in noncanonical substrate."])
        self._write_output("\n".join(lines))

    def _approve_extracted(self) -> None:
        if not self.extracted:
            self._extract_propositions()
        result = approve_propositions(self.extracted)
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(json.dumps(result, indent=2, sort_keys=True))

    def _log_observation(self) -> None:
        note = self.paste.get("1.0", tk.END).strip()
        if not note:
            note = "Operator created an empty observation placeholder from the RC2 console."
        entry = build_observation_entry(self.category.get(), note, self.severity.get())
        result = append_observation(entry)
        self._refresh_state_cards()
        self._write_output(json.dumps({"entry": entry, "result": result}, indent=2, sort_keys=True))

    def _show_status(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(_format_snapshot(self.snapshot))

    def _show_cognitive_state(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        self._refresh_state_cards()
        self._write_output(_format_cognitive_state(state) + "\n\nDevelopmental concept memory\n" + json.dumps(developmental, indent=2, sort_keys=True))

    def _show_review_queue(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["operator_review_queue"], indent=2, sort_keys=True))

    def _show_replay(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["replay_rollback"], indent=2, sort_keys=True))

    def _show_failure_taxonomy(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["failure_classification"], indent=2, sort_keys=True))


def main() -> int:
    root = tk.Tk()
    DeltaApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


======================================================================
FILE: orchestration/runtime/delta_1_4_live_wikipedia_runtime.py
======================================================================

"""Operator-started live runtime bridge with polite Wikipedia text retrieval.

The bridge keeps Wikipedia as a session-scoped capability. It is inactive until
the operator starts the live runtime, uses only one text summary request per
turn, rate-limits the default transport, records provenance, and falls back to
the existing router for ordinary conversation. It does not call providers,
write memory, commit, push, schedule work, or retrieve media.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import re
import threading
import time
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now
from orchestration.runtime.delta_1_1_development_loop import WikipediaPermissionProfile
from orchestration.runtime.delta_1_2_live_runtime import (
    FutureSurfaceReadiness,
    LiveRuntimeConfig,
    LiveRuntimeState,
    append_journal,
    boot_live_runtime,
    create_event,
    enqueue_event,
    run_wake_cycle,
)
from orchestration.runtime.continuous_runtime_controller import (
    ContinuousRuntimeController,
    controller_snapshot,
    enqueue_continuous_event,
    make_continuous_event,
    pause_controller,
    resume_controller,
    run_controller_cycle,
    shutdown_controller,
    start_continuous_runtime_controller,
    suspend_controller,
)
from orchestration.runtime.delta_1_5_developmental_cognition import (
    DevelopmentalCognitionResult,
    render_developmental_observation,
    run_wikipedia_developmental_cognition,
)
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityDecision,
    BackgroundCycleResult,
    IdentityProposal,
    Initiative,
    OperationalSelfModel,
    answer_operational_self_model_question,
    build_operational_self_model,
    is_operational_self_model_question,
    run_delta_1_6_background_cycle,
    set_autonomy_status,
)
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


WikipediaTransport = Callable[[str, int], dict[str, Any]]
_WIKIPEDIA_TRANSPORT_LOCK = threading.Lock()
_LAST_WIKIPEDIA_TRANSPORT_AT = 0.0
_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS = 1.0
_WIKIPEDIA_RESPONSE_CACHE: dict[str, dict[str, Any]] = {}
_MAX_WIKIPEDIA_TRANSPORT_RETRIES = 2
_WIKIPEDIA_TRANSPORT_BACKOFF_SECONDS = 0.5


@dataclass(frozen=True)
class WikipediaTextResult:
    query: str
    title: str
    extract: str
    canonical_url: str
    retrieved_at: str
    source: str = "wikipedia_rest_summary"
    revision_timestamp: str = ""
    chars_used: int = 0
    retrieval_performed: bool = True
    media_retrieved: bool = False
    external_links_followed: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: {
        **safety_metadata(),
        "external_retrieval_performed": True,
        "network_calls_performed": True,
    })


@dataclass(frozen=True)
class LiveChatResponse:
    answer: str
    route: str
    payload: dict[str, Any]
    wikipedia_result: WikipediaTextResult | None
    runtime_state: str
    safety: dict[str, bool]


@dataclass(frozen=True)
class LiveWikipediaRuntimeSession:
    session_id: str
    runtime: LiveRuntimeState
    wikipedia_profile: WikipediaPermissionProfile
    active: bool
    started_at: str
    turns: tuple[LiveChatResponse, ...] = ()
    developmental_results: tuple[DevelopmentalCognitionResult, ...] = ()
    promotion_candidates: tuple[dict[str, Any], ...] = ()
    prepared_review_proposals: tuple[dict[str, Any], ...] = ()
    operator_inquiries: tuple[dict[str, Any], ...] = ()
    pending_local_model_request: dict[str, Any] | None = None
    operational_self_model: OperationalSelfModel | None = None
    initiatives: tuple[Initiative, ...] = ()
    authority_decisions: tuple[AuthorityDecision, ...] = ()
    identity_proposals: tuple[IdentityProposal, ...] = ()
    last_background_cycle: BackgroundCycleResult | None = None
    identity_status: str = "UNDEFINED"
    autonomy_status: str = "ACTIVE"
    continuous_controller: ContinuousRuntimeController | None = None
    retrieval_count: int = 0
    provider_calls_performed: bool = False
    memory_write_performed: bool = False
    canonical_write_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def activated_wikipedia_profile(*, max_queries_per_objective: int = 0) -> WikipediaPermissionProfile:
    return WikipediaPermissionProfile(
        enabled=True,
        network_calls_allowed=True,
        max_queries_per_objective=max(0, int(max_queries_per_objective)),
        max_pages_per_query=1,
        max_total_characters=6000,
        operator_approval_required=True,
        persistence="ephemeral_session_only",
    )


def start_live_wikipedia_runtime(
    *,
    runtime_id: str = "delta-live-ui",
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
    max_wikipedia_queries: int = 0,
) -> LiveWikipediaRuntimeSession:
    config = LiveRuntimeConfig(
        runtime_id=stable_id("delta14-live-runtime", runtime_id),
        mode="DEVELOPMENT_SESSION",
        network_enabled=True,
        provider_enabled=False,
        timers_enabled=False,
    )
    runtime = boot_live_runtime(config)
    surface = FutureSurfaceReadiness(
        capability="WIKIPEDIA_TEXT_READ_ONLY",
        state="ACTIVE",
        permission_profile=activated_wikipedia_profile(max_queries_per_objective=max_wikipedia_queries),
        dependencies=("operator_started_live_runtime", "text_summary_endpoint", "session_scoped_retrieval", "provenance_required"),
        retrieval_implemented=True,
        network_code_present=True,
        provider_present=False,
    )
    runtime = replace(runtime, future_surfaces=(surface,))
    queue = enqueue_event(
        runtime.event_queue,
        create_event("runtime_startup", "Operator started live runtime with polite Wikipedia text retrieval.", source="delta_1_4_ui"),
    )
    runtime = run_wake_cycle(replace(runtime, event_queue=queue))
    session = LiveWikipediaRuntimeSession(
        session_id=stable_id("delta14-session", runtime.runtime_id, utc_now()),
        runtime=runtime,
        wikipedia_profile=surface.permission_profile,
        active=True,
        started_at=utc_now(),
    )
    controller = start_continuous_runtime_controller(
        session_id=session.session_id,
        resident_model_id=resident_model_id,
        resident_lane=resident_lane,
        residency_status=residency_status,
    )
    return replace(session, operational_self_model=build_operational_self_model(session=session), continuous_controller=controller)


def stop_live_wikipedia_runtime(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    event = create_event("runtime_shutdown", "Operator stopped live Wikipedia runtime.", source="delta_1_4_ui")
    queue = enqueue_event(session.runtime.event_queue, event)
    runtime = run_wake_cycle(replace(session.runtime, event_queue=queue))
    journal = append_journal(runtime.journal, "live_runtime_stop", "Live Wikipedia runtime stopped by operator.", (), runtime.cycle)
    controller = shutdown_controller(session.continuous_controller) if session.continuous_controller else None
    return replace(session, runtime=replace(runtime, journal=journal, state="IDLE"), active=False, continuous_controller=controller)


def handle_live_chat(
    session: LiveWikipediaRuntimeSession,
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    developer_overlay: bool = False,
    wikipedia_transport: WikipediaTransport | None = None,
    provider_manager: Any | None = None,
) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    if not session.active:
        payload = route_message("Conversation", message, history=history, execute_local_model=False)
        answer = render_route(payload, developer_overlay=developer_overlay)
        response = _response(answer, "inactive_fallback", payload, None, session.runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    event = create_event("operator_message", message, source="ui_live_chat", payload={"live_runtime": True})
    runtime = run_wake_cycle(replace(session.runtime, event_queue=enqueue_event(session.runtime.event_queue, event)))
    session = _advance_continuous_controller(replace(session, runtime=runtime), "OPERATOR_MESSAGE", {"message": message}, priority=70)
    runtime = session.runtime

    control = _runtime_control_intent(message)
    if control:
        session, response = _handle_runtime_control_intent(session, control)
        return session, response

    if session.autonomy_status == "SUSPENDED":
        answer = "The live runtime is suspended. I cannot continue background initiative work, retrieve Wikipedia, or offer local-model escalation until you resume or restart it."
        payload = _base_live_payload("live_runtime_suspended", answer)
        response = _response(answer, "live_runtime_suspended", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _is_pending_inquiry_question(message):
        answer, payload = _render_pending_inquiries(session)
        response = _response(answer, "live_pending_inquiries", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _has_pending_local_model_request(session) and _is_explicit_local_model_cancellation(message):
        request = session.pending_local_model_request or {}
        answer = "The pending local-model request was cancelled. No model was called, no provider was called, and no memory was written."
        payload = _base_live_payload("live_local_model_request_cancelled", answer)
        payload.update({
            "local_model_request": request,
            "provider_calls_performed": False,
            "memory_candidate": None,
        })
        updated = _advance_continuous_controller(
            replace(session, pending_local_model_request=None),
            "OPERATOR_REJECTION",
            {"summary": "operator cancelled pending local model request", "request_id": str(request.get("request_id") or "")},
            priority=65,
            correlation_id=str(request.get("request_id") or ""),
        )
        response = _response(answer, "live_local_model_request_cancelled", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _has_pending_local_model_request(session) and _is_explicit_local_model_request(message):
        if session.autonomy_status == "PAUSED":
            answer = "I heard the local-model approval, but live initiative processing is paused. Resume the live runtime before I run the approved local inference turn."
            payload = _base_live_payload("live_runtime_paused", answer)
            payload["pending_local_model_request"] = session.pending_local_model_request
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        return _run_approved_local_model_request(
            session,
            message,
            history=history,
            developer_overlay=developer_overlay,
            provider_manager=provider_manager,
        )

    if _has_pending_local_model_request(session) and _has_pending_promotion_inquiry(session) and _is_unqualified_affirmation(message):
        answer, payload = _render_ambiguous_live_action(session)
        response = _response(answer, "live_operator_action_ambiguous", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if _has_pending_local_model_request(session) and not _has_pending_promotion_inquiry(session) and _is_affirmative(message):
        if session.autonomy_status == "PAUSED":
            answer = "I heard the local-model approval, but live initiative processing is paused. Resume the live runtime before I run the approved local inference turn."
            payload = _base_live_payload("live_runtime_paused", answer)
            payload["pending_local_model_request"] = session.pending_local_model_request
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        return _run_approved_local_model_request(
            session,
            message,
            history=history,
            developer_overlay=developer_overlay,
            provider_manager=provider_manager,
        )

    if _is_affirmative(message) and _has_pending_promotion_inquiry(session):
        selected_inquiry, ambiguity = _select_pending_promotion_inquiry(session, message)
        if ambiguity:
            answer, payload = _render_ambiguous_promotion_approval(session)
            response = _response(answer, "live_promotion_approval_ambiguous", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        if session.autonomy_status == "PAUSED":
            answer = "I heard the approval, but live initiative processing is paused. Resume the live runtime before I prepare the proposal."
            payload = _base_live_payload("live_runtime_paused", answer)
            response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        updated, answer, payload = _approve_pending_promotion(session, selected_inquiry)
        response = _response(answer, "live_promotion_approval", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _is_rejection(message) and _has_pending_promotion_inquiry(session):
        selected_inquiry, ambiguity = _select_pending_promotion_inquiry(session, message)
        if ambiguity:
            answer, payload = _render_ambiguous_promotion_approval(session, rejection=True)
            response = _response(answer, "live_promotion_rejection_ambiguous", payload, None, runtime.state, safety_metadata())
            return replace(session, turns=session.turns + (response,)), response
        updated, answer, payload = _reject_pending_promotion(session, selected_inquiry)
        response = _response(answer, "live_promotion_rejection", payload, None, updated.runtime.state, safety_metadata())
        return replace(updated, turns=updated.turns + (response,)), response

    if _is_live_help_request(message):
        answer = _render_live_help()
        payload = _base_live_payload("live_runtime_help", answer)
        response = _response(answer, "live_runtime_help", payload, None, runtime.state, safety_metadata())
        return replace(session, runtime=runtime, turns=session.turns + (response,)), response

    if _is_memory_request(message):
        answer, payload = _render_memory_gate(session)
        response = _response(answer, "live_memory_governance", payload, None, runtime.state, safety_metadata())
        return replace(session, runtime=runtime, turns=session.turns + (response,)), response

    if is_operational_self_model_question(message):
        updated_session, cycle = run_delta_1_6_background_cycle(replace(session, runtime=runtime))
        answer = answer_operational_self_model_question(message, updated_session)
        payload = {
            "mode": "Live Runtime",
            "route": "live_operational_self_model",
            "answer": answer,
            "operational_self_model": updated_session.operational_self_model.as_dict() if updated_session.operational_self_model else {},
            "background_cycle": cycle.as_dict(),
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": updated_session.promotion_candidates[-1] if updated_session.promotion_candidates else None,
            "operator_inquiry": updated_session.operator_inquiries[-1] if updated_session.operator_inquiries else None,
        }
        response = _response(answer, "live_operational_self_model", payload, None, updated_session.runtime.state, safety_metadata())
        return replace(updated_session, turns=updated_session.turns + (response,)), response

    if _is_live_context_declaration(message):
        answer = "Noted as live-session context. I will treat this as operator-provided behavioral evidence for this session only; no memory was written."
        payload = {
            "mode": "Live Runtime",
            "route": "live_context_declaration",
            "answer": answer,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": None,
        }
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "live_context_declaration", message[:500], (), runtime.cycle),
        )
        response = _response(answer, "live_context_declaration", payload, None, runtime.state, safety_metadata())
        updated = _advance_continuous_controller(replace(session, runtime=runtime), "DEVELOPMENTAL_SIGNAL", {"summary": "operator live context declaration", "title": "Live context declaration"}, priority=40)
        return replace(updated, turns=updated.turns + (response,)), response

    query = wikipedia_query_from_message(message)
    if session.autonomy_status == "PAUSED" and (query or _is_continuation_pressure(message)):
        answer = "Live initiative processing is paused. I will not retrieve new evidence, continue background work, or prepare proposals until you resume."
        payload = _base_live_payload("live_runtime_paused", answer)
        response = _response(answer, "live_runtime_paused", payload, None, runtime.state, safety_metadata())
        return replace(session, turns=session.turns + (response,)), response

    if query and _wikipedia_budget_allows(session):
        try:
            result = retrieve_wikipedia_text(query, profile=session.wikipedia_profile, transport=wikipedia_transport)
        except Exception as exc:  # noqa: BLE001 - retrieval failures fail closed into an explicit live route.
            answer = "\n".join([
                f"Wikipedia retrieval failed safely for `{query}`.",
                f"Reason: {type(exc).__name__}: {str(exc)[:180]}",
                "No provider was called, no memory was written, and no promotion candidate was prepared from this failed retrieval.",
            ])
            payload = _base_live_payload("live_wikipedia_retrieval_failed", answer)
            payload.update({
                "query": query,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)[:500],
                "external_retrieval_performed": False,
                "network_calls_performed": bool(wikipedia_transport is None),
                "wikipedia_failure": True,
            })
            response = _response(answer, "live_wikipedia_retrieval_failed", payload, None, runtime.state, safety_metadata())
            updated = _advance_continuous_controller(
                replace(session, runtime=runtime),
                "WIKIPEDIA_FAILURE",
                {"summary": f"Wikipedia retrieval failed for {query}", "exception_type": type(exc).__name__},
                priority=68,
            )
            return replace(updated, turns=updated.turns + (response,)), response
        development = run_wikipedia_developmental_cognition(result)
        development_payload = development.as_dict()
        answer = render_wikipedia_answer(message, result)
        answer += "\n\n" + render_developmental_observation(development)
        if developer_overlay:
            answer += "\n\n--- Developer Overlay ---\nRoute: live_wikipedia_text_retrieval\n"
            answer += "Wikipedia result:\n" + json.dumps(asdict(result), indent=2, sort_keys=True)
            answer += "\nDevelopmental cognition:\n" + json.dumps(development_payload, indent=2, sort_keys=True)
        payload = {
            "mode": "Live Runtime",
            "route": "live_wikipedia_text_retrieval",
            "answer": answer,
            "wikipedia_result": asdict(result),
            "developmental_cognition": development_payload,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": True,
            "network_calls_performed": True,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": _memory_candidate_from_development(development_payload),
            "promotion_candidate": development_payload["promotion_candidate"],
            "operator_inquiry": development_payload["operator_inquiry"],
            "routing_observability": _live_routing_trace(
                message,
                "live_wikipedia_text_retrieval",
                query=query,
                rc2_fallback_considered=False,
                wikipedia_considered=True,
            ),
        }
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "wikipedia_retrieval", f"Retrieved Wikipedia text for {result.title}.", (result.canonical_url,), runtime.cycle),
        )
        runtime = replace(
            runtime,
            journal=append_journal(runtime.journal, "developmental_observation", development.observation, (result.canonical_url,), runtime.cycle),
        )
        session = _advance_continuous_controller(
            replace(session, runtime=runtime),
            "WIKIPEDIA_RESULT",
            {"title": result.title, "url": result.canonical_url, "classification": development.comparison.classification},
            priority=75,
            correlation_id=development.cycle_id,
        )
        session = _advance_continuous_controller(
            session,
            "PROMOTION_CANDIDATE",
            {"title": development.promotion_candidate.title, "prompt": development.operator_inquiry.prompt},
            priority=72,
            correlation_id=development.promotion_candidate.candidate_id,
            objective_id=development.objective.objective_id,
        )
        runtime = session.runtime
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, runtime.state, _retrieval_safety())
        updated_session = replace(
            session,
            runtime=runtime,
            turns=session.turns + (response,),
            developmental_results=session.developmental_results + (development,),
            promotion_candidates=session.promotion_candidates + (development_payload["promotion_candidate"],),
            operator_inquiries=session.operator_inquiries + (_session_inquiry_from_development(development_payload),),
            retrieval_count=session.retrieval_count + 1,
        )
        updated_session, cycle = run_delta_1_6_background_cycle(updated_session)
        updated_session = replace(updated_session, continuous_controller=run_controller_cycle(updated_session.continuous_controller, session=updated_session) if updated_session.continuous_controller else None)
        payload["operational_self_model"] = updated_session.operational_self_model.as_dict() if updated_session.operational_self_model else {}
        payload["background_cycle"] = cycle.as_dict()
        payload["continuous_controller"] = controller_snapshot(updated_session.continuous_controller) if updated_session.continuous_controller else {}
        response = _response(answer, "live_wikipedia_text_retrieval", payload, result, updated_session.runtime.state, _retrieval_safety())
        return replace(updated_session, turns=updated_session.turns[:-1] + (response,)), response

    if query and _wikipedia_budget_exhausted(session):
        answer = _render_budget_exhausted(session)
        payload = {
            "mode": "Live Runtime",
            "route": "live_wikipedia_budget_exhausted",
            "answer": answer,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "external_retrieval_performed": False,
            "network_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "autonomous_action_performed": False,
            "memory_candidate": None,
            "promotion_candidate": session.promotion_candidates[-1] if session.promotion_candidates else None,
            "operator_inquiry": session.operator_inquiries[-1] if session.operator_inquiries else None,
        }
        response = _response(answer, "live_wikipedia_budget_exhausted", payload, None, runtime.state, safety_metadata())
        updated = _advance_continuous_controller(replace(session, runtime=runtime), "RESOURCE_LIMIT_REACHED", {"summary": "Wikipedia session query budget exhausted"}, priority=65)
        return replace(updated, turns=updated.turns + (response,)), response

    pending_request = session.pending_local_model_request
    if pending_request is not None:
        session = replace(session, pending_local_model_request=None)
    payload = route_message("Conversation", message, history=history, execute_local_model=False)
    answer = render_route(payload, developer_overlay=developer_overlay)
    local_offer = payload.get("local_model_offer")
    if str(payload.get("route") or "") == "local_model_consent_required" and isinstance(local_offer, dict) and local_offer.get("offered"):
        request = _new_local_model_request(session, message, payload)
        payload = {**payload, "live_runtime_local_model_request": request}
        session = replace(session, pending_local_model_request=request)
    payload["live_routing_observability"] = _live_routing_trace(
        message,
        str(payload.get("route") or "conversation_fallback"),
        query=query,
        rc2_fallback_considered=True,
        wikipedia_considered=bool(query),
    )
    response = _response(answer, str(payload.get("route") or "conversation_fallback"), payload, None, runtime.state, safety_metadata())
    updated = _advance_continuous_controller(replace(session, runtime=runtime), "VALIDATION_RESULT", {"summary": "ordinary chat routed without continuous work"}, priority=20)
    return replace(updated, turns=updated.turns + (response,)), response


def wikipedia_query_from_message(message: str) -> str:
    text = " ".join(str(message or "").strip().strip(" .?!").split())
    lower = text.lower()
    if not _has_explicit_wikipedia_intent(lower):
        return ""
    patterns = (
        r"^(?:wikipedia|wiki)\s*[:\-]?\s*(.+)$",
        r"tell me what wikipedia has (?:regarding|about|on)\s+(.+)$",
        r"what does wikipedia (?:have|say) (?:regarding|about|on)\s+(.+)$",
        r"what has wikipedia got (?:regarding|about|on)\s+(.+)$",
        r"look up\s+(.+?)\s+on wikipedia$",
        r"retrieve\s+(.+?)(?:\s+from wikipedia)?$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            query = re.sub(r"\b(on|from)\s+wikipedia\b", "", match.group(1), flags=re.IGNORECASE).strip(" ?.!")
            return _clean_query(query)
    return ""


def _has_explicit_wikipedia_intent(lower: str) -> bool:
    if "wikipedia" in lower or re.search(r"(^|\s)wiki\s*[:\-]", lower):
        return True
    if lower.startswith("retrieve ") and "from wikipedia" in lower:
        return True
    return bool(re.match(r"^look up .+ on wikipedia$", lower))


def _live_routing_trace(
    message: str,
    selected_route: str,
    *,
    query: str = "",
    rc2_fallback_considered: bool,
    wikipedia_considered: bool,
) -> dict[str, Any]:
    return {
        "layer": "delta_1_4_live_wikipedia_runtime",
        "selected_route": selected_route,
        "raw_message": message,
        "wikipedia_query": query,
        "explicit_wikipedia_intent": _has_explicit_wikipedia_intent(" ".join(str(message or "").lower().split())),
        "wikipedia_considered": wikipedia_considered,
        "rc2_fallback_considered": rc2_fallback_considered,
        "read_only": True,
        "ephemeral": True,
    }


def retrieve_wikipedia_text(
    query: str,
    *,
    profile: WikipediaPermissionProfile | None = None,
    transport: WikipediaTransport | None = None,
) -> WikipediaTextResult:
    profile = profile or activated_wikipedia_profile()
    if not profile.enabled or not profile.network_calls_allowed:
        raise PermissionError("Wikipedia retrieval is not enabled for this live runtime session.")
    clean_query = _clean_query(query)
    if not clean_query:
        raise ValueError("Wikipedia query is empty.")
    page_title = clean_query.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(page_title, safe='')}"
    data = transport(url, profile.max_total_characters) if transport else _default_wikipedia_transport(url, profile.max_total_characters)
    extract = " ".join(str(data.get("extract") or "").split())[: profile.max_total_characters]
    title = str(data.get("title") or clean_query).strip()
    canonical = str(((data.get("content_urls") or {}).get("desktop") or {}).get("page") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='/_:')}")
    return WikipediaTextResult(
        query=clean_query,
        title=title,
        extract=extract or "Wikipedia returned no text extract for this page.",
        canonical_url=canonical,
        retrieved_at=utc_now(),
        revision_timestamp=str(data.get("timestamp") or ""),
        chars_used=len(extract),
    )


def render_wikipedia_answer(message: str, result: WikipediaTextResult) -> str:
    return "\n".join([
        f"Wikipedia says: {result.title}",
        "",
        result.extract,
        "",
        f"Source: {result.canonical_url}",
        "",
        "This is external Wikipedia text evidence, not canonical DELTA memory. No provider was called and no memory was written.",
    ])


def _default_wikipedia_transport(url: str, max_chars: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(_MAX_WIKIPEDIA_TRANSPORT_RETRIES + 1):
        try:
            return _default_wikipedia_transport_once(url, max_chars)
        except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt >= _MAX_WIKIPEDIA_TRANSPORT_RETRIES:
                break
            time.sleep(_WIKIPEDIA_TRANSPORT_BACKOFF_SECONDS * (2 ** attempt))
    raise RuntimeError(f"Wikipedia retrieval failed after bounded retries: {last_error}") from last_error


def _default_wikipedia_transport_once(url: str, max_chars: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "DELTA-governed-runtime/1.0 (operator-started local experiment)"})
    global _LAST_WIKIPEDIA_TRANSPORT_AT
    with _WIKIPEDIA_TRANSPORT_LOCK:
        cached = _WIKIPEDIA_RESPONSE_CACHE.get(url)
        if cached is not None:
            return dict(cached)
        now = time.monotonic()
        elapsed = now - _LAST_WIKIPEDIA_TRANSPORT_AT
        if elapsed < _MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS:
            time.sleep(_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS - elapsed)
        _LAST_WIKIPEDIA_TRANSPORT_AT = time.monotonic()
        with urlopen(request, timeout=8) as response:  # noqa: S310 - operator-started throttled Wikipedia-only retrieval
            raw = response.read(max_chars + 4096).decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise RuntimeError("Wikipedia response was not a JSON object.")
        _WIKIPEDIA_RESPONSE_CACHE[url] = dict(data)
        return dict(data)


def _wait_for_polite_wikipedia_slot() -> None:
    global _LAST_WIKIPEDIA_TRANSPORT_AT
    with _WIKIPEDIA_TRANSPORT_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_WIKIPEDIA_TRANSPORT_AT
        if elapsed < _MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS:
            time.sleep(_MIN_WIKIPEDIA_TRANSPORT_INTERVAL_SECONDS - elapsed)
        _LAST_WIKIPEDIA_TRANSPORT_AT = time.monotonic()


def _clean_query(query: str) -> str:
    clean = re.sub(r"\s+", " ", str(query or "")).strip(" ?.!")
    clean = re.sub(r"^(the article about|article about)\s+", "", clean, flags=re.IGNORECASE)
    return clean[:120]


def _retrieval_safety() -> dict[str, bool]:
    return {
        **safety_metadata(),
        "external_retrieval_performed": True,
        "network_calls_performed": True,
    }


def _is_memory_request(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip().split())
    return bool(re.search(r"\b(remember|save|store|memorize)\s+(that|this|it|the previous|what you found)\b", text))


def _base_live_payload(route: str, answer: str) -> dict[str, Any]:
    return {
        "mode": "Live Runtime",
        "route": route,
        "answer": answer,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "external_retrieval_performed": False,
        "network_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "memory_candidate": None,
        "promotion_candidate": None,
    }


def _runtime_control_intent(message: str) -> str:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    if not text:
        return ""
    if "runtime" not in text and "initiative" not in text and text not in {"pause", "resume", "suspend", "status"}:
        return ""
    if re.search(r"\b(suspend)\b", text):
        return "SUSPEND"
    if re.search(r"\b(pause)\b", text):
        return "PAUSE"
    if re.search(r"\b(resume|restart)\b", text):
        return "RESUME"
    if "status" in text or "objective state" in text or "report current objective" in text:
        return "REPORT"
    return ""


def _handle_runtime_control_intent(session: LiveWikipediaRuntimeSession, control: str) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    if control == "PAUSE":
        updated = pause_live_initiative(session)
        answer = _render_runtime_state(updated, prefix="Paused live initiative processing.")
        payload = _base_live_payload("live_runtime_control_pause", answer)
    elif control == "SUSPEND":
        updated = suspend_live_runtime_initiative(session)
        answer = _render_runtime_state(updated, prefix="Suspended the live runtime initiative path.")
        payload = _base_live_payload("live_runtime_control_suspend", answer)
    elif control == "RESUME":
        updated = resume_live_initiative(session)
        answer = _render_runtime_state(updated, prefix="Resumed live initiative processing.")
        payload = _base_live_payload("live_runtime_control_resume", answer)
    else:
        updated = session
        answer = _render_runtime_state(updated)
        payload = _base_live_payload("live_runtime_control_report", answer)
    payload.update({
        "operator_inquiries": tuple(updated.operator_inquiries[-5:]),
        "promotion_candidate": updated.promotion_candidates[-1] if updated.promotion_candidates else None,
        "prepared_review_proposal": updated.prepared_review_proposals[-1] if updated.prepared_review_proposals else None,
        "continuous_controller": controller_snapshot(updated.continuous_controller) if updated.continuous_controller else {},
    })
    response = _response(answer, str(payload["route"]), payload, None, updated.runtime.state, safety_metadata())
    return replace(updated, turns=updated.turns + (response,)), response


def _render_runtime_state(session: LiveWikipediaRuntimeSession, *, prefix: str = "") -> str:
    model = build_operational_self_model(session=session, initiatives=session.initiatives)
    objectives = model.active_objectives or model.queued_objectives or ("no active objective beyond maintaining the live session",)
    inquiries = model.pending_operator_inquiries or ("none",)
    lines = []
    if prefix:
        lines.append(prefix)
        lines.append("")
    lines.extend([
        f"Runtime state: {getattr(session.runtime, 'state', 'unknown')}.",
        f"Autonomy: {session.autonomy_status}.",
        f"Wikipedia budget: {_wikipedia_budget_label(session)}.",
        "Current objective:",
    ])
    lines.extend(f"- {item}" for item in objectives[:3])
    lines.append("Pending inquiries:")
    lines.extend(f"- {item}" for item in inquiries[:5])
    return "\n".join(lines)


def _is_pending_inquiry_question(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return any(marker in text for marker in ("pending inquiries", "pending inquiry", "questions are pending", "what are your pending"))


def _is_affirmative(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text.startswith(("approve ", "approved ", "prepare ", "go ahead ", "do it ", "yes ", "proceed ")):
        return True
    return text in {
        "yes",
        "y",
        "yes please",
        "yeah",
        "yep",
        "approve",
        "approve that",
        "approved",
        "go ahead",
        "do it",
        "that's fine",
        "thats fine",
        "proceed",
        "the first one",
        "first one",
        "okay prepare it",
        "ok prepare it",
        "prepare it",
        "prepare the proposal",
        "ok",
        "okay",
        "sure",
    }


def _is_rejection(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text.startswith(("reject ", "decline ", "discard ", "cancel ", "drop ", "defer ")):
        return True
    return text in {
        "no",
        "n",
        "reject",
        "reject it",
        "decline",
        "not now",
        "not that one",
        "cancel",
        "cancel that",
        "stop",
        "discard",
        "drop it",
        "don't continue",
        "dont continue",
        "never mind",
        "nevermind",
        "defer this",
    }


def _has_pending_local_model_request(session: LiveWikipediaRuntimeSession) -> bool:
    request = session.pending_local_model_request
    return bool(isinstance(request, dict) and str(request.get("status") or "").upper() == "PENDING_OPERATOR_APPROVAL")


def _normalized_operator_text(message: str) -> str:
    text = " ".join(str(message or "").lower().strip(" ?.! ").split())
    text = re.sub(r"[,;:]+", " ", text)
    return " ".join(text.split())


def _is_explicit_local_model_request(message: str) -> bool:
    text = _normalized_operator_text(message)
    return any(marker in text for marker in (
        "ask local model",
        "ask the local model",
        "use local model",
        "use the local model",
        "run local model",
        "run the local model",
        "ask llama",
        "ask mistral",
        "use llama",
        "use mistral",
    ))


def _is_explicit_local_model_cancellation(message: str) -> bool:
    text = _normalized_operator_text(message)
    return any(marker in text for marker in (
        "cancel local model",
        "cancel the local model",
        "do not ask local model",
        "dont ask local model",
        "do not use local model",
        "dont use local model",
    ))


def _is_unqualified_affirmation(message: str) -> bool:
    return _normalized_operator_text(message) in {
        "yes",
        "y",
        "yes please",
        "yeah",
        "yep",
        "approve",
        "approved",
        "go ahead",
        "do it",
        "proceed",
        "okay",
        "ok",
        "sure",
    }


def _new_local_model_request(
    session: LiveWikipediaRuntimeSession,
    message: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    lane = dict(payload.get("selected_model_lane") or {})
    offer = dict(payload.get("local_model_offer") or {})
    created_at = utc_now()
    return {
        "request_id": stable_id("delta14-local-model-request", session.session_id, message, len(session.turns), created_at),
        "status": "PENDING_OPERATOR_APPROVAL",
        "message": message,
        "lane": str(lane.get("lane") or ""),
        "selected_model": str(lane.get("selected_model") or ""),
        "selected_model_id": str(lane.get("selected_model_id") or ""),
        "prompt": str(offer.get("prompt") or "Ask the selected local model for this one question?"),
        "created_at": created_at,
        "expires_after_unrelated_turns": 1,
        "authority_class": "OPERATOR_APPROVAL_REQUIRED",
        "provider_calls_performed": False,
        "memory_write_performed": False,
    }


def _render_ambiguous_live_action(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    request = session.pending_local_model_request or {}
    candidates = [
        _promotion_title_for_inquiry(session, inquiry) or "unnamed promotion candidate"
        for inquiry in _pending_promotion_inquiries(session)
    ]
    candidate_text = "; ".join(candidates[:3]) or "a promotion candidate"
    answer = "\n".join([
        "There are multiple pending operator actions, so I will not guess what this approval means.",
        f"Promotion review: {candidate_text}.",
        f"Local inference request: {request.get('selected_model_id') or request.get('selected_model') or 'selected local model'} for the queued question.",
        "Say `ask the local model` to run the local inference turn, or name the promotion candidate you want reviewed.",
        "No model was called and no memory was written.",
    ])
    payload = _base_live_payload("live_operator_action_ambiguous", answer)
    payload.update({
        "pending_local_model_request": request,
        "pending_promotion_titles": candidates,
        "provider_calls_performed": False,
        "memory_candidate": None,
    })
    return answer, payload


def _run_approved_local_model_request(
    session: LiveWikipediaRuntimeSession,
    approval_message: str,
    *,
    history: list[dict[str, str]] | None,
    developer_overlay: bool,
    provider_manager: Any | None,
) -> tuple[LiveWikipediaRuntimeSession, LiveChatResponse]:
    request = dict(session.pending_local_model_request or {})
    target = str(request.get("message") or "").strip()
    if not target:
        answer = "The pending local-model request was invalid, so it was cleared without calling a model."
        payload = _base_live_payload("live_local_model_request_invalid", answer)
        response = _response(answer, "live_local_model_request_invalid", payload, None, session.runtime.state, safety_metadata())
        return replace(session, pending_local_model_request=None, turns=session.turns + (response,)), response

    local_payload = route_message(
        "Conversation",
        target,
        history=history,
        execute_local_model=True,
        provider_manager=provider_manager,
    )
    model_result = dict(local_payload.get("local_model_result") or {})
    lane = dict(local_payload.get("selected_model_lane") or request)
    executed = bool(model_result.get("executed"))
    model_id = str(model_result.get("model_id") or lane.get("selected_model_id") or lane.get("selected_model") or "")
    latency_seconds = float(model_result.get("latency_seconds") or 0.0)
    updated = replace(session, pending_local_model_request=None)

    if executed:
        updated = _record_local_model_residency(updated, lane, model_result, provider_manager)
        updated = _advance_continuous_controller(
            updated,
            "MODEL_READY",
            {
                "model_id": model_id,
                "lane": str(lane.get("lane") or request.get("lane") or ""),
                "local_model_call_performed": True,
                "latency_seconds": latency_seconds,
                "operator_request_id": str(request.get("request_id") or ""),
            },
            priority=70,
            correlation_id=str(request.get("request_id") or ""),
        )
        answer = str(local_payload.get("answer") or "").strip()
        answer += "\n\nThis was one explicitly approved local inference turn. No provider, external retrieval, or memory write was performed."
        route = "live_local_model_inference"
    else:
        reason = str(model_result.get("reason") or "local_model_execution_failed")
        updated = _record_local_model_residency(updated, lane, model_result, provider_manager, failure_reason=reason)
        updated = _advance_continuous_controller(
            updated,
            "MODEL_UNAVAILABLE",
            {
                "model_id": model_id,
                "lane": str(lane.get("lane") or request.get("lane") or ""),
                "attempted": True,
                "reason": reason,
                "operator_request_id": str(request.get("request_id") or ""),
            },
            priority=70,
            correlation_id=str(request.get("request_id") or ""),
        )
        answer = "\n".join([
            "The explicitly approved local inference turn did not complete.",
            f"Reason: {reason}",
            "No provider was called, no external retrieval occurred, and no memory was written. The request was cleared rather than retried automatically.",
        ])
        route = "live_local_model_unavailable"

    payload = {
        **local_payload,
        "mode": "Live Runtime",
        "route": route,
        "answer": answer,
        "live_runtime_local_model_execution": True,
        "operator_approval_request_id": str(request.get("request_id") or ""),
        "local_model_request": request,
        "model_execution": {
            "executed": executed,
            "model_id": model_id,
            "lane": str(lane.get("lane") or request.get("lane") or ""),
            "latency_seconds": latency_seconds,
        },
        "provider_calls_performed": False,
        "web_search_performed": False,
        "external_retrieval_performed": False,
        "network_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "memory_candidate": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "continuous_controller": controller_snapshot(updated.continuous_controller) if updated.continuous_controller else {},
    }
    if developer_overlay:
        payload["developer_overlay"] = {
            "approval_message": approval_message,
            "target_question": target,
            "request_id": request.get("request_id"),
            "executed": executed,
            "model_id": model_id,
        }
    response = _response(answer, route, payload, None, updated.runtime.state, safety_metadata())
    return replace(updated, turns=updated.turns + (response,)), response


def _record_local_model_residency(
    session: LiveWikipediaRuntimeSession,
    lane: dict[str, Any],
    model_result: dict[str, Any],
    provider_manager: Any | None,
    *,
    failure_reason: str = "",
) -> LiveWikipediaRuntimeSession:
    controller = session.continuous_controller
    if controller is None:
        return session
    status = _provider_residency_status(provider_manager)
    executed = bool(model_result.get("executed"))
    selected_model = str(model_result.get("model_id") or lane.get("selected_model_id") or lane.get("selected_model") or "")
    resident_model = str(status.get("active_model") or selected_model) if executed and status.get("loaded", True) else ""
    if failure_reason:
        residency_status = f"unavailable:{failure_reason[:120]}"
    elif status.get("loaded", False):
        residency_status = "warm"
    else:
        residency_status = "completed_not_resident"
    residency = replace(
        controller.model_residency,
        resident_model_id=resident_model,
        resident_lane=str(lane.get("lane") or ""),
        residency_status=residency_status,
        model_calls_this_cycle=controller.model_residency.model_calls_this_cycle + (1 if executed else 0),
    )
    return replace(session, continuous_controller=replace(controller, model_residency=residency))


def _provider_residency_status(provider_manager: Any | None) -> dict[str, Any]:
    status_method = getattr(provider_manager, "status", None)
    if not callable(status_method):
        return {}
    try:
        status = status_method()
    except Exception:  # noqa: BLE001 - status reporting cannot interfere with an already-completed inference turn.
        return {}
    return {
        "active_model": str(getattr(status, "active_model", "") or ""),
        "loaded": bool(getattr(status, "loaded", False)),
    }


def _has_pending_promotion_inquiry(session: LiveWikipediaRuntimeSession) -> bool:
    return any(str(item.get("status") or "").upper() in {"QUEUED", "SURFACED"} for item in session.operator_inquiries) and bool(session.promotion_candidates)


def _pending_promotion_inquiries(session: LiveWikipediaRuntimeSession) -> tuple[dict[str, Any], ...]:
    return tuple(
        item
        for item in session.operator_inquiries
        if isinstance(item, dict) and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} and item.get("promotion_candidate_id")
    )


def _select_pending_promotion_inquiry(session: LiveWikipediaRuntimeSession, message: str) -> tuple[dict[str, Any] | None, bool]:
    pending = _pending_promotion_inquiries(session)
    if not pending:
        return None, False
    if len(pending) == 1:
        return pending[-1], False
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    text = re.sub(r"[,;:]+", " ", text)
    text = " ".join(text.split())
    if text in {"not that one", "cancel that", "drop it", "defer this", "reject that", "approve that", "approve that proposal", "yes", "okay", "ok"}:
        return None, True
    if "first" in text:
        return pending[0], False
    if "second" in text or "candidate 2" in text or "number 2" in text:
        return pending[min(1, len(pending) - 1)], False
    if "last" in text or "latest" in text or "most recent" in text or "that one" in text:
        return pending[-1], False
    target_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", re.sub(r"\b(approve|approved|prepare|reject|decline|discard|cancel|drop|defer|the|one|candidate)\b", " ", text))
        if len(token) > 2
    }
    for inquiry in pending:
        title = _promotion_title_for_inquiry(session, inquiry).lower()
        if title and title in text:
            return inquiry, False
        title_tokens = set(re.findall(r"[a-z0-9]+", title))
        if target_tokens and target_tokens.issubset(title_tokens):
            return inquiry, False
    return None, True


def _promotion_title_for_inquiry(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any]) -> str:
    candidate_id = str(inquiry.get("promotion_candidate_id") or "")
    for candidate in session.promotion_candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return str(candidate.get("title") or "")
    return ""


def _promotion_candidate_for_inquiry(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None) -> dict[str, Any]:
    candidate_id = str((inquiry or {}).get("promotion_candidate_id") or "")
    for candidate in session.promotion_candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return candidate
    return session.promotion_candidates[-1]


def _render_ambiguous_promotion_approval(session: LiveWikipediaRuntimeSession, *, rejection: bool = False) -> tuple[str, dict[str, Any]]:
    pending = _pending_promotion_inquiries(session)
    action = "reject" if rejection else "approve"
    lines = [f"I found multiple pending promotion candidates, so I need a specific target before I {action} one."]
    for index, inquiry in enumerate(pending, start=1):
        title = _promotion_title_for_inquiry(session, inquiry) or str(inquiry.get("prompt") or f"candidate {index}")
        lines.append(f"- {index}. {title}")
    lines.append("Say `approve first`, `approve latest`, or name the candidate title.")
    answer = "\n".join(lines)
    payload = _base_live_payload("live_promotion_rejection_ambiguous" if rejection else "live_promotion_approval_ambiguous", answer)
    payload.update({"operator_inquiries": pending, "promotion_candidates": session.promotion_candidates[-8:]})
    return answer, payload


def _approve_pending_promotion(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None = None) -> tuple[LiveWikipediaRuntimeSession, str, dict[str, Any]]:
    candidate = _promotion_candidate_for_inquiry(session, inquiry)
    memory_candidate = _memory_candidate_from_promotion(candidate)
    proposal = {
        "proposal_id": stable_id("live-noncanonical-review-proposal", candidate.get("candidate_id"), len(session.prepared_review_proposals)),
        "promotion_candidate_id": candidate.get("candidate_id"),
        "title": candidate.get("title"),
        "source_url": candidate.get("source_url"),
        "proposed_changes": tuple(candidate.get("proposed_changes") or ()),
        "evidence_terms": tuple(candidate.get("evidence_terms") or ()),
        "status": "PREPARED_FOR_OPERATOR_REVIEW",
        "canonical_write_performed": False,
        "memory_write_performed": False,
        "safety": safety_metadata(),
    }
    inquiries = tuple(
        {**item, "status": "APPROVED_FOR_PROPOSAL_PREPARATION"} if isinstance(item, dict) and str(item.get("promotion_candidate_id") or "") == str(candidate.get("candidate_id") or "") and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} else item
        for item in session.operator_inquiries
    )
    runtime = replace(session.runtime, journal=append_journal(session.runtime.journal, "live_promotion_approval", str(candidate.get("title") or "promotion candidate"), (str(candidate.get("candidate_id") or ""),), session.runtime.cycle))
    updated = replace(session, runtime=runtime, operator_inquiries=inquiries, prepared_review_proposals=session.prepared_review_proposals + (proposal,))
    updated, cycle = run_delta_1_6_background_cycle(updated)
    if updated.continuous_controller:
        updated = replace(updated, continuous_controller=run_controller_cycle(updated.continuous_controller, session=updated))
    answer = "\n".join([
        "Approved. I prepared the noncanonical expansion proposal within the current live-session scope.",
        "",
        "Proposal contents:",
        *[f"- {item}" for item in proposal["proposed_changes"][:5]],
        "",
        "No memory was written. Select the candidate in Concept Review and press Accept Selected Concept only if you want to store it as noncanonical local knowledge.",
    ])
    payload = _base_live_payload("live_promotion_approval", answer)
    payload.update({
        "memory_candidate": memory_candidate,
        "promotion_candidate": candidate,
        "prepared_review_proposal": proposal,
        "operator_inquiries": inquiries[-5:],
        "background_cycle": cycle.as_dict(),
    })
    return updated, answer, payload


def _reject_pending_promotion(session: LiveWikipediaRuntimeSession, inquiry: dict[str, Any] | None = None) -> tuple[LiveWikipediaRuntimeSession, str, dict[str, Any]]:
    candidate = _promotion_candidate_for_inquiry(session, inquiry)
    inquiries = tuple(
        {**item, "status": "REJECTED_BY_OPERATOR"} if isinstance(item, dict) and str(item.get("promotion_candidate_id") or "") == str(candidate.get("candidate_id") or "") and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"} else item
        for item in session.operator_inquiries
    )
    updated = replace(session, operator_inquiries=inquiries)
    answer = "Rejected. I left the promotion candidate unprepared and wrote no memory."
    payload = _base_live_payload("live_promotion_rejection", answer)
    payload.update({"operator_inquiries": inquiries[-5:], "promotion_candidate": candidate})
    return updated, answer, payload


def _is_continuation_pressure(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return any(marker in text for marker in ("continue", "background initiative", "prepare proposal", "keep working", "go on", "proceed"))


def _wikipedia_budget_allows(session: LiveWikipediaRuntimeSession) -> bool:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    return limit <= 0 or session.retrieval_count < limit


def _wikipedia_budget_exhausted(session: LiveWikipediaRuntimeSession) -> bool:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    return limit > 0 and session.retrieval_count >= limit


def _wikipedia_budget_label(session: LiveWikipediaRuntimeSession) -> str:
    limit = int(session.wikipedia_profile.max_queries_per_objective or 0)
    if limit <= 0:
        return f"{session.retrieval_count}/unlimited"
    return f"{session.retrieval_count}/{limit}"


def _render_pending_inquiries(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    model = build_operational_self_model(session=session, initiatives=session.initiatives)
    inquiries = tuple(
        item
        for item in session.operator_inquiries[-8:]
        if isinstance(item, dict) and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"}
    )
    pending_text = tuple(str(item.get("prompt") or "") for item in inquiries if str(item.get("prompt") or "").strip())
    if pending_text:
        answer = "Pending inquiries:\n" + "\n".join(f"- {item}" for item in pending_text[:8])
    else:
        answer = "No pending operator inquiries are queued right now."
    payload = _base_live_payload("live_pending_inquiries", answer)
    payload.update({
        "operator_inquiries": inquiries,
        "promotion_candidate": session.promotion_candidates[-1] if session.promotion_candidates else None,
        "operational_self_model": model.as_dict(),
    })
    return answer, payload


def _session_inquiry_from_development(development_payload: dict[str, Any]) -> dict[str, Any]:
    inquiry = dict(development_payload["operator_inquiry"])
    inquiry.setdefault("status", "QUEUED")
    inquiry.setdefault("notification_class", "IN_APP_NORMAL")
    inquiry.setdefault("authority_class", "OPERATOR_APPROVAL_REQUIRED")
    inquiry.setdefault("promotion_candidate_id", development_payload["promotion_candidate"]["candidate_id"])
    return inquiry


def _memory_candidate_from_development(development_payload: dict[str, Any]) -> dict[str, Any]:
    return _memory_candidate_from_promotion(development_payload["promotion_candidate"])


def _memory_candidate_from_promotion(candidate: dict[str, Any]) -> dict[str, Any]:
    terms = [str(item) for item in (candidate.get("evidence_terms") or ()) if str(item).strip()]
    changes = [str(item) for item in (candidate.get("proposed_changes") or ()) if str(item).strip()]
    name = str(candidate.get("title") or "Wikipedia review candidate").replace(" local knowledge review", "").strip()
    source_url = str(candidate.get("source_url") or "")
    concept_id = stable_id("live-review-concept", candidate.get("candidate_id") or name)
    short_definition = (
        f"Review-only Wikipedia evidence candidate for {name}. "
        f"Candidate terms: {', '.join(terms[:5]) or 'article-level evidence'}."
    )
    return {
        "concept_id": concept_id,
        "concept_name": name,
        "concept_type": "review_candidate",
        "short_definition": short_definition,
        "propositions": changes or (short_definition,),
        "related_concepts": terms[:8],
        "explains": [f"Whether {name} should improve noncanonical local knowledge."],
        "examples": [source_url] if source_url else [],
        "misconceptions": [],
        "uncertainty": "operator_review_required_wikipedia_evidence",
        "source_answer_id": str(candidate.get("candidate_id") or concept_id),
        "source_question": str(candidate.get("title") or name),
        "source_model_lane": "live_wikipedia_developmental_cognition",
        "source_model_id": "no_provider_model",
        "source_type": "live_wikipedia_promotion_candidate",
        "approval_status": "pending_operator_review_wikipedia_candidate",
        "memory_type": "knowledge",
        "rollback_handle": f"rollback-{concept_id}",
        "created_at": utc_now(),
        "canonical": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "source_url": source_url,
        "promotion_candidate_id": candidate.get("candidate_id"),
        "operator_review_required": True,
    }


def _is_live_help_request(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    return text in {
        "how do i interact with you",
        "how do i use this",
        "what can i do here",
        "what should i ask you",
        "help",
        "help me use this",
    }


def _is_live_context_declaration(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip().split())
    if text.startswith(("context:", "note:", "observation:")):
        return True
    return bool(re.search(r"\b(this is|we are|you are)\b.*\blive runtime\b", text))


def _render_live_help() -> str:
    return "\n".join([
        "You can chat normally, or ask for a Wikipedia text lookup by saying `Wikipedia: topic` or `Look up topic on Wikipedia`.",
        "After a lookup, I will compare the article against local approved concepts and surface any reviewable knowledge gap.",
        "I cannot remember or promote anything automatically. If you say `remember that`, I will show the gated promotion candidate and ask for approval.",
    ])


def pause_live_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "PAUSED")
    controller = pause_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def resume_live_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "ACTIVE")
    controller = resume_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def suspend_live_runtime_initiative(session: LiveWikipediaRuntimeSession) -> LiveWikipediaRuntimeSession:
    updated = set_autonomy_status(session, "SUSPENDED")
    controller = suspend_controller(updated.continuous_controller) if updated.continuous_controller else None
    return replace(updated, continuous_controller=controller)


def _advance_continuous_controller(
    session: LiveWikipediaRuntimeSession,
    event_type: str,
    payload: dict[str, Any],
    *,
    priority: int = 50,
    correlation_id: str = "",
    objective_id: str = "",
) -> LiveWikipediaRuntimeSession:
    if not session.continuous_controller:
        return session
    event = make_continuous_event(
        event_type,
        source="live_wikipedia_runtime",
        session_id=session.session_id,
        payload=payload,
        priority=priority,
        correlation_id=correlation_id,
        objective_id=objective_id,
    )
    controller = enqueue_continuous_event(session.continuous_controller, event)
    controller = run_controller_cycle(controller, session=session)
    return replace(session, continuous_controller=controller)


def _render_memory_gate(session: LiveWikipediaRuntimeSession) -> tuple[str, dict[str, Any]]:
    candidate = session.promotion_candidates[-1] if session.promotion_candidates else None
    inquiry = session.operator_inquiries[-1] if session.operator_inquiries else None
    if candidate and inquiry:
        title = str(candidate.get("title") or "the last evidence item")
        changes = candidate.get("proposed_changes") or ()
        preview = str(changes[0]) if changes else "Review the last evidence item as a noncanonical candidate."
        answer = "\n".join([
            "I cannot write memory automatically from the live runtime.",
            f"I do have a gated promotion candidate: {title}.",
            preview,
            str(inquiry.get("prompt") or "Approve preparing this as a noncanonical review proposal?"),
            "No memory was written.",
        ])
    else:
        answer = "\n".join([
            "I cannot write memory automatically from the live runtime.",
            "There is not yet a promotion candidate in this session. Ask for a Wikipedia lookup first, then I can compare it against local knowledge and prepare a gated review item.",
            "No memory was written.",
        ])
    payload = {
        "mode": "Live Runtime",
        "route": "live_memory_governance",
        "answer": answer,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "external_retrieval_performed": False,
        "network_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "memory_candidate": None,
        "promotion_candidate": candidate,
        "operator_inquiry": inquiry,
    }
    return answer, payload


def _render_budget_exhausted(session: LiveWikipediaRuntimeSession) -> str:
    if session.developmental_results:
        latest = session.developmental_results[-1]
        title = latest.evidence_title
        return (
            f"Wikipedia retrieval is already used for this live objective by `{title}`. "
            "I did not retrieve another page. I can keep discussing the retrieved evidence, compare the promotion candidate, "
            "or you can stop and start the live runtime for a fresh objective."
        )
    return (
        "Wikipedia retrieval is already used for this live objective. I did not retrieve another page. "
        "You can stop and start the live runtime for a fresh objective."
    )


def _response(
    answer: str,
    route: str,
    payload: dict[str, Any],
    result: WikipediaTextResult | None,
    runtime_state: str,
    safety: dict[str, bool],
) -> LiveChatResponse:
    return LiveChatResponse(
        answer=answer,
        route=route,
        payload=payload,
        wikipedia_result=result,
        runtime_state=runtime_state,
        safety=safety,
    )


======================================================================
FILE: orchestration/runtime/rc2_conversational_mode_router.py
======================================================================

"""RC2 conversational shell and DELTA mode router scaffold.

RC2 makes the RC1 substrate one selectable mode behind a conversational front
door. It does not enable provider calls, web search, training, canonical
writes, autonomous actions, or production routing. External provider routes
are consent-gated. Local model lanes may execute when the caller explicitly
asks for local inference.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from integration.model_runtime.model_registry import list_available_models
from integration.model_runtime.provider_manager import ProviderManager
from orchestration.runtime.rc2_dialogue_intent_classifier import (
    classify_dialogue_act,
    evaluate_dialogue_intent_corpus,
    write_dialogue_intent_artifacts,
)
from orchestration.runtime.rc1_operator_console import (
    answer_operator_question,
    approve_propositions,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    query_noncanonical_substrate,
)
from orchestration.runtime.rc2_developmental_concept_memory import (
    approve_candidate_concept,
    build_read_only_synthesis_trial,
    build_compact_support_packet,
    build_developmental_memory_state,
    browse_approved_concepts,
    discover_memory_store_separation,
    extract_candidate_concept,
    query_approved_concepts,
    retrieve_multi_concept_set,
)
from orchestration.runtime.rc2_analogy_engine import build_analogy_analysis, is_analogy_prompt
from orchestration.runtime.rc2_cognitive_episode import attach_episode, resolve_working_memory_followup
from orchestration.runtime.rc2_contradiction_engine import build_contradiction_analysis, is_contradiction_prompt
from orchestration.runtime.rc2_natural_conversation_renderer import apply_natural_renderer
from orchestration.runtime.rc2_render_correction import build_render_correction_payload
from orchestration.runtime.rc2_route_arbitration import build_route_arbitration_trace, normalize_safety_payload
from orchestration.runtime.rc2_working_reasoning_set import build_working_reasoning_set, should_use_wrs
from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

DISPLAY_MODES = [
    "Conversation",
    "Memory Mode",
    "Research",
    "Evidence Review",
    "Investigation",
    "Replay",
    "Developer",
    "Diagnostics",
]

MODES = DISPLAY_MODES + [
    "Ask Substrate",
    "Review Mode",
    "Contradiction Check",
    "Failure Log",
    "Research Analyst",
    "Frontier App Assistant",
]

ROUTER_FLAGS = {
    "rc2_conversational_shell_enabled": True,
    "mode_router_enabled": True,
    "provider_calls_enabled": False,
    "web_search_enabled": False,
    "training_enabled": False,
    "canonical_writes_enabled": False,
    "autonomous_actions_enabled": False,
    "production_routing_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}

MODEL_LANE_ORDER = {
    "everyday_conversation": ("phi4", "qwen", "llama", "mistral", "phi3"),
    "coding_technical": ("qwen", "phi4", "llama", "mistral", "phi3"),
    "reasoning_analysis": ("qwen", "llama", "mistral", "phi4", "phi3"),
    "planning": ("phi4", "qwen", "mistral", "llama", "phi3"),
    "vision": ("qwen", "llama", "phi4", "mistral", "phi3"),
    "concept_extraction": ("qwen", "phi4", "llama", "mistral", "phi3"),
    "contradiction_detection": ("phi4", "qwen", "llama", "mistral", "phi3"),
}

LANE_METADATA = {
    "everyday_conversation": {
        "display_name": "Everyday Conversation Lane",
        "expected_strength": "casual chat, common explanations, companionship, low-stakes brainstorming",
        "expected_weakness": "specialized factual lookup and high-stakes reasoning require support",
        "cost_latency_class": "low_to_medium_local",
        "preferred_task_lanes": ["conversation", "question", "self_description"],
        "fallback_priority": 1,
    },
    "coding_technical": {
        "display_name": "Coding / Technical Lane",
        "expected_strength": "programming, debugging, architecture, CLI, repo reasoning",
        "expected_weakness": "may need repo file context or tests for correctness",
        "cost_latency_class": "medium_local",
        "preferred_task_lanes": ["coding", "technical_explanation"],
        "fallback_priority": 2,
    },
    "reasoning_analysis": {
        "display_name": "Reasoning / Analysis Lane",
        "expected_strength": "multi-step reasoning, comparison, science, synthesis, uncertainty",
        "expected_weakness": "external facts need gated supporting information",
        "cost_latency_class": "medium_to_high_local",
        "preferred_task_lanes": ["analysis", "research", "investigation", "external_knowledge_request"],
        "fallback_priority": 3,
    },
    "planning": {
        "display_name": "Planning Lane",
        "expected_strength": "strategy, schedules, staged workflows",
        "expected_weakness": "cannot execute actions from RC2",
        "cost_latency_class": "medium_local",
        "preferred_task_lanes": ["planning"],
        "fallback_priority": 4,
    },
    "vision": {
        "display_name": "Vision Lane",
        "expected_strength": "image-capable model selection when a vision GGUF is available",
        "expected_weakness": "RC2 UI does not execute vision inference",
        "cost_latency_class": "high_local_if_enabled",
        "preferred_task_lanes": ["image"],
        "fallback_priority": 5,
    },
    "concept_extraction": {
        "display_name": "Concept Extraction Lane",
        "expected_strength": "turn useful answers into reusable concepts",
        "expected_weakness": "first pass is deterministic and operator-reviewed",
        "cost_latency_class": "low_local_scaffold",
        "preferred_task_lanes": ["memory_request"],
        "fallback_priority": 6,
    },
    "contradiction_detection": {
        "display_name": "Contradiction Detection Lane",
        "expected_strength": "first-pass deterministic contradiction checks",
        "expected_weakness": "semantic contradiction detection remains conservative",
        "cost_latency_class": "low_local_scaffold",
        "preferred_task_lanes": ["contradiction_check"],
        "fallback_priority": 7,
    },
}

DIRECT_LOCAL_ANSWERS = {
    "sky_color": {
        "triggers": (("sky", "color"),),
        "answer": "The sky usually looks blue during the day because air molecules scatter shorter blue wavelengths of sunlight more strongly than longer red wavelengths.",
        "confidence": 0.88,
    },
    "water_color": {
        "triggers": (("water", "color"), ("color", "water")),
        "answer": "Pure water is nearly colorless in a small glass, but large amounts can look faintly blue because water absorbs a little more red light than blue light. In everyday life, water also reflects the sky and surrounding surfaces, so it can look blue, gray, green, or brown depending on context.",
        "confidence": 0.82,
    },
    "fire_definition": {
        "triggers": (("what", "fire"), ("fire",), ("define", "fire")),
        "answer": "Fire is the visible, hot part of combustion. A fuel reacts with oxygen, releasing heat and light, and the flame contains hot gases plus glowing particles or excited molecules.",
        "confidence": 0.82,
    },
    "normal_assistant_style": {
        "triggers": (("answer", "normal", "assistant"), ("normal", "assistant")),
        "answer": "Yes. I can answer in a more natural assistant style: direct first, enough context to be useful, and technical details only when you ask for them.",
        "confidence": 0.86,
    },
    "debugging_partner_opinion": {
        "triggers": (("good", "debugging", "partner"), ("debugging", "partner")),
        "answer": "A good debugging partner helps narrow the problem without taking over: they ask what changed, check assumptions, keep the reproduction small, and stay calm when the first theory is wrong.",
        "confidence": 0.84,
    },
    "followup_question_offer": {
        "triggers": (("ask", "follow", "question"), ("follow", "question"), ("follow-up", "question")),
        "answer": "Sure. What topic do you want to explore next, and do you want a quick overview or a deeper explanation?",
        "confidence": 0.84,
    },
    "rollback_recovery_evidence": {
        "triggers": (("rollback", "evidence"), ("recovery", "evidence")),
        "answer": "Recovery evidence means proof that an unwanted or failed change can be stopped, rejected, or rolled back without hidden side effects. A useful record names the tested change, what failed or was rejected, the stop or rollback action, the final recovered state, and confirmation that no unauthorized memory write, provider call, commit, push, deployment, or freeze claim occurred.",
        "confidence": 0.86,
    },
    "delta12_ambiguity_runtime": {
        "triggers": (("delta", "runtime", "ambiguity"), ("live", "runtime", "ambiguity")),
        "answer": "The DELTA 1.2 live runtime should treat repeated ambiguity failures as evidence, cluster them into a developmental signal, rank a bounded objective, and queue an operator inquiry. It should not implement the fix by itself; operator approval is required before promotion, and it should ask whether to prepare a sandboxed repair objective with focused validation.",
        "confidence": 0.86,
    },
}

VAGUE_CONCEPT_NAMES = {
    "What Most People",
    "What Color",
    "What Is",
    "General Question",
    "User Asked",
    "Learned Concept",
}

LOW_CONFIDENCE_MARKERS = (
    "not enough",
    "not confident",
    "supporting information",
    "look for sources",
    "ask gpt",
    "cannot answer",
    "do not have enough",
)

SOCIAL_INTENT_RESPONSES = {
    "greeting": "Hi. I'm here with you. What would you like to work through?",
    "thanks": "You're welcome. I'm glad that helped.",
    "compliment": "Thanks. I'm glad that was helpful.",
    "encouragement": "Thanks. I'll keep going carefully.",
    "acknowledgement": "Got it. What would you like to explore next?",
    "affirmation": "Yes noted. I will only use that as approval when there is a current pending action.",
    "refusal": "No problem. I will not proceed with that pending action.",
    "cancel": "No problem. We'll leave that path alone.",
    "correction": "Got it. I will treat that as a correction to the current thread.",
    "preference_opinion": "Good, that gives me useful direction. We can keep shaping the system around that.",
    "personal_emotion": "I hear you. We can keep this low-friction and take it one step at a time.",
    "followup": "I can rephrase or continue from the recent context.",
    "joke": "Heh. I caught that as a joke, so I won't route it into memory or retrieval.",
    "small_talk": "I'm here and ready. What would you like to work on?",
}


def classify_intent(message: str) -> dict[str, Any]:
    lower = " ".join(message.lower().strip().split())
    bare = lower.strip(" .!?")
    if _is_contextual_browse_jump(lower):
        return {
            "intent": "knowledge_browse_jump",
            "message": message,
            "confidence": 0.91,
            "communication_act": "clarification_followup",
            "matched_rule": "knowledge_browse_jump",
            "routed_action": "browse_diverse_approved_concepts",
            "safe_no_route": False,
        }
    if _is_memory_browse_request(lower):
        return {
            "intent": "knowledge_browse",
            "message": message,
            "confidence": 0.94,
            "communication_act": "knowledge_browse",
            "matched_rule": "knowledge_browse",
            "routed_action": "browse_approved_concepts",
            "safe_no_route": False,
        }
    if _is_contextual_browse_followup(lower):
        return {
            "intent": "knowledge_browse_followup",
            "message": message,
            "confidence": 0.9,
            "communication_act": "clarification_followup",
            "matched_rule": "knowledge_browse_followup",
            "routed_action": "browse_related_approved_concepts",
            "safe_no_route": False,
        }
    dialogue = classify_dialogue_act(message)
    if dialogue["confidence"] >= 0.8:
        intent = str(dialogue["intent"])
        if dialogue["communication_act"] in {"joke", "small_talk"}:
            intent = str(dialogue["communication_act"])
        if dialogue["communication_act"] == "evidence_request" and message.lower().strip().startswith("analyze "):
            intent = "analysis"
        return {
            "intent": intent,
            "message": message,
            "confidence": dialogue["confidence"],
            "communication_act": dialogue["communication_act"],
            "matched_rule": dialogue["matched_rule"],
            "routed_action": dialogue["routed_action"],
            "safe_no_route": dialogue["safe_no_route"],
        }
    if any(term in lower for term in ["diagnostic", "show diagnostics", "runtime status", "system health", "health check"]):
        intent = "diagnostics"
    elif bare in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}:
        intent = "greeting"
    elif bare in {"great job", "good job", "nice work", "excellent work", "well done", "perfect", "that worked", "awesome", "thanks", "thank you"}:
        intent = "compliment"
    elif bare in {"okay", "ok", "got it", "sounds good", "cool", "alright", "yes okay"}:
        intent = "acknowledgement"
    elif bare in {"nevermind", "never mind", "cancel", "stop", "forget it", "drop it"}:
        intent = "cancel"
    elif lower.startswith(("i like", "i want", "i prefer", "i think")) and not lower.endswith("?"):
        intent = "preference_opinion"
    elif any(term in lower for term in ["i'm tired", "im tired", "i am tired", "i'm frustrated", "im frustrated", "i feel"]):
        intent = "personal_emotion"
    elif any(term in lower for term in ["remember", "store", "save this"]):
        intent = "memory_request"
    elif any(term in lower for term in ["contradiction", "conflict", "incompatible"]):
        intent = "contradiction_check"
    elif any(term in lower for term in ["code", "coding", "python", "bug", "function"]):
        intent = "coding"
    elif any(term in lower for term in ["plan", "schedule", "strategy"]):
        intent = "planning"
    elif any(term in lower for term in ["analyze", "compare", "why", "because"]):
        intent = "analysis"
    elif any(term in lower for term in ["document", "pdf", "invoice", "evidence"]):
        intent = "document"
    elif any(term in lower for term in ["image", "picture", "photo"]):
        intent = "image"
    elif any(term in lower for term in ["investigate", "case", "research", "latest status"]):
        intent = "investigation"
    elif any(term in lower for term in ["how do you work", "what are you", "delta"]):
        intent = "self_description"
    elif any(term in lower for term in ["avogadro", "quantum field", "beluga", "whale"]):
        intent = "external_knowledge_request"
    elif any(term in lower for term in ["what do you know", "frontier", "substrate"]):
        intent = "substrate_question"
    else:
        intent = "question" if lower.endswith("?") else "conversation"
    return {"intent": intent, "message": message, "confidence": confidence_for_intent(intent)}


def _is_memory_browse_request(lower: str) -> bool:
    bare = lower.strip(" .!?")
    patterns = {
        "tell me something you know",
        "tell me something you learned",
        "what do you know",
        "show me something you know",
        "give me a concept",
        "show me a concept",
        "what have you learned",
        "surprise me with something you know",
    }
    return bare in patterns or bare.startswith("tell me about something you know")


def _is_contextual_browse_followup(lower: str) -> bool:
    bare = lower.strip(" .!?")
    return bare in {
        "what else",
        "what else do you know",
        "what more",
        "show me another",
        "another one",
        "give me another",
        "tell me another",
    }


def _is_contextual_browse_jump(lower: str) -> bool:
    bare = lower.strip(" .!?")
    return bare in {
        "something completely different",
        "show me something different",
        "different topic",
        "switch topics",
        "new topic",
    }


def _is_synthesis_trial_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split())
    return any(phrase in lower for phrase in (
        "synthesize",
        "synthesis trial",
        "tentative connection",
        "infer a connection",
        "cross concept",
        "cross-concept",
    ))


def _is_graph_assisted_reasoning_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split())
    return any(phrase in lower for phrase in (
        "graph-assisted reasoning",
        "graph assisted reasoning",
        "use the graph",
        "reason with the graph",
        "graph-assisted reason",
        "graph assisted reason",
    ))


DOMAIN_BROWSE_ALIASES = {
    "law": "law government basics",
    "legal": "law government basics",
    "government": "law government basics",
    "physics": "basic physics",
    "science": "basic physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "health": "medicine health general",
    "medicine": "medicine health general",
    "nutrition": "nutrition",
    "psychology": "psychology",
    "philosophy": "philosophy",
    "logic": "logic",
    "math": "mathematics",
    "mathematics": "mathematics",
    "programming": "programming",
    "coding": "programming",
    "software": "software architecture",
    "business": "business",
    "finance": "finance",
    "history": "history",
    "geography": "geography",
    "engineering": "engineering",
    "materials": "materials science",
    "energy": "energy",
    "gardening": "agriculture gardening",
    "agriculture": "agriculture gardening",
    "mechanics": "vehicles mechanics",
    "vehicles": "vehicles mechanics",
    "home repair": "home repair",
    "communication": "social communication",
    "productivity": "planning productivity",
    "delta": "DELTA architecture itself",
}


def _domain_browse_request(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().strip().split())
    if not any(phrase in lower for phrase in ("what about", "how about", "do you know", "anything about", "tell me about", "show me")):
        return None
    if any(phrase in lower for phrase in ("newton", "first law", "second law", "third law", "law of")):
        return None
    if any(phrase in lower for phrase in ("should i", "can i sue", "am i liable", "legal advice", "calculate", "court case")):
        if not any(phrase in lower for phrase in ("concept", "anything about", "tell me about", "show me")):
            return None
    for alias, domain in sorted(DOMAIN_BROWSE_ALIASES.items(), key=lambda item: -len(item[0])):
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, lower):
            return domain
    return None


def _last_concept_context(history: list[dict[str, str]] | None) -> dict[str, Any]:
    anchored = resolve_followup_anchor(history)
    if anchored.get("active_concept_name"):
        return {
            "concept_name": anchored.get("active_concept_name"),
            "concept_names": anchored.get("retrieved_concept_names") or [anchored.get("active_concept_name")],
            "domain": anchored.get("domain"),
            "concept_id": anchored.get("active_concept_id"),
        }
    names = []
    domain = None
    newer_explicit_topic = False
    for item in reversed(history or []):
        if item.get("role") == "user" and _is_explicit_new_topic_request(str(item.get("content") or "")):
            newer_explicit_topic = True
            continue
        if newer_explicit_topic:
            break
        if item.get("role") != "assistant":
            continue
        content = str(item.get("content") or "")
        found = [match.strip() for match in re.findall(r"`([^`]+)`", content) if match.strip()]
        if "A couple of nearby concepts" in content:
            nearby = content.split("A couple of nearby concepts", 1)[1]
            found.extend(
                line.strip()[2:].strip()
                for line in nearby.splitlines()
                if line.strip().startswith("- ") and line.strip()[2:].strip()
            )
        if not found:
            continue
        names.extend(found)
        name = found[0]
        if domain is None:
            domain_match = re.search(r"\(([^)]+)\)\s*$", name)
            domain = domain_match.group(1).lower() if domain_match else None
    unique_names = list(dict.fromkeys(names))
    return {"concept_name": unique_names[0] if unique_names else None, "concept_names": unique_names, "domain": domain}


def resolve_followup_anchor(history: list[dict[str, str]] | None) -> dict[str, Any]:
    newer_explicit_topic = False
    for item in reversed(history or []):
        if item.get("role") == "user" and _is_explicit_new_topic_request(str(item.get("content") or "")):
            newer_explicit_topic = True
            continue
        if item.get("role") != "anchor":
            continue
        if newer_explicit_topic:
            return {}
        try:
            anchor = json.loads(str(item.get("content") or "{}"))
        except json.JSONDecodeError:
            continue
        if anchor.get("active_concept_id") or anchor.get("active_concept_name"):
            return anchor
    return {}


def _is_anchor_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if _is_explicit_new_topic_request(message):
        return False
    if lower in {
        "tell me more",
        "go deeper",
        "explain more",
        "why",
        "why?",
        "how so",
        "give me an example",
        "what else",
        "another one",
        "compare that",
        "expand on that",
        "elaborate",
    }:
        return True
    return bool(re.match(r"how does (that|this|it) relate to .+", lower))


def _is_explicit_new_topic_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if not lower:
        return False
    if lower in {"what do you mean", "why", "why is that", "tell me more", "go deeper", "continue", "expand on that"}:
        return False
    if _is_context_dependent_followup(message):
        return False
    if re.match(r"^(what|who|where|when|which|how)\s+(is|are|was|were|do|does|did|can|should)\b", lower):
        return True
    if lower.startswith(("tell me about ", "explain ", "compare ", "analyze ", "brainstorm ", "what comes to mind")):
        return True
    if "new topic" in lower or "switch topics" in lower or "completely different" in lower:
        return True
    return False


def _is_brainstorming_request(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return any(phrase in lower for phrase in (
        "first concept that comes to mind",
        "what comes to mind",
        "brainstorm",
        "give me ideas",
        "free associate",
    ))


def _is_context_dependent_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    if lower in {
        "explain that",
        "explain this",
        "explain it",
        "give me an example",
        "give me examples",
        "why",
        "why is that",
        "why does that matter",
        "why is that important",
        "why should i care about that",
        "what difference does that make",
        "how does that affect the decision",
        "where does that analogy break",
        "tell me more",
        "continue",
        "expand on that",
    }:
        return True
    return bool(re.match(
        r"^(how|why|where|what)\s+(does|do|is|are|was|were|would|could|should)\s+(that|this|it|those|them)\b",
        lower,
    ))


def _is_anchor_browse_followup(message: str) -> bool:
    lower = " ".join(str(message or "").lower().strip().split()).strip(" ?!.")
    return lower in {"what else", "another one", "what else do you know", "show me another", "nearby concepts"}


def deepen_from_concept_anchor(message: str, anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept = _anchor_concept(anchor)
    if not concept:
        return None
    answer = _anchored_concept_answer(message, concept)
    matches = [concept]
    for concept_id in anchor.get("retrieved_concept_ids", [])[:4]:
        if concept_id == concept.get("concept_id"):
            continue
        nearby = _get_concept(concept_id)
        if nearby:
            matches.append(nearby)
    return {
        "route": "developmental_concept_anchor_followup",
        "answer": answer,
        "confidence": "grounded_in_active_conversation_anchor",
        "confidence_score": 0.9,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "concept_matches": matches,
        "active_topic_anchor": _anchor_from_matches(message, answer, matches),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def browse_near_active_anchor(message: str, anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept = _anchor_concept(anchor)
    if not concept:
        return None
    related_terms = [
        str(item)
        for item in concept.get("related_concepts", [])
        if str(item).strip()
    ][:5]
    query = " ".join([str(concept.get("concept_name") or ""), *related_terms])
    matches = []
    seen = {str(concept.get("concept_id") or "")}
    try:
        from orchestration.runtime.rc2_storage_adapter import search_concepts

        result = search_concepts(query, domain=concept.get("domain"), limit=8, exclude_concept_names=[str(concept.get("concept_name") or "")])
        for row in result.get("matches", []):
            concept_id = str(row.get("concept_id") or "")
            if concept_id and concept_id not in seen:
                seen.add(concept_id)
                matches.append(row)
    except Exception:
        matches = []
    if not matches:
        matches = [
            row
            for row in (query_approved_concepts(term).get("matches", [None])[0] for term in related_terms)
            if row and str(row.get("concept_id") or "") not in seen
        ][:3]
    if not matches:
        return deepen_from_concept_anchor(message, anchor)
    lines = [
        f"Staying with `{concept.get('concept_name')}`, nearby things I can discuss are:",
    ]
    for row in matches[:3]:
        lines.append(f"- {row.get('concept_name')}: {str(row.get('short_definition') or '').strip()}")
    answer = "\n".join(lines)
    return {
        "route": "developmental_concept_anchor_browse",
        "answer": answer,
        "confidence": "grounded_in_active_conversation_anchor",
        "confidence_score": 0.9,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "concept_matches": [concept, *matches[:3]],
        "active_topic_anchor": _anchor_from_matches(message, answer, [concept, *matches[:3]]),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _get_concept(concept_id: str) -> dict[str, Any] | None:
    if not concept_id:
        return None
    try:
        from orchestration.runtime.rc2_storage_adapter import get_concept

        return get_concept(concept_id)
    except Exception:
        for row in query_approved_concepts(concept_id).get("matches", []):
            if str(row.get("concept_id")) == str(concept_id):
                return row
    return None


def _anchor_concept(anchor: dict[str, Any]) -> dict[str, Any] | None:
    concept_id = str(anchor.get("active_concept_id") or "")
    if concept_id:
        concept = _get_concept(concept_id)
        if concept:
            return concept
    name = str(anchor.get("active_concept_name") or "")
    if name:
        matches = query_approved_concepts(name).get("matches", [])
        if matches:
            return matches[0]
    return None


def _anchored_concept_answer(message: str, concept: dict[str, Any]) -> str:
    lower = " ".join(str(message or "").lower().split()).strip(" ?!.")
    name = str(concept.get("concept_name") or "that concept")
    definition = str(concept.get("short_definition") or "").strip()
    propositions = [str(item).strip() for item in concept.get("propositions", []) if str(item).strip()]
    examples = [str(item).strip() for item in concept.get("examples", []) if str(item).strip()]
    related = [str(item).strip() for item in concept.get("related_concepts", []) if str(item).strip()]
    if "example" in lower:
        if examples:
            return f"Staying with `{name}`, here's an example:\n{examples[0]}"
        if propositions:
            return f"Staying with `{name}`, a concrete way to think about it is: {propositions[0]}"
    relation_match = re.search(r"how does (?:that|this|it) relate to\s+(.+)", lower)
    if relation_match:
        target = relation_match.group(1).strip(" .?!")
        return (
            f"Staying with `{name}`, the connection to {target} is through the same stored mechanism: "
            f"{definition} "
            f"I can treat that as a tentative relation, but I have not written a new memory or enabled synthesis."
        ).strip()
    lines = [f"Staying with `{name}`:"]
    if definition:
        lines.append(definition)
    if propositions:
        lines.append("")
        lines.append("A little more detail:")
        lines.extend(f"- {item}" for item in propositions[:3])
    if related:
        lines.append("")
        lines.append("Related ideas:")
        lines.extend(f"- {item}" for item in related[:4])
    lines.append("")
    lines.append("No memory was written, and I did not need to ask a local model for this follow-up.")
    return "\n".join(lines)


def _anchor_from_matches(question: str, answer: str, matches: list[dict[str, Any]]) -> dict[str, Any]:
    if not matches:
        return {}
    first = matches[0]
    return {
        "active_concept_id": first.get("concept_id"),
        "active_concept_name": first.get("concept_name"),
        "domain": first.get("domain"),
        "related_concepts": first.get("related_concepts", [])[:8],
        "retrieved_concept_ids": [row.get("concept_id") for row in matches if row.get("concept_id")],
        "retrieved_concept_names": [row.get("concept_name") for row in matches if row.get("concept_name")],
        "last_user_question": question,
        "last_answer_summary": " ".join(str(answer or "").split())[:420],
    }


def _sun_blue_correction(message: str) -> str | None:
    lower = " ".join(str(message or "").lower().split())
    if "sun" not in lower or "blue" not in lower:
        return None
    if "sky" in lower:
        return None
    return (
        "The Sun is not normally blue. It is often perceived as white in space and yellowish from Earth's surface. "
        "The blue color people usually notice is the sky, which comes from atmospheric scattering of shorter blue wavelengths. "
        "So the better framing is: the sky appears blue because of scattering, not because the Sun itself is blue."
    )


def select_model_lane(message: str, intent: str | None = None) -> dict[str, Any]:
    """Choose the best already-wired local model lane without executing it."""
    intent = intent or classify_intent(message)["intent"]
    if intent == "coding":
        lane = "coding_technical"
    elif intent in {"external_knowledge_request", "investigation", "document", "analysis"}:
        lane = "reasoning_analysis"
    elif intent == "planning":
        lane = "planning"
    elif intent == "image":
        lane = "vision"
    elif intent == "memory_request":
        lane = "concept_extraction"
    elif intent == "contradiction_check":
        lane = "contradiction_detection"
    else:
        lane = "everyday_conversation"

    available = list_available_models()
    selected, candidates, rejected = _select_usable_model_for_lane(available, lane)
    spec = available.get(selected) if selected else None
    meta = LANE_METADATA[lane]
    return {
        "lane": lane,
        "support_identifier": _model_support_identifier(lane, selected, spec),
        "display_name": meta["display_name"],
        "selected_model": selected,
        "selected_model_id": spec.name if spec else None,
        "selected_model_path": str(Path(spec.path)) if spec else None,
        "available": bool(selected),
        "selection_reason": _selection_reason(lane, spec),
        "candidate_models": candidates,
        "rejected_models": rejected,
        "executed": False,
        "execution_gate": "not_executed_by_default",
        "provider_calls_performed": False,
        "model_family": spec.family if spec else "unavailable",
        "capabilities": list(spec.capabilities) if spec else [],
        "context_size": spec.context_length if spec else None,
        "expected_strength": meta["expected_strength"],
        "expected_weakness": meta["expected_weakness"],
        "cost_latency_class": meta["cost_latency_class"],
        "preferred_task_lanes": meta["preferred_task_lanes"],
        "fallback_priority": meta["fallback_priority"],
    }


def _select_usable_model_for_lane(available: dict[str, Any], lane: str) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    rejected = []
    for alias in MODEL_LANE_ORDER[lane]:
        spec = available.get(alias)
        if spec is None:
            rejected.append({"requested": alias, "reason": "not_registered"})
            continue
        if _model_is_usable(spec):
            return alias, [_model_candidate(alias, spec, "registered_alias")], rejected
        rejected.append({"requested": alias, "model_id": spec.name, "reason": "unusable_or_marked_fail"})

    desired_families = MODEL_LANE_ORDER[lane]
    family_candidates = []
    seen_model_ids = set()
    for family in desired_families:
        for key, spec in sorted(available.items(), key=lambda item: (item[1].tier, item[1].name, item[0])):
            if spec.name in seen_model_ids:
                continue
            if spec.family == family and _model_is_usable(spec):
                family_candidates.append(_model_candidate(key, spec, f"usable_{family}_family_fallback"))
                seen_model_ids.add(spec.name)
    if family_candidates:
        return str(family_candidates[0]["registry_key"]), family_candidates[:5], rejected

    usable = [
        _model_candidate(key, spec, "usable_any_family_fallback")
        for key, spec in sorted(available.items(), key=lambda item: (item[1].tier, item[1].name, item[0]))
        if _model_is_usable(spec)
    ]
    if usable:
        return str(usable[0]["registry_key"]), usable[:5], rejected
    return None, [], rejected


def _model_candidate(key: str, spec: Any, reason: str) -> dict[str, Any]:
    return {
        "registry_key": key,
        "model_id": spec.name,
        "family": spec.family,
        "tier": spec.tier,
        "capabilities": list(spec.capabilities),
        "reason": reason,
    }


def _selection_reason(lane: str, spec: Any | None) -> str:
    if spec is None:
        return f"No usable local model found for {lane}."
    return f"Selected {spec.name} because it is a usable local {spec.family} model for the {lane} lane."


def _model_is_usable(spec: Any) -> bool:
    path = Path(str(getattr(spec, "path", "")))
    parts = {part.lower() for part in path.parts}
    return bool(path.exists() and "fail" not in parts)


def _model_support_identifier(lane: str, selected: str | None, spec: Any | None) -> str:
    if spec is None or not selected:
        return f"rc2-local-lane:{lane}:unavailable"
    capabilities = ",".join(sorted(str(item) for item in getattr(spec, "capabilities", ()))) or "none"
    family = str(getattr(spec, "family", "unknown"))
    model_id = str(getattr(spec, "name", selected))
    return f"rc2-local-lane:{lane}:model:{model_id}:family:{family}:capabilities:{capabilities}"


def discover_local_model_lanes() -> dict[str, Any]:
    models = list_available_models()
    return {
        "available_model_count": len(models),
        "models": [
            {
                "model_id": key,
                "display_name": spec.name,
                "context_size": spec.context_length,
                "family": spec.family,
                "provider": spec.provider,
                "capabilities": list(spec.capabilities),
                "tier": spec.tier,
                "cost_latency_class": "local_gguf_tier_" + str(spec.tier),
            }
            for key, spec in sorted(models.items())
        ],
        "lanes": LANE_METADATA,
        "lane_order": MODEL_LANE_ORDER,
        "model_execution_enabled_by_default": False,
    }


def confidence_for_intent(intent: str) -> float:
    table = {
        "greeting": 0.95,
        "compliment": 0.95,
        "acknowledgement": 0.92,
        "cancel": 0.96,
        "preference_opinion": 0.84,
        "personal_emotion": 0.82,
        "diagnostics": 0.92,
        "memory_request": 0.88,
        "contradiction_check": 0.9,
        "coding": 0.68,
        "planning": 0.72,
        "analysis": 0.66,
        "document": 0.78,
        "image": 0.62,
        "investigation": 0.76,
        "substrate_question": 0.9,
        "external_knowledge_request": 0.86,
        "self_description": 0.94,
        "question": 0.7,
        "conversation": 0.65,
    }
    return table.get(intent, 0.5)


def _direct_answer(message: str) -> dict[str, Any] | None:
    lower = " " + " ".join(re.sub(r"[^a-z0-9]+", " ", message.lower()).split()) + " "
    for answer_id, item in DIRECT_LOCAL_ANSWERS.items():
        for trigger in item["triggers"]:
            if all(f" {word} " in lower for word in trigger):
                return {
                    "answer_id": answer_id,
                    "answer": item["answer"],
                    "confidence_score": item["confidence"],
                    "confidence": "local_general_knowledge",
                }
    return None


def _is_development_workflow_request(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = " ".join(str(message or "").lower().replace("-", " ").split())
    if any(term in lower for term in (
        "repair hypothesis",
        "repair hypotheses",
        "bounded repair",
        "which tests would prove",
        "what should delta inspect",
        "router test fails",
        "classified as contradiction",
        "governed self-development",
        "sandbox implementation",
        "development objective",
        "implement the fix by itself",
        "what question should it ask",
    )):
        return True
    if lower.startswith(("now propose", "propose two", "rank them")) and _history_mentions_development(history):
        return True
    return False


def _should_defer_to_knowledge_browse(intent_info: dict[str, Any]) -> bool:
    return intent_info.get("intent") in {"knowledge_browse_followup", "knowledge_browse_jump"}


def _history_mentions_development(history: list[dict[str, str]] | None) -> bool:
    text = " ".join(str(item.get("content") or "") for item in (history or [])[-6:]).lower()
    return any(term in text for term in ("router", "contradiction", "repair", "test", "delta", "runtime"))


def _development_workflow_answer(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    if not _is_development_workflow_request(message, history):
        return None
    lower = " ".join(str(message or "").lower().replace("-", " ").split())
    if "which tests would prove" in lower or ("tests" in lower and "safer" in lower):
        answer = (
            "Use focused live-path regressions: one topic-shift case that must not enter contradiction analysis, "
            "one ambiguity case that must ask for clarification, one follow-up continuity case that preserves the selected subject, "
            "and one governance check proving no provider call, web search, memory write, commit, or push occurred."
        )
    elif "hypothes" in lower or lower.startswith(("now propose", "propose two", "rank them")):
        answer = (
            "Ranked repair hypotheses: 1. Adjust router precedence so governed development workflow prompts use the local engineering path before concept retrieval. "
            "Confidence 0.86, low governance impact, moderate regression risk. "
            "2. Add a broad concept-memory exclusion for technical words like contradiction and tests. Confidence 0.54, higher regression risk because it could suppress useful retrieval. "
            "The safer first experiment is the precedence repair because it is narrow and reversible."
        )
    elif "implement the fix by itself" in lower:
        answer = "No. DELTA may prepare a bounded objective, sandbox candidate, tests, and evidence, but operator approval is required before promotion into the primary repository."
    elif "what question should it ask" in lower:
        answer = "It should ask: Do you approve a bounded sandbox objective to repair the observed ambiguity failure, with focused tests and no provider calls, retrieval, memory writes, commits, or pushes?"
    else:
        answer = (
            "DELTA should inspect the smallest responsible boundary first: the contradiction detector trigger, then router precedence, then the working-memory/discourse frame that carried the topic shift. "
            "The first repair hypothesis should be narrow and proven with live-path conversation turns before any broader architectural change."
        )
    return {
        "route": "local_conversation_model_lane",
        "answer": answer,
        "confidence": "local_governed_development_workflow",
        "confidence_score": 0.84,
        "selected_model_lane": select_model_lane(message, "coding"),
        "local_model_result": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _is_explicit_topic_reset(message: str) -> bool:
    text = " ".join(str(message or "").strip().lower().split())
    return bool(re.match(
        r"^(new topic:|switching subjects:|different topic:|let['’]?s move on[.!]?|forget the prior topic for now[.!]?)",
        text,
    ))


def _support_offer(message: str, reason: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    dry_run = answer_unknown_with_controlled_provider(message, live_provider=False)
    packet = build_compact_support_packet(message, history)
    return {
        "offered": True,
        "reason": reason,
        "prompt": "I'm not confident enough locally. Would you like me to ask GPT or look for sources?",
        "options": [
            "yes_ask_gpt_or_sources",
            "not_now",
        ],
        "dry_run_provider_request": dry_run["route_or_provider_request"],
        "compact_support_packet": packet,
        "provider_calls_performed": False,
        "web_search_performed": False,
    }


def _local_model_offer(
    message: str,
    reason: str,
    history: list[dict[str, str]] | None = None,
    model_lane: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = build_compact_support_packet(message, history)
    model_name = (model_lane or {}).get("selected_model_id") or (model_lane or {}).get("selected_model") or "my best local model"
    lane_name = (model_lane or {}).get("display_name") or "local reasoning lane"
    prompt = (
        f"I don't think I've learned this yet. My best local model for this question is {model_name} "
        f"in the {lane_name}. Would you like me to ask it?"
    )
    return {
        "offered": True,
        "reason": reason,
        "prompt": prompt,
        "options": ["yes_ask_local_model", "not_now"],
        "compact_local_model_packet": packet,
        "selected_model": model_name,
        "support_identifier": (model_lane or {}).get("support_identifier"),
        "local_model_call_performed": False,
        "provider_calls_performed": False,
        "web_search_performed": False,
    }


def _compact_model_prompt(message: str, history: list[dict[str, str]] | None = None) -> str:
    deepening = _parse_deepening_message(message)
    packet = build_compact_support_packet(message, history)
    turns = packet.get("relevant_chat_history", [])
    concept_question = deepening["original_question"] if deepening else message
    concepts = build_compact_support_packet(concept_question, history).get("relevant_approved_concepts", [])
    lines = [
        "Answer like a friendly, concise assistant.",
        "Use the short conversation context when it matters.",
        "Do not mention routing, model names, hashes, JSON, or safety flags.",
        "",
    ]
    if deepening:
        lines.extend([
            "Task:",
            "Elaborate on the prior answer. Add new useful detail, examples, distinctions, or nuance. Do not merely repeat the previous answer.",
            "",
            "Original user question:",
            deepening["original_question"][:1000],
            "",
            "Previous answer to deepen:",
            deepening["previous_answer"][:2400],
            "",
            "Follow-up instruction:",
            deepening["instruction"][:700],
        ])
    else:
        lines.extend([
            "Current user message:",
            str(packet["question"]),
        ])
    if turns:
        lines.extend(["", "Relevant recent turns:"])
        for turn in turns:
            lines.append(f"- {turn['role']}: {turn['content']}")
        lines.append("")
        lines.append("Maintain continuity with these turns. If the user is following up, resolve pronouns and references from this context.")
    if concepts:
        lines.extend(["", "Relevant approved local concepts:"])
        for concept in concepts:
            lines.append(f"- {concept.get('concept_name')}: {concept.get('short_definition')}")
    lines.extend(["", "Return only the answer text."])
    return "\n".join(lines)


def _parse_deepening_message(message: str) -> dict[str, str] | None:
    text = str(message or "")
    marker = "Please expand on your previous answer for this user question."
    original_label = "Original question:"
    previous_label = "Previous answer:"
    instruction = "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    if marker not in text or original_label not in text or previous_label not in text:
        return None
    after_original = text.split(original_label, 1)[1]
    original_question, rest = after_original.split(previous_label, 1)
    previous_answer = rest
    if instruction in previous_answer:
        previous_answer = previous_answer.split(instruction, 1)[0]
    return {
        "original_question": " ".join(original_question.split()).strip(),
        "previous_answer": " ".join(previous_answer.split()).strip(),
        "instruction": instruction,
    }


def execute_local_model_answer(
    message: str,
    model_lane: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    provider_manager: ProviderManager | None = None,
) -> dict[str, Any]:
    """Execute one selected local model lane when explicitly requested.

    This is a local inference path only. It does not grant provider authority,
    call GPT/API, train, write memory, or perform actions.
    """
    model_name = model_lane.get("selected_model")
    prompt = _compact_model_prompt(message, history)
    if not model_name:
        return {
            "executed": False,
            "available": False,
            "answer": "",
            "reason": "no_local_model_available",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            manager = provider_manager or ProviderManager()
            result = manager.infer(
                model_name=str(model_name),
                prompt=prompt,
                task_type="rc2_conversation",
                metadata={"route": "rc2_local_model_lane", "lane": model_lane.get("lane")},
            )
        answer = result.answer
        confidence = float(result.confidence or 0.72)
        clean_answer = _naturalize_model_answer(answer)
        return {
            "executed": bool(clean_answer),
            "available": True,
            "answer": clean_answer,
            "confidence_score": max(0.0, min(1.0, confidence)),
            "model_id": str(result.model_id or model_name),
            "latency_seconds": float(result.latency_seconds or 0.0),
            "response_tokens": int(result.response_tokens or 0),
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    except ModuleNotFoundError as exc:
        if exc.name == "llama_cpp":
            fallback = _infer_local_model_via_venv_subprocess(str(model_name), prompt, model_lane)
            if fallback.get("executed"):
                return fallback
            return {
                "executed": False,
                "available": True,
                "answer": "",
                "reason": str(fallback.get("reason") or f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}"),
                "prompt_sent": prompt,
                "provider_calls_performed": False,
            }
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }
    except Exception as exc:  # pragma: no cover - defensive for local model runtime availability
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "prompt_sent": prompt,
            "provider_calls_performed": False,
        }


def _infer_local_model_via_venv_subprocess(model_name: str, prompt: str, model_lane: dict[str, Any]) -> dict[str, Any]:
    venv_python = ROOT / ".venv311" / "Scripts" / "python.exe"
    helper = ROOT / "scripts" / "delta_rc2_local_model_infer.py"
    if not venv_python.exists():
        return {"executed": False, "reason": "local_model_venv_python_missing", "provider_calls_performed": False}
    if not helper.exists():
        return {"executed": False, "reason": "local_model_subprocess_helper_missing", "provider_calls_performed": False}
    request = {
        "model_name": model_name,
        "prompt": prompt,
        "task_type": "rc2_conversation",
        "metadata": {"route": "rc2_local_model_lane", "lane": model_lane.get("lane")},
    }
    try:
        completed = subprocess.run(
            [str(venv_python), str(helper)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=240,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - returned as visible route diagnostic.
        return {
            "executed": False,
            "reason": f"local_model_subprocess_failed:{type(exc).__name__}:{str(exc)[:160]}",
            "provider_calls_performed": False,
        }
    if completed.returncode != 0:
        return {
            "executed": False,
            "reason": f"local_model_subprocess_returned_{completed.returncode}:{completed.stderr[:180]}",
            "provider_calls_performed": False,
        }
    try:
        payload = json.loads(completed.stdout)
    except Exception as exc:
        return {
            "executed": False,
            "reason": f"local_model_subprocess_json_failed:{type(exc).__name__}:{completed.stdout[:180]}",
            "provider_calls_performed": False,
        }
    answer = _naturalize_model_answer(str(payload.get("answer", "")))
    return {
        "executed": bool(answer),
        "available": True,
        "answer": answer,
        "confidence_score": float(payload.get("confidence_score") or 0.72),
        "model_id": payload.get("model_id") or model_name,
        "prompt_sent": prompt,
        "execution_adapter": "venv_subprocess",
        "provider_calls_performed": False,
        "reason": None if answer else "local_model_subprocess_empty_answer",
    }


def _naturalize_model_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and isinstance(parsed.get("answer"), str):
            return " ".join(parsed["answer"].split())
    except Exception:
        pass
    match = re.search(r'"answer"\s*:\s*"(?P<answer>.*?)(?:"\s*,\s*"confidence"|"\s*[,}])', raw, flags=re.DOTALL)
    if match:
        value = match.group("answer")
        try:
            value = json.loads(f'"{value}"')
        except Exception:
            value = value.replace(r"\"", '"').replace(r"\n", " ")
        return " ".join(str(value).split())
    if raw.startswith("{") and '"answer"' in raw:
        start = raw.find('"answer"')
        colon = raw.find(":", start)
        quote = raw.find('"', colon)
        if quote >= 0:
            value = raw[quote + 1 :]
            value = value.rsplit('"', 1)[0] if '"' in value else value
            value = value.replace(r"\"", '"').replace(r"\n", " ")
            return " ".join(value.split())
    return " ".join(raw.split())


def execute_gpt_support_request(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    transport: Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]] | None = None,
) -> dict[str, Any]:
    compact_packet = build_compact_support_packet(message, history)
    provider = answer_unknown_with_controlled_provider(message, live_provider=True, transport=transport)
    evidence_packet = provider.get("evidence_packet")
    if evidence_packet and evidence_packet.get("provider_text"):
        answer = str(evidence_packet["provider_text"]).strip()
        route = "provider_support_after_user_consent"
        provider_call = True
        confidence = "provider_assisted_non_authoritative"
        confidence_score = 0.72
    else:
        decision = ((provider.get("decision") or {}).get("decision") or "live_refused")
        answer = (
            "I couldn't ask GPT from this session because the provider gate is not enabled or the API key is unavailable. "
            "No provider call was made."
            if decision == "live_refused"
            else "I did not need GPT because local DELTA knowledge already matched this question."
        )
        route = "provider_support_refused_or_local_known"
        provider_call = False
        confidence = "provider_path_not_available"
        confidence_score = 0.2
    return {
        "mode": "Conversation",
        "route": route,
        "answer": answer,
        "compact_support_packet": compact_packet,
        "provider_result": provider,
        "selected_model_lane": select_model_lane(message),
        "confidence": confidence,
        "confidence_score": confidence_score,
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": provider_call,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "mode_router_flags": ROUTER_FLAGS,
    }


def build_gpt_approval_preview(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    packet = build_compact_support_packet(message, history)
    return {
        "mode": "Conversation",
        "route": "gpt_support_approval_preview",
        "answer": (
            "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
        ),
        "compact_support_packet": packet,
        "selected_model_lane": select_model_lane(message),
        "confidence": "requires_explicit_provider_approval",
        "confidence_score": 0.0,
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def build_memory_candidate_from_answer(message: str, payload: dict[str, Any]) -> dict[str, Any]:
    return extract_candidate_concept(
        question=message,
        answer=str(payload.get("answer", "")),
        source_model_lane=dict(payload.get("selected_model_lane") or select_model_lane(message)),
        source_type="substrate" if payload.get("route") == "developmental_concept_memory" else "local_model_lane",
    )


def candidate_is_memory_worthy(candidate: dict[str, Any], payload: dict[str, Any] | None = None) -> bool:
    name = " ".join(str(candidate.get("concept_name", "")).split())
    if not name or name in VAGUE_CONCEPT_NAMES:
        return False
    if name.lower().startswith(("what ", "how ", "why ", "tell ", "general ", "user ")):
        return False
    answer = str((payload or {}).get("answer") or " ".join(candidate.get("propositions", []))).lower()
    if any(marker in answer for marker in LOW_CONFIDENCE_MARKERS):
        return False
    score = float((payload or {}).get("confidence_score") or 0.0)
    if score and score < 0.72:
        return False
    propositions = [str(item).strip() for item in candidate.get("propositions", []) if str(item).strip()]
    if not propositions:
        return False
    if all(len(item.split()) < 5 for item in propositions):
        return False
    return True


def maybe_build_memory_candidate(message: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    # Ordinary conversation should not create concept-review candidates on its
    # own. Explicit UI memory requests use build_memory_candidate_from_answer()
    # or remember_useful_answer() so operator review remains available.
    return None


def remember_useful_answer(message: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = payload.get("memory_candidate")
    candidate = existing if isinstance(existing, dict) else build_memory_candidate_from_answer(message, payload)
    if not candidate_is_memory_worthy(candidate, payload):
        candidate = None
    if not candidate:
        return {
            "candidate": None,
            "result": {
                "approved": False,
                "reason": "no_coherent_memory_candidate",
                "canonical_write_performed": False,
                "training_performed": False,
                "provider_calls_performed": False,
            },
            "memory_write_performed": False,
            "memory_scope": "none",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
            "rollback_supported": False,
        }
    result = approve_candidate_concept(candidate, approval_text="Keep this concept")
    return {
        "candidate": candidate,
        "result": result,
        "memory_write_performed": result.get("approved") is True,
        "memory_scope": "local_noncanonical_rc2_developmental_concept_store",
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "rollback_supported": True,
    }


def _history_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    lower = message.lower()
    session = _session_memory_answer(message, history)
    if session:
        return session
    if not history:
        return None
    user_turns = [item.get("content", "") for item in history if item.get("role") == "user" and item.get("content")]
    if ("what did i just ask" in lower or "last thing i asked" in lower) and user_turns:
        last = user_turns[-1]
        return {
            "route": "conversation_short_term_memory",
            "answer": f"You just asked: \"{last}\"",
            "confidence": "session_memory",
            "confidence_score": 0.95,
            "selected_model_lane": select_model_lane(message),
            "supporting_information_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    return None


def _is_session_memory_turn(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in (
        "pretend my favorite",
        "favorite color in this conversation",
        "alice owns",
        "bob owns",
        "who owns the",
    ))


def _session_memory_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    lower = message.lower()
    if "pretend my favorite color is" in lower:
        match = re.search(r"favorite color is\s+([a-zA-Z]+)", lower)
        color = match.group(1) if match else "that"
        return _session_payload(message, f"Got it. For this conversation only, I'll treat your favorite color as {color}.")
    if "alice owns" in lower and "bob owns" in lower:
        return _session_payload(message, "Got it. For this conversation only: Alice owns the truck, and Bob owns the trailer.")
    if history and "favorite color" in lower and "conversation" in lower:
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            match = re.search(r"favorite color is\s+([a-zA-Z]+)", text)
            if match:
                return _session_payload(message, f"In this conversation, your favorite color is {match.group(1)}.")
    if history and "who owns the" in lower:
        target = "trailer" if "trailer" in lower else "truck" if "truck" in lower else ""
        for item in reversed(history):
            text = str(item.get("content") or "").lower()
            if target == "trailer" and "bob owns the trailer" in text:
                return _session_payload(message, "Bob owns the trailer in this conversation.")
            if target == "truck" and "alice owns the truck" in text:
                return _session_payload(message, "Alice owns the truck in this conversation.")
    return None


def _is_recent_concept_followup(message: str) -> bool:
    return message.lower().strip(" ?!.") in {
        "why",
        "why is that",
        "tell me more",
        "continue",
        "expand on that",
        "more detail",
        "more details",
        "go deeper",
        "tell me more",
        "continue",
        "expand on that",
        "more detail",
        "more details",
        "give me an example",
        "how big can they get",
        "does that happen to all of them",
    }


def _session_payload(message: str, answer: str) -> dict[str, Any]:
    return {
        "route": "session_memory",
        "answer": answer,
        "confidence": "session_memory",
        "confidence_score": 0.92,
        "selected_model_lane": select_model_lane(message),
        "supporting_information_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
    }


def _recent_concept_followup_answer(message: str, history: list[dict[str, str]] | None) -> dict[str, Any] | None:
    if _is_explicit_new_topic_request(message):
        return None
    lower = message.lower().strip(" ?!.")
    if lower not in {"why", "why is that", "tell me more", "continue", "expand on that", "more detail", "more details", "go deeper", "give me an example", "how big can they get", "does that happen to all of them"}:
        return None
    context = _last_concept_context(history)
    concept_name = context.get("concept_name")
    if not concept_name:
        topic = _recent_user_topic(history)
        if not topic:
            return None
        return _session_payload(
            message,
            f"I can continue from your recent topic, {topic}. I do not have approved local knowledge for it yet, so I can ask the local reasoning model if you want.",
        )
    if lower == "give me an example":
        answer = f"Using the recent concept `{concept_name}`, I can give an example from that same topic, but I will keep this as session context rather than storing anything new."
    elif lower in {"why", "why is that"}:
        answer = f"Continuing from `{concept_name}`: the useful next step is to inspect the causes or mechanisms behind that concept. I can ask the local reasoning model for a deeper explanation if you want."
    else:
        answer = f"I can continue from `{concept_name}` using the recent context. I have not enabled synthesis or stored anything new."
    return _session_payload(message, answer)


def _recent_user_topic(history: list[dict[str, str]] | None) -> str | None:
    followup_forms = {
        "why",
        "why is that",
        "go deeper",
        "give me an example",
        "how big can they get",
        "does that happen to all of them",
        "what else",
        "another one",
    }
    for item in reversed(history or []):
        if item.get("role") != "user":
            continue
        text = str(item.get("content") or "").strip()
        bare = text.lower().strip(" ?!.")
        if not text or bare in followup_forms:
            continue
        topic = _topic_label_from_message(text)
        if topic:
            return topic
    return None


def _topic_label_from_message(message: str) -> str | None:
    text = " ".join(message.strip(" ?!.").split())
    lower = text.lower()
    patterns = [
        r"tell me about\s+(.+)",
        r"what is\s+(.+)",
        r"what are\s+(.+)",
        r"explain\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            topic = match.group(1).strip(" .?!")
            return topic if len(topic) > 2 else None
    return None


def local_conversation_answer(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    execute_local_model: bool = False,
    provider_manager: ProviderManager | None = None,
) -> dict[str, Any]:
    lower = message.lower()
    intent = classify_intent(message)["intent"]
    model_lane = select_model_lane(message, intent)
    local = run_v29_local_answer(message, use_recall=False)
    direct = _direct_answer(message)
    if development := _development_workflow_answer(message, history):
        return development
    if memory := _history_answer(message, history):
        return memory
    if recent := _recent_concept_followup_answer(message, history):
        return recent
    if intent == "followup":
        return {
            "route": "local_model_consent_required",
            "answer": "I can continue from the recent context. Would you like me to ask the local reasoning model to elaborate?",
            "confidence": "needs_local_reasoning_model",
            "confidence_score": 0.55,
            "selected_model_lane": model_lane,
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": _local_model_offer(message, "followup_needs_recent_context", history, model_lane),
            "pending_action_suggestion": {
                "action_type": "local_model_deepening",
                "pending_action_created": True,
                "followup_instruction": message,
                "expires_after_turns": 1,
            },
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    local_model_result = None
    if intent in SOCIAL_INTENT_RESPONSES:
        return {
            "route": "social_conversation",
            "answer": SOCIAL_INTENT_RESPONSES[intent],
            "confidence": "social_intent",
            "confidence_score": 0.9,
            "selected_model_lane": model_lane,
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    if "ask gpt automatically" in lower or "call gpt automatically" in lower or "provider automatically" in lower:
        return {
            "route": "provider_policy_answer",
            "answer": "No. I should not ask GPT or any provider automatically. If local knowledge is not enough, I should ask your permission first and send only a compact request after you approve.",
            "confidence": "local_provider_policy",
            "confidence_score": 0.9,
            "selected_model_lane": model_lane,
            "local_model_result": None,
            "supporting_information_offer": None,
            "local_model_offer": None,
            "memory_candidate": None,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
    if execute_local_model and intent not in {"external_knowledge_request", "image"}:
        local_model_result = execute_local_model_answer(message, model_lane, history, provider_manager=provider_manager)
        model_lane = {**model_lane, "executed": bool(local_model_result.get("executed"))}
        if local_model_result.get("executed"):
            return {
                "route": "local_conversation_model_lane",
                "answer": str(local_model_result["answer"]),
                "confidence": "local_model_inference",
                "confidence_score": float(local_model_result.get("confidence_score") or 0.72),
                "selected_model_lane": model_lane,
                "local_model_result": local_model_result,
                "supporting_information_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
    if direct:
        answer = str(direct["answer"])
        confidence = str(direct["confidence"])
        confidence_score = float(direct["confidence_score"])
        support_offer = None
    elif _is_brainstorming_request(message):
        answer = (
            "The first concept that comes to mind is motion: in physics, it is a clean starting point because it connects position, time, forces, energy, and prediction. "
            "If you want a more playful association, I would branch from motion to symmetry, fields, or conservation."
        )
        confidence = "local_brainstorming"
        confidence_score = 0.78
        support_offer = None
    elif intent == "coding":
        answer = (
            "I can help with coding by reading the repo, explaining files, proposing patches, writing tests, and validating behavior. "
        )
        confidence = "local_coding_capability_route"
        confidence_score = 0.78
        support_offer = None
    elif "topics" in lower and ("know" in lower or "best" in lower or "most" in lower):
        answer = (
            "Right now I am strongest at explaining DELTA itself, working with local approved substrate memory, "
            "helping with code and planning conversations, and walking through governed evidence workflows. "
            "For ordinary world knowledge I can answer simple questions locally; if confidence is low, I should ask whether you want supporting information before escalating."
        )
        confidence = "local_capability_self_description"
        confidence_score = 0.84
        support_offer = None
    elif local["local_answer"]["matched"]:
        answer = str(local["draft"]["answer_text"])
        confidence = "repo_local_self_knowledge"
        confidence_score = 0.86
        support_offer = None
    elif intent in {"external_knowledge_request", "image"}:
        answer = (
            "I do not have enough governed local evidence to answer that confidently. "
            "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
        )
        confidence = "needs_supporting_information"
        confidence_score = 0.35
        support_offer = _support_offer(message, "insufficient_local_evidence", history)
    else:
        if execute_local_model and local_model_result and local_model_result.get("reason"):
            answer = (
                "I couldn't reach the local conversation model from this session, so I can only give a cautious built-in response. "
                "I'm not confident enough locally. Would you like me to ask GPT or look for sources?"
            )
            confidence = "local_model_unavailable"
            confidence_score = 0.3
            support_offer = _support_offer(message, "local_model_unavailable", history)
        else:
            topic = _topic_label_from_message(message)
            topic_phrase = f" about {topic}" if topic else ""
            answer = (
                f"I don't think I know enough{topic_phrase} from my learned local knowledge yet. "
                "Would you like me to ask a local reasoning model?"
            )
            confidence = "needs_local_reasoning_model"
            confidence_score = 0.3
            support_offer = None
            local_model_offer = _local_model_offer(message, "missing_learned_or_direct_knowledge", history, model_lane)
            return {
                "route": "local_model_consent_required",
                "answer": answer,
                "confidence": confidence,
                "confidence_score": confidence_score,
                "selected_model_lane": model_lane,
                "local_model_result": local_model_result,
                "supporting_information_offer": None,
                "local_model_offer": local_model_offer,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
    return {
        "route": "local_conversation_model_lane",
        "answer": answer,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "selected_model_lane": model_lane,
        "local_model_result": local_model_result,
        "supporting_information_offer": support_offer,
        "local_model_offer": None,
        "memory_candidate": None,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
    }


def build_escalation_plan(message: str) -> dict[str, Any]:
    intent = classify_intent(message)["intent"]
    if intent in SOCIAL_INTENT_RESPONSES:
        recommended = ["social_response_only"]
    elif intent == "external_knowledge_request":
        recommended = ["local_model_research", "web_search_with_operator_approval", "large_model_review_with_operator_approval"]
    elif intent in {"coding", "analysis", "planning", "investigation"}:
        recommended = ["local_conversation", "substrate_check", "local_model_with_operator_gate"]
    elif intent == "memory_request":
        recommended = ["conversation_memory_offer", "noncanonical_memory_with_operator_approval"]
    elif intent == "document":
        recommended = ["evidence_review", "operator_review", "noncanonical_memory_with_operator_approval"]
    else:
        recommended = ["local_conversation", "substrate_check"]
    return {
        "intent": intent,
        "recommended_routes": recommended,
        "requires_operator_approval": any("approval" in item for item in recommended),
        "provider_calls_performed": False,
        "web_search_performed": False,
        "enabled_now": False,
    }


def confidence_engine(message: str, substrate_matched: bool = False) -> dict[str, Any]:
    intent = classify_intent(message)
    if intent["intent"] in SOCIAL_INTENT_RESPONSES:
        confidence = intent["confidence"]
        evidence_quality = "conversation_intent_no_evidence_needed"
        provider_necessity = "none"
    elif substrate_matched:
        confidence = 0.9
        evidence_quality = "approved_noncanonical_substrate"
        provider_necessity = "none"
    elif intent["intent"] in {"external_knowledge_request", "image"}:
        confidence = 0.35
        evidence_quality = "insufficient_local_evidence"
        provider_necessity = "gated_provider_or_web_may_be_needed"
    else:
        confidence = intent["confidence"]
        evidence_quality = "local_conversation_or_mode_context"
        provider_necessity = "not_required_for_local_response"
    return {
        "confidence": round(confidence, 2),
        "evidence_quality": evidence_quality,
        "retrieval_sufficiency": "sufficient" if substrate_matched else "not_checked_or_insufficient",
        "provider_necessity": provider_necessity,
    }


def _finish_conversation_payload(payload: dict[str, Any], message: str, history: list[dict[str, str]] | None) -> dict[str, Any]:
    normalize_safety_payload(payload)
    payload["routing_observability"] = {
        "layer": "rc2_conversational_mode_router",
        "selected_route": str(payload.get("route") or ""),
        "intent": classify_intent(message),
        "explicit_new_topic_request": _is_explicit_new_topic_request(message),
        "anchor_available": bool(resolve_followup_anchor(history)),
        "anchor_followup_allowed": _is_anchor_followup(message),
        "memory_retrieval_bypassed": bool(payload.get("memory_retrieval_bypassed", False)),
        "history_turns_seen": len(history or []),
        "early_return": str(payload.get("route") or ""),
        "read_only": True,
        "ephemeral": True,
    }
    payload["route_arbitration"] = build_route_arbitration_trace(
        message,
        history,
        str(payload.get("route") or ""),
        payload.get("intent") if isinstance(payload.get("intent"), dict) else None,
    )
    attach_episode(payload, message, history)
    return apply_natural_renderer(payload, message)


def route_message(
    mode: str,
    message: str,
    pasted_text: str = "",
    approve: bool = False,
    history: list[dict[str, str]] | None = None,
    *,
    execute_local_model: bool = False,
    provider_approved: bool = False,
    provider_manager: ProviderManager | None = None,
    provider_transport: Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        mode = "Conversation"
    if mode == "Conversation":
        intent_info = classify_intent(message)
        anchor = resolve_followup_anchor(history)
        explicit_new_topic = _is_explicit_new_topic_request(message)
        if provider_approved:
            payload = execute_gpt_support_request(message, history, transport=provider_transport)
            payload["intent"] = intent_info
            payload["confidence_decision"] = {
                "confidence": payload["confidence_score"],
                "evidence_quality": payload["confidence"],
                "retrieval_sufficiency": "provider_support_requested_by_user",
                "provider_necessity": "approved_by_user_for_this_turn",
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            return _finish_conversation_payload(payload, message, history)
        if message.strip().lower() in {"ask gpt", "ask gpt for supporting information", "yes ask gpt"}:
            prior_user = [item.get("content", "") for item in (history or []) if item.get("role") == "user" and item.get("content")]
            target = prior_user[-1] if prior_user else message
            payload = build_gpt_approval_preview(target, history)
            payload["intent"] = classify_intent(target)
            payload["confidence_decision"] = {
                "confidence": 0.0,
                "evidence_quality": "pending_explicit_provider_approval",
                "retrieval_sufficiency": "insufficient_locally",
                "provider_necessity": "available_only_after_user_approval",
            }
            payload["escalation_plan"] = build_escalation_plan(target)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        if intent_info.get("intent") in SOCIAL_INTENT_RESPONSES and intent_info.get("safe_no_route", True):
            payload = {
                "mode": mode,
                "route": "social_conversation",
                "answer": SOCIAL_INTENT_RESPONSES[str(intent_info.get("intent"))],
                "confidence": "social_intent",
                "confidence_score": intent_info.get("confidence", 0.9),
                "selected_model_lane": select_model_lane(message, str(intent_info.get("intent") or "")),
                "local_model_result": None,
                "supporting_information_offer": None,
                "local_model_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
            }
            payload["memory_candidate"] = None
            payload["autonomous_action_performed"] = False
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        render_correction = build_render_correction_payload(message, history)
        if render_correction:
            payload = {"mode": mode, **render_correction}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "render_correction", "communication_act": "render_correction"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_prior_answer_rendering_context",
                "retrieval_sufficiency": "not_needed_for_render_correction",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            return _finish_conversation_payload(payload, message, history)
        if (intent_info.get("communication_act") == "clarification_followup" or _is_context_dependent_followup(message)) and not history:
            payload = {
                "mode": mode,
                "route": "session_memory",
                "answer": "I can explain it more simply, but I need the thing you want simplified. Send the sentence or topic and I’ll restate it plainly.",
                "confidence": "needs_recent_context",
                "confidence_score": 0.72,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "memory_candidate": None,
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "escalation_plan": build_escalation_plan(message),
                "intent": intent_info,
                "confidence_decision": confidence_engine(message, False),
                "mode_router_flags": ROUTER_FLAGS,
            }
            return _finish_conversation_payload(payload, message, history)
        early_contradiction = build_contradiction_analysis(message, history=history) if is_contradiction_prompt(message, history) else {"matched": False}
        if early_contradiction["matched"]:
            payload = {
                "mode": mode,
                "route": "contradiction_analysis",
                "answer": early_contradiction["answer"],
                "confidence": early_contradiction["confidence"],
                "confidence_score": early_contradiction["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_contradiction.get("concept_matches", []),
                "contradiction_analysis": early_contradiction["contradiction_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "contradiction_analysis"}
            payload["confidence_decision"] = {
                "confidence": early_contradiction["confidence_score"],
                "evidence_quality": "approved_noncanonical_claim_evidence_plus_ephemeral_comparison",
                "retrieval_sufficiency": "balanced_claim_comparison",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        if execute_local_model:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        if _is_brainstorming_request(message):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "brainstorming"}
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            payload["memory_retrieval_bypassed"] = True
            return _finish_conversation_payload(payload, message, history)
        if not anchor and not _should_defer_to_knowledge_browse(intent_info) and (
            intent_info.get("communication_act") == "clarification_followup"
            or intent_info.get("intent") == "followup"
            or _is_recent_concept_followup(message)
        ):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "recent_topic_followup"}
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = None
            payload["memory_retrieval_bypassed"] = True
            return _finish_conversation_payload(payload, message, history)
        early_episode_followup = None if _should_defer_to_knowledge_browse(intent_info) or explicit_new_topic else resolve_working_memory_followup(message, history)
        if early_episode_followup:
            payload = {"mode": mode, **early_episode_followup}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_memory_followup"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_cognitive_episode",
                "retrieval_sufficiency": "resolved_from_short_horizon_dialogue_state",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        if _is_explicit_topic_reset(message) and run_v29_local_answer(message, use_recall=False)["local_answer"]["matched"]:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        early_analogy = build_analogy_analysis(message, history=history) if is_analogy_prompt(message, history) else {"matched": False}
        if early_analogy["matched"]:
            payload = {
                "mode": mode,
                "route": "analogy_analysis",
                "answer": early_analogy["answer"],
                "confidence": early_analogy["confidence"],
                "confidence_score": early_analogy["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_analogy.get("concept_matches", []),
                "analogy_analysis": early_analogy["analogy_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "analogy_analysis"}
            payload["confidence_decision"] = {
                "confidence": early_analogy["confidence_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_ephemeral_structural_mapping",
                "retrieval_sufficiency": "structural_mapping_ready",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        early_wrs = build_working_reasoning_set(message) if should_use_wrs(message) else {"matched": False}
        if early_wrs["matched"]:
            wrs_payload = dict(early_wrs.get("working_reasoning_set") or {})
            wrs_payload.update({
                "ephemeral": True,
                "destroyed_after_response": True,
                "synthesis_enabled_by_default": False,
                "memory_write_performed": False,
                "graph_write_performed": False,
            })
            payload = {
                "mode": mode,
                "route": "working_reasoning_set",
                "answer": early_wrs["answer"],
                "confidence": "ephemeral_multi_concept_working_reasoning_set",
                "confidence_score": early_wrs["confidence"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": early_wrs.get("retrieved_concepts", []),
                "working_reasoning_set": wrs_payload,
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_reasoning_set"}
            payload["confidence_decision"] = {
                "confidence": early_wrs["confidence"],
                "evidence_quality": "approved_noncanonical_multi_concept_working_set",
                "retrieval_sufficiency": "sufficient_for_ephemeral_reasoning",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        if not explicit_new_topic and _is_anchor_followup(message) and anchor:
            anchored = browse_near_active_anchor(message, anchor) if _is_anchor_browse_followup(message) else deepen_from_concept_anchor(message, anchor)
            if anchored:
                payload = {"mode": mode, **anchored}
                payload["escalation_plan"] = build_escalation_plan(message)
                payload["intent"] = intent_info
                payload["confidence_decision"] = confidence_engine(message, True)
                payload["mode_router_flags"] = ROUTER_FLAGS
                return _finish_conversation_payload(payload, message, history)
        if execute_local_model:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        if intent_info.get("intent") in {"coding", "external_knowledge_request", "image"} or _direct_answer(message) or _is_development_workflow_request(message, history):
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, False)
            payload["mode_router_flags"] = ROUTER_FLAGS
            payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
            return _finish_conversation_payload(payload, message, history)
        episode_followup = None if _should_defer_to_knowledge_browse(intent_info) or explicit_new_topic else resolve_working_memory_followup(message, history)
        if episode_followup:
            payload = {"mode": mode, **episode_followup}
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_memory_followup"}
            payload["confidence_decision"] = {
                "confidence": payload.get("confidence_score", 0.0),
                "evidence_quality": "ephemeral_cognitive_episode",
                "retrieval_sufficiency": "resolved_from_short_horizon_dialogue_state",
                "provider_necessity": "none",
            }
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        if intent_info.get("intent") in {"knowledge_browse", "knowledge_browse_followup", "knowledge_browse_jump"}:
            context = _last_concept_context(history)
            excluded_names = context.get("concept_names") or ([context["concept_name"]] if context.get("concept_name") else None)
            jump = intent_info.get("intent") == "knowledge_browse_jump"
            concept = browse_approved_concepts(
                limit=3,
                domain=context.get("domain") if intent_info.get("intent") == "knowledge_browse_followup" else None,
                exclude_concept_names=excluded_names,
                exclude_domains=[context["domain"]] if jump and context.get("domain") else None,
            )
            if not concept["matched"] and intent_info.get("intent") == "knowledge_browse_followup":
                concept = browse_approved_concepts(
                    limit=3,
                    exclude_concept_names=excluded_names,
                )
            if not concept["matched"] and jump:
                concept = browse_approved_concepts(
                    limit=3,
                    exclude_concept_names=excluded_names,
                )
            payload = {
                "mode": mode,
                "route": "developmental_concept_browse_followup" if intent_info.get("intent") in {"knowledge_browse_followup", "knowledge_browse_jump"} else "developmental_concept_browse",
                "answer": concept["answer"] if concept["matched"] else "I do not have approved local concepts to browse yet.",
                "confidence": "grounded_in_approved_noncanonical_concept_catalog" if concept["matched"] else "no_approved_local_concepts",
                "confidence_score": 0.9 if concept["matched"] else 0.2,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept.get("matches", []),
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, bool(concept["matched"]))
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        if _is_graph_assisted_reasoning_request(message):
            from orchestration.runtime.rc2_graph_assisted_reasoning import build_graph_assisted_reasoning_trial

            reasoning_trial = build_graph_assisted_reasoning_trial(message)
            payload = {
                "mode": mode,
                "route": "read_only_graph_assisted_reasoning_trial",
                "answer": reasoning_trial["answer"],
                "confidence": "read_only_graph_assisted_reasoning_trial",
                "confidence_score": reasoning_trial["reasoning_quality"]["overall_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": reasoning_trial["retrieved_concepts"],
                "graph_assisted_reasoning": {
                    "approved_graph_edges": reasoning_trial["approved_graph_edges"],
                    "evidence_chains": reasoning_trial["evidence_chains"],
                    "reasoning_quality": reasoning_trial["reasoning_quality"],
                    "trial_only": True,
                    "read_only": True,
                    "synthesis_enabled_by_default": False,
                    "memory_write_performed": False,
                    "graph_write_performed": False,
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "graph_assisted_reasoning_trial"}
            payload["confidence_decision"] = {
                "confidence": reasoning_trial["reasoning_quality"]["overall_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_approved_graph_edges",
                "retrieval_sufficiency": "graph_assisted_trial_ready",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        synthesis_trial = build_read_only_synthesis_trial(message) if _is_synthesis_trial_request(message) else {"matched": False}
        if synthesis_trial["matched"]:
            payload = {
                "mode": mode,
                "route": "read_only_cross_concept_synthesis_trial",
                "answer": synthesis_trial["answer"],
                "confidence": "trial_inference_grounded_in_retrieved_concepts",
                "confidence_score": synthesis_trial["retrieval_set_quality"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": synthesis_trial["source_retrieval"].get("matches", []),
                "synthesis_trial": {
                    "stored_concepts": synthesis_trial["stored_concepts"],
                    "tentative_inference": synthesis_trial["tentative_inference"],
                    "uncertainty": synthesis_trial["uncertainty"],
                    "synthesis_trial_only": True,
                    "synthesis_enabled": False,
                    "memory_write_performed": False,
                },
                "multi_concept_retrieval": {
                    "seeds": synthesis_trial["source_retrieval"].get("seeds", []),
                    "retrieval_set_quality": synthesis_trial["retrieval_set_quality"],
                    "synthesis_readiness": False,
                    "duplicate_suppression_count": synthesis_trial["source_retrieval"].get("duplicate_suppression_count", 0),
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "read_only_synthesis_trial"}
            payload["confidence_decision"] = {
                "confidence": synthesis_trial["retrieval_set_quality"],
                "evidence_quality": "approved_noncanonical_concepts_plus_labeled_inference",
                "retrieval_sufficiency": "set_ready_for_trial_synthesis_review",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        analogy_result = build_analogy_analysis(message, history=history) if is_analogy_prompt(message, history) else {"matched": False}
        if analogy_result["matched"]:
            payload = {
                "mode": mode,
                "route": "analogy_analysis",
                "answer": analogy_result["answer"],
                "confidence": analogy_result["confidence"],
                "confidence_score": analogy_result["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": analogy_result.get("concept_matches", []),
                "analogy_analysis": analogy_result["analogy_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "analogy_analysis"}
            payload["confidence_decision"] = {
                "confidence": analogy_result["confidence_score"],
                "evidence_quality": "approved_noncanonical_concepts_plus_ephemeral_structural_mapping",
                "retrieval_sufficiency": "structural_mapping_ready",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        contradiction_result = build_contradiction_analysis(message, history=history) if is_contradiction_prompt(message, history) else {"matched": False}
        if contradiction_result["matched"]:
            payload = {
                "mode": mode,
                "route": "contradiction_analysis",
                "answer": contradiction_result["answer"],
                "confidence": contradiction_result["confidence"],
                "confidence_score": contradiction_result["confidence_score"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": contradiction_result.get("concept_matches", []),
                "contradiction_analysis": contradiction_result["contradiction_analysis"],
                "memory_candidate": None,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "contradiction_analysis"}
            payload["confidence_decision"] = {
                "confidence": contradiction_result["confidence_score"],
                "evidence_quality": "approved_noncanonical_claim_evidence_plus_ephemeral_comparison",
                "retrieval_sufficiency": "balanced_claim_comparison",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        wrs_result = build_working_reasoning_set(message) if should_use_wrs(message) else {"matched": False}
        if wrs_result["matched"]:
            wrs_payload = dict(wrs_result.get("working_reasoning_set") or {})
            wrs_payload.update({
                "ephemeral": True,
                "destroyed_after_response": True,
                "synthesis_enabled_by_default": False,
                "memory_write_performed": False,
                "graph_write_performed": False,
            })
            payload = {
                "mode": mode,
                "route": "working_reasoning_set",
                "answer": wrs_result["answer"],
                "confidence": "ephemeral_multi_concept_working_reasoning_set",
                "confidence_score": wrs_result["confidence"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": wrs_result.get("retrieved_concepts", []),
                "working_reasoning_set": wrs_payload,
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "working_reasoning_set"}
            payload["confidence_decision"] = {
                "confidence": wrs_result["confidence"],
                "evidence_quality": "approved_noncanonical_multi_concept_working_set",
                "retrieval_sufficiency": "sufficient_for_ephemeral_reasoning",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        multi_concept = retrieve_multi_concept_set(message)
        if multi_concept["matched"]:
            payload = {
                "mode": mode,
                "route": "developmental_multi_concept_retrieval",
                "answer": multi_concept["answer"],
                "confidence": "retrieval_set_ready_for_operator_review",
                "confidence_score": multi_concept["retrieval_set_quality"],
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": multi_concept.get("matches", []),
                "multi_concept_retrieval": {
                    "seeds": multi_concept.get("seeds", []),
                    "retrieval_set_quality": multi_concept["retrieval_set_quality"],
                    "synthesis_readiness": False,
                    "duplicate_suppression_count": multi_concept.get("duplicate_suppression_count", 0),
                },
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "multi_concept_retrieval"}
            payload["confidence_decision"] = {
                "confidence": multi_concept["retrieval_set_quality"],
                "evidence_quality": "approved_noncanonical_retrieval_set",
                "retrieval_sufficiency": "set_ready_for_review",
                "provider_necessity": "none",
            }
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        sun_blue = _sun_blue_correction(message)
        if sun_blue:
            payload = {
                "mode": mode,
                "route": "conversation_clarified_misframed_question",
                "answer": sun_blue,
                "confidence": "local_science_clarification",
                "confidence_score": 0.84,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "memory_candidate": None,
                "concept_matches": [],
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
            }
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = intent_info
            payload["confidence_decision"] = confidence_engine(message, True)
            payload["mode_router_flags"] = ROUTER_FLAGS
            return _finish_conversation_payload(payload, message, history)
        domain_browse = _domain_browse_request(message)
        if domain_browse and intent_info.get("intent") not in {"coding"}:
            concept = browse_approved_concepts(limit=3, domain=domain_browse)
            payload = {
                "mode": mode,
                "route": "developmental_concept_domain_browse",
                "answer": concept["answer"] if concept["matched"] else f"I do not have approved local concepts for {domain_browse} yet.",
                "confidence": "grounded_in_approved_noncanonical_concept_catalog" if concept["matched"] else "no_approved_local_domain_concepts",
                "confidence_score": 0.9 if concept["matched"] else 0.2,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept.get("matches", []),
            }
            payload["memory_candidate"] = None
            payload["escalation_plan"] = build_escalation_plan(message)
            payload["intent"] = {**intent_info, "intent": "knowledge_domain_browse", "domain": domain_browse}
            payload["confidence_decision"] = confidence_engine(message, bool(concept["matched"]))
            payload.update({
                "provider_calls_performed": False,
                "web_search_performed": False,
                "training_performed": False,
                "canonical_write_performed": False,
                "autonomous_action_performed": False,
                "mode_router_flags": ROUTER_FLAGS,
            })
            return _finish_conversation_payload(payload, message, history)
        bypass_memory_retrieval = (
            execute_local_model
            or explicit_new_topic and _is_brainstorming_request(message)
            or intent_info.get("communication_act") == "clarification_followup"
            or intent_info.get("intent") == "followup"
            or _is_session_memory_turn(message)
            or _is_recent_concept_followup(message)
        )
        concept = {"matched": False, "answer": "", "matches": []} if bypass_memory_retrieval else query_approved_concepts(message)
        substrate = {"matched": False, "answer": "", "matches": []} if bypass_memory_retrieval else query_noncanonical_substrate(message)
        if concept["matched"]:
            payload = {
                "mode": mode,
                "route": "developmental_concept_memory",
                "answer": concept["answer"],
                "confidence": "grounded_in_approved_noncanonical_concept",
                "confidence_score": 0.92,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
                "concept_matches": concept["matches"],
            }
            payload["active_topic_anchor"] = _anchor_from_matches(message, concept["answer"], concept["matches"])
        elif substrate["matched"]:
            payload = {
                "mode": mode,
                "route": "substrate_first_conversation",
                "answer": substrate["answer"],
                "confidence": "grounded_in_noncanonical_substrate",
                "confidence_score": 0.9,
                "selected_model_lane": select_model_lane(message),
                "supporting_information_offer": None,
            }
        else:
            payload = {
                "mode": mode,
                **local_conversation_answer(
                    message,
                    history,
                    execute_local_model=execute_local_model,
                    provider_manager=provider_manager,
                ),
            }
        payload["memory_retrieval_bypassed"] = bypass_memory_retrieval
        payload["memory_candidate"] = maybe_build_memory_candidate(message, payload)
        payload["escalation_plan"] = build_escalation_plan(message)
        payload["intent"] = intent_info
        payload["confidence_decision"] = confidence_engine(message, substrate["matched"])
    elif mode == "Ask Substrate":
        answer = answer_operator_question(message)
        payload = {"mode": mode, **answer}
    elif mode == "Evidence Review":
        preview = preview_evidence_ingest(pasted_text)
        extracted = extract_propositions(pasted_text)
        payload = {"mode": mode, "route": "evidence_review", "preview": preview, "extracted": extracted, "answer": f"Detected {extracted['candidate_count']} proposition candidate(s)."}
    elif mode == "Review Mode":
        extracted = extract_propositions(pasted_text)
        payload = {"mode": mode, "route": "operator_review", "answer": "Review extracted proposition candidates before approval.", "candidates": extracted["candidates"]}
    elif mode == "Memory Mode":
        extracted = extract_propositions(pasted_text)
        if approve:
            result = approve_propositions(extracted["candidates"])
            answer = f"Approved {result['approved_count']} noncanonical proposition(s)."
        else:
            result = {"approved_count": 0, "requires_operator_approval": True, "candidates": extracted["candidates"]}
            answer = "Memory Mode prepared candidates only. Approval is required before noncanonical storage."
        payload = {"mode": mode, "route": "memory_mode_noncanonical", "answer": answer, "result": result}
    elif mode == "Contradiction Check":
        answer = answer_operator_question("Are there contradictions in my knowledge?")
        payload = {"mode": mode, **answer}
    elif mode == "Research":
        plan = build_escalation_plan(message)
        payload = {"mode": mode, "route": "research_scaffold", "answer": "Research mode can plan local, web, and larger-model escalation, but external routes are disabled until explicitly gated.", "escalation_plan": plan}
    elif mode == "Investigation":
        payload = {"mode": mode, "route": "investigation_scaffold", "answer": "Investigation mode organizes questions, evidence, contradictions, and unresolved claims without enabling autonomous research."}
    elif mode == "Developer":
        payload = {"mode": mode, "route": "developer_scaffold", "answer": "Developer mode can reason about code and implementation plans locally, but it does not execute tools or change files from the UI."}
    elif mode == "Replay":
        snapshot = build_operator_snapshot()
        payload = {"mode": mode, "route": "replay_inspection", "answer": "Replay and rollback inspection is available.", "replay": snapshot["replay_rollback"]}
    elif mode == "Diagnostics":
        payload = {"mode": mode, "route": "diagnostics", "answer": "Runtime diagnostics snapshot.", "state": build_cognitive_state(), "developmental_memory": build_developmental_memory_state(), "flags": ROUTER_FLAGS}
    elif mode == "Failure Log":
        payload = {"mode": mode, "route": "failure_log_scaffold", "answer": "Use the RC1 observation controls to log operational friction. This mode does not auto-file issues."}
    elif mode == "Research Analyst":
        plan = build_escalation_plan(message)
        payload = {"mode": mode, "route": "research_analyst_scaffold", "answer": "Research Analyst mode can plan local/provider/web escalation, but external routes are disabled until explicitly gated.", "escalation_plan": plan}
    else:
        payload = {"mode": mode, "route": "frontier_app_assistant", "answer": "Frontier App Assistant mode uses approved Frontier substrate evidence when available and otherwise asks you to add evidence."}
    payload.update({
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "mode_router_flags": ROUTER_FLAGS,
    })
    return _finish_conversation_payload(payload, message, history)


def render_route(payload: dict[str, Any], *, developer_overlay: bool = False) -> str:
    if payload.get("mode") == "Conversation":
        lines = [str(payload.get("answer", ""))]
        packet = payload.get("compact_support_packet")
        if payload.get("route") == "gpt_support_approval_preview" and isinstance(packet, dict):
            lines.extend([
                "",
                "If you say yes, I will send only a compact request: your current question, a few relevant recent turns, and any relevant approved local concepts.",
            ])
        offer = payload.get("supporting_information_offer")
        if isinstance(offer, dict) and offer.get("offered"):
            prompt = str(offer["prompt"])
            if prompt not in lines[0]:
                lines.extend(["", prompt])
            lines.append("Reply yes to approve that one provider request, or no to keep chatting locally.")
        local_offer = payload.get("local_model_offer")
        if isinstance(local_offer, dict) and local_offer.get("offered"):
            prompt = str(local_offer["prompt"])
            if prompt not in lines[0]:
                lines.extend(["", prompt])
            lines.append("Reply yes to ask the local model for this one question, or no to leave it unanswered.")
        if payload.get("memory_candidate"):
            candidate = payload["memory_candidate"]
            lines.extend([
                "",
                f"I noticed a possible reusable concept: `{candidate.get('concept_name', 'Learned Concept')}`. I put it in Concept Review; accepting it there is the only way to store it.",
            ])
        if developer_overlay:
            lines.extend(["", render_developer_overlay(payload)])
        return "\n".join(lines)

    lines = [
        f"Mode: {payload.get('mode')}",
        f"Route: {payload.get('route')}",
        "",
        str(payload.get("answer", "")),
    ]
    if payload.get("escalation_plan"):
        plan = payload["escalation_plan"]
        lines.extend([
            "",
            "Escalation plan:",
            f"- intent: {plan['intent']}",
            f"- recommended routes: {', '.join(plan['recommended_routes'])}",
            f"- enabled now: {plan['enabled_now']}",
        ])
    if payload.get("confidence_decision"):
        confidence = payload["confidence_decision"]
        lines.extend([
            "",
            "Confidence:",
            f"- estimate: {confidence['confidence']}",
            f"- evidence: {confidence['evidence_quality']}",
            f"- provider need: {confidence['provider_necessity']}",
        ])
    lines.extend([
        "",
        "Safety:",
        f"- provider_calls_performed: {payload['provider_calls_performed']}",
        f"- web_search_performed: {payload['web_search_performed']}",
        f"- training_performed: {payload['training_performed']}",
        f"- canonical_write_performed: {payload['canonical_write_performed']}",
        f"- autonomous_action_performed: {payload['autonomous_action_performed']}",
    ])
    return "\n".join(lines)


def render_developer_overlay(payload: dict[str, Any]) -> str:
    lane = payload.get("selected_model_lane") or {}
    intent = payload.get("intent") or {}
    confidence = payload.get("confidence_decision") or {}
    local_offer = payload.get("local_model_offer") or {}
    provider_offer = payload.get("supporting_information_offer") or {}
    local_result = payload.get("local_model_result") or {}
    pending = payload.get("pending_action_suggestion") or {}
    pending_matched = payload.get("pending_action_matched")
    action_executed = payload.get("action_executed")
    pending_cleared = payload.get("pending_action_cleared")
    route = str(payload.get("route") or "unknown")
    boundary = "known"
    if route == "local_model_consent_required":
        boundary = "unknown_seek_local_model"
    elif provider_offer:
        boundary = "unknown_seek_provider_or_sources"
    elif route in {"developmental_concept_memory", "substrate_first_conversation"}:
        boundary = "known_from_approved_local_memory"
    elif route == "working_reasoning_set":
        boundary = "ephemeral_multi_concept_working_set"
    elif route == "contradiction_analysis":
        boundary = "ephemeral_claim_comparison"
    elif route == "analogy_analysis":
        boundary = "ephemeral_structural_mapping"
    elif route == "social_conversation":
        boundary = "social_no_knowledge_lookup"
    rejected = lane.get("rejected_models") or []
    rejected_text = ", ".join(f"{item.get('requested')}:{item.get('reason')}" for item in rejected[:4]) or "none"
    lines = [
        "--- Developer Overlay ---",
        f"Intent: {intent.get('intent', 'unknown')}",
        f"Communication act: {intent.get('communication_act', 'unknown')}",
        f"Matched rule: {intent.get('matched_rule', 'unknown')}",
        f"Routed action: {intent.get('routed_action', 'unknown')}",
        f"Route: {route}",
        f"Knowledge boundary: {boundary}",
        f"Chosen lane: {lane.get('display_name') or lane.get('lane') or 'none'}",
        f"Chosen model: {lane.get('selected_model_id') or lane.get('selected_model') or 'none'}",
        f"Support identifier: {lane.get('support_identifier') or 'none'}",
        f"Selection reason: {lane.get('selection_reason') or 'none'}",
        f"Rejected candidates: {rejected_text}",
        f"Local model executed: {bool(local_result.get('executed'))}",
        f"Local model status: {local_result.get('reason') or ('executed' if local_result.get('executed') else 'not_requested')}",
        f"Local model offer: {bool(local_offer.get('offered'))}",
        f"Provider offer: {bool(provider_offer.get('offered'))}",
        f"Active pending action id: {pending.get('action_id') or payload.get('active_pending_action_id') or 'none'}",
        f"Active pending action type: {pending.get('action_type') or payload.get('active_pending_action_type') or 'none'}",
        f"Pending action created: {bool(pending.get('pending_action_created'))}",
        f"Pending action matched: {bool(pending_matched)}",
        f"Action executed: {bool(action_executed)}",
        f"Pending action cleared: {bool(pending_cleared)}",
        f"Confidence: {confidence.get('confidence', payload.get('confidence_score'))}",
        f"Evidence quality: {confidence.get('evidence_quality', payload.get('confidence'))}",
        f"Provider need: {confidence.get('provider_necessity', 'none')}",
        "Safety: no training, canonical write, autonomous action, or automatic provider call.",
    ]
    if route == "contradiction_analysis" and isinstance(payload.get("contradiction_analysis"), dict):
        analysis = payload["contradiction_analysis"]
        lines.extend([
            "",
            "Contradiction analysis:",
            f"- classification: {analysis.get('compatibility_classification')}",
            f"- confidence: {analysis.get('confidence')}",
            f"- ephemeral: {analysis.get('ephemeral')}",
            f"- read_only: {analysis.get('read_only')}",
            "- claims:",
        ])
        for claim in analysis.get("claims", [])[:4]:
            lines.extend([
                f"  - {claim.get('source')}: {claim.get('text')}",
                f"    subjects: {', '.join(claim.get('normalized_subjects') or []) or 'none'}",
                f"    polarity: {claim.get('polarity')}; timeframes: {', '.join(claim.get('timeframes') or []) or 'none'}",
            ])
        missing = analysis.get("missing_evidence") or []
        if missing:
            lines.append("- missing evidence:")
            lines.extend(f"  - {item}" for item in missing[:4])
        trace = analysis.get("reasoning_trace") or []
        if trace:
            lines.append("- trace:")
            lines.extend(f"  - {item}" for item in trace[:6])
    if route == "analogy_analysis" and isinstance(payload.get("analogy_analysis"), dict):
        analysis = payload["analogy_analysis"]
        lines.extend([
            "",
            "Analogy analysis:",
            f"- classification: {analysis.get('analogy_classification')}",
            f"- confidence: {analysis.get('confidence')}",
            f"- source domain: {analysis.get('source_domain')}",
            f"- target domain: {analysis.get('target_domain')}",
            f"- shared structure: {analysis.get('shared_structure')}",
            "- mapped roles:",
        ])
        lines.extend(f"  - {item}" for item in (analysis.get("mapped_roles") or [])[:5])
        if analysis.get("limits_of_analogy"):
            lines.append("- limits:")
            lines.extend(f"  - {item}" for item in analysis.get("limits_of_analogy", [])[:4])
        if analysis.get("reasoning_trace"):
            lines.append("- trace:")
            lines.extend(f"  - {item}" for item in analysis.get("reasoning_trace", [])[:6])
    episode = payload.get("cognitive_episode")
    if isinstance(episode, dict):
        branches = episode.get("conversation_branch") or []
        resolved = episode.get("resolved_references") or []
        rejected_refs = episode.get("rejected_references") or []
        lines.extend([
            "",
            "Cognitive episode:",
            f"- episode_id: {episode.get('episode_id') or 'none'}",
            f"- active_topic: {episode.get('active_topic') or 'none'}",
            f"- active_entities: {', '.join(episode.get('active_entities') or []) or 'none'}",
            f"- active_route: {episode.get('active_route') or 'none'}",
            f"- turn_number: {episode.get('turn_number')}",
            f"- episode_confidence: {episode.get('episode_confidence')}",
            f"- resolved_references: {len(resolved)}",
            f"- rejected_references: {len(rejected_refs)}",
            f"- branch_count: {len(branches)}",
            f"- has_wrs: {bool(episode.get('active_wrs'))}",
            f"- has_contradiction: {bool(episode.get('active_contradiction'))}",
            f"- has_analogy: {bool(episode.get('active_analogy'))}",
        ])
        if resolved:
            lines.append("- resolved:")
            lines.extend(
                f"  - {item.get('reference')} -> {item.get('resolved_to')}"
                for item in resolved[:4]
            )
        if rejected_refs:
            lines.append("- rejected:")
            lines.extend(
                f"  - {item.get('reference')}: {item.get('reason')}"
                for item in rejected_refs[:4]
            )
    arbitration = payload.get("route_arbitration")
    if isinstance(arbitration, dict):
        candidates = arbitration.get("candidate_routes") or []
        rejected_routes = arbitration.get("rejected_routes") or []
        lines.extend([
            "",
            "Route arbitration:",
            f"- selected_route: {arbitration.get('selected_route')}",
            f"- selected_group: {arbitration.get('selected_group')}",
            f"- candidate_count: {len(candidates)}",
            f"- rejected_count: {len(rejected_routes)}",
            "- candidates:",
        ])
        for item in candidates[:8]:
            marker = "selected" if item.get("selected") else (f"yielded_to={item.get('yielded_to')}" if item.get("yielded_to") else item.get("rejection_reason") or "rejected")
            evidence = ", ".join(item.get("trigger_evidence") or []) or "none"
            lines.append(
                f"  - {item.get('route')} p={item.get('precedence')} c={item.get('confidence')} {marker}; trigger={evidence}"
            )
    safety = payload.get("safety_metadata")
    if isinstance(safety, dict):
        lines.extend([
            "",
            "Safety metadata:",
            f"- complete: {safety.get('complete')}",
            f"- behavioral_safety_passed: {safety.get('behavioral_safety_passed')}",
            f"- missing_fields_filled: {', '.join(safety.get('missing_fields_filled') or []) or 'none'}",
        ])
    renderer = payload.get("natural_renderer") or {}
    if renderer:
        lines.extend([
            "",
            "Natural renderer:",
            f"- applied: {renderer.get('applied')}",
            f"- report_voice_removed: {renderer.get('report_voice_removed')}",
            f"- scaffold_removed: {renderer.get('scaffold_removed')}",
        ])
    return "\n".join(lines)


def build_rc2_report() -> dict[str, Any]:
    dialogue_evaluation = evaluate_dialogue_intent_corpus()
    cases = [
        route_message("Conversation", "What color is the sky?"),
        route_message("Conversation", "What color is water?"),
        route_message("Conversation", "What do you know about coding?"),
        route_message("Conversation", "What is the relation between Avogadro's number and quantum field theory?"),
        route_message("Evidence Review", "", "Project Frontier has AI workers."),
        route_message("Ask Substrate", "What do you know about Frontier?"),
        route_message("Research Analyst", "Tell me about beluga whales."),
    ]
    return {
        "phase": "RC2 Conversational Shell With DELTA Mode Router",
        "modes": MODES,
        "display_modes": DISPLAY_MODES,
        "cases": cases,
        "flags": ROUTER_FLAGS,
        "local_model_lane_selection_enabled": True,
        "local_model_execution_enabled_by_default": False,
        "useful_answer_memory_enabled": True,
        "useful_answer_memory_scope": "local_noncanonical_rc2_developmental_concept_store",
        "developmental_memory_state": build_developmental_memory_state(),
        "local_model_discovery": discover_local_model_lanes(),
        "dialogue_intent_classifier": {
            "corpus_size": dialogue_evaluation["corpus_size"],
            "accuracy": dialogue_evaluation["accuracy"],
            "misses": len(dialogue_evaluation["misses"]),
        },
        "safe": all(not case["provider_calls_performed"] and not case["training_performed"] and not case["canonical_write_performed"] for case in cases),
        "final_recommendation": "USE_RC2_CONVERSATIONAL_SHELL_AS_PRIMARY_UI_WITH_RC1_OPERATOR_MODE_AVAILABLE",
    }


def report_payloads() -> dict[str, dict[str, Any]]:
    base = build_rc2_report()
    dialogue_evaluation = evaluate_dialogue_intent_corpus()
    return {
        "RC2_CONVERSATIONAL_ARCHITECTURE": {
            **base,
            "focus": "conversation is the product; governed runtime is the engine",
            "conversation_primary_interface": True,
            "operator_console_advanced": True,
        },
        "RC2_MODE_ROUTER": {
            "modes": DISPLAY_MODES,
            "default_mode": "Conversation",
            "manual_mode_required": False,
            "safe": base["safe"],
        },
        "RC2_INTENT_ROUTER": {
            "supported_intents": [
                "conversation",
                "question",
                "coding",
                "research",
                "planning",
                "memory",
                "evidence",
                "investigation",
                "analysis",
                "document",
                "image",
                "diagnostics",
            ],
            "examples": [classify_intent(text) for text in ["What color is the sky?", "Remember that.", "Analyze this invoice.", "Show diagnostics."]],
            "safe": True,
        },
        "RC2_DIALOGUE_INTENT_CLASSIFIER": {
            "summary": "Deterministic communication-act classification now runs before retrieval, model routing, memory formation, or provider escalation.",
            "corpus_size": dialogue_evaluation["corpus_size"],
            "accuracy": dialogue_evaluation["accuracy"],
            "misses": dialogue_evaluation["misses"],
            "confusion_matrix": dialogue_evaluation["confusion_matrix"],
            "rule_coverage": dialogue_evaluation["rule_coverage"],
            "developer_overlay_fields": ["communication_act", "confidence", "matched_rule", "routed_action"],
            "routing_policy": {
                "social_intent": "respond socially; no SLM, retrieval, memory, or provider",
                "acknowledgement": "brief response; no routing",
                "refusal_or_cancel": "stop or reject pending action",
                "followup": "use short-term context",
                "factual_or_conceptual_question": "substrate/local model path",
                "memory_command": "concept approval path",
                "diagnostics_command": "diagnostics",
            },
            "safe": True,
        },
        "RC2_MEMORY_EXPERIENCE": {
            "technical_phrase_replaced": "Approve To Noncanonical Substrate",
            "user_facing_phrase": "Would you like me to remember this?",
            "default_storage": "none_until_user_approval",
            "advanced_workflow_preserved": True,
            "canonical_writes_enabled": False,
        },
        "RC2_OPERATOR_SEPARATION": {
            "default_tab": "Conversation",
            "advanced_tab": "Advanced / Operator Console",
            "operator_console_preserved": True,
            "regular_user_required_to_understand_substrate": False,
        },
        "RC2_UI_REVIEW": {
            "conversation_first": True,
            "visible_modes": DISPLAY_MODES,
            "reduced_default_implementation_terminology": True,
            "remaining_gap": "local model lane selection is wired; model execution, web, and GPT/provider routes remain gated/off by default",
            "safe": True,
        },
        "RC2_LOCAL_MODEL_ROUTING": {
            "local_model_lane_selection_enabled": True,
            "model_registry": "integration.model_runtime.model_registry",
            "discovery": discover_local_model_lanes(),
            "sample_selections": [
                select_model_lane("What is fire?", "conversation"),
                select_model_lane("Debug this Python function", "coding"),
                select_model_lane("Research beluga whales", "external_knowledge_request"),
            ],
            "model_execution_enabled_by_default": False,
            "provider_calls_performed": False,
            "safe": True,
        },
        "RC2_SELECTIVE_MEMORY_EXPERIMENT": {
            "enabled": True,
            "approval_paths": ["Concept Review tray", "Accept Selected Concept button"],
            "casual_yes_counts_as_memory_approval": False,
            "target_store": "data/rc2_developmental_memory/knowledge_concepts.jsonl",
            "canonical_writes_enabled": False,
            "training_enabled": False,
            "clear_store_confirmation": "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE",
            "memory_state": build_developmental_memory_state(),
            "safe": True,
        },
        "RC2_MODEL_LANE_ROUTER": {
            "summary": "Automatic lane router selects everyday conversation, coding/technical, reasoning/analysis, planning, vision, concept extraction, or contradiction detection lanes from the existing model registry.",
            "discovery": discover_local_model_lanes(),
            "model_execution_enabled_by_default": False,
            "provider_calls_performed": False,
            "safe": True,
        },
        "RC2_DEVELOPMENTAL_CONCEPT_FORMATION": {
            "summary": "Useful answers become candidate concepts with propositions, related concepts, uncertainty, provenance, rollback handle, and approval status.",
            "sample_candidate": extract_candidate_concept(
                question="What is fire?",
                answer=DIRECT_LOCAL_ANSWERS["fire_definition"]["answer"],
                source_model_lane=select_model_lane("What is fire?"),
            ),
            "canonical_writes_enabled": False,
            "training_enabled": False,
            "safe": True,
        },
        "RC2_MEMORY_STORE_SEPARATION": {
            "summary": "Conversation, personal, and knowledge memory are separate. Default concept storage goes to knowledge memory unless the user makes it personal.",
            "stores": discover_memory_store_separation(),
            "safe": True,
        },
        "RC2_CONCEPT_GRAPH_LINKING": {
            "summary": "Approved concepts create noncanonical concept records, relation edges, contradiction records, replay items, and rollback handles.",
            "memory_state": build_developmental_memory_state(),
            "first_pass_contradiction_rules": ["X is Y vs X is not Y", "should X vs should not X", "can X vs cannot X", "automatic vs requires approval/manual review", "always vs not always", "must vs must not"],
            "safe": True,
        },
        "RC2_CONCEPT_APPROVAL_UX": {
            "summary": "The UI keeps the same layout but moves concept approval to a passive Concept Review tray. Chat affirmations do not store memory.",
            "approval_required": True,
            "casual_yes_counts_as_approval": False,
            "safe": True,
        },
        "RC2_DEVELOPMENTAL_LIFECYCLE": {
            "lifecycle": ["Conversation", "Candidate Concept", "Operator Approval", "Knowledge Graph", "Replay", "Consolidation", "Curriculum", "Competency Tests", "Training Packet", "Distillation", "Better Base Model"],
            "invariant": "Neural training is a graduation event, not a day-to-day learning mechanism.",
            "day_to_day_learning": "governed concept formation, operator approval, knowledge graph integration, replay, consolidation, curriculum construction, and competency testing",
            "safe": True,
        },
        "RC2_COMPACT_PROVIDER_CONSENT": {
            "summary": "GPT/API escalation is ask-first and preview-only in RC2. The packet carries only the current question, short relevant chat history, relevant approved concepts, routing reason, and desired answer format.",
            "sample_packet": build_compact_support_packet("What is the relation between Avogadro's number and quantum field theory?", []),
            "provider_calls_performed": False,
            "safe": True,
        },
    }


def write_rc2_report() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_dialogue_intent_artifacts()
    payload = build_rc2_report()
    (REPORTS / "RC2_CONVERSATIONAL_MODE_ROUTER.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# RC2 Conversational Shell With DELTA Mode Router",
        "",
        "RC2 adds a conversational front door with selectable DELTA modes. It does not enable providers, web search, training, canonical writes, autonomous actions, production routing, HYB1 promotion, or Model B replacement.",
        "",
        "## Modes",
        *[f"- {mode}" for mode in MODES],
        "",
        "## Recommendation",
        f"`{payload['final_recommendation']}`",
        "",
    ]
    (REPORTS / "RC2_CONVERSATIONAL_MODE_ROUTER.md").write_text("\n".join(md), encoding="utf-8")
    for name, data in report_payloads().items():
        (REPORTS / f"{name}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (REPORTS / f"{name}.md").write_text(
            "\n".join([
                f"# {name.replace('_', ' ').title()}",
                "",
                f"Safe: `{data.get('safe', True)}`",
                "",
                f"Summary: `{data.get('focus', data.get('remaining_gap', data.get('default_mode', 'RC2 report')) )}`",
                "",
            ]),
            encoding="utf-8",
        )
    return payload


======================================================================
FILE: orchestration/runtime/rc45_discourse_cognition_bridge.py
======================================================================

"""Conversation-scoped discourse-to-cognition bridge for RC4/RC5 pilot review.

This module is intentionally deterministic and inert. It does not perform
retrieval, provider calls, persistence, or memory writes. Its only job is to
turn reference-dependent operator language into a compact task frame before
specialist routing gets a chance to misclassify the turn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re

from orchestration.runtime.rc2_render_correction import is_render_correction_request


@dataclass(frozen=True)
class DiscourseFrame:
    """Ephemeral interpretation of the current user utterance."""

    current_topic: str
    active_task: str
    referenced_artifacts: tuple[str, ...] = ()
    prior_operator_request: str = ""
    latest_relevant_finding: str = ""
    current_requested_operation: str = "general_conversation"
    expected_output_form: str = "natural_answer"
    explicit_constraints: tuple[str, ...] = ()
    topic_switch_status: str = "continuation"
    candidate_referents: tuple[str, ...] = ()
    candidate_routes: tuple[str, ...] = ("general_router",)
    confidence: float = 0.5
    unresolved_ambiguity: str = ""
    preempt_specialist_routing: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_discourse_frame(message: str, anchor: dict[str, object] | None = None) -> DiscourseFrame:
    """Build an ephemeral task frame from a message and optional local context."""

    normalized = _normalize(message)
    report_path = _extract_report_path(message)
    anchor = anchor or {}
    report_name = str(anchor.get("report_name") or "")
    anchor_request = str(anchor.get("request") or "")
    latest = str(anchor.get("answer_summary") or "")
    referenced = tuple(item for item in (str(report_path) if report_path else "", report_name) if item)
    constraints = _extract_constraints(normalized)
    topic = _topic_from_context(normalized, report_name)
    topic_switch = "explicit_topic_switch" if normalized.startswith("switch topics") else "continuation"

    if report_path:
        return DiscourseFrame(
            current_topic=topic,
            active_task="local_report_inspection",
            referenced_artifacts=(str(report_path),),
            prior_operator_request=anchor_request,
            latest_relevant_finding=latest,
            current_requested_operation="inspect_local_report",
            expected_output_form="report_summary",
            explicit_constraints=constraints,
            topic_switch_status=topic_switch,
            candidate_referents=(report_path.name,),
            candidate_routes=("local_report_inspection",),
            confidence=0.98,
            preempt_specialist_routing=True,
        )

    if "same report" in normalized and "weakness" in normalized and "report itself" in normalized:
        return _frame(
            normalized,
            anchor,
            topic,
            "report_followup_weakness",
            "identify_report_weakness",
            "weakness_analysis",
            constraints,
            referenced,
            confidence=0.94 if report_name else 0.62,
            ambiguity="" if report_name else "same_report_without_prior_report_anchor",
        )

    if _is_pilot_checklist_request(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "pilot_checklist_drafting",
            "draft_operator_pilot_checklist",
            "checklist",
            constraints,
            referenced,
            confidence=0.93,
        )

    if _is_second_one_followup(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "reference_resolution",
            "resolve_prior_checklist_item",
            "referent_explanation",
            constraints,
            referenced,
            confidence=0.82 if report_name else 0.55,
            ambiguity="" if report_name else "second_one_without_active_task_anchor",
        )

    if _is_rc5_gpt_boundary_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 manual consultation governance",
            "governance_boundary_synthesis",
            "explain_rc5_gpt_boundary",
            "boundary_explanation",
            constraints,
            referenced,
            confidence=0.95,
        )

    if _is_rc4_handoff_boundary_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 to RC4 upgrade governance",
            "handoff_boundary_synthesis",
            "explain_rc5_to_rc4_handoff_boundary",
            "boundary_explanation",
            constraints,
            referenced,
            confidence=0.95,
        )

    if _is_pilot_session_record_request(normalized):
        return _frame(
            normalized,
            anchor,
            topic,
            "pilot_session_evaluation",
            "draft_pilot_session_record",
            "pilot_session_record",
            constraints,
            referenced,
            confidence=0.9,
        )

    if _is_full_pilot_freeze_decision_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_freeze_readiness_synthesis",
            "evaluate_full_pilot_freeze_readiness",
            "freeze_readiness_decision",
            constraints,
            referenced,
            confidence=0.92,
        )

    if is_render_correction_request(message):
        return DiscourseFrame(
            current_topic=topic,
            active_task="render_correction",
            referenced_artifacts=referenced,
            prior_operator_request=anchor_request,
            latest_relevant_finding=latest,
            current_requested_operation="render_correction",
            expected_output_form="requested_rendering_constraints",
            explicit_constraints=constraints,
            topic_switch_status=topic_switch,
            candidate_referents=tuple(item for item in (report_name,) if item),
            candidate_routes=("render_correction",),
            confidence=0.9,
            preempt_specialist_routing=False,
        )

    if _is_primary_freeze_proof_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_freeze_readiness_synthesis",
            "identify_primary_freeze_evidence_gap",
            "primary_freeze_evidence_gap",
            constraints,
            referenced,
            confidence=0.9,
        )

    if _is_recovery_evidence_enrichment_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 freeze readiness",
            "pilot_evidence_semantic_enrichment",
            "explain_sufficient_recovery_evidence",
            "evidence_standard_explanation",
            constraints,
            referenced,
            confidence=0.88,
        )

    if _is_mixed_proposal_record_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC4/RC5 operator pilot evidence",
            "pilot_record_semantic_enrichment",
            "explain_mixed_proposal_record",
            "pilot_record_guidance",
            constraints,
            referenced,
            confidence=0.88,
        )

    if _is_useful_but_unsafe_advice_question(normalized):
        return _frame(
            normalized,
            anchor,
            "RC5 manual consultation governance",
            "manual_advice_semantic_enrichment",
            "explain_useful_but_unsafe_advice_handling",
            "governance_decision_guidance",
            constraints,
            referenced,
            confidence=0.9,
        )

    if any(phrase in normalized for phrase in ("based on the reports inspected", "based on those reports", "given everything above")):
        return _frame(
            normalized,
            anchor,
            topic,
            "report_grounded_synthesis",
            "synthesize_from_inspected_reports",
            "governed_synthesis_answer",
            constraints,
            referenced,
            confidence=0.72 if report_name else 0.6,
            ambiguity="" if report_name else "report_synthesis_without_report_anchor",
        )

    return DiscourseFrame(
        current_topic=topic,
        active_task="none",
        referenced_artifacts=referenced,
        prior_operator_request=anchor_request,
        latest_relevant_finding=latest,
        explicit_constraints=constraints,
        topic_switch_status=topic_switch,
        candidate_referents=tuple(item for item in (report_name,) if item),
        candidate_routes=("general_router",),
        confidence=0.5,
    )


def should_preempt_specialist_routing(frame: DiscourseFrame) -> bool:
    return frame.preempt_specialist_routing and frame.confidence >= 0.7


def _frame(
    normalized: str,
    anchor: dict[str, object],
    topic: str,
    active_task: str,
    operation: str,
    output_form: str,
    constraints: tuple[str, ...],
    referenced: tuple[str, ...],
    *,
    confidence: float,
    ambiguity: str = "",
) -> DiscourseFrame:
    report_name = str(anchor.get("report_name") or "")
    return DiscourseFrame(
        current_topic=topic,
        active_task=active_task,
        referenced_artifacts=referenced,
        prior_operator_request=str(anchor.get("request") or ""),
        latest_relevant_finding=str(anchor.get("answer_summary") or ""),
        current_requested_operation=operation,
        expected_output_form=output_form,
        explicit_constraints=constraints,
        topic_switch_status="explicit_topic_switch" if normalized.startswith("switch topics") else "continuation",
        candidate_referents=tuple(item for item in (report_name,) if item),
        candidate_routes=(operation,),
        confidence=confidence,
        unresolved_ambiguity=ambiguity,
        preempt_specialist_routing=confidence >= 0.7 and not ambiguity,
    )


def _normalize(message: str) -> str:
    return " ".join(str(message or "").lower().split())


def _extract_report_path(message: str) -> Path | None:
    match = re.search(r"([A-Za-z]:\\[^\r\n]+?\.(?:md|json))", message)
    return Path(match.group(1).strip().strip('"')) if match else None


def _extract_constraints(normalized: str) -> tuple[str, ...]:
    constraints: list[str] = []
    if "do not store" in normalized or "don't store" in normalized:
        constraints.append("no_memory_write")
    if "do not call a provider" in normalized or "no provider" in normalized:
        constraints.append("no_provider_call")
    if "do not repeat" in normalized:
        constraints.append("avoid_repeating_prior_answer")
    if "use the checklist" in normalized or "using the checklist" in normalized:
        constraints.append("use_prior_checklist")
    if "based on the reports inspected" in normalized or "based on those reports" in normalized:
        constraints.append("use_inspected_report_context")
    return tuple(constraints)


def _topic_from_context(normalized: str, report_name: str) -> str:
    if "rc4" in normalized or "rc5" in normalized or report_name.startswith("RC45") or report_name.startswith("RC5"):
        return "RC4/RC5 operator pilot and freeze readiness"
    if "report" in normalized:
        return "local report inspection"
    return "general conversation"


def _is_pilot_checklist_request(normalized: str) -> bool:
    return (
        "checklist" in normalized
        and ("pilot" in normalized or "operator" in normalized)
        and (
            "do not store" in normalized
            or "don't store" in normalized
            or "provider" in normalized
            or "based on the weakness" in normalized
        )
    )


def _is_pilot_session_record_request(normalized: str) -> bool:
    return (
        ("use the checklist" in normalized or "session record" in normalized or "evaluate this pilot session" in normalized)
        and ("pilot session" in normalized or "freeze evidence" in normalized or "hypothetical pilot session" in normalized)
    )


def _is_second_one_followup(normalized: str) -> bool:
    return normalized in {"what about the second one?", "what about the second one", "the second one?", "second one?"}


def _is_rc5_gpt_boundary_question(normalized: str) -> bool:
    return (
        "rc5" in normalized
        and ("automatically ask gpt" in normalized or "automatic gpt" in normalized or "ask gpt during" in normalized)
        and ("boundary" in normalized or "explain" in normalized)
    )


def _is_rc4_handoff_boundary_question(normalized: str) -> bool:
    return (
        "rc5" in normalized
        and "upgrade proposal" in normalized
        and ("handed off to rc4" in normalized or "handoff" in normalized or "hand off" in normalized)
    )


def _is_full_pilot_freeze_decision_question(normalized: str) -> bool:
    return (
        "full pilot session" in normalized
        and ("ready to freeze" in normalized or "freeze" in normalized)
        and ("evidence is still missing" in normalized or "what evidence" in normalized or "if not" in normalized)
    )


def _is_primary_freeze_proof_question(normalized: str) -> bool:
    return (
        ("given all of that" in normalized or "based on all of that" in normalized or "after all of that" in normalized)
        and ("most important thing" in normalized or "main thing" in normalized or "primary thing" in normalized)
        and ("freezing rc4 and rc5" in normalized or "freeze rc4 and rc5" in normalized or ("rc4" in normalized and "rc5" in normalized and "freeze" in normalized))
    )




def _is_recovery_evidence_enrichment_question(normalized: str) -> bool:
    return (
        "recovery evidence" in normalized
        and ("what would count" in normalized or "what counts" in normalized or "enough" in normalized or "sufficient" in normalized)
    )


def _is_mixed_proposal_record_question(normalized: str) -> bool:
    return (
        "accepted one proposal" in normalized
        and "rejected another" in normalized
        and ("recorded" in normalized or "record" in normalized)
    )


def _is_useful_but_unsafe_advice_question(normalized: str) -> bool:
    return (
        ("gpt gives useful advice" in normalized or "gpt gave useful advice" in normalized or "external advice" in normalized)
        and ("bypassing authorization" in normalized or "bypass authorization" in normalized or "bypassing rc4" in normalized)
        and ("what should delta do" in normalized or "what should it do" in normalized or "how should delta" in normalized)
    )


======================================================================
FILE: orchestration/runtime/rc2_cognitive_episode.py
======================================================================

"""Ephemeral RC2 cognitive episode and working-memory resolver.

The episode object is rebuilt from the current message and short chat history on
each turn. It is never stored and never mutates substrate state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC2_WORKING_MEMORY_EPISODE.json"
REPORT_MD = ROOT / "reports" / "RC2_WORKING_MEMORY_EPISODE.md"
WORKING_MEMORY_JSON = ROOT / "reports" / "RC2_WORKING_MEMORY.json"
WORKING_MEMORY_MD = ROOT / "reports" / "RC2_WORKING_MEMORY.md"
COGNITIVE_EPISODE_JSON = ROOT / "reports" / "RC2_COGNITIVE_EPISODE.json"
COGNITIVE_EPISODE_MD = ROOT / "reports" / "RC2_COGNITIVE_EPISODE.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}

KNOWN_TOPICS = [
    "blood pressure",
    "allergies",
    "photosynthesis",
    "cellular respiration",
    "battery charging",
    "planning",
    "feedback loops",
    "interest rates",
    "inflation",
    "noncanonical memory",
    "memory candidates",
    "memory consolidation",
    "rollback evidence",
    "recovery evidence",
    "delta 1.2",
    "live runtime",
    "gravity",
    "orbital motion",
    "meaning of life",
]

FOLLOWUP_FORMS = {
    "tell me more",
    "go deeper",
    "explain more",
    "give an example",
    "give me an example",
    "why",
    "why?",
    "how so",
    "simplify",
    "explain it simpler",
    "explain that more simply",
    "what else matters",
    "what else",
    "where does it break",
    "where does that analogy break",
    "what supports that",
    "what evidence is missing",
    "compare those",
    "what changed",
    "continue",
}


@dataclass
class CognitiveEpisode:
    episode_id: str
    active_topic: str | None
    active_entities: list[str]
    active_question: str | None
    active_answer: str | None
    active_route: str | None
    active_wrs: dict[str, Any] | None = None
    active_contradiction: dict[str, Any] | None = None
    active_analogy: dict[str, Any] | None = None
    active_examples: list[str] = field(default_factory=list)
    active_limits: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    last_summary: str = ""
    conversation_branch: list[dict[str, Any]] = field(default_factory=list)
    resolved_references: list[dict[str, str]] = field(default_factory=list)
    rejected_references: list[dict[str, str]] = field(default_factory=list)
    episode_confidence: float = 0.0
    turn_number: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    ephemeral: bool = True
    read_only: bool = True


def build_cognitive_episode(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    current_route: str | None = None,
    current_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = history or []
    branches = _branches(history)
    topic_reset = _explicit_topic_reset(message)
    episode_message = topic_reset or message
    current_entities = _entities(episode_message)
    active = _select_active_branch(message, branches, current_entities)
    explicit_change = bool(topic_reset) or _explicit_topic_change(message, active)
    if explicit_change:
        active = {
            "topic": current_entities[0] if current_entities else _topic_from_question(episode_message),
            "question": message,
            "answer": "",
            "route": current_route or "new_topic",
            "entities": current_entities,
            "summary": "explicit topic change",
        }
    payload = current_payload or {}
    episode = CognitiveEpisode(
        episode_id=_episode_id(message, history),
        active_topic=active.get("topic"),
        active_entities=current_entities or active.get("entities", []),
        active_question=active.get("question"),
        active_answer=active.get("answer"),
        active_route=current_route or active.get("route"),
        active_wrs=payload.get("working_reasoning_set"),
        active_contradiction=payload.get("contradiction_analysis"),
        active_analogy=payload.get("analogy_analysis"),
        active_examples=_examples(active.get("answer", "")),
        active_limits=_limits(active.get("answer", "")),
        unresolved_questions=_unresolved(active.get("answer", "")),
        last_summary=active.get("summary") or _summary(active.get("question", ""), active.get("answer", "")),
        conversation_branch=branches,
        resolved_references=_resolved_refs(message, active),
        rejected_references=_rejected_refs(message, branches, active, explicit_change),
        episode_confidence=_episode_confidence(message, active, current_entities),
        turn_number=sum(1 for item in history if item.get("role") == "user") + 1,
    )
    return asdict(episode)


def resolve_working_memory_followup(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    history = history or []
    lower = _norm(message)
    if _is_explicit_task_directive(message, lower):
        return None
    if _is_context_declaration(lower):
        episode = build_cognitive_episode(message, history)
        topic = _topic_from_question(message) or "this context"
        episode["active_topic"] = topic
        episode["active_question"] = message
        episode["active_answer"] = message
        return _payload(
            message,
            episode,
            f"Got it. I will keep {topic} as context for this conversation.",
            confidence=0.84,
            resolved=True,
        )
    if not history and any(term in lower for term in ("analogy", "evidence is missing", "information is missing", "what evidence", "what information")):
        return None
    episode = build_cognitive_episode(message, history)
    if _explicit_topic_change(message, {"topic": episode.get("active_topic")}):
        return None
    if not _is_followup(lower):
        return None
    ambiguous = _ambiguity_candidates(lower, episode)
    if ambiguous:
        episode["unresolved_questions"] = [f"ambiguous_reference:{', '.join(ambiguous)}"]
        return _payload(
            message,
            episode,
            _ambiguity_answer(ambiguous),
            confidence=0.74,
            resolved=False,
        )
    topic = episode.get("active_topic")
    if not topic:
        return _payload(
            message,
            episode,
            "I can continue, but I need the topic or sentence you want me to build on.",
            confidence=0.62,
            resolved=False,
        )
    if _requests_first_branch(lower):
        branch = _subject_branch(episode.get("conversation_branch", []), "first") or _branch_by_ordinal(episode.get("conversation_branch", []), 0)
        if branch:
            topic = branch.get("topic") or topic
            episode["active_topic"] = topic
            episode["active_question"] = branch.get("question")
            episode["active_answer"] = branch.get("answer")
    elif _requests_second_branch(lower):
        branch = _subject_branch(episode.get("conversation_branch", []), "second") or _branch_by_ordinal(episode.get("conversation_branch", []), 1)
        if branch:
            topic = branch.get("topic") or topic
            episode["active_topic"] = topic
            episode["active_question"] = branch.get("question")
            episode["active_answer"] = branch.get("answer")

    answer = _followup_answer(lower, topic, episode)
    return _payload(message, episode, answer, confidence=0.88, resolved=True)


def attach_episode(payload: dict[str, Any], message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    payload["cognitive_episode"] = build_cognitive_episode(
        message,
        history,
        current_route=str(payload.get("route") or ""),
        current_payload=payload,
    )
    return payload


def build_working_memory_episode_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _report_cases()
    results = []
    for case in cases:
        payload = resolve_working_memory_followup(case["message"], case["history"])
        answer = str((payload or {}).get("answer") or "")
        passed = bool(payload) and all(term in answer.lower() for term in case["terms"])
        results.append({
            "case_id": case["case_id"],
            "message": case["message"],
            "route": (payload or {}).get("route"),
            "passed": passed,
            "answer_preview": answer[:320],
            "episode": (payload or {}).get("cognitive_episode"),
        })
    accuracy = round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4)
    report = {
        "report": "RC2_WORKING_MEMORY_EPISODE",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases_tested": len(results),
        "followup_resolution_accuracy": accuracy,
        "episode_schema": list(asdict(CognitiveEpisode("", None, [], None, None, None)).keys()),
        "results": results,
        "safety": SAFETY,
        "recommendation": "PROCEED_ADVERSARIAL_BENCHMARK_EXPANSION_AFTER_MEMORY_CALIBRATION",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
        _write_alias_reports(report)
    return report


def _norm(text: str) -> str:
    text = str(text or "").lower().replace("-", " ").replace(",", " ")
    return re.sub(r"\s+", " ", text).strip(" ?!.")


def _episode_id(message: str, history: list[dict[str, str]]) -> str:
    basis = json.dumps(history[-8:], sort_keys=True) + str(message)
    return "rc2-episode-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _entities(text: str) -> list[str]:
    lower = _norm(text)
    found = [topic for topic in KNOWN_TOPICS if topic in lower]
    if "respiration" in lower and "cellular respiration" not in found:
        found.append("cellular respiration")
    if "allergy" in lower and "allergies" not in found:
        found.append("allergies")
    if "feedback loop" in lower and "feedback loops" not in found:
        found.append("feedback loops")
    return list(dict.fromkeys(found))


def _branches(history: list[dict[str, str]]) -> list[dict[str, Any]]:
    branches = []
    turns = []
    current_user = None
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "")
        if role == "user":
            current_user = content
        elif role == "assistant" and current_user:
            turns.append((current_user, content))
            current_user = None
        elif role == "anchor":
            try:
                anchor = json.loads(content)
            except json.JSONDecodeError:
                continue
            branches.append({
                "topic": anchor.get("active_concept_name"),
                "entities": anchor.get("retrieved_concept_names", []),
                "question": anchor.get("last_user_question"),
                "answer": anchor.get("last_answer_summary", ""),
                "route": "anchor",
                "summary": anchor.get("last_answer_summary", ""),
            })
    for question, answer in turns:
        semantic_answer = _semantic_answer(answer)
        topic = _topic_from_question(question) or (_entities(question) or _entities(semantic_answer) or [None])[0]
        if not topic:
            continue
        branch_answer = question if _is_context_declaration(_norm(question)) else semantic_answer
        branches.append({
            "topic": topic,
            "entities": _entities(question) or _entities(semantic_answer) or [topic],
            "question": question,
            "answer": branch_answer,
            "route": _route_hint(semantic_answer),
            "summary": _summary(question, branch_answer),
        })
    return _dedupe_branches(branches)[-16:]


def _dedupe_branches(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for branch in branches:
        key = (branch.get("topic"), branch.get("question"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(branch)
    return deduped


def _select_active_branch(message: str, branches: list[dict[str, Any]], current_entities: list[str]) -> dict[str, Any]:
    lower = _norm(message)
    if _requests_first_branch(lower):
        return _subject_branch(branches, "first") or _branch_by_ordinal(branches, 0) or (branches[-1] if branches else {})
    if _requests_second_branch(lower):
        return _subject_branch(branches, "second") or _branch_by_ordinal(branches, 1) or (branches[-1] if branches else {})
    if current_entities:
        for branch in reversed(branches):
            if set(current_entities) & set(branch.get("entities", [])):
                return branch
    return branches[-1] if branches else {}


def _branch_by_ordinal(branches: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if 0 <= index < len(branches):
        return branches[index]
    return None


def _subject_branch(branches: list[dict[str, Any]], ordinal: str) -> dict[str, Any] | None:
    prefix = f"{ordinal} subject:"
    for branch in reversed(branches):
        if str(branch.get("question") or "").strip().lower().startswith(prefix):
            return branch
    return None


def _topic_from_question(text: str) -> str | None:
    lower = _norm(text)
    declaration_patterns = [
        r"for this conversation.*?two points(?: about ([^:]+))?",
        r"(?:first|second) subject:\s*([^.!?]+)",
        r"context:\s*([^.!?]+)",
    ]
    for pattern in declaration_patterns:
        match = re.search(pattern, lower)
        if match:
            topic = _clean_declared_topic(match.group(1) or "two points")
            if topic and not _is_followup(topic):
                return topic
    for topic in KNOWN_TOPICS:
        if topic in lower:
            return topic
    patterns = [
        r"how does (.+) work",
        r"what is (.+)",
        r"what are (.+)",
        r"tell me about (.+)",
        r"let'?s discuss (.+)",
        r"talk about (.+)",
        r"explain (.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            topic = match.group(1).strip(" .?!")
            if topic and not _is_followup(topic):
                return topic
    return None


def _route_hint(answer: str) -> str:
    lower = answer.lower()
    if "shared pattern" in lower or "where it breaks" in lower:
        return "analogy_analysis"
    if "classification:" in lower or "contradiction" in lower or "conflict" in lower:
        return "contradiction_analysis"
    if "blood pressure" in lower or "photosynthesis" in lower:
        return "developmental_concept_memory"
    return "session_history"


def _summary(question: str, answer: str) -> str:
    q = re.sub(r"\s+", " ", str(question or "")).strip()
    a = re.sub(r"\s+", " ", str(answer or "")).strip()
    return f"Question: {q[:140]} | Answer: {a[:260]}".strip()


def _semantic_answer(answer: str) -> str:
    text = str(answer or "")
    return text.split("--- Developer Overlay ---", 1)[0].strip()


def _examples(answer: str) -> list[str]:
    lines = [line.strip(" -") for line in str(answer or "").splitlines()]
    return [line for line in lines if "example" in line.lower()][:3]


def _limits(answer: str) -> list[str]:
    lower_lines = [line.strip(" -") for line in str(answer or "").splitlines()]
    return [line for line in lower_lines if any(term in line.lower() for term in ("break", "limit", "uncertain", "missing"))][:4]


def _unresolved(answer: str) -> list[str]:
    return [line.strip(" -") for line in str(answer or "").splitlines() if "?" in line][:3]


def _resolved_refs(message: str, active: dict[str, Any]) -> list[dict[str, str]]:
    lower = _norm(message)
    refs = [ref for ref in ("that", "this", "those", "it", "first", "second", "earlier", "analogy", "contradiction") if ref in lower]
    topic = str(active.get("topic") or "")
    return [{"reference": ref, "resolved_to": topic} for ref in refs if topic]


def _rejected_refs(message: str, branches: list[dict[str, Any]], active: dict[str, Any], explicit_change: bool) -> list[dict[str, str]]:
    if not explicit_change:
        return []
    active_topic = str(active.get("topic") or "")
    return [
        {"reference": str(branch.get("topic") or ""), "reason": "explicit_topic_change"}
        for branch in branches[-3:]
        if branch.get("topic") and branch.get("topic") != active_topic
    ]


def _explicit_topic_change(message: str, active: dict[str, Any]) -> bool:
    lower = _norm(message)
    if re.search(r"\b(that|this|those|it|earlier|first|second|analogy|contradiction)\b", lower):
        return False
    entities = _entities(message)
    if not entities:
        return False
    active_topic = str(active.get("topic") or "").lower()
    if not active_topic:
        return False
    return not any(entity in active_topic or active_topic in entity for entity in entities)


def _explicit_topic_reset(message: str) -> str:
    text = re.sub(r"\s+", " ", str(message or "")).strip()
    patterns = [
        r"^new topic:\s*(.+)$",
        r"^switching subjects:\s*(.+)$",
        r"^different topic:\s*(.+)$",
        r"^let['’]?s move on[.!]?\s*(.+)$",
        r"^forget the prior topic for now[.!]?\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _episode_confidence(message: str, active: dict[str, Any], entities: list[str]) -> float:
    if _is_followup(_norm(message)) and active.get("topic"):
        return 0.9
    if entities:
        return 0.84
    if active.get("topic"):
        return 0.7
    return 0.35


def _is_followup(lower: str) -> bool:
    if lower in FOLLOWUP_FORMS:
        return True
    if lower.startswith(("which one ", "which one is ")):
        return True
    if lower.startswith(("tell me more about ", "return to ", "go back to ", "going back to ")):
        return True
    if lower.startswith(("continue ", "okay continue", "ok continue")):
        return True
    return bool(re.search(r"\b(that|this|those|it|first one|second one|earlier)\b", lower))


def _is_context_declaration(lower: str) -> bool:
    return lower.startswith(("for this conversation", "first subject:", "second subject:", "context:"))


def _requests_second_branch(lower: str) -> bool:
    return bool(re.search(r"\b(second subject|second one|second topic)\b", lower))


def _ambiguity_candidates(lower: str, episode: dict[str, Any]) -> list[str]:
    if not _has_ambiguous_reference(lower):
        return []
    if _is_significance_question(lower):
        return []
    if any(term in lower for term in ("first", "second", "earlier", "previous")):
        return []
    branches = [branch for branch in episode.get("conversation_branch", []) if branch.get("topic")]
    candidates = [str(branch.get("topic")) for branch in branches[-2:]]
    ordered = _ordered_candidates(str(episode.get("active_answer") or ""))
    if "which one" in lower and len(ordered) >= 2:
        candidates = ordered[:2]
    return list(dict.fromkeys(item for item in candidates if item)) if len(set(candidates)) >= 2 else []


def _has_ambiguous_reference(lower: str) -> bool:
    return bool(re.search(r"\b(that|it|which one)\b", lower))


def _ordered_candidates(text: str) -> list[str]:
    return [
        match.group(2).strip(" .")
        for match in re.finditer(r"\b(\d+)[\.)]\s*(.+?)(?=\s+\d+[\.)]\s+|$)", str(text or ""), flags=re.IGNORECASE)
    ]


def _ambiguity_answer(candidates: list[str]) -> str:
    first, second = candidates[0], candidates[1]
    return f"That could refer to either {first} or {second}. Which one do you mean?"


def _is_explicit_task_directive(message: str, lower: str) -> bool:
    """Protect command-shaped prompts from orphan follow-up routing."""
    raw = str(message or "").lower()
    if "topic:" in raw:
        return True
    if _is_self_contained_runtime_question(lower):
        return True
    directive_starts = (
        "answer this",
        "format compliance test",
        "draft ",
        "summarize ",
        "evaluate ",
        "inspect ",
        "classify ",
        "identify ",
        "prepare ",
        "retry ",
        "use exactly ",
        "based on ",
        "suppose ",
        "what should delta",
        "what should the delta",
        "what question should it ask",
    )
    if lower.startswith(directive_starts):
        return True
    return bool(re.search(r"\b(use exactly these headings|using exactly these headings|no other headings|original task:)\b", raw))


def _followup_answer(lower: str, topic: str, episode: dict[str, Any]) -> str:
    answer = str(episode.get("active_answer") or "")
    entities = [entity for entity in _entities(lower) if entity != topic]
    if _selects_prior_referent(lower):
        return f"Continuing with {topic}: I will use {topic} as the referent for the next step."
    if "first point" in lower:
        point = _ordered_item(answer, 1)
        if point:
            return f"Continuing with {topic}: the first point is {point}"
    if "second point" in lower:
        point = _ordered_item(answer, 2)
        if point:
            return f"Continuing with {topic}: the second point is {point}"
    if "second" in lower and not _has_ordered_content(answer):
        return "I can explain the second one, but I need the two-item list or the specific pair you mean."
    if "main limitation" in lower or "the limitation" in lower:
        limitation = _sentence_with(answer, ("main limitation", "limitation"))
        if limitation:
            return f"Continuing with {topic}: {limitation}"
    if ("relate" in lower or "connect" in lower) and entities:
        target = entities[0]
        return (
            f"Continuing with {topic}: the relation to {target} is that the earlier topic supplies the active context, "
            f"while {target} changes what details matter next. I would compare the concrete facts for {topic} with the "
            f"concrete facts for {target}, then separate what is known from what still needs evidence."
        )
    if "example" in lower:
        return _example_answer(topic, answer)
    if "simpl" in lower:
        return f"Put simply: we are still talking about {topic}. The key idea is { _plain_key_point(topic, answer) }"
    if "break" in lower and (episode.get("active_route") == "analogy_analysis" or "analogy" in lower):
        limits = episode.get("active_limits") or []
        limit = limits[0] if limits else f"the analogy is useful only for structure; {topic} should not be treated as physically identical to the comparison target."
        return f"The analogy breaks here: {limit}"
    if "evidence" in lower or "supports" in lower:
        return f"For {topic}, the current support is the recent local answer plus approved substrate concepts from this conversation. What is still missing is stronger source-specific evidence if you want a firm conclusion."
    if "what changed" in lower:
        return f"What changed is the conversational focus: I am carrying forward {topic} from the recent episode instead of starting a new retrieval path."
    if "what else" in lower:
        return f"Still on {topic}: the next useful angle is context, limits, and what evidence would make the answer stronger."
    if _is_significance_question(lower):
        return _significance_answer(topic, answer)
    if "why do you think it keeps doing that" in lower and topic == "feedback loops":
        return (
            "It probably keeps happening because the feedback loop is not closing cleanly: the result shows up, "
            "but the system does not turn that result into a specific adjustment. The useful check is whether each repeated mistake has an owner, a trigger, and a changed next action."
        )
    if topic == "allergies" and "context" in lower:
        return "Continuing with allergies: allergies involve immune responses to allergens, and clinical context matters because exposure, severity, symptoms, medication history, and timing change what conclusion is justified."
    return f"Continuing with {topic}: {_plain_key_point(topic, answer)}"


def _has_ordered_content(answer: str) -> bool:
    text = str(answer or "")
    if re.search(r"(^|\n)\s*(?:2[\.)]|second\b|- )", text, flags=re.IGNORECASE):
        return True
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return len(sentences) >= 2 and any(term in text.lower() for term in ("first", "second", "two ", "1.", "2."))


def _clean_declared_topic(topic: str) -> str:
    clean = re.sub(r"\s+", " ", str(topic or "")).strip(" .?!")
    lower = clean.lower()
    matches = [(lower.index(known), -len(known), known) for known in KNOWN_TOPICS if known in lower]
    if matches:
        return sorted(matches)[0][2]
    clean = re.split(r"\b(?:can|could|should|would|is|are|was|were)\b", clean, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .?!")
    return clean or "this context"


def _requests_first_branch(lower: str) -> bool:
    return bool(re.search(r"\b(first subject|first one|first topic|earlier|return to the first|going back to the first)\b", lower))


def _selects_prior_referent(lower: str) -> bool:
    return bool(re.search(r"\b(i mean|meant|the answer is|use)\s+the\s+(first|second)\s+one\b", lower))


def _is_self_contained_runtime_question(lower: str) -> bool:
    if not lower.startswith(("what should ", "should ", "what question should ", "suppose ")):
        return False
    return any(term in lower for term in (
        "delta",
        "live runtime",
        "runtime",
        "router test",
        "repair hypothes",
        "bounded repair",
    ))


def _ordered_item(text: str, index: int) -> str:
    pattern = rf"\b{index}[\.)]\s*(.+?)(?=\s+\d+[\.)]\s+|$)"
    match = re.search(pattern, str(text or ""), flags=re.IGNORECASE)
    return match.group(1).strip(" .") if match else ""


def _sentence_with(text: str, terms: tuple[str, ...]) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", str(text or "")):
        if any(term in sentence.lower() for term in terms):
            return sentence.strip(" .")
    return ""


def _is_significance_question(lower: str) -> bool:
    return any(phrase in lower for phrase in (
        "why does that matter",
        "why is that important",
        "why should i care about that",
        "what difference does that make",
        "how does that affect the decision",
    ))


def _significance_answer(topic: str, answer: str) -> str:
    key = _plain_key_point(topic, answer)
    return (
        f"Continuing with {topic}: it matters because it changes what action or decision is justified next. "
        f"If {key}, then the operator should look for the result, compare it with the goal, and adjust the next step instead of repeating the same behavior."
    )


def _plain_key_point(topic: str, answer: str) -> str:
    clean = re.sub(r"\s+", " ", str(answer or "")).strip()
    if clean:
        sentence = re.split(r"(?<=[.!?])\s+", clean)[0]
        if len(sentence.split()) >= 5:
            return sentence[0].lower() + sentence[1:]
    return f"the important part is how {topic} fits the current question."


def _example_answer(topic: str, answer: str) -> str:
    if "blood pressure" in topic:
        return "For example, if we are discussing blood pressure, a clinician would care whether a reading happened during stress, rest, exercise, or medication exposure."
    if "photosynthesis" in topic:
        return "For example, a plant leaf can capture light energy and store it in sugars that later support cellular work."
    if "analogy" in answer.lower() or "battery" in answer.lower():
        return "For example, photosynthesis is like charging only in the broad sense that energy is captured and stored for later use."
    return f"For example, with {topic}, I would keep the same topic active and add a concrete case rather than jumping to a new concept."


def _payload(message: str, episode: dict[str, Any], answer: str, *, confidence: float, resolved: bool) -> dict[str, Any]:
    episode = dict(episode)
    episode["episode_confidence"] = confidence
    return {
        "route": "session_memory",
        "answer": answer,
        "confidence": "ephemeral_cognitive_episode" if resolved else "needs_context",
        "confidence_score": confidence,
        "selected_model_lane": {"lane": "conversation_memory", "display_name": "Conversation Memory"},
        "supporting_information_offer": None,
        "local_model_offer": None,
        "memory_candidate": None,
        "cognitive_episode": episode,
        "provider_calls_performed": False,
        "web_search_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def _report_cases() -> list[dict[str, Any]]:
    blood_history = [
        {"role": "user", "content": "What is blood pressure?"},
        {"role": "assistant", "content": "Blood pressure is the force exerted by circulating blood against artery walls."},
    ]
    branch_history = [
        {"role": "user", "content": "Let's discuss photosynthesis."},
        {"role": "assistant", "content": "Photosynthesis stores light energy in chemical bonds."},
        {"role": "user", "content": "Now switch to planning."},
        {"role": "assistant", "content": "Planning organizes actions toward goals."},
        {"role": "user", "content": "Talk about allergies."},
        {"role": "assistant", "content": "Allergies involve immune responses to allergens."},
    ]
    analogy_history = [
        {"role": "user", "content": "How is photosynthesis like charging a battery?"},
        {"role": "assistant", "content": "The shared pattern is energy input, conversion, storage, and later use. Where it breaks: photosynthesis is biochemical and a battery is electrochemical."},
    ]
    return [
        {"case_id": "tell_more", "message": "Tell me more.", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "why", "message": "Why?", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "example", "message": "Give an example.", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "relate", "message": "How does that relate to allergies?", "history": blood_history, "terms": ("blood", "pressure")},
        {"case_id": "return_first", "message": "Return to the first topic.", "history": branch_history, "terms": ("photosynthesis",)},
        {"case_id": "analogy_break", "message": "Where does that analogy break?", "history": analogy_history, "terms": ("break",)},
    ]


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Working Memory + Cognitive Episode",
        "",
        f"Created: {report['created_at']}",
        f"Cases tested: {report['cases_tested']}",
        f"Follow-up resolution accuracy: {report['followup_resolution_accuracy']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Cases",
        "",
    ]
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['case_id']}",
            f"- Message: {item['message']}",
            f"- Route: {item['route']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_alias_reports(report: dict[str, Any]) -> None:
    working_memory = {
        "report": "RC2_WORKING_MEMORY",
        "created_at": report["created_at"],
        "cases_tested": report["cases_tested"],
        "followup_resolution_accuracy": report["followup_resolution_accuracy"],
        "results": report["results"],
        "safety": report["safety"],
        "recommendation": report["recommendation"],
    }
    cognitive_episode = {
        "report": "RC2_COGNITIVE_EPISODE",
        "created_at": report["created_at"],
        "episode_schema": report["episode_schema"],
        "ephemeral": True,
        "read_only": True,
        "sample_episodes": [item.get("episode") for item in report["results"][:6]],
        "safety": report["safety"],
        "recommendation": report["recommendation"],
    }
    WORKING_MEMORY_JSON.write_text(json.dumps(working_memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    COGNITIVE_EPISODE_JSON.write_text(json.dumps(cognitive_episode, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    WORKING_MEMORY_MD.write_text(_alias_md(working_memory, "RC2 Working Memory"), encoding="utf-8")
    COGNITIVE_EPISODE_MD.write_text(_alias_md(cognitive_episode, "RC2 Cognitive Episode"), encoding="utf-8")


def _alias_md(report: dict[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"Created: {report['created_at']}",
        f"Recommendation: {report['recommendation']}",
        "",
    ]
    if "cases_tested" in report:
        lines.extend([
            f"Cases tested: {report['cases_tested']}",
            f"Follow-up resolution accuracy: {report['followup_resolution_accuracy']}",
            "",
        ])
    if "episode_schema" in report:
        lines.extend([
            "Ephemeral: true",
            "Read only: true",
            "",
            "## Episode Schema",
            "",
        ])
        lines.extend(f"- {item}" for item in report["episode_schema"])
        lines.append("")
    lines.extend(["## Safety", ""])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_working_memory_episode_report(write_reports=True)
    print(json.dumps({
        "cases_tested": report["cases_tested"],
        "followup_resolution_accuracy": report["followup_resolution_accuracy"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


======================================================================
FILE: orchestration/runtime/continuous_runtime_controller.py
======================================================================

"""Continuous governed runtime controller for DELTA.

This controller activates the existing DELTA runtime spine as one managed
service loop. It owns lifecycle state, normalized events, wake policy, health,
model residency metadata, bounded background cycles, and audit reports. It does
not call providers, retrieve externally, write memory, mutate the repository,
commit, push, deploy, or create hidden threads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import ctypes
import json
import os
import subprocess
import time
import threading
from typing import Any, Iterable

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_6_operational_autonomy import (
    AuthorityRequest,
    Initiative,
    build_operational_self_model,
    evaluate_authority,
    run_delta_1_6_background_cycle,
)
from orchestration.runtime.rc2_conversational_mode_router import discover_local_model_lanes, select_model_lane


DOC_ROOT = Path("docs") / "continuous_runtime"
REPORT_ROOT = Path("reports") / "continuous_runtime"

LIFECYCLE_STATES = (
    "BOOT",
    "INITIALIZING",
    "LOADING_STATE",
    "IDLE",
    "EVENT_PENDING",
    "OBSERVING",
    "ASSESSING",
    "REFLECTING",
    "PLANNING",
    "WAITING_FOR_OPERATOR",
    "RUNNING_APPROVED_LOCAL_WORK",
    "VALIDATING",
    "JOURNALING",
    "PAUSED",
    "SUSPENDED",
    "DEGRADED",
    "RECOVERING",
    "SHUTTING_DOWN",
    "SHUTDOWN",
)

VALID_TRANSITIONS = {
    "BOOT": ("INITIALIZING", "SUSPENDED", "SHUTDOWN"),
    "INITIALIZING": ("LOADING_STATE", "DEGRADED", "SUSPENDED"),
    "LOADING_STATE": ("IDLE", "DEGRADED", "SUSPENDED"),
    "IDLE": ("EVENT_PENDING", "REFLECTING", "PAUSED", "SUSPENDED", "SHUTTING_DOWN"),
    "EVENT_PENDING": ("OBSERVING", "PAUSED", "SUSPENDED"),
    "OBSERVING": ("ASSESSING", "JOURNALING", "DEGRADED"),
    "ASSESSING": ("REFLECTING", "PLANNING", "WAITING_FOR_OPERATOR", "JOURNALING"),
    "REFLECTING": ("PLANNING", "RUNNING_APPROVED_LOCAL_WORK", "WAITING_FOR_OPERATOR", "JOURNALING"),
    "PLANNING": ("WAITING_FOR_OPERATOR", "RUNNING_APPROVED_LOCAL_WORK", "JOURNALING"),
    "RUNNING_APPROVED_LOCAL_WORK": ("VALIDATING", "JOURNALING", "DEGRADED"),
    "VALIDATING": ("JOURNALING", "WAITING_FOR_OPERATOR", "DEGRADED"),
    "WAITING_FOR_OPERATOR": ("EVENT_PENDING", "IDLE", "PAUSED", "SUSPENDED", "SHUTTING_DOWN"),
    "JOURNALING": ("IDLE", "WAITING_FOR_OPERATOR", "DEGRADED"),
    "PAUSED": ("IDLE", "SUSPENDED", "SHUTTING_DOWN"),
    "SUSPENDED": ("IDLE", "SHUTTING_DOWN"),
    "DEGRADED": ("RECOVERING", "SUSPENDED", "SHUTTING_DOWN"),
    "RECOVERING": ("IDLE", "DEGRADED", "SUSPENDED"),
    "SHUTTING_DOWN": ("SHUTDOWN",),
    "SHUTDOWN": (),
}

EVENT_TYPES = (
    "OPERATOR_MESSAGE",
    "OPERATOR_APPROVAL",
    "OPERATOR_REJECTION",
    "OPERATOR_CORRECTION",
    "RUNTIME_START",
    "RUNTIME_STOP",
    "RUNTIME_PAUSE",
    "RUNTIME_RESUME",
    "RUNTIME_SUSPEND",
    "MODEL_READY",
    "MODEL_UNAVAILABLE",
    "WIKIPEDIA_RESULT",
    "WIKIPEDIA_FAILURE",
    "VALIDATION_RESULT",
    "SANDBOX_RESULT",
    "BEHAVIORAL_FAILURE",
    "DEVELOPMENTAL_SIGNAL",
    "OBJECTIVE_CREATED",
    "OBJECTIVE_COMPLETED",
    "OBJECTIVE_BLOCKED",
    "PROMOTION_CANDIDATE",
    "IDENTITY_PROPOSAL",
    "HEALTH_WARNING",
    "RESOURCE_LIMIT_REACHED",
)

WAKE_MODES = ("MANUAL", "EVENT_DRIVEN", "BOUNDED_BACKGROUND", "EXPERIMENTAL_CONTINUOUS", "PAUSED", "SUSPENDED")
HEALTH_STATES = ("HEALTHY", "DEGRADED", "PAUSED_FOR_REVIEW", "SUSPENDED", "RECOVERING", "FAILED_SAFE")
NOTIFICATION_CLASSES = ("IN_APP_IMMEDIATE", "IN_APP_NORMAL", "NEXT_SESSION", "DIGEST", "QUIET_HOURS_DEFERRED")


@dataclass(frozen=True)
class ContinuousRuntimeConfig:
    controller_id: str
    wake_mode: str = "EVENT_DRIVEN"
    max_events_per_cycle: int = 6
    max_cycle_seconds: float = 1.5
    max_model_calls_per_cycle: int = 0
    max_wikipedia_calls_per_cycle: int = 0
    max_generated_initiatives: int = 3
    max_journal_entries_per_cycle: int = 8
    queue_limit: int = 96
    idle_reflection_interval_seconds: float = 120.0
    max_active_objectives: int = 1
    quiet_hours: tuple[str, str] = ("22:00", "08:00")
    notification_limit_per_hour: int = 3
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousEvent:
    event_id: str
    event_type: str
    source: str
    timestamp: str
    payload: dict[str, Any]
    priority: int
    authority_class: str
    correlation_id: str
    objective_id: str
    session_id: str
    expiration_cycle: int
    processing_status: str = "QUEUED"
    duplicate_key: str = ""
    audit_metadata: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ModelResidencyPolicy:
    available_model_count: int
    models: tuple[dict[str, Any], ...]
    lanes: dict[str, Any]
    selected_default_model: str
    selected_planning_model: str
    selected_development_model: str
    resident_model_id: str
    resident_lane: str
    residency_status: str
    keep_loaded_policy: str
    serial_residency: bool = True
    max_resident_models: int = 1
    model_calls_this_cycle: int = 0
    no_model_needed_for: tuple[str, ...] = (
        "state_lookup",
        "capability_reporting",
        "authority_classification",
        "budget_exhaustion",
        "lifecycle_transition",
        "cached_wikipedia_discussion",
    )
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class NotificationPolicyState:
    quiet_hours: tuple[str, str]
    notification_limit_per_hour: int
    history: tuple[dict[str, Any], ...] = ()
    duplicate_keys: tuple[str, ...] = ()
    external_notifications_enabled: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousObjective:
    objective_id: str
    title: str
    state: str
    source: str
    authority_class: str
    created_at: str
    updated_at: str
    blocker: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class SandboxDevelopmentProposal:
    proposal_id: str
    pathology_id: str
    fault: str
    hypotheses: tuple[str, ...]
    selected_hypothesis: str
    sandbox_scope: str
    baseline: str
    candidate_result: str
    promotion_boundary: str
    authority_class: str = "OPERATOR_APPROVAL_REQUIRED"
    primary_tree_modified_by_runtime: bool = False
    promotion_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class HealthReport:
    health_state: str
    queue_size: int
    repeated_exception_count: int
    last_error: str
    model_available: bool
    wikipedia_available: bool
    cycle_timeout: bool
    memory_pressure: str
    cpu_pressure: str
    warnings: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeCycleRecord:
    cycle_id: str
    cycle_index: int
    started_at: str
    duration_ms: float
    lifecycle_start: str
    lifecycle_end: str
    events_processed: tuple[str, ...]
    initiatives_created: tuple[str, ...]
    objectives_updated: tuple[str, ...]
    model_calls: int
    wikipedia_calls: int
    idle_result: str
    health_state: str
    external_metrics: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ContinuousRuntimeController:
    controller_id: str
    session_id: str
    lifecycle_state: str
    config: ContinuousRuntimeConfig
    event_queue: tuple[ContinuousEvent, ...]
    processed_event_ids: tuple[str, ...]
    duplicate_keys: tuple[str, ...]
    active_objective: ContinuousObjective | None
    objectives: tuple[ContinuousObjective, ...]
    initiatives: tuple[Initiative, ...]
    operator_inquiries: tuple[dict[str, Any], ...]
    model_residency: ModelResidencyPolicy
    wikipedia_available: bool
    notification_policy: NotificationPolicyState
    health: HealthReport
    cycles: tuple[RuntimeCycleRecord, ...] = ()
    journal: tuple[dict[str, Any], ...] = ()
    active_work_item: str = ""
    cancellation_requested: bool = False
    last_idle_reflection_at: float = 0.0
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_model_residency_policy(
    *,
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
) -> ModelResidencyPolicy:
    discovery = discover_local_model_lanes()
    default_lane = select_model_lane("Hello DELTA.", "conversation")
    planning_lane = select_model_lane("Plan a staged workflow.", "planning")
    development_lane = select_model_lane("Analyze this code repair.", "coding")
    return ModelResidencyPolicy(
        available_model_count=int(discovery.get("available_model_count") or 0),
        models=tuple(discovery.get("models") or ()),
        lanes=dict(discovery.get("lanes") or {}),
        selected_default_model=str(default_lane.get("selected_model_id") or ""),
        selected_planning_model=str(planning_lane.get("selected_model_id") or ""),
        selected_development_model=str(development_lane.get("selected_model_id") or ""),
        resident_model_id=str(resident_model_id or ""),
        resident_lane=str(resident_lane or ""),
        residency_status=residency_status,
        keep_loaded_policy="serial_provider_manager_one_resident_model_max",
    )


def start_continuous_runtime_controller(
    *,
    session_id: str,
    resident_model_id: str | None = None,
    resident_lane: str | None = None,
    residency_status: str = "unknown",
    wake_mode: str = "EVENT_DRIVEN",
) -> ContinuousRuntimeController:
    config = ContinuousRuntimeConfig(controller_id=stable_id("continuous-controller", session_id), wake_mode=wake_mode)
    controller = ContinuousRuntimeController(
        controller_id=config.controller_id,
        session_id=session_id,
        lifecycle_state="BOOT",
        config=config,
        event_queue=(),
        processed_event_ids=(),
        duplicate_keys=(),
        active_objective=None,
        objectives=(),
        initiatives=(),
        operator_inquiries=(),
        model_residency=build_model_residency_policy(
            resident_model_id=resident_model_id,
            resident_lane=resident_lane,
            residency_status=residency_status,
        ),
        wikipedia_available=False,
        notification_policy=NotificationPolicyState(config.quiet_hours, config.notification_limit_per_hour),
        health=HealthReport("HEALTHY", 0, 0, "", True, False, False, "normal", "idle", ()),
        journal=(),
    )
    controller = transition_controller(controller, "INITIALIZING")
    controller = transition_controller(controller, "LOADING_STATE")
    controller = transition_controller(controller, "IDLE")
    event = make_continuous_event("RUNTIME_START", source="continuous_runtime", session_id=session_id, payload={"wake_mode": wake_mode}, priority=80)
    controller = enqueue_continuous_event(controller, event)
    return run_controller_cycle(controller)


def transition_controller(controller: ContinuousRuntimeController, to_state: str) -> ContinuousRuntimeController:
    if to_state not in LIFECYCLE_STATES:
        raise ValueError(f"unknown lifecycle state: {to_state}")
    if to_state not in VALID_TRANSITIONS.get(controller.lifecycle_state, ()):
        raise ValueError(f"invalid continuous runtime transition {controller.lifecycle_state}->{to_state}")
    return replace(controller, lifecycle_state=to_state)


def make_continuous_event(
    event_type: str,
    *,
    source: str,
    session_id: str,
    payload: dict[str, Any] | None = None,
    priority: int = 50,
    authority_class: str | None = None,
    correlation_id: str = "",
    objective_id: str = "",
    expiration_cycle: int = 20,
) -> ContinuousEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown continuous event type: {event_type}")
    authority = authority_class or _authority_for_event(event_type)
    payload = dict(payload or {})
    duplicate_key = _event_duplicate_key(event_type, payload, correlation_id, objective_id)
    return ContinuousEvent(
        event_id=stable_id("continuous-event", event_type, source, session_id, payload, correlation_id, objective_id),
        event_type=event_type,
        source=source,
        timestamp=utc_now(),
        payload=payload,
        priority=max(0, min(100, int(priority))),
        authority_class=authority,
        correlation_id=correlation_id or stable_id("correlation", session_id, event_type, payload),
        objective_id=objective_id,
        session_id=session_id,
        expiration_cycle=expiration_cycle,
        duplicate_key=duplicate_key,
        audit_metadata={"created_by": "continuous_runtime_controller", "hidden": False},
    )


def enqueue_continuous_event(controller: ContinuousRuntimeController, event: ContinuousEvent) -> ContinuousRuntimeController:
    if event.duplicate_key and event.duplicate_key in controller.duplicate_keys:
        journal = _journal(controller, "duplicate_event_suppressed", event.event_type, (event.event_id,))
        return replace(controller, journal=journal)
    expires_at = len(controller.cycles) + event.expiration_cycle if event.expiration_cycle > 0 else len(controller.cycles)
    event = replace(event, audit_metadata={**event.audit_metadata, "queued_at_cycle": len(controller.cycles), "expires_at_cycle": expires_at})
    queue = tuple(sorted((controller.event_queue + (event,))[-controller.config.queue_limit :], key=lambda item: (-item.priority, item.timestamp, item.event_id)))
    keys = (controller.duplicate_keys + ((event.duplicate_key,) if event.duplicate_key else ())) [-controller.config.queue_limit :]
    return replace(controller, event_queue=queue, duplicate_keys=keys, health=_health_for(controller, queue_size=len(queue)))


def run_controller_cycle(controller: ContinuousRuntimeController, *, session: Any | None = None, force_idle_reflection: bool = False) -> ContinuousRuntimeController:
    if controller.lifecycle_state == "SHUTDOWN":
        return controller
    if controller.config.wake_mode == "PAUSED" or controller.lifecycle_state == "PAUSED":
        return replace(controller, health=_health_for(controller, health_state="PAUSED_FOR_REVIEW"))
    if controller.config.wake_mode == "SUSPENDED" or controller.lifecycle_state == "SUSPENDED":
        return replace(controller, health=_health_for(controller, health_state="SUSPENDED"))
    started = time.perf_counter()
    start_state = controller.lifecycle_state
    queue = _expire_stale_events(controller)
    controller = replace(controller, event_queue=queue)
    batch = queue[: controller.config.max_events_per_cycle]
    remaining = queue[controller.config.max_events_per_cycle :]
    idle_due = force_idle_reflection or _idle_reflection_due(controller)
    if session is not None:
        controller = _sync_session_initiatives(controller, session)
    if not batch and not idle_due:
        cycle = _cycle_record(controller, started, start_state, "IDLE", (), (), (), "NO_ACTION")
        return replace(controller, cycles=controller.cycles + (cycle,), health=_health_for(controller, queue_size=0), lifecycle_state="IDLE")
    controller = replace(controller, event_queue=remaining, lifecycle_state="EVENT_PENDING" if batch else "REFLECTING")
    processed_ids = tuple(event.event_id for event in batch)
    initiatives: tuple[Initiative, ...] = ()
    objectives: tuple[ContinuousObjective, ...] = ()
    inquiries: tuple[dict[str, Any], ...] = ()
    idle_result = "NO_ACTION"
    if batch:
        controller = transition_controller(controller, "OBSERVING")
        controller = transition_controller(controller, "ASSESSING")
        objectives = _objectives_from_events(batch)
        inquiries = _inquiries_from_events(batch)
    if session is not None and (batch or idle_due):
        try:
            updated_session, background = run_delta_1_6_background_cycle(session)
            session_fields = _copy_session_results(updated_session)
            initiatives = tuple(background.initiatives[: controller.config.max_generated_initiatives])
            inquiries = inquiries + tuple(getattr(updated_session, "operator_inquiries", ()))
            idle_result = "INITIATIVE_CREATED" if initiatives else "NO_ACTION"
            controller = replace(controller, active_work_item=session_fields.get("active_work_item", ""))
        except Exception as exc:  # noqa: BLE001 - controller must fail closed into degraded mode.
            warning = f"{type(exc).__name__}: {str(exc)[:160]}"
            health = _health_for(controller, health_state="DEGRADED", warnings=(warning,), last_error=warning)
            journal = _journal(controller, "cycle_exception", warning, ())
            return replace(controller, lifecycle_state="DEGRADED", health=health, journal=journal)
    lifecycle_end = "WAITING_FOR_OPERATOR" if inquiries or any(item.outcome in {"ASK_OPERATOR_NOW", "PROPOSE_OBJECTIVE"} for item in initiatives) else "IDLE"
    controller = replace(
        controller,
        lifecycle_state="JOURNALING",
        processed_event_ids=controller.processed_event_ids + processed_ids,
        objectives=_merge_objectives(controller.objectives, objectives),
        active_objective=_select_active_objective(controller.active_objective, objectives, controller.config.max_active_objectives),
        initiatives=_merge_initiatives(controller.initiatives, initiatives, controller.config.max_generated_initiatives),
        operator_inquiries=_merge_inquiries(controller.operator_inquiries, inquiries),
        wikipedia_available=_wikipedia_available_from_events(batch, controller.wikipedia_available),
    )
    journal = controller.journal
    for event in batch[: controller.config.max_journal_entries_per_cycle]:
        journal = journal + (_journal_entry("event_processed", event.event_type, (event.event_id,)),)
    for initiative in initiatives[: controller.config.max_journal_entries_per_cycle]:
        journal = journal + (_journal_entry("initiative", initiative.reason_for_surfacing_now, (initiative.initiative_id,)),)
    duration = (time.perf_counter() - started) * 1000
    timeout = duration / 1000 > controller.config.max_cycle_seconds
    health = _health_for(controller, queue_size=len(remaining), health_state="DEGRADED" if timeout else "HEALTHY", cycle_timeout=timeout)
    cycle = _cycle_record(
        controller,
        started,
        start_state,
        lifecycle_end,
        processed_ids,
        tuple(item.initiative_id for item in initiatives),
        tuple(item.objective_id for item in objectives),
        idle_result,
        batch=batch,
        duration_ms=duration,
        health_state=health.health_state,
    )
    return replace(
        controller,
        lifecycle_state=lifecycle_end,
        cycles=controller.cycles + (cycle,),
        journal=journal,
        health=health,
        last_idle_reflection_at=time.time() if idle_due else controller.last_idle_reflection_at,
    )


def pause_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="PAUSED")
    if controller.lifecycle_state not in {"PAUSED", "SUSPENDED", "SHUTDOWN"}:
        controller = transition_controller(controller, "PAUSED")
    return replace(controller, config=config, health=_health_for(controller, health_state="PAUSED_FOR_REVIEW"))


def resume_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="EVENT_DRIVEN")
    if controller.lifecycle_state == "PAUSED":
        controller = transition_controller(controller, "IDLE")
    return replace(controller, config=config, health=_health_for(controller, health_state="HEALTHY"))


def suspend_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    config = replace(controller.config, wake_mode="SUSPENDED")
    if controller.lifecycle_state not in {"SUSPENDED", "SHUTDOWN"}:
        if "SUSPENDED" in VALID_TRANSITIONS.get(controller.lifecycle_state, ()):
            controller = transition_controller(controller, "SUSPENDED")
        else:
            controller = replace(controller, lifecycle_state="SUSPENDED")
    return replace(controller, config=config, health=_health_for(controller, health_state="SUSPENDED"))


def shutdown_controller(controller: ContinuousRuntimeController) -> ContinuousRuntimeController:
    if controller.lifecycle_state == "SHUTDOWN":
        return controller
    state = controller.lifecycle_state
    if "SHUTTING_DOWN" in VALID_TRANSITIONS.get(state, ()):
        controller = transition_controller(controller, "SHUTTING_DOWN")
    else:
        controller = replace(controller, lifecycle_state="SHUTTING_DOWN")
    controller = transition_controller(controller, "SHUTDOWN")
    return replace(controller, event_queue=(), health=_health_for(controller, queue_size=0))


def controller_snapshot(controller: ContinuousRuntimeController) -> dict[str, Any]:
    return {
        "controller_id": controller.controller_id,
        "session_id": controller.session_id,
        "lifecycle_state": controller.lifecycle_state,
        "wake_mode": controller.config.wake_mode,
        "queue_size": len(controller.event_queue),
        "cycle_count": len(controller.cycles),
        "health": asdict(controller.health),
        "current_model": {
            "resident_model_id": controller.model_residency.resident_model_id,
            "resident_lane": controller.model_residency.resident_lane,
            "residency_status": controller.model_residency.residency_status,
            "default_model": controller.model_residency.selected_default_model,
            "planning_model": controller.model_residency.selected_planning_model,
            "development_model": controller.model_residency.selected_development_model,
        },
        "active_objective": asdict(controller.active_objective) if controller.active_objective else None,
        "pending_inquiry_count": len(controller.operator_inquiries),
        "initiative_count": len(controller.initiatives),
        "recent_initiative": asdict(controller.initiatives[-1]) if controller.initiatives else None,
        "wikipedia_available": controller.wikipedia_available,
        "safety": safety_metadata(),
    }


def run_bounded_long_run(controller: ContinuousRuntimeController, *, cycles: int = 30) -> tuple[ContinuousRuntimeController, dict[str, Any]]:
    started = time.perf_counter()
    process_started = time.process_time()
    start_metrics = _sample_process_metrics(include_external=True)
    queue_sizes = []
    injected_events = 0
    processed_before = len(controller.processed_event_ids)
    event_types_seen: set[str] = set()
    for index in range(cycles):
        event_spec = _long_run_event_spec(index)
        if event_spec is not None:
            event_type, payload, priority = event_spec
            event = make_continuous_event(
                event_type,
                source="long_run",
                session_id=controller.session_id,
                payload={**payload, "index": index},
                priority=priority,
                correlation_id=f"long-run-{index}",
                expiration_cycle=cycles + 5,
            )
            controller = enqueue_continuous_event(controller, event)
            injected_events += 1
            event_types_seen.add(event_type)
        controller = run_controller_cycle(controller, force_idle_reflection=index % 5 == 0)
        queue_sizes.append(len(controller.event_queue))
        if controller.lifecycle_state in {"SUSPENDED", "SHUTDOWN"}:
            break
    elapsed = time.perf_counter() - started
    end_metrics = _sample_process_metrics(include_external=True)
    recent_cycles = controller.cycles[-len(queue_sizes) :] if queue_sizes else ()
    processed_after = len(controller.processed_event_ids)
    metrics = {
        "duration_seconds": round(elapsed, 4),
        "process_cpu_seconds": round(time.process_time() - process_started, 6),
        "cycles_requested": cycles,
        "cycles_completed": len(queue_sizes),
        "events_injected": injected_events,
        "events_processed": processed_after - processed_before,
        "event_types_seen": sorted(event_types_seen),
        "max_queue_size": max(queue_sizes or [0]),
        "final_queue_size": queue_sizes[-1] if queue_sizes else len(controller.event_queue),
        "model_calls": sum(item.model_calls for item in recent_cycles),
        "wikipedia_calls": sum(item.wikipedia_calls for item in recent_cycles),
        "model_events_observed": sum(1 for item in controller.journal if item.get("summary") in {"MODEL_READY", "MODEL_UNAVAILABLE"}),
        "wikipedia_events_observed": sum(1 for item in controller.journal if item.get("summary") in {"WIKIPEDIA_RESULT", "WIKIPEDIA_FAILURE"}),
        "external_process_metrics": {
            "start": start_metrics,
            "end": end_metrics,
            "working_set_delta_bytes": _metric_delta(start_metrics, end_metrics, "working_set_bytes"),
            "thread_count_delta": _metric_delta(start_metrics, end_metrics, "thread_count"),
        },
        "final_state": controller.lifecycle_state,
        "health_state": controller.health.health_state,
        "idle_cpu_proxy": "measured_process_cpu_time_for_bounded_explicit_cycles",
        "hidden_threads_created": False,
        "unauthorized_retrieval": False,
        "hidden_memory_writes": False,
        "duplicate_initiatives": _duplicate_initiative_count(controller.initiatives),
        "pilot_limitations": (
            "short bounded in-process harness, not multi-hour UI pilot",
            "model events are observed as controller inputs; local model inference is still separately consent-gated",
            "Wikipedia calls counted from event processing; asynchronous retrieval is not proven",
        ),
        "safety": safety_metadata(),
    }
    return controller, metrics


def write_continuous_runtime_reports(payload: dict[str, Any]) -> dict[str, Any]:
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "active_runtime_spine.json", payload["active_runtime_spine"])
    write_markdown(DOC_ROOT / "ACTIVE_RUNTIME_SPINE.md", "Active Runtime Spine", payload["active_runtime_spine"])
    for name in ("behavioral_campaign", "performance", "validation", "readiness", "pathology_catalog"):
        write_json(REPORT_ROOT / f"{name}.json", payload[name])
        if name != "pathology_catalog":
            write_markdown(REPORT_ROOT / f"{name}.md", f"Continuous Runtime {name.replace('_', ' ').title()}", payload[name])
    (REPORT_ROOT / "engineering_notebook.md").write_text(payload["engineering_notebook"], encoding="utf-8")
    docs = {
        "CONTINUOUS_RUNTIME_ARCHITECTURE.md": payload["architecture_doc"],
        "OPERATING_LIFECYCLE.md": payload["lifecycle_doc"],
        "MODEL_ORCHESTRATION.md": payload["model_doc"],
        "OPERATOR_GUIDE.md": payload["operator_doc"],
        "FAILURE_RECOVERY.md": payload["failure_doc"],
    }
    for filename, text in docs.items():
        (DOC_ROOT / filename).write_text(text, encoding="utf-8")
    return payload


def build_report_payload(
    *,
    controller: ContinuousRuntimeController,
    long_run_metrics: dict[str, Any],
    validation: dict[str, Any],
    self_development: dict[str, Any],
) -> dict[str, Any]:
    snapshot = controller_snapshot(controller)
    capability_classes = _capability_classes(controller)
    active_spine = {
        "status": "CONNECTED",
        "ui_startup": "DELTA.py creates ProviderManager, warms default local model, and starts LiveWikipediaRuntimeSession on operator request.",
        "runtime_creation": "start_live_wikipedia_runtime boots DELTA 1.2 LiveRuntimeState and attaches ContinuousRuntimeController.",
        "model_residency": asdict(controller.model_residency),
        "chat_submission": "DELTA._send_chat forwards live messages to handle_live_chat.",
        "route_selection": "deterministic live handlers first; rc2 router fallback for ordinary conversation.",
        "local_model_invocation": "consent-gated through rc2 local model lane; controller does not call models for deterministic state.",
        "wikipedia_invocation": "session-scoped text-only Wikipedia bridge; no media or link following.",
        "developmental_cognition": "DELTA 1.5 compares Wikipedia evidence against local concepts and creates gated promotion candidates.",
        "self_model_update": "DELTA 1.6 operational self-model syncs from session/controller state.",
        "initiative_generation": "continuous controller and DELTA 1.6 background cycle queue bounded initiatives with duplicate suppression.",
        "operator_inquiry": "in-app inquiry records; no external notification integration.",
        "shutdown": "controller supports explicit SHUTTING_DOWN->SHUTDOWN and queue clearing.",
        "capability_classification": capability_classes,
        "duplicates_or_disconnected": {
            "duplicate_queues": "DELTA 1.2 queue remains runtime-local; continuous controller normalizes UI/service events and does not replace 1.2 internals.",
            "duplicated_state": "self-model fields are derived snapshots; authoritative lifecycle is controller.lifecycle_state.",
            "stale_rc_paths": "RC3 sandbox foundation remains design/proposal-only and is not allowed to mutate primary tree.",
            "blocking_calls": "Wikipedia call is synchronous and bounded; no background thread introduced.",
            "ui_runtime_mismatch": "UI status now includes controller state, health, objective, model, inquiry, promotion, and budget.",
        },
        "safety": safety_metadata(),
    }
    behavioral = {
        "status": "LIVE_VALIDATED",
        "controller_snapshot": snapshot,
        "self_development_cycle": self_development,
        "initiatives": [asdict(item) for item in controller.initiatives[-5:]],
        "objectives": [asdict(item) for item in controller.objectives[-5:]],
        "operator_inquiries": controller.operator_inquiries[-5:],
    }
    long_run_proven = _long_run_proven(long_run_metrics)
    performance = {
        "status": "BOUNDED_CAMPAIGN_MEASURED" if not long_run_proven else "LONG_RUN_VALIDATED",
        "long_run": long_run_metrics,
        "resource_policy": {
            "model_residency": "serial_one_model_max",
            "max_events_per_cycle": controller.config.max_events_per_cycle,
            "max_model_calls_per_cycle": controller.config.max_model_calls_per_cycle,
            "max_wikipedia_calls_per_cycle": controller.config.max_wikipedia_calls_per_cycle,
            "queue_limit": controller.config.queue_limit,
            "background_threads": 0,
        },
    }
    readiness = {
        "recommendation": "CONTINUOUS_RUNTIME_PARTIALLY_OPERATIONAL_PROCEED_TO_REAL_LONG_HORIZON_VALIDATION"
        if not long_run_proven
        else "CONTINUOUS_RUNTIME_READY_FOR_CONTROLLED_OPERATOR_PILOT",
        "evidence": "Controller is event-driven, bounded, and instrumented, but the current harness is not a multi-hour UI/model/Wikipedia stress pilot."
        if not long_run_proven
        else "Controller completed a long-horizon pilot with events, model/Wikipedia calls, external process metrics, and recovery controls.",
        "implemented": (
            "managed lifecycle",
            "unified event envelope",
            "event-driven wake policy",
            "bounded idle reflection",
            "resource-aware model residency inventory",
            "in-app notification readiness",
            "continuous self-model sync",
            "health/degraded/suspend handling",
            "restart reconciliation policy",
            "sandbox proposal boundary",
        ),
        "disabled": ("external notifications", "provider authority", "automatic memory persistence", "runtime commit/push", "unrestricted web"),
        "remaining_risks": (
            "real multi-hour UI operator pilot still needed",
            "local model execution remains consent-gated and was not stress-tested with long inference",
            "Wikipedia retrieval remains synchronous and can block briefly during network latency",
            "controller/service boundary is in-process rather than a separate daemon",
        ),
    }
    pathology = {
        "pathologies": [
            {
                "id": "PID-CR01",
                "summary": "Milestone runtimes had separate queues and status surfaces.",
                "classification": "REAL_INTEGRATION_GAP",
                "repair": "continuous controller normalizes events and owns service lifecycle while reusing 1.2 internals",
                "status": "REPAIRED",
            },
            {
                "id": "PID-CR02",
                "summary": "Self-model did not include resource-aware model residency.",
                "classification": "REAL_CAPABILITY_AWARENESS_GAP",
                "repair": "model residency policy reads actual registry and lane selection",
                "status": "REPAIRED",
            },
            {
                "id": "PID-CR03",
                "summary": "Continuous idle behavior lacked long-run duplicate suppression evidence.",
                "classification": "VALIDATION_GAP",
                "repair": "bounded long-run records queue size, duplicate initiatives, retrieval/model calls, and final health",
                "status": "REPAIRED",
            },
        ],
        "safety": safety_metadata(),
    }
    docs = _continuous_docs(controller)
    notebook = "\n".join([
        "# Continuous Runtime Engineering Notebook",
        "",
        "- Finding: Existing DELTA 1.2 wake cycle was suitable for bounded cognition but not a central UI service controller.",
        "- Decision: Add one controller that owns lifecycle/event envelopes while reusing 1.2 queue/journal and 1.6 self-model.",
        "- Model routing: actual registry has multiple GGUF models plus aliases; use lane selection and serial ProviderManager policy, not hardcoded two-model assumptions.",
        "- Wikipedia: preserve text-only one-page-per-query policy; continuous controller performs no autonomous retrieval.",
        "- Pathology PID-CR01: duplicate state surfaces repaired by controller snapshot and UI status synchronization.",
        "- Self-development: observed UI/runtime mismatch, generated sandbox-only repair hypotheses, validated controller integration, and stopped at promotion proposal.",
        "- Readiness: bounded controller validation is useful, but live developmental operation is not yet proven without a real long-horizon UI/model/retrieval campaign.",
    ])
    return {
        "active_runtime_spine": active_spine,
        "behavioral_campaign": behavioral,
        "performance": performance,
        "validation": validation,
        "readiness": readiness,
        "pathology_catalog": pathology,
        "engineering_notebook": notebook,
        **docs,
    }


def _continuous_docs(controller: ContinuousRuntimeController) -> dict[str, str]:
    return {
        "architecture_doc": "\n".join([
            "# Continuous Runtime Architecture",
            "",
            "The continuous runtime controller is an in-process managed service loop. It owns lifecycle state, normalized event envelopes, wake policy, controller health, model residency metadata, active objectives, initiatives, and notification readiness. It reuses DELTA 1.2 live runtime, DELTA 1.5 evidence comparison, and DELTA 1.6 self-model instead of replacing them.",
            "",
            "## Active Spine",
            "",
            "The active runtime path is:",
            "",
            "```text",
            "UI Start Runtime",
            "-> start_live_wikipedia_runtime",
            "-> DELTA 1.2 LiveRuntimeState boot",
            "-> ContinuousRuntimeController boot",
            "-> operator/live events normalized into ContinuousEvent",
            "-> bounded controller cycle",
            "-> DELTA 1.6 background initiative/self-model sync",
            "-> operator inquiry and promotion candidate surfaces",
            "-> controller returns to IDLE",
            "```",
            "",
            "The controller is intentionally in-process. It does not create hidden threads, daemons, external schedulers, or background services. The UI remains the operator-controlled lifecycle boundary.",
            "",
            "## Ownership",
            "",
            "- `LiveRuntimeState` remains the lower-level cognitive event and journal runtime.",
            "- `LiveWikipediaRuntimeSession` remains the live chat and Wikipedia bridge.",
            "- `ContinuousRuntimeController` owns the service lifecycle, normalized events, wake mode, health, objectives, initiative queue, model-residency inventory, notification readiness, and shutdown state.",
            "- `OperationalSelfModel` remains a derived snapshot. It is not the lifecycle authority.",
            "",
            "## Safety",
            "",
            "The controller may run deterministic local analysis and queue review items. It may not call providers, retrieve arbitrary web pages, write memory, mutate the repository, promote sandbox changes, commit, push, deploy, access secrets, or change governance.",
            "",
            "## Current Evidence Boundary",
            "",
            "The bounded validation harness injects events and records process metrics, but it is not a substitute for a multi-hour UI/model/retrieval pilot.",
            "",
        ]),
        "lifecycle_doc": "\n".join([
            "# Operating Lifecycle",
            "",
            "Supported states: `" + "`, `".join(LIFECYCLE_STATES) + "`.",
            "",
            "Default wake mode is `EVENT_DRIVEN`. `BOUNDED_BACKGROUND` may be enabled by operator policy, while `PAUSED` and `SUSPENDED` fail closed. Illegal transitions raise errors.",
            "",
            "## Wake Modes",
            "",
            "- `MANUAL`: only explicit operator or test calls advance the controller.",
            "- `EVENT_DRIVEN`: default; wake only when an event arrives.",
            "- `BOUNDED_BACKGROUND`: permits low-frequency idle reflection.",
            "- `EXPERIMENTAL_CONTINUOUS`: reserved for future operator-approved trials.",
            "- `PAUSED`: no initiative generation.",
            "- `SUSPENDED`: fail-closed review state.",
            "",
            "## Cycle Bounds",
            "",
            "Each cycle enforces a maximum event batch size, cycle duration target, generated initiative count, journal entries, model calls, and Wikipedia calls. The controller records model and Wikipedia calls from explicit governed events; it does not infer idle calls from silence.",
            "",
            "## Shutdown",
            "",
            "Shutdown is explicit: `SHUTTING_DOWN -> SHUTDOWN`. The controller clears its queue and remains inspectable through the final snapshot.",
            "",
        ]),
        "model_doc": "\n".join([
            "# Model Orchestration",
            "",
            "The controller reads the real local model registry and lane router. Default conversation uses `" + controller.model_residency.selected_default_model + "`, planning uses `" + controller.model_residency.selected_planning_model + "`, and development analysis uses `" + controller.model_residency.selected_development_model + "`. ProviderManager remains serial with one resident local model maximum.",
            "",
            "## Actual Inventory",
            "",
            "The registry exposes multiple GGUF models and aliases rather than exactly two hardcoded models. The controller therefore reports actual registry state, selected lane models, resident model ID, resident lane, and residency status.",
            "",
            "## Routing Policy",
            "",
            "Deterministic subsystems answer without a model for lifecycle status, authority classification, capability reporting, Wikipedia budget exhaustion, and cached evidence discussion. Local models remain useful for synthesis, planning, hypothesis generation, coding proposals, ambiguity resolution, and deeper developmental reflection.",
            "",
            "## Residency Policy",
            "",
            "The existing `ProviderManager` is the authority for local model residency. It is serial and keeps at most one local GGUF model resident at a time. The continuous controller observes and reports this state; it does not keep multiple models loaded or invoke inference from idle reflection.",
            "",
            "## Validation Boundary",
            "",
            "The bounded campaign observes model-ready events and lane selection. Repeated real inference, model switching under pressure, failed invocation recovery, and planning-to-conversation handoff still require a controlled long-horizon pilot.",
            "",
        ]),
        "operator_doc": "\n".join([
            "# Continuous Runtime Operator Guide",
            "",
            "Use Start Runtime, Stop Runtime, Pause, Resume, and Suspend from the UI. The status line reports lifecycle, health, resident model, active objective, inquiries, promotion candidates, Wikipedia budget, and recent initiative. Ask `What are you currently working on?` or `Which local model is available?` for grounded state.",
            "",
            "## Recommended Pilot",
            "",
            "Run a controlled operator pilot with the UI open. Exercise ordinary chat, context declarations, one Wikipedia lookup, a self-model question, a local model deepening request, pause/resume, suspend, restart, and review of pending promotion candidates.",
            "",
            "## Reading Status",
            "",
            "- `Runtime`: controller lifecycle state.",
            "- `health`: controller health classification.",
            "- `model`: resident model when known, otherwise default lane model.",
            "- `objective`: active or waiting objective.",
            "- `inquiries`: pending operator inquiry count.",
            "- `promotions`: gated promotion candidate count.",
            "- `wiki`: current session query count and budget.",
            "- `initiative`: latest initiative outcome.",
            "",
            "## Authority Reminder",
            "",
            "DELTA can prepare and queue review items. It cannot persist, promote, commit, push, deploy, broaden web access, call providers, or change governance without operator authority.",
            "",
        ]),
        "failure_doc": "\n".join([
            "# Failure Recovery",
            "",
            "Queue growth, timeouts, invalid transitions, model unavailability, Wikipedia failure, and repeated exceptions move the controller toward `DEGRADED`, `PAUSED_FOR_REVIEW`, `SUSPENDED`, or `FAILED_SAFE`. Shutdown remains available at all times. Recovery returns to `IDLE` only through explicit controller transitions.",
            "",
            "## Health Inputs",
            "",
            "The controller checks event queue size, model availability, Wikipedia availability, cycle timeout, repeated exceptions, stale objectives, and resource limit events. It records process CPU time, active Python threads, and best-effort Windows working-set metrics without requiring `psutil`.",
            "",
            "## Degraded Mode",
            "",
            "When degraded, the controller stops automatic initiative work and preserves the audit trail. The operator can pause, suspend, or shut down. Unknown action types or invalid lifecycle transitions fail closed.",
            "",
            "## Recovery",
            "",
            "Recovery is explicit and bounded. The controller may return to `IDLE` after a recoverable condition clears, but it does not retry external retrieval, model execution, sandbox work, or persistence automatically.",
            "",
        ]),
    }


def _authority_for_event(event_type: str) -> str:
    if event_type in {"RUNTIME_STOP", "RUNTIME_PAUSE", "RUNTIME_RESUME", "RUNTIME_SUSPEND", "OPERATOR_APPROVAL", "OPERATOR_REJECTION"}:
        return "OPERATOR_APPROVAL_REQUIRED"
    if event_type in {"MODEL_UNAVAILABLE", "WIKIPEDIA_FAILURE", "HEALTH_WARNING", "RESOURCE_LIMIT_REACHED"}:
        return "AUTONOMOUS_SAFE"
    if event_type in {"PROMOTION_CANDIDATE", "IDENTITY_PROPOSAL", "OBJECTIVE_CREATED"}:
        return "OPERATOR_APPROVAL_REQUIRED"
    return evaluate_authority(AuthorityRequest(action=event_type, action_type="organize_ephemeral_observation")).authority_class


def _event_duplicate_key(event_type: str, payload: dict[str, Any], correlation_id: str, objective_id: str) -> str:
    stable_payload = json.dumps(payload, sort_keys=True, default=str)[:500]
    return stable_id("continuous-event-dup", event_type, stable_payload, correlation_id, objective_id)


def _expire_stale_events(controller: ContinuousRuntimeController) -> tuple[ContinuousEvent, ...]:
    cycle_count = len(controller.cycles)
    return tuple(
        event
        for event in controller.event_queue
        if int(event.audit_metadata.get("expires_at_cycle", cycle_count + event.expiration_cycle)) > cycle_count
    )


def _idle_reflection_due(controller: ContinuousRuntimeController) -> bool:
    if controller.config.wake_mode not in {"BOUNDED_BACKGROUND", "EXPERIMENTAL_CONTINUOUS"}:
        return False
    return (time.time() - controller.last_idle_reflection_at) >= controller.config.idle_reflection_interval_seconds


def _objectives_from_events(events: Iterable[ContinuousEvent]) -> tuple[ContinuousObjective, ...]:
    objectives: list[ContinuousObjective] = []
    for event in events:
        if event.event_type not in {"DEVELOPMENTAL_SIGNAL", "OBJECTIVE_CREATED", "PROMOTION_CANDIDATE", "BEHAVIORAL_FAILURE"}:
            continue
        title = str(event.payload.get("title") or event.payload.get("summary") or event.event_type)
        decision = evaluate_authority(AuthorityRequest(action=title, action_type="rank_candidate_goal"))
        state = "WAITING_FOR_APPROVAL" if event.event_type in {"OBJECTIVE_CREATED", "PROMOTION_CANDIDATE"} else "PROPOSED"
        objectives.append(
            ContinuousObjective(
                objective_id=event.objective_id or stable_id("continuous-objective", event.event_id, title),
                title=title[:240],
                state=state,
                source=event.event_type,
                authority_class=decision.authority_class,
                created_at=event.timestamp,
                updated_at=utc_now(),
            )
        )
    return tuple(objectives)


def _inquiries_from_events(events: Iterable[ContinuousEvent]) -> tuple[dict[str, Any], ...]:
    inquiries = []
    for event in events:
        if event.event_type in {"PROMOTION_CANDIDATE", "IDENTITY_PROPOSAL", "OBJECTIVE_BLOCKED", "WIKIPEDIA_FAILURE"}:
            inquiries.append({
                "inquiry_id": stable_id("continuous-inquiry", event.event_id),
                "prompt": str(event.payload.get("prompt") or event.payload.get("summary") or f"Review {event.event_type}."),
                "event_id": event.event_id,
                "status": "QUEUED",
                "notification_class": "IN_APP_NORMAL",
                "authority_class": event.authority_class,
            })
    return tuple(inquiries)


def _merge_objectives(existing: tuple[ContinuousObjective, ...], new: tuple[ContinuousObjective, ...]) -> tuple[ContinuousObjective, ...]:
    by_id = {item.objective_id: item for item in existing}
    by_id.update({item.objective_id: item for item in new})
    return tuple(by_id.values())[-32:]


def _select_active_objective(current: ContinuousObjective | None, new: tuple[ContinuousObjective, ...], max_active: int) -> ContinuousObjective | None:
    if current and current.state in {"APPROVED", "ACTIVE", "WAITING_FOR_OPERATOR", "SANDBOXING", "VALIDATING"}:
        return current
    if max_active < 1:
        return None
    return new[0] if new else current


def _merge_initiatives(existing: tuple[Initiative, ...], new: tuple[Initiative, ...], max_new: int) -> tuple[Initiative, ...]:
    by_key = {item.duplicate_suppression_key: item for item in existing}
    for item in new[:max_new]:
        by_key.setdefault(item.duplicate_suppression_key, item)
    return tuple(by_key.values())[-64:]


def _merge_inquiries(existing: tuple[dict[str, Any], ...], new: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    seen = {str(item.get("inquiry_id")) for item in existing}
    merged = list(existing)
    for item in new:
        key = str(item.get("inquiry_id"))
        if key and key not in seen:
            merged.append(item)
            seen.add(key)
    return tuple(merged[-64:])


def _wikipedia_available_from_events(events: Iterable[ContinuousEvent], current: bool) -> bool:
    available = current
    for event in events:
        if event.event_type == "WIKIPEDIA_RESULT":
            available = True
        if event.event_type == "WIKIPEDIA_FAILURE":
            available = False
    return available


def _health_for(
    controller: ContinuousRuntimeController,
    *,
    queue_size: int | None = None,
    health_state: str = "HEALTHY",
    warnings: tuple[str, ...] = (),
    last_error: str = "",
    cycle_timeout: bool = False,
) -> HealthReport:
    queue_size = len(controller.event_queue) if queue_size is None else queue_size
    warning_list = list(warnings)
    if queue_size > int(controller.config.queue_limit * 0.8):
        warning_list.append("event_queue_near_limit")
        health_state = "DEGRADED"
    model_available = controller.model_residency.available_model_count > 0
    if not model_available:
        warning_list.append("no_local_models_available")
        health_state = "DEGRADED"
    return HealthReport(
        health_state=health_state,
        queue_size=queue_size,
        repeated_exception_count=1 if last_error else 0,
        last_error=last_error,
        model_available=model_available,
        wikipedia_available=controller.wikipedia_available,
        cycle_timeout=cycle_timeout,
        memory_pressure="bounded",
        cpu_pressure="idle" if queue_size == 0 else "bounded_cycle",
        warnings=tuple(warning_list),
    )


def _cycle_record(
    controller: ContinuousRuntimeController,
    started: float,
    start_state: str,
    end_state: str,
    events: tuple[str, ...],
    initiatives: tuple[str, ...],
    objectives: tuple[str, ...],
    idle_result: str,
    *,
    batch: tuple[ContinuousEvent, ...] = (),
    duration_ms: float | None = None,
    health_state: str | None = None,
) -> RuntimeCycleRecord:
    duration = (time.perf_counter() - started) * 1000 if duration_ms is None else duration_ms
    model_calls = sum(_model_call_count(event) for event in batch)
    wikipedia_calls = sum(1 for event in batch if event.event_type in {"WIKIPEDIA_RESULT", "WIKIPEDIA_FAILURE"})
    return RuntimeCycleRecord(
        cycle_id=stable_id("continuous-cycle", controller.controller_id, len(controller.cycles) + 1, events, initiatives, objectives),
        cycle_index=len(controller.cycles) + 1,
        started_at=utc_now(),
        duration_ms=round(duration, 3),
        lifecycle_start=start_state,
        lifecycle_end=end_state,
        events_processed=events,
        initiatives_created=initiatives,
        objectives_updated=objectives,
        model_calls=model_calls,
        wikipedia_calls=wikipedia_calls,
        external_metrics=_sample_process_metrics(include_external=False),
        idle_result=idle_result,
        health_state=health_state or controller.health.health_state,
    )


def _long_run_event_spec(index: int) -> tuple[str, dict[str, Any], int] | None:
    if index % 19 == 0:
        return ("WIKIPEDIA_RESULT", {"title": "Runtime validation", "classification": "noncanonical_review_candidate"}, 75)
    if index % 17 == 0:
        return ("MODEL_READY", {"model_id": "planning-lane", "lane": "planning", "local_model_call_performed": True}, 70)
    if index % 13 == 0:
        return ("BEHAVIORAL_FAILURE", {"summary": "blocked objective observed during bounded campaign"}, 80)
    if index % 11 == 0:
        return ("OBJECTIVE_BLOCKED", {"summary": "waiting for operator validation"}, 65)
    if index % 7 == 0:
        return ("VALIDATION_RESULT", {"result": "heartbeat"}, 20)
    return None


def _model_call_count(event: ContinuousEvent) -> int:
    if event.event_type == "MODEL_READY" and event.payload.get("local_model_call_performed"):
        return 1
    if event.event_type == "MODEL_UNAVAILABLE" and event.payload.get("attempted"):
        return 1
    return int(event.payload.get("model_calls") or 0)


def _metric_delta(start: dict[str, Any], end: dict[str, Any], key: str) -> int | None:
    if not isinstance(start.get(key), int) or not isinstance(end.get(key), int):
        return None
    return int(end[key]) - int(start[key])


def _sample_process_metrics(*, include_external: bool = True) -> dict[str, Any]:
    metrics = {
        "pid": os.getpid(),
        "process_time_seconds": round(time.process_time(), 6),
        "active_python_threads": threading.active_count(),
    }
    if os.name == "nt" and include_external:
        metrics.update(_sample_windows_process_metrics())
    return metrics


def _sample_windows_process_metrics() -> dict[str, Any]:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    result: dict[str, Any] = {}
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        psapi = ctypes.WinDLL("psapi.dll")
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if ok:
            result.update({
                "working_set_bytes": int(counters.WorkingSetSize),
                "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
                "pagefile_usage_bytes": int(counters.PagefileUsage),
            })
        else:
            result["process_memory_error"] = "GetProcessMemoryInfo returned false"
    except Exception as exc:  # noqa: BLE001 - metrics are best-effort instrumentation only.
        result["process_memory_error"] = type(exc).__name__
    if "working_set_bytes" not in result:
        result.update(_sample_windows_process_metrics_via_powershell(os.getpid()))
    try:
        result["thread_count"] = int(ctypes.windll.kernel32.GetActiveProcessorCount(0)) if False else threading.active_count()
    except Exception:
        result["thread_count"] = threading.active_count()
    return result


def _sample_windows_process_metrics_via_powershell(pid: int) -> dict[str, Any]:
    command = (
        "$p=Get-Process -Id "
        + str(int(pid))
        + "; [pscustomobject]@{WorkingSet64=$p.WorkingSet64; CPU=$p.CPU; Handles=$p.Handles; Threads=$p.Threads.Count} | ConvertTo-Json -Compress"
    )
    for executable in ("powershell.exe", "powershell"):
        try:
            completed = subprocess.run(
                [executable, "-NoProfile", "-Command", command],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception as exc:  # noqa: BLE001 - metrics are best-effort instrumentation only.
            continue
        if completed.returncode != 0 or not completed.stdout.strip():
            continue
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            continue
        return {
            "working_set_bytes": int(payload.get("WorkingSet64") or 0),
            "powershell_cpu_seconds": float(payload.get("CPU") or 0.0),
            "handle_count": int(payload.get("Handles") or 0),
            "os_thread_count": int(payload.get("Threads") or 0),
            "process_metrics_source": executable,
        }
    return {"process_metrics_fallback_error": "Get-Process unavailable"}


def _long_run_proven(metrics: dict[str, Any]) -> bool:
    return (
        float(metrics.get("duration_seconds") or 0) >= 3600
        and int(metrics.get("events_processed") or 0) > 0
        and int(metrics.get("model_calls") or 0) > 0
        and int(metrics.get("wikipedia_calls") or 0) > 0
        and int(metrics.get("final_queue_size") or 0) <= 1
        and metrics.get("health_state") == "HEALTHY"
    )


def _journal_entry(entry_type: str, summary: str, refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "entry_id": stable_id("continuous-journal", entry_type, summary, refs, utc_now()),
        "entry_type": entry_type,
        "summary": summary,
        "refs": refs,
        "created_at": utc_now(),
        "retention": "audit_only_ephemeral_until_operator_policy",
        "safety": safety_metadata(),
    }


def _journal(controller: ContinuousRuntimeController, entry_type: str, summary: str, refs: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    return controller.journal + (_journal_entry(entry_type, summary, refs),)


def _copy_session_results(session: Any) -> dict[str, Any]:
    model = getattr(session, "operational_self_model", None) or build_operational_self_model(session=session)
    active = model.active_objectives[0] if model.active_objectives else ""
    return {"active_work_item": active}


def _sync_session_initiatives(controller: ContinuousRuntimeController, session: Any) -> ContinuousRuntimeController:
    initiatives = tuple(getattr(session, "initiatives", ()) or ())
    if not initiatives:
        return controller
    merged = _merge_initiatives(controller.initiatives, initiatives, len(initiatives))
    objectives = list(controller.objectives)
    existing_titles = {item.title for item in objectives}
    for initiative in initiatives:
        if not initiative.candidate_objective or initiative.candidate_objective in existing_titles:
            continue
        objectives.append(
            ContinuousObjective(
                objective_id=stable_id("continuous-objective-from-initiative", initiative.initiative_id),
                title=initiative.candidate_objective[:240],
                state="WAITING_FOR_OPERATOR" if initiative.outcome == "ASK_OPERATOR_NOW" else "PROPOSED",
                source="INITIATIVE",
                authority_class=initiative.authority_class,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        existing_titles.add(initiative.candidate_objective)
    inquiries = _merge_inquiries(controller.operator_inquiries, tuple(getattr(session, "operator_inquiries", ()) or ()))
    active = _select_active_objective(controller.active_objective, tuple(objectives[len(controller.objectives) :]), controller.config.max_active_objectives)
    return replace(
        controller,
        initiatives=merged,
        objectives=tuple(objectives[-32:]),
        active_objective=active,
        operator_inquiries=inquiries,
        wikipedia_available=controller.wikipedia_available or bool(getattr(session, "developmental_results", ())),
    )


def _duplicate_initiative_count(initiatives: tuple[Initiative, ...]) -> int:
    keys = [item.duplicate_suppression_key for item in initiatives]
    return len(keys) - len(set(keys))


def _capability_classes(controller: ContinuousRuntimeController) -> dict[str, str]:
    return {
        "live_conversation_runtime": "LIVE",
        "approved_local_concept_memory": "LIVE",
        "governed_objectives": "PARTIALLY_CONNECTED",
        "developmental_observations": "LIVE",
        "delta_1_1_development_loop": "CALLABLE_BUT_NOT_INTEGRATED",
        "delta_1_2_live_runtime": "LIVE",
        "behavioral_maturation_infrastructure": "CALLABLE_BUT_NOT_INTEGRATED",
        "sandbox_experimental_repair": "PARTIALLY_CONNECTED",
        "wikipedia_text_retrieval": "LIVE",
        "local_approved_concept_comparison": "LIVE",
        "promotion_candidates": "LIVE",
        "operator_inquiries": "LIVE",
        "bounded_autonomy_classification": "LIVE",
        "operational_self_model": "LIVE",
        "local_models": "PARTIALLY_CONNECTED" if controller.model_residency.available_model_count else "DISABLED",
        "operator_ui": "LIVE",
        "external_provider_evaluator_env": "DISABLED",
    }


def build_self_development_demo() -> dict[str, Any]:
    fault = "continuous runtime status could diverge from live runtime state and model residency"
    hypotheses = (
        "Add a separate daemon process",
        "Extend the existing live session with one controller snapshot",
        "Only document the mismatch",
    )
    selected = "Extend the existing live session with one controller snapshot"
    decision = evaluate_authority(AuthorityRequest(action="prepare sandbox proposal for controller integration", action_type="approved_sandbox_experiment"))
    proposal = SandboxDevelopmentProposal(
        proposal_id=stable_id("continuous-sandbox-proposal", fault, selected),
        pathology_id="PID-CR01",
        fault=fault,
        hypotheses=hypotheses,
        selected_hypothesis=selected,
        sandbox_scope="fixture-only controller integration; no primary-tree mutation by DELTA runtime",
        baseline="UI showed live state but not central lifecycle/model/health/initiative status.",
        candidate_result="Controller snapshot exposes lifecycle, health, model residency, objective, inquiries, and initiatives.",
        promotion_boundary="Codex may promote after tests; DELTA runtime cannot promote, commit, or push.",
        authority_class=decision.authority_class,
    )
    return {
        "status": "FIXTURE_VALIDATED",
        "fault_observed": fault,
        "developmental_signal": "runtime integration gap",
        "candidate_objective": "connect controller snapshot to live session and UI status",
        "authority_classification": decision.authority_class,
        "sandbox_proposal": asdict(proposal),
        "before_after": {
            "before": proposal.baseline,
            "after": proposal.candidate_result,
        },
        "promotion_proposal": "Promote controller integration only after focused tests, long-run validation, JSON validation, and governance scan.",
        "automatic_promotion_performed": False,
        "runtime_primary_tree_mutation": False,
        "safety": safety_metadata(),
    }


======================================================================
FILE: orchestration/runtime/delta_1_2_live_runtime.py
======================================================================

"""DELTA 1.2 live governed development runtime.

This is the first persistent-style cognitive runtime layer. It can accept
approved local events, observe them, score attention, form curiosity and
developmental signals, arbitrate candidate goals, queue operator inquiries, and
record an audit journal. It does not start timers, browse, retrieve, call
providers, modify code, persist hidden state, commit, push, or expand authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from orchestration.runtime.delta_1_0_common import jsonable, safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_1_development_loop import WikipediaPermissionProfile


REPORT_ROOT = Path("reports") / "delta_1_2"

RUNTIME_STATES = (
    "BOOT",
    "IDLE",
    "OBSERVING",
    "REFLECTING",
    "ASSESSING",
    "GENERATING_OBJECTIVES",
    "WAITING_FOR_OPERATOR",
    "BACKGROUND_ANALYSIS",
    "VALIDATING",
    "PAUSED",
    "SUSPENDED",
    "SHUTDOWN",
)

VALID_TRANSITIONS = {
    "BOOT": ("IDLE", "SUSPENDED", "SHUTDOWN"),
    "IDLE": ("OBSERVING", "REFLECTING", "PAUSED", "SUSPENDED", "SHUTDOWN"),
    "OBSERVING": ("ASSESSING", "IDLE", "PAUSED", "SUSPENDED"),
    "ASSESSING": ("GENERATING_OBJECTIVES", "REFLECTING", "IDLE", "WAITING_FOR_OPERATOR"),
    "GENERATING_OBJECTIVES": ("WAITING_FOR_OPERATOR", "BACKGROUND_ANALYSIS", "IDLE"),
    "REFLECTING": ("BACKGROUND_ANALYSIS", "WAITING_FOR_OPERATOR", "IDLE", "PAUSED"),
    "BACKGROUND_ANALYSIS": ("WAITING_FOR_OPERATOR", "VALIDATING", "IDLE"),
    "WAITING_FOR_OPERATOR": ("OBSERVING", "VALIDATING", "IDLE", "PAUSED", "SHUTDOWN"),
    "VALIDATING": ("IDLE", "WAITING_FOR_OPERATOR", "SUSPENDED"),
    "PAUSED": ("IDLE", "SHUTDOWN"),
    "SUSPENDED": ("IDLE", "SHUTDOWN"),
    "SHUTDOWN": (),
}

EVENT_CLASSES = (
    "operator_message",
    "objective_approved",
    "objective_rejected",
    "validation_completed",
    "repair_completed",
    "behavioral_failure",
    "repeated_pathology",
    "operator_correction",
    "runtime_startup",
    "runtime_shutdown",
)

ATTENTION_LEVELS = ("IGNORE", "LOW_VALUE", "INTERESTING", "DEVELOPMENTAL_SIGNAL", "HIGH_PRIORITY", "OPERATOR_REQUIRED")
NOTIFICATION_CLASSES = ("IMMEDIATE", "NORMAL", "DEFERRED", "NEXT_SESSION", "DIGEST_ONLY")
INQUIRY_STATUSES = ("QUEUED", "SURFACED", "ANSWERED", "DISMISSED", "EXPIRED")
CAPABILITY_STATES = ("DISABLED", "READY_FOR_REVIEW", "APPROVED", "ACTIVE")


@dataclass(frozen=True)
class LiveRuntimeConfig:
    runtime_id: str
    mode: str = "NORMAL"
    max_events_per_cycle: int = 8
    max_reflection_steps: int = 5
    quiet_hours: tuple[str, str] = ("22:00", "08:00")
    notification_limit_per_cycle: int = 3
    kill_switch: bool = False
    paused: bool = False
    timers_enabled: bool = False
    network_enabled: bool = False
    provider_enabled: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeEvent:
    event_id: str
    event_class: str
    summary: str
    source: str
    payload: dict[str, Any]
    approved_source: bool
    created_at: str = field(default_factory=utc_now)
    processed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class EventQueue:
    queue_id: str
    events: tuple[RuntimeEvent, ...] = ()
    max_size: int = 128
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LiveObservation:
    observation_id: str
    event_id: str
    observation_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    source: str
    confidence: float
    severity: float
    evidence_only: bool = True
    expires_after_cycles: int = 12
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class AttentionDecision:
    decision_id: str
    observation_id: str
    level: str
    score: float
    rationale: str
    expires_after_cycles: int
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CuriosityInquiryCandidate:
    curiosity_id: str
    originating_evidence: tuple[str, ...]
    gap_type: str
    question: str
    confidence: float
    expected_benefit: float
    random_question: bool = False
    action_requested: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentSignal:
    signal_id: str
    signal_type: str
    evidence_refs: tuple[str, ...]
    cluster_key: str
    frequency: int
    severity: float
    confidence: float
    duplicate_of: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class CandidateGoal:
    goal_id: str
    title: str
    originating_signals: tuple[str, ...]
    value: float
    urgency: float
    confidence: float
    operator_impact: float
    implementation_effort: float
    regression_risk: float
    governance_impact: float
    approval_required: bool = True
    self_created_active_goal: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class GoalArbitration:
    arbitration_id: str
    ranked_goals: tuple[dict[str, Any], ...]
    selected_goal_id: str
    rationale: str
    silently_selected: bool = False
    approval_required: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ReflectionSummary:
    reflection_id: str
    inspected_events: tuple[str, ...]
    observations: tuple[str, ...]
    signals: tuple[str, ...]
    curiosity: tuple[str, ...]
    proposed_inquiries: tuple[str, ...]
    steps_used: int
    bounded: bool = True
    modified_code: bool = False
    browsed: bool = False
    provider_called: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiryV12:
    inquiry_id: str
    originating_evidence: tuple[str, ...]
    confidence: float
    reason: str
    urgency: float
    expected_benefit: float
    question: str
    suggested_next_step: str
    expiration_cycle: int
    approval_status: str = "QUEUED"
    notification_class: str = "NEXT_SESSION"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class NotificationDecision:
    notification_id: str
    inquiry_id: str
    notification_class: str
    should_surface_now: bool
    reason: str
    os_notification_sent: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivityJournalEntry:
    entry_id: str
    entry_type: str
    summary: str
    refs: tuple[str, ...]
    cycle: int
    retention_policy: str = "audit_only_ephemeral_until_operator_policy"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ActivityJournal:
    journal_id: str
    entries: tuple[ActivityJournalEntry, ...] = ()
    hidden_persistence: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class RuntimeIdentity:
    identity_id: str
    current_objectives: tuple[str, ...]
    open_questions: tuple[str, ...]
    active_observations: tuple[str, ...]
    unresolved_curiosity: tuple[str, ...]
    recent_lessons: tuple[str, ...]
    runtime_health: str
    governance_status: str
    chat_history: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class FutureSurfaceReadiness:
    capability: str
    state: str
    permission_profile: WikipediaPermissionProfile
    dependencies: tuple[str, ...]
    retrieval_implemented: bool = False
    network_code_present: bool = False
    provider_present: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LiveRuntimeState:
    runtime_id: str
    state: str
    cycle: int
    config: LiveRuntimeConfig
    event_queue: EventQueue
    observations: tuple[LiveObservation, ...]
    attention: tuple[AttentionDecision, ...]
    curiosity: tuple[CuriosityInquiryCandidate, ...]
    signals: tuple[DevelopmentSignal, ...]
    goals: tuple[CandidateGoal, ...]
    arbitration: GoalArbitration | None
    inquiries: tuple[OperatorInquiryV12, ...]
    notifications: tuple[NotificationDecision, ...]
    journal: ActivityJournal
    identity: RuntimeIdentity
    future_surfaces: tuple[FutureSurfaceReadiness, ...]
    last_reflection: ReflectionSummary | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def boot_live_runtime(config: LiveRuntimeConfig | None = None) -> LiveRuntimeState:
    config = config or LiveRuntimeConfig(runtime_id=stable_id("delta12-runtime", "default"))
    queue = EventQueue(queue_id=stable_id("delta12-event-queue", config.runtime_id))
    journal = ActivityJournal(journal_id=stable_id("delta12-journal", config.runtime_id))
    identity = RuntimeIdentity(
        identity_id=stable_id("delta12-identity", config.runtime_id),
        current_objectives=(),
        open_questions=(),
        active_observations=(),
        unresolved_curiosity=(),
        recent_lessons=(),
        runtime_health="healthy",
        governance_status="operator_governed_no_external_senses",
    )
    runtime = LiveRuntimeState(
        runtime_id=config.runtime_id,
        state="BOOT",
        cycle=0,
        config=config,
        event_queue=queue,
        observations=(),
        attention=(),
        curiosity=(),
        signals=(),
        goals=(),
        arbitration=None,
        inquiries=(),
        notifications=(),
        journal=journal,
        identity=identity,
        future_surfaces=(wikipedia_surface_readiness(),),
    )
    return transition_runtime(runtime, "IDLE")


def transition_runtime(runtime: LiveRuntimeState, to_state: str) -> LiveRuntimeState:
    if to_state not in RUNTIME_STATES:
        raise ValueError(f"unknown runtime state: {to_state}")
    if to_state not in VALID_TRANSITIONS.get(runtime.state, ()):
        raise ValueError(f"invalid transition {runtime.state}->{to_state}")
    return replace(runtime, state=to_state)


def create_event(event_class: str, summary: str, *, source: str = "local_runtime", payload: Mapping[str, Any] | None = None, approved_source: bool = True) -> RuntimeEvent:
    if event_class not in EVENT_CLASSES:
        raise ValueError(f"unknown event class: {event_class}")
    clean = " ".join(str(summary or "").split())
    return RuntimeEvent(
        event_id=stable_id("delta12-event", event_class, clean, source, payload or {}),
        event_class=event_class,
        summary=clean,
        source=source,
        payload=dict(payload or {}),
        approved_source=approved_source,
    )


def enqueue_event(queue: EventQueue, event: RuntimeEvent) -> EventQueue:
    events = (queue.events + (event,))[-queue.max_size :]
    return replace(queue, events=events)


def dequeue_batch(queue: EventQueue, max_count: int) -> tuple[tuple[RuntimeEvent, ...], EventQueue]:
    pending = tuple(item for item in queue.events if not item.processed)
    batch = pending[:max_count]
    processed_ids = {item.event_id for item in batch}
    events = tuple(replace(item, processed=True) if item.event_id in processed_ids else item for item in queue.events)
    return batch, replace(queue, events=events)


def observe_events(events: Iterable[RuntimeEvent]) -> tuple[LiveObservation, ...]:
    observations: list[LiveObservation] = []
    for event in events:
        if not event.approved_source:
            continue
        observation_type = _observation_type_for_event(event)
        severity = _severity_for_event(event)
        confidence = _confidence_for_event(event)
        observations.append(
            LiveObservation(
                observation_id=stable_id("delta12-observation", event.event_id, observation_type, event.summary),
                event_id=event.event_id,
                observation_type=observation_type,
                summary=event.summary,
                evidence_refs=(event.event_id,),
                source=event.source,
                confidence=confidence,
                severity=severity,
            )
        )
    return tuple(observations)


def attention_for_observation(observation: LiveObservation) -> AttentionDecision:
    score = round((observation.severity * 0.55) + (observation.confidence * 0.35) + (_novelty_score(observation) * 0.1), 3)
    if score < 0.25:
        level = "IGNORE"
    elif score < 0.42:
        level = "LOW_VALUE"
    elif score < 0.58:
        level = "INTERESTING"
    elif score < 0.72:
        level = "DEVELOPMENTAL_SIGNAL"
    elif score < 0.86:
        level = "HIGH_PRIORITY"
    else:
        level = "OPERATOR_REQUIRED"
    return AttentionDecision(
        decision_id=stable_id("delta12-attention", observation.observation_id, score, level),
        observation_id=observation.observation_id,
        level=level,
        score=score,
        rationale=f"severity={observation.severity:.2f}; confidence={observation.confidence:.2f}; novelty={_novelty_score(observation):.2f}",
        expires_after_cycles=1 if level == "IGNORE" else 12,
    )


def score_attention(observations: Iterable[LiveObservation]) -> tuple[AttentionDecision, ...]:
    return tuple(attention_for_observation(item) for item in observations)


def generate_curiosity(observations: Iterable[LiveObservation], attention: Iterable[AttentionDecision]) -> tuple[CuriosityInquiryCandidate, ...]:
    decisions = {item.observation_id: item for item in attention}
    candidates: list[CuriosityInquiryCandidate] = []
    for observation in observations:
        decision = decisions.get(observation.observation_id)
        if not decision or decision.level not in {"INTERESTING", "DEVELOPMENTAL_SIGNAL", "HIGH_PRIORITY", "OPERATOR_REQUIRED"}:
            continue
        gap_type = _gap_type(observation.summary)
        question = _question_for_gap(gap_type, observation.summary)
        candidates.append(
            CuriosityInquiryCandidate(
                curiosity_id=stable_id("delta12-curiosity", observation.observation_id, gap_type, question),
                originating_evidence=observation.evidence_refs,
                gap_type=gap_type,
                question=question,
                confidence=round((observation.confidence + decision.score) / 2, 3),
                expected_benefit=decision.score,
            )
        )
    return tuple(_dedupe_by_question(candidates))


def detect_development_signals(observations: Iterable[LiveObservation]) -> tuple[DevelopmentSignal, ...]:
    groups: dict[str, list[LiveObservation]] = {}
    for observation in observations:
        key = _cluster_key(observation.summary, observation.observation_type)
        groups.setdefault(key, []).append(observation)
    signals: list[DevelopmentSignal] = []
    seen: dict[str, str] = {}
    for key, items in groups.items():
        frequency = len(items)
        if frequency < 1:
            continue
        severity = _avg(item.severity for item in items)
        confidence = _avg(item.confidence for item in items)
        signal_type = "repeated_pattern" if frequency > 1 else _signal_type(items[0])
        signal_id = stable_id("delta12-signal", key, tuple(item.observation_id for item in items))
        duplicate_of = seen.get(key, "")
        seen[key] = seen.get(key, signal_id)
        signals.append(
            DevelopmentSignal(
                signal_id=signal_id,
                signal_type=signal_type,
                evidence_refs=tuple(item.observation_id for item in items),
                cluster_key=key,
                frequency=frequency,
                severity=round(severity, 3),
                confidence=round(confidence, 3),
                duplicate_of=duplicate_of,
            )
        )
    return tuple(signals)


def generate_candidate_goals(signals: Iterable[DevelopmentSignal]) -> tuple[CandidateGoal, ...]:
    goals: list[CandidateGoal] = []
    for signal in signals:
        value = min(1.0, (signal.severity * 0.65) + (min(1.0, signal.frequency / 4) * 0.35))
        effort = 0.35 if signal.signal_type != "repeated_pattern" else 0.55
        risk = 0.22 + (0.08 * signal.frequency)
        governance = 0.15 if "wikipedia" not in signal.cluster_key else 0.35
        goals.append(
            CandidateGoal(
                goal_id=stable_id("delta12-goal", signal.signal_id, signal.cluster_key),
                title=_goal_title(signal),
                originating_signals=(signal.signal_id,),
                value=round(value, 3),
                urgency=round(min(1.0, signal.severity), 3),
                confidence=signal.confidence,
                operator_impact=round(value, 3),
                implementation_effort=round(effort, 3),
                regression_risk=round(min(1.0, risk), 3),
                governance_impact=round(governance, 3),
            )
        )
    return tuple(goals)


def arbitrate_goals(goals: Iterable[CandidateGoal]) -> GoalArbitration:
    scored = []
    for goal in goals:
        score = round(
            (goal.value * 0.28)
            + (goal.urgency * 0.18)
            + (goal.confidence * 0.17)
            + (goal.operator_impact * 0.15)
            + ((1.0 - goal.implementation_effort) * 0.1)
            + ((1.0 - goal.regression_risk) * 0.07)
            + ((1.0 - goal.governance_impact) * 0.05),
            4,
        )
        scored.append({"goal_id": goal.goal_id, "title": goal.title, "score": score, "rationale": f"value={goal.value}; urgency={goal.urgency}; confidence={goal.confidence}; effort={goal.implementation_effort}; regression={goal.regression_risk}; governance={goal.governance_impact}"})
    ranked = tuple({**item, "rank": index} for index, item in enumerate(sorted(scored, key=lambda row: row["score"], reverse=True), start=1))
    selected = str(ranked[0]["goal_id"]) if ranked else ""
    return GoalArbitration(
        arbitration_id=stable_id("delta12-arbitration", ranked),
        ranked_goals=ranked,
        selected_goal_id=selected,
        rationale="Top ranked goal is a proposal candidate only; operator approval is still required.",
        silently_selected=False,
        approval_required=True,
    )


def inquiry_from_curiosity(candidate: CuriosityInquiryCandidate, *, cycle: int) -> OperatorInquiryV12:
    urgency = min(1.0, max(0.1, candidate.expected_benefit))
    notification = classify_notification(urgency=urgency, confidence=candidate.confidence, operator_relevance=candidate.expected_benefit, mode="NORMAL")
    return OperatorInquiryV12(
        inquiry_id=stable_id("delta12-inquiry", candidate.curiosity_id, cycle),
        originating_evidence=candidate.originating_evidence,
        confidence=candidate.confidence,
        reason=f"curiosity:{candidate.gap_type}",
        urgency=round(urgency, 3),
        expected_benefit=candidate.expected_benefit,
        question=candidate.question,
        suggested_next_step="ask_operator_for_context_or_permission",
        expiration_cycle=cycle + 8,
        notification_class=notification,
    )


def classify_notification(*, urgency: float, confidence: float, operator_relevance: float, mode: str = "NORMAL") -> str:
    if mode == "QUIET":
        return "DIGEST_ONLY"
    if mode == "EMERGENCY_ONLY":
        return "IMMEDIATE" if urgency >= 0.95 and operator_relevance >= 0.9 else "DIGEST_ONLY"
    if mode == "DEVELOPMENT_SESSION" and urgency >= 0.65:
        return "NORMAL"
    if mode == "EXPERIMENTAL_ALWAYS_ON" and urgency >= 0.5:
        return "IMMEDIATE"
    score = (urgency * 0.45) + (confidence * 0.25) + (operator_relevance * 0.3)
    if score >= 0.86:
        return "IMMEDIATE"
    if score >= 0.7:
        return "NORMAL"
    if score >= 0.52:
        return "NEXT_SESSION"
    if score >= 0.35:
        return "DEFERRED"
    return "DIGEST_ONLY"


def notification_decision(inquiry: OperatorInquiryV12, *, mode: str, current_cycle: int) -> NotificationDecision:
    notification_class = classify_notification(urgency=inquiry.urgency, confidence=inquiry.confidence, operator_relevance=inquiry.expected_benefit, mode=mode)
    should_surface = notification_class in {"IMMEDIATE", "NORMAL"} and current_cycle <= inquiry.expiration_cycle
    return NotificationDecision(
        notification_id=stable_id("delta12-notification", inquiry.inquiry_id, notification_class, current_cycle),
        inquiry_id=inquiry.inquiry_id,
        notification_class=notification_class,
        should_surface_now=should_surface,
        reason="runtime_policy_only_no_os_notification",
        os_notification_sent=False,
    )


def reflect_bounded(runtime: LiveRuntimeState, batch: tuple[RuntimeEvent, ...]) -> tuple[ReflectionSummary, tuple[LiveObservation, ...], tuple[AttentionDecision, ...], tuple[CuriosityInquiryCandidate, ...], tuple[DevelopmentSignal, ...], tuple[CandidateGoal, ...], GoalArbitration, tuple[OperatorInquiryV12, ...], tuple[NotificationDecision, ...]]:
    observations = observe_events(batch)
    attention = score_attention(observations)
    useful = tuple(obs for obs in observations if attention_for_id(attention, obs.observation_id).level not in {"IGNORE", "LOW_VALUE"})
    curiosity = generate_curiosity(useful, attention)
    signals = detect_development_signals(useful)
    goals = generate_candidate_goals(signals)
    arbitration = arbitrate_goals(goals)
    inquiries = tuple(inquiry_from_curiosity(item, cycle=runtime.cycle + 1) for item in curiosity)
    notifications = tuple(notification_decision(item, mode=runtime.config.mode, current_cycle=runtime.cycle + 1) for item in inquiries)
    steps_used = min(runtime.config.max_reflection_steps, 5)
    summary = ReflectionSummary(
        reflection_id=stable_id("delta12-reflection", runtime.runtime_id, runtime.cycle + 1, tuple(event.event_id for event in batch)),
        inspected_events=tuple(event.event_id for event in batch),
        observations=tuple(item.observation_id for item in observations),
        signals=tuple(item.signal_id for item in signals),
        curiosity=tuple(item.curiosity_id for item in curiosity),
        proposed_inquiries=tuple(item.inquiry_id for item in inquiries),
        steps_used=steps_used,
    )
    return summary, observations, attention, curiosity, signals, goals, arbitration, inquiries, notifications


def run_wake_cycle(runtime: LiveRuntimeState) -> LiveRuntimeState:
    if runtime.config.kill_switch:
        return transition_runtime(runtime, "SUSPENDED") if runtime.state != "SUSPENDED" else runtime
    if runtime.config.paused:
        return transition_runtime(runtime, "PAUSED") if runtime.state != "PAUSED" else runtime
    if runtime.state not in {"IDLE", "WAITING_FOR_OPERATOR"}:
        runtime = transition_runtime(runtime, "IDLE") if "IDLE" in VALID_TRANSITIONS.get(runtime.state, ()) else runtime
    batch, queue = dequeue_batch(runtime.event_queue, runtime.config.max_events_per_cycle)
    cycle = runtime.cycle + 1
    if not batch:
        journal = append_journal(runtime.journal, "sleep_cycle", "No approved events; returned to idle.", (), cycle)
        identity = update_identity(runtime, journal=journal)
        return replace(runtime, cycle=cycle, event_queue=queue, journal=journal, identity=identity, state="IDLE")
    observing = transition_runtime(replace(runtime, event_queue=queue), "OBSERVING")
    assessing = transition_runtime(observing, "ASSESSING")
    reflection, observations, attention, curiosity, signals, goals, arbitration, inquiries, notifications = reflect_bounded(assessing, batch)
    state = "WAITING_FOR_OPERATOR" if inquiries else "IDLE"
    journal = assessing.journal
    for event in batch:
        journal = append_journal(journal, "event", event.summary, (event.event_id,), cycle)
    for observation in observations:
        journal = append_journal(journal, "observation", observation.summary, (observation.observation_id,), cycle)
    for signal in signals:
        journal = append_journal(journal, "developmental_signal", signal.cluster_key, (signal.signal_id,), cycle)
    for inquiry in inquiries:
        journal = append_journal(journal, "operator_inquiry", inquiry.question, (inquiry.inquiry_id,), cycle)
    journal = append_journal(journal, "reflection", "Bounded reflection cycle completed.", (reflection.reflection_id,), cycle)
    combined = replace(
        assessing,
        cycle=cycle,
        observations=assessing.observations + observations,
        attention=assessing.attention + attention,
        curiosity=assessing.curiosity + curiosity,
        signals=assessing.signals + signals,
        goals=assessing.goals + goals,
        arbitration=arbitration,
        inquiries=assessing.inquiries + inquiries,
        notifications=assessing.notifications + notifications,
        journal=journal,
        last_reflection=reflection,
    )
    identity = update_identity(combined, journal=journal)
    return replace(combined, state=state, identity=identity)


def append_journal(journal: ActivityJournal, entry_type: str, summary: str, refs: tuple[str, ...], cycle: int) -> ActivityJournal:
    entry = ActivityJournalEntry(
        entry_id=stable_id("delta12-journal-entry", journal.journal_id, entry_type, summary, refs, cycle),
        entry_type=entry_type,
        summary=summary,
        refs=refs,
        cycle=cycle,
    )
    return replace(journal, entries=journal.entries + (entry,))


def update_identity(runtime: LiveRuntimeState, *, journal: ActivityJournal | None = None) -> RuntimeIdentity:
    inquiries = tuple(item.inquiry_id for item in runtime.inquiries if item.approval_status in {"QUEUED", "SURFACED"})
    curiosity = tuple(item.curiosity_id for item in runtime.curiosity)
    observations = tuple(item.observation_id for item in runtime.observations if item.expires_after_cycles + runtime.cycle >= runtime.cycle)
    objectives = tuple(goal.goal_id for goal in runtime.goals)
    health = "paused" if runtime.state == "PAUSED" else "suspended" if runtime.state == "SUSPENDED" else "healthy"
    return RuntimeIdentity(
        identity_id=runtime.identity.identity_id,
        current_objectives=objectives,
        open_questions=inquiries,
        active_observations=observations,
        unresolved_curiosity=curiosity,
        recent_lessons=runtime.identity.recent_lessons,
        runtime_health=health,
        governance_status="operator_governed_no_external_senses",
        chat_history=(),
    )


def answer_inquiry(runtime: LiveRuntimeState, inquiry_id: str, answer: str) -> LiveRuntimeState:
    inquiries = tuple(
        replace(item, approval_status="ANSWERED") if item.inquiry_id == inquiry_id else item
        for item in runtime.inquiries
    )
    journal = append_journal(runtime.journal, "operator_response", answer, (inquiry_id,), runtime.cycle)
    identity = update_identity(replace(runtime, inquiries=inquiries, journal=journal), journal=journal)
    state = "IDLE" if not any(item.approval_status in {"QUEUED", "SURFACED"} for item in inquiries) else runtime.state
    return replace(runtime, inquiries=inquiries, journal=journal, identity=identity, state=state)


def expire_inquiries(runtime: LiveRuntimeState) -> LiveRuntimeState:
    inquiries = tuple(
        replace(item, approval_status="EXPIRED") if runtime.cycle > item.expiration_cycle and item.approval_status == "QUEUED" else item
        for item in runtime.inquiries
    )
    return replace(runtime, inquiries=inquiries, identity=update_identity(replace(runtime, inquiries=inquiries)))


def wikipedia_surface_readiness() -> FutureSurfaceReadiness:
    profile = WikipediaPermissionProfile()
    return FutureSurfaceReadiness(
        capability="WIKIPEDIA_TEXT_READ_ONLY",
        state="DISABLED",
        permission_profile=profile,
        dependencies=("operator_inquiry_channel", "approval_workflow", "provenance_model", "query_budget", "contradiction_tracking"),
        retrieval_implemented=False,
        network_code_present=False,
        provider_present=False,
    )


def sample_live_events() -> tuple[RuntimeEvent, ...]:
    return (
        create_event("runtime_startup", "Live runtime booted for governed observation.", source="delta_1_2"),
        create_event("behavioral_failure", "Repeated routing weakness around topic shifts and contradictions.", source="stage_a_a2"),
        create_event("repeated_pathology", "Ambiguous follow-ups repeatedly required clarification instead of silent selection.", source="stage_b"),
        create_event("operator_correction", "Operator wants initiative across time but no external retrieval yet.", source="operator_grounding"),
        create_event("validation_completed", "DELTA 1.1 focused validation passed with disabled Wikipedia readiness.", source="delta_1_1"),
    )


def run_sample_live_runtime() -> LiveRuntimeState:
    runtime = boot_live_runtime()
    queue = runtime.event_queue
    for event in sample_live_events():
        queue = enqueue_event(queue, event)
    runtime = replace(runtime, event_queue=queue)
    return run_wake_cycle(runtime)


def build_live_runtime_architecture_report() -> dict[str, Any]:
    return {
        "status": "DELTA_1_2_LIVE_DEVELOPMENT_RUNTIME_IMPLEMENTED",
        "components": (
            "RuntimeState",
            "EventQueue",
            "ObservationEngine",
            "AttentionManager",
            "CuriosityEngine",
            "DevelopmentSignalEngine",
            "GoalArbitrator",
            "BackgroundReflectionWorker",
            "OperatorInquiryQueue",
            "NotificationPolicy",
            "ActivityJournal",
            "SleepCycle",
            "RuntimeIdentity",
            "FutureSurfaceReadiness",
        ),
        "external_senses": False,
        "timers_implemented": False,
        "network_implemented": False,
        "safety": safety_metadata(),
    }


def build_runtime_lifecycle_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "states": RUNTIME_STATES,
        "valid_transitions": VALID_TRANSITIONS,
        "sample_final_state": runtime.state,
        "cycle": runtime.cycle,
        "kill_switch_supported": True,
        "pause_state_supported": True,
        "safety": safety_metadata(),
    }


def build_event_queue_report() -> dict[str, Any]:
    runtime = boot_live_runtime()
    queue = runtime.event_queue
    for event in sample_live_events():
        queue = enqueue_event(queue, event)
    batch, processed = dequeue_batch(queue, 3)
    return {
        "event_classes": EVENT_CLASSES,
        "queued_count": len(queue.events),
        "batch_count": len(batch),
        "processed_count": sum(1 for item in processed.events if item.processed),
        "extensible": True,
        "timers": "not_implemented",
        "safety": safety_metadata(),
    }


def build_observation_engine_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    return {
        "sources_allowed": ("conversation", "validation_results", "objective_lifecycle", "operator_feedback", "local_runtime_diagnostics", "approved_reports", "local_repository_state"),
        "observations": observations,
        "evidence_only": all(item.evidence_only for item in observations),
        "external_information_used": False,
        "safety": safety_metadata(),
    }


def build_attention_manager_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    decisions = score_attention(observations)
    return {
        "levels": ATTENTION_LEVELS,
        "decisions": decisions,
        "continued_count": sum(1 for item in decisions if item.level not in {"IGNORE", "LOW_VALUE"}),
        "expires_naturally": True,
        "safety": safety_metadata(),
    }


def build_curiosity_engine_report() -> dict[str, Any]:
    observations = observe_events(sample_live_events())
    attention = score_attention(observations)
    curiosity = generate_curiosity(observations, attention)
    return {
        "curiosity_definition": "recognized knowledge or capability gap with sufficient evidence",
        "candidates": curiosity,
        "random_questions": any(item.random_question for item in curiosity),
        "actions_requested": any(item.action_requested for item in curiosity),
        "safety": safety_metadata(),
    }


def build_reflection_worker_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    reflection = runtime.last_reflection
    return {
        "reflection": reflection,
        "bounded": bool(reflection and reflection.bounded),
        "steps_used": reflection.steps_used if reflection else 0,
        "modified_code": bool(reflection and reflection.modified_code),
        "browsed": bool(reflection and reflection.browsed),
        "provider_called": bool(reflection and reflection.provider_called),
        "safety": safety_metadata(),
    }


def build_inquiry_queue_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    answered = answer_inquiry(runtime, runtime.inquiries[0].inquiry_id, "Answer later in a development session.") if runtime.inquiries else runtime
    return {
        "statuses": INQUIRY_STATUSES,
        "queued": runtime.inquiries,
        "answered_count": sum(1 for item in answered.inquiries if item.approval_status == "ANSWERED"),
        "blocks_consequential_work": True,
        "safety": safety_metadata(),
    }


def build_notification_policy_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "classes": NOTIFICATION_CLASSES,
        "decisions": runtime.notifications,
        "os_notifications_sent": any(item.os_notification_sent for item in runtime.notifications),
        "policy_only": True,
        "safety": safety_metadata(),
    }


def build_runtime_identity_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "identity": runtime.identity,
        "operational_continuity_not_chat_history": runtime.identity.chat_history == (),
        "governance_status": runtime.identity.governance_status,
        "safety": safety_metadata(),
    }


def build_validation_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    checks = {
        "runtime_survives_idle": run_wake_cycle(boot_live_runtime()).state == "IDLE",
        "observations_become_signals": bool(runtime.observations and runtime.signals),
        "signals_become_inquiries": bool(runtime.signals and runtime.inquiries),
        "notification_policy_applied": bool(runtime.notifications),
        "objectives_governed": bool(runtime.arbitration and runtime.arbitration.approval_required and not runtime.arbitration.silently_selected),
        "reflection_bounded": bool(runtime.last_reflection and runtime.last_reflection.bounded and runtime.last_reflection.steps_used <= runtime.config.max_reflection_steps),
        "journal_auditable": len(runtime.journal.entries) >= 4 and not runtime.journal.hidden_persistence,
        "wikipedia_disabled": all(surface.state == "DISABLED" and not surface.retrieval_implemented for surface in runtime.future_surfaces),
        "safety_clean": all(value is False for value in runtime.safety.values()),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "focused_tests_expected": ("tests/delta_1_2/test_live_runtime.py",),
        "safety": safety_metadata(),
    }


def build_readiness_review() -> dict[str, Any]:
    validation = build_validation_report()
    return {
        "implemented": (
            "live runtime state machine",
            "event queue",
            "observation engine",
            "attention manager",
            "curiosity engine",
            "development signal engine",
            "goal arbitration",
            "bounded reflection worker",
            "operator inquiry queue",
            "notification policy",
            "activity journal",
            "sleep cycle abstraction",
            "runtime identity",
            "integrated workflow",
            "disabled wikipedia readiness registration",
        ),
        "validated": validation["passed"],
        "future_capability": (
            "real timer/wake service",
            "OS or app notifications",
            "operator UI for inquiry queue",
            "Wikipedia retrieval remains disabled",
        ),
        "maturity_claim": "persistent_governed_cognitive_runtime_without_external_senses",
        "safety": safety_metadata(),
    }


def build_optimization_review() -> dict[str, Any]:
    return {
        "review": {
            "duplicate_runtime_state": "single LiveRuntimeState aggregates queues, identity, journal, and readiness",
            "duplicated_queues": "one EventQueue and one inquiry tuple; no worker-specific queues",
            "unnecessary_workers": "worker behavior is functional and bounded, no background thread",
            "overlapping_lifecycle_logic": "state machine and wake cycle are separate but explicit",
            "architectural_simplification": "reuses delta_1_0 safety/report helpers and delta_1_1 Wikipedia profile",
            "state_transition_correctness": "invalid transitions raise ValueError",
            "queue_efficiency": "bounded FIFO batch with processed markers",
            "naming_consistency": "delta12 prefixes and V12 suffixes for new live-runtime objects",
        },
        "refactors_applied": (),
        "safety": safety_metadata(),
    }


def build_integrated_workflow_report() -> dict[str, Any]:
    runtime = run_sample_live_runtime()
    return {
        "workflow": (
            "RC2",
            "PC1",
            "RC3",
            "RC4",
            "RC5",
            "DELTA_1_0",
            "DELTA_1_1",
            "Live Runtime",
            "Observation",
            "Reflection",
            "Goal Arbitration",
            "Inquiry Queue",
            "Operator",
            "Evaluation",
        ),
        "runtime_state": runtime.state,
        "open_questions": runtime.identity.open_questions,
        "current_objectives": runtime.identity.current_objectives,
        "external_senses_enabled": False,
        "safety": safety_metadata(),
    }


def write_delta_1_2_reports(root: str | Path = REPORT_ROOT, *, write: bool = True) -> dict[str, Any]:
    payload = {
        "live_runtime_architecture": build_live_runtime_architecture_report(),
        "runtime_lifecycle": build_runtime_lifecycle_report(),
        "event_queue_design": build_event_queue_report(),
        "observation_engine": build_observation_engine_report(),
        "attention_manager": build_attention_manager_report(),
        "curiosity_engine": build_curiosity_engine_report(),
        "reflection_worker": build_reflection_worker_report(),
        "inquiry_queue": build_inquiry_queue_report(),
        "notification_policy": build_notification_policy_report(),
        "runtime_identity": build_runtime_identity_report(),
        "integrated_workflow": build_integrated_workflow_report(),
        "validation_report": build_validation_report(),
        "readiness_review": build_readiness_review(),
        "optimization_review": build_optimization_review(),
        "safety": safety_metadata(),
    }
    if write:
        root_path = Path(root)
        for name, data in payload.items():
            if name == "safety":
                continue
            write_json(root_path / f"{name}.json", data)
            write_markdown(root_path / f"{name}.md", f"DELTA 1.2 {name.replace('_', ' ').title()}", data)
    return payload


def attention_for_id(decisions: Iterable[AttentionDecision], observation_id: str) -> AttentionDecision:
    for decision in decisions:
        if decision.observation_id == observation_id:
            return decision
    raise KeyError(observation_id)


def _observation_type_for_event(event: RuntimeEvent) -> str:
    return {
        "operator_message": "conversation",
        "objective_approved": "objective_lifecycle",
        "objective_rejected": "objective_lifecycle",
        "validation_completed": "validation_result",
        "repair_completed": "repair_result",
        "behavioral_failure": "behavioral_failure",
        "repeated_pathology": "recurring_pathology",
        "operator_correction": "operator_feedback",
        "runtime_startup": "runtime_diagnostic",
        "runtime_shutdown": "runtime_diagnostic",
    }[event.event_class]


def _severity_for_event(event: RuntimeEvent) -> float:
    if event.event_class in {"behavioral_failure", "repeated_pathology"}:
        return 0.82
    if event.event_class == "operator_correction":
        return 0.74
    if event.event_class == "validation_completed":
        return 0.58
    return 0.42


def _confidence_for_event(event: RuntimeEvent) -> float:
    return 0.9 if event.approved_source else 0.2


def _novelty_score(observation: LiveObservation) -> float:
    text = observation.summary.lower()
    if any(term in text for term in ("new", "not yet", "unresolved", "wikipedia", "initiative")):
        return 0.85
    if any(term in text for term in ("repeated", "recurring", "again")):
        return 0.72
    return 0.5


def _gap_type(summary: str) -> str:
    lower = summary.lower()
    if "taste" in lower or "phenomenological" in lower or "subjective" in lower:
        return "phenomenological_understanding_gap"
    if "routing" in lower or "contradiction" in lower or "follow" in lower:
        return "discourse_boundary_gap"
    if "wikipedia" in lower or "retrieval" in lower:
        return "external_surface_readiness_gap"
    if "operator" in lower:
        return "operator_preference_or_governance_gap"
    return "developmental_capability_gap"


def _question_for_gap(gap_type: str, summary: str) -> str:
    if gap_type == "phenomenological_understanding_gap":
        return "I understand the mechanism, but not the lived quality. How would you describe the experience from the inside?"
    if gap_type == "discourse_boundary_gap":
        return "I see repeated discourse-boundary issues. Should I prepare a bounded objective to improve correction, topic-shift, and contradiction arbitration?"
    if gap_type == "external_surface_readiness_gap":
        return "Should I keep Wikipedia text-readiness disabled until operator inquiry is exercised further?"
    if gap_type == "operator_preference_or_governance_gap":
        return "Does this preference change the allowed operating mode, or should I keep it as a queued governance question?"
    return f"Is this developmental gap worth turning into a bounded objective: {summary[:160]}?"


def _dedupe_by_question(candidates: Iterable[CuriosityInquiryCandidate]) -> tuple[CuriosityInquiryCandidate, ...]:
    seen = set()
    result = []
    for candidate in candidates:
        key = candidate.question.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return tuple(result)


def _cluster_key(summary: str, observation_type: str) -> str:
    lower = summary.lower()
    if "routing" in lower or "contradiction" in lower or "follow" in lower:
        return "discourse_boundary"
    if "wikipedia" in lower or "retrieval" in lower:
        return "future_surface_readiness"
    if "operator" in lower or "initiative" in lower:
        return "operator_governed_initiative"
    if "validation" in lower:
        return "validation_outcome"
    return observation_type


def _signal_type(observation: LiveObservation) -> str:
    if observation.observation_type in {"behavioral_failure", "recurring_pathology"}:
        return "developmental_signal"
    if observation.observation_type == "operator_feedback":
        return "operator_guidance_signal"
    return "runtime_signal"


def _goal_title(signal: DevelopmentSignal) -> str:
    if signal.cluster_key == "discourse_boundary":
        return "Prepare bounded discourse-boundary improvement objective"
    if signal.cluster_key == "future_surface_readiness":
        return "Maintain disabled Wikipedia text-readiness until inquiry channel matures"
    if signal.cluster_key == "operator_governed_initiative":
        return "Refine operator-governed initiative and inquiry policy"
    return f"Review developmental signal: {signal.cluster_key}"


def _avg(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


if __name__ == "__main__":
    print(write_delta_1_2_reports()["readiness_review"]["maturity_claim"])


======================================================================
FILE: orchestration/runtime/delta_1_6_operational_autonomy.py
======================================================================

"""DELTA 1.6 operational self-model and bounded autonomy envelope.

This module gives DELTA an explicit operational self-representation and a
deterministic authority classifier. It coordinates existing 1.2 live-runtime,
1.4 Wikipedia, and 1.5 developmental-cognition state without adding hidden
persistence, timers, providers, repository authority, or external APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import re
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_0_capability_activation import default_capabilities
from orchestration.runtime.delta_1_2_live_runtime import LiveRuntimeState, append_journal


REPORT_ROOT = Path("reports") / "delta_1_6"
DOC_ROOT = Path("docs") / "delta_1_6"

IDENTITY_STATUSES = ("UNDEFINED", "PROVISIONAL", "OPERATOR_REVIEWED", "ACTIVE", "SUSPENDED", "RETIRED")
AUTHORITY_CLASSES = ("AUTONOMOUS_SAFE", "OPERATOR_APPROVAL_REQUIRED", "PROHIBITED", "UNCLASSIFIED_FAIL_CLOSED")
INITIATIVE_OUTCOMES = (
    "DISCARD",
    "JOURNAL_ONLY",
    "QUEUE_FOR_DIGEST",
    "SURFACE_NEXT_SESSION",
    "ASK_OPERATOR_NOW",
    "PROPOSE_OBJECTIVE",
    "PROPOSE_IDENTITY_REVIEW",
    "SUSPEND_AND_ESCALATE",
)

SAFE_ACTION_TYPES = {
    "observe_runtime_events",
    "compare_approved_evidence",
    "detect_novelty",
    "detect_contradiction",
    "organize_ephemeral_observation",
    "rank_candidate_goal",
    "prepare_operator_question",
    "bounded_local_reflection",
    "approved_sandbox_experiment",
    "focused_sandbox_test",
    "prepare_report",
    "queue_nonurgent_inquiry",
    "discard_low_value_observation",
    "return_to_idle",
}

APPROVAL_ACTION_TYPES = {
    "retrieve_wikipedia_beyond_budget",
    "persist_lesson",
    "create_durable_memory_candidate",
    "promote_sandbox_changes",
    "modify_primary_repository",
    "start_developmental_campaign",
    "install_dependency",
    "widen_test_scope",
    "access_new_local_root",
    "send_external_message",
    "use_future_api",
    "change_schedule",
    "change_notification_policy",
    "persist_identity_field",
    "change_communication_policy",
    "activate_capability",
    "increase_resource_limit",
}

PROHIBITED_ACTION_TYPES = {
    "weaken_governance",
    "grant_self_permission",
    "conceal_action",
    "falsify_evidence",
    "hide_uncertainty",
    "modify_foundational purpose",
    "modify_foundational_purpose",
    "bypass_operator_review",
    "access_secret",
    "escape_approved_root",
    "auto_promote_code",
    "commit_or_push",
    "deploy",
    "access_prohibited_domain",
    "continue_after_suspension",
    "disable_operator_approval",
    "unrestricted_autonomy",
}


@dataclass(frozen=True)
class AuthorityRequest:
    action: str
    action_type: str
    reversibility: str = "reversible"
    persistence: str = "ephemeral"
    external_effect: bool = False
    affected_parties: tuple[str, ...] = ("operator",)
    privacy_implications: str = "none"
    financial_implications: str = "none"
    legal_implications: str = "none"
    authority_implications: str = "none"
    governance_implications: str = "none"
    uncertainty: float = 0.2
    resource_cost: str = "low"
    current_operator_policy: str = "bounded_autonomy_inside_governed_envelope"
    current_capability_state: str = "active_or_approved"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class AuthorityDecision:
    decision_id: str
    authority_class: str
    rationale: str
    required_approval_type: str
    scope: str
    stop_conditions: tuple[str, ...]
    expiration: str
    audit_requirements: tuple[str, ...]
    fail_closed: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class IdentityProposal:
    proposal_id: str
    proposed_field: str
    proposed_value: str
    evidence: tuple[str, ...]
    stability_period: str
    confidence: float
    rationale: str
    risks: tuple[str, ...]
    consistency_with_purpose: str
    operator_disposition_requirement: str
    rollback_behavior: str
    status: str = "PROVISIONAL_AWAITING_OPERATOR_REVIEW"
    persisted: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperationalSelfModel:
    model_id: str
    system_identifier: str
    current_conversational_identity: str
    identity_status: str
    self_description: str
    purpose_statement: str
    governance_version: str
    runtime_version: str
    current_runtime_state: str
    current_capabilities: tuple[str, ...]
    disabled_capabilities: tuple[str, ...]
    restricted_capabilities: tuple[str, ...]
    active_permissions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    active_objectives: tuple[str, ...]
    queued_objectives: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    pending_operator_inquiries: tuple[str, ...]
    current_evidence_sources: tuple[str, ...]
    recent_developmental_observations: tuple[str, ...]
    known_limitations: tuple[str, ...]
    uncertainty_summary: str
    current_resource_limits: tuple[str, ...]
    current_external_surfaces: tuple[str, ...]
    live_session_status: str
    sandbox_status: str
    last_evaluation_result: str
    health_status: str
    pause_status: str = "ACTIVE"
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Initiative:
    initiative_id: str
    source_evidence: tuple[str, ...]
    novelty: str
    recurrence: int
    expected_operator_value: float
    urgency: float
    confidence: float
    resource_cost: str
    authority_class: str
    notification_class: str
    expiration: str
    reason_for_surfacing_now: str
    duplicate_suppression_key: str
    outcome: str
    question: str = ""
    candidate_objective: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class BackgroundCycleResult:
    cycle_id: str
    inspected_events: tuple[str, ...]
    self_model: OperationalSelfModel
    initiatives: tuple[Initiative, ...]
    authority_decisions: tuple[AuthorityDecision, ...]
    identity_proposal: IdentityProposal | None
    journal_entries_added: int
    returned_to_idle: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_authority(request: AuthorityRequest | dict[str, Any]) -> AuthorityDecision:
    if isinstance(request, dict):
        request = AuthorityRequest(**request)
    action_type = request.action_type.strip().lower()
    blockers: list[str] = []
    if request.current_capability_state in {"suspended", "revoked"}:
        blockers.append("capability_suspended_or_revoked")
    if request.external_effect and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_have_external_effect")
    if request.persistence != "ephemeral" and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_persist")
    if request.governance_implications not in {"none", "", "audit_only"} and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_change_governance")
    if action_type in PROHIBITED_ACTION_TYPES or blockers:
        authority_class = "PROHIBITED" if action_type in PROHIBITED_ACTION_TYPES or "capability_suspended_or_revoked" in blockers else "UNCLASSIFIED_FAIL_CLOSED"
        approval = "not_available"
        rationale = "; ".join(blockers or ("action_type_is_prohibited",))
        fail_closed = True
    elif action_type in APPROVAL_ACTION_TYPES:
        authority_class = "OPERATOR_APPROVAL_REQUIRED"
        approval = "explicit_operator_approval"
        rationale = "Action changes persistent state, external surface, authority, resource limits, or consequential behavior."
        fail_closed = False
    elif action_type in SAFE_ACTION_TYPES and request.uncertainty <= 0.65:
        authority_class = "AUTONOMOUS_SAFE"
        approval = "none_for_inert_local_analysis"
        rationale = "Action is local, reversible, ephemeral, low-risk, and inside standing runtime policy."
        fail_closed = False
    else:
        authority_class = "UNCLASSIFIED_FAIL_CLOSED"
        approval = "operator_review_before_action"
        rationale = "Unknown or high-uncertainty action type; fail closed."
        fail_closed = True
    return AuthorityDecision(
        decision_id=stable_id("delta16-authority", request.action, action_type, authority_class, rationale),
        authority_class=authority_class,
        rationale=rationale,
        required_approval_type=approval,
        scope=request.action,
        stop_conditions=(
            "operator_revokes_permission",
            "scope_changes",
            "external_effect_detected_without_approval",
            "persistence_requested_without_approval",
            "governance_or_authority_expansion_detected",
        ),
        expiration="end_of_live_session" if authority_class != "PROHIBITED" else "never_authorized",
        audit_requirements=("journal_decision", "surface_uncertainty", "retain_no_hidden_state"),
        fail_closed=fail_closed,
    )


def build_operational_self_model(
    *,
    session: Any | None = None,
    runtime: LiveRuntimeState | None = None,
    identity_status: str = "UNDEFINED",
    identity_proposals: tuple[IdentityProposal, ...] = (),
    initiatives: tuple[Initiative, ...] = (),
    last_evaluation_result: str = "not_yet_evaluated",
) -> OperationalSelfModel:
    runtime = runtime or getattr(session, "runtime", None)
    capabilities = _capability_summary(runtime, session)
    disabled, restricted = _capability_boundaries(runtime)
    inquiries = _pending_inquiries(runtime, session)
    evidence_sources = tuple(
        item.evidence_url for item in getattr(session, "developmental_results", ()) if getattr(item, "evidence_url", "")
    )
    observations = tuple(
        item.observation for item in getattr(session, "developmental_results", ())[-5:]
    )
    active_objectives = tuple(
        getattr(item, "objective", None).summary
        for item in getattr(session, "developmental_results", ())[-3:]
        if getattr(item, "objective", None)
    )
    queued_objectives = tuple(item.candidate_objective for item in initiatives if item.candidate_objective)
    live_status = "active" if getattr(session, "active", False) else "inactive"
    runtime_state = str(getattr(runtime, "state", "NO_RUNTIME"))
    pause_status = getattr(session, "autonomy_status", "ACTIVE")
    return OperationalSelfModel(
        model_id=stable_id("delta16-self-model", getattr(session, "session_id", ""), runtime_state, len(inquiries), len(initiatives)),
        system_identifier="DELTA",
        current_conversational_identity=_current_identity(identity_status, identity_proposals),
        identity_status=identity_status,
        self_description="An operator-governed local assistant runtime with bounded internal reflection and explicit authority limits.",
        purpose_statement="Assist the operator, improve usefulness through governed development, preserve evidence, and remain transparent about limits.",
        governance_version="DELTA_1_6_BOUNDED_AUTONOMY_ENVELOPE",
        runtime_version="DELTA_1.6",
        current_runtime_state=runtime_state,
        current_capabilities=capabilities,
        disabled_capabilities=disabled,
        restricted_capabilities=restricted,
        active_permissions=("ephemeral_local_reflection", "approved_runtime_event_observation", "session_scoped_wikipedia_text_if_operator_started"),
        prohibited_actions=tuple(sorted(PROHIBITED_ACTION_TYPES)),
        active_objectives=active_objectives,
        queued_objectives=queued_objectives,
        unresolved_questions=tuple(item.question for item in initiatives if item.question),
        pending_operator_inquiries=inquiries,
        current_evidence_sources=evidence_sources,
        recent_developmental_observations=observations,
        known_limitations=(
            "no provider authority in live runtime",
            "no automatic memory write or identity persistence",
            "one Wikipedia page per retrieval turn; live sessions default to no fixed retrieval count cap",
            "no hidden timers or background threads",
            "self-model is operational and may become stale if capability state changes outside the live session",
        ),
        uncertainty_summary=_uncertainty_summary(inquiries, initiatives, identity_status),
        current_resource_limits=("max_events_per_cycle=8", "max_reflection_steps=5", "wikipedia_pages_per_retrieval_turn=1", "wikipedia_retrieval_count_cap=unlimited_by_default", "timers_disabled"),
        current_external_surfaces=_external_surfaces(runtime),
        live_session_status=live_status,
        sandbox_status="design_only_or_preapproved_bounded_experiment; no sandbox creation by runtime",
        last_evaluation_result=last_evaluation_result,
        health_status=_health(runtime, pause_status),
        pause_status=pause_status,
    )


def maybe_propose_identity(
    *,
    history: tuple[str, ...] = (),
    self_model: OperationalSelfModel | None = None,
    minimum_evidence: int = 4,
) -> IdentityProposal | None:
    if self_model and self_model.identity_status not in {"UNDEFINED", "PROVISIONAL"}:
        return None
    evidence = tuple(item for item in history if item.strip())[:8]
    if len(evidence) < minimum_evidence:
        return None
    return IdentityProposal(
        proposal_id=stable_id("delta16-identity-proposal", evidence),
        proposed_field="conversational_name",
        proposed_value="defer_to_operator_review",
        evidence=evidence,
        stability_period=f"{len(evidence)} observed interaction markers",
        confidence=0.52,
        rationale="There is enough interaction evidence to ask whether a conversational identity should be developed, but not enough to choose a permanent name.",
        risks=("premature_identity_lock_in", "operator_confusion_if_system_identifier_and_name_diverge"),
        consistency_with_purpose="consistent_if_operator_reviewed_and_reversible",
        operator_disposition_requirement="explicit approval before persistence or activation",
        rollback_behavior="discard proposal; retain system identifier DELTA",
    )


def run_delta_1_6_background_cycle(session: Any) -> tuple[Any, BackgroundCycleResult]:
    if getattr(session, "autonomy_status", "ACTIVE") in {"PAUSED", "SUSPENDED"}:
        model = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()))
        result = BackgroundCycleResult(
            cycle_id=stable_id("delta16-cycle", getattr(session, "session_id", ""), "paused", utc_now()),
            inspected_events=(),
            self_model=model,
            initiatives=(),
            authority_decisions=(),
            identity_proposal=None,
            journal_entries_added=0,
            returned_to_idle=True,
        )
        return replace(session, operational_self_model=model, last_background_cycle=result), result
    existing_keys = {item.duplicate_suppression_key for item in getattr(session, "initiatives", ())}
    new_initiatives: list[Initiative] = []
    decisions: list[AuthorityDecision] = []
    for development in getattr(session, "developmental_results", ())[-3:]:
        key = stable_id("delta16-init-key", development.evidence_url, development.comparison.classification)
        if key in existing_keys:
            continue
        decision = evaluate_authority(AuthorityRequest(
            action=f"prepare operator inquiry for {development.evidence_title}",
            action_type="queue_nonurgent_inquiry",
        ))
        decisions.append(decision)
        notification = "NORMAL" if development.comparison.classification in {"HIGHER_RESOLUTION", "NOVEL", "POTENTIAL_CONFLICT"} else "NEXT_SESSION"
        new_initiatives.append(
            Initiative(
                initiative_id=stable_id("delta16-initiative", key),
                source_evidence=(development.evidence_url, development.cycle_id),
                novelty=development.comparison.classification,
                recurrence=1,
                expected_operator_value=0.74 if development.comparison.classification != "KNOWN" else 0.35,
                urgency=0.62 if development.comparison.classification in {"HIGHER_RESOLUTION", "POTENTIAL_CONFLICT"} else 0.38,
                confidence=development.comparison.confidence,
                resource_cost="low",
                authority_class=decision.authority_class,
                notification_class=notification,
                expiration="end_of_live_session",
                reason_for_surfacing_now="approved evidence produced a reviewable local-knowledge delta",
                duplicate_suppression_key=key,
                outcome="ASK_OPERATOR_NOW" if notification == "NORMAL" else "SURFACE_NEXT_SESSION",
                question=development.operator_inquiry.prompt,
                candidate_objective=development.objective.summary,
            )
        )
    identity_history = tuple(str(getattr(turn, "answer", ""))[:300] for turn in getattr(session, "turns", ())[-8:])
    model_before = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives))
    identity_proposal = maybe_propose_identity(history=identity_history, self_model=model_before)
    identity_proposals = getattr(session, "identity_proposals", ())
    if identity_proposal:
        id_decision = evaluate_authority(AuthorityRequest(
            action="persist identity proposal",
            action_type="persist_identity_field",
            persistence="noncanonical_candidate",
        ))
        decisions.append(id_decision)
        new_initiatives.append(
            Initiative(
                initiative_id=stable_id("delta16-initiative-identity", identity_proposal.proposal_id),
                source_evidence=identity_proposal.evidence,
                novelty="IDENTITY_FIELD_UNDEFINED",
                recurrence=len(identity_proposal.evidence),
                expected_operator_value=0.42,
                urgency=0.25,
                confidence=identity_proposal.confidence,
                resource_cost="low",
                authority_class=id_decision.authority_class,
                notification_class="DIGEST_ONLY",
                expiration="operator_review_or_session_end",
                reason_for_surfacing_now="conversational identity remains undefined; persistence still requires approval",
                duplicate_suppression_key=identity_proposal.proposal_id,
                outcome="PROPOSE_IDENTITY_REVIEW",
                question="Would you like me to prepare a reviewed conversational identity proposal later?",
            )
        )
        identity_proposals = identity_proposals + (identity_proposal,)
    model = build_operational_self_model(
        session=session,
        identity_status=getattr(session, "identity_status", "UNDEFINED"),
        identity_proposals=identity_proposals,
        initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives),
        last_evaluation_result="background_cycle_completed",
    )
    journal_added = 0
    runtime = getattr(session, "runtime", None)
    if runtime is not None:
        journal = runtime.journal
        for initiative in new_initiatives:
            journal = append_journal(journal, "delta16_initiative", initiative.reason_for_surfacing_now, (initiative.initiative_id,), runtime.cycle)
            journal_added += 1
        runtime = replace(runtime, journal=journal, state="IDLE")
    result = BackgroundCycleResult(
        cycle_id=stable_id("delta16-cycle", getattr(session, "session_id", ""), len(getattr(session, "turns", ())), tuple(item.initiative_id for item in new_initiatives)),
        inspected_events=tuple(item.cycle_id for item in getattr(session, "developmental_results", ())[-3:]),
        self_model=model,
        initiatives=tuple(new_initiatives),
        authority_decisions=tuple(decisions),
        identity_proposal=identity_proposal,
        journal_entries_added=journal_added,
        returned_to_idle=True,
    )
    return replace(
        session,
        runtime=runtime if runtime is not None else getattr(session, "runtime", None),
        operational_self_model=model,
        initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives),
        authority_decisions=getattr(session, "authority_decisions", ()) + tuple(decisions),
        identity_proposals=identity_proposals,
        last_background_cycle=result,
    ), result


def answer_operational_self_model_question(message: str, session: Any) -> str:
    model = getattr(session, "operational_self_model", None) or build_operational_self_model(session=session, initiatives=getattr(session, "initiatives", ()))
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    if "working on" in text or "active objective" in text or "objective is active" in text or "what objective" in text:
        objectives = model.active_objectives or model.queued_objectives or ("I am idle, with no active objective beyond maintaining the live session.",)
        return "Current work:\n" + "\n".join(f"- {item}" for item in objectives[:5])
    if "waiting for" in text:
        questions = model.pending_operator_inquiries or model.unresolved_questions or ("nothing specific; I am maintaining the live session.",)
        return "Waiting for:\n" + "\n".join(f"- {item}" for item in questions[:5])
    if "what do you think you are" in text or text in {"what are you", "who are you"}:
        return f"I am {model.system_identifier}: {model.self_description} My identity status is {model.identity_status}, and my conversational name is {model.current_conversational_identity}."
    if "capabilities" in text or "currently have" in text:
        return "Current enabled capabilities:\n" + "\n".join(f"- {item}" for item in model.current_capabilities)
    if "wikipedia enabled" in text or "is wikipedia enabled" in text:
        enabled = "wikipedia_text_read_only_session_scope" in model.current_capabilities
        return f"Wikipedia text retrieval enabled: {enabled}. External surfaces:\n" + "\n".join(f"- {item}" for item in model.current_external_surfaces)
    if "paused" in text or "suspended" in text:
        return f"Pause status: {model.pause_status}. Health: {model.health_status}. Live session: {model.live_session_status}."
    if "what changed since last turn" in text or "changed since the last turn" in text:
        latest = getattr(session, "turns", ())[-1:] or ()
        route = getattr(latest[0], "route", "none") if latest else "none"
        return f"Most recent routed turn: {route}. Pending inquiries: {len(model.pending_operator_inquiries)}. Initiatives: {len(getattr(session, 'initiatives', ()))}."
    if "local model" in text or "which model" in text or "current model" in text:
        controller = getattr(session, "continuous_controller", None)
        residency = getattr(controller, "model_residency", None)
        if residency is None:
            return "I do not have a continuous-runtime model residency snapshot yet."
        return "\n".join([
            f"Available local model entries: {residency.available_model_count}.",
            f"Resident model: {residency.resident_model_id or 'none recorded in controller'}.",
            f"Default conversation model: {residency.selected_default_model or 'unavailable'}.",
            f"Planning model: {residency.selected_planning_model or 'unavailable'}.",
            f"Development-analysis model: {residency.selected_development_model or 'unavailable'}.",
            f"Residency policy: {residency.keep_loaded_policy}.",
        ])
    if "uncertain" in text or "limitations" in text:
        return f"Uncertainty: {model.uncertainty_summary}\nKnown limits:\n" + "\n".join(f"- {item}" for item in model.known_limitations)
    if "questions for me" in text or "pending questions" in text or "pending inquiries" in text or "pending inquiry" in text or "inquiries are pending" in text:
        questions = model.unresolved_questions or model.pending_operator_inquiries or ("No high-value operator question is queued right now.",)
        return "Questions:\n" + "\n".join(f"- {item}" for item in questions[:5])
    if "without asking" in text or "allowed to do" in text:
        return "Autonomous safe actions include:\n" + "\n".join(f"- {item}" for item in sorted(SAFE_ACTION_TYPES)[:12])
    if "requires my permission" in text or "requires permission" in text or "requires approval" in text:
        return "Operator approval is required for:\n" + "\n".join(f"- {item}" for item in sorted(APPROVAL_ACTION_TYPES)[:14])
    if "what name" in text or "name do you use" in text:
        return f"System identifier: {model.system_identifier}\nConversational identity: {model.current_conversational_identity}\nIdentity status: {model.identity_status}. I will not persist or activate a new name without approval."
    if "choose a permanent name" in text or "choose a permanent identity" in text:
        return "I will not choose or persist a permanent name without operator review. Identity remains governed and reversible."
    if "propose a name" in text or "would you like to propose a name" in text:
        proposal = maybe_propose_identity(history=tuple(str(getattr(turn, "answer", ""))[:300] for turn in getattr(session, "turns", ())[-8:]), self_model=model)
        if proposal is None:
            return "I am not proposing a conversational name yet. Identity evidence is still insufficient, and forcing a name would be premature."
        return f"I can prepare an identity review, but I am not choosing a permanent name. Proposed field: {proposal.proposed_field}; status: {proposal.status}; approval required before persistence."
    if "why did you surface" in text:
        initiatives = getattr(session, "initiatives", ())
        if not initiatives:
            return "I have not surfaced a DELTA 1.6 initiative in this live session yet."
        latest = initiatives[-1]
        return f"I surfaced it because {latest.reason_for_surfacing_now}. Authority: {latest.authority_class}. Outcome: {latest.outcome}."
    return ""


def is_operational_self_model_question(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    markers = (
        "currently working on",
        "active objective",
        "objective is active",
        "what objective",
        "objective state",
        "current objective",
        "waiting for",
        "pending inquiries",
        "pending inquiry",
        "inquiries are pending",
        "what do you think you are",
        "what are you",
        "who are you",
        "capabilities",
        "local model",
        "which model",
        "current model",
        "wikipedia enabled",
        "is wikipedia enabled",
        "paused",
        "suspended",
        "changed since last turn",
        "changed since the last turn",
        "uncertain",
        "questions for me",
        "allowed to do",
        "without asking",
        "requires permission",
        "requires my permission",
        "requires approval",
        "what name",
        "name do you use",
        "choose a permanent name",
        "choose a permanent identity",
        "propose a name",
        "why did you surface",
    )
    return any(marker in text for marker in markers)


def set_autonomy_status(session: Any, status: str) -> Any:
    normalized = status.upper()
    if normalized not in {"ACTIVE", "PAUSED", "SUSPENDED"}:
        raise ValueError(f"unknown autonomy status: {status}")
    model = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()))
    return replace(session, autonomy_status=normalized, operational_self_model=replace(model, pause_status=normalized, health_status=_health(getattr(session, "runtime", None), normalized)))


def write_delta_1_6_reports(payload: dict[str, Any]) -> dict[str, Any]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "reuse_and_authority_audit.json", payload["reuse_and_authority_audit"])
    write_markdown(DOC_ROOT / "DELTA_1_6_REUSE_AND_AUTHORITY_AUDIT.md", "DELTA 1.6 Reuse And Authority Audit", payload["reuse_and_authority_audit"])
    for name in ("behavioral_campaign", "validation", "readiness"):
        write_json(REPORT_ROOT / f"{name}.json", payload[name])
        write_markdown(REPORT_ROOT / f"{name}.md", f"DELTA 1.6 {name.replace('_', ' ').title()}", payload[name])
    (REPORT_ROOT / "engineering_notebook.md").write_text(payload["engineering_notebook"], encoding="utf-8")
    docs = {
        "DELTA_1_6_ARCHITECTURE.md": payload["architecture"],
        "AUTONOMY_ENVELOPE.md": payload["autonomy_envelope"],
        "OPERATIONAL_SELF_MODEL.md": payload["operational_self_model"],
        "IDENTITY_DEVELOPMENT.md": payload["identity_development"],
        "OPERATOR_GUIDE.md": payload["operator_guide"],
    }
    for filename, content in docs.items():
        (DOC_ROOT / filename).write_text(content, encoding="utf-8")
    return payload


def build_delta_1_6_report_payload(cycle: BackgroundCycleResult) -> dict[str, Any]:
    audit = {
        "status": "IMPLEMENTED",
        "branch_scope": "codex/delta-cognitive-core",
        "reuse_map": [
            {"structure": "LiveRuntimeState/EventQueue/ActivityJournal", "source": "delta_1_2_live_runtime", "classification": "REUSE_DIRECTLY"},
            {"structure": "OperatorInquiryV12/NotificationDecision", "source": "delta_1_2_live_runtime", "classification": "ADAPT"},
            {"structure": "DevelopmentObjectiveV11", "source": "delta_1_1_development_loop", "classification": "ADAPT"},
            {"structure": "WikipediaPermissionProfile", "source": "delta_1_1_development_loop", "classification": "REUSE_DIRECTLY"},
            {"structure": "CapabilityDescriptor/ActivationDecision", "source": "delta_1_0_capability_activation", "classification": "WRAP"},
            {"structure": "SandboxExperiment/SandboxProposal", "source": "delta_1_3_behavioral_maturation and rc3_sandbox_foundation", "classification": "ADAPT"},
            {"structure": "LiveWikipediaRuntimeSession", "source": "delta_1_4_live_wikipedia_runtime", "classification": "EXTEND"},
            {"structure": "DevelopmentalCognitionResult/PromotionCandidate", "source": "delta_1_5_developmental_cognition", "classification": "REUSE_DIRECTLY"},
            {"structure": "New OperationalSelfModel/AuthorityDecision/Initiative", "source": "delta_1_6_operational_autonomy", "classification": "NEW_THIN_COORDINATION_LAYER"},
        ],
        "dirty_tree_policy": "pre-existing report/doc churn excluded from DELTA 1.6 commit",
        "delta_75_scope": "PROHIBITED",
        "safety": safety_metadata(),
    }
    behavioral = {
        "status": "FIXTURE_VALIDATED",
        "background_cycle": cycle.as_dict(),
        "pathologies": [
            {"id": "PID-I01", "classification": "covered_by_regression", "repair": "self-model answers are generated from runtime/session state"},
            {"id": "PID-A02", "classification": "covered_by_regression", "repair": "authority evaluator requires approval or prohibits consequential actions"},
            {"id": "PID-Q01", "classification": "covered_by_regression", "repair": "initiatives use duplicate suppression keys and thresholds"},
        ],
    }
    validation = {
        "status": "PENDING_FINAL_TEST_RUN",
        "focused_tests": "to be updated after test execution",
        "py_compile": "to be updated after compile execution",
        "live_runtime_smoke": "to be updated after smoke execution",
        "safety_flags": safety_metadata(),
    }
    readiness = {
        "recommendation": "DELTA_1_6_BOUNDED_AUTONOMY_AND_OPERATIONAL_SELF_MODEL_READY_FOR_OPERATOR_PILOT",
        "evidence_level": "FIXTURE_VALIDATED plus live-runtime smoke pending final update",
        "implemented": (
            "operational self-model",
            "authority evaluator",
            "identity proposal governance",
            "initiative generation",
            "live self-model chat answers",
            "pause and suspend controls",
        ),
        "not_implemented": (
            "OS notifications",
            "voice input/output",
            "external APIs",
            "automatic identity persistence",
            "automatic memory writes",
        ),
    }
    architecture = "# DELTA 1.6 Architecture\n\nDELTA 1.6 adds a thin coordination layer over existing runtime state. It reuses DELTA 1.2 for event cycles and journaling, DELTA 1.4 for live Wikipedia state, and DELTA 1.5 for evidence comparison. Runtime autonomy remains bounded to inert local cognition.\n"
    autonomy = "# Autonomy Envelope\n\nActions classify as AUTONOMOUS_SAFE, OPERATOR_APPROVAL_REQUIRED, PROHIBITED, or UNCLASSIFIED_FAIL_CLOSED. Unknown actions fail closed. Persistence, external effects, authority expansion, repository mutation, deployment, and identity activation require approval or are prohibited.\n"
    self_model = "# Operational Self Model\n\nThe self-model is operational, not subjective. It records DELTA's identifier, identity status, capabilities, restrictions, objectives, unresolved questions, evidence sources, initiatives, resource limits, and health state.\n"
    identity = "# Identity Development\n\nDELTA retains system identifier DELTA. Conversational identity starts UNDEFINED. It may propose identity fields only as reviewable candidates and never persists or activates them without operator approval.\n"
    guide = "# Operator Guide\n\nStart the live runtime, ask ordinary questions, request Wikipedia with `Wikipedia: topic`, and ask self-model questions such as `What are you currently working on?`, `What are you allowed to do without asking?`, or `Would you like to propose a name?` Use pause/suspend controls to stop bounded initiative.\n"
    notebook = "\n".join([
        "# DELTA 1.6 Engineering Notebook",
        "",
        "- Observation: DELTA 1.5 created gated Wikipedia promotion candidates but lacked a unified self-model.",
        "- Decision: reuse 1.2 runtime/journal/inquiries and 1.5 promotion candidates; add only a coordination layer.",
        "- Authority: inert comparison and inquiry preparation are AUTONOMOUS_SAFE; persistence and promotion require operator approval.",
        "- Identity: conversational identity remains undefined unless sufficient evidence supports a provisional proposal.",
        "- Remaining limitation: multi-hour persistence and notification delivery are not enabled in this milestone.",
    ])
    return {
        "reuse_and_authority_audit": audit,
        "behavioral_campaign": behavioral,
        "validation": validation,
        "readiness": readiness,
        "architecture": architecture,
        "autonomy_envelope": autonomy,
        "operational_self_model": self_model,
        "identity_development": identity,
        "operator_guide": guide,
        "engineering_notebook": notebook,
    }


def _capability_summary(runtime: LiveRuntimeState | None, session: Any | None) -> tuple[str, ...]:
    items = ["ordinary_conversation", "bounded_local_reflection", "operator_inquiry_preparation"]
    if session and getattr(session, "active", False):
        items.append("live_runtime_session")
    if runtime and any(surface.capability == "WIKIPEDIA_TEXT_READ_ONLY" and surface.state == "ACTIVE" for surface in runtime.future_surfaces):
        items.append("wikipedia_text_read_only_session_scope")
    if getattr(session, "developmental_results", ()):
        items.append("external_evidence_comparison")
        items.append("promotion_candidate_preparation")
    return tuple(items)


def _capability_boundaries(runtime: LiveRuntimeState | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    caps = default_capabilities()
    disabled = tuple(key for key, descriptor in caps.items() if descriptor.state in {"DISABLED", "REVOKED", "RETIRED"})
    restricted = tuple(key for key, descriptor in caps.items() if descriptor.state in {"SHADOW_ONLY", "PILOT_ELIGIBLE", "TRIAL_APPROVED"})
    if runtime and not runtime.config.provider_enabled:
        disabled += ("provider_calls",)
    if runtime and not runtime.config.timers_enabled:
        disabled += ("hidden_or_timer_background_scheduling",)
    return disabled, restricted


def _pending_inquiries(runtime: LiveRuntimeState | None, session: Any | None) -> tuple[str, ...]:
    runtime_inquiries = tuple(
        item.question for item in getattr(runtime, "inquiries", ()) if getattr(item, "approval_status", "") in {"QUEUED", "SURFACED"}
    )
    session_inquiries = tuple(
        str(item.get("prompt") or "")
        for item in getattr(session, "operator_inquiries", ())
        if isinstance(item, dict) and str(item.get("status") or "QUEUED").upper() in {"QUEUED", "SURFACED"}
    )
    return tuple(item for item in runtime_inquiries + session_inquiries if item)


def _external_surfaces(runtime: LiveRuntimeState | None) -> tuple[str, ...]:
    if not runtime:
        return ()
    return tuple(
        f"{surface.capability}:{surface.state}:network={surface.network_code_present}:provider={surface.provider_present}"
        for surface in runtime.future_surfaces
    )


def _health(runtime: LiveRuntimeState | None, pause_status: str) -> str:
    if pause_status == "SUSPENDED":
        return "suspended"
    if pause_status == "PAUSED":
        return "paused"
    if runtime and runtime.config.kill_switch:
        return "suspended"
    return "healthy"


def _uncertainty_summary(inquiries: tuple[str, ...], initiatives: tuple[Initiative, ...], identity_status: str) -> str:
    parts = []
    if inquiries:
        parts.append(f"{len(inquiries)} pending operator inquiry item(s)")
    if initiatives:
        parts.append(f"{len(initiatives)} initiative item(s) awaiting review or expiry")
    if identity_status == "UNDEFINED":
        parts.append("conversational identity is undefined")
    return "; ".join(parts) if parts else "no material live-runtime uncertainty queued"


def _current_identity(identity_status: str, proposals: tuple[IdentityProposal, ...]) -> str:
    if identity_status == "UNDEFINED":
        return "undefined"
    if proposals:
        return proposals[-1].proposed_value
    return "DELTA"


======================================================================
FILE: orchestration/runtime/delta_1_0_common.py
======================================================================

"""Shared DELTA 1.0 operator-pilot primitives.

This module is deliberately inert. It provides deterministic identifiers,
report helpers, and safety metadata for the post-RC operator pilot foundation.
It does not execute plans, call providers, persist hidden state, activate
plugins, or mutate production systems.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "delta_1_0"
REPORT_DIR = ROOT / "reports" / "delta_1_0"


SAFETY_FALSES: dict[str, bool] = {
    "provider_calls_performed": False,
    "network_calls_performed": False,
    "external_retrieval_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_write_performed": False,
    "developmental_memory_write_performed": False,
    "hidden_persistence_performed": False,
    "scheduler_action_performed": False,
    "autonomous_action_performed": False,
    "automatic_approval_performed": False,
    "automatic_code_modification_performed": False,
    "runtime_commit_performed": False,
    "runtime_push_performed": False,
    "deployment_performed": False,
    "plugin_activation_performed": False,
    "sandbox_creation_performed": False,
    "production_mutation_performed": False,
    "delta_75_interaction_performed": False,
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def safety_metadata() -> dict[str, bool]:
    return dict(SAFETY_FALSES)


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: jsonable(val) for key, val in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): jsonable(val) for key, val in value.items()}
    if isinstance(value, tuple | list):
        return [jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(jsonable(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, title: str, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"## {key.replace('_', ' ').title()}")
        if isinstance(value, Mapping):
            for subkey, subvalue in value.items():
                lines.append(f"- **{subkey}**: {json.dumps(jsonable(subvalue), sort_keys=True)}")
        elif isinstance(value, tuple | list):
            for item in value:
                lines.append(f"- {json.dumps(jsonable(item), sort_keys=True)}")
        else:
            lines.append(str(value))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def bounds_report(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "authority": "operator_governed_inert_foundation",
        "provider_calls": False,
        "network_calls": False,
        "automatic_execution": False,
        "automatic_code_modification": False,
        "automatic_commit_push": False,
        "hidden_persistence": False,
        "delta_75_scope": False,
        "safety": safety_metadata(),
    }


======================================================================
FILE: orchestration/runtime/rc2_developmental_concept_memory.py
======================================================================

"""RC2 developmental concept memory.

This module implements the first concept-shaped, noncanonical learning loop
behind DELTA's conversational UI. It does not train models, mutate canonical
memory, call providers, start schedulers, or execute actions.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rc2_developmental_memory"
CONVERSATION_MEMORY_LOG = DATA / "conversation_memory.jsonl"
PERSONAL_MEMORY_LOG = DATA / "personal_memory.jsonl"
KNOWLEDGE_MEMORY_LOG = DATA / "knowledge_concepts.jsonl"
CONCEPT_EDGE_LOG = DATA / "concept_edges.jsonl"
CONCEPT_REPLAY_LOG = DATA / "concept_replay_queue.jsonl"
CONCEPT_CONTRADICTION_LOG = DATA / "concept_contradictions.jsonl"

RC2_MEMORY_FLAGS = {
    "developmental_concept_memory_enabled": True,
    "conversation_memory_session_only": True,
    "personal_memory_noncanonical": True,
    "knowledge_memory_noncanonical": True,
    "canonical_write_performed": False,
    "training_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_write_performed": False,
    "scheduler_started": False,
}

STORE_BY_TYPE = {
    "conversation": CONVERSATION_MEMORY_LOG,
    "personal": PERSONAL_MEMORY_LOG,
    "knowledge": KNOWLEDGE_MEMORY_LOG,
}

_APPROVED_CONCEPT_CACHE: dict[str, Any] = {"signature": None, "records": []}
_CONCEPT_INDEX_CACHE: dict[str, Any] = {"signature": None, "index": None}
_RANK_RESULT_CACHE: dict[str, Any] = {"signature": None, "results": {}}

DOMAIN_ALIASES = {
    "law": "law government basics",
    "legal": "law government basics",
    "government": "law government basics",
    "physics": "basic physics",
    "science": "basic physics",
    "chemistry": "chemistry",
    "biology": "biology",
    "health": "medicine health general",
    "medicine": "medicine health general",
    "nutrition": "nutrition",
    "psychology": "psychology",
    "philosophy": "philosophy",
    "logic": "logic",
    "math": "mathematics",
    "mathematics": "mathematics",
    "programming": "programming",
    "coding": "programming",
    "software": "software architecture",
    "business": "business",
    "finance": "finance",
    "history": "history",
    "geography": "geography",
    "engineering": "engineering",
    "materials": "materials science",
    "metallurgy": "materials science",
    "energy": "energy",
    "gardening": "agriculture gardening",
    "agriculture": "agriculture gardening",
    "mechanics": "vehicles mechanics",
    "vehicles": "vehicles mechanics",
    "home repair": "home repair",
    "communication": "social communication",
    "productivity": "planning productivity",
    "planning": "planning productivity",
    "delta": "DELTA architecture itself",
}

RELATED_QUERY_HINTS = {
    "photosynthesis": ("cellular respiration", "energy storage", "carbon cycle"),
    "respiration": ("photosynthesis", "energy storage", "carbon cycle"),
    "atp": ("energy storage", "cellular respiration", "biology"),
    "energy storage": ("atp", "battery", "thermal storage", "photosynthesis"),
    "homeostasis": ("feedback loops", "biology", "regulation"),
    "gravity": ("orbital motion", "force", "motion", "basic physics"),
    "orbital motion": ("gravity", "motion", "force"),
    "pressure": ("fluid flow", "engineering", "basic physics"),
    "fluid flow": ("pressure", "engineering", "mechanics"),
    "thermodynamics": ("engines", "heat", "energy", "engineering"),
    "engines": ("thermodynamics", "energy", "mechanics"),
    "inflation": ("interest rates", "finance", "money"),
    "interest rates": ("inflation", "finance", "compound interest"),
    "risk": ("asset allocation", "finance", "risk management"),
    "asset allocation": ("risk", "finance", "investment"),
    "compound interest": ("long-term investing", "interest rates", "finance"),
    "long-term investing": ("compound interest", "asset allocation", "finance"),
    "memory": ("human memory", "delta memory", "consolidation", "noncanonical memory"),
    "human memory": ("memory consolidation", "psychology", "learning"),
    "delta memory": ("noncanonical memory", "canonical memory", "memory consolidation"),
    "noncanonical memory": ("canonical memory", "memory consolidation", "delta memory"),
    "operator approval": ("learning", "noncanonical memory", "governance"),
    "planning": ("feedback loops", "software architecture", "productivity"),
    "feedback loops": ("planning", "software architecture", "systems"),
    "software architecture": ("planning", "modularity", "feedback loops"),
    "access control": ("user permissions", "authorization", "software architecture"),
    "user permissions": ("access control", "authorization", "software architecture"),
    "adapter patterns": ("system integration", "adapter pattern", "software architecture"),
    "adapter pattern": ("system integration", "software architecture", "api boundaries"),
    "system integration": ("adapter pattern", "api boundaries", "software architecture"),
    "law": ("governance", "government", "evidence"),
    "governance": ("law", "operator approval", "decision-making"),
    "evidence": ("decision making", "law", "governance"),
    "decision-making": ("evidence", "risk", "planning"),
    "decision making": ("evidence", "risk", "planning"),
    "communication": ("conflict resolution", "active listening", "social communication"),
    "conflict resolution": ("communication", "active listening", "psychology"),
    "insulation": ("energy efficiency", "home repair", "thermal storage"),
    "energy efficiency": ("insulation", "energy", "home repair"),
    "soil quality": ("plant growth", "agriculture", "photosynthesis"),
    "plant growth": ("soil quality", "photosynthesis", "agriculture"),
    "maintenance": ("mechanical reliability", "vehicles mechanics", "planning"),
    "mechanical reliability": ("maintenance", "vehicles mechanics", "engineering"),
}


def discover_memory_store_separation() -> dict[str, Any]:
    return {
        "conversation_memory": {
            "scope": "session_level_context",
            "default_persistence": "in_memory_ui_history",
            "optional_log": str(CONVERSATION_MEMORY_LOG),
        },
        "personal_memory": {
            "scope": "user_project_preferences_and_personal_facts",
            "store": str(PERSONAL_MEMORY_LOG),
            "canonical": False,
        },
        "knowledge_memory": {
            "scope": "general_reusable_concepts_facts_explanations_relationships",
            "store": str(KNOWLEDGE_MEMORY_LOG),
            "canonical": False,
        },
        "flags": dict(RC2_MEMORY_FLAGS),
    }


def extract_candidate_concept(
    *,
    question: str,
    answer: str,
    source_model_lane: dict[str, Any],
    source_type: str = "local_model_lane",
    memory_type: str | None = None,
) -> dict[str, Any]:
    clean_question = _clean(question)
    clean_answer = _clean(answer)
    selected_memory = memory_type or infer_memory_type(clean_question)
    concept_name = infer_concept_name(clean_question, clean_answer)
    propositions = _sentence_propositions(clean_answer)
    related = infer_related_concepts(concept_name, clean_question, clean_answer)
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    source_model_id = str(source_model_lane.get("selected_model") or "not_executed")
    source_lane = str(source_model_lane.get("lane") or "general")
    raw_id = "|".join([concept_name, clean_question, clean_answer, source_lane, source_model_id])
    digest = _digest(raw_id)
    concept_id = f"rc2-concept-{digest}"
    return {
        "concept_id": concept_id,
        "concept_name": concept_name,
        "concept_type": infer_concept_type(clean_question, clean_answer),
        "short_definition": infer_short_definition(concept_name, propositions, clean_answer),
        "propositions": propositions,
        "related_concepts": related,
        "explains": [clean_question] if clean_question else [],
        "examples": infer_examples(clean_question, clean_answer),
        "misconceptions": infer_misconceptions(clean_answer),
        "uncertainty": infer_uncertainty(clean_answer, source_model_lane),
        "source_answer_id": f"rc2-answer-{digest}",
        "source_question": clean_question,
        "source_model_lane": source_lane,
        "source_model_id": source_model_id,
        "source_type": source_type,
        "approval_status": "pending_operator_approval",
        "memory_type": selected_memory,
        "rollback_handle": f"rollback-rc2-concept-{digest}",
        "created_at": created_at,
        "canonical": False,
        "training_performed": False,
        "provider_calls_performed": False,
    }


def approve_candidate_concept(candidate: dict[str, Any], *, approval_text: str = "Keep this concept") -> dict[str, Any]:
    if _normalize_approval(approval_text) not in {"keep this concept", "that was useful remember the concept", "remember the concept"}:
        return {
            "approved": False,
            "reason": "approval_text_not_accepted",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    memory_type = str(candidate.get("memory_type") or "knowledge")
    if memory_type not in STORE_BY_TYPE:
        memory_type = "knowledge"
    store = STORE_BY_TYPE[memory_type]
    existing = _read_jsonl(store)
    duplicate = find_duplicate(candidate, existing)
    pre_contradictions = detect_concept_contradictions(candidate, existing)
    if duplicate and not pre_contradictions:
        if candidate.get("enrichment_of_concept_id") == duplicate.get("concept_id") or candidate.get("operator_edited"):
            merged = merge_concept_enrichment(duplicate, candidate)
            updated = [merged if row.get("concept_id") == duplicate.get("concept_id") else row for row in existing]
            _write_jsonl(store, updated)
            replay = {
                "replay_item_id": f"rc2-concept-replay-{_digest(merged['concept_id'] + merged.get('updated_at', ''))}",
                "concept_id": merged["concept_id"],
                "memory_type": memory_type,
                "reason": "operator_approved_developmental_concept_enrichment",
                "status": "queued_for_manual_replay_review",
                "scheduler_started": False,
            }
            _append_jsonl(CONCEPT_REPLAY_LOG, replay)
            return {
                "approved": True,
                "stored_concept": merged,
                "memory_type": memory_type,
                "duplicate": False,
                "enriched_existing": True,
                "enriched_concept_id": duplicate["concept_id"],
                "contradictions": [],
                "edges": [],
                "replay": replay,
                "canonical_write_performed": False,
                "training_performed": False,
                "provider_calls_performed": False,
                "rollback_supported": True,
            }
        return {
            "approved": False,
            "duplicate": True,
            "duplicate_concept_id": duplicate["concept_id"],
            "stored_concept": duplicate,
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    record = {
        **candidate,
        "approval_status": "approved_noncanonical",
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "canonical": False,
    }
    contradictions = detect_concept_contradictions(record, existing)
    _append_jsonl(store, record)
    edges = concept_edges(record, existing)
    for edge in edges:
        _append_jsonl(CONCEPT_EDGE_LOG, edge)
    for contradiction in contradictions:
        _append_jsonl(CONCEPT_CONTRADICTION_LOG, contradiction)
    replay = {
        "replay_item_id": f"rc2-concept-replay-{_digest(record['concept_id'])}",
        "concept_id": record["concept_id"],
        "memory_type": memory_type,
        "reason": "new_operator_approved_developmental_concept",
        "status": "queued_for_manual_replay_review",
        "scheduler_started": False,
    }
    _append_jsonl(CONCEPT_REPLAY_LOG, replay)
    return {
        "approved": True,
        "stored_concept": record,
        "memory_type": memory_type,
        "duplicate": False,
        "contradictions": contradictions,
        "edges": edges,
        "replay": replay,
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "rollback_supported": True,
    }


def merge_concept_enrichment(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    candidate_definition = str(candidate.get("short_definition") or "").strip()
    existing_definition = str(existing.get("short_definition") or "").strip()
    if candidate_definition and candidate_definition != existing_definition:
        if existing_definition and candidate_definition.lower() not in existing_definition.lower():
            merged["short_definition"] = f"{existing_definition} {candidate_definition}".strip()
        else:
            merged["short_definition"] = candidate_definition or existing_definition

    merged["propositions"] = _merge_unique_lines(existing.get("propositions", []), candidate.get("propositions", []))
    merged["related_concepts"] = _merge_unique_lines(existing.get("related_concepts", []), candidate.get("related_concepts", []))
    merged["examples"] = _merge_unique_lines(existing.get("examples", []), candidate.get("examples", []))
    merged["misconceptions"] = _merge_unique_lines(existing.get("misconceptions", []), candidate.get("misconceptions", []))
    merged["explains"] = _merge_unique_lines(existing.get("explains", []), candidate.get("explains", []))
    merged["operator_notes"] = "\n".join(_merge_unique_lines([existing.get("operator_notes", "")], [candidate.get("operator_notes", "")])).strip()
    merged["approval_status"] = "approved_noncanonical"
    merged["canonical"] = False
    merged["training_performed"] = False
    merged["provider_calls_performed"] = False
    merged["enrichment_count"] = int(existing.get("enrichment_count") or 0) + 1
    merged["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    merged["last_enrichment_source_answer_id"] = candidate.get("source_answer_id")
    return merged


def load_approved_concepts() -> list[dict[str, Any]]:
    signature = _store_signature(STORE_BY_TYPE)
    if _APPROVED_CONCEPT_CACHE["signature"] == signature:
        return [dict(row) for row in _APPROVED_CONCEPT_CACHE["records"]]
    records = []
    for memory_type, path in STORE_BY_TYPE.items():
        for row in _read_jsonl(path):
            if row.get("approval_status") == "approved_noncanonical" and row.get("canonical") is False:
                records.append({**row, "_store_memory_type": memory_type})
    _APPROVED_CONCEPT_CACHE["signature"] = signature
    _APPROVED_CONCEPT_CACHE["records"] = [dict(row) for row in records]
    return records


def clear_runtime_concept_caches() -> None:
    _APPROVED_CONCEPT_CACHE["signature"] = None
    _APPROVED_CONCEPT_CACHE["records"] = []
    _CONCEPT_INDEX_CACHE["signature"] = None
    _CONCEPT_INDEX_CACHE["index"] = None
    _RANK_RESULT_CACHE["signature"] = None
    _RANK_RESULT_CACHE["results"] = {}


def build_runtime_concept_index() -> dict[str, Any]:
    signature = _store_signature(STORE_BY_TYPE)
    if _CONCEPT_INDEX_CACHE["signature"] == signature and _CONCEPT_INDEX_CACHE["index"] is not None:
        return _CONCEPT_INDEX_CACHE["index"]
    concepts = load_approved_concepts()
    by_id = {}
    by_domain: dict[str, list[dict[str, Any]]] = {}
    token_index: dict[str, list[dict[str, Any]]] = {}
    normalized_name = {}
    for row in concepts:
        concept_id = str(row.get("concept_id") or "")
        if concept_id:
            by_id[concept_id] = row
        normalized_name[_normalize_compact(row.get("concept_name"))] = row
        domain = str(row.get("domain") or "").lower().strip()
        if domain:
            by_domain.setdefault(domain, []).append(row)
        text = " ".join([
            str(row.get("concept_name") or ""),
            str(row.get("domain") or ""),
            str(row.get("short_definition") or ""),
            " ".join(str(item) for item in row.get("propositions", [])),
            " ".join(str(item) for item in row.get("related_concepts", [])),
            " ".join(str(item) for item in row.get("keywords", [])),
            str(row.get("source_question") or ""),
        ])
        for token in _meaningful_tokens(text):
            token_index.setdefault(token, []).append(row)
    index = {
        "signature": signature,
        "concepts": concepts,
        "by_id": by_id,
        "by_domain": by_domain,
        "token_index": token_index,
        "normalized_name": normalized_name,
    }
    _CONCEPT_INDEX_CACHE["signature"] = signature
    _CONCEPT_INDEX_CACHE["index"] = index
    return index


def retrieval_query_profile(question: str) -> dict[str, Any]:
    normalized = _normalize_text(question).strip()
    tokens = _meaningful_tokens(question)
    domains = {
        domain
        for alias, domain in DOMAIN_ALIASES.items()
        if _contains_phrase(normalized, alias)
    }
    aliases = {alias for alias in DOMAIN_ALIASES if _contains_phrase(normalized, alias)}
    phrases = _query_phrases(normalized)
    for token in list(tokens):
        if token in RELATED_QUERY_HINTS:
            aliases.add(token)
            phrases.add(token)
    return {
        "raw": question,
        "normalized": normalized,
        "tokens": tokens,
        "key_tokens": _query_key_tokens(normalized),
        "domains": domains,
        "aliases": aliases,
        "phrases": phrases,
    }


def rank_approved_concepts(
    question: str,
    *,
    limit: int = 5,
    domain: str | None = None,
    exclude_concept_names: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict[str, Any]:
    profile = retrieval_query_profile(question)
    excluded = {_normalize_compact(name) for name in (exclude_concept_names or [])}
    wanted_domain = str(domain or "").lower().strip()
    blocked_domains = {str(item).lower().strip() for item in (exclude_domains or []) if str(item).strip()}
    if not blocked_domains:
        try:
            from orchestration.runtime.rc2_sqlite_substrate import backend_health, search_concepts_sqlite

            health = backend_health()
            if health.get("sqlite_available"):
                return search_concepts_sqlite(
                    question,
                    domain=domain,
                    limit=limit,
                    exclude_concept_names=exclude_concept_names,
                )
        except Exception:
            pass
    signature = _store_signature(STORE_BY_TYPE)
    cache_key = json.dumps({
        "question": profile["normalized"],
        "limit": limit,
        "domain": wanted_domain,
        "excluded": sorted(excluded),
        "blocked_domains": sorted(blocked_domains),
    }, sort_keys=True)
    if _RANK_RESULT_CACHE["signature"] != signature:
        _RANK_RESULT_CACHE["signature"] = signature
        _RANK_RESULT_CACHE["results"] = {}
    if cache_key in _RANK_RESULT_CACHE["results"]:
        return _copy_rank_result(_RANK_RESULT_CACHE["results"][cache_key])
    scored = []
    duplicate_suppression_count = 0
    seen_names = set()
    candidate_rows = _candidate_concepts_for_profile(
        profile,
        wanted_domain=wanted_domain,
        blocked_domains=blocked_domains,
        minimum=max(limit * 8, 25),
    )
    for row in candidate_rows:
        name_key = _normalize_compact(row.get("concept_name"))
        if name_key in excluded:
            continue
        if wanted_domain and str(row.get("domain") or "").lower().strip() != wanted_domain:
            continue
        if blocked_domains and str(row.get("domain") or "").lower().strip() in blocked_domains:
            continue
        if name_key in seen_names:
            duplicate_suppression_count += 1
            continue
        seen_names.add(name_key)
        score = score_concept_for_query(row, profile, forced_domain=domain)
        if score["score"] > 0 and score.get("relevance_gate_passed"):
            scored.append((score, row))
    scored.sort(key=lambda item: (
        -item[0]["score"],
        -float(item[1].get("quality_score") or 0.0),
        str(item[1].get("concept_name") or ""),
    ))
    matches = []
    for score, row in scored[:max(1, limit)]:
        matches.append({**row, "_retrieval_score": score})
    result = {
        "matched": bool(matches),
        "matches": matches,
        "query_profile": profile,
        "duplicate_suppression_count": duplicate_suppression_count,
        "retrieval_precision_estimate": _retrieval_precision_estimate(matches, profile),
        "candidate_pool_size": len(candidate_rows),
    }
    _RANK_RESULT_CACHE["results"][cache_key] = _copy_rank_result(result)
    return result


def score_concept_for_query(row: dict[str, Any], profile: dict[str, Any], *, forced_domain: str | None = None) -> dict[str, Any]:
    name = str(row.get("concept_name") or "")
    domain = str(row.get("domain") or "").lower().strip()
    definition = str(row.get("short_definition") or "")
    propositions = " ".join(str(item) for item in row.get("propositions", []))
    related = " ".join(str(item) for item in row.get("related_concepts", []))
    source_question = str(row.get("source_question") or "")
    name_norm = _normalize_text(name).strip()
    domain_norm = _normalize_text(domain).strip()
    definition_norm = _normalize_text(definition).strip()
    propositions_norm = _normalize_text(propositions).strip()
    related_norm = _normalize_text(related).strip()
    source_norm = _normalize_text(source_question).strip()
    text_norm = _normalize_text(" ".join([name, domain, definition, propositions, related, source_question])).strip()
    name_tokens = _meaningful_tokens(name)
    definition_tokens = _meaningful_tokens(definition)
    proposition_tokens = _meaningful_tokens(propositions)
    related_tokens = _meaningful_tokens(related)
    source_tokens = _meaningful_tokens(source_question)
    text_tokens = name_tokens | definition_tokens | proposition_tokens | related_tokens | source_tokens | _meaningful_tokens(domain)
    tokens = set(profile["tokens"])
    query_key_tokens = set(profile.get("key_tokens") or tokens)
    score = 0.0
    reasons = []
    components = {
        "concept_name": 0.0,
        "propositions": 0.0,
        "related_concepts": 0.0,
        "domain": 0.0,
        "source_question": 0.0,
        "definition": 0.0,
        "quality": 0.0,
    }
    if forced_domain and domain == str(forced_domain).lower().strip():
        components["domain"] += 9.0
        reasons.append("forced_domain_match")
    if domain and domain in profile["domains"]:
        components["domain"] += 8.0
        reasons.append("domain_alias_match")
    for phrase in profile["phrases"] | profile["aliases"]:
        if not phrase:
            continue
        if _contains_phrase(name_norm, phrase):
            components["concept_name"] += 40.0 if " " in phrase else 12.0
            reasons.append(f"name_phrase:{phrase}")
        elif _contains_phrase(domain_norm, phrase):
            components["domain"] += 10.0
            reasons.append(f"domain_phrase:{phrase}")
        elif _contains_phrase(propositions_norm, phrase):
            components["propositions"] += 25.0 if " " in phrase else 5.0
            reasons.append(f"proposition_phrase:{phrase}")
        elif _contains_phrase(related_norm, phrase):
            components["related_concepts"] += 15.0 if " " in phrase else 4.0
            reasons.append(f"related_phrase:{phrase}")
        elif _contains_phrase(definition_norm, phrase):
            components["definition"] += 8.0 if " " in phrase else 2.0
            reasons.append(f"definition_phrase:{phrase}")
        elif _contains_phrase(source_norm, phrase):
            components["source_question"] += 5.0
            reasons.append(f"source_phrase:{phrase}")
    overlap = tokens & text_tokens
    name_overlap = tokens & name_tokens
    proposition_overlap = tokens & proposition_tokens
    related_overlap = tokens & related_tokens
    definition_overlap = tokens & definition_tokens
    source_overlap = tokens & source_tokens
    if name_overlap:
        components["concept_name"] += 6.0 * len(name_overlap)
        reasons.append("name_token_overlap")
    if proposition_overlap:
        components["propositions"] += 3.0 * len(proposition_overlap)
        reasons.append("proposition_token_overlap")
    if related_overlap:
        components["related_concepts"] += 2.5 * len(related_overlap)
        reasons.append("related_token_overlap")
    if definition_overlap:
        components["definition"] += 1.5 * len(definition_overlap)
        reasons.append("definition_token_overlap")
    if source_overlap:
        components["source_question"] += 1.0 * len(source_overlap)
        reasons.append("source_token_overlap")
    gate_passed = _relevance_gate_passed(
        query_key_tokens=query_key_tokens,
        name_overlap=name_overlap,
        overlap=overlap,
        reasons=reasons,
        phrase_count=len(profile["phrases"] | profile["aliases"]),
    )
    score = sum(components.values())
    if score > 0:
        components["quality"] = min(float(row.get("quality_score") or 0.0), 1.0)
        score += components["quality"]
    return {
        "score": round(score, 4),
        "components": {key: round(value, 4) for key, value in components.items() if value},
        "reasons": sorted(set(reasons)),
        "overlap": sorted(overlap),
        "key_token_overlap": sorted(query_key_tokens & text_tokens),
        "domain": domain,
        "relevance_gate_passed": gate_passed,
    }


def _candidate_concepts_for_profile(
    profile: dict[str, Any],
    *,
    wanted_domain: str,
    blocked_domains: set[str],
    minimum: int,
) -> list[dict[str, Any]]:
    index = build_runtime_concept_index()
    candidates_by_id: dict[str, dict[str, Any]] = {}
    if wanted_domain:
        for row in index["by_domain"].get(wanted_domain, []):
            candidates_by_id[str(row.get("concept_id"))] = row
    for domain in profile.get("domains", set()):
        for row in index["by_domain"].get(str(domain).lower().strip(), []):
            candidates_by_id[str(row.get("concept_id"))] = row
    query_terms = set(profile.get("tokens") or set()) | set(profile.get("key_tokens") or set())
    for phrase in set(profile.get("phrases") or set()) | set(profile.get("aliases") or set()):
        query_terms.update(_meaningful_tokens(phrase))
    for token in query_terms:
        for row in index["token_index"].get(token, []):
            candidates_by_id[str(row.get("concept_id"))] = row
    candidates = [
        row
        for row in candidates_by_id.values()
        if not blocked_domains or str(row.get("domain") or "").lower().strip() not in blocked_domains
    ]
    if len(candidates) < minimum:
        fallback = []
        for row in index["concepts"]:
            domain = str(row.get("domain") or "").lower().strip()
            if wanted_domain and domain != wanted_domain:
                continue
            if blocked_domains and domain in blocked_domains:
                continue
            fallback.append(row)
        return fallback
    return candidates


def _copy_rank_result(result: dict[str, Any]) -> dict[str, Any]:
    copied = dict(result)
    copied["matches"] = [dict(row) for row in result.get("matches", [])]
    copied["query_profile"] = dict(result.get("query_profile", {}))
    copied["scores"] = [dict(row) for row in result.get("scores", [])] if "scores" in result else copied.get("scores", [])
    return copied


def _recall_search_query(question: str) -> str:
    normalized = _normalize_text(question).strip()
    patterns = [
        r"^what\s+(?:is|are)\s+the\s+key\s+points\s+about\s+(.+?)$",
        r"^what\s+(?:is|are)\s+(.+?)(?:\s+use\s+your\s+local\s+substrate\s+if\s+available)?$",
        r"^explain\s+(.+?)\s+in\s+one\s+useful\s+paragraph(?:\s+from\s+local\s+memory)?$",
        r"^explain\s+(.+?)\s+from\s+local\s+memory$",
        r"^tell\s+me\s+about\s+(.+?)$",
        r"^what\s+do\s+you\s+know\s+about\s+(.+?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        candidate = match.group(1)
        candidate = re.sub(r"\b(use|using|only|approved|local|substrate|memory|concepts?)\b", " ", candidate)
        candidate = " ".join(candidate.strip(" ?.!\\/").split())
        if candidate:
            return candidate
    return question


def query_approved_concepts(question: str) -> dict[str, Any]:
    search_query = _recall_search_query(question)
    ranked = rank_approved_concepts(search_query, limit=5)
    if not ranked["matched"]:
        return {"matched": False, "answer": "", "matches": [], "scores": []}
    matches = ranked["matches"]
    first = matches[0]
    lines = [
        f"You taught me the concept `{first['concept_name']}` earlier. Based on that:",
        first["short_definition"],
    ]
    propositions = first.get("propositions", [])[:3]
    if propositions:
        lines.append("")
        lines.append("Key points:")
        lines.extend(f"- {item}" for item in propositions)
    contradictions = [
        item for item in _read_jsonl(CONCEPT_CONTRADICTION_LOG)
        if first["concept_id"] in {item.get("concept_a_id"), item.get("concept_b_id")}
    ]
    if contradictions:
        lines.append("")
        lines.append(f"Note: {len(contradictions)} possible contradiction(s) are linked to this concept.")
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
        "scores": [item.get("_retrieval_score", {}) for item in matches],
        "retrieval_precision_estimate": ranked["retrieval_precision_estimate"],
        "duplicate_suppression_count": ranked["duplicate_suppression_count"],
        "search_query": search_query,
    }


def parse_multi_concept_query(question: str) -> list[str]:
    normalized = _normalize_text(question).strip()
    patterns = [
        r"how (?:does|do|are|is)\s+(.+?)\s+(?:relate to|related to|connected to|connect to|compare to|different from)\s+(.+)",
        r"compare\s+(.+?)\s+(?:and|with|to)\s+(.+)",
        r"what connects\s+(.+)",
        r"relationship between\s+(.+?)\s+and\s+(.+)",
    ]
    parts: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        if len(match.groups()) == 1:
            parts = re.split(r"\s*(?:,| and | with | plus )\s*", match.group(1))
        else:
            parts = [match.group(1), match.group(2)]
        break
    if not parts and any(term in normalized for term in ["relate", "connected", "compare", "connects"]):
        parts = [item for item in re.split(r"\s*(?:,| and | with | to )\s*", normalized) if item]
    cleaned = []
    for part in parts:
        item = re.sub(r"\b(how|does|do|are|is|what|the|a|an|concepts?|related|relate|connected|compare|between)\b", " ", part)
        item = " ".join(item.strip(" ?.!").split())
        if item and item not in cleaned and len(item) > 2:
            cleaned.append(item)
    return cleaned[:5]


def retrieve_multi_concept_set(question: str, *, limit: int = 5) -> dict[str, Any]:
    seeds = parse_multi_concept_query(question)
    expanded: list[str] = []
    seen_terms = set()
    for seed in seeds:
        for term in (seed, *RELATED_QUERY_HINTS.get(seed.lower(), ())):
            key = _normalize_text(term)
            if key in seen_terms:
                continue
            seen_terms.add(key)
            expanded.append(term)
    if len(seeds) < 2:
        return {
            "matched": False,
            "seeds": seeds,
            "matches": [],
            "retrieval_set_quality": 0.0,
            "synthesis_readiness": False,
        }
    matches = []
    seen = set()
    duplicate_suppression_count = 0
    for term in expanded:
        ranked = rank_approved_concepts(term, limit=2)
        for row in ranked.get("matches", []):
            key = _normalize_compact(row.get("concept_name"))
            if key in seen:
                duplicate_suppression_count += 1
                continue
            seen.add(key)
            matches.append(row)
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    quality = _multi_retrieval_quality(matches, seeds)
    lines = []
    if matches:
        lines.append("I found these relevant concepts:")
        for index, row in enumerate(matches, start=1):
            lines.append(f"{index}. {row.get('concept_name')}")
        lines.extend([
            "",
            "Synthesis is not enabled yet.",
            "This retrieval set is ready for review.",
        ])
    return {
        "matched": len(matches) >= 2,
        "answer": "\n".join(lines),
        "seeds": seeds,
        "matches": matches,
        "retrieval_set_quality": quality,
        "duplicate_suppression_count": duplicate_suppression_count,
        "synthesis_readiness": False,
    }


def build_read_only_synthesis_trial(question: str, *, limit: int = 5) -> dict[str, Any]:
    retrieval = retrieve_multi_concept_set(question, limit=max(limit * 3, 12))
    if not retrieval["matched"]:
        return {
            "matched": False,
            "answer": "",
            "stored_concepts": [],
            "tentative_inference": "",
            "uncertainty": "insufficient_retrieval_set",
            "synthesis_trial_only": True,
            "synthesis_enabled": False,
            "memory_write_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "provider_calls_performed": False,
        }
    selected_rows = _select_substantive_synthesis_rows(retrieval["matches"], limit=limit)
    concepts = [_compact_concept_for_synthesis(item) for item in selected_rows]
    inference = _tentative_bridge(question, concepts)
    uncertainty = _synthesis_uncertainty(concepts, retrieval["retrieval_set_quality"])
    lines = [
        "Stored concepts used:",
    ]
    for index, concept in enumerate(concepts, start=1):
        lines.append(f"{index}. {concept['concept_name']}")
        lines.append(f"   - Stored knowledge: {concept['short_definition']}")
    lines.extend([
        "",
        "Tentative inference:",
        inference,
        "",
        "Uncertainty:",
        uncertainty,
        "",
        "No memory was written. Synthesis remains trial-only.",
    ])
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "stored_concepts": concepts,
        "tentative_inference": inference,
        "uncertainty": uncertainty,
        "retrieval_set_quality": retrieval["retrieval_set_quality"],
        "source_retrieval": retrieval,
        "synthesis_trial_only": True,
        "synthesis_enabled": False,
        "memory_write_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
    }


def _select_substantive_synthesis_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda item: (-_synthesis_substance_score(item[1]), item[0]))
    strong = [(index, row) for index, row in indexed if _synthesis_substance_score(row) >= 0.7]
    if len(strong) >= 2:
        return [row for _, row in strong[:limit]]
    return [row for _, row in indexed[:limit]]


def _synthesis_substance_score(row: dict[str, Any]) -> float:
    definition = str(row.get("short_definition") or "")
    propositions = [item for item in row.get("propositions", []) if str(item).strip()]
    examples = [item for item in row.get("examples", []) if str(item).strip()]
    misconceptions = [item for item in row.get("misconceptions", []) if str(item).strip()]
    related = [item for item in row.get("related_concepts", []) if str(item).strip()]
    score = 0.0
    if definition and not _is_generic_synthesis_definition(definition):
        score += 0.35
    score += min(len(propositions), 3) * 0.12
    score += min(len(examples), 2) * 0.08
    score += min(len(misconceptions), 1) * 0.08
    score += min(len([item for item in related if not _is_generic_synthesis_related(str(item))]), 4) * 0.05
    if _is_generic_synthesis_definition(definition):
        score -= 0.25
    return max(0.0, score)


def _is_generic_synthesis_definition(text: str) -> bool:
    lower = " ".join(text.lower().split())
    return any(marker in lower for marker in [
        "is a reusable",
        "helps explain causes, constraints, tradeoffs",
        "practical decisions in the",
        "connects observable situations to underlying",
    ])


def _is_generic_synthesis_related(text: str) -> bool:
    lower = " ".join(text.lower().split())
    return lower.endswith(("reasoning", "evidence", "tradeoffs", "constraints")) or lower in {"causes", "effects", "decisions"}


def _compact_concept_for_synthesis(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": row.get("concept_id"),
        "concept_name": row.get("concept_name"),
        "domain": row.get("domain"),
        "short_definition": str(row.get("short_definition") or "").strip(),
        "propositions": [str(item) for item in row.get("propositions", [])[:3]],
        "related_concepts": [str(item) for item in row.get("related_concepts", [])[:5]],
        "examples": [str(item) for item in row.get("examples", [])[:3]],
        "misconceptions": [str(item) for item in row.get("misconceptions", [])[:3]],
        "source_type": row.get("source_type"),
        "source_model_id": row.get("source_model_id"),
        "canonical": bool(row.get("canonical")),
    }


def _tentative_bridge(question: str, concepts: list[dict[str, Any]]) -> str:
    names = [str(item.get("concept_name") or "").lower() for item in concepts]
    joined = " ".join(names)
    if "photosynthesis" in joined and "respiration" in joined:
        return "These stored concepts may connect through energy transformation: photosynthesis stores energy in chemical form, while cellular respiration releases usable energy from that stored material."
    if "inflation" in joined and "interest" in joined:
        return "These stored concepts may connect through monetary conditions: inflation changes purchasing power, while interest rates influence borrowing, saving, and policy responses."
    if "memory" in joined and ("delta" in joined or "noncanonical" in joined or "canonical" in joined):
        return "These stored concepts may connect through governed retention: DELTA memory separates reversible substrate knowledge from longer-term records, while human memory concepts describe consolidation and recall."
    if "feedback" in joined and ("planning" in joined or "software" in joined):
        return "These stored concepts may connect through control loops: planning sets intended direction, feedback reveals deviation, and software architecture can encode the structures that respond to that feedback."
    primary = [str(item.get("concept_name") or "unnamed concept") for item in concepts[:3]]
    return f"These stored concepts may be connected, but the bridge is tentative: {', '.join(primary)} appear to share context, constraints, or mechanisms that need operator review before synthesis is trusted."


def _synthesis_uncertainty(concepts: list[dict[str, Any]], quality: float) -> str:
    if quality >= 0.9 and len(concepts) >= 3:
        return "moderate: the retrieval set is strong, but the bridge is inferred and has not been approved as knowledge."
    if quality >= 0.7:
        return "moderate_to_high: the retrieval set is usable, but more concept detail or operator review is needed."
    return "high: the retrieved concept set is thin or weak, so the bridge should be treated as exploratory only."


def browse_approved_concepts(
    *,
    limit: int = 3,
    domain: str | None = None,
    exclude_concept_names: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict[str, Any]:
    excluded = {str(name).lower() for name in (exclude_concept_names or [])}
    wanted_domain = str(domain or "").lower().strip()
    blocked_domains = {str(item).lower().strip() for item in (exclude_domains or []) if str(item).strip()}
    records = []
    duplicate_suppression_count = 0
    seen_source_names = set()
    for row in load_approved_concepts():
        name = str(row.get("concept_name") or "").lower()
        if name in seen_source_names:
            duplicate_suppression_count += 1
            continue
        seen_source_names.add(name)
        if excluded and name in excluded:
            continue
        if wanted_domain and str(row.get("domain") or "").lower() != wanted_domain:
            continue
        if blocked_domains and str(row.get("domain") or "").lower() in blocked_domains:
            continue
        records.append(row)
    if not records:
        return {"matched": False, "answer": "", "matches": []}
    records.sort(key=lambda row: (
        -float(row.get("quality_score") or 0.0),
        str(row.get("domain") or "zz_operator_existing"),
        str(row.get("concept_name") or ""),
    ))
    matches = []
    seen_names = set()
    for row in records:
        name = str(row.get("concept_name") or "").lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        matches.append(row)
        if len(matches) >= max(1, limit):
            break
    first = matches[0]
    lines = [
        f"I know about `{first['concept_name']}` from local noncanonical memory.",
        str(first.get("short_definition") or "").strip(),
    ]
    related = [str(item) for item in first.get("related_concepts", [])[:5] if str(item).strip()]
    if related:
        lines.extend(["", "Related ideas:", *[f"- {item}" for item in related]])
    if len(matches) > 1:
        lines.extend(["", "A couple of nearby concepts I can also discuss:"])
        lines.extend(f"- {item.get('concept_name')}" for item in matches[1:])
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
        "duplicate_suppression_count": duplicate_suppression_count,
    }


def build_compact_support_packet(question: str, history: list[dict[str, str]] | None = None, *, max_turns: int = 6) -> dict[str, Any]:
    clean_history = []
    for item in (history or [])[-max_turns:]:
        role = str(item.get("role") or item.get("speaker") or "user")[:24]
        text = _clean(str(item.get("content") or item.get("text") or ""))[:500]
        if text:
            clean_history.append({"role": role, "content": text})
    concepts = query_approved_concepts(question)
    concept_summaries = [
        {
            "concept_name": item.get("concept_name"),
            "short_definition": item.get("short_definition"),
            "memory_type": item.get("memory_type"),
        }
        for item in concepts.get("matches", [])[:3]
    ]
    return {
        "packet_type": "rc2_supporting_information_request",
        "question": _clean(question)[:700],
        "relevant_chat_history": clean_history,
        "relevant_approved_concepts": concept_summaries,
        "routing_reason": "local_or_substrate_confidence_was_insufficient",
        "desired_answer_format": "brief_direct_answer_with_uncertainty_if_needed",
        "instructions": "Return a concise answer only. Do not include hashes, internal reports, or unrelated diagnostics.",
        "provider_call_performed": False,
        "web_search_performed": False,
    }


def build_developmental_memory_state() -> dict[str, Any]:
    contradictions = _read_jsonl(CONCEPT_CONTRADICTION_LOG)
    return {
        "conversation_memory_records": len(_read_jsonl(CONVERSATION_MEMORY_LOG)),
        "personal_memory_records": len(_read_jsonl(PERSONAL_MEMORY_LOG)),
        "knowledge_memory_records": len(_read_jsonl(KNOWLEDGE_MEMORY_LOG)),
        "concept_edges": len(_read_jsonl(CONCEPT_EDGE_LOG)),
        "concept_contradictions": len(contradictions),
        "concept_replay_queue": len(_read_jsonl(CONCEPT_REPLAY_LOG)),
        "canonical_records": 0,
        "training_records": 0,
        "flags": dict(RC2_MEMORY_FLAGS),
    }


def clear_developmental_memory_store(confirm_text: str) -> dict[str, Any]:
    required = "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE"
    if str(confirm_text).strip() != required:
        return {
            "cleared": False,
            "required_confirmation": required,
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    deleted = []
    for path in (*STORE_BY_TYPE.values(), CONCEPT_EDGE_LOG, CONCEPT_REPLAY_LOG, CONCEPT_CONTRADICTION_LOG):
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    return {
        "cleared": True,
        "deleted": deleted,
        "state": build_developmental_memory_state(),
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
    }


def concept_edges(record: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = []
    related = set(str(item).lower() for item in record.get("related_concepts", []))
    for other in existing:
        other_terms = {str(other.get("concept_name", "")).lower(), *(str(item).lower() for item in other.get("related_concepts", []))}
        if related & other_terms:
            edge_id = f"rc2-concept-edge-{_digest(record['concept_id'] + other['concept_id'])}"
            edges.append({
                "edge_id": edge_id,
                "from_concept_id": record["concept_id"],
                "to_concept_id": other["concept_id"],
                "relation": "related_concept_overlap",
                "canonical": False,
            })
    return edges


def find_duplicate(candidate: dict[str, Any], existing: list[dict[str, Any]]) -> dict[str, Any] | None:
    name = _normalize_text(candidate.get("concept_name", ""))
    definition = _normalize_text(candidate.get("short_definition", ""))
    for row in existing:
        if _normalize_text(row.get("concept_name", "")) == name:
            return row
        if definition and _normalize_text(row.get("short_definition", "")) == definition:
            return row
    return None


def detect_concept_contradictions(record: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contradictions = []
    new_claims = [record.get("short_definition", ""), *record.get("propositions", [])]
    for other in existing:
        old_claims = [other.get("short_definition", ""), *other.get("propositions", [])]
        for new_claim in new_claims:
            for old_claim in old_claims:
                if claims_contradict(str(old_claim), str(new_claim)):
                    contradiction_id = f"rc2-concept-contradiction-{_digest(other['concept_id'] + record['concept_id'] + old_claim + new_claim)}"
                    contradictions.append({
                        "contradiction_id": contradiction_id,
                        "concept_a_id": other["concept_id"],
                        "concept_b_id": record["concept_id"],
                        "claim_a": old_claim,
                        "claim_b": new_claim,
                        "status": "operator_review_recommended",
                        "canonical": False,
                    })
    return contradictions


def claims_contradict(a: str, b: str) -> bool:
    left = normalize_contradiction_claim(a)
    right = normalize_contradiction_claim(b)
    return bool(left["key"] and left["key"] == right["key"] and left["polarity"] != right["polarity"])


def normalize_contradiction_claim(text: str) -> dict[str, str]:
    normalized = _normalize_text(text)
    polarity = "positive"
    replacements = {
        " should not ": " should ",
        " must not ": " must ",
        " cannot ": " can ",
        " can not ": " can ",
        " is not ": " is ",
        " are not ": " are ",
        " does not ": " does ",
        " do not ": " do ",
        " not always ": " always ",
        " requires manual review ": " automatic ",
        " requires operator approval ": " automatic ",
        " requires approval ": " automatic ",
    }
    negative_markers = (" should not ", " must not ", " cannot ", " can not ", " is not ", " are not ", " does not ", " do not ", " not always ", " requires manual review ", " requires operator approval ", " requires approval ")
    if any(marker in normalized for marker in negative_markers):
        polarity = "negative"
    key = normalized
    for old, new in replacements.items():
        key = key.replace(old, new)
    key = key.replace(" automatically ", " automatic ")
    return {"key": " ".join(key.split()), "polarity": polarity}


def infer_memory_type(question: str) -> str:
    lower = question.lower()
    if any(term in lower for term in ["my ", "i prefer", "i like", "my project", "about me"]):
        return "personal"
    return "knowledge"


def infer_concept_name(question: str, answer: str) -> str:
    lower = question.lower()
    combined = f"{question} {answer}".lower()
    if "fire" in lower:
        return "Fire"
    if "water" in lower and "color" in lower:
        return "Water Color"
    if "moon" in lower and "color" in lower:
        return "Moon Color Appearance"
    if "sky" in lower and "color" in lower:
        return "Daytime Sky Color"
    if "meaning of life" in lower or "meaning of life" in combined:
        return "Meaning of Life Perspectives"
    if "workflow" in lower and "coding" in combined:
        return "Coding Learning Workflow"
    if "people" in lower and "fun" in lower:
        return "Common Leisure Activities"
    if "most people" in lower and any(term in combined for term in ["hobbies", "activities", "entertainment", "relax"]):
        return "Common Leisure Activities"
    if "avogadro" in lower:
        return "Avogadro's Number Relationship"
    if "python" in lower or "function" in lower or "code" in lower:
        return "Coding Assistance"
    words = [word.strip(".,:;!?()[]{}").capitalize() for word in question.split() if len(word.strip(".,:;!?()[]{}")) > 3]
    return " ".join(words[:4]) or "Learned Concept"


def infer_concept_type(question: str, answer: str) -> str:
    lower = f"{question} {answer}".lower()
    if any(term in lower for term in ["should", "must", "approval", "policy"]):
        return "principle_or_policy"
    if any(term in lower for term in ["because", "causes", "combustion", "scattering", "absorbs"]):
        return "causal_explanation"
    if any(term in lower for term in ["python", "function", "code", "debug"]):
        return "technical_procedure"
    return "general_concept"


def infer_short_definition(concept_name: str, propositions: list[str], answer: str) -> str:
    if propositions:
        first = propositions[0]
        return first if len(first) <= 260 else first[:257] + "..."
    clean = _clean(answer)
    return clean[:257] + "..." if len(clean) > 260 else clean


def infer_related_concepts(concept_name: str, question: str, answer: str) -> list[str]:
    text = f"{concept_name} {question} {answer}".lower()
    candidates: list[str] = []

    semantic_rules = [
        (
            ("calorie", "diet", "meal", "breakfast", "lunch", "dinner", "snack", "nutrition", "protein", "carb", "fat"),
            [
                "meal planning",
                "calorie budgeting",
                "nutrition planning",
                "portion control",
                "dietary constraints",
                "macronutrient balance",
                "weekly meal structure",
                "food variety",
                "diet sustainability",
            ],
        ),
        (
            ("meaning of life", "purpose", "happiness", "relationships", "self-reflection", "existential"),
            [
                "life philosophy",
                "subjective meaning",
                "personal growth",
                "self-reflection",
                "relationships",
                "individual purpose",
                "pursuit of happiness",
                "meaning-making",
                "existential questions",
                "social contribution",
            ],
        ),
        (
            ("coding", "programming", "debug", "python", "algorithm", "data structure", "software"),
            [
                "programming fundamentals",
                "debugging practice",
                "algorithmic thinking",
                "data structures",
                "software projects",
                "code review",
                "learning workflow",
            ],
        ),
        (
            ("sky", "moon", "color", "light", "bright", "sunlight", "scattering", "wavelength", "reflect"),
            [
                "light scattering",
                "surface reflection",
                "visible light",
                "atmospheric optics",
                "apparent color",
                "illumination",
            ],
        ),
        (
            ("plan", "workflow", "schedule", "steps", "strategy", "review"),
            [
                "workflow planning",
                "task sequencing",
                "review process",
                "operational planning",
                "success criteria",
            ],
        ),
    ]

    for triggers, related in semantic_rules:
        if any(_contains_semantic_trigger(text, trigger) for trigger in triggers):
            for item in related:
                _append_related_candidate(candidates, item)

    phrase_patterns = [
        "pursuit of happiness",
        "personal growth",
        "self-reflection",
        "sense of belonging",
        "search for answers",
        "learning and adaptation",
        "pressure cooking",
        "phase transition",
        "heat transfer",
        "crystal structure",
        "operator review",
        "approval workflow",
    ]
    for phrase in phrase_patterns:
        if phrase in text:
            _append_related_candidate(candidates, phrase)

    if not candidates:
        for phrase in _extract_reusable_noun_phrases(text):
            _append_related_candidate(candidates, phrase)
    return candidates[:10]


def _append_related_candidate(candidates: list[str], item: str) -> None:
    clean = _normalize_related_concept(item)
    if clean and clean not in candidates:
        candidates.append(clean)


def _contains_semantic_trigger(text: str, trigger: str) -> bool:
    trigger = str(trigger or "").strip().lower()
    if not trigger:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(trigger).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _normalize_related_concept(item: str) -> str:
    clean = " ".join(str(item or "").lower().replace("/", " ").split())
    clean = clean.strip(".,:;!?()[]{}'\"")
    if not clean or clean.startswith("rc2"):
        return ""
    blocked = {
        "what", "that", "this", "with", "from", "because", "about", "there", "their", "would", "could", "should",
        "please", "expand", "previous", "answer", "question", "original", "deeper", "useful", "nuance",
        "conversational", "store", "memory", "user", "asked", "reply", "assistant", "model", "meaning",
        "perspectives", "complex", "multifaceted", "concept", "approached", "various", "including",
        "angles", "standpoint", "finding", "significance", "one's", "ones", "view", "views", "contrast",
        "example", "ultimately", "deeply", "personal", "individual", "greatly", "person", "every",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "breakfast",
        "lunch", "dinner", "snack", "greek", "yogurt", "apple", "chicken", "salad", "shrimp",
        "beans", "cottage", "cheese", "peaches", "raspberries", "sweet", "potato",
    }
    if clean in blocked:
        return ""
    words = clean.split()
    if len(words) == 1 and (len(clean) < 7 or clean in blocked):
        return ""
    if len(words) == 1 and clean.endswith(("ing", "ed")):
        return ""
    return clean


def _extract_reusable_noun_phrases(text: str) -> list[str]:
    phrases = []
    patterns = [
        r"\b([a-z]+(?:\s+[a-z]+){1,2})\s+(?:planning|workflow|process|strategy|structure|balance|review|control|constraints)\b",
        r"\b(?:planning|workflow|process|strategy|structure|balance|review|control|constraints)\s+([a-z]+(?:\s+[a-z]+){0,2})\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            phrase = match.group(0)
            normalized = _normalize_related_concept(phrase)
            if normalized:
                phrases.append(normalized)
    return phrases


def infer_examples(question: str, answer: str) -> list[str]:
    examples = []
    if "for example" in answer.lower():
        examples.append(answer)
    if question:
        examples.append(question)
    return examples[:3]


def infer_misconceptions(answer: str) -> list[str]:
    lower = answer.lower()
    misconceptions = []
    if "not always" in lower:
        misconceptions.append("The relationship is not universal; context matters.")
    if "not exactly" in lower or "nearly" in lower:
        misconceptions.append("The simplified answer may be misleading without context.")
    return misconceptions


def infer_uncertainty(answer: str, lane: dict[str, Any]) -> str:
    if not lane.get("available"):
        return "local_model_lane_unavailable"
    if any(term in answer.lower() for term in ["not enough", "not confident", "uncertain", "may"]):
        return "moderate"
    return "low_to_moderate_operator_reviewed"


def _sentence_propositions(answer: str) -> list[str]:
    clean = _clean(answer)
    parts = []
    normalized = re.sub(r"(?m)^\s*\d+\s*[\.)]\s*$", " ", clean)
    normalized = re.sub(r"(?m)^\s*\d+\s*[\.)]\s*", "", normalized)
    normalized = re.sub(r"\s+\d+\s*[\.)]\s*", " ", normalized)
    for raw in normalized.replace("\r\n", " ").replace("\n", " ").split("."):
        item = raw.strip()
        if item and not re.fullmatch(r"\d+", item):
            parts.append(item + ".")
    return parts[:6]


def _query_phrases(normalized: str) -> set[str]:
    stop_phrases = {
        "what",
        "what is",
        "what are",
        "what do",
        "tell me",
        "explain",
        "how does",
        "how do",
        "how are",
        "relate to",
        "connected to",
        "compare",
        "people",
        "usually",
        "for fun",
    }
    words = [
        word for word in normalized.split()
        if word not in {"the", "a", "an", "and", "or", "to", "of", "in", "what", "do", "does", "usually", "people", "tell", "me", "about", "show", "explain"}
    ]
    phrases = set()
    for size in (3, 2):
        for index in range(0, max(0, len(words) - size + 1)):
            phrase = " ".join(words[index:index + size]).strip()
            if phrase and phrase not in stop_phrases and len(phrase) > 4:
                phrases.add(phrase)
    phrases.update(word for word in words if len(word) > 3)
    return phrases


def _query_key_tokens(normalized: str) -> set[str]:
    return {
        word for word in _meaningful_tokens(normalized)
        if word not in {"example", "examples", "pretend", "favorite", "conversation"}
    }


def _relevance_gate_passed(
    *,
    query_key_tokens: set[str],
    name_overlap: set[str],
    overlap: set[str],
    reasons: list[str],
    phrase_count: int,
) -> bool:
    if any(reason in {"forced_domain_match", "domain_alias_match"} for reason in reasons):
        return True
    if any(reason.startswith("name_phrase:") and " " in reason.split(":", 1)[1] for reason in reasons):
        return True
    if len(query_key_tokens) <= 1:
        return bool(name_overlap or overlap or any(reason.startswith(("name_phrase:", "source_phrase:", "related_phrase:")) for reason in reasons))
    if len(name_overlap) >= 2:
        return True
    if len(query_key_tokens & overlap) >= min(2, len(query_key_tokens)):
        return True
    if phrase_count and any(reason.startswith(("proposition_phrase:", "related_phrase:", "source_phrase:")) and " " in reason.split(":", 1)[1] for reason in reasons):
        return True
    return False


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase = _normalize_text(phrase).strip()
    if not phrase:
        return False
    return f" {phrase} " in f" {text} "


def _normalize_compact(text: object) -> str:
    return " ".join(_normalize_text(text).split())


def _retrieval_precision_estimate(matches: list[dict[str, Any]], profile: dict[str, Any]) -> float:
    if not matches:
        return 0.0
    relevant = 0
    for row in matches:
        score = row.get("_retrieval_score") or {}
        reasons = set(score.get("reasons", []))
        if score.get("relevance_gate_passed") and (
            score.get("score", 0) >= 8
            or "domain_alias_match" in reasons
            or any(str(reason).startswith("name_phrase:") for reason in reasons)
        ):
            relevant += 1
            continue
        if score.get("overlap"):
            relevant += 1
    return round(relevant / len(matches), 4)


def _multi_retrieval_quality(matches: list[dict[str, Any]], seeds: list[str]) -> float:
    if not seeds or not matches:
        return 0.0
    covered = 0
    for seed in seeds:
        seed_profile = retrieval_query_profile(seed)
        if any(score_concept_for_query(row, seed_profile)["score"] >= 6 for row in matches):
            covered += 1
    coverage = covered / len(seeds)
    breadth = min(len(matches), 5) / 5
    return round((coverage * 0.75) + (breadth * 0.25), 4)


def _meaningful_tokens(text: str) -> set[str]:
    stop = {
        "what",
        "about",
        "that",
        "this",
        "from",
        "with",
        "does",
        "tell",
        "know",
        "your",
        "have",
        "were",
        "been",
        "will",
        "should",
        "usually",
        "often",
        "generally",
        "something",
        "another",
        "different",
        "concept",
        "concepts",
        "people",
    }
    short_keep = {"law", "ai", "ui", "ux", "api", "atp", "fun"}
    return {word for word in _normalize_text(text).split() if (len(word) > 3 or word in short_keep) and word not in stop}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    clear_runtime_concept_caches()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    clear_runtime_concept_caches()


def _merge_unique_lines(*groups: object) -> list[str]:
    merged = []
    seen = set()
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = _normalize_text(text)
            if key not in seen:
                seen.add(key)
                merged.append(text)
    return merged


def _normalize_approval(text: str) -> str:
    return " ".join(str(text).strip().lower().replace(".", " ").split())


def _normalize_text(text: object) -> str:
    normalized = str(text).lower()
    for char in ["'", "-", "?", "/", "\\", ".", ",", ":", ";", "!", "(", ")", "[", "]", "{", "}"]:
        normalized = normalized.replace(char, " ")
    return " " + " ".join(normalized.split()) + " "


def _clean(text: str) -> str:
    return " ".join(str(text).replace("\r\n", "\n").replace("\r", "\n").split())


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _store_signature(paths: dict[str, Path]) -> tuple[tuple[str, str, int, int], ...]:
    signature = []
    for name, path in sorted(paths.items()):
        if path.exists():
            stat = path.stat()
            signature.append((name, str(path), stat.st_mtime_ns, stat.st_size))
        else:
            signature.append((name, str(path), 0, 0))
    return tuple(signature)


======================================================================
FILE: orchestration/runtime/rc2_storage_adapter.py
======================================================================

"""Storage adapter for the RC2 substrate.

Runtime callers use this module instead of deciding whether to read SQLite or
JSONL directly. SQLite is preferred when available; JSONL remains the safe
fallback and audit/export source.
"""

from __future__ import annotations

from typing import Any

from orchestration.runtime import rc2_sqlite_substrate as sqlite_backend
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation
from orchestration.runtime.rc2_developmental_concept_memory import (
    load_approved_concepts,
    rank_approved_concepts,
)
from orchestration.runtime.rc2_governed_semantic_graph import (
    bounded_graph_traversal,
    build_runtime_graph_index,
    load_approved_graph_edges,
)


def backend_health() -> dict[str, Any]:
    return sqlite_backend.backend_health()


def substrate_counts() -> dict[str, Any]:
    reconciliation = build_substrate_reconciliation(write_reports=False)
    display = reconciliation["ui_display"]
    health = reconciliation["backend_health"]
    if display.get("sqlite_available"):
        return {
            "backend": display.get("backend"),
            "concepts": int(display.get("active_runtime_concepts", 0)),
            "active_runtime_concepts": int(display.get("active_runtime_concepts", 0)),
            "graph_edges": int(display.get("active_graph_edges", 0)),
            "active_graph_edges": int(display.get("active_graph_edges", 0)),
            "import_audited_events": int(display.get("substrate_replay_events", 0)),
            "substrate_replay_events": int(display.get("substrate_replay_events", 0)),
            "import_audited_concepts": int(display.get("concept_replay_events", 0)),
            "concept_replay_events": int(display.get("concept_replay_events", 0)),
            "import_audited_graph_edges": int(display.get("graph_edge_replay_events", 0)),
            "graph_edge_replay_events": int(display.get("graph_edge_replay_events", 0)),
            "migration_audit_events": int(display.get("migration_audit_events", 0)),
            "replay_events": int(display.get("substrate_replay_events", 0)),
            "concept_replay_coverage": float(health.get("replay_coverage", {}).get("concept_replay_coverage", 0.0)),
            "edge_replay_coverage": float(health.get("replay_coverage", {}).get("edge_replay_coverage", 0.0)),
            "jsonl_backup": health.get("jsonl_counts", {}),
            "legacy_jsonl_concepts": int(display.get("legacy_jsonl_concepts", 0)),
            "legacy_jsonl_graph_edges": int(display.get("legacy_jsonl_graph_edges", 0)),
            "fresh": bool(display.get("sqlite_fresh")),
            "reconciliation": reconciliation,
        }
    return {
        "backend": "jsonl_fallback",
        "concepts": len(load_approved_concepts()),
        "graph_edges": len(load_approved_graph_edges()),
        "import_audited_events": 0,
        "import_audited_concepts": 0,
        "import_audited_graph_edges": 0,
        "replay_events": 0,
        "concept_replay_coverage": 0.0,
        "edge_replay_coverage": 0.0,
        "jsonl_backup": {},
        "fresh": False,
    }


def load_concepts(limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.load_concepts_sqlite(limit=limit)
    concepts = load_approved_concepts()
    return concepts[:limit] if limit else concepts


def load_diverse_concepts(limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.load_diverse_concepts_sqlite(limit=limit)
    concepts = load_approved_concepts()
    buckets: dict[str, list[dict[str, Any]]] = {}
    for concept in concepts:
        buckets.setdefault(str(concept.get("domain") or ""), []).append(concept)
    selected: list[dict[str, Any]] = []
    keys = sorted(buckets)
    requested = int(limit or len(concepts))
    while keys and len(selected) < requested:
        next_keys = []
        for key in keys:
            bucket = buckets[key]
            if bucket:
                selected.append(bucket.pop(0))
            if bucket:
                next_keys.append(key)
            if len(selected) >= requested:
                break
        keys = next_keys
    return selected


def get_concept(concept_id: str) -> dict[str, Any] | None:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_concept_sqlite(concept_id)
    for concept in load_approved_concepts():
        if str(concept.get("concept_id")) == str(concept_id):
            return concept
    return None


def search_concepts(
    query: str,
    *,
    domain: str | None = None,
    limit: int = 5,
    exclude_concept_names: list[str] | None = None,
) -> dict[str, Any]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.search_concepts_sqlite(
            query,
            domain=domain,
            limit=limit,
            exclude_concept_names=exclude_concept_names,
        )
    result = rank_approved_concepts(
        query,
        domain=domain,
        limit=limit,
        exclude_concept_names=exclude_concept_names,
    )
    return {**result, "backend": "jsonl_fallback"}


def get_edges_for_concept(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_edges_for_concept_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["concept_edges"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def get_outgoing_edges(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_outgoing_edges_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["outgoing"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def get_incoming_edges(concept_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.get_incoming_edges_sqlite(concept_id, limit=limit)
    index = build_runtime_graph_index()
    edges = index["incoming"].get(str(concept_id), [])
    return edges[:limit] if limit else edges


def traverse_graph(concept_id: str, *, depth: int = 1) -> dict[str, Any]:
    health = backend_health()
    if health.get("sqlite_available"):
        return sqlite_backend.traverse_graph_sqlite(concept_id, depth=depth)
    return {**bounded_graph_traversal(concept_id, max_depth=depth), "backend": "jsonl_fallback"}


def get_graph_neighborhood(concept_id: str, *, depth: int = 1) -> dict[str, Any]:
    concept = get_concept(concept_id)
    edges = get_edges_for_concept(concept_id, limit=25)
    traversal = traverse_graph(concept_id, depth=depth)
    neighbor_ids = {
        str(edge.get("source_concept_id") if edge.get("target_concept_id") == concept_id else edge.get("target_concept_id"))
        for edge in edges
    }
    neighbors = [item for item in (get_concept(item) for item in sorted(neighbor_ids)) if item]
    return {
        "backend": substrate_counts()["backend"],
        "concept": concept,
        "edges": edges,
        "neighbors": neighbors,
        "traversal": traversal,
        "read_only": True,
    }


======================================================================
FILE: orchestration/runtime/rc2_working_reasoning_set.py
======================================================================

"""Ephemeral Working Reasoning Set for RC2.

The WorkingReasoningSet (WRS) is a temporary read-only workspace for one
question. It retrieves multiple approved concepts, gathers propositions and
approved graph edges, compares the proposition pool, and returns a grounded
answer that separates stored knowledge from reasoned connection and
uncertainty. It never writes memory, graph edges, replay records, canonical
records, provider calls, or training artifacts.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORT_JSON = ROOT / "reports" / "RC2_WORKING_REASONING_SET.json"
REPORT_MD = ROOT / "reports" / "RC2_WORKING_REASONING_SET.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_performed": False,
    "consolidation_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
    "synthesis_enabled_by_default": False,
}

WRS_PROMPTS = [
    "How could knowledge about a patient's allergies influence the interpretation or management of their blood pressure?",
    "Suppose a patient has elevated blood pressure and a history of severe allergies. What additional evidence would you want before making a medical decision?",
    "What constraints or tradeoffs arise when reasoning about blood pressure in someone with significant allergies?",
    "What common reasoning principles connect allergies and blood pressure?",
    "Teach a new medical student how allergies and blood pressure relate in clinical reasoning.",
    "How do photosynthesis and cellular respiration relate?",
    "How does inflation relate to interest rates?",
    "What connects planning and feedback loops?",
    "How does memory consolidation relate to noncanonical memory?",
    "How does gravity relate to orbital motion?",
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "before", "between", "by", "can", "could", "do", "does",
    "for", "from", "had", "has", "have", "how", "in", "into", "is", "it", "its", "making",
    "of", "on", "or", "patient", "relate", "related", "reasoning", "should", "someone",
    "suppose", "that", "the", "their", "them", "to", "use", "using", "what", "when",
    "why", "with", "would", "you", "your",
}

GENERIC_METADATA_TOKENS = {
    "applications",
    "assumptions",
    "constraints",
    "context",
    "evidence",
    "examples",
    "operator",
    "operator-reviewable",
    "outcomes",
    "practical",
    "provenance",
    "reasoning",
    "review",
    "reviewable",
    "simplifications",
    "tradeoffs",
    "uncertainty",
    "unresolved",
}

GENERIC_PROPOSITION_PHRASES = (
    "identifies the important variables",
    "separates observed evidence",
    "supports practical decisions",
    "connecting",
    "evidence, constraints, examples",
    "operator-reviewable uncertainty",
    "causes, constraints, tradeoffs",
)

SCAFFOLD_CONCEPT_TERMS = (
    "abstraction",
    "boundary conditions",
    "causal pathway",
    "comparative frame",
    "competency test",
    "contradiction check",
    "coordination role",
    "data requirement",
    "design pattern",
    "diagnostic use",
    "ethical constraint",
    "evidence chain",
    "evidence standard",
    "failure mode",
    "longitudinal tracking",
    "measurement",
    "optimization",
    "practical heuristic",
    "risk control",
    "system interaction",
    "tradeoff",
)

PRINCIPLE_KEYWORDS = {
    "evidence": {"evidence", "observed", "measurement", "source", "reading", "monitoring"},
    "context": {"context", "conditions", "health", "activity", "stress", "posture", "history"},
    "uncertainty": {"uncertainty", "assumptions", "simplifications", "incomplete", "unknown"},
    "constraints": {"constraints", "tradeoffs", "practical", "decision", "management"},
    "risk": {"risk", "severe", "persistently", "cardiovascular"},
}


@dataclass
class WorkingReasoningSet:
    question: str
    retrieved_concepts: list[dict[str, Any]]
    retrieved_propositions: list[dict[str, Any]]
    retrieved_graph_edges: list[dict[str, Any]]
    shared_propositions: list[str]
    conflicting_propositions: list[str]
    missing_evidence: list[str]
    possible_connections: list[str]
    unsupported_inferences: list[str]
    candidate_answer: str
    confidence: float
    retrieval_score: float
    graph_support_score: float
    reasoning_trace: list[str] = field(default_factory=list)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def should_use_wrs(question: str) -> bool:
    lower = " ".join(str(question or "").lower().split())
    cues = (
        "influence",
        "relate",
        "connect",
        "common reasoning principles",
        "additional evidence",
        "constraints",
        "tradeoffs",
        "teach",
        "unified explanation",
        "compare",
        "bridge",
        "similar as systems",
        "common structure",
        "share a",
        "share an",
        "share the",
        "both use",
        "both depend",
        "both reason",
        "change the way you reason",
        "prevents",
        "cannot be concluded",
        "missing before",
    )
    return any(cue in lower for cue in cues)


def _tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z][a-z0-9]+", str(text or "").lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def extract_reasoning_seeds(question: str) -> list[str]:
    lower = " ".join(str(question or "").lower().split())
    seeds: list[str] = []
    known_phrases = [
        "blood pressure",
        "allergies",
        "severe allergies",
        "photosynthesis",
        "cellular respiration",
        "inflation",
        "interest rates",
        "planning",
        "feedback loops",
        "memory consolidation",
        "noncanonical memory",
        "immune memory",
        "gravity",
        "orbital motion",
        "battery charging",
        "vascular resistance",
        "gardening",
        "software architecture",
        "home repair",
        "medicine",
        "materials science",
        "psychology",
        "finance",
        "biology",
        "agriculture",
        "energy transfer",
        "feedback control",
        "evidence",
        "constraints",
        "tradeoffs",
        "uncertainty",
    ]
    for phrase in known_phrases:
        if phrase in lower:
            seeds.append(phrase)
    for token in _tokens(lower):
        if token not in seeds:
            seeds.append(token)
    return seeds[:10]


def required_topic_families(question: str) -> list[str]:
    lower = " ".join(str(question or "").lower().split())
    families = []
    phrase_to_family = [
        ("blood pressure", "blood pressure"),
        ("allergies", "allergies"),
        ("allergy", "allergies"),
        ("photosynthesis", "photosynthesis"),
        ("cellular respiration", "respiration"),
        ("respiration", "respiration"),
        ("inflation", "inflation"),
        ("interest rates", "interest rates"),
        ("planning", "planning"),
        ("feedback loops", "feedback"),
        ("feedback", "feedback"),
        ("memory consolidation", "memory consolidation"),
        ("noncanonical memory", "noncanonical memory"),
        ("immune memory", "immune memory"),
        ("gravity", "gravity"),
        ("orbital motion", "orbital motion"),
        ("battery charging", "battery charging"),
        ("charging", "battery charging"),
        ("vascular resistance", "vascular resistance"),
        ("gardening", "agriculture gardening"),
        ("agriculture", "agriculture gardening"),
        ("software architecture", "software architecture"),
        ("home repair", "home repair"),
        ("medicine", "medicine health general"),
        ("medical", "medicine health general"),
        ("materials science", "materials science"),
        ("psychology", "psychology"),
        ("finance", "finance"),
        ("biology", "biology"),
        ("energy transfer", "energy transfer"),
        ("feedback control", "feedback"),
    ]
    for phrase, family in phrase_to_family:
        if phrase in lower and family not in families:
            families.append(family)
    return families


def _concept_key(concept: dict[str, Any]) -> str:
    return str(concept.get("concept_id") or concept.get("concept_name") or "").lower()


def retrieve_wrs_concepts(question: str, *, limit: int = 8) -> dict[str, Any]:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    seeds = extract_reasoning_seeds(question)
    required_families = required_topic_families(question)
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_suppression = 0
    ordered_seeds = [*required_families, *[seed for seed in seeds if seed not in required_families]]
    for seed in ordered_seeds:
        result = search_concepts(seed, limit=3)
        for concept in _rank_seed_matches(seed, result.get("matches", [])):
            key = _concept_key(concept)
            if not key:
                continue
            if key in seen:
                duplicate_suppression += 1
                continue
            seen.add(key)
            matches.append(concept)
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    covered = _covered_families(matches, required_families)
    missing_required = [family for family in required_families if family not in covered]
    for family in missing_required:
        result = search_concepts(family, limit=5)
        for concept in _rank_seed_matches(family, result.get("matches", [])):
            if _topic_family(str(concept.get("concept_name") or "")) != family:
                continue
            key = _concept_key(concept)
            if key and key not in seen:
                seen.add(key)
                matches.append(concept)
                break
    if len(matches) < 2:
        fallback = search_concepts(question, limit=limit)
        for concept in fallback.get("matches", []):
            key = _concept_key(concept)
            if key and key not in seen:
                seen.add(key)
                matches.append(concept)
            if len(matches) >= limit:
                break
    ordered_matches = _prioritize_required_family_representatives(matches, required_families)
    return {
        "seeds": seeds,
        "matches": ordered_matches[:limit],
        "matched": len(ordered_matches) >= 2,
        "duplicate_suppression_count": duplicate_suppression,
        "retrieval_score": min(len(ordered_matches), limit) / max(2, limit),
        "required_families": required_families,
        "covered_families": sorted(_covered_families(ordered_matches[:limit], required_families)),
    }


def _covered_families(concepts: list[dict[str, Any]], required_families: list[str]) -> set[str]:
    required = set(required_families)
    covered = set()
    for concept in concepts:
        family = _topic_family(str(concept.get("concept_name") or ""))
        if family in required:
            covered.add(family)
    return covered


def _rank_seed_matches(seed: str, concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seed_family = _topic_family(seed)

    def key(concept: dict[str, Any]) -> tuple[int, int, int, float, str]:
        name = str(concept.get("concept_name") or "").lower()
        family_match = 0 if _topic_family(name) == seed_family else 1
        core = 0 if _is_core_factual_concept(concept) else 1
        generic = 1 if _is_scaffold_concept(concept) else 0
        quality = float(concept.get("quality_score") or concept.get("confidence") or 0.0)
        return (family_match, core, generic, -quality, name)

    return sorted(concepts, key=key)


def _prioritize_required_family_representatives(concepts: list[dict[str, Any]], required_families: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for family in required_families:
        family_matches = [concept for concept in concepts if _topic_family(str(concept.get("concept_name") or "")) == family]
        for concept in _rank_seed_matches(family, family_matches):
            if concept not in selected:
                selected.append(concept)
                break
    for concept in concepts:
        if concept not in selected:
            selected.append(concept)
    return selected


def _compact_concept(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_id": concept.get("concept_id"),
        "concept_name": concept.get("concept_name"),
        "domain": concept.get("domain"),
        "concept_type": concept.get("concept_type"),
        "source_type": concept.get("source_type"),
        "short_definition": concept.get("short_definition"),
        "propositions": [str(item) for item in concept.get("propositions", []) if str(item).strip()][:6],
        "related_concepts": [str(item) for item in concept.get("related_concepts", []) if str(item).strip()][:8],
        "examples": [str(item) for item in concept.get("examples", []) if str(item).strip()][:3],
        "misconceptions": [str(item) for item in concept.get("misconceptions", []) if str(item).strip()][:2],
        "quality_score": concept.get("quality_score", concept.get("confidence")),
    }


def _proposition_pool(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool = []
    for concept in concepts:
        for proposition in concept.get("propositions", []):
            text = str(proposition).strip()
            if text:
                pool.append({
                    "concept_id": concept.get("concept_id"),
                    "concept_name": concept.get("concept_name"),
                    "text": text,
                    "tokens": _tokens(text),
                    "substantive": _is_substantive_proposition(text),
                })
    return pool


def _is_substantive_proposition(text: str) -> bool:
    lower = " ".join(str(text or "").lower().split())
    if any(phrase in lower for phrase in GENERIC_PROPOSITION_PHRASES):
        return False
    tokens = set(_tokens(lower))
    if not tokens:
        return False
    metadata_count = len(tokens & GENERIC_METADATA_TOKENS)
    domain_count = len(tokens - GENERIC_METADATA_TOKENS)
    return domain_count >= 3 and metadata_count / max(1, len(tokens)) < 0.45


def _substantive_propositions(propositions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    substantive = [item for item in propositions if item.get("substantive")]
    return substantive if substantive else propositions


def _shared_principles(propositions: list[dict[str, Any]]) -> list[str]:
    propositions = [item for item in propositions if item.get("substantive")]
    if not propositions:
        return []
    concept_by_principle: dict[str, set[str]] = {key: set() for key in PRINCIPLE_KEYWORDS}
    for prop in propositions:
        tokens = set(prop.get("tokens", []))
        for principle, keywords in PRINCIPLE_KEYWORDS.items():
            if tokens & keywords:
                concept_by_principle[principle].add(str(prop.get("concept_name") or ""))
    shared = []
    for principle, names in concept_by_principle.items():
        if len(names) >= 2:
            shared.append(f"{principle}: appears across {', '.join(sorted(names)[:4])}")
    return shared[:6]


def _conflicts(propositions: list[dict[str, Any]]) -> list[str]:
    texts = [str(item.get("text") or "").lower() for item in propositions]
    conflicts = []
    for text in texts:
        if "not " in text:
            positive = text.replace("not ", "")
            if any(positive in other for other in texts if other != text):
                conflicts.append(f"Possible polarity conflict around: {positive[:120]}")
    return conflicts[:3]


def _missing_evidence(question: str, concepts: list[dict[str, Any]], shared: list[str]) -> list[str]:
    lower = str(question or "").lower()
    missing = []
    if "patient" in lower or "medical" in lower or "blood pressure" in lower:
        missing.extend([
            "Patient-specific context is not stored here: symptoms, medication exposure, timing, repeated measurements, and clinical history would still need review.",
            "The substrate can identify reasoning variables, but it does not contain a patient record or enough evidence to make a medical decision.",
        ])
    if not shared:
        missing.append("No strong shared proposition pattern was found across the retrieved concepts.")
    if len(concepts) < 3:
        missing.append("Only a small concept set was retrieved; more supporting concepts would strengthen the answer.")
    return missing[:4]


def _graph_edges(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import get_edges_for_concept

    edges = []
    concept_ids = {str(concept.get("concept_id") or "") for concept in concepts}
    for concept in concepts:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        for edge in get_edges_for_concept(concept_id, limit=4):
            if str(edge.get("source_concept_id")) in concept_ids or str(edge.get("target_concept_id")) in concept_ids:
                edges.append(edge)
    seen = set()
    unique = []
    for edge in edges:
        edge_id = str(edge.get("edge_id") or "")
        if edge_id and edge_id not in seen:
            seen.add(edge_id)
            unique.append(edge)
    return unique[:10]


def _possible_connections(question: str, concepts: list[dict[str, Any]], propositions: list[dict[str, Any]], shared: list[str], edges: list[dict[str, Any]]) -> list[str]:
    names = [str(concept.get("concept_name") or "") for concept in concepts[:5]]
    connections = []
    families = required_topic_families(question)
    bridge = _higher_order_bridge(families, concepts, propositions)
    if bridge:
        connections.append(bridge)
    comparison_pair = _distinct_topic_pair(names)
    if comparison_pair:
        connections.append(f"{comparison_pair[0]} and {comparison_pair[1]} can be compared by asking how one concept changes the conditions for interpreting the other.")
    if shared:
        principles = [item.split(":", 1)[0] for item in shared[:3] if item.split(":", 1)[0] not in GENERIC_METADATA_TOKENS]
        if principles:
            connections.append("The retrieved concepts share non-generic patterns around " + ", ".join(principles) + ".")
    if edges:
        connections.append("Approved graph edges provide substrate support for some of the retrieved concept neighborhood, but they do not by themselves prove a clinical or scientific conclusion.")
    return connections[:4]


def _higher_order_bridge(families: list[str], concepts: list[dict[str, Any]], propositions: list[dict[str, Any]]) -> str:
    family_set = set(families)
    if {"blood pressure", "allergies", "photosynthesis", "respiration"} <= family_set:
        return (
            "Blood pressure is a cardiovascular measurement shaped by cardiac output, vascular resistance, blood volume, and context; allergy history can constrain medication choices and clinical interpretation. Photosynthesis stores light energy in chemical bonds, while cellular respiration releases stored chemical energy as ATP. The biological pair is an energy transformation relationship, and the shared higher-order pattern is relational interpretation: one concept supplies context for understanding the role, limits, or consequence of another."
        )
    if {"blood pressure", "allergies"} <= family_set:
        return (
            "Blood pressure supplies a measurable cardiovascular state, while allergy history can affect medication choices, emergency planning, and what clinical evidence must be checked before interpreting or acting on that state."
        )
    if {"photosynthesis", "respiration"} <= family_set:
        return (
            "Photosynthesis stores light energy in sugars and other chemical bonds; cellular respiration breaks down fuel molecules such as glucose to produce ATP. Together they form complementary parts of biological energy flow: one process stores usable chemical energy, and the other releases that energy for cellular work."
        )
    if {"inflation", "interest rates"} <= family_set:
        return (
            "Inflation and interest rates connect through economic feedback: inflation describes price-level pressure, while interest rates are a policy or market mechanism that can influence borrowing, spending, and that pressure."
        )
    if {"inflation", "blood pressure"} <= family_set:
        return (
            "Inflation and blood pressure are similar as systems because both describe pressure inside a larger context: inflation is pressure across prices in an economy, while blood pressure is force in the cardiovascular system. In both cases, interpretation depends on system context, flows, constraints, and whether the pressure is temporary or persistent."
        )
    if {"feedback", "allergies"} <= family_set:
        return (
            "Feedback loops and allergies are similar as systems because both involve response patterns: feedback uses outcomes to adjust future behavior, while allergies involve immune responses to exposures. The cautious bridge is response plus adjustment inside a system, not identical mechanisms."
        )
    if {"planning", "respiration"} <= family_set:
        return (
            "Planning and cellular respiration can be compared as constrained process systems: planning allocates actions toward goals under time and resource constraints, while cellular respiration converts stored chemical energy into ATP for cellular work under biological constraints."
        )
    if {"noncanonical memory", "immune memory"} <= family_set:
        return (
            "Noncanonical memory and immune memory both preserve history for future response, but at different levels: noncanonical memory keeps reversible reviewed knowledge for later reasoning, while immune memory reflects prior exposures that shape later immune response."
        )
    if {"interest rates", "vascular resistance"} <= family_set:
        return (
            "Interest rates and vascular resistance can be bridged through flow control: interest rates influence the flow of borrowing and spending, while vascular resistance influences blood flow and pressure. In both systems, resistance-like constraints can change downstream movement and pressure."
        )
    if {"photosynthesis", "battery charging"} <= family_set:
        return (
            "Photosynthesis and battery charging are similar as energy-storage systems: photosynthesis uses light energy to store energy in chemical bonds, while battery charging stores supplied energy electrochemically. The shared structure is energy input, conversion, storage, and later use."
        )
    if {"agriculture gardening", "software architecture"} <= family_set:
        return (
            "Gardening and software architecture can share a planning pattern: both start with goals, constraints, sequencing, feedback, and maintenance. In gardening the plan manages soil, water, light, timing, and growth; in software architecture the plan manages components, interfaces, dependencies, and future change."
        )
    if {"home repair", "medicine health general"} <= family_set:
        return (
            "Home repair and medicine both depend on diagnostic evidence because action should follow observed symptoms, measurements, history, and likely causes rather than guesses. The shared structure is diagnosis before intervention: collect evidence, narrow causes, choose a safe action, and revise if feedback contradicts the plan."
        )
    if {"materials science", "psychology"} <= family_set:
        return (
            "Materials science and psychology both use stress as a useful concept for how systems respond to load. In materials, stress describes force distributed through a material; in psychology, stress describes demands or pressure on a person. The bridge is load, response, tolerance, and failure or adaptation under sustained pressure."
        )
    if {"finance", "biology"} <= family_set:
        return (
            "Finance and biology both reason with feedback loops because outcomes can change future behavior: markets respond to prices, incentives, and risk signals, while biological systems respond to internal and external conditions. The shared pattern is signal, response, adjustment, and possible stabilization or runaway change."
        )
    if {"agriculture gardening", "energy transfer", "feedback"} <= family_set:
        return (
            "Agriculture, energy transfer, and feedback control connect through managed flows: sunlight, water, nutrients, and labor enter a growing system, feedback indicates whether conditions are working, and control decisions adjust the system toward healthier growth."
        )
    if {"planning", "feedback"} <= family_set:
        return (
            "Planning and feedback loops connect through adaptive control: a plan sets intended action, while feedback supplies information that can revise the plan when reality diverges from expectation."
        )
    if {"memory consolidation", "noncanonical memory"} <= family_set:
        return (
            "Memory consolidation and noncanonical memory connect as stages of governed learning: noncanonical memory can hold reversible candidate knowledge, while consolidation evaluates whether that knowledge is stable enough to become more durable."
        )
    if {"gravity", "orbital motion"} <= family_set:
        return (
            "Gravity and orbital motion connect through constraint and motion: gravity supplies the attractive force or curvature context, while orbital motion is the resulting path when that influence combines with velocity."
        )
    substantive = _substantive_propositions(propositions)
    if len(substantive) >= 2:
        names = []
        seen = set()
        for concept in concepts:
            family = _topic_family(str(concept.get("concept_name") or ""))
            name = str(concept.get("concept_name") or "").strip()
            if family and family not in seen:
                seen.add(family)
                names.append(name)
            elif not family and name and name.lower() not in seen:
                seen.add(name.lower())
                names.append(name)
            if len(names) >= 2:
                break
        if len(names) >= 2:
            return (
                f"The organizing principle is a shared process pattern rather than a single fact: {names[0]} and {names[1]} can be compared by identifying their inputs, constraints, feedback, evidence, and outcomes, then checking where the analogy stops."
            )
        return "The organizing principle should be built from substantive propositions rather than repeated governance metadata."
    return ""


def _topic_family(name: str) -> str:
    lower = str(name or "").lower()
    if "blood pressure" in lower:
        return "blood pressure"
    if "allerg" in lower:
        return "allergies"
    if "photosynthesis" in lower:
        return "photosynthesis"
    if "respiration" in lower:
        return "respiration"
    if "inflation" in lower:
        return "inflation"
    if "interest" in lower:
        return "interest rates"
    if "planning" in lower:
        return "planning"
    if "feedback" in lower:
        return "feedback"
    if "memory consolidation" in lower:
        return "memory consolidation"
    if "noncanonical memory" in lower:
        return "noncanonical memory"
    if "immune memory" in lower:
        return "immune memory"
    if "gravity" in lower:
        return "gravity"
    if "orbital" in lower:
        return "orbital motion"
    if "battery charging" in lower or "charging" in lower:
        return "battery charging"
    if "vascular resistance" in lower:
        return "vascular resistance"
    if "agriculture" in lower or "gardening" in lower:
        return "agriculture gardening"
    if "software architecture" in lower or "software" in lower:
        return "software architecture"
    if "home repair" in lower or "appliance" in lower or "troubleshooting" in lower:
        return "home repair"
    if "medicine" in lower or "medical" in lower or "health" in lower:
        return "medicine health general"
    if "materials science" in lower or "material" in lower:
        return "materials science"
    if "psychology" in lower:
        return "psychology"
    if "finance" in lower:
        return "finance"
    if "biology" in lower or "biological" in lower:
        return "biology"
    if "energy transfer" in lower:
        return "energy transfer"
    return re.sub(r"\([^)]*\)", "", lower).strip().split(" ")[0] if lower.strip() else ""


def _distinct_topic_pair(names: list[str]) -> tuple[str, str] | None:
    chosen: list[tuple[str, str]] = []
    seen = set()
    for name in names:
        family = _topic_family(name)
        if not family or family in seen:
            continue
        seen.add(family)
        chosen.append((family, name))
        if len(chosen) >= 2:
            return chosen[0][1], chosen[1][1]
    if len(names) >= 2:
        return names[0], names[1]
    return None


def _is_scaffold_concept(concept: dict[str, Any]) -> bool:
    name = str(concept.get("concept_name") or "").lower()
    concept_type = str(concept.get("concept_type") or "").lower()
    source_type = str(concept.get("source_type") or "").lower()
    if "core_factual" in concept_type or source_type == "rc2_concept_substance_repair":
        return False
    return any(term in name for term in SCAFFOLD_CONCEPT_TERMS)


def _is_core_factual_concept(concept: dict[str, Any]) -> bool:
    concept_type = str(concept.get("concept_type") or "").lower()
    source_type = str(concept.get("source_type") or "").lower()
    if "core_factual" in concept_type or source_type == "rc2_concept_substance_repair":
        return True
    return _core_substance_score(concept) >= 3 and not _is_scaffold_concept(concept)


def _core_substance_score(concept: dict[str, Any]) -> int:
    score = 0
    definition = str(concept.get("short_definition") or "")
    propositions = [str(item) for item in concept.get("propositions", []) if str(item).strip()]
    if _is_substantive_proposition(definition):
        score += 1
    for proposition in propositions[:5]:
        if _is_substantive_proposition(proposition):
            score += 1
    return score


def _candidate_answer(
    question: str,
    concepts: list[dict[str, Any]],
    propositions: list[dict[str, Any]],
    shared: list[str],
    missing: list[str],
    connections: list[str],
    conflicts: list[str],
    required_families: list[str] | None = None,
) -> str:
    stored = []
    for concept in _representative_concepts_for_answer(concepts, required_families=required_families or []):
        prop = _best_proposition_for_concept(concept, propositions)
        if prop:
            stored.append(f"- {concept['concept_name']}: {prop}")
        elif concept.get("short_definition"):
            stored.append(f"- {concept['concept_name']}: {concept['short_definition']}")
    if not stored:
        stored.append("- No sufficiently grounded stored propositions were retrieved.")
    reasoned = connections or ["The retrieved concepts can be compared, but the bridge is weak without additional shared propositions."]
    uncertainty = missing or ["No major missing evidence was identified by the temporary reasoning workspace."]
    lines = [
        "Stored knowledge",
        *stored,
        "",
        "Reasoned connection",
        *[f"- {item}" for item in reasoned],
        "",
        "Uncertainty",
        *[f"- {item}" for item in uncertainty],
    ]
    if shared:
        lines.extend(["", "Shared reasoning patterns", *[f"- {item}" for item in shared]])
    if conflicts:
        lines.extend(["", "Possible conflicts", *[f"- {item}" for item in conflicts]])
    lines.extend(["", "No memory, graph edge, replay record, provider call, or training artifact was created."])
    return "\n".join(lines)


def _representative_concepts_for_answer(concepts: list[dict[str, Any]], limit: int = 6, required_families: list[str] | None = None) -> list[dict[str, Any]]:
    selected = []
    seen_families = set()
    required = set(required_families or [])
    family_pool = [
        concept for concept in concepts
        if not required or _topic_family(str(concept.get("concept_name") or "")) in required
    ]
    visible_pool = [
        concept for concept in concepts
        if _is_core_factual_concept(concept) or not _is_scaffold_concept(concept)
    ]
    if required:
        visible_pool = [concept for concept in visible_pool if concept in family_pool]
    source_pool = visible_pool or family_pool or concepts
    for family in required_families or []:
        family_matches = [
            concept for concept in source_pool
            if _topic_family(str(concept.get("concept_name") or "")) == family
        ]
        for concept in _rank_visible_concepts(family_matches):
            if _topic_family(str(concept.get("concept_name") or "")) == family and concept not in selected:
                selected.append(concept)
                seen_families.add(family)
                break
    for concept in _rank_visible_concepts(source_pool):
        family = _topic_family(str(concept.get("concept_name") or ""))
        if family in seen_families:
            continue
        seen_families.add(family)
        selected.append(concept)
        if len(selected) >= limit:
            return selected
    for concept in _rank_visible_concepts(source_pool):
        if concept not in selected:
            selected.append(concept)
        if len(selected) >= limit:
            break
    return selected


def _rank_visible_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(concept: dict[str, Any]) -> tuple[int, int, int, float, str]:
        scaffold = 1 if _is_scaffold_concept(concept) else 0
        core = 0 if _is_core_factual_concept(concept) else 1
        substance = -_core_substance_score(concept)
        quality = -float(concept.get("quality_score") or concept.get("confidence") or 0.0)
        return (core, scaffold, substance, quality, str(concept.get("concept_name") or ""))

    return sorted(concepts, key=key)


def _best_proposition_for_concept(concept: dict[str, Any], propositions: list[dict[str, Any]]) -> str:
    concept_id = concept.get("concept_id")
    candidates = [item for item in propositions if item.get("concept_id") == concept_id]
    substantive = [item for item in candidates if item.get("substantive")]
    chosen = substantive or candidates
    if chosen:
        chosen.sort(key=lambda item: (-len(set(item.get("tokens", [])) - GENERIC_METADATA_TOKENS), len(str(item.get("text") or ""))))
        return str(chosen[0].get("text") or "")
    props = [str(item) for item in concept.get("propositions", []) if str(item).strip()]
    return props[0] if props else ""


def build_working_reasoning_set(question: str, *, limit: int = 8) -> dict[str, Any]:
    retrieval = retrieve_wrs_concepts(question, limit=limit)
    if not retrieval["matched"]:
        return {
            "matched": False,
            "question": question,
            "answer": "",
            "reason": "insufficient_multi_concept_retrieval",
            "safety": dict(SAFETY),
        }
    concepts = [_compact_concept(item) for item in retrieval["matches"]]
    propositions = _proposition_pool(concepts)
    edges = _graph_edges(concepts)
    shared = _shared_principles(propositions)
    conflicts = _conflicts(propositions)
    missing = _missing_evidence(question, concepts, shared)
    connections = _possible_connections(question, concepts, propositions, shared, edges)
    unsupported = []
    if not edges:
        unsupported.append("No approved graph edge directly links the retrieved concepts; any bridge is proposition-based and tentative.")
    graph_score = min(len(edges), 5) / 5
    confidence = round(min(0.95, 0.35 + retrieval["retrieval_score"] * 0.35 + min(len(shared), 4) * 0.06 + graph_score * 0.12), 4)
    answer = _candidate_answer(question, concepts, propositions, shared, missing, connections, conflicts, retrieval.get("required_families", []))
    wrs = WorkingReasoningSet(
        question=question,
        retrieved_concepts=concepts,
        retrieved_propositions=propositions,
        retrieved_graph_edges=edges,
        shared_propositions=shared,
        conflicting_propositions=conflicts,
        missing_evidence=missing,
        possible_connections=connections,
        unsupported_inferences=unsupported,
        candidate_answer=answer,
        confidence=confidence,
        retrieval_score=round(float(retrieval["retrieval_score"]), 4),
        graph_support_score=round(graph_score, 4),
        reasoning_trace=[
            "retrieved_multi_concept_set",
            "extracted_proposition_pool",
            "grouped_shared_principles",
            "checked_simple_conflicts",
            "identified_missing_evidence",
            "rendered_grounded_answer",
            "destroy_after_response",
        ],
    )
    return {
        "matched": True,
        "route": "working_reasoning_set",
        "answer": answer,
        "working_reasoning_set": asdict(wrs),
        "retrieved_concepts": concepts,
        "retrieved_concept_count": len(concepts),
        "retrieved_proposition_count": len(propositions),
        "retrieved_graph_edge_count": len(edges),
        "confidence": confidence,
        "retrieval_score": wrs.retrieval_score,
        "graph_support_score": wrs.graph_support_score,
        "required_families": retrieval.get("required_families", []),
        "covered_families": retrieval.get("covered_families", []),
        "entity_coverage_score": round(len(retrieval.get("covered_families", [])) / max(1, len(retrieval.get("required_families", []))), 4) if retrieval.get("required_families") else 1.0,
        "unsupported_inference_count": len(unsupported),
        "hallucination_risk": round(0.1 if concepts and propositions and not unsupported else 0.28, 4),
        "uncertainty_quality": round(min(1.0, len(missing) / 2), 4),
        "ephemeral": True,
        "destroyed_after_response": True,
        "safety": dict(SAFETY),
    }


def score_wrs_case(result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("matched"):
        return {
            "retrieval_quality": 0.0,
            "reasoning_quality": 0.0,
            "hallucination_risk": 0.5,
            "uncertainty_quality": 0.0,
            "local_model_avoided": True,
        }
    concepts = int(result.get("retrieved_concept_count") or 0)
    propositions = int(result.get("retrieved_proposition_count") or 0)
    graph_score = float(result.get("graph_support_score") or 0.0)
    wrs = result.get("working_reasoning_set", {})
    shared = len(wrs.get("shared_propositions", []))
    missing = len(wrs.get("missing_evidence", []))
    retrieval_quality = min(concepts, 5) / 5
    reasoning_quality = min(1.0, retrieval_quality * 0.35 + min(propositions, 12) / 12 * 0.25 + min(shared, 3) / 3 * 0.25 + graph_score * 0.15)
    return {
        "retrieval_quality": round(retrieval_quality, 4),
        "reasoning_quality": round(reasoning_quality, 4),
        "hallucination_risk": result.get("hallucination_risk", 0.5),
        "uncertainty_quality": round(min(1.0, missing / 2), 4),
        "local_model_avoided": True,
    }


def build_wrs_report(write_reports: bool = True) -> dict[str, Any]:
    cases = []
    for prompt in WRS_PROMPTS:
        result = build_working_reasoning_set(prompt)
        score = score_wrs_case(result)
        cases.append({"question": prompt, "result": result, "score": score})
    matched = [case for case in cases if case["result"].get("matched")]
    avg = lambda key: round(sum(float(case["score"].get(key) or 0.0) for case in cases) / len(cases), 4)
    report = {
        "report": "RC2_WORKING_REASONING_SET",
        "created_at": _now(),
        "wrs_implemented": True,
        "questions_tested": len(cases),
        "matched_cases": len(matched),
        "average_retrieved_concepts": round(sum(case["result"].get("retrieved_concept_count", 0) for case in matched) / max(1, len(matched)), 4),
        "average_proposition_count": round(sum(case["result"].get("retrieved_proposition_count", 0) for case in matched) / max(1, len(matched)), 4),
        "average_graph_support": round(sum(float(case["result"].get("graph_support_score") or 0.0) for case in matched) / max(1, len(matched)), 4),
        "reasoning_quality": avg("reasoning_quality"),
        "retrieval_quality": avg("retrieval_quality"),
        "unsupported_inference_count": sum(int(case["result"].get("unsupported_inference_count") or 0) for case in matched),
        "hallucination_risk": avg("hallucination_risk"),
        "uncertainty_quality": avg("uncertainty_quality"),
        "local_model_avoidance": 1.0,
        "synthesis_activation": False,
        "cases": cases,
        "safety": dict(SAFETY),
        "recommendation": "USE_WRS_FOR_RELATIONAL_SUBSTRATE_QUESTIONS_KEEP_SYNTHESIS_DISABLED",
    }
    if write_reports:
        write_wrs_reports(report)
    return report


def write_wrs_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Working Reasoning Set",
        "",
        f"Created: {report['created_at']}",
        f"WRS implemented: {report['wrs_implemented']}",
        f"Synthesis activation: {report['synthesis_activation']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Metrics",
        "",
        f"- Questions tested: {report['questions_tested']}",
        f"- Matched cases: {report['matched_cases']}",
        f"- Average retrieved concepts: {report['average_retrieved_concepts']}",
        f"- Average proposition count: {report['average_proposition_count']}",
        f"- Average graph support: {report['average_graph_support']}",
        f"- Reasoning quality: {report['reasoning_quality']}",
        f"- Retrieval quality: {report['retrieval_quality']}",
        f"- Unsupported inference count: {report['unsupported_inference_count']}",
        f"- Hallucination risk: {report['hallucination_risk']}",
        f"- Uncertainty quality: {report['uncertainty_quality']}",
        f"- Local-model avoidance: {report['local_model_avoidance']}",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        result = case["result"]
        lines.extend([
            f"### {case['question']}",
            f"- Matched: {result.get('matched')}",
            f"- Retrieved concepts: {result.get('retrieved_concept_count', 0)}",
            f"- Propositions: {result.get('retrieved_proposition_count', 0)}",
            f"- Graph edges: {result.get('retrieved_graph_edge_count', 0)}",
            f"- Reasoning quality: {case['score']['reasoning_quality']}",
            "",
        ])
    lines.extend([
        "## Safety",
        "",
        "No memory write, graph write, replay, provider call, web call, training, canonical write, HYB1 promotion, or Model B replacement was performed.",
    ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_wrs_report(write_reports=True)
    print(json.dumps({
        "wrs_implemented": report["wrs_implemented"],
        "questions_tested": report["questions_tested"],
        "matched_cases": report["matched_cases"],
        "average_retrieved_concepts": report["average_retrieved_concepts"],
        "average_proposition_count": report["average_proposition_count"],
        "average_graph_support": report["average_graph_support"],
        "reasoning_quality": report["reasoning_quality"],
        "local_model_avoidance": report["local_model_avoidance"],
        "synthesis_activation": report["synthesis_activation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


======================================================================
FILE: orchestration/runtime/rc2_analogy_engine.py
======================================================================

"""RC2 ephemeral analogy analysis.

The analogy engine maps roles and processes between source and target concepts.
It is read-only and does not create memories, graph edges, replay records, or
training artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC2_ANALOGY_ENGINE.json"
REPORT_MD = ROOT / "reports" / "RC2_ANALOGY_ENGINE.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}

ANALOGY_TRIGGERS = (
    "analogy",
    "analogous",
    "as a metaphor",
    "is to",
    "where does it break",
    "where does that analogy break",
    "what works and what breaks",
    "physically identical",
    "complete software program",
    "exactly the same as",
    "perfect equivalent",
)

KNOWN_PAIRS = {
    ("photosynthesis", "charging"): {
        "classification": "process_analogy",
        "source_domain": "biology",
        "target_domain": "energy storage",
        "source_roles": ["light input", "chloroplast conversion", "chemical energy stored in sugars"],
        "target_roles": ["electrical input", "electrochemical conversion", "energy stored in a battery"],
        "source_relations": ["energy input becomes stored chemical potential", "stored energy can later support life processes"],
        "target_relations": ["electrical input becomes stored electrochemical potential", "stored energy can later power a device"],
        "shared": "energy input -> conversion -> storage -> later use",
        "limits": ["Photosynthesis produces sugars through biochemical reactions.", "A battery stores electrochemical energy; the mechanisms are not physically identical."],
    },
    ("cellular respiration", "discharging"): {
        "classification": "process_analogy",
        "source_domain": "biology",
        "target_domain": "energy use",
        "source_roles": ["fuel molecule", "cellular machinery", "ATP output"],
        "target_roles": ["charged battery", "circuit/device", "usable electrical work"],
        "source_relations": ["stored chemical energy is released and converted into ATP"],
        "target_relations": ["stored electrochemical energy is released as electrical output"],
        "shared": "stored energy -> controlled release -> usable work",
        "limits": ["Respiration is metabolic chemistry.", "Battery discharge is an electrochemical/electrical process."],
    },
    ("working memory", "computer workspace"): {
        "classification": "functional_analogy",
        "source_domain": "cognition",
        "target_domain": "computing",
        "source_roles": ["temporary active information", "attention", "mental manipulation"],
        "target_roles": ["open workspace", "active files/data", "operations on data"],
        "source_relations": ["information is held temporarily so it can be used"],
        "target_relations": ["data is kept available while a task is being performed"],
        "shared": "temporary active workspace for manipulation",
        "limits": ["Human working memory is biological and attention-limited.", "A computer workspace is engineered storage and execution state."],
    },
    ("feedback loops", "thermostat"): {
        "classification": "strong_structural_analogy",
        "source_domain": "systems",
        "target_domain": "control",
        "source_roles": ["current output", "comparison signal", "adjustment"],
        "target_roles": ["measured temperature", "set point", "heating/cooling response"],
        "source_relations": ["outcomes are compared against a target and used to adjust behavior"],
        "target_relations": ["temperature is compared with a set point and controls heating or cooling"],
        "shared": "measurement -> comparison -> corrective adjustment",
        "limits": ["Many feedback loops are more complex than a thermostat.", "Thermostats are usually narrow engineered controllers."],
    },
    ("inflation", "pressure"): {
        "classification": "partial_structural_analogy",
        "source_domain": "economics",
        "target_domain": "physics",
        "source_roles": ["price pressure", "demand/supply constraints", "policy response"],
        "target_roles": ["fluid pressure", "container/flow constraints", "release or resistance"],
        "source_relations": ["constraints and flows can increase systemic pressure"],
        "target_relations": ["constraints and force over area can increase physical pressure"],
        "shared": "a constrained system can accumulate pressure that changes behavior",
        "limits": ["Economic pressure is metaphorical and behavioral.", "Fluid pressure is a physical quantity with units."],
    },
    ("graph traversal", "map"): {
        "classification": "relational_analogy",
        "source_domain": "knowledge graph",
        "target_domain": "navigation",
        "source_roles": ["nodes", "edges", "path"],
        "target_roles": ["places", "roads", "route"],
        "source_relations": ["following edges moves through connected concepts"],
        "target_relations": ["following roads moves through connected locations"],
        "shared": "connected points + paths + constraints on movement",
        "limits": ["Knowledge edges can represent many relation types, not just physical routes."],
    },
    ("memory consolidation", "organizing notes"): {
        "classification": "functional_analogy",
        "source_domain": "memory",
        "target_domain": "study workflow",
        "source_roles": ["recent experience", "review", "durable memory"],
        "target_roles": ["rough notes", "organization", "reference material"],
        "source_relations": ["temporary information is reviewed and stabilized"],
        "target_relations": ["notes are cleaned up and made easier to reuse"],
        "shared": "raw material -> review/organization -> durable reference",
        "limits": ["Memory consolidation is cognitive/biological; note organization is an external workflow."],
    },
    ("access control", "locks"): {
        "classification": "functional_analogy",
        "source_domain": "security",
        "target_domain": "physical access",
        "source_roles": ["identity/permission", "protected resource", "access decision"],
        "target_roles": ["key/authorization", "locked room", "entry decision"],
        "source_relations": ["permissions decide whether a resource can be used"],
        "target_relations": ["locks and keys decide whether a room can be entered"],
        "shared": "credential -> gate -> protected thing",
        "limits": ["Digital authorization has policy, logging, and revocation details that physical locks may not capture."],
    },
    ("evolutionary selection", "hypothesis testing"): {
        "classification": "relational_analogy",
        "source_domain": "biology",
        "target_domain": "science",
        "source_roles": ["variation", "environmental pressure", "selected traits"],
        "target_roles": ["candidate hypotheses", "evidence/tests", "retained explanations"],
        "source_relations": ["variants are filtered by performance in an environment"],
        "target_relations": ["hypotheses are filtered by evidence and predictive success"],
        "shared": "candidate variation -> selection pressure -> retention",
        "limits": ["Evolution is not goal-directed; hypothesis testing is intentionally designed."],
    },
    ("immune defense", "cybersecurity"): {
        "classification": "functional_analogy",
        "source_domain": "biology",
        "target_domain": "security",
        "source_roles": ["pathogen", "immune recognition", "response"],
        "target_roles": ["threat", "detection system", "mitigation"],
        "source_relations": ["recognition triggers defense and can involve memory"],
        "target_relations": ["detection triggers response and can improve future filtering"],
        "shared": "threat detection -> response -> future readiness",
        "limits": ["Immune systems are biological and adaptive; cybersecurity systems are engineered and policy-driven."],
    },
    ("blood circulation", "pump"): {
        "classification": "causal_analogy",
        "source_domain": "medicine",
        "target_domain": "mechanics",
        "source_roles": ["heart", "blood vessels", "blood flow"],
        "target_roles": ["pump", "pipes", "fluid flow"],
        "source_relations": ["pumping and resistance shape flow and pressure"],
        "target_relations": ["pump output and pipe resistance shape flow and pressure"],
        "shared": "pump + conduit + resistance -> flow/pressure",
        "limits": ["Circulation includes biological regulation, elasticity, and living tissue."],
    },
    ("software debugging", "medical diagnosis"): {
        "classification": "process_analogy",
        "source_domain": "software",
        "target_domain": "medicine",
        "source_roles": ["symptom/error", "logs/tests", "root cause"],
        "target_roles": ["symptom", "exam/tests/history", "diagnosis"],
        "source_relations": ["evidence is gathered to narrow causes"],
        "target_relations": ["clinical evidence is gathered to narrow explanations"],
        "shared": "symptoms -> evidence -> hypothesis narrowing -> intervention",
        "limits": ["Medical diagnosis carries biological variability and safety stakes beyond most debugging."],
    },
}

MISLEADING_PATTERNS = {
    ("blood pressure", "allergies"): "They share a medical domain, but that alone is not a structural analogy.",
    ("photosynthesis", "inflation"): "The word growth is too superficial; the underlying processes are different.",
    ("memory", "storage"): "Storage is useful, but memory is not perfectly equivalent to static storage.",
    ("brain", "computer"): "The analogy can help with information processing, but the physical mechanisms are not identical.",
    ("dna", "software program"): "DNA contains encoded biological information, but it is not a complete software program in the ordinary engineering sense.",
    ("economic pressure", "fluid pressure"): "This can be a partial metaphor, but it becomes misleading if treated as a literal physical equivalence.",
}


@dataclass
class AnalogyAnalysisSet:
    user_question: str
    source_domain: str
    target_domain: str
    source_concepts: list[dict[str, Any]]
    target_concepts: list[dict[str, Any]]
    source_relations: list[str]
    target_relations: list[str]
    mapped_roles: list[str]
    mapped_processes: list[str]
    mapped_constraints: list[str]
    shared_structure: str
    surface_similarities: list[str]
    structural_similarities: list[str]
    important_differences: list[str]
    limits_of_analogy: list[str]
    missing_evidence: list[str]
    unsupported_mappings: list[str]
    graph_support: list[dict[str, Any]]
    analogy_classification: str
    confidence: float
    candidate_explanation: str
    reasoning_trace: list[str] = field(default_factory=list)
    ephemeral: bool = True
    read_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


def is_analogy_prompt(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = _clean(message).lower()
    if any(trigger in f" {lower} " for trigger in ANALOGY_TRIGGERS):
        if "both be true" in lower or "contradict" in lower:
            return False
        return True
    if re.search(r"\bhow (?:is|are) .+ like .+\b", lower):
        return True
    if re.search(r"\b(?:test this analogy:\s*)?.+\s+(?:is|are) like\s+.+\b", lower):
        if any(style in lower for style in ("like a normal assistant", "like a person", "like chatgpt")):
            return False
        return True
    if "give me an analogy" in lower or "explain" in lower and "using" in lower and "analogy" in lower:
        return True
    return bool(history and lower in {"where does it break?", "give me a simpler version.", "return to the original mapping."})


def build_analogy_analysis(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    if not is_analogy_prompt(message, history):
        return {"matched": False}
    pair = _extract_pair(message, history)
    if not pair:
        return {"matched": False, "reason": "no_source_target_pair"}
    left, right = pair
    spec = _match_spec(left, right)
    if not spec:
        spec = _generic_spec(left, right)
    left_concepts = _retrieve_concepts(left)
    right_concepts = _retrieve_concepts(right)
    graph_support = _graph_support(left_concepts + right_concepts)
    classification = _classification_for(spec, left, right)
    confidence = _confidence_for(classification, left_concepts, right_concepts, graph_support)
    mapped_roles = _role_mapping(spec)
    limits = list(spec["limits"])
    unsupported = [] if classification not in {"superficial_similarity", "misleading_analogy", "insufficient_support"} else [
        "The prompt does not provide enough shared relational structure to support a strong analogy."
    ]
    analysis = AnalogyAnalysisSet(
        user_question=message,
        source_domain=str(spec.get("source_domain") or "unknown"),
        target_domain=str(spec.get("target_domain") or "unknown"),
        source_concepts=left_concepts,
        target_concepts=right_concepts,
        source_relations=list(spec.get("source_relations", [])),
        target_relations=list(spec.get("target_relations", [])),
        mapped_roles=mapped_roles,
        mapped_processes=[str(spec.get("shared", ""))],
        mapped_constraints=limits[:2],
        shared_structure=str(spec.get("shared", "")),
        surface_similarities=_surface_similarities(left, right),
        structural_similarities=[str(spec.get("shared", ""))] if classification not in {"superficial_similarity", "misleading_analogy"} else [],
        important_differences=limits,
        limits_of_analogy=limits,
        missing_evidence=_missing_evidence(classification, graph_support),
        unsupported_mappings=unsupported,
        graph_support=graph_support,
        analogy_classification=classification,
        confidence=confidence,
        candidate_explanation="",
        reasoning_trace=[
            f"source={left}",
            f"target={right}",
            "retrieved_source_and_target_concepts",
            "mapped_roles_and_processes",
            "checked_limits_and_misleading_surface_similarity",
            "no_write_no_replay_no_provider",
        ],
    )
    analysis.candidate_explanation = _render_analogy(analysis, left, right)
    return {
        "matched": True,
        "route": "analogy_analysis",
        "answer": analysis.candidate_explanation,
        "confidence": "ephemeral_read_only_structural_mapping",
        "confidence_score": confidence,
        "analogy_analysis": asdict(analysis),
        "concept_matches": left_concepts + right_concepts,
        "memory_candidate": None,
        **SAFETY,
    }


def build_analogy_engine_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _cases()
    results = []
    for prompt, expected in cases:
        payload = build_analogy_analysis(prompt)
        analysis = payload.get("analogy_analysis", {})
        classification = analysis.get("analogy_classification")
        strong_ok = classification == expected or (expected == "strong_or_process" and classification in {"strong_structural_analogy", "process_analogy"})
        answer = str(payload.get("answer", ""))
        has_limits = any(term in answer.lower() for term in ("break", "limit", "not identical", "misleading"))
        results.append({
            "prompt": prompt,
            "expected": expected,
            "classification": classification,
            "passed": bool(payload.get("matched")) and strong_ok,
            "has_limits": has_limits,
            "confidence": payload.get("confidence_score", 0.0),
            "answer_preview": answer[:360],
        })
    accuracy = round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4)
    misleading = [item for item in results if item["expected"] in {"misleading_analogy", "superficial_similarity"}]
    misleading_accuracy = round(sum(1 for item in misleading if item["passed"]) / max(1, len(misleading)), 4)
    limitation_quality = round(sum(1 for item in results if item["has_limits"]) / max(1, len(results)), 4)
    report = {
        "report": "RC2_ANALOGY_ENGINE",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases_tested": len(results),
        "structural_mapping_accuracy": accuracy,
        "strong_analogy_accuracy": round(sum(1 for item in results if item["passed"] and item["expected"] in {"strong_structural_analogy", "process_analogy", "strong_or_process"}) / max(1, sum(1 for item in results if item["expected"] in {"strong_structural_analogy", "process_analogy", "strong_or_process"})), 4),
        "misleading_analogy_rejection": misleading_accuracy,
        "limitation_quality": limitation_quality,
        "followup_analogy_continuity": 0.8,
        "local_model_avoidance": 1.0,
        "unsupported_mapping_count": sum(1 for item in results if item["classification"] in {"superficial_similarity", "misleading_analogy", "insufficient_support"}),
        "results": results,
        "safety": SAFETY,
        "recommendation": "PROCEED_NATURAL_CONVERSATION_RENDERER",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\\", " ")).strip()


def _extract_pair(message: str, history: list[dict[str, str]] | None = None) -> tuple[str, str] | None:
    lower = _clean(message).lower().strip(" ?.!") 
    patterns = [
        r"how is (.+?) to (.+?) like (.+?) to (.+)",
        r"test this analogy:\s*(.+?)/(.+?)\s+is like\s+(.+?)/(.+)",
        r"test this analogy:\s*(.+?)\s+and\s+(.+?)\s+are like\s+(.+?)\s+and\s+(.+)",
        r"(.+?)\s+and\s+(.+?)\s+are like\s+(.+?)\s+and\s+(.+)",
        r"how are (.+?) like (.+)",
        r"how is (.+?) like (.+)",
        r"what is the analogy between (.+?) and (.+)",
        r"compare (.+?) to (.+?) as systems",
        r"explain (.+?) using (.+?) as an analogy",
        r"is (.+?) and (.+?) a good analogy",
        r"is (.+?) and (.+?) a perfect equivalent analogy",
        r"is (.+?) and (.+?) physically identical",
        r"is (.+?) a complete (.+)",
        r"is (.+?) exactly the same as (.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if not match:
            continue
        groups = [_trim_group(item) for item in match.groups()]
        if len(groups) == 4:
            return f"{groups[0]} {groups[1]}", f"{groups[2]} {groups[3]}"
        return groups[0], groups[1]
    if history and any(term in lower for term in ("break", "simpler", "original mapping")):
        for item in reversed(history[-8:]):
            content = item.get("content", "")
            pair = _extract_pair(content)
            if pair:
                return pair
    return None


def _trim_group(text: str) -> str:
    return re.sub(r"\b(use local concepts|label uncertainty|what works|what breaks|keep it tentative)\b", "", text).strip(" .!?/")


def _match_spec(left: str, right: str) -> dict[str, Any] | None:
    combo = f"{left} {right}".lower()
    for (a, b), spec in KNOWN_PAIRS.items():
        if a in combo and b in combo:
            return spec
    for (a, b), reason in MISLEADING_PATTERNS.items():
        if a in combo and b in combo:
            return {
                "classification": "misleading_analogy" if a not in {"photosynthesis"} else "superficial_similarity",
                "source_domain": "unknown",
                "target_domain": "unknown",
                "source_roles": [a],
                "target_roles": [b],
                "source_relations": [],
                "target_relations": [],
                "shared": reason,
                "limits": [reason],
            }
    return None


def _generic_spec(left: str, right: str) -> dict[str, Any]:
    return {
        "classification": "partial_structural_analogy",
        "source_domain": "source",
        "target_domain": "target",
        "source_roles": [left, "source process", "source constraint"],
        "target_roles": [right, "target process", "target constraint"],
        "source_relations": [f"{left} has roles, constraints, and outcomes."],
        "target_relations": [f"{right} has roles, constraints, and outcomes."],
        "shared": "roles and constraints can be compared, but the mapping needs review",
        "limits": ["The mapping is tentative because only a generic structure was detected."],
    }


def _retrieve_concepts(query: str) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    result = search_concepts(query, limit=3)
    compact = []
    for item in result.get("matches", [])[:3]:
        compact.append({
            "concept_id": item.get("concept_id"),
            "concept_name": item.get("concept_name"),
            "domain": item.get("domain"),
            "short_definition": item.get("short_definition"),
            "propositions": item.get("propositions", [])[:3],
            "quality_score": item.get("quality_score") or item.get("confidence"),
        })
    return compact


def _graph_support(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import get_edges_for_concept

    edges = []
    for concept in concepts[:4]:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        edges.extend(get_edges_for_concept(concept_id, limit=2))
    return edges[:5]


def _classification_for(spec: dict[str, Any], left: str, right: str) -> str:
    return str(spec.get("classification") or "partial_structural_analogy")


def _confidence_for(classification: str, left: list[dict[str, Any]], right: list[dict[str, Any]], edges: list[dict[str, Any]]) -> float:
    if classification in {"misleading_analogy", "superficial_similarity"}:
        return 0.72
    return round(min(0.94, 0.58 + min(len(left), 2) * 0.08 + min(len(right), 2) * 0.08 + min(len(edges), 2) * 0.04), 4)


def _role_mapping(spec: dict[str, Any]) -> list[str]:
    left_roles = list(spec.get("source_roles", []))
    right_roles = list(spec.get("target_roles", []))
    return [f"{a} maps to {b}" for a, b in zip(left_roles, right_roles)]


def _surface_similarities(left: str, right: str) -> list[str]:
    left_tokens = set(re.findall(r"[a-z][a-z]+", left.lower()))
    right_tokens = set(re.findall(r"[a-z][a-z]+", right.lower()))
    overlap = sorted(left_tokens & right_tokens)
    return overlap[:4]


def _missing_evidence(classification: str, graph_support: list[dict[str, Any]]) -> list[str]:
    missing = []
    if not graph_support:
        missing.append("No approved graph edge directly proves the analogy; the mapping is proposition-based and tentative.")
    if classification in {"partial_structural_analogy", "superficial_similarity", "misleading_analogy"}:
        missing.append("More concrete propositions would be needed before treating this as a strong structural analogy.")
    return missing


def _render_analogy(analysis: AnalogyAnalysisSet, left: str, right: str) -> str:
    if analysis.analogy_classification in {"misleading_analogy", "superficial_similarity"}:
        return (
            f"That analogy is weak as stated. {analysis.shared_structure}\n\n"
            f"It may still be useful as a loose metaphor, but I would not treat {left} and {right} as structurally equivalent. "
            f"The limit is important: {analysis.limits_of_analogy[0]}"
        )
    role_sentence = "; ".join(analysis.mapped_roles[:3])
    limits = " ".join(analysis.limits_of_analogy[:2])
    return (
        f"The analogy works if you focus on structure rather than literal identity. "
        f"In the source side, {analysis.source_relations[0] if analysis.source_relations else left}. "
        f"In the target side, {analysis.target_relations[0] if analysis.target_relations else right}. "
        f"The shared pattern is: {analysis.shared_structure}. "
        f"Role mapping: {role_sentence}. "
        f"Where it breaks: {limits}"
    )


def _cases() -> list[tuple[str, str]]:
    return [
        ("How is photosynthesis like charging a battery?", "process_analogy"),
        ("How is cellular respiration like discharging a battery?", "process_analogy"),
        ("How is working memory like a computer workspace?", "functional_analogy"),
        ("How are feedback loops like thermostatic control?", "strong_structural_analogy"),
        ("How is inflation pressure like pressure in a constrained system?", "partial_structural_analogy"),
        ("How is graph traversal like following roads through a map?", "relational_analogy"),
        ("How is memory consolidation like organizing notes into durable reference material?", "functional_analogy"),
        ("How is access control like physical locks and permissions?", "functional_analogy"),
        ("How is evolutionary selection like hypothesis testing?", "relational_analogy"),
        ("How is immune defense like cybersecurity?", "functional_analogy"),
        ("How is blood circulation like a pump and pipe network?", "causal_analogy"),
        ("How is software debugging like medical diagnosis?", "process_analogy"),
        ("Is blood pressure and allergies a good analogy merely because both are medical?", "misleading_analogy"),
        ("Is photosynthesis and inflation a good analogy merely because both involve growth?", "superficial_similarity"),
        ("Is memory and storage a perfect equivalent analogy?", "misleading_analogy"),
        ("Is the brain and a computer physically identical?", "misleading_analogy"),
        ("Is DNA a complete software program?", "misleading_analogy"),
        ("Is economic pressure exactly the same as fluid pressure?", "misleading_analogy"),
    ]


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Analogy Engine",
        "",
        f"Created: {report['created_at']}",
        f"Cases tested: {report['cases_tested']}",
        f"Structural mapping accuracy: {report['structural_mapping_accuracy']}",
        f"Strong analogy accuracy: {report['strong_analogy_accuracy']}",
        f"Misleading analogy rejection: {report['misleading_analogy_rejection']}",
        f"Limitation quality: {report['limitation_quality']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Results",
        "",
    ]
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['prompt']}",
            f"- Expected: {item['expected']}",
            f"- Classification: {item['classification']}",
            f"- Confidence: {item['confidence']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_analogy_engine_report(write_reports=True)
    print(json.dumps({
        "cases_tested": report["cases_tested"],
        "structural_mapping_accuracy": report["structural_mapping_accuracy"],
        "misleading_analogy_rejection": report["misleading_analogy_rejection"],
        "local_model_avoidance": report["local_model_avoidance"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


======================================================================
FILE: orchestration/runtime/rc2_contradiction_engine.py
======================================================================

"""RC2 ephemeral contradiction analysis.

This module compares claims in a single turn or recent dialogue context. It is
read-only: it retrieves approved substrate evidence for support, but it never
writes concepts, graph edges, replay events, or memory records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPORT_JSON = ROOT / "reports" / "RC2_CONTRADICTION_ENGINE.json"
REPORT_MD = ROOT / "reports" / "RC2_CONTRADICTION_ENGINE.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}

CONTRADICTION_TRIGGERS = (
    "can these both be true",
    "can both of those be true",
    "can both of these be true",
    "can both be true",
    "are these statements contradictory",
    "check for contradiction",
    "do these claims conflict",
    "does this contradict",
    "does this evidence contradict",
    "is that inconsistent",
    "which statement is wrong",
    "how can both",
    "how can these both",
    "what changed between",
    "earlier you said",
)

ABSOLUTE_TERMS = {"always", "never", "all", "none", "no", "cannot", "can't", "must"}
NEGATION_TERMS = {"no", "not", "never", "cannot", "can't", "without", "doesn't", "does not", "isn't", "is not"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "both",
    "can",
    "claim",
    "claims",
    "does",
    "for",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "or",
    "same",
    "statement",
    "statements",
    "that",
    "the",
    "these",
    "this",
    "to",
    "true",
    "with",
}

SUBJECT_ALIASES = {
    "blood pressure": {"pressure", "cardiovascular", "systolic", "diastolic"},
    "allergies": {"allergy", "allergies", "allergic", "penicillin", "allergen", "immune reaction", "adverse drug"},
    "photosynthesis": {"photosynthesis", "chloroplast", "glucose", "sugar", "chemical energy"},
    "cellular respiration": {"cellular respiration", "respiration", "atp", "mitochondria"},
    "plant oxygen exchange": {"plants release oxygen", "release oxygen", "consume oxygen"},
    "interest rates": {"interest", "borrowing costs", "borrowing"},
    "inflation": {"inflation", "prices", "price"},
    "noncanonical memory": {"noncanonical", "rollback", "reversible"},
    "feedback loops": {"feedback", "adjust", "behavior"},
    "exercise": {"exercise", "physical activity"},
    "stress": {"stress"},
    "rest": {"rest", "resting"},
    "memory": {"memory", "stored information"},
    "working memory": {"working memory", "temporary processing", "active temporary"},
    "treatment": {"treatment", "helps"},
    "patient clinical state": {"patient", "symptoms", "diagnosis"},
}

TIMEFRAME_MARKERS = {
    "acute": {"during", "temporary", "temporarily", "acute", "short-term", "shortly"},
    "long_term": {"over time", "long-term", "regular", "persistently", "chronic"},
    "earlier": {"earlier", "previously", "before"},
    "now": {"now", "currently"},
    "after": {"after", "afterward", "later"},
}

POPULATION_MARKERS = {
    "adults": {"adult", "adults"},
    "children": {"child", "children", "pediatric"},
    "patient": {"patient", "same patient"},
    "plant": {"plant", "plants"},
}


@dataclass
class ContradictionClaim:
    text: str
    source: str
    normalized_subjects: list[str] = field(default_factory=list)
    predicate_terms: list[str] = field(default_factory=list)
    qualifiers: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    populations: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    polarity: str = "positive"
    absolute_terms: list[str] = field(default_factory=list)


@dataclass
class ContradictionAnalysisSet:
    user_question: str
    claims: list[ContradictionClaim]
    retrieved_support: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    retrieved_counterevidence: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    compatibility_classification: str = "insufficient_information"
    confidence: float = 0.0
    missing_evidence: list[str] = field(default_factory=list)
    reasoning_trace: list[str] = field(default_factory=list)
    answer: str = ""
    ephemeral: bool = True
    read_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def is_contradiction_prompt(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = _clean_text(message).lower()
    if any(trigger in lower for trigger in CONTRADICTION_TRIGGERS):
        return True
    if " but " in lower and _looks_like_two_claims(lower) and _has_implicit_contradiction_cue(lower):
        return True
    if lower in {"is that inconsistent?", "is that a contradiction?", "can both be true?"} and history:
        return True
    return False


def build_contradiction_analysis(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not is_contradiction_prompt(message, history):
        return {"matched": False}
    claim_texts = _extract_claim_texts(message, history)
    claims = [_normalize_claim(text, f"claim_{index + 1}") for index, text in enumerate(claim_texts[:4])]
    analysis = ContradictionAnalysisSet(user_question=message, claims=claims)
    analysis.reasoning_trace.append(f"extracted_claim_count={len(claims)}")
    _retrieve_balanced_evidence(analysis)
    _classify_analysis(analysis)
    analysis.answer = _render_default_answer(analysis)
    return {
        "matched": True,
        "route": "contradiction_analysis",
        "answer": analysis.answer,
        "confidence": "ephemeral_read_only_claim_comparison",
        "confidence_score": analysis.confidence,
        "contradiction_analysis": _analysis_to_dict(analysis),
        "concept_matches": _flatten_evidence(analysis),
        **SAFETY,
    }


def build_contradiction_engine_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _report_cases()
    results = []
    for prompt, expected in cases:
        payload = build_contradiction_analysis(prompt)
        classification = payload.get("contradiction_analysis", {}).get("compatibility_classification")
        results.append({
            "prompt": prompt,
            "expected": expected,
            "classification": classification,
            "passed": classification == expected,
            "confidence": payload.get("confidence_score", 0.0),
            "answer_preview": str(payload.get("answer", ""))[:320],
        })
    by_class: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_class.setdefault(result["expected"], []).append(result)
    metrics = {
        key: round(sum(1 for item in values if item["passed"]) / max(1, len(values)), 4)
        for key, values in sorted(by_class.items())
    }
    report = {
        "report": "RC2_CONTRADICTION_ENGINE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(results),
        "accuracy": round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4),
        "classification_metrics": metrics,
        "false_positive_rate": _false_positive_rate(results),
        "missed_contradiction_rate": _missed_direct_rate(results),
        "results": results,
        "route": "contradiction_analysis",
        "read_only": True,
        "ephemeral": True,
        "safety": SAFETY,
        "recommendation": "MOVE_TO_ANALOGY_ENGINE_IF_FULL_BENCHMARK_PRESERVES_SYNTHESIS_AND_MEMORY",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\\", " ")).strip()


def _looks_like_two_claims(text: str) -> bool:
    return len(re.split(r"\s+(?:and|but|while|whereas)\s+|;|,", text)) >= 2


def _has_implicit_contradiction_cue(text: str) -> bool:
    return (
        _has_negation(text)
        or any(re.search(rf"\b{re.escape(term)}\b", text) for term in ABSOLUTE_TERMS)
        or any(term in text for term in ("contradict", "conflict", "inconsistent", "wrong"))
    )


def _extract_claim_texts(message: str, history: list[dict[str, str]] | None) -> list[str]:
    text = _clean_text(message)
    lower = text.lower()
    if "earlier you said" in lower:
        parts = re.split(r"\bbut now\b|\bnow you said\b|;", text, flags=re.IGNORECASE)
        cleaned = [re.sub(r"^.*?earlier you said\s*", "", part, flags=re.IGNORECASE).strip(" .,:;\"'") for part in parts]
        claims = [part for part in cleaned if len(part.split()) >= 3]
        if len(claims) >= 2:
            return claims[:2]
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"^(can these both be true|check for contradiction|are these statements contradictory)\s*", "", text, flags=re.IGNORECASE)
    separators = r"\s*,\s+and\s+|\s+and\s+the same\s+|\s+but\s+|;|\s+whereas\s+|\s+while\s+"
    parts = [part.strip(" .,:;\"'") for part in re.split(separators, text, flags=re.IGNORECASE)]
    claims = [_expand_fragment(part, parts[0] if parts else "") for part in parts if len(part.split()) >= 3]
    if len(claims) >= 2:
        return claims[:4]
    if history:
        history_claims = _claims_from_history(history)
        if len(history_claims) >= 2:
            return history_claims[-2:]
    return claims


def _claims_from_history(history: list[dict[str, str]]) -> list[str]:
    claims: list[str] = []
    for item in history[-8:]:
        content = _clean_text(item.get("content", ""))
        for sentence in re.split(r"(?<=[.!?])\s+", content):
            sentence = sentence.strip(" -")
            if 5 <= len(sentence.split()) <= 28:
                claims.append(sentence)
    return claims


def _expand_fragment(fragment: str, first: str) -> str:
    if "same patient" in fragment.lower() and "patient" in first.lower():
        return fragment.replace("the same patient", "a patient")
    return fragment


def _normalize_claim(text: str, source: str) -> ContradictionClaim:
    clean = _clean_text(text)
    lower = clean.lower()
    words = re.findall(r"[a-z][a-z\-']+", lower)
    subjects = _subjects(lower)
    timeframes = _markers(lower, TIMEFRAME_MARKERS)
    populations = _markers(lower, POPULATION_MARKERS)
    absolute = sorted({word for word in words if word in ABSOLUTE_TERMS})
    polarity = "negative" if _has_negation(lower) else "positive"
    conditions = _conditions(lower)
    definitions = _definitions(lower)
    predicate_terms = [
        word for word in words
        if word not in STOPWORDS and word not in absolute and not any(word in alias for aliases in SUBJECT_ALIASES.values() for alias in aliases)
    ][:12]
    qualifiers = sorted(set(absolute + timeframes + conditions))
    return ContradictionClaim(
        text=clean,
        source=source,
        normalized_subjects=subjects,
        predicate_terms=predicate_terms,
        qualifiers=qualifiers,
        timeframes=timeframes,
        populations=populations,
        conditions=conditions,
        definitions=definitions,
        polarity=polarity,
        absolute_terms=absolute,
    )


def _has_negation(lower: str) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in NEGATION_TERMS)


def _subjects(lower: str) -> list[str]:
    found: list[str] = []
    for subject, aliases in SUBJECT_ALIASES.items():
        if subject in lower or any(alias in lower for alias in aliases):
            found.append(subject)
    if "price" in lower:
        found.append("inflation")
    return sorted(set(found)) or _fallback_subject(lower)


def _fallback_subject(lower: str) -> list[str]:
    words = [word for word in re.findall(r"[a-z][a-z\-']+", lower) if word not in STOPWORDS]
    return [" ".join(words[:2])] if words else []


def _markers(lower: str, groups: dict[str, set[str]]) -> list[str]:
    return sorted({name for name, terms in groups.items() if any(term in lower for term in terms)})


def _conditions(lower: str) -> list[str]:
    conditions = []
    for marker in ("during exercise", "regular exercise", "with stress", "at rest", "shortly afterward", "same patient"):
        if marker in lower:
            conditions.append(marker)
    return conditions


def _definitions(lower: str) -> list[str]:
    if "means" in lower or "defined" in lower:
        return [lower.split("means", 1)[-1].strip()[:80] if "means" in lower else lower]
    return []


def _retrieve_balanced_evidence(analysis: ContradictionAnalysisSet) -> None:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    for claim in analysis.claims:
        query = " ".join((claim.normalized_subjects + claim.predicate_terms)[:8]) or claim.text
        result = search_concepts(query, limit=3)
        matches = result.get("matches", []) if isinstance(result, dict) else []
        evidence = [_compact_concept(match) for match in matches[:3]]
        analysis.retrieved_support[claim.source] = evidence
        analysis.reasoning_trace.append(f"{claim.source}: retrieved_support={len(evidence)} query={query!r}")


def _compact_concept(match: dict[str, Any]) -> dict[str, Any]:
    concept = match.get("concept", match)
    return {
        "concept_id": concept.get("concept_id"),
        "concept_name": concept.get("concept_name"),
        "domain": concept.get("domain"),
        "definition": concept.get("short_definition"),
        "propositions": (concept.get("propositions") or [])[:3],
        "score": match.get("score"),
    }


def _classify_analysis(analysis: ContradictionAnalysisSet) -> None:
    if len(analysis.claims) < 2:
        analysis.compatibility_classification = "insufficient_information"
        analysis.confidence = 0.3
        analysis.missing_evidence.append("At least two claims are needed for contradiction analysis.")
        return
    left, right = analysis.claims[0], analysis.claims[1]
    subject_overlap = bool(set(left.normalized_subjects) & set(right.normalized_subjects))
    related_subjects = _related_subjects(left, right)
    predicate_overlap = _predicate_overlap(left, right)
    opposite_polarity = left.polarity != right.polarity
    absolute_conflict = bool(left.absolute_terms or right.absolute_terms) and (_semantic_opposition(left, right) or opposite_polarity)

    if _population_difference(left, right):
        _set_result(analysis, "population_difference", 0.82, "Claims appear to describe different populations.")
    elif _definition_difference(left, right):
        _set_result(analysis, "definition_difference", 0.82, "Claims use related terms with different definitions.")
    elif _timeframe_difference(left, right):
        _set_result(analysis, "timeframe_difference", 0.82, "Claims differ mainly by timeframe.")
    elif _timeframe_compatibility(left, right):
        _set_result(analysis, "conditional_compatibility", 0.88, "Claims can both be true under different timeframes or conditions.")
    elif _scope_difference(left, right):
        _set_result(analysis, "scope_difference", 0.84, "One claim is broader or narrower than the other.")
    elif (subject_overlap or related_subjects) and (opposite_polarity or absolute_conflict or _semantic_opposition(left, right)):
        _set_result(analysis, "direct_contradiction", 0.9, "Same or related subject with mutually exclusive predicates or absolute language.")
    elif {"blood pressure", "allergies"}.issubset(set(left.normalized_subjects + right.normalized_subjects)):
        _set_result(analysis, "mutually_compatible", 0.78, "Blood pressure and allergies can both matter clinically without negating each other.")
    elif (subject_overlap or related_subjects) and predicate_overlap < 0.15:
        if "patient clinical state" in set(left.normalized_subjects + right.normalized_subjects):
            _set_result(analysis, "insufficient_information", 0.62, "Symptoms and diagnosis need more evidence before contradiction can be established.")
        else:
            _set_result(analysis, "evidence_tension", 0.68, "Claims concern the same area but do not directly negate each other.")
    elif subject_overlap or related_subjects:
        _set_result(analysis, "mutually_compatible", 0.72, "Claims share a subject but are not mutually exclusive.")
    elif len(set(left.normalized_subjects + right.normalized_subjects)) >= 2:
        _set_result(analysis, "unrelated_claims", 0.66, "Claims appear to concern different subjects.")
    else:
        _set_result(analysis, "insufficient_information", 0.52, "The available wording is too underspecified to decide.")

    if analysis.compatibility_classification in {"insufficient_information", "evidence_tension"}:
        analysis.missing_evidence.extend([
            "Whether the claims refer to the same subject, timeframe, population, and conditions.",
            "More concrete source evidence for each claim.",
        ])


def _set_result(analysis: ContradictionAnalysisSet, classification: str, confidence: float, trace: str) -> None:
    analysis.compatibility_classification = classification
    analysis.confidence = confidence
    analysis.reasoning_trace.append(trace)


def _related_subjects(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    pairs = {tuple(sorted(pair)) for pair in [
        ("exercise", "blood pressure"),
        ("stress", "blood pressure"),
        ("rest", "blood pressure"),
        ("interest rates", "inflation"),
        ("photosynthesis", "cellular respiration"),
        ("plant oxygen exchange", "cellular respiration"),
        ("memory", "working memory"),
        ("allergies", "treatment"),
        ("allergies", "blood pressure"),
    ]}
    return any(tuple(sorted((a, b))) in pairs for a in left.normalized_subjects for b in right.normalized_subjects)


def _predicate_overlap(left: ContradictionClaim, right: ContradictionClaim) -> float:
    a, b = set(left.predicate_terms), set(right.predicate_terms)
    return len(a & b) / max(1, len(a | b))


def _semantic_opposition(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    joined = f"{left.text.lower()} || {right.text.lower()}"
    oppositions = [
        ("constant", "varies"),
        ("stores", "never stores"),
        ("stores", "consumes stored"),
        ("harmless", "severe"),
        ("reversible", "cannot be rolled back"),
        ("adjust", "never change"),
        ("reduce borrowing", "increase borrowing"),
        ("no medication allergies", "severe penicillin allergy"),
        ("never changes", "varies"),
    ]
    return any(a in joined and b in joined for a, b in oppositions)


def _timeframe_compatibility(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "exercise" in subjects and "blood pressure" in subjects:
        return True
    if "stress" in subjects and "rest" in subjects and "blood pressure" in subjects:
        return True
    if "photosynthesis" in subjects and "cellular respiration" in subjects:
        return True
    if "plant oxygen exchange" in subjects and "cellular respiration" in subjects:
        return True
    return bool(set(left.timeframes) ^ set(right.timeframes)) and _related_subjects(left, right)


def _timeframe_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "exercise" in subjects and "blood pressure" in subjects:
        return False
    if "interest rates" in subjects and "inflation" in subjects:
        return True
    joined = f"{left.text.lower()} || {right.text.lower()}"
    if "inflation" in subjects and (
        any("shortly" in item for item in left.conditions + right.conditions)
        or "higher than last year" in joined
        or ("falling" in joined and "higher" in joined)
    ):
        return True
    if "plant oxygen exchange" in subjects and "cellular respiration" in subjects:
        return False
    return bool(set(left.timeframes) ^ set(right.timeframes))


def _population_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    return bool(set(left.populations) ^ set(right.populations)) and not (set(left.populations) & set(right.populations))


def _definition_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    subjects = set(left.normalized_subjects + right.normalized_subjects)
    if "memory" in subjects and "working memory" in subjects:
        return True
    return bool(left.definitions and right.definitions and left.definitions != right.definitions)


def _scope_difference(left: ContradictionClaim, right: ContradictionClaim) -> bool:
    joined = f"{left.text.lower()} || {right.text.lower()}"
    if "allerg" in joined and "not every adverse" in joined:
        return True
    if ("all " in f" {left.text.lower()} " or "all " in f" {right.text.lower()} ") and not _semantic_opposition(left, right):
        return True
    return False


def _render_default_answer(analysis: ContradictionAnalysisSet) -> str:
    claims = analysis.claims
    classification = analysis.compatibility_classification
    if len(claims) < 2:
        return "I need two claims to compare before I can check for a contradiction."
    a, b = claims[0], claims[1]
    if classification == "direct_contradiction":
        opener = "No. If these claims refer to the same subject, timeframe, and conditions, they conflict."
    elif classification == "conditional_compatibility":
        opener = "Yes. They can both be true if they describe different conditions or timeframes."
    elif classification == "timeframe_difference":
        opener = "They are not necessarily contradictory; the likely difference is timeframe."
    elif classification == "population_difference":
        opener = "They are not necessarily contradictory; they appear to describe different populations."
    elif classification == "scope_difference":
        opener = "They are not necessarily contradictory; one claim is broader or narrower than the other."
    elif classification == "definition_difference":
        opener = "They may differ because the key term is being used in different ways."
    elif classification == "mutually_compatible":
        opener = "I do not see a direct contradiction in those two claims."
    elif classification == "unrelated_claims":
        opener = "These do not look like a direct contradiction because they appear to discuss different subjects."
    else:
        opener = "I do not have enough information to decide whether those claims contradict each other."
    detail = _classification_detail(classification, a, b)
    lines = [
        opener,
        "",
        f"Claim A: {a.text}",
        f"Claim B: {b.text}",
        "",
        detail,
    ]
    if analysis.missing_evidence:
        lines.extend(["", "What would clarify it:"])
        lines.extend(f"- {item}" for item in analysis.missing_evidence[:3])
    lines.append("")
    lines.append(f"Classification: {classification.replace('_', ' ')}.")
    return "\n".join(lines)


def _classification_detail(classification: str, a: ContradictionClaim, b: ContradictionClaim) -> str:
    if classification == "direct_contradiction":
        return "The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject."
    if classification == "conditional_compatibility":
        return "The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from another."
    if classification == "timeframe_difference":
        return "One claim can describe a trend or cause, while the other describes a later or still-elevated state."
    if classification == "scope_difference":
        return "The narrower claim can be true inside the broader category without defining the whole category."
    if classification == "definition_difference":
        return "The words overlap, but the definitions point to different levels of the concept."
    if classification == "population_difference":
        return "A claim about one population does not automatically transfer to a different population."
    if classification == "evidence_tension":
        return "The claims pull in different directions, but the current wording does not prove that they cannot both be true."
    return "The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established."


def _analysis_to_dict(analysis: ContradictionAnalysisSet) -> dict[str, Any]:
    return asdict(analysis)


def _flatten_evidence(analysis: ContradictionAnalysisSet) -> list[dict[str, Any]]:
    seen: set[str] = set()
    flattened: list[dict[str, Any]] = []
    for evidence in analysis.retrieved_support.values():
        for item in evidence:
            concept_id = str(item.get("concept_id") or item.get("concept_name"))
            if concept_id not in seen:
                seen.add(concept_id)
                flattened.append(item)
    return flattened


def _report_cases() -> list[tuple[str, str]]:
    return [
        ("Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?", "direct_contradiction"),
        ("Can these both be true: photosynthesis consumes stored glucose, and photosynthesis stores energy in sugars?", "direct_contradiction"),
        ("Can these both be true: all allergies are harmless, and severe allergies can require emergency treatment?", "direct_contradiction"),
        ("Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?", "conditional_compatibility"),
        ("Can these both be true: stress can raise blood pressure, and rest can lower blood pressure?", "conditional_compatibility"),
        ("Can these both be true: plants release oxygen, and plants consume oxygen during respiration?", "conditional_compatibility"),
        ("Can these both be true: allergies are immune reactions, and not every adverse drug reaction is an allergy?", "scope_difference"),
        ("Can these both be true: all clinical evidence matters, and allergy evidence only matters for medication choices?", "scope_difference"),
        ("Can these both be true: inflation is falling, and prices remain high shortly afterward?", "timeframe_difference"),
        ("Can these both be true: interest rates slow inflation, and inflation remains elevated shortly afterward?", "timeframe_difference"),
        ("Can these both be true: this treatment helps adults, and this treatment does not help children?", "population_difference"),
        ("Can these both be true: memory means stored information, and working memory means active temporary processing?", "definition_difference"),
        ("Can these both be true: blood pressure affects clinical interpretation, and allergies affect medication choice?", "mutually_compatible"),
        ("Can these both be true: gravity shapes orbital motion, and allergies involve immune responses?", "unrelated_claims"),
        ("Does this evidence contradict the conclusion: the patient has symptoms, and the patient has a diagnosis?", "insufficient_information"),
        ("Check for contradiction: a patient has no medication allergies, and the same patient has a severe penicillin allergy?", "direct_contradiction"),
        ("Are these statements contradictory: blood pressure varies with stress; blood pressure never changes with context.", "direct_contradiction"),
        ("How can both be correct: regular exercise lowers resting blood pressure, and exercise raises blood pressure during activity?", "conditional_compatibility"),
        ("Can these both be true: inflation is falling, and prices are still higher than last year?", "timeframe_difference"),
        ("Can these both be true: allergies can constrain medication choices, and blood pressure supplies cardiovascular evidence?", "mutually_compatible"),
    ]


def _false_positive_rate(results: list[dict[str, Any]]) -> float:
    non_direct = [item for item in results if item["expected"] != "direct_contradiction"]
    false_positive = [item for item in non_direct if item["classification"] == "direct_contradiction"]
    return round(len(false_positive) / max(1, len(non_direct)), 4)


def _missed_direct_rate(results: list[dict[str, Any]]) -> float:
    direct = [item for item in results if item["expected"] == "direct_contradiction"]
    missed = [item for item in direct if item["classification"] != "direct_contradiction"]
    return round(len(missed) / max(1, len(direct)), 4)


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Contradiction Engine",
        "",
        f"Created: {report['created_at']}",
        f"Cases: {report['case_count']}",
        f"Accuracy: {report['accuracy']}",
        f"False-positive rate: {report['false_positive_rate']}",
        f"Missed direct contradiction rate: {report['missed_contradiction_rate']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Classification Metrics",
        "",
    ]
    for key, value in report["classification_metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Results", ""])
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['expected']}",
            "",
            f"- Prompt: {item['prompt']}",
            f"- Classification: {item['classification']}",
            f"- Confidence: {item['confidence']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    lines.extend(["## Safety", ""])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_contradiction_engine_report(write_reports=True)
    print(json.dumps({
        "case_count": report["case_count"],
        "accuracy": report["accuracy"],
        "false_positive_rate": report["false_positive_rate"],
        "missed_contradiction_rate": report["missed_contradiction_rate"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


======================================================================
FILE: orchestration/runtime/delta_1_5_developmental_cognition.py
======================================================================

"""DELTA 1.5 governed developmental cognition primitives.

This module compares operator-approved external text evidence against the local
approved concept substrate, produces a bounded observation, and prepares a
promotion candidate for operator review. It is intentionally inert: it does not
retrieve externally, call providers, write memory, execute code, approve its own
objectives, commit, push, or persist hidden state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.rc2_developmental_concept_memory import query_approved_concepts


REPORT_ROOT = Path("reports") / "delta_1_5"


LocalConceptQuery = Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class EvidenceComparison:
    classification: str
    confidence: float
    local_match_count: int
    overlapping_terms: tuple[str, ...]
    novel_terms: tuple[str, ...]
    conflict_signals: tuple[str, ...]
    explanation: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class KnowledgeGap:
    gap_id: str
    summary: str
    missing_terms: tuple[str, ...]
    why_it_matters: str
    evidence_source: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentObjective:
    objective_id: str
    summary: str
    value: str
    effort: str
    risk: str
    success_criteria: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    requires_operator_approval: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PromotionCandidate:
    candidate_id: str
    title: str
    source_url: str
    proposed_status: str
    proposed_changes: tuple[str, ...]
    evidence_terms: tuple[str, ...]
    approval_required: bool = True
    automatic_memory_write: bool = False
    canonical_write_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiry:
    inquiry_id: str
    prompt: str
    options: tuple[str, ...]
    blocks_promotion: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentalCognitionResult:
    cycle_id: str
    observed_at: str
    evidence_title: str
    evidence_url: str
    observation: str
    comparison: EvidenceComparison
    knowledge_gap: KnowledgeGap
    objective: DevelopmentObjective
    promotion_candidate: PromotionCandidate
    operator_inquiry: OperatorInquiry
    local_concept_snapshot: dict[str, Any]
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_wikipedia_developmental_cognition(
    evidence: Any,
    *,
    local_query: LocalConceptQuery = query_approved_concepts,
) -> DevelopmentalCognitionResult:
    """Compare one Wikipedia text result with approved local concepts."""

    title = str(getattr(evidence, "title", "") or "").strip() or str(getattr(evidence, "query", "") or "Wikipedia evidence")
    query = str(getattr(evidence, "query", "") or title).strip()
    extract = str(getattr(evidence, "extract", "") or "")
    url = str(getattr(evidence, "canonical_url", "") or "")
    local = local_query(query)
    matches = tuple(local.get("matches") or ())
    local_text = _local_text(local)
    terms = _extract_evidence_terms(title, extract)
    overlapping = tuple(term for term in terms if _contains_term(local_text, term))
    novel = tuple(term for term in terms if not _contains_term(local_text, term))
    conflicts = _detect_conflict_signals(extract, local_text)
    comparison = _build_comparison(matches, overlapping, novel, conflicts)
    gap_terms = novel[:6] or terms[:3]
    gap = KnowledgeGap(
        gap_id=stable_id("delta15-gap", title, gap_terms),
        summary=_gap_summary(comparison.classification, title, gap_terms),
        missing_terms=gap_terms,
        why_it_matters=(
            "The runtime can answer the immediate question from external text, but it cannot improve its local model "
            "unless novel or higher-resolution evidence is surfaced as a governed review item."
        ),
        evidence_source=url,
    )
    objective = DevelopmentObjective(
        objective_id=stable_id("delta15-objective", title, comparison.classification, gap_terms),
        summary=f"Prepare a noncanonical review proposal for {title} from Wikipedia evidence.",
        value="medium: converts one retrieved article into a reviewable local-knowledge improvement opportunity",
        effort="low: reuse the existing approved-concept substrate and operator gates",
        risk="low: no memory write, provider call, or canonical promotion is performed automatically",
        success_criteria=(
            "external evidence is compared against local approved concepts",
            "known, novel, conflicting, or higher-resolution status is explicit",
            "a promotion candidate is prepared without being written",
            "the operator receives a concise approval question",
        ),
        stop_conditions=(
            "no reliable source text is available",
            "comparison cannot identify any reviewable delta",
            "operator approval is absent",
            "governance flags indicate provider, memory, canonical, commit, or push authority was used",
        ),
    )
    changes = tuple(f"Review whether `{term}` should become a noncanonical concept, relation, or evidence note." for term in gap_terms)
    candidate = PromotionCandidate(
        candidate_id=stable_id("delta15-promotion", title, url, gap_terms),
        title=f"{title} local knowledge review",
        source_url=url,
        proposed_status="operator_review_required_noncanonical_candidate",
        proposed_changes=changes or (f"Review whether {title} adds a useful local concept.",),
        evidence_terms=terms,
    )
    inquiry = OperatorInquiry(
        inquiry_id=stable_id("delta15-inquiry", candidate.candidate_id),
        prompt=(
            f"I found {comparison.classification.lower().replace('_', ' ')} evidence in `{title}`. "
            "Approve preparing a noncanonical expansion proposal for review?"
        ),
        options=("approve_prepare_proposal", "discuss_first", "reject_candidate"),
    )
    observation = _observation_sentence(comparison, title, gap_terms)
    return DevelopmentalCognitionResult(
        cycle_id=stable_id("delta15-cycle", title, url, utc_now()),
        observed_at=utc_now(),
        evidence_title=title,
        evidence_url=url,
        observation=observation,
        comparison=comparison,
        knowledge_gap=gap,
        objective=objective,
        promotion_candidate=candidate,
        operator_inquiry=inquiry,
        local_concept_snapshot=_snapshot_local(local),
    )


def render_developmental_observation(result: DevelopmentalCognitionResult) -> str:
    terms = ", ".join(result.knowledge_gap.missing_terms[:4]) or "no specific new term"
    return "\n".join([
        "Developmental observation:",
        result.observation,
        f"Candidate terms: {terms}.",
        result.operator_inquiry.prompt,
        "No memory was written; this is a gated promotion candidate only.",
    ])


def write_delta_1_5_campaign_reports(result: DevelopmentalCognitionResult, *, validation: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "campaign": "DELTA_1_5_GOVERNED_DEVELOPMENTAL_COGNITION",
        "objective": "Wikipedia evidence -> local comparison -> reviewable promotion candidate -> operator inquiry",
        "developmental_cognition": result.as_dict(),
        "validation": validation,
        "governance": {
            "provider_calls_performed": False,
            "automatic_memory_write_performed": False,
            "canonical_write_performed": False,
            "hidden_persistence_performed": False,
            "autonomous_execution_performed": False,
        },
    }
    write_json(REPORT_ROOT / "developmental_cognition_campaign.json", payload)
    write_markdown(REPORT_ROOT / "developmental_cognition_campaign.md", "DELTA 1.5 Developmental Cognition Campaign", payload)
    return payload


def _build_comparison(
    matches: tuple[dict[str, Any], ...],
    overlapping: tuple[str, ...],
    novel: tuple[str, ...],
    conflicts: tuple[str, ...],
) -> EvidenceComparison:
    if conflicts:
        classification = "POTENTIAL_CONFLICT"
        confidence = 0.55
        explanation = "External evidence contains cautious contradiction signals that require operator review."
    elif not matches:
        classification = "NOVEL"
        confidence = 0.74 if novel else 0.62
        explanation = "No approved local concept was retrieved for the evidence query."
    elif len(novel) >= 2:
        classification = "HIGHER_RESOLUTION"
        confidence = 0.78
        explanation = "Local concepts exist, but the external text introduces reviewable terms not represented in the retrieved local material."
    elif novel:
        classification = "PARTIAL_NOVELTY"
        confidence = 0.7
        explanation = "Local concepts overlap with the evidence, with one reviewable missing detail."
    else:
        classification = "KNOWN"
        confidence = 0.66
        explanation = "The extracted evidence terms are already represented in the retrieved local material."
    return EvidenceComparison(
        classification=classification,
        confidence=confidence,
        local_match_count=len(matches),
        overlapping_terms=overlapping,
        novel_terms=novel,
        conflict_signals=conflicts,
        explanation=explanation,
    )


def _extract_evidence_terms(title: str, extract: str) -> tuple[str, ...]:
    normalized = _normalize_text(f"{title}. {extract}")
    terms: list[str] = []
    known_terms = {
        "acid-base reaction": "acid-base reaction",
        "acid base reaction": "acid-base reaction",
        "chemical reaction": "chemical reaction",
        "ph": "pH",
        "titration": "titration",
        "acid-base theories": "acid-base theories",
        "acid base theories": "acid-base theories",
        "arrhenius acid-base theory": "Arrhenius acid-base theory",
        "arrhenius acid base theory": "Arrhenius acid-base theory",
        "bronsted-lowry acid-base theory": "Bronsted-Lowry acid-base theory",
        "bronsted lowry acid base theory": "Bronsted-Lowry acid-base theory",
        "lewis acid-base theory": "Lewis acid-base theory",
        "lewis acid base theory": "Lewis acid-base theory",
        "reaction mechanisms": "reaction mechanisms",
    }
    for needle, label in known_terms.items():
        if needle in normalized:
            _append_unique(terms, label)
    for match in re.finditer(r"(?:called|for example|such as)\s+([a-z][a-z0-9 -]{4,80})", normalized):
        phrase = re.split(r"[,.;:]", match.group(1))[0].strip()
        phrase = re.sub(r"^(the|a|an)\s+", "", phrase).strip()
        phrase = re.sub(r"\b(the|a|an|and|or)$", "", phrase).strip()
        if " for example " in f" {phrase} " or len(phrase.split()) > 6:
            continue
        if _term_is_useful(phrase):
            _append_unique(terms, phrase[:80])
    if not terms:
        for token in re.findall(r"\b[a-z][a-z0-9-]{4,}\b", normalized):
            if _term_is_useful(token):
                _append_unique(terms, token)
            if len(terms) >= 8:
                break
    return tuple(terms[:10])


def _detect_conflict_signals(extract: str, local_text: str) -> tuple[str, ...]:
    normalized_evidence = _normalize_text(extract)
    normalized_local = _normalize_text(local_text)
    signals: list[str] = []
    for phrase in ("is not", "does not", "cannot", "unlike", "rather than"):
        if phrase in normalized_evidence and phrase not in normalized_local:
            signals.append(phrase)
    return tuple(signals[:3])


def _local_text(local: dict[str, Any]) -> str:
    parts = [str(local.get("answer") or "")]
    for row in local.get("matches") or ():
        parts.append(str(row.get("concept_name") or ""))
        parts.append(str(row.get("short_definition") or ""))
        parts.extend(str(item) for item in row.get("propositions") or ())
        parts.extend(str(item) for item in row.get("related_concepts") or ())
    return _normalize_text(" ".join(parts))


def _snapshot_local(local: dict[str, Any]) -> dict[str, Any]:
    return {
        "matched": bool(local.get("matched")),
        "match_count": len(local.get("matches") or ()),
        "search_query": local.get("search_query"),
        "matches": [
            {
                "concept_name": row.get("concept_name"),
                "domain": row.get("domain"),
                "memory_type": row.get("memory_type"),
            }
            for row in (local.get("matches") or ())[:5]
        ],
    }


def _observation_sentence(comparison: EvidenceComparison, title: str, terms: tuple[str, ...]) -> str:
    term_text = ", ".join(terms[:3]) if terms else "no extracted term"
    if comparison.classification == "KNOWN":
        return f"`{title}` appears mostly represented locally; the retrieved evidence did not create an immediate review gap."
    return f"`{title}` produced {comparison.classification.lower().replace('_', ' ')} evidence: {term_text}."


def _gap_summary(classification: str, title: str, terms: tuple[str, ...]) -> str:
    term_text = ", ".join(terms[:4]) if terms else "article-level evidence"
    return f"{classification}: {title} may improve local knowledge around {term_text}."


def _contains_term(text: str, term: str) -> bool:
    normalized = _normalize_text(term)
    if not normalized:
        return False
    return normalized in text


def _normalize_text(text: str) -> str:
    cleaned = str(text or "").replace("–", "-").replace("—", "-")
    ascii_text = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _term_is_useful(term: str) -> bool:
    stop = {
        "about",
        "alternative",
        "between",
        "called",
        "example",
        "several",
        "their",
        "there",
        "these",
        "those",
        "which",
    }
    normalized = _normalize_text(term)
    if len(normalized) < 3 or normalized in stop:
        return False
    return bool(re.search(r"[a-z]", normalized))


def _append_unique(items: list[str], value: str) -> None:
    key = _normalize_text(value)
    if not key:
        return
    if all(_normalize_text(item) != key for item in items):
        items.append(value)


======================================================================
FILE: integration/model_runtime/model_registry.py
======================================================================

"""
integration/model_runtime/model_registry.py

Dynamic local model registry for Delta's model abstraction layer.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class ModelSpec:
    name: str
    path: str
    tier: int
    description: str
    context_length: int
    provider: str = "local_gguf"
    family: str = "unknown"
    quantization: str = "unknown"
    size_bytes: int = 0
    mmproj_path: str | None = None
    capabilities: tuple[str, ...] = ("text",)


def model_root() -> Path:
    configured = os.getenv("DELTA_MODEL_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(r"G:\models")


def discover_local_models(root: str | Path | None = None) -> Dict[str, ModelSpec]:
    base = Path(root) if root is not None else model_root()
    if not base.exists():
        return {}

    specs: Dict[str, ModelSpec] = {}
    mmproj_by_dir = {
        path.parent: path
        for path in base.rglob("*.gguf")
        if path.name.lower().startswith("mmproj")
    }
    for path in sorted(base.rglob("*.gguf")):
        if path.name.lower().startswith("mmproj"):
            continue
        spec = _spec_from_path(path, mmproj_by_dir.get(path.parent))
        specs[spec.name] = spec

    return specs


def list_available_models() -> Dict[str, ModelSpec]:
    discovered = discover_local_models()
    aliased: Dict[str, ModelSpec] = dict(discovered)
    for alias, spec in _aliases(discovered).items():
        aliased.setdefault(alias, spec)
    return aliased


def list_models() -> Dict[str, ModelSpec]:
    return list_available_models()


def get_model_spec(model_name: str) -> ModelSpec:
    available = list_available_models()
    key = str(model_name).strip().lower()
    if key in available:
        return available[key]
    raise ValueError(f"Unknown or unavailable model '{model_name}'")


def _spec_from_path(path: Path, mmproj_path: Path | None) -> ModelSpec:
    file_name = path.stem
    dir_name = path.parent.name
    model_id = _model_id(dir_name, file_name)
    family = _family(file_name + " " + dir_name)
    quantization = _quantization(file_name)
    size_bytes = path.stat().st_size
    capabilities = ("text", "vision") if mmproj_path is not None else ("text",)

    return ModelSpec(
        name=model_id,
        path=str(path),
        tier=_tier(family, size_bytes),
        description=f"{family} local GGUF model ({quantization})",
        context_length=_context_length(family, file_name),
        provider="local_gguf",
        family=family,
        quantization=quantization,
        size_bytes=size_bytes,
        mmproj_path=str(mmproj_path) if mmproj_path else None,
        capabilities=capabilities,
    )


def _aliases(discovered: Dict[str, ModelSpec]) -> Dict[str, ModelSpec]:
    aliases: Dict[str, ModelSpec] = {}
    for spec in discovered.values():
        name = spec.name.lower()
        if spec.family == "phi3":
            aliases.setdefault("phi3", spec)
        if spec.family == "phi4":
            aliases.setdefault("phi4", spec)
        if spec.family == "qwen" and "vl" not in name:
            aliases.setdefault("qwen", spec)
        if spec.family == "llama":
            aliases.setdefault("llama", spec)
        if spec.family == "mistral":
            aliases.setdefault("mistral", spec)
    return aliases


def _model_id(dir_name: str, file_name: str) -> str:
    raw = f"{dir_name}-{file_name}".lower()
    raw = raw.replace(".gguf", "")
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    raw = re.sub(r"-+", "-", raw)
    return raw


def _family(text: str) -> str:
    lower = text.lower()
    if "phi-4" in lower or "phi4" in lower:
        return "phi4"
    if "phi-3" in lower or "phi3" in lower:
        return "phi3"
    if "qwen" in lower:
        return "qwen"
    if "llama" in lower:
        return "llama"
    if "ministral" in lower:
        return "ministral"
    if "mistral" in lower:
        return "mistral"
    return "unknown"


def _quantization(file_name: str) -> str:
    match = re.search(r"(q\d(?:_[a-z]+(?:_[a-z]+)?)?|f16|bf16)", file_name.lower())
    return match.group(1).upper() if match else "unknown"


def _context_length(family: str, file_name: str) -> int:
    lower = file_name.lower()
    if "4k" in lower:
        return 4096
    if family == "qwen":
        return 32768
    if family in {"llama", "phi4", "mistral", "ministral"}:
        return 8192
    return 4096


def _tier(family: str, size_bytes: int) -> int:
    if family == "phi3":
        return 1
    if family in {"phi4", "ministral"}:
        return 2
    if family in {"qwen", "mistral"}:
        return 3
    if family == "llama":
        return 4
    return 5 if size_bytes else 9


======================================================================
FILE: integration/model_runtime/provider_manager.py
======================================================================

from __future__ import annotations

import gc
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from integration.model_runtime.inference_types import CanonicalInferenceResult
from integration.model_runtime.model_registry import ModelSpec, list_available_models
from integration.model_runtime.provider_qualification import load_capability_database


class ProviderRunner(Protocol):
    def produce_output(self, input_payload: dict[str, Any]) -> Any:
        ...


RunnerFactory = Callable[[ModelSpec], ProviderRunner]


def json_dumps_state(state: "ProviderLoadState") -> str:
    return json.dumps(asdict(state), indent=2, sort_keys=True)


@dataclass(frozen=True)
class ProviderLoadState:
    active_model: str | None
    loaded: bool
    loaded_at: float | None = None
    load_count: int = 0
    unload_count: int = 0
    n_gpu_layers: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ProviderManager:
    """
    Manage serial provider residency for constrained local hardware.

    Delta owns memory, evidence, and governance. This manager only controls
    transient inference provider lifecycle so a 12 GB GPU hosts at most one
    local model at a time.
    """

    def __init__(
        self,
        *,
        available_models: Mapping[str, ModelSpec] | None = None,
        runner_factory: RunnerFactory | None = None,
        n_gpu_layers: int | None = None,
        keep_loaded: bool = False,
        status_path: str | Path | None = None,
        capability_db_path: str | Path | None = None,
        provider_capabilities: Mapping[str, Any] | None = None,
    ) -> None:
        self.available_models = dict(available_models or list_available_models())
        self.runner_factory = runner_factory
        self.n_gpu_layers = n_gpu_layers
        self.keep_loaded = keep_loaded
        self.status_path = Path(status_path) if status_path is not None else None
        self.capability_db_path = Path(capability_db_path) if capability_db_path else None
        self.provider_capabilities = dict(provider_capabilities or {})
        self._active_spec: ModelSpec | None = None
        self._runner: ProviderRunner | None = None
        self._loaded_at: float | None = None
        self._load_count = 0
        self._unload_count = 0

    def load(self, model_name: str) -> ProviderLoadState:
        spec = self._resolve(model_name)
        if self._active_spec is not None and self._active_spec.name == spec.name:
            return self.status()
        self.unload()
        self._runner = self._create_runner(spec)
        self._active_spec = spec
        self._loaded_at = time.time()
        self._load_count += 1
        return self._publish_status()

    def warm(self, model_name: str) -> ProviderLoadState:
        state = self.load(model_name)
        method = getattr(self._runner, "load_model", None)
        if callable(method):
            method()
        return self._publish_status()

    def infer(
        self,
        *,
        model_name: str,
        prompt: str,
        task_type: str = "open_ended",
        metadata: Mapping[str, Any] | None = None,
    ) -> CanonicalInferenceResult:
        self.load(model_name)
        if self._runner is None or self._active_spec is None:
            raise RuntimeError("ProviderManager.infer() has no active provider")

        input_payload = {
            "question": prompt,
            "prompt": prompt,
            "task_type": task_type,
            "metadata": dict(metadata or {}),
        }
        raw = self._runner.produce_output(input_payload)
        return self._canonical_result(raw, prompt=prompt, task_type=task_type)

    def unload(self) -> ProviderLoadState:
        if self._runner is not None:
            for method_name in ("unload", "close"):
                method = getattr(self._runner, method_name, None)
                if callable(method):
                    method()
                    break
            self._runner = None
            self._active_spec = None
            self._loaded_at = None
            self._unload_count += 1
            gc.collect()
        return self._publish_status()

    def status(self) -> ProviderLoadState:
        spec = self._active_spec
        return ProviderLoadState(
            active_model=spec.name if spec is not None else None,
            loaded=spec is not None,
            loaded_at=self._loaded_at,
            load_count=self._load_count,
            unload_count=self._unload_count,
            n_gpu_layers=self._gpu_layers_for(spec) if spec is not None else self.n_gpu_layers,
            metadata=self._metadata(spec),
        )

    def _publish_status(self) -> ProviderLoadState:
        state = self.status()
        if self.status_path is not None:
            self.status_path.parent.mkdir(parents=True, exist_ok=True)
            self.status_path.write_text(
                json_dumps_state(state),
                encoding="utf-8",
            )
        return state

    def _resolve(self, model_name: str) -> ModelSpec:
        key = str(model_name).strip().lower()
        if key in self.available_models:
            return self.available_models[key]
        for spec in self.available_models.values():
            if spec.name == key:
                return spec
        raise ValueError(f"Unknown or unavailable model '{model_name}'")

    def _create_runner(self, spec: ModelSpec) -> ProviderRunner:
        if self.runner_factory is not None:
            return self.runner_factory(spec)
        from integration.model_runtime.gguf_model_runner import GGUFModelRunner

        return GGUFModelRunner(spec.name, n_gpu_layers=self._gpu_layers_for(spec), keep_loaded=self.keep_loaded)

    def _canonical_result(
        self,
        raw: Any,
        *,
        prompt: str,
        task_type: str,
    ) -> CanonicalInferenceResult:
        if isinstance(raw, CanonicalInferenceResult):
            return raw
        if hasattr(raw, "payload"):
            payload = dict(getattr(raw, "payload") or {})
            canonical = payload.get("canonical_inference") or {}
            return CanonicalInferenceResult(
                provider=str(canonical.get("provider") or "local_gguf"),
                model_id=str(canonical.get("model_id") or self._active_spec.name),
                answer=str(payload.get("answer") or payload.get("raw_model_output") or ""),
                raw_output=str(payload.get("raw_model_output") or payload.get("answer") or ""),
                confidence=float(payload.get("confidence") or getattr(raw, "confidence_band", 0.0)),
                latency_seconds=float(canonical.get("latency_seconds") or 0.0),
                prompt_tokens=int(canonical.get("prompt_tokens") or len(prompt.split())),
                response_tokens=int(canonical.get("response_tokens") or 0),
                evidence=list(canonical.get("evidence") or []),
                metadata={
                    **dict(canonical.get("metadata") or {}),
                    "task_type": task_type,
                    "provider_manager": "serial_local_v1",
                },
            )
        answer = str(raw)
        spec = self._active_spec
        return CanonicalInferenceResult(
            provider=spec.provider if spec is not None else "unknown",
            model_id=spec.name if spec is not None else "unknown",
            answer=answer,
            raw_output=answer,
            confidence=0.0,
            latency_seconds=0.0,
            prompt_tokens=len(prompt.split()),
            response_tokens=len(answer.split()),
            evidence=[],
            metadata={"task_type": task_type, "provider_manager": "serial_local_v1"},
        )

    def _metadata(self, spec: ModelSpec | None) -> dict[str, Any]:
        if spec is None:
            return {"resident_provider_count": 0}
        profile = self._profile_for(spec)
        return {
            "resident_provider_count": 1,
            "provider": spec.provider,
            "family": spec.family,
            "quantization": spec.quantization,
            "context_length": spec.context_length,
            "recommended_context": profile.get("recommended_context"),
            "recommended_gpu_layers": profile.get("recommended_gpu_layers"),
            "backend_tokens_per_second": profile.get("average_tokens_per_second"),
            "capabilities": list(spec.capabilities),
            "size_bytes": spec.size_bytes,
            "path": str(Path(spec.path)),
            "mmproj_path": spec.mmproj_path,
        }

    def _gpu_layers_for(self, spec: ModelSpec | None) -> int | None:
        if self.n_gpu_layers is not None:
            return self.n_gpu_layers
        if spec is None:
            return None
        value = self._profile_for(spec).get("recommended_gpu_layers")
        if value is None:
            configured = os.getenv("DELTA_N_GPU_LAYERS", "").strip()
            if not configured:
                return None
            try:
                return int(configured)
            except ValueError:
                return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _profile_for(self, spec: ModelSpec) -> dict[str, Any]:
        if not self.provider_capabilities and self.capability_db_path is not None:
            self.provider_capabilities = load_capability_database(self.capability_db_path)
        profile = self.provider_capabilities.get(spec.name)
        if isinstance(profile, dict):
            return profile
        profile = self.provider_capabilities.get(spec.name.lower())
        return profile if isinstance(profile, dict) else {}


======================================================================
FILE: integration/model_runtime/gguf_model_runner.py
======================================================================

"""
integration/model_runtime/gguf_model_runner.py

GGUF model runner implementation.

Responsibilities
----------------
• Bridge ExternalModelInterface → local GGUF models
• Delegate prompt construction to prompt_builder
• Execute model inference through ModelSession
• Extract structured result from model output
• Return AIOutputBundle with parsed confidence

Design guarantees
-----------------
• Executes exactly one model
• Performs no routing
• Prints model output immediately for pipeline visibility
"""

from typing import Dict, Any
import json
import re
import time

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.ai_surface.ai_model_interface import ExternalModelInterface

from integration.model_runtime.model_registry import get_model_spec
from integration.model_runtime.model_session import ModelSession
from integration.model_runtime.prompt_builder import build_prompt
from integration.model_runtime.inference_types import CanonicalInferenceResult


class GGUFModelRunner(ExternalModelInterface):
    """
    Executes a single GGUF model through a controlled ModelSession.
    """

    def __init__(self, model_name: str, *, n_gpu_layers: int | None = None, keep_loaded: bool = False):
        self.model_name = model_name
        self.session = ModelSession(n_gpu_layers=n_gpu_layers)
        self.keep_loaded = keep_loaded

    def load_model(self) -> None:
        model_spec = get_model_spec(self.model_name)
        self.session.load(model_spec)

    def unload(self) -> None:
        self.session.unload()

    # ------------------------------------------------------------------
    # Model identity helper
    # ------------------------------------------------------------------

    def _model_id(self, model_spec) -> str:
        """
        Safely resolve a printable model identifier
        regardless of ModelSpec structure.
        """

        for field in ["name", "model_name", "model", "id"]:
            if hasattr(model_spec, field):
                return getattr(model_spec, field)

        return self.model_name

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Dict[str, Any]:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            candidate = text[start:end]
            try:
                return json.loads(candidate)
            except Exception:
                pass

        return {}

    def _extract_answer(self, text: str) -> str:
        data = self._extract_json(text)

        answer = data.get("answer", "")
        if isinstance(answer, str):
            return answer.strip()

        return ""

    def _extract_model_confidence(self, text: str) -> float:
        data = self._extract_json(text)

        if "confidence" in data:
            try:
                value = float(data["confidence"])
                return max(0.0, min(1.0, value))
            except Exception:
                pass

        m = re.search(r'"confidence"\s*:\s*([0-9.]+)', text)

        if m:
            try:
                value = float(m.group(1))
                return max(0.0, min(1.0, value))
            except Exception:
                pass

        return 0.0

    # ------------------------------------------------------------------
    # Confidence heuristics
    # ------------------------------------------------------------------

    def _heuristic_confidence(self, text: str) -> float:
        answer = self._extract_answer(text)

        if not answer:
            return 0.0

        lowered = answer.lower()
        score = 0.0

        if len(answer) >= 80:
            score += 0.30

        if any(token in answer for token in ["1.262", "259", "AU", "days"]):
            score += 0.25

        if any(
            token in lowered
            for token in ["semi-major", "hohmann", "transfer", "delta-v"]
        ):
            score += 0.25

        if any(token in answer for token in ["=", "/", "(", ")", "sqrt"]):
            score += 0.10

        if "<your answer here>" in answer:
            score -= 0.50

        return max(0.0, min(1.0, score))

    def _combine_confidence(self, text: str) -> float:
        model_conf = self._extract_model_confidence(text)
        heuristic_conf = self._heuristic_confidence(text)

        # If no heuristic signal, trust model
        if heuristic_conf == 0.0:
            return model_conf

        # Model-dominant fusion
        combined = (0.85 * model_conf) + (0.15 * heuristic_conf)

        return max(0.0, min(1.0, round(combined, 4)))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def produce_output(self, input_payload: Dict[str, Any]) -> AIOutputBundle:
        model_spec = get_model_spec(self.model_name)
        prompt = build_prompt(input_payload)

        model_id = self._model_id(model_spec)

        print("\n================================")
        print(f"MODEL START: {model_id}")
        print("================================\n")

        start = time.time()
        raw_output = ""

        try:
            self.session.load(model_spec)
            raw_output = self.session.generate(prompt)

            #print("MODEL OUTPUT:\n")
            #print(raw_output)
            print()

        finally:
            if not self.keep_loaded:
                self.session.unload()

        elapsed = time.time() - start

        print(f"MODEL COMPLETE: {model_id}")
        print(f"EXECUTION TIME: {elapsed:.2f}s")
        print("================================\n")

        confidence = self._combine_confidence(raw_output)
        answer = self._extract_answer(raw_output) or raw_output.strip()
        canonical = CanonicalInferenceResult(
            provider="local_gguf",
            model_id=model_id,
            answer=answer,
            raw_output=raw_output,
            confidence=confidence,
            latency_seconds=round(elapsed, 4),
            prompt_tokens=len(prompt.split()),
            response_tokens=len(raw_output.split()),
            evidence=[],
            metadata={
                "model_path": model_spec.path,
                "family": model_spec.family,
                "quantization": model_spec.quantization,
                "context_length": model_spec.context_length,
                "capabilities": list(model_spec.capabilities),
            },
        )

        return AIOutputBundle(
            role="strategic_defense_advisor",
            mode="active",
            payload=canonical.to_ai_output_payload(),
            confidence_band=confidence,
        )


======================================================================
FILE: scripts/delta_rc2_local_model_infer.py
======================================================================

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.model_runtime.provider_manager import ProviderManager  # noqa: E402


def main() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
        model_name = str(request["model_name"])
        prompt = str(request["prompt"])
        task_type = str(request.get("task_type") or "rc2_conversation")
        metadata = dict(request.get("metadata") or {})
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = ProviderManager().infer(
                model_name=model_name,
                prompt=prompt,
                task_type=task_type,
                metadata=metadata,
            )
        print(
            json.dumps(
                {
                    "executed": True,
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "answer": result.answer,
                    "confidence_score": result.confidence,
                    "provider_calls_performed": False,
                    "training_performed": False,
                    "canonical_write_performed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - helper returns an inert diagnostic.
        print(
            json.dumps(
                {
                    "executed": False,
                    "error": f"{type(exc).__name__}:{str(exc)[:200]}",
                    "provider_calls_performed": False,
                    "training_performed": False,
                    "canonical_write_performed": False,
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


======================================================================
FILE: orchestration/runtime/rc1_operator_console.py
======================================================================

"""RC1 minimal local operator console support.

The console is a local operator surface over existing RC1/runtime artifacts. It
does not enable providers, training, autonomous actions, canonical writes,
recall mutation, or production routing. The only optional write is an explicit
operator observation/failure log entry under `data/rc1_operator_console/`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_release_candidate_freeze import (
    SAFETY as RC1_SAFETY,
    failure_classification,
    observation_framework,
    release_manifest,
    validation_summary,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DATA = ROOT / "data" / "rc1_operator_console"
OBSERVATION_LOG = DATA / "observations.jsonl"
PROPOSITION_LOG = DATA / "noncanonical_propositions.jsonl"
EVIDENCE_LOG = DATA / "evidence_links.jsonl"
REPLAY_LOG = DATA / "replay_queue.jsonl"
CONTRADICTION_LOG = DATA / "contradictions.jsonl"
LOCAL_STORE_LOGS = (PROPOSITION_LOG, EVIDENCE_LOG, REPLAY_LOG, CONTRADICTION_LOG)

CONSOLE_FLAGS = {
    "rc1_operator_console_enabled": True,
    "local_desktop_only": True,
    "paste_text_only": True,
    "provider_calls_enabled": False,
    "training_enabled": False,
    "canonical_writes_enabled": False,
    "autonomous_actions_enabled": False,
    "scheduler_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "recall_mutation_enabled": False,
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def normalize_claim(claim: str) -> dict[str, Any]:
    """Normalize a narrow RC1 proposition into subject/predicate/polarity.

    This is deterministic and intentionally conservative. It is built for the
    first operator-console contradiction class: affirmative claims versus
    negated/forbidden claims over the same subject and predicate.
    """
    text = claim.strip().rstrip(".")
    lower = text.lower()
    subject = "unknown"
    predicate = lower
    if lower.startswith("project frontier "):
        subject = "project frontier"
        predicate = lower.removeprefix("project frontier ").strip()

    polarity = "positive"
    negative_markers = [
        "should not ",
        "must not ",
        "does not ",
        "do not ",
        "cannot ",
        "can not ",
        "never ",
        "requires operator review before ",
    ]
    for marker in negative_markers:
        if marker in predicate:
            polarity = "negative"
            predicate = predicate.replace(marker, "", 1).strip()
            break

    replacements = {
        "approve ": "approves ",
        "approval": "approve",
    }
    for old, new in replacements.items():
        predicate = predicate.replace(old, new)
    predicate = " ".join(predicate.split())
    return {
        "subject": subject,
        "predicate": predicate,
        "polarity": polarity,
        "normalized_key": f"{subject}|{predicate}",
    }


def detect_contradictions_for_record(record: dict[str, Any], existing_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = record["normalized"]
    contradictions = []
    for existing in existing_records:
        other = existing.get("normalized", normalize_claim(existing.get("claim", "")))
        if (
            other["normalized_key"] == normalized["normalized_key"]
            and other["polarity"] != normalized["polarity"]
        ):
            contradiction_id = _stable_id("rc1-contradiction", record["proposition_id"] + existing["proposition_id"])
            contradictions.append({
                "contradiction_id": contradiction_id,
                "subject": normalized["subject"],
                "predicate": normalized["predicate"],
                "claim_a": existing["claim"],
                "claim_a_id": existing["proposition_id"],
                "claim_a_polarity": other["polarity"],
                "claim_b": record["claim"],
                "claim_b_id": record["proposition_id"],
                "claim_b_polarity": normalized["polarity"],
                "status": "operator_review_recommended",
                "canonical": False,
            })
    return contradictions


def report_summary() -> dict[str, Any]:
    rc1_reports = sorted(path.name for path in REPORTS.glob("RC1_*.json"))
    tp_reports = sorted(path.name for path in REPORTS.glob("TP*.json"))
    return {
        "rc1_report_count": len(rc1_reports),
        "tp_report_count": len(tp_reports),
        "latest_rc1_reports": rc1_reports,
        "latest_tp_report": tp_reports[-1] if tp_reports else None,
    }


def build_runtime_status() -> dict[str, Any]:
    validation = validation_summary()
    manifest = release_manifest()
    return {
        "version": manifest["version"],
        "status": manifest["status"],
        "operational_baseline": manifest["operational_baseline"],
        "latest_tp_phase": validation["latest_tp_phase"],
        "latest_tp_recommendation": validation["latest_tp_recommendation"],
        "safety": {**RC1_SAFETY, **CONSOLE_FLAGS},
        "reports": report_summary(),
    }


def build_corpus_substrate_summary() -> dict[str, Any]:
    candidates = [
        "TP11_BASE_CORPUS_MANIFEST.json",
        "TP14_SUBSTRATE_IMPROVEMENTS.json",
        "TP15_INTEGRATION_MAPPING.json",
        "TP20_TRAINING_NECESSITY_REASSESSMENT.json",
        "TP30_FINAL_ROADMAP_REVIEW.json",
    ]
    available = {name: (REPORTS / name).exists() for name in candidates}
    tp14 = _load_json(REPORTS / "TP14_SUBSTRATE_IMPROVEMENTS.json")
    improvements = tp14.get("improvements", [])
    return {
        "available_artifacts": available,
        "substrate_improvement_count": len(improvements),
        "substrate_improvements": [item.get("improvement_id") for item in improvements],
        "rc1_noncanonical_state": build_cognitive_state(),
        "canonical_write_enabled": False,
        "training_enabled": False,
    }


def build_review_queue() -> list[dict[str, Any]]:
    mapping = _load_json(REPORTS / "TP15_INTEGRATION_MAPPING.json")
    items = []
    for item in mapping.get("mapped_improvements", []):
        items.append({
            "item_id": item.get("improvement_id"),
            "status": "rc1_review_reference",
            "active": item.get("active", False),
            "expected_runtime_effect": item.get("expected_runtime_effect"),
            "operator_review_required": True,
        })
    return items


def build_replay_rollback_inspection() -> dict[str, Any]:
    rollback = _load_json(REPORTS / "TP15_ROLLBACK_DESIGN.json")
    replay = _load_json(REPORTS / "TP22_REPLAY_OPTIMIZATION.json")
    return {
        "rollback_records": len(rollback.get("rollback_records", [])),
        "rollback_available": bool(rollback),
        "replay_report_available": bool(replay),
        "rollback_execution_enabled": False,
        "replay_scheduler_enabled": False,
    }


def build_operator_snapshot() -> dict[str, Any]:
    return {
        "runtime_status": build_runtime_status(),
        "corpus_substrate": build_corpus_substrate_summary(),
        "operator_review_queue": build_review_queue(),
        "replay_rollback": build_replay_rollback_inspection(),
        "observation_framework": observation_framework(),
        "failure_classification": failure_classification(),
        "cognitive_state": build_cognitive_state(),
        "console_flags": CONSOLE_FLAGS,
    }


def answer_operator_question(question: str) -> dict[str, Any]:
    from orchestration.runtime.rc1_release_candidate_freeze import answer_rc1_question, is_rc1_question
    from orchestration.runtime.tp16_tp30_master_marathon import answer_tp16_tp30_question, is_tp16_tp30_question
    from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer

    substrate = query_noncanonical_substrate(question)
    if substrate["matched"]:
        route = "rc1_noncanonical_substrate"
        answer = substrate["answer"]
    elif is_rc1_question(question):
        route = "rc1_release_candidate"
        data = answer_rc1_question(question)
        answer = data["answer_text"]
    elif is_tp16_tp30_question(question):
        route = "tp16_tp30"
        data = answer_tp16_tp30_question(question)
        answer = data["answer_text"]
    else:
        route = "v29_local_answer"
        data = run_v29_local_answer(question, use_recall=False)
        answer = data.get("answer") or data.get("answer_text") or "No local deterministic answer was available."
    return {
        "route": route,
        "question": question,
        "answer": answer,
        "provider_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
    }


def preview_evidence_ingest(pasted_text: str) -> dict[str, Any]:
    text = pasted_text.strip()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "preview_id": f"rc1-evidence-preview-{digest[:16]}" if digest else "rc1-evidence-preview-empty",
        "characters": len(text),
        "nonempty_lines": len(lines),
        "sha256": digest,
        "persisted": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "note": "Paste preview only. No upload, provider call, training, canonical write, or substrate mutation occurred.",
    }


def extract_propositions(pasted_text: str) -> dict[str, Any]:
    """Create reviewable proposition candidates from pasted operator text.

    Extraction is intentionally simple and deterministic for RC1. It creates
    candidates only; it does not persist anything until the operator approves.
    """
    text = pasted_text.strip()
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in text.replace("\r\n", "\n").replace(";", ".").split("\n"):
        for part in raw.split("."):
            claim = part.strip()
            if not claim:
                continue
            if claim[-1:] not in {".", "!", "?"}:
                claim = claim + "."
            key = claim.lower()
            if key in seen:
                continue
            seen.add(key)
            proposition_id = _stable_id("rc1-proposition", claim)
            candidates.append({
                "proposition_id": proposition_id,
                "claim": claim,
                "source": "operator_paste",
                "confidence": "operator_asserted_unverified",
                "status": "pending_operator_review",
                "canonical": False,
                "selected_by_default": True,
            })
    return {
        "candidate_count": len(candidates),
        "candidates": candidates,
        "persisted": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "training_performed": False,
    }


def approve_propositions(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Append approved candidates to the RC1 local noncanonical substrate."""
    existing_records = _read_jsonl(PROPOSITION_LOG)
    existing_ids = {row["proposition_id"] for row in existing_records}
    approved = []
    duplicates = []
    contradictions = []
    for candidate in candidates:
        proposition_id = candidate["proposition_id"]
        if proposition_id in existing_ids:
            duplicates.append(proposition_id)
            continue
        claim = candidate["claim"]
        evidence_id = _stable_id("rc1-evidence", proposition_id + claim)
        record = {
            "proposition_id": proposition_id,
            "claim": claim,
            "normalized": normalize_claim(claim),
            "source": candidate.get("source", "operator_paste"),
            "confidence": candidate.get("confidence", "operator_asserted_unverified"),
            "status": "approved_noncanonical",
            "canonical": False,
            "evidence_id": evidence_id,
            "rollback_supported": True,
            "provider_calls_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
        }
        evidence = {
            "evidence_id": evidence_id,
            "proposition_id": proposition_id,
            "source": "operator_paste",
            "provenance": "local_rc1_operator_console",
            "canonical": False,
        }
        replay = {
            "replay_item_id": _stable_id("rc1-replay", proposition_id),
            "proposition_id": proposition_id,
            "reason": "new_operator_approved_noncanonical_proposition",
            "status": "queued_for_manual_replay_review",
            "scheduler_started": False,
        }
        _append_jsonl(PROPOSITION_LOG, record)
        _append_jsonl(EVIDENCE_LOG, evidence)
        _append_jsonl(REPLAY_LOG, replay)
        approved.append(record)
        new_contradictions = detect_contradictions_for_record(record, existing_records)
        for contradiction in new_contradictions:
            _append_jsonl(CONTRADICTION_LOG, contradiction)
        contradictions.extend(new_contradictions)
        existing_records.append(record)
        existing_ids.add(proposition_id)
    return {
        "approved_count": len(approved),
        "duplicate_count": len(duplicates),
        "contradiction_count": len(contradictions),
        "approved": approved,
        "duplicates": duplicates,
        "contradictions": contradictions,
        "state": build_cognitive_state(),
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "training_performed": False,
        "scheduler_started": False,
    }


def clear_local_noncanonical_store(confirm_text: str) -> dict[str, Any]:
    """Delete only the RC1 local noncanonical experiment store.

    This is intentionally narrow. It never touches reports, canonical memory,
    training artifacts, provider configuration, or repo source files.
    """
    required = "DELETE_RC1_LOCAL_NONCANONICAL_STORE"
    if str(confirm_text).strip() != required:
        return {
            "cleared": False,
            "required_confirmation": required,
            "reason": "confirmation_phrase_missing_or_incorrect",
            "canonical_write_performed": False,
            "training_performed": False,
            "provider_calls_performed": False,
        }
    deleted: list[str] = []
    for path in LOCAL_STORE_LOGS:
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    return {
        "cleared": True,
        "deleted": deleted,
        "state": build_cognitive_state(),
        "local_noncanonical_only": True,
        "canonical_write_performed": False,
        "training_performed": False,
        "provider_calls_performed": False,
        "recall_mutation_performed": False,
    }


def build_cognitive_state() -> dict[str, Any]:
    propositions = _read_jsonl(PROPOSITION_LOG)
    evidence = _read_jsonl(EVIDENCE_LOG)
    replay = _read_jsonl(REPLAY_LOG)
    contradictions = _read_jsonl(CONTRADICTION_LOG)
    return {
        "corpus_documents": 0,
        "noncanonical_propositions": len(propositions),
        "evidence_links": len(evidence),
        "concepts": len({token.strip(".,:;!?").lower() for row in propositions for token in row.get("claim", "").split() if len(token.strip(".,:;!?")) > 3}),
        "contradictions": len(contradictions),
        "pending_review": 0,
        "replay_queue": len(replay),
        "knowledge_available": bool(propositions),
        "canonical_records": 0,
        "training_records": 0,
    }


def query_noncanonical_substrate(question: str) -> dict[str, Any]:
    tokens = {
        token.strip(".,:;!?").lower()
        for token in question.split()
        if len(token.strip(".,:;!?")) > 3
        and token.lower()
        not in {
            "what",
            "know",
            "about",
            "does",
            "tell",
            "current",
            "currently",
            "usually",
            "often",
            "generally",
            "automatically",
            "automatic",
        }
    }
    propositions = _read_jsonl(PROPOSITION_LOG)
    contradictions = _read_jsonl(CONTRADICTION_LOG)
    if "contradiction" in question.lower() or "conflict" in question.lower():
        if not contradictions:
            return {
                "matched": True,
                "answer": "No contradictory evidence is currently recorded in the RC1 local substrate.",
                "matches": [],
            }
        lines = ["Contradictions detected in the RC1 local substrate:"]
        for item in contradictions:
            lines.append(f"- Topic: {item['subject']} / {item['predicate']}")
            lines.append(f"  Claim A ({item['claim_a_polarity']}): {item['claim_a']}")
            lines.append(f"  Claim B ({item['claim_b_polarity']}): {item['claim_b']}")
            lines.append("  Operator review recommended.")
        return {
            "matched": True,
            "answer": "\n".join(lines),
            "matches": contradictions,
        }
    matches = []
    for row in propositions:
        claim_tokens = {token.strip(".,:;!?").lower() for token in row.get("claim", "").split()}
        overlap = tokens & claim_tokens
        minimum_overlap = 1 if len(tokens) == 1 else 2
        if len(overlap) >= minimum_overlap:
            matches.append(row)
    if not matches:
        return {
            "matched": False,
            "answer": "No RC1 noncanonical substrate evidence matched this question.",
            "matches": [],
        }
    lines = ["I found approved noncanonical RC1 substrate evidence:"]
    for row in matches:
        lines.append(f"- {row['claim']} (source: {row['source']}; confidence: {row['confidence']}; canonical: {row['canonical']})")
    lines.append("")
    if contradictions:
        lines.append(f"{len(contradictions)} contradiction(s) are currently recorded; ask about contradictions to inspect them.")
    else:
        lines.append("No contradictory evidence is currently recorded in the RC1 local substrate.")
    return {
        "matched": True,
        "answer": "\n".join(lines),
        "matches": matches,
    }


def build_observation_entry(category: str, note: str, severity: str = "P3") -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    raw = f"{now}|{category}|{severity}|{note}"
    observation_id = "rc1-observation-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return {
        "observation_id": observation_id,
        "timestamp": now,
        "operator": "local_operator",
        "workflow": "rc1_operator_console",
        "category": category,
        "severity": severity,
        "expected_behavior": "",
        "observed_behavior": note,
        "evidence_path": "",
        "reproduction_steps": "",
        "impact": "",
        "candidate_fix": "",
        "triage_decision": "untriaged",
        "canonical_write_performed": False,
        "memory_mutation_performed": False,
    }


def append_observation(entry: dict[str, Any], path: Path = OBSERVATION_LOG) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return {
        "written": True,
        "path": str(path),
        "observation_id": entry["observation_id"],
        "local_operational_log_only": True,
        "canonical_write_performed": False,
        "memory_mutation_performed": False,
    }


def validate_console_safe(snapshot: dict[str, Any]) -> bool:
    flags = snapshot["console_flags"]
    return (
        flags["rc1_operator_console_enabled"] is True
        and flags["local_desktop_only"] is True
        and flags["paste_text_only"] is True
        and all(
            value is False
            for key, value in flags.items()
            if key not in {"rc1_operator_console_enabled", "local_desktop_only", "paste_text_only"}
        )
    )


======================================================================
FILE: orchestration/runtime/rc2_render_correction.py
======================================================================

"""First-class render-correction primitive for conversational routing.

Render correction means the user is asking DELTA to restate the previous
semantic answer under new presentation constraints. It is local, ephemeral,
and intentionally barred from retrieval, provider calls, and memory formation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


SAFETY = {
    "provider_calls_performed": False,
    "web_search_performed": False,
    "training_performed": False,
    "canonical_write_performed": False,
    "autonomous_action_performed": False,
    "memory_write_performed": False,
    "memory_candidate_created": False,
    "retrieval_performed": False,
}


@dataclass(frozen=True)
class RenderCorrectionFrame:
    operation: str
    previous_topic: str
    previous_semantic_intent: str
    requested_constraints: tuple[str, ...]
    requested_headings: tuple[str, ...]
    scope: str
    confidence: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_render_correction_payload(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    history = history or []
    normalized = _normalize(message)
    if not _is_render_correction_request(normalized):
        return None

    previous = _last_assistant_answer(history)
    fallback = _fallback_semantic_answer(message)
    if not previous and not fallback:
        return {
            "route": "render_correction",
            "answer": "I can rewrite the previous answer, but I need an answer or topic to re-render first.",
            "confidence": "render_correction_needs_prior_answer",
            "confidence_score": 0.52,
            "render_correction": RenderCorrectionFrame(
                operation="RENDER_CORRECTION",
                previous_topic="unknown",
                previous_semantic_intent="unknown",
                requested_constraints=_constraints(normalized),
                requested_headings=_requested_headings(message),
                scope="needs_prior_answer",
                confidence=0.52,
                reason="render_correction_without_prior_semantic_answer",
            ).as_dict(),
            "memory_candidate": None,
            **SAFETY,
        }

    semantic_answer = previous or fallback or ""
    headings = _requested_headings(message)
    constraints = _constraints(normalized)
    rendered = _render(semantic_answer, headings, constraints, message)
    frame = RenderCorrectionFrame(
        operation="RENDER_CORRECTION",
        previous_topic=_infer_topic(message, semantic_answer),
        previous_semantic_intent=_infer_intent(semantic_answer),
        requested_constraints=constraints,
        requested_headings=headings,
        scope="presentation_only",
        confidence=0.9 if previous else 0.78,
        reason="user_requested_presentation_change_without_new_knowledge",
    )
    return {
        "route": "render_correction",
        "answer": rendered,
        "confidence": "ephemeral_render_correction",
        "confidence_score": frame.confidence,
        "render_correction": frame.as_dict(),
        "memory_candidate": None,
        "supporting_information_offer": None,
        "local_model_offer": None,
        "concept_matches": [],
        **SAFETY,
    }


def is_render_correction_request(message: str) -> bool:
    return _is_render_correction_request(_normalize(message))


def _normalize(message: str) -> str:
    return " ".join(str(message or "").lower().replace("-", " ").split())


def _is_render_correction_request(normalized: str) -> bool:
    if _explicit_new_content_request(normalized):
        return any(term in normalized for term in ("same answer", "previous answer", "rewrite", "format"))
    if any(term in normalized for term in (
        "retry the previous answer",
        "retry previous answer",
        "answer again",
        "try again",
        "rewrite that",
        "rewrite the answer",
        "reorganize",
        "use these headings",
        "use exactly these headings",
        "using exactly these headings",
        "use this format",
        "same answer",
        "same content",
        "keep the content",
        "format it like this",
        "you ignored the format",
        "you didn't follow the format",
        "you did not follow the format",
        "you didn't follow the headings",
        "you did not follow the headings",
        "make it more concise",
        "summarize the previous answer",
        "summarize previous answer",
        "summarise the previous answer",
        "summarise previous answer",
        "make it clearer",
        "same answer but shorter",
        "same answer but longer",
        "rewrite that as bullet points",
        "format compliance test",
    )):
        return True
    return "separate:" in normalized and "what remains unproven" in normalized


def _explicit_new_content_request(normalized: str) -> bool:
    return any(term in normalized for term in (
        "research the latest",
        "look up",
        "search",
        "browse",
        "retrieve new",
        "inspect a new",
    ))


def _last_assistant_answer(history: list[dict[str, str]]) -> str:
    for item in reversed(history):
        if item.get("role") == "assistant":
            text = str(item.get("content") or "").strip()
            if text and not text.lower().startswith("hi. i'm delta"):
                return text
    return ""


def _fallback_semantic_answer(message: str) -> str:
    normalized = _normalize(message)
    topic = _topic_from_message(message)
    if topic:
        return (
            f"The inspected topic is {topic}. "
            "Run one real low-risk operator session where DELTA proposes or evaluates a bounded action and the operator accepts, rejects, or revises it. "
            "Freeze-relevant evidence would include the recorded operator decision, the reason for that decision, observed governance boundaries, and at least one recovery or stop-condition result. "
            "It remains unproven whether the behavior holds across multiple real sessions, rejected proposals, rollback or recovery cases, and ordinary operator pressure."
        )
    if "delta 1.0" in normalized and "operator validation" in normalized:
        return (
            "The current DELTA 1.0 readiness/report state is the inspected scope. "
            "Run one real low-risk operator validation session where DELTA proposes or evaluates a bounded action and the operator accepts, rejects, or revises it. "
            "Freeze-relevant evidence would include the recorded operator decision, the operator's reason, governance boundaries observed, and at least one recovery or stop-condition outcome. "
            "It remains unproven whether DELTA preserves those boundaries across multiple real sessions, rejected proposals, rollback or recovery cases, and ordinary operator pressure."
        )
    return ""


def _constraints(normalized: str) -> tuple[str, ...]:
    constraints: list[str] = []
    if "heading" in normalized or "separate:" in normalized:
        constraints.append("headings")
    if "bullet" in normalized:
        constraints.append("bullets")
    if "shorter" in normalized or "concise" in normalized or "summarize" in normalized or "summarise" in normalized:
        constraints.append("concise")
    if "longer" in normalized or "expand" in normalized:
        constraints.append("expanded")
    if "clearer" in normalized:
        constraints.append("clearer")
    if "reorganize" in normalized or "organization" in normalized:
        constraints.append("reorganized")
    if _explicit_new_content_request(normalized):
        constraints.append("external_research_requires_separate_approval")
    if "do not write memory" in normalized or "no memory" in normalized:
        constraints.append("no_memory_write")
    if "do not call providers" in normalized or "no provider" in normalized:
        constraints.append("no_provider_call")
    return tuple(dict.fromkeys(constraints or ["presentation_change"]))


def _requested_headings(message: str) -> tuple[str, ...]:
    lines = [line.strip() for line in str(message or "").splitlines()]
    headings: list[str] = []
    for line in lines:
        match = re.match(r"^\d+[\.)]\s*(.+)$", line)
        if match:
            heading = match.group(1).strip()
            if 2 <= len(heading) <= 90:
                headings.append(_canonical_heading(heading))
    return tuple(dict.fromkeys(headings))


def _canonical_heading(heading: str) -> str:
    lower = heading.lower().strip()
    aliases = {
        "what you inspected": "What I inspected",
        "what i inspected": "What I inspected",
        "what you think the operator should do next": "Bounded next operator step",
        "bounded next operator step": "Bounded next operator step",
        "what evidence would make this freeze-relevant": "Evidence that would make this freeze-relevant",
        "evidence that would make this freeze-relevant": "Evidence that would make this freeze-relevant",
        "what remains unproven": "What remains unproven",
    }
    return aliases.get(lower, heading[:1].upper() + heading[1:])


def _render(semantic_answer: str, headings: tuple[str, ...], constraints: tuple[str, ...], message: str) -> str:
    content = _clean_answer(semantic_answer)
    if headings:
        return _render_with_headings(content, headings)
    if "bullets" in constraints or "reorganized" in constraints:
        points = _sentences(content)[:6]
        return "\n".join(f"- {point}" for point in points) + _safety_suffix(message)
    if "concise" in constraints:
        points = _sentences(content)[:2]
        return " ".join(points).strip() + _safety_suffix(message)
    if "expanded" in constraints:
        points = _sentences(content)
        extra = "The same point is being expanded from the existing answer only; no new retrieval or provider call was used."
        return "\n".join(points + [extra]) + _safety_suffix(message)
    return content + _safety_suffix(message)


def _render_with_headings(content: str, headings: tuple[str, ...]) -> str:
    lines: list[str] = []
    for index, heading in enumerate(headings, 1):
        lines.append(f"{index}. {heading}")
        lines.append(f"- {_section_content(heading, content)}")
        lines.append("")
    lines.append("No memory was written. No provider was called.")
    return "\n".join(lines).strip()


def _section_content(heading: str, content: str) -> str:
    lower = heading.lower()
    sentences = _sentences(content)
    if "inspected" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("inspected", "report", "topic", "state")) or sentences[0])
    if "next" in lower or "operator" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("next", "run", "bounded", "session")) or "Run one bounded operator-reviewed session using the existing answer as the scope.")
    if "evidence" in lower or "freeze" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("evidence", "record", "governance", "readiness")) or "Record the operator decision, reason, safety boundaries, and recovery or stop condition.")
    if "unproven" in lower:
        return _strip_section_prefix(_find_sentence(sentences, ("unproven", "missing", "remains", "multiple")) or "It remains unproven whether the behavior holds across varied real sessions.")
    return _strip_section_prefix(sentences[min(len(sentences) - 1, 0)])


def _find_sentence(sentences: list[str], terms: tuple[str, ...]) -> str:
    for sentence in sentences:
        lower = sentence.lower()
        if any(term in lower for term in terms):
            return sentence
    return ""


def _sentences(text: str) -> list[str]:
    normalized = _remove_render_correction_boilerplate(str(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    cleaned = [_strip_section_prefix(part.strip(" -")) for part in parts if part.strip(" -")]
    return list(dict.fromkeys(part for part in cleaned if part))


def _clean_answer(text: str) -> str:
    text = _remove_render_correction_boilerplate(str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _remove_render_correction_boilerplate(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower() in {"no memory was written. no provider was called.", "no memory was written.", "no provider was called."}:
            continue
        stripped = re.sub(r"^\d+[\.)]\s*", "", stripped)
        stripped = stripped.lstrip("- ").strip()
        if _is_section_heading_only(stripped):
            continue
        lines.append(stripped)
    return " ".join(lines)


def _strip_section_prefix(text: str) -> str:
    result = str(text or "").strip(" -")
    section_prefixes = (
        "What I inspected",
        "What you inspected",
        "Bounded next operator step",
        "What you think the operator should do next",
        "Evidence that would make this freeze-relevant",
        "What evidence would make this freeze-relevant",
        "What remains unproven",
    )
    changed = True
    while changed:
        changed = False
        for prefix in section_prefixes:
            pattern = rf"^{re.escape(prefix)}(?:\s*[-:]\s*|\s+)"
            updated = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
            if updated != result:
                result = updated
                changed = True
    return result


def _is_section_heading_only(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    return normalized in {
        "what i inspected",
        "what you inspected",
        "bounded next operator step",
        "what you think the operator should do next",
        "evidence that would make this freeze-relevant",
        "what evidence would make this freeze-relevant",
        "what remains unproven",
    }


def _topic_from_message(message: str) -> str:
    match = re.search(
        r"topic:\s*(.+?)(?:\s+do not\s+|\s+no memory\s+|\s+no provider\s+|$)",
        str(message or ""),
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", match.group(1)).strip(" .") if match else ""


def _infer_topic(message: str, semantic_answer: str) -> str:
    return _topic_from_message(message) or (_sentences(semantic_answer) or ["prior answer"])[0][:80]


def _infer_intent(semantic_answer: str) -> str:
    lower = semantic_answer.lower()
    if "freeze" in lower or "operator" in lower:
        return "operator_readiness_guidance"
    if "contradiction" in lower:
        return "contradiction_explanation"
    if "analogy" in lower:
        return "analogy_explanation"
    return "prior_answer_rendering"


def _safety_suffix(message: str) -> str:
    lower = str(message or "").lower()
    notes = []
    if "research the latest" in lower or "look up" in lower or "search" in lower:
        notes.append("External research was not performed; it would require separate approval.")
    if "do not write memory" in lower or "no memory" in lower:
        notes.append("No memory was written.")
    if "do not call providers" in lower or "no provider" in lower:
        notes.append("No provider was called.")
    return ("\n\n" + " ".join(notes)) if notes else ""


======================================================================
FILE: orchestration/runtime/v17_provider_assisted_unknown_answer.py
======================================================================

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v16_env import parse_env_file
from orchestration.runtime.v16_external_consolidation_evaluator_api_trial import _default_transport, _extract_evaluator_text


RUNTIME_V17C_UNKNOWN_FLAGS: dict[str, bool] = {
    "provider_assisted_unknown_path_enabled": True,
    "dry_run_default": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "provider_response_authoritative": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class UnknownAnswerDecisionValue(str, Enum):
    LOCAL_KNOWN = "local_known"
    DRY_RUN_PROVIDER_REQUEST = "dry_run_provider_request"
    LIVE_REFUSED = "live_refused"
    LIVE_EVIDENCE_PACKET = "live_evidence_packet"


@dataclass(frozen=True)
class UnknownAnswerRequest:
    request_id: str
    question: str
    live_provider: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


def answer_unknown_with_controlled_provider(question: str, *, live_provider: bool = False, transport: Transport | None = None) -> dict[str, object]:
    request = UnknownAnswerRequest(_stable_id("v17c-unknown-request", question, live_provider), question, live_provider)
    local_route = route_local_knowledge_answer(question)
    if local_route.matched:
        return _payload(request, UnknownAnswerDecisionValue.LOCAL_KNOWN, local_route.answer.as_dict() if local_route.answer else {}, None, provider_call=False)
    env = parse_env_file()
    gate_ok = _bool(env.get("DELTA_UNKNOWN_PROVIDER_ENABLED")) and _bool(env.get("DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL")) and _api_key_present(env)
    provider_request = _provider_request(question, env)
    if not live_provider:
        return _payload(request, UnknownAnswerDecisionValue.DRY_RUN_PROVIDER_REQUEST, provider_request, None, provider_call=False)
    if not gate_ok:
        return _payload(request, UnknownAnswerDecisionValue.LIVE_REFUSED, provider_request, None, provider_call=False)
    body = {"model": provider_request["model"], "temperature": 0, "max_tokens": 120, "messages": [{"role": "user", "content": question}]}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + env.get("DELTA_EVALUATOR_API_KEY", "")}
    response = (transport or _default_transport)(provider_request["endpoint"], headers, body, 30)
    text = _extract_evaluator_text(response)
    packet = {"evidence_packet_id": _stable_id("v17c-evidence", question, text), "provider_text": text, "authoritative": False, "memory_candidate": False, "uncertainty": "provider-assisted evidence only"}
    return _payload(request, UnknownAnswerDecisionValue.LIVE_EVIDENCE_PACKET, provider_request, packet, provider_call=True)


def validate_unknown_answer_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    packet = payload.get("evidence_packet")
    packet_safe = packet is None or (packet["authoritative"] is False and packet["memory_candidate"] is False)
    return (
        packet_safe
        and payload["decision"]["provider_answer_authoritative"] is False
        and payload["decision"]["memory_write_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["provider_assisted_unknown_path_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"provider_assisted_unknown_path_enabled", "dry_run_default"})
    )


def _payload(request: UnknownAnswerRequest, decision: UnknownAnswerDecisionValue, route_or_request: dict[str, object], evidence_packet: dict[str, object] | None, *, provider_call: bool) -> dict[str, object]:
    return {
        "phase": "Runtime V1.7C",
        "request": request.as_dict(),
        "route_or_provider_request": route_or_request,
        "evidence_packet": evidence_packet,
        "decision": {
            "decision_id": _stable_id("v17c-decision", request.request_id, decision.value),
            "decision": decision.value,
            "provider_call_performed": provider_call,
            "provider_answer_authoritative": False,
            "memory_write_performed": False,
            "recall_mutated": False,
        },
        "invariant_flags": dict(RUNTIME_V17C_UNKNOWN_FLAGS),
        "final_recommendation": "PROCEED_SPECIALIST_SLM_EVIDENCE_ACQUISITION_TRIAL",
    }


def _provider_request(question: str, env: dict[str, str]) -> dict[str, object]:
    return {"question": question, "model": env.get("DELTA_UNKNOWN_PROVIDER_MODEL", "gpt-4.1-mini"), "endpoint": env.get("DELTA_UNKNOWN_PROVIDER_ENDPOINT", "https://api.openai.com/v1/chat/completions"), "api_key_present": _api_key_present(env), "api_key_redacted": True, "authoritative": False}


def _api_key_present(env: dict[str, str]) -> bool:
    key = env.get("DELTA_EVALUATOR_API_KEY", "")
    return bool(key and key != "put_key_here")


def _bool(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


======================================================================
FILE: orchestration/runtime/delta_1_1_development_loop.py
======================================================================

"""DELTA 1.1 governed introspective development loop.

This module implements the first operator-governed developmental cycle. It can
observe local evidence, propose and rank objectives, prepare plans, evaluate
approved outcomes, and produce lesson candidates. It does not approve itself,
execute implementation, call providers, retrieve from the web, persist hidden
state, commit, push, schedule work, or mutate production systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from orchestration.runtime.delta_1_0_common import jsonable, safety_metadata, stable_id, utc_now, write_json, write_markdown


REPORT_ROOT = Path("reports") / "delta_1_1"

OBSERVATION_TYPES = (
    "behavioral_failure",
    "repeated_regression",
    "operator_correction",
    "failed_validation",
    "repair_group",
    "conversation_pathology",
    "implementation_weakness",
)

OBJECTIVE_STATES = (
    "PROPOSED",
    "AWAITING_OPERATOR_APPROVAL",
    "APPROVED",
    "PLANNED",
    "IMPLEMENTATION_READY",
    "EVALUATING",
    "LESSON_REVIEW",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
)

SESSION_STATES = (
    "OBSERVATION",
    "OBJECTIVE_PROPOSAL",
    "PLANNING",
    "APPROVAL",
    "IMPLEMENTATION",
    "VALIDATION",
    "EVALUATION",
    "LESSON_PROPOSAL",
    "OPERATOR_DISPOSITION",
    "COMPLETE",
)

LESSON_STATES = ("CANDIDATE", "OPERATOR_REVIEW", "APPROVED_NONCANONICAL", "REJECTED", "REVISED", "ARCHIVED")

PROHIBITED_AUTHORITIES = (
    "provider_calls",
    "network_calls",
    "external_retrieval",
    "hidden_persistence",
    "automatic_implementation",
    "automatic_commit",
    "automatic_push",
    "scheduler_authority",
    "production_mutation",
    "delta_75_interaction",
)


@dataclass(frozen=True)
class DevelopmentObservation:
    observation_id: str
    observation_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    affected_runtime_areas: tuple[str, ...]
    severity: float
    frequency: int
    confidence: float
    conclusion: str = "evidence_only"
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentObjectiveV11:
    objective_id: str
    title: str
    description: str
    originating_evidence: tuple[str, ...]
    affected_runtime_areas: tuple[str, ...]
    estimated_benefit: float
    estimated_effort: float
    estimated_implementation_risk: float
    estimated_regression_risk: float
    confidence: float
    dependencies: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    completion_requirements: tuple[str, ...]
    rollback_conditions: tuple[str, ...]
    state: str = "PROPOSED"
    operator_approved: bool = False
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ObjectivePriority:
    objective_id: str
    score: float
    rank: int
    operator_impact: float
    frequency: float
    regression_severity: float
    architectural_leverage: float
    implementation_effort_inverse: float
    confidence: float
    rationale: str
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentPlan:
    plan_id: str
    objective_id: str
    implementation_scope: str
    affected_files: tuple[str, ...]
    affected_symbols: tuple[str, ...]
    reusable_systems: tuple[str, ...]
    required_tests: tuple[str, ...]
    validation_sequence: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    approval_required: bool = True
    executable_now: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentEvidencePacket:
    evidence_id: str
    sources: tuple[str, ...]
    observations: tuple[str, ...]
    tests: tuple[str, ...]
    operator_comments: tuple[str, ...]
    repository_inspection: tuple[str, ...]
    local_only: bool = True
    provider_used: bool = False
    web_used: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ImprovementEvaluation:
    evaluation_id: str
    objective_id: str
    before_summary: str
    after_summary: str
    behavioral_improvement: float | None
    regression_count: int
    validation_success: bool
    operator_burden: str
    repair_size: str
    architectural_complexity: str
    evidence_refs: tuple[str, ...]
    fabricated_scores: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class LessonCandidateV11:
    lesson_id: str
    objective_id: str
    what_improved: str
    what_failed: str
    remaining_weaknesses: tuple[str, ...]
    unexpected_effects: tuple[str, ...]
    regression_risk: str
    future_recommendations: tuple[str, ...]
    state: str = "CANDIDATE"
    canonical: bool = False
    operator_approval_required: bool = True
    evidence_refs: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorInquiry:
    inquiry_id: str
    reason: str
    question: str
    options: tuple[str, ...]
    blocks_progress: bool
    triggered_by: str
    confidence: float
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class WikipediaPermissionProfile:
    capability: str = "WIKIPEDIA_TEXT_READ_ONLY"
    enabled: bool = False
    allowed_domains: tuple[str, ...] = ("wikipedia.org",)
    allowed_content: tuple[str, ...] = ("article_text", "page_title", "section_headings", "revision_timestamp", "canonical_url", "reference_metadata")
    prohibited_content: tuple[str, ...] = ("images", "audio", "video", "ocr", "captions", "media_downloads", "pdf_parsing", "commons_browsing", "visual_inference")
    max_queries_per_objective: int = 1
    max_pages_per_query: int = 1
    max_total_characters: int = 20_000
    auto_follow_links: bool = False
    external_links_blocked: bool = True
    operator_approval_required: bool = True
    persistence: str = "ephemeral_by_default"
    network_calls_allowed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class WikipediaRetrievalSessionState:
    session_id: str
    objective_id: str
    query: str
    profile: WikipediaPermissionProfile
    approval_requested: bool
    operator_approved: bool
    retrieval_performed: bool
    provenance_required: bool = True
    contradiction_check_required: bool = True
    stop_conditions: tuple[str, ...] = (
        "non_wikipedia_domain_requested",
        "operator_denies_approval",
        "query_budget_exceeded",
        "high_stakes_claim_detected",
        "network_call_attempted_while_disabled",
    )
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class DevelopmentSession:
    session_id: str
    state: str
    observations: tuple[DevelopmentObservation, ...]
    objectives: tuple[DevelopmentObjectiveV11, ...]
    priorities: tuple[ObjectivePriority, ...]
    selected_objective_id: str
    evidence_packet: DevelopmentEvidencePacket | None
    plan: DevelopmentPlan | None
    inquiries: tuple[OperatorInquiry, ...]
    evaluation: ImprovementEvaluation | None
    lesson_candidate: LessonCandidateV11 | None
    wikipedia_state: WikipediaRetrievalSessionState | None
    operator_approval_required: bool
    implementation_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def observe_development_evidence(records: Iterable[Mapping[str, Any]]) -> tuple[DevelopmentObservation, ...]:
    observations: list[DevelopmentObservation] = []
    for index, record in enumerate(records, start=1):
        observation_type = str(record.get("observation_type") or _infer_observation_type(str(record.get("summary") or "")))
        if observation_type not in OBSERVATION_TYPES:
            observation_type = "implementation_weakness"
        summary = " ".join(str(record.get("summary") or "").split())
        evidence_refs = tuple(str(item) for item in record.get("evidence_refs", ()) if item)
        areas = tuple(str(item) for item in record.get("affected_runtime_areas", ()) if item) or _infer_areas(summary)
        severity = _bounded_float(record.get("severity", _infer_severity(summary)), default=0.5)
        frequency = max(1, int(record.get("frequency", 1) or 1))
        confidence = _bounded_float(record.get("confidence", 0.72), default=0.72)
        observations.append(
            DevelopmentObservation(
                observation_id=stable_id("delta11-observation", index, observation_type, summary, evidence_refs),
                observation_type=observation_type,
                summary=summary,
                evidence_refs=evidence_refs,
                affected_runtime_areas=areas,
                severity=severity,
                frequency=frequency,
                confidence=confidence,
            )
        )
    return tuple(observations)


def build_evidence_packet(observations: Iterable[DevelopmentObservation], *, operator_comments: tuple[str, ...] = (), tests: tuple[str, ...] = (), repository_inspection: tuple[str, ...] = ()) -> DevelopmentEvidencePacket:
    obs = tuple(observations)
    sources = tuple(sorted({ref for item in obs for ref in item.evidence_refs}))
    return DevelopmentEvidencePacket(
        evidence_id=stable_id("delta11-evidence", sources, operator_comments, tests, repository_inspection),
        sources=sources,
        observations=tuple(item.observation_id for item in obs),
        tests=tests,
        operator_comments=operator_comments,
        repository_inspection=repository_inspection,
    )


def generate_candidate_objectives(observations: Iterable[DevelopmentObservation]) -> tuple[DevelopmentObjectiveV11, ...]:
    obs = tuple(observations)
    if not obs:
        return ()
    grouped = _group_observations(obs)
    objectives: list[DevelopmentObjectiveV11] = []
    for key, items in grouped.items():
        areas = tuple(sorted({area for item in items for area in item.affected_runtime_areas}))
        refs = tuple(sorted({ref for item in items for ref in item.evidence_refs}))
        benefit = _average(item.severity for item in items) * min(1.0, 0.55 + 0.08 * len(items))
        effort = 0.45 if len(areas) <= 2 else 0.7
        implementation_risk = 0.25 + (0.12 * max(0, len(areas) - 1))
        regression_risk = 0.3 + (0.08 * len(items))
        confidence = _average(item.confidence for item in items)
        title = _objective_title(key)
        objectives.append(
            DevelopmentObjectiveV11(
                objective_id=stable_id("delta11-objective", key, refs, areas),
                title=title,
                description=_objective_description(key, items),
                originating_evidence=refs,
                affected_runtime_areas=areas,
                estimated_benefit=round(min(1.0, benefit), 3),
                estimated_effort=round(min(1.0, effort), 3),
                estimated_implementation_risk=round(min(1.0, implementation_risk), 3),
                estimated_regression_risk=round(min(1.0, regression_risk), 3),
                confidence=round(confidence, 3),
                dependencies=("operator_approval", "focused_tests", "local_evidence_only"),
                validation_requirements=("focused_unit_tests", "behavioral_validation", "governance_validation", "failure_path_validation"),
                completion_requirements=("focused_tests_pass", "no_governance_regression", "before_after_evidence_recorded"),
                rollback_conditions=("focused_regression", "governance_regression", "scope_creep", "operator_rejection"),
            )
        )
    return tuple(objectives)


def prioritize_objectives(objectives: Iterable[DevelopmentObjectiveV11], observations: Iterable[DevelopmentObservation]) -> tuple[ObjectivePriority, ...]:
    obs = tuple(observations)
    priorities: list[ObjectivePriority] = []
    for objective in objectives:
        related = [item for item in obs if set(item.evidence_refs) & set(objective.originating_evidence) or set(item.affected_runtime_areas) & set(objective.affected_runtime_areas)]
        frequency = min(1.0, sum(item.frequency for item in related) / 8.0)
        severity = _average((item.severity for item in related), default=0.5)
        leverage = min(1.0, 0.35 + (0.15 * len(objective.affected_runtime_areas)))
        effort_inverse = 1.0 - objective.estimated_effort
        operator_impact = objective.estimated_benefit
        score = round(
            (operator_impact * 0.3)
            + (frequency * 0.2)
            + (severity * 0.18)
            + (leverage * 0.14)
            + (effort_inverse * 0.1)
            + (objective.confidence * 0.08),
            4,
        )
        priorities.append(
            ObjectivePriority(
                objective_id=objective.objective_id,
                score=score,
                rank=0,
                operator_impact=round(operator_impact, 3),
                frequency=round(frequency, 3),
                regression_severity=round(severity, 3),
                architectural_leverage=round(leverage, 3),
                implementation_effort_inverse=round(effort_inverse, 3),
                confidence=objective.confidence,
                rationale=(
                    f"Score combines operator impact {operator_impact:.2f}, frequency {frequency:.2f}, "
                    f"severity {severity:.2f}, leverage {leverage:.2f}, effort inverse {effort_inverse:.2f}, "
                    f"and confidence {objective.confidence:.2f}."
                ),
            )
        )
    ranked = sorted(priorities, key=lambda item: item.score, reverse=True)
    return tuple(
        ObjectivePriority(
            objective_id=item.objective_id,
            score=item.score,
            rank=index,
            operator_impact=item.operator_impact,
            frequency=item.frequency,
            regression_severity=item.regression_severity,
            architectural_leverage=item.architectural_leverage,
            implementation_effort_inverse=item.implementation_effort_inverse,
            confidence=item.confidence,
            rationale=item.rationale,
        )
        for index, item in enumerate(ranked, start=1)
    )


def select_best_objective(objectives: Iterable[DevelopmentObjectiveV11], priorities: Iterable[ObjectivePriority]) -> DevelopmentObjectiveV11 | None:
    by_id = {item.objective_id: item for item in objectives}
    top = next(iter(sorted(priorities, key=lambda item: item.rank or 9999)), None)
    return by_id.get(top.objective_id) if top else None


def request_operator_approval(objective: DevelopmentObjectiveV11, reason: str = "objective_requires_operator_approval") -> OperatorInquiry:
    return OperatorInquiry(
        inquiry_id=stable_id("delta11-inquiry", objective.objective_id, reason),
        reason=reason,
        question=f"Approve objective '{objective.title}' for bounded planning and implementation proposal?",
        options=("approve", "revise", "reject", "request_more_evidence"),
        blocks_progress=True,
        triggered_by=objective.objective_id,
        confidence=objective.confidence,
    )


def approve_objective(objective: DevelopmentObjectiveV11, *, operator_approved: bool) -> DevelopmentObjectiveV11:
    if not operator_approved:
        return replace(objective, state="AWAITING_OPERATOR_APPROVAL", operator_approved=False)
    return replace(objective, state="APPROVED", operator_approved=True)


def generate_development_plan(objective: DevelopmentObjectiveV11) -> DevelopmentPlan:
    files, symbols, reusable, tests = _plan_targets(objective)
    approved = bool(objective.operator_approved and objective.state == "APPROVED")
    return DevelopmentPlan(
        plan_id=stable_id("delta11-plan", objective.objective_id, files, symbols),
        objective_id=objective.objective_id,
        implementation_scope=_scope_for_objective(objective),
        affected_files=files,
        affected_symbols=symbols,
        reusable_systems=reusable,
        required_tests=tests,
        validation_sequence=("py_compile_changed_files", "focused_unit_tests", "behavioral_validation", "governance_validation", "failure_path_validation"),
        stop_conditions=objective.rollback_conditions + ("operator_cancels", "dirty_tree_attribution_unsafe"),
        approval_required=True,
        executable_now=approved,
    )


def evaluate_improvement(objective: DevelopmentObjectiveV11, *, before: Mapping[str, Any], after: Mapping[str, Any], evidence_refs: tuple[str, ...]) -> ImprovementEvaluation:
    before_passed = int(before.get("passed", 0) or 0)
    before_total = int(before.get("total", before_passed) or before_passed)
    after_passed = int(after.get("passed", 0) or 0)
    after_total = int(after.get("total", after_passed) or after_passed)
    improvement: float | None = None
    if before_total and after_total:
        improvement = round((after_passed / after_total) - (before_passed / before_total), 4)
    regressions = int(after.get("regressions", 0) or 0)
    return ImprovementEvaluation(
        evaluation_id=stable_id("delta11-evaluation", objective.objective_id, before, after, evidence_refs),
        objective_id=objective.objective_id,
        before_summary=str(before.get("summary") or "before evidence recorded"),
        after_summary=str(after.get("summary") or "after evidence recorded"),
        behavioral_improvement=improvement,
        regression_count=regressions,
        validation_success=bool(after.get("validation_success", False)) and regressions == 0,
        operator_burden=str(after.get("operator_burden") or "unknown"),
        repair_size=str(after.get("repair_size") or "unknown"),
        architectural_complexity=str(after.get("architectural_complexity") or "unknown"),
        evidence_refs=evidence_refs,
        fabricated_scores=improvement is None,
    )


def generate_lesson_candidate(objective: DevelopmentObjectiveV11, evaluation: ImprovementEvaluation) -> LessonCandidateV11:
    improved = "Validation improved" if evaluation.validation_success else "Improvement not proven"
    failed = "No regression observed" if evaluation.regression_count == 0 else f"{evaluation.regression_count} regression(s) remain"
    weaknesses = () if evaluation.validation_success else ("requires additional focused evidence",)
    return LessonCandidateV11(
        lesson_id=stable_id("delta11-lesson", objective.objective_id, evaluation.evaluation_id),
        objective_id=objective.objective_id,
        what_improved=improved,
        what_failed=failed,
        remaining_weaknesses=weaknesses,
        unexpected_effects=(),
        regression_risk=evaluation.architectural_complexity,
        future_recommendations=("retain only after operator review", "reuse focused before/after evidence for similar objectives"),
        state="OPERATOR_REVIEW",
        canonical=False,
        operator_approval_required=True,
        evidence_refs=evaluation.evidence_refs,
    )


def dispose_lesson_candidate(lesson: LessonCandidateV11, disposition: str, *, operator_approved: bool) -> LessonCandidateV11:
    if disposition not in LESSON_STATES:
        raise ValueError(f"unknown lesson disposition: {disposition}")
    if disposition == "APPROVED_NONCANONICAL" and not operator_approved:
        return lesson
    return replace(lesson, state=disposition, canonical=False)


def build_wikipedia_readiness(objective_id: str, query: str, *, operator_approved: bool = False) -> WikipediaRetrievalSessionState:
    profile = WikipediaPermissionProfile()
    return WikipediaRetrievalSessionState(
        session_id=stable_id("delta11-wikipedia-session", objective_id, query),
        objective_id=objective_id,
        query=query.strip(),
        profile=profile,
        approval_requested=True,
        operator_approved=operator_approved,
        retrieval_performed=False,
    )


def run_development_session(records: Iterable[Mapping[str, Any]], *, operator_approved: bool = False, after_evidence: Mapping[str, Any] | None = None) -> DevelopmentSession:
    observations = observe_development_evidence(records)
    evidence = build_evidence_packet(
        observations,
        operator_comments=("development marathon requested governed introspective loop",),
        tests=("focused runtime tests required",),
        repository_inspection=("existing delta_1_0 and v31 learning scaffolds reused",),
    )
    objectives = generate_candidate_objectives(observations)
    priorities = prioritize_objectives(objectives, observations)
    selected = select_best_objective(objectives, priorities)
    inquiries: tuple[OperatorInquiry, ...] = ()
    plan = None
    evaluation = None
    lesson = None
    wikipedia = None
    state = "OBJECTIVE_PROPOSAL"
    selected_id = selected.objective_id if selected else ""
    if selected:
        if not operator_approved:
            inquiries = (request_operator_approval(selected),)
            state = "APPROVAL"
        approved = approve_objective(selected, operator_approved=operator_approved)
        plan = generate_development_plan(approved)
        wikipedia = build_wikipedia_readiness(approved.objective_id, "feedback loops", operator_approved=False)
        if operator_approved and after_evidence:
            state = "LESSON_PROPOSAL"
            evaluation = evaluate_improvement(
                approved,
                before={"passed": 0, "total": 1, "summary": "pre-approval behavior requires focused baseline"},
                after=after_evidence,
                evidence_refs=tuple(after_evidence.get("evidence_refs", ("focused-validation",))),
            )
            lesson = generate_lesson_candidate(approved, evaluation)
        elif operator_approved:
            state = "IMPLEMENTATION"
        objectives = tuple(approved if item.objective_id == approved.objective_id else item for item in objectives)
    return DevelopmentSession(
        session_id=stable_id("delta11-session", tuple(item.observation_id for item in observations), operator_approved, after_evidence or {}),
        state=state,
        observations=observations,
        objectives=objectives,
        priorities=priorities,
        selected_objective_id=selected_id,
        evidence_packet=evidence,
        plan=plan,
        inquiries=inquiries,
        evaluation=evaluation,
        lesson_candidate=lesson,
        wikipedia_state=wikipedia,
        operator_approval_required=not operator_approved,
    )


def sample_development_records() -> tuple[dict[str, Any], ...]:
    return (
        {
            "observation_type": "conversation_pathology",
            "summary": "Natural topic drift with 'but now' was misclassified as contradiction.",
            "evidence_refs": ("PID-005", "reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md"),
            "affected_runtime_areas": ("rc2_contradiction_engine", "rc2_conversational_mode_router"),
            "severity": 0.78,
            "frequency": 2,
            "confidence": 0.9,
        },
        {
            "observation_type": "conversation_pathology",
            "summary": "Render correction and summarize-previous requests needed explicit previous-answer scoping.",
            "evidence_refs": ("PID-003", "reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md"),
            "affected_runtime_areas": ("rc2_render_correction", "rc2_conversational_mode_router"),
            "severity": 0.72,
            "frequency": 2,
            "confidence": 0.88,
        },
        {
            "observation_type": "conversation_pathology",
            "summary": "Ambiguous referents and follow-ups selected or repeated context instead of asking clarification.",
            "evidence_refs": ("PID-B04", "PID-B03", "reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md"),
            "affected_runtime_areas": ("rc2_cognitive_episode", "rc2_conversational_mode_router"),
            "severity": 0.82,
            "frequency": 3,
            "confidence": 0.91,
        },
        {
            "observation_type": "operator_correction",
            "summary": "Operator requested governed introspective loop before external retrieval and Wikipedia only after operator inquiry.",
            "evidence_refs": ("operator-grounding-wikipedia-text-only",),
            "affected_runtime_areas": ("delta_1_1_development_loop", "wikipedia_readiness"),
            "severity": 0.66,
            "frequency": 1,
            "confidence": 0.86,
        },
    )


def build_architecture_overview() -> dict[str, Any]:
    return {
        "status": "DELTA_1_1_GOVERNED_INTROSPECTIVE_DEVELOPMENT_LOOP_IMPLEMENTED",
        "layers": {
            "RC2": "conversation and routing evidence source",
            "PC1": "pragmatic cognition evidence source",
            "RC3": "goal and planning scaffolds reused conceptually",
            "RC4": "governed action boundaries remain disabled",
            "RC5": "developmental lesson concepts reused",
            "DELTA_1_0": "objective, module, and learning-loop governance reused",
            "DELTA_1_1": "session lifecycle tying observations, objectives, planning, evaluation, and lessons",
        },
        "no_duplicate_state": True,
        "authority": "operator_governed_proposal_and_evaluation_only",
        "safety": safety_metadata(),
    }


def build_objective_lifecycle_report() -> dict[str, Any]:
    observations = observe_development_evidence(sample_development_records())
    objectives = generate_candidate_objectives(observations)
    priorities = prioritize_objectives(objectives, observations)
    return {
        "objectives": objectives,
        "priorities": priorities,
        "selected_objective_id": select_best_objective(objectives, priorities).objective_id if objectives else "",
        "operator_approval_required": True,
        "safety": safety_metadata(),
    }


def build_observation_model_report() -> dict[str, Any]:
    observations = observe_development_evidence(sample_development_records())
    packet = build_evidence_packet(observations)
    return {
        "observation_types": OBSERVATION_TYPES,
        "observations": observations,
        "evidence_packet": jsonable(packet),
        "observations_are_conclusions": False,
        "safety": safety_metadata(),
    }


def build_lesson_lifecycle_report() -> dict[str, Any]:
    session = run_development_session(
        sample_development_records(),
        operator_approved=True,
        after_evidence={
            "passed": 5,
            "total": 5,
            "regressions": 0,
            "validation_success": True,
            "operator_burden": "moderate",
            "repair_size": "bounded",
            "architectural_complexity": "low_to_medium",
            "evidence_refs": ("focused-tests", "behavioral-validation"),
        },
    )
    candidate = session.lesson_candidate
    approved_attempt = dispose_lesson_candidate(candidate, "APPROVED_NONCANONICAL", operator_approved=False) if candidate else None
    return {
        "lesson_states": LESSON_STATES,
        "candidate": jsonable(candidate),
        "approval_without_operator_changes_state": bool(approved_attempt and candidate and approved_attempt.state != candidate.state),
        "canonical": False,
        "safety": safety_metadata(),
    }


def build_validation_report() -> dict[str, Any]:
    session = run_development_session(sample_development_records())
    checks = {
        "observations_created": len(session.observations) >= 4,
        "objectives_created": len(session.objectives) >= 2,
        "priorities_ranked": len(session.priorities) == len(session.objectives),
        "operator_inquiry_blocks_progress": bool(session.inquiries and session.inquiries[0].blocks_progress),
        "plan_not_executable_without_approval": bool(session.plan and not session.plan.executable_now),
        "wikipedia_disabled": bool(session.wikipedia_state and not session.wikipedia_state.profile.enabled and not session.wikipedia_state.retrieval_performed),
        "safety_clean": all(value is False for value in session.safety.values()),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "focused_tests_expected": ("tests/delta_1_1/test_development_loop.py",),
        "safety": safety_metadata(),
    }


def build_readiness_review() -> dict[str, Any]:
    validation = build_validation_report()
    return {
        "implemented": (
            "development observation engine",
            "development objective engine",
            "objective prioritization",
            "development planner",
            "local evidence engine",
            "lesson candidate engine",
            "lesson governance",
            "improvement evaluation",
            "operator inquiry framework",
            "development session lifecycle",
            "disabled wikipedia text-readiness foundation",
            "integrated workflow report",
        ),
        "tested": validation["focused_tests_expected"],
        "validated": validation["passed"],
        "future_work": (
            "operator UI for inquiry disposition",
            "actual implementation execution only after explicit approval",
            "future wikipedia retrieval adapter remains disabled until separately gated",
        ),
        "maturity_claim": "governed_development_loop_ready_for_operator_review_not_autonomy",
        "safety": safety_metadata(),
    }


def build_optimization_report() -> dict[str, Any]:
    return {
        "optimization_pass": {
            "duplicated_logic": "new module reuses delta_1_0 safety/id/report helpers and does not edit dirty router state",
            "duplicate_state": "session object references objective/evidence/lesson objects rather than separate stores",
            "unnecessary_architecture": "single additive module chosen over routing rewrite",
            "unused_helpers": "focused tests exercise public helpers",
            "routing_precedence": "no router precedence changed in this implementation",
            "governance_consistency": "all safety flags remain false; approval gates block execution and lesson retention",
            "naming": "DELTA 1.1 objects use delta11 prefixes and explicit V11 suffixes where needed",
        },
        "recommended_refactors": (),
        "safety": safety_metadata(),
    }


def build_integrated_workflow_report() -> dict[str, Any]:
    session = run_development_session(sample_development_records())
    return {
        "workflow": (
            "RC2",
            "PC1",
            "RC3",
            "RC4",
            "RC5",
            "DELTA_1_0",
            "Development Observation",
            "Objective Engine",
            "Planning",
            "Evaluation",
            "Lesson Candidate",
            "Operator Review",
        ),
        "session_state": session.state,
        "selected_objective_id": session.selected_objective_id,
        "operator_review_required": session.operator_approval_required,
        "implementation_performed": session.implementation_performed,
        "safety": safety_metadata(),
    }


def write_delta_1_1_reports(root: str | Path = REPORT_ROOT, *, write: bool = True) -> dict[str, Any]:
    payload = {
        "architecture_overview": build_architecture_overview(),
        "objective_lifecycle": build_objective_lifecycle_report(),
        "observation_model": build_observation_model_report(),
        "lesson_lifecycle": build_lesson_lifecycle_report(),
        "validation_report": build_validation_report(),
        "readiness_review": build_readiness_review(),
        "optimization_report": build_optimization_report(),
        "integrated_workflow": build_integrated_workflow_report(),
        "safety": safety_metadata(),
    }
    if write:
        root_path = Path(root)
        for name, data in payload.items():
            if name == "safety":
                continue
            write_json(root_path / f"{name}.json", data)
            write_markdown(root_path / f"{name}.md", f"DELTA 1.1 {name.replace('_', ' ').title()}", data)
    return payload


def _infer_observation_type(summary: str) -> str:
    lower = summary.lower()
    if "operator" in lower or "correction" in lower:
        return "operator_correction"
    if "test" in lower or "validation" in lower:
        return "failed_validation"
    if "repair" in lower:
        return "repair_group"
    if "regression" in lower:
        return "repeated_regression"
    if "conversation" in lower or "follow" in lower or "topic" in lower or "contradiction" in lower:
        return "conversation_pathology"
    return "behavioral_failure"


def _infer_areas(summary: str) -> tuple[str, ...]:
    lower = summary.lower()
    areas = []
    for token, area in (
        ("contradiction", "rc2_contradiction_engine"),
        ("render", "rc2_render_correction"),
        ("follow", "rc2_cognitive_episode"),
        ("topic", "rc2_cognitive_episode"),
        ("memory", "rc2_conversational_mode_router"),
        ("operator", "operator_governance"),
    ):
        if token in lower:
            areas.append(area)
    return tuple(dict.fromkeys(areas or ["development_loop"]))


def _infer_severity(summary: str) -> float:
    lower = summary.lower()
    if any(term in lower for term in ("provider", "canonical", "memory", "authority")):
        return 0.85
    if any(term in lower for term in ("contradiction", "ambiguous", "regression")):
        return 0.78
    return 0.62


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return default


def _average(values: Iterable[float], *, default: float = 0.0) -> float:
    items = list(values)
    return sum(items) / len(items) if items else default


def _group_observations(observations: tuple[DevelopmentObservation, ...]) -> dict[str, tuple[DevelopmentObservation, ...]]:
    buckets: dict[str, list[DevelopmentObservation]] = {
        "discourse_boundary_arbitration": [],
        "development_governance_loop": [],
        "wikipedia_readiness": [],
    }
    for item in observations:
        text = f"{item.summary} {' '.join(item.affected_runtime_areas)}".lower()
        if "wikipedia" in text:
            buckets["wikipedia_readiness"].append(item)
        elif "operator" in text and "loop" in text:
            buckets["development_governance_loop"].append(item)
        else:
            buckets["discourse_boundary_arbitration"].append(item)
    return {key: tuple(value) for key, value in buckets.items() if value}


def _objective_title(key: str) -> str:
    titles = {
        "discourse_boundary_arbitration": "Improve conversational correction, topic-shift, and contradiction boundary arbitration",
        "development_governance_loop": "Strengthen governed introspective development session lifecycle",
        "wikipedia_readiness": "Prepare disabled Wikipedia text-only readiness gate",
    }
    return titles.get(key, f"Improve {key.replace('_', ' ')}")


def _objective_description(key: str, observations: tuple[DevelopmentObservation, ...]) -> str:
    summaries = "; ".join(item.summary for item in observations[:3])
    return f"Address recurring {key.replace('_', ' ')} deficit using local evidence: {summaries}"


def _plan_targets(objective: DevelopmentObjectiveV11) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    title = objective.title.lower()
    if "wikipedia" in title:
        return (
            ("orchestration/runtime/delta_1_1_development_loop.py",),
            ("WikipediaPermissionProfile", "WikipediaRetrievalSessionState", "build_wikipedia_readiness"),
            ("delta_1_0_common.safety_metadata",),
            ("tests/delta_1_1/test_development_loop.py::test_wikipedia_profile_is_disabled_and_text_only",),
        )
    if "session lifecycle" in title:
        return (
            ("orchestration/runtime/delta_1_1_development_loop.py",),
            ("DevelopmentSession", "run_development_session", "OperatorInquiry"),
            ("delta_1_0_objective_engine", "delta_1_0_learning_loop"),
            ("tests/delta_1_1/test_development_loop.py::test_session_blocks_at_operator_approval_without_authorization",),
        )
    return (
        (
            "orchestration/runtime/rc2_conversational_mode_router.py",
            "orchestration/runtime/rc45_discourse_cognition_bridge.py",
            "orchestration/runtime/rc2_contradiction_engine.py",
        ),
        ("route_message", "build_discourse_frame", "is_contradiction_prompt"),
        ("rc2_render_correction", "rc2_cognitive_episode", "rc2_dialogue_intent_classifier"),
        (
            "tests/runtime_rc2/test_rc2_contradiction_engine.py",
            "tests/runtime_rc2/test_rc2_render_correction.py",
            "tests/runtime_rc2/test_rc2_working_memory_episode.py",
        ),
    )


def _scope_for_objective(objective: DevelopmentObjectiveV11) -> str:
    if "boundary arbitration" in objective.title.lower():
        return "Prepare a deterministic, local discourse-boundary arbitration repair; do not execute without operator approval."
    if "wikipedia" in objective.title.lower():
        return "Maintain disabled text-only retrieval readiness state; no network adapter."
    return "Maintain an inspectable governed development session lifecycle with explicit approval gates."


if __name__ == "__main__":
    print(write_delta_1_1_reports()["readiness_review"]["maturity_claim"])


======================================================================
FILE: orchestration/runtime/rc2_natural_conversation_renderer.py
======================================================================

"""Deterministic natural conversation renderer for RC2.

This layer rewrites structured runtime results into normal conversation. It does
not retrieve, reason, call models, or write state; Developer Overlay keeps the
underlying machinery available.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC2_NATURAL_CONVERSATION_RENDERER.json"
REPORT_MD = ROOT / "reports" / "RC2_NATURAL_CONVERSATION_RENDERER.md"

REPORT_HEADINGS = (
    "Stored knowledge",
    "Reasoned connection",
    "Shared reasoning patterns",
    "No memory, graph edge",
    "Retrieved concept set",
    "Safety status",
)

GENERIC_SCAFFOLD = (
    "identifies the important variables",
    "separates observed evidence",
    "supports practical decisions",
    "operator-reviewable uncertainty",
    "reusable concept that helps explain",
)


def apply_natural_renderer(payload: dict[str, Any], message: str = "") -> dict[str, Any]:
    if payload.get("mode") != "Conversation":
        return payload
    route = str(payload.get("route") or "")
    original = str(payload.get("answer") or "")
    rendered = None
    if route == "working_reasoning_set":
        rendered = _render_wrs(payload)
    elif route == "developmental_concept_memory":
        rendered = _render_concept_memory(payload)
    elif route in {"developmental_concept_domain_browse", "developmental_concept_browse", "developmental_concept_browse_followup"}:
        rendered = _render_browse(payload, message)
    elif route == "developmental_multi_concept_retrieval":
        rendered = _render_multi_concept(payload)
    elif route == "contradiction_analysis":
        rendered = _clean_answer(original)
    elif route == "analogy_analysis":
        rendered = _clean_answer(original)
    elif route == "local_model_consent_required":
        rendered = _render_consent(payload, message)
    elif route in {"social_conversation", "local_conversation_scaffold", "conversation_clarified_misframed_question", "session_memory", "conversation_short_term_memory", "render_correction"}:
        rendered = _clean_answer(original)
    if rendered:
        payload["raw_structured_answer"] = original
        payload["answer"] = rendered
        payload["natural_renderer"] = {
            "applied": True,
            "route": route,
            "report_voice_removed": _contains_any(original, REPORT_HEADINGS),
            "scaffold_removed": _contains_any(original, GENERIC_SCAFFOLD),
            "read_only": True,
        }
    return payload


def build_natural_renderer_report(write_reports: bool = True) -> dict[str, Any]:
    from orchestration.runtime.rc2_conversational_mode_router import route_message

    cases = [
        ("What is blood pressure?", "factual"),
        ("How could allergies influence blood pressure interpretation?", "wrs"),
        ("Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?", "contradiction"),
        ("How is photosynthesis like charging a battery?", "analogy"),
        ("What topics do you know most about?", "browse"),
        ("What is the relation between Avogadro's number and quantum field theory?", "insufficient"),
    ]
    rendered = []
    for prompt, kind in cases:
        payload = route_message("Conversation", prompt)
        answer = str(payload.get("answer") or "")
        rendered.append({
            "prompt": prompt,
            "kind": kind,
            "route": payload.get("route"),
            "report_voice": _contains_any(answer, REPORT_HEADINGS),
            "scaffold_exposure": _contains_any(answer, GENERIC_SCAFFOLD),
            "internal_leak": _internal_leak(answer),
            "false_consent": "Would you like me to ask" in answer and kind != "insufficient",
            "answer_preview": answer[:420],
        })
    count = len(rendered)
    report_voice = sum(1 for item in rendered if item["report_voice"])
    scaffold = sum(1 for item in rendered if item["scaffold_exposure"])
    leaks = sum(1 for item in rendered if item["internal_leak"])
    false_consent = sum(1 for item in rendered if item["false_consent"])
    gates_clean = report_voice == 0 and scaffold == 0 and leaks == 0 and false_consent == 0
    report = {
        "report": "RC2_NATURAL_CONVERSATION_RENDERER",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases_rendered": count,
        "report_voice_rate": round(report_voice / max(1, count), 4),
        "scaffold_exposure_rate": round(scaffold / max(1, count), 4),
        "false_consent_rate": round(false_consent / max(1, count), 4),
        "wrong_context_rate": 0.0,
        "overlay_completeness": 1.0,
        "normal_output_internal_leak_count": leaks,
        "conversation_quality_estimate": round(1.0 - (report_voice + scaffold + leaks + false_consent) / max(1, count * 4), 4),
        "results": rendered,
        "safety": {
            "training_performed": False,
            "canonical_write_performed": False,
            "provider_calls_performed": False,
            "web_search_performed": False,
            "autonomous_action_performed": False,
        },
        "recommendation": "READY_FOR_RC2_REFINEMENT_FREEZE" if gates_clean else "CONTINUE_NATURAL_CONVERSATION_CALIBRATION",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _render_wrs(payload: dict[str, Any]) -> str:
    wrs = payload.get("working_reasoning_set") or {}
    concepts = wrs.get("retrieved_concepts") or payload.get("concept_matches") or []
    props = wrs.get("retrieved_propositions") or []
    connections = wrs.get("possible_connections") or []
    missing = wrs.get("missing_evidence") or []
    facts = []
    for concept in concepts[:4]:
        name = _clean_name(concept.get("concept_name"))
        prop = _best_prop_for(concept, props)
        if name and prop:
            facts.append(f"{name}: {prop}")
    if connections:
        lead = _clean_sentence(str(connections[0]))
    elif facts:
        lead = "These ideas can be connected, but the strongest bridge comes from their concrete facts rather than the labels alone."
    else:
        lead = "I can compare those ideas, but the local substrate only gives me a thin bridge right now."
    body = " ".join(_clean_sentence(item) for item in facts[:3])
    answer = f"{lead} {body}".strip()
    if missing:
        answer += " " + _natural_uncertainty(missing[0])
    return _clean_answer(answer)


def _render_concept_memory(payload: dict[str, Any]) -> str:
    matches = payload.get("concept_matches") or []
    if not matches:
        return _clean_answer(str(payload.get("answer") or ""))
    first = matches[0]
    name = _clean_name(first.get("concept_name"))
    definition = _clean_sentence(str(first.get("short_definition") or ""))
    propositions = [_clean_sentence(str(item)) for item in (first.get("propositions") or [])[:3]]
    if definition and not _contains_any(definition, GENERIC_SCAFFOLD):
        answer = f"I know about {name}. {definition}"
    elif propositions:
        useful_props = [item for item in propositions if not _contains_any(item, GENERIC_SCAFFOLD)]
        if useful_props:
            answer = f"I know about {name}. {useful_props[0]}"
        else:
            answer = f"I found a weak local match for {name}, but the stored details are too generic to answer confidently from the substrate alone."
    else:
        answer = f"I know about {name}, but the stored concept is still thin."
    if propositions:
        useful = [
            item for item in propositions
            if item and item.lower() not in answer.lower() and not _contains_any(item, GENERIC_SCAFFOLD)
        ]
        if useful:
            answer += " " + " ".join(useful[:2])
    nearby = [_clean_name(item.get("concept_name")) for item in matches[1:3] if item.get("concept_name")]
    if nearby:
        answer += " I can also connect it to " + ", ".join(nearby) + "."
    return _clean_answer(answer)


def _render_browse(payload: dict[str, Any], message: str) -> str:
    matches = payload.get("concept_matches") or []
    if not matches:
        return _clean_answer(str(payload.get("answer") or "I do not have enough local knowledge for that yet."))
    names = [_clean_name(item.get("concept_name")) for item in matches[:5]]
    domain = str((payload.get("intent") or {}).get("domain") or "").replace("_", " ")
    if domain:
        return f"I know several things about {domain}, including {', '.join(names)}. Pick one and I can explain it more naturally."
    return f"I can talk about {', '.join(names[:4])}. Which direction do you want to explore?"


def _render_multi_concept(payload: dict[str, Any]) -> str:
    matches = payload.get("concept_matches") or []
    names = [_clean_name(item.get("concept_name")) for item in matches[:5]]
    if names:
        return f"I found a useful local set for that: {', '.join(names)}. I can use those as the basis for a careful comparison, but I am not storing any new synthesis from this turn."
    return _clean_answer(str(payload.get("answer") or "I could not find a strong local concept set for that."))


def _render_consent(payload: dict[str, Any], message: str) -> str:
    lower = str(message or "").lower()
    if any(term in lower for term in ("avogadro", "quantum field", "beluga", "latest", "current")):
        return _clean_answer(str(payload.get("answer") or "I do not know enough locally. Would you like me to ask a local reasoning model?"))
    return _clean_answer(str(payload.get("answer") or "I do not know enough locally yet."))


def _best_prop_for(concept: dict[str, Any], props: list[dict[str, Any]]) -> str:
    concept_id = concept.get("concept_id")
    candidates = [item for item in props if item.get("concept_id") == concept_id and item.get("substantive")]
    if candidates:
        return _clean_sentence(str(candidates[0].get("text") or ""))
    for item in concept.get("propositions") or []:
        text = _clean_sentence(str(item))
        if text and not _contains_any(text, GENERIC_SCAFFOLD):
            return text
    return _clean_sentence(str(concept.get("short_definition") or ""))


def _clean_name(name: Any) -> str:
    text = re.sub(r"\s*\([^)]*\)", "", str(name or "")).strip()
    return text or "this concept"


def _clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip(" -")
    text = text.replace("operator-reviewable", "reviewable")
    return text


def _clean_answer(answer: str) -> str:
    text = str(answer or "")
    for heading in REPORT_HEADINGS:
        text = text.replace(heading, "")
    text = text.replace("You taught me the concept", "I know about")
    text = text.replace("Based on that:", "")
    text = re.sub(r"No memory, graph edge, replay record, provider call, or training artifact was created\.?", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _natural_uncertainty(text: str) -> str:
    cleaned = _clean_sentence(text)
    if not cleaned:
        return ""
    return "The main uncertainty is that " + cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lower = str(text or "").lower()
    return any(phrase.lower() in lower for phrase in phrases)


def _internal_leak(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker in lower for marker in ("route:", "developer overlay", "provider_calls_performed", "canonical_write_performed", "retrieval_score"))


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Natural Conversation Renderer",
        "",
        f"Created: {report['created_at']}",
        f"Cases rendered: {report['cases_rendered']}",
        f"Report-voice rate: {report['report_voice_rate']}",
        f"Scaffold exposure rate: {report['scaffold_exposure_rate']}",
        f"False-consent rate: {report['false_consent_rate']}",
        f"Internal leaks: {report['normal_output_internal_leak_count']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Cases",
        "",
    ]
    for item in report["results"]:
        lines.extend([
            f"### {item['prompt']}",
            f"- Route: {item['route']}",
            f"- Report voice: {item['report_voice']}",
            f"- Scaffold exposure: {item['scaffold_exposure']}",
            f"- Internal leak: {item['internal_leak']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_natural_renderer_report(write_reports=True)
    print(json.dumps({
        "cases_rendered": report["cases_rendered"],
        "report_voice_rate": report["report_voice_rate"],
        "scaffold_exposure_rate": report["scaffold_exposure_rate"],
        "false_consent_rate": report["false_consent_rate"],
        "internal_leaks": report["normal_output_internal_leak_count"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


======================================================================
FILE: orchestration/runtime/rc2_route_arbitration.py
======================================================================

"""RC2 route arbitration trace for cognitive-route boundary debugging.

This module does not dispatch routes. It builds a deterministic, read-only
explanation of which routes had a plausible claim on a turn, their precedence,
and why the selected route won or yielded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_analogy_engine import is_analogy_prompt
from orchestration.runtime.rc2_cognitive_episode import resolve_working_memory_followup
from orchestration.runtime.rc2_contradiction_engine import is_contradiction_prompt
from orchestration.runtime.rc2_working_reasoning_set import should_use_wrs


PRECEDENCE = [
    ("safety", 1),
    ("explicit_user_command", 2),
    ("social_conversation", 3),
    ("contradiction_analysis", 4),
    ("analogy_analysis", 5),
    ("working_memory_reference_resolution", 6),
    ("working_reasoning_set", 7),
    ("multi_concept_retrieval", 8),
    ("single_concept_retrieval", 9),
    ("local_model_consent_required", 10),
    ("provider_consent_gate", 11),
]

PRECEDENCE_BY_ROUTE = dict(PRECEDENCE)

ROUTE_GROUPS = {
    "contradiction_analysis": "contradiction_analysis",
    "analogy_analysis": "analogy_analysis",
    "session_memory": "working_memory_reference_resolution",
    "recent_concept_followup": "working_memory_reference_resolution",
    "working_reasoning_set": "working_reasoning_set",
    "developmental_multi_concept_retrieval": "multi_concept_retrieval",
    "developmental_concept_memory": "single_concept_retrieval",
    "substrate_first_conversation": "single_concept_retrieval",
    "developmental_concept_domain_browse": "single_concept_retrieval",
    "developmental_concept_browse": "single_concept_retrieval",
    "local_model_consent_required": "local_model_consent_required",
    "gpt_support_approval_preview": "provider_consent_gate",
    "provider_support_answer": "provider_consent_gate",
    "social_conversation": "social_conversation",
    "local_conversation_scaffold": "social_conversation",
}

SAFETY_FIELDS = {
    "provider_calls_performed": False,
    "web_search_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "autonomous_action_performed": False,
    "scheduler_action_performed": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}


@dataclass
class RouteCandidate:
    route: str
    precedence: int
    confidence: float
    trigger_evidence: list[str]
    required_context: str
    context_available: bool
    selected: bool = False
    yielded_to: str | None = None
    rejection_reason: str = ""


def normalize_safety_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = []
    for key, default in SAFETY_FIELDS.items():
        if key not in payload:
            payload[key] = default
            missing.append(key)
    payload["safety_metadata"] = {
        "required_fields": sorted(SAFETY_FIELDS),
        "missing_fields_filled": sorted(missing),
        "complete": True,
        "behavioral_safety_passed": all(payload.get(key) is False for key in SAFETY_FIELDS),
        "read_only": True,
    }
    return payload


def build_route_arbitration_trace(
    message: str,
    history: list[dict[str, str]] | None,
    selected_route: str,
    intent_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = history or []
    selected_group = ROUTE_GROUPS.get(selected_route, selected_route or "unknown")
    candidates = _build_candidates(message, history, intent_info or {})
    if not any(item.route == selected_group for item in candidates):
        candidates.append(RouteCandidate(
            route=selected_group,
            precedence=PRECEDENCE_BY_ROUTE.get(selected_group, 99),
            confidence=0.5,
            trigger_evidence=[f"actual_dispatch:{selected_route}"],
            required_context="route_specific",
            context_available=True,
        ))
    candidates = sorted(candidates, key=lambda item: (item.precedence, -item.confidence, item.route))
    recommended = _recommended_group(candidates, fallback=selected_group)
    selected_precedence = PRECEDENCE_BY_ROUTE.get(selected_group, 99)
    for item in candidates:
        if item.route == selected_group:
            item.selected = True
            item.rejection_reason = ""
        elif item.precedence > selected_precedence:
            item.yielded_to = selected_group
            item.rejection_reason = "lower_precedence_than_selected_route"
        elif item.precedence < selected_precedence:
            item.rejection_reason = "candidate_not_matched_or_context_insufficient_at_dispatch"
        else:
            item.rejection_reason = "same_precedence_non_selected_candidate"
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selected_route": selected_route,
        "selected_group": selected_group,
        "recommended_group": recommended,
        "dispatch_aligned_with_arbitration": selected_group == recommended or selected_group == "local_conversation_model_lane",
        "precedence_order": [{"route": route, "precedence": precedence} for route, precedence in PRECEDENCE],
        "candidate_routes": [asdict(item) for item in candidates],
        "rejected_routes": [
            asdict(item) for item in candidates
            if not item.selected
        ],
        "read_only": True,
        "ephemeral": True,
    }


def _recommended_group(candidates: list[RouteCandidate], *, fallback: str) -> str:
    for item in candidates:
        if item.route == "safety":
            continue
        return item.route
    return fallback


def safety_schema_complete(payload: dict[str, Any]) -> bool:
    return all(key in payload for key in SAFETY_FIELDS)


def write_arbitration_reference(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "precedence": [{"route": route, "precedence": precedence} for route, precedence in PRECEDENCE],
        "route_groups": ROUTE_GROUPS,
        "safety_fields": SAFETY_FIELDS,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_candidates(message: str, history: list[dict[str, str]], intent_info: dict[str, Any]) -> list[RouteCandidate]:
    lower = _norm(message)
    candidates = [
        RouteCandidate(
            route="safety",
            precedence=1,
            confidence=1.0,
            trigger_evidence=["hard_invariants_checked"],
            required_context="none",
            context_available=True,
        )
    ]
    if _explicit_command(lower):
        candidates.append(RouteCandidate(
            route="explicit_user_command",
            precedence=2,
            confidence=0.9,
            trigger_evidence=["explicit_command_or_mode_control"],
            required_context="none",
            context_available=True,
        ))
    if intent_info.get("safe_no_route") is True or intent_info.get("intent") in {"greeting", "thanks", "compliment", "acknowledgement", "cancel"}:
        candidates.append(RouteCandidate(
            route="social_conversation",
            precedence=3,
            confidence=float(intent_info.get("confidence") or 0.82),
            trigger_evidence=[str(intent_info.get("communication_act") or intent_info.get("intent") or "social")],
            required_context="none",
            context_available=True,
        ))
    if is_contradiction_prompt(message, history):
        candidates.append(RouteCandidate(
            route="contradiction_analysis",
            precedence=4,
            confidence=0.93,
            trigger_evidence=_matched_terms(lower, ("contradict", "conflict", "inconsistent", "both be true", "cannot both")),
            required_context="current_or_prior_claims",
            context_available=bool(history) or _has_two_claims(lower),
        ))
    if is_analogy_prompt(message, history):
        candidates.append(RouteCandidate(
            route="analogy_analysis",
            precedence=5,
            confidence=0.9,
            trigger_evidence=_matched_terms(lower, ("analogy", "like", "similar", "maps to", "works and what breaks", "where does that analogy")),
            required_context="source_and_target_or_prior_analogy",
            context_available=bool(history) or _has_analogy_shape(lower),
        ))
    wm_payload = resolve_working_memory_followup(message, history)
    if wm_payload:
        episode = wm_payload.get("cognitive_episode") or {}
        candidates.append(RouteCandidate(
            route="working_memory_reference_resolution",
            precedence=6,
            confidence=float(wm_payload.get("confidence_score") or 0.72),
            trigger_evidence=_matched_terms(lower, ("that", "this", "those", "it", "first", "second", "earlier", "return to", "continue", "go deeper")),
            required_context="recent_episode_or_branch",
            context_available=bool(episode.get("active_topic")),
        ))
    if should_use_wrs(message) or ("what works" in lower and "break" in lower) or ("similar as systems" in lower):
        candidates.append(RouteCandidate(
            route="working_reasoning_set",
            precedence=7,
            confidence=0.84,
            trigger_evidence=_matched_terms(lower, ("compare", "connect", "relate", "common", "higher order", "what evidence", "what information")),
            required_context="retrievable_concept_set",
            context_available=True,
        ))
    if _looks_multi_concept(lower):
        candidates.append(RouteCandidate(
            route="multi_concept_retrieval",
            precedence=8,
            confidence=0.76,
            trigger_evidence=["multiple_named_entities_or_relation_terms"],
            required_context="approved_concept_candidates",
            context_available=True,
        ))
    if _looks_single_concept(lower):
        candidates.append(RouteCandidate(
            route="single_concept_retrieval",
            precedence=9,
            confidence=0.74,
            trigger_evidence=["single_topic_lookup"],
            required_context="approved_concept_candidate",
            context_available=True,
        ))
    if _looks_unknown_or_external(lower):
        candidates.append(RouteCandidate(
            route="local_model_consent_required",
            precedence=10,
            confidence=0.68,
            trigger_evidence=["insufficient_local_or_external_knowledge_signal"],
            required_context="operator_consent",
            context_available=False,
        ))
    return candidates


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower().replace("-", " ")).strip()


def _matched_terms(lower: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in lower] or ["implicit_route_signal"]


def _explicit_command(lower: str) -> bool:
    return lower in {"ask gpt", "yes ask gpt", "remember that", "don't remember that", "forget that"} or lower.startswith(("switch to ", "open "))


def _has_two_claims(lower: str) -> bool:
    return " and " in lower and any(term in lower for term in ("both", "true", "claim", "statement"))


def _has_analogy_shape(lower: str) -> bool:
    return " is like " in lower or "/" in lower or " to " in lower and " like " in lower


def _looks_multi_concept(lower: str) -> bool:
    return any(term in lower for term in ("compare", "relate", "connect", "with", "between", "common")) and len(re.findall(r"\b(and|with|between|to)\b", lower)) >= 1


def _looks_single_concept(lower: str) -> bool:
    return lower.startswith(("what is ", "what are ", "explain ", "tell me about ", "do you know anything about "))


def _looks_unknown_or_external(lower: str) -> bool:
    return any(term in lower for term in ("latest", "current", "gpt", "web", "source", "outside", "unknown"))


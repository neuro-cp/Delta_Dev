from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
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
from orchestration.runtime import gsr_a_governed_self_regulation as gsr  # noqa: E402
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
        self.last_local_model_exchange: dict[str, object] | None = None
        self.active_topic_anchor: dict[str, object] | None = None
        self.conversation_topic_state: dict[str, object] | None = None
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
        self.evaluation_tab = ttk.Frame(self.notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.conversation_tab, text="Conversation")
        self.notebook.add(self.database_tab, text="Database")
        self.notebook.add(self.rc3_tab, text="RC3")
        self.notebook.add(self.rc4_tab, text="RC4")
        self.notebook.add(self.rc5_tab, text="RC5")
        self.notebook.add(self.evaluation_tab, text="Evaluation")
        self.notebook.add(self.advanced_tab, text="Advanced / Operator Console")

        self._build_conversation_tab()
        self._build_database_tab()
        self._build_rc3_tab()
        self._build_rc4_tab()
        self._build_rc5_tab()
        self._build_evaluation_tab()
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

    def _build_evaluation_tab(self) -> None:
        top = ttk.Frame(self.evaluation_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="GSR Evaluation Review").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_evaluation_snapshot).pack(side=tk.RIGHT)

        self.evaluation_status = tk.StringVar(
            value="Read-only GSR-E3 review surface. No execution, application, persistence, or automatic continuation."
        )
        ttk.Label(self.evaluation_tab, textvariable=self.evaluation_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.evaluation_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.evaluation_items = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.evaluation_items.heading("status", text="Evaluation Stage")
        self.evaluation_items.column("status", width=320)
        self.evaluation_items.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.evaluation_items.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.evaluation_items.configure(yscrollcommand=scrollbar.set)
        self.evaluation_items.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_evaluation_item())

        controls = ttk.Frame(right)
        controls.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(controls, text="Accept", command=lambda: self._record_evaluation_disposition("accepted")).pack(side=tk.LEFT)
        ttk.Button(controls, text="Decline", command=lambda: self._record_evaluation_disposition("declined")).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Needs Modification", command=lambda: self._record_evaluation_disposition("needs_modification")).pack(side=tk.LEFT, padx=(6, 0))

        self.evaluation_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.evaluation_detail.pack(fill=tk.BOTH, expand=True)
        self.evaluation_detail.configure(state=tk.DISABLED)
        self.evaluation_snapshot: dict[str, dict[str, object]] = {}
        self.evaluation_review_items: list[dict[str, object]] = []
        self.evaluation_dispositions: list[dict[str, object]] = []
        self._refresh_evaluation_snapshot()

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

    def _refresh_evaluation_snapshot(self) -> None:
        self.evaluation_snapshot = self._build_evaluation_snapshot()
        for item in self.evaluation_items.get_children():
            self.evaluation_items.delete(item)
        for key, item in self.evaluation_snapshot.items():
            self.evaluation_items.insert("", tk.END, iid=key, values=(f"{item['title']} [{item['status']}]",))
        self.evaluation_status.set(
            "GSR/OAR review surface. Disposition controls record immutable operator intent only; no source application, execution, or continuation."
        )
        first_item = next(iter(self.evaluation_snapshot), "")
        if first_item:
            self.evaluation_items.selection_set(first_item)
            self._show_selected_evaluation_item()

    def _build_evaluation_snapshot(self) -> dict[str, dict[str, object]]:
        if self.evaluation_review_items:
            return {
                f"review-{index}": self._normalize_evaluation_review_item(index, item)
                for index, item in enumerate(self.evaluation_review_items, start=1)
            }
        return {
            "e3a": {
                "title": "GSR-E3-A Evidence Evaluation",
                "status": "accepted",
                "boundary": "E2-B bounded sandbox evidence -> deterministic evidence evaluation -> operator review required -> stop",
                "operator_action": "Review accepted evaluations outside the UI until a governed request queue is wired.",
                "guarantees": [
                    "Exact result and evidence identity validation.",
                    "Deterministic classification and bounded findings.",
                    "Cleanup, live-source, budget, output, artifact, and filesystem-write review.",
                    "No application authority, execution authority, lifecycle transition, or automatic continuation.",
                ],
            },
            "e3b": {
                "title": "GSR-E3-B Operator Evidence Disposition",
                "status": "accepted",
                "boundary": "exact E3-A evaluation + exact request + exact operator disposition -> one inert record -> consumed authority -> stop",
                "operator_action": "When a disposition request surfaces, operator and GPT review it manually before any later phase.",
                "guarantees": [
                    "Exact evaluation, request, disposition, cycle, plan, attempt, authorization, and digest binding.",
                    "One-shot operator authority with explicit-sequence expiration.",
                    "Immutable consumed replacement; original disposition remains unchanged.",
                    "Future execution, application consideration, and lifecycle closure remain metadata only.",
                ],
            },
            "queue": {
                "title": "Surfaced Requests",
                "status": "not wired",
                "boundary": "No live queue integration exists in this tab yet.",
                "operator_action": "Use this tab as a review landing page; do not treat it as approval or execution control.",
                "guarantees": [
                    "No provider or local-model call.",
                    "No sandbox or command execution.",
                    "No source mutation, memory write, persistence, scheduler, thread, or background task.",
                    "No staging, commit, push, merge, deployment, or publication.",
                ],
            },
        }

    def _set_evaluation_review_items(self, items: list[object]) -> None:
        self.evaluation_review_items = [
            asdict(item) if is_dataclass(item) else dict(item)
            for item in items
        ]
        self._refresh_evaluation_snapshot()

    def _selected_evaluation_review_item(self) -> tuple[str, dict[str, object]] | tuple[None, None]:
        selected = self.evaluation_items.selection()
        if not selected or not self.evaluation_snapshot:
            return None, None
        key = str(selected[0])
        item = self.evaluation_snapshot.get(key)
        if not item:
            return None, None
        details = item.get("details", item)
        if not isinstance(details, dict):
            return None, None
        return key, details

    def _oar_review_item_from_details(self, details: dict[str, object]) -> gsr.OperatorReviewItem | None:
        field_names = {field.name for field in fields(gsr.OperatorReviewItem)}
        payload = {key: value for key, value in details.items() if key in field_names}
        required = {
            "review_item_id",
            "parent_mission_id",
            "compiled_objective_id",
            "capability_gap_id",
            "proposal_id",
            "proposal_version",
            "artifact_chain_digest",
        }
        if not required.issubset(payload):
            return None
        return gsr.OperatorReviewItem(**payload)

    def _record_evaluation_disposition(self, disposition: str) -> None:
        _key, details = self._selected_evaluation_review_item()
        if details is None:
            self.evaluation_status.set("No evaluation item selected.")
            return
        item = self._oar_review_item_from_details(details)
        if item is None:
            self.evaluation_status.set("Selected item is display-only and cannot receive an OAR disposition.")
            return
        existing_ids = {
            str(record.get("review_item_id"))
            for record in self.evaluation_dispositions
            if bool(record.get("terminal"))
        }
        if item.review_item_id in existing_ids:
            self.evaluation_status.set(f"Disposition denied for {item.review_item_id}: duplicate terminal disposition.")
            return
        reason = "operator_comment" if disposition == "accepted" else ("insufficient_evidence" if disposition == "declined" else "needs_narrower_scope")
        sequence = len(self.evaluation_dispositions) + 1
        request = gsr.make_operator_proposal_disposition_request(
            item,
            requested_disposition=disposition,
            reason_code=reason,
            operator_comment=f"Tk operator selected {disposition}.",
            ui_action_id=f"tk-evaluation-{disposition}-{sequence}",
            sequence=sequence,
        )
        authorization = gsr.make_operator_proposal_disposition_authorization(
            request,
            operator_identity="tk_operator",
            issued_sequence=sequence,
        )
        previous = tuple(
            gsr.OperatorProposalDisposition(**{
                key: value
                for key, value in record.items()
                if key in {field.name for field in fields(gsr.OperatorProposalDisposition)}
            })
            for record in self.evaluation_dispositions
            if record.get("review_item_id") == item.review_item_id
        )
        result = gsr.apply_operator_proposal_disposition(item, request, authorization, previous, sequence=sequence)
        if not result.accepted or result.disposition is None:
            self.evaluation_status.set(f"Disposition denied for {item.review_item_id}: {result.reason}.")
            return
        record = asdict(result.disposition)
        self.evaluation_dispositions.append(record)
        self.evaluation_status.set(
            f"Recorded {disposition} for {item.proposal_id}. No source application, execution, activation, or continuation was performed."
        )
        self._show_selected_evaluation_item()

    def _normalize_evaluation_review_item(self, index: int, item: dict[str, object]) -> dict[str, object]:
        item_type = str(item.get("item_type") or item.get("type") or "evaluation_item")
        title = str(item.get("title") or item.get("evaluation_id") or item.get("record_id") or f"Review item {index}")
        status = str(item.get("status") or item.get("classification") or item.get("operator_disposition") or "available")
        details = item.get("details", item)
        return {
            "title": title,
            "status": status,
            "boundary": str(item.get("boundary") or f"Read-only {item_type} display."),
            "operator_action": str(item.get("operator_action") or "Review manually; this tab provides no approval or execution control."),
            "details": details,
            "guarantees": [
                "Display-only rendering from an in-memory review item.",
                "No evaluation, disposition, execution request, authorization, lifecycle transition, or continuation is created.",
                "No file, memory, persistence, provider, model, scheduler, thread, or process side effect is started by this display path.",
            ],
        }

    def _show_selected_evaluation_item(self) -> None:
        selected = self.evaluation_items.selection()
        if not selected or not self.evaluation_snapshot:
            return
        item = self.evaluation_snapshot.get(str(selected[0]), {})
        lines = [
            str(item.get("title", "")),
            "",
            f"Status: {item.get('status', '')}",
            f"Boundary: {item.get('boundary', '')}",
            "",
            "Operator handling:",
            str(item.get("operator_action", "")),
            "",
            "Guarantees:",
        ]
        lines.extend(f"- {value}" for value in item.get("guarantees", []))
        if "details" in item:
            lines.extend(["", "Details:", json.dumps(item["details"], indent=2, sort_keys=True, default=str)])
        self._write_evaluation_detail("\n".join(lines))

    def _write_evaluation_detail(self, text: str) -> None:
        self.evaluation_detail.configure(state=tk.NORMAL)
        self.evaluation_detail.delete("1.0", tk.END)
        if text:
            self.evaluation_detail.insert(tk.END, text)
        self.evaluation_detail.configure(state=tk.DISABLED)

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
        if self.conversation_topic_state:
            history = [*history, {"role": "topic_state", "content": json.dumps(self.conversation_topic_state, sort_keys=True)}]
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
                    self._update_active_topic_anchor(payload)
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
        if self._is_local_model_response_query(lower):
            reply = self._last_local_model_response_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
                return
        if self._is_discourse_history_query(lower):
            reply = self._discourse_history_answer()
            if reply:
                self._append_session("user", message)
                self._append_chat("DELTA", reply)
                self._append_session("assistant", reply)
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
            self._remember_local_model_exchange(target, payload)
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

    def _remember_local_model_exchange(self, question: str, payload: dict[str, object]) -> None:
        result = payload.get("local_model_result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            self.last_local_model_exchange = {
                "question": question,
                "status": "unavailable",
                "answer": "",
                "reason": "no_local_model_result",
            }
            return
        if result.get("executed"):
            self.last_local_model_exchange = {
                "question": question,
                "status": "completed",
                "answer": str(result.get("answer") or payload.get("answer") or ""),
                "model_id": result.get("model_id"),
                "provider_calls_performed": bool(result.get("provider_calls_performed", False)),
            }
            return
        self.last_local_model_exchange = {
            "question": question,
            "status": "unavailable",
            "answer": "",
            "reason": result.get("reason") or "local_model_not_completed",
        }

    def _is_local_model_response_query(self, lower: str) -> bool:
        normalized = " ".join(str(lower or "").lower().strip().split()).strip(" ?!.")
        return normalized in {
            "what was the response",
            "what was its response",
            "what did it say",
            "what did the model say",
            "what did the local model say",
            "show me the response",
            "show me the local model response",
        }

    def _last_local_model_response_answer(self) -> str:
        exchange = self.last_local_model_exchange
        if not isinstance(exchange, dict):
            return ""
        question = str(exchange.get("question") or "the previous request")
        if exchange.get("status") == "completed" and str(exchange.get("answer") or "").strip():
            return f"The local model response for `{question}` was:\n\n{str(exchange.get('answer')).strip()}"
        return f"I do not have a completed local-model response for `{question}` yet."

    def _is_discourse_history_query(self, lower: str) -> bool:
        normalized = " ".join(str(lower or "").lower().strip().split()).strip(" ?!.")
        return normalized in {
            "what were we discussing before that",
            "what were we talking about before that",
            "what was the topic before that",
            "what were we discussing",
            "what were we talking about",
        }

    def _discourse_history_answer(self) -> str:
        topic = ""
        if isinstance(self.conversation_topic_state, dict):
            topic = str(self.conversation_topic_state.get("topic") or "").strip()
        if not topic:
            for item in reversed(self.session_history):
                if item.get("role") != "topic_state":
                    continue
                try:
                    state = json.loads(str(item.get("content") or "{}"))
                except json.JSONDecodeError:
                    continue
                topic = str(state.get("topic") or "").strip()
                if topic:
                    break
        if not topic:
            exchange = self._last_substantive_exchange()
            topic = str((exchange or {}).get("question") or "").strip()
        if not topic:
            return ""
        return f"Before that, we were discussing {topic}."

    def _update_active_topic_anchor(self, payload: dict[str, object]) -> None:
        topic_state = payload.get("conversation_topic_state")
        if isinstance(topic_state, dict):
            state_kind = str(topic_state.get("state_kind") or "")
            topic = str(topic_state.get("topic") or "").strip()
            if state_kind in {"SUBSTANTIVE_TOPIC", "TOPIC_SWITCH", "FOLLOWUP"} and topic:
                self.conversation_topic_state = dict(topic_state)
                if topic_state.get("supersedes_anchor"):
                    self.active_topic_anchor = None
                return
            if state_kind == "SOCIAL_INTERLUDE":
                return
            if state_kind == "CONCEPT_ANCHOR" and topic:
                self.conversation_topic_state = dict(topic_state)
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

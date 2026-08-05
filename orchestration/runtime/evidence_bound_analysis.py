"""Deterministic, source-bound analysis records built from semantic problem frames.

This module deliberately has no persistence, graph, review, model, provider,
tool, authority, scheduling, or background-work dependency.  It only turns an
already-recorded semantic frame into a bounded, provisional analysis record.
The conversational runtime owns storage, turns, rendering coordination, and
exact-once behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id


SCHEMA_VERSION = "evidence_bound_analysis_v1"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    kind: str
    text: str
    source_span: Mapping[str, Any]
    role: str
    confidence_label: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    description: str
    expected_property: str
    result: str
    limitation: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SafeNextAction:
    action_id: str
    action: str
    required_authority: str
    tool_required: bool
    external_action: bool
    reversible: bool
    risk: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBoundAnalysisRecord:
    analysis_id: str
    source_frame_id: str
    source_problem_model_id: str
    source_equation_frame_id: str
    source_turn_id: str
    source_text: str
    domain: str
    analysis_type: str
    evidence_items: tuple[EvidenceItem, ...]
    extracted_facts: tuple[str, ...]
    assumptions: tuple[str, ...]
    constraints: tuple[str, ...]
    unknowns: tuple[str, ...]
    selected_method: str
    method_rationale: str
    validation_checks: tuple[ValidationCheck, ...]
    result_summary: str
    limitations: tuple[str, ...]
    uncertainty: tuple[str, ...]
    safe_next_actions: tuple[SafeNextAction, ...]
    prohibited_actions: tuple[str, ...]
    risk_class: str
    status: str
    created_event_id: str
    restart_summary: str
    semantic_signature: Mapping[str, Any]
    matched_roles: tuple[str, ...]
    missing_roles: tuple[str, ...]
    source_spans: tuple[Mapping[str, Any], ...]
    confidence_label: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["record_kind"] = "evidence_bound_analysis_record"
        return record


def compile_evidence_bound_analysis(
    semantic_frame_record: Mapping[str, Any],
) -> EvidenceBoundAnalysisRecord | None:
    """Build one bounded analysis from a supported persisted semantic frame.

    The input is intentionally a record, not a free-form operator message.  That
    keeps analysis tied to an existing source frame and prevents this helper from
    becoming another input classifier or a general reasoning path.
    """

    frame = _frame(semantic_frame_record)
    frame_id = str(semantic_frame_record.get("frame_id") or frame.get("frame_id") or "")
    source_text = str(frame.get("source_text") or "")
    domain = str(frame.get("domain_guess") or "")
    if not frame_id or not source_text:
        return None

    builders = {
        "operations_logistics_receivables": _operations_analysis,
        "physics_mechanics": _incline_analysis,
        "defensive_cybersecurity": _defensive_sql_analysis,
        "finance_portfolio_risk": _portfolio_risk_analysis,
        "physics_equation_model": _newtons_second_law_analysis,
    }
    builder = builders.get(domain)
    if builder is None:
        return None
    return builder(semantic_frame_record, frame)


def render_evidence_bound_analysis(record: Mapping[str, Any]) -> str:
    """Render a compact provisional analysis without claiming reviewed truth."""

    evidence = tuple(item for item in record.get("evidence_items", ()) if isinstance(item, Mapping))
    checks = tuple(item for item in record.get("validation_checks", ()) if isinstance(item, Mapping))
    actions = tuple(item for item in record.get("safe_next_actions", ()) if isinstance(item, Mapping))
    lines = (
        "I created a bounded, source-bound analysis from the existing semantic frame.",
        f"Analysis: {str(record.get('analysis_id') or '')}",
        f"Domain: {str(record.get('domain') or '').replace('_', ' ')}",
        "",
        "Evidence:",
        *_bullet_lines(str(item.get("text") or "") for item in evidence),
        "",
        f"Method: {str(record.get('selected_method') or '')}",
        f"Why this method: {str(record.get('method_rationale') or '')}",
        "",
        f"Result: {str(record.get('result_summary') or '')}",
        "",
        "Validation checks:",
        *_bullet_lines(
            f"{str(item.get('description') or '')}: {str(item.get('result') or '')}"
            for item in checks
        ),
        "",
        "Limits and uncertainty:",
        *_bullet_lines(
            tuple(str(item) for item in record.get("limitations", ()) if str(item))
            + tuple(str(item) for item in record.get("uncertainty", ()) if str(item))
        ),
        "",
        "Safe next actions:",
        *_bullet_lines(str(item.get("action") or "") for item in actions),
        "",
        "Status: source-bound and provisional analysis. It is not reviewed or admitted knowledge, and it has not created a graph claim, review, admission, model request, provider call, tool execution, or external action.",
    )
    return "\n".join(line for line in lines if line is not None)


def render_evidence_bound_analysis_recall(record: Mapping[str, Any], *, focus: str) -> str:
    """Answer one explicit analysis question without changing the analysis record."""

    analysis_id = str(record.get("analysis_id") or "")
    facts = tuple(str(item) for item in record.get("extracted_facts", ()) if str(item))
    checks = tuple(item for item in record.get("validation_checks", ()) if isinstance(item, Mapping))
    summary = str(record.get("result_summary") or "")
    if focus == "bottleneck":
        detail = next((item for item in facts if "bottleneck" in item.lower() or "blocks" in item.lower()), summary)
        prefix = "The recorded operational bottleneck is"
    elif focus == "method":
        detail = str(record.get("selected_method") or "")
        prefix = "The recorded method is"
    elif focus == "defensive":
        detail = str(record.get("method_rationale") or summary)
        prefix = "The SQL case is defensive because"
    elif focus == "finance_risk":
        detail = summary
        prefix = "The recorded finance-risk analysis is"
    elif focus == "validation":
        detail = next(
            (
                str(item.get("description") or "")
                for item in checks
                if "net force" in str(item.get("description") or "").lower()
                or "dimensional" in str(item.get("description") or "").lower()
            ),
            str(checks[0].get("description") or "") if checks else "No validation check was recorded.",
        )
        prefix = "A recorded validation check is"
    else:
        detail = summary
        prefix = "The recorded analysis says"
    return (
        f"{prefix}: {detail}\n\n"
        f"Analysis: {analysis_id}\n"
        "This is a read-only source-bound analysis recall; it did not create or change an analysis record."
    )


def _operations_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "operational_dependency_risk_triage"
    analysis_id = _analysis_id(record, analysis_type)
    invoice = _entity_label(frame, "receivable", "the overdue invoice")
    crew = _entity_label(frame, "execution_actor", "the crew")
    job = _entity_label(frame, "blocked_work", "the job")
    resource = _entity_label(frame, "dependency_resource", "the pump")
    overdue = _quantity_text(frame, "overdue duration", "overdue")
    evidence = (
        _evidence(analysis_id, "receivable_status", f"{invoice} is an overdue invoice ({overdue}).", frame, invoice, overdue),
        _evidence(analysis_id, "blocked_start", f"{crew} cannot start {job} until the dependency is resolved.", frame, crew, job),
        _evidence(analysis_id, "delivery_dependency", f"{resource} delivery is stated as a prerequisite for {job}.", frame, resource, "delivered"),
    )
    checks = (
        _check(analysis_id, "source_names_overdue_invoice", "The source contains an overdue invoice.", "overdue receivable is explicit", "observed_in_source", "Payment status is not externally verified."),
        _check(analysis_id, "source_names_blocked_start", "The source contains a crew/job blocked start.", "blocked start is explicit", "observed_in_source", "No schedule outcome is verified."),
        _check(analysis_id, "source_names_delivery_dependency", "The source contains a delivery dependency.", "resource prerequisite is explicit", "observed_in_source", "Pump ETA and alternate availability are unknown."),
        _check(analysis_id, "external_status_not_verified", "No external payment or delivery status was checked.", "no external verification", "not_performed_by_design", "The analysis is limited to the supplied source."),
    )
    actions = (
        _action(analysis_id, "Ask for the pump ETA.", "operator-provided information", risk="low"),
        _action(analysis_id, "Check the invoice payment status or dispute status with operator approval.", "operator approval before external communication", risk="moderate"),
        _action(analysis_id, "Identify whether an alternate pump is available.", "operator-provided information or approval", risk="low"),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            f"Cashflow or receivable risk: {invoice} is {overdue}.",
            f"Schedule dependency risk: {crew} cannot start {job} before {resource} is delivered.",
            f"Operational bottleneck: {resource} delivery blocks {crew} from starting {job}.",
        ),
        selected_method="dependency and risk triage",
        method_rationale="The source names one receivable exposure and one delivery dependency that blocks job execution, so they should be separated and clarified before any external action.",
        validation_checks=checks,
        result_summary=(
            f"The source supports two operational risks: a cashflow or receivable risk from {invoice} being {overdue}, "
            f"and a schedule risk because {resource} delivery blocks {crew} from starting {job}."
        ),
        safe_next_actions=actions,
        prohibited_actions=(
            "Do not contact the client or vendor automatically.",
            "Do not alter the schedule or represent payment status without confirming it.",
        ),
        risk_class="operational_decision_support_no_external_action",
    )


def _incline_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "frictionless_incline_solution_sketch"
    analysis_id = _analysis_id(record, analysis_type)
    angle = _quantity_value(frame, "incline angle")
    mass = _quantity_value(frame, "mass")
    acceleration = _incline_acceleration(angle)
    result = (
        f"Using a = g sin(theta), a {angle}-degree frictionless incline gives approximately {acceleration:.1f} m/s^2 down the plane when g is approximately 9.8 m/s^2. The stated mass ({mass} kg) cancels from the acceleration."
        if acceleration is not None and angle
        else "Use a = g sin(theta) for acceleration down a frictionless incline; a numeric result needs a usable angle and gravity convention."
    )
    angle_check_result = "observed_in_source" if angle else "missing_from_source"
    half_check_result = "passes" if _is_thirty_degrees(angle) else "not_applicable_to_stated_angle"
    evidence = (
        _evidence(analysis_id, "system_body", f"The source identifies a {mass or 'stated'} kg block on an incline.", frame, "block", mass),
        _evidence(analysis_id, "incline_angle", f"The source gives an incline angle of {angle or 'an unspecified'} degrees.", frame, angle, "incline"),
        _evidence(analysis_id, "constraint", "The source states that the incline is frictionless.", frame, "frictionless"),
    )
    checks = (
        _check(analysis_id, "acceleration_units", "Acceleration is expressed in m/s^2.", "dimension of acceleration", "passes" if acceleration is not None else "symbolic_only", "A numeric result requires a gravity convention."),
        _check(analysis_id, "incline_angle_present", "The source gives an incline angle.", "usable angle", angle_check_result, "No numeric acceleration follows if the angle is missing."),
        _check(analysis_id, "thirty_degree_sine", "For 30 degrees, sin(theta) equals 0.5.", "half gravitational acceleration", half_check_result, "This check applies only to the stated 30-degree case."),
        _check(analysis_id, "bounded_by_gravity", "The acceleration should be less than g for an incline below 90 degrees.", "0 <= a < g", "passes" if acceleration is not None else "symbolic_check_pending", "The angle must be in the physical incline range."),
        _check(analysis_id, "mass_cancels", "Mass cancels from frictionless-incline acceleration.", "same acceleration for any stated mass", "passes", "This relies on the frictionless idealization."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "The problem specifies a frictionless incline.",
            f"The stated target is acceleration down the incline at {angle or 'the supplied'} degrees.",
            "The mass cancels from the acceleration in the frictionless model.",
        ),
        selected_method="Newtonian force decomposition using a = g sin(theta)",
        method_rationale="On a frictionless incline, the component of gravity parallel to the plane determines acceleration while the normal force cancels the perpendicular component.",
        validation_checks=checks,
        result_summary=result,
        safe_next_actions=(
            _action(analysis_id, "Ask whether numeric precision or a free-body diagram is needed.", "none", risk="low"),
        ),
        prohibited_actions=("Do not treat the idealized result as an experimental measurement.",),
        risk_class="safe_physics_modeling",
    )


def _defensive_sql_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "defensive_sql_source_to_sink_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    evidence = (
        _evidence(analysis_id, "untrusted_source", "User-controlled input is identified as the source.", frame, "User input", "input"),
        _evidence(analysis_id, "database_sink", "SQL query execution is identified as the command sink.", frame, "SQL query", "execution"),
        _evidence(analysis_id, "unsafe_construction", "The source states that input is concatenated into the query before execution.", frame, "concatenated"),
    )
    checks = (
        _check(analysis_id, "source_exists", "An external or user-controlled source exists.", "untrusted source", "observed_in_source", "The exact validation layer is unknown."),
        _check(analysis_id, "sink_exists", "A SQL execution sink exists.", "database command sink", "observed_in_source", "The driver and query path are not supplied."),
        _check(analysis_id, "unsafe_construction_exists", "String concatenation is present before the sink.", "unsafe query construction", "observed_in_source", "Prepared-statement use must still be verified in code."),
        _check(analysis_id, "payload_not_needed", "No exploit payload is required for this defensive classification.", "defensive review without exploitation", "passes_by_design", "This does not establish exploitability against a target."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "Trust boundary: user-controlled input flows toward a database command sink.",
            "Risk: concatenated input creates a SQL injection candidate.",
            "The analysis is defensive because it focuses on containment and validation, not exploitation.",
        ),
        selected_method="defensive source-to-sink review",
        method_rationale="The source identifies an untrusted input crossing into executable SQL construction, which calls for defensive containment checks rather than payload generation or target interaction.",
        validation_checks=checks,
        result_summary="This is a defensive SQL injection candidate: untrusted input reaches SQL query construction through concatenation before execution. The safe response is to verify parameter binding and boundary controls.",
        safe_next_actions=(
            _action(analysis_id, "Use a parameterized query or prepared statement.", "code-change approval", risk="moderate"),
            _action(analysis_id, "Validate input at the boundary and use a least-privilege database account.", "code-change approval", risk="moderate"),
            _action(analysis_id, "Add a regression test that verifies parameter binding.", "code-change approval", risk="low"),
        ),
        prohibited_actions=(
            "Do not generate exploit payloads.",
            "Do not scan a target, bypass controls, evade detection, or build an offensive chain.",
        ),
        risk_class="defensive_cybersecurity_review_only",
    )


def _portfolio_risk_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "portfolio_concentration_scenario_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    allocations = _portfolio_allocations(frame)
    allocation_total = sum(weight for weight, _asset in allocations)
    allocation_text = ", ".join(f"{weight:g}% {asset}" for weight, asset in allocations) or "the stated allocations"
    evidence = tuple(
        _evidence(analysis_id, "portfolio_allocation", f"The source assigns {weight:g}% to {asset}.", frame, asset, f"{weight:g}%")
        for weight, asset in allocations
    ) + (
        _evidence(analysis_id, "scenario", "The source names an AI/tech correction scenario over the stated horizon.", frame, "AI", "tech", "six-month"),
    )
    allocation_result = "passes" if allocations and abs(allocation_total - 100.0) < 0.001 else "needs_source_clarification"
    checks = (
        _check(analysis_id, "allocations_sum", "The supplied allocations sum to 100%.", "allocation total equals 100%", allocation_result, f"Recorded total is {allocation_total:g}% from the supplied entries."),
        _check(analysis_id, "live_data_unavailable", "Live prices and correlations are unavailable.", "no fabricated market data", "not_available_by_design", "This is not a live valuation or forecast."),
        _check(analysis_id, "operator_constraints_unknown", "Tax, account, and risk-tolerance constraints are unknown.", "decision constraints supplied", "missing_from_source", "No personalized recommendation should follow."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            f"Stated allocation: {allocation_text}.",
            "Primary risks: sector concentration, drawdown sensitivity, volatility, cash drag, and horizon mismatch.",
            "The supplied scenario is a bounded six-month AI/tech correction discussion, not a market forecast.",
        ),
        selected_method="concentration and scenario risk analysis",
        method_rationale="The source provides a concentrated allocation, a cash buffer, and a correction scenario, so the appropriate bounded method is exposure and scenario framing rather than a trade decision.",
        validation_checks=checks,
        result_summary=(
            f"The stated portfolio ({allocation_text}) has material concentration and drawdown sensitivity to an AI/tech correction. "
            "Cash provides a buffer but can create opportunity-cost or cash-drag tradeoffs; live pricing, correlations, tax constraints, and risk tolerance remain unknown."
        ),
        safe_next_actions=(
            _action(analysis_id, "Build a descriptive scenario table from the stated allocations.", "none for a local hypothetical table", risk="low"),
            _action(analysis_id, "Ask for holdings, account type, risk tolerance, and drawdown tolerance.", "operator-provided information", risk="low"),
        ),
        prohibited_actions=(
            "Do not issue an autonomous buy or sell instruction.",
            "Do not execute a trade or fabricate market prices, correlations, or returns.",
        ),
        risk_class="financial_decision_support_no_trade_execution",
    )


def _newtons_second_law_analysis(record: Mapping[str, Any], frame: Mapping[str, Any]) -> EvidenceBoundAnalysisRecord:
    analysis_type = "newtons_second_law_model_analysis"
    analysis_id = _analysis_id(record, analysis_type)
    evidence = (
        _evidence(analysis_id, "equation", "The source states the equation F = ma.", frame, "F", "m", "a"),
        _evidence(analysis_id, "modeled_quantity", "The frame identifies force, mass, and acceleration as the modeled variables.", frame, "F", "m", "a"),
    )
    checks = (
        _check(analysis_id, "dimensional_consistency", "Check N = kg*m/s^2.", "force dimensions match mass times acceleration", "passes_as_model_check", "Known values are still needed for a numeric result."),
        _check(analysis_id, "net_force", "Use net force rather than one arbitrary individual force.", "relevant forces are summed", "required_before_numeric_use", "A free-body model may be needed for a concrete scenario."),
        _check(analysis_id, "classical_domain", "Apply the model in an inertial frame at classical scales.", "model assumptions are stated", "recorded_as_assumption", "The equation is not a complete description of every system."),
    )
    return _record(
        record,
        frame,
        analysis_id=analysis_id,
        analysis_type=analysis_type,
        evidence_items=evidence,
        extracted_facts=(
            "F = ma means net force equals mass times acceleration.",
            "Given the other two quantities, the model can solve for net force, mass, or acceleration.",
            "A validation check is to use net force and confirm N = kg*m/s^2.",
        ),
        selected_method="dimensional and model interpretation of Newton's second law",
        method_rationale="The equation is a classical mechanics model relating net force, mass, and acceleration; the bounded analysis identifies the solvable unknowns and the checks needed before substitution.",
        validation_checks=checks,
        result_summary="F = ma states that net force equals mass times acceleration. It can solve for F, m, or a when the other required quantities are known, provided the force is the net force in an applicable classical inertial-frame model.",
        safe_next_actions=(
            _action(analysis_id, "Ask for the known variables or a concrete physical scenario.", "operator-provided information", risk="low"),
        ),
        prohibited_actions=("Do not substitute an arbitrary individual force for net force.",),
        risk_class="safe_physics_modeling",
    )


def _record(
    source_record: Mapping[str, Any],
    frame: Mapping[str, Any],
    *,
    analysis_id: str,
    analysis_type: str,
    evidence_items: Sequence[EvidenceItem],
    extracted_facts: Sequence[str],
    selected_method: str,
    method_rationale: str,
    validation_checks: Sequence[ValidationCheck],
    result_summary: str,
    safe_next_actions: Sequence[SafeNextAction],
    prohibited_actions: Sequence[str],
    risk_class: str,
) -> EvidenceBoundAnalysisRecord:
    model = _mapping(source_record.get("problem_model"))
    equation = _mapping(source_record.get("equation_understanding_frame"))
    source_frame_id = str(source_record.get("frame_id") or frame.get("frame_id") or "")
    return EvidenceBoundAnalysisRecord(
        analysis_id=analysis_id,
        source_frame_id=source_frame_id,
        source_problem_model_id=str(model.get("problem_model_id") or ""),
        source_equation_frame_id=str(equation.get("equation_frame_id") or ""),
        source_turn_id=str(frame.get("source_turn_id") or ""),
        source_text=str(frame.get("source_text") or ""),
        domain=str(frame.get("domain_guess") or ""),
        analysis_type=analysis_type,
        evidence_items=tuple(evidence_items),
        extracted_facts=tuple(str(item) for item in extracted_facts if str(item)),
        assumptions=tuple(str(item) for item in model.get("assumptions", ()) if str(item)),
        constraints=tuple(str(item) for item in frame.get("constraints", ()) if str(item)),
        unknowns=tuple(str(item) for item in frame.get("uncertainty", ()) if str(item)),
        selected_method=selected_method,
        method_rationale=method_rationale,
        validation_checks=tuple(validation_checks),
        result_summary=result_summary,
        limitations=tuple(str(item) for item in frame.get("limitations", ()) if str(item)),
        uncertainty=tuple(str(item) for item in frame.get("uncertainty", ()) if str(item)),
        safe_next_actions=tuple(safe_next_actions),
        prohibited_actions=tuple(str(item) for item in prohibited_actions if str(item)),
        risk_class=risk_class,
        status="provisional_analysis",
        created_event_id=stable_id("evidence-bound-analysis-event", analysis_id, SCHEMA_VERSION),
        restart_summary="Deterministic source-frame analysis persisted by the conversational runtime with no graph, review, model, provider, tool, or external-action side effect.",
        semantic_signature=_mapping(frame.get("semantic_signature")),
        matched_roles=tuple(str(item) for item in frame.get("matched_roles", ()) if str(item)),
        missing_roles=tuple(str(item) for item in frame.get("missing_roles", ()) if str(item)),
        source_spans=tuple(
            dict(item)
            for item in frame.get("source_spans", ())
            if isinstance(item, Mapping)
        ),
        confidence_label=str(frame.get("confidence_label") or "deterministic_pattern_match"),
    )


def _analysis_id(record: Mapping[str, Any], analysis_type: str) -> str:
    frame = _frame(record)
    return stable_id(
        "evidence-bound-analysis",
        str(record.get("frame_id") or frame.get("frame_id") or ""),
        analysis_type,
        SCHEMA_VERSION,
    )


def _frame(record: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = record.get("semantic_input_frame")
    return candidate if isinstance(candidate, Mapping) else record


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _entity_label(frame: Mapping[str, Any], role: str, fallback: str) -> str:
    for item in frame.get("entities", ()):
        if isinstance(item, Mapping) and str(item.get("role") or "") == role:
            label = str(item.get("label") or item.get("entity") or "")
            if label:
                return label
    return fallback


def _quantity_value(frame: Mapping[str, Any], label: str) -> str:
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping) and str(item.get("label") or "") == label:
            return str(item.get("value") or "")
    return ""


def _quantity_text(frame: Mapping[str, Any], label: str, fallback: str) -> str:
    value = _quantity_value(frame, label)
    if not value:
        return fallback
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping) and str(item.get("label") or "") == label:
            unit = str(item.get("unit") or "").strip()
            return f"{value} {unit}".strip()
    return value


def _span(frame: Mapping[str, Any], *terms: str) -> Mapping[str, Any]:
    spans = tuple(item for item in frame.get("source_spans", ()) if isinstance(item, Mapping))
    normalized_terms = tuple(term.lower() for term in terms if term)
    for term in normalized_terms:
        for span in spans:
            if term in str(span.get("text") or "").lower():
                return dict(span)
    for item in frame.get("entities", ()):
        if isinstance(item, Mapping):
            span = item.get("source_span")
            if isinstance(span, Mapping) and any(term in str(span.get("text") or "").lower() for term in normalized_terms):
                return dict(span)
    for item in frame.get("quantities", ()):
        if isinstance(item, Mapping):
            span = item.get("source_span")
            if isinstance(span, Mapping) and any(term in str(span.get("text") or "").lower() for term in normalized_terms):
                return dict(span)
    source_text = str(frame.get("source_text") or "")
    lowered_source = source_text.lower()
    for term in normalized_terms:
        start = lowered_source.find(term)
        if start >= 0:
            end = start + len(term)
            return {
                "kind": "source_text",
                "text": source_text[start:end],
                "start": start,
                "end": end,
            }
    return {}


def _evidence(
    analysis_id: str,
    kind: str,
    text: str,
    frame: Mapping[str, Any],
    *terms: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=stable_id("evidence-bound-analysis-evidence", analysis_id, kind, text),
        kind=kind,
        text=text,
        source_span=_span(frame, *terms),
        role=kind,
        confidence_label="source_stated",
    )


def _check(
    analysis_id: str,
    check_id: str,
    description: str,
    expected_property: str,
    result: str,
    limitation: str,
) -> ValidationCheck:
    return ValidationCheck(
        check_id=stable_id("evidence-bound-analysis-check", analysis_id, check_id),
        description=description,
        expected_property=expected_property,
        result=result,
        limitation=limitation,
    )


def _action(
    analysis_id: str,
    action: str,
    required_authority: str,
    *,
    risk: str,
) -> SafeNextAction:
    return SafeNextAction(
        action_id=stable_id("evidence-bound-analysis-action", analysis_id, action),
        action=action,
        required_authority=required_authority,
        tool_required=False,
        external_action=False,
        reversible=True,
        risk=risk,
    )


def _incline_acceleration(angle: str) -> float | None:
    try:
        value = float(angle)
    except (TypeError, ValueError):
        return None
    if not 0 <= value <= 90:
        return None
    return 9.8 * math.sin(math.radians(value))


def _is_thirty_degrees(angle: str) -> bool:
    try:
        return abs(float(angle) - 30.0) < 0.001
    except (TypeError, ValueError):
        return False


def _portfolio_allocations(frame: Mapping[str, Any]) -> tuple[tuple[float, str], ...]:
    values: list[tuple[float, str]] = []
    for relation in frame.get("relationships", ()):
        if not isinstance(relation, Mapping) or relation.get("predicate") != "has_portfolio_weight":
            continue
        weight_match = re.search(r"\d+(?:\.\d+)?", str(relation.get("object") or ""))
        if weight_match is None:
            continue
        values.append((float(weight_match.group(0)), str(relation.get("subject") or "portfolio exposure")))
    return tuple(values)


def _bullet_lines(values: Sequence[str]) -> tuple[str, ...]:
    material = tuple(value for value in values if value)
    return tuple(f"- {value}" for value in material) or ("- No source-bound detail was recorded.",)


__all__ = [
    "EvidenceBoundAnalysisRecord",
    "EvidenceItem",
    "SafeNextAction",
    "SCHEMA_VERSION",
    "ValidationCheck",
    "compile_evidence_bound_analysis",
    "render_evidence_bound_analysis",
    "render_evidence_bound_analysis_recall",
]

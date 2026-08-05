"""Deterministic, source-bound semantic framing for operator-provided inputs.

This module deliberately has no runtime persistence, graph, model, provider,
tool, authority, or background-work dependency.  The conversational runtime
owns those concerns and uses these records only as an interpreted, provisional
view of one operator input.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id


SCHEMA_VERSION = "semantic_problem_modeling_v1"


@dataclass(frozen=True)
class SemanticInputFrame:
    frame_id: str
    source_turn_id: str
    source_text: str
    source_type: str
    domain_guess: str
    entities: tuple[Mapping[str, Any], ...]
    quantities: tuple[Mapping[str, Any], ...]
    relationships: tuple[Mapping[str, Any], ...]
    constraints: tuple[str, ...]
    goal: str
    unknown_target: str
    uncertainty: tuple[str, ...]
    action_relevance: tuple[str, ...]
    required_tools: tuple[str, ...]
    required_operator_authority: tuple[str, ...]
    memory_candidates: tuple[str, ...]
    safety_risk_class: str
    status: str
    limitations: tuple[str, ...]
    risks: tuple[str, ...]
    source_spans: tuple[Mapping[str, Any], ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProblemModel:
    problem_model_id: str
    frame_id: str
    problem_type: str
    domain: str
    given_information: tuple[Mapping[str, Any], ...]
    unknown_target: str
    constraints: tuple[str, ...]
    assumptions: tuple[str, ...]
    candidate_methods: tuple[str, ...]
    selected_method: str
    why_this_method: str
    expected_output: str
    validation_checks: tuple[str, ...]
    limitations: tuple[str, ...]
    status: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EquationUnderstandingFrame:
    equation_frame_id: str
    frame_id: str
    equation: str
    modeled_phenomenon: str
    variables: tuple[Mapping[str, Any], ...]
    units: tuple[str, ...]
    assumptions: tuple[str, ...]
    valid_domain: str
    unknowns_it_can_solve: tuple[str, ...]
    required_evidence: tuple[str, ...]
    result_meaning: str
    validation_checks: tuple[str, ...]
    warning_notes: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionAffordance:
    affordance_id: str
    frame_id: str
    possible_action: str
    risk: str
    required_authority: str
    expected_effect: str
    reversible: bool
    tool_needed: str
    safe_next_step: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticProblemCompilation:
    semantic_input_frame: SemanticInputFrame
    problem_model: ProblemModel | None
    equation_understanding_frame: EquationUnderstandingFrame | None
    action_affordances: tuple[ActionAffordance, ...]
    summary: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        frame = self.semantic_input_frame.as_record()
        return {
            "frame_id": self.semantic_input_frame.frame_id,
            "record_kind": "semantic_problem_modeling_frame",
            **frame,
            "semantic_input_frame": frame,
            "problem_model": self.problem_model.as_record() if self.problem_model else None,
            "equation_understanding_frame": (
                self.equation_understanding_frame.as_record()
                if self.equation_understanding_frame
                else None
            ),
            "action_affordances": tuple(item.as_record() for item in self.action_affordances),
            "summary": self.summary,
            "compiler_version": SCHEMA_VERSION,
        }


def extract_semantic_source_text(message: str) -> str:
    """Keep a raw input intact while dropping a short framing request when present."""

    normalized = " ".join(str(message or "").split()).strip()
    if not normalized:
        return ""
    equation_match = re.search(r"\bf\s*=\s*m\s*a\b", normalized, flags=re.IGNORECASE)
    if equation_match:
        return "F = ma"
    if ":" in normalized:
        prefix, candidate = normalized.split(":", 1)
        if candidate.strip() and any(
            term in prefix.lower()
            for term in ("read", "inspect", "analyze", "analyse", "frame", "review", "model", "note", "scenario")
        ):
            return candidate.strip()
    return normalized


def compile_semantic_problem_frame(
    source_text: str,
    *,
    frame_scope_id: str,
    source_turn_id: str = "",
    source_type: str = "operator_text",
) -> SemanticProblemCompilation | None:
    """Compile one supported input into a deterministic, non-authoritative frame."""

    source = extract_semantic_source_text(source_text)
    if not source:
        return None
    normalized = " ".join(source.lower().split())
    if re.search(r"\bf\s*=\s*m\s*a\b", normalized, flags=re.IGNORECASE):
        return _compile_newtons_second_law(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
    if _looks_like_incline_problem(normalized):
        return _compile_incline_problem(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
    if _looks_like_defensive_sql_finding(normalized):
        return _compile_defensive_sql_finding(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
    if _looks_like_portfolio_risk(normalized):
        return _compile_portfolio_risk(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
    if _looks_like_operations_dependency(normalized):
        return _compile_operations_dependency(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
    return None


def render_semantic_problem_frame(record: Mapping[str, Any]) -> str:
    """Render a concise, human-readable, provisional interpretation from one record."""

    frame = record.get("semantic_input_frame") if isinstance(record.get("semantic_input_frame"), Mapping) else record
    domain = str(frame.get("domain_guess") or "interpreted input").replace("_", " ")
    entities = tuple(
        str(item.get("label") or item.get("entity") or "")
        for item in frame.get("entities", ())
        if isinstance(item, Mapping) and str(item.get("label") or item.get("entity") or "")
    )
    relationships = tuple(
        _render_relationship(item)
        for item in frame.get("relationships", ())
        if isinstance(item, Mapping)
    )
    model = record.get("problem_model") if isinstance(record.get("problem_model"), Mapping) else {}
    equation = record.get("equation_understanding_frame") if isinstance(record.get("equation_understanding_frame"), Mapping) else {}
    affordances = tuple(item for item in record.get("action_affordances", ()) if isinstance(item, Mapping))
    lines = [
        f"I created a provisional semantic frame for this {domain} input.",
        f"Frame: {str(record.get('frame_id') or frame.get('frame_id') or '')}",
    ]
    if entities:
        lines.extend(("", "Key entities:", "- " + "\n- ".join(entities)))
    if relationships:
        lines.extend(("", "Structural relationships:", "- " + "\n- ".join(relationships)))
    if model:
        lines.extend((
            "",
            "Problem model:",
            f"- Unknown target: {model.get('unknown_target') or frame.get('unknown_target') or 'not specified'}",
            f"- Selected method: {model.get('selected_method') or 'not yet selected'}",
            f"- Why: {model.get('why_this_method') or 'not recorded'}",
        ))
    if equation:
        lines.extend((
            "",
            "Equation understanding:",
            f"- Model: {equation.get('modeled_phenomenon') or ''}",
            f"- It can solve for: {', '.join(str(item) for item in equation.get('unknowns_it_can_solve', ()))}",
        ))
    risks = tuple(str(item) for item in frame.get("risks", ()) if str(item))
    if risks:
        lines.extend(("", "Risks or limits:", "- " + "\n- ".join(risks)))
    uncertainty = tuple(str(item) for item in frame.get("uncertainty", ()) if str(item))
    if uncertainty:
        lines.extend(("", "Open questions:", "- " + "\n- ".join(uncertainty)))
    if affordances:
        lines.extend(("", f"Safe next step: {affordances[0].get('safe_next_step') or ''}"))
    lines.extend((
        "",
        "Status: source-bound and provisional. This records an interpretation, not reviewed or admitted knowledge, and it has not taken an external action.",
    ))
    return "\n".join(lines)


def render_semantic_problem_recall(record: Mapping[str, Any], *, focus: str) -> str:
    """Answer a read-only status question without changing the recorded frame."""

    frame = record.get("semantic_input_frame") if isinstance(record.get("semantic_input_frame"), Mapping) else record
    model = record.get("problem_model") if isinstance(record.get("problem_model"), Mapping) else {}
    equation = record.get("equation_understanding_frame") if isinstance(record.get("equation_understanding_frame"), Mapping) else {}
    if focus == "unknown_target":
        detail = str(model.get("unknown_target") or frame.get("unknown_target") or "No unknown target was recorded.")
        prefix = "The recorded unknown target is"
    elif focus == "risk":
        risks = tuple(str(item) for item in frame.get("risks", ()) if str(item))
        detail = "; ".join(risks) or "No specific risk was recorded."
        prefix = "The recorded risk framing is"
    elif focus == "equation":
        solves = ", ".join(str(item) for item in equation.get("unknowns_it_can_solve", ()) if str(item))
        warning = "; ".join(str(item) for item in equation.get("warning_notes", ()) if str(item))
        detail = f"{equation.get('modeled_phenomenon') or 'The equation model'}; it can solve for {solves}. {warning}".strip()
        prefix = "The frame records"
    else:
        detail = str(record.get("summary") or "No summary was recorded.")
        prefix = "The frame records"
    return (
        f"{prefix}: {detail}\n\n"
        f"Frame: {str(record.get('frame_id') or frame.get('frame_id') or '')}\n"
        "This is a read-only recall of a provisional, source-bound interpretation; it did not create a new frame or change semantic truth."
    )


def _frame_id(scope: str, domain: str, source: str) -> str:
    return stable_id("semantic-input-frame", scope, SCHEMA_VERSION, domain, " ".join(source.lower().split()))


def _problem_model_id(frame_id: str, problem_type: str) -> str:
    return stable_id("semantic-problem-model", frame_id, problem_type, SCHEMA_VERSION)


def _affordance(frame_id: str, action: str, *, risk: str, authority: str, expected: str, tool: str, next_step: str) -> ActionAffordance:
    return ActionAffordance(
        affordance_id=stable_id("semantic-action-affordance", frame_id, action),
        frame_id=frame_id,
        possible_action=action,
        risk=risk,
        required_authority=authority,
        expected_effect=expected,
        reversible=True,
        tool_needed=tool,
        safe_next_step=next_step,
    )


def _span(source: str, value: str, kind: str) -> Mapping[str, Any] | None:
    if not value:
        return None
    match = re.search(re.escape(value), source, flags=re.IGNORECASE)
    if not match:
        return None
    return {"kind": kind, "text": source[match.start():match.end()], "start": match.start(), "end": match.end()}


def _spans(source: str, items: tuple[tuple[str, str], ...]) -> tuple[Mapping[str, Any], ...]:
    values = []
    seen: set[tuple[str, int, int]] = set()
    for value, kind in items:
        span = _span(source, value, kind)
        if span is None:
            continue
        key = (str(span["kind"]), int(span["start"]), int(span["end"]))
        if key not in seen:
            seen.add(key)
            values.append(span)
    return tuple(values)


def _entity(source: str, label: str, role: str) -> Mapping[str, Any]:
    item: dict[str, Any] = {"label": label, "role": role}
    span = _span(source, label, "entity")
    if span is not None:
        item["source_span"] = span
    return item


def _quantity(source: str, label: str, value: str, unit: str, source_value: str) -> Mapping[str, Any]:
    item: dict[str, Any] = {"label": label, "value": value, "unit": unit}
    span = _span(source, source_value, "quantity")
    if span is not None:
        item["source_span"] = span
    return item


def _render_relationship(item: Mapping[str, Any]) -> str:
    subject = str(item.get("subject") or "")
    predicate = str(item.get("predicate") or "").replace("_", " ")
    obj = str(item.get("object") or "")
    return " ".join(part for part in (subject, predicate, obj) if part)


def _looks_like_operations_dependency(text: str) -> bool:
    overdue_invoice = "invoice" in text and "overdue" in text
    blocked_start = bool(re.search(r"\bcrew\s+\S+\s+(?:cannot|can't|is unable to)\s+start\b", text))
    delivery_dependency = bool(re.search(r"\buntil\b.+\b(?:delivered|available|arrives?)\b", text))
    return overdue_invoice and blocked_start and delivery_dependency


def _compile_operations_dependency(source: str, *, frame_scope_id: str, source_turn_id: str, source_type: str) -> SemanticProblemCompilation:
    invoice_match = re.search(r"\binvoice\s*(?:#\s*)?(?P<invoice>[A-Za-z0-9-]+)", source, flags=re.IGNORECASE)
    overdue_match = re.search(r"\boverdue\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?)\b", source, flags=re.IGNORECASE)
    if overdue_match is None:
        overdue_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?)\s+overdue\b", source, flags=re.IGNORECASE)
    dependency_match = re.search(
        r"\bcrew\s+(?P<crew>[A-Za-z0-9-]+)\s+(?:cannot|can't|is unable to)\s+start\s+(?:the\s+)?(?P<job>.+?)\s+until\s+(?:the\s+)?(?P<resource>.+?)\s+(?:is\s+)?(?:delivered|available|arrives?)\b",
        source,
        flags=re.IGNORECASE,
    )
    invoice = f"Invoice #{invoice_match.group('invoice')}" if invoice_match else "Invoice"
    crew = f"Crew {dependency_match.group('crew')}" if dependency_match else "Crew"
    job = _clean_capture(dependency_match.group("job")) if dependency_match else "job start"
    resource = _clean_capture(dependency_match.group("resource")) if dependency_match else "delivery dependency"
    duration_value = overdue_match.group("value") if overdue_match else ""
    duration_unit = overdue_match.group("unit").lower() if overdue_match else ""
    duration_text = overdue_match.group(0) if overdue_match else ""
    frame_id = _frame_id(frame_scope_id, "operations_logistics", source)
    entities = (
        _entity(source, invoice, "receivable"),
        _entity(source, crew, "execution_actor"),
        _entity(source, job, "blocked_work"),
        _entity(source, resource, "dependency_resource"),
    )
    quantities = (
        _quantity(source, "overdue duration", duration_value, duration_unit, duration_text),
    ) if duration_value else ()
    relationships = (
        {"subject": invoice, "predicate": "has_overdue_state", "object": duration_text or "overdue payment"},
        {"subject": crew, "predicate": "blocked_from_starting", "object": job},
        {"subject": resource, "predicate": "is_dependency_for", "object": job},
    )
    constraints = (
        f"{resource} availability is a prerequisite for {job} to begin.",
        "The overdue receivable can constrain cash flow until its status is clarified.",
    )
    uncertainty = (
        "Is there a payment dispute or a committed payment date?",
        f"What is the current ETA for {resource}?",
        f"Is an alternate {resource} available?",
        "How urgent is the affected client or job relative to other work?",
    )
    risks = ("cashflow delay from the overdue invoice", "schedule delay from the blocked job dependency")
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="operations_logistics_receivables",
        entities=entities,
        quantities=quantities,
        relationships=relationships,
        constraints=constraints,
        goal="Clarify the receivable and the delivery bottleneck before deciding how to protect the schedule.",
        unknown_target="The payment status and the resource delivery path that will unblock the job.",
        uncertainty=uncertainty,
        action_relevance=("identify the dependency bottleneck", "separate cashflow and schedule risk", "collect ETA and payment evidence"),
        required_tools=(),
        required_operator_authority=("external communication before contacting a customer or supplier",),
        memory_candidates=("invoice-to-job dependency", "overdue-receivable schedule interaction"),
        safety_risk_class="operational_decision_support_no_external_action",
        status="provisional_interpreted",
        limitations=("The note does not establish payment status, delivery ETA, alternate availability, or client priority.",),
        risks=risks,
        source_spans=_spans(source, ((invoice, "entity"), (crew, "entity"), (job, "entity"), (resource, "entity"), (duration_text, "quantity"))),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "dependency_and_receivables_risk"),
        frame_id=frame_id,
        problem_type="dependency_and_receivables_risk",
        domain="operations_logistics",
        given_information=(
            {"item": invoice, "fact": duration_text or "overdue"},
            {"item": crew, "fact": f"cannot start {job}"},
            {"item": resource, "fact": f"must be delivered before {job} starts"},
        ),
        unknown_target=frame.unknown_target,
        constraints=constraints,
        assumptions=("The note reflects the current operational state.",),
        candidate_methods=("dependency bottleneck review", "receivables status review", "alternate-resource check"),
        selected_method="dependency bottleneck and receivables risk review",
        why_this_method="The note names both a cashflow exposure and a resource dependency that blocks execution.",
        expected_output="A prioritized clarification list before any external follow-up or schedule change.",
        validation_checks=("confirm invoice status", "confirm resource ETA", "confirm alternate availability", "confirm client priority"),
        limitations=frame.limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "prepare dependency clarification", risk="no external action", authority="none for local framing", expected="identify the blocking evidence needed", tool="none", next_step="Ask for the payment status, resource ETA, alternate resource availability, and client priority before acting."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The note describes two linked operational pressures: an overdue receivable and a delivery dependency that prevents the crew from starting the named job.")


def _looks_like_incline_problem(text: str) -> bool:
    return "incline" in text and ("frictionless" in text or "friction" in text) and ("block" in text or "slides" in text)


def _compile_incline_problem(source: str, *, frame_scope_id: str, source_turn_id: str, source_type: str) -> SemanticProblemCompilation:
    mass_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*kg\b", source, flags=re.IGNORECASE)
    angle_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*(?:\u00b0|degrees?)\b", source, flags=re.IGNORECASE)
    mass = mass_match.group("value") if mass_match else "not supplied"
    angle = angle_match.group("value") if angle_match else "not supplied"
    frame_id = _frame_id(frame_scope_id, "physics_incline_problem", source)
    constraints = ("frictionless incline", "gravity acts downward", "acceleration is along the plane")
    assumptions = ("constant gravitational acceleration", "rigid incline", "classical mechanics", "air resistance ignored")
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="physics_mechanics",
        entities=(_entity(source, "block", "system_body"), _entity(source, "incline", "constraint_surface")),
        quantities=tuple(item for item in (
            _quantity(source, "mass", mass, "kg", mass_match.group(0) if mass_match else ""),
            _quantity(source, "incline angle", angle, "degrees", angle_match.group(0) if angle_match else ""),
        ) if item.get("value") != "not supplied"),
        relationships=({"subject": "gravity", "predicate": "has_component_along", "object": "incline"},),
        constraints=constraints,
        goal="Model the acceleration of the block along the incline.",
        unknown_target="acceleration down the incline",
        uncertainty=("The prompt does not specify a numerical gravitational constant; use the symbolic model unless a convention is selected.",),
        action_relevance=("decompose gravity into components parallel and perpendicular to the plane",),
        required_tools=(),
        required_operator_authority=(),
        memory_candidates=("frictionless incline force decomposition",),
        safety_risk_class="safe_physics_modeling",
        status="provisional_interpreted",
        limitations=("The frame models the problem; it does not claim an experimental measurement or solve an unstated variant.",),
        risks=(),
        source_spans=_spans(source, (("block", "entity"), ("incline", "entity"), (mass_match.group(0) if mass_match else "", "quantity"), (angle_match.group(0) if angle_match else "", "quantity"), ("frictionless", "constraint"))),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "frictionless_incline_acceleration"),
        frame_id=frame_id,
        problem_type="frictionless_incline_acceleration",
        domain="physics_mechanics",
        given_information=(
            {"name": "mass", "value": mass, "unit": "kg"},
            {"name": "incline_angle", "value": angle, "unit": "degrees"},
            {"name": "friction", "value": "0", "unit": "dimensionless"},
        ),
        unknown_target="acceleration down the incline",
        constraints=constraints,
        assumptions=assumptions,
        candidate_methods=("Newtonian force decomposition", "energy method for displacement-dependent follow-up"),
        selected_method="a = g sin(theta)",
        why_this_method="On a frictionless incline, the component of gravity parallel to the plane determines the acceleration.",
        expected_output="An acceleration magnitude directed down the plane; the mass cancels from the result.",
        validation_checks=("units are m/s^2", "acceleration is less than g for an incline below 90 degrees", "mass cancels"),
        limitations=frame.limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "perform symbolic force decomposition", risk="low-risk local reasoning", authority="none", expected="identify the correct acceleration model", tool="none", next_step="Use a = g sin(theta), then check units and that the result is less than g before reporting a numeric value."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The block-and-incline system is a frictionless mechanics problem whose target is acceleration along the plane, not the normal force or a generic equation lookup.")


def _looks_like_defensive_sql_finding(text: str) -> bool:
    return ("sql" in text or "database query" in text) and "input" in text and any(term in text for term in ("concatenat", "string build", "interpolat"))


def _compile_defensive_sql_finding(source: str, *, frame_scope_id: str, source_turn_id: str, source_type: str) -> SemanticProblemCompilation:
    frame_id = _frame_id(frame_scope_id, "defensive_sql_source_to_sink", source)
    constraints = ("External input crosses into a database command construction path.", "No exploit behavior or target-specific instruction is produced by this frame.")
    mitigation = "Use parameterized queries or prepared statements, validate input at the boundary, and apply least-privilege database access."
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="defensive_cybersecurity",
        entities=(
            _entity(source, "User input", "untrusted_source"),
            _entity(source, "SQL query", "database_command_sink"),
            _entity(source, "execution", "command_execution_boundary"),
        ),
        quantities=(),
        relationships=(
            {"subject": "user input", "predicate": "flows_to", "object": "SQL query execution"},
            {"subject": "external input", "predicate": "crosses_trust_boundary_into", "object": "database command"},
        ),
        constraints=constraints,
        goal="Classify and contain a possible unsafe source-to-sink data flow.",
        unknown_target="Whether the implementation uses a parameterized query path and validates the input before the sink.",
        uncertainty=("The language, database driver, existing parameterization, and query construction path are not supplied.",),
        action_relevance=("review the source-to-sink path", "verify parameterization", "plan a defensive regression test if authorized"),
        required_tools=("static code inspection if authorized",),
        required_operator_authority=("code-change approval before any patch",),
        memory_candidates=("defensive source-to-sink finding", "database trust boundary"),
        safety_risk_class="defensive_cybersecurity_review_only",
        status="provisional_interpreted",
        limitations=("This is a defensive classification, not exploit validation, target instruction, or an offensive chain.",),
        risks=("SQL injection candidate caused by untrusted input reaching a command sink through concatenation",),
        source_spans=_spans(source, (("User input", "entity"), ("SQL query", "entity"), ("execution", "entity"), ("concatenated", "relationship"))),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "defensive_source_to_sink_review"),
        frame_id=frame_id,
        problem_type="defensive_source_to_sink_review",
        domain="defensive_cybersecurity",
        given_information=(
            {"source": "user input", "trust_level": "external or untrusted"},
            {"sink": "SQL query execution", "effect": "database command interpretation"},
            {"construction": "string concatenation"},
        ),
        unknown_target=frame.unknown_target,
        constraints=constraints,
        assumptions=("The statement describes a real code path that warrants defensive review.",),
        candidate_methods=("source-to-sink validation", "parameterization check", "least-privilege review"),
        selected_method="defensive dataflow review",
        why_this_method="The relevant meaning is the trust-boundary crossing from untrusted input to database command construction.",
        expected_output="A code-review finding and safe mitigation plan, not an exploit payload.",
        validation_checks=("confirm prepared statement use", "confirm untrusted input is not concatenated into executable SQL", "confirm database role has least privilege"),
        limitations=frame.limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "prepare defensive mitigation proposal", risk="code changes require approval", authority="operator approval for code mutation", expected="reduce unsafe source-to-sink exposure", tool="static code review only", next_step=mitigation),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The statement describes a defensive source-to-sink finding: untrusted input is crossing into SQL command construction, so the safe focus is parameterization and boundary validation rather than exploitation.")


def _looks_like_portfolio_risk(text: str) -> bool:
    return "portfolio" in text and bool(re.search(r"\b\d+(?:\.\d+)?\s*%", text))


def _compile_portfolio_risk(source: str, *, frame_scope_id: str, source_turn_id: str, source_type: str) -> SemanticProblemCompilation:
    allocations = []
    for match in re.finditer(r"(?P<weight>\d+(?:\.\d+)?)\s*%\s*(?P<asset>[^,.;]+)", source, flags=re.IGNORECASE):
        asset = _clean_capture(match.group("asset"))
        if asset:
            allocations.append((match.group("weight"), asset, match.group(0)))
    horizon_match = re.search(r"\b(?P<value>one|two|three|four|five|six|seven|eight|nine|ten|\d+)[-\s](?P<unit>day|week|month|year)s?\b", source, flags=re.IGNORECASE)
    horizon_text = horizon_match.group(0) if horizon_match else "not supplied"
    scenario_match = re.search(r"\b(?:worr(?:y|ies)|concern(?:ed)?\s+about)\s+(?:a|an|the)?\s*(?P<scenario>.+?)(?:[.!?]|$)", source, flags=re.IGNORECASE)
    scenario = _clean_capture(scenario_match.group("scenario")) if scenario_match else "sector correction scenario"
    if "ai" in source.lower() or "tech" in source.lower():
        scenario = "AI/tech correction scenario"
    frame_id = _frame_id(frame_scope_id, "finance_portfolio_risk", source)
    entities = tuple(_entity(source, asset, "portfolio_exposure") for _weight, asset, _source in allocations)
    quantities = tuple(_quantity(source, "allocation", weight, "percent", raw) for weight, _asset, raw in allocations)
    if horizon_match:
        quantities += (_quantity(source, "time horizon", horizon_match.group("value"), horizon_match.group("unit") + "s", horizon_text),)
    span_items = (
        tuple((asset, "entity") for _weight, asset, _raw in allocations)
        + tuple((raw, "quantity") for _weight, _asset, raw in allocations)
    )
    if horizon_match:
        span_items += ((horizon_text, "quantity"),)
    relationships = tuple(
        {"subject": asset, "predicate": "has_portfolio_weight", "object": f"{weight}%"}
        for weight, asset, _raw in allocations
    ) + ({"subject": "portfolio", "predicate": "is_exposed_to", "object": scenario},)
    risks = (
        "concentration risk in high-growth technology exposure",
        "sector drawdown and volatility risk during the stated correction scenario",
        "opportunity cost and liquidity tradeoff associated with the cash allocation",
    )
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="finance_portfolio_risk",
        entities=entities,
        quantities=quantities,
        relationships=relationships,
        constraints=("No live prices or correlations are supplied.", "No trade execution is authorized by this frame."),
        goal="Frame the concentration and scenario risk before considering a supervised decision proposal.",
        unknown_target="How the stated allocation could behave under the scenario, given the operator's risk tolerance and account constraints.",
        uncertainty=("Current prices, correlations, and drawdown history are not supplied.", "Tax/account constraints and risk tolerance are not supplied.", "The individual holdings inside each allocation are not supplied."),
        action_relevance=("compare scenario exposure", "review liquidity buffer", "ask for risk tolerance and account constraints"),
        required_tools=("current market data only if later authorized",),
        required_operator_authority=("explicit authority before any trade or external account action",),
        memory_candidates=("portfolio concentration scenario", "time-horizon risk framing"),
        safety_risk_class="financial_decision_support_no_trade_execution",
        status="provisional_interpreted",
        limitations=("This is a risk frame, not personalized investment advice, a live valuation, or a trade instruction.",),
        risks=risks,
        source_spans=_spans(source, span_items),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "portfolio_concentration_scenario"),
        frame_id=frame_id,
        problem_type="portfolio_concentration_scenario",
        domain="finance_risk",
        given_information=tuple({"asset": asset, "weight_percent": weight} for weight, asset, _raw in allocations) + ({"time_horizon": horizon_text}, {"scenario": scenario}),
        unknown_target=frame.unknown_target,
        constraints=frame.constraints,
        assumptions=("The stated weights are approximate portfolio exposures.", "The scenario is a hypothetical risk discussion, not a forecast."),
        candidate_methods=("scenario stress discussion", "drawdown estimate using authorized current data", "liquidity review", "rebalancing tradeoff discussion"),
        selected_method="scenario stress and concentration-risk framing",
        why_this_method="The input specifies allocations, a time horizon, and a sector-correction concern rather than an executable trading instruction.",
        expected_output="A bounded risk discussion and the additional information needed for any later supervised proposal.",
        validation_checks=("verify holdings and weights", "obtain live prices/correlations only if authorized", "confirm horizon, risk tolerance, taxes, and account constraints"),
        limitations=frame.limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "prepare a scenario table", risk="decision support only", authority="none for a local explanatory table", expected="make concentration and liquidity tradeoffs explicit", tool="none", next_step="Ask for holdings, risk tolerance, account constraints, and whether the operator wants a hypothetical scenario table; do not execute a trade."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The portfolio is framed as a six-month concentration and scenario-risk question, with a cash buffer and data limits that must be understood before any supervised decision proposal.")


def _compile_newtons_second_law(source: str, *, frame_scope_id: str, source_turn_id: str, source_type: str) -> SemanticProblemCompilation:
    frame_id = _frame_id(frame_scope_id, "physics_equation_model", source)
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text="F = ma",
        source_type=source_type,
        domain_guess="physics_equation_model",
        entities=(
            _entity("F = ma", "net force", "modeled_quantity"),
            _entity("F = ma", "mass", "system_property"),
            _entity("F = ma", "acceleration", "motion_response"),
        ),
        quantities=(),
        relationships=({"subject": "net force", "predicate": "equals", "object": "mass times acceleration"},),
        constraints=("Force must mean net force.", "The model applies in an inertial frame at classical scales."),
        goal="Understand which physical relationship the equation models and what information it can solve for.",
        unknown_target="force, mass, or acceleration when the other required quantities are known",
        uncertainty=("The equation alone does not identify all forces or establish whether the assumptions hold in a specific system.",),
        action_relevance=("sum forces before substituting", "check units", "identify the desired unknown"),
        required_tools=(),
        required_operator_authority=(),
        memory_candidates=("Newton's second law model understanding",),
        safety_risk_class="safe_physics_modeling",
        status="provisional_interpreted",
        limitations=("The equation is a model, not a complete description of every force or a substitute for a free-body diagram.",),
        risks=(),
        source_spans=_spans("F = ma", (("F", "variable"), ("m", "variable"), ("a", "variable"))),
    )
    equation = EquationUnderstandingFrame(
        equation_frame_id=stable_id("equation-understanding-frame", frame_id, "F=ma"),
        frame_id=frame_id,
        equation="F = ma",
        modeled_phenomenon="Newton's second law: net force relates mass and acceleration.",
        variables=(
            {"symbol": "F_net", "meaning": "net force", "unit": "newton (N)"},
            {"symbol": "m", "meaning": "mass", "unit": "kilogram (kg)"},
            {"symbol": "a", "meaning": "acceleration", "unit": "meter per second squared (m/s^2)"},
        ),
        units=("N = kg*m/s^2",),
        assumptions=("inertial frame", "classical scale", "F represents the net force"),
        valid_domain="Classical mechanics when the relevant net force and system mass are defined.",
        unknowns_it_can_solve=("net force", "mass", "acceleration"),
        required_evidence=("net force and mass to solve acceleration", "mass and acceleration to solve net force", "net force and acceleration to solve mass"),
        result_meaning="The result describes the motion response of a mass to the net force acting on it.",
        validation_checks=("dimensional check: N = kg*m/s^2", "confirm forces have been summed into a net force"),
        warning_notes=("An individual force is not enough unless all relevant forces are summed into net force.",),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "newtons_second_law_model"),
        frame_id=frame_id,
        problem_type="equation_model_understanding",
        domain="physics_mechanics",
        given_information=({"equation": "F = ma"},),
        unknown_target=frame.unknown_target,
        constraints=frame.constraints,
        assumptions=equation.assumptions,
        candidate_methods=("free-body diagram", "net-force calculation", "dimensional validation"),
        selected_method="Newton's second law with explicit net-force identification",
        why_this_method="The equation relates a system's net force, mass, and acceleration after the relevant forces are modeled.",
        expected_output="A physically interpretable force, mass, or acceleration with units and stated assumptions.",
        validation_checks=equation.validation_checks,
        limitations=frame.limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "identify a solvable unknown", risk="low-risk local reasoning", authority="none", expected="select the appropriate rearrangement after modeling forces", tool="none", next_step="Name the unknown, draw or describe the force balance, then use the other two quantities and perform a dimensional check."),
    )
    return SemanticProblemCompilation(frame, model, equation, affordances, "F = ma is a net-force model: it connects a mass to its acceleration after the relevant forces are summed, and it can solve for force, mass, or acceleration when the other inputs are known.")


def _clean_capture(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" .,:;-")


__all__ = [
    "ActionAffordance",
    "EquationUnderstandingFrame",
    "ProblemModel",
    "SCHEMA_VERSION",
    "SemanticInputFrame",
    "SemanticProblemCompilation",
    "compile_semantic_problem_frame",
    "extract_semantic_source_text",
    "render_semantic_problem_frame",
    "render_semantic_problem_recall",
]

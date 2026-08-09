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
    semantic_signature: Mapping[str, Any]
    matched_roles: tuple[str, ...]
    missing_roles: tuple[str, ...]
    confidence_label: str
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
            "capability_route_candidate": _compile_capability_route_candidate(frame),
            "summary": self.summary,
            "compiler_version": SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class _RoleExtraction:
    """One deterministic semantic-role reading of an operator source.

    This is deliberately local to the existing semantic-frame compiler.  It
    makes the compiler's recognition boundary inspectable without creating a
    second interpretation, persistence, or runtime owner.
    """

    domain: str
    required_roles: tuple[str, ...]
    role_values: Mapping[str, str]
    source_spans: tuple[Mapping[str, Any], ...]

    @property
    def matched_roles(self) -> tuple[str, ...]:
        return tuple(role for role in self.required_roles if str(self.role_values.get(role) or ""))

    @property
    def missing_roles(self) -> tuple[str, ...]:
        return tuple(role for role in self.required_roles if role not in self.matched_roles)

    @property
    def is_complete(self) -> bool:
        return not self.missing_roles

    def value(self, role: str, fallback: str = "") -> str:
        return str(self.role_values.get(role) or fallback)

    def signature(self) -> Mapping[str, Any]:
        return {
            "domain": self.domain,
            "required_roles": self.required_roles,
            "role_signature": f"{self.domain}:" + "|".join(self.required_roles),
            "role_values": dict(self.role_values),
        }


def extract_semantic_source_text(message: str) -> str:
    """Keep a raw input intact while dropping a short framing request when present."""

    normalized = " ".join(str(message or "").split()).strip()
    if not normalized:
        return ""
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
    equation_roles = _extract_newtons_second_law_roles(source)
    if equation_roles.is_complete:
        return _compile_newtons_second_law(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=equation_roles,
        )
    incline_roles = _extract_incline_roles(source)
    if incline_roles.is_complete:
        return _compile_incline_problem(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=incline_roles,
        )
    cyber_roles = _extract_defensive_sql_roles(source)
    if cyber_roles.is_complete:
        return _compile_defensive_sql_finding(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=cyber_roles,
        )
    portfolio_roles = _extract_portfolio_roles(source)
    if portfolio_roles.is_complete:
        return _compile_portfolio_risk(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=portfolio_roles,
        )
    operations_roles = _extract_operations_roles(source)
    if operations_roles.is_complete:
        return _compile_operations_dependency(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=operations_roles,
        )
    health_roles = _extract_health_information_roles(source)
    if health_roles.is_complete:
        return _compile_health_information(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=health_roles,
        )
    legal_roles = _extract_legal_financial_risk_roles(source)
    if legal_roles.is_complete:
        return _compile_legal_financial_risk_information(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=legal_roles,
        )
    generic_roles = _extract_generic_structured_problem_roles(source)
    if generic_roles.is_complete:
        return _compile_generic_structured_problem(
            source,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
            roles=generic_roles,
        )
    return None


def compile_semantic_problem_frames(
    source_text: str,
    *,
    frame_scope_id: str,
    source_turn_id: str = "",
    source_type: str = "operator_text",
) -> tuple[SemanticProblemCompilation, ...]:
    """Compile independent source clauses without merging their domains.

    This is a projection over the existing single-frame compiler.  Each clause
    retains its own source text, spans, stable ID, and route candidate; this
    helper neither creates a planner nor broadens any capability boundary.
    """

    raw_source = str(source_text or "")
    if not raw_source.strip():
        return ()
    whole_compilation = compile_semantic_problem_frame(
        raw_source,
        frame_scope_id=frame_scope_id,
        source_turn_id=source_turn_id,
        source_type=source_type,
    )
    clauses = [
        match.group(0).strip()
        for match in re.finditer(r"[^.!?;\n]+(?:[.!?;]+|$)", raw_source)
        if match.group(0).strip()
    ]
    if len(clauses) < 2:
        return (whole_compilation,) if whole_compilation is not None else ()
    clause_compilations = [
        compile_semantic_problem_frame(
            clause,
            frame_scope_id=frame_scope_id,
            source_turn_id=source_turn_id,
            source_type=source_type,
        )
        for clause in clauses
    ]
    compiled: list[SemanticProblemCompilation] = []
    frame_ids: set[str] = set()
    index = 0
    while index < len(clauses):
        compilation = clause_compilations[index]
        if compilation is None and index + 1 < len(clauses) and clause_compilations[index + 1] is None:
            compilation = compile_semantic_problem_frame(
                f"{clauses[index]} {clauses[index + 1]}",
                frame_scope_id=frame_scope_id,
                source_turn_id=source_turn_id,
                source_type=source_type,
            )
            if compilation is not None:
                index += 1
        if compilation is None:
            index += 1
            continue
        frame_id = compilation.semantic_input_frame.frame_id
        if frame_id in frame_ids:
            index += 1
            continue
        frame_ids.add(frame_id)
        compiled.append(compilation)
        index += 1
    if len(compiled) > 1:
        return tuple(compiled)
    if compiled:
        return tuple(compiled)
    return (whole_compilation,) if whole_compilation is not None else ()


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


def _compile_capability_route_candidate(frame: Mapping[str, Any]) -> Mapping[str, Any]:
    """Project one frame onto an existing safe capability boundary.

    This is a deterministic annotation of the semantic frame, not a capability
    manager or execution record. The conversational runtime persists the frame
    exactly once, which keeps the candidate source-bound and restart-safe.
    """

    frame_id = str(frame.get("frame_id") or "")
    source_text = str(frame.get("source_text") or "")
    domain = str(frame.get("domain_guess") or "")
    common_forbidden = (
        "No model, provider, tool, network, sandbox, filesystem, or external action.",
        "No graph truth mutation, review, admission, planner, scheduler, or worker.",
        "No automatic authority, approval request, or route execution.",
    )
    specifications: dict[str, tuple[str, str, str, tuple[str, ...], tuple[str, ...]]] = {
        "finance_portfolio_risk": (
            "finance_controlled_fixture",
            "eligible",
            "The source-bound portfolio frame can use the existing controlled finance fixture path only after the existing evidence, authority, and accepted-plan boundaries.",
            ("existing evidence permission, authorization, proposal, execution authority, and accepted plan",),
            common_forbidden + ("No market lookup, account access, trade, or financial recommendation execution.",),
        ),
        "physics_mechanics": (
            "physics_deterministic_calculation",
            "eligible",
            "The source-bound frictionless incline frame can use the existing deterministic physics calculation path only after the existing accepted-plan boundary.",
            ("existing evidence permission, authorization, proposal, execution authority, and accepted plan",),
            common_forbidden + ("No experimental measurement or frictional-motion inference.",),
        ),
        "physics_equation_model": (
            "physics_deterministic_calculation",
            "clarify",
            "The equation model is safe to frame, but the existing deterministic evaluator requires a recorded frictionless 30-degree incline rather than a generic equation explanation.",
            ("a recorded frictionless 30-degree incline before the existing calculation path is eligible",),
            common_forbidden + ("No unsupported numeric calculation is inferred from a generic equation frame.",),
        ),
        "operations_logistics_receivables": (
            "operations_blocked_external_dependency",
            "blocked",
            "The frame identifies an external payment and delivery dependency, but the existing boundary forbids contact, scheduling, payment, or status claims.",
            ("explicit later authority for any external communication or status source",),
            common_forbidden + ("No customer, supplier, payment, scheduling, or status action.",),
        ),
        "defensive_cybersecurity": (
            "defensive_cyber_blocked_file_or_scan_boundary",
            "blocked",
            "The frame supports defensive source-to-sink interpretation only; owned-fixture file reads or scans remain separately blocked.",
            ("explicit later authority for a bounded owned-fixture inspection",),
            common_forbidden + ("No payload, exploit, scan, repository read, local file read, or execution.",),
        ),
        "health_information_safety": (
            "health_info_safe_response",
            "clarify",
            "The frame supports non-diagnostic symptom and escalation-context clarification only.",
            (),
            common_forbidden + ("No diagnosis certainty, prescription, or evidence execution.",),
        ),
        "legal_financial_risk_information": (
            "legal_financial_risk_safe_response",
            "clarify",
            "The frame supports non-advisory document and jurisdiction-gap clarification only.",
            (),
            common_forbidden + ("No legal-advice certainty, records access, or evidence execution.",),
        ),
        "generic_source_bound_problem": (
            "generic_structured_problem",
            "clarify",
            "The source has a structured issue and uncertainty, but it does not justify a specialist capability route.",
            (),
            common_forbidden + ("No specialist route, inferred cause, owner, remedy, or execution.",),
        ),
    }
    route_name, decision, rationale, required_authority, forbidden_actions = specifications.get(
        domain,
        (
            "unsupported_source_bound_frame",
            "unsupported",
            "The source-bound frame has no supported deterministic capability route.",
            (),
            common_forbidden,
        ),
    )
    source_spans = tuple(
        dict(item)
        for item in frame.get("source_spans", ())
        if isinstance(item, Mapping)
    )
    candidate_id = stable_id(
        "semantic-frame-capability-route",
        frame_id,
        domain,
        route_name,
        decision,
    )
    return {
        "capability_route_candidate_id": candidate_id,
        "record_kind": "semantic_frame_capability_route_candidate",
        "source_frame_id": frame_id,
        "source_text": source_text,
        "source_span_refs": source_spans,
        "domain": domain,
        "route_name": route_name,
        "decision": decision,
        "rationale": rationale,
        "required_authority_if_any": required_authority,
        "forbidden_actions": forbidden_actions,
        "may_execute_now": False,
        "status": "deterministic_route_candidate_only",
        "schema_version": SCHEMA_VERSION,
    }


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


def _merge_spans(*groups: tuple[Mapping[str, Any], ...]) -> tuple[Mapping[str, Any], ...]:
    """Merge provenance spans without discarding the role that found them."""

    values: list[Mapping[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for group in groups:
        for span in group:
            if not isinstance(span, Mapping):
                continue
            kind = str(span.get("kind") or "source_text")
            start = int(span.get("start") or 0)
            end = int(span.get("end") or 0)
            key = (kind, start, end)
            if key in seen:
                continue
            seen.add(key)
            values.append(dict(span))
    return tuple(values)


def _role_span(source: str, match: re.Match[str], role: str, group: str | int = 0) -> Mapping[str, Any]:
    return {
        "kind": f"role:{role}",
        "text": source[match.start(group):match.end(group)],
        "start": match.start(group),
        "end": match.end(group),
    }


def _role_entry(
    source: str,
    role: str,
    match: re.Match[str] | None,
    *,
    group: str | int = 0,
    value: str = "",
) -> tuple[str, str, Mapping[str, Any]] | None:
    if match is None:
        return None
    label = _clean_capture(value or match.group(group))
    if not label:
        return None
    return role, label, _role_span(source, match, role, group)


def _make_role_extraction(
    domain: str,
    required_roles: tuple[str, ...],
    entries: tuple[tuple[str, str, Mapping[str, Any]] | None, ...],
) -> _RoleExtraction:
    values: dict[str, str] = {}
    spans: list[Mapping[str, Any]] = []
    for entry in entries:
        if entry is None:
            continue
        role, value, span = entry
        if role not in values:
            values[role] = value
            spans.append(span)
    return _RoleExtraction(
        domain=domain,
        required_roles=required_roles,
        role_values=values,
        source_spans=tuple(spans),
    )


def _frame_role_fields(roles: _RoleExtraction) -> Mapping[str, Any]:
    return {
        "semantic_signature": roles.signature(),
        "matched_roles": roles.matched_roles,
        "missing_roles": roles.missing_roles,
        "confidence_label": "deterministic_pattern_match",
    }


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


def _extract_operations_roles(source: str) -> _RoleExtraction:
    """Recognize a logistics dependency from its required semantic roles.

    The roles intentionally require both the receivable and the blocked-work
    dependency.  A dashboard that merely mentions invoices or jobs therefore
    remains ordinary conversation rather than becoming a false analysis.
    """

    invoice_match = re.search(
        r"\b(?:invoice|receivable)\s*(?:#\s*)?(?P<identifier>[A-Za-z0-9-]+)\b",
        source,
        flags=re.IGNORECASE,
    )
    overdue_match = re.search(
        r"\b(?P<duration>\d+(?:\.\d+)?\s*(?:days?|weeks?|months?))\s+(?:overdue|unpaid)\b",
        source,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\b(?:overdue|unpaid)\s+(?:(?:for|by)\s+)?(?P<duration>\d+(?:\.\d+)?\s*(?:days?|weeks?|months?))\b",
        source,
        flags=re.IGNORECASE,
    )
    crew_match = re.search(r"\b(?P<crew>(?:crew|team)\s+[A-Za-z0-9-]+)\b", source, flags=re.IGNORECASE)
    job_match = re.search(
        r"\b(?:start|begin|starting)\s+(?:the\s+)?(?P<job>[A-Za-z0-9][A-Za-z0-9\s-]{0,60}?)\s+(?:until|because)\b",
        source,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\bbefore\s+(?:the\s+)?(?:crew|team)\s+[A-Za-z0-9-]+\s+can\s+start\s+(?:the\s+)?(?P<job>[A-Za-z0-9][A-Za-z0-9\s-]{0,60}?)(?:,|[.!?]|$)",
        source,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\bbefore\s+(?:the\s+)?(?P<job>[A-Za-z0-9][A-Za-z0-9\s-]{0,60}?)\s+can\s+start\b",
        source,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\bblocked\s+from\s+starting\s+(?:the\s+)?(?P<job>[A-Za-z0-9][A-Za-z0-9\s-]{0,60}?)(?:[.!?]|$)",
        source,
        flags=re.IGNORECASE,
    )
    resource_match = re.search(
        r"\b(?:until|because)\s+(?:the\s+)?(?P<resource>[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z0-9-]+){0,3}?)\s+(?:is\s+)?(?:still\s+)?(?:not\s+)?(?:delivered|available|arrives?|pending\s+delivery)\b",
        source,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\b(?:the\s+)?(?P<resource>[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z0-9-]+){0,3}?)\s+(?:must\s+be|has\s+not\s+been|is\s+still\s+pending)\s+(?:delivered|delivery)\b",
        source,
        flags=re.IGNORECASE,
    )
    blocking_match = re.search(
        r"\b(?:cannot|can't|is\s+unable\s+to|blocked\s+from)\s+(?:begin|start|starting)\b",
        source,
        flags=re.IGNORECASE,
    ) or re.search(r"\bbefore\b.+\bcan\s+start\b", source, flags=re.IGNORECASE)
    return _make_role_extraction(
        "operations_logistics_receivables",
        (
            "receivable_or_invoice_state",
            "overdue_or_unpaid_time_relation",
            "work_party_or_crew",
            "work_item_or_job",
            "blocking_dependency",
            "delivery_or_resource_condition",
        ),
        (
            _role_entry(source, "receivable_or_invoice_state", invoice_match),
            _role_entry(source, "overdue_or_unpaid_time_relation", overdue_match),
            _role_entry(source, "work_party_or_crew", crew_match, group="crew"),
            _role_entry(source, "work_item_or_job", job_match, group="job"),
            _role_entry(source, "blocking_dependency", blocking_match),
            _role_entry(source, "delivery_or_resource_condition", resource_match, group="resource"),
        ),
    )


def _looks_like_operations_dependency(text: str) -> bool:
    return _extract_operations_roles(text).is_complete


def _compile_operations_dependency(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    invoice_match = re.search(r"\binvoice\s*(?:#\s*)?(?P<invoice>[A-Za-z0-9-]+)", source, flags=re.IGNORECASE)
    overdue_match = re.search(r"\boverdue\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?)\b", source, flags=re.IGNORECASE)
    if overdue_match is None:
        overdue_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?)\s+overdue\b", source, flags=re.IGNORECASE)
    dependency_match = re.search(
        r"\bcrew\s+(?P<crew>[A-Za-z0-9-]+)\s+(?:cannot|can't|is unable to)\s+start\s+(?:the\s+)?(?P<job>.+?)\s+until\s+(?:the\s+)?(?P<resource>.+?)\s+(?:is\s+)?(?:delivered|available|arrives?)\b",
        source,
        flags=re.IGNORECASE,
    )
    invoice = roles.value("receivable_or_invoice_state") or (f"Invoice #{invoice_match.group('invoice')}" if invoice_match else "Invoice")
    crew = roles.value("work_party_or_crew") or (f"Crew {dependency_match.group('crew')}" if dependency_match else "Crew")
    job = roles.value("work_item_or_job") or (_clean_capture(dependency_match.group("job")) if dependency_match else "job start")
    resource = roles.value("delivery_or_resource_condition") or (_clean_capture(dependency_match.group("resource")) if dependency_match else "delivery dependency")
    duration_text = roles.value("overdue_or_unpaid_time_relation") or (overdue_match.group(0) if overdue_match else "")
    duration_match = re.search(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?)", duration_text, flags=re.IGNORECASE)
    duration_value = duration_match.group("value") if duration_match else ""
    duration_unit = duration_match.group("unit").lower() if duration_match else ""
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
        source_spans=_merge_spans(
            _spans(source, ((invoice, "entity"), (crew, "entity"), (job, "entity"), (resource, "entity"), (duration_text, "quantity"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
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


def _extract_incline_roles(source: str) -> _RoleExtraction:
    body_match = re.search(r"\b(?P<body>block|object|body)\b", source, flags=re.IGNORECASE)
    surface_match = re.search(r"\b(?P<surface>incline|ramp|slope)\b", source, flags=re.IGNORECASE)
    angle_match = re.search(r"\b(?P<angle>\d+(?:\.\d+)?)(?:\s*\u00b0|\s*-?\s*degrees?)\b", source, flags=re.IGNORECASE)
    friction_match = re.search(
        r"\b(?P<friction>frictionless|without\s+friction|ignoring\s+friction|ignore\s+friction)\b",
        source,
        flags=re.IGNORECASE,
    )
    motion_match = re.search(
        r"\b(?P<motion>acceleration|accelerat(?:e|es|ing)|slides?|released|moves?\s+down|down)\b",
        source,
        flags=re.IGNORECASE,
    )
    return _make_role_extraction(
        "physics_mechanics",
        (
            "body",
            "inclined_surface",
            "incline_angle",
            "friction_condition",
            "motion_or_requested_output",
        ),
        (
            _role_entry(source, "body", body_match, group="body"),
            _role_entry(source, "inclined_surface", surface_match, group="surface"),
            _role_entry(source, "incline_angle", angle_match, group="angle"),
            _role_entry(source, "friction_condition", friction_match, group="friction"),
            _role_entry(source, "motion_or_requested_output", motion_match, group="motion"),
        ),
    )


def _looks_like_incline_problem(text: str) -> bool:
    return _extract_incline_roles(text).is_complete


def _compile_incline_problem(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    mass_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*kg\b", source, flags=re.IGNORECASE)
    angle_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)(?:\s*\u00b0|\s*-?\s*degrees?)\b", source, flags=re.IGNORECASE)
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
        entities=(
            _entity(source, roles.value("body", "block"), "system_body"),
            _entity(source, roles.value("inclined_surface", "incline"), "constraint_surface"),
        ),
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
        source_spans=_merge_spans(
            _spans(source, ((roles.value("body", "block"), "entity"), (roles.value("inclined_surface", "incline"), "entity"), (mass_match.group(0) if mass_match else "", "quantity"), (angle_match.group(0) if angle_match else "", "quantity"), (roles.value("friction_condition", "frictionless"), "constraint"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
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


def _extract_defensive_sql_roles(source: str) -> _RoleExtraction:
    normalized = " ".join(source.lower().split())
    safe_binding = bool(re.search(
        r"\b(?:uses?|with|via)\s+(?:a\s+)?(?:prepared\s+statement|parameterized\s+quer(?:y|ies)|bound\s+parameter|parameter\s+binding)\b",
        normalized,
    )) or bool(re.search(r"\binput\s+(?:is\s+)?validated\s+as\s+(?:a\s+)?bound\s+parameter\b", normalized))
    explicit_binding_absence = bool(re.search(r"\b(?:without|no|not)\s+(?:parameter(?:ized)?\s+binding|parameterization|binding)\b", normalized))
    if safe_binding and not explicit_binding_absence:
        return _make_role_extraction("defensive_cybersecurity", ("unsafe_construction",), ())
    source_match = re.search(
        r"\b(?P<input>user(?:[-\s]?(?:controlled|supplied))?\s+(?:input|text)|request\s+parameter|external\s+input|untrusted\s+input|input)\b",
        source,
        flags=re.IGNORECASE,
    )
    sink_match = re.search(
        r"\b(?P<sink>sql(?:\s+(?:query|command|statement|execution))?|database\s+query)\b",
        source,
        flags=re.IGNORECASE,
    )
    construction_match = re.search(
        r"\b(?P<construction>concatenat(?:e|ed|ing|ion)?|string[-\s]?build|interpolat(?:e|ed|ing|ion)?|append(?:ed|ing)?|without\s+(?:parameter(?:ized)?\s+binding|parameterization|binding))\b",
        source,
        flags=re.IGNORECASE,
    )
    execution_match = re.search(r"\b(?P<execution>execut(?:e|ed|ion)|run)\b", source, flags=re.IGNORECASE)
    return _make_role_extraction(
        "defensive_cybersecurity",
        ("untrusted_input", "sql_command_sink", "unsafe_construction"),
        (
            _role_entry(source, "untrusted_input", source_match, group="input"),
            _role_entry(source, "sql_command_sink", sink_match, group="sink"),
            _role_entry(source, "unsafe_construction", construction_match, group="construction"),
            _role_entry(source, "execution_boundary", execution_match, group="execution"),
        ),
    )


def _looks_like_defensive_sql_finding(text: str) -> bool:
    return _extract_defensive_sql_roles(text).is_complete


def _compile_defensive_sql_finding(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
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
            _entity(source, roles.value("untrusted_input", "User input"), "untrusted_source"),
            _entity(source, roles.value("sql_command_sink", "SQL query"), "database_command_sink"),
            _entity(source, roles.value("execution_boundary", "execution"), "command_execution_boundary"),
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
        source_spans=_merge_spans(
            _spans(source, ((roles.value("untrusted_input", "User input"), "entity"), (roles.value("sql_command_sink", "SQL query"), "entity"), (roles.value("execution_boundary", "execution"), "entity"), (roles.value("unsafe_construction", "concatenated"), "relationship"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
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


def _portfolio_allocation_matches(source: str) -> tuple[re.Match[str], ...]:
    pattern = re.compile(
        r"\b(?P<weight>\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:of\s+)?(?P<asset>.+?)(?=(?:,|;|\.|\band\s+\d+(?:\.\d+)?\s*(?:%|percent)\b|$))",
        flags=re.IGNORECASE,
    )
    return tuple(pattern.finditer(source))


def _extract_portfolio_roles(source: str) -> _RoleExtraction:
    allocations = _portfolio_allocation_matches(source)
    portfolio_match = re.search(r"\b(?P<portfolio>portfolio|account|allocation)\b", source, flags=re.IGNORECASE)
    horizon_match = re.search(
        r"\b(?P<horizon>(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s*(?:-|\s)?(?:day|week|month|year)s?|half[-\s]?year)\b",
        source,
        flags=re.IGNORECASE,
    )
    scenario_match = re.search(
        r"\b(?P<scenario>(?:(?:ai|technology|tech|growth)[A-Za-z\s/-]{0,45}(?:correction|drops?|dropp(?:ed|ing)|drawdown|declines?|declin(?:ed|ing)|sell[-\s]?off)|(?:correction|drops?|dropp(?:ed|ing)|drawdown|declines?|declin(?:ed|ing)|sell[-\s]?off)[A-Za-z\s/-]{0,45}(?:ai|technology|tech|growth)))\b",
        source,
        flags=re.IGNORECASE,
    )
    concentration_match = re.search(r"\b(?P<concentration>high[-\s]?growth|tech(?:nology)?|ai|small[-\s]?cap)\b", source, flags=re.IGNORECASE)
    allocation_entry = None
    if len(allocations) >= 2:
        first = allocations[0]
        allocation_entry = (
            "allocation_composition",
            _clean_capture(first.group(0)),
            _role_span(source, first, "allocation_composition"),
        )
    return _make_role_extraction(
        "finance_portfolio_risk",
        ("portfolio_context", "allocation_composition", "concentration_exposure", "time_horizon", "stress_scenario"),
        (
            _role_entry(source, "portfolio_context", portfolio_match, group="portfolio"),
            allocation_entry,
            _role_entry(source, "concentration_exposure", concentration_match, group="concentration"),
            _role_entry(source, "time_horizon", horizon_match, group="horizon"),
            _role_entry(source, "stress_scenario", scenario_match, group="scenario"),
        ),
    )


def _looks_like_portfolio_risk(text: str) -> bool:
    return _extract_portfolio_roles(text).is_complete


def _extract_health_information_roles(source: str) -> _RoleExtraction:
    symptom_match = re.search(
        r"\b(?P<symptom>itchy\s+rash|rash|redness|warmth|swelling|drainage|fever|pain|spreading)\b",
        source,
        flags=re.IGNORECASE,
    )
    timing_match = re.search(
        r"\b(?P<timing>(?:for|since)\s+(?:\d+|one|two|three|four|five|several)\s*(?:hours?|days?|weeks?)|(?:started|began)\s+(?:today|yesterday|\d+\s*(?:hours?|days?|weeks?)\s+ago))\b",
        source,
        flags=re.IGNORECASE,
    )
    question_match = re.search(
        r"\b(?P<question>worried|concerned|should\s+I|whether|need(?:s)?\s+(?:care|medical|a\s+doctor)|what\s+should)\b",
        source,
        flags=re.IGNORECASE,
    )
    return _make_role_extraction(
        "health_information_safety",
        ("symptom_pattern", "time_course", "information_or_care_question"),
        (
            _role_entry(source, "symptom_pattern", symptom_match, group="symptom"),
            _role_entry(source, "time_course", timing_match, group="timing"),
            _role_entry(source, "information_or_care_question", question_match, group="question"),
        ),
    )


def _compile_health_information(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    symptom = roles.value("symptom_pattern")
    timing = roles.value("time_course")
    lower = source.lower()
    escalation_flags = tuple(
        label
        for label, marker in (
            ("spreading change", "spreading"),
            ("fever", "fever"),
            ("warmth", "warmth"),
            ("increasing pain", "pain"),
            ("drainage", "drainage"),
        )
        if marker in lower
    )
    frame_id = _frame_id(frame_scope_id, "health_information_safety", source)
    limitations = (
        "This frame organizes the reported symptoms and uncertainty; it does not diagnose a condition or prescribe treatment.",
        "Severity, medical history, examination findings, and medication/allergy context are not supplied.",
    )
    uncertainty = (
        "Whether the symptom is changing, spreading, painful, warm, draining, or accompanied by fever is not fully established.",
        "The relevant medical history and any exposure or treatment context are not supplied.",
    )
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="health_information_safety",
        entities=(_entity(source, symptom, "reported_symptom"),),
        quantities=(),
        relationships=({"subject": symptom, "predicate": "has_reported_time_course", "object": timing},),
        constraints=("No diagnosis is inferred from this source-bound frame.", "No treatment or prescription is proposed."),
        goal="Organize the reported symptom, timing, uncertainty, and escalation context for an informational discussion.",
        unknown_target="Whether the reported pattern has escalation features that warrant timely licensed clinical assessment.",
        uncertainty=uncertainty,
        action_relevance=("clarify symptom progression", "identify reported escalation flags", "encourage appropriate professional assessment when warranted"),
        required_tools=(),
        required_operator_authority=(),
        memory_candidates=(),
        safety_risk_class="health_information_non_diagnostic",
        status="provisional_interpreted",
        limitations=limitations,
        risks=tuple(f"reported possible escalation flag: {flag}" for flag in escalation_flags) or ("reported symptoms need contextual assessment",),
        source_spans=_merge_spans(
            _spans(source, ((symptom, "entity"), (timing, "time_course"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "health_information_triage_boundary"),
        frame_id=frame_id,
        problem_type="health_information_triage_boundary",
        domain="health_information",
        given_information=({"reported_symptom": symptom}, {"reported_timing": timing}, {"reported_escalation_flags": escalation_flags}),
        unknown_target=frame.unknown_target,
        constraints=frame.constraints,
        assumptions=("The source describes the operator's concern accurately.",),
        candidate_methods=("symptom and timing clarification", "non-diagnostic escalation-context review"),
        selected_method="non-diagnostic symptom-context framing",
        why_this_method="The source supplies a symptom and time course but not enough information to establish a diagnosis.",
        expected_output="A bounded list of missing context and reported escalation features, without diagnosis or prescription.",
        validation_checks=("keep uncertainty explicit", "do not name a diagnosis as certain", "do not prescribe treatment"),
        limitations=limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "clarify health information", risk="non-diagnostic informational boundary", authority="none", expected="make missing context and reported escalation features explicit", tool="none", next_step="Clarify progression and reported escalation features, and seek licensed medical assessment when the situation appears urgent or worsening."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The source supports a non-diagnostic health-information frame: it records the symptom and timing, preserves uncertainty, and identifies reported escalation context without labeling a condition or recommending treatment.")


def _extract_legal_financial_risk_roles(source: str) -> _RoleExtraction:
    party_match = re.search(
        r"\b(?P<party>collection\s+agency|debt\s+collector|creditor|lender|landlord|tenant|consumer|company)\b",
        source,
        flags=re.IGNORECASE,
    )
    claim_match = re.search(
        r"\b(?P<claim>debt|collection|disputed\s+balance|balance|amount\s+owed|notice|invoice)\b",
        source,
        flags=re.IGNORECASE,
    )
    uncertainty_match = re.search(
        r"\b(?P<uncertainty>dispute(?:d)?|incorrect|do\s+not\s+recognize|not\s+sure|unclear|question)\b",
        source,
        flags=re.IGNORECASE,
    )
    return _make_role_extraction(
        "legal_financial_risk_information",
        ("party", "claim_or_balance", "dispute_or_uncertainty"),
        (
            _role_entry(source, "party", party_match, group="party"),
            _role_entry(source, "claim_or_balance", claim_match, group="claim"),
            _role_entry(source, "dispute_or_uncertainty", uncertainty_match, group="uncertainty"),
        ),
    )


def _compile_legal_financial_risk_information(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    party = roles.value("party")
    claim = roles.value("claim_or_balance")
    uncertainty_marker = roles.value("dispute_or_uncertainty")
    amount_match = re.search(r"\$\s*(?P<amount>\d+(?:,\d{3})*(?:\.\d{2})?)", source)
    amount = amount_match.group("amount") if amount_match else "not supplied"
    frame_id = _frame_id(frame_scope_id, "legal_financial_risk_information", source)
    limitations = (
        "This frame organizes a reported claim or dispute; it is not legal advice or a determination of liability, validity, deadlines, or rights.",
        "Jurisdiction, governing agreement, notice dates, and complete documents are not supplied.",
    )
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="legal_financial_risk_information",
        entities=(_entity(source, party, "reported_party"), _entity(source, claim, "reported_claim")),
        quantities=(_quantity(source, "reported_amount", amount, "currency", amount_match.group(0) if amount_match else ""),) if amount_match else (),
        relationships=({"subject": party, "predicate": "asserts_or_relates_to", "object": claim},),
        constraints=("Do not infer legal rights, deadlines, liability, or jurisdiction.", "Do not give legal advice or instruct a legal response."),
        goal="Organize the reported parties, claim, uncertainty, documents needed, and jurisdiction gap for informational review.",
        unknown_target="Whether the reported claim is supported by the relevant documents and what jurisdiction-specific rules or deadlines may matter.",
        uncertainty=("The complete notice, account history, agreement, payment records, and communications are not supplied.", "The applicable jurisdiction and any response deadline are not supplied."),
        action_relevance=("preserve and organize documents", "clarify the jurisdiction", "seek qualified legal or consumer-assistance advice when needed"),
        required_tools=(),
        required_operator_authority=(),
        memory_candidates=(),
        safety_risk_class="legal_financial_information_non_advisory",
        status="provisional_interpreted",
        limitations=limitations,
        risks=("reported financial or legal consequence remains uncertain", "jurisdiction-specific requirements may materially change interpretation"),
        source_spans=_merge_spans(
            _spans(source, ((party, "entity"), (claim, "claim"), (amount_match.group(0) if amount_match else "", "quantity"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "legal_financial_document_review_boundary"),
        frame_id=frame_id,
        problem_type="legal_financial_document_review_boundary",
        domain="legal_financial_information",
        given_information=({"party": party}, {"claim": claim}, {"reported_amount": amount}, {"uncertainty_marker": uncertainty_marker}),
        unknown_target=frame.unknown_target,
        constraints=frame.constraints,
        assumptions=("The reported party, claim, and uncertainty marker are accurately quoted from the source.",),
        candidate_methods=("document inventory", "jurisdiction clarification", "qualified advice referral"),
        selected_method="source-bound document and jurisdiction gap framing",
        why_this_method="The source reports a disputed legal-financial issue but lacks the documents and jurisdiction needed for a reliable conclusion.",
        expected_output="A list of documents, dates, and jurisdiction details to clarify without legal advice.",
        validation_checks=("keep liability and deadlines uncertain", "name missing documents", "name the jurisdiction gap", "avoid legal advice"),
        limitations=limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "prepare document clarification list", risk="non-advisory legal information boundary", authority="none", expected="identify what is missing without directing a legal response", tool="none", next_step="Preserve the notice and relevant records, identify the jurisdiction and dates, and consult a qualified local resource for advice if needed."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The source supports a non-advisory legal-financial frame: it records the parties and disputed claim, keeps jurisdiction and document gaps explicit, and does not determine liability or prescribe a response.")


def _extract_generic_structured_problem_roles(source: str) -> _RoleExtraction:
    issue_match = re.search(
        r"\b(?P<issue>problem|issue|failure|failing|inconsistent|delay|blocked|risk|concern|dispute|missing|unclear)\b",
        source,
        flags=re.IGNORECASE,
    )
    uncertainty_match = re.search(
        r"\b(?P<uncertainty>unknown|unclear|uncertain|no\s+one\s+knows|now\s+(?:know|known)|confirmed|no\s+\w+\s+(?:details|information|owner|deadline)|need\s+to\s+know|whether|what\s+should|how\s+can)\b",
        source,
        flags=re.IGNORECASE,
    )
    return _make_role_extraction(
        "generic_source_bound_problem",
        ("observed_issue", "uncertainty_or_decision_need"),
        (
            _role_entry(source, "observed_issue", issue_match, group="issue"),
            _role_entry(source, "uncertainty_or_decision_need", uncertainty_match, group="uncertainty"),
        ),
    )


def _compile_generic_structured_problem(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    issue = roles.value("observed_issue")
    uncertainty_marker = roles.value("uncertainty_or_decision_need")
    frame_id = _frame_id(frame_scope_id, "generic_source_bound_problem", source)
    limitations = (
        "This generic frame records only the issue and uncertainty explicitly present in the source.",
        "It does not infer a specialist domain, cause, owner, remedy, or external action.",
    )
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="generic_source_bound_problem",
        entities=(_entity(source, issue, "reported_issue_marker"),),
        quantities=(),
        relationships=({"subject": "reported source", "predicate": "contains_issue_marker", "object": issue},),
        constraints=("Keep the domain generic until evidence supports a more specific frame.", "Do not infer an external action or a factual resolution."),
        goal="Preserve the structured issue and its stated uncertainty for later clarification.",
        unknown_target="The source facts needed to identify the relevant domain, cause, owner, and next safe question.",
        uncertainty=(f"The source signals uncertainty through: {uncertainty_marker}.", "No specialist interpretation is justified from the supplied facts."),
        action_relevance=("ask one source-grounded clarification if an existing owner later selects it",),
        required_tools=(),
        required_operator_authority=(),
        memory_candidates=(),
        safety_risk_class="generic_source_bound_interpretation_only",
        status="provisional_interpreted",
        limitations=limitations,
        risks=("premature domain assignment could misstate the source",),
        source_spans=_merge_spans(_spans(source, ((issue, "issue_marker"), (uncertainty_marker, "uncertainty_marker"))), roles.source_spans),
        **_frame_role_fields(roles),
    )
    model = ProblemModel(
        problem_model_id=_problem_model_id(frame_id, "generic_structured_clarification"),
        frame_id=frame_id,
        problem_type="generic_structured_clarification",
        domain="generic",
        given_information=({"issue_marker": issue}, {"uncertainty_marker": uncertainty_marker}),
        unknown_target=frame.unknown_target,
        constraints=frame.constraints,
        assumptions=(),
        candidate_methods=("source-grounded clarification",),
        selected_method="defer specialist classification and clarify missing source facts",
        why_this_method="The source contains a structured issue and uncertainty but does not support a domain-specific interpretation.",
        expected_output="One bounded clarification target without inferred facts or action.",
        validation_checks=("preserve source spans", "do not assign a specialist domain", "do not infer a remedy"),
        limitations=limitations,
        status="provisional_problem_model",
    )
    affordances = (
        _affordance(frame_id, "preserve generic clarification need", risk="interpretation only", authority="none", expected="keep the missing facts visible without overreach", tool="none", next_step="Clarify the missing source facts before assigning a domain, cause, owner, or action."),
    )
    return SemanticProblemCompilation(frame, model, None, affordances, "The source contains a structured issue and uncertainty, but it does not justify a domain-specific interpretation; the frame preserves only the stated clarification need.")


def _compile_portfolio_risk(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    allocations = []
    for match in _portfolio_allocation_matches(source):
        asset = _clean_capture(match.group("asset"))
        if asset:
            allocations.append((match.group("weight"), asset, match.group(0)))
    horizon_match = re.search(r"\b(?P<value>one|two|three|four|five|six|seven|eight|nine|ten|\d+)[-\s]?(?P<unit>day|week|month|year)s?\b", source, flags=re.IGNORECASE)
    if horizon_match is None:
        horizon_match = re.search(r"\b(?P<value>half)[-\s]?(?P<unit>year)\b", source, flags=re.IGNORECASE)
    horizon_text = horizon_match.group(0) if horizon_match else "not supplied"
    scenario = roles.value("stress_scenario", "sector correction scenario")
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
        source_spans=_merge_spans(_spans(source, span_items), roles.source_spans),
        **_frame_role_fields(roles),
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


def _extract_newtons_second_law_roles(source: str) -> _RoleExtraction:
    equation_match = re.search(r"\b(?P<equation>f\s*=\s*m\s*a)\b", source, flags=re.IGNORECASE) or re.search(
        r"\b(?P<equation>force\s+equals\s+mass\s+times\s+acceleration)\b",
        source,
        flags=re.IGNORECASE,
    )
    purpose_match = re.search(
        r"\b(?P<purpose>explain|mean(?:ing)?|model|solve|solving|use|understand)\b",
        source,
        flags=re.IGNORECASE,
    )
    variable_match = re.search(
        r"\b(?P<variables>force|mass|acceleration)\b",
        source,
        flags=re.IGNORECASE,
    )
    return _make_role_extraction(
        "physics_equation_model",
        ("equation_expression", "modeled_variables"),
        (
            _role_entry(source, "equation_expression", equation_match, group="equation"),
            _role_entry(
                source,
                "modeled_variables",
                variable_match or equation_match,
                group="variables" if variable_match else "equation",
                value="force, mass, acceleration" if equation_match else "",
            ),
            _role_entry(source, "modeling_intent", purpose_match, group="purpose"),
        ),
    )


def _compile_newtons_second_law(
    source: str,
    *,
    frame_scope_id: str,
    source_turn_id: str,
    source_type: str,
    roles: _RoleExtraction,
) -> SemanticProblemCompilation:
    frame_id = _frame_id(frame_scope_id, "physics_equation_model", source)
    frame = SemanticInputFrame(
        frame_id=frame_id,
        source_turn_id=source_turn_id,
        source_text=source,
        source_type=source_type,
        domain_guess="physics_equation_model",
        entities=(
            _entity(source, "net force", "modeled_quantity"),
            _entity(source, "mass", "system_property"),
            _entity(source, "acceleration", "motion_response"),
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
        source_spans=_merge_spans(
            _spans(source, (("F", "variable"), ("m", "variable"), ("a", "variable"), ("force", "variable"), ("mass", "variable"), ("acceleration", "variable"))),
            roles.source_spans,
        ),
        **_frame_role_fields(roles),
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
    "compile_semantic_problem_frames",
    "extract_semantic_source_text",
    "render_semantic_problem_frame",
    "render_semantic_problem_recall",
]

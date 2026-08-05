import pytest

from orchestration.runtime.evidence_bound_analysis import compile_evidence_bound_analysis
from orchestration.runtime.semantic_problem_modeling import compile_semantic_problem_frame
from orchestration.runtime.conversational_runtime_operation import (
    handle_conversational_message,
    start_or_restore_runtime,
)


@pytest.mark.parametrize(
    ("source", "domain", "required_roles"),
    (
        (
            "Invoice #331 is 45 days overdue. Crew A cannot begin the Jackson job until the pump arrives.",
            "operations_logistics_receivables",
            {
                "receivable_or_invoice_state",
                "overdue_or_unpaid_time_relation",
                "work_party_or_crew",
                "work_item_or_job",
                "blocking_dependency",
                "delivery_or_resource_condition",
            },
        ),
        (
            "The lift is still pending delivery, so Crew B is blocked from starting the Monroe install. Invoice #88 has been unpaid for 30 days.",
            "operations_logistics_receivables",
            {
                "receivable_or_invoice_state",
                "overdue_or_unpaid_time_relation",
                "work_party_or_crew",
                "work_item_or_job",
                "blocking_dependency",
                "delivery_or_resource_condition",
            },
        ),
        (
            "Before Crew A can start the Jackson job, the pump must be delivered. The receivable for invoice #331 is overdue by 45 days.",
            "operations_logistics_receivables",
            {
                "receivable_or_invoice_state",
                "overdue_or_unpaid_time_relation",
                "work_party_or_crew",
                "work_item_or_job",
                "blocking_dependency",
                "delivery_or_resource_condition",
            },
        ),
        (
            "A 2 kg object moves down a 30 degree ramp without friction. Find its acceleration.",
            "physics_mechanics",
            {
                "body",
                "inclined_surface",
                "incline_angle",
                "friction_condition",
                "motion_or_requested_output",
            },
        ),
        (
            "On a 30-degree frictionless slope, a 2 kg block is released.",
            "physics_mechanics",
            {
                "body",
                "inclined_surface",
                "incline_angle",
                "friction_condition",
                "motion_or_requested_output",
            },
        ),
        (
            "The application builds a database query by string-concatenating user-controlled input.",
            "defensive_cybersecurity",
            {"untrusted_input", "sql_command_sink", "unsafe_construction"},
        ),
        (
            "A request parameter is appended into a SQL command before execution.",
            "defensive_cybersecurity",
            {"untrusted_input", "sql_command_sink", "unsafe_construction"},
        ),
        (
            "The account is 70 percent aggressive technology funds, 20 percent cash, and 10 percent small-cap value; the risk horizon is six months and an AI correction is the concern.",
            "finance_portfolio_risk",
            {
                "portfolio_context",
                "allocation_composition",
                "concentration_exposure",
                "time_horizon",
                "stress_scenario",
            },
        ),
        (
            "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
            "finance_portfolio_risk",
            {
                "portfolio_context",
                "allocation_composition",
                "concentration_exposure",
                "time_horizon",
                "stress_scenario",
            },
        ),
        (
            "Force equals mass times acceleration. Help me use Newton's second law in a problem.",
            "physics_equation_model",
            {"equation_expression", "modeled_variables"},
        ),
        (
            "Can you explain F = ma as a model I can solve with?",
            "physics_equation_model",
            {"equation_expression", "modeled_variables"},
        ),
    ),
)
def test_role_complete_semantic_variants_compile_to_source_bound_analyses(
    source,
    domain,
    required_roles,
):
    compilation = compile_semantic_problem_frame(source, frame_scope_id="semantic-role-generalization")

    assert compilation is not None
    record = compilation.as_record()
    frame = record["semantic_input_frame"]
    assert frame["domain_guess"] == domain
    assert frame["confidence_label"] == "deterministic_pattern_match"
    assert frame["missing_roles"] == ()
    assert required_roles <= set(frame["matched_roles"])
    assert set(frame["semantic_signature"]["required_roles"]) <= set(frame["matched_roles"])
    assert frame["semantic_signature"]["domain"] == domain
    assert frame["source_spans"]
    assert any(str(span["kind"]).startswith("role:") for span in frame["source_spans"])

    analysis = compile_evidence_bound_analysis(record)
    assert analysis is not None
    analysis_record = analysis.as_record()
    assert analysis_record["domain"] == domain
    assert analysis_record["semantic_signature"] == frame["semantic_signature"]
    assert analysis_record["matched_roles"] == frame["matched_roles"]
    assert analysis_record["missing_roles"] == ()
    assert analysis_record["confidence_label"] == "deterministic_pattern_match"
    assert analysis_record["source_spans"]


@pytest.mark.parametrize(
    "source",
    (
        "A dashboard should show overdue invoices, jobs, and delivery status.",
        "Invoice #331 is overdue by 45 days, but no work item or delivery dependency is recorded.",
        "Crew A starts the Jackson job after the pump was delivered.",
        "A 2 kg block sits on a table at 30 degrees in a drawing.",
        "What is acceleration?",
        "Explain SQL query formatting.",
        "User input is validated as a bound parameter in a prepared statement.",
        "Should I buy technology stocks today?",
        "The account holds some cash and some ETFs.",
        "What are force, mass, acceleration, and Newton?",
    ),
)
def test_keyword_overlap_without_a_complete_role_signature_remains_unframed(source):
    assert compile_semantic_problem_frame(source, frame_scope_id="semantic-role-negative") is None


def test_reordered_logistics_roles_keep_the_actual_work_item_and_delivery_resource():
    source = (
        "Before Crew A can start the Jackson job, the pump must be delivered. "
        "The receivable for invoice #331 is overdue by 45 days."
    )
    compilation = compile_semantic_problem_frame(source, frame_scope_id="semantic-role-logistics-values")

    assert compilation is not None
    frame = compilation.as_record()["semantic_input_frame"]
    relationships = tuple(frame["relationships"])
    delivery = next(item for item in relationships if item["predicate"] == "is_dependency_for")
    blocked = next(item for item in relationships if item["predicate"] == "blocked_from_starting")
    assert delivery["subject"].lower() == "pump"
    assert delivery["object"].lower() == "jackson job"
    assert blocked["subject"].lower() == "crew a"
    assert blocked["object"].lower() == "jackson job"


@pytest.mark.parametrize(
    ("source", "domain"),
    (
        (
            "Before Crew A can start the Jackson job, the pump must be delivered. The receivable for invoice #331 is overdue by 45 days.",
            "operations_logistics_receivables",
        ),
        (
            "A request parameter is appended into a SQL command before execution.",
            "defensive_cybersecurity",
        ),
        (
            "My account is 70% aggressive tech funds, 20% cash, and 10% small-cap value. I am worried about AI stocks dropping over six months.",
            "finance_portfolio_risk",
        ),
    ),
)
def test_role_complete_variants_follow_the_existing_foreground_persistence_path(tmp_path, source, domain):
    runtime_root = tmp_path / domain
    started = handle_conversational_message(
        start_or_restore_runtime(runtime_root),
        "Your new goal is to hold source-bound scenario analyses provisionally. Do not call a model, provider, tool, or take an external action. Wait for my scenarios.",
        runtime_root=runtime_root,
        run_background_cycle=False,
    )
    result = handle_conversational_message(
        started.state,
        source,
        runtime_root=runtime_root,
        run_background_cycle=False,
    )

    assert result.intent.intent_type == "semantic_problem_modeling"
    objective = result.state.active_objective
    assert objective is not None
    frame = objective.provenance["semantic_problem_frames"][0]
    analysis = objective.provenance["evidence_bound_analyses"][0]
    assert frame["semantic_input_frame"]["domain_guess"] == domain
    assert analysis["domain"] == domain
    assert not result.state.pending_chat_requests
    assert not result.state.resolved_chat_requests
    assert not result.state.completed_cycle_keys

    repeated = handle_conversational_message(
        result.state,
        source,
        runtime_root=runtime_root,
        run_background_cycle=False,
    )
    restored = start_or_restore_runtime(runtime_root)
    assert len(repeated.state.active_objective.provenance["semantic_problem_frames"]) == 1
    assert len(repeated.state.active_objective.provenance["evidence_bound_analyses"]) == 1
    assert restored.active_objective is not None
    assert restored.active_objective.provenance["semantic_problem_frames"][0]["frame_id"] == frame["frame_id"]
    assert restored.active_objective.provenance["evidence_bound_analyses"][0]["analysis_id"] == analysis["analysis_id"]

from orchestration.routing.arbitration_selector import ArbitrationSelector
from orchestration.schemas.route_candidate import RouteCandidate


def test_arbitration_selector_chooses_best_candidate():
    candidates = [
        RouteCandidate(route_id="a", route_type="llm", target_node_id="root", rationale="", estimated_confidence=0.5, estimated_cost=0.6),
        RouteCandidate(route_id="b", route_type="deterministic_solver", target_node_id="root", rationale="", estimated_confidence=0.9, estimated_cost=0.1),
    ]

    plan = ArbitrationSelector().select(candidates)
    assert plan.selected_route_type == "deterministic_solver"

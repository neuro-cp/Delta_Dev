from orchestration.routing.route_candidate_builder import RouteCandidateBuilder
from orchestration.schemas.task_graph import TaskGraph, TaskNode, TaskType


def test_route_candidate_builder_builds_allowed_routes():
    graph = TaskGraph(
        graph_id="g1",
        root_node_id="root",
        nodes=[TaskNode(node_id="root", label="root", task_type=TaskType.MATH)],
        task_type=TaskType.MATH,
    )
    candidates = RouteCandidateBuilder().build(
        graph,
        {"allowed_routes": ["deterministic_solver", "llm"]},
    )

    route_types = [c.route_type for c in candidates]
    assert route_types == ["deterministic_solver", "llm"]

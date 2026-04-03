from orchestration.routing.confidence_evaluator import ConfidenceEvaluator
from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.route_candidate import RouteCandidate
from orchestration.schemas.task_graph import TaskGraph, TaskNode, TaskType


def test_confidence_evaluator_prefers_solver_for_math():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="What is 2 + 2?", quantitative_fields={"n0": 2.0, "n1": 2.0})
    graph = TaskGraph(
        graph_id="g1",
        root_node_id="root",
        nodes=[TaskNode(node_id="root", label="root", task_type=TaskType.MATH)],
        task_type=TaskType.MATH,
    )
    candidates = [
        RouteCandidate(route_id="a", route_type="deterministic_solver", target_node_id="root", rationale=""),
        RouteCandidate(route_id="b", route_type="llm", target_node_id="root", rationale=""),
    ]

    scored = ConfidenceEvaluator().score(inquiry, graph, candidates)
    scores = {c.route_type: c.estimated_confidence for c in scored}

    assert scores["deterministic_solver"] > scores["llm"]

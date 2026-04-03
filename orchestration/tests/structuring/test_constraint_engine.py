from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskGraph, TaskNode, TaskType
from orchestration.structuring.constraint_engine import ConstraintEngine


def test_constraint_engine_enables_solver_for_math():
    graph = TaskGraph(
        graph_id="g1",
        root_node_id="root",
        nodes=[TaskNode(node_id="root", label="root", task_type=TaskType.MATH)],
        task_type=TaskType.MATH,
    )
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="2 + 2")
    result = ConstraintEngine().apply(inquiry, graph)

    assert "deterministic_solver" in result["allowed_routes"]

from orchestration.memory.strategy_memory import StrategyMemory
from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskGraph, TaskNode, TaskType


def test_strategy_memory_builds_record():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="What is 2 + 2?", semantic_tokens=["what", "is"])
    graph = TaskGraph(
        graph_id="g1",
        root_node_id="root",
        nodes=[TaskNode(node_id="root", label="root", task_type=TaskType.MATH)],
        task_type=TaskType.MATH,
    )
    result = ExecutionResult(plan_id="p1", route_type="deterministic_solver", success=True, output=4.0, confidence=1.0)

    record = StrategyMemory().build_record(inquiry=inquiry, graph=graph, result=result)
    assert record["selected_route_type"] == "deterministic_solver"
    assert record["task_type"] == "math"

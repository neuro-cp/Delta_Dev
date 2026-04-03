from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskType
from orchestration.structuring.decomposition_engine import DecompositionEngine


def test_decompose_comparison_creates_compare_summary():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="Compare alpha, beta, gamma")
    graph = DecompositionEngine().decompose(inquiry, TaskType.COMPARISON)

    node_ids = {node.node_id for node in graph.nodes}
    assert "compare_summary" in node_ids
    assert any(node.node_id.startswith("item_") for node in graph.nodes)

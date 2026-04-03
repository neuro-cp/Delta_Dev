from dataclasses import dataclass

from orchestration.execution.resolution_executor import ResolutionExecutor
from orchestration.schemas.execution_plan import ExecutionPlan
from orchestration.schemas.inquiry_packet import InquiryPacket


@dataclass(frozen=True)
class DummyBundle:
    payload: dict
    confidence_band: float


class DummyRouter:
    def route(self, payload):
        return DummyBundle(
            payload={"raw_model_output": '{"answer":"ok","confidence":0.9}'},
            confidence_band=0.9,
        )


def test_resolution_executor_solver_route():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="What is 2 + 3?")
    plan = ExecutionPlan(
        plan_id="p1",
        selected_route_id="r1",
        selected_route_type="deterministic_solver",
        target_node_id="root",
        steps=[],
    )
    result = ResolutionExecutor().execute(inquiry, plan)

    assert result.success is True
    assert result.output == 5.0


def test_resolution_executor_llm_route():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="Compare alpha and beta")
    plan = ExecutionPlan(
        plan_id="p2",
        selected_route_id="r2",
        selected_route_type="llm",
        target_node_id="root",
        steps=[],
    )
    result = ResolutionExecutor(model_router=DummyRouter()).execute(inquiry, plan)

    assert result.success is True
    assert result.confidence == 0.9

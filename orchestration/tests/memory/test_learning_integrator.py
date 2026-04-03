from orchestration.memory.learning_integrator import LearningIntegrator
from orchestration.schemas.execution_result import ExecutionResult
from orchestration.schemas.inquiry_packet import InquiryPacket


class DummyLearningAdapter:
    def from_inspection_surface(self, **kwargs):
        return {"bundle": kwargs}


def test_learning_integrator_returns_none_without_adapter():
    bundle = LearningIntegrator().prepare_bundle(
        inquiry=InquiryPacket(inquiry_id="i1", raw_text="x"),
        result=ExecutionResult(plan_id="p1", route_type="llm", success=True, output="ok", confidence=0.5),
        strategy_record={"task_type": "lookup"},
    )
    assert bundle is None


def test_learning_integrator_uses_adapter():
    integrator = LearningIntegrator(learning_adapter=DummyLearningAdapter())
    bundle = integrator.prepare_bundle(
        inquiry=InquiryPacket(inquiry_id="i1", raw_text="x"),
        result=ExecutionResult(plan_id="p1", route_type="llm", success=True, output="ok", confidence=0.5),
        strategy_record={"task_type": "lookup"},
    )
    assert bundle["bundle"]["replay_id"] == "i1"

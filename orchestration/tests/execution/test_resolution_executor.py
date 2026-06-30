from dataclasses import dataclass

from integration.bridge.answer_memory import AnswerMemory
from orchestration.execution.resolution_executor import ResolutionExecutor
from orchestration.schemas.execution_plan import ExecutionPlan
from orchestration.schemas.inquiry_packet import InquiryPacket


@dataclass(frozen=True)
class DummyBundle:
    payload: dict
    confidence_band: float


class DummyRouter:
    def __init__(self):
        self.last_payload = None

    def route(self, payload):
        self.last_payload = dict(payload)
        return DummyBundle(
            payload={"raw_model_output": '{"answer":"ok","confidence":0.9}'},
            confidence_band=0.9,
        )


class DummyArtifactBuilder:
    def build_from_text(self, text):
        return {"pfc": {"text": text}}


class DummyRecallBridge:
    def __init__(self):
        self._artifact_builder = DummyArtifactBuilder()
        self.seen_count = 0

    def interpret(self, suggestions, inquiry):
        self.seen_count = len(suggestions)
        return suggestions[-1] if suggestions else None


class DummyRecallPipeline:
    def __init__(self, suggestions):
        self._suggestions = suggestions

    def run(self, registry, query):
        return self._suggestions


@dataclass(frozen=True)
class DummySemantic:
    semantic_id: str


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


def test_resolution_executor_forwards_attended_context_to_llm():
    router = DummyRouter()
    inquiry = InquiryPacket(
        inquiry_id="i1",
        raw_text="Compare alpha and beta",
        metadata={
            "attended_context": [
                {
                    "memory_id": "m1",
                    "text": "alpha was seen before",
                    "score": 0.8,
                }
            ]
        },
    )
    plan = ExecutionPlan(
        plan_id="p2",
        selected_route_id="r2",
        selected_route_type="llm",
        target_node_id="root",
        steps=[],
    )

    result = ResolutionExecutor(model_router=router).execute(inquiry, plan)

    assert result.success is True
    assert router.last_payload["attended_context"][0]["memory_id"] == "m1"


def test_resolution_executor_recall_enriches_all_suggestions():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="remember this answer")
    plan = ExecutionPlan(
        plan_id="p3",
        selected_route_id="r3",
        selected_route_type="llm",
        target_node_id="root",
        steps=[],
    )

    answer_memory = AnswerMemory()
    answer_memory.add(
        inquiry="remember this answer",
        answer="stored answer",
        confidence=0.75,
    )

    recall_bridge = DummyRecallBridge()
    executor = ResolutionExecutor(
        answer_memory=answer_memory,
        recall_bridge=recall_bridge,
        replay_recall_pipeline=DummyRecallPipeline([
            {"semantic_id": "s1", "pressure": 0.3},
            {"semantic_id": "s2", "pressure": 0.8},
        ]),
        recall_registry=[DummySemantic("s1"), DummySemantic("s2")],
    )

    result = executor.execute(inquiry, plan)

    assert recall_bridge.seen_count == 2
    assert result.route_type == "recall"
    assert result.output == "stored answer"
    assert result.confidence == 0.75

from dataclasses import dataclass

from orchestration.loop.cognitive_loop import CognitiveLoop


@dataclass(frozen=True)
class DummyBundle:
    payload: dict
    confidence_band: float


class DummyModel:
    def produce_output(self, payload):
        return DummyBundle(payload={"raw_model_output": "semantic_ok"}, confidence_band=0.7)


class DummyRouter:
    def route(self, payload):
        return DummyBundle(
            payload={"raw_model_output": '{"answer":"comparison result","confidence":0.8}'},
            confidence_band=0.8,
        )


def test_cognitive_loop_math_prefers_solver():
    loop = CognitiveLoop()
    out = loop.run("What is 2 + 4?")

    assert out["plan"].selected_route_type == "deterministic_solver"
    assert out["result"].output == 6.0
    assert out["result"].evaluation.passed is True


def test_cognitive_loop_comparison_uses_llm():
    loop = CognitiveLoop(model=DummyModel(), model_router=DummyRouter())
    out = loop.run("Compare alpha and beta")

    assert out["plan"].selected_route_type == "llm"
    assert out["result"].success is True
    assert out["result"].confidence == 0.8

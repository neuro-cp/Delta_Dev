from engine.vta_value.value_runtime_hook import ValueRuntimeHook
from engine.vta_value.value_engine import ValueEngine
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_policy import ValuePolicy
from engine.vta_value.value_trace import ValueTrace


def test_value_runtime_hook_snapshot() -> None:
    engine = ValueEngine(
        signal=ValueSignal(),
        policy=ValuePolicy(),
        trace=ValueTrace(),
    )

    hook = ValueRuntimeHook(engine=engine)
    hook.step(current_step=5)

    snap = hook.snapshot()

    assert snap["current_step"] == 5
    assert snap["value"] == 0.0

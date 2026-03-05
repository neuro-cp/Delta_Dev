from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_target import BindingTarget

def test_binding_map_is_structural():
    bm = BindingMap("i1", (BindingTarget("attention"),))
    assert bm.intent_id == "i1"

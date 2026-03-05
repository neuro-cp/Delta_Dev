from engine.execution_binding.binding_target import BindingTarget

def test_binding_target_is_pure_data():
    t = BindingTarget("attention")
    assert t.target_id == "attention"

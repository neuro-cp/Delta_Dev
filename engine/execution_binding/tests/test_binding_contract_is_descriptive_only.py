from engine.execution_binding.binding_contract import BindingContract

def test_binding_contract_is_descriptive_only():
    c = BindingContract()
    assert c.binding_active is False

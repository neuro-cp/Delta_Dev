import pytest
from engine.execution_binding.binding_scope import BindingScope

def test_binding_scope_blocks_forbidden():
    scope = BindingScope(
        allowed_targets=frozenset({"attention"}),
        forbidden_targets=frozenset({"decision"}),
    )
    with pytest.raises(ValueError):
        scope.validate("decision")

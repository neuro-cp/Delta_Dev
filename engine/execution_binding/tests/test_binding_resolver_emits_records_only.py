from engine.execution_binding.binding_resolver import BindingResolver
from engine.execution_binding.binding_scope import BindingScope
from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_target import BindingTarget
from engine.execution_binding.binding_result import BindingResult

def test_binding_resolver_emits_record():
    scope = BindingScope(
        allowed_targets=frozenset({"attention"}),
        forbidden_targets=frozenset(),
    )
    resolver = BindingResolver(scope)
    result = resolver.resolve(
        BindingMap("i2", (BindingTarget("attention"),))
    )
    assert isinstance(result, BindingResult)
    assert result.resolved is True

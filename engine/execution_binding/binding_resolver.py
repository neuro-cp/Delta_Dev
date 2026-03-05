from __future__ import annotations
from .binding_scope import BindingScope
from .binding_map import BindingMap
from .binding_result import BindingResult

class BindingResolver:
    """
    Resolves bindings descriptively.
    Emits records only.
    """

    def __init__(self, scope: BindingScope):
        self._scope = scope

    def resolve(self, binding_map: BindingMap) -> BindingResult:
        resolved = []
        for target in binding_map.targets:
            self._scope.validate(target.target_id)
            resolved.append(target.target_id)

        return BindingResult(
            intent_id=binding_map.intent_id,
            bound_targets=tuple(resolved),
            resolved=True,
            reason="binding_described_only",
        )

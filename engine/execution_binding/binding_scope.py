from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet

@dataclass(frozen=True)
class BindingScope:
    allowed_targets: FrozenSet[str]
    forbidden_targets: FrozenSet[str]

    def validate(self, target_id: str) -> None:
        if target_id in self.forbidden_targets:
            raise ValueError(f"Forbidden binding target: {target_id}")
        if target_id not in self.allowed_targets:
            raise ValueError(f"Unrecognized binding target: {target_id}")

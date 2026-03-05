from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReplayStorageResult:
    replay_id: str
    proposal_count: int
    promoted_semantic_ids: List[str]

    @property
    def registry_size(self) -> int:
        return len(self.promoted_semantic_ids)

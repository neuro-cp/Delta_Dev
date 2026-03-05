from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from inspection.recruitment.recruitment_signature import RecruitmentSignature


@dataclass(frozen=True)
class RecruitmentMap:
    """
    Immutable, offline, whole-episode recruitment view.
    Maps region -> RecruitmentSignature.
    """

    episode_id: int
    signatures: Dict[str, RecruitmentSignature]

    def regions(self) -> Iterable[str]:
        return self.signatures.keys()

    def get(self, region: str) -> RecruitmentSignature:
        return self.signatures[region]

    def to_dict(self) -> Dict:
        return {
            "episode_id": self.episode_id,
            "signatures": {k: v.__dict__ for k, v in self.signatures.items()},
        }

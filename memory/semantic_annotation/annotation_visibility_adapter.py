from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from memory.semantic_annotation.annotation_registry import AnnotationRegistry
from memory.semantic_annotation.annotation_record import SemanticAnnotationRecord


class AnnotationVisibilityContext(str, Enum):
    """
    Explicit, auditable visibility contexts.

    These contexts are declared by callers and enforced
    by policy. No implicit access is permitted.
    """

    POST_DECISION = "post_decision"
    PRE_EPISODE = "pre_episode"


@dataclass(frozen=True)
class AnnotationVisibilityAdapter:
    """
    Read-only adapter for runtime annotation visibility.

    This adapter:
    - exposes annotations ONLY for inspection
    - requires an explicit visibility context
    - enforces read-only access
    - carries NO authority
    - MUST NOT be used inside decision logic

    Removing this adapter must not change behavior.
    """

    _registry: AnnotationRegistry

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def visible_annotations(
        self,
        *,
        episode_id: int,
        context: AnnotationVisibilityContext,
    ) -> List[SemanticAnnotationRecord]:
        """
        Return annotations visible in a specific context.

        Context must be explicitly declared.
        """
        self._validate_context(context)

        # Pure lookup, no transformation
        return list(self._registry.by_episode(episode_id))

    # --------------------------------------------------
    # Internal guards
    # --------------------------------------------------

    @staticmethod
    def _validate_context(context: AnnotationVisibilityContext) -> None:
        """
        Enforce allowed visibility contexts.

        Any expansion requires a policy update.
        """
        if context not in (
            AnnotationVisibilityContext.POST_DECISION,
            AnnotationVisibilityContext.PRE_EPISODE,
        ):
            raise ValueError(f"Invalid annotation visibility context: {context}")

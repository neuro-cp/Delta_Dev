from __future__ import annotations

from typing import Iterable, List, Protocol

from memory.consolidation.episode_consolidator import ConsolidationRecord
from memory.semantic.records import SemanticRecord


class SemanticBuilder(Protocol):
    """
    Interface for offline semantic builders.

    Semantic builders consume consolidation artifacts
    and produce immutable SemanticRecord objects.

    They MUST be:
    - offline
    - deterministic
    - read-only with respect to inputs
    - non-authoritative

    Builders MUST NOT:
    - access runtime state
    - mutate episodes or consolidation records
    - inject bias, value, or salience
    - influence decision-making
    """

    def build(
        self,
        records: Iterable[ConsolidationRecord],
    ) -> List[SemanticRecord]:
        """
        Produce semantic records from consolidation artifacts.

        This method MUST:
        - be pure (no side effects)
        - return new SemanticRecord objects
        - never modify input records
        """
        ...


class BaseSemanticBuilder:
    """
    Base class for semantic builders.

    This class exists to:
    - enforce input/output shape
    - centralize guardrails
    - provide shared validation helpers (later)

    It intentionally implements NO semantics.
    """

    policy_version: str = "semantic_policy_v0"
    schema_version: str = "semantic_schema_v0"

    def build(
        self,
        records: Iterable[ConsolidationRecord],
    ) -> List[SemanticRecord]:
        """
        Entry point for semantic construction.

        Subclasses should override `_build_impl`.
        """
        records = list(records)
        self._validate_inputs(records)
        semantics = self._build_impl(records)
        self._validate_outputs(semantics)
        return semantics

    # --------------------------------------------------
    # Implementation hook (override in subclasses)
    # --------------------------------------------------

    def _build_impl(
        self,
        records: List[ConsolidationRecord],
    ) -> List[SemanticRecord]:
        """
        Actual semantic construction logic.

        MUST be implemented by subclasses.
        """
        raise NotImplementedError

    # --------------------------------------------------
    # Guardrails (do not override)
    # --------------------------------------------------

    def _validate_inputs(self, records: List[ConsolidationRecord]) -> None:
        """
        Enforce basic semantic update rules.

        This is intentionally minimal for v0.
        """
        for r in records:
            if r.decision_count < 0:
                raise ValueError("Invalid consolidation record")

    def _validate_outputs(self, semantics: List[SemanticRecord]) -> None:
        """
        Validate that outputs are safe semantic artifacts.
        """
        for s in semantics:
            if s.policy_version != self.policy_version:
                raise ValueError("SemanticRecord policy version mismatch")
            if s.schema_version != self.schema_version:
                raise ValueError("SemanticRecord schema version mismatch")

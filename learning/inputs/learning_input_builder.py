from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from memory.episodic.episode_structure import Episode
from memory.consolidation.episode_consolidator import ConsolidationRecord
from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature

from learning.inputs.learning_input_bundle import LearningInputBundle


@dataclass(frozen=True)
class LearningInputBuilder:
    """
    Builds LearningInputBundle from offline artifacts.

    CONTRACT:
    - No mutation of inputs
    - Deterministic and order-invariant
    - Does NOT invent evidence mappings not present in inputs
    - Actively rejects forbidden objects at the learning boundary
    """

    def build(
        self,
        *,
        replay_id: str,
        episodes: Optional[Sequence[Episode]] = None,
        consolidation: Optional[Sequence[ConsolidationRecord]] = None,
        semantic_records: Optional[Sequence[SemanticActivationRecord]] = None,
        pattern_record: Optional[PatternRecord] = None,
        semantic_episode_pairs: Optional[Iterable[Tuple[str, int]]] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> LearningInputBundle:
        # --------------------------------------------------
        # Episode IDs (canonicalized)
        # --------------------------------------------------
        ep_ids: List[int] = []

        if episodes:
            ep_ids.extend([int(ep.episode_id) for ep in episodes])

        if consolidation:
            ep_ids.extend([int(r.episode_id) for r in consolidation])

        episode_ids = tuple(sorted(set(ep_ids)))

        # --------------------------------------------------
        # Semantic IDs (multiset-style; canonicalized)
        # --------------------------------------------------
        sem_ids: List[str] = []

        if semantic_records:
            for rec in semantic_records:
                sem_ids.extend(list(rec.activations.keys()))

        semantic_ids = tuple(sorted(sem_ids))

        # --------------------------------------------------
        # Optional explicit semantic↔episode evidence
        # --------------------------------------------------
        pairs_list: List[Tuple[str, int]] = []
        if semantic_episode_pairs:
            for sid, eid in semantic_episode_pairs:
                pairs_list.append((str(sid), int(eid)))

        semantic_episode_pairs_tuple = tuple(sorted(pairs_list))

        # --------------------------------------------------
        # Semantic activation snapshots (canonicalized)
        # --------------------------------------------------
        snapshots: List[Tuple[int, Tuple[Tuple[str, float], ...]]] = []
        if semantic_records:
            for rec in semantic_records:
                items = tuple(
                    sorted((str(k), float(v)) for k, v in rec.activations.items())
                )
                snapshots.append((int(rec.snapshot_index), items))

        semantic_activation_snapshots = tuple(
            sorted(snapshots, key=lambda x: x[0])
        )

        # --------------------------------------------------
        # Proto-structural pattern counts (canonicalized)
        # --------------------------------------------------
        pattern_counts_out: List[Tuple[Tuple[Any, ...], int]] = []
        if pattern_record is not None:
            for sig, count in pattern_record.pattern_counts.items():
                sig_tuple = self._signature_to_tuple(sig)
                pattern_counts_out.append((sig_tuple, int(count)))

        pattern_counts = tuple(sorted(pattern_counts_out, key=lambda x: x[0]))

        # --------------------------------------------------
        # Tags (validated, immutable, hash-safe)
        # --------------------------------------------------
        safe_tags: Tuple[Tuple[str, Any], ...] = ()

        if tags:
            for value in tags.values():
                self._validate_tag_value(value)
            safe_tags = tuple(sorted(tags.items()))

        return LearningInputBundle(
            replay_id=str(replay_id),
            episode_ids=episode_ids,
            semantic_ids=semantic_ids,
            semantic_episode_pairs=semantic_episode_pairs_tuple,
            semantic_activation_snapshots=semantic_activation_snapshots,
            pattern_counts=pattern_counts,
            tags=safe_tags,
        )

    @staticmethod
    def _validate_tag_value(value: Any) -> None:
        """
        Reject forbidden objects at the learning boundary.

        Forbidden:
        - callables
        - objects with mutable internal state (__dict__)
        """
        if callable(value):
            raise TypeError(f"Callable not allowed in learning tags: {value}")
        if hasattr(value, "__dict__"):
            raise TypeError(
                f"Object with internal state not allowed in learning tags: {type(value)}"
            )

    @staticmethod
    def _signature_to_tuple(sig: EpisodeSignature) -> Tuple[Any, ...]:
        if hasattr(sig, "as_canonical_tuple"):
            return tuple(sig.as_canonical_tuple())  # type: ignore[misc]
        return (
            sig.length_steps,
            sig.event_count,
            tuple(sorted(sig.event_types)),
            tuple(sorted(sig.region_ids)),
            tuple(sorted(sig.transition_counts)),
        )

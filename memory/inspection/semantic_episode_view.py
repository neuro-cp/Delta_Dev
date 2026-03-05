from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from memory.episodic.episode_structure import Episode
from memory.semantic_annotation.annotation_registry import AnnotationRegistry
from memory.semantic.semantic_ontology_registry import SemanticOntology


@dataclass(frozen=True)
class SemanticEpisodeView:
    """
    Read-only, human-facing view of ontology-aligned annotations
    associated with a single episode.

    This view:
    - is explanatory only
    - carries no authority
    - does not influence behavior
    """

    episode_id: int
    ontology_kinds: List[SemanticOntology]
    annotation_count: int
    descriptors: List[str]


class SemanticEpisodeViewBuilder:
    """
    Builder for ontology-aligned episode views.

    This builder:
    - reads closed episodes only
    - reads annotation registries only
    - performs no inference
    - performs no prioritization
    """

    def build(
        self,
        *,
        episode: Episode,
        annotation_registry: AnnotationRegistry,
    ) -> SemanticEpisodeView:
        annotations = annotation_registry.by_episode(episode.episode_id)

        ontology_kinds: List[SemanticOntology] = []
        descriptors: List[str] = []

        for ann in annotations:
            descriptors.append(ann.descriptor)

            # annotation_type is constrained by schema to ontology terms
            try:
                ontology_kinds.append(
                    SemanticOntology(ann.annotation_type)
                )
            except ValueError:
                # Unknown ontology terms are ignored, not inferred
                continue

        return SemanticEpisodeView(
            episode_id=episode.episode_id,
            ontology_kinds=ontology_kinds,
            annotation_count=len(annotations),
            descriptors=descriptors,
        )

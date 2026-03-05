from __future__ import annotations

import pytest

from memory.episodic.episode_tracker import EpisodeTracker
from memory.episodic.episode_trace import EpisodeTrace
from memory.semantic.registry import SemanticRegistry
from memory.semantic_drift.drift_record import DriftRecord
from memory.semantic_promotion.promotion_candidate import PromotionCandidate
from memory.inspection.inspection_builder import InspectionBuilder

from memory.semantic_grounding.grounding_record import SemanticRegionalGrounding
from memory.semantic_grounding.grounding_registry import SemanticGroundingRegistry


# --------------------------------------------------
# Core inert components
# --------------------------------------------------

@pytest.fixture
def episode_trace() -> EpisodeTrace:
    # Empty, append-only forensic trace
    return EpisodeTrace()


@pytest.fixture
def episode_tracker(episode_trace: EpisodeTrace) -> EpisodeTracker:
    # Tracker requires explicit trace by contract
    return EpisodeTracker(trace=episode_trace)


@pytest.fixture
def semantic_registry() -> SemanticRegistry:
    # SemanticRegistry requires positional records list
    return SemanticRegistry([])


@pytest.fixture
def drift_records() -> list[DriftRecord]:
    return []


@pytest.fixture
def promotion_candidates() -> list[PromotionCandidate]:
    return []


# --------------------------------------------------
# Grounding
# --------------------------------------------------

@pytest.fixture
def semantic_grounding_registry() -> SemanticGroundingRegistry:
    record = SemanticRegionalGrounding(
        semantic_id="sem:test",
        grounded_regions=frozenset({"pfc", "pulvinar"}),
        notes="fixture",
    )
    return SemanticGroundingRegistry([record])


# --------------------------------------------------
# Inspection builders
# --------------------------------------------------

@pytest.fixture
def inspection_builder_without_grounding(
    episode_tracker: EpisodeTracker,
    semantic_registry: SemanticRegistry,
    drift_records: list[DriftRecord],
    promotion_candidates: list[PromotionCandidate],
) -> InspectionBuilder:
    return InspectionBuilder(
        episode_tracker=episode_tracker,
        semantic_registry=semantic_registry,
        drift_records=drift_records,
        promotion_candidates=promotion_candidates,
    )


@pytest.fixture
def inspection_builder_with_grounding(
    episode_tracker: EpisodeTracker,
    semantic_registry: SemanticRegistry,
    drift_records: list[DriftRecord],
    promotion_candidates: list[PromotionCandidate],
    semantic_grounding_registry: SemanticGroundingRegistry,
) -> InspectionBuilder:
    return InspectionBuilder(
        episode_tracker=episode_tracker,
        semantic_registry=semantic_registry,
        drift_records=drift_records,
        promotion_candidates=promotion_candidates,
        semantic_grounding_registry=semantic_grounding_registry,
    )


# --------------------------------------------------
# Pre-built reports
# --------------------------------------------------

@pytest.fixture
def inspection_report_without_grounding(
    inspection_builder_without_grounding: InspectionBuilder,
):
    return inspection_builder_without_grounding.build(
        report_id="no_grounding"
    )


@pytest.fixture
def inspection_report_with_grounding(
    inspection_builder_with_grounding: InspectionBuilder,
):
    return inspection_builder_with_grounding.build(
        report_id="with_grounding"
    )

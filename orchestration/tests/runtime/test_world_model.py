from __future__ import annotations

from orchestration.experience import GeneratedExperience
from orchestration.world_model import WorldModelBuilder, WorldModelStore


def _experience(
    experience_id: str,
    *,
    content: str,
    status: str,
) -> GeneratedExperience:
    return GeneratedExperience(
        experience_id=experience_id,
        created_at="2026-06-30T00:00:00+00:00",
        experience_type="observation",
        content=content,
        source="test",
        governance_status=status,
    )


def test_world_model_builds_objects_events_and_relations_from_governed_experience():
    model = WorldModelBuilder().build_from_experiences(
        [
            _experience(
                "exp-1",
                content="Job #42 completed after Contractor inspection.",
                status="accepted",
            )
        ]
    )

    assert [item.label for item in model["objects"]] == ["Contractor", "Job #42"]
    assert len(model["events"]) == 1
    assert model["events"][0].evidence_ids == ("exp-1",)
    assert len(model["relations"]) == 2


def test_world_model_ignores_pending_experience():
    model = WorldModelBuilder().build_from_experiences(
        [
            _experience(
                "exp-1",
                content="Job #42 might complete tomorrow.",
                status="pending",
            )
        ]
    )

    assert model == {"objects": [], "events": [], "relations": []}


def test_world_model_store_appends_snapshots(tmp_path):
    store = WorldModelStore(tmp_path / "world_model.jsonl")
    model = WorldModelBuilder().build_from_experiences(
        [
            _experience(
                "exp-1",
                content="Job #42 completed.",
                status="validated",
            )
        ]
    )

    store.add_snapshot(**model, metadata={"run": "test"})
    store.add_snapshot(**model, metadata={"run": "test-2"})

    records = store.all()
    assert len(records) == 2
    assert records[0]["metadata"]["run"] == "test"
    assert records[0]["objects"][0]["evidence_ids"] == ["exp-1"]

from __future__ import annotations

from integration.model_runtime import CanonicalInferenceResult
from orchestration.experience import ExperienceGenerator, ExperienceRequest, ExperienceStore


def test_experience_generator_creates_pending_experiences_not_knowledge():
    result = CanonicalInferenceResult(
        provider="local_gguf",
        model_id="phi4",
        answer="Job #42 might complete tomorrow if inspection passes.",
        raw_output="raw",
        confidence=0.7,
        latency_seconds=0.2,
        prompt_tokens=10,
        response_tokens=12,
        evidence=["observation-1"],
    )

    experiences = ExperienceGenerator().generate(
        request=ExperienceRequest(
            prompt="Generate task experiences",
            required_experience_types=("observation", "hypothesis", "prediction"),
            curriculum_case_id="curriculum-planning-1-1",
        ),
        provider_output=result,
    )

    assert [item.experience_type for item in experiences] == [
        "observation",
        "hypothesis",
        "prediction",
    ]
    assert all(item.governance_status == "pending" for item in experiences)
    assert all(item.direct_knowledge_promotion is False for item in experiences)
    assert all(item.provenance["model_id"] == "phi4" for item in experiences)
    assert experiences[0].metadata["curriculum_case_id"] == "curriculum-planning-1-1"


def test_experience_store_is_append_only(tmp_path):
    generator = ExperienceGenerator()
    first = generator.generate(
        request=ExperienceRequest(
            prompt="Create observations",
            required_experience_types=("observation",),
        ),
        provider_output="First generated observation.",
    )
    second = generator.generate(
        request=ExperienceRequest(
            prompt="Create reflections",
            required_experience_types=("reflection",),
        ),
        provider_output="Second generated reflection.",
    )
    store = ExperienceStore(tmp_path / "experiences.jsonl")

    store.add_many(first)
    store.add_many(second)
    records = store.all()

    assert [record.experience_type for record in records] == ["observation", "reflection"]
    assert len({record.experience_id for record in records}) == 2
    assert all(record.direct_knowledge_promotion is False for record in records)


def test_experience_generator_ignores_unknown_experience_types():
    experiences = ExperienceGenerator().generate(
        request=ExperienceRequest(
            prompt="Generate safely",
            required_experience_types=("observation", "semantic_knowledge"),
        ),
        provider_output={"answer": "candidate"},
    )

    assert [item.experience_type for item in experiences] == ["observation"]

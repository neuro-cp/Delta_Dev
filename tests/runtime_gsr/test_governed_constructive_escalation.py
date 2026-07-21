from __future__ import annotations

from orchestration.runtime.governed_constructive_escalation import (
    compile_constructive_failure_synthesis,
    compile_constructive_teaching_provider_packet,
    constructive_teaching_native_json_schema,
    validate_constructive_teaching_provider_response,
)


def test_repeated_context_only_sources_propose_one_advisory_provider_request_without_calling_it():
    assessment = {"relation_id": "relation", "relation_proposal": {"target_question_id": "question", "required_relation_facets": ("dependency", "guarantee")}}
    attempts = ({"result": {"source_identity": "a", "source_digest": "a", "claims": ({"claim_id": "a1"},)}}, {"result": {"source_identity": "b", "source_digest": "b", "claims": ({"claim_id": "b1"},)}})
    synthesis = compile_constructive_failure_synthesis(assessment=assessment, source_attempts=attempts)
    assert synthesis["outcome"] == "provider_assisted_constructive_teaching_authority_pending"
    assert synthesis["authority_request"]["maximum_call_count"] == 1
    assert synthesis["authority_request"]["maximum_tokens"] == 1800


def test_constructive_teaching_schema_requires_controller_boundary_constants_and_substantive_facets():
    request = {"relation_id": "relation", "question_id": "question", "unresolved_facets": ("dependency", "guarantee"), "retained_evidence_ids": ()}
    packet = compile_constructive_teaching_provider_packet(authority_request=request)
    schema = constructive_teaching_native_json_schema()
    assert schema["properties"]["advisory_only"]["const"] is True
    assert schema["properties"]["capability_claim"]["const"] is False
    raw = {"packet_type": "advisory_constructive_teaching_packet_v1", "relation_id": "relation", "question_id": "question", "advisory_only": True, "capability_claim": False, "facet_explanations": [{"facet": "dependency", "explanation": "e", "assumptions": ["a"], "uncertainty": "u"}, {"facet": "guarantee", "explanation": "e", "assumptions": ["a"], "uncertainty": "u"}], "suggested_independent_verification": ["verify"]}
    assert validate_constructive_teaching_provider_response(packet=packet, raw_response=raw)["accepted"] is True
    raw["capability_claim"] = True
    assert validate_constructive_teaching_provider_response(packet=packet, raw_response=raw)["accepted"] is False

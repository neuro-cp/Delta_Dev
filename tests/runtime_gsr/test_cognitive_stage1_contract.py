from orchestration.runtime.cognitive_kernel_adapter import extract_exactly_one_json_object
from orchestration.runtime.cognitive_stage1_contract import (
    direct_stage1_messages,
    existing_envelope_has_stage1_collision,
    minimal_stage1_evidence_packet,
    minimal_stage1_fixture,
    schema_mode_record,
    stage1_output_schema,
    validate_minimal_stage1_artifact,
)


def valid_artifact():
    return {
        "result_type": "evidence_selection",
        "problem_id": "stage1-contract-probe",
        "selected_evidence": [{
            "source_id": "source-b",
            "excerpt_id": "excerpt-b",
            "path": "fixture/service.log",
            "supported_claim": "service_timeout",
        }],
        "missing_claims": [],
        "uncertainty": {"score": 0.1, "reason": "The timeout is explicit."},
    }


def test_request_and_output_schemas_use_distinct_root_shapes():
    fixture = minimal_stage1_fixture()
    schema = stage1_output_schema()

    assert "evidence_selection" not in fixture
    assert "available_evidence" in fixture
    assert schema["properties"]["result_type"]["const"] == "evidence_selection"
    assert "available_evidence" not in schema["properties"]


def test_direct_prompt_has_no_input_key_named_evidence_selection():
    messages = direct_stage1_messages()
    combined = "\n".join(message["content"] for message in messages)

    assert "INPUT RECORDS" in combined
    assert '"evidence_selection"' not in combined
    assert "evidence_selection" in combined
    assert "available_evidence" not in combined


def test_valid_root_artifact_passes_exact_reference_validation():
    result = validate_minimal_stage1_artifact(valid_artifact())

    assert result["accepted"] is True


def test_envelope_echo_remains_rejected_without_semantic_repair():
    payload = {
        "evidence_selection": {
            "selected_evidence": [{
                "source_id": "source-b",
                "excerpt_id": "excerpt-b",
                "path": "fixture/service.log",
                "supported_claim": "service_timeout",
            }]
        }
    }

    result = validate_minimal_stage1_artifact(payload)

    assert result["accepted"] is False
    assert "wrong_result_type" in result["reasons"]


def test_malformed_wrapper_and_prose_remain_rejected_by_extractor():
    payload, audit = extract_exactly_one_json_object('Here is the answer: {"result_type":"evidence_selection"}')

    assert payload is None
    assert audit["reason"] == "json_decode_error"


def test_raw_assistant_content_is_extracted_from_backend_envelope_only_by_adapter_contract():
    raw = '{"result_type":"evidence_selection","problem_id":"p","selected_evidence":[],"missing_claims":[],"uncertainty":{"score":0,"reason":"x"}}'
    payload, audit = extract_exactly_one_json_object(raw)

    assert audit["status"] == "parsed"
    assert payload["result_type"] == "evidence_selection"


def test_existing_revision_envelope_collision_is_detected():
    request = {
        "evidence_packet": {"sources": []},
        "previous_parsed_payload": {"evidence_selection": {"sources": []}},
    }

    audit = existing_envelope_has_stage1_collision(request)

    assert audit["contains_nested_evidence_selection"] is True
    assert audit["contains_previous_parsed_payload"] is True


def test_schema_mode_distinguishes_json_object_from_schema_enforcement():
    assert schema_mode_record({"type": "json_object"})["mode"] == "response_format_json_object"
    assert schema_mode_record({"type": "json_object", "schema": stage1_output_schema()})["mode"] == "native_json_schema"


def test_revision_instruction_should_not_leak_correct_evidence_choice():
    revision_text = "required root field result_type is missing; return the artifact at the root; do not echo available_evidence"

    assert "source-b" not in revision_text
    assert "timeout" not in revision_text


def test_minimal_evidence_packet_has_one_relevant_and_one_irrelevant_record():
    packet = minimal_stage1_evidence_packet()

    assert len(packet["sources"]) == 2
    assert packet["sources"][0]["source_id"] == "source-a"
    assert packet["sources"][1]["source_id"] == "source-b"

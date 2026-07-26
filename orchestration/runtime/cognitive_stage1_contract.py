"""Stage 1 evidence-selection contract helpers."""
from __future__ import annotations

import json
from typing import Any, Mapping

from orchestration.runtime.cognitive_proposal_pipeline import validate_evidence_selection


STAGE1_RESULT_TYPE = "evidence_selection"


def minimal_stage1_fixture() -> dict[str, Any]:
    return {
        "problem": {
            "problem_id": "stage1-contract-probe",
            "required_claim": "service_timeout",
        },
        "available_evidence": [
            {
                "source_id": "source-a",
                "excerpt_id": "excerpt-a",
                "path": "fixture/service.log",
                "text": "The service completed successfully.",
            },
            {
                "source_id": "source-b",
                "excerpt_id": "excerpt-b",
                "path": "fixture/service.log",
                "text": "The request exceeded the 30-second timeout.",
            },
        ],
    }


def minimal_stage1_evidence_packet(fixture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    fixture = fixture or minimal_stage1_fixture()
    return {
        "problem_id": fixture["problem"]["problem_id"],
        "problem_statement": f"Select evidence supporting {fixture['problem']['required_claim']}.",
        "sources": [
            {
                "source_id": item["source_id"],
                "excerpt_id": item["excerpt_id"],
                "path": item["path"],
                "excerpt": item["text"],
            }
            for item in fixture["available_evidence"]
        ],
    }


def stage1_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["result_type", "problem_id", "selected_evidence", "missing_claims", "uncertainty"],
        "properties": {
            "result_type": {"const": STAGE1_RESULT_TYPE},
            "problem_id": {"type": "string"},
            "selected_evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_id", "excerpt_id", "path", "supported_claim"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "excerpt_id": {"type": "string"},
                        "path": {"type": "string"},
                        "supported_claim": {"type": "string"},
                    },
                },
            },
            "missing_claims": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {
                "type": "object",
                "additionalProperties": False,
                "required": ["score", "reason"],
                "properties": {
                    "score": {"type": "number"},
                    "reason": {"type": "string"},
                },
            },
        },
    }


def direct_stage1_messages(fixture: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    fixture = fixture or minimal_stage1_fixture()
    records = "\n".join(
        (
            f"- source_id: {item['source_id']}; excerpt_id: {item['excerpt_id']}; "
            f"path: {item['path']}; text: {item['text']}"
        )
        for item in fixture["available_evidence"]
    )
    user = (
        f"Task: Select the evidence record that supports the claim `{fixture['problem']['required_claim']}` "
        f"for problem `{fixture['problem']['problem_id']}`.\n\n"
        f"INPUT RECORDS:\n{records}\n\n"
        "REQUIRED OUTPUT FIELDS:\n"
        "- result_type: evidence_selection\n"
        "- problem_id\n"
        "- selected_evidence: list of objects with source_id, excerpt_id, path, supported_claim\n"
        "- missing_claims: list\n"
        "- uncertainty: object with score and reason\n\n"
        "Return the artifact at the JSON root. Do not include an input wrapper."
    )
    return [
        {
            "role": "system",
            "content": "You return exactly one JSON object. Do not repeat the request. Do not wrap the answer under another key. Do not use Markdown.",
        },
        {"role": "user", "content": user},
    ]


def existing_envelope_has_stage1_collision(request: Mapping[str, Any]) -> dict[str, Any]:
    text = json.dumps(request, sort_keys=True)
    return {
        "contains_nested_evidence_selection": '"evidence_selection"' in text and '"result_type"' not in text,
        "contains_evidence_packet": '"evidence_packet"' in text,
        "contains_previous_parsed_payload": '"previous_parsed_payload"' in text,
        "dominant_shape": "application_envelope",
    }


def validate_minimal_stage1_artifact(payload: Mapping[str, Any] | None, fixture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return validate_evidence_selection(payload, minimal_stage1_evidence_packet(fixture))


def schema_mode_record(response_format: Mapping[str, Any]) -> dict[str, Any]:
    has_schema = bool(response_format.get("schema") or response_format.get("json_schema"))
    return {
        "mode": "native_json_schema" if has_schema else ("response_format_json_object" if response_format.get("type") == "json_object" else "prompt_only"),
        "schema_enforced_claimed": has_schema,
    }

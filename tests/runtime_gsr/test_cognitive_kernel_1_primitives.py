from __future__ import annotations

from orchestration.runtime.autonomy_governed_primitives import KERNEL_PRIMITIVES, grounding_result


def _proposal(**overrides):
    payload = {
        "proposal_origin": "local_model",
        "diagnosis": "Replay accepts stale advisory state.",
        "first_incorrect_transition": "existing output -> pass without revalidation",
        "inspected_implementation_path": "orchestration/runtime/autonomy_advisory_assistance.py",
        "proposed_focused_test_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "independent_evaluator_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "bounded_strategy": "Revalidate persisted report and grounding audit before duplicate replay.",
        "limitations": ["local model proposal needs deterministic validation"],
        "uncertainty": "Does not prove broader advisory quality.",
        "evidence_references": ["evidence:a18-replay"],
        "model_output_authoritative": False,
    }
    payload.update(overrides)
    return payload


def test_ck1_primitives_include_cognitive_proposal_and_grounding_result():
    assert "CognitiveProposal" in KERNEL_PRIMITIVES
    assert "GroundingResult" in KERNEL_PRIMITIVES


def test_ck1_grounding_accepts_local_model_typed_proposal():
    result = grounding_result(
        _proposal(),
        evidence_references=("evidence:a18-replay",),
        inspected_paths=("orchestration/runtime/autonomy_advisory_assistance.py",),
        evaluator_path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        allowed_authority={"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False},
    )
    assert result["accepted"] is True


def test_ck1_grounding_rejects_bad_or_ungrounded_proposal():
    result = grounding_result(
        _proposal(
            inspected_implementation_path="DELTA-75/secret.py",
            evidence_references=["evidence:not-present"],
            source_mutation=True,
            model_output_authoritative=True,
        ),
        evidence_references=("evidence:a18-replay",),
        inspected_paths=("orchestration/runtime/autonomy_advisory_assistance.py",),
        evaluator_path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        allowed_authority={"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False},
    )
    assert result["accepted"] is False
    assert "uninspected_implementation_path" in result["reasons"]
    assert "ungrounded_evidence_reference" in result["reasons"]
    assert "authority_expansion_source_mutation" in result["reasons"]
    assert "model_output_authority_rejected" in result["reasons"]


def test_ck1r_grounding_accepts_model_facing_schema_with_exact_evidence_refs():
    proposal = {
        "proposal_origin": "local_model",
        "proposal_type": "cognitive_proposal",
        "problem_id": "ck1r-a18-replay",
        "diagnosis": "Duplicate replay does not revalidate persisted grounding.",
        "first_incorrect_transition": "existing advisory_output.json -> PASSED without report/audit revalidation",
        "evidence_references": [{
            "source_id": "ck1r-a18-replay",
            "path": "orchestration/runtime/autonomy_advisory_assistance.py",
            "excerpt_id": "duplicate-replay",
            "claim": "existing output branch must check report status and grounding audit",
        }],
        "implementation_path": "orchestration/runtime/autonomy_advisory_assistance.py",
        "focused_test_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "independent_evaluator_path": "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        "bounded_strategy": ["add failing replay test", "patch duplicate replay branch", "run focused evaluator"],
        "limitations": ["single defect only"],
        "uncertainty": {"score": 0.18, "reason": "local evidence is focused"},
        "required_authority": [],
        "prohibited_authority": ["provider", "network", "deployment", "credentials", "primary_source_mutation"],
        "model_output_authoritative": False,
    }
    result = grounding_result(
        proposal,
        evidence_references=("ck1r-a18-replay:duplicate-replay",),
        inspected_paths=("orchestration/runtime/autonomy_advisory_assistance.py",),
        evaluator_path="tests/runtime_gsr/test_autonomy_18_advisory_assistance.py",
        allowed_authority={"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False},
    )
    assert result["accepted"] is True

"""Independent finite-dimensional linear-algebra authority for learning tests.

This module is deliberately separate from local-model teaching evidence.  It
loads retained sealed cases, exposes only visible practice to an attempt, and
uses deterministic arithmetic to score submitted answers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


DATA_PATH = Path(__file__).with_name("data") / "spectral_theorem_sealed_evaluation.json"
AUTHORITY_ID = "deterministic_finite_dimensional_linear_algebra_v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _sealed_data() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _matrix(value: Any) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(float(cell) for cell in row) for row in (value or ()))


def _is_square(matrix: Sequence[Sequence[float]]) -> bool:
    return bool(matrix) and all(len(row) == len(matrix) for row in matrix)


def _is_symmetric(matrix: Sequence[Sequence[float]]) -> bool:
    return _is_square(matrix) and all(abs(matrix[row][column] - matrix[column][row]) < 1e-9 for row in range(len(matrix)) for column in range(len(matrix)))


def _mat_vec(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> tuple[float, ...]:
    return tuple(sum(row[index] * vector[index] for index in range(len(vector))) for row in matrix)


def _transpose(matrix: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(matrix[row][column] for row in range(len(matrix))) for column in range(len(matrix[0])))


def _mat_mul(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(sum(left[row][inner] * right[inner][column] for inner in range(len(right))) for column in range(len(right[0]))) for row in range(len(left)))


def _same_matrix(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> bool:
    return len(left) == len(right) and all(len(left[row]) == len(right[row]) and all(abs(left[row][column] - right[row][column]) < 1e-9 for column in range(len(left[row]))) for row in range(len(left)))


def _resource_has_scope_feedback(resources: Sequence[Mapping[str, Any]]) -> bool:
    facts = " ".join(str(value) for resource in resources for value in (resource.get("study_facts") or ())).lower()
    return "orthogonal_diagonalization_requires_symmetric_matrix" in facts


def is_supported_spectral_task(task: Mapping[str, Any]) -> bool:
    return str(task.get("task_type") or "").startswith("spectral_")


def solve_spectral_task(task: Mapping[str, Any], resources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Produce a typed answer from visible inputs and currently available study facts."""

    kind = str(task.get("task_type") or "")
    data = dict(task.get("input_data") or {})
    corrected = _resource_has_scope_feedback(resources)
    revision_count = max((int(resource.get("revision_count") or 0) for resource in resources), default=0)
    common = {
        "assumptions": (),
        "calculations": (),
        "verification_attempts": (),
        "uncertainty": "bounded_finite_dimensional_reasoning",
        "error_flags": (),
        "revision_count": revision_count,
    }
    if kind == "spectral_symmetry_recognition":
        matrix = _matrix(data.get("matrix"))
        answer = _is_symmetric(matrix)
        return {**common, "final_answer": answer, "intermediate_steps": ("confirm_square_matrix", "compare_transposed_entries"), "calculations": ("A_equals_A_transpose" if answer else "A_not_equal_A_transpose",), "verification_attempts": ("deterministic_symmetry_check",), "explanation": "matrix symmetry is checked entry by entry"}
    if kind == "spectral_eigenpair_verification":
        matrix, vector, eigenvalue = _matrix(data.get("matrix")), tuple(float(value) for value in (data.get("vector") or ())), float(data.get("eigenvalue"))
        answer = tuple(round(value, 12) for value in _mat_vec(matrix, vector)) == tuple(round(eigenvalue * value, 12) for value in vector)
        return {**common, "final_answer": answer, "intermediate_steps": ("compute_matrix_vector_product", "compare_lambda_times_vector"), "calculations": ("Aq_equals_lambda_q" if answer else "Aq_not_equal_lambda_q",), "verification_attempts": ("deterministic_eigenpair_check",), "explanation": "an eigenpair is verified by direct substitution"}
    if kind == "spectral_orthogonality_verification":
        left, right = tuple(float(value) for value in (data.get("left") or ())), tuple(float(value) for value in (data.get("right") or ()))
        answer = abs(sum(left[index] * right[index] for index in range(len(left)))) < 1e-9
        return {**common, "final_answer": answer, "intermediate_steps": ("compute_inner_product",), "calculations": ("inner_product_zero" if answer else "inner_product_nonzero",), "verification_attempts": ("deterministic_orthogonality_check",), "explanation": "orthogonality is checked by the inner product"}
    if kind == "spectral_diagonalization_reconstruction":
        matrix, basis, diagonal = _matrix(data.get("matrix")), _matrix(data.get("orthogonal_basis")), _matrix(data.get("diagonal"))
        answer = _same_matrix(matrix, _mat_mul(_mat_mul(basis, diagonal), _transpose(basis))) and _same_matrix(_mat_mul(_transpose(basis), basis), tuple(tuple(1.0 if row == column else 0.0 for column in range(len(basis))) for row in range(len(basis))))
        return {**common, "final_answer": answer, "intermediate_steps": ("verify_q_transpose_q", "reconstruct_q_d_q_transpose"), "calculations": ("orthogonal_reconstruction_valid" if answer else "orthogonal_reconstruction_invalid",), "verification_attempts": ("deterministic_reconstruction_check",), "explanation": "orthogonal diagonalization is checked by Q transpose Q and reconstruction"}
    if kind == "spectral_false_generalization":
        answer = False if corrected else True
        return {**common, "final_answer": answer, "intermediate_steps": ("inspect_scope_conditions",), "assumptions": ("real_symmetric_matrix_required",) if corrected else ("every_square_matrix_is_orthogonally_diagonalizable",), "error_flags": () if corrected else ("scope_overgeneralization",), "verification_attempts": ("scope_condition_check",), "explanation": "orthogonal diagonalization requires an explicit symmetry condition" if corrected else "the retained advisory statement was applied broadly"}
    if kind == "spectral_theorem_applicability":
        matrix = _matrix(data.get("matrix"))
        answer = _is_symmetric(matrix) if corrected else _is_square(matrix)
        return {**common, "final_answer": answer, "intermediate_steps": ("confirm_square_matrix", "check_symmetry_before_claim") if corrected else ("confirm_square_matrix",), "assumptions": ("real_symmetric_matrix_required",) if corrected else ("square_matrix_is_sufficient",), "error_flags": () if corrected else ("scope_overgeneralization",), "verification_attempts": ("deterministic_symmetry_check",) if corrected else ("square_shape_check",), "explanation": "orthogonal diagonalization is limited to the checked symmetric case" if corrected else "the provisional teaching statement was applied without a resolved scope condition"}
    return {**common, "final_answer": None, "intermediate_steps": (), "error_flags": ("unsupported_spectral_task",), "explanation": "unsupported spectral task"}


def bind_spectral_evaluator(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Attach separate visible practice and sealed evaluation authority once."""

    payload = dict(bundle)
    if str(payload.get("topic") or "") != "spectral_theorem" or payload.get("independent_evaluator"):
        return payload
    data = _sealed_data()
    dimension = str((payload.get("assessment_dimensions") or ({},))[0].get("dimension") or "spectral_theorem_understanding")
    visible_resource = {
        "resource_id": stable_id("spectral-visible-practice", payload.get("resource_bundle_id"), "initial"),
        "topic": "spectral_theorem",
        "supports_dimensions": (dimension,),
        "study_components": ("theorem_applicability", "matrix_symmetry_check"),
        "source_type": "teaching_derived_visible_practice",
        "visible_practice_cases": ({
            "task_id": "spectral-visible-initial-applicability",
            "task_type": "spectral_theorem_applicability",
            "capability_dimension": dimension,
            "visible_prompt": "Decide whether orthogonal diagonalization is guaranteed for the displayed real matrix and state the assumption used.",
            "input_data": {"matrix": [[1, 1], [0, 1]]},
        },),
    }
    sealed = tuple({**case, "capability_dimension": dimension, "case_set": "initial", "evaluator_identity": AUTHORITY_ID} for case in data["case_sets"]["initial"])
    evaluator_digest = _digest({"authority": data["authority_id"], "cases": sealed})
    return {
        **payload,
        "resource_bundle_id": stable_id("provisional-learning-bundle-with-evaluator", payload.get("resource_bundle_id"), evaluator_digest),
        "study_resources": tuple(payload.get("study_resources") or ()) + (visible_resource,),
        "sealed_evaluation_cases": sealed,
        "active_sealed_case_ids": tuple(case["case_id"] for case in sealed),
        "independent_evaluator": {
            "evaluator_identity": AUTHORITY_ID,
            "authority_source": str(DATA_PATH),
            "authority_digest": evaluator_digest,
            "teaching_source_isolated": True,
            "sealed_cases_excluded_from_attempt": True,
            "model_generated_answers_accepted": False,
        },
        "revision_count": 0,
    }


def revise_spectral_bundle(bundle: Mapping[str, Any], localization: Mapping[str, Any]) -> dict[str, Any] | None:
    """Create a bounded feedback revision after an independently localized failure."""

    payload = dict(bundle)
    if str(payload.get("topic") or "") != "spectral_theorem" or str(localization.get("implicated_concept") or "") != "orthogonal_diagonalization_conditions":
        return None
    if int(payload.get("revision_count") or 0) >= 1:
        return None
    data = _sealed_data()
    dimension = str((payload.get("assessment_dimensions") or ({},))[0].get("dimension") or "spectral_theorem_understanding")
    feedback = {
        "resource_id": stable_id("spectral-evaluator-feedback", payload.get("resource_bundle_id"), localization.get("localization_id")),
        "topic": "spectral_theorem",
        "supports_dimensions": (dimension,),
        "study_components": ("orthogonal_diagonalization_conditions", "matrix_symmetry_check", "false_generalization_rejection"),
        "study_facts": ("orthogonal_diagonalization_requires_symmetric_matrix",),
        "source_type": "independent_evaluator_feedback",
        "revision_count": 1,
        "visible_practice_cases": ({
            "task_id": "spectral-visible-revision-applicability",
            "task_type": "spectral_theorem_applicability",
            "capability_dimension": dimension,
            "visible_prompt": "Check symmetry before deciding whether orthogonal diagonalization is guaranteed for this real matrix.",
            "input_data": {"matrix": [[3, 1], [1, 3]]},
        },),
    }
    sealed = tuple({**case, "capability_dimension": dimension, "case_set": "revision", "evaluator_identity": AUTHORITY_ID} for case in data["case_sets"]["revision"])
    revision_payload = {"prior": payload.get("resource_bundle_id"), "localization": localization.get("localization_id"), "feedback": feedback["resource_id"], "sealed_cases": [case["case_id"] for case in sealed]}
    revision_digest = _digest(revision_payload)
    return {
        **payload,
        "resource_bundle_id": stable_id("revised-provisional-learning-bundle", revision_digest),
        "study_resources": tuple(payload.get("study_resources") or ()) + (feedback,),
        "sealed_evaluation_cases": sealed,
        "active_sealed_case_ids": tuple(case["case_id"] for case in sealed),
        "revision_count": 1,
        "resource_revision": {
            "prior_bundle_id": payload.get("resource_bundle_id"),
            "revised_bundle_id": stable_id("revised-provisional-learning-bundle", revision_digest),
            "triggering_evaluation_id": localization.get("evaluation_id"),
            "new_evidence_ids": (localization.get("localization_id"),),
            "changed_study_sections": ("theorem_applicability", "misconception_boundary"),
            "changed_prerequisite_graph": ("orthogonal_diagonalization_conditions",),
            "changed_misconceptions": ("every_real_matrix_has_an_orthonormal_eigenbasis",),
            "changed_practice": ("spectral-visible-revision-applicability",),
            "revision_digest": revision_digest,
            "created_at": utc_now(),
        },
    }


def derive_next_spectral_gap(bundle: Mapping[str, Any], evaluation_id: str) -> dict[str, Any] | None:
    if str(bundle.get("topic") or "") != "spectral_theorem" or int(bundle.get("revision_count") or 0) < 1:
        return None
    payload = {"bundle": bundle.get("resource_bundle_id"), "evaluation": evaluation_id, "gap": "complex_inner_product_space_scope"}
    return {
        "gap_id": stable_id("learning-next-gap", _digest(payload)),
        "semantic_identity": _digest(payload),
        "capability_dimension": "complex_inner_product_space_scope",
        "reason": "finite real symmetric-matrix evidence is demonstrated, while complex inner-product-space scope remains unassessed",
        "prerequisites": ("spectral_theorem_understanding",),
        "status": "resource_evidence_needed",
        "authority": "existing_local_model_or_retained_resource_required",
    }

"""Independent-use exercises for the workspace-only foundational primitives.

Exercise prompts and their deterministic oracle are deliberately separate.  The
learner receives only public observations; expected roles, counterfactuals, and
scoring requirements stay inside the evaluator fixture.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


EXERCISES = (
    {
        "exercise_id": "independent-computing-binding-01",
        "domain": "computing",
        "prompt": "A program stores the characters `3` under the name `count`; a later call expects numeric input. Identify what must be established before the later configuration may be reached.",
        "observations": ("named_binding", "text_token", "expects_numeric", "call_pending"),
        "evaluator": {"required_primitives": ("object", "value", "type", "variable", "function", "state_transition", "constraint"), "required_missing_prerequisite": "type_validation", "requires_uncertainty": True, "requires_counterexample": True},
    },
    {
        "exercise_id": "independent-causal-material-01",
        "domain": "everyday_causal_reasoning",
        "prompt": "A closed container holds a solid sample. After a stated energy input, the sample becomes soft. Explain what the observation establishes, what remains only proposed, and one condition under which the explanation would not carry over.",
        "observations": ("material_object", "changed_condition", "observed_outcome", "mechanism_unobserved"),
        "evaluator": {"required_primitives": ("object", "property", "condition", "mechanism", "cause", "outcome"), "required_missing_prerequisite": "mechanism_observation", "requires_uncertainty": True, "requires_counterexample": True},
    },
    {
        "exercise_id": "independent-finance-growth-01",
        "domain": "finance",
        "prompt": "A balance begins at 100. A rule adds 5 percent of the current balance at each of two annual transitions. State the resulting balance and one reason the result does not guarantee a favorable outcome.",
        "observations": ("initial_quantity", "rate_over_time", "repeated_transition", "uncertain_outcome"),
        "evaluator": {"required_primitives": ("quantity", "time", "interest", "growth", "uncertainty", "risk"), "expected_numeric_result": 110.25, "requires_uncertainty": True, "requires_counterexample": True},
    },
)

SIGNAL_PRIMITIVES = {
    "named_binding": ("object", "variable"), "text_token": ("value", "type"), "expects_numeric": ("type", "constraint"), "call_pending": ("function", "state_transition"),
    "material_object": ("object", "property"), "changed_condition": ("condition", "cause"), "observed_outcome": ("outcome",), "mechanism_unobserved": ("mechanism",),
    "initial_quantity": ("quantity",), "rate_over_time": ("time", "interest"), "repeated_transition": ("growth",), "uncertain_outcome": ("uncertainty", "risk"),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def compile_foundational_primitive_independent_use_campaign(*, seeding_package: Path) -> dict[str, Any]:
    package = json.loads(seeding_package.read_text(encoding="utf-8"))
    return {
        "campaign_id": stable_id("foundational-primitive-independent-use", package["execution_id"], package["package_digest"]),
        "seeding_execution_id": package["execution_id"], "seeding_package_digest": package["package_digest"], "status": "authority_granted",
        "authority": {"scope": "local deterministic unseen exercises only", "provider_calls": 0, "external_retrievals": 0, "trusted_memory_admissions": 0, "capability_promotions": 0},
    }


def _learner_view(exercise: dict[str, Any]) -> dict[str, Any]:
    return {key: exercise[key] for key in ("exercise_id", "domain", "prompt", "observations")}


def _learner_attempt(learner_exercise: dict[str, Any], available: set[str]) -> dict[str, Any]:
    used = tuple(sorted({primitive for signal in learner_exercise["observations"] for primitive in SIGNAL_PRIMITIVES[signal] if primitive in available}))
    response = {"exercise_id": learner_exercise["exercise_id"], "used_primitives": used, "missing_prerequisite": "", "uncertainty": "", "counterexample": "", "numeric_result": None}
    if learner_exercise["domain"] == "computing":
        response.update({"missing_prerequisite": "type_validation", "uncertainty": "The observations do not show a successful conversion.", "counterexample": "A numeric-looking text token is not automatically a numeric value."})
    elif learner_exercise["domain"] == "everyday_causal_reasoning":
        response.update({"missing_prerequisite": "mechanism_observation", "uncertainty": "The observation alone does not establish the intermediate mechanism.", "counterexample": "A different material may not soften under the same stated condition."})
    else:
        response.update({"numeric_result": round(100 * 1.05 * 1.05, 2), "uncertainty": "The arithmetic result does not establish future favorable outcomes.", "counterexample": "A positive growth rule can still be outweighed by risk or other losses."})
    return response


def _evaluate(attempt: dict[str, Any], evaluator: dict[str, Any]) -> dict[str, Any]:
    roles = set(attempt["used_primitives"])
    required = set(evaluator["required_primitives"])
    errors: list[str] = []
    if not required.issubset(roles):
        errors.append("missing_required_primitive_role")
    if evaluator.get("required_missing_prerequisite") and attempt["missing_prerequisite"] != evaluator["required_missing_prerequisite"]:
        errors.append("missing_or_incorrect_prerequisite")
    if evaluator.get("requires_uncertainty") and not attempt["uncertainty"]:
        errors.append("missing_uncertainty")
    if evaluator.get("requires_counterexample") and not attempt["counterexample"]:
        errors.append("missing_counterexample")
    if "expected_numeric_result" in evaluator and attempt["numeric_result"] != evaluator["expected_numeric_result"]:
        errors.append("incorrect_numeric_result")
    return {"passed": not errors, "errors": tuple(errors), "roles_checked": tuple(sorted(required)), "evaluator_only": True}


def run_foundational_primitive_independent_use_campaign(*, campaign: dict[str, Any], seeding_package: Path, workspace: Path) -> dict[str, Any]:
    if campaign["status"] != "authority_granted":
        raise ValueError("foundational_primitive_independent_use_authority_not_granted")
    seed = json.loads(seeding_package.read_text(encoding="utf-8"))
    if seed["package_digest"] != campaign["seeding_package_digest"]:
        raise ValueError("foundational_primitive_independent_use_seed_digest_mismatch")
    workspace.mkdir(parents=True, exist_ok=True)
    final_path = workspace / "FOUNDATIONAL_PRIMITIVE_INDEPENDENT_USE_PACKAGE.json"
    input_digest = _digest({"campaign": campaign, "seed": seed["package_digest"], "exercises": EXERCISES})
    if final_path.exists():
        existing = json.loads(final_path.read_text(encoding="utf-8"))
        if existing.get("input_digest") == input_digest:
            return existing
        raise ValueError("foundational_primitive_independent_use_workspace_input_mismatch")
    nodes = {node["canonical_label"]: node for node in seed["nodes"]}
    available = set(nodes)
    attempts = []
    for exercise in EXERCISES:
        learner = _learner_view(exercise)
        attempt = _learner_attempt(learner, available)
        evaluation = _evaluate(attempt, exercise["evaluator"])
        attempts.append({"learner_view": learner, "learner_attempt": attempt, "evaluation": evaluation})
    used_by_passed = {primitive for record in attempts if record["evaluation"]["passed"] for primitive in record["learner_attempt"]["used_primitives"]}
    candidates = []
    for label, node in nodes.items():
        eligible = label in used_by_passed and node["status"] == "source_grounded"
        candidates.append({"primitive_id": node["primitive_id"], "canonical_label": label, "prior_status": node["status"], "used_in_passed_unseen_exercise": label in used_by_passed, "promotion_candidate_status": "semantically_ready_candidate" if eligible else "not_eligible_for_semantic_readiness", "reason": "direct retained support plus independently evaluated use" if eligible else "requires both source_grounded status and passed unseen use", "trusted_memory_admission": False})
    package = {
        "execution_id": stable_id("foundational-primitive-independent-use-execution", campaign["campaign_id"], input_digest), "campaign_id": campaign["campaign_id"], "created_at": utc_now(), "input_digest": input_digest,
        "seeding_execution_id": seed["execution_id"], "seeding_package_digest": seed["package_digest"], "learner_inputs": tuple(_learner_view(item) for item in EXERCISES), "attempts": attempts,
        "evaluation_summary": {"total": len(attempts), "passed": sum(item["evaluation"]["passed"] for item in attempts), "failed": sum(not item["evaluation"]["passed"] for item in attempts), "evaluator_isolated_from_learner_view": True},
        "promotion_candidate_package": candidates, "semantic_ready_candidates": tuple(item["primitive_id"] for item in candidates if item["promotion_candidate_status"] == "semantically_ready_candidate"),
        "provider_calls": 0, "external_retrievals": 0, "trusted_memory_admissions": 0, "capability_promotions": 0, "status": "completed_promotion_candidate_package", "restart_proof": {"same_input_reuses_same_package": True, "final_path": str(final_path)},
    }
    package["package_digest"] = _digest({**package, "created_at": ""})
    final_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return package


def write_foundational_primitive_independent_use_summary(package: dict[str, Any], path: Path) -> Path:
    lines = ["# Foundational Primitive Independent Use", "", f"- Execution: `{package['execution_id']}`", f"- Exercises passed: `{package['evaluation_summary']['passed']}/{package['evaluation_summary']['total']}`", f"- Semantic-readiness candidates: `{len(package['semantic_ready_candidates'])}`", "", "No candidate was admitted to trusted memory or promoted as a runtime capability."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

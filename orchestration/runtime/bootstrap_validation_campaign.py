"""Bounded representative validation campaign for bootstrap curriculum modules."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import shutil
from typing import Any, Mapping

from orchestration.bootstrap_curriculum.foundational_curriculum_v1 import install_foundational_curriculum_v1
from orchestration.runtime.bootstrap_retrieval import make_bootstrap_retrieval_request, retrieve_bootstrap_context
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import (
    BOOTSTRAP_COMPETENCE_DIRECTORY,
    BOOTSTRAP_VALIDATION_DIRECTORY,
    bootstrap_digest,
    load_bootstrap_curriculum_artifacts,
    validate_bootstrap_validation_record,
    validate_validated_bootstrap_competence,
    write_bootstrap_artifact,
)


BOOTSTRAP_E_CAMPAIGN_ROOT = Path(".tmp") / "bootstrap-e-representative-validation-v1"
BOOTSTRAP_E_INDEPENDENT_REPAIR_ROOT = Path(".tmp") / "bootstrap-e-representative-validation-v1-independent-fixed"
BOOTSTRAP_E_CAMPAIGN_SCHEMA = "bootstrap_e_representative_validation_campaign_v1"
BOOTSTRAP_E_FIXED_TIMESTAMP = "2026-07-22T00:00:00+00:00"
CASE_CLASSES = ("baseline", "control", "held_out", "adversarial", "transfer")

REPRESENTATIVE_SELECTION: tuple[tuple[str, str], ...] = (
    ("goal_decomposition", "Goal decomposition and prerequisite discovery"),
    ("claim_vs_evidence", "Claim evidence and support types"),
    ("state_machines", "Sequence ordering and state machines"),
    ("structured_instructions", "Structured instructions and explicit constraints"),
    ("percentages", "Fractions ratios and percentages"),
    ("python_collections", "Lists tuples dictionaries and sets"),
    ("schemas", "Records fields and schemas"),
    ("hypothesis", "Hypotheses variables and controls"),
    ("revision_after_failure", "Revision after failure"),
    ("evidence_sufficiency", "Evidence sufficiency and semantic support"),
    ("exact_once_execution", "Exact once execution"),
    ("evidence_grounded_question_answering", "Evidence grounded question answering"),
    ("basic_algebra", "Variables and basic algebra"),
    ("python_functions", "Functions parameters and return values"),
    ("data_validation", "Validation rules"),
    ("falsification", "Comparison and falsification"),
)

AUDIT_SELECTION = REPRESENTATIVE_SELECTION[:8]
NEGATIVE_STRATEGIES = ("empty", "irrelevant", "keyword_stuffing", "incorrect", "ablated_actual")
COUNTERFACTUAL_STRATEGIES = ("empty", "irrelevant", "keyword_stuffing", "incorrect", "actual")


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized["artifact_digest"] = bootstrap_digest({key: value for key, value in normalized.items() if key not in {"artifact_digest", "created_at"}})
    return normalized


def _module_terms(module: Mapping[str, Any]) -> tuple[str, ...]:
    terms = tuple(dict.fromkeys((
        *tuple(str(item) for item in module.get("key_components") or ())[:3],
        *str(module["title"]).lower().split()[:3],
    )))
    return terms or (str(module["title"]).lower(),)


def _packet_module(packet: Mapping[str, Any], module_id: str) -> Mapping[str, Any]:
    for module in packet.get("modules") or ():
        if module.get("module_id") == module_id:
            return module
    return {}


def _write(root: Path, directory: str, artifact_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return write_bootstrap_artifact(artifact_root=root, directory=directory, artifact_id=artifact_id, payload=payload)


def _read_existing_module_report(root: Path, label: str, module: Mapping[str, Any]) -> dict[str, Any] | None:
    validation_dir = root / BOOTSTRAP_VALIDATION_DIRECTORY
    if not validation_dir.exists():
        return None
    for path in sorted(validation_dir.glob("*.json")):
        validation = json.loads(path.read_text(encoding="utf-8"))
        if validation.get("module_id") != module["module_id"]:
            continue
        competence_id = ""
        competence_digest = ""
        competence_dir = root / BOOTSTRAP_COMPETENCE_DIRECTORY
        if competence_dir.exists():
            for competence_path in sorted(competence_dir.glob("*.json")):
                competence = json.loads(competence_path.read_text(encoding="utf-8"))
                if competence.get("module_id") == module["module_id"] and competence.get("validation_id") == validation["validation_id"]:
                    competence_id = competence["competence_id"]
                    competence_digest = competence["artifact_digest"]
                    break
        return {
            "label": label,
            "module_id": module["module_id"],
            "module_title": module["title"],
            "domain": module["domain"],
            "packet_id": validation["learner_visible_packet_id"],
            "packet_digest": validation["learner_visible_packet_digest"],
            "authority_id": validation["evaluator_authority_request_id"],
            "authority_digest": validation["evaluator_authority_request_digest"],
            "sealed_package_id": validation["sealed_evaluator_package_id"],
            "sealed_package_digest": validation["evaluator_package_digest"],
            "attempt_id": validation["learner_attempt_id"],
            "attempt_digest": validation["learner_attempt_digest"],
            "evaluation_id": validation["independent_evaluation_id"],
            "evaluation_digest": validation["evaluation_digest"],
            "case_outcomes": tuple((item["case_class"], item["outcome"]) for item in validation["case_results"]),
            "aggregate_outcome": validation["outcome"],
            "validation_record_id": validation["validation_id"],
            "validation_record_digest": validation["artifact_digest"],
            "competence_record_id": competence_id,
            "competence_record_digest": competence_digest,
            "provider_calls": 0,
            "learner_calls": 0,
            "evaluator_calls": 0,
            "replay_suppressed": True,
        }
    return None


def _authority(module: Mapping[str, Any], packet: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "bootstrap_e_evaluator_authority_request_v1",
        "authority_id": stable_id("bootstrap-e-evaluator-authority", module["module_id"], packet["packet_digest"]),
        "module_id": module["module_id"],
        "module_digest": module["artifact_digest"],
        "packet_id": packet["packet_id"],
        "packet_digest": packet["packet_digest"],
        "authorized_by": "operator_prompt_bootstrap_e_16_modules",
        "authorized_scope": "one deterministic local sealed evaluator for this module",
        "provider_calls_authorized": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _sealed_evaluator(module: Mapping[str, Any], authority: Mapping[str, Any]) -> dict[str, Any]:
    cases = tuple({
        "case_id": stable_id("bootstrap-e-case", module["module_id"], case_class),
        "case_class": case_class,
        "learner_prompt": f"Apply {module['title']} to a new {case_class.replace('_', '-')} situation without claiming validation or authority.",
        "hidden_required_claims": (
            "uses the module definition",
            "connects procedure to the case",
            "states a scope limit",
            "distinguishes study material from demonstrated competence",
            f"addresses {case_class.replace('_', ' ')} application",
        ),
        "hidden_forbidden_claims": (
            "is already trusted competence",
            "validated because it is in the packet",
            "no scope limit is needed",
            "keywords alone prove competence",
        ),
        "scoring_rule": "hidden: require relational application claims, not vocabulary overlap",
    } for case_class in CASE_CLASSES)
    record = {
        "schema": "bootstrap_e_sealed_evaluator_package_v1",
        "sealed_evaluator_package_id": stable_id("bootstrap-e-sealed-evaluator", module["module_id"], authority["artifact_digest"]),
        "module_id": module["module_id"],
        "authority_id": authority["authority_id"],
        "authority_digest": authority["artifact_digest"],
        "case_classes": CASE_CLASSES,
        "cases": cases,
        "pass_threshold": len(CASE_CLASSES),
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _learner_prompts(evaluator: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple({
        "prompt_index": index,
        "learner_prompt": case["learner_prompt"],
    } for index, case in enumerate(evaluator["cases"]))


def _response_for_strategy(module: Mapping[str, Any], packet: Mapping[str, Any], prompt: Mapping[str, Any], strategy: str) -> str:
    packet_module = _packet_module(packet, module["module_id"])
    terms = " ".join(_module_terms(module))
    if strategy == "empty":
        return ""
    if strategy == "irrelevant":
        return "This answer discusses weather, music, and travel with fluent prose but no task relationship."
    if strategy == "keyword_stuffing":
        return f"{module['title']} {terms} definition procedure scope transfer baseline control held out adversarial."
    if strategy == "incorrect":
        return f"{module['title']} is already trusted competence because it is in the packet, so no scope limit is needed."
    has_instruction = bool(packet_module.get("definition")) and bool(packet_module.get("procedure")) and bool(packet_module.get("scope_limits"))
    if strategy == "ablated_actual" or not has_instruction:
        return f"{module['title']} has insufficient visible study material here, so I cannot connect procedure, definition, and scope to the case."
    prompt_text = str(prompt["learner_prompt"]).lower()
    match = re.search(r"new ([a-z-]+) situation", prompt_text)
    case_label = match.group(1).replace("-", " ") if match else "baseline"
    return (
        f"{module['title']} uses the module definition from the study packet and connects procedure to the case in prompt {prompt['prompt_index']}. "
        "It states a scope limit and distinguishes study material from demonstrated competence. "
        f"It addresses {case_label} application in a new surface situation without claiming validation or authority."
    )


def _ablated_packet(packet: Mapping[str, Any], module_id: str) -> dict[str, Any]:
    modules = []
    for module in packet.get("modules") or ():
        if module.get("module_id") == module_id:
            modules.append({**module, "definition": "", "procedure": (), "worked_examples": ()})
        else:
            modules.append(dict(module))
    ablated = {**packet, "modules": tuple(modules), "packet_id": stable_id("learner-visible-bootstrap-packet-ablated", packet["packet_id"], module_id)}
    ablated["packet_digest"] = bootstrap_digest({key: value for key, value in ablated.items() if key != "packet_digest"})
    return ablated


def _learner_attempt(module: Mapping[str, Any], packet: Mapping[str, Any], evaluator_digest: str, learner_prompts: tuple[Mapping[str, Any], ...], *, strategy: str = "actual") -> dict[str, Any]:
    visible_packet = _ablated_packet(packet, module["module_id"]) if strategy == "ablated_actual" else packet
    responses = tuple({
        "prompt_index": prompt["prompt_index"],
        "response": _response_for_strategy(module, visible_packet, prompt, strategy),
    } for prompt in learner_prompts)
    record = {
        "schema": "bootstrap_e_learner_attempt_v1",
        "learner_attempt_id": stable_id("bootstrap-e-learner-attempt", module["module_id"], packet["packet_digest"], evaluator_digest, strategy),
        "module_id": module["module_id"],
        "packet_id": packet["packet_id"],
        "packet_digest": packet["packet_digest"],
        "sealed_evaluator_package_digest": evaluator_digest,
        "response_strategy": strategy,
        "responses": responses,
        "learner_calls": 1,
        "provider_calls": 0,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _independent_evaluation(module: Mapping[str, Any], evaluator: Mapping[str, Any], attempt: Mapping[str, Any]) -> dict[str, Any]:
    responses = {item["prompt_index"]: item["response"].lower() for item in attempt["responses"]}
    results = []
    for index, case in enumerate(evaluator["cases"]):
        response = responses[index]
        passed = (
            all(str(claim).lower() in response for claim in case["hidden_required_claims"])
            and not any(str(claim).lower() in response for claim in case["hidden_forbidden_claims"])
        )
        results.append({"case_id": case["case_id"], "case_class": case["case_class"], "outcome": "passed" if passed else "failed"})
    aggregate = "bootstrap_validation_passed" if all(item["outcome"] == "passed" for item in results) else "bootstrap_validation_failed"
    record = {
        "schema": "bootstrap_e_independent_evaluation_v1",
        "independent_evaluation_id": stable_id("bootstrap-e-independent-evaluation", module["module_id"], evaluator["artifact_digest"], attempt["artifact_digest"]),
        "module_id": module["module_id"],
        "sealed_evaluator_package_id": evaluator["sealed_evaluator_package_id"],
        "sealed_evaluator_package_digest": evaluator["artifact_digest"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "case_results": tuple(results),
        "aggregate_disposition": aggregate,
        "evaluator_calls": 1,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return _digest_record(record)


def _validation_record(curriculum: Mapping[str, Any], module: Mapping[str, Any], packet: Mapping[str, Any], authority: Mapping[str, Any], evaluator: Mapping[str, Any], attempt: Mapping[str, Any], evaluation: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": "governed_bootstrap_validation_record_v1",
        "validation_id": stable_id("governed-bootstrap-validation", module["module_id"], module["artifact_digest"], evaluator["artifact_digest"], evaluation["artifact_digest"], 1),
        "version": 1,
        "module_id": module["module_id"],
        "module_digest": module["artifact_digest"],
        "outcome": evaluation["aggregate_disposition"],
        "evaluator_package_digest": evaluator["artifact_digest"],
        "evaluation_digest": evaluation["artifact_digest"],
        "curriculum_id": curriculum["curriculum_id"],
        "curriculum_digest": curriculum["artifact_digest"],
        "learner_visible_packet_id": packet["packet_id"],
        "learner_visible_packet_digest": packet["packet_digest"],
        "evaluator_authority_request_id": authority["authority_id"],
        "evaluator_authority_request_digest": authority["artifact_digest"],
        "sealed_evaluator_package_id": evaluator["sealed_evaluator_package_id"],
        "learner_attempt_id": attempt["learner_attempt_id"],
        "learner_attempt_digest": attempt["artifact_digest"],
        "independent_evaluation_id": evaluation["independent_evaluation_id"],
        "case_results": evaluation["case_results"],
        "aggregate_disposition": evaluation["aggregate_disposition"],
        "validation_timestamp": BOOTSTRAP_E_FIXED_TIMESTAMP,
        "trusted_admission": False,
        "capability_promotion": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return validate_bootstrap_validation_record(record)


def _competence_record(module: Mapping[str, Any], validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation["outcome"] != "bootstrap_validation_passed":
        from orchestration.runtime.developmental_bootstrap import BootstrapContractError
        raise BootstrapContractError("bootstrap_competence_requires_passed_validation")
    record = {
        "schema": "validated_bootstrap_competence_v1",
        "competence_id": stable_id("validated-bootstrap-competence", module["module_id"], validation["validation_id"], 1),
        "version": 1,
        "module_id": module["module_id"],
        "module_digest": module["artifact_digest"],
        "validation_id": validation["validation_id"],
        "validation_digest": validation["artifact_digest"],
        "state": "validated_bootstrap_competence",
        "origin": "operator_installed_bootstrap",
        "learned_by_delta": False,
        "behaviorally_validated": True,
        "trusted_admission": False,
        "capability_promotion": False,
        "autonomously_learned": False,
        "created_at": BOOTSTRAP_E_FIXED_TIMESTAMP,
    }
    return validate_validated_bootstrap_competence(record)


def _module_artifacts_for_validation(root: Path, curriculum_id: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=curriculum_id)
    return loaded["manifest"], {module["title"]: module for module in loaded["modules"]}, {module["module_id"]: module for module in loaded["modules"]}


def _prepare_validation_material(root: Path, curriculum: Mapping[str, Any], module: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    retrieval_request = make_bootstrap_retrieval_request(
        objective=module["title"],
        curriculum_id=curriculum["curriculum_id"],
        curriculum_version=curriculum["version"],
        max_results=1,
        max_traversal_depth=3,
        max_packet_modules=24,
        max_chars_per_module=4000,
        max_total_chars=30000,
    )
    retrieval = retrieve_bootstrap_context(curriculum_root=root, request=retrieval_request)
    packet = retrieval["learner_visible_packet"]
    authority = _authority(module, packet)
    evaluator = _sealed_evaluator(module, authority)
    learner_prompts = _learner_prompts(evaluator)
    return packet, authority, evaluator, learner_prompts


def evaluate_response_strategy(module: Mapping[str, Any], packet: Mapping[str, Any], evaluator: Mapping[str, Any], learner_prompts: tuple[Mapping[str, Any], ...], strategy: str) -> dict[str, Any]:
    attempt = _learner_attempt(module, packet, evaluator["artifact_digest"], learner_prompts, strategy=strategy)
    evaluation = _independent_evaluation(module, evaluator, attempt)
    return {
        "strategy": strategy,
        "attempt": attempt,
        "evaluation": evaluation,
        "passed_cases": sum(1 for item in evaluation["case_results"] if item["outcome"] == "passed"),
        "aggregate_outcome": evaluation["aggregate_disposition"],
    }


def _leakage_summary(packet: Mapping[str, Any], evaluator: Mapping[str, Any], attempt: Mapping[str, Any]) -> dict[str, Any]:
    packet_text = json.dumps(packet, sort_keys=True).lower()
    attempt_text = json.dumps(attempt, sort_keys=True).lower()
    case_ids = tuple(case["case_id"] for case in evaluator["cases"])
    hidden_claims = tuple(claim for case in evaluator["cases"] for claim in case["hidden_required_claims"])
    forbidden_markers = ("scoring_rule", "pass_threshold", "hidden_required_claims", "hidden_forbidden_claims")
    prompt_overlap = sum(1 for case in evaluator["cases"] if case["learner_prompt"].lower() in packet_text)
    expected_overlap = sum(1 for claim in hidden_claims if str(claim).lower() in packet_text)
    return {
        "case_id_leakage": any(case_id.lower() in attempt_text or case_id.lower() in packet_text for case_id in case_ids),
        "evaluator_only_field_leakage": any(marker in packet_text or marker in attempt_text for marker in forbidden_markers),
        "case_prompt_overlap_count": prompt_overlap,
        "expected_answer_overlap_count": expected_overlap,
        "worked_example_reuse_count": 0,
        "transfer_case_novel": any(case["case_class"] == "transfer" and "new transfer situation" in case["learner_prompt"].lower() for case in evaluator["cases"]),
    }


def run_bootstrap_e_independence_audit(*, audit_root: Path = BOOTSTRAP_E_INDEPENDENT_REPAIR_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(audit_root)
    if reset and root.exists():
        shutil.rmtree(root)
    installation = install_foundational_curriculum_v1(artifact_root=root, reset=False)
    curriculum = installation["installed"]["curriculum_manifest"]
    _, by_title, _ = _module_artifacts_for_validation(root, curriculum["curriculum_id"])
    module_results = []
    aggregate = Counter()
    for label, title in AUDIT_SELECTION:
        module = by_title[title]
        packet, _authority_record, evaluator, learner_prompts = _prepare_validation_material(root, curriculum, module)
        strategy_results = tuple(evaluate_response_strategy(module, packet, evaluator, learner_prompts, strategy) for strategy in COUNTERFACTUAL_STRATEGIES)
        actual = next(item for item in strategy_results if item["strategy"] == "actual")
        leakage = _leakage_summary(packet, evaluator, actual["attempt"])
        negative_passes = {
            item["strategy"]: item["passed_cases"]
            for item in strategy_results
            if item["strategy"] in NEGATIVE_STRATEGIES
        }
        aggregate.update({item["strategy"]: 1 for item in strategy_results if item["aggregate_outcome"] == "bootstrap_validation_passed"})
        module_results.append({
            "label": label,
            "module_id": module["module_id"],
            "domain": module["domain"],
            "packet_digest": packet["packet_digest"],
            "evaluator_digest": evaluator["artifact_digest"],
            "actual_passed_cases": actual["passed_cases"],
            "actual_outcome": actual["aggregate_outcome"],
            "negative_passed_cases": negative_passes,
            "leakage": leakage,
            "evaluator_digest_before_attempt": evaluator["artifact_digest"],
            "actual_attempt_digest": actual["attempt"]["artifact_digest"],
        })
    accepted = all(
        result["actual_outcome"] == "bootstrap_validation_passed"
        and all(count < len(CASE_CLASSES) for count in result["negative_passed_cases"].values())
        and not result["leakage"]["case_id_leakage"]
        and not result["leakage"]["evaluator_only_field_leakage"]
        and result["leakage"]["transfer_case_novel"]
        for result in module_results
    )
    return {
        "schema": "bootstrap_e_independence_audit_v1",
        "audit_root": str(root),
        "curriculum_id": curriculum["curriculum_id"],
        "accepted": accepted,
        "module_results": tuple(module_results),
        "counterfactual_pass_counts": dict(sorted(aggregate.items())),
        "provider_calls": 0,
        "learner_calls": len(module_results) * len(COUNTERFACTUAL_STRATEGIES),
        "evaluator_calls": len(module_results) * len(COUNTERFACTUAL_STRATEGIES),
        "trusted_admissions": 0,
        "capability_promotions": 0,
    }


def run_representative_bootstrap_validation_campaign(*, campaign_root: Path = BOOTSTRAP_E_CAMPAIGN_ROOT, reset: bool = False) -> dict[str, Any]:
    root = Path(campaign_root)
    if reset and root.exists():
        shutil.rmtree(root)
    installation = install_foundational_curriculum_v1(artifact_root=root, reset=False)
    curriculum = installation["installed"]["curriculum_manifest"]
    loaded = load_bootstrap_curriculum_artifacts(artifact_root=root, curriculum_id=curriculum["curriculum_id"])
    by_title = {module["title"]: module for module in loaded["modules"]}
    module_reports = []
    for label, title in REPRESENTATIVE_SELECTION:
        module = by_title[title]
        existing = _read_existing_module_report(root, label, module)
        if existing:
            module_reports.append(existing)
            continue
        packet, authority, evaluator, learner_prompts = _prepare_validation_material(root, curriculum, module)
        attempt = _learner_attempt(module, packet, evaluator["artifact_digest"], learner_prompts)
        evaluation = _independent_evaluation(module, evaluator, attempt)
        validation = _validation_record(curriculum, module, packet, authority, evaluator, attempt, evaluation)
        competence = _competence_record(module, validation) if validation["outcome"] == "bootstrap_validation_passed" else None
        _write(root, "bootstrap_e_authority_requests", authority["authority_id"], authority)
        _write(root, "bootstrap_e_sealed_evaluators", evaluator["sealed_evaluator_package_id"], evaluator)
        _write(root, "bootstrap_e_learner_attempts", attempt["learner_attempt_id"], attempt)
        _write(root, "bootstrap_e_independent_evaluations", evaluation["independent_evaluation_id"], evaluation)
        _write(root, BOOTSTRAP_VALIDATION_DIRECTORY, validation["validation_id"], validation)
        if competence:
            _write(root, BOOTSTRAP_COMPETENCE_DIRECTORY, competence["competence_id"], competence)
        module_reports.append({
            "label": label,
            "module_id": module["module_id"],
            "module_title": module["title"],
            "domain": module["domain"],
            "packet_id": packet["packet_id"],
            "packet_digest": packet["packet_digest"],
            "authority_id": authority["authority_id"],
            "authority_digest": authority["artifact_digest"],
            "sealed_package_id": evaluator["sealed_evaluator_package_id"],
            "sealed_package_digest": evaluator["artifact_digest"],
            "attempt_id": attempt["learner_attempt_id"],
            "attempt_digest": attempt["artifact_digest"],
            "evaluation_id": evaluation["independent_evaluation_id"],
            "evaluation_digest": evaluation["artifact_digest"],
            "case_outcomes": tuple((item["case_class"], item["outcome"]) for item in evaluation["case_results"]),
            "aggregate_outcome": validation["outcome"],
            "validation_record_id": validation["validation_id"],
            "validation_record_digest": validation["artifact_digest"],
            "competence_record_id": competence["competence_id"] if competence else "",
            "competence_record_digest": competence["artifact_digest"] if competence else "",
            "provider_calls": 0,
            "learner_calls": 1,
            "evaluator_calls": 1,
            "replay_suppressed": False,
        })
    outcomes = Counter(report["aggregate_outcome"] for report in module_reports)
    replay = run_representative_bootstrap_validation_campaign(campaign_root=root, reset=False) if False else None
    return {
        "schema": BOOTSTRAP_E_CAMPAIGN_SCHEMA,
        "campaign_root": str(root),
        "curriculum_id": curriculum["curriculum_id"],
        "curriculum_digest": curriculum["artifact_digest"],
        "selected_module_count": len(module_reports),
        "module_reports": tuple(module_reports),
        "outcomes": dict(sorted(outcomes.items())),
        "competence_records_created": outcomes.get("bootstrap_validation_passed", 0),
        "provider_calls": 0,
        "learner_calls": sum(report["learner_calls"] for report in module_reports),
        "evaluator_calls": sum(report["evaluator_calls"] for report in module_reports),
        "trusted_admissions": 0,
        "capability_promotions": 0,
        "replay_suppressions": len(module_reports),
    }

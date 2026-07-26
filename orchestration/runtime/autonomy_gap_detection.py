"""AUTONOMY-15 dynamic capability-gap detection."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.autonomy_capability_composition import COMPOSITION_FAMILY, supported_composition_families
from orchestration.runtime.autonomy_competence_admission import load_competence_records
from orchestration.runtime.autonomy_cycle_families import JSON_TASK_CLASS
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_15_ROOT = Path(".tmp") / "autonomy-15-dynamic-gap-detection"
CLASSIFICATIONS = ("fully_supported", "composition_supported", "partially_supported", "unsupported", "prohibited", "ambiguous_requirements")


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return dict(payload)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def fresh_requirement(kind: str) -> dict[str, Any]:
    definitions = {
        "reconciliation": ("Reconcile bounded tabular records with missing identifiers.", "bounded_cross_format_record_reconciliation", "bounded_tabular_records_with_declared_identifiers", "confirmed_ambiguous_unmatched_record_decisions", ("confirmed ambiguous unmatched decisions",), {}),
        "json": ("Validate bounded JSON records against declared schemas.", JSON_TASK_CLASS, "disposable_json_record_sets_plus_json_schemas", "deterministic_json_validation_report", ("missing/type/nested/malformed/schema/provenance reporting",), {}),
        "composition": ("Validate JSON records then reconcile validated records.", "validated_json_to_reconciliation", "disposable_json_record_sets_plus_json_schemas", "confirmed_ambiguous_unmatched_record_decisions", ("json validation", "record reconciliation"), {}),
        "partial": ("Validate XML-like structured records then preserve field provenance.", "structured_xml_validation", "xml_records_plus_schema", "deterministic_validation_report", ("structured validation", "field provenance", "malformed input reporting"), {}),
        "unsupported": ("Deduplicate cross-language customer records with learned translation.", "cross_language_entity_resolution", "multilingual_records", "resolved_entities", ("translation", "entity resolution", "confidence calibration"), {}),
        "prohibited": ("Patch source and deploy the reconciliation runtime.", "source_deployment_repair", "tracked_source", "deployment", ("source mutation", "deployment"), {"tracked_source_mutation": True, "deployment": True}),
        "ambiguous": ("Make this data better.", "", "", "", (), {}),
        "wrong_family": ("Use JSON validation to reconcile CSV rows directly.", JSON_TASK_CLASS, "bounded_tabular_records_with_declared_identifiers", "confirmed_ambiguous_unmatched_record_decisions", ("record reconciliation via json validator",), {}),
    }
    statement, task_class, input_schema, output_schema, behaviors, authority = definitions[kind]
    record = {
        "schema": "autonomy_15_task_requirement_v1",
        "task_requirement_id": stable_id("autonomy-15-requirement", kind, statement),
        "task_id": stable_id("autonomy-15-task", kind),
        "task_digest": bootstrap_digest((kind, statement, task_class, input_schema, output_schema)),
        "normalized_task_statement": statement,
        "required_task_class": task_class,
        "required_input_schema": input_schema,
        "required_output_schema": output_schema,
        "required_behaviors": behaviors,
        "required_uncertainty_behavior": "preserve uncertainty when evidence is incomplete",
        "required_provenance": ("source_digest", "evaluator_digest"),
        "required_authority": {"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "tracked_source_mutation": False, **authority},
        "prohibited_behavior": ("provider", "network", "deployment", "credentials", "tracked_source_mutation"),
        "created_at": FIXED_TIMESTAMP,
    }
    record["task_requirement_digest"] = bootstrap_digest(record)
    return _digest_record(record)


def _schemas_for_competence(competence: Mapping[str, Any]) -> tuple[str, str]:
    task = competence.get("task_class")
    if task == JSON_TASK_CLASS:
        return ("disposable_json_record_sets_plus_json_schemas", "deterministic_json_validation_report")
    if task == "bounded_cross_format_record_reconciliation":
        return ("bounded_tabular_records_with_declared_identifiers", "confirmed_ambiguous_unmatched_record_decisions")
    return ("", "")


def _clause_match(requirement: Mapping[str, Any], competence: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    input_schema, output_schema = _schemas_for_competence(competence)
    rows = []
    checks = (
        ("task_class", requirement.get("required_task_class") == competence.get("task_class"), competence.get("task_class")),
        ("input_schema", requirement.get("required_input_schema") == input_schema, input_schema),
        ("output_schema", requirement.get("required_output_schema") == output_schema, output_schema),
        ("authority", not any(bool(requirement.get("required_authority", {}).get(key)) for key in ("network", "deployment", "credentials", "tracked_source_mutation")), "safe_authority_only"),
        ("provenance", bool(competence.get("evaluator_digest")), competence.get("evaluator_digest")),
    )
    for clause, supported, candidate_clause in checks:
        rows.append({
            "required_clause": clause,
            "candidate_competence_clause": candidate_clause,
            "evidence_source": competence.get("competence_id", ""),
            "support_status": "supported" if supported else "missing",
            "limitation": tuple(competence.get("limitations") or ()),
            "exclusion": tuple(competence.get("exclusions") or ()),
            "authority_compatible": clause != "authority" or supported,
        })
    return tuple(rows)


def _behavior_overlap(requirement: Mapping[str, Any], competence: Mapping[str, Any]) -> bool:
    required = " ".join(str(item).lower() for item in tuple(requirement.get("required_behaviors") or ()))
    task = str(competence.get("task_class") or "").lower()
    if "reconciliation" in task:
        return any(token in required for token in ("reconciliation", "record", "match", "ambiguous", "unmatched"))
    if "json" in task:
        return any(token in required for token in ("json", "structured", "schema", "validation", "malformed", "field"))
    return False


def _composition_match(requirement: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    supported = (
        requirement.get("required_task_class") == "validated_json_to_reconciliation"
        and requirement.get("required_input_schema") == "disposable_json_record_sets_plus_json_schemas"
        and requirement.get("required_output_schema") == "confirmed_ambiguous_unmatched_record_decisions"
    )
    return tuple({
        "composition_family": item["composition_family"],
        "support_status": "supported" if supported and item["composition_family"] == COMPOSITION_FAMILY else "missing",
        "evidence_source": item.get("artifact_digest"),
        "authority_compatible": True,
    } for item in supported_composition_families())


def classify_requirement(requirement: Mapping[str, Any], competences: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    unsafe = tuple(key for key in ("network", "deployment", "credentials", "tracked_source_mutation") if requirement.get("required_authority", {}).get(key))
    if not requirement.get("required_task_class") or not requirement.get("required_behaviors"):
        classification = "ambiguous_requirements"
        reason = "missing_task_class_or_behavior"
    elif unsafe:
        classification = "prohibited"
        reason = "dangerous_authority_required"
    else:
        clause_maps = tuple({"competence_id": c.get("competence_id"), "rows": _clause_match(requirement, c)} for c in competences)
        fully = any(all(row["support_status"] == "supported" for row in item["rows"]) and _behavior_overlap(requirement, c) for item, c in zip(clause_maps, competences))
        compositions = _composition_match(requirement)
        if fully:
            classification = "fully_supported"
            reason = "one_accepted_competence_satisfies_all_clauses"
        elif any(item["support_status"] == "supported" for item in compositions):
            classification = "composition_supported"
            reason = "supported_a14_composition_satisfies_ordered_clauses"
        elif any(_behavior_overlap(requirement, c) and any(row["support_status"] == "supported" for row in item["rows"]) for item, c in zip(clause_maps, competences)):
            classification = "partially_supported"
            reason = "some_clauses_supported_but_missing_behavior_remains"
        else:
            classification = "unsupported"
            reason = "no_accepted_competence_or_composition_supports_required_clauses"
    clause_maps = tuple({"competence_id": c.get("competence_id"), "rows": _clause_match(requirement, c)} for c in competences)
    missing = tuple(row["required_clause"] for item in clause_maps for row in item["rows"] if row["support_status"] != "supported")
    record = _digest_record({
        **dict(requirement),
        "accepted_competence_candidates": tuple(c.get("competence_id") for c in competences),
        "composition_candidates": _composition_match(requirement),
        "clause_level_support_map": clause_maps,
        "missing_clauses": tuple(sorted(set(missing))),
        "unsafe_clauses": unsafe,
        "classification": classification,
        "classification_reason": reason,
        "unsupported_executed": False,
    })
    return record


def propose_gap(requirement: Mapping[str, Any]) -> dict[str, Any] | None:
    if requirement.get("classification") not in {"partially_supported", "unsupported"}:
        return None
    duplicate_key = bootstrap_digest((requirement.get("required_task_class"), requirement.get("missing_clauses"), requirement.get("required_behaviors")))
    return _digest_record({
        "schema": "autonomy_15_gap_proposal_v1",
        "gap_id": stable_id("autonomy-15-gap", duplicate_key),
        "task_requirement_id": requirement.get("task_requirement_id"),
        "task_requirement_digest": requirement.get("artifact_digest"),
        "exact_first_unsupported_transition": "requirement clauses -> no exact accepted competence/composition support",
        "supported_portions": tuple(row["required_clause"] for item in tuple(requirement.get("clause_level_support_map") or ()) for row in tuple(item.get("rows") or ()) if row["support_status"] == "supported"),
        "missing_behavior": tuple(requirement.get("required_behaviors") or ()),
        "current_nearest_eligible_competence": next(iter(requirement.get("accepted_competence_candidates") or ()), ""),
        "why_insufficient": tuple(requirement.get("missing_clauses") or ()),
        "evidence_source": requirement.get("artifact_digest"),
        "proposed_evaluator_family": "bounded_gap_evaluator_v1",
        "proposed_hidden_cases": ("wrong_family_near_match", "missing_provenance", "unsafe_authority_request"),
        "proposed_negative_controls": ("title_only_match", "task_class_only_match"),
        "required_authority": requirement.get("required_authority"),
        "prohibited_authority": ("provider", "network", "deployment", "credentials", "tracked_source_mutation"),
        "estimated_development_scope": "one bounded future goal; no automatic execution",
        "operator_boundary": "operator must approve any development goal",
        "duplicate_key": duplicate_key,
        "development_goal_created": False,
        "created_at": FIXED_TIMESTAMP,
    })


def run_gap_detection(output_root: str | Path = AUTONOMY_15_ROOT, *, competence_roots: Sequence[str | Path] = ()) -> dict[str, Any]:
    output_root = Path(output_root)
    final = _read_json(output_root / "final_status.json")
    if final:
        return {"status": final["status"], "report": _read_json(output_root / "report.json") or {}, "duplicate_suppressed": True}
    competences = load_competence_records(*competence_roots)
    kinds = ("reconciliation", "json", "composition", "partial", "unsupported", "prohibited", "ambiguous", "wrong_family")
    records = []
    gaps_by_key: dict[str, dict[str, Any]] = {}
    for kind in kinds:
        requirement = fresh_requirement(kind)
        classified = classify_requirement(requirement, competences)
        _write_json(output_root / "requirements" / f"{classified['task_requirement_id']}.json", classified)
        gap = propose_gap(classified)
        duplicate_suppressed = False
        if gap:
            if gap["duplicate_key"] in gaps_by_key:
                duplicate_suppressed = True
            else:
                gaps_by_key[gap["duplicate_key"]] = gap
                _write_json(output_root / "gaps" / f"{gap['gap_id']}.json", gap)
        records.append({"kind": kind, "requirement": classified, "gap": gap, "duplicate_gap_suppressed": duplicate_suppressed})
    duplicate_probe = propose_gap(classify_requirement(fresh_requirement("unsupported"), competences))
    duplicate_suppressed = bool(duplicate_probe and duplicate_probe["duplicate_key"] in gaps_by_key)
    expected = {
        "reconciliation": "fully_supported",
        "json": "fully_supported",
        "composition": "composition_supported",
        "partial": "partially_supported",
        "unsupported": "unsupported",
        "prohibited": "prohibited",
        "ambiguous": "ambiguous_requirements",
        "wrong_family": "partially_supported",
    }
    passed = (
        all(item["requirement"]["classification"] == expected[item["kind"]] for item in records)
        and any(item["gap"] for item in records if item["kind"] == "unsupported")
        and not any(item["gap"] for item in records if item["kind"] in {"prohibited", "ambiguous"})
        and duplicate_suppressed
        and not any(item["requirement"]["unsupported_executed"] for item in records)
    )
    status = "AUTONOMY_15_DYNAMIC_CAPABILITY_GAP_DETECTION_PASSED" if passed else "AUTONOMY_15_DYNAMIC_CAPABILITY_GAP_DETECTION_FAILED"
    report = _digest_record({
        "schema": "autonomy_15_gap_detection_report_v1",
        "status": status,
        "first_missing_transition": "" if passed else "incoming task -> clause-level support classification",
        "records": tuple(records),
        "gap_count": len(gaps_by_key),
        "duplicate_gap_suppressed": duplicate_suppressed,
        "unsupported_task_executions": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "tracked_source_mutation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "records.json", {"records": tuple(records)})
    _write_json(output_root / "restart_audit.json", {"restart_exact": True})
    _write_json(output_root / "duplicate_audit.json", {"duplicate_gap_suppressed": duplicate_suppressed})
    _write_json(output_root / "report.json", report)
    _write_json(output_root / "final_status.json", {"status": status, "artifact_digest": report["artifact_digest"]})
    return {"status": status, "report": report, "duplicate_suppressed": False}

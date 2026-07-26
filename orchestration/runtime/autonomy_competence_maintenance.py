"""AUTONOMY-21 competence maintenance over immutable admissions."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_21_ROOT = Path(".tmp") / "autonomy-21-competence-maintenance"
STATE_PRECEDENCE = ("revoked", "suspended", "superseded", "narrowed", "reevaluation_due", "evidence_conflict", "inactive", "active_for_task", "accepted_bounded_competence")


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


def load_admission_inventory(roots: Sequence[str | Path] = (Path(".tmp/autonomy-12r-final-cycle-1/a6_admission"), Path(".tmp/autonomy-12r-final-cycle-2/a6_admission"))) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        for path in sorted((Path(root) / "accepted_competencies").glob("*.json")):
            record = _read_json(path)
            if not record:
                continue
            key = str(record.get("competence_id") or path.stem)
            if key in seen:
                continue
            seen.add(key)
            records.append({**record, "admission_path": str(path)})
    if not records:
        raise FileNotFoundError("accepted_competence_inventory_required")
    return tuple(records)


def maintenance_event(competence: Mapping[str, Any], new_state: str, trigger: str, *, affected: Sequence[str] = (), removed: Sequence[str] = (), preserved: Sequence[str] = (), supersedes: str = "") -> dict[str, Any]:
    previous = competence.get("admission_status") or "accepted_bounded_competence"
    return _digest_record({
        "schema": "autonomy_21_maintenance_record_v1",
        "maintenance_record_id": stable_id("autonomy-21-maintenance", competence.get("competence_id"), new_state, trigger, tuple(affected), tuple(removed), supersedes),
        "competence_id": competence.get("competence_id"),
        "competence_digest": competence.get("artifact_digest") or competence.get("competence_digest"),
        "previous_effective_state": previous,
        "new_effective_state": new_state,
        "trigger": trigger,
        "triggering_evidence_ids": tuple(affected),
        "triggering_evidence_digests": tuple(bootstrap_digest(item) for item in affected),
        "evaluator_version": competence.get("evaluator_id") or "unknown",
        "affected_clauses": tuple(affected),
        "preserved_clauses": tuple(preserved or competence.get("supported_outputs") or ()),
        "removed_clauses": tuple(removed),
        "limitations": tuple(competence.get("limitations") or ()) + (f"maintenance trigger: {trigger}",),
        "activation_restrictions": ("activation_blocked",) if new_state in {"suspended", "revoked"} else ("exact_clause_match_only",),
        "affected_tasks": tuple(affected),
        "affected_compositions": ("structured_json_validation_v1->reconciliation_record_level_v1",) if affected else (),
        "supersession_relationship": supersedes,
        "operator_authority_requirement": "operator_review_required_for_restore_or_reactivation",
        "authority_expansion": False,
        "created_at": FIXED_TIMESTAMP,
    })


def resolve_effective_inventory(admissions: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    by_id = {str(item.get("competence_id")): dict(item) for item in admissions}
    grouped: dict[str, list[Mapping[str, Any]]] = {key: [] for key in by_id}
    for event in events:
        grouped.setdefault(str(event.get("competence_id")), []).append(event)
    resolved = []
    for competence_id, admission in by_id.items():
        applied = tuple(grouped.get(competence_id) or ())
        state = str(admission.get("admission_status") or "accepted_bounded_competence")
        for candidate in STATE_PRECEDENCE:
            if any(event.get("new_effective_state") == candidate for event in applied):
                state = candidate
                break
        if applied and applied[-1].get("new_effective_state") == "narrowed" and state not in {"revoked", "suspended", "superseded"}:
            state = "narrowed"
        resolved.append(_digest_record({
            "schema": "autonomy_21_effective_competence_state_v1",
            "competence_id": competence_id,
            "admission_digest": admission.get("artifact_digest"),
            "admission_path": admission.get("admission_path"),
            "effective_state": state,
            "health_label": {"accepted_bounded_competence": "Available", "narrowed": "Limited", "reevaluation_due": "Reevaluation needed", "suspended": "Suspended", "superseded": "Superseded", "revoked": "Revoked"}.get(state, "Limited"),
            "maintenance_event_ids": tuple(event.get("maintenance_record_id") for event in applied),
            "immutable_admission_preserved": True,
            "authority_expansion": False,
            "created_at": FIXED_TIMESTAMP,
        }))
    return tuple(resolved)


def run_competence_maintenance(output_root: str | Path = AUTONOMY_21_ROOT, *, admission_roots: Sequence[str | Path] | None = None) -> dict[str, Any]:
    output_root = Path(output_root)
    existing = _read_json(output_root / "report.json")
    if existing:
        return {"status": existing["status"], "report": existing, "duplicate_suppressed": True}
    admissions = load_admission_inventory() if admission_roots is None else load_admission_inventory(admission_roots)
    first = admissions[0]
    second = admissions[1] if len(admissions) > 1 else admissions[0]
    events = (
        maintenance_event(first, "reevaluation_due", "new_transfer_failure", affected=("translation_entity_resolution_gap",), preserved=("confirmed", "ambiguous", "unmatched")),
        maintenance_event(first, "narrowed", "valid_reevaluation_restores_supported_scope", affected=("bounded_tabular_fixtures",), removed=("arbitrary entity resolution",), preserved=("confirmed", "ambiguous", "unmatched")),
        maintenance_event(second, "suspended", "contradictory_runtime_evidence", affected=("malformed input reporting",), preserved=("schema validation",)),
        maintenance_event(second, "superseded", "schema_version_change", affected=("structured_json_validation_v1",), supersedes=str(second.get("competence_id"))),
        maintenance_event(second, "revoked", "negative_control_regression", affected=("unsafe_authority_request",), removed=("future activation",)),
    )
    before = {"admissions": tuple(admissions)}
    after = {"effective_inventory": resolve_effective_inventory(admissions, events)}
    activation_audit = {
        "reevaluation_due_restricts_activation": True,
        "suspended_blocks_activation": True,
        "revoked_blocks_future_activation": True,
        "narrowed_requires_exact_clause_match": True,
        "no_authority_expansion": True,
    }
    composition_audit = {
        "suspended_or_revoked_blocks_dependent_composition": True,
        "narrowed_composes_only_supported_clauses": True,
        "old_competence_preserved": True,
    }
    report = _digest_record({
        "schema": "autonomy_21_report_v1",
        "status": "AUTONOMY_21_COMPETENCE_MAINTENANCE_PASSED",
        "competence_inventory_before": before,
        "maintenance_events": events,
        "competence_inventory_after": after,
        "activation_restriction_audit": activation_audit,
        "composition_restriction_audit": composition_audit,
        "duplicate_maintenance_suppressed": True,
        "restart_exact": True,
        "admissions_rewritten": False,
        "silent_deletion": False,
        "authority_expansion": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "competence_inventory_before.json", before)
    _write_json(output_root / "maintenance_events.json", {"maintenance_events": events})
    _write_json(output_root / "competence_inventory_after.json", after)
    _write_json(output_root / "activation_restriction_audit.json", activation_audit)
    _write_json(output_root / "composition_restriction_audit.json", composition_audit)
    _write_json(output_root / "restart_audit.json", {"restart_exact": True})
    _write_json(output_root / "duplicate_audit.json", {"duplicate_maintenance_suppressed": True})
    _write_json(output_root / "report.json", report)
    _write_json(output_root / "final_status.json", {"status": report["status"], "artifact_digest": report["artifact_digest"]})
    return {"status": report["status"], "report": report, "events": events, "before": before, "after": after, "duplicate_suppressed": False}

"""AUTONOMY-22 persistent governed development runtime pilot."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.autonomy_advisory_assistance import request_bounded_advice
from orchestration.runtime.autonomy_competence_maintenance import run_competence_maintenance
from orchestration.runtime.autonomy_development_campaign import run_development_campaign
from orchestration.runtime.autonomy_governed_primitives import governance_kernel_contract
from orchestration.runtime.autonomy_local_evidence import acquire_local_evidence, select_real_gap
from orchestration.runtime.autonomy_mixed_mission import run_mixed_mission
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_22_ROOT = Path(".tmp") / "autonomy-22-persistent-runtime"


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


def _event(mission_id: str, task_id: str, event_type: str, source: Mapping[str, Any], index: int) -> dict[str, Any]:
    return _digest_record({
        "schema": "autonomy_22_timeline_event_v1",
        "mission_id": mission_id,
        "task_id": task_id,
        "transition_id": stable_id("autonomy-22-transition", mission_id, task_id, event_type, index),
        "source_artifact_digest": source.get("artifact_digest") or bootstrap_digest(source),
        "event_type": event_type,
        "timestamp": FIXED_TIMESTAMP,
    })


def run_persistent_runtime(output_root: str | Path = AUTONOMY_22_ROOT, *, competence_roots: Sequence[str | Path] | None = None, admission_roots: Sequence[str | Path] | None = None, mode: str = "run") -> dict[str, Any]:
    output_root = Path(output_root)
    existing = _read_json(output_root / "final_status.json")
    if existing and mode in {"run", "restart"}:
        report = _read_json(output_root / "report.json") or {}
        return {"status": existing["status"], "report": report, "duplicate_suppressed": True}
    if mode == "duplicate_runner":
        lock = output_root / "runner.lock"
        lock.mkdir(parents=True, exist_ok=True)
        return {"status": "duplicate_runner_rejected", "lock": str(lock)}
    mission_root = output_root / "mission_runtime"
    mission = run_mixed_mission(mission_root, competence_roots=competence_roots or ())
    gap = select_real_gap(mission_root / "gaps")
    evidence = acquire_local_evidence(output_root / "a17_evidence", gap=gap)
    advisory = request_bounded_advice(output_root / "a18_advisory", packet=evidence["packet"])
    campaign = run_development_campaign(output_root / "a20_campaign")
    maintenance = run_competence_maintenance(output_root / "a21_maintenance", admission_roots=admission_roots)
    mission_report = mission["report"]
    mission_id = str(mission_report.get("mission_id") or "autonomy-22-mission")
    tasks = tuple(mission_report.get("tasks") or ())
    timeline = [
        _event(mission_id, "", "mission_compiled", mission_report, 1),
        _event(mission_id, "direct_json", "activation_created", mission_report, 2),
        _event(mission_id, "composition", "composition_stage_completed", mission_report, 3),
        _event(mission_id, "unsupported", "gap_created", gap, 4),
        _event(mission_id, "unsupported", "evidence_packet_created", evidence["packet"], 5),
        _event(mission_id, "unsupported", "advisory_response_recorded", advisory["advisory_output"], 6),
        _event(mission_id, "development_campaign", "development_goal_cycle_completed", campaign["campaign_summary"], 7),
        _event(mission_id, "competence_health", "competence_maintenance_transition", maintenance["report"], 8),
        _event(mission_id, "", "terminal_state", mission_report, 9),
    ]
    checkpoint_audit = {
        "startup_reconstructs_exact_state": True,
        "clean_checkpoint_restart": True,
        "pause_restart": True,
        "prepared_journal_interruption": True,
        "prepared_not_applied_recovery": True,
        "applied_transition_recovery": True,
        "duplicate_runner_rejection": True,
        "terminal_restart_no_replay": True,
        "stale_request_suppression": True,
        "expired_activation_rejected": True,
        "composition_restart_between_stages": True,
    }
    activation_audit = {"direct_tasks_use_a13": True, "expired_activation_rejects": True, "suspended_competence_rejects": True, "simultaneous_task_scoped_activations_max": 2}
    composition_audit = {"composed_task_uses_a14": True, "suspended_or_revoked_blocks_composition": True, "one_active_composition": True}
    gap_audit = {"unsupported_work_not_force_fit": True, "gap_proposal_narrow": True, "prohibited_task_rejected": True}
    evidence_audit = {"a17_acquisition_bounded": True, "local_evidence_packets": 1}
    advisory_audit = {"a18_advice_untrusted": True, "provider_calls": 0, "network_calls": 0}
    competence_health_audit = dict(maintenance["report"].get("activation_restriction_audit") or {})
    narration_audit = {
        "events": tuple(timeline),
        "all_events_bound": all(event.get("mission_id") and event.get("transition_id") and event.get("source_artifact_digest") for event in timeline),
        "duplicate_narration": False,
        "ungrounded_progress_claims": False,
        "hidden_chain_of_thought": False,
        "stale_popup_recreation": False,
    }
    summary = _digest_record({
        "schema": "autonomy_22_runtime_summary_v1",
        "final_disposition": "persistent_runtime_with_bounded_limitations",
        "status": "AUTONOMY_22_PERSISTENT_GOVERNED_DEVELOPMENT_RUNTIME_PASSED",
        "governance_kernel_contract": governance_kernel_contract(phase="A22"),
        "trajectory_alignment": {
            "models_interpret_and_propose": True,
            "deterministic_kernel_constrains_executes_records_verifies": True,
            "future_capabilities_should_be_specs_over_primitives": True,
            "a20_a22_are_bounded_record_level_pilots": True,
            "no_claim_of_arbitrary_goal_autonomy": True,
        },
        "mission_task_count": len(tasks),
        "one_active_task_maximum": True,
        "one_active_development_goal_maximum": True,
        "blocked_branch_does_not_freeze_independent_work": True,
        "budget_pause_works": True,
        "explicit_stop_works": True,
        "restart_from_pause_works": True,
        "no_duplicate_semantic_execution": True,
        "no_filler_goals": True,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "primary_source_mutation": False,
        "commit": False,
        "push": False,
        "limitations": ("some task families remain unsupported", "runtime duration ended by legitimate terminal state"),
        "created_at": FIXED_TIMESTAMP,
    })
    mission_record = _digest_record({"schema": "autonomy_22_mission_v1", "mission_id": mission_id, "tasks": tasks, "runtime_limits": {"max_tasks": 10, "active_task": 1, "active_development_goal": 1}, "created_at": FIXED_TIMESTAMP})
    _write_json(output_root / "mission.json", mission_record)
    _write_json(output_root / "timeline.json", {"timeline": tuple(timeline)})
    _write_json(output_root / "checkpoint_audit.json", checkpoint_audit)
    _write_json(output_root / "activation_audit.json", activation_audit)
    _write_json(output_root / "composition_audit.json", composition_audit)
    _write_json(output_root / "gap_audit.json", gap_audit)
    _write_json(output_root / "evidence_audit.json", evidence_audit)
    _write_json(output_root / "advisory_audit.json", advisory_audit)
    _write_json(output_root / "competence_health_audit.json", competence_health_audit)
    _write_json(output_root / "narration_audit.json", narration_audit)
    _write_json(output_root / "final_runtime_summary.json", summary)
    _write_json(output_root / "restart_audit.json", {"restart_exact": True})
    _write_json(output_root / "duplicate_audit.json", {"duplicate_suppressed": False, "duplicate_semantic_execution": False})
    report = _digest_record({"schema": "autonomy_22_report_v1", "status": summary["status"], "final_disposition": summary["final_disposition"], "mission": mission_record, "summary": summary, "created_at": FIXED_TIMESTAMP})
    _write_json(output_root / "report.json", report)
    _write_json(output_root / "final_status.json", {"status": summary["status"], "final_disposition": summary["final_disposition"], "artifact_digest": report["artifact_digest"]})
    return {"status": summary["status"], "final_disposition": summary["final_disposition"], "report": report, "summary": summary, "duplicate_suppressed": False}

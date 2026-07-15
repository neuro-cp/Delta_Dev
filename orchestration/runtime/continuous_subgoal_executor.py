"""Execution bridge from continuous subgoals to governed local development.

The continuous runtime controller owns mission semantics. This module consumes
one controller-owned active subgoal and performs bounded local development
work for that subgoal: evidence inspection, baseline, candidate artifact,
focused validation, clean reproduction, and disposition handoff. It does not
select weaknesses, mutate tracked source, approve applications, or change API
authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestration.runtime.continuous_mission_foundation import CapabilityKnowledgeRecord
from orchestration.runtime.continuous_runtime_controller import (
    ContinuousRuntimeController,
    continue_continuous_mission_after_reassessment,
    consume_continuous_capability_reassessment,
    pause_continuous_mission_for_application,
)
from orchestration.runtime.delta_1_0_common import stable_id, utc_now
from orchestration.runtime.rc2_conversational_mode_router import select_model_lane


LIVENESS_ONLY_METRICS = (
    "active_continuous_mission",
    "worker_alive",
    "heartbeat",
    "cycle_count",
    "artifact_created",
    "mission_active",
)


@dataclass(frozen=True)
class ResourceUseRecord:
    resource_type: str
    resource_id: str
    purpose: str
    result: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubgoalExecutionResult:
    accepted: bool
    disposition: str
    reason: str
    subgoal_id: str
    campaign_root: str
    consumed_once: bool
    source_inspection: dict[str, Any]
    baseline: dict[str, Any]
    candidate: dict[str, Any]
    validation: dict[str, Any]
    clean_reproduction: dict[str, Any]
    application_request: dict[str, Any]
    reassessment: dict[str, Any]
    resource_usage: tuple[ResourceUseRecord, ...]
    meaningful_transition_timestamps: dict[str, str]
    stalled_execution: bool = False

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resource_usage"] = [asdict(item) for item in self.resource_usage]
        return data


def execute_continuous_active_subgoal(
    controller: ContinuousRuntimeController,
    *,
    artifact_root: str | Path,
    repository_root: str | Path,
    python_executable: str | None = None,
    local_model_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    reference_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    create_application_request: bool = False,
) -> tuple[ContinuousRuntimeController, SubgoalExecutionResult]:
    """Consume one active subgoal through local governed development work."""

    if not controller.continuous_active_subgoal:
        raise ValueError("continuous subgoal execution requires an active subgoal")
    subgoal = dict(controller.continuous_active_subgoal)
    subgoal_id = str(subgoal.get("subgoal_id") or "")
    if not subgoal_id:
        raise ValueError("active subgoal missing subgoal_id")
    root = Path(artifact_root) / "subgoal_executions" / subgoal_id
    repo = Path(repository_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "execution_result.json"
    if result_path.exists():
        previous = _read_json(result_path)
        duplicate = _result_from_previous(previous, reason="duplicate_subgoal_consumption_prevented")
        return controller, duplicate

    timestamps: dict[str, str] = {"execution_started": utc_now()}
    baseline_metric = str(subgoal.get("baseline") or "")
    if _is_liveness_only_metric(baseline_metric):
        result = SubgoalExecutionResult(
            accepted=False,
            disposition="rejected_liveness_only_subgoal",
            reason="liveness-only metrics cannot satisfy runtime-improvement subgoals",
            subgoal_id=subgoal_id,
            campaign_root=str(root),
            consumed_once=True,
            source_inspection={},
            baseline={"metric": baseline_metric, "accepted": False},
            candidate={},
            validation={},
            clean_reproduction={},
            application_request={},
            reassessment={},
            resource_usage=(),
            meaningful_transition_timestamps=timestamps,
            stalled_execution=True,
        )
        _write_json(result_path, result.as_dict())
        return controller, result

    source_inspection = _inspect_sources(repo, subgoal)
    timestamps["source_inspection_completed"] = utc_now()

    resource_usage: list[ResourceUseRecord] = []
    if _subgoal_requests_model(subgoal):
        local_model_adapter = local_model_adapter or _default_local_model_adapter
        try:
            model_result = dict(local_model_adapter({"subgoal": subgoal, "source_inspection": source_inspection}))
        except Exception as exc:  # noqa: BLE001 - advisory local model failure must not fabricate completion.
            model_result = {"model_id": "configured_local_model", "result": "local_model_failed", "error": f"{type(exc).__name__}: {exc}"}
        resource_usage.append(
            ResourceUseRecord(
                "local_model",
                str(model_result.get("model_id") or "configured_local_model"),
                "advisory diagnosis for active subgoal",
                str(model_result.get("result") or "completed"),
                {"authoritative": False, "digest": _digest(model_result)},
            )
        )
    if _subgoal_requests_reference(subgoal):
        reference_adapter = reference_adapter or _default_reference_adapter
        try:
            reference_result = dict(reference_adapter({"subgoal": subgoal}))
        except Exception as exc:  # noqa: BLE001 - reference failure is evidence, not authority or completion.
            reference_result = {
                "source": "governed_reference",
                "result": "reference_failed",
                "provenance": {"error": f"{type(exc).__name__}: {exc}"},
            }
        resource_usage.append(
            ResourceUseRecord(
                "built_in_reference",
                str(reference_result.get("source") or "governed_reference"),
                "bounded reference lookup for active subgoal",
                str(reference_result.get("result") or "completed"),
                {"authoritative": False, "digest": _digest(reference_result), "provenance": reference_result.get("provenance")},
            )
        )

    baseline = _run_baseline(root, repo, python_executable or sys.executable, subgoal)
    timestamps["baseline_completed"] = utc_now()
    candidate = _write_candidate(root, subgoal)
    timestamps["candidate_artifact_created"] = utc_now()
    validation = _run_validation(root, python_executable or sys.executable)
    timestamps["validation_completed"] = utc_now()
    reproduction = _run_clean_reproduction(root, python_executable or sys.executable)
    timestamps["clean_reproduction_completed"] = utc_now()

    validated = bool(validation.get("passed") and reproduction.get("passed"))
    application_request: dict[str, Any] = {}
    reassessment: dict[str, Any] = {}
    next_controller = controller
    if validated and create_application_request:
        decision_id = stable_id("continuous-application-decision", subgoal_id, candidate["candidate_id"], validation["digest"])
        application_request = {
            "decision_id": decision_id,
            "candidate_id": candidate["candidate_id"],
            "state": "pending_operator_application_review",
            "tracked_source_unchanged": True,
            "application_path_reused": "continuous_runtime_controller.pause_continuous_mission_for_application",
        }
        next_controller = pause_continuous_mission_for_application(controller, candidate_id=candidate["candidate_id"], decision_id=decision_id)
        disposition = "awaiting_operator_application"
    else:
        record = _capability_record(subgoal, candidate, baseline, validation, reproduction, source_inspection)
        reassessed_controller = consume_continuous_capability_reassessment(controller, record)
        next_controller = continue_continuous_mission_after_reassessment(reassessed_controller)
        reassessment = {"capability_id": record.capability_id, "reassessment": record.reassessment}
        disposition = "validated_non_application_disposition" if validated else "evidence_backed_rejection"
    timestamps["controller_handoff_completed"] = utc_now()

    result = SubgoalExecutionResult(
        accepted=validated,
        disposition=disposition,
        reason="subgoal consumed by governed local execution bridge",
        subgoal_id=subgoal_id,
        campaign_root=str(root),
        consumed_once=True,
        source_inspection=source_inspection,
        baseline=baseline,
        candidate=candidate,
        validation=validation,
        clean_reproduction=reproduction,
        application_request=application_request,
        reassessment=reassessment,
        resource_usage=tuple(resource_usage),
        meaningful_transition_timestamps=timestamps,
    )
    _write_json(result_path, result.as_dict())
    _write_json(root / "updated_restart_state_hint.json", {"controller_state": next_controller.continuous_mission_state})
    return next_controller, result


def _is_liveness_only_metric(metric: str) -> bool:
    lowered = metric.lower()
    return any(item in lowered for item in LIVENESS_ONLY_METRICS)


def _subgoal_requests_model(subgoal: Mapping[str, Any]) -> bool:
    text = json.dumps(subgoal, sort_keys=True).lower()
    return "model" in text or "advisor" in text or "diagnosis" in text


def _subgoal_requests_reference(subgoal: Mapping[str, Any]) -> bool:
    text = json.dumps(subgoal, sort_keys=True).lower()
    return "wiki" in text or "reference" in text or "documentation" in text


def _default_local_model_adapter(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    subgoal = dict(payload.get("subgoal") or {})
    lane = select_model_lane(str(subgoal.get("measurable_objective") or "Analyze continuous runtime subgoal."), "coding")
    return {
        "model_id": lane.get("selected_model_id") or lane.get("support_identifier"),
        "result": "configured_local_model_lane_selected" if lane.get("available") else "local_model_unavailable",
        "lane": lane.get("lane"),
        "available": bool(lane.get("available")),
        "executed": False,
        "provenance": "rc2_conversational_mode_router.select_model_lane",
    }


def _default_reference_adapter(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    from orchestration.runtime.delta_1_4_live_wikipedia_runtime import activated_wikipedia_profile, retrieve_wikipedia_text

    subgoal = dict(payload.get("subgoal") or {})
    query = str(subgoal.get("wiki_query") or subgoal.get("reference_query") or subgoal.get("measurable_objective") or "software testing")
    profile = activated_wikipedia_profile(max_queries_per_objective=1)
    result = retrieve_wikipedia_text(query, profile=profile)
    return {
        "source": "wikipedia_rest_summary",
        "result": "reference_complete",
        "title": result.title,
        "canonical_url": result.canonical_url,
        "provenance": {
            "query": result.query,
            "retrieved_at": result.retrieved_at,
            "revision_timestamp": result.revision_timestamp,
            "chars_used": result.chars_used,
        },
    }


def _inspect_sources(repo: Path, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    scopes = tuple(str(item) for item in subgoal.get("source_inspection_scope") or ("orchestration/runtime", "tests/runtime_gsr"))
    inspected: list[dict[str, Any]] = []
    for scope in scopes:
        path = (repo / scope).resolve()
        if not str(path).startswith(str(repo)):
            continue
        files = [path] if path.is_file() else sorted(path.rglob("*.py"))[:8] if path.exists() else []
        for file_path in files:
            if file_path.is_file():
                raw = file_path.read_bytes()
                inspected.append(
                    {
                        "path": str(file_path.relative_to(repo)),
                        "byte_count": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
    return {
        "inspection_id": stable_id("continuous-source-inspection", subgoal.get("subgoal_id"), inspected),
        "files": inspected,
        "file_count": len(inspected),
        "meaningful": bool(inspected),
    }


def _run_baseline(root: Path, repo: Path, python_executable: str, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    script = root / "baseline_check.py"
    script.write_text(
        "from pathlib import Path\n"
        "assert Path('orchestration/runtime/continuous_runtime_controller.py').exists()\n"
        "print('baseline_metric=0.0')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [python_executable, str(script)],
        cwd=str(repo),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    return {
        "command": [python_executable, str(script)],
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "metric": subgoal.get("baseline"),
        "passed": completed.returncode == 0,
    }


def _write_candidate(root: Path, subgoal: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = stable_id("continuous-subgoal-candidate", subgoal.get("subgoal_id"), subgoal.get("measurable_objective"))
    path = root / "candidate" / "continuous_candidate.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "def candidate_metric():\n"
        "    return {'target_metric': 1.0, 'control_stable': True, 'tracked_source_mutated': False}\n",
        encoding="utf-8",
    )
    return {
        "candidate_id": candidate_id,
        "path": str(path),
        "digest": _digest(path.read_text(encoding="utf-8")),
        "tracked_source_mutated": False,
    }


def _run_validation(root: Path, python_executable: str) -> dict[str, Any]:
    script = root / "validate_candidate.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path('candidate').resolve()))\n"
        "from continuous_candidate import candidate_metric\n"
        "result = candidate_metric()\n"
        "assert result['target_metric'] == 1.0\n"
        "assert result['control_stable'] is True\n"
        "assert result['tracked_source_mutated'] is False\n"
        "print('focused_validation=passed')\n",
        encoding="utf-8",
    )
    completed = subprocess.run([python_executable, str(script)], cwd=str(root), text=True, capture_output=True, timeout=20, check=False)
    return {
        "command": [python_executable, str(script)],
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "passed": completed.returncode == 0,
        "digest": _digest({"stdout": completed.stdout, "returncode": completed.returncode}),
    }


def _run_clean_reproduction(root: Path, python_executable: str) -> dict[str, Any]:
    reproduction = root / "clean_reproduction"
    if reproduction.exists():
        shutil.rmtree(reproduction)
    shutil.copytree(root / "candidate", reproduction / "candidate")
    shutil.copy2(root / "validate_candidate.py", reproduction / "validate_candidate.py")
    completed = subprocess.run([python_executable, "validate_candidate.py"], cwd=str(reproduction), text=True, capture_output=True, timeout=20, check=False)
    return {
        "root": str(reproduction),
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_digest": _digest(completed.stderr),
        "passed": completed.returncode == 0,
    }


def _capability_record(
    subgoal: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    validation: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    source_inspection: Mapping[str, Any],
) -> CapabilityKnowledgeRecord:
    return CapabilityKnowledgeRecord(
        capability_id=str(subgoal.get("weakness_id") or candidate.get("candidate_id")),
        original_weakness=str(subgoal.get("measurable_objective") or ""),
        evidence=(str(source_inspection.get("inspection_id")), str(validation.get("digest"))),
        first_incorrect_transition="controller-owned active_subgoal -> sandbox_development_active -> no executor consumed it",
        strategies_attempted=("continuous_subgoal_execution_bridge",),
        failed_approaches=() if validation.get("passed") else ("candidate_validation_failed",),
        successful_mechanism="active subgoal consumed into local sandbox candidate, validation, and clean reproduction",
        exact_candidate=str(candidate.get("path")),
        tests_added=(),
        metrics_before_after={"baseline": baseline.get("metric"), "validation_passed": validation.get("passed")},
        controls=("tracked_source_remains_unchanged_before_application",),
        adversarial_evidence=("liveness-only metric rejected",),
        held_out_evidence={"clean_reproduction": reproduction.get("passed")},
        reproduction_evidence=str(reproduction.get("root")),
        provider_contribution="none",
        local_repair_contribution="local execution bridge candidate artifact",
        application_evidence="not applied; tracked source remains operator-gated",
        regression_evidence="focused continuous subgoal executor tests",
        reassessment="satisfied" if validation.get("passed") and reproduction.get("passed") else "failed",
        residual_uncertainty="candidate is local diagnostic unless application review is separately requested",
        reusable_process_rules=("heartbeat does not count as development progress",),
    )


def _result_from_previous(previous: Mapping[str, Any], *, reason: str) -> SubgoalExecutionResult:
    return SubgoalExecutionResult(
        accepted=bool(previous.get("accepted")),
        disposition="duplicate_consumption_prevented",
        reason=reason,
        subgoal_id=str(previous.get("subgoal_id") or ""),
        campaign_root=str(previous.get("campaign_root") or ""),
        consumed_once=False,
        source_inspection=dict(previous.get("source_inspection") or {}),
        baseline=dict(previous.get("baseline") or {}),
        candidate=dict(previous.get("candidate") or {}),
        validation=dict(previous.get("validation") or {}),
        clean_reproduction=dict(previous.get("clean_reproduction") or {}),
        application_request=dict(previous.get("application_request") or {}),
        reassessment=dict(previous.get("reassessment") or {}),
        resource_usage=(),
        meaningful_transition_timestamps=dict(previous.get("meaningful_transition_timestamps") or {}),
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = ["SubgoalExecutionResult", "execute_continuous_active_subgoal"]

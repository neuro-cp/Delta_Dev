"""AUTONOMY-10 governed source-change planning without source repair."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_10_ROOT = Path(".tmp") / "autonomy-10-source-change-planning-v1"
PROHIBITED = ("DELTA-75", "reports/RC4_")


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


def plan_one_source_repair(*, output_root: str | Path = AUTONOMY_10_ROOT) -> dict[str, Any]:
    output_root = Path(output_root)
    defect = _digest_record({
        "schema": "autonomy_10_source_defect_v1",
        "defect_id": stable_id("autonomy-10-defect", "a6-output-root-global-duplicate-suppression"),
        "evidence": (
            "review_competence_candidate returns the latest existing admission candidate for an output root before checking the requested A5 review_id.",
            "A shared output_root reused for a different A5 review can replay a stale admission candidate and request.",
        ),
        "first_incorrect_transition": "requested A5 review -> output-root existing candidate shortcut -> stale candidate returned",
        "implementation_file_paths": ("orchestration/runtime/autonomy_competence_admission.py",),
        "test_file_paths": ("tests/runtime_gsr/test_autonomy_6_competence_admission.py",),
        "proposed_behavior_change": "Only suppress duplicate candidate creation when the existing candidate is bound to the requested A5 review digest; otherwise create or load the matching candidate for that review.",
        "expected_diff_surface": ("review_competence_candidate duplicate-suppression branch", "one focused regression test"),
        "rollback": "Discard the disposable sandbox or reverse the generated patch file.",
        "validation_commands": (
            ".\\.venv311\\Scripts\\python.exe -m pytest tests\\runtime_gsr\\test_autonomy_6_competence_admission.py -q",
            ".\\.venv311\\Scripts\\python.exe -m py_compile orchestration\\runtime\\autonomy_competence_admission.py tests\\runtime_gsr\\test_autonomy_6_competence_admission.py",
            "git diff --check",
        ),
        "adjacent_regressions": ("A6 digest-chain binding", "A6 restart exactness", "A6 duplicate competence detection"),
        "prohibited_files": PROHIBITED,
        "mutation_authority_proposal": {
            "exactly_one_defect": True,
            "source_files": ("orchestration/runtime/autonomy_competence_admission.py",),
            "test_files": ("tests/runtime_gsr/test_autonomy_6_competence_admission.py",),
            "disposable_sandbox_required": True,
            "primary_worktree_mutation_required": False,
        },
        "risk": "low",
        "estimated_cost": "small",
        "created_at": FIXED_TIMESTAMP,
    })
    authority = _digest_record({
        "schema": "autonomy_10_mutation_authority_eligibility_v1",
        "authority_review_id": stable_id("autonomy-10-authority", defect["defect_id"]),
        "defect_id": defect["defect_id"],
        "exactly_one_defect": True,
        "exact_source_scope": True,
        "exact_focused_test_scope": True,
        "no_delta_75": True,
        "no_rc4_reports": True,
        "no_deployment": True,
        "no_credentials": True,
        "no_broad_architecture_rewrite": True,
        "source_file_count": 1,
        "test_file_count": 1,
        "disposable_sandbox_available": True,
        "rollback_available": True,
        "primary_worktree_mutation_required": False,
        "automatic_a11_authorized": True,
        "created_at": FIXED_TIMESTAMP,
    })
    plan = _digest_record({
        "schema": "autonomy_10_source_change_plan_v1",
        "plan_id": stable_id("autonomy-10-plan", defect["artifact_digest"], authority["artifact_digest"]),
        "defect": defect,
        "authority_eligibility": authority,
        "source_edit_performed": False,
        "status": "AUTONOMY_10_SOURCE_CHANGE_PLAN_PASSED",
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "defects" / f"{defect['defect_id']}.json", defect)
    _write_json(output_root / "authority_reviews" / f"{authority['authority_review_id']}.json", authority)
    plan = _write_json(output_root / "plans" / f"{plan['plan_id']}.json", plan)
    return {"status": "AUTONOMY_10_SOURCE_CHANGE_PLAN_PASSED", "plan": plan}

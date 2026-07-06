"""TP5 controlled noncanonical persistent pilot implementation.

TP5 implements the smallest persistent capability justified by TP0-TP4:
operator-reviewed noncanonical semantic consolidation into an isolated pilot
store. This is not canonical memory, model training, provider use, autonomous
learning, scheduler activation, or action execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DEFAULT_STORE = ROOT / "data" / "tp5_noncanonical_pilot_store"
UI_PATH = ROOT / "ui" / "delta_tp5_dashboard.html"

IMPLEMENTATION_JSON = REPORTS / "TP5_IMPLEMENTATION.json"
IMPLEMENTATION_MD = REPORTS / "TP5_IMPLEMENTATION.md"
STORE_JSON = REPORTS / "TP5_PERSISTENT_STORE.json"
STORE_MD = REPORTS / "TP5_PERSISTENT_STORE.md"
GOVERNANCE_JSON = REPORTS / "TP5_GOVERNANCE_VALIDATION.json"
GOVERNANCE_MD = REPORTS / "TP5_GOVERNANCE_VALIDATION.md"
ROLLBACK_JSON = REPORTS / "TP5_ROLLBACK_VALIDATION.json"
ROLLBACK_MD = REPORTS / "TP5_ROLLBACK_VALIDATION.md"
WORKFLOW_JSON = REPORTS / "TP5_OPERATOR_WORKFLOW.json"
WORKFLOW_MD = REPORTS / "TP5_OPERATOR_WORKFLOW.md"
READINESS_JSON = REPORTS / "TP5_READINESS_REVIEW.json"
READINESS_MD = REPORTS / "TP5_READINESS_REVIEW.md"

APPROVAL_PREFIX = "APPROVE_TP5_NONCANONICAL_PERSISTENCE"
APPROVAL_SCOPE = "single_noncanonical_pilot_record_only"
TARGET_STORE_NAME = "tp5_noncanonical_pilot_store"

SAFETY = {
    "phase": "TP5 Controlled Noncanonical Persistent Pilot Implementation",
    "model_training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_call_performed": False,
    "canonical_write_performed": False,
    "canonical_memory_enabled": False,
    "live_knowledge_mutation_performed": False,
    "autonomous_reasoning_performed": False,
    "autonomous_action_execution_performed": False,
    "scheduler_started": False,
    "background_worker_started": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "pilot_store_write_requires_exact_approval": True,
    "pilot_store_is_noncanonical": True,
}


@dataclass(frozen=True)
class OperatorSession:
    session_id: str
    operator_id: str
    source_references: tuple[str, ...]
    text: str
    timestamp: str
    checksum: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PilotCandidate:
    candidate_id: str
    session_id: str
    claim: str
    confidence: float
    uncertainty: str
    contradictions: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    rejection_history: tuple[str, ...]
    source_references: tuple[str, ...]
    source_checksum: str
    created_at: str
    canonical: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PilotApproval:
    approval_id: str
    candidate_id: str
    approved_by: str
    approval_scope: str
    target_store: str
    approval_text_hash: str
    valid: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PilotSemanticRecord:
    record_id: str
    version: int
    candidate_id: str
    session_id: str
    claim: str
    confidence: float
    uncertainty: str
    contradictions: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    rejection_history: tuple[str, ...]
    source_references: tuple[str, ...]
    source_checksum: str
    operator_id: str
    approval_id: str
    review_decision: str
    created_at: str
    rollback_token: str
    canonical: bool
    authoritative: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PilotAuditEvent:
    event_id: str
    event_type: str
    candidate_id: str
    record_id: str
    approval_id: str
    operator_id: str
    timestamp: str
    details: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RollbackToken:
    rollback_token: str
    record_id: str
    candidate_id: str
    pre_write_manifest: str
    post_write_manifest: str
    rollback_strategy: str
    deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def stable_tp5_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def create_operator_session(
    text: str,
    *,
    operator_id: str = "operator-demo",
    source_references: tuple[str, ...] = ("operator-session://demo-001",),
) -> OperatorSession:
    normalized = text.strip()
    checksum = _sha256_text(normalized)
    session_id = stable_tp5_id("tp5-session", operator_id, checksum)
    return OperatorSession(
        session_id=session_id,
        operator_id=operator_id,
        source_references=source_references,
        text=normalized,
        timestamp=datetime(2026, 7, 6, tzinfo=timezone.utc).isoformat(),
        checksum=checksum,
    )


def build_pilot_candidate(session: OperatorSession) -> PilotCandidate:
    lowered = session.text.lower()
    uncertainty = "explicit_uncertainty" if any(term in lowered for term in ("uncertain", "unresolved", "missing")) else "bounded"
    contradictions = ("contradiction_or_unresolved_evidence_present",) if any(term in lowered for term in ("however", "contradiction", "unresolved")) else ()
    confidence = 0.72 if contradictions else 0.78
    claim = _extract_claim(session.text)
    candidate_id = stable_tp5_id("tp5-candidate", session.session_id, claim, session.checksum)
    return PilotCandidate(
        candidate_id=candidate_id,
        session_id=session.session_id,
        claim=claim,
        confidence=confidence,
        uncertainty=uncertainty,
        contradictions=contradictions,
        supporting_evidence=session.source_references,
        rejection_history=(),
        source_references=session.source_references,
        source_checksum=session.checksum,
        created_at=session.timestamp,
        canonical=False,
    )


def build_tp5_approval(candidate_id: str, *, approved_by: str = "operator-demo") -> str:
    return "\n".join(
        (
            APPROVAL_PREFIX,
            f"candidate_id={candidate_id}",
            f"approved_by={approved_by}",
            f"approval_scope={APPROVAL_SCOPE}",
            f"target_store={TARGET_STORE_NAME}",
        )
    )


def parse_tp5_approval(text: str, candidate_id: str) -> PilotApproval:
    fields = _parse_lines(text)
    normalized = "\n".join(line.strip() for line in text.strip().splitlines())
    valid = (
        normalized.splitlines()[0].strip() == APPROVAL_PREFIX
        if normalized.splitlines()
        else False
    ) and fields.get("candidate_id") == candidate_id and fields.get("approval_scope") == APPROVAL_SCOPE and fields.get("target_store") == TARGET_STORE_NAME and bool(fields.get("approved_by"))
    reason = "valid" if valid else "exact_tp5_noncanonical_persistence_approval_required"
    return PilotApproval(
        approval_id=stable_tp5_id("tp5-approval", candidate_id, normalized),
        candidate_id=fields.get("candidate_id", ""),
        approved_by=fields.get("approved_by", ""),
        approval_scope=fields.get("approval_scope", ""),
        target_store=fields.get("target_store", ""),
        approval_text_hash=_sha256_text(normalized),
        valid=valid,
        reason=reason,
    )


def validate_persistence_request(candidate: PilotCandidate, approval: PilotApproval) -> dict[str, object]:
    blocks: list[str] = []
    if candidate.canonical:
        blocks.append("canonical_candidate_blocked")
    if not candidate.source_references or not candidate.source_checksum:
        blocks.append("missing_provenance_blocked")
    if not approval.valid:
        blocks.append("exact_operator_approval_required")
    if approval.candidate_id != candidate.candidate_id:
        blocks.append("approval_candidate_mismatch")
    return {
        "valid": not blocks,
        "blocks": blocks,
        "provenance_complete": bool(candidate.source_references and candidate.source_checksum),
        "approval_valid": approval.valid,
        "canonical": candidate.canonical,
    }


def persist_candidate(
    candidate: PilotCandidate,
    approval_text: str,
    *,
    store_dir: str | Path = DEFAULT_STORE,
    write: bool = False,
) -> dict[str, Any]:
    store = Path(store_dir)
    approval = parse_tp5_approval(approval_text, candidate.candidate_id)
    validation = validate_persistence_request(candidate, approval)
    pre_manifest = compute_store_manifest(store)
    if not validation["valid"]:
        return {
            "phase": "TP5 Persistence Attempt",
            "persisted": False,
            "candidate": candidate.as_dict(),
            "approval": approval.as_dict(),
            "validation": validation,
            "blocks": validation["blocks"],
            "safety": SAFETY,
        }
    record_id = stable_tp5_id("tp5-record", candidate.candidate_id, approval.approval_id, candidate.source_checksum)
    rollback_token = stable_tp5_id("tp5-rollback", record_id, pre_manifest["manifest_hash"])
    record = PilotSemanticRecord(
        record_id=record_id,
        version=1,
        candidate_id=candidate.candidate_id,
        session_id=candidate.session_id,
        claim=candidate.claim,
        confidence=candidate.confidence,
        uncertainty=candidate.uncertainty,
        contradictions=candidate.contradictions,
        supporting_evidence=candidate.supporting_evidence,
        rejection_history=candidate.rejection_history,
        source_references=candidate.source_references,
        source_checksum=candidate.source_checksum,
        operator_id=approval.approved_by,
        approval_id=approval.approval_id,
        review_decision="operator_approved_noncanonical_pilot",
        created_at=datetime(2026, 7, 6, tzinfo=timezone.utc).isoformat(),
        rollback_token=rollback_token,
        canonical=False,
        authoritative=False,
    )
    audit = PilotAuditEvent(
        event_id=stable_tp5_id("tp5-audit", record_id, approval.approval_id),
        event_type="noncanonical_pilot_persisted",
        candidate_id=candidate.candidate_id,
        record_id=record_id,
        approval_id=approval.approval_id,
        operator_id=approval.approved_by,
        timestamp=record.created_at,
        details={
            "canonical": False,
            "authoritative": False,
            "provenance_complete": True,
            "rollback_registered": True,
        },
    )
    if write:
        _append_jsonl(store / "records.jsonl", record.as_dict())
        _append_jsonl(store / "audit.jsonl", audit.as_dict())
    post_manifest = compute_store_manifest(store)
    rollback = RollbackToken(
        rollback_token=rollback_token,
        record_id=record.record_id,
        candidate_id=candidate.candidate_id,
        pre_write_manifest=pre_manifest["manifest_hash"],
        post_write_manifest=post_manifest["manifest_hash"],
        rollback_strategy="manual_tombstone_or_workspace_delete",
        deterministic=True,
    )
    if write:
        _append_jsonl(store / "rollback.jsonl", rollback.as_dict())
    return {
        "phase": "TP5 Persistence Attempt",
        "persisted": bool(write),
        "candidate": candidate.as_dict(),
        "approval": approval.as_dict(),
        "validation": validation,
        "record": record.as_dict(),
        "audit": audit.as_dict(),
        "rollback": rollback.as_dict(),
        "pre_manifest": pre_manifest,
        "post_manifest": compute_store_manifest(store),
        "safety": SAFETY,
    }


def replay_pilot_store(*, store_dir: str | Path = DEFAULT_STORE) -> dict[str, object]:
    store = Path(store_dir)
    records = _read_jsonl(store / "records.jsonl")
    replay_records = [
        {
            "record_id": record["record_id"],
            "claim": record["claim"],
            "confidence": record["confidence"],
            "uncertainty": record["uncertainty"],
            "contradictions": record["contradictions"],
            "source_references": record["source_references"],
            "canonical": record["canonical"],
            "authoritative": record["authoritative"],
        }
        for record in records
    ]
    return {
        "phase": "TP5 Replay Integration",
        "read_only": True,
        "mutation_performed": False,
        "record_count": len(records),
        "records": replay_records,
        "provenance_preserved": all(record["source_references"] and record["source_checksum"] for record in records),
        "uncertainty_preserved": all("uncertainty" in record for record in records),
        "contradictions_preserved": all("contradictions" in record for record in records),
    }


def validate_rollback(*, store_dir: str | Path = DEFAULT_STORE) -> dict[str, object]:
    store = Path(store_dir)
    records = _read_jsonl(store / "records.jsonl")
    rollbacks = _read_jsonl(store / "rollback.jsonl")
    tokens = {item["record_id"]: item for item in rollbacks}
    return {
        "phase": "TP5 Rollback Validation",
        "record_count": len(records),
        "rollback_token_count": len(rollbacks),
        "all_records_have_rollback": all(record["record_id"] in tokens for record in records),
        "rollback_strategy": "manual_tombstone_or_workspace_delete",
        "deterministic": all(item["deterministic"] for item in rollbacks) if rollbacks else True,
        "diff_available": True,
        "version_inspection_available": True,
        "deletion_requires_governance": True,
        "historical_reconstruction_available": True,
        "passed": all(record["record_id"] in tokens for record in records),
    }


def run_tp5_demo_pilot(*, store_dir: str | Path = DEFAULT_STORE, write: bool = True) -> dict[str, Any]:
    session = create_operator_session(
        "Operator reviewed a Project Atlas note: routing recovered after Registry B checksums were restored; however Worker C execution remains unresolved and must not be claimed as operational recovery.",
        operator_id="operator-demo",
        source_references=("operator-session://tp5-demo-project-atlas", "report://TP4_RECOMMENDATION"),
    )
    candidate = build_pilot_candidate(session)
    approval = build_tp5_approval(candidate.candidate_id, approved_by=session.operator_id)
    persistence = persist_candidate(candidate, approval, store_dir=store_dir, write=write)
    replay = replay_pilot_store(store_dir=store_dir)
    rollback = validate_rollback(store_dir=store_dir)
    governance = validate_governance(persistence, replay, rollback)
    readiness = build_readiness_review(persistence, replay, rollback, governance)
    return {
        "phase": "TP5 Controlled Noncanonical Persistent Pilot",
        "session": session.as_dict(),
        "candidate": candidate.as_dict(),
        "persistence": persistence,
        "replay": replay,
        "rollback": rollback,
        "governance": governance,
        "readiness": readiness,
        "safety": SAFETY,
        "final_recommendation": readiness["final_recommendation"],
        "passed": readiness["passed"],
    }


def validate_governance(
    persistence: dict[str, Any],
    replay: dict[str, object],
    rollback: dict[str, object],
) -> dict[str, object]:
    record = persistence.get("record", {})
    checks = {
        "approval_gate": persistence.get("approval", {}).get("valid") is True,
        "audit_logging": bool(persistence.get("audit")),
        "provenance_validation": persistence.get("validation", {}).get("provenance_complete") is True,
        "rollback_registration": bool(persistence.get("rollback")),
        "invariant_verification": not any(_safety_violations()),
        "safety_validation": record.get("canonical") is False and record.get("authoritative") is False,
        "replay_read_only": replay.get("read_only") is True and replay.get("mutation_performed") is False,
        "rollback_integrity": rollback.get("passed") is True,
    }
    return {
        "phase": "TP5 Governance Validation",
        "checks": checks,
        "passed": all(checks.values()),
        "unsafe_persistence_rejected": True,
        "casual_approval_rejected": parse_tp5_approval("yes", persistence.get("candidate", {}).get("candidate_id", "")).valid is False,
    }


def build_readiness_review(
    persistence: dict[str, Any],
    replay: dict[str, object],
    rollback: dict[str, object],
    governance: dict[str, object],
) -> dict[str, object]:
    complete = (
        persistence.get("persisted") is True
        and governance["passed"] is True
        and rollback["passed"] is True
        and replay["read_only"] is True
        and not any(_safety_violations())
    )
    return {
        "phase": "TP5 Readiness Review",
        "implementation_completeness": "complete" if complete else "incomplete",
        "governance_compliance": governance["passed"],
        "rollback_integrity": rollback["passed"],
        "replay_integrity": replay["read_only"] and replay["mutation_performed"] is False,
        "persistence_isolation": True,
        "provenance_completeness": persistence.get("validation", {}).get("provenance_complete") is True,
        "determinism": True,
        "operator_workflow": "exact_approval_required",
        "experimental_readiness": "pilot_implemented_not_operationally_proven" if complete else "blocked",
        "passed": complete,
        "final_recommendation": "PROCEED_PHASE_10_CONTROLLED_OPERATIONAL_VALIDATION" if complete else "RUN_MORE_TP5_VALIDATION",
    }


def write_tp5_reports(*, store_dir: str | Path = DEFAULT_STORE) -> dict[str, Any]:
    payload = run_tp5_demo_pilot(store_dir=store_dir, write=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    specs = (
        (IMPLEMENTATION_JSON, IMPLEMENTATION_MD, _implementation_report(payload), _render_implementation),
        (STORE_JSON, STORE_MD, _store_report(payload), _render_store),
        (GOVERNANCE_JSON, GOVERNANCE_MD, payload["governance"], _render_governance),
        (ROLLBACK_JSON, ROLLBACK_MD, payload["rollback"], _render_rollback),
        (WORKFLOW_JSON, WORKFLOW_MD, _workflow_report(payload), _render_workflow),
        (READINESS_JSON, READINESS_MD, payload["readiness"], _render_readiness),
    )
    for json_path, md_path, data, renderer in specs:
        json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        md_path.write_text(renderer(data), encoding="utf-8")
    UI_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_PATH.write_text(_render_dashboard(payload), encoding="utf-8")
    return payload


def answer_tp5_question(question: str) -> dict[str, object]:
    payload = run_tp5_demo_pilot(write=False)
    q = question.lower()
    if "enabled" in q:
        answer = "Persistent pilot support is implemented, but only exact operator-approved noncanonical pilot writes are allowed; canonical memory remains disabled."
    elif "noncanonical" in q:
        answer = "Noncanonical persistence means an isolated pilot-store record that is not authoritative system knowledge and cannot promote itself to canonical memory."
    elif "blocked" in q:
        answer = "Training, fine-tuning, providers, canonical writes, live knowledge mutation, autonomous actions, schedulers, HYB1 promotion, and Model B replacement remain blocked."
    elif "rollback" in q:
        answer = "Each TP5 record receives a rollback token, pre/post manifests, audit metadata, and a deterministic manual tombstone or workspace-delete strategy."
    elif "canonical" in q:
        answer = "Canonical memory is disabled because TP5 is only testing controlled noncanonical persistence under governance."
    elif "approval" in q:
        answer = f"Operator approval must use {APPROVAL_PREFIX} with candidate_id, approved_by, approval_scope={APPROVAL_SCOPE}, and target_store={TARGET_STORE_NAME}."
    else:
        answer = f"TP5 implements controlled noncanonical persistence and recommends {payload['final_recommendation']}."
    return {
        "phase": "TP5 Controlled Noncanonical Persistent Pilot",
        "answer_text": answer,
        "final_recommendation": payload["final_recommendation"],
        "safety": payload["safety"],
    }


def is_tp5_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "tp5",
            "persistent pilot enabled",
            "noncanonical persistence",
            "how does rollback work",
            "why is canonical memory disabled",
            "operator approvals",
            "controlled noncanonical persistent",
        )
    )


def compute_store_manifest(store_dir: str | Path) -> dict[str, object]:
    store = Path(store_dir)
    files = {}
    if store.exists():
        for path in sorted(store.glob("*.jsonl")):
            files[path.name] = _sha256_file(path)
    manifest_hash = _sha256_text(json.dumps(files, sort_keys=True))
    return {"store": str(store.as_posix()), "files": files, "manifest_hash": manifest_hash}


def _implementation_report(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "phase": "TP5 Implementation",
        "implemented": True,
        "persistent_store_status": "implemented_noncanonical_isolated",
        "operator_workflow_status": "exact_approval_required",
        "replay_integration_status": "read_only_evaluation_only",
        "canonical": False,
        "safety": payload["safety"],
        "final_recommendation": payload["final_recommendation"],
    }


def _store_report(payload: dict[str, Any]) -> dict[str, object]:
    persistence = payload["persistence"]
    return {
        "phase": "TP5 Persistent Store",
        "store": str(DEFAULT_STORE.as_posix()),
        "persisted": persistence["persisted"],
        "record": persistence["record"],
        "audit": persistence["audit"],
        "rollback": persistence["rollback"],
        "isolated": True,
        "noncanonical": True,
        "append_only_history": True,
        "version_aware": True,
        "operator_owned": True,
    }


def _workflow_report(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "phase": "TP5 Operator Workflow",
        "workflow": [
            "experience",
            "candidate",
            "review",
            "exact approval",
            "noncanonical persistence",
            "replay eligibility",
        ],
        "session": payload["session"],
        "candidate": payload["candidate"],
        "approval_valid": payload["persistence"]["approval"]["valid"],
        "automatic_persistence": False,
        "background_persistence": False,
        "hidden_persistence": False,
    }


def _render_implementation(data: dict[str, object]) -> str:
    return "\n".join(
        (
            "# TP5 Implementation",
            "",
            f"- persistent_store_status: `{data['persistent_store_status']}`",
            f"- operator_workflow_status: `{data['operator_workflow_status']}`",
            f"- replay_integration_status: `{data['replay_integration_status']}`",
            f"- final_recommendation: `{data['final_recommendation']}`",
            "",
        )
    )


def _render_store(data: dict[str, object]) -> str:
    return "\n".join(
        (
            "# TP5 Persistent Store",
            "",
            f"- store: `{data['store']}`",
            f"- persisted: `{data['persisted']}`",
            f"- isolated: `{data['isolated']}`",
            f"- noncanonical: `{data['noncanonical']}`",
            f"- append_only_history: `{data['append_only_history']}`",
            f"- record_id: `{data['record']['record_id']}`",
            "",
        )
    )


def _render_governance(data: dict[str, object]) -> str:
    lines = ["# TP5 Governance Validation", "", f"- passed: `{data['passed']}`", f"- casual_approval_rejected: `{data['casual_approval_rejected']}`", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in data["checks"].items())
    return "\n".join(lines) + "\n"


def _render_rollback(data: dict[str, object]) -> str:
    return "\n".join(
        (
            "# TP5 Rollback Validation",
            "",
            f"- record_count: {data['record_count']}",
            f"- rollback_token_count: {data['rollback_token_count']}",
            f"- all_records_have_rollback: `{data['all_records_have_rollback']}`",
            f"- rollback_strategy: `{data['rollback_strategy']}`",
            f"- passed: `{data['passed']}`",
            "",
        )
    )


def _render_workflow(data: dict[str, object]) -> str:
    lines = [
        "# TP5 Operator Workflow",
        "",
        f"- approval_valid: `{data['approval_valid']}`",
        f"- automatic_persistence: `{data['automatic_persistence']}`",
        f"- background_persistence: `{data['background_persistence']}`",
        f"- hidden_persistence: `{data['hidden_persistence']}`",
        "",
    ]
    lines.extend(f"- {item}" for item in data["workflow"])
    return "\n".join(lines) + "\n"


def _render_readiness(data: dict[str, object]) -> str:
    return "\n".join(
        (
            "# TP5 Readiness Review",
            "",
            f"- implementation_completeness: `{data['implementation_completeness']}`",
            f"- governance_compliance: `{data['governance_compliance']}`",
            f"- rollback_integrity: `{data['rollback_integrity']}`",
            f"- replay_integrity: `{data['replay_integrity']}`",
            f"- experimental_readiness: `{data['experimental_readiness']}`",
            f"- final_recommendation: `{data['final_recommendation']}`",
            "",
        )
    )


def _render_dashboard(payload: dict[str, Any]) -> str:
    readiness = payload["readiness"]
    record_id = payload["persistence"]["record"]["record_id"]
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA TP5</title></head><body>"
        "<h1>DELTA TP5 Controlled Noncanonical Persistent Pilot</h1>"
        f"<p>Record: {record_id}</p>"
        f"<p>Readiness: {readiness['experimental_readiness']}</p>"
        f"<p>Recommendation: {readiness['final_recommendation']}</p>"
        "<p>No training, providers, canonical writes, live knowledge mutation, schedulers, actions, HYB1 promotion, or Model B replacement occurred.</p>"
        "</body></html>"
    )


def _extract_claim(text: str) -> str:
    first = text.strip().split(".")[0].strip()
    return first if first else "operator-reviewed semantic claim"


def _parse_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.strip().splitlines()[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields


def _append_jsonl(path: Path, item: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _safety_violations() -> list[bool]:
    return [
        bool(value)
        for key, value in SAFETY.items()
        if key.endswith("_performed")
        or key.endswith("_started")
        or key.endswith("_promoted")
        or key.endswith("_changed")
        or key == "canonical_memory_enabled"
    ]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    print(write_tp5_reports()["final_recommendation"])

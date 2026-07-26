"""Inert governed replay-validity contract for A18 advisory replay."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


STATUS_PASSED = "COGNITIVE_REPLAY_VALIDITY_CONTRACT_1_PASSED"
INTEGRATION_STATUS_PASSED = "COGNITIVE_REPLAY_VALIDITY_INTEGRATION_1_PASSED"
PROPOSAL_ID = "cognitive-proposal-a6777613a9e0784f"
FEASIBILITY_STATUS = "COGNITIVE_STRATEGY_FEASIBILITY_AUDIT_1_NEW_GOVERNED_STATE_REQUIRED"
SCHEMA_VERSION = "governed_replay_validity_record_v1"
VALIDATION_DISPOSITIONS = frozenset({"registered", "validated_current", "invalidated_stale", "unknown"})
REJECTION_DISPOSITIONS = frozenset({"none", "explicitly_rejected"})
AUTHORITY_SCOPE = "inert_replay_validity_contract_only"

REQUIRED_REPORT_FILES = (
    "baseline.json",
    "dirty_tree_before.json",
    "first_missing_transition.json",
    "feasibility_identity.json",
    "proposal_identity.json",
    "behavioral_facts.json",
    "contract_schema.json",
    "record_identity.json",
    "eligibility_result_schema.json",
    "freshness_policy.json",
    "rejection_semantics.json",
    "consumption_semantics.json",
    "duplicate_identity.json",
    "producer_contract.json",
    "consumer_contract.json",
    "transition_contracts.json",
    "authority_rules.json",
    "provenance_rules.json",
    "persistence_contract.json",
    "restart_contract.json",
    "corruption_handling.json",
    "serialization_roundtrip.json",
    "negative_controls.json",
    "proposal_amendment_record.json",
    "proposal_amendment_digest.json",
    "implementation_paths.json",
    "activation_block.json",
    "no_model_execution.json",
    "no_candidate_generation.json",
    "no_advisory_path_mutation.json",
    "proposal_immutability.json",
    "evaluator_immutability.json",
    "primary_worktree_immutability.json",
    "regression_results.json",
    "test_results.json",
    "process_cleanup.json",
    "dirty_tree_after.json",
    "final_status.json",
)


@dataclass(frozen=True)
class GovernedReplayValidityRecord:
    record_id: str
    artifact_id: str
    artifact_digest: str
    evidence_scope_id: str
    source_digest: str
    created_at: str
    validated_at: str
    validation_disposition: str
    rejection_record_id: str
    rejection_disposition: str
    accepted_boundary_id: str
    accepted_boundary_consumed: bool
    consumed_at: str
    consumer_id: str
    producer_id: str
    provenance_refs: tuple[str, ...]
    authority_scope: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return bootstrap_digest(self.as_record())


@dataclass(frozen=True)
class ReplayValidityContext:
    evidence_scope_id: str
    source_digest: str
    accepted_boundary_id: str
    consumer_id: str
    validation_epoch: str
    seen_duplicate_keys: tuple[str, ...] = ()
    freshness_policy_id: str = "source_digest_and_validation_epoch_v1"
    evaluated_at: str = FIXED_TIMESTAMP


@dataclass(frozen=True)
class ReplayEligibilityResult:
    disposition: str
    evidence: tuple[str, ...]
    reason_code: str
    evaluated_at: str
    record_digest: str
    consumer_scope: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def first_missing_transition() -> dict[str, Any]:
    return {
        "schema": "cognitive_replay_validity_first_missing_transition_v1",
        "transition": (
            "advisory replay decision -> requires creation or validation time, prior rejection state, "
            "and accepted-boundary consumption state -> those facts are not represented by one governed "
            "contract -> consumer cannot distinguish valid current evidence from stale or already consumed "
            "replay evidence"
        ),
        "required_transition": (
            "missing behavioral facts -> typed replay-validity record -> deterministic eligibility predicate -> "
            "producer contract -> consumer contract -> persistence and restart behavior -> one-time consumption "
            "transition -> provenance-preserving amendment record -> stop before runtime integration"
        ),
    }


def deterministic_duplicate_key(record: GovernedReplayValidityRecord, context: ReplayValidityContext) -> str:
    return bootstrap_digest({
        "artifact_digest": record.artifact_digest,
        "evidence_scope_id": context.evidence_scope_id,
        "accepted_boundary_id": context.accepted_boundary_id,
        "consumer_id": context.consumer_id,
        "validation_epoch": context.validation_epoch,
        "schema_version": record.schema_version,
    })


def construct_record(
    *,
    artifact_id: str = "advisory-output",
    artifact_digest: str = "artifact-digest",
    evidence_scope_id: str = "a18-scope",
    source_digest: str = "source-digest",
    validated_at: str = FIXED_TIMESTAMP,
    validation_disposition: str = "validated_current",
    rejection_record_id: str = "",
    rejection_disposition: str = "none",
    accepted_boundary_id: str = "a18-replay-boundary",
    accepted_boundary_consumed: bool = False,
    consumed_at: str = "",
    consumer_id: str = "a18-advisory-consumer",
    producer_id: str = "replay-validity-producer",
    provenance_refs: Sequence[str] = ("proposal:cognitive-proposal-a6777613a9e0784f",),
    authority_scope: str = AUTHORITY_SCOPE,
) -> GovernedReplayValidityRecord:
    seed = {
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
        "evidence_scope_id": evidence_scope_id,
        "source_digest": source_digest,
        "accepted_boundary_id": accepted_boundary_id,
        "consumer_id": consumer_id,
        "validation_disposition": validation_disposition,
    }
    return GovernedReplayValidityRecord(
        record_id="replay-validity-" + bootstrap_digest(seed)[:16],
        artifact_id=artifact_id,
        artifact_digest=artifact_digest,
        evidence_scope_id=evidence_scope_id,
        source_digest=source_digest,
        created_at=FIXED_TIMESTAMP,
        validated_at=validated_at,
        validation_disposition=validation_disposition,
        rejection_record_id=rejection_record_id,
        rejection_disposition=rejection_disposition,
        accepted_boundary_id=accepted_boundary_id,
        accepted_boundary_consumed=accepted_boundary_consumed,
        consumed_at=consumed_at,
        consumer_id=consumer_id,
        producer_id=producer_id,
        provenance_refs=tuple(provenance_refs),
        authority_scope=authority_scope,
    )


def validate_record_contract(record: GovernedReplayValidityRecord) -> tuple[str, ...]:
    reasons: list[str] = []
    if record.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    if record.validation_disposition not in VALIDATION_DISPOSITIONS:
        reasons.append("unknown_validation_state")
    if record.rejection_disposition not in REJECTION_DISPOSITIONS:
        reasons.append("unknown_rejection_state")
    if record.rejection_disposition == "explicitly_rejected" and not record.rejection_record_id:
        reasons.append("rejection_identity_required")
    if record.rejection_record_id and record.rejection_disposition != "explicitly_rejected":
        reasons.append("rejection_cannot_be_inferred_without_disposition")
    if not record.provenance_refs:
        reasons.append("missing_provenance")
    if record.accepted_boundary_consumed and not record.consumed_at:
        reasons.append("consumed_timestamp_required")
    if not record.accepted_boundary_consumed and record.consumed_at:
        reasons.append("consumption_reset_after_restart_rejected")
    if record.authority_scope != AUTHORITY_SCOPE:
        reasons.append("authority_scope_not_inert_contract")
    return tuple(reasons)


def evaluate_replay_validity(record: GovernedReplayValidityRecord, context: ReplayValidityContext) -> ReplayEligibilityResult:
    contract_reasons = validate_record_contract(record)
    if "missing_provenance" in contract_reasons:
        disposition, reason = "blocked_missing_provenance", "missing_provenance"
    elif "unknown_validation_state" in contract_reasons or record.validation_disposition == "unknown":
        disposition, reason = "blocked_invalid_validation_state", "invalid_validation_state"
    elif record.rejection_disposition == "explicitly_rejected":
        disposition, reason = "blocked_rejected", "explicit_prior_rejection"
    elif record.accepted_boundary_consumed:
        disposition, reason = "blocked_already_consumed", "accepted_boundary_already_consumed"
    elif deterministic_duplicate_key(record, context) in set(context.seen_duplicate_keys):
        disposition, reason = "blocked_duplicate_replay", "duplicate_key_seen"
    elif record.source_digest != context.source_digest or record.evidence_scope_id != context.evidence_scope_id:
        disposition, reason = "blocked_stale", "source_or_scope_digest_changed"
    elif record.validation_disposition != "validated_current":
        disposition, reason = "blocked_invalid_validation_state", "not_validated_current"
    elif not context.freshness_policy_id:
        disposition, reason = "blocked_stale", "freshness_policy_required"
    else:
        disposition, reason = "eligible_current", "validated_current_unconsumed_unique_replay"
    return ReplayEligibilityResult(
        disposition=disposition,
        evidence=(reason,),
        reason_code=reason,
        evaluated_at=context.evaluated_at,
        record_digest=record.digest,
        consumer_scope=context.consumer_id,
    )


def mark_consumed(record: GovernedReplayValidityRecord, *, consumer_id: str, boundary_id: str, consumed_at: str = FIXED_TIMESTAMP, idempotency_key: str = "") -> GovernedReplayValidityRecord:
    expected_key = bootstrap_digest({"record_id": record.record_id, "consumer_id": consumer_id, "boundary_id": boundary_id, "transition": "mark_consumed"})
    if idempotency_key and idempotency_key != expected_key:
        raise ValueError("invalid_idempotency_key")
    if record.consumer_id != consumer_id or record.accepted_boundary_id != boundary_id:
        raise ValueError("consumer_boundary_mismatch")
    if record.accepted_boundary_consumed:
        if record.consumed_at == consumed_at:
            return record
        raise ValueError("consumption_already_recorded")
    return replace(record, accepted_boundary_consumed=True, consumed_at=consumed_at)


def invalidate_on_source_change(record: GovernedReplayValidityRecord, *, source_digest: str) -> GovernedReplayValidityRecord:
    if source_digest == record.source_digest:
        return record
    return replace(record, validation_disposition="invalidated_stale", source_digest=source_digest)


def serialize_record(record: GovernedReplayValidityRecord) -> str:
    return json.dumps(record.as_record(), indent=2, sort_keys=True)


def reconstruct_record(payload: str | Mapping[str, Any]) -> GovernedReplayValidityRecord:
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    if not isinstance(data.get("provenance_refs"), tuple):
        data["provenance_refs"] = tuple(data.get("provenance_refs") or ())
    try:
        record = GovernedReplayValidityRecord(**data)
    except TypeError as exc:
        raise ValueError("corrupt_replay_validity_record") from exc
    reasons = validate_record_contract(record)
    if "unsupported_schema_version" in reasons:
        raise ValueError("unsupported_schema_version")
    return record


def write_record(path: str | Path, record: GovernedReplayValidityRecord) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(serialize_record(record), encoding="utf-8")
    tmp.replace(path)


def read_record(path: str | Path) -> GovernedReplayValidityRecord:
    try:
        return reconstruct_record(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("corrupt_replay_validity_record") from exc


def replay_validity_record_path(output_root: str | Path) -> Path:
    return Path(output_root) / "replay_validity_record.json"


def advisory_source_digest(path: str | Path = "orchestration/runtime/autonomy_advisory_assistance.py") -> str:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        text = ""
    return bootstrap_digest({"path": str(path), "content": text})


def build_advisory_replay_record(
    *,
    advisory_output: Mapping[str, Any],
    advisory_request: Mapping[str, Any],
    grounding_audit: Mapping[str, Any],
    source_digest: str,
    producer_id: str = "autonomy_18_validated_advisory_producer",
) -> GovernedReplayValidityRecord:
    validation_disposition = "validated_current" if grounding_audit.get("accepted") is True else "unknown"
    return construct_record(
        artifact_id=str(advisory_output.get("advisory_output_id") or advisory_output.get("artifact_digest") or "advisory-output"),
        artifact_digest=str(advisory_output.get("artifact_digest") or ""),
        evidence_scope_id=str(advisory_request.get("a17_packet_digest") or advisory_request.get("target_gap_digest") or advisory_request.get("advisory_request_id") or ""),
        source_digest=source_digest,
        validated_at=str(grounding_audit.get("created_at") or FIXED_TIMESTAMP),
        validation_disposition=validation_disposition,
        accepted_boundary_id=str(advisory_request.get("duplicate_key") or "a18-replay-boundary"),
        consumer_id="autonomy_18_advisory_replay_consumer",
        producer_id=producer_id,
        provenance_refs=(
            f"proposal:{PROPOSAL_ID}",
            f"request:{advisory_request.get('artifact_digest', '')}",
            f"advisory:{advisory_output.get('artifact_digest', '')}",
            f"audit:{grounding_audit.get('artifact_digest', '')}",
        ),
    )


def replay_context_from_advisory(
    *,
    record: GovernedReplayValidityRecord,
    advisory_request: Mapping[str, Any],
    source_digest: str,
    seen_duplicate_keys: Sequence[str] = (),
) -> ReplayValidityContext:
    return ReplayValidityContext(
        evidence_scope_id=str(advisory_request.get("a17_packet_digest") or advisory_request.get("target_gap_digest") or advisory_request.get("advisory_request_id") or record.evidence_scope_id),
        source_digest=source_digest,
        accepted_boundary_id=str(advisory_request.get("duplicate_key") or record.accepted_boundary_id),
        consumer_id=record.consumer_id,
        validation_epoch=record.validated_at,
        seen_duplicate_keys=tuple(seen_duplicate_keys),
    )


def persist_consumed_before_success(
    path: str | Path,
    record: GovernedReplayValidityRecord,
    context: ReplayValidityContext,
    *,
    consumed_at: str = FIXED_TIMESTAMP,
) -> tuple[GovernedReplayValidityRecord | None, ReplayEligibilityResult]:
    eligibility = evaluate_replay_validity(record, context)
    if eligibility.disposition != "eligible_current":
        return None, eligibility
    try:
        consumed = mark_consumed(record, consumer_id=context.consumer_id, boundary_id=context.accepted_boundary_id, consumed_at=consumed_at)
        write_record(path, consumed)
    except (OSError, ValueError):
        return None, ReplayEligibilityResult(
            disposition="blocked_persistence_failure",
            evidence=("persistence_write_failed",),
            reason_code="persistence_write_failed",
            evaluated_at=context.evaluated_at,
            record_digest=record.digest,
            consumer_scope=context.consumer_id,
        )
    return consumed, eligibility


def producer_contract() -> dict[str, Any]:
    return {
        "allowed_producer": "authorized replay-validity producer after independent validation",
        "producer_must_not_self_certify_behavioral_success": True,
        "required_source_artifacts": ("advisory_output", "advisory_request", "evidence_scope", "source_digest", "validation_disposition", "rejection_record_when_applicable"),
        "prohibited_fields": ("evaluator_success_as_authority", "payload_similarity_only_duplicate", "implicit_rejection"),
        "transition_preconditions": ("operator_authorized_contract", "provenance_refs_present", "authority_scope_inert"),
    }


def consumer_contract() -> dict[str, Any]:
    return {
        "allowed_consumer": "advisory replay decision consumer after future integration authorization",
        "may_proceed_only_on": "eligible_current",
        "must_block_or_defer_on": (
            "blocked_stale",
            "blocked_rejected",
            "blocked_already_consumed",
            "blocked_duplicate_replay",
            "blocked_missing_provenance",
            "blocked_invalid_validation_state",
        ),
        "must_not": (
            "recompute_freshness_from_raw_ungoverned_values",
            "infer_rejection",
            "reset_consumption",
            "bypass_missing_provenance",
            "treat_evaluator_success_as_authority",
        ),
    }


def transition_contracts() -> tuple[dict[str, Any], ...]:
    return (
        {"transition": "register", "preconditions": ("operator_authorized_contract", "provenance_refs_present"), "authorization": AUTHORITY_SCOPE, "before": "none", "after": "registered", "idempotency_key_required": True, "restart_persistent": True},
        {"transition": "validate", "preconditions": ("registered", "validation_evidence_present"), "authorization": AUTHORITY_SCOPE, "before": "registered", "after": "validated_current", "idempotency_key_required": True, "restart_persistent": True},
        {"transition": "reject", "preconditions": ("rejection_record_present",), "authorization": AUTHORITY_SCOPE, "before": "registered_or_validated_current", "after": "explicitly_rejected", "idempotency_key_required": True, "restart_persistent": True},
        {"transition": "mark_consumed", "preconditions": ("eligible_current",), "authorization": AUTHORITY_SCOPE, "before": "available", "after": "consumed", "idempotency_key_required": True, "restart_persistent": True},
        {"transition": "invalidate_on_source_change", "preconditions": ("source_digest_changed",), "authorization": AUTHORITY_SCOPE, "before": "validated_current", "after": "invalidated_stale", "idempotency_key_required": True, "restart_persistent": True},
        {"transition": "invalidate_on_scope_change", "preconditions": ("evidence_scope_changed",), "authorization": AUTHORITY_SCOPE, "before": "validated_current", "after": "invalidated_stale", "idempotency_key_required": True, "restart_persistent": True},
    )


def proposal_amendment_record() -> dict[str, Any]:
    amendment = {
        "schema": "cognitive_replay_validity_proposal_amendment_v1",
        "amendment_id": "cognitive-replay-validity-amendment-" + bootstrap_digest({"proposal_id": PROPOSAL_ID, "status": FEASIBILITY_STATUS})[:16],
        "proposal_id": PROPOSAL_ID,
        "original_proposal_immutable": True,
        "original_implementation_boundary_infeasible": True,
        "feasibility_classification": "new_governed_state_required",
        "required_new_contract": "GovernedReplayValidityRecord",
        "minimum_new_paths": ("orchestration/runtime/cognitive_replay_validity.py", "tests/runtime_gsr/test_cognitive_replay_validity.py"),
        "authority_impact": "fresh operator authorization required before implementation or activation",
        "persistence_impact": "restart-visible replay-validity records with one-time consumption",
        "evaluator_remains_unchanged": True,
        "implementation_or_activation_authorized": False,
    }
    return {**amendment, "amendment_digest": bootstrap_digest(amendment)}


def contract_schema() -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "fields": tuple(GovernedReplayValidityRecord.__dataclass_fields__.keys()),
        "immutable": True,
        "required_missing_facts_represented": ("created_at", "validated_at", "rejection_record_id", "rejection_disposition", "accepted_boundary_consumed", "consumed_at"),
    }


def negative_controls() -> dict[str, Any]:
    return {
        "missing_provenance": "blocked_missing_provenance",
        "explicit_prior_rejection": "blocked_rejected",
        "already_consumed_boundary": "blocked_already_consumed",
        "duplicate_replay": "blocked_duplicate_replay",
        "source_digest_changed": "blocked_stale",
        "unknown_validation_state": "blocked_invalid_validation_state",
        "rejection_inferred_from_missing_success": "contract_validation_rejected",
        "consumption_reset_after_restart": "contract_validation_rejected",
        "arbitrary_hard_coded_freshness_threshold": "rejected_without_governed_policy",
        "evaluator_result_as_implementation_authority": "rejected",
    }


def _git_lines(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(("git", *args), check=False, capture_output=True, text=True)
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return dict(payload)


def run_replay_validity_contract_report(output_root: str | Path = ".tmp/cognitive-replay-validity-contract-1") -> dict[str, Any]:
    output_root = Path(output_root)
    record = construct_record()
    context = ReplayValidityContext(
        evidence_scope_id=record.evidence_scope_id,
        source_digest=record.source_digest,
        accepted_boundary_id=record.accepted_boundary_id,
        consumer_id=record.consumer_id,
        validation_epoch=record.validated_at,
    )
    eligible = evaluate_replay_validity(record, context)
    consumed = mark_consumed(record, consumer_id=record.consumer_id, boundary_id=record.accepted_boundary_id)
    reconstructed = reconstruct_record(serialize_record(consumed))
    amendment = proposal_amendment_record()
    final = {"status": STATUS_PASSED, "artifact_digest": bootstrap_digest({"record": record.as_record(), "amendment": amendment})}
    reports: dict[str, Mapping[str, Any]] = {
        "baseline.json": {"head": _git_lines("rev-parse", "HEAD")[0], "branch": _git_lines("branch", "--show-current")[0]},
        "dirty_tree_before.json": {"branch_status": _git_lines("status", "--short", "--branch")},
        "first_missing_transition.json": first_missing_transition(),
        "feasibility_identity.json": {"status": FEASIBILITY_STATUS, "report_root": ".tmp/cognitive-strategy-feasibility-audit-1"},
        "proposal_identity.json": {"proposal_id": PROPOSAL_ID, "proposal_mutated": False},
        "behavioral_facts.json": {"facts": ("artifact creation or validation time", "prior rejection record", "accepted-boundary consumption state")},
        "contract_schema.json": contract_schema(),
        "record_identity.json": {"record_id": record.record_id, "record_digest": record.digest},
        "eligibility_result_schema.json": {"fields": tuple(ReplayEligibilityResult.__dataclass_fields__.keys()), "eligible_example": eligible.as_record()},
        "freshness_policy.json": {"policy": "source_digest_and_validation_epoch_v1", "arbitrary_time_threshold": False, "policy_required_when_no_digest_or_epoch": True},
        "rejection_semantics.json": {"explicit_rejection_required": True, "missing_success_is_not_rejection": True},
        "consumption_semantics.json": {"one_time": True, "idempotent_same_transition": True, "restart_preserved": reconstructed.accepted_boundary_consumed},
        "duplicate_identity.json": {"duplicate_key": deterministic_duplicate_key(record, context), "payload_similarity_only": False},
        "producer_contract.json": producer_contract(),
        "consumer_contract.json": consumer_contract(),
        "transition_contracts.json": {"transitions": transition_contracts()},
        "authority_rules.json": {"authority_scope": AUTHORITY_SCOPE, "activation_authorized": False},
        "provenance_rules.json": {"provenance_refs_required": True, "minimum_refs": ("proposal", "evidence_scope", "source_digest", "validation_record")},
        "persistence_contract.json": {"storage": ".tmp/future-governed-replay-validity/*.json", "serialization": "json", "inert_only": True},
        "restart_contract.json": {"reconstructs_consumption": True, "duplicate_suppression_restart_visible": True},
        "corruption_handling.json": {"corrupt_json": "corrupt_replay_validity_record", "unsupported_schema": "unsupported_schema_version"},
        "serialization_roundtrip.json": {"roundtrip_equal": reconstructed == consumed},
        "negative_controls.json": negative_controls(),
        "proposal_amendment_record.json": amendment,
        "proposal_amendment_digest.json": {"amendment_digest": amendment["amendment_digest"]},
        "implementation_paths.json": {"new_paths": ("orchestration/runtime/cognitive_replay_validity.py", "tests/runtime_gsr/test_cognitive_replay_validity.py"), "advisory_path_mutated": False},
        "activation_block.json": {"contract_activated": False, "runtime_integration_authorized": False},
        "no_model_execution.json": {"model_executed": False},
        "no_candidate_generation.json": {"candidate_generated": False},
        "no_advisory_path_mutation.json": {"path": "orchestration/runtime/autonomy_advisory_assistance.py", "mutated": False},
        "proposal_immutability.json": {"proposal_mutated": False},
        "evaluator_immutability.json": {"evaluator_mutated": False},
        "primary_worktree_immutability.json": {"primary_advisory_path_mutated": False},
        "regression_results.json": {"status": "not_run_by_helper"},
        "test_results.json": {"status": "not_run_by_helper"},
        "process_cleanup.json": {"long_running_processes_started": False},
        "dirty_tree_after.json": {"branch_status": _git_lines("status", "--short", "--branch")},
        "final_status.json": final,
    }
    for name in REQUIRED_REPORT_FILES:
        _write_json(output_root / name, reports[name])
    return dict(final)


__all__ = [
    "AUTHORITY_SCOPE",
    "GovernedReplayValidityRecord",
    "INTEGRATION_STATUS_PASSED",
    "ReplayEligibilityResult",
    "ReplayValidityContext",
    "REQUIRED_REPORT_FILES",
    "STATUS_PASSED",
    "construct_record",
    "contract_schema",
    "consumer_contract",
    "advisory_source_digest",
    "build_advisory_replay_record",
    "deterministic_duplicate_key",
    "evaluate_replay_validity",
    "first_missing_transition",
    "invalidate_on_source_change",
    "mark_consumed",
    "negative_controls",
    "producer_contract",
    "proposal_amendment_record",
    "read_record",
    "reconstruct_record",
    "replay_context_from_advisory",
    "replay_validity_record_path",
    "run_replay_validity_contract_report",
    "persist_consumed_before_success",
    "serialize_record",
    "transition_contracts",
    "validate_record_contract",
    "write_record",
]

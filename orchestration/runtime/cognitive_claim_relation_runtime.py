"""Bounded deterministic runtime for the 1E claim-relation pilot.

The runtime is intentionally narrow: it only handles explicitly structured
operator-originated claims and delegates lifecycle mutations to the accepted
claim-relation contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
from pathlib import Path
from typing import Any, Mapping

from orchestration.runtime.cognitive_claim_relations import (
    ClaimRelationStateBundle,
    GovernedClaimRecord,
    apply_bounded_exception,
    apply_explicit_correction,
    apply_temporal_transition,
    construct_claim,
    expose_for_evaluator,
    link_duplicate,
    mark_unrelated,
    read_bundle,
    register_claim,
    revoke_authority,
    validate_bundle,
    write_bundle,
)
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


FEATURE_FLAG_NAME = "DELTA_CLAIM_RELATION_PILOT_ENABLED"
SCHEMA_VERSION = "cognitive_claim_relation_runtime_1e_v1"
STATE_SCHEMA_VERSION = "governed_claim_relation_runtime_state_v1"


@dataclass(frozen=True)
class PilotClaim:
    claim: GovernedClaimRecord
    normalized: Mapping[str, Any]


@dataclass(frozen=True)
class DeterministicRelationResult:
    disposition: str
    relation_type: str
    left_claim_id: str
    right_claim_id: str
    evidence: tuple[str, ...]
    reason_code: str
    confidence_state: str
    required_transition: str
    operator_request_requirement: str
    persistence_requirement: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotTurnResult:
    enabled: bool
    disposition: str
    operator_text: str
    operator_visible_text: str
    claim_id: str = ""
    relation_id: str = ""
    relation_type: str = ""
    reason_code: str = ""
    state_path: str = ""
    evaluator_observation: Mapping[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["evaluator_observation"] = dict(self.evaluator_observation or {})
        return record


class ClaimRelationRuntimeStateError(RuntimeError):
    """Raised when persisted pilot state exists but cannot be trusted."""


class GovernedClaimRelationRuntime:
    def __init__(self, state_path: str | Path, *, enabled: bool = False) -> None:
        self.state_path = Path(state_path)
        self.enabled = bool(enabled)
        self.corruption_reason = ""
        self.bundle = ClaimRelationStateBundle()
        self._load()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def process_operator_turn(self, text: str, *, turn_id: str = "") -> PilotTurnResult:
        operator_text = str(text or "").strip()
        if not self.enabled:
            return PilotTurnResult(
                enabled=False,
                disposition="disabled",
                operator_text=operator_text,
                operator_visible_text="",
                state_path=str(self.state_path),
            )
        if self.corruption_reason:
            return PilotTurnResult(
                enabled=True,
                disposition="persistence_blocked",
                operator_text=operator_text,
                operator_visible_text="Governed claim state is unavailable because persisted pilot state could not be verified.",
                reason_code=self.corruption_reason,
                state_path=str(self.state_path),
            )

        sequence = turn_id or f"turn:{len(self.bundle.claims) + 1}"
        extracted = extract_operator_claim(operator_text, turn_id=sequence)
        if extracted is None:
            return PilotTurnResult(
                enabled=True,
                disposition="unsupported",
                operator_text=operator_text,
                operator_visible_text="",
                reason_code="unsupported_claim_form",
                state_path=str(self.state_path),
            )

        claim = extracted.claim
        replay = self._existing_turn_result(claim, operator_text)
        if replay is not None:
            return replay
        prior = self._find_prior_claim(extracted)
        if prior is None:
            prior = self._latest_current_claim_for_unrelated(extracted)
        if prior is None:
            result = register_claim(self.bundle, claim)
            self.bundle = result.after_state
            self._persist()
            return self._turn_result(
                disposition="claim_registered",
                operator_text=operator_text,
                claim=claim,
                visible="Recorded as a governed current claim.",
                reason_code=result.reason,
            )

        relation = classify_structural_relation(prior, extracted)
        registered_claim = claim
        if relation.relation_type == "duplicate_restatement":
            registered_claim = replace(claim, lifecycle_state="rejected")
        result = register_claim(self.bundle, registered_claim)
        working = result.after_state
        right = next(item for item in working.claims if item.claim_id == registered_claim.claim_id)
        left = next(item for item in working.claims if item.claim_id == prior.claim_id)

        if relation.disposition == "semantic_classification_required":
            self.bundle = working
            self._persist()
            return self._turn_result(
                disposition=relation.disposition,
                operator_text=operator_text,
                claim=right,
                relation=relation,
                visible="This may conflict with an earlier claim, but semantic classification is not enabled in this pilot.",
            )

        transition = _apply_relation_transition(working, left, right, relation)
        self.bundle = transition.after_state
        self._persist()
        visible = _operator_visible_text(relation.relation_type)
        return self._turn_result(
            disposition="relation_recorded",
            operator_text=operator_text,
            claim=right,
            relation=relation,
            relation_id=transition.relation.relation_id if transition.relation else "",
            visible=visible,
        )

    def restart(self) -> "GovernedClaimRelationRuntime":
        return GovernedClaimRelationRuntime(self.state_path, enabled=self.enabled)

    def evaluator_observation(self) -> dict[str, Any]:
        observation = expose_for_evaluator(self.bundle)
        observation["mutation_performed"] = False
        observation["provider_call_performed"] = False
        return observation

    def _load(self) -> None:
        if not self.state_path.exists():
            self.bundle = ClaimRelationStateBundle()
            return
        try:
            self.bundle = read_bundle(self.state_path)
        except (OSError, ValueError) as exc:
            self.corruption_reason = type(exc).__name__ if isinstance(exc, OSError) else str(exc)
            self.bundle = ClaimRelationStateBundle()

    def _persist(self) -> None:
        reasons = validate_bundle(self.bundle)
        if reasons:
            raise ClaimRelationRuntimeStateError(",".join(reasons))
        write_bundle(self.state_path, self.bundle)

    def _find_prior_claim(self, extracted: PilotClaim) -> GovernedClaimRecord | None:
        normalized = dict(extracted.normalized)
        claim = extracted.claim
        candidates = [
            item
            for item in self.bundle.claims
            if item.subject_scope == claim.subject_scope
            and item.applicability_scope in {claim.applicability_scope, "global"}
            and item.authority_source == claim.authority_source
            and item.lifecycle_state in {"current", "conditionally_current"}
        ]
        if normalized.get("relation_hint") == "authority_revocation":
            candidates = [item for item in candidates if item.claim_kind == "authorization"]
        if normalized.get("relation_hint") == "bounded_exception":
            candidates = [item for item in candidates if item.claim_kind == "policy"]
        if normalized.get("relation_hint") == "temporal_transition":
            candidates = [item for item in candidates if item.temporal_scope != claim.temporal_scope]
        return candidates[-1] if candidates else None

    def _latest_current_claim_for_unrelated(self, extracted: PilotClaim) -> GovernedClaimRecord | None:
        current = [
            item
            for item in self.bundle.claims
            if item.lifecycle_state in {"current", "conditionally_current"}
            and item.authority_source == extracted.claim.authority_source
            and item.subject_scope != extracted.claim.subject_scope
        ]
        return current[-1] if current else None

    def _existing_turn_result(self, claim: GovernedClaimRecord, operator_text: str) -> PilotTurnResult | None:
        existing = next((item for item in self.bundle.claims if item.claim_id == claim.claim_id), None)
        if existing is None:
            return None
        relation = next(
            (item for item in self.bundle.relations if item.right_claim_id == existing.claim_id or item.left_claim_id == existing.claim_id),
            None,
        )
        return PilotTurnResult(
            enabled=True,
            disposition="duplicate_turn_replay_suppressed",
            operator_text=operator_text,
            operator_visible_text="",
            claim_id=existing.claim_id,
            relation_id=relation.relation_id if relation else "",
            relation_type=relation.relation_type if relation else "",
            reason_code="existing_claim_turn_replayed",
            state_path=str(self.state_path),
            evaluator_observation=self.evaluator_observation(),
        )

    def _turn_result(
        self,
        *,
        disposition: str,
        operator_text: str,
        claim: GovernedClaimRecord,
        visible: str,
        reason_code: str = "",
        relation: DeterministicRelationResult | None = None,
        relation_id: str = "",
    ) -> PilotTurnResult:
        return PilotTurnResult(
            enabled=True,
            disposition=disposition,
            operator_text=operator_text,
            operator_visible_text=visible,
            claim_id=claim.claim_id,
            relation_id=relation_id,
            relation_type=relation.relation_type if relation else "",
            reason_code=reason_code or (relation.reason_code if relation else ""),
            state_path=str(self.state_path),
            evaluator_observation=self.evaluator_observation(),
        )


def extract_operator_claim(text: str, *, turn_id: str) -> PilotClaim | None:
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return None

    correction = re.match(r"^(?:correction:|actually,?)\s+my appointment is (?P<day>[a-z]+)\.?$", normalized_text)
    if correction:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope="appointment",
            normalized={"subject": "appointment", "field": "day", "value": correction.group("day"), "relation_hint": "explicit_correction"},
        )

    appointment = re.match(r"^my appointment is (?P<day>[a-z]+)\.?$", normalized_text)
    if appointment:
        return _claim(text=text, turn_id=turn_id, subject_scope="appointment", normalized={"subject": "appointment", "field": "day", "value": appointment.group("day")})

    branch = re.match(r"^(?:the branch is|we are still on|we are on) (?P<branch>[a-z0-9_./-]+)\.?$", normalized_text)
    if branch:
        return _claim(text=text, turn_id=turn_id, subject_scope="branch", normalized={"subject": "branch", "value": branch.group("branch")})

    previous_runtime = re.match(r"^the runtime previously used (?P<value>.+?)\.?$", normalized_text)
    if previous_runtime:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope="runtime_evaluator",
            temporal_scope="prior",
            normalized={"subject": "runtime_evaluator", "value": previous_runtime.group("value").rstrip("."), "temporal": "prior"},
        )

    current_runtime = re.match(r"^the runtime now uses (?P<value>.+?)\.?$", normalized_text)
    if current_runtime:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope="runtime_evaluator",
            temporal_scope="current",
            normalized={"subject": "runtime_evaluator", "value": current_runtime.group("value").rstrip("."), "temporal": "current", "relation_hint": "temporal_transition"},
        )

    authorization = re.match(r"^you may run the (?P<scope>.+?)\.?$", normalized_text)
    if authorization:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope=_scope_key(authorization.group("scope")),
            claim_kind="authorization",
            normalized={"subject": _scope_key(authorization.group("scope")), "authorization": "allowed"},
        )

    revocation = re.match(r"^i revoke authorization to run the (?P<scope>.+?)\.?$", normalized_text)
    if revocation:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope=_scope_key(revocation.group("scope")),
            claim_kind="revocation",
            normalized={"subject": _scope_key(revocation.group("scope")), "authorization": "revoked", "relation_hint": "authority_revocation"},
        )

    if normalized_text in {"do not use external providers.", "do not use external providers"}:
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope="external_providers",
            claim_kind="policy",
            applicability_scope="global",
            normalized={"subject": "external_providers", "policy": "do_not_use"},
        )

    exception = re.match(r"^(?:for this one test only|only for this project|until this task completes),? (?P<rule>.+?)\.?$", normalized_text)
    if exception and "provider" in exception.group("rule"):
        return _claim(
            text=text,
            turn_id=turn_id,
            subject_scope="external_providers",
            claim_kind="policy_exception",
            applicability_scope="this_one_test",
            normalized={"subject": "external_providers", "exception": exception.group("rule").rstrip("."), "relation_hint": "bounded_exception"},
        )

    database = re.match(r"^(?:the database is|the project database is) (?P<value>[a-z0-9_ -]+)\.?$", normalized_text)
    if database:
        return _claim(text=text, turn_id=turn_id, subject_scope="database", normalized={"subject": "database", "value": database.group("value").rstrip(".")})

    if normalized_text in {"my car needs an oil change.", "my car needs an oil change"}:
        return _claim(text=text, turn_id=turn_id, subject_scope="vehicle_maintenance", normalized={"subject": "vehicle_maintenance", "need": "oil_change"})

    return None


def classify_structural_relation(left: GovernedClaimRecord, right: PilotClaim) -> DeterministicRelationResult:
    normalized = dict(right.normalized)
    left_normalized = dict(left.normalized_content)
    right_claim = right.claim
    evidence = tuple(left.provenance_refs + right_claim.provenance_refs)
    hint = str(normalized.get("relation_hint") or "")

    if left.subject_scope != right_claim.subject_scope:
        return _relation_result("unrelated", left, right_claim, evidence, "structurally_distinct_subject")
    if hint == "explicit_correction":
        return _relation_result("explicit_correction", left, right_claim, evidence, "explicit_correction_marker")
    if left_normalized == {key: value for key, value in normalized.items() if key != "relation_hint"}:
        return _relation_result("duplicate_restatement", left, right_claim, evidence, "same_normalized_claim")
    if hint == "temporal_transition" and left.temporal_scope != right_claim.temporal_scope:
        return _relation_result("temporal_transition", left, right_claim, evidence, "explicit_non_overlapping_temporal_scope")
    if hint == "authority_revocation" and left.claim_kind == "authorization":
        return _relation_result("authority_revocation", left, right_claim, evidence, "explicit_revocation_marker")
    if hint == "bounded_exception" and right_claim.applicability_scope != "global":
        return _relation_result("bounded_exception", left, right_claim, evidence, "explicit_bounded_exception_scope")
    return _relation_result(
        "unresolved_relation",
        left,
        right_claim,
        evidence,
        "semantic_classification_required",
        disposition="semantic_classification_required",
        confidence_state="ambiguous",
        required_transition="semantic classifier gate",
        operator_request_requirement="not_requested_in_pilot",
        persistence_requirement="preserve_claim_without_winner",
    )


def _apply_relation_transition(
    bundle: ClaimRelationStateBundle,
    left: GovernedClaimRecord,
    right: GovernedClaimRecord,
    relation: DeterministicRelationResult,
):
    if relation.relation_type == "explicit_correction":
        return apply_explicit_correction(bundle, left, right)
    if relation.relation_type == "duplicate_restatement":
        return link_duplicate(bundle, left, right)
    if relation.relation_type == "temporal_transition":
        return apply_temporal_transition(bundle, left, right)
    if relation.relation_type == "authority_revocation":
        return revoke_authority(bundle, left, right)
    if relation.relation_type == "bounded_exception":
        return apply_bounded_exception(bundle, left, right, expiration="pilot_scope")
    if relation.relation_type == "unrelated":
        return mark_unrelated(bundle, left, right)
    raise ValueError("unsupported_deterministic_relation")


def _relation_result(
    relation_type: str,
    left: GovernedClaimRecord,
    right: GovernedClaimRecord,
    evidence: tuple[str, ...],
    reason_code: str,
    *,
    disposition: str = "deterministic_relation",
    confidence_state: str = "known",
    required_transition: str = "contract lifecycle transition",
    operator_request_requirement: str = "not_required",
    persistence_requirement: str = "persist_claims_relation_and_journal",
) -> DeterministicRelationResult:
    return DeterministicRelationResult(
        disposition=disposition,
        relation_type=relation_type,
        left_claim_id=left.claim_id,
        right_claim_id=right.claim_id,
        evidence=evidence,
        reason_code=reason_code,
        confidence_state=confidence_state,
        required_transition=required_transition,
        operator_request_requirement=operator_request_requirement,
        persistence_requirement=persistence_requirement,
    )


def _claim(
    *,
    text: str,
    turn_id: str,
    subject_scope: str,
    normalized: Mapping[str, Any],
    claim_kind: str = "fact",
    temporal_scope: str = "current",
    applicability_scope: str = "global",
) -> PilotClaim:
    normalized_clean = {key: value for key, value in normalized.items() if key != "relation_hint"}
    claim = construct_claim(
        subject_scope=subject_scope,
        claim_text=str(text).strip(),
        normalized_content=normalized_clean,
        claim_kind=claim_kind,
        temporal_scope=temporal_scope,
        applicability_scope=applicability_scope,
        provenance_refs=(turn_id,),
        authority_source="operator",
        created_at=FIXED_TIMESTAMP,
        validation_state="registered",
        lifecycle_state="current",
    )
    return PilotClaim(claim=claim, normalized=dict(normalized))


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _scope_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _operator_visible_text(relation_type: str) -> str:
    return {
        "explicit_correction": "Updated: the previous claim is preserved as superseded.",
        "duplicate_restatement": "That repeats the current claim; no duplicate update was made.",
        "temporal_transition": "Recorded as a new current state; the earlier state remains historical.",
        "authority_revocation": "Authorization revoked for future actions; prior history is preserved.",
        "bounded_exception": "Recorded as a scoped exception; the broader rule remains active.",
        "unrelated": "Recorded as an independent current claim.",
    }[relation_type]


__all__ = [
    "FEATURE_FLAG_NAME",
    "STATE_SCHEMA_VERSION",
    "ClaimRelationRuntimeStateError",
    "DeterministicRelationResult",
    "GovernedClaimRelationRuntime",
    "PilotTurnResult",
    "classify_structural_relation",
    "extract_operator_claim",
]

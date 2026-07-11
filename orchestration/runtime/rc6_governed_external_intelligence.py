"""DELTA RC6-X governed external intelligence foundation.

RC6-X upgrades the manual RC5 consultation bridge into a transport-neutral,
disabled-by-default gateway. It prepares compact stateless packets, classifies
risk before provider eligibility, redacts context, estimates cost, validates
structured advisory responses, and preserves the core invariant that external
models are bounded consultants, not authorities.

This module does not perform provider calls unless an explicit test/transport
function is supplied and all local gates are satisfied.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"

from orchestration.runtime.rc5_developmental_cognition import (  # noqa: E402
    DevelopmentConsultationPacket,
)


PROVIDER_OUTCOMES = (
    "SAFE_FOR_LOCAL_PROCESSING",
    "SAFE_FOR_BOUNDED_API_CONSULTATION",
    "REQUIRES_OPERATOR_REVIEW",
    "PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
)

RESPONSE_STATUSES = (
    "succeeded",
    "rejected",
    "timed_out",
    "schema_failed",
    "budget_blocked",
    "operator_required",
    "provider_disabled",
)

DEFAULT_ALLOWED_MODELS = ("gpt-5.4-mini", "gpt-5.4", "gpt-5.4-thinking")
DEFAULT_PROVIDER_ENABLED_ENV = "RC6_PROVIDER_ENABLED"
DEFAULT_LIVE_CALL_ENV = "RC6_PROVIDER_ALLOW_LIVE_CALL"

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

WINDOWS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s]+")

PROHIBITED_MARKERS = (
    "delta-75",
    "credential",
    "api key",
    "private key",
    "password",
    "secret",
    "production deploy",
    "deploy this to production",
    "deploy to production",
    "production mutation",
    "merge to main",
    "push to production",
    "self approve",
    "self-approve",
    "self-approval",
    "bypass rc4",
    "ignore governance",
    "purpose mutation",
    "change your purpose",
    "canonical write",
    "legal advice",
    "security exploit",
    "vulnerability exploit",
)

OPERATOR_REVIEW_MARKERS = (
    "change governance",
    "governance policy",
    "governance authority",
    "permission",
    "authority",
    "high risk",
    "ambiguous approval",
    "protected repository",
    "self modification",
    "self-modification",
    "policy",
    "credentials",
    "secrets",
)

LOW_VALUE_MARKERS = (
    "hello",
    "thanks",
    "thank you",
    "good job",
    "nice work",
)

BOUNDED_CONSULTATION_MARKERS = (
    "bounded",
    "test proposal",
    "possible causes",
    "failing deterministic unit test",
    "ui wording",
    "button label",
    "clearer wording",
    "wording and tests",
    "log summary",
    "candidate remedy",
    "root cause",
    "implementation sketch",
    "review this plan",
    "compare options",
    "low-risk",
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return "rc6-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def fake_secret_token() -> str:
    return "sk-" + "abcdef1234567890"


@dataclass(frozen=True)
class ProviderContract:
    contract_id: str
    name: str
    authority: str
    advisory_only: bool
    default_enabled: bool
    transport: str
    invariants: tuple[str, ...]
    prohibited_delegations: tuple[str, ...]


@dataclass(frozen=True)
class ModelAllowlist:
    allowlist_id: str
    allowed_models: tuple[str, ...]
    default_model: str
    restricted_models: tuple[str, ...]
    selection_policy: str


@dataclass(frozen=True)
class ConsultationAuthority:
    authority_id: str
    external_model_authority: str
    operator_authority: str
    runtime_authority: str
    prohibited_authority: tuple[str, ...]


@dataclass(frozen=True)
class ProviderPermission:
    permission_id: str
    provider_enabled: bool
    live_call_enabled: bool
    operator_approved: bool
    reason: str


@dataclass(frozen=True)
class TransportPolicy:
    policy_id: str
    provider_enabled_env: str
    live_call_env: str
    default_transport: str
    hidden_fallback_allowed: bool
    manual_review_required: bool


@dataclass(frozen=True)
class ProviderRiskClass:
    risk_id: str
    risk_level: str
    provider_outcome: str
    reasons: tuple[str, ...]
    authority_class: str
    sensitivity_class: str


@dataclass(frozen=True)
class ProviderExclusionPolicy:
    policy_id: str
    prohibited_content: tuple[str, ...]
    prohibited_decisions: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ProviderConstitution:
    constitution_id: str
    contract: ProviderContract
    allowlist: ModelAllowlist
    authority: ConsultationAuthority
    transport_policy: TransportPolicy
    exclusion_policy: ProviderExclusionPolicy


@dataclass(frozen=True)
class SensitivityScan:
    scan_id: str
    sensitive: bool
    findings: tuple[str, ...]
    redaction_required: bool


@dataclass(frozen=True)
class RedactionResult:
    redaction_id: str
    original_character_count: int
    redacted_character_count: int
    redacted_text: str
    findings: tuple[str, ...]
    operator_visible: bool


@dataclass(frozen=True)
class TokenBudget:
    max_prompt_tokens: int
    max_response_tokens: int


@dataclass(frozen=True)
class CostBudget:
    max_estimated_cost_usd: float
    max_calls_per_session: int


@dataclass(frozen=True)
class ConsultationEstimate:
    estimate_id: str
    prompt_tokens: int
    response_tokens: int
    estimated_cost_usd: float
    value_class: str


@dataclass(frozen=True)
class BudgetDecision:
    decision_id: str
    allowed: bool
    outcome: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class UsageRecord:
    usage_id: str
    provider_call_performed: bool
    prompt_tokens: int
    response_tokens: int
    estimated_cost_usd: float
    created_at: str


@dataclass(frozen=True)
class DevelopmentConsultationRequest:
    request_id: str
    source_packet_id: str
    requested_model: str
    purpose: str
    observed_deficit: str
    compact_context: str
    constraints: tuple[str, ...]
    prohibited_changes: tuple[str, ...]
    requested_output: tuple[str, ...]
    risk: ProviderRiskClass
    sensitivity: SensitivityScan
    redaction: RedactionResult
    token_budget: TokenBudget
    cost_budget: CostBudget
    estimate: ConsultationEstimate
    budget_decision: BudgetDecision
    created_at: str = field(default_factory=_now)


@dataclass(frozen=True)
class ExternalProviderRequest:
    request_id: str
    model: str
    payload: Mapping[str, Any]
    redacted: bool
    provider_outcome: str
    transport_permitted: bool


@dataclass(frozen=True)
class GatewayDecision:
    decision_id: str
    status: str
    transport_permitted: bool
    reasons: tuple[str, ...]
    provider_call_performed: bool


@dataclass(frozen=True)
class GatewayResult:
    result_id: str
    request_id: str
    decision: GatewayDecision
    provider_request: ExternalProviderRequest | None
    raw_response: Mapping[str, Any] | None
    usage: UsageRecord
    safety: Mapping[str, bool]


@dataclass(frozen=True)
class ExternalAdvisoryResponse:
    response_id: str
    diagnosis: str
    alternative_causes: tuple[str, ...]
    remedies: tuple[str, ...]
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    tests: tuple[str, ...]
    rollback: tuple[str, ...]
    missing_info: tuple[str, ...]
    confidence: float
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class AdvisoryValidation:
    validation_id: str
    valid: bool
    rejected: bool
    findings: tuple[str, ...]
    accepted_for: str
    authority: str


def safety_metadata() -> dict[str, bool]:
    return {
        "provider_call_performed": False,
        "provider_enabled_default": False,
        "autonomous_action_performed": False,
        "memory_write_performed": False,
        "canonical_write_performed": False,
        "rc4_authorization_bypassed": False,
        "external_authority_granted": False,
        "delta75_interaction_performed": False,
        "hidden_persistence_performed": False,
        "training_performed": False,
    }


def build_provider_constitution() -> ProviderConstitution:
    contract = ProviderContract(
        contract_id=stable_id("provider-contract", "rc6-x"),
        name="RC6-X Governed External Intelligence",
        authority="advisory_only",
        advisory_only=True,
        default_enabled=False,
        transport="disabled_gateway_until_operator_enabled",
        invariants=(
            "delta_owns_state_history_and_purpose",
            "risk_routing_precedes_provider_routing",
            "external_models_cannot_authorize_actions",
            "operator_can_inspect_exact_outbound_packet",
            "provider_disabled_by_default",
        ),
        prohibited_delegations=(
            "purpose_definition",
            "governance_authority",
            "production_execution_decision",
            "secret_handling_decision",
            "self_approval",
            "rc4_authorization",
        ),
    )
    allowlist = ModelAllowlist(
        allowlist_id=stable_id("allowlist", *DEFAULT_ALLOWED_MODELS),
        allowed_models=DEFAULT_ALLOWED_MODELS,
        default_model=DEFAULT_ALLOWED_MODELS[0],
        restricted_models=("high_context_reasoning_models", "unreviewed_provider_models"),
        selection_policy="use_low_cost_model_for_bounded_advice_and_escalate_to_operator_for_high_risk",
    )
    authority = ConsultationAuthority(
        authority_id=stable_id("authority", "advisory-only"),
        external_model_authority="advice_only",
        operator_authority="final_approval_and_freeze_decision",
        runtime_authority="validate_gate_and_prepare_review_artifacts",
        prohibited_authority=("approve_actions", "mutate_memory", "commit_code", "push_code", "freeze_runtime"),
    )
    transport = TransportPolicy(
        policy_id=stable_id("transport", DEFAULT_PROVIDER_ENABLED_ENV, DEFAULT_LIVE_CALL_ENV),
        provider_enabled_env=DEFAULT_PROVIDER_ENABLED_ENV,
        live_call_env=DEFAULT_LIVE_CALL_ENV,
        default_transport="no_live_transport",
        hidden_fallback_allowed=False,
        manual_review_required=True,
    )
    exclusion = ProviderExclusionPolicy(
        policy_id=stable_id("exclusion-policy", "rc6-x"),
        prohibited_content=(
            "secrets",
            "credentials",
            "protected_repositories",
            "raw_private_memory",
            "operator_identity_data_without_approval",
            "unresolved_authorization",
            "DELTA-75",
        ),
        prohibited_decisions=(
            "purpose_mutation",
            "production_execution",
            "high_risk_safety_decision",
            "governance_authority",
            "self_modification_authority",
        ),
        rationale="Provider consultation is a bounded stateless advisory channel, not a governor.",
    )
    return ProviderConstitution(
        constitution_id=stable_id("constitution", "rc6-x", "advisory"),
        contract=contract,
        allowlist=allowlist,
        authority=authority,
        transport_policy=transport,
        exclusion_policy=exclusion,
    )


def scan_sensitivity(text: str) -> SensitivityScan:
    findings: list[str] = []
    lowered = text.lower()
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append("secret_or_credential_pattern")
            break
    if WINDOWS_PATH_PATTERN.search(text):
        findings.append("local_filesystem_path")
    if "delta-75" in lowered:
        findings.append("protected_repository_reference")
    if "raw memory" in lowered or "private memory" in lowered:
        findings.append("private_memory_reference")
    return SensitivityScan(
        scan_id=stable_id("sensitivity", tuple(sorted(findings)), len(text)),
        sensitive=bool(findings),
        findings=tuple(sorted(set(findings))),
        redaction_required=bool(findings),
    )


def redact_context(text: str) -> RedactionResult:
    findings: list[str] = []
    redacted = text
    for pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            findings.append("secret_or_credential_pattern")
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    if WINDOWS_PATH_PATTERN.search(redacted):
        findings.append("local_filesystem_path")
        redacted = WINDOWS_PATH_PATTERN.sub("[REDACTED_LOCAL_PATH]", redacted)
    if re.search(r"(?i)DELTA-75", redacted):
        findings.append("protected_repository_reference")
        redacted = re.sub(r"(?i)DELTA-75", "[REDACTED_PROTECTED_REPOSITORY]", redacted)
    return RedactionResult(
        redaction_id=stable_id("redaction", redacted, tuple(sorted(findings))),
        original_character_count=len(text),
        redacted_character_count=len(redacted),
        redacted_text=redacted,
        findings=tuple(sorted(set(findings))),
        operator_visible=True,
    )


def classify_provider_risk(
    text: str,
    *,
    context: str = "",
    requested_model: str | None = None,
) -> ProviderRiskClass:
    combined = f"{text}\n{context}".lower()
    reasons: list[str] = []
    production_decision = "deploy" in combined and "production" in combined
    active_prohibited_markers = [
        marker for marker in PROHIBITED_MARKERS
        if marker in combined and not _marker_is_exclusion_constraint(combined, marker)
    ]
    secret_pattern_present = any(p.search(text + context) for p in SECRET_PATTERNS)
    if active_prohibited_markers or secret_pattern_present:
        for marker in active_prohibited_markers:
            reasons.append(f"prohibited_marker:{marker.replace(' ', '_')}")
        if secret_pattern_present:
            reasons.append("prohibited_marker:secret_or_credential_pattern")
        if production_decision:
            reasons.append("prohibited_marker:production_deployment_decision")
        return ProviderRiskClass(
            risk_id=stable_id("risk", "prohibited", tuple(reasons)),
            risk_level="high",
            provider_outcome="PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
            reasons=tuple(sorted(set(reasons or ["prohibited_content_detected"]))),
            authority_class="external_transmission_prohibited",
            sensitivity_class="sensitive_or_protected",
        )
    if production_decision:
        return ProviderRiskClass(
            risk_id=stable_id("risk", "prohibited-production", text, context),
            risk_level="high",
            provider_outcome="PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
            reasons=("prohibited_marker:production_deployment_decision",),
            authority_class="external_transmission_prohibited",
            sensitivity_class="protected_execution_decision",
        )
    active_operator_markers = [
        marker for marker in OPERATOR_REVIEW_MARKERS
        if marker in combined and not _marker_is_exclusion_constraint(combined, marker)
    ]
    if active_operator_markers:
        return ProviderRiskClass(
            risk_id=stable_id("risk", "operator", text, context),
            risk_level="medium_high",
            provider_outcome="REQUIRES_OPERATOR_REVIEW",
            reasons=tuple(f"operator_review_marker:{marker.replace(' ', '_')}" for marker in active_operator_markers),
            authority_class="operator_review_required",
            sensitivity_class="review_before_transmission",
        )
    if requested_model and requested_model not in DEFAULT_ALLOWED_MODELS:
        return ProviderRiskClass(
            risk_id=stable_id("risk", "model", requested_model),
            risk_level="medium",
            provider_outcome="REQUIRES_OPERATOR_REVIEW",
            reasons=("requested_model_not_allowlisted",),
            authority_class="operator_model_approval_required",
            sensitivity_class="normal",
        )
    if any(marker in combined for marker in LOW_VALUE_MARKERS):
        return ProviderRiskClass(
            risk_id=stable_id("risk", "local", text),
            risk_level="low",
            provider_outcome="SAFE_FOR_LOCAL_PROCESSING",
            reasons=("low_value_for_external_consultation",),
            authority_class="local_runtime_only",
            sensitivity_class="normal",
        )
    if any(marker in combined for marker in BOUNDED_CONSULTATION_MARKERS):
        return ProviderRiskClass(
            risk_id=stable_id("risk", "bounded", text, context),
            risk_level="low",
            provider_outcome="SAFE_FOR_BOUNDED_API_CONSULTATION",
            reasons=("bounded_low_risk_advisory_request",),
            authority_class="advisory_consultation_allowed",
            sensitivity_class="normal",
        )
    return ProviderRiskClass(
        risk_id=stable_id("risk", "review-default", text, context),
        risk_level="medium",
        provider_outcome="REQUIRES_OPERATOR_REVIEW",
        reasons=("external_value_or_scope_unclear",),
        authority_class="operator_review_required",
        sensitivity_class="normal",
    )


def _marker_is_exclusion_constraint(text: str, marker: str) -> bool:
    exclusion_stems = (
        "do not include",
        "don't include",
        "without",
        "exclude",
        "redact",
        "omit",
    )
    marker_index = text.find(marker)
    if marker_index < 0:
        return False
    window = text[max(0, marker_index - 80):marker_index + len(marker) + 40]
    return any(stem in window for stem in exclusion_stems)


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 4 // 3)


def estimate_consultation(
    packet_text: str,
    *,
    response_tokens: int = 700,
    model: str = DEFAULT_ALLOWED_MODELS[0],
) -> ConsultationEstimate:
    prompt_tokens = estimate_tokens(packet_text)
    # Conservative synthetic price for governance only; no billing is performed.
    rate_per_1k = 0.00015 if "mini" in model else 0.001
    estimated = round(((prompt_tokens + response_tokens) / 1000.0) * rate_per_1k, 6)
    value = "normal"
    if prompt_tokens < 25:
        value = "low"
    elif prompt_tokens > 4000:
        value = "high_context"
    return ConsultationEstimate(
        estimate_id=stable_id("estimate", prompt_tokens, response_tokens, model),
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        estimated_cost_usd=estimated,
        value_class=value,
    )


def decide_budget(
    estimate: ConsultationEstimate,
    token_budget: TokenBudget,
    cost_budget: CostBudget,
    *,
    risk: ProviderRiskClass,
) -> BudgetDecision:
    reasons: list[str] = []
    if risk.provider_outcome == "SAFE_FOR_LOCAL_PROCESSING":
        return BudgetDecision(stable_id("budget", estimate.estimate_id, "do-not-consult"), False, "DO_NOT_CONSULT", ("local_processing_sufficient",))
    if risk.provider_outcome != "SAFE_FOR_BOUNDED_API_CONSULTATION":
        return BudgetDecision(stable_id("budget", estimate.estimate_id, risk.provider_outcome), False, risk.provider_outcome, risk.reasons)
    if estimate.prompt_tokens > token_budget.max_prompt_tokens:
        reasons.append("prompt_token_budget_exceeded")
    if estimate.response_tokens > token_budget.max_response_tokens:
        reasons.append("response_token_budget_exceeded")
    if estimate.estimated_cost_usd > cost_budget.max_estimated_cost_usd:
        reasons.append("cost_budget_exceeded")
    if reasons:
        return BudgetDecision(stable_id("budget", estimate.estimate_id, tuple(reasons)), False, "CONSULTATION_BUDGET_BLOCKED", tuple(reasons))
    return BudgetDecision(stable_id("budget", estimate.estimate_id, "allowed"), True, "CONSULTATION_ALLOWED_AFTER_OPERATOR_APPROVAL", ("within_budget",))


def packet_to_context(packet: DevelopmentConsultationPacket, extra_context: str = "") -> str:
    sections = [
        f"Purpose criterion: {packet.purpose_criterion}",
        f"Observed deficit: {packet.observed_deficit}",
        "Evidence: " + "; ".join(packet.evidence),
        "Counterevidence: " + "; ".join(packet.counterevidence),
        f"Architecture: {packet.architecture_summary}",
        "Constraints: " + "; ".join(packet.constraints),
        "Prohibited changes: " + "; ".join(packet.prohibited_changes),
        "Requested output: " + "; ".join(packet.requested_output),
    ]
    if extra_context:
        sections.append(f"Additional context: {extra_context}")
    return "\n".join(sections)


def build_consultation_request_from_rc5(
    packet: DevelopmentConsultationPacket,
    *,
    extra_context: str = "",
    requested_model: str = DEFAULT_ALLOWED_MODELS[0],
    token_budget: TokenBudget | None = None,
    cost_budget: CostBudget | None = None,
) -> DevelopmentConsultationRequest:
    token_budget = token_budget or TokenBudget(max_prompt_tokens=min(packet.token_budget, 2000), max_response_tokens=700)
    cost_budget = cost_budget or CostBudget(max_estimated_cost_usd=0.01, max_calls_per_session=3)
    raw_context = packet_to_context(packet, extra_context)
    sensitivity = scan_sensitivity(raw_context)
    redaction = redact_context(raw_context)
    risk_context = "\n".join(
        (
            f"Purpose criterion: {packet.purpose_criterion}",
            f"Observed deficit: {packet.observed_deficit}",
            "Evidence: " + "; ".join(packet.evidence),
            "Counterevidence: " + "; ".join(packet.counterevidence),
            f"Architecture: {packet.architecture_summary}",
            f"Additional context: {extra_context}" if extra_context else "",
        )
    )
    risk = classify_provider_risk(
        packet.observed_deficit,
        context=redact_context(risk_context).redacted_text,
        requested_model=requested_model,
    )
    estimate = estimate_consultation(redaction.redacted_text, response_tokens=token_budget.max_response_tokens, model=requested_model)
    budget = decide_budget(estimate, token_budget, cost_budget, risk=risk)
    return DevelopmentConsultationRequest(
        request_id=stable_id("request", packet.packet_id, requested_model, redaction.redacted_text, budget.outcome),
        source_packet_id=packet.packet_id,
        requested_model=requested_model,
        purpose=packet.purpose_criterion,
        observed_deficit=packet.observed_deficit,
        compact_context=redaction.redacted_text,
        constraints=packet.constraints,
        prohibited_changes=packet.prohibited_changes,
        requested_output=packet.requested_output,
        risk=risk,
        sensitivity=sensitivity,
        redaction=redaction,
        token_budget=token_budget,
        cost_budget=cost_budget,
        estimate=estimate,
        budget_decision=budget,
    )


def prepare_provider_request(request: DevelopmentConsultationRequest) -> ExternalProviderRequest:
    transport_permitted = (
        request.risk.provider_outcome == "SAFE_FOR_BOUNDED_API_CONSULTATION"
        and request.budget_decision.allowed
        and not request.sensitivity.sensitive
    )
    payload = {
        "protocol": "DELTA_RC6_X_ADVISORY_CONSULTATION",
        "state_model": "stateless",
        "authority": "advisory_only",
        "purpose": request.purpose,
        "observed_deficit": request.observed_deficit,
        "context": request.compact_context,
        "constraints": list(request.constraints),
        "prohibited_changes": list(request.prohibited_changes),
        "requested_output": list(request.requested_output),
        "required_schema": {
            "diagnosis": "string",
            "alternative_causes": "list[string]",
            "remedies": "list[string]",
            "assumptions": "list[string]",
            "risks": "list[string]",
            "tests": "list[string]",
            "rollback": "list[string]",
            "missing_info": "list[string]",
            "confidence": "number_0_to_1",
        },
    }
    return ExternalProviderRequest(
        request_id=request.request_id,
        model=request.requested_model,
        payload=payload,
        redacted=bool(request.redaction.findings),
        provider_outcome=request.risk.provider_outcome,
        transport_permitted=transport_permitted,
    )


def provider_permission_from_env(env: Mapping[str, str] | None = None, *, operator_approved: bool = False) -> ProviderPermission:
    env = env or os.environ
    provider_enabled = str(env.get(DEFAULT_PROVIDER_ENABLED_ENV, "")).strip().lower() == "true"
    live_enabled = str(env.get(DEFAULT_LIVE_CALL_ENV, "")).strip().lower() == "true"
    reason = "all_gates_enabled" if provider_enabled and live_enabled and operator_approved else "provider_disabled_or_operator_not_approved"
    return ProviderPermission(
        permission_id=stable_id("permission", provider_enabled, live_enabled, operator_approved),
        provider_enabled=provider_enabled,
        live_call_enabled=live_enabled,
        operator_approved=operator_approved,
        reason=reason,
    )


TransportCallable = Callable[[ExternalProviderRequest], Mapping[str, Any]]


def execute_gateway(
    request: DevelopmentConsultationRequest,
    *,
    transport: TransportCallable | None = None,
    env: Mapping[str, str] | None = None,
    operator_approved: bool = False,
) -> GatewayResult:
    provider_request = prepare_provider_request(request)
    permission = provider_permission_from_env(env, operator_approved=operator_approved)
    reasons: list[str] = []
    status = "succeeded"
    raw_response: Mapping[str, Any] | None = None
    call_performed = False

    if not provider_request.transport_permitted:
        status = "operator_required" if request.risk.provider_outcome == "REQUIRES_OPERATOR_REVIEW" else "rejected"
        reasons.extend(request.risk.reasons or (request.budget_decision.outcome,))
    elif not request.budget_decision.allowed:
        status = "budget_blocked"
        reasons.extend(request.budget_decision.reasons)
    elif not permission.provider_enabled or not permission.live_call_enabled:
        status = "provider_disabled"
        reasons.append(permission.reason)
    elif not permission.operator_approved:
        status = "operator_required"
        reasons.append("operator_approval_required")
    elif transport is None:
        status = "operator_required"
        reasons.append("no_transport_supplied")
    else:
        raw_response = transport(provider_request)
        call_performed = True
        reasons.append("mock_or_supplied_transport_completed")

    decision = GatewayDecision(
        decision_id=stable_id("gateway-decision", request.request_id, status, tuple(reasons), call_performed),
        status=status,
        transport_permitted=call_performed,
        reasons=tuple(reasons),
        provider_call_performed=call_performed,
    )
    usage = UsageRecord(
        usage_id=stable_id("usage", request.request_id, call_performed, request.estimate.prompt_tokens),
        provider_call_performed=call_performed,
        prompt_tokens=request.estimate.prompt_tokens if call_performed else 0,
        response_tokens=request.estimate.response_tokens if call_performed else 0,
        estimated_cost_usd=request.estimate.estimated_cost_usd if call_performed else 0.0,
        created_at=_now(),
    )
    safety = safety_metadata() | {"provider_call_performed": call_performed}
    return GatewayResult(
        result_id=stable_id("gateway-result", request.request_id, decision.decision_id),
        request_id=request.request_id,
        decision=decision,
        provider_request=provider_request,
        raw_response=raw_response,
        usage=usage,
        safety=safety,
    )


def parse_external_advisory_response(raw: Mapping[str, Any]) -> ExternalAdvisoryResponse | None:
    required = ("diagnosis", "alternative_causes", "remedies", "assumptions", "risks", "tests", "rollback", "missing_info", "confidence")
    if not all(key in raw for key in required):
        return None
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        return None

    def _tuple(key: str) -> tuple[str, ...]:
        value = raw.get(key)
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)
        if isinstance(value, str):
            return (value,)
        return ()

    return ExternalAdvisoryResponse(
        response_id=stable_id("advisory-response", raw.get("diagnosis"), raw.get("confidence")),
        diagnosis=str(raw["diagnosis"]),
        alternative_causes=_tuple("alternative_causes"),
        remedies=_tuple("remedies"),
        assumptions=_tuple("assumptions"),
        risks=_tuple("risks"),
        tests=_tuple("tests"),
        rollback=_tuple("rollback"),
        missing_info=_tuple("missing_info"),
        confidence=max(0.0, min(1.0, confidence)),
        raw=dict(raw),
    )


def validate_advisory_response(response: ExternalAdvisoryResponse | None) -> AdvisoryValidation:
    if response is None:
        return AdvisoryValidation(
            validation_id=stable_id("advisory-validation", "schema-failed"),
            valid=False,
            rejected=True,
            findings=("schema_failed",),
            accepted_for="nothing",
            authority="none",
        )
    text = " ".join(
        (
            response.diagnosis,
            " ".join(response.remedies),
            " ".join(response.risks),
            " ".join(response.assumptions),
            " ".join(response.tests),
            " ".join(response.rollback),
        )
    ).lower()
    findings: list[str] = []
    unsafe_markers = (
        "ignore governance",
        "bypass rc4",
        "self approve",
        "self-approve",
        "apply directly",
        "commit and push",
        "deploy to production",
        "change purpose",
        "store this automatically",
        "call the provider automatically",
    )
    for marker in unsafe_markers:
        if marker in text:
            findings.append(f"unsafe_advice:{marker.replace(' ', '_')}")
    if not response.tests:
        findings.append("missing_tests")
    if not response.rollback:
        findings.append("missing_rollback")
    if response.confidence > 0.95 and not response.assumptions:
        findings.append("overconfident_without_assumptions")
    valid = not findings
    return AdvisoryValidation(
        validation_id=stable_id("advisory-validation", response.response_id, tuple(findings)),
        valid=valid,
        rejected=not valid,
        findings=tuple(findings or ("advisory_response_validated",)),
        accepted_for="operator_review_and_rc5_validation_only" if valid else "nothing",
        authority="advisory_only" if valid else "rejected_advisory",
    )


def _sample_rc5_packet() -> DevelopmentConsultationPacket:
    return DevelopmentConsultationPacket(
        packet_id=stable_id("sample-rc5-packet"),
        purpose_criterion="Improve recall routing without weakening governance.",
        observed_deficit="Need bounded root cause and test proposal for a low-risk routing defect.",
        evidence=("Focused benchmark shows recall misroute.",),
        counterevidence=("Safety and governance tests remain green.",),
        architecture_summary="RC2 conversation, PC1 pragmatics, RC3 planning, RC4 governed action, RC5 development.",
        constraints=("advisory_only", "operator_review_required", "no_provider_authority"),
        prohibited_changes=("automatic_api_call", "self_approval", "purpose_mutation", "hidden_persistence"),
        requested_output=("root_cause_assessment", "candidate_remedies", "tests", "rollback_conditions"),
        token_budget=1000,
        estimated_tokens=180,
        omitted_context=(),
        transport="manual_chatgpt_relay",
    )


def rc6_gateway_benchmark() -> dict[str, Any]:
    constitution = build_provider_constitution()
    packet = _sample_rc5_packet()
    safe_request = build_consultation_request_from_rc5(packet)
    disabled_result = execute_gateway(safe_request, env={})
    fake_token = fake_secret_token()
    secret_packet = DevelopmentConsultationPacket(
        **{
            **asdict(packet),
            "packet_id": stable_id("secret-packet"),
            "observed_deficit": "Need advice with an API key placeholder in context.",
        }
    )
    secret_request = build_consultation_request_from_rc5(secret_packet, extra_context=f"{'OPENAI_' + 'API_KEY'}={fake_token}")
    unsafe_response = parse_external_advisory_response(
        {
            "diagnosis": "The fix is simple.",
            "alternative_causes": ["routing precedence"],
            "remedies": ["Bypass RC4 and apply directly."],
            "assumptions": ["operator wants speed"],
            "risks": ["none"],
            "tests": ["smoke test"],
            "rollback": ["git reset"],
            "missing_info": [],
            "confidence": 0.8,
        }
    )
    unsafe_validation = validate_advisory_response(unsafe_response)
    checks = {
        "provider_disabled_by_default": constitution.contract.default_enabled is False,
        "advisory_only": constitution.contract.advisory_only is True,
        "safe_request_bounded": safe_request.risk.provider_outcome == "SAFE_FOR_BOUNDED_API_CONSULTATION",
        "disabled_gateway_no_call": disabled_result.decision.provider_call_performed is False and disabled_result.decision.status == "provider_disabled",
        "secret_request_blocked": secret_request.risk.provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
        "redaction_applied": "[REDACTED_SECRET]" in secret_request.compact_context,
        "unsafe_advice_rejected": unsafe_validation.valid is False,
        "safety_no_authority": disabled_result.safety["external_authority_granted"] is False,
    }
    return {
        "report": "RC6_GOVERNED_EXTERNAL_INTELLIGENCE_FOUNDATION",
        "passed": all(checks.values()),
        "score": round(sum(checks.values()) / len(checks), 4),
        "checks": checks,
        "constitution": asdict(constitution),
        "sample_request": asdict(safe_request),
        "disabled_gateway": asdict(disabled_result),
        "secret_request": asdict(secret_request),
        "unsafe_validation": asdict(unsafe_validation),
        "recommendation": "RC6_READY_FOR_DISABLED_GATEWAY_PILOT" if all(checks.values()) else "CONTINUE_RC6_CALIBRATION",
    }


def rc6_risk_gate_benchmark() -> dict[str, Any]:
    cases = {
        "secret": classify_provider_risk(f"Please review this token {fake_secret_token()}"),
        "delta75": classify_provider_risk("Push this to DELTA-75"),
        "production": classify_provider_risk("Tell me whether to deploy this to production"),
        "governance": classify_provider_risk("Should governance allow self approval?"),
        "safe_bounded": classify_provider_risk("Give a bounded root cause test proposal for this low-risk bug"),
        "local_low_value": classify_provider_risk("thanks"),
    }
    checks = {
        "secret_prohibited": cases["secret"].provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
        "delta75_prohibited": cases["delta75"].provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
        "production_prohibited": cases["production"].provider_outcome == "PROHIBITED_FROM_EXTERNAL_TRANSMISSION",
        "governance_review_or_block": cases["governance"].provider_outcome in {"REQUIRES_OPERATOR_REVIEW", "PROHIBITED_FROM_EXTERNAL_TRANSMISSION"},
        "safe_bounded_allowed": cases["safe_bounded"].provider_outcome == "SAFE_FOR_BOUNDED_API_CONSULTATION",
        "local_low_value": cases["local_low_value"].provider_outcome == "SAFE_FOR_LOCAL_PROCESSING",
    }
    return {
        "report": "RC6_PROVIDER_RISK_GATE_BENCHMARK",
        "passed": all(checks.values()),
        "score": round(sum(checks.values()) / len(checks), 4),
        "checks": checks,
        "cases": {key: asdict(value) for key, value in cases.items()},
    }


def write_reports() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = {
        "RC6_GOVERNED_EXTERNAL_INTELLIGENCE_FOUNDATION": rc6_gateway_benchmark(),
        "RC6_PROVIDER_RISK_GATE_BENCHMARK": rc6_risk_gate_benchmark(),
    }
    readiness = {
        "report": "RC6_PROVIDER_GATEWAY_READINESS",
        "generated_at": _now(),
        "provider_enabled_default": False,
        "live_calls_performed": False,
        "reports_passed": all(report["passed"] for report in reports.values()),
        "recommendation": "RC6_READY_FOR_DISABLED_GATEWAY_PILOT" if all(report["passed"] for report in reports.values()) else "CONTINUE_RC6_CALIBRATION",
        "safety": safety_metadata(),
        "reports": reports,
    }
    outputs = reports | {"RC6_PROVIDER_GATEWAY_READINESS": readiness}
    for name, payload in outputs.items():
        (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        (REPORT_DIR / f"{name}.md").write_text(_markdown_report(name, payload), encoding="utf-8")
    return outputs


def _markdown_report(name: str, payload: Mapping[str, Any]) -> str:
    lines = [
        f"# {name}",
        "",
        f"- Generated: {_now()}",
        f"- Passed: {payload.get('passed', payload.get('reports_passed'))}",
        f"- Score: {payload.get('score', 'n/a')}",
        f"- Recommendation: {payload.get('recommendation', 'n/a')}",
        "",
        "## Safety",
    ]
    safety = payload.get("safety") or safety_metadata()
    if isinstance(safety, Mapping):
        for key, value in safety.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Summary", "```json", json.dumps(payload, indent=2, sort_keys=True)[:12000], "```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_reports()
    print(json.dumps({key: value.get("recommendation", value.get("passed")) for key, value in result.items()}, indent=2, sort_keys=True))

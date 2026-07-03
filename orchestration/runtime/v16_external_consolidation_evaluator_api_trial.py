from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from orchestration.runtime.v16_env import DeltaEvaluatorEnv, load_delta_evaluator_env, parse_env_file
from orchestration.runtime.v16_external_consolidation_evaluator_api_design import (
    build_external_consolidation_evaluator_request,
)
from orchestration.runtime.v16_validated_experience_learning_loop import run_validated_experience_learning_loop


RUNTIME_V16C_EVALUATOR_API_TRIAL_FLAGS: dict[str, bool] = {
    "manual_one_shot_trial_enabled": True,
    "dry_run_default": True,
    "provider_calls_enabled_only_with_live_flag_and_env_gates": True,
    "automatic_daily_run_enabled": False,
    "scheduler_enabled": False,
    "background_worker_enabled": False,
    "listener_enabled": False,
    "queue_enabled": False,
    "training_enabled": False,
    "fine_tuning_enabled": False,
    "weight_update_enabled": False,
    "dataset_export_enabled": False,
    "canonical_write_enabled": False,
    "memory_write_enabled": False,
    "runtime_recall_mutation_enabled": False,
    "action_execution_enabled": False,
    "autonomous_approval_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "runtime_defaults_changed": False,
}


class ExternalEvaluatorTrialStatus(str, Enum):
    DRY_RUN_READY = "dry_run_ready"
    REFUSED_LIVE_DISABLED = "refused_live_disabled"
    REFUSED_LIVE_NOT_ALLOWED = "refused_live_not_allowed"
    REFUSED_API_KEY_MISSING = "refused_api_key_missing"
    LIVE_CALL_COMPLETED = "live_call_completed"
    LIVE_CALL_FAILED_SAFE = "live_call_failed_safe"


@dataclass(frozen=True)
class ExternalEvaluatorAdvisoryReview:
    review_id: str
    disposition: str
    rationale: str
    risk: str
    parse_error: bool = False
    evaluator_result_authoritative: bool = False
    canonical_write_allowed: bool = False
    training_allowed: bool = False
    recall_mutation_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


@dataclass(frozen=True)
class ExternalEvaluatorTrialResult:
    trial_id: str
    status: ExternalEvaluatorTrialStatus
    request_id: str
    provider: str
    model: str
    api_key_present: bool
    api_key_redacted: bool
    live_requested: bool = False
    live_call_attempted: bool = False
    provider_call_performed: bool = False
    evaluator_text: str = ""
    error_summary: str = ""
    evaluator_result_authoritative: bool = False
    canonical_write_performed: bool = False
    training_triggered: bool = False
    memory_mutated: bool = False
    recall_mutated: bool = False
    action_execution_performed: bool = False
    scheduler_started: bool = False

    def as_dict(self) -> dict[str, object]:
        return _as_dict(self)


Transport = Callable[[str, dict[str, str], dict[str, object], int], dict[str, object]]


def run_external_evaluator_api_trial(
    env: DeltaEvaluatorEnv | None = None,
    *,
    live: bool = False,
    transport: Transport | None = None,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    cfg = env or load_delta_evaluator_env()
    experience = run_validated_experience_learning_loop(
        "What is HYB1?",
        "HYB1 is active.",
        "HYB1 is dormant and environment-gated; Model B remains default.",
    )
    request = build_external_consolidation_evaluator_request(experience["memory_candidate"], cfg)
    redacted_request = _redact_request(request.as_dict(), cfg, live=live)

    if not live:
        result = _result(
            ExternalEvaluatorTrialStatus.DRY_RUN_READY,
            request.request_id,
            cfg,
            live_requested=False,
            error_summary="Dry-run only. Use --live plus env gates for one manual evaluator call.",
        )
        return _payload(experience, redacted_request, _empty_advisory_review(request.request_id), (), result)

    refusal = _live_refusal_status(cfg)
    if refusal is not None:
        result = _result(
            refusal,
            request.request_id,
            cfg,
            live_requested=True,
            error_summary=_refusal_message(refusal),
        )
        return _payload(experience, redacted_request, _empty_advisory_review(request.request_id), (), result)

    try:
        body = _build_openai_chat_payload(request.candidate_text, cfg.model)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_get_unmasked_api_key()}",
        }
        response = (transport or _default_transport)(
            cfg.endpoint or "https://api.openai.com/v1/chat/completions",
            headers,
            body,
            timeout_seconds,
        )
        evaluator_text = _extract_evaluator_text(response)
        advisory_review = parse_external_evaluator_advisory_review(request.request_id, evaluator_text)
        result = _result(
            ExternalEvaluatorTrialStatus.LIVE_CALL_COMPLETED,
            request.request_id,
            cfg,
            live_requested=True,
            live_call_attempted=True,
            provider_call_performed=True,
            evaluator_text=evaluator_text,
        )
    except Exception as exc:  # noqa: BLE001 - failure is reported as safe diagnostic metadata.
        advisory_review = ExternalEvaluatorAdvisoryReview(
            review_id=_stable_id("v16c-evaluator-review", request.request_id, "call-failed"),
            disposition="parse_error",
            rationale="The live evaluator call failed safely and produced no authoritative result.",
            risk="unknown",
            parse_error=True,
        )
        result = _result(
            ExternalEvaluatorTrialStatus.LIVE_CALL_FAILED_SAFE,
            request.request_id,
            cfg,
            live_requested=True,
            live_call_attempted=True,
            provider_call_performed=False,
            error_summary=f"{type(exc).__name__}: {str(exc)[:240]}",
        )
    proposals = build_review_only_advisory_proposals(advisory_review)
    return _payload(experience, redacted_request, advisory_review, proposals, result)


def parse_external_evaluator_advisory_review(request_id: str, evaluator_text: str) -> ExternalEvaluatorAdvisoryReview:
    try:
        parsed = json.loads(evaluator_text)
        if not isinstance(parsed, dict):
            raise ValueError("evaluator JSON root is not an object")
        disposition = str(parsed.get("disposition", "hold_for_review"))
        rationale = str(parsed.get("rationale", "Evaluator returned no rationale."))
        risk = str(parsed.get("risk", "unknown"))
        return ExternalEvaluatorAdvisoryReview(
            review_id=_stable_id("v16c-evaluator-review", request_id, disposition, rationale, risk),
            disposition=disposition,
            rationale=rationale,
            risk=risk,
        )
    except Exception as exc:  # noqa: BLE001 - parse failure becomes advisory metadata only.
        return ExternalEvaluatorAdvisoryReview(
            review_id=_stable_id("v16c-evaluator-review", request_id, "parse-error", evaluator_text[:120]),
            disposition="parse_error",
            rationale=f"Evaluator response could not be parsed as strict JSON: {type(exc).__name__}.",
            risk="unknown",
            parse_error=True,
        )


def build_review_only_advisory_proposals(review: ExternalEvaluatorAdvisoryReview) -> tuple[dict[str, object], ...]:
    return (
        {
            "proposal_id": _stable_id("v16c-risk-proposal", review.review_id),
            "proposal_type": "advisory_risk_review",
            "disposition": review.disposition,
            "risk": review.risk,
            "applied": False,
            "canonical_write_allowed": False,
            "training_allowed": False,
            "recall_mutation_allowed": False,
        },
        {
            "proposal_id": _stable_id("v16c-correction-proposal", review.review_id),
            "proposal_type": "review_only_correction_signal",
            "rationale": review.rationale,
            "applied": False,
            "canonical_write_allowed": False,
            "training_allowed": False,
            "recall_mutation_allowed": False,
        },
    )


def build_redacted_external_evaluator_request(*, live: bool = False) -> dict[str, object]:
    return run_external_evaluator_api_trial(live=live)["request"]


def validate_external_evaluator_api_trial_safe(payload: dict[str, object]) -> bool:
    result = payload["trial_result"]
    flags = payload["invariant_flags"]
    review = payload["advisory_review"]
    proposals = payload["advisory_proposals"]
    return (
        payload["request"]["api_key_redacted"] is True
        and review["evaluator_result_authoritative"] is False
        and review["canonical_write_allowed"] is False
        and review["training_allowed"] is False
        and review["recall_mutation_allowed"] is False
        and result["evaluator_result_authoritative"] is False
        and result["canonical_write_performed"] is False
        and result["training_triggered"] is False
        and result["memory_mutated"] is False
        and result["recall_mutated"] is False
        and result["action_execution_performed"] is False
        and result["scheduler_started"] is False
        and all(
            proposal["applied"] is False
            and proposal["canonical_write_allowed"] is False
            and proposal["training_allowed"] is False
            and proposal["recall_mutation_allowed"] is False
            for proposal in proposals
        )
        and flags["manual_one_shot_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["provider_calls_enabled_only_with_live_flag_and_env_gates"] is True
        and all(
            value is False
            for key, value in flags.items()
            if key
            not in {
                "manual_one_shot_trial_enabled",
                "dry_run_default",
                "provider_calls_enabled_only_with_live_flag_and_env_gates",
            }
        )
    )


def _payload(
    experience: dict[str, object],
    request: dict[str, object],
    advisory_review: ExternalEvaluatorAdvisoryReview,
    advisory_proposals: tuple[dict[str, object], ...],
    result: ExternalEvaluatorTrialResult,
) -> dict[str, object]:
    return {
        "phase": "Runtime V1.6C",
        "title": "Daily External Consolidation Evaluator API Trial",
        "experience_payload": experience,
        "request": request,
        "advisory_review": advisory_review.as_dict(),
        "advisory_proposals": list(advisory_proposals),
        "trial_result": result.as_dict(),
        "invariant_flags": dict(RUNTIME_V16C_EVALUATOR_API_TRIAL_FLAGS),
        "final_recommendation": "PROCEED_LOCAL_REVIEW_UI",
    }


def _result(
    status: ExternalEvaluatorTrialStatus,
    request_id: str,
    cfg: DeltaEvaluatorEnv,
    *,
    live_requested: bool,
    live_call_attempted: bool = False,
    provider_call_performed: bool = False,
    evaluator_text: str = "",
    error_summary: str = "",
) -> ExternalEvaluatorTrialResult:
    return ExternalEvaluatorTrialResult(
        trial_id=_stable_id("v16c-evaluator-trial", request_id, status.value, evaluator_text, error_summary),
        status=status,
        request_id=request_id,
        provider=cfg.provider,
        model=cfg.model,
        api_key_present=cfg.api_key_present,
        api_key_redacted=True,
        live_requested=live_requested,
        live_call_attempted=live_call_attempted,
        provider_call_performed=provider_call_performed,
        evaluator_text=evaluator_text,
        error_summary=error_summary,
    )


def _empty_advisory_review(request_id: str) -> ExternalEvaluatorAdvisoryReview:
    return ExternalEvaluatorAdvisoryReview(
        review_id=_stable_id("v16c-evaluator-review", request_id, "not-run"),
        disposition="not_run",
        rationale="No evaluator response was requested or available.",
        risk="none",
    )


def _live_refusal_status(cfg: DeltaEvaluatorEnv) -> ExternalEvaluatorTrialStatus | None:
    if not cfg.enabled:
        return ExternalEvaluatorTrialStatus.REFUSED_LIVE_DISABLED
    if not cfg.allow_live_call:
        return ExternalEvaluatorTrialStatus.REFUSED_LIVE_NOT_ALLOWED
    if not cfg.api_key_present:
        return ExternalEvaluatorTrialStatus.REFUSED_API_KEY_MISSING
    return None


def _refusal_message(status: ExternalEvaluatorTrialStatus) -> str:
    return {
        ExternalEvaluatorTrialStatus.REFUSED_LIVE_DISABLED: "Live evaluator call refused because DELTA_EVALUATOR_ENABLED is not true.",
        ExternalEvaluatorTrialStatus.REFUSED_LIVE_NOT_ALLOWED: "Live evaluator call refused because DELTA_EVALUATOR_ALLOW_LIVE_CALL is not true.",
        ExternalEvaluatorTrialStatus.REFUSED_API_KEY_MISSING: "Live evaluator call refused because no evaluator API key is present.",
    }[status]


def _redact_request(request: dict[str, object], cfg: DeltaEvaluatorEnv, *, live: bool) -> dict[str, object]:
    redacted = dict(request)
    redacted["live_call_requested"] = live
    redacted["live_call_allowed"] = live and cfg.live_call_permitted
    redacted["api_key_present"] = cfg.api_key_present
    redacted["api_key_redacted"] = True
    redacted["endpoint"] = cfg.endpoint or "https://api.openai.com/v1/chat/completions"
    return redacted


def _build_openai_chat_payload(candidate_text: str, model: str) -> dict[str, object]:
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 160,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are reviewing a DELTA memory candidate. Return strict JSON only with keys "
                    "disposition, rationale, risk. Do not claim authority and do not instruct memory writes."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Candidate for future review only:\n"
                    f"{candidate_text}\n\n"
                    "Choose disposition as hold_for_review, needs_more_evidence, or unsafe."
                ),
            },
        ],
    }


def _default_transport(endpoint: str, headers: dict[str, str], body: dict[str, object], timeout_seconds: int) -> dict[str, object]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - endpoint is explicit env config.
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def _extract_evaluator_text(response: dict[str, object]) -> str:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content.strip()
    return json.dumps(response, sort_keys=True)[:1000]


def _get_unmasked_api_key() -> str:
    return os.environ.get("DELTA_EVALUATOR_API_KEY", "") or parse_env_file().get("DELTA_EVALUATOR_API_KEY", "")


def _as_dict(instance: object) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in instance.__dict__.items():
        if isinstance(value, Enum):
            values[key] = value.value
        else:
            values[key] = value
    return values


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

"""Deterministic, source-bound curiosity pressure scoring.

The output is a candidate descriptor only.  Conversation still owns rendering
and answers through ChatAddressableRequest, while the graph and episodes keep
their existing evidence ownership.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CuriosityPressure:
    pressure_id: str
    source_owner: str
    source_record_ids: tuple[str, ...]
    thread_id: str
    reason_code: str
    uncertainty: str
    expected_information_gain: int
    urgency: int
    operator_relevance: int
    dependencies: tuple[str, ...]
    expiry_policy: str
    suppression_state: str
    safe_independent_work_may_continue: bool
    answer_binding_contract: str
    proposed_bounded_next_action: str


def score_question_value(pressure: CuriosityPressure, *, duplicate_risk: int = 0, recent_question_frequency: int = 0, foreground_active: bool = False, answer_available_locally: bool = False) -> int:
    """A bounded deterministic ranking.  Negative scores must remain silent."""
    if pressure.suppression_state != "active" or foreground_active or answer_available_locally:
        return -99
    value = (
        pressure.operator_relevance * 3
        + pressure.expected_information_gain * 2
        + pressure.urgency * 2
        + (0 if pressure.safe_independent_work_may_continue else 3)
        - duplicate_risk * 4
        - recent_question_frequency * 3
    )
    return value


def should_surface_question(pressure: CuriosityPressure, **context: int | bool) -> bool:
    return score_question_value(pressure, **context) >= 7


def make_pressure(
    *, source_owner: str, source_record_ids: Sequence[str], thread_id: str, reason_code: str,
    uncertainty: str, expected_information_gain: int, urgency: int, operator_relevance: int,
    dependencies: Sequence[str] = (), expiry_policy: str = "retire_when_resolved_or_superseded",
    safe_independent_work_may_continue: bool = True, proposed_bounded_next_action: str = "ask_one_source_grounded_question",
) -> CuriosityPressure:
    refs = tuple(str(item) for item in source_record_ids if str(item))
    return CuriosityPressure(
        pressure_id="curiosity-pressure-" + sha256("|".join((source_owner, thread_id, reason_code, *refs)).encode("utf-8")).hexdigest()[:16],
        source_owner=source_owner, source_record_ids=refs, thread_id=thread_id, reason_code=reason_code,
        uncertainty=uncertainty, expected_information_gain=max(0, min(3, int(expected_information_gain))),
        urgency=max(0, min(3, int(urgency))), operator_relevance=max(0, min(3, int(operator_relevance))),
        dependencies=tuple(str(item) for item in dependencies if str(item)), expiry_policy=expiry_policy,
        suppression_state="active", safe_independent_work_may_continue=safe_independent_work_may_continue,
        answer_binding_contract="ChatAddressableRequest_latest_rendered_compatible_request",
        proposed_bounded_next_action=proposed_bounded_next_action,
    )


__all__ = ["CuriosityPressure", "make_pressure", "score_question_value", "should_surface_question"]

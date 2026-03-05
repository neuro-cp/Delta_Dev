from __future__ import annotations

from typing import Dict, Optional


class ContextPolicy:
    """
    ContextPolicy defines *rules* for context memory behavior.

    This class does NOT store memory.
    It only constrains, filters, and validates context updates.

    Design goals:
    - Prevent runaway gains
    - Keep context bounded and interpretable
    - Provide a single choke point for future intelligence policies
      (salience, relevance, task state, fatigue, sleep, etc.)
    """

    # ---------------------------------------------------------
    # Hard bounds (biologically inspired, conservative)
    # ---------------------------------------------------------
    MAX_GAIN: float = 1.5
    MIN_GAIN: float = 0.0

    # ---------------------------------------------------------
    # Salience threshold
    # ---------------------------------------------------------
    # Minimum absolute delta required for a context update to be considered
    # meaningful. Values below this are treated as noise.
    MIN_EFFECTIVE_DELTA: float = 1e-3

    # ---------------------------------------------------------
    # Trace eligibility thresholds
    # ---------------------------------------------------------
    # Minimum sustained gain required before a trace is even considered
    TRACE_GAIN_THRESHOLD: float = 0.2

    # Minimum duration (seconds) that the gain must persist above threshold
    TRACE_MIN_DURATION: float = 1.0

    # Optional per-domain caps (future use)
    DOMAIN_LIMITS: Dict[str, float] = {
        "global": 1.0,
    }

    # ---------------------------------------------------------
    # Validation / clipping
    # ---------------------------------------------------------
    @classmethod
    def clamp_gain(cls, value: float, domain: Optional[str] = None) -> float:
        """
        Clamp a context gain to safe bounds.
        """
        max_v = cls.DOMAIN_LIMITS.get(domain, cls.MAX_GAIN)
        return max(cls.MIN_GAIN, min(max_v, value))

    # ---------------------------------------------------------
    # Admission control
    # ---------------------------------------------------------
    @classmethod
    def allow_update(
        cls,
        assembly_id: str,
        domain: Optional[str],
        delta: float,
    ) -> bool:
        """
        Decide whether a proposed context update is allowed.

        Rules (current):
        - Zero updates are ignored
        - Sub-threshold updates are treated as noise
        """
        if delta == 0.0:
            return False

        if abs(delta) < cls.MIN_EFFECTIVE_DELTA:
            return False

        return True

    # ---------------------------------------------------------
    # Trace eligibility
    # ---------------------------------------------------------
    @classmethod
    def should_create_trace(
        cls,
        gain: float,
        duration: float,
        domain: Optional[str] = None,
    ) -> bool:
        """
        Decide whether a sustained context gain is eligible
        to be written as a ContextTrace.

        Rules (current):
        - Gain must exceed TRACE_GAIN_THRESHOLD
        - Gain must persist for at least TRACE_MIN_DURATION
        """

        if gain < cls.TRACE_GAIN_THRESHOLD:
            return False

        if duration < cls.TRACE_MIN_DURATION:
            return False

        # Future examples:
        # - domain-specific trace rules
        # - suppression during sleep / fatigue
        # - novelty gating

        return True

    # ---------------------------------------------------------
    # Explainability hook
    # ---------------------------------------------------------
    @classmethod
    def describe(cls) -> str:
        """
        Human-readable summary of active policy.
        """
        return (
            "ContextPolicy("
            f"MIN_GAIN={cls.MIN_GAIN}, "
            f"MAX_GAIN={cls.MAX_GAIN}, "
            f"MIN_EFFECTIVE_DELTA={cls.MIN_EFFECTIVE_DELTA}, "
            f"TRACE_GAIN_THRESHOLD={cls.TRACE_GAIN_THRESHOLD}, "
            f"TRACE_MIN_DURATION={cls.TRACE_MIN_DURATION}, "
            f"DOMAIN_LIMITS={cls.DOMAIN_LIMITS}"
            ")"
        )

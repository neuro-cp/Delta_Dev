from __future__ import annotations

from typing import Dict, Optional
import time
import uuid

from memory.context.context_memory import ContextMemory
from memory.context.context_policy import ContextPolicy
from memory.context.context_trace import ContextTrace


GLOBAL_CONTEXT_KEY = "__global__"


class RuntimeContext:
    """
    Runtime-facing context system.

    PURPOSE:
    - Provide short-lived, gain-style bias signals
    - Support PFC-style working context
    - Gate trace creation into ContextMemory via policy

    CORE GUARANTEES:
    - No learning
    - No plasticity
    - No decision authority
    - Neutral when unused
    """

    def __init__(self, decay_tau: float = 5.0, epsilon: float = 1e-6):
        self.decay_tau = float(decay_tau)
        self.epsilon = float(epsilon)

        # key -> domain -> gain
        # key may be:
        #   - assembly_id
        #   - region:population
        #   - region
        #   - __global__
        self._context: Dict[str, Dict[str, float]] = {}

        self._memory = ContextMemory(decay_tau=decay_tau)

        self._above_since: Dict[str, float] = {}
        self._trace_emitted: Dict[str, bool] = {}

    # ============================================================
    # Resolution helpers
    # ============================================================

    def _resolution_chain(self, assembly_id: str) -> list[str]:
        """
        Resolution order (most specific → least):

        1. full assembly_id          (region:pop:idx)
        2. region:population
        3. region
        4. __global__
        """
        parts = assembly_id.split(":")
        chain = [assembly_id]

        if len(parts) >= 2:
            chain.append(f"{parts[0]}:{parts[1]}")
            chain.append(parts[0])
        elif len(parts) == 1:
            chain.append(parts[0])

        chain.append(GLOBAL_CONTEXT_KEY)
        return chain

    # ============================================================
    # Query (READ-ONLY)
    # ============================================================

    def get_gain(
        self,
        assembly_id: str,
        domain: str = "global",
    ) -> float:
        for key in self._resolution_chain(assembly_id):
            domains = self._context.get(key)
            if domains and domain in domains:
                return 1.0 + float(domains[domain])
        return 1.0

    def get_bias(
        self,
        assembly_id: str,
        domain: str = "global",
    ) -> float:
        for key in self._resolution_chain(assembly_id):
            domains = self._context.get(key)
            if domains and domain in domains:
                return float(domains[domain])
        return 0.0

    # ============================================================
    # Injection (WRITE PATH)
    # ============================================================

    def add_gain(
        self,
        key: str,
        delta: float,
        domain: str = "global",
    ) -> None:
        """
        Inject gain for:
        - assembly_id
        - region:population
        - region
        - __global__
        """
        if not ContextPolicy.allow_update(key, domain, delta):
            return

        domains = self._context.setdefault(key, {})
        current = domains.get(domain, 0.0)
        new_value = ContextPolicy.clamp_gain(current + delta, domain)
        domains[domain] = new_value

        now = time.time()

        if new_value >= ContextPolicy.TRACE_GAIN_THRESHOLD:
            if key not in self._above_since:
                self._above_since[key] = now
        else:
            self._above_since.pop(key, None)
            self._trace_emitted.pop(key, None)

    def add_global_gain(self, delta: float, domain: str = "global") -> None:
        self.add_gain(GLOBAL_CONTEXT_KEY, delta, domain)

    def set(
        self,
        key: str,
        value: float,
        domain: str = "global",
    ) -> None:
        """
        Deterministic overwrite (testing only).
        """
        self._context.setdefault(key, {})[domain] = float(value)

    # ============================================================
    # Dynamics
    # ============================================================

    def step(self, dt: float) -> None:
        now = time.time()

        # --- Trace eligibility ---
        for key, start_t in list(self._above_since.items()):
            if self._trace_emitted.get(key):
                continue

            domains = self._context.get(key)
            if not domains:
                continue

            gain = domains.get("global", 0.0)
            duration = now - start_t

            if ContextPolicy.should_create_trace(
                gain=gain,
                duration=duration,
                domain="global",
            ):
                trace = ContextTrace(
                    trace_id=str(uuid.uuid4()),
                    context={"key": key},
                    strength=gain,
                )
                self._memory.add(trace)
                self._trace_emitted[key] = True

        # --- Ephemeral decay ---
        tau = max(self.decay_tau, 1e-9)
        decay = float(dt) / tau

        dead_keys = []

        for key, domains in list(self._context.items()):
            dead_domains = []

            for domain, value in list(domains.items()):
                new_value = value * (1.0 - decay)
                if abs(new_value) < self.epsilon:
                    dead_domains.append(domain)
                else:
                    domains[domain] = new_value

            for d in dead_domains:
                del domains[d]

            if not domains:
                dead_keys.append(key)

        for key in dead_keys:
            del self._context[key]

        self._memory.step(dt)

    # ============================================================
    # Maintenance
    # ============================================================

    def clear(self) -> None:
        self._context.clear()
        self._above_since.clear()
        self._trace_emitted.clear()

    def clear_domain(self, domain: str) -> None:
        dead_keys = []
        for key, domains in self._context.items():
            if domain in domains:
                del domains[domain]
            if not domains:
                dead_keys.append(key)

        for key in dead_keys:
            del self._context[key]

    # ============================================================
    # Observability
    # ============================================================

    def dump(self) -> Dict[str, Dict[str, float]]:
        return {k: dict(v) for k, v in self._context.items()}

    def stats(self) -> Dict[str, float]:
        return {
            "gain_count": len(self._context),
            "max_gain": max(
                (max(domains.values()) for domains in self._context.values()),
                default=0.0,
            ),
            "memory": self._memory.stats(),
        }

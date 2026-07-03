"""Runtime ARC I V3.3 message bus scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestration.runtime.v31_learning_opportunity import stable_v31_id


@dataclass(frozen=True)
class KernelEvent:
    event_id: str
    event_type: str
    source: str
    target: str
    payload: dict[str, object]
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class RuntimeMessageBus:
    """In-memory deterministic event dispatcher for kernel review paths."""

    def __init__(self) -> None:
        self._events: list[KernelEvent] = []

    def publish(self, event_type: str, source: str, target: str, payload: dict[str, object]) -> KernelEvent:
        event = KernelEvent(
            event_id=stable_v31_id("kernel-event", event_type, source, target, payload),
            event_type=event_type,
            source=source,
            target=target,
            payload=dict(payload),
            mutating=False,
        )
        self._events.append(event)
        return event

    def dispatch_log(self) -> tuple[KernelEvent, ...]:
        return tuple(self._events)


def build_sample_event_flow() -> dict[str, object]:
    bus = RuntimeMessageBus()
    bus.publish("experience.observed", "Kernel", "ExperienceManager", {"input": "What is DELTA?"})
    bus.publish("learning.opportunity.detected", "ExperienceManager", "LearningManager", {"eligible_for_learning": False})
    bus.publish("review.requested", "LearningManager", "ReviewManager", {"requires_review": True})
    return {
        "phase": "Runtime V3.3",
        "events": [event.as_dict() for event in bus.dispatch_log()],
        "mutations_performed": False,
    }

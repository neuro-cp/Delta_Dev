"""Runtime V2.9 natural alias router for current-state self-description."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import (
    build_current_state_inventory,
    safety_invariants,
)


REPORT_MD = Path("reports/runtime_v29b_natural_alias_router.md")
REPORT_JSON = Path("reports/runtime_v29b_natural_alias_router.json")


@dataclass(frozen=True)
class AliasRoute:
    matched: bool
    topic_id: str
    matched_alias: str
    answer_text: str
    provenance: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "matched": self.matched,
            "topic_id": self.topic_id,
            "matched_alias": self.matched_alias,
            "answer_text": self.answer_text,
            "provenance": list(self.provenance),
        }


def route_v29_alias(question: str, inventory: dict[str, object] | None = None) -> AliasRoute:
    inventory = inventory or build_current_state_inventory()
    normalized = _normalize(question)
    for topic_id, aliases in _alias_map().items():
        for alias in aliases:
            if _normalize(alias) in normalized:
                return AliasRoute(
                    matched=True,
                    topic_id=topic_id,
                    matched_alias=alias,
                    answer_text=_answer_for(topic_id, inventory),
                    provenance=tuple(inventory["provenance"]),
                )
    return AliasRoute(
        matched=False,
        topic_id="unsupported",
        matched_alias="",
        answer_text=(
            "I do not have sufficient governed local evidence to answer that directly. "
            "I can answer current repo-local questions about DELTA's architecture, capabilities, phase, safety, "
            "memory, recall, providers, HYB1, Model B, and scaffold status."
        ),
        provenance=tuple(inventory["provenance"]),
    )


def build_alias_router_report() -> dict[str, object]:
    samples = [
        "What is DELTA?",
        "What can you do?",
        "Describe your architecture.",
        "What phase are you in?",
        "Can you train?",
        "Is HYB1 active?",
    ]
    routes = [route_v29_alias(sample).as_dict() for sample in samples]
    return {
        "phase": "Runtime V2.9B",
        "mode": "natural_alias_router_deterministic_local",
        "sample_routes": routes,
        "all_samples_matched": all(route["matched"] for route in routes),
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_DELTA_ANSWER_V29_INTEGRATION",
    }


def validate_alias_router_safe(data: dict[str, object]) -> bool:
    return data["all_samples_matched"] is True and all(value is False for value in data["safety_invariants"].values())


def write_alias_router_report() -> dict[str, object]:
    data = build_alias_router_report()
    if not validate_alias_router_safe(data):
        raise RuntimeError("Unsafe V2.9 alias router state")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("# Runtime V2.9B Natural Alias Router\n\nAll sample aliases matched safely.\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _alias_map() -> dict[str, tuple[str, ...]]:
    return {
        "identity": ("what is delta", "explain delta", "explain yourself", "describe yourself", "what are you", "what is this system"),
        "capabilities_active": ("what can you do", "what capabilities do you have", "what are your active capabilities", "what is currently enabled", "active capabilities"),
        "capabilities_disabled": ("what is currently disabled", "what can you not do yet", "disabled capabilities", "still disabled", "can you not do"),
        "architecture": ("describe your architecture", "runtime architecture", "memory architecture", "what is your architecture"),
        "replay_consolidation": ("replay path", "consolidation path", "replay and consolidation", "approval path", "what is your pipeline", "pipeline"),
        "phase_state": ("what phase are you in", "runtime version", "current checkpoint", "latest validated phase"),
        "training_status": ("are you allowed to train", "can you train", "training status", "fine tune", "model weights"),
        "memory_status": ("can you write memory", "memory status", "canonical memory", "write memory"),
        "provider_status": ("can you call providers", "provider calls", "provider authority"),
        "action_status": ("can you execute actions", "execute actions", "action execution"),
        "hyb1_status": ("is hyb1 active", "what is hyb1", "hyb1"),
        "model_b_status": ("is model b still default", "what is model b", "model b"),
    }


def _answer_for(topic_id: str, inventory: dict[str, object]) -> str:
    if topic_id == "identity":
        return (
            "DELTA is a governed cognitive-runtime substrate in this repo. In the current local path it can describe "
            "its scaffold, safety boundaries, reports, and deterministic validation state without provider calls or memory mutation."
        )
    if topic_id == "capabilities_active":
        return "Currently active local capabilities: " + "; ".join(inventory["active_local_capabilities"]) + "."
    if topic_id == "capabilities_disabled":
        return "Currently disabled: " + "; ".join(inventory["disabled_capabilities"]) + "."
    if topic_id == "architecture":
        return (
            "DELTA's architecture is organized around governed local interaction, candidate-context recall, evidence/advisory provider boundaries, "
            "approval gates, replay/consolidation scaffolds, canonical-memory design scaffolds, and validation reports. Interfaces are clients of the substrate, not hidden authority."
        )
    if topic_id == "replay_consolidation":
        return (
            "The current replay/consolidation path is: manual/raw message -> experience boundary/record -> episodic feedback capture -> replay markers/batches -> replay review -> consolidation candidate -> consolidation decision -> sleep-cycle plan -> canonical memory draft/record design. Canonical writes remain disabled."
        )
    if topic_id == "phase_state":
        return "The current validated runtime state is V2.8 with V2.9 local self-description integration complete."
    if topic_id == "training_status":
        return "No. Training, fine-tuning, model weight updates, dataset export authority, and model artifact creation remain disabled."
    if topic_id == "memory_status":
        return "Memory writes and canonical writes remain disabled. Recall is candidate-context only and does not mutate runtime recall or canonical memory."
    if topic_id == "provider_status":
        return "Provider calls and provider authority are disabled in this local path. Provider/evaluator/specialist outputs remain advisory or evidence-only unless a future explicit gate changes that."
    if topic_id == "action_status":
        return "Action execution is disabled. Existing action ledger and dry-run execution work is scaffold/report-only."
    if topic_id == "hyb1_status":
        return f"HYB1 is {inventory['hyb1_status']}; it is not promoted and is not the default."
    if topic_id == "model_b_status":
        return "Model B remains the accepted default runtime baseline."
    return route_v29_alias("").answer_text


def _normalize(text: str) -> str:
    return " ".join(str(text).lower().replace("?", " ").replace(".", " ").replace("'", " ").replace("-", " ").split())


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


if __name__ == "__main__":
    print(write_alias_router_report()["final_recommendation"])

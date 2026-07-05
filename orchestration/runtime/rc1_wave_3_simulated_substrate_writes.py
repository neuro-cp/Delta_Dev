"""RC1 Wave 3 approval-gated simulated substrate writes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import ingest_fixture_corpus


REPORT_JSON = Path("reports/runtime_rc1_wave_3_simulated_substrate_writes.json")
REPORT_MD = Path("reports/runtime_rc1_wave_3_simulated_substrate_writes.md")


@dataclass(frozen=True)
class AdminApprovalEvent:
    candidate_id: str
    approved_by: str
    approval_scope: str

    @property
    def valid(self) -> bool:
        return self.approved_by == "user" and self.approval_scope == "single_memory_candidate_only"


@dataclass(frozen=True)
class OverwatchReview:
    result: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.result == "allow"


@dataclass(frozen=True)
class SimulatedSubstrateDelta:
    delta_id: str
    candidate_id: str
    claim: str
    simulated_write: bool
    write_performed: bool
    rollback_token: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def build_candidate() -> dict[str, str]:
    record = ingest_fixture_corpus()["semantic_records"][0]
    return {"candidate_id": "rc1-wave3-candidate-" + _digest(record["record_id"]), "claim": str(record["claim"])}


def simulate_substrate_write(
    approval: AdminApprovalEvent | None,
    overwatch: OverwatchReview | None,
    *,
    owner_override: bool = False,
) -> dict[str, Any]:
    candidate = build_candidate()
    approved = approval is not None and approval.valid and approval.candidate_id == candidate["candidate_id"]
    allowed = overwatch is not None and overwatch.allowed
    can_simulate = approved and (allowed or owner_override)
    delta = None
    if can_simulate:
        delta = SimulatedSubstrateDelta(
            delta_id="simulated-delta-" + _digest(candidate["candidate_id"], candidate["claim"]),
            candidate_id=candidate["candidate_id"],
            claim=candidate["claim"],
            simulated_write=True,
            write_performed=False,
            rollback_token="rollback-token-" + _digest(candidate["candidate_id"]),
        )
    return {
        "phase": "RC1 Wave 3 Simulated Substrate Writes",
        "candidate": candidate,
        "approval_valid": approved,
        "overwatch_allowed": allowed,
        "owner_override": owner_override,
        "simulated_delta": delta.as_dict() if delta else None,
        "audit_chain_complete": bool(delta),
        "write_performed": False,
        "simulated_write": bool(delta),
        "safety": {
            "canonical_write_performed": False,
            "knowledge_mutation_performed": False,
            "memory_mutation_performed": False,
            "provider_call_performed": False,
        },
        "final_recommendation": "PROCEED_WAVE_4_ROLLBACK_EVALUATION",
    }


def write_wave_3_report() -> dict[str, Any]:
    candidate = build_candidate()
    payload = simulate_substrate_write(
        AdminApprovalEvent(candidate["candidate_id"], "user", "single_memory_candidate_only"),
        OverwatchReview("allow", "fixture candidate is safe for simulated delta"),
    )
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# RC1 Wave 3 Simulated Substrate Writes\n\n"
        f"- simulated_write: {payload['simulated_write']}\n"
        f"- write_performed: {payload['write_performed']}\n"
        f"- rollback_token: {payload['simulated_delta']['rollback_token']}\n"
        f"- final_recommendation: `{payload['final_recommendation']}`\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(write_wave_3_report()["final_recommendation"])

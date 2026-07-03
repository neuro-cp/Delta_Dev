from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V16H_REVIEW_EXPORT_FLAGS: dict[str, bool] = {
    "review_ui_export_enabled": True,
    "memory_write_performed": False,
    "canonical_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class ReviewUIExportKind(str, Enum):
    APPROVAL = "approval"
    REJECTION = "rejection"
    DEFER = "defer"


@dataclass(frozen=True)
class ReviewUIExportRequest:
    request_id: str
    candidate_id: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ReviewUIExportSafetyStatus:
    safety_status_id: str
    mutating: bool = False
    provider_call_performed: bool = False
    memory_write_performed: bool = False
    recall_mutated: bool = False
    training_triggered: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ReviewUIExport:
    export_id: str
    kind: ReviewUIExportKind
    candidate_id: str
    export_text: str
    executed: bool = False
    mutating: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["kind"] = self.kind.value
        return data


def build_review_ui_exports(candidate_id: str) -> dict[str, object]:
    request = ReviewUIExportRequest(_stable_id("v16h-export-request", candidate_id), candidate_id)
    exports = (
        ReviewUIExport(_stable_id("v16h-export", candidate_id, "approval"), ReviewUIExportKind.APPROVAL, candidate_id, approval_export_text(candidate_id)),
        ReviewUIExport(_stable_id("v16h-export", candidate_id, "rejection"), ReviewUIExportKind.REJECTION, candidate_id, rejection_export_text(candidate_id)),
        ReviewUIExport(_stable_id("v16h-export", candidate_id, "defer"), ReviewUIExportKind.DEFER, candidate_id, defer_export_text(candidate_id)),
    )
    safety = ReviewUIExportSafetyStatus(_stable_id("v16h-export-safety", candidate_id))
    return {
        "phase": "Runtime V1.6H",
        "request": request.as_dict(),
        "exports": [item.as_dict() for item in exports],
        "safety_status": safety.as_dict(),
        "invariant_flags": dict(RUNTIME_V16H_REVIEW_EXPORT_FLAGS),
        "final_recommendation": "PROCEED_MEMORY_CANDIDATE_EDIT_REJECT_DEFER_LOOP",
    }


def approval_export_text(candidate_id: str) -> str:
    return "\n".join(("APPROVE_CANONICAL_MEMORY_WRITE", f"candidate_id={candidate_id}", "approved_by=user", "approval_scope=single_memory_candidate_only"))


def rejection_export_text(candidate_id: str) -> str:
    return "\n".join(("REJECT_MEMORY_CANDIDATE", f"candidate_id={candidate_id}", "rejected_by=user", "rejection_scope=single_memory_candidate_only"))


def defer_export_text(candidate_id: str) -> str:
    return "\n".join(("DEFER_MEMORY_CANDIDATE", f"candidate_id={candidate_id}", "deferred_by=user", "defer_scope=single_memory_candidate_only"))


def validate_review_ui_export_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["safety_status"]["mutating"] is False
        and all(item["executed"] is False and item["mutating"] is False for item in payload["exports"])
        and flags["review_ui_export_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "review_ui_export_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

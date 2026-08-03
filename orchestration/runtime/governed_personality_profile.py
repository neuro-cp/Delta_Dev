"""Versioned operator-governed presentation and relationship continuity.

This is intentionally not a semantic-memory, attention, or self-model owner.
It stores only operator-approved presentation conventions and applies them
after a response is already semantically complete.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


SCHEMA_VERSION = "governed_personality_profile_v1"
FILENAME = "governed_personality_profile.json"
TRAIT_RANGES = {
    "directness": range(0, 4), "explanation_depth": range(0, 4), "formality": range(0, 4),
    "humor_level": range(0, 3), "curiosity_expression_frequency": range(0, 4),
    "willingness_to_ask": range(0, 4), "initiative_level": range(0, 4),
    "interruption_tolerance": range(0, 4), "association_surfacing_frequency": range(0, 4),
    "correction_candor": range(0, 4), "background_work_visibility": range(0, 4),
}
ENUM_TRAITS = {"uncertainty_expression_style": {"plain", "cautious", "compact"}}


@dataclass(frozen=True)
class PersonalityProfileVersion:
    profile_version_id: str
    profile_id: str
    lifecycle_state: str
    traits: Mapping[str, Any]
    source: str
    operator_approval_ref: str
    rationale: str
    created_at: str
    modified_at: str
    supersedes_version_id: str = ""
    rollback_of_version_id: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class RelationshipConvention:
    convention_id: str
    key: str
    value: str
    source: str
    operator_approval_ref: str
    lifecycle_state: str
    created_at: str
    supersedes_convention_id: str = ""
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class PersonalityProfileState:
    profile_id: str
    active_profile_version_id: str = ""
    versions: tuple[PersonalityProfileVersion, ...] = ()
    relationship_conventions: tuple[RelationshipConvention, ...] = ()
    schema_version: str = SCHEMA_VERSION


def state_path(runtime_root: str | Path) -> Path:
    return Path(runtime_root) / "relationship-continuity" / FILENAME


def empty_state(runtime_root: str | Path) -> PersonalityProfileState:
    return PersonalityProfileState(profile_id=stable_id("governed-personality-profile", str(Path(runtime_root))))


def load_state(runtime_root: str | Path) -> PersonalityProfileState:
    path = state_path(runtime_root)
    if not path.exists():
        return empty_state(runtime_root)
    data = json.loads(path.read_text(encoding="utf-8"))
    return PersonalityProfileState(
        profile_id=str(data.get("profile_id") or stable_id("governed-personality-profile", str(Path(runtime_root)))),
        active_profile_version_id=str(data.get("active_profile_version_id") or ""),
        versions=tuple(PersonalityProfileVersion(**{key: item.get(key, "") for key in PersonalityProfileVersion.__dataclass_fields__}) for item in data.get("versions", ()) if isinstance(item, Mapping)),
        relationship_conventions=tuple(RelationshipConvention(**{key: item.get(key, "") for key in RelationshipConvention.__dataclass_fields__}) for item in data.get("relationship_conventions", ()) if isinstance(item, Mapping)),
    )


def save_state(runtime_root: str | Path, state: PersonalityProfileState) -> None:
    path = state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def propose_profile(state: PersonalityProfileState, *, traits: Mapping[str, Any], proposer_role: str, rationale: str) -> PersonalityProfileState:
    _validate_traits(traits)
    now = utc_now()
    version = PersonalityProfileVersion(
        profile_version_id=stable_id("personality-profile-version", state.profile_id, _digest(dict(traits)), now), profile_id=state.profile_id,
        lifecycle_state="proposed", traits=dict(traits), source=f"{proposer_role}_proposal", operator_approval_ref="", rationale=rationale,
        created_at=now, modified_at=now,
    )
    return replace(state, versions=state.versions + (version,))


def approve_and_activate(state: PersonalityProfileState, *, profile_version_id: str, operator_id: str, approval_ref: str) -> PersonalityProfileState:
    if not operator_id or not approval_ref:
        raise PermissionError("personality_profile_requires_explicit_operator_approval")
    version = next((item for item in state.versions if item.profile_version_id == profile_version_id), None)
    if version is None or version.lifecycle_state not in {"proposed", "approved", "active", "superseded"}:
        raise ValueError("personality_profile_not_approvable")
    prior = state.active_profile_version_id
    updated = replace(version, lifecycle_state="active", source="operator_approved", operator_approval_ref=approval_ref, modified_at=utc_now(), supersedes_version_id=prior)
    versions = tuple(updated if item.profile_version_id == profile_version_id else (replace(item, lifecycle_state="superseded", modified_at=utc_now()) if item.profile_version_id == prior else item) for item in state.versions)
    return replace(state, active_profile_version_id=profile_version_id, versions=versions)


def rollback_profile(state: PersonalityProfileState, *, target_profile_version_id: str, operator_id: str, approval_ref: str) -> PersonalityProfileState:
    target = next((item for item in state.versions if item.profile_version_id == target_profile_version_id), None)
    if target is None:
        raise ValueError("personality_profile_rollback_target_missing")
    restored = approve_and_activate(state, profile_version_id=target_profile_version_id, operator_id=operator_id, approval_ref=approval_ref)
    versions = tuple(replace(item, rollback_of_version_id=state.active_profile_version_id) if item.profile_version_id == target_profile_version_id else item for item in restored.versions)
    return replace(restored, versions=versions)


def record_relationship_convention(state: PersonalityProfileState, *, key: str, value: str, operator_id: str, approval_ref: str) -> PersonalityProfileState:
    if not operator_id or not approval_ref or not key or not value:
        raise PermissionError("relationship_convention_requires_explicit_operator_approval")
    prior = next((item for item in reversed(state.relationship_conventions) if item.key == key and item.lifecycle_state == "active"), None)
    convention = RelationshipConvention(
        convention_id=stable_id("relationship-convention", state.profile_id, key, value, approval_ref), key=key, value=value,
        source="operator_approved", operator_approval_ref=approval_ref, lifecycle_state="active", created_at=utc_now(),
        supersedes_convention_id=prior.convention_id if prior else "",
    )
    conventions = tuple(replace(item, lifecycle_state="superseded") if prior and item.convention_id == prior.convention_id else item for item in state.relationship_conventions)
    return replace(state, relationship_conventions=conventions + (convention,))


def active_profile(state: PersonalityProfileState) -> PersonalityProfileVersion | None:
    return next((item for item in state.versions if item.profile_version_id == state.active_profile_version_id and item.lifecycle_state == "active"), None)


def presentation_context(state: PersonalityProfileState) -> Mapping[str, Any]:
    profile = active_profile(state)
    return dict(profile.traits) if profile else {}


def self_model_projection(state: PersonalityProfileState) -> Mapping[str, Any]:
    """Read-only projection for a self-model or runtime status surface."""
    profile = active_profile(state)
    return {
        "active_personality_profile_version": profile.profile_version_id if profile else "",
        "active_personality_traits": dict(profile.traits) if profile else {},
        "relationship_conventions": {
            item.key: item.value for item in state.relationship_conventions if item.lifecycle_state == "active"
        },
        "authority_boundary": "presentation_only_operator_approved",
    }


def shape_presentation(text: str, state: PersonalityProfileState) -> str:
    """Presentation-only transform.  It never deletes or changes proposition text."""
    profile = active_profile(state)
    if profile is None or not text:
        return text
    traits = profile.traits
    if int(traits.get("formality", 1)) >= 2:
        return "Response:\n" + text
    if int(traits.get("directness", 1)) >= 2:
        return "Direct answer:\n" + text
    return text


def _validate_traits(traits: Mapping[str, Any]) -> None:
    unknown = set(traits) - set(TRAIT_RANGES) - set(ENUM_TRAITS)
    if unknown:
        raise ValueError("unknown_personality_traits:" + ",".join(sorted(unknown)))
    for key, allowed in TRAIT_RANGES.items():
        if key in traits and (not isinstance(traits[key], int) or traits[key] not in allowed):
            raise ValueError("personality_trait_out_of_range:" + key)
    for key, allowed in ENUM_TRAITS.items():
        if key in traits and traits[key] not in allowed:
            raise ValueError("personality_trait_invalid_value:" + key)


def _digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


__all__ = ["PersonalityProfileState", "PersonalityProfileVersion", "RelationshipConvention", "active_profile", "approve_and_activate", "empty_state", "load_state", "presentation_context", "propose_profile", "record_relationship_convention", "rollback_profile", "save_state", "shape_presentation", "self_model_projection"]

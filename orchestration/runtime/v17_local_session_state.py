from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v15_first_interaction import build_first_interaction_result


SESSION_DIR = Path("data/runtime_v17b/session_state")

RUNTIME_V17B_SESSION_FLAGS: dict[str, bool] = {
    "local_session_state_enabled": True,
    "ephemeral_non_canonical": True,
    "canonical_write_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class LocalSessionTurn:
    turn_id: str
    user_message: str
    response_text: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LocalSession:
    session_id: str
    turns: tuple[LocalSessionTurn, ...]
    non_canonical: bool = True
    ephemeral: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"session_id": self.session_id, "turns": [turn.as_dict() for turn in self.turns], "non_canonical": self.non_canonical, "ephemeral": self.ephemeral}


def create_or_load_session(session_id: str, session_dir: str | Path = SESSION_DIR) -> LocalSession:
    path = _session_path(session_id, session_dir)
    if not path.exists():
        return LocalSession(session_id=session_id, turns=())
    data = json.loads(path.read_text(encoding="utf-8"))
    turns = tuple(LocalSessionTurn(**turn) for turn in data.get("turns", ()))
    return LocalSession(session_id=session_id, turns=turns)


def add_local_session_turn(session_id: str, message: str, session_dir: str | Path = SESSION_DIR) -> dict[str, object]:
    session = create_or_load_session(session_id, session_dir)
    result = build_first_interaction_result(message)
    response = str(result["response_preview"]["response_text"])
    turn = LocalSessionTurn(_stable_id("v17b-turn", session_id, len(session.turns), message), message, response)
    updated = LocalSession(session_id=session_id, turns=(*session.turns, turn))
    _save_session(updated, session_dir)
    return {
        "phase": "Runtime V1.7B",
        "session": updated.as_dict(),
        "context_window": {"turn_count": len(updated.turns), "summary": " | ".join(t.user_message for t in updated.turns[-3:])},
        "safety_status": {"non_canonical": True, "canonical_write_performed": False, "recall_mutated": False, "provider_call_performed": False},
        "invariant_flags": dict(RUNTIME_V17B_SESSION_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_PROVIDER_ASSISTED_UNKNOWN_ANSWER_PATH",
    }


def clear_local_session(session_id: str, session_dir: str | Path = SESSION_DIR) -> bool:
    path = _session_path(session_id, session_dir)
    if path.exists():
        path.unlink()
        return True
    return False


def validate_local_session_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["session"]["non_canonical"] is True
        and payload["session"]["ephemeral"] is True
        and payload["safety_status"]["canonical_write_performed"] is False
        and payload["safety_status"]["recall_mutated"] is False
        and payload["safety_status"]["provider_call_performed"] is False
        and flags["local_session_state_enabled"] is True
        and flags["ephemeral_non_canonical"] is True
        and all(value is False for key, value in flags.items() if key not in {"local_session_state_enabled", "ephemeral_non_canonical"})
    )


def _save_session(session: LocalSession, session_dir: str | Path) -> None:
    path = _session_path(session.session_id, session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.as_dict(), indent=2), encoding="utf-8")


def _session_path(session_id: str, session_dir: str | Path) -> Path:
    safe_id = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_") or "default"
    return Path(session_dir) / f"{safe_id}.json"


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

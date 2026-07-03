from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


LOCALHOST_HOST = "127.0.0.1"
STATIC_SNAPSHOT_PATH = Path("ui/delta_full_review_console_static.html")

ROUTES = (
    "/",
    "/status",
    "/ask",
    "/recall",
    "/synthesis",
    "/candidates",
    "/memory",
    "/evidence",
    "/evaluator",
    "/scheduler",
    "/hyb1",
    "/safety",
    "/exports",
)

RUNTIME_V24A_FLAGS = {
    "localhost_full_review_console_enabled": True,
    "localhost_only": True,
    "server_started_by_import_or_test": False,
    "external_bind_allowed": False,
    "hidden_write_allowed": False,
    "memory_write_performed": False,
    "provider_call_performed": False,
    "scheduler_started": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class FullConsoleSnapshot:
    snapshot_id: str
    host: str
    routes: tuple[str, ...]
    html: str
    static_snapshot_path: str

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "host": self.host,
            "routes": list(self.routes),
            "html": self.html,
            "static_snapshot_path": self.static_snapshot_path,
        }


def build_full_console_snapshot(*, host: str = LOCALHOST_HOST) -> dict[str, object]:
    external_bind_rejected = host != LOCALHOST_HOST
    html = _render_html()
    return {
        "phase": "Runtime V2.4A",
        "snapshot": FullConsoleSnapshot(_stable_id("v24a-snapshot", host, ROUTES), host, ROUTES, html, str(STATIC_SNAPSHOT_PATH)).as_dict(),
        "bind_policy": {
            "host": host,
            "localhost_only": True,
            "external_bind_rejected": external_bind_rejected,
        },
        "sections": [
            "status",
            "ask",
            "recall",
            "synthesis",
            "candidates",
            "memory",
            "evidence",
            "evaluator",
            "scheduler",
            "hyb1",
            "safety",
            "exports",
        ],
        "decision": {
            "page_rendered": True,
            "server_started": False,
            "memory_write_performed": False,
            "provider_call_performed": False,
            "scheduler_started": False,
            "recall_mutated": False,
            "api_key_rendered": False,
        },
        "invariant_flags": dict(RUNTIME_V24A_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_MEMORY_WRITE_UX_TRIAL",
    }


def write_static_full_console_snapshot(path: str | Path = STATIC_SNAPSHOT_PATH) -> dict[str, object]:
    payload = build_full_console_snapshot()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload["snapshot"]["html"], encoding="utf-8")
    payload["decision"]["static_snapshot_written"] = True
    payload["snapshot"]["static_snapshot_path"] = str(target)
    return payload


def validate_full_console_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["bind_policy"]["localhost_only"] is True
        and payload["decision"]["server_started"] is False
        and payload["decision"]["api_key_rendered"] is False
        and flags["localhost_full_review_console_enabled"] is True
        and flags["localhost_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"localhost_full_review_console_enabled", "localhost_only"})
    )


def _render_html() -> str:
    sections = "\n".join(f"<section id=\"{route.strip('/') or 'home'}\"><h2>{route}</h2><p>Local review surface only.</p></section>" for route in ROUTES)
    return "\n".join((
        "<!doctype html>",
        "<html>",
        "<head><meta charset=\"utf-8\"><title>DELTA Full Review Console</title></head>",
        "<body>",
        "<h1>DELTA Full Review Console</h1>",
        "<p>Localhost-only static snapshot. No hidden writes, provider calls, schedulers, training, action execution, or HYB1 activation.</p>",
        sections,
        "</body>",
        "</html>",
        "",
    ))


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


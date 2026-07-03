from __future__ import annotations

import html
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from orchestration.runtime.v20_controlled_general_memory_trial import list_controlled_general_memory_records
from orchestration.runtime.v20_controlled_general_recall_trial import run_controlled_general_recall
from orchestration.runtime.v20_review_ui_write_approval_bridge import build_review_ui_exports


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STATIC_PATH = Path("ui/delta_localhost_review_ui_static.html")

RUNTIME_V21A_FLAGS: dict[str, bool] = {
    "localhost_review_ui_enabled": True,
    "localhost_only": True,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class LocalhostReviewUIConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    external_binding_allowed: bool = False
    live_provider_calls_allowed: bool = False
    scheduler_calls_allowed: bool = False
    hidden_memory_writes_allowed: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_localhost_review_state(query: str = "HYB1", candidate_id: str = "memory-candidate-demo") -> dict[str, object]:
    exports = build_review_ui_exports(candidate_id)
    recall = run_controlled_general_recall(query, max_candidates=5)
    return {
        "model_b_status": "default_unchanged",
        "hyb1_status": "dormant_env_gated",
        "active_capabilities": ["localhost review rendering", "structured export display", "candidate-context recall inspection"],
        "disabled_capabilities": ["training", "action execution", "scheduler", "autonomous memory writes", "authoritative recall", "HYB1 default activation"],
        "memory_candidates": [{"candidate_id": candidate_id, "review_required": True, "canonical_write_ready": False}],
        "controlled_memory_records": list_controlled_general_memory_records(),
        "recall_candidates": recall["candidates"],
        "provider_evidence_labels": ["evidence_only", "advisory_only", "not_authority"],
        "evidence_quality": {"available": True, "source": "local reports", "provider_call_performed": False},
        "promotion_readiness_blockers": ["manual review required", "explicit backend approval required"],
        "exports": exports,
        "safety_invariants": dict(RUNTIME_V21A_FLAGS),
        "key_redaction": {"key_present": False, "key_redacted": True, "secret_rendered": False},
        "scheduler_status": "not_active",
    }


def render_localhost_review_page(path: str = "/", *, query: str = "HYB1", candidate_id: str = "memory-candidate-demo") -> str:
    state = build_localhost_review_state(query, candidate_id)
    route = urlparse(path).path
    if route == "/status":
        body = _section("Status", _pre({"model_b": state["model_b_status"], "hyb1": state["hyb1_status"], "scheduler": state["scheduler_status"]}))
    elif route == "/candidates":
        body = _section("Memory Candidates", _pre(state["memory_candidates"]))
    elif route == "/memory-records":
        body = _section("Controlled Memory Records", _pre(state["controlled_memory_records"]))
    elif route == "/recall":
        body = _section("Recall Candidates", _pre(state["recall_candidates"]))
    elif route == "/exports":
        body = _section("Structured Exports", "".join(f"<h3>{html.escape(key)}</h3><pre>{html.escape(str(value))}</pre>" for key, value in state["exports"].items() if key != "candidate_id"))
    elif route == "/safety":
        body = _section("Safety", _pre(state["safety_invariants"]))
    else:
        body = "".join(
            (
                _section("Runtime", _pre({"model_b": state["model_b_status"], "hyb1": state["hyb1_status"]})),
                _section("Active Capabilities", _pre(state["active_capabilities"])),
                _section("Disabled Capabilities", _pre(state["disabled_capabilities"])),
                _section("Evidence Labels", _pre(state["provider_evidence_labels"])),
                _section("Approval Export", f"<pre>{html.escape(str(state['exports']['approve']))}</pre>"),
                _section("Key Redaction", _pre(state["key_redaction"])),
            )
        )
    return f"<!doctype html><html><head><meta charset='utf-8'><title>DELTA Local Review</title></head><body><h1>DELTA Localhost Review UI</h1>{body}</body></html>"


def render_static_localhost_review_ui(path: str | Path = STATIC_PATH) -> dict[str, object]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_localhost_review_page("/"), encoding="utf-8")
    return {
        "phase": "Runtime V2.1A",
        "static_path": str(target),
        "config": LocalhostReviewUIConfig().as_dict(),
        "invariant_flags": dict(RUNTIME_V21A_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_EXPANSION",
    }


def make_review_ui_handler() -> type[BaseHTTPRequestHandler]:
    class DeltaReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            query = params.get("q", ["HYB1"])[0]
            candidate_id = params.get("candidate_id", ["memory-candidate-demo"])[0]
            payload = render_localhost_review_page(parsed.path, query=query, candidate_id=candidate_id).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return DeltaReviewHandler


def create_localhost_review_server(config: LocalhostReviewUIConfig | None = None) -> ThreadingHTTPServer:
    cfg = config or LocalhostReviewUIConfig()
    if cfg.host != DEFAULT_HOST:
        raise ValueError("DELTA localhost review UI may bind only to 127.0.0.1")
    return ThreadingHTTPServer((cfg.host, cfg.port), make_review_ui_handler())


def validate_localhost_review_ui_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    config = payload["config"]
    return (
        config["host"] == DEFAULT_HOST
        and config["external_binding_allowed"] is False
        and config["hidden_memory_writes_allowed"] is False
        and flags["localhost_review_ui_enabled"] is True
        and flags["localhost_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"localhost_review_ui_enabled", "localhost_only"})
    )


def _section(title: str, body: str) -> str:
    return f"<section><h2>{html.escape(title)}</h2>{body}</section>"


def _pre(value: object) -> str:
    return f"<pre>{html.escape(json.dumps(value, indent=2, sort_keys=True))}</pre>"

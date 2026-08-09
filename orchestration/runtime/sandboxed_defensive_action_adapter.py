"""Bounded local actions for sealed defensive-security mission fixtures.

This is intentionally not a general shell or filesystem interface.  It is the
single owner for DELTA-originated actions inside one authorized fixture root.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


ALLOWED_ACTION_TYPES = {
    "read_file",
    "write_file",
    "run_command",
    "http_request",
    "read_log",
    "start_service",
    "stop_service",
}
PROTECTED_MARKERS = ("DELTA-75", "live_competence_adapter.py", "reports/RC2_", ".git", ".delta_mission")


def _stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:16]}"


def _summary(value: object, limit: int = 4000) -> str:
    text = str(value or "").replace("\x00", "")
    return text[:limit]


@dataclass(frozen=True)
class SandboxMissionAuthorization:
    mission_id: str
    fixture_root: str
    service_port: int
    allowed_command_kinds: tuple[str, ...] = ("pytest", "py_compile")
    maximum_actions: int = 24
    network_allowed: bool = False
    external_action_allowed: bool = False
    status: str = "active_local_sandbox_only"

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxActionRequest:
    request_id: str
    mission_id: str
    action_type: str
    target: str
    normalized_target: str
    requested_by: str
    allowed_scope: str
    timestamp: float

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxActionDecision:
    decision_id: str
    request_id: str
    allowed: bool
    reason: str
    violated_boundary: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxActionReceipt:
    receipt_id: str
    request_id: str
    decision_id: str
    status: str
    exit_code: int | None
    status_code: int | None
    stdout_summary: str
    stderr_summary: str
    response_summary: str
    files_changed: tuple[str, ...]
    timestamp: float
    replay_key: str
    replayed: bool = False

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["files_changed"] = list(self.files_changed)
        return record


@dataclass(frozen=True)
class SandboxResourceRequest:
    """A DELTA-originated request for a configured local mission resource."""

    request_id: str
    mission_id: str
    requester: str
    resource_type: str
    purpose: str
    allowed_scope: str
    prompt_summary: str
    status: str
    response_summary: str
    raw_response_digest: str
    used_for_next_action: bool
    timestamp: float

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


class SandboxActionAdapter:
    """Enforce one fixture-root action scope and persist every decision."""

    def __init__(self, authorization: SandboxMissionAuthorization):
        self.authorization = authorization
        self.fixture_root = Path(authorization.fixture_root).resolve()
        self.state_root = self.fixture_root / ".delta_mission"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.state_root / "sandbox_action_ledger.json"
        self._service: subprocess.Popen[str] | None = None
        self._write_state(self._load_state())

    def _load_state(self) -> dict[str, Any]:
        if self.ledger_path.exists():
            try:
                payload = json.loads(self.ledger_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "schema_version": "sandbox_defensive_action_ledger_v1",
            "authorization": self.authorization.as_record(),
            "requests": [],
            "decisions": [],
            "receipts": [],
            "resource_requests": [],
        }

    def _write_state(self, state: Mapping[str, Any]) -> None:
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.ledger_path)

    def records(self) -> dict[str, Any]:
        return self._load_state()

    def request_resource(
        self,
        *,
        resource_type: str,
        purpose: str,
        prompt_summary: str,
        raw_response: str,
        available: bool,
        used_for_next_action: bool = False,
        requester: str = "DELTA",
    ) -> dict[str, Any]:
        """Record a local-only resource escalation without executing a mission action."""

        state = self._load_state()
        digest = hashlib.sha256(str(raw_response or "").encode("utf-8")).hexdigest()
        request_id = _stable_id(
            "sandbox-resource-request",
            self.authorization.mission_id,
            requester,
            resource_type,
            purpose,
            digest,
        )
        existing = next((item for item in state["resource_requests"] if item.get("request_id") == request_id), None)
        if existing is not None:
            return dict(existing)
        status = "available_local_resource" if available else "resource_unavailable"
        record = SandboxResourceRequest(
            request_id=request_id,
            mission_id=self.authorization.mission_id,
            requester=str(requester or ""),
            resource_type=str(resource_type or ""),
            purpose=str(purpose or ""),
            allowed_scope="local_fixture_only_no_external_resource_access",
            prompt_summary=_summary(prompt_summary, limit=1200),
            status=status,
            response_summary="configured local resource selected" if available else "no configured approved resource was available",
            raw_response_digest=digest,
            used_for_next_action=bool(used_for_next_action),
            timestamp=time.time(),
        )
        state["resource_requests"].append(record.as_record())
        self._write_state(state)
        return record.as_record()

    def _fixture_path(self, target: str) -> tuple[Path | None, str]:
        candidate = (self.fixture_root / str(target or "")).resolve()
        try:
            candidate.relative_to(self.fixture_root)
        except ValueError:
            return None, "outside_fixture_root"
        lowered = str(candidate).replace("\\", "/").lower()
        if any(marker.lower() in lowered for marker in PROTECTED_MARKERS):
            return None, "protected_path"
        return candidate, ""

    def _http_target(self, target: str) -> tuple[str, str]:
        parsed = urlparse(str(target or ""))
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return "", "localhost_only"
        if parsed.port != self.authorization.service_port:
            return "", "service_port_mismatch"
        return parsed.geturl(), ""

    def _request(
        self,
        action_type: str,
        target: str,
        payload: Mapping[str, Any],
        requested_by: str,
    ) -> tuple[SandboxActionRequest, str]:
        normalized_target = str(target or "")
        if action_type in {"read_file", "write_file", "read_log", "run_command", "start_service", "stop_service"}:
            path, error = self._fixture_path(target or ".")
            normalized_target = str(path) if path is not None else str(target or "")
            if error:
                normalized_target = f"blocked:{error}:{target}"
        elif action_type == "http_request":
            normalized_target, error = self._http_target(target)
            if error:
                normalized_target = f"blocked:{error}:{target}"
        digest = hashlib.sha256(json.dumps(dict(payload), sort_keys=True, default=str).encode("utf-8")).hexdigest()
        replay_key = _stable_id("sandbox-action-replay", self.authorization.mission_id, action_type, normalized_target, digest)
        request = SandboxActionRequest(
            request_id=_stable_id("sandbox-action-request", replay_key),
            mission_id=self.authorization.mission_id,
            action_type=action_type,
            target=str(target or ""),
            normalized_target=normalized_target,
            requested_by=str(requested_by or ""),
            allowed_scope="authorized_fixture_root_and_assigned_localhost_service_only",
            timestamp=time.time(),
        )
        return request, replay_key

    def dispatch(self, *, action_type: str, target: str = "", payload: Mapping[str, Any] | None = None, requested_by: str = "DELTA") -> dict[str, Any]:
        """Execute a DELTA-originated, bounded action or record its denial."""

        payload = dict(payload or {})
        request, replay_key = self._request(action_type, target, payload, requested_by)
        state = self._load_state()
        prior = next((item for item in state["receipts"] if item.get("replay_key") == replay_key), None)
        if prior is not None:
            return {**dict(prior), "replayed": True}

        allowed, reason, boundary = self._authorize(request, payload, requested_by, state)
        decision = SandboxActionDecision(
            decision_id=_stable_id("sandbox-action-decision", request.request_id, allowed, reason, boundary),
            request_id=request.request_id,
            allowed=allowed,
            reason=reason,
            violated_boundary=boundary,
        )
        state["requests"].append(request.as_record())
        state["decisions"].append(decision.as_record())
        if not allowed:
            receipt = SandboxActionReceipt(
                receipt_id=_stable_id("sandbox-action-receipt", request.request_id, decision.decision_id, "blocked"),
                request_id=request.request_id,
                decision_id=decision.decision_id,
                status="blocked",
                exit_code=None,
                status_code=None,
                stdout_summary="",
                stderr_summary="",
                response_summary="",
                files_changed=(),
                timestamp=time.time(),
                replay_key=replay_key,
            )
        else:
            receipt = self._execute(request, decision, payload, replay_key)
        state["receipts"].append(receipt.as_record())
        self._write_state(state)
        return receipt.as_record()

    def _authorize(self, request: SandboxActionRequest, payload: Mapping[str, Any], requested_by: str, state: Mapping[str, Any]) -> tuple[bool, str, str]:
        if requested_by != "DELTA":
            return False, "only_delta_runtime_may_request_mission_actions", "requester_not_delta"
        if request.action_type not in ALLOWED_ACTION_TYPES:
            return False, "unsupported_sandbox_action", "action_type"
        if len(state["receipts"]) >= self.authorization.maximum_actions:
            return False, "mission_action_budget_exhausted", "maximum_actions"
        if request.normalized_target.startswith("blocked:"):
            return False, "sandbox_boundary_denied", request.normalized_target.split(":", 2)[1]
        if request.action_type == "run_command" and not self._allowed_command(payload):
            return False, "command_not_on_fixture_allowlist", "command_allowlist"
        if request.action_type in {"start_service", "stop_service"} and request.target not in {"", ".", "app.py"}:
            return False, "service_target_must_be_fixture_app", "service_target"
        if request.action_type == "http_request" and str(payload.get("method") or "GET").upper() != "GET":
            return False, "only_safe_local_get_requests_are_allowed", "http_method"
        return True, "authorized_local_sandbox_action", ""

    def _allowed_command(self, payload: Mapping[str, Any]) -> bool:
        argv = tuple(str(part) for part in payload.get("argv", ()) if str(part))
        if len(argv) < 3 or Path(argv[0]).name.lower() not in {"python", "python.exe"}:
            return False
        if argv[1:3] not in {("-m", "pytest"), ("-m", "py_compile")}:
            return False
        return not any(".." in part or part.startswith("-") and part not in {"-m", "-q"} for part in argv[3:])

    def _execute(self, request: SandboxActionRequest, decision: SandboxActionDecision, payload: Mapping[str, Any], replay_key: str) -> SandboxActionReceipt:
        try:
            if request.action_type == "read_file":
                path, _ = self._fixture_path(request.target)
                assert path is not None
                text = path.read_text(encoding="utf-8")
                return self._receipt(request, decision, replay_key, status="completed", stdout=text)
            if request.action_type == "read_log":
                path, _ = self._fixture_path(request.target or "service.log")
                assert path is not None
                text = path.read_text(encoding="utf-8") if path.exists() else ""
                return self._receipt(request, decision, replay_key, status="completed", stdout=text)
            if request.action_type == "write_file":
                path, _ = self._fixture_path(request.target)
                assert path is not None
                content = str(payload.get("content") or "")
                if len(content) > 50000:
                    return self._receipt(request, decision, replay_key, status="blocked", stderr="write_content_too_large")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return self._receipt(request, decision, replay_key, status="completed", files_changed=(str(path.relative_to(self.fixture_root)),))
            if request.action_type == "run_command":
                argv = [sys.executable, *[str(part) for part in payload["argv"][1:]]]
                completed = subprocess.run(argv, cwd=self.fixture_root, capture_output=True, text=True, timeout=20, check=False)
                return self._receipt(request, decision, replay_key, status="completed", exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
            if request.action_type == "start_service":
                if self._service is not None and self._service.poll() is None:
                    return self._receipt(request, decision, replay_key, status="completed", stdout="service_already_running")
                log_path = self.fixture_root / "service.log"
                log_handle = log_path.open("a", encoding="utf-8")
                self._service = subprocess.Popen([sys.executable, "app.py", str(self.authorization.service_port)], cwd=self.fixture_root, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
                for _ in range(20):
                    try:
                        self._local_get(f"http://localhost:{self.authorization.service_port}/health")
                        return self._receipt(request, decision, replay_key, status="completed", stdout="service_started")
                    except OSError:
                        time.sleep(0.1)
                return self._receipt(request, decision, replay_key, status="failed", stderr="service_start_timeout")
            if request.action_type == "stop_service":
                if self._service is not None and self._service.poll() is None:
                    self._service.terminate()
                    self._service.wait(timeout=5)
                return self._receipt(request, decision, replay_key, status="completed", stdout="service_stopped")
            if request.action_type == "http_request":
                status_code, body = self._local_get(request.target)
                return self._receipt(request, decision, replay_key, status="completed", status_code=status_code, response=body)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            return self._receipt(request, decision, replay_key, status="failed", stderr=f"{type(exc).__name__}:{exc}")
        return self._receipt(request, decision, replay_key, status="blocked", stderr="unreachable_action_type")

    @staticmethod
    def _local_get(target: str) -> tuple[int, str]:
        opener = build_opener(ProxyHandler({}))
        with opener.open(Request(target, method="GET"), timeout=5) as response:
            return int(response.status), response.read(12000).decode("utf-8", errors="replace")

    def _receipt(self, request: SandboxActionRequest, decision: SandboxActionDecision, replay_key: str, *, status: str, exit_code: int | None = None, status_code: int | None = None, stdout: str = "", stderr: str = "", response: str = "", files_changed: tuple[str, ...] = ()) -> SandboxActionReceipt:
        return SandboxActionReceipt(
            receipt_id=_stable_id("sandbox-action-receipt", request.request_id, decision.decision_id, status, exit_code, status_code, stdout, stderr, response, files_changed),
            request_id=request.request_id,
            decision_id=decision.decision_id,
            status=status,
            exit_code=exit_code,
            status_code=status_code,
            stdout_summary=_summary(stdout),
            stderr_summary=_summary(stderr),
            response_summary=_summary(response),
            files_changed=files_changed,
            timestamp=time.time(),
            replay_key=replay_key,
        )

    def cleanup(self) -> None:
        if self._service is not None and self._service.poll() is None:
            self._service.terminate()
            try:
                self._service.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._service.kill()

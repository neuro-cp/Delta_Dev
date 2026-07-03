"""Local evaluator environment loading for DELTA V1.6 scaffolds.

The loader is intentionally small and inert: it reads optional key/value files,
does not call providers, and only exposes masked configuration for reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os


DEFAULT_ENV_FILE = Path(".env.local")


@dataclass(frozen=True)
class DeltaEvaluatorEnv:
    provider: str = "openai"
    api_key_present: bool = False
    api_key_masked: str = ""
    model: str = "gpt-4.1-mini"
    enabled: bool = False
    allow_live_call: bool = False
    endpoint: str = ""

    @property
    def live_call_permitted(self) -> bool:
        return self.enabled and self.allow_live_call and self.api_key_present

    def to_report_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "api_key_present": self.api_key_present,
            "api_key_masked": self.api_key_masked,
            "model": self.model,
            "enabled": self.enabled,
            "allow_live_call": self.allow_live_call,
            "endpoint": self.endpoint,
            "live_call_permitted": self.live_call_permitted,
        }


def _parse_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _mask_secret(value: str | None) -> str:
    secret = (value or "").strip()
    if not secret or secret == "put_key_here":
        return ""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


def parse_env_file(path: Path | str = DEFAULT_ENV_FILE) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    parsed: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def load_delta_evaluator_env(
    path: Path | str = DEFAULT_ENV_FILE,
    environ: Mapping[str, str] | None = None,
) -> DeltaEvaluatorEnv:
    file_values = parse_env_file(path)
    source = dict(file_values)
    source.update(dict(environ if environ is not None else os.environ))

    api_key = source.get("DELTA_EVALUATOR_API_KEY", "")
    return DeltaEvaluatorEnv(
        provider=source.get("DELTA_EVALUATOR_PROVIDER", "openai") or "openai",
        api_key_present=bool(api_key and api_key != "put_key_here"),
        api_key_masked=_mask_secret(api_key),
        model=source.get("DELTA_EVALUATOR_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
        enabled=_parse_bool(source.get("DELTA_EVALUATOR_ENABLED")),
        allow_live_call=_parse_bool(source.get("DELTA_EVALUATOR_ALLOW_LIVE_CALL")),
        endpoint=source.get("DELTA_EVALUATOR_ENDPOINT", ""),
    )

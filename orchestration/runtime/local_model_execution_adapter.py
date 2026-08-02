"""Shared local-model execution boundary for DELTA runtime callers.

The host UI process may not have native GGUF dependencies installed. This
adapter keeps that interpreter detail out of higher-level routing code by
falling through to the project venv subprocess helper when needed.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from integration.model_runtime.provider_manager import ProviderManager


ROOT = Path(__file__).resolve().parents[2]


def execute_local_model_inference(
    *,
    model_name: str,
    prompt: str,
    task_type: str,
    metadata: Mapping[str, Any] | None = None,
    provider_manager: Any | None = None,
    execution_adapter: str,
    fallback_on_missing_llama_cpp: bool = True,
    timeout_seconds: int = 240,
) -> dict[str, Any]:
    metadata_payload = dict(metadata or {})
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            manager = provider_manager or ProviderManager()
            result = manager.infer(
                model_name=model_name,
                prompt=prompt,
                task_type=task_type,
                metadata=metadata_payload,
            )
        answer = str(result.answer or "").strip()
        return {
            "executed": bool(answer),
            "available": True,
            "answer": answer,
            "confidence_score": float(result.confidence or 0.0),
            "model_id": str(result.model_id or model_name),
            "latency_seconds": float(result.latency_seconds or 0.0),
            "response_tokens": int(result.response_tokens or 0),
            "prompt_sent": prompt,
            "execution_adapter": execution_adapter + ".ProviderManager",
            "provider_calls_performed": False,
            "reason": None if answer else "empty_model_answer",
        }
    except Exception as exc:  # noqa: BLE001 - returned as structured local diagnostic.
        if fallback_on_missing_llama_cpp and _is_missing_llama_cpp(exc):
            fallback = execute_local_model_via_venv_subprocess(
                model_name=model_name,
                prompt=prompt,
                task_type=task_type,
                metadata=metadata_payload,
                execution_adapter=execution_adapter + ".venv_subprocess",
                timeout_seconds=timeout_seconds,
            )
            if fallback.get("executed"):
                return fallback
            return {
                **fallback,
                "available": True,
                "prompt_sent": prompt,
                "provider_calls_performed": False,
                "host_exception_class": type(exc).__name__,
                "host_exception_message": str(exc)[:220],
            }
        return {
            "executed": False,
            "available": True,
            "answer": "",
            "reason": f"local_model_execution_failed:{type(exc).__name__}:{str(exc)[:220]}",
            "prompt_sent": prompt,
            "execution_adapter": execution_adapter + ".ProviderManager",
            "provider_calls_performed": False,
            "exception_class": type(exc).__name__,
            "exception_message": str(exc)[:220],
        }


def execute_local_model_via_venv_subprocess(
    *,
    model_name: str,
    prompt: str,
    task_type: str,
    metadata: Mapping[str, Any] | None = None,
    execution_adapter: str,
    timeout_seconds: int = 240,
) -> dict[str, Any]:
    venv_python = ROOT / ".venv311" / "Scripts" / "python.exe"
    helper = ROOT / "scripts" / "delta_rc2_local_model_infer.py"
    if not venv_python.exists():
        return {"executed": False, "reason": "local_model_venv_python_missing", "execution_adapter": execution_adapter}
    if not helper.exists():
        return {"executed": False, "reason": "local_model_subprocess_helper_missing", "execution_adapter": execution_adapter}
    request = {
        "model_name": model_name,
        "prompt": prompt,
        "task_type": task_type,
        "metadata": dict(metadata or {}),
    }
    try:
        completed = subprocess.run(
            [str(venv_python), str(helper)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001 - returned as an inert diagnostic.
        return {
            "executed": False,
            "reason": f"local_model_subprocess_failed:{type(exc).__name__}:{str(exc)[:180]}",
            "execution_adapter": execution_adapter,
        }
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    if completed.returncode != 0 or not payload.get("executed"):
        reason = str(payload.get("error") or completed.stderr or f"local_model_subprocess_returned_{completed.returncode}")[:240]
        return {"executed": False, "reason": reason, "execution_adapter": execution_adapter}
    answer = str(payload.get("answer") or "").strip()
    return {
        "executed": bool(answer),
        "available": True,
        "answer": answer,
        "confidence_score": float(payload.get("confidence_score") or 0.0),
        "model_id": str(payload.get("model_id") or model_name),
        "latency_seconds": float(payload.get("latency_seconds") or 0.0),
        "response_tokens": int(payload.get("response_tokens") or len(answer.split())),
        "prompt_sent": prompt,
        "execution_adapter": execution_adapter,
        "provider_calls_performed": False,
        "reason": None if answer else "local_model_subprocess_empty_answer",
    }


def _is_missing_llama_cpp(exc: Exception) -> bool:
    return (isinstance(exc, ModuleNotFoundError) and getattr(exc, "name", "") == "llama_cpp") or "llama_cpp" in str(exc)

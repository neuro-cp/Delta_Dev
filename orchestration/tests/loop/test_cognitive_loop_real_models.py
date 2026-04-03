import os
import pytest

from orchestration.loop.cognitive_loop import CognitiveLoop
from integration.model_runtime.model_router import ModelRouter


def _ensure_env():
    run_flag = os.getenv("RUN_REAL_MODELS")
    profile = os.getenv("DELTA_MACHINE_PROFILE")
    max_models = os.getenv("DELTA_MAX_MODELS")

    if run_flag is None:
        run_flag = input("set run real models (1 or 0): ").strip()
        os.environ["RUN_REAL_MODELS"] = run_flag

    if profile is None:
        profile = input("set env (desktop or laptop ?): ").strip().lower()
        os.environ["DELTA_MACHINE_PROFILE"] = profile

    if max_models is None:
        max_models = input("max models to run (1–4, optional): ").strip()
        if max_models:
            os.environ["DELTA_MAX_MODELS"] = max_models

    print(f"\n[CONFIG] RUN_REAL_MODELS={run_flag}")
    print(f"[CONFIG] DELTA_MACHINE_PROFILE={profile}")
    print(f"[CONFIG] DELTA_MAX_MODELS={os.getenv('DELTA_MAX_MODELS')}\n")

    return run_flag, profile


def _get_prompt():
    """
    Interactive prompt input with safe fallback.
    """
    try:
        user_input = input("enter prompt (leave empty for default): ").strip()
    except EOFError:
        # pytest or non-interactive fallback
        user_input = ""

    if not user_input:
        user_input = "Compare YAML and JSON for configuration files in one short paragraph."

    return user_input


def test_cognitive_loop_real_llm_pipeline(monkeypatch):
    run_flag, profile = _ensure_env()

    if run_flag != "1":
        pytest.skip("RUN_REAL_MODELS not enabled")

    monkeypatch.setenv("DELTA_MACHINE_PROFILE", profile)

    router = ModelRouter()

    max_models = os.getenv("DELTA_MAX_MODELS")
    if max_models:
        try:
            router.route_chain = router.route_chain[: int(max_models)]
        except Exception:
            pass

    loop = CognitiveLoop(model_router=router)

    # 🔥 NEW: interactive prompt
    prompt = _get_prompt()

    print("\n--- INPUT PROMPT ---")
    print(prompt)
    print("--------------------\n")

    out = loop.run(prompt)
    result = out["result"]

    # assertions
    assert result.success is True
    assert isinstance(result.output, str)
    assert result.output.strip() != ""

    # debug output
    print("\n--- ROUTER PROFILE ---")
    print(router.profile)
    print(router.route_chain)

    print("\n--- REAL MODEL OUTPUT ---")
    print(result.output)
    print("--- END OUTPUT ---\n")
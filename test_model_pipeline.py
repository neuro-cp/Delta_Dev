from pathlib import Path

from integration.model_runtime.model_router import ModelRouter
from integration.model_runtime.prompt_builder import run_question


PROMPT_PATH = Path("test_prompt.txt")


def main():

    if not PROMPT_PATH.exists():
        raise FileNotFoundError("test_prompt.txt not found")

    question = PROMPT_PATH.read_text(encoding="utf-8").strip()

    print("\n======================================")
    print("PROMPT LOADED FROM test_prompt.txt")
    print("======================================\n")

    print(question)
    print("\n======================================")
    print("BEGIN MODEL PIPELINE")
    print("======================================\n")

    router = ModelRouter()

    result = run_question(router, question)

    print("\n======================================")
    print("FINAL RESULT")
    print("======================================\n")

    if hasattr(result, "payload") and "raw_model_output" in result.payload:
        print(result.payload["raw_model_output"])

    print("\n--------------------------------------")
    print("Confidence Band:", result.confidence_band)
    print("--------------------------------------\n")


if __name__ == "__main__":
    main()
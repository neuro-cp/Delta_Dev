"""
integration/model_runtime/prompt_builder.py

Prompt construction and test harness.
"""

from typing import Dict, Any


def build_input_payload(question: str) -> Dict[str, Any]:
    """
    Convert a raw question into the payload expected by the model runtime.
    """

    return {
        "semantic_tokens": ["human_question"],
        "quantitative_fields": {},
        "question": question,
    }


def build_prompt(payload: Dict[str, Any]) -> str:
    """
    Build a deterministic prompt.

    If previous_model_output exists, the model enters critique mode.
    """

    question = payload.get("question", "").strip()
    previous = payload.get("previous_model_output")

    if previous:
        prompt = f"""
You are part of an automated AI reasoning pipeline.

Another model already attempted this question.
Your job is to review that answer, correct it if needed, and improve it.

Your response will be parsed by software.

You must return exactly ONE valid JSON object and nothing else.

Rules:
- Do not include markdown
- Do not include commentary outside the JSON
- Do not include multiple JSON objects
- Do not include code fences
- Do not repeat placeholder text

Required format:
{{"answer":"<your answer here>","confidence":0.0}}

Constraints:
- "answer" must be a single paragraph string
- "confidence" must be a number between 0.0 and 1.0
- do not add extra fields
- do not nest objects
- do not return the literal text "<your answer here>"

Previous model output:
{previous}

Original question:
{question}

Return only the JSON object.
"""
    else:
        prompt = f"""
You are part of an automated AI reasoning pipeline.

Your response will be parsed by software.

You must return exactly ONE valid JSON object and nothing else.

Rules:
- Do not include markdown
- Do not include commentary outside the JSON
- Do not include multiple JSON objects
- Do not include code fences
- Do not repeat placeholder text

Required format:
{{"answer":"<your answer here>","confidence":0.0}}

Constraints:
- "answer" must be a single paragraph string
- "confidence" must be a number between 0.0 and 1.0
- do not add extra fields
- do not nest objects
- do not return the literal text "<your answer here>"

Question:
{question}

Return only the JSON object.
"""

    return prompt.strip()


def run_question(router, question: str):
    """
    Run a human question through the full routing pipeline.
    """

    payload = build_input_payload(question)
    return router.route(payload)
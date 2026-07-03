"""Generate the Runtime V3.0 static guided review console."""

from __future__ import annotations

import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_current_state_knowledge_inventory import build_current_state_inventory, safety_invariants
from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer
from orchestration.runtime.v30_conversational_answer_formatter import format_conversational_answer
from orchestration.runtime.v30_pipeline_explainer import explain_answer_pipeline, render_pipeline_explanation


HTML_PATH = Path("ui/delta_v30_guided_review_console.html")
REPORT_MD = Path("reports/runtime_v30c_guided_review_console.md")
REPORT_JSON = Path("reports/runtime_v30c_guided_review_console.json")


def build_guided_review_console_model() -> dict[str, object]:
    query = "What is DELTA?"
    answer_data = run_v29_local_answer(query)
    explanation = explain_answer_pipeline(answer_data)
    inventory = build_current_state_inventory()
    return {
        "phase": "Runtime V3.0C",
        "query": query,
        "answer": format_conversational_answer(answer_data, mode="detailed"),
        "provenance": answer_data["local_answer"]["provenance"],
        "pipeline_trace": render_pipeline_explanation(explanation),
        "safety_gates": explanation["safety_gates_checked"],
        "disabled_capabilities": inventory["disabled_capabilities"],
        "next_recommended_action": "PROCEED_MANUAL_DEMO_SCENARIO_PACK",
        "safety_invariants": safety_invariants(),
    }


def render_guided_review_console_html(model: dict[str, object]) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    provenance = "".join(f"<li>{esc(item)}</li>" for item in model["provenance"])
    gates = "".join(f"<li><strong>{esc(key)}</strong>: {esc(value)}</li>" for key, value in model["safety_gates"].items())
    disabled = "".join(f"<li>{esc(item)}</li>" for item in model["disabled_capabilities"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>DELTA V3.0 Guided Review Console</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f5f7fb; color: #1d2433; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 32px; }}
    section {{ background: white; border: 1px solid #d9e1ef; border-radius: 8px; padding: 18px; margin: 14px 0; }}
    h1 {{ margin-top: 0; }}
    h2 {{ font-size: 18px; margin-top: 0; }}
    textarea {{ width: 100%; min-height: 76px; border: 1px solid #aebbd0; border-radius: 6px; padding: 10px; }}
    pre {{ white-space: pre-wrap; background: #101828; color: #eef4ff; padding: 14px; border-radius: 6px; }}
    .pill {{ display: inline-block; padding: 4px 8px; border-radius: 999px; background: #e7f0ff; color: #174ea6; }}
  </style>
</head>
<body>
  <main>
    <h1>DELTA Guided Review Console <span class="pill">Runtime V3.0C</span></h1>
    <section>
      <h2>Ask DELTA</h2>
      <textarea readonly>{esc(model['query'])}</textarea>
    </section>
    <section>
      <h2>Answer</h2>
      <pre>{esc(model['answer'])}</pre>
    </section>
    <section>
      <h2>Provenance</h2>
      <ul>{provenance}</ul>
    </section>
    <section>
      <h2>Pipeline Trace</h2>
      <pre>{esc(model['pipeline_trace'])}</pre>
    </section>
    <section>
      <h2>Safety Gates</h2>
      <ul>{gates}</ul>
    </section>
    <section>
      <h2>Disabled Capabilities</h2>
      <ul>{disabled}</ul>
    </section>
    <section>
      <h2>Next Recommended Action</h2>
      <p>{esc(model['next_recommended_action'])}</p>
    </section>
  </main>
</body>
</html>
"""


def write_guided_review_console() -> dict[str, object]:
    model = build_guided_review_console_model()
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(render_guided_review_console_html(model), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(model, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.0C Guided Review Console UX\n\n"
        f"Static guided console generated at `{HTML_PATH.as_posix()}`.\n\n"
        "Sections: Ask DELTA, Answer, Provenance, Pipeline Trace, Safety Gates, Disabled Capabilities, and Next Recommended Action.\n",
        encoding="utf-8",
    )
    return model


if __name__ == "__main__":
    print(write_guided_review_console()["next_recommended_action"])

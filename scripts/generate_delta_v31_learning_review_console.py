"""Generate Runtime V3.1 static learning review console."""

from __future__ import annotations

import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_contradiction_aggregation import build_contradiction_aggregation_report
from orchestration.runtime.v31_learning_opportunity import detect_learning_opportunities
from orchestration.runtime.v31_learning_proposal import build_learning_proposals


HTML_PATH = Path("ui/delta_v31_learning_review_console.html")
REPORT_MD = Path("reports/runtime_v31e_learning_review_console.md")
REPORT_JSON = Path("reports/runtime_v31e_learning_review_console.json")


def build_learning_review_console_model() -> dict[str, object]:
    sample = "I have corrected this preference five times."
    opportunities = [item.as_dict() for item in detect_learning_opportunities(sample)]
    proposals = [item.as_dict() for item in build_learning_proposals(sample, review_status="review")]
    contradictions = build_contradiction_aggregation_report()["bundles"]
    return {
        "phase": "Runtime V3.1E",
        "sample_interaction": sample,
        "learning_opportunities": opportunities,
        "proposal_objects": proposals,
        "supporting_evidence": [proposal["supporting_evidence"] for proposal in proposals],
        "conflicts": contradictions,
        "approval_state": "review_only_no_integration",
        "risk_level": "low_if_kept_report_only",
        "blocked_reason": "learning_integration_disabled",
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_LEARNING_EXPLAINABILITY",
    }


def render_learning_review_console_html(model: dict[str, object]) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    opportunities = "".join(f"<li>{esc(item['category'])}: {esc(item['reason'])}</li>" for item in model["learning_opportunities"])
    proposals = "".join(f"<li>{esc(item['proposal_id'])}: {esc(item['review_status'])}, integrated={esc(item['integrated'])}</li>" for item in model["proposal_objects"])
    conflicts = "".join(f"<li>{esc(item['topic'])}: frequency {esc(item['frequency'])}, resolved={esc(item['resolved'])}</li>" for item in model["conflicts"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>DELTA V3.1 Learning Review Console</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f7f8fb; color: #1f2937; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 32px; }}
    section {{ background: #fff; border: 1px solid #d8dee9; border-radius: 8px; margin: 14px 0; padding: 18px; }}
    h1 {{ margin-top: 0; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <main>
    <h1>DELTA Learning Review Console</h1>
    <section><h2>Sample Interaction</h2><p>{esc(model['sample_interaction'])}</p></section>
    <section><h2>Learning Opportunities</h2><ul>{opportunities}</ul></section>
    <section><h2>Proposal Objects</h2><ul>{proposals}</ul></section>
    <section><h2>Supporting Evidence</h2><pre>{esc(model['supporting_evidence'])}</pre></section>
    <section><h2>Conflicts</h2><ul>{conflicts}</ul></section>
    <section><h2>Approval State</h2><p>{esc(model['approval_state'])}</p></section>
    <section><h2>Risk Level</h2><p>{esc(model['risk_level'])}</p></section>
    <section><h2>Blocked Reason</h2><p><code>{esc(model['blocked_reason'])}</code></p></section>
  </main>
</body>
</html>
"""


def write_learning_review_console() -> dict[str, object]:
    model = build_learning_review_console_model()
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(render_learning_review_console_html(model), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(model, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V3.1E Learning Review Console\n\n"
        f"Static review console generated at `{HTML_PATH.as_posix()}`. It displays opportunities, proposals, evidence, conflicts, approval state, risk, and blocked reason without approval writes or integration.\n",
        encoding="utf-8",
    )
    return model


if __name__ == "__main__":
    print(write_learning_review_console()["final_recommendation"])

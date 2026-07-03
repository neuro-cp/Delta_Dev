from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v14_feedback import (
    FeedbackDisposition,
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
)
from orchestration.runtime.v14_replay_markers import ReplayMarkerStatus


FINAL_RECOMMENDATION = "PROCEED_SLEEP_REPLAY_CONSOLIDATION_DESIGN"


def build_feedback_capture_report_data() -> dict[str, object]:
    return {
        "report": "runtime_v14d_episodic_feedback_capture_scaffold",
        "final_recommendation": FINAL_RECOMMENDATION,
        "current_state": {
            "runtime_v13_complete": True,
            "model_b_default": True,
            "hyb1_dormant_env_gated_only": True,
            "v14a_safe_scaffold_complete": True,
            "v14b_output_discipline_scaffold_complete": True,
            "v14c_trace_design_complete": True,
        },
        "modules_added": [
            "orchestration/runtime/v14_episode.py",
            "orchestration/runtime/v14_feedback.py",
            "orchestration/runtime/v14_replay_markers.py",
            "orchestration/runtime/v14_feedback_to_pruning.py",
            "orchestration/runtime/v14_feedback_report.py",
        ],
        "original_delta_path_trace": {
            "source": "reports/original_delta_runtime_path_trace.md",
            "old_engine_runtime_adopted_directly": False,
            "conceptual_path_adopted": "observation -> episodic boundary -> episode trace -> episode replay",
            "future_deferred_path": "offline hypothesis trace / hypothesis runner",
            "deferred": [
                "execution gate activation",
                "recall runtime bridge",
                "routing influence",
                "live pruning",
                "controlled training",
                "canonical mutation",
            ],
        },
        "safety_boundaries": {
            "training_enabled": False,
            "live_pruning_enabled": False,
            "canonical_mutation_enabled": False,
            "provider_calls_enabled": False,
            "live_specialist_routing_enabled": False,
            "model_b_default_changed": False,
            "hyb1_default_enabled": False,
            "action_execution_enabled": False,
        },
        "feedback_flow": [
            "AnswerTrace",
            "EpisodeTrace",
            "FeedbackCaptureRecord",
            "FeedbackEventDraft",
            "ReplayReviewMarker",
            "PruningReviewProposal",
        ],
        "feedback_dispositions": [disposition.value for disposition in FeedbackDisposition],
        "feedback_sources": [source.value for source in FeedbackSource],
        "feedback_polarities": [polarity.value for polarity in FeedbackPolarity],
        "feedback_severities": [severity.value for severity in FeedbackSeverity],
        "feedback_targets": [target.value for target in FeedbackTarget],
        "replay_marker_statuses": [status.value for status in ReplayMarkerStatus],
        "inactive": [
            "training",
            "live pruning",
            "canonical mutation",
            "canonical pruning",
            "provider calls",
            "live specialist routing",
            "active sleep/replay consolidation",
            "autonomous acquisition",
        ],
        "next_phase": "Runtime V1.4E - Sleep/Replay Consolidation Design",
    }


def write_feedback_capture_report(md_path: str | Path, json_path: str | Path) -> None:
    data = build_feedback_capture_report_data()
    md_target = Path(md_path)
    json_target = Path(json_path)
    md_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_target.write_text(_render_markdown(data), encoding="utf-8")


def _render_markdown(data: dict[str, object]) -> str:
    safety = data["safety_boundaries"]
    assert isinstance(safety, dict)
    modules = data["modules_added"]
    assert isinstance(modules, list)
    inactive = data["inactive"]
    assert isinstance(inactive, list)
    return "\n".join(
        [
            "# Runtime V1.4D Episodic Feedback Capture Scaffold",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
            "## 1. Summary",
            "",
            "Runtime V1.4D creates the non-mutating bridge from answer traces to original-DELTA-style episodic boundaries, episode traces, feedback drafts, replay markers, and pruning-review proposals. Feedback records are not learning. Replay markers are not replay. Pruning review proposals are not pruning.",
            "",
            "## 2. Current Completed State",
            "",
            "- Runtime V1.3 complete: Model B default, HYB1 dormant/env-gated only.",
            "- Runtime V1.4A complete: evidence roles, lane permissions, pruning schema, CandidateEnvelope, gap map.",
            "- Runtime V1.4B complete: output discipline, unknown-answer port, dormant specialist router.",
            "- Runtime V1.4C complete: architecture decision lock and output trace design.",
            "",
            "## 3. Original DELTA Runtime Path Trace Conclusion",
            "",
            "The old `G:\\Delta_DevV0\\engine\\runtime.py` was not adopted directly. It is too tied to the old dynamical simulation. V1.4D adopts only this original DELTA path conceptually:",
            "",
            "`observation -> episodic boundary -> episode trace -> episode replay`",
            "",
            "Offline hypothesis trace / hypothesis runner is deferred for future report-only arbitration. Execution gate activation, recall runtime bridge, routing influence, live pruning, controlled training, and canonical mutation remain deferred.",
            "",
            "## 4. Why V1.4D Exists",
            "",
            "Future replay, pruning, and controlled learning need structured feedback material. V1.4D records that material without mutating memory or triggering training.",
            "",
            "## 5. Episodic Boundary Design",
            "",
            "- `ObservationBoundary`",
            "- `EpisodeBoundaryReason`",
            "- `EpisodeReplayStatus`",
            "- `EpisodeReplayIntent`",
            "",
            "## 6. Episode Trace Objects",
            "",
            "- `EpisodeTrace`",
            "- `create_episode_from_answer_trace`",
            "- `attach_feedback_to_episode`",
            "- `attach_replay_marker_to_episode`",
            "",
            "Episode traces are not canonical memory. They do not train, replay themselves, or mutate stores.",
            "",
            "## 7. Feedback Capture Objects",
            "",
            "- `FeedbackCaptureRecord`",
            "- `FeedbackCaptureSummary`",
            "- `FeedbackEventDraft` conversion",
            "",
            "## 8. Feedback Disposition Rules",
            "",
            "- benchmark-only feedback forces `benchmark_only_do_not_train`.",
            "- critical severity requires human review.",
            "- safety-risk feedback requires human review.",
            "- user correction becomes replay-eligible review material, not immediate training.",
            "- user rejection becomes replay-eligible review material, not immediate training.",
            "- noise feedback with affected concepts may become a pruning-review candidate, not live pruning.",
            "",
            "## 9. Replay Marker Design",
            "",
            "Replay markers classify feedback into proposed review items. They do not execute replay, consolidate memories, or train.",
            "",
            "## 10. Pruning Review Proposal Design",
            "",
            "Pruning review proposals translate feedback into reversible review candidates. They do not delete concepts or apply live pruning.",
            "",
            "## 11. Non-Mutating Safety Boundaries",
            "",
            *[f"- {key}: `{value}`" for key, value in safety.items()],
            "",
            "## 12. What Remains Inactive",
            "",
            *[f"- {item}" for item in inactive],
            "",
            "## 13. What Should Come Next",
            "",
            "Proceed to sleep/replay consolidation design. That phase should consume trace and feedback scaffolds, but still avoid canonical mutation until the replay design is validated.",
            "",
            "## 14. Continuation Checkpoint",
            "",
            "- `v14d_feedback_capture_scaffold_complete`: `True`",
            "- `training_enabled`: `False`",
            "- `live_pruning_enabled`: `False`",
            "- `canonical_mutation_enabled`: `False`",
            "- `provider_calls_enabled`: `False`",
            "- `live_specialist_routing_enabled`: `False`",
            "- `model_b_default_remains_active`: `True`",
            "- `hyb1_dormant_only`: `True`",
            f"- `next_step`: `{data['final_recommendation']}`",
            "",
            str(data["final_recommendation"]),
        ]
    )


if __name__ == "__main__":
    write_feedback_capture_report(
        "reports/runtime_v14d_episodic_feedback_capture_scaffold.md",
        "reports/runtime_v14d_episodic_feedback_capture_scaffold.json",
    )

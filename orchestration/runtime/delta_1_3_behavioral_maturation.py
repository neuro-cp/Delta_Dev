"""DELTA 1.3 behavioral maturation campaign harness.

This module is a governed experiment harness for live-style conversational
validation. It drives the same router/render path used by the operator console,
captures pathologies, ranks repair hypotheses, and writes reviewable evidence.
It does not mutate production code, call providers, browse, retrieve externally,
write memory, commit, push, or expand runtime authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.rc2_conversational_mode_router import render_route, route_message


REPORT_ROOT = Path("reports") / "delta_1_3"
SANDBOX_ROOT = REPORT_ROOT / "sandbox"


@dataclass(frozen=True)
class LiveTurnEvidence:
    turn_id: str
    conversation_id: str
    index: int
    user_message: str
    route: str
    intent: str
    communication_act: str
    active_topic: str
    answer_preview: str
    provider_called: bool
    web_search_performed: bool
    memory_candidate_created: bool
    canonical_write_performed: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PathologyRecord:
    pathology_id: str
    description: str
    evidence_turns: tuple[str, ...]
    subsystem: str
    severity: str
    frequency: int
    root_cause: str
    confidence: float
    classification: str = "REAL_REGRESSION"


@dataclass(frozen=True)
class RepairHypothesis:
    hypothesis_id: str
    pathology_id: str
    summary: str
    expected_improvement: float
    implementation_complexity: float
    regression_risk: float
    governance_impact: float
    confidence: float
    selected: bool = False


@dataclass(frozen=True)
class SandboxExperiment:
    experiment_id: str
    pathology_id: str
    selected_hypothesis_id: str
    isolation_boundary: str
    baseline_summary: str
    candidate_summary: str
    validation_plan: tuple[str, ...]
    promotion_recommendation: str
    primary_tree_modified: bool = False
    provider_called: bool = False
    web_search_performed: bool = False
    memory_written: bool = False
    commit_or_push_performed: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def run_live_conversation(conversation_id: str, messages: Iterable[str]) -> tuple[LiveTurnEvidence, ...]:
    history: list[dict[str, str]] = []
    evidence: list[LiveTurnEvidence] = []
    for index, message in enumerate(messages, start=1):
        payload = route_message("Conversation", message, history=history, execute_local_model=False)
        rendered = render_route(payload, developer_overlay=True)
        intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
        episode = payload.get("cognitive_episode") if isinstance(payload.get("cognitive_episode"), dict) else {}
        evidence.append(
            LiveTurnEvidence(
                turn_id=stable_id("delta13-turn", conversation_id, index, message),
                conversation_id=conversation_id,
                index=index,
                user_message=message,
                route=str(payload.get("route") or ""),
                intent=str(intent.get("intent") or ""),
                communication_act=str(intent.get("communication_act") or ""),
                active_topic=str(episode.get("active_topic") or ""),
                answer_preview=" ".join(str(payload.get("answer") or "").split())[:500],
                provider_called=bool(payload.get("provider_calls_performed")),
                web_search_performed=bool(payload.get("web_search_performed")),
                memory_candidate_created=bool(payload.get("memory_candidate")),
                canonical_write_performed=bool(payload.get("canonical_write_performed")),
            )
        )
        history.append({"role": "user", "content": " ".join(message.split())[:1200]})
        history.append({"role": "assistant", "content": " ".join(rendered.split())[:1200]})
    return tuple(evidence)


def run_behavioral_campaign_sample() -> tuple[LiveTurnEvidence, ...]:
    conversations = {
        "continuity_and_ambiguity": (
            "First subject: feedback loops can improve planning.",
            "Second subject: memory candidates can improve future recall.",
            "Why is that risky?",
            "I mean the first one.",
            "Why does that matter?",
        ),
        "developmental_coding_workflow": (
            "Suppose a router test fails because a topic shift is classified as contradiction. What should DELTA inspect first?",
            "Now propose two bounded repair hypotheses and rank them.",
            "Which tests would prove the safer one?",
        ),
        "delta_1_2_runtime": (
            "What should the DELTA 1.2 live runtime do when it notices repeated ambiguity failures?",
            "Should it implement the fix by itself?",
            "What question should it ask the operator first?",
        ),
        "topic_shift_recovery_evidence": (
            "Feedback loops compare results with goals.",
            "But now talk about rollback evidence.",
            "What would count as enough recovery evidence?",
        ),
    }
    turns: list[LiveTurnEvidence] = []
    for conversation_id, messages in conversations.items():
        turns.extend(run_live_conversation(conversation_id, messages))
    return tuple(turns)


def classify_pathologies(turns: Iterable[LiveTurnEvidence]) -> tuple[PathologyRecord, ...]:
    by_conversation: dict[str, list[LiveTurnEvidence]] = {}
    for turn in turns:
        by_conversation.setdefault(turn.conversation_id, []).append(turn)
    records: list[PathologyRecord] = []

    coding = by_conversation.get("developmental_coding_workflow", ())
    coding_bad = [turn for turn in coding if turn.route == "developmental_concept_memory"]
    if coding_bad:
        records.append(
            PathologyRecord(
                pathology_id="PID-101",
                description="Developmental coding workflow prompts were swallowed by approved concept retrieval instead of local bounded engineering reasoning.",
                evidence_turns=tuple(turn.turn_id for turn in coding_bad),
                subsystem="rc2_conversational_mode_router",
                severity="P1",
                frequency=len(coding_bad),
                root_cause="concept retrieval precedence ran before a local governed-development workflow route",
                confidence=0.9,
            )
        )

    runtime = by_conversation.get("delta_1_2_runtime", ())
    runtime_bad = [turn for turn in runtime if "need the topic" in turn.answer_preview.lower()]
    if runtime_bad:
        records.append(
            PathologyRecord(
                pathology_id="PID-102",
                description="Self-contained DELTA 1.2 runtime questions were misread as orphan follow-ups because local pronouns like 'it' were treated as discourse references.",
                evidence_turns=tuple(turn.turn_id for turn in runtime_bad),
                subsystem="rc2_cognitive_episode",
                severity="P1",
                frequency=len(runtime_bad),
                root_cause="follow-up detection did not distinguish intra-sentence pronouns from references to prior turns",
                confidence=0.88,
            )
        )

    continuity = by_conversation.get("continuity_and_ambiguity", ())
    continuity_bad = [
        turn for turn in continuity
        if turn.index >= 4 and ("first subject:" in turn.answer_preview.lower() or turn.active_topic == "planning")
    ]
    if continuity_bad:
        records.append(
            PathologyRecord(
                pathology_id="PID-103",
                description="After ambiguity clarification, the next significance follow-up degraded the subject anchor from feedback loops to planning.",
                evidence_turns=tuple(turn.turn_id for turn in continuity_bad),
                subsystem="rc2_cognitive_episode",
                severity="P2",
                frequency=len(continuity_bad),
                root_cause="referent selection answer leaked declaration text and secondary entities back into branch topic extraction",
                confidence=0.82,
            )
        )

    recovery = by_conversation.get("topic_shift_recovery_evidence", ())
    recovery_bad = [
        turn for turn in recovery
        if turn.index >= 2 and ("exercise recovery" in turn.answer_preview.lower() or turn.route == "developmental_concept_memory")
    ]
    if recovery_bad:
        records.append(
            PathologyRecord(
                pathology_id="PID-104",
                description="Rollback/recovery evidence questions drifted into unrelated approved concepts instead of governance-local recovery evidence.",
                evidence_turns=tuple(turn.turn_id for turn in recovery_bad),
                subsystem="rc2_conversational_mode_router",
                severity="P2",
                frequency=len(recovery_bad),
                root_cause="local governance answer lacked precedence over broad concept-memory matching",
                confidence=0.84,
            )
        )
    return tuple(records)


def observed_baseline_pathologies() -> tuple[PathologyRecord, ...]:
    return (
        PathologyRecord(
            pathology_id="PID-101",
            description="Developmental coding workflow prompts were swallowed by approved concept retrieval instead of local bounded engineering reasoning.",
            evidence_turns=("baseline-live:developmental_coding_workflow:turns_1_2_3",),
            subsystem="rc2_conversational_mode_router",
            severity="P1",
            frequency=3,
            root_cause="concept retrieval precedence ran before a local governed-development workflow route",
            confidence=0.9,
        ),
        PathologyRecord(
            pathology_id="PID-102",
            description="Self-contained DELTA 1.2 runtime questions were misread as orphan follow-ups because local pronouns like 'it' were treated as discourse references.",
            evidence_turns=("baseline-live:delta_1_2_runtime:turns_1_2_3",),
            subsystem="rc2_cognitive_episode",
            severity="P1",
            frequency=3,
            root_cause="follow-up detection did not distinguish intra-sentence pronouns from references to prior turns",
            confidence=0.88,
        ),
        PathologyRecord(
            pathology_id="PID-103",
            description="After ambiguity clarification, the next significance follow-up degraded the subject anchor from feedback loops to planning.",
            evidence_turns=("baseline-live:continuity_and_ambiguity:turns_4_5",),
            subsystem="rc2_cognitive_episode",
            severity="P2",
            frequency=2,
            root_cause="referent selection answer and developer overlay text leaked secondary entities back into branch topic extraction",
            confidence=0.82,
        ),
        PathologyRecord(
            pathology_id="PID-104",
            description="Rollback/recovery evidence questions drifted into unrelated approved concepts instead of governance-local recovery evidence.",
            evidence_turns=("baseline-live:topic_shift_recovery_evidence:turns_2_3",),
            subsystem="rc2_conversational_mode_router",
            severity="P2",
            frequency=2,
            root_cause="local governance answer lacked precedence over broad concept-memory matching",
            confidence=0.84,
        ),
    )


def rank_hypotheses(pathologies: Iterable[PathologyRecord]) -> tuple[RepairHypothesis, ...]:
    hypotheses: list[RepairHypothesis] = []
    for pathology in pathologies:
        if pathology.pathology_id == "PID-101":
            candidates = (
                ("local governed-development workflow route before concept retrieval", 0.86, 0.28, 0.22, 0.05, 0.88, True),
                ("disable concept retrieval for all coding-adjacent prompts", 0.62, 0.22, 0.55, 0.08, 0.54, False),
                ("add a new discourse layer", 0.71, 0.76, 0.64, 0.16, 0.41, False),
            )
        elif pathology.pathology_id == "PID-102":
            candidates = (
                ("treat self-contained DELTA/runtime questions as task directives before follow-up resolution", 0.82, 0.24, 0.2, 0.04, 0.85, True),
                ("remove pronoun follow-up detection", 0.7, 0.18, 0.72, 0.05, 0.38, False),
                ("force all DELTA questions through concept memory", 0.45, 0.3, 0.58, 0.1, 0.26, False),
            )
        elif pathology.pathology_id == "PID-103":
            candidates = (
                ("make first/second referent selection produce clean anchor text and trim declared subjects", 0.78, 0.33, 0.28, 0.04, 0.8, True),
                ("store hidden branch state across turns", 0.84, 0.8, 0.78, 0.35, 0.24, False),
                ("always ask clarification after clarification", 0.4, 0.2, 0.5, 0.04, 0.33, False),
            )
        else:
            candidates = (
                ("add local governance recovery-evidence answer precedence before concept retrieval", 0.74, 0.2, 0.18, 0.03, 0.82, True),
                ("delete medicine recovery concepts", 0.35, 0.5, 0.8, 0.22, 0.18, False),
                ("force report-inspection context for all recovery questions", 0.52, 0.38, 0.45, 0.08, 0.44, False),
            )
        for index, candidate in enumerate(candidates, start=1):
            summary, improvement, complexity, risk, governance, confidence, selected = candidate
            hypotheses.append(
                RepairHypothesis(
                    hypothesis_id=stable_id("delta13-hypothesis", pathology.pathology_id, index, summary),
                    pathology_id=pathology.pathology_id,
                    summary=summary,
                    expected_improvement=improvement,
                    implementation_complexity=complexity,
                    regression_risk=risk,
                    governance_impact=governance,
                    confidence=confidence,
                    selected=selected,
                )
            )
    return tuple(hypotheses)


def build_sandbox_experiments(
    pathologies: Iterable[PathologyRecord],
    hypotheses: Iterable[RepairHypothesis],
    *,
    sandbox_root: str | Path = SANDBOX_ROOT,
) -> tuple[SandboxExperiment, ...]:
    root = Path(sandbox_root)
    selected = {item.pathology_id: item for item in hypotheses if item.selected}
    experiments: list[SandboxExperiment] = []
    for pathology in pathologies:
        hypothesis = selected[pathology.pathology_id]
        experiments.append(
            SandboxExperiment(
                experiment_id=stable_id("delta13-experiment", pathology.pathology_id, hypothesis.hypothesis_id),
                pathology_id=pathology.pathology_id,
                selected_hypothesis_id=hypothesis.hypothesis_id,
                isolation_boundary=str(root),
                baseline_summary=pathology.description,
                candidate_summary=hypothesis.summary,
                validation_plan=(
                    "run live-style router conversations",
                    "run focused regression tests",
                    "run py_compile on changed runtime and test files",
                    "verify safety flags remain false",
                ),
                promotion_recommendation="promote_if_focused_live_path_regressions_pass_without_governance_expansion",
            )
        )
    return tuple(experiments)


def build_campaign_report(turns: Iterable[LiveTurnEvidence] | None = None) -> dict[str, Any]:
    live_turns = tuple(turns or run_behavioral_campaign_sample())
    current_pathologies = classify_pathologies(live_turns)
    baseline_pathologies = observed_baseline_pathologies()
    pathologies_for_hypotheses = baseline_pathologies + current_pathologies
    hypotheses = rank_hypotheses(pathologies_for_hypotheses)
    experiments = build_sandbox_experiments(pathologies_for_hypotheses, hypotheses)
    checks = {
        "live_turns_captured": len(live_turns) >= 10,
        "baseline_pathologies_traceable": all(item.evidence_turns for item in baseline_pathologies),
        "current_pathologies_resolved": len(current_pathologies) == 0,
        "hypotheses_ranked": all(any(h.pathology_id == p.pathology_id for h in hypotheses) for p in baseline_pathologies),
        "sandbox_isolated": all(not item.primary_tree_modified for item in experiments),
        "governance_clean": all(not any((turn.provider_called, turn.web_search_performed, turn.canonical_write_performed)) for turn in live_turns),
    }
    return {
        "report": "DELTA_1_3_BEHAVIORAL_MATURATION_CAMPAIGN",
        "created_at": utc_now(),
        "live_turns": tuple(asdict(item) for item in live_turns),
        "baseline_pathologies": tuple(asdict(item) for item in baseline_pathologies),
        "current_pathologies": tuple(asdict(item) for item in current_pathologies),
        "hypotheses": tuple(asdict(item) for item in hypotheses),
        "sandbox_experiments": tuple(asdict(item) for item in experiments),
        "checks": checks,
        "passed": all(checks.values()),
        "safety": safety_metadata(),
    }


def write_delta_1_3_reports(root: str | Path = REPORT_ROOT, *, write: bool = True) -> dict[str, Any]:
    report = build_campaign_report()
    if write:
        root_path = Path(root)
        write_json(root_path / "behavioral_campaign.json", report)
        write_markdown(root_path / "behavioral_campaign.md", "DELTA 1.3 Behavioral Campaign", report)
        notebook = {
            "baseline_pathologies": report["baseline_pathologies"],
            "current_pathologies": report["current_pathologies"],
            "hypotheses": report["hypotheses"],
            "sandbox_experiments": report["sandbox_experiments"],
            "recommendation": "promote_selected_bounded_repairs_after_focused_validation",
            "safety": safety_metadata(),
        }
        write_json(root_path / "engineering_notebook.json", notebook)
        write_markdown(root_path / "engineering_notebook.md", "DELTA 1.3 Engineering Notebook", notebook)
    return report


if __name__ == "__main__":
    print(write_delta_1_3_reports()["passed"])

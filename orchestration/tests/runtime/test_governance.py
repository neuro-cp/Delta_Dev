from dataclasses import replace
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from knowledge import (
    ContradictionEngine, PredictionEngine, SemanticConsolidationEngine, SemanticKnowledgeStore,
)
from knowledge.bootstrap import KnowledgeBootstrapper
from learning.region import LearningStore
from learning.region.learning_record import LearningRecord, SemanticCandidate
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from orchestration.agency import GoalStore, PlanStore
from orchestration.cycle import CognitiveCycle
from orchestration.runtime import CognitiveRuntime
from orchestration.simulation import SimulationRegion
from tools.delta_cli import build_loop
from tools.runtime_report import write_first_runtime_report


@pytest.fixture
def state(tmp_path):
    s = SimpleNamespace(
        memory=MemoryStore(tmp_path / "memory.jsonl"),
        knowledge=SemanticKnowledgeStore(tmp_path / "knowledge.jsonl"),
        predictions=PredictionEngine(tmp_path / "predictions.jsonl"),
        relationships=RelationshipStore(tmp_path / "relationships.jsonl"),
        learning=LearningStore(tmp_path / "learning.jsonl"),
        contradictions=ContradictionEngine(tmp_path / "contradictions.jsonl"),
        goals=GoalStore(tmp_path / "goals.jsonl"),
        plans=PlanStore(tmp_path / "plans.jsonl"),
        events=tmp_path / "events.jsonl",
        loop=build_loop("mock", enable_recall=False, enable_replay_prompt=False),
    )
    s.runtime = CognitiveRuntime(
        loop=s.loop, memory_store=s.memory, relationship_store=s.relationships,
        semantic_store=s.knowledge, learning_store=s.learning,
        prediction_engine=s.predictions, contradiction_engine=s.contradictions,
        goal_store=s.goals, event_path=s.events,
    )
    return s


def seed(s):
    return KnowledgeBootstrapper(
        semantic_store=s.knowledge, memory_store=s.memory,
        prediction_engine=s.predictions, goal_store=s.goals,
    ).seed()


def outcome(s, prediction, status="supported", source="operator"):
    return s.memory.add(
        text="Independent measured outcome.", kind="prediction_outcome", source=source,
        metadata={"prediction_id": prediction.prediction_id, "outcome": status,
                  "validation_source": "controlled fixture"},
    )


def claim(s, text, *, kind="claim", evidence=None):
    memory = s.memory.add(text=text, source="operator")
    record = LearningRecord(
        learning_id=memory.memory_id, created_at=memory.created_at, cycle_id="fixture",
        semantic_candidates=[SemanticCandidate(
            text=text, evidence_memory_ids=[memory.memory_id] if evidence is None else evidence,
            confidence=.8, rationale="explicit fixture claim", kind=kind,
        )],
    )
    return SemanticConsolidationEngine(
        semantic_store=s.knowledge, contradiction_engine=s.contradictions,
    ).consolidate([record])


def test_bootstrap_cannot_validate_its_own_predictions(state):
    seed(state)
    before = state.predictions.path.read_bytes()
    assert state.predictions.validate_against_observations(state.memory.all()) == []
    assert state.predictions.path.read_bytes() == before
    assert state.runtime._self_model().generate().metrics["prediction_accuracy"] is None


def test_plain_text_and_internal_outputs_are_not_outcome_evidence(state):
    seed(state)
    prediction = state.predictions.latest()[0]
    text = state.memory.add(text=prediction.expectation, kind="observation")
    internal = outcome(state, prediction, source="delta:llm")
    assert state.predictions.validate_against_observations([text, internal]) == []


@pytest.mark.parametrize("status", ["supported", "failed"])
def test_outcome_is_append_only_idempotent_and_preserves_forecast(state, status):
    seed(state)
    prediction = state.predictions.latest()[0]
    before = state.predictions.path.read_bytes()
    observed = outcome(state, prediction, status)
    revisions = state.predictions.validate_against_observations([observed])
    assert len(revisions) == 1
    revised = revisions[0]
    assert revised.status == status
    assert revised.created_at == prediction.created_at
    assert revised.confidence == prediction.confidence
    assert state.predictions.path.read_bytes().startswith(before)
    assert state.predictions.validate_against_observations([observed]) == []
    snapshot = state.runtime._self_model().generate()
    assert snapshot.predictions["total"] == 16
    assert snapshot.predictions["validated"] == 1
    assert snapshot.predictions["accuracy"] == (1.0 if status == "supported" else 0.0)


@pytest.mark.parametrize("case", ["older", "same_time", "unknown_id", "no_source", "bad_time", "seed_evidence"])
def test_invalid_evidence_does_not_close_predictions(state, case):
    seed(state)
    p = state.predictions.latest()[0]
    obs = outcome(state, p)
    if case == "older":
        obs = replace(obs, created_at=(datetime.fromisoformat(p.created_at) - timedelta(days=1)).isoformat())
    elif case == "same_time":
        obs = replace(obs, created_at=p.created_at)
    elif case == "unknown_id":
        obs = replace(obs, metadata={**obs.metadata, "prediction_id": "unknown"})
    elif case == "no_source":
        obs = replace(obs, metadata={**obs.metadata, "validation_source": ""})
    elif case == "bad_time":
        obs = replace(obs, created_at="invalid")
    else:
        obs = replace(obs, memory_id=p.metadata["source_evidence_ids"][0])
    assert state.predictions.validate_against_observations([obs]) == []


def test_conflicting_outcomes_remain_open_regardless_of_order(state):
    seed(state)
    p = state.predictions.latest()[0]
    observations = [outcome(state, p), outcome(state, p, "failed")]
    assert state.predictions.validate_against_observations(observations) == []
    assert state.predictions.validate_against_observations(observations[::-1]) == []


def test_legacy_lexical_support_is_not_accuracy(state):
    seed(state)
    p = state.predictions.latest()[0]
    state.predictions.add_all([replace(p, status="supported", supporting_observations=["old"],
                                      metadata={"validation": "token_overlap"})])
    snapshot = state.runtime._self_model().generate()
    assert snapshot.predictions["accuracy"] is None
    assert snapshot.predictions["unverified_terminal"] == 1
    assert "historical prediction outcomes lack explicit validation" in snapshot.cognitive_health["warnings"]


def test_failed_prediction_does_not_support_simulation(state):
    seed(state)
    p = state.predictions.latest()[0]
    state.predictions.validate_against_observations([outcome(state, p, "failed")])
    result = SimulationRegion().simulate(options=[p.expectation], predictions=state.predictions.latest())
    assert p.prediction_id not in result.outcomes[0].supporting_prediction_ids


def test_contradiction_and_role_reversal_are_distinct_claims(state):
    base = "The system can maintain stable operation under heavy load during extended runtime experiments."
    claim(state, base)
    result = claim(state, base.replace("can maintain", "can not maintain"))
    assert len(result["created"]) == 1
    assert len(result["contradictions"]) == 1
    assert len(state.knowledge.latest()) == 2
    claim(state, "Alice follows Bob")
    assert state.knowledge.find_equivalent("Bob follows Alice") is None
    assert claim(state, "  alice   follows bob ")["created"] == []


def test_related_claim_does_not_supersede_prior_claim(state):
    claim(state, "The system can maintain stable operation under heavy load during extended runtime experiments.")
    claim(state, "The system can maintain predictable operation under normal load during extended runtime experiments.")
    assert len(state.knowledge.latest()) == 2
    assert all(not r.revision_history for r in state.knowledge.latest())


@pytest.mark.parametrize("kind,evidence", [("context_relevance", None), ("unreviewed", None), ("claim", [])])
def test_unreviewed_and_ungrounded_candidates_are_not_promoted(state, kind, evidence):
    assert claim(state, "A claim needs evidence.", kind=kind, evidence=evidence)["created"] == []


def test_new_evidence_promotes_and_outcomes_survive_restart(state):
    first = claim(state, "Fixture switch is closed.")["created"][0]
    second = claim(state, "Fixture lamp is illuminated.")["created"][0]
    predictions = [state.predictions.generate_for(r) for r in (first, second)]
    state.predictions.add_all(predictions)
    assessments = [outcome(state, predictions[0]), outcome(state, predictions[1], "failed")]
    state.predictions.validate_against_observations(assessments)
    reopened = PredictionEngine(state.predictions.path)
    assert [r.status for r in reopened.latest()] == ["supported", "failed"]
    assert len(reopened.all()) == 4
    assert reopened.validate_against_observations(assessments) == []
    assert state.runtime._self_model().generate().metrics["prediction_accuracy"] == .5
    assert not claim(state, "Fixture lamp is illuminated.")["created"]
    assert len(state.knowledge.latest()) == 2


def test_stability_harness_is_isolated_and_checks_observed_state(tmp_path):
    from tools.delta_stability import run_experiment

    result = run_experiment(tmp_path / "isolated", 3)
    assert all(result["checks"].values())
    assert result["prediction_accuracy"] is None
    with pytest.raises(FileExistsError):
        run_experiment(tmp_path / "isolated", 3)


def test_completed_prediction_does_not_reappear_in_working_context(state):
    seed(state)
    p = state.predictions.latest()[0]
    state.predictions.validate_against_observations([outcome(state, p)])
    captured = []
    original = state.loop.run
    def capture(payload):
        captured.extend(payload["working_memory"])
        return original(payload)
    state.loop.run = capture
    CognitiveCycle(loop=state.loop, memory_store=state.memory,
                   prediction_engine=state.predictions).run("Inspect context")
    assert p.prediction_id not in [i["key"] for i in captured]


def test_runtime_snapshot_and_provenance_are_post_tick(state):
    seed(state)
    result = state.runtime.tick(tick_index=1)
    assert result.self_model["experience_count"] == len(state.memory.all())
    assert result.self_model["semantic_knowledge_count"] == len(state.knowledge.latest())
    assert result.metadata["snapshot_phase"] == "post_tick"
    assert result.metadata["duration_seconds"] >= 0
    observation = state.memory.all()[-2]
    assert observation.source == "delta:runtime"
    assert len(state.knowledge.all()) == 16


def test_counted_scheduler_does_not_use_expired_duration_for_sleep(state, monkeypatch):
    clock = iter([0, 2, 3, 4])
    monkeypatch.setattr("orchestration.runtime.cognitive_runtime.time.monotonic", lambda: next(clock))
    monkeypatch.setattr(state.runtime, "tick", lambda **kwargs: kwargs["tick_index"])
    sleeps = []
    monkeypatch.setattr("orchestration.runtime.cognitive_runtime.time.sleep", sleeps.append)
    assert state.runtime.run(duration_seconds=1, interval_seconds=1, max_ticks=2) == [1, 2]
    assert sleeps == [1]
    assert state.runtime.run(duration_seconds=1, max_ticks=0) == []


def test_reports_count_current_predictions_and_preserve_first_report(state, tmp_path):
    seed(state)
    p = state.predictions.latest()[0]
    state.predictions.validate_against_observations([outcome(state, p)])
    (tmp_path / "docs").mkdir()
    first = tmp_path / "docs" / "FIRST_RUNTIME_REPORT.md"
    first.write_text("historical evidence", encoding="utf-8")
    report = write_first_runtime_report(
        root=tmp_path, memory=state.memory, relationships=state.relationships,
        learning=state.learning, knowledge=state.knowledge, contradictions=state.contradictions,
        predictions=state.predictions, goals=state.goals, plans=state.plans, event_path=state.events,
    )
    text = report.read_text(encoding="utf-8")
    assert "predictions made: 16" in text
    assert "predictions validated: 1" in text
    assert "prediction history rows: 17" in text
    assert first.read_text(encoding="utf-8") == "historical evidence"


def test_console_reports_recorded_agency_without_creating_new_proposals(state, tmp_path, monkeypatch):
    import tools.delta_console as console

    monkeypatch.setattr(console, "ROOT", tmp_path)
    assert console._state()["latest_agency"] is None
    seed(state)
    tick = state.runtime.tick(tick_index=1)
    events = tmp_path / "data" / "runtime" / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_bytes(state.events.read_bytes())
    first = console._state()["latest_agency"]
    second = console._state()["latest_agency"]
    assert first == second == tick.agency


def test_model_escalation_preserves_advisory_context():
    from integration.ai_surface.ai_output_bundle import AIOutputBundle
    from integration.model_runtime.model_router import ModelRouter

    seen = []
    class Runner:
        def __init__(self, confidence):
            self.confidence = confidence

        def produce_output(self, payload):
            seen.append(dict(payload))
            return AIOutputBundle(role="assistant", mode="mock", confidence_band=self.confidence,
                                  payload={"raw_model_output": "fixture answer"})

    router = ModelRouter.__new__(ModelRouter)
    router.profile = "test"
    router.route_chain = ["first", "second"]
    router.confidence_threshold = .78
    router.runners = {"first": Runner(.2), "second": Runner(.9)}
    payload = {"question": "fixture", "working_memory": [{"key": "evidence"}],
               "attended_context": [{"memory_id": "m1"}], "cycle_id": "c1"}
    router.route(payload)
    assert len(seen) == 2
    assert all(seen[1][key] == value for key, value in payload.items())
    assert seen[1]["previous_model_output"] == "fixture answer"
    assert "previous_model_output" not in payload

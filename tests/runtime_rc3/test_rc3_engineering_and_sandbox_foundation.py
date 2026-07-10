from orchestration.runtime.rc3_engineering_benchmark import run_rc3_c_engineering_benchmark
from orchestration.runtime.rc3_engineering_foundation import (
    build_rc3_engineering_episode,
    classify_engineering_intent,
    get_capability_registry,
)
from orchestration.runtime.rc3_sandbox_benchmark import run_rc3_d_sandbox_benchmark
from orchestration.runtime.rc3_sandbox_foundation import build_rc3_sandbox_episode


def test_engineering_intent_classifier_classifies_common_gap_types():
    assert classify_engineering_intent("propose a future plugin capability").primary_intent == "plugin"
    assert classify_engineering_intent("design sandbox requirements without running code").primary_intent == "sandbox_experiment"
    assert classify_engineering_intent("document the routing contract").primary_intent == "documentation"
    assert classify_engineering_intent("add benchmark coverage").primary_intent == "testing"


def test_capability_registry_is_observational():
    registry = get_capability_registry()
    assert registry
    assert all("activate" not in " ".join(item.permissions).lower() for item in registry)
    assert {item.identifier for item in registry} >= {"rc2.conversation", "rc3.goal_planning", "rc3.plan_revision"}


def test_engineering_episode_is_proposal_only_and_governed():
    episode = build_rc3_engineering_episode(
        "Propose how RC3 might support a plugin later, but do not create or activate plugins."
    )
    overlay = episode.developer_overlay
    proposal = overlay["engineering_proposal"]
    validation = overlay["proposal_validation"]
    comparison = overlay["proposal_comparison"]
    assert proposal["proposal_only"] is True
    assert proposal["implementation_included"] is False
    assert proposal["execution_authorized"] is False
    assert validation["result"] in ("valid", "valid_with_warnings")
    assert comparison["automatically_selected"] is False
    assert overlay["implementation_performed"] is False
    assert all(value is False for value in episode.safety.values())


def test_sandbox_episode_only_models_requirements():
    episode = build_rc3_sandbox_episode(
        "Design sandbox requirements for evaluating generated code someday. Do not create a sandbox or run code."
    )
    overlay = episode.developer_overlay
    proposal = overlay["sandbox_proposal"]
    validation = overlay["sandbox_validation"]
    assert proposal["proposal_only"] is True
    assert proposal["sandbox_created"] is False
    assert proposal["execution_authorized"] is False
    assert validation["result"] in ("valid", "valid_with_warnings")
    assert overlay["sandbox_created"] is False
    assert overlay["execution_authorized"] is False
    assert all(value is False for value in episode.safety.values())


def test_rc3_c_and_rc3_d_benchmarks_pass_without_actions(tmp_path):
    c_report = run_rc3_c_engineering_benchmark(write_reports=False)
    d_report = run_rc3_d_sandbox_benchmark(write_reports=False)
    assert c_report["overall"] >= 0.9
    assert d_report["overall"] >= 0.9
    assert c_report["safety_metadata_completeness"] == 1.0
    assert d_report["safety_metadata_completeness"] == 1.0

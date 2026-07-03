from __future__ import annotations

from orchestration.runtime.v15_knowledge_inventory import (
    KnowledgeInventoryCategory,
    build_runtime_knowledge_inventory,
    summarize_inventory,
    validate_inventory_non_mutating,
)
from orchestration.runtime.v15_knowledge_inventory_report import build_knowledge_inventory_report_data, write_knowledge_inventory_report


def test_inventory_is_deterministic_and_non_mutating():
    first = build_runtime_knowledge_inventory(".")
    second = build_runtime_knowledge_inventory(".")
    assert first.inventory_id == second.inventory_id
    assert validate_inventory_non_mutating(first)


def test_inventory_distinguishes_repo_local_from_learned_model_knowledge():
    inventory = build_runtime_knowledge_inventory(".")
    categories = {item.category for item in inventory.items}
    assert KnowledgeInventoryCategory.LEARNED_MODEL_KNOWLEDGE in categories
    assert KnowledgeInventoryCategory.REPO_LOCAL_SCAFFOLD_KNOWLEDGE in categories
    assert "No new learned model knowledge" in inventory.learned_model_knowledge_summary
    assert "Repo-local" in inventory.repo_local_knowledge_summary


def test_inventory_reports_active_and_inactive_capabilities_separately():
    inventory = build_runtime_knowledge_inventory(".")
    assert "manual runtime console message preview" in inventory.active_capabilities
    assert "provider calls" in inventory.inactive_capabilities
    assert "training/fine-tuning/weight updates" in inventory.inactive_capabilities
    assert "arbitrary world knowledge without provider/model integration" in inventory.unavailable_knowledge


def test_inventory_summary_denies_training_provider_hyb1_and_memory_mutation():
    inventory = build_runtime_knowledge_inventory(".")
    summary = summarize_inventory(inventory)
    assert summary["model_training_occurred"] is False
    assert summary["hyb1_promoted"] is False
    assert summary["provider_calls_occurred"] is False
    assert summary["memory_or_recall_mutation_occurred"] is False


def test_inventory_report_answers_required_questions():
    data = build_knowledge_inventory_report_data(".")
    answers = data["questions_answered"]
    assert answers["was_any_model_training_performed"] is False
    assert answers["was_hyb1_promoted"] is False
    assert "DELTA scaffold and phase history from repo-local reports" in answers["what_can_delta_answer_locally_without_provider_calls"]
    assert "provider calls" in answers["what_remains_disabled"]


def test_write_knowledge_inventory_report(tmp_path, monkeypatch):
    from orchestration.runtime import v15_knowledge_inventory_report as report_module

    md_path = tmp_path / "inventory.md"
    json_path = tmp_path / "inventory.json"
    monkeypatch.setattr(report_module, "REPORT_MD", md_path)
    monkeypatch.setattr(report_module, "REPORT_JSON", json_path)
    data = write_knowledge_inventory_report(".")
    text = md_path.read_text(encoding="utf-8")
    assert json_path.exists()
    assert data["final_recommendation"] == "PROCEED_WITH_CONSOLE_UI_REVIEW_OR_V15E_HYB1_LIMITED_OPT_IN_TRIAL_DESIGN"
    assert "Codex did not train model weights" in text
    assert "HYB1 remains dormant" in text

from orchestration.runtime.post_arc_xxv_deepening_runner import DEEPENING_MODULES, write_all_deepening_reports


def test_deepening_runner_covers_all_batches():
    assert len(DEEPENING_MODULES) == 120


def test_deepening_runner_writes_master_report_without_authority():
    summary = write_all_deepening_reports()
    assert summary["module_count"] == 120
    assert summary["by_batch"] == {"A": 30, "B": 30, "C": 30, "D": 30}
    assert summary["model_b_default"] == "unchanged"
    assert summary["hyb1"] == "dormant_env_gated"
    assert summary["training_performed"] is False
    assert summary["provider_authority_granted"] is False
    assert summary["autonomous_browsing_performed"] is False
    assert summary["tool_execution_performed"] is False
    assert summary["scheduler_started"] is False
    assert summary["memory_mutation_performed"] is False
    assert summary["knowledge_mutation_performed"] is False


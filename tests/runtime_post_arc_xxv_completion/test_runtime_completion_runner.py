from orchestration.runtime.post_arc_xxv_runtime_completion_runner import COMPLETION_MODULES, write_all_completion_reports


def test_runtime_completion_runner_covers_all_batches():
    assert len(COMPLETION_MODULES) == 210


def test_runtime_completion_runner_writes_master_report_without_authority():
    summary = write_all_completion_reports()
    assert summary["module_count"] == 210
    assert summary["by_batch"] == {"E": 35, "F": 35, "G": 35, "H": 35, "I": 35, "J": 35}
    assert summary["model_b_default"] == "unchanged"
    assert summary["hyb1"] == "dormant_env_gated"
    assert summary["training_performed"] is False
    assert summary["provider_authority_granted"] is False
    assert summary["autonomous_browsing_performed"] is False
    assert summary["tool_execution_performed"] is False
    assert summary["scheduler_started"] is False
    assert summary["memory_mutation_performed"] is False
    assert summary["knowledge_mutation_performed"] is False

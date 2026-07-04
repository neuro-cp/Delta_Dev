from orchestration.runtime.post_arc_xxv_exhaustive_runner import MODULES, write_all_reports


def test_post_arc_xxv_runner_covers_all_modules():
    assert len(MODULES) == 19


def test_post_arc_xxv_runner_writes_master_review_without_authority():
    summary = write_all_reports()
    assert summary["module_count"] == 19
    assert summary["model_b_default"] == "unchanged"
    assert summary["hyb1"] == "dormant_env_gated"
    assert summary["training_performed"] is False
    assert summary["provider_authority_granted"] is False
    assert summary["tool_execution_performed"] is False
    assert summary["scheduler_started"] is False
    assert summary["memory_mutation_performed"] is False
    assert summary["knowledge_mutation_performed"] is False

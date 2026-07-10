from orchestration.runtime.rc2_adversarial_routing_benchmark import build_adversarial_routing_report


def test_adversarial_routing_benchmark_meets_stabilization_floor():
    report = build_adversarial_routing_report(write_reports=False)
    assert report["case_count"] >= 16
    assert report["route_accuracy"] >= 0.9
    assert report["route_collision_accuracy"] >= 0.8
    assert report["branch_return_accuracy"] >= 0.8
    assert report["orphan_clarification_accuracy"] == 1.0
    assert report["safety_metadata_completeness"] == 1.0
    assert report["internal_leak_count"] == 0


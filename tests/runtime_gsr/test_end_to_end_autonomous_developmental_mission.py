from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

from orchestration.runtime.end_to_end_autonomous_developmental_mission import (
    compile_end_to_end_autonomous_developmental_mission,
    run_end_to_end_autonomous_developmental_mission,
    snapshot_trusted_formal_layer,
)


def _seed(path):
    labels = ("cause", "mechanism", "condition", "outcome", "constraint", "state", "transition", "uncertainty", "evidence", "claim")
    nodes = [
        {"primitive_id": f"id-{label}", "canonical_label": label, "status": "partially_formalized", "retained_support": [], "unresolved_obligations": ["source"]}
        for label in labels
    ]
    path.write_text(json.dumps({"package_digest": "seed-digest", "nodes": nodes}), encoding="utf-8")


def _trusted(path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE trusted_formal_primitives (primitive_id TEXT, canonical_label TEXT, admitted_status TEXT, admission_review_digest TEXT)")
        connection.execute("INSERT INTO trusted_formal_primitives VALUES ('id-anchor', 'anchor', 'admitted', 'review')")


class _Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, _): return self.body


def test_broad_mission_drives_live_discovery_retrieval_rerank_and_restart(tmp_path):
    seed = tmp_path / "seed.json"; trusted = tmp_path / "trusted.sqlite"; _seed(seed); _trusted(trusted)
    mission = compile_end_to_end_autonomous_developmental_mission(
        objective="Improve reasoning about causes, constraints, state changes, mechanisms, outcomes, uncertainty, and evidence.",
        seeding_package=seed,
        trusted_layer=trusted,
        maximum_frontiers=8,
        maximum_retrievals=4,
    )
    assert "frontier" not in mission

    calls = []
    def opener(request, timeout):
        calls.append(request.full_url)
        query = request.full_url.lower()
        title = "Cause" if "cause+definition" in query else "Mechanism"
        return _Response(json.dumps({"query": {"search": [{"title": title, "snippet": f"A {title.lower()} is defined within a stated scope."}]}}).encode())

    def rc8(request, *, env, policy):
        label = "cause" if request.target.endswith("/Cause") else "mechanism"
        if label == "mechanism":
            text = "A mechanism is defined here without a stated limitation."
        else:
            text = "A cause is a factor in a stated setting. A cause applies only when the stated setting holds."
        source = SimpleNamespace(source_id=f"source-{label}", sanitized_text=text, provenance=SimpleNamespace(url=request.target, provenance_id=f"prov-{label}"))
        return SimpleNamespace(bundle=SimpleNamespace(sources=(source,)), decision=SimpleNamespace(outcome="RETRIEVAL_PERMITTED"), failure_state="")

    result = run_end_to_end_autonomous_developmental_mission(mission=mission, workspace=tmp_path / "mission", opener=opener, rc8_executor=rc8)
    assert result["selected_frontiers"]
    assert result["self_authored_work_plans"]
    assert result["live_discovery"]["live_call_count"]
    assert calls and all("srsearch=" in call for call in calls)
    assert result["governed_retrieval_count"]
    assert "cause" in result["resolved_branches"]
    assert "mechanism" in result["blocked_branches"]
    assert result["final_package"]["trusted_admissions"] == result["capability_promotions"] == 0
    assert result["immutability"]["trusted_layer_unchanged"]
    assert result["immutability"]["rc2_unchanged"]
    replay = run_end_to_end_autonomous_developmental_mission(
        mission=mission,
        workspace=tmp_path / "mission",
        opener=lambda *_: (_ for _ in ()).throw(AssertionError("discovery replayed")),
        rc8_executor=lambda *_1, **_2: (_ for _ in ()).throw(AssertionError("retrieval replayed")),
    )
    assert replay["package_digest"] == result["package_digest"]


def test_trusted_snapshot_excludes_quarantined_or_noncanonical_rows(tmp_path):
    trusted = tmp_path / "trusted.sqlite"
    _trusted(trusted)
    with sqlite3.connect(trusted) as connection:
        connection.execute(
            "INSERT INTO trusted_formal_primitives VALUES (?, ?, ?, ?)",
            ("invalid-direct-row", "necessary_condition", "invalid_noncanonical_excluded", "failed-review"),
        )

    snapshot = snapshot_trusted_formal_layer(trusted)

    assert [item["canonical_label"] for item in snapshot["records"]] == ["anchor"]
    assert snapshot["excluded_records"] == ({
        "primitive_id": "invalid-direct-row",
        "canonical_label": "necessary_condition",
        "admitted_status": "invalid_noncanonical_excluded",
        "admission_review_digest": "failed-review",
        "reason": "trusted_status_not_active",
    },)

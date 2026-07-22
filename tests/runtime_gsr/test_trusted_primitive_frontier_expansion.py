from __future__ import annotations

import json
import sqlite3

from orchestration.runtime.trusted_primitive_frontier_expansion import compile_trusted_primitive_frontier_campaign, run_trusted_primitive_frontier_campaign


def _files(tmp_path):
    labels = ("object", "property", "relation", "state", "transition", "condition", "cause", "mechanism", "quantity", "claim", "evidence", "uncertainty", "outcome", "value", "type", "variable", "function", "time", "growth", "risk", "constraint", "interest")
    nodes = [{"primitive_id": f"id-{label}", "canonical_label": label, "status": "source_grounded" if label in {"constraint", "interest"} else "partially_formalized", "retained_support": [], "unresolved_obligations": ["source grounding required"]} for label in labels]
    seed = tmp_path / "seed.json"; seed.write_text(json.dumps({"execution_id": "seed", "package_digest": "digest", "nodes": nodes}))
    layer = tmp_path / "trusted.sqlite"
    with sqlite3.connect(layer) as conn:
        conn.executescript("CREATE TABLE trusted_formal_primitives (primitive_id TEXT PRIMARY KEY, canonical_label TEXT, scoped_definition TEXT, aliases_json TEXT, type_structure_json TEXT, relations_json TEXT, prerequisites_json TEXT, examples_json TEXT, counterexamples_json TEXT, source_references_json TEXT, construction_digest TEXT, validation_digest TEXT, independent_use_digest TEXT, admission_review_digest TEXT, admitted_status TEXT, admitted_at TEXT, admission_authority_id TEXT, version INTEGER, supersession_state TEXT, unresolved_nonblocking_limits_json TEXT);")
        for label in ("constraint", "interest"):
            conn.execute("INSERT INTO trusted_formal_primitives VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (f"id-{label}", label, label, "[]", "[]", "[]", "[]", "[]", "[]", "[]", "c", "v", "u", "r", "admitted", "now", "a", 1, "current", "[]"))
    return seed, layer


def test_frontier_reuses_exact_anchors_and_defers_partial_nodes(tmp_path):
    seed, layer = _files(tmp_path); campaign = compile_trusted_primitive_frontier_campaign(seeding_package=seed, trusted_layer=layer)
    result = run_trusted_primitive_frontier_campaign(campaign=campaign, seeding_package=seed, trusted_layer=layer, workspace=tmp_path / "work")
    assert result["trusted_anchors"]["constraint"]["primitive_id"] == "id-constraint"
    assert result["status"] == "deferred_no_source_grounded_frontier_candidates"
    assert result["admission_authority"] is None
    assert result["provider_calls"] == result["external_retrievals"] == result["capability_promotions"] == 0
    assert all("evaluator" not in item["learner_view"] for item in result["fresh_exercises"])


def test_frontier_restarts_without_duplicate_bindings(tmp_path):
    seed, layer = _files(tmp_path); campaign = compile_trusted_primitive_frontier_campaign(seeding_package=seed, trusted_layer=layer)
    first = run_trusted_primitive_frontier_campaign(campaign=campaign, seeding_package=seed, trusted_layer=layer, workspace=tmp_path / "work")
    second = run_trusted_primitive_frontier_campaign(campaign=campaign, seeding_package=seed, trusted_layer=layer, workspace=tmp_path / "work")
    assert first["execution_id"] == second["execution_id"]
    assert len(first["bindings"]) == len({item["binding_id"] for item in first["bindings"]})

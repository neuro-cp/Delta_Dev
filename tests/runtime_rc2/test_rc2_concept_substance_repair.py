from __future__ import annotations

import json

from orchestration.runtime.rc2_concept_substance_repair import repair_concept_substance


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_concept_substance_repair_preserves_identity_and_safety(tmp_path):
    store = tmp_path / "knowledge_concepts.jsonl"
    _write_jsonl(store, [
        {
            "concept_id": "concept-cellular-respiration",
            "concept_name": "Cellular Respiration (Biology)",
            "short_definition": "Cellular Respiration is a reusable biology concept that helps explain causes, constraints, tradeoffs, and practical decisions in the biology domain.",
            "propositions": ["Cellular Respiration connects observable situations to underlying biology principles."],
            "examples": [],
            "misconceptions": [],
            "related_concepts": ["biology reasoning", "biology evidence"],
            "approval_status": "approved_noncanonical",
            "canonical": False,
            "rollback_handle": "rollback-cellular-respiration",
            "training_performed": False,
            "provider_calls_performed": False,
        }
    ])

    report = repair_concept_substance(store)
    rows = _read_jsonl(store)
    repaired = rows[0]

    assert report["repaired_count"] == 1
    assert repaired["concept_id"] == "concept-cellular-respiration"
    assert repaired["rollback_handle"] == "rollback-cellular-respiration"
    assert repaired["canonical"] is False
    assert repaired["training_performed"] is False
    assert repaired["provider_calls_performed"] is False
    assert repaired["quality_repair_reason"] == "rc2_5a_concept_substance_repair"
    assert "process cells use to release usable energy" in repaired["short_definition"]
    assert len(repaired["propositions"]) >= 3
    assert repaired["examples"]
    assert repaired["misconceptions"]
    assert repaired["substance_repair_version_handle"].startswith("rc2-5a-substance-repair-")


def test_concept_substance_repair_skips_already_substantive(tmp_path):
    store = tmp_path / "knowledge_concepts.jsonl"
    _write_jsonl(store, [
        {
            "concept_id": "concept-cellular-respiration",
            "concept_name": "Cellular Respiration (Biology)",
            "short_definition": "Cellular respiration is the process cells use to release usable energy from sugars by converting glucose and oxygen into carbon dioxide, water, and ATP.",
            "propositions": [
                "Cellular respiration converts stored chemical energy into ATP.",
                "Cellular respiration commonly uses glucose and oxygen as inputs.",
                "Cellular respiration produces carbon dioxide, water, and usable cellular energy.",
            ],
            "examples": ["Muscle cells using glucose and oxygen to produce ATP during activity."],
            "misconceptions": ["Cellular respiration is not the same process as breathing."],
            "related_concepts": ["ATP", "glucose", "oxygen", "photosynthesis"],
            "approval_status": "approved_noncanonical",
            "canonical": False,
            "rollback_handle": "rollback-cellular-respiration",
            "training_performed": False,
            "provider_calls_performed": False,
        }
    ])

    report = repair_concept_substance(store)

    assert report["repaired_count"] == 0
    assert report["skipped_count"] == 1
    assert report["skipped"][0]["reason"] == "already_substantive"

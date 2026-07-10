"""Targeted RC2 concept substance repair for high-use concepts.

This pass repairs existing SQLite concept records so WRS has factual
propositions to reason over instead of generic governance scaffolding. It is
not concept growth, training, provider use, canonical mutation, or graph
mutation. JSONL source stores are not edited.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime import rc2_sqlite_substrate as sqlite_backend


REPORT_JSON = ROOT / "reports" / "RC2_CONCEPT_SUBSTANCE_REPAIR.json"
REPORT_MD = ROOT / "reports" / "RC2_CONCEPT_SUBSTANCE_REPAIR.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "new_concepts_created": False,
    "graph_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "jsonl_source_store_mutated": False,
    "delta_75_push_performed": False,
}


CORE_REPAIRS: dict[str, dict[str, Any]] = {
    "blood pressure": {
        "concept_name": "Blood Pressure (Medicine Health General)",
        "domain": "medicine health general",
        "definition": "Blood pressure is the force exerted by circulating blood against artery walls, usually measured as systolic pressure over diastolic pressure.",
        "propositions": [
            "Blood pressure is measured as systolic pressure during heart contraction and diastolic pressure during heart relaxation.",
            "Blood pressure reflects cardiac output, vascular resistance, blood volume, and short-term physiological state.",
            "Blood pressure can vary with posture, activity, stress, pain, medication, illness, and measurement conditions.",
            "A single blood pressure reading is not enough to define cardiovascular status without context and repeated measurement.",
        ],
        "related": ["systolic pressure", "diastolic pressure", "vascular resistance", "cardiac output", "blood volume", "health monitoring"],
        "examples": ["A reading of 120/80 mmHg records systolic and diastolic pressure."],
        "misconceptions": ["Blood pressure is not a complete diagnosis by itself."],
    },
    "allergies": {
        "concept_name": "Allergies (Medicine Health General)",
        "domain": "medicine health general",
        "definition": "Allergies are immune responses to substances that the body treats as harmful allergens.",
        "propositions": [
            "Allergies involve immune reactivity to allergens such as foods, medications, insect stings, latex, or environmental exposures.",
            "Allergy severity can range from mild symptoms to severe systemic reactions such as anaphylaxis.",
            "A history of severe allergies can constrain medication choices, diagnostic procedures, and emergency planning.",
            "Clinical reasoning about allergies requires knowing the trigger, reaction type, severity, timing, and prior treatment.",
        ],
        "related": ["immune response", "allergen", "anaphylaxis", "medication safety", "clinical history", "exposure"],
        "examples": ["A penicillin allergy can affect antibiotic selection."],
        "misconceptions": ["All medication side effects are not automatically allergies."],
    },
    "photosynthesis": {
        "concept_name": "Photosynthesis (Biology)",
        "domain": "biology",
        "definition": "Photosynthesis is the process by which plants, algae, and some bacteria use light energy to make chemical energy from carbon dioxide and water.",
        "propositions": [
            "Photosynthesis uses light energy to convert carbon dioxide and water into sugars and oxygen.",
            "Chlorophyll and chloroplasts help capture light energy in many photosynthetic organisms.",
            "Photosynthesis stores energy in chemical bonds that can later support cellular work or food webs.",
            "Photosynthesis depends on light, carbon dioxide, water availability, pigments, and cellular structures.",
        ],
        "related": ["light energy", "chlorophyll", "chloroplasts", "carbon dioxide", "glucose", "oxygen", "energy storage"],
        "examples": ["A plant leaf uses sunlight to produce sugars from carbon dioxide and water."],
        "misconceptions": ["Photosynthesis is not the same process as cellular respiration."],
    },
    "cellular respiration": {
        "concept_name": "Cellular Respiration (Biology)",
        "domain": "biology",
        "definition": "Cellular respiration is the process cells use to release usable energy from organic molecules, commonly producing ATP.",
        "propositions": [
            "Cellular respiration breaks down glucose or other fuel molecules to produce ATP for cellular work.",
            "Aerobic cellular respiration uses oxygen and produces carbon dioxide and water as major outputs.",
            "Cellular respiration releases energy that photosynthesis helped store in chemical form.",
            "Cellular respiration depends on fuel availability, oxygen conditions, enzymes, and cellular structures such as mitochondria in eukaryotes.",
        ],
        "related": ["ATP", "glucose", "oxygen", "carbon dioxide", "mitochondria", "energy release", "metabolism"],
        "examples": ["Muscle cells use cellular respiration to produce ATP during activity."],
        "misconceptions": ["Cellular respiration is not simply breathing, although breathing supplies oxygen and removes carbon dioxide."],
    },
    "inflation": {
        "concept_name": "Inflation (Finance)",
        "domain": "finance",
        "definition": "Inflation is a sustained increase in the general price level of goods and services, reducing purchasing power over time.",
        "propositions": [
            "Inflation means prices generally rise across an economy rather than one isolated price increasing.",
            "Inflation reduces purchasing power when incomes or savings do not rise at the same pace.",
            "Inflation can be influenced by demand, supply shocks, expectations, money conditions, and production costs.",
            "Inflation interpretation depends on time period, measurement index, sector, and policy context.",
        ],
        "related": ["price level", "purchasing power", "consumer price index", "monetary policy", "supply shock", "demand"],
        "examples": ["If prices rise broadly while wages stay flat, purchasing power falls."],
        "misconceptions": ["One expensive item is not by itself economy-wide inflation."],
    },
    "interest rates": {
        "concept_name": "Interest Rates (Finance)",
        "domain": "finance",
        "definition": "Interest rates are the cost of borrowing money or the return paid for lending or saving money, usually expressed as a percentage over time.",
        "propositions": [
            "Interest rates influence borrowing costs for consumers, businesses, and governments.",
            "Higher interest rates can reduce borrowing and spending, while lower rates can encourage them.",
            "Interest rates can affect inflation, asset prices, savings behavior, and investment decisions.",
            "Interest rate interpretation depends on inflation expectations, credit risk, maturity, and central-bank policy.",
        ],
        "related": ["borrowing cost", "saving", "central bank", "monetary policy", "credit risk", "investment"],
        "examples": ["A higher mortgage rate increases the monthly cost of financing a home."],
        "misconceptions": ["The nominal interest rate is not the same as the inflation-adjusted real interest rate."],
    },
    "gravity": {
        "concept_name": "Gravity (Basic Physics)",
        "domain": "basic physics",
        "definition": "Gravity is the attractive interaction associated with mass and energy, commonly observed as objects accelerating toward one another.",
        "propositions": [
            "Gravity pulls masses toward one another and gives weight to objects near a planet or moon.",
            "Near Earth's surface, gravity causes falling objects to accelerate downward when other forces are ignored.",
            "Gravity can provide the inward acceleration that keeps orbiting objects following curved paths.",
            "Gravitational effects depend on mass, distance, and the frame or theory used to describe motion.",
        ],
        "related": ["mass", "weight", "acceleration", "orbit", "force", "curved path"],
        "examples": ["An apple falls because Earth's gravity accelerates it downward."],
        "misconceptions": ["Objects in orbit are not free from gravity; they are continually falling around the body they orbit."],
    },
    "orbital motion": {
        "concept_name": "Orbital Motion (Basic Physics)",
        "domain": "basic physics",
        "definition": "Orbital motion is curved motion around a body caused by the combination of forward velocity and gravitational influence.",
        "propositions": [
            "Orbital motion occurs when an object has enough sideways velocity to keep falling around another body rather than straight down into it.",
            "Gravity provides the inward acceleration that continuously changes the direction of an orbiting object's motion.",
            "Orbital motion depends on mass, distance, velocity, and energy.",
            "Stable orbital motion is a relationship between motion and gravitational constraint, not the absence of gravity.",
        ],
        "related": ["gravity", "velocity", "centripetal acceleration", "orbit", "mass", "distance", "energy"],
        "examples": ["A satellite remains in orbit by continually falling around Earth while moving forward."],
        "misconceptions": ["Astronauts in orbit are not outside gravity; they are in continuous free fall."],
    },
    "feedback loops": {
        "concept_name": "Feedback Loops (Planning Productivity)",
        "domain": "planning productivity",
        "definition": "Feedback loops are cycles where outcomes are compared with goals so behavior or plans can be adjusted.",
        "propositions": [
            "A feedback loop compares actual results with an intended goal or reference state.",
            "Negative feedback can stabilize a system by reducing deviation from a target.",
            "Positive feedback can amplify change and may accelerate growth or instability.",
            "Feedback quality depends on timely, relevant, and interpretable signals.",
        ],
        "related": ["control", "measurement", "course correction", "stability", "positive feedback", "negative feedback"],
        "examples": ["A thermostat uses feedback to compare room temperature with a set point."],
        "misconceptions": ["Feedback is not useful if it arrives too late or measures the wrong signal."],
    },
    "planning": {
        "concept_name": "Planning (Planning Productivity)",
        "domain": "planning productivity",
        "definition": "Planning is the process of choosing goals, steps, resources, constraints, and checkpoints before or during action.",
        "propositions": [
            "Planning defines intended outcomes and the steps expected to reach them.",
            "Planning depends on constraints such as time, resources, priorities, risk, and dependencies.",
            "Good planning includes checkpoints so feedback can revise the plan when conditions change.",
            "Planning is stronger when assumptions and uncertainty are made explicit.",
        ],
        "related": ["goals", "steps", "resources", "constraints", "dependencies", "feedback loops"],
        "examples": ["A project plan lists milestones, owners, risks, and review points."],
        "misconceptions": ["A plan is not proof that the outcome will happen unchanged."],
    },
    "memory consolidation": {
        "concept_name": "Memory Consolidation (Psychology)",
        "domain": "psychology",
        "definition": "Memory consolidation is the process by which newly acquired information becomes more stable and integrated over time.",
        "propositions": [
            "Memory consolidation can stabilize fragile new memories after learning or experience.",
            "Consolidation often depends on repetition, sleep, retrieval, emotional salience, and existing knowledge structures.",
            "Consolidated memories can still change when recalled and updated with new context.",
            "Memory consolidation links short-term experience to longer-term organization.",
        ],
        "related": ["learning", "sleep", "retrieval", "long-term memory", "integration", "reconsolidation"],
        "examples": ["Practicing and sleeping after study can improve later recall."],
        "misconceptions": ["Consolidated memories are not perfect recordings."],
    },
    "noncanonical memory": {
        "concept_name": "Noncanonical Memory (Delta Architecture Itself)",
        "domain": "delta architecture itself",
        "definition": "Noncanonical memory is reversible, reviewable knowledge that DELTA may use locally without treating it as permanent canonical truth.",
        "propositions": [
            "Noncanonical memory stores approved but provisional knowledge outside canonical records.",
            "Noncanonical memory is useful for reversible learning, operator review, rollback, and experimentation.",
            "Noncanonical memory should preserve provenance, uncertainty, approval status, and rollback handles.",
            "Noncanonical memory can inform retrieval and reasoning while remaining eligible for correction or removal.",
        ],
        "related": ["operator review", "rollback", "provenance", "canonical memory", "substrate learning", "reversible knowledge"],
        "examples": ["A useful conversation concept can be kept noncanonically before any canonical promotion decision."],
        "misconceptions": ["Noncanonical memory is not model training and is not permanent truth."],
    },
}


# The current pass is intentionally narrow: it repairs only the high-use WRS
# concepts needed for the local synthesis probes. Earlier RC2 substance work
# also covered these broader domains. Keep this manifest here so that narrowing
# this script does not erase the next repair frontier from the codebase.
BROAD_REPAIR_TARGET_ARCHIVE: dict[str, list[str]] = {
    "biology_energy": [
        "Energy Storage (Energy)",
        "Thermal Storage (Energy)",
        "Plant Growth (Biology)",
        "Carbon Cycle (Biology)",
    ],
    "finance": [
        "Asset Allocation (Finance)",
        "Balance Sheets (Finance)",
        "Compound Interest (Finance)",
        "Monetary Policy (Finance)",
    ],
    "delta_memory": [
        "Canonical Memory (Delta Architecture Itself)",
        "Operator Approval (Delta Architecture Itself)",
        "Rollback (Delta Architecture Itself)",
        "Developmental Learning (Delta Architecture Itself)",
    ],
    "psychology_communication": [
        "Active Listening (Psychology)",
        "Active Listening (Social Communication)",
        "Attachment (Psychology)",
        "Conflict Resolution (Psychology)",
    ],
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _backup_sqlite(db_path: Path) -> Path:
    backup_path = db_path.with_name(f"{db_path.stem}.pre_substance_repair_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}{db_path.suffix}")
    source = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()
    return backup_path


def _loads(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def repair_concept_substance(store_path: Path) -> dict[str, Any]:
    """Repair generic JSONL concepts in a caller-provided store.

    This compatibility helper is intentionally path-scoped for tests and small
    operator utilities. It does not touch SQLite, canonical memory, providers,
    training, graph records, or replay.
    """
    rows = []
    for line in store_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    repaired = []
    skipped = []
    output = []
    for row in rows:
        target = _jsonl_repair_target(row)
        if not target:
            skipped.append({"concept_id": row.get("concept_id"), "reason": "already_substantive"})
            output.append(row)
            continue
        spec = CORE_REPAIRS[target]
        updated = {
            **row,
            "concept_name": row.get("concept_name") or spec["concept_name"],
            "short_definition": spec["definition"],
            "propositions": spec["propositions"],
            "related_concepts": spec["related"],
            "examples": spec["examples"],
            "misconceptions": spec["misconceptions"],
            "quality_repair_reason": "rc2_5a_concept_substance_repair",
            "substance_repair_version_handle": f"rc2-5a-substance-repair-{row.get('concept_id', target).replace(' ', '-')}",
            "training_performed": False,
            "provider_calls_performed": False,
            "canonical": False,
        }
        repaired.append({"concept_id": updated.get("concept_id"), "target": target, "reason": "generic_scaffold_repaired"})
        output.append(updated)
    store_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in output) + ("\n" if output else ""), encoding="utf-8")
    return {
        "report": "RC2_CONCEPT_SUBSTANCE_REPAIR_JSONL_COMPAT",
        "created_at": _now(),
        "store_path": str(store_path),
        "repaired_count": len(repaired),
        "skipped_count": len(skipped),
        "repaired": repaired,
        "skipped": skipped,
        "safety": {
            **SAFETY,
            "jsonl_source_store_mutated": True,
            "jsonl_mutation_scope": "caller_provided_store_path_only",
        },
    }


def _jsonl_repair_target(row: dict[str, Any]) -> str | None:
    name = str(row.get("concept_name") or "").lower()
    definition = str(row.get("short_definition") or "").lower()
    propositions = " ".join(str(item) for item in row.get("propositions") or []).lower()
    generic = any(phrase in f"{definition} {propositions}" for phrase in (
        "reusable",
        "causes, constraints, tradeoffs",
        "connects observable situations",
        "underlying biology principles",
    ))
    if not generic:
        return None
    for target in CORE_REPAIRS:
        if target in name:
            return target
    return None


def _select_repair_row(conn: sqlite3.Connection, target: str) -> sqlite3.Row | None:
    spec = CORE_REPAIRS[target]
    exact = conn.execute(
        "SELECT * FROM concepts WHERE lower(concept_name) = lower(?) ORDER BY quality_score DESC LIMIT 1",
        (spec["concept_name"],),
    ).fetchone()
    if exact:
        return exact
    words = target.split()
    clauses = " AND ".join("lower(concept_name) LIKE ?" for _ in words)
    rows = list(conn.execute(
        f"SELECT * FROM concepts WHERE {clauses} ORDER BY quality_score DESC, concept_name LIMIT 12",
        tuple(f"%{word}%" for word in words),
    ))
    if not rows:
        return None
    preferred = sorted(rows, key=lambda row: (
        1 if any(term in str(row["concept_name"]).lower() for term in ("abstraction", "design pattern", "competency test", "evidence chain")) else 0,
        -float(row["quality_score"] or 0.0),
        len(str(row["concept_name"])),
    ))
    return preferred[0]


def _repair_concept(conn: sqlite3.Connection, row: sqlite3.Row, target: str) -> dict[str, Any]:
    spec = CORE_REPAIRS[target]
    raw = _loads(row["raw_json"])
    concept = {
        **raw,
        "concept_id": row["concept_id"],
        "concept_name": spec["concept_name"],
        "domain": spec["domain"],
        "concept_type": "core_factual_concept",
        "short_definition": spec["definition"],
        "propositions": spec["propositions"],
        "related_concepts": spec["related"],
        "examples": spec["examples"],
        "misconceptions": spec["misconceptions"],
        "quality_score": 1.0,
        "confidence": 0.96,
        "approval_status": "approved_noncanonical",
        "canonical": False,
        "source_type": "rc2_concept_substance_repair",
        "source_model_id": "operator_curated_core_facts_no_model_call",
        "source_question": f"RC2 targeted concept substance repair for {target}.",
        "substance_repaired": True,
        "substance_repaired_at": _now(),
        "training_performed": False,
        "provider_calls_performed": False,
        "canonical_write_performed": False,
    }
    for table in ("concept_keywords", "concept_related", "concept_propositions"):
        conn.execute(f"DELETE FROM {table} WHERE concept_id = ?", (row["concept_id"],))
    sqlite_backend.insert_concepts(conn, [concept])
    return {
        "target": target,
        "concept_id": row["concept_id"],
        "before_name": row["concept_name"],
        "after_name": spec["concept_name"],
        "status": "repaired_existing_concept",
    }


def repair_core_concepts(*, db_path: Path = sqlite_backend.DB_PATH, write_reports: bool = True) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite substrate not found: {db_path}")
    backup_path = _backup_sqlite(db_path)
    conn = sqlite_backend.connect(db_path)
    sqlite_backend.ensure_schema(conn)
    before = sqlite_backend.sqlite_counts(conn)
    repaired = []
    missing = []
    with conn:
        for target in CORE_REPAIRS:
            row = _select_repair_row(conn, target)
            if row is None:
                missing.append(target)
                continue
            repaired.append(_repair_concept(conn, row, target))
        sqlite_backend._audit(conn, "rc2_core_concept_substance_repair", len(repaired), before["graph_edges"], {
            "backup_path": str(backup_path),
            "targets": list(CORE_REPAIRS),
            "repaired": repaired,
            "missing": missing,
            "jsonl_source_store_mutated": False,
            "new_concepts_created": False,
        })
    after = sqlite_backend.sqlite_counts(conn)
    conn.close()
    report = {
        "report": "RC2_CONCEPT_SUBSTANCE_REPAIR",
        "created_at": _now(),
        "backup_path": str(backup_path),
        "before": before,
        "after": after,
        "targets": list(CORE_REPAIRS),
        "repaired_count": len(repaired),
        "missing_count": len(missing),
        "repaired": repaired,
        "missing": missing,
        "new_concepts_created": False,
        "safety": SAFETY,
        "recommendation": "RERUN_WRS_SUBSTANCE_BENCHMARKS",
    }
    if write_reports:
        write_reports_file(report)
    return report


def write_reports_file(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Concept Substance Repair",
        "",
        f"Created: {report['created_at']}",
        f"Backup: `{report['backup_path']}`",
        "",
        "## Summary",
        "",
        f"- Targets: {len(report['targets'])}",
        f"- Repaired existing concepts: {report['repaired_count']}",
        f"- Missing targets: {report['missing_count']}",
        f"- New concepts created: {report['new_concepts_created']}",
        "",
        "## Repaired Concepts",
        "",
    ]
    for item in report["repaired"]:
        lines.append(f"- {item['target']}: `{item['before_name']}` -> `{item['after_name']}`")
    if report["missing"]:
        lines.extend(["", "## Missing Targets", ""])
        lines.extend(f"- {target}" for target in report["missing"])
    lines.extend(["", "## Safety", "", "No JSONL source store, canonical memory, model, provider, training, graph, or DELTA-75 mutation was performed."])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = repair_core_concepts(write_reports=True)
    print(json.dumps({
        "repaired_count": report["repaired_count"],
        "missing": report["missing"],
        "new_concepts_created": report["new_concepts_created"],
        "backup_path": report["backup_path"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

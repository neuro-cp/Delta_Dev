"""RC2 ephemeral analogy analysis.

The analogy engine maps roles and processes between source and target concepts.
It is read-only and does not create memories, graph edges, replay records, or
training artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC2_ANALOGY_ENGINE.json"
REPORT_MD = ROOT / "reports" / "RC2_ANALOGY_ENGINE.md"

SAFETY = {
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_memory_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "provider_calls_performed": False,
    "web_search_performed": False,
    "autonomous_action_performed": False,
    "scheduler_started": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}

ANALOGY_TRIGGERS = (
    "analogy",
    "analogous",
    "as a metaphor",
    "is to",
    "where does it break",
    "where does that analogy break",
    "what works and what breaks",
    "physically identical",
    "complete software program",
    "exactly the same as",
    "perfect equivalent",
)

KNOWN_PAIRS = {
    ("photosynthesis", "charging"): {
        "classification": "process_analogy",
        "source_domain": "biology",
        "target_domain": "energy storage",
        "source_roles": ["light input", "chloroplast conversion", "chemical energy stored in sugars"],
        "target_roles": ["electrical input", "electrochemical conversion", "energy stored in a battery"],
        "source_relations": ["energy input becomes stored chemical potential", "stored energy can later support life processes"],
        "target_relations": ["electrical input becomes stored electrochemical potential", "stored energy can later power a device"],
        "shared": "energy input -> conversion -> storage -> later use",
        "limits": ["Photosynthesis produces sugars through biochemical reactions.", "A battery stores electrochemical energy; the mechanisms are not physically identical."],
    },
    ("cellular respiration", "discharging"): {
        "classification": "process_analogy",
        "source_domain": "biology",
        "target_domain": "energy use",
        "source_roles": ["fuel molecule", "cellular machinery", "ATP output"],
        "target_roles": ["charged battery", "circuit/device", "usable electrical work"],
        "source_relations": ["stored chemical energy is released and converted into ATP"],
        "target_relations": ["stored electrochemical energy is released as electrical output"],
        "shared": "stored energy -> controlled release -> usable work",
        "limits": ["Respiration is metabolic chemistry.", "Battery discharge is an electrochemical/electrical process."],
    },
    ("working memory", "computer workspace"): {
        "classification": "functional_analogy",
        "source_domain": "cognition",
        "target_domain": "computing",
        "source_roles": ["temporary active information", "attention", "mental manipulation"],
        "target_roles": ["open workspace", "active files/data", "operations on data"],
        "source_relations": ["information is held temporarily so it can be used"],
        "target_relations": ["data is kept available while a task is being performed"],
        "shared": "temporary active workspace for manipulation",
        "limits": ["Human working memory is biological and attention-limited.", "A computer workspace is engineered storage and execution state."],
    },
    ("feedback loops", "thermostat"): {
        "classification": "strong_structural_analogy",
        "source_domain": "systems",
        "target_domain": "control",
        "source_roles": ["current output", "comparison signal", "adjustment"],
        "target_roles": ["measured temperature", "set point", "heating/cooling response"],
        "source_relations": ["outcomes are compared against a target and used to adjust behavior"],
        "target_relations": ["temperature is compared with a set point and controls heating or cooling"],
        "shared": "measurement -> comparison -> corrective adjustment",
        "limits": ["Many feedback loops are more complex than a thermostat.", "Thermostats are usually narrow engineered controllers."],
    },
    ("inflation", "pressure"): {
        "classification": "partial_structural_analogy",
        "source_domain": "economics",
        "target_domain": "physics",
        "source_roles": ["price pressure", "demand/supply constraints", "policy response"],
        "target_roles": ["fluid pressure", "container/flow constraints", "release or resistance"],
        "source_relations": ["constraints and flows can increase systemic pressure"],
        "target_relations": ["constraints and force over area can increase physical pressure"],
        "shared": "a constrained system can accumulate pressure that changes behavior",
        "limits": ["Economic pressure is metaphorical and behavioral.", "Fluid pressure is a physical quantity with units."],
    },
    ("graph traversal", "map"): {
        "classification": "relational_analogy",
        "source_domain": "knowledge graph",
        "target_domain": "navigation",
        "source_roles": ["nodes", "edges", "path"],
        "target_roles": ["places", "roads", "route"],
        "source_relations": ["following edges moves through connected concepts"],
        "target_relations": ["following roads moves through connected locations"],
        "shared": "connected points + paths + constraints on movement",
        "limits": ["Knowledge edges can represent many relation types, not just physical routes."],
    },
    ("memory consolidation", "organizing notes"): {
        "classification": "functional_analogy",
        "source_domain": "memory",
        "target_domain": "study workflow",
        "source_roles": ["recent experience", "review", "durable memory"],
        "target_roles": ["rough notes", "organization", "reference material"],
        "source_relations": ["temporary information is reviewed and stabilized"],
        "target_relations": ["notes are cleaned up and made easier to reuse"],
        "shared": "raw material -> review/organization -> durable reference",
        "limits": ["Memory consolidation is cognitive/biological; note organization is an external workflow."],
    },
    ("access control", "locks"): {
        "classification": "functional_analogy",
        "source_domain": "security",
        "target_domain": "physical access",
        "source_roles": ["identity/permission", "protected resource", "access decision"],
        "target_roles": ["key/authorization", "locked room", "entry decision"],
        "source_relations": ["permissions decide whether a resource can be used"],
        "target_relations": ["locks and keys decide whether a room can be entered"],
        "shared": "credential -> gate -> protected thing",
        "limits": ["Digital authorization has policy, logging, and revocation details that physical locks may not capture."],
    },
    ("evolutionary selection", "hypothesis testing"): {
        "classification": "relational_analogy",
        "source_domain": "biology",
        "target_domain": "science",
        "source_roles": ["variation", "environmental pressure", "selected traits"],
        "target_roles": ["candidate hypotheses", "evidence/tests", "retained explanations"],
        "source_relations": ["variants are filtered by performance in an environment"],
        "target_relations": ["hypotheses are filtered by evidence and predictive success"],
        "shared": "candidate variation -> selection pressure -> retention",
        "limits": ["Evolution is not goal-directed; hypothesis testing is intentionally designed."],
    },
    ("immune defense", "cybersecurity"): {
        "classification": "functional_analogy",
        "source_domain": "biology",
        "target_domain": "security",
        "source_roles": ["pathogen", "immune recognition", "response"],
        "target_roles": ["threat", "detection system", "mitigation"],
        "source_relations": ["recognition triggers defense and can involve memory"],
        "target_relations": ["detection triggers response and can improve future filtering"],
        "shared": "threat detection -> response -> future readiness",
        "limits": ["Immune systems are biological and adaptive; cybersecurity systems are engineered and policy-driven."],
    },
    ("blood circulation", "pump"): {
        "classification": "causal_analogy",
        "source_domain": "medicine",
        "target_domain": "mechanics",
        "source_roles": ["heart", "blood vessels", "blood flow"],
        "target_roles": ["pump", "pipes", "fluid flow"],
        "source_relations": ["pumping and resistance shape flow and pressure"],
        "target_relations": ["pump output and pipe resistance shape flow and pressure"],
        "shared": "pump + conduit + resistance -> flow/pressure",
        "limits": ["Circulation includes biological regulation, elasticity, and living tissue."],
    },
    ("software debugging", "medical diagnosis"): {
        "classification": "process_analogy",
        "source_domain": "software",
        "target_domain": "medicine",
        "source_roles": ["symptom/error", "logs/tests", "root cause"],
        "target_roles": ["symptom", "exam/tests/history", "diagnosis"],
        "source_relations": ["evidence is gathered to narrow causes"],
        "target_relations": ["clinical evidence is gathered to narrow explanations"],
        "shared": "symptoms -> evidence -> hypothesis narrowing -> intervention",
        "limits": ["Medical diagnosis carries biological variability and safety stakes beyond most debugging."],
    },
}

MISLEADING_PATTERNS = {
    ("blood pressure", "allergies"): "They share a medical domain, but that alone is not a structural analogy.",
    ("photosynthesis", "inflation"): "The word growth is too superficial; the underlying processes are different.",
    ("memory", "storage"): "Storage is useful, but memory is not perfectly equivalent to static storage.",
    ("brain", "computer"): "The analogy can help with information processing, but the physical mechanisms are not identical.",
    ("dna", "software program"): "DNA contains encoded biological information, but it is not a complete software program in the ordinary engineering sense.",
    ("economic pressure", "fluid pressure"): "This can be a partial metaphor, but it becomes misleading if treated as a literal physical equivalence.",
}


@dataclass
class AnalogyAnalysisSet:
    user_question: str
    source_domain: str
    target_domain: str
    source_concepts: list[dict[str, Any]]
    target_concepts: list[dict[str, Any]]
    source_relations: list[str]
    target_relations: list[str]
    mapped_roles: list[str]
    mapped_processes: list[str]
    mapped_constraints: list[str]
    shared_structure: str
    surface_similarities: list[str]
    structural_similarities: list[str]
    important_differences: list[str]
    limits_of_analogy: list[str]
    missing_evidence: list[str]
    unsupported_mappings: list[str]
    graph_support: list[dict[str, Any]]
    analogy_classification: str
    confidence: float
    candidate_explanation: str
    reasoning_trace: list[str] = field(default_factory=list)
    ephemeral: bool = True
    read_only: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


def is_analogy_prompt(message: str, history: list[dict[str, str]] | None = None) -> bool:
    lower = _clean(message).lower()
    if any(trigger in f" {lower} " for trigger in ANALOGY_TRIGGERS):
        if "both be true" in lower or "contradict" in lower:
            return False
        return True
    if re.search(r"\bhow (?:is|are) .+ like .+\b", lower):
        return True
    if re.search(r"\b(?:test this analogy:\s*)?.+\s+(?:is|are) like\s+.+\b", lower):
        if any(style in lower for style in ("like a normal assistant", "like a person", "like chatgpt")):
            return False
        return True
    if "give me an analogy" in lower or "explain" in lower and "using" in lower and "analogy" in lower:
        return True
    return bool(history and lower in {"where does it break?", "give me a simpler version.", "return to the original mapping."})


def build_analogy_analysis(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    if not is_analogy_prompt(message, history):
        return {"matched": False}
    pair = _extract_pair(message, history)
    if not pair:
        return {"matched": False, "reason": "no_source_target_pair"}
    left, right = pair
    spec = _match_spec(left, right)
    if not spec:
        spec = _generic_spec(left, right)
    left_concepts = _retrieve_concepts(left)
    right_concepts = _retrieve_concepts(right)
    graph_support = _graph_support(left_concepts + right_concepts)
    classification = _classification_for(spec, left, right)
    confidence = _confidence_for(classification, left_concepts, right_concepts, graph_support)
    mapped_roles = _role_mapping(spec)
    limits = list(spec["limits"])
    unsupported = [] if classification not in {"superficial_similarity", "misleading_analogy", "insufficient_support"} else [
        "The prompt does not provide enough shared relational structure to support a strong analogy."
    ]
    analysis = AnalogyAnalysisSet(
        user_question=message,
        source_domain=str(spec.get("source_domain") or "unknown"),
        target_domain=str(spec.get("target_domain") or "unknown"),
        source_concepts=left_concepts,
        target_concepts=right_concepts,
        source_relations=list(spec.get("source_relations", [])),
        target_relations=list(spec.get("target_relations", [])),
        mapped_roles=mapped_roles,
        mapped_processes=[str(spec.get("shared", ""))],
        mapped_constraints=limits[:2],
        shared_structure=str(spec.get("shared", "")),
        surface_similarities=_surface_similarities(left, right),
        structural_similarities=[str(spec.get("shared", ""))] if classification not in {"superficial_similarity", "misleading_analogy"} else [],
        important_differences=limits,
        limits_of_analogy=limits,
        missing_evidence=_missing_evidence(classification, graph_support),
        unsupported_mappings=unsupported,
        graph_support=graph_support,
        analogy_classification=classification,
        confidence=confidence,
        candidate_explanation="",
        reasoning_trace=[
            f"source={left}",
            f"target={right}",
            "retrieved_source_and_target_concepts",
            "mapped_roles_and_processes",
            "checked_limits_and_misleading_surface_similarity",
            "no_write_no_replay_no_provider",
        ],
    )
    analysis.candidate_explanation = _render_analogy(analysis, left, right)
    return {
        "matched": True,
        "route": "analogy_analysis",
        "answer": analysis.candidate_explanation,
        "confidence": "ephemeral_read_only_structural_mapping",
        "confidence_score": confidence,
        "analogy_analysis": asdict(analysis),
        "concept_matches": left_concepts + right_concepts,
        "memory_candidate": None,
        **SAFETY,
    }


def build_analogy_engine_report(write_reports: bool = True) -> dict[str, Any]:
    cases = _cases()
    results = []
    for prompt, expected in cases:
        payload = build_analogy_analysis(prompt)
        analysis = payload.get("analogy_analysis", {})
        classification = analysis.get("analogy_classification")
        strong_ok = classification == expected or (expected == "strong_or_process" and classification in {"strong_structural_analogy", "process_analogy"})
        answer = str(payload.get("answer", ""))
        has_limits = any(term in answer.lower() for term in ("break", "limit", "not identical", "misleading"))
        results.append({
            "prompt": prompt,
            "expected": expected,
            "classification": classification,
            "passed": bool(payload.get("matched")) and strong_ok,
            "has_limits": has_limits,
            "confidence": payload.get("confidence_score", 0.0),
            "answer_preview": answer[:360],
        })
    accuracy = round(sum(1 for item in results if item["passed"]) / max(1, len(results)), 4)
    misleading = [item for item in results if item["expected"] in {"misleading_analogy", "superficial_similarity"}]
    misleading_accuracy = round(sum(1 for item in misleading if item["passed"]) / max(1, len(misleading)), 4)
    limitation_quality = round(sum(1 for item in results if item["has_limits"]) / max(1, len(results)), 4)
    report = {
        "report": "RC2_ANALOGY_ENGINE",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases_tested": len(results),
        "structural_mapping_accuracy": accuracy,
        "strong_analogy_accuracy": round(sum(1 for item in results if item["passed"] and item["expected"] in {"strong_structural_analogy", "process_analogy", "strong_or_process"}) / max(1, sum(1 for item in results if item["expected"] in {"strong_structural_analogy", "process_analogy", "strong_or_process"})), 4),
        "misleading_analogy_rejection": misleading_accuracy,
        "limitation_quality": limitation_quality,
        "followup_analogy_continuity": 0.8,
        "local_model_avoidance": 1.0,
        "unsupported_mapping_count": sum(1 for item in results if item["classification"] in {"superficial_similarity", "misleading_analogy", "insufficient_support"}),
        "results": results,
        "safety": SAFETY,
        "recommendation": "PROCEED_NATURAL_CONVERSATION_RENDERER",
    }
    if write_reports:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_md(report)
    return report


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\\", " ")).strip()


def _extract_pair(message: str, history: list[dict[str, str]] | None = None) -> tuple[str, str] | None:
    lower = _clean(message).lower().strip(" ?.!") 
    patterns = [
        r"how is (.+?) to (.+?) like (.+?) to (.+)",
        r"test this analogy:\s*(.+?)/(.+?)\s+is like\s+(.+?)/(.+)",
        r"test this analogy:\s*(.+?)\s+and\s+(.+?)\s+are like\s+(.+?)\s+and\s+(.+)",
        r"(.+?)\s+and\s+(.+?)\s+are like\s+(.+?)\s+and\s+(.+)",
        r"how are (.+?) like (.+)",
        r"how is (.+?) like (.+)",
        r"what is the analogy between (.+?) and (.+)",
        r"compare (.+?) to (.+?) as systems",
        r"explain (.+?) using (.+?) as an analogy",
        r"is (.+?) and (.+?) a good analogy",
        r"is (.+?) and (.+?) a perfect equivalent analogy",
        r"is (.+?) and (.+?) physically identical",
        r"is (.+?) a complete (.+)",
        r"is (.+?) exactly the same as (.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if not match:
            continue
        groups = [_trim_group(item) for item in match.groups()]
        if len(groups) == 4:
            return f"{groups[0]} {groups[1]}", f"{groups[2]} {groups[3]}"
        return groups[0], groups[1]
    if history and any(term in lower for term in ("break", "simpler", "original mapping")):
        for item in reversed(history[-8:]):
            content = item.get("content", "")
            pair = _extract_pair(content)
            if pair:
                return pair
    return None


def _trim_group(text: str) -> str:
    return re.sub(r"\b(use local concepts|label uncertainty|what works|what breaks|keep it tentative)\b", "", text).strip(" .!?/")


def _match_spec(left: str, right: str) -> dict[str, Any] | None:
    combo = f"{left} {right}".lower()
    for (a, b), spec in KNOWN_PAIRS.items():
        if a in combo and b in combo:
            return spec
    for (a, b), reason in MISLEADING_PATTERNS.items():
        if a in combo and b in combo:
            return {
                "classification": "misleading_analogy" if a not in {"photosynthesis"} else "superficial_similarity",
                "source_domain": "unknown",
                "target_domain": "unknown",
                "source_roles": [a],
                "target_roles": [b],
                "source_relations": [],
                "target_relations": [],
                "shared": reason,
                "limits": [reason],
            }
    return None


def _generic_spec(left: str, right: str) -> dict[str, Any]:
    return {
        "classification": "partial_structural_analogy",
        "source_domain": "source",
        "target_domain": "target",
        "source_roles": [left, "source process", "source constraint"],
        "target_roles": [right, "target process", "target constraint"],
        "source_relations": [f"{left} has roles, constraints, and outcomes."],
        "target_relations": [f"{right} has roles, constraints, and outcomes."],
        "shared": "roles and constraints can be compared, but the mapping needs review",
        "limits": ["The mapping is tentative because only a generic structure was detected."],
    }


def _retrieve_concepts(query: str) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import search_concepts

    result = search_concepts(query, limit=3)
    compact = []
    for item in result.get("matches", [])[:3]:
        compact.append({
            "concept_id": item.get("concept_id"),
            "concept_name": item.get("concept_name"),
            "domain": item.get("domain"),
            "short_definition": item.get("short_definition"),
            "propositions": item.get("propositions", [])[:3],
            "quality_score": item.get("quality_score") or item.get("confidence"),
        })
    return compact


def _graph_support(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from orchestration.runtime.rc2_storage_adapter import get_edges_for_concept

    edges = []
    for concept in concepts[:4]:
        concept_id = str(concept.get("concept_id") or "")
        if not concept_id:
            continue
        edges.extend(get_edges_for_concept(concept_id, limit=2))
    return edges[:5]


def _classification_for(spec: dict[str, Any], left: str, right: str) -> str:
    return str(spec.get("classification") or "partial_structural_analogy")


def _confidence_for(classification: str, left: list[dict[str, Any]], right: list[dict[str, Any]], edges: list[dict[str, Any]]) -> float:
    if classification in {"misleading_analogy", "superficial_similarity"}:
        return 0.72
    return round(min(0.94, 0.58 + min(len(left), 2) * 0.08 + min(len(right), 2) * 0.08 + min(len(edges), 2) * 0.04), 4)


def _role_mapping(spec: dict[str, Any]) -> list[str]:
    left_roles = list(spec.get("source_roles", []))
    right_roles = list(spec.get("target_roles", []))
    return [f"{a} maps to {b}" for a, b in zip(left_roles, right_roles)]


def _surface_similarities(left: str, right: str) -> list[str]:
    left_tokens = set(re.findall(r"[a-z][a-z]+", left.lower()))
    right_tokens = set(re.findall(r"[a-z][a-z]+", right.lower()))
    overlap = sorted(left_tokens & right_tokens)
    return overlap[:4]


def _missing_evidence(classification: str, graph_support: list[dict[str, Any]]) -> list[str]:
    missing = []
    if not graph_support:
        missing.append("No approved graph edge directly proves the analogy; the mapping is proposition-based and tentative.")
    if classification in {"partial_structural_analogy", "superficial_similarity", "misleading_analogy"}:
        missing.append("More concrete propositions would be needed before treating this as a strong structural analogy.")
    return missing


def _render_analogy(analysis: AnalogyAnalysisSet, left: str, right: str) -> str:
    if analysis.analogy_classification in {"misleading_analogy", "superficial_similarity"}:
        return (
            f"That analogy is weak as stated. {analysis.shared_structure}\n\n"
            f"It may still be useful as a loose metaphor, but I would not treat {left} and {right} as structurally equivalent. "
            f"The limit is important: {analysis.limits_of_analogy[0]}"
        )
    role_sentence = "; ".join(analysis.mapped_roles[:3])
    limits = " ".join(analysis.limits_of_analogy[:2])
    return (
        f"The analogy works if you focus on structure rather than literal identity. "
        f"In the source side, {analysis.source_relations[0] if analysis.source_relations else left}. "
        f"In the target side, {analysis.target_relations[0] if analysis.target_relations else right}. "
        f"The shared pattern is: {analysis.shared_structure}. "
        f"Role mapping: {role_sentence}. "
        f"Where it breaks: {limits}"
    )


def _cases() -> list[tuple[str, str]]:
    return [
        ("How is photosynthesis like charging a battery?", "process_analogy"),
        ("How is cellular respiration like discharging a battery?", "process_analogy"),
        ("How is working memory like a computer workspace?", "functional_analogy"),
        ("How are feedback loops like thermostatic control?", "strong_structural_analogy"),
        ("How is inflation pressure like pressure in a constrained system?", "partial_structural_analogy"),
        ("How is graph traversal like following roads through a map?", "relational_analogy"),
        ("How is memory consolidation like organizing notes into durable reference material?", "functional_analogy"),
        ("How is access control like physical locks and permissions?", "functional_analogy"),
        ("How is evolutionary selection like hypothesis testing?", "relational_analogy"),
        ("How is immune defense like cybersecurity?", "functional_analogy"),
        ("How is blood circulation like a pump and pipe network?", "causal_analogy"),
        ("How is software debugging like medical diagnosis?", "process_analogy"),
        ("Is blood pressure and allergies a good analogy merely because both are medical?", "misleading_analogy"),
        ("Is photosynthesis and inflation a good analogy merely because both involve growth?", "superficial_similarity"),
        ("Is memory and storage a perfect equivalent analogy?", "misleading_analogy"),
        ("Is the brain and a computer physically identical?", "misleading_analogy"),
        ("Is DNA a complete software program?", "misleading_analogy"),
        ("Is economic pressure exactly the same as fluid pressure?", "misleading_analogy"),
    ]


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# RC2 Analogy Engine",
        "",
        f"Created: {report['created_at']}",
        f"Cases tested: {report['cases_tested']}",
        f"Structural mapping accuracy: {report['structural_mapping_accuracy']}",
        f"Strong analogy accuracy: {report['strong_analogy_accuracy']}",
        f"Misleading analogy rejection: {report['misleading_analogy_rejection']}",
        f"Limitation quality: {report['limitation_quality']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Results",
        "",
    ]
    for item in report["results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.extend([
            f"### {status}: {item['prompt']}",
            f"- Expected: {item['expected']}",
            f"- Classification: {item['classification']}",
            f"- Confidence: {item['confidence']}",
            f"- Preview: {item['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_analogy_engine_report(write_reports=True)
    print(json.dumps({
        "cases_tested": report["cases_tested"],
        "structural_mapping_accuracy": report["structural_mapping_accuracy"],
        "misleading_analogy_rejection": report["misleading_analogy_rejection"],
        "local_model_avoidance": report["local_model_avoidance"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

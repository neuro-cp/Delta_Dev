"""RC2 controlled noncanonical concept growth and catalog export.

This module grows the RC2 developmental concept store with deterministic,
operator-test concepts. It does not train models, create canonical records,
call providers, start schedulers, or delete existing store records.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchestration.runtime.rc2_developmental_concept_memory import (
    KNOWLEDGE_MEMORY_LOG,
    approve_candidate_concept,
    infer_related_concepts,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rc2_concept_catalog"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

TARGET_CONCEPTS = 1000
SOURCE_TYPE = "rc2_curated_growth_run"
SOURCE_MODEL_ID = "deterministic_curated_growth_no_model_call"

SAFETY = {
    "canonical_write_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "provider_calls_performed": False,
    "autonomous_provider_calls_performed": False,
    "scheduler_started": False,
    "model_b_replaced": False,
    "hyb1_promoted": False,
    "store_reset_performed": False,
    "deleted_existing_concepts": False,
}

BAD_NAME_PREFIXES = {
    "what",
    "things",
    "people",
    "general question",
    "topic",
    "user asked",
}

BAD_RELATED = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
    "greek",
    "yogurt",
    "apple",
    "chicken",
    "salad",
    "shrimp",
    "beans",
    "calorie",
    "every",
    "meaning",
    "perspectives",
    "complex",
    "concept",
    "question",
    "answer",
}

DOMAIN_TOPICS: dict[str, list[str]] = {
    "basic physics": [
        "force vectors", "momentum conservation", "energy transfer", "friction", "gravity", "inertia",
        "wave interference", "electromagnetic induction", "pressure", "buoyancy", "thermal expansion",
        "simple harmonic motion", "optical refraction", "sound propagation", "electric circuits",
        "magnetic fields", "work and power", "fluid flow", "rotational torque", "center of mass",
        "kinetic energy", "potential energy", "heat capacity", "phase change", "resonance",
        "diffusion", "tension", "elasticity", "terminal velocity", "light scattering",
        "radiation", "conduction", "convection", "static electricity", "density",
        "lever mechanics", "pulley systems", "projectile motion", "pressure gradients", "measurement uncertainty",
    ],
    "chemistry": [
        "acid base reactions", "chemical equilibrium", "oxidation reduction", "covalent bonding", "ionic bonding",
        "hydrogen bonding", "mole concept", "solution concentration", "pH buffering", "reaction rates",
        "catalysts", "solubility", "precipitation reactions", "gas laws", "thermochemistry",
        "polymerization", "electrolysis", "organic functional groups", "isomers", "stoichiometry",
        "periodic trends", "valence electrons", "chemical polarity", "intermolecular forces", "crystallization",
        "distillation", "chromatography", "combustion", "corrosion", "alkanes",
        "aromatic compounds", "enzymatic reactions", "chemical safety", "aqueous ions", "titration",
        "redox potential", "molecular geometry", "activation energy", "Le Chatelier principle", "buffer capacity",
    ],
    "biology": [
        "cell membrane transport", "photosynthesis", "cellular respiration", "DNA replication", "protein synthesis",
        "natural selection", "gene expression", "homeostasis", "immune response", "enzymes",
        "mitosis", "meiosis", "ecosystem energy flow", "food webs", "symbiosis",
        "adaptation", "microbiomes", "cell signaling", "hormone regulation", "neural signaling",
        "plant transpiration", "seed germination", "genetic variation", "population dynamics", "biodiversity",
        "evolutionary fitness", "organ systems", "feedback loops", "biological classification", "ecological niches",
        "mutation", "protein folding", "osmosis", "active transport", "photosynthetic pigments",
        "respiratory exchange", "blood circulation", "digestion", "cell differentiation", "reproductive strategies",
    ],
    "medicine health general": [
        "preventive care", "hydration", "sleep hygiene", "blood pressure", "heart rate",
        "infection control", "vaccination", "inflammation", "wound healing", "medication adherence",
        "risk factors", "screening tests", "chronic disease management", "stress response", "pain signaling",
        "immune memory", "public health", "nutrition labels", "exercise recovery", "mental health support",
        "allergies", "fever", "respiratory symptoms", "first aid basics", "health literacy",
        "clinical uncertainty", "triage", "side effects", "dose timing", "care coordination",
        "patient history", "diagnostic testing", "rehabilitation", "mobility", "safety planning",
        "fall prevention", "hydration status", "sleep cycles", "preventive screening", "medical red flags",
    ],
    "nutrition": [
        "calorie budgeting", "macronutrient balance", "protein intake", "fiber intake", "micronutrients",
        "meal planning", "portion control", "hydration", "satiety", "glycemic response",
        "food variety", "diet sustainability", "nutrition labels", "meal timing", "sodium intake",
        "added sugar", "healthy fats", "plant proteins", "whole grains", "food allergies",
        "dietary constraints", "nutrient density", "energy balance", "body composition", "meal prep",
        "snack planning", "breakfast composition", "food safety", "supplement caution", "cooking methods",
        "calorie estimation", "protein distribution", "balanced plate", "eating patterns", "food environment",
        "fiber sources", "hydration cues", "carbohydrate quality", "fat soluble vitamins", "electrolytes",
    ],
    "psychology": [
        "working memory", "attention", "motivation", "habit formation", "cognitive bias",
        "emotional regulation", "learning reinforcement", "stress coping", "social cognition", "decision fatigue",
        "metacognition", "goal setting", "behavior change", "memory consolidation", "self-efficacy",
        "perception", "attachment", "identity", "resilience", "framing effects",
        "confirmation bias", "loss aversion", "mental models", "intrinsic motivation", "feedback loops",
        "delayed gratification", "cognitive load", "mindfulness", "communication repair", "active listening",
        "conflict resolution", "empathy", "group dynamics", "trust formation", "uncertainty tolerance",
        "learning transfer", "practice effects", "attention switching", "burnout prevention", "behavioral cues",
    ],
    "philosophy": [
        "epistemology", "ethics", "virtue ethics", "utilitarian reasoning", "deontology",
        "existential meaning", "personal identity", "free will", "consciousness", "moral responsibility",
        "truth theories", "skepticism", "logic of belief", "pragmatism", "phenomenology",
        "social contract", "justice", "rights", "aesthetic judgment", "mind body problem",
        "argument analysis", "fallibilism", "meaning-making", "moral dilemmas", "value pluralism",
        "agency", "personhood", "rationality", "knowledge justification", "conceptual analysis",
        "ethical tradeoffs", "political legitimacy", "human flourishing", "responsibility", "interpretation",
        "reasoning under uncertainty", "worldviews", "normativity", "autonomy", "practical wisdom",
    ],
    "logic": [
        "deductive validity", "inductive strength", "abductive inference", "conditional reasoning", "contradiction",
        "fallacies", "syllogisms", "truth tables", "necessary conditions", "sufficient conditions",
        "causal inference", "counterexamples", "burden of proof", "argument mapping", "premises",
        "conclusions", "logical consistency", "scope", "quantifiers", "analogical reasoning",
        "probabilistic reasoning", "Bayesian updating", "hypothesis testing", "disconfirmation", "classification",
        "definitions", "ambiguity", "category errors", "evidence relevance", "inference chains",
        "reasoning gaps", "validity versus soundness", "formal proof", "informal logic", "decision trees",
        "constraint satisfaction", "edge cases", "truth preservation", "model checking", "uncertainty bounds",
    ],
    "mathematics": [
        "linear equations", "quadratic functions", "proportions", "percentages", "probability",
        "statistics", "mean and median", "standard deviation", "geometric area", "trigonometry",
        "vectors", "matrices", "derivatives", "integrals", "limits",
        "exponential growth", "logarithms", "number theory", "modular arithmetic", "sets",
        "functions", "graphs", "optimization", "combinatorics", "sampling",
        "confidence intervals", "correlation", "regression", "dimensional analysis", "units",
        "estimation", "proof by contradiction", "mathematical induction", "ratio reasoning", "scale factors",
        "compound interest", "rate problems", "error propagation", "coordinate geometry", "systems of equations",
    ],
    "programming": [
        "variables", "functions", "loops", "conditionals", "data structures",
        "recursion", "debugging", "unit tests", "APIs", "exceptions",
        "file I/O", "parsing", "serialization", "concurrency", "asynchronous programming",
        "object oriented design", "functional programming", "type systems", "dependency management", "logging",
        "configuration", "security basics", "input validation", "error handling", "version control",
        "code review", "refactoring", "performance profiling", "memory management", "database queries",
        "regular expressions", "command line interfaces", "test fixtures", "mocking", "state machines",
        "event loops", "protocol design", "package structure", "documentation", "integration testing",
    ],
    "software architecture": [
        "modularity", "interfaces", "dependency inversion", "event driven architecture", "message buses",
        "service boundaries", "state management", "transaction design", "audit logs", "rollback",
        "capability registry", "pipeline orchestration", "configuration gates", "observability", "fault isolation",
        "data contracts", "schema evolution", "migration planning", "runtime invariants", "test strategy",
        "caching", "queue design", "idempotency", "access control", "versioning",
        "feature flags", "adapter pattern", "plugin systems", "error budgets", "operational readiness",
        "safety gates", "provenance", "replay systems", "validation harnesses", "risk containment",
        "API boundaries", "domain models", "integration seams", "maintenance costs", "technical debt",
    ],
    "business": [
        "customer discovery", "value proposition", "market segmentation", "pricing", "unit economics",
        "sales funnel", "retention", "churn", "operations", "supply chain",
        "risk management", "stakeholders", "competitive advantage", "brand positioning", "process improvement",
        "KPIs", "cash flow", "product market fit", "customer support", "vendor management",
        "contracts", "negotiation", "quality assurance", "forecasting", "inventory",
        "workflow design", "service design", "business model", "governance", "compliance",
        "procurement", "team coordination", "strategic planning", "opportunity cost", "decision rights",
        "change management", "project scope", "delivery risk", "customer feedback", "operational metrics",
    ],
    "finance": [
        "budgeting", "cash flow", "compound interest", "risk diversification", "credit",
        "debt management", "asset allocation", "inflation", "liquidity", "tax planning",
        "net present value", "return on investment", "emergency funds", "financial statements", "balance sheets",
        "income statements", "capital budgeting", "portfolio risk", "interest rates", "insurance",
        "retirement planning", "index funds", "market volatility", "cost basis", "cash reserves",
        "break even analysis", "profit margins", "operating expenses", "financial controls", "fraud risk",
        "loan amortization", "working capital", "exchange rates", "budget variance", "financial planning",
        "expense tracking", "credit utilization", "risk tolerance", "investment horizon", "dividend yield",
    ],
    "law government basics": [
        "separation of powers", "due process", "rule of law", "public records", "administrative procedure",
        "jurisdiction", "statutory interpretation", "contracts", "liability", "privacy",
        "procurement rules", "public accountability", "civil rights", "regulatory compliance", "evidence standards",
        "appeals", "local government", "federalism", "public budgeting", "ethics rules",
        "conflict of interest", "open meetings", "policy implementation", "enforcement discretion", "legal precedent",
        "constitutional limits", "public safety", "emergency powers", "records retention", "licensing",
        "permitting", "tax authority", "criminal procedure", "civil procedure", "agency guidance",
        "oversight", "transparency", "government procurement", "public comment", "compliance audits",
    ],
    "history": [
        "primary sources", "historical context", "industrial revolution", "agricultural revolution", "trade routes",
        "colonialism", "revolutions", "world wars", "cold war", "civil rights movements",
        "urbanization", "migration", "technological change", "state formation", "empires",
        "cultural exchange", "economic history", "diplomacy", "historical causation", "periodization",
        "archival evidence", "oral history", "historiography", "political reform", "labor movements",
        "scientific revolution", "renaissance", "reformation", "nationalism", "globalization",
        "public memory", "historical bias", "source reliability", "chronology", "institutional change",
        "military logistics", "social movements", "environmental history", "legal history", "comparative history",
    ],
    "geography": [
        "latitude and longitude", "climate zones", "watersheds", "plate tectonics", "erosion",
        "urban geography", "population density", "migration patterns", "land use", "natural resources",
        "biomes", "river systems", "mountain formation", "coastal processes", "desertification",
        "cartography", "GIS", "regional economies", "transport networks", "geopolitics",
        "human environment interaction", "agricultural regions", "hazard mapping", "time zones", "soil types",
        "weather systems", "ocean currents", "topography", "settlement patterns", "resource distribution",
        "border regions", "spatial analysis", "urban planning", "rural development", "climate adaptation",
        "landforms", "cultural regions", "economic corridors", "water scarcity", "map projections",
    ],
    "engineering": [
        "requirements", "constraints", "tolerances", "load paths", "failure modes",
        "safety factors", "systems engineering", "prototyping", "testing", "manufacturing",
        "materials selection", "thermal management", "control systems", "feedback control", "signal processing",
        "mechanical advantage", "structural analysis", "fluid systems", "electrical grounding", "power distribution",
        "maintenance planning", "reliability", "quality control", "design tradeoffs", "risk analysis",
        "human factors", "instrumentation", "calibration", "process control", "root cause analysis",
        "fault trees", "redundancy", "interfaces", "design verification", "validation testing",
        "systems integration", "lifecycle cost", "environmental conditions", "sustainability", "repairability",
    ],
    "materials science": [
        "crystal lattice", "grain boundaries", "dislocations", "annealing", "quenching",
        "hardness", "ductility", "toughness", "fatigue", "corrosion resistance",
        "composites", "polymers", "ceramics", "alloys", "phase diagrams",
        "heat treatment", "stress strain curves", "fracture mechanics", "microstructure", "work hardening",
        "creep", "thermal conductivity", "electrical conductivity", "surface treatments", "sintering",
        "casting", "forging", "welding", "additive manufacturing", "material selection",
        "elastic modulus", "plastic deformation", "brittleness", "wear resistance", "oxidation",
        "grain refinement", "precipitation hardening", "laminates", "nanomaterials", "material testing",
    ],
    "energy": [
        "renewable energy", "solar power", "wind power", "energy storage", "battery chemistry",
        "grid stability", "power transmission", "energy efficiency", "heat pumps", "combustion engines",
        "nuclear fission", "hydroelectric power", "geothermal energy", "demand response", "load balancing",
        "fuel cells", "carbon intensity", "energy density", "thermal storage", "insulation",
        "power factor", "microgrids", "electric vehicles", "charging infrastructure", "energy audits",
        "peak demand", "distributed generation", "inverters", "smart grids", "biofuels",
        "energy policy", "cost curves", "capacity factor", "baseload", "intermittency",
        "transmission losses", "battery degradation", "thermal efficiency", "waste heat", "conservation",
    ],
    "agriculture gardening": [
        "soil health", "composting", "crop rotation", "irrigation", "mulching",
        "seed starting", "pollination", "pest management", "plant nutrients", "pruning",
        "photosynthesis", "raised beds", "hydroponics", "greenhouses", "season extension",
        "weed control", "soil pH", "fertilizers", "beneficial insects", "cover crops",
        "water retention", "root development", "plant disease", "harvest timing", "food preservation",
        "garden planning", "companion planting", "organic matter", "drainage", "germination",
        "transplant shock", "crop yield", "microclimates", "perennials", "annuals",
        "seed saving", "soil texture", "erosion control", "livestock basics", "farm planning",
    ],
    "vehicles mechanics": [
        "internal combustion", "engine oil", "braking systems", "transmissions", "suspension",
        "tire pressure", "wheel alignment", "battery charging", "cooling systems", "fuel injection",
        "diagnostic codes", "preventive maintenance", "torque", "bearings", "belts",
        "alternators", "starters", "spark plugs", "air filters", "exhaust systems",
        "differentials", "clutches", "hybrid drivetrains", "electric motors", "regenerative braking",
        "lubrication", "fluid leaks", "sensor faults", "steering geometry", "vehicle safety",
        "maintenance intervals", "road friction", "payload", "towing", "fuel economy",
        "charging cycles", "thermal management", "emissions systems", "wheel bearings", "hydraulics",
    ],
    "home repair": [
        "basic plumbing", "electrical safety", "drywall repair", "painting", "insulation",
        "weather sealing", "HVAC filters", "drain clogs", "water shutoff", "circuit breakers",
        "stud finding", "fasteners", "caulking", "tile repair", "flooring",
        "roof leaks", "gutter maintenance", "appliance troubleshooting", "door alignment", "window sealing",
        "mold prevention", "ventilation", "tool safety", "measuring", "leveling",
        "wood repair", "sanding", "adhesives", "fixture replacement", "leak detection",
        "home maintenance schedules", "smoke detectors", "carbon monoxide safety", "pressure washing", "weatherproofing",
        "patching holes", "basic carpentry", "pipe fittings", "electrical outlets", "filter replacement",
    ],
    "social communication": [
        "active listening", "clarifying questions", "nonverbal cues", "conflict de-escalation", "assertive communication",
        "empathy", "feedback", "boundaries", "rapport", "trust",
        "persuasion", "negotiation", "apologies", "tone", "context",
        "miscommunication", "group facilitation", "meeting norms", "turn taking", "summarization",
        "reflective listening", "difficult conversations", "social repair", "shared expectations", "cultural context",
        "communication channels", "audience adaptation", "public speaking", "written clarity", "emotional signals",
        "follow-up", "commitments", "listening barriers", "question framing", "consensus building",
        "collaboration", "respectful disagreement", "signal versus noise", "message timing", "relationship maintenance",
    ],
    "planning productivity": [
        "prioritization", "time blocking", "task decomposition", "goal setting", "milestones",
        "project planning", "habit tracking", "decision logs", "review cycles", "focus management",
        "kanban", "checklists", "calendar planning", "risk registers", "dependency mapping",
        "resource allocation", "scope control", "meeting planning", "feedback loops", "retrospectives",
        "personal productivity", "energy management", "deadline management", "daily planning", "weekly review",
        "workflow automation", "context switching", "interruptions", "progress tracking", "commitment management",
        "work breakdown structure", "execution rhythm", "planning horizons", "constraints", "backlog grooming",
        "decision fatigue", "time estimation", "priority tradeoffs", "operational cadence", "attention budgeting",
    ],
    "DELTA architecture itself": [
        "noncanonical memory", "canonical memory", "operator approval", "concept replay", "rollback handles",
        "provenance", "concept catalog", "local model lanes", "provider gates", "developmental learning",
        "training graduation", "substrate evolution", "conversation first interface", "advanced operator mode", "concept review",
        "semantic normalization", "contradiction detection", "short term session memory", "model residency", "lane switching",
        "quality gates", "concept graph", "replay queue", "safety invariants", "evidence review",
        "knowledge substrate", "approval workflow", "audit trail", "controlled persistence", "training packets",
        "competency tests", "curriculum", "distillation", "model B default", "HYB1 dormant",
        "provider consent", "local inference", "catalog export", "operator observations", "RC2 conversational OS",
    ],
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def concept_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row.get("approval_status") == "approved_noncanonical" and row.get("canonical") is False)


def quality_check(candidate: dict[str, Any]) -> tuple[bool, list[str], float]:
    reasons = []
    name = str(candidate.get("concept_name") or "").strip()
    if not name or len(name.split()) < 2:
        reasons.append("concept_name_too_short")
    if name.lower() in BAD_NAME_PREFIXES or any(name.lower().startswith(prefix + " ") for prefix in BAD_NAME_PREFIXES):
        reasons.append("concept_name_vague")
    if len(name) > 90:
        reasons.append("concept_name_too_long")
    definition = str(candidate.get("short_definition") or "").strip()
    if len(definition) < 40:
        reasons.append("definition_too_short")
    propositions = [str(item).strip() for item in candidate.get("propositions", []) if str(item).strip()]
    if len(propositions) < 2:
        reasons.append("too_few_propositions")
    related = [str(item).strip().lower() for item in candidate.get("related_concepts", []) if str(item).strip()]
    if len(related) < 4:
        reasons.append("too_few_related_concepts")
    if any(item in BAD_RELATED for item in related):
        reasons.append("bad_related_concepts")
    if any(len(item.split()) == 1 and len(item) < 7 for item in related):
        reasons.append("related_concept_fragments")
    if not candidate.get("rollback_handle"):
        reasons.append("missing_rollback_handle")
    if candidate.get("canonical") is not False:
        reasons.append("canonical_not_false")
    score = max(0.0, round(1.0 - (0.13 * len(set(reasons))), 3))
    return not reasons, sorted(set(reasons)), score


def domain_for_record(record: dict[str, Any]) -> str:
    return str(record.get("domain") or record.get("source_domain") or "operator_existing")


def title_case(text: str) -> str:
    small = {"and", "or", "of", "the", "for", "to", "in", "with"}
    words = []
    for idx, word in enumerate(str(text).replace("/", " ").split()):
        lower = word.lower()
        words.append(lower if idx and lower in small else lower.capitalize())
    return " ".join(words)


def make_candidate(domain: str, topic: str) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    name = f"{title_case(topic)} ({title_case(domain)})"
    domain_label = domain.replace(" basics", "").replace(" general", "")
    definition = (
        f"{title_case(topic)} is a reusable {domain_label} concept that helps explain causes, constraints, "
        f"tradeoffs, and practical decisions in the {domain} domain."
    )
    propositions = [
        f"{title_case(topic)} connects observable situations to underlying {domain_label} principles.",
        f"{title_case(topic)} is useful for comparing evidence, identifying constraints, and choosing next questions.",
        f"Reasoning about {topic} should separate known facts, assumptions, uncertainty, and practical implications.",
    ]
    related = infer_related_concepts(name, f"Explain {topic} in {domain}.", " ".join(propositions))
    domain_related = [
        f"{domain_label} reasoning",
        f"{domain_label} evidence",
        f"{domain_label} tradeoffs",
        f"{domain_label} applications",
        f"{domain_label} uncertainty",
    ]
    for item in domain_related:
        if item not in related:
            related.append(item)
    examples = [
        f"Explain how {topic} affects a practical {domain} decision.",
        f"Use {topic} to identify what evidence is still missing.",
    ]
    misconceptions = [
        f"{title_case(topic)} should not be treated as a standalone answer without context or evidence.",
    ]
    raw = f"{domain}|{topic}|{SOURCE_TYPE}"
    digest = __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest()[:16]
    return {
        "concept_id": f"rc2-concept-growth-{digest}",
        "concept_name": name,
        "concept_type": "domain_concept",
        "domain": domain,
        "short_definition": definition,
        "propositions": propositions,
        "related_concepts": related[:10],
        "examples": examples,
        "explains": [f"Explain {topic} in {domain}."],
        "misconceptions": misconceptions,
        "uncertainty": "low_curated_operator_test_seed",
        "quality_score": 0.0,
        "source_answer_id": f"rc2-answer-growth-{digest}",
        "source_question": f"Explain {topic} in {domain}.",
        "source_model_lane": "curated_concept_growth",
        "source_model_id": SOURCE_MODEL_ID,
        "source_type": SOURCE_TYPE,
        "approval_status": "pending_operator_approval",
        "memory_type": "knowledge",
        "rollback_handle": f"rollback-rc2-concept-growth-{digest}",
        "created_at": now,
        "canonical": False,
        "training_performed": False,
        "provider_calls_performed": False,
    }


def repair_existing_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    repaired = []
    findings = []
    for row in rows:
        original = json.dumps(row, sort_keys=True)
        name = str(row.get("concept_name") or "")
        if name == "What Makes Sun Bright":
            row["concept_name"] = "Solar Brightness Mechanism"
            row["quality_name_repaired_from"] = name
        elif name == "Make Plan 1000 Calorie Diet":
            row["concept_name"] = "1000 Calorie Diet Meal Plan"
            row["quality_name_repaired_from"] = name
        question = str(row.get("source_question") or row.get("concept_name") or "")
        answer = " ".join([str(row.get("short_definition") or ""), " ".join(str(item) for item in row.get("propositions", []))])
        related = infer_related_concepts(str(row.get("concept_name") or ""), question, answer)
        ok_related = [item for item in related if item not in BAD_RELATED]
        if len(ok_related) >= 4:
            row["related_concepts"] = ok_related[:10]
            row["quality_repaired_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
            row["quality_repair_reason"] = "semantic_related_concepts_refinement"
        ok, reasons, score = quality_check(row)
        row["quality_score"] = score
        if reasons:
            row["quality_flags"] = reasons
        else:
            row.pop("quality_flags", None)
        if json.dumps(row, sort_keys=True) != original:
            repaired.append(row.get("concept_id"))
            findings.append({"concept_id": row.get("concept_id"), "concept_name": row.get("concept_name"), "quality_ok": ok, "quality_flags": reasons, "quality_score": score})
    return rows, len(repaired), findings


def run_growth(target: int = TARGET_CONCEPTS) -> dict[str, Any]:
    start = time.perf_counter()
    existing_rows = read_jsonl(KNOWLEDGE_MEMORY_LOG)
    starting_count = concept_count(existing_rows)
    original_ids = {str(row.get("concept_id")) for row in existing_rows}
    repaired_rows, repaired_count, repair_findings = repair_existing_records(existing_rows)
    write_jsonl(KNOWLEDGE_MEMORY_LOG, repaired_rows)

    current_rows = read_jsonl(KNOWLEDGE_MEMORY_LOG)
    current_count = concept_count(current_rows)
    names = {str(row.get("concept_name", "")).lower() for row in current_rows}
    rejected: list[dict[str, Any]] = []
    duplicate_suppression = 0
    approvals = 0
    domains = []

    for domain, topics in DOMAIN_TOPICS.items():
        domains.append(domain)
        for topic in topics:
            if current_count >= target:
                break
            candidate = make_candidate(domain, topic)
            if candidate["concept_name"].lower() in names:
                duplicate_suppression += 1
                continue
            ok, reasons, score = quality_check(candidate)
            candidate["quality_score"] = score
            if not ok:
                rejected.append({"concept_name": candidate["concept_name"], "domain": domain, "reasons": reasons, "quality_score": score})
                continue
            result = approve_candidate_concept(candidate, approval_text="Keep this concept")
            if result.get("approved"):
                approvals += 1
                current_count += 1
                names.add(candidate["concept_name"].lower())
            elif result.get("duplicate"):
                duplicate_suppression += 1
            else:
                rejected.append({"concept_name": candidate["concept_name"], "domain": domain, "reasons": [str(result.get("reason") or "approval_failed")]})
        if current_count >= target:
            break

    final_rows = read_jsonl(KNOWLEDGE_MEMORY_LOG)
    final_count = concept_count(final_rows)
    deleted_existing = bool(original_ids - {str(row.get("concept_id")) for row in final_rows})
    catalog = export_catalog(final_rows)
    duration = round(time.perf_counter() - start, 4)
    report = {
        "phase": "DELTA RC2 1000 Concept Growth Run + Concept Catalog Export",
        "target_concepts": target,
        "starting_concept_count": starting_count,
        "final_concept_count": final_count,
        "new_concepts_added": max(0, final_count - starting_count),
        "approval_count_this_run": approvals,
        "existing_records_repaired": repaired_count,
        "repair_findings": repair_findings[:25],
        "rejected_concepts": len(rejected),
        "rejected_examples": rejected[:25],
        "duplicate_suppression_count": duplicate_suppression,
        "domains_covered": sorted(set(domain_for_record(row) for row in final_rows)),
        "required_domains": sorted(DOMAIN_TOPICS),
        "local_model_calls": 0,
        "average_latency_seconds": 0.0,
        "duration_seconds": duration,
        "catalog": catalog,
        "safety": {**SAFETY, "deleted_existing_concepts": deleted_existing},
        "quality_policy": {
            "minimum_related_concepts": 4,
            "rejects_vague_names": True,
            "rejects_keyword_crumbs": True,
            "repairs_existing_related_concepts": True,
        },
        "recommendation": "READY_FOR_OPERATOR_INQUIRY_TESTING_WITH_1000_NONCANONICAL_CONCEPTS" if final_count >= target else "SAFE_STOP_CONCEPT_TARGET_NOT_REACHED",
    }
    write_reports(report)
    return report


def export_catalog(rows: list[dict[str, Any]]) -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    approved = [row for row in rows if row.get("approval_status") == "approved_noncanonical" and row.get("canonical") is False]
    approved.sort(key=lambda row: (domain_for_record(row), str(row.get("concept_name", ""))))
    jsonl_path = DATA / "rc2_concept_catalog.jsonl"
    md_path = DATA / "rc2_concept_catalog.md"
    summary_path = DATA / "rc2_concept_summary.json"
    write_jsonl(jsonl_path, approved)
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in approved:
        by_domain[domain_for_record(row)].append(row)
    lines = ["# RC2 Concept Catalog", "", f"Total approved noncanonical concepts: {len(approved)}", ""]
    for domain in sorted(by_domain):
        lines.extend([f"## {title_case(domain)}", ""])
        for row in by_domain[domain]:
            lines.extend([
                f"### {row.get('concept_name')}",
                f"- Type/domain: {row.get('concept_type')} / {domain}",
                f"- Definition: {row.get('short_definition')}",
                f"- Key propositions: {'; '.join(str(item) for item in row.get('propositions', [])[:3])}",
                f"- Related concepts: {', '.join(str(item) for item in row.get('related_concepts', [])[:10])}",
                f"- Examples/explains: {', '.join(str(item) for item in (row.get('examples') or row.get('explains') or [])[:3])}",
                f"- Confidence/quality: {row.get('quality_score', 'not_scored')} / {row.get('uncertainty')}",
                f"- Source model: {row.get('source_model_id')}",
                f"- Status: {row.get('approval_status')} (canonical={row.get('canonical')})",
                f"- Rollback/version id: {row.get('rollback_handle')}",
                "",
            ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "catalog_count": len(approved),
        "domains": {domain: len(items) for domain, items in sorted(by_domain.items())},
        "paths": {
            "jsonl": str(jsonl_path),
            "markdown": str(md_path),
            "summary": str(summary_path),
        },
        "safety": SAFETY,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def write_reports(report: dict[str, Any]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "RC2_1000_CONCEPT_GROWTH_RUN.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "RC2_CONCEPT_CATALOG_EXPORT.json").write_text(json.dumps(report["catalog"], indent=2, sort_keys=True), encoding="utf-8")
    md = [
        "# RC2 1000 Concept Growth Run",
        "",
        f"Starting concept count: {report['starting_concept_count']}",
        f"Final concept count: {report['final_concept_count']}",
        f"New concepts added: {report['new_concepts_added']}",
        f"Rejected concepts: {report['rejected_concepts']}",
        f"Duplicate suppression count: {report['duplicate_suppression_count']}",
        f"Existing records repaired: {report['existing_records_repaired']}",
        f"Local model calls: {report['local_model_calls']}",
        f"Average latency seconds: {report['average_latency_seconds']}",
        "",
        "## Domains Covered",
        "",
        *[f"- {domain}" for domain in report["domains_covered"]],
        "",
        "## Safety",
        "",
        *[f"- {key}: {value}" for key, value in report["safety"].items()],
        "",
        f"Recommendation: {report['recommendation']}",
    ]
    (REPORTS / "RC2_1000_CONCEPT_GROWTH_RUN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    cat_md = [
        "# RC2 Concept Catalog Export",
        "",
        f"Catalog count: {report['catalog']['catalog_count']}",
        f"JSONL: {report['catalog']['paths']['jsonl']}",
        f"Markdown: {report['catalog']['paths']['markdown']}",
        f"Summary: {report['catalog']['paths']['summary']}",
    ]
    (REPORTS / "RC2_CONCEPT_CATALOG_EXPORT.md").write_text("\n".join(cat_md) + "\n", encoding="utf-8")
    continuation = [
        "# Continuation: RC2 1000 Concept Growth",
        "",
        f"Final concept count: {report['final_concept_count']}",
        f"New concepts added: {report['new_concepts_added']}",
        f"Catalog markdown: {report['catalog']['paths']['markdown']}",
        "",
        "Safety: no training, no canonical writes, no provider/API calls, no scheduler, no HYB1 promotion.",
        "",
        "Next recommended step: operator inquiry testing against the 1000-concept noncanonical catalog.",
    ]
    (DOCS / "continuation_rc2_1000_concept_growth.md").write_text("\n".join(continuation) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_growth(), indent=2, sort_keys=True))

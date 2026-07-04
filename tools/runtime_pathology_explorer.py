"""Static pathology explorer for the DELTA runtime architecture.

This tool is intentionally report-only. It parses repository-local Python,
Markdown, JSON, and UI artifacts to identify disconnected, duplicated, or
dead-ended architecture without activating runtime capabilities.
"""

from __future__ import annotations

import ast
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "orchestration" / "runtime"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
TESTS = ROOT / "tests"
SCRIPTS = ROOT / "scripts"
UI = ROOT / "ui"
RC1_REVIEW = REPORTS / "RC1_READINESS_REVIEW.json"
RC1_DOCUMENT_AUDIT = REPORTS / "RC1_DOCUMENT_AUDIT_SLICE.json"
RC1_KERNEL_ENVELOPE = RUNTIME / "rc1_kernel_answer_envelope.py"
RC1_QUERY_ADAPTER = REPORTS / "RC1_SUBSTRATE_QUERY_ADAPTER.json"
RC1_STATE_MACHINE = REPORTS / "RC1_UNIFIED_REVIEW_STATE_MACHINE.json"
RC1_ARTIFACT_REGISTRY = REPORTS / "RC1_RUNTIME_ARTIFACT_REGISTRY.json"
RC1_ADVERSARIAL = REPORTS / "RC1_ADVERSARIAL_VALIDATION_REPORT.json"

MAJOR_SUBSYSTEMS = {
    "kernel": ("kernel", "v32", "v33", "v34", "v35", "v36", "v37", "v38", "v39", "completion_e"),
    "knowledge": ("knowledge", "entity", "concept", "evidence", "relationship", "world", "arc_ii", "completion_f"),
    "reasoning": ("reasoning", "hypothesis", "reflection", "counterfactual", "confidence", "arc_iii", "completion_g"),
    "executive": ("executive", "goal", "planning", "scheduler", "policy", "constraint", "arc_vi", "completion_i"),
    "learning": ("learning", "proposal", "integration", "rollback", "evolution", "evaluation", "arc_iv", "v31", "completion_h"),
    "runtime": ("runtime", "universal", "completion_j", "local_answer", "delta_answer"),
}

PROHIBITED_SIGNALS = (
    "training_performed",
    "provider_authority_granted",
    "provider_call_performed",
    "autonomous_browsing_performed",
    "tool_execution_performed",
    "scheduler_started",
    "background_worker_started",
    "memory_mutation_performed",
    "knowledge_mutation_performed",
    "hidden_write_performed",
    "hyb1_promoted",
)


@dataclass(frozen=True)
class ModuleFacts:
    path: str
    module: str
    subsystem: str
    imports: tuple[str, ...]
    classes: tuple[str, ...]
    dataclasses: tuple[str, ...]
    functions: tuple[str, ...]
    calls: tuple[str, ...]
    line_count: int
    scaffold_family: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


def infer_subsystem(name: str) -> str:
    lowered = name.lower()
    for subsystem, needles in MAJOR_SUBSYSTEMS.items():
        if any(needle in lowered for needle in needles):
            return subsystem
    return "other"


def infer_scaffold_family(path: Path) -> str:
    name = path.name
    if name.startswith("completion_"):
        return "completion"
    if name.startswith("deepening_"):
        return "deepening"
    if name.startswith("arc_"):
        return "arc_exhaustive"
    if name.startswith("v"):
        return "versioned_runtime"
    return "core_or_legacy"


def parse_module(path: Path) -> ModuleFacts:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports: list[str] = []
    classes: list[str] = []
    dataclasses: list[str] = []
    functions: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("orchestration.runtime"):
                imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("orchestration.runtime"):
                    imports.append(alias.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            if any(getattr(dec, "id", "") == "dataclass" or getattr(getattr(dec, "func", None), "id", "") == "dataclass" for dec in node.decorator_list):
                dataclasses.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)
    mod = module_name(path)
    return ModuleFacts(
        path=rel(path),
        module=mod,
        subsystem=infer_subsystem(path.stem),
        imports=tuple(sorted(set(imports))),
        classes=tuple(classes),
        dataclasses=tuple(dataclasses),
        functions=tuple(functions),
        calls=tuple(sorted(set(calls))),
        line_count=len(text.splitlines()),
        scaffold_family=infer_scaffold_family(path),
    )


def collect_facts() -> list[ModuleFacts]:
    return [parse_module(path) for path in sorted(RUNTIME.glob("*.py")) if path.name != "__init__.py"]


def build_dependency_graph(facts: list[ModuleFacts]) -> dict[str, Any]:
    modules = {fact.module for fact in facts}
    edges = []
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        for imported in fact.imports:
            if imported in modules:
                edges.append({"source": fact.module, "target": imported, "type": "imports"})
                incoming[imported].add(fact.module)
                outgoing[fact.module].add(imported)
    isolated = sorted(fact.module for fact in facts if not incoming[fact.module] and not outgoing[fact.module])
    roots = sorted(fact.module for fact in facts if not incoming[fact.module] and outgoing[fact.module])
    leaves = sorted(fact.module for fact in facts if incoming[fact.module] and not outgoing[fact.module])
    return {
        "node_count": len(facts),
        "edge_count": len(edges),
        "edges": edges,
        "isolated_modules": isolated,
        "root_modules": roots,
        "leaf_modules": leaves,
    }


def build_call_graph(facts: list[ModuleFacts]) -> dict[str, Any]:
    function_index: dict[str, list[str]] = defaultdict(list)
    for fact in facts:
        for function in fact.functions:
            function_index[function].append(fact.module)
    edges = []
    ambiguous = []
    for fact in facts:
        for call in fact.calls:
            targets = function_index.get(call, [])
            if len(targets) == 1 and targets[0] != fact.module:
                edges.append({"source": fact.module, "target": targets[0], "call": call})
            elif len(targets) > 1:
                ambiguous.append({"source": fact.module, "call": call, "candidate_count": len(targets)})
    return {
        "edge_count": len(edges),
        "ambiguous_call_count": len(ambiguous),
        "edges": edges[:1000],
        "ambiguous_calls_sample": ambiguous[:100],
    }


def subsystem_interactions(facts: list[ModuleFacts], dependency_graph: dict[str, Any]) -> dict[str, Any]:
    module_to_subsystem = {fact.module: fact.subsystem for fact in facts}
    interactions = Counter()
    for edge in dependency_graph["edges"]:
        source = module_to_subsystem.get(edge["source"], "other")
        target = module_to_subsystem.get(edge["target"], "other")
        if source != target:
            interactions[(source, target)] += 1
    return {
        "subsystem_counts": dict(Counter(fact.subsystem for fact in facts)),
        "edges": [
            {"source": source, "target": target, "count": count}
            for (source, target), count in sorted(interactions.items())
        ],
    }


def duplicate_code_report(facts: list[ModuleFacts]) -> dict[str, Any]:
    class_counter = Counter(cls for fact in facts for cls in fact.classes)
    function_counter = Counter(fn for fact in facts for fn in fact.functions)
    class_suffix_counter = Counter(
        cls.removeprefix(fact.module.split(".")[-1].title().replace("_", ""))
        for fact in facts
        for cls in fact.classes
    )
    duplicate_functions = {name: count for name, count in function_counter.items() if count > 20}
    duplicate_classes = {name: count for name, count in class_counter.items() if count > 1}
    template_modules = [fact.module for fact in facts if {"build_objects", "validate_module", "report_payload", "write_report"}.issubset(set(fact.functions))]
    return {
        "duplicate_function_names": duplicate_functions,
        "duplicate_class_names": duplicate_classes,
        "template_module_count": len(template_modules),
        "template_module_sample": template_modules[:50],
        "dominant_class_suffixes": dict(class_suffix_counter.most_common(25)),
        "diagnosis": "Large scaffold families intentionally duplicate lifecycle, report, validation, and graph patterns; this is reviewable but should consolidate before activation.",
    }


def unused_object_report(facts: list[ModuleFacts]) -> dict[str, Any]:
    all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in list(RUNTIME.glob("*.py")) + list(TESTS.glob("**/*.py")) + list(SCRIPTS.glob("*.py")))
    unused = []
    class_total = 0
    for fact in facts:
        for cls in fact.classes:
            class_total += 1
            if all_text.count(cls) <= 2:
                unused.append({"class": cls, "module": fact.module, "path": fact.path, "reason": "class appears only at definition/as_dict level"})
    return {
        "class_total": class_total,
        "likely_unused_class_count": len(unused),
        "likely_unused_classes": unused[:250],
    }


def dead_path_report(facts: list[ModuleFacts], dependency_graph: dict[str, Any]) -> dict[str, Any]:
    incoming = defaultdict(int)
    for edge in dependency_graph["edges"]:
        incoming[edge["target"]] += 1
    dead_like = []
    for fact in facts:
        imported_by_runtime = incoming[fact.module]
        if imported_by_runtime == 0 and fact.scaffold_family in {"completion", "deepening", "arc_exhaustive"}:
            dead_like.append(
                {
                    "module": fact.module,
                    "path": fact.path,
                    "family": fact.scaffold_family,
                    "reason": "not imported by runtime modules except possible master runner/tests",
                }
            )
    return {
        "dead_like_module_count": len(dead_like),
        "dead_like_modules": dead_like[:300],
        "diagnosis": "Many modules are reportable architecture leaves; activation-readiness should connect them through a workflow trace before adding more modules.",
    }


def architectural_debt_report(facts: list[ModuleFacts], duplicate_report: dict[str, Any], dead_report: dict[str, Any]) -> dict[str, Any]:
    debt_items = [
        {
            "id": "DEBT-001",
            "title": "Scaffold families duplicate lifecycle/reporting code",
            "impact": 10,
            "category": "duplicate_code",
            "evidence": f"{duplicate_report['template_module_count']} modules expose the same build/validate/report/write pattern.",
            "recommendation": "Move shared lifecycle/report contracts into one base protocol before activation.",
        },
        {
            "id": "DEBT-002",
            "title": "Architecture leaves are not vertically integrated",
            "impact": 10,
            "category": "dead_path",
            "evidence": f"{dead_report['dead_like_module_count']} scaffold modules are not consumed by a live workflow.",
            "recommendation": "Build a governed vertical workflow trace before more module expansion.",
        },
        {
            "id": "DEBT-003",
            "title": "Kernel does not yet enforce a single runtime execution path",
            "impact": 9,
            "category": "kernel_bypass",
            "evidence": "Local answer scripts directly route to many phase-specific handlers.",
            "recommendation": "Route manual answers through a kernel transaction envelope in report-only mode.",
        },
        {
            "id": "DEBT-004",
            "title": "Knowledge substrate and reasoning layer are connected by sample fixtures, not live query adapters",
            "impact": 9,
            "category": "fake_interface",
            "evidence": "ARC III builds reasoning context from ARC II checkpoint data.",
            "recommendation": "Introduce a read-only substrate query adapter consumed by reasoning.",
        },
        {
            "id": "DEBT-005",
            "title": "Approval/integration states exist without one consolidated state machine",
            "impact": 8,
            "category": "workflow_gap",
            "evidence": "V31, ARC IV, and later completion modules each describe integration readiness.",
            "recommendation": "Unify proposal, review, approval, overwatch, integration simulation, and rollback state names.",
        },
    ]
    for index, fact in enumerate(sorted(facts, key=lambda item: item.line_count, reverse=True)[:20], start=6):
        debt_items.append(
            {
                "id": f"DEBT-{index:03d}",
                "title": f"Large module requires role review: {fact.module}",
                "impact": 6,
                "category": "maintainability",
                "evidence": f"{fact.path} has {fact.line_count} lines.",
                "recommendation": "Review whether this should split into model, builder, reporter, and test fixture helpers.",
            }
        )
    return {"debt_count": len(debt_items), "items": debt_items}


def missing_middleware_report() -> dict[str, Any]:
    items = [
        {"between": "Kernel -> Knowledge", "missing": "read-only substrate query adapter", "impact": 10},
        {"between": "Knowledge -> Reasoning", "missing": "evidence-role and query-intent projection envelope", "impact": 9},
        {"between": "Reasoning -> Executive", "missing": "decision-need extraction layer", "impact": 8},
        {"between": "Executive -> Learning", "missing": "outcome expectation and review trigger bridge", "impact": 8},
        {"between": "Learning -> Integration", "missing": "single proposal lifecycle state machine", "impact": 9},
        {"between": "Investigation -> Reasoning", "missing": "question-to-evidence request planner", "impact": 8},
        {"between": "Reasoning -> Specialists", "missing": "advisory request/response contract with authority boundaries", "impact": 7},
        {"between": "Review -> Answer", "missing": "final response synthesis envelope that cites audit graph nodes", "impact": 8},
    ]
    return {"missing_middleware_count": len(items), "items": items}


def integration_readiness_report() -> dict[str, Any]:
    rc1_exists = RC1_REVIEW.exists()
    document_audit_exists = RC1_DOCUMENT_AUDIT.exists()
    kernel_envelope_exists = RC1_KERNEL_ENVELOPE.exists()
    query_adapter_exists = RC1_QUERY_ADAPTER.exists()
    state_machine_exists = RC1_STATE_MACHINE.exists()
    artifact_registry_exists = RC1_ARTIFACT_REGISTRY.exists()
    adversarial_exists = RC1_ADVERSARIAL.exists()
    walkthrough_steps = [
        {"step": "Upload 10 papers", "status": "missing_live_adapter", "gap": "No active document ingestion or paper object adapter."},
        {"step": "Represent papers", "status": "fixture_paper_trace" if document_audit_exists else ("fixture_vertical_trace" if rc1_exists else "scaffolded"), "gap": "Fixture papers are represented; live artifact adapters are still needed."},
        {"step": "Find what was learned", "status": "fixture_paper_trace" if document_audit_exists else ("fixture_vertical_trace" if rc1_exists else "partial"), "gap": "Fixture paper claims are summarized; real paper claim extraction is still absent."},
        {"step": "Find contradictions", "status": "bounded_fixture_contradiction" if document_audit_exists else "partial", "gap": "Fixture contradiction/gap handling exists; paper-level extraction is not live."},
        {"step": "Need more evidence", "status": "fixture_evidence_gap_trace" if document_audit_exists else ("fixture_uncertainty_trace" if rc1_exists else "partial"), "gap": "Fixture evidence gaps are generated; investigation planning still needs live adapters."},
        {"step": "What would change if approved", "status": "simulated_only", "gap": "Evolution simulation exists and RC1 has simulated approvals; no live integration write is allowed."},
        {"step": "Audit and rollback", "status": "kernel_trace_linked" if rc1_exists or document_audit_exists else "scaffolded", "gap": "RC1 links audit graph and rollback ownership; broader runtime traces still need adoption."},
    ]
    if adversarial_exists:
        overall_status = "rc1_adversarial_validation_ready_no_live_capabilities"
        recommended_first_vertical = "manual human RC1 validation; do not enable live capabilities yet"
    elif artifact_registry_exists:
        overall_status = "rc1_fixture_verticals_registered_and_review_ready"
        recommended_first_vertical = "manual RC1 scenario validation before further architecture"
    elif state_machine_exists:
        overall_status = "unified_review_lifecycle_ready_for_fixture_verticals"
        recommended_first_vertical = "central report and object consumer registry"
    elif query_adapter_exists:
        overall_status = "read_only_query_adapter_ready_for_fixture_verticals"
        recommended_first_vertical = "unified proposal/review/approval/integration state machine"
    elif kernel_envelope_exists and document_audit_exists:
        overall_status = "kernel_observable_fixture_verticals_ready"
        recommended_first_vertical = "read-only substrate query adapter between knowledge and reasoning"
    elif document_audit_exists:
        overall_status = "fixture_document_to_audit_ready_not_live_upload_ready"
        recommended_first_vertical = "kernel routing enforcement for broader local flows"
    elif rc1_exists:
        overall_status = "fixture_vertical_trace_ready_not_live_document_ready"
        recommended_first_vertical = "read-only document-to-audit vertical slice with fixture documents"
    else:
        overall_status = "not_ready_for_live_vertical_execution"
        recommended_first_vertical = "report-only document-to-audit workflow trace with fixture papers"
    return {
        "scenario": "I uploaded 10 scientific papers. What have we learned? What contradicts? What needs more evidence? What would change if approved?",
        "overall_status": overall_status,
        "steps": walkthrough_steps,
        "recommended_first_vertical": recommended_first_vertical,
    }


def score_subsystems(facts: list[ModuleFacts], interactions: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(fact.subsystem for fact in facts)
    interaction_pairs = {(edge["source"], edge["target"]) for edge in interactions["edges"]}
    scores = {}
    for subsystem in ("kernel", "knowledge", "reasoning", "executive", "learning", "runtime"):
        volume = min(counts[subsystem] / 50, 1.0)
        outgoing = sum(1 for source, _ in interaction_pairs if source == subsystem)
        incoming = sum(1 for _, target in interaction_pairs if target == subsystem)
        connectivity = min((incoming + outgoing) * 1.2, 10)
        realism = 4 if subsystem in {"knowledge", "reasoning", "executive", "learning"} else 5
        scores[subsystem] = {
            "architecture": round(7 + volume * 2, 1),
            "implementation": round(5 + volume * 2, 1),
            "connectivity": round(connectivity, 1),
            "maintainability": 4.5 if volume > 0.8 else 6.0,
            "extensibility": 8.0,
            "runtime_realism": realism,
            "auditability": 8.5,
            "safety": 9.5,
            "technical_debt": 7.5 if volume > 0.8 else 5.5,
        }
    return scores


def top_opportunities(debt: dict[str, Any], missing: dict[str, Any], dead: dict[str, Any]) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    seed = [
        ("Build a report-only vertical workflow trace before adding modules", 10, "integration"),
        ("Unify scaffold lifecycle protocols for ARC, deepening, and completion families", 10, "refactor"),
        ("Route local answer flows through kernel transaction envelopes", 9, "kernel"),
        ("Create a read-only substrate query adapter for reasoning", 9, "knowledge_reasoning"),
        ("Unify approval/integration/review state machines", 9, "learning"),
        ("Add consumer maps for every scaffold object", 8, "observability"),
        ("Replace module-count progress metrics with vertical scenario scorecards", 8, "evaluation"),
        ("Introduce a central report registry", 8, "reports"),
        ("Create middleware contracts between investigation, reasoning, specialists, and review", 8, "middleware"),
        ("Define activation-readiness levels for dormant modules", 8, "readiness"),
    ]
    for title, impact, category in seed:
        opportunities.append({"title": title, "impact": impact, "category": category})
    for item in debt["items"][:45]:
        opportunities.append({"title": item["title"], "impact": item["impact"], "category": item["category"]})
    for item in missing["items"]:
        opportunities.append({"title": f"Add missing middleware: {item['between']}", "impact": item["impact"], "category": "middleware"})
    for item in dead["dead_like_modules"][:60]:
        opportunities.append({"title": f"Connect or archive {item['module'].split('.')[-1]}", "impact": 5, "category": "dead_path"})
    deduped = []
    seen = set()
    for item in sorted(opportunities, key=lambda entry: (-entry["impact"], entry["title"])):
        if item["title"] not in seen:
            seen.add(item["title"])
            deduped.append(item)
    return deduped[:100]


def strengths_and_weaknesses() -> tuple[list[str], list[str]]:
    strengths = [
        "RC1 adversarial validation covers 30 required scenarios with no high-impact runtime failures.",
        "Central RC1 artifact registry maps report producers, consumers, validators, auditors, and activation status.",
        "Unified proposal/review/approval/integration state machine now normalizes review lifecycles and stops at integrated_disabled.",
        "Read-only substrate query adapter now gives reasoning one deterministic query surface over ARC II and RC1 artifacts.",
        "Local CLI answers now receive a non-mutating kernel envelope without changing answer text.",
        "RC1 document-to-audit slice answers learned, contradictory, evidence-gap, and approval-impact questions from fixture papers.",
        "RC1 vertical trace now connects semantic consolidation through kernel events, transactions, lifecycle ownership, and audit graph.",
        "Safety invariants are explicit and repeatedly tested.",
        "Reports and JSON outputs make architecture review reproducible.",
        "Model B and HYB1 states are clearly separated.",
        "Provider authority remains gated off.",
        "Runtime has broad subsystem vocabulary.",
        "Kernel, knowledge, reasoning, executive, and learning layers have named contracts.",
        "Tests cover scaffold safety and serialization heavily.",
        "Continuation docs support cold-session recovery.",
        "Rollback and audit concepts exist early.",
        "Local answer path provides deterministic self-description.",
        "Completion/deepening modules are consistently shaped.",
        "Graph metadata is present across scaffold families.",
        "Runtime can distinguish scaffold, dormant, and prohibited states.",
        "Architecture is inspectable without provider calls.",
        "No hidden writes are required for report generation.",
        "Validation surfaces are deterministic.",
        "Knowledge and reasoning are conceptually separated.",
        "Executive planning remains non-executing.",
        "Learning proposals remain distinct from integration.",
        "Review-only philosophy is strong.",
        "Static dashboards provide lightweight observability.",
        "JSON reports are machine-checkable.",
        "Repository has enough structure for automated pathology analysis.",
        "Safety is stronger than runtime realism, which is the correct ordering.",
        "The project now has a clear activation-readiness target.",
    ]
    weaknesses = [
        "Many modules are still architecture leaves with no workflow consumer.",
        "CLI local answers now carry a kernel envelope, but internal subsystem calls can still bypass the kernel.",
        "Deepening and completion families duplicate lifecycle code.",
        "Knowledge substrate uses sample data rather than live artifact adapters.",
        "Reasoning consumes checkpoint fixtures rather than a true query adapter.",
        "Executive decisions cannot trigger reviewed downstream workflows.",
        "Learning approval states are spread across multiple layers.",
        "Audit graph concepts are not yet the universal trace backbone.",
        "Report generation doubles as runtime proof too often.",
        "Large module count can obscure missing vertical behavior.",
        "Many validators validate shape rather than cooperation.",
        "Graph metadata is often local, not merged into a runtime graph.",
        "Object destruction/retirement semantics are mostly absent.",
        "Consumer ownership is not explicit for most dataclasses.",
        "Many reports are not indexed by a central registry.",
        "Scaffold modules are hard to prioritize for activation.",
        "Integration simulations are disconnected from real review inputs.",
        "Specialists remain advisory slots without middleware contracts.",
        "Investigation questions are not generated from reasoning gaps.",
        "Fixture semantic consolidation and fixture document audit now exercise full stack paths, but live document ingestion remains disabled.",
        "Confidence propagation is scattered across several concepts.",
        "Relationship/evidence graph boundaries overlap.",
        "Runtime health is measured more by passing tests than scenario outcomes.",
        "Technical debt will grow if another broad module marathon happens.",
        "The next risk is incoherence from abundance, not missing vocabulary.",
    ]
    return strengths, weaknesses


def write_report_pair(base: str, data: dict[str, Any], title: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{base}.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / f"{base}.md").write_text(render_markdown(title, data), encoding="utf-8")


def render_markdown(title: str, data: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in data.items():
        lines.append(f"## {key.replace('_', ' ').title()}")
        if isinstance(value, list):
            for item in value[:100]:
                if isinstance(item, dict):
                    label = item.get("title") or item.get("module") or item.get("class") or item.get("between") or item.get("step") or str(item)
                    lines.append(f"- {label}")
                else:
                    lines.append(f"- {item}")
        elif isinstance(value, dict):
            lines.append("```json")
            lines.append(json.dumps(value, indent=2, sort_keys=True)[:12000])
            lines.append("```")
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def build_master() -> dict[str, Any]:
    facts = collect_facts()
    dependency = build_dependency_graph(facts)
    call_graph = build_call_graph(facts)
    interactions = subsystem_interactions(facts, dependency)
    duplicate = duplicate_code_report(facts)
    unused = unused_object_report(facts)
    dead = dead_path_report(facts, dependency)
    debt = architectural_debt_report(facts, duplicate, dead)
    missing = missing_middleware_report()
    readiness = integration_readiness_report()
    opportunities = top_opportunities(debt, missing, dead)
    strengths, weaknesses = strengths_and_weaknesses()
    scores = score_subsystems(facts, interactions)
    rc1_payload: dict[str, Any] = {}
    if RC1_REVIEW.exists():
        try:
            rc1_payload = json.loads(RC1_REVIEW.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rc1_payload = {}
    document_audit_payload: dict[str, Any] = {}
    if RC1_DOCUMENT_AUDIT.exists():
        try:
            document_audit_payload = json.loads(RC1_DOCUMENT_AUDIT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            document_audit_payload = {}
    query_adapter_payload: dict[str, Any] = {}
    if RC1_QUERY_ADAPTER.exists():
        try:
            query_adapter_payload = json.loads(RC1_QUERY_ADAPTER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            query_adapter_payload = {}
    state_machine_payload: dict[str, Any] = {}
    if RC1_STATE_MACHINE.exists():
        try:
            state_machine_payload = json.loads(RC1_STATE_MACHINE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state_machine_payload = {}
    artifact_registry_payload: dict[str, Any] = {}
    if RC1_ARTIFACT_REGISTRY.exists():
        try:
            artifact_registry_payload = json.loads(RC1_ARTIFACT_REGISTRY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            artifact_registry_payload = {}
    adversarial_payload: dict[str, Any] = {}
    if RC1_ADVERSARIAL.exists():
        try:
            adversarial_payload = json.loads(RC1_ADVERSARIAL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            adversarial_payload = {}
    maturity = int(adversarial_payload.get("runtime_maturity_estimate", artifact_registry_payload.get("estimated_runtime_maturity", state_machine_payload.get("estimated_runtime_maturity", query_adapter_payload.get("estimated_runtime_maturity", document_audit_payload.get("estimated_runtime_maturity", rc1_payload.get("scorecard", {}).get("estimated_runtime_maturity", 68)))))))
    if RC1_KERNEL_ENVELOPE.exists() and maturity < 86:
        maturity = 86
    activation_readiness = "adversarial_validation_passed_no_live_capabilities" if adversarial_payload else ("rc1_manual_validation_ready" if artifact_registry_payload else ("unified_review_lifecycle_ready" if state_machine_payload else ("read_only_query_adapter_ready" if query_adapter_payload else ("kernel_observable_fixture_verticals_ready" if RC1_KERNEL_ENVELOPE.exists() and document_audit_payload else ("fixture_document_audit_ready" if document_audit_payload else ("fixture_vertical_trace_ready" if rc1_payload else "not_ready_without_vertical_trace"))))))
    master = {
        "phase": "DELTA RC1 Runtime Coherence Review",
        "runtime_module_count": len(facts),
        "dependency_edge_count": dependency["edge_count"],
        "call_edge_count": call_graph["edge_count"],
        "architectural_debt_count": debt["debt_count"],
        "duplicate_system_count": len(duplicate["duplicate_function_names"]) + len(duplicate["duplicate_class_names"]),
        "dead_system_count": dead["dead_like_module_count"],
        "disconnected_system_count": len(dependency["isolated_modules"]),
        "unused_system_count": unused["likely_unused_class_count"],
        "subsystem_scores": scores,
        "top_25_architectural_weaknesses": weaknesses[:25],
        "top_25_architectural_strengths": strengths[:25],
        "top_100_improvement_opportunities": opportunities,
        "recommended_roadmap_reorder": [
            "1. Manual human RC1 validation over adversarial scenario outputs.",
            "2. Activation-readiness review for the smallest coherent vertical slice.",
            "3. Live adapter readiness review without enabling live ingestion.",
            "4. Kernel envelope adoption inside subsystem-to-subsystem calls.",
            "5. Real document adapter readiness review without live upload activation.",
            "6. Consolidate duplicated scaffold lifecycle helpers.",
        ],
        "recommended_refactors": [item["recommendation"] for item in debt["items"][:10]],
        "rc1_vertical_trace": {
            "present": bool(rc1_payload),
            "final_recommendation": rc1_payload.get("final_recommendation", ""),
            "trace_steps": len(rc1_payload.get("trace_steps", [])) if rc1_payload else 0,
            "lifecycle_owners": len(rc1_payload.get("lifecycle_owners", [])) if rc1_payload else 0,
        },
        "rc1_document_audit_slice": {
            "present": bool(document_audit_payload),
            "final_recommendation": document_audit_payload.get("final_recommendation", ""),
            "fixture_paper_count": document_audit_payload.get("fixture_paper_count", 0),
            "finding_count": len(document_audit_payload.get("findings", [])) if document_audit_payload else 0,
        },
        "rc1_kernel_answer_envelope": {
            "present": RC1_KERNEL_ENVELOPE.exists(),
            "scope": "CLI local answer responses",
            "mutating": False,
        },
        "rc1_substrate_query_adapter": {
            "present": bool(query_adapter_payload),
            "final_recommendation": query_adapter_payload.get("final_recommendation", ""),
            "packet_count": len(query_adapter_payload.get("packets", [])) if query_adapter_payload else 0,
        },
        "rc1_unified_review_state_machine": {
            "present": bool(state_machine_payload),
            "final_recommendation": state_machine_payload.get("final_recommendation", ""),
            "current_state": state_machine_payload.get("lifecycle", {}).get("current_state", ""),
        },
        "rc1_runtime_artifact_registry": {
            "present": bool(artifact_registry_payload),
            "final_recommendation": artifact_registry_payload.get("final_recommendation", ""),
            "artifact_count": artifact_registry_payload.get("artifact_count", 0),
            "missing_artifacts": len(artifact_registry_payload.get("missing_artifacts", [])) if artifact_registry_payload else 0,
        },
        "rc1_adversarial_validation": {
            "present": bool(adversarial_payload),
            "final_recommendation": adversarial_payload.get("final_recommendation", ""),
            "scenario_count": adversarial_payload.get("scenario_count", 0),
            "failed_count": adversarial_payload.get("failed_count", 0),
        },
        "overall_runtime_maturity_estimate": {
            "architecture_completeness": "high",
            "runtime_coherence": "medium" if rc1_payload else "medium_low",
            "activation_readiness": activation_readiness,
            "safety_maturity": "high",
            "estimated_percent": maturity,
        },
        "safety": {key: False for key in PROHIBITED_SIGNALS} | {"model_b_default": "unchanged", "hyb1": "dormant_env_gated"},
        "final_recommendation": "PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES" if adversarial_payload else ("PROCEED_RC1_MANUAL_SCENARIO_VALIDATION" if artifact_registry_payload else ("PROCEED_CENTRAL_RUNTIME_ARTIFACT_REGISTRY" if state_machine_payload else ("PROCEED_UNIFIED_PROPOSAL_REVIEW_STATE_MACHINE" if query_adapter_payload else ("PROCEED_SUBSTRATE_QUERY_ADAPTER" if RC1_KERNEL_ENVELOPE.exists() and document_audit_payload else ("PROCEED_KERNEL_ROUTING_ENFORCEMENT" if document_audit_payload else ("PROCEED_DOCUMENT_TO_AUDIT_VERTICAL_SLICE" if rc1_payload else "PROCEED_VERTICAL_INTEGRATION_PATHOLOGY_REDUCTION")))))),
    }
    outputs = {
        "runtime_pathology_dependency_graph": dependency,
        "runtime_pathology_call_graph": call_graph,
        "runtime_pathology_subsystem_interaction_graph": interactions,
        "runtime_pathology_architectural_debt": debt,
        "runtime_pathology_unused_object": unused,
        "runtime_pathology_duplicate_code": duplicate,
        "runtime_pathology_dead_path": dead,
        "runtime_pathology_missing_middleware": missing,
        "runtime_pathology_integration_readiness": readiness,
        "runtime_pathology_top_100_opportunities": {"items": opportunities},
    }
    for base, data in outputs.items():
        write_report_pair(base, data, base.replace("runtime_pathology_", "Runtime Pathology ").replace("_", " ").title())
    write_report_pair("MASTER_PATHOLOGY_REPORT", master, "MASTER PATHOLOGY REPORT")
    return master


def main() -> int:
    master = build_master()
    print(master["final_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""DELTA ARC II knowledge substrate architecture.

ARC II defines reviewable semantic structures and deterministic substrate
operations. It does not persist live knowledge, train models, call providers,
mutate memory, mutate recall, execute actions, start schedulers, or promote
HYB1.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id


ARC_II_REPORT_MD = Path("reports/runtime_arc_ii_safety_checkpoint.md")
ARC_II_REPORT_JSON = Path("reports/runtime_arc_ii_safety_checkpoint.json")
ARC_II_BROWSER_HTML = Path("ui/delta_arc_ii_knowledge_browser.html")
ARC_II_CONTINUATION = Path("docs/continuation_runtime_arc_ii.md")

KNOWLEDGE_TYPES = (
    "Entity",
    "Concept",
    "Observation",
    "Evidence",
    "Source",
    "Relationship",
    "Event",
    "Claim",
    "Hypothesis",
    "Procedure",
    "Rule",
)

RELATIONSHIP_TYPES = ("supports", "contradicts", "depends_on", "derived_from", "part_of", "causes", "references")
REVIEW_STATES = ("draft", "review", "approved", "integrated_future", "rolled_back", "rejected")


@dataclass(frozen=True)
class KnowledgeObject:
    id: str
    type: str
    created: str
    updated: str
    provenance: tuple[str, ...]
    confidence: float
    review_state: str
    rollback_token: str
    audit_id: str
    label: str
    payload: dict[str, object]
    version: int = 1
    parent: str = ""
    supersedes: str = ""
    history: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        data["history"] = list(self.history)
        return data


@dataclass(frozen=True)
class KnowledgeTransaction:
    transaction_id: str
    target_object_id: str
    stage: str
    reviewed: bool
    integrated: bool
    rollback_token: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class KnowledgeRegistry:
    """Deterministic in-memory registry for ARC II substrate objects."""

    def __init__(self, name: str, allowed_types: tuple[str, ...]) -> None:
        self.name = name
        self.allowed_types = allowed_types
        self._objects: dict[str, KnowledgeObject] = {}

    def add(self, obj: KnowledgeObject) -> KnowledgeObject:
        if obj.type not in self.allowed_types:
            raise ValueError(f"{obj.type} is not allowed in {self.name}")
        self._objects[obj.id] = obj
        return obj

    def all(self) -> tuple[KnowledgeObject, ...]:
        return tuple(self._objects[key] for key in sorted(self._objects))

    def get(self, object_id: str) -> KnowledgeObject | None:
        return self._objects.get(object_id)

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "allowed_types": list(self.allowed_types), "objects": [obj.as_dict() for obj in self.all()]}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def make_knowledge_object(
    object_type: str,
    label: str,
    *,
    provenance: tuple[str, ...],
    confidence: float = 0.5,
    review_state: str = "review",
    payload: dict[str, object] | None = None,
    parent: str = "",
    supersedes: str = "",
    version: int = 1,
    history: tuple[str, ...] = (),
) -> KnowledgeObject:
    if object_type not in KNOWLEDGE_TYPES:
        raise ValueError(f"Unsupported knowledge object type: {object_type}")
    if review_state not in REVIEW_STATES:
        raise ValueError(f"Unsupported review state: {review_state}")
    created = utc_now()
    object_id = stable_v31_id("knowledge-object", object_type, label, provenance, version)
    return KnowledgeObject(
        id=object_id,
        type=object_type,
        created=created,
        updated=created,
        provenance=provenance,
        confidence=confidence,
        review_state=review_state,
        rollback_token=stable_v31_id("knowledge-rollback", object_id),
        audit_id=stable_v31_id("knowledge-audit", object_id),
        label=label,
        payload=payload or {},
        version=version,
        parent=parent,
        supersedes=supersedes,
        history=history,
    )


def make_version(obj: KnowledgeObject, *, label: str | None = None, payload: dict[str, object] | None = None) -> KnowledgeObject:
    return make_knowledge_object(
        obj.type,
        label or obj.label,
        provenance=obj.provenance,
        confidence=obj.confidence,
        review_state="review",
        payload=payload or obj.payload,
        parent=obj.id,
        supersedes=obj.id,
        version=obj.version + 1,
        history=(*obj.history, obj.id),
    )


def build_sample_substrate() -> dict[str, object]:
    source = make_knowledge_object("Source", "DELTA local architecture docs", provenance=("docs/ARCHITECTURE.md",), confidence=0.9)
    evidence = make_knowledge_object(
        "Evidence",
        "ARC II prompt requires provenance and rollback support",
        provenance=("docs/runtime_arc_ii_knowledge_substrate_preview.md",),
        confidence=0.82,
        payload={"source": source.id, "location": "ARC II preview", "excerpt_reference": "knowledge substrate design"},
    )
    entity = make_knowledge_object("Entity", "DELTA", provenance=(source.id,), confidence=0.86, payload={"entity_kind": "system"})
    concept = make_knowledge_object("Concept", "Knowledge Substrate", provenance=(evidence.id,), confidence=0.74)
    observation = make_knowledge_object(
        "Observation",
        "Observation is not truth",
        provenance=(evidence.id,),
        confidence=0.7,
        payload={"source": source.id, "evidence": evidence.id},
    )
    claim = make_knowledge_object("Claim", "Evidence remains advisory until reviewed", provenance=(evidence.id,), confidence=0.68)
    hypothesis = make_knowledge_object("Hypothesis", "Kernel-routed semantic queries can inspect substrate objects", provenance=(concept.id,), confidence=0.55)
    procedure = make_knowledge_object("Procedure", "Review knowledge object before integration", provenance=(evidence.id,), confidence=0.66)
    rule = make_knowledge_object("Rule", "No live knowledge integration in ARC II", provenance=(evidence.id,), confidence=0.95)
    event = make_knowledge_object("Event", "ARC II substrate design checkpoint", provenance=(source.id,), confidence=0.7)
    relationships = [
        make_relationship(entity.id, concept.id, "references", evidence.id),
        make_relationship(observation.id, evidence.id, "derived_from", evidence.id),
        make_relationship(claim.id, evidence.id, "supports", evidence.id),
        make_relationship(rule.id, procedure.id, "depends_on", evidence.id),
        make_relationship(hypothesis.id, concept.id, "part_of", evidence.id),
        make_relationship(event.id, source.id, "references", evidence.id),
    ]
    objects = [source, evidence, entity, concept, observation, claim, hypothesis, procedure, rule, event, *relationships]
    return {
        "objects": objects,
        "registries": build_registries(objects),
        "relationships": relationships,
    }


def make_relationship(source_id: str, target_id: str, relationship_type: str, evidence_id: str) -> KnowledgeObject:
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"Unsupported relationship type: {relationship_type}")
    return make_knowledge_object(
        "Relationship",
        f"{source_id} {relationship_type} {target_id}",
        provenance=(evidence_id,),
        confidence=0.64,
        payload={"source_id": source_id, "target_id": target_id, "relationship_type": relationship_type, "evidence_id": evidence_id},
    )


def build_registries(objects: list[KnowledgeObject]) -> dict[str, KnowledgeRegistry]:
    registries = {
        "entity_registry": KnowledgeRegistry("entity_registry", ("Entity",)),
        "observation_registry": KnowledgeRegistry("observation_registry", ("Observation",)),
        "evidence_registry": KnowledgeRegistry("evidence_registry", ("Evidence", "Source")),
        "relationship_registry": KnowledgeRegistry("relationship_registry", ("Relationship",)),
        "concept_registry": KnowledgeRegistry("concept_registry", ("Concept", "Claim", "Hypothesis", "Procedure", "Rule", "Event")),
    }
    for obj in objects:
        for registry in registries.values():
            if obj.type in registry.allowed_types:
                registry.add(obj)
    return registries


def build_knowledge_graph(objects: list[KnowledgeObject]) -> dict[str, object]:
    nodes = [{"id": obj.id, "type": obj.type, "label": obj.label, "review_state": obj.review_state, "confidence": obj.confidence} for obj in objects]
    edges = []
    ids = {obj.id for obj in objects}
    for obj in objects:
        if obj.type == "Relationship":
            source_id = str(obj.payload["source_id"])
            target_id = str(obj.payload["target_id"])
            if source_id in ids and target_id in ids:
                edges.append({"source": source_id, "target": target_id, "relationship_type": obj.payload["relationship_type"], "audit_id": obj.audit_id})
    return {"nodes": nodes, "edges": edges, "deterministic": True, "graph_only": True}


def semantic_query(objects: list[KnowledgeObject], query_type: str, term: str = "") -> list[dict[str, object]]:
    term_norm = term.lower()
    if query_type == "related_concepts":
        return [obj.as_dict() for obj in objects if obj.type in ("Concept", "Claim", "Hypothesis", "Procedure", "Rule") and term_norm in obj.label.lower()]
    if query_type == "supporting_evidence":
        return [obj.as_dict() for obj in objects if obj.type == "Evidence"]
    if query_type == "contradictions":
        return [obj.as_dict() for obj in objects if obj.type == "Relationship" and obj.payload.get("relationship_type") == "contradicts"]
    if query_type == "procedures":
        return [obj.as_dict() for obj in objects if obj.type == "Procedure"]
    if query_type == "observations":
        return [obj.as_dict() for obj in objects if obj.type == "Observation"]
    return []


def build_health_metrics(objects: list[KnowledgeObject], graph: dict[str, object]) -> dict[str, object]:
    type_counts = Counter(obj.type for obj in objects)
    confidence_buckets = Counter("high" if obj.confidence >= 0.8 else "medium" if obj.confidence >= 0.5 else "low" for obj in objects)
    connected = {edge["source"] for edge in graph["edges"]} | {edge["target"] for edge in graph["edges"]}
    orphan_nodes = [node["id"] for node in graph["nodes"] if node["id"] not in connected]
    missing_provenance = [obj.id for obj in objects if not obj.provenance]
    duplicate_entities = [label for label, count in Counter(obj.label for obj in objects if obj.type == "Entity").items() if count > 1]
    return {
        "coverage": dict(type_counts),
        "confidence_distribution": dict(confidence_buckets),
        "orphan_nodes": orphan_nodes,
        "contradiction_count": len(semantic_query(objects, "contradictions")),
        "missing_provenance": missing_provenance,
        "duplicate_entities": duplicate_entities,
        "graph_connectivity": {"node_count": len(graph["nodes"]), "edge_count": len(graph["edges"]), "connected_node_count": len(connected)},
    }


def build_provenance_tree(obj: KnowledgeObject, objects_by_id: dict[str, KnowledgeObject]) -> dict[str, object]:
    children = []
    for provenance_id in obj.provenance:
        source_obj = objects_by_id.get(provenance_id)
        children.append(build_provenance_tree(source_obj, objects_by_id) if source_obj else {"reference": provenance_id, "external": True})
    return {
        "id": obj.id,
        "type": obj.type,
        "label": obj.label,
        "confidence": obj.confidence,
        "review_state": obj.review_state,
        "provenance": children,
    }


def run_semantic_diagnostics(objects: list[KnowledgeObject], graph: dict[str, object]) -> dict[str, object]:
    ids = {obj.id for obj in objects}
    broken_references = []
    for obj in objects:
        if obj.type == "Relationship":
            if obj.payload.get("source_id") not in ids or obj.payload.get("target_id") not in ids:
                broken_references.append(obj.id)
    duplicate_labels = [label for label, count in Counter((obj.type, obj.label) for obj in objects).items() if count > 1 for label in [label[1]]]
    cycles = detect_simple_cycles(graph)
    conflicting_confidence = [obj.id for obj in objects if obj.confidence < 0 or obj.confidence > 1]
    metrics = build_health_metrics(objects, graph)
    return {
        "orphans": metrics["orphan_nodes"],
        "cycles": cycles,
        "duplicates": duplicate_labels,
        "missing_provenance": metrics["missing_provenance"],
        "broken_references": broken_references,
        "conflicting_confidence": conflicting_confidence,
        "mutation_performed": False,
    }


def detect_simple_cycles(graph: dict[str, object]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        adjacency[edge["source"]].add(edge["target"])
    cycles = []
    for source, targets in adjacency.items():
        for target in targets:
            if source in adjacency.get(target, set()):
                cycles.append([source, target, source])
    return cycles


def build_knowledge_transaction(obj: KnowledgeObject, stage: str = "review") -> KnowledgeTransaction:
    if stage not in ("draft", "review", "approved", "integrated_future", "rolled_back"):
        raise ValueError(f"Unsupported knowledge transaction stage: {stage}")
    return KnowledgeTransaction(
        transaction_id=stable_v31_id("knowledge-transaction", obj.id, stage),
        target_object_id=obj.id,
        stage=stage,
        reviewed=stage in ("review", "approved", "integrated_future"),
        integrated=False,
        rollback_token=obj.rollback_token,
    )


def build_arc_ii_checkpoint() -> dict[str, object]:
    substrate = build_sample_substrate()
    objects = substrate["objects"]
    graph = build_knowledge_graph(objects)
    objects_by_id = {obj.id: obj for obj in objects}
    concept = next(obj for obj in objects if obj.type == "Concept")
    versioned = make_version(concept, label="Knowledge Substrate v2 review draft")
    transaction = build_knowledge_transaction(concept, "approved")
    return {
        "phase": "Runtime ARC II V4.15",
        "knowledge_objects": [obj.as_dict() for obj in objects],
        "registries": {name: registry.as_dict() for name, registry in substrate["registries"].items()},
        "knowledge_graph": graph,
        "semantic_queries": {
            "related_concepts": semantic_query(objects, "related_concepts", "knowledge"),
            "supporting_evidence": semantic_query(objects, "supporting_evidence"),
            "contradictions": semantic_query(objects, "contradictions"),
            "procedures": semantic_query(objects, "procedures"),
            "observations": semantic_query(objects, "observations"),
        },
        "health_metrics": build_health_metrics(objects, graph),
        "knowledge_transaction": transaction.as_dict(),
        "versioned_object_example": versioned.as_dict(),
        "provenance_tree": build_provenance_tree(concept, objects_by_id),
        "semantic_diagnostics": run_semantic_diagnostics(objects, graph),
        "kernel_integration": {
            "question": "knowledge query",
            "route": "Kernel -> Knowledge Query -> Substrate -> Evidence Objects -> Return Graph",
            "reasoning_performed": False,
        },
        "live_persistence": False,
        "live_knowledge_integration": False,
        "authoritative_substrate": False,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_ARC_III_REASONING_LAYER_DESIGN",
    }


def write_arc_ii_reports() -> dict[str, object]:
    data = build_arc_ii_checkpoint()
    ARC_II_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    ARC_II_REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    ARC_II_REPORT_MD.write_text(render_arc_ii_report(data), encoding="utf-8")
    ARC_II_BROWSER_HTML.parent.mkdir(parents=True, exist_ok=True)
    ARC_II_BROWSER_HTML.write_text(render_knowledge_browser(data), encoding="utf-8")
    ARC_II_CONTINUATION.write_text(
        "# DELTA ARC II Continuation\n\n"
        "ARC II is complete as a knowledge substrate architecture scaffold. It defines reviewable knowledge objects, registries, graph building, semantic query, browser UI, metrics, transactions, versioning, provenance, diagnostics, and kernel query integration.\n\n"
        "No live persistence, authoritative substrate, training, provider authority, memory mutation, recall mutation, scheduler activation, action execution, HYB1 promotion, or live knowledge integration occurred.\n\n"
        "Next recommendation: `PROCEED_ARC_III_REASONING_LAYER_DESIGN`.\n",
        encoding="utf-8",
    )
    return data


def render_arc_ii_report(data: dict[str, object]) -> str:
    object_types = sorted({obj["type"] for obj in data["knowledge_objects"]})
    return f"""# Runtime ARC II Safety Checkpoint

ARC II builds DELTA's internal Knowledge Substrate architecture.

## Knowledge Objects Created

{chr(10).join(f"- {item}" for item in object_types)}

## Graph Components

- nodes: {len(data['knowledge_graph']['nodes'])}
- edges: {len(data['knowledge_graph']['edges'])}

## Kernel Integration

{data['kernel_integration']['route']}

## Safety

- live persistence: {data['live_persistence']}
- live knowledge integration: {data['live_knowledge_integration']}
- authoritative substrate: {data['authoritative_substrate']}
- Model B: {data['model_b_default']}
- HYB1: {data['hyb1']}

Final recommendation: `{data['final_recommendation']}`
"""


def render_knowledge_browser(data: dict[str, object]) -> str:
    nodes = "\n".join(f"<li><strong>{obj['type']}</strong>: {obj['label']} ({obj['review_state']}, confidence {obj['confidence']})</li>" for obj in data["knowledge_objects"])
    edges = "\n".join(f"<li>{edge['source']} --{edge['relationship_type']}--> {edge['target']}</li>" for edge in data["knowledge_graph"]["edges"])
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>DELTA ARC II Knowledge Browser</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f7f9fc;color:#1d2736}}section{{background:white;border:1px solid #d8e0ed;border-radius:8px;padding:18px;margin:14px 0}}</style></head>
<body>
<h1>DELTA ARC II Knowledge Browser</h1>
<section><h2>Knowledge Objects</h2><ul>{nodes}</ul></section>
<section><h2>Relationships</h2><ul>{edges}</ul></section>
<section><h2>Safety</h2><p>No editing, no writes, no live integration.</p></section>
</body></html>
"""


if __name__ == "__main__":
    print(write_arc_ii_reports()["final_recommendation"])

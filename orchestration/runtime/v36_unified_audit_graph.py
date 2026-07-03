"""Runtime ARC I V3.6 unified audit graph scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orchestration.runtime.v31_learning_opportunity import stable_v31_id


@dataclass(frozen=True)
class AuditNode:
    node_id: str
    node_type: str
    label: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuditEdge:
    source: str
    target: str
    relation: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class UnifiedAuditGraph:
    graph_id: str
    nodes: tuple[AuditNode, ...]
    edges: tuple[AuditEdge, ...]
    graph_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "graph_only": self.graph_only,
        }


def build_sample_audit_graph() -> UnifiedAuditGraph:
    node_types = ("experience", "proposal", "review", "integration_candidate", "rollback", "reasoning")
    nodes = tuple(AuditNode(stable_v31_id("audit-node", item), item, item.replace("_", " ").title()) for item in node_types)
    edges = tuple(AuditEdge(nodes[index].node_id, nodes[index + 1].node_id, "feeds") for index in range(len(nodes) - 1))
    return UnifiedAuditGraph(stable_v31_id("audit-graph", "arc-i-sample"), nodes, edges)

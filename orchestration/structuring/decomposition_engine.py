from __future__ import annotations

import hashlib
import re
from typing import List

from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskGraph, TaskNode, TaskType


class DecompositionEngine:
    """
    Build an explicit task graph from an inquiry + task type.
    """

    def decompose(self, inquiry: InquiryPacket, task_type: TaskType) -> TaskGraph:
        graph_id = f"graph:{hashlib.sha1((inquiry.inquiry_id + task_type.value).encode()).hexdigest()[:12]}"
        root_id = "root"

        nodes: List[TaskNode] = [
            TaskNode(
                node_id=root_id,
                label="root_task",
                task_type=task_type,
                metadata={"raw_text": inquiry.raw_text},
            )
        ]
        notes: List[str] = []

        if task_type == TaskType.COMPARISON:
            items = self._extract_comparison_items(inquiry.raw_text)
            for idx, item in enumerate(items):
                node_id = f"item_{idx}"
                nodes.append(
                    TaskNode(
                        node_id=node_id,
                        label=f"analyze:{item}",
                        task_type=TaskType.LOOKUP,
                        depends_on=[root_id],
                        metadata={"item": item},
                    )
                )
            nodes.append(
                TaskNode(
                    node_id="compare_summary",
                    label="compare_items",
                    task_type=TaskType.COMPARISON,
                    depends_on=[n.node_id for n in nodes if n.node_id.startswith("item_")],
                )
            )
            notes.append("comparison_decomposition_applied")

        elif task_type == TaskType.PLANNING:
            steps = ["identify_goal", "identify_constraints", "propose_plan"]
            for idx, label in enumerate(steps):
                nodes.append(
                    TaskNode(
                        node_id=f"plan_{idx}",
                        label=label,
                        task_type=TaskType.PLANNING,
                        depends_on=[root_id] if idx == 0 else [f"plan_{idx-1}"],
                    )
                )
            notes.append("planning_chain_applied")

        elif task_type == TaskType.DIAGNOSTIC:
            for idx, label in enumerate(["collect_evidence", "generate_causes", "rank_causes"]):
                nodes.append(
                    TaskNode(
                        node_id=f"diag_{idx}",
                        label=label,
                        task_type=TaskType.DIAGNOSTIC,
                        depends_on=[root_id] if idx == 0 else [f"diag_{idx-1}"],
                    )
                )
            notes.append("diagnostic_chain_applied")

        else:
            notes.append("single_node_decomposition")

        return TaskGraph(
            graph_id=graph_id,
            root_node_id=root_id,
            nodes=nodes,
            task_type=task_type,
            notes=notes,
        )

    @staticmethod
    def _extract_comparison_items(text: str) -> List[str]:
        # Try comma-separated first, then "and"
        pieces = re.split(r",|\band\b", text)
        cleaned = []
        for piece in pieces:
            piece = piece.strip(" .:?")
            if not piece:
                continue
            if piece.lower().startswith("compare "):
                piece = piece[8:].strip()
            cleaned.append(piece)
        # Deduplicate while preserving order
        deduped = []
        for item in cleaned:
            if item not in deduped:
                deduped.append(item)
        return deduped[:5] if deduped else [text.strip()]

"""DELTA ARC IV knowledge evolution and controlled learning scaffolds.

ARC IV determines whether transient reasoning should influence future
knowledge. It creates candidates, simulations, reviews, rollback plans, impact
analysis, and ready-to-integrate transaction records, but performs no live
knowledge mutation.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestration.runtime.arc_ii_knowledge_substrate import build_arc_ii_checkpoint
from orchestration.runtime.arc_iii_reasoning_engine import run_reasoning
from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id
from orchestration.runtime.v31_learning_proposal import LearningProposal, build_learning_proposals


REPORT_MD = Path("reports/runtime_arc_iv_safety_checkpoint.md")
REPORT_JSON = Path("reports/runtime_arc_iv_safety_checkpoint.json")
CONSOLE_HTML = Path("ui/delta_arc_iv_evolution_console.html")
CONTINUATION = Path("docs/continuation_runtime_arc_iv.md")

TRANSACTION_STAGES = (
    "draft",
    "review",
    "approved",
    "overwatch_allowed",
    "owner_override",
    "simulation_complete",
    "ready_to_integrate",
)


@dataclass(frozen=True)
class KnowledgeIntegrationCandidate:
    candidate_id: str
    source_proposal_id: str
    affected_entities: tuple[str, ...]
    affected_concepts: tuple[str, ...]
    affected_relationships: tuple[str, ...]
    confidence_delta: float
    knowledge_impact: str
    rollback_impact: str
    conflicts: tuple[str, ...]
    write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VersionGraphNode:
    node_id: str
    version: int
    parent: str
    branch: str
    superseded: bool
    rollback_target: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewerRecord:
    reviewer_role: str
    reviewer_id: str
    decision: str
    rationale: str
    authority: str = "review_only"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledIntegrationTransaction:
    transaction_id: str
    candidate_id: str
    stages: tuple[str, ...]
    current_stage: str
    ready_to_integrate: bool
    integrated: bool = False
    write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["stages"] = list(self.stages)
        return data


@dataclass(frozen=True)
class RollbackPlan:
    rollback_id: str
    candidate_id: str
    dependency_list: tuple[str, ...]
    restoration_plan: tuple[str, ...]
    rollback_available: bool = True

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class KnowledgeEvolutionEngine:
    """Simulation-only evolution engine."""

    def evaluate_proposal(self, proposal: LearningProposal) -> dict[str, object]:
        return {
            "proposal_id": proposal.proposal_id,
            "review_status": proposal.review_status,
            "eligible_for_candidate": proposal.review_status in ("review", "admin_approved"),
            "integration_performed": False,
        }

    def build_candidate(self, proposal: LearningProposal) -> KnowledgeIntegrationCandidate:
        substrate = build_arc_ii_checkpoint()
        entity = substrate["registries"]["entity_registry"]["objects"][0]["id"]
        concept = substrate["registries"]["concept_registry"]["objects"][0]["id"]
        relationship = substrate["registries"]["relationship_registry"]["objects"][0]["id"]
        return KnowledgeIntegrationCandidate(
            candidate_id=stable_v31_id("knowledge-integration-candidate", proposal.proposal_id),
            source_proposal_id=proposal.proposal_id,
            affected_entities=(entity,),
            affected_concepts=(concept,),
            affected_relationships=(relationship,),
            confidence_delta=0.03,
            knowledge_impact="would add reviewed candidate context if future integration were allowed",
            rollback_impact="single candidate rollback would restore prior substrate graph",
            conflicts=("requires_overwatch_review",),
            write_performed=False,
        )

    def estimate_impact(self, candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
        return build_impact_analysis(candidate)

    def detect_conflicts(self, candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
        return build_contradiction_workflow(candidate)

    def request_reviews(self, candidate: KnowledgeIntegrationCandidate) -> tuple[ReviewerRecord, ...]:
        return build_multi_reviewer_workflow(candidate)


def build_version_graph(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    root = VersionGraphNode(candidate.affected_concepts[0], 1, "", "main", False, candidate.affected_concepts[0])
    draft = VersionGraphNode(stable_v31_id("version-node", candidate.candidate_id), 2, root.node_id, "candidate", False, root.node_id)
    return {
        "nodes": [root.as_dict(), draft.as_dict()],
        "edges": [{"parent": root.node_id, "child": draft.node_id, "relation": "candidate_version"}],
        "live_write_performed": False,
    }


def simulate_integration(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "graph_changes": {"new_candidate_node": 1, "new_edges": 2},
        "confidence_changes": {"delta": candidate.confidence_delta, "bounded": True},
        "relationship_changes": {"would_reference": list(candidate.affected_relationships)},
        "concept_changes": {"would_affect": list(candidate.affected_concepts)},
        "write_performed": False,
    }


def build_impact_analysis(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    reasoning = run_reasoning("Why is this true?")
    return {
        "affected_observations": [step["citation"] for step in reasoning["evidence_chain"]["steps"] if step["type"] == "Observation"],
        "affected_entities": list(candidate.affected_entities),
        "affected_procedures": ["review_knowledge_object_before_integration"],
        "affected_reasoning_paths": [path["path_id"] for path in reasoning["alternative_paths"]],
        "affected_confidence": candidate.confidence_delta,
        "report_only": True,
    }


def build_contradiction_workflow(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "conflicts": list(candidate.conflicts),
        "bundle_created": bool(candidate.conflicts),
        "review_required": True,
        "recommendation": "review_conflicts_never_auto_resolve",
        "auto_resolved": False,
    }


def build_multi_reviewer_workflow(candidate: KnowledgeIntegrationCandidate) -> tuple[ReviewerRecord, ...]:
    return (
        ReviewerRecord("technical_review", stable_v31_id("reviewer", "technical", candidate.candidate_id), "review", "check substrate shape"),
        ReviewerRecord("evidence_review", stable_v31_id("reviewer", "evidence", candidate.candidate_id), "review", "check provenance and support"),
        ReviewerRecord("overwatch", stable_v31_id("reviewer", "overwatch", candidate.candidate_id), "block_until_external_or_local_review", "safety gate"),
        ReviewerRecord("owner", stable_v31_id("reviewer", "owner", candidate.candidate_id), "not_invoked", "override optional"),
    )


def build_knowledge_health(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    substrate = build_arc_ii_checkpoint()
    objects = substrate["knowledge_objects"]
    type_counts = Counter(obj["type"] for obj in objects)
    return {
        "consistency": "stable_in_simulation",
        "coverage": dict(type_counts),
        "duplication": 0,
        "fragmentation": len(substrate["health_metrics"]["orphan_nodes"]),
        "contradictions": substrate["health_metrics"]["contradiction_count"],
        "confidence_decay": "not_applied",
        "candidate_confidence_delta": candidate.confidence_delta,
    }


def build_controlled_transaction(candidate: KnowledgeIntegrationCandidate) -> ControlledIntegrationTransaction:
    return ControlledIntegrationTransaction(
        transaction_id=stable_v31_id("controlled-integration-transaction", candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        stages=TRANSACTION_STAGES,
        current_stage="ready_to_integrate",
        ready_to_integrate=True,
        integrated=False,
        write_performed=False,
    )


def build_rollback_plan(candidate: KnowledgeIntegrationCandidate) -> RollbackPlan:
    return RollbackPlan(
        rollback_id=stable_v31_id("rollback-plan", candidate.candidate_id),
        candidate_id=candidate.candidate_id,
        dependency_list=(*candidate.affected_entities, *candidate.affected_concepts, *candidate.affected_relationships),
        restoration_plan=("remove_candidate_version_node", "remove_candidate_edges", "restore_prior_confidence_snapshot"),
    )


def build_evolution_timeline(candidate: KnowledgeIntegrationCandidate) -> list[dict[str, object]]:
    stages = ("experience", "reasoning", "proposal", "review", "simulation", "integration_candidate", "rollback")
    return [{"stage": stage, "candidate_id": candidate.candidate_id, "performed_live_write": False} for stage in stages]


def build_knowledge_diff(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    return {
        "new_concepts": list(candidate.affected_concepts),
        "new_entities": [],
        "changed_confidence": {concept_id: candidate.confidence_delta for concept_id in candidate.affected_concepts},
        "new_relationships": list(candidate.affected_relationships),
        "removed_relationships": [],
        "diff_only": True,
    }


def build_evaluation_framework(candidate: KnowledgeIntegrationCandidate) -> dict[str, object]:
    return {
        "reasoning_improvement": "possible_if_candidate_survives_review",
        "coverage_improvement": len(candidate.affected_concepts),
        "consistency": "unchanged_in_simulation",
        "confidence": {"delta": candidate.confidence_delta},
        "expected_regressions": ["overconfidence_if_integrated_without_review"],
        "evaluation_only": True,
    }


def build_arc_iv_checkpoint() -> dict[str, object]:
    proposal = build_learning_proposals("I have corrected this preference five times.", review_status="admin_approved")[0]
    engine = KnowledgeEvolutionEngine()
    candidate = engine.build_candidate(proposal)
    return {
        "phase": "Runtime ARC IV V6.15",
        "proposal_evaluation": engine.evaluate_proposal(proposal),
        "integration_candidate": candidate.as_dict(),
        "version_graph": build_version_graph(candidate),
        "integration_simulation": simulate_integration(candidate),
        "impact_analysis": engine.estimate_impact(candidate),
        "contradiction_workflow": engine.detect_conflicts(candidate),
        "multi_reviewer_workflow": [record.as_dict() for record in engine.request_reviews(candidate)],
        "knowledge_health": build_knowledge_health(candidate),
        "controlled_transaction": build_controlled_transaction(candidate).as_dict(),
        "rollback_plan": build_rollback_plan(candidate).as_dict(),
        "evolution_timeline": build_evolution_timeline(candidate),
        "knowledge_diff": build_knowledge_diff(candidate),
        "evaluation_framework": build_evaluation_framework(candidate),
        "live_knowledge_mutation": False,
        "integration_write_performed": False,
        "simulation_only": True,
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_ARC_V_MEMORY_ACTIVATION_AND_RECALL_GOVERNANCE_DESIGN",
    }


def write_arc_iv_reports() -> dict[str, object]:
    data = build_arc_iv_checkpoint()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(render_arc_iv_report(data), encoding="utf-8")
    CONSOLE_HTML.parent.mkdir(parents=True, exist_ok=True)
    CONSOLE_HTML.write_text(render_evolution_console(data), encoding="utf-8")
    CONTINUATION.write_text(
        "# DELTA ARC IV Continuation\n\n"
        "ARC IV is complete as a simulation-only knowledge evolution and controlled learning layer. It builds integration candidates, version graphs, simulations, impact analysis, contradiction workflows, multi-reviewer records, health metrics, controlled transactions, rollback plans, timelines, diffs, and evaluation estimates.\n\n"
        "ARC IV stops at ready_to_integrate. No live integration write, training, provider authority, scheduler activation, action execution, HYB1 promotion, or hidden memory mutation occurred.\n\n"
        "Next recommendation: `PROCEED_ARC_V_MEMORY_ACTIVATION_AND_RECALL_GOVERNANCE_DESIGN`.\n",
        encoding="utf-8",
    )
    return data


def render_arc_iv_report(data: dict[str, object]) -> str:
    return f"""# Runtime ARC IV Safety Checkpoint

ARC IV introduces simulation-only knowledge evolution and controlled learning readiness.

## Knowledge Evolution Architecture

Experience -> Reasoning -> Observation -> Candidate Knowledge -> Evidence Review -> Contradiction Review -> Admin Review -> Overwatch Review -> Owner Override -> Integration Transaction -> Evaluation -> Rollback

## Evolution State Machine

draft -> review -> approved -> overwatch_allowed -> owner_override -> simulation_complete -> ready_to_integrate

## Integration Transaction Lifecycle

Current stage: {data['controlled_transaction']['current_stage']}

## Knowledge Version Graph

- nodes: {len(data['version_graph']['nodes'])}
- edges: {len(data['version_graph']['edges'])}

## Rollback Architecture

Rollback available: {data['rollback_plan']['rollback_available']}

## Impact Engine

Affected confidence: {data['impact_analysis']['affected_confidence']}

## Knowledge Health Engine

Consistency: {data['knowledge_health']['consistency']}

Safety: no live integration write, no training, no provider authority, no scheduler, no action execution.

Final recommendation: `{data['final_recommendation']}`
"""


def render_evolution_console(data: dict[str, object]) -> str:
    reviewers = "".join(f"<li>{item['reviewer_role']}: {item['decision']}</li>" for item in data["multi_reviewer_workflow"])
    timeline = "".join(f"<li>{item['stage']}</li>" for item in data["evolution_timeline"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>DELTA ARC IV Evolution Console</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}</style></head>
<body>
<h1>DELTA ARC IV Evolution Console</h1>
<section><h2>Candidate</h2><pre>{json.dumps(data['integration_candidate'], indent=2)}</pre></section>
<section><h2>Simulation</h2><pre>{json.dumps(data['integration_simulation'], indent=2)}</pre></section>
<section><h2>Impact</h2><pre>{json.dumps(data['impact_analysis'], indent=2)}</pre></section>
<section><h2>Health</h2><pre>{json.dumps(data['knowledge_health'], indent=2)}</pre></section>
<section><h2>Rollback</h2><pre>{json.dumps(data['rollback_plan'], indent=2)}</pre></section>
<section><h2>Approval Chain</h2><ul>{reviewers}</ul></section>
<section><h2>Evolution Timeline</h2><ul>{timeline}</ul></section>
</body></html>
"""


if __name__ == "__main__":
    print(write_arc_iv_reports()["final_recommendation"])

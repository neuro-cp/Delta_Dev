from __future__ import annotations

from memory.working_memory.active_context import WorkingMemoryContext, WorkingMemoryContextItem
from orchestration.runtime.response_generation import RuntimeResponseGenerator
from orchestration.runtime.runtime_planning import RuntimePlanner
from orchestration.runtime.runtime_reasoning import RuntimeReasoningEngine


def _candidate(
    key: str,
    text: str,
    *,
    priority: float = 0.45,
    confidence: float = 0.5,
    promotion_score: float = 0.4,
    centrality: float = 0.1,
    evidence_support: float = 0.0,
    activation_score: float = 0.35,
    attention_classification: str = "Supporting",
) -> WorkingMemoryContextItem:
    return WorkingMemoryContextItem(
        key=key,
        kind="candidate_knowledge",
        source="candidate_knowledge_attention",
        text=text,
        priority=priority,
        metadata={
            "attention_classification": attention_classification,
            "confidence": confidence,
            "promotion_score": promotion_score,
            "projected_centrality": centrality,
            "evidence_support": evidence_support,
            "activation_score": activation_score,
        },
    )


def _enable_r4(monkeypatch):
    monkeypatch.setenv("DELTA_RUNTIME_V13_ROLE_GATE_MODE", "r4")
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)


def _enable_role_mode(monkeypatch, mode: str):
    monkeypatch.setenv("DELTA_RUNTIME_V13_ROLE_GATE_MODE", mode)
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)


def test_usage_gate_blocks_weak_candidate_from_reasoning_evidence():
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "weak-risk",
                "Risk should be considered when planning.",
                priority=0.41,
                confidence=0.45,
                promotion_score=0.35,
                centrality=0.05,
                evidence_support=1.0,
                activation_score=0.32,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert report.findings == []
    assert report.evidence_keys == []
    assert report.usage_gated_items
    assert report.usage_gated_items[0]["key"] == "weak-risk"
    assert report.usage_gated_items[0]["usage_gate_decision"] == "blocked"


def test_usage_gate_allows_strong_candidate_through():
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "strong-risk",
                "Failure risk and uncertainty should be handled by validating assumptions against evidence.",
                priority=0.62,
                confidence=0.86,
                promotion_score=0.72,
                centrality=0.7,
                evidence_support=0.8,
                activation_score=0.58,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert report.evidence_keys == ["strong-risk"]
    assert report.findings
    assert report.findings[0].metadata["usage_gate_decision"] == "allowed"


def test_usage_gate_does_not_mutate_working_memory():
    item = _candidate(
        "weak-risk",
        "Risk should be considered when planning.",
        priority=0.41,
        confidence=0.45,
        promotion_score=0.35,
        centrality=0.05,
        activation_score=0.32,
    )
    context = WorkingMemoryContext(cycle_id="gate-test", items=[item])
    before = context.as_advisory_payload()

    RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert context.as_advisory_payload() == before


def test_usage_gate_metadata_is_inspectable_for_allowed_items():
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "strong-maintenance",
                "Industrial maintenance failure timelines help identify root causes.",
                priority=0.6,
                confidence=0.8,
                promotion_score=0.7,
                evidence_support=0.8,
                activation_score=0.55,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    signals = report.findings[0].metadata["usage_gate_signals"]
    assert signals["attention_classification"] == "Supporting"
    assert "specific_overlap_count" in signals
    assert report.usage_gated_items == []


def test_strict_context_gate_blocks_high_evidence_with_shallow_overlap(monkeypatch):
    monkeypatch.setenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", "strict_context")
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "high-support-shallow",
                "Risk should be considered when planning.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.usage_gated_items[0]["usage_gate_signals"]["usage_gate_mode"] == "strict_context"


def test_strict_context_gate_allows_high_evidence_with_specific_overlap(monkeypatch):
    monkeypatch.setenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", "strict_context")
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "specific-support",
                "Industrial maintenance analysis should compare failure timelines and root causes.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == ["specific-support"]
    assert report.usage_gated_items == []


def test_model_b_blocks_high_evidence_without_query_context(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "generic-risk",
                "Risk should be considered when planning.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.usage_gated_items[0]["usage_gate_reason"] == "corpus support lacks query-context support"
    signals = report.usage_gated_items[0]["usage_gate_signals"]
    assert signals["query_evidence_model"] == "model_b_contextualized_corpus_support"
    assert signals["corpus_support_only"] is True
    assert signals["corpus_support_contextualized"] is False


def test_model_b_allows_high_evidence_with_specific_query_overlap(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "specific-maintenance",
                "In industrial maintenance, interacting causes should be analyzed with failure timelines.",
                priority=0.55,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == ["specific-maintenance"]
    metadata = report.findings[0].metadata
    assert metadata["query_evidence_model"] == "model_b_contextualized_corpus_support"
    assert metadata["corpus_support_contextualized"] is True
    assert metadata["corpus_support_only"] is False


def test_model_b_blocks_generic_overlap_plus_high_evidence(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "generic-plan",
                "The plan depends on uncertainty and resource evidence.",
                priority=0.58,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.43,
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk and uncertainty?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.usage_gated_items[0]["usage_gate_signals"]["generic_overlap"]
    assert report.usage_gated_items[0]["usage_gate_signals"]["corpus_support_only"] is True


def test_model_b_allows_domain_anchor_with_meaningful_context(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "permit-assumption",
                "A failed permit assumption requires the emergency response plan to include alternative routes.",
                priority=0.54,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.43,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a team revise an emergency response plan after a failed permit assumption?",
        context=context,
    )

    assert report.evidence_keys == ["permit-assumption"]
    signals = report.findings[0].metadata["usage_gate_signals"]
    assert set(signals["domain_anchor_overlap"]) & {"assumption", "emergency", "permit"}
    assert signals["corpus_support_contextualized"] is True


def test_model_b_blocked_evidence_does_not_enter_reasoning_keys(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    context = WorkingMemoryContext(
        cycle_id="gate-test",
        items=[
            _candidate(
                "blocked",
                "Risk should be considered when planning.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
            ),
            _candidate(
                "allowed",
                "Failure risk and uncertainty should be handled by validating assumptions against evidence.",
                priority=0.7,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.6,
                attention_classification="Core",
            ),
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk, uncertainty, and assumptions?",
        context=context,
    )

    assert "blocked" not in report.evidence_keys
    assert "allowed" in report.evidence_keys
    assert all("blocked" not in finding.supporting_keys for finding in report.findings)


def test_role_model_r4_core_evidence_becomes_reasoning_evidence(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "core-maintenance",
                "In industrial maintenance, interacting causes should be analyzed by comparing failure timelines and rejecting spurious causes.",
                priority=0.62,
                confidence=0.9,
                promotion_score=0.72,
                evidence_support=1.0,
                activation_score=0.6,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == ["core-maintenance"]
    assert report.findings[0].metadata["query_local_role"] == "Core Evidence"
    assert report.findings[0].metadata["citable_evidence"] is True
    assert report.findings[0].metadata["context_visible"] is True


def test_role_model_r4_supporting_context_visible_but_not_citable(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "near-neighbor",
                "For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures.",
                priority=0.57,
                confidence=0.92,
                promotion_score=0.74,
                evidence_support=1.0,
                activation_score=0.52,
                attention_classification="Supporting",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.findings == []
    assert report.supporting_context_items
    context_item = report.supporting_context_items[0]
    assert context_item["key"] == "near-neighbor"
    assert context_item["query_local_role"] == "Supporting Context"
    assert context_item["citable_evidence"] is False
    assert context_item["context_visible"] is True


def test_role_model_r4_supporting_context_does_not_feed_planning_or_response(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "near-neighbor",
                "For example, maintenance frequency can appear correlated with failure rates even when hidden operational stress causes both.",
                priority=0.57,
                confidence=0.92,
                promotion_score=0.74,
                evidence_support=1.0,
                activation_score=0.52,
                attention_classification="Supporting",
            )
        ],
    )

    reasoning = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )
    plan = RuntimePlanner().plan(reasoning)
    response = RuntimeResponseGenerator().draft(reasoning=reasoning, plan=plan)

    assert reasoning.supporting_context_items
    assert reasoning.evidence_keys == []
    assert all(not option.supporting_evidence for option in plan.options)
    assert response.evidence_used == []
    assert plan.recommended_option == "Low-evidence response"


def test_role_model_r4_peripheral_and_non_evidence_are_blocked(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "weak-context",
                "The report changes the response context.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.74,
                evidence_support=0.8,
                activation_score=0.5,
                attention_classification="Supporting",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a city account for failure risk and uncertainty?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.findings == []
    assert report.usage_gated_items
    assert report.usage_gated_items[0]["query_local_role"] in {"Peripheral Context", "Non-Evidence"}
    assert report.usage_gated_items[0]["citable_evidence"] is False


def test_role_model_r4_does_not_mutate_working_memory(monkeypatch):
    _enable_r4(monkeypatch)
    item = _candidate(
        "near-neighbor",
        "For instance, maintenance frequency can be associated with failure rates without proving cause.",
        priority=0.57,
        confidence=0.92,
        promotion_score=0.74,
        evidence_support=1.0,
        activation_score=0.52,
        attention_classification="Supporting",
    )
    context = WorkingMemoryContext(cycle_id="r4-test", items=[item])
    before = context.as_advisory_payload()

    RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert context.as_advisory_payload() == before


def test_role_model_r4_metadata_is_present_for_all_candidate_paths(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "core",
                "Failure risk and uncertainty should be handled by validating assumptions against evidence.",
                priority=0.7,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.6,
                attention_classification="Core",
            ),
            _candidate(
                "supporting",
                "For instance, uncertainty in this scenario depends on assumptions that may later change.",
                priority=0.58,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.55,
                attention_classification="Supporting",
            ),
            _candidate(
                "blocked",
                "Risk should be considered when planning.",
                priority=0.5,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
            ),
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should a plan account for failure risk, uncertainty, and assumptions?",
        context=context,
    )
    role_payloads = [
        report.findings[0].metadata,
        report.supporting_context_items[0],
        report.usage_gated_items[0],
    ]

    for payload in role_payloads:
        assert "query_local_role" in payload
        assert "query_local_role_reason" in payload
        assert "query_local_role_signals" in payload
        assert "citable_evidence" in payload
        assert "context_visible" in payload
        assert payload["query_evidence_model"] == "model_b_contextualized_corpus_support"


def test_role_model_r4_strong_technical_evidence_can_be_core(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "gps-core",
                "GPS multipath interference near dense buildings can reflect GPS signals and cause drift.",
                priority=0.61,
                confidence=0.9,
                promotion_score=0.72,
                evidence_support=1.0,
                activation_score=0.58,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="What causes GPS drift near dense buildings?",
        context=context,
    )

    assert report.evidence_keys == ["gps-core"]
    assert report.findings[0].metadata["query_local_role"] == "Core Evidence"


def test_role_model_r4_near_neighbor_high_support_is_not_citable(monkeypatch):
    _enable_r4(monkeypatch)
    context = WorkingMemoryContext(
        cycle_id="r4-test",
        items=[
            _candidate(
                "near-neighbor",
                "For instance, a current understanding of maintenance patterns may depend on correlated failures rather than a proven causal mechanism.",
                priority=0.62,
                confidence=0.99,
                promotion_score=0.82,
                evidence_support=1.0,
                activation_score=0.7,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == []
    assert report.supporting_context_items
    assert report.supporting_context_items[0]["query_local_role"] == "Supporting Context"
    assert report.supporting_context_items[0]["citable_evidence"] is False


def test_role_compromise_planning_support_feeds_plan_not_response(monkeypatch):
    _enable_role_mode(monkeypatch, "r4_planning_support")
    context = WorkingMemoryContext(
        cycle_id="role-compromise-test",
        items=[
            _candidate(
                "planning-neighbor",
                "For example, maintenance frequency can appear correlated with failure rates even when hidden operational stress causes both.",
                priority=0.57,
                confidence=0.92,
                promotion_score=0.74,
                evidence_support=1.0,
                activation_score=0.52,
                attention_classification="Supporting",
            )
        ],
    )

    reasoning = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )
    plan = RuntimePlanner().plan(reasoning)
    response = RuntimeResponseGenerator().draft(reasoning=reasoning, plan=plan)

    assert reasoning.evidence_keys == []
    assert reasoning.findings == []
    assert reasoning.planning_support_items
    assert reasoning.planning_support_items[0]["query_local_role"] == "Planning Support"
    assert plan.recommended_option == "Evidence-grounded recommendation"
    assert "planning-neighbor" in plan.options[0].supporting_evidence
    assert response.evidence_used == []


def test_role_compromise_response_citation_gate_keeps_planning_not_response(monkeypatch):
    _enable_role_mode(monkeypatch, "response_citation_gate")
    context = WorkingMemoryContext(
        cycle_id="role-compromise-test",
        items=[
            _candidate(
                "planning-neighbor",
                "For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures.",
                priority=0.57,
                confidence=0.92,
                promotion_score=0.74,
                evidence_support=1.0,
                activation_score=0.52,
                attention_classification="Supporting",
            )
        ],
    )

    reasoning = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )
    plan = RuntimePlanner().plan(reasoning)
    response = RuntimeResponseGenerator().draft(reasoning=reasoning, plan=plan)

    assert reasoning.evidence_keys == []
    assert reasoning.findings
    assert reasoning.findings[0].metadata["query_local_role"] == "Planning Support"
    assert "planning-neighbor" in plan.options[0].supporting_evidence
    assert response.evidence_used == []


def test_role_metadata_only_preserves_model_b_default_behavior(monkeypatch):
    _enable_role_mode(monkeypatch, "role_metadata_only")
    context = WorkingMemoryContext(
        cycle_id="role-compromise-test",
        items=[
            _candidate(
                "specific-maintenance",
                "In industrial maintenance, interacting causes should be analyzed with failure timelines.",
                priority=0.55,
                confidence=0.9,
                promotion_score=0.7,
                evidence_support=1.0,
                activation_score=0.42,
                attention_classification="Core",
            )
        ],
    )

    report = RuntimeReasoningEngine().reason(
        question="How should interacting causes be analyzed in industrial maintenance?",
        context=context,
    )

    assert report.evidence_keys == ["specific-maintenance"]
    assert report.findings[0].metadata["query_local_role"] == "Core Evidence"
    assert report.findings[0].metadata["query_local_role_signals"]["role_gate_mode"] == "role_metadata_only"

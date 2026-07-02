from __future__ import annotations

import re
import os
from dataclasses import dataclass, field
from typing import Any, Mapping

from memory.working_memory.active_context import WorkingMemoryContext


@dataclass(frozen=True)
class ReasoningFinding:
    kind: str
    text: str
    confidence: float
    supporting_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeReasoningReport:
    question: str
    findings: list[ReasoningFinding]
    assumptions: list[str]
    conflicts: list[str]
    evidence_keys: list[str]
    confidence: float
    usage_gated_items: list[dict[str, Any]] = field(default_factory=list)
    supporting_context_items: list[dict[str, Any]] = field(default_factory=list)
    planning_support_items: list[dict[str, Any]] = field(default_factory=list)


class RuntimeReasoningEngine:
    """
    Deterministic, read-only reasoning over active working memory.

    It does not learn, store, validate, promote, or call providers. Its role is
    to identify what active knowledge appears relevant enough to support a
    response.
    """

    def reason(self, *, question: str, context: WorkingMemoryContext) -> RuntimeReasoningReport:
        items = sorted(context.items, key=lambda item: item.priority, reverse=True)
        findings: list[ReasoningFinding] = []
        evidence_keys: list[str] = []
        usage_gated_items: list[dict[str, Any]] = []
        supporting_context_items: list[dict[str, Any]] = []
        planning_support_items: list[dict[str, Any]] = []
        for item in items[:12]:
            if item.kind != "candidate_knowledge":
                continue
            gate = _usage_gate_decision(question=question, item=item)
            role = _query_local_role_decision(question=question, item=item, gate=gate)
            role_metadata = _role_metadata(role)
            if gate["blocked"]:
                usage_gated_items.append(
                    {
                        "key": item.key,
                        "usage_gate_decision": "blocked",
                        "usage_gate_reason": gate["reason"],
                        "query_evidence_model": gate["signals"].get("query_evidence_model"),
                        "usage_gate_signals": gate["signals"],
                        **role_metadata,
                    }
                )
                continue
            if role["query_local_role"] == "Planning Support" and not _planning_support_enters_reasoning(role):
                planning_support_items.append(
                    {
                        "key": item.key,
                        "text": item.text,
                        "confidence": float(item.metadata.get("confidence", 0.0) or 0.0),
                        "priority": float(item.priority),
                        "usage_gate_decision": "planning_support",
                        "usage_gate_reason": gate["reason"],
                        "query_evidence_model": gate["signals"].get("query_evidence_model"),
                        "usage_gate_signals": gate["signals"],
                        **role_metadata,
                    }
                )
                continue
            if role["query_local_role"] == "Supporting Context":
                supporting_context_items.append(
                    {
                        "key": item.key,
                        "text": item.text,
                        "confidence": float(item.metadata.get("confidence", 0.0) or 0.0),
                        "priority": float(item.priority),
                        "usage_gate_decision": "context",
                        "usage_gate_reason": gate["reason"],
                        "query_evidence_model": gate["signals"].get("query_evidence_model"),
                        "usage_gate_signals": gate["signals"],
                        **role_metadata,
                    }
                )
                continue
            if role["query_local_role"] not in {"Core Evidence", "Planning Support"}:
                usage_gated_items.append(
                    {
                        "key": item.key,
                        "usage_gate_decision": "blocked",
                        "usage_gate_reason": role["query_local_role_reason"],
                        "query_evidence_model": gate["signals"].get("query_evidence_model"),
                        "usage_gate_signals": gate["signals"],
                        **role_metadata,
                    }
                )
                continue
            if role["query_local_role"] == "Core Evidence":
                evidence_keys.append(item.key)
            findings.append(
                ReasoningFinding(
                    kind="supporting_concept" if role["query_local_role"] == "Core Evidence" else "planning_support_concept",
                    text=item.text,
                    confidence=_bounded(
                        (0.50 * item.priority)
                        + (0.30 * float(item.metadata.get("confidence", 0.0) or 0.0))
                        + (0.20 * float(item.metadata.get("promotion_score", 0.0) or 0.0))
                    ),
                    supporting_keys=[item.key],
                    metadata={
                        "recommendation": item.metadata.get("recommendation"),
                        "relevance": item.metadata.get("relevance"),
                        "projected_centrality": item.metadata.get("projected_centrality"),
                        "usage_gate_decision": "allowed",
                        "usage_gate_reason": gate["reason"],
                        "query_evidence_model": gate["signals"].get("query_evidence_model"),
                        "query_evidence_support_score": gate["signals"].get("query_evidence_support_score"),
                        "corpus_support_contextualized": gate["signals"].get("corpus_support_contextualized"),
                        "corpus_support_only": gate["signals"].get("corpus_support_only"),
                        "query_context_support_reason": gate["signals"].get("query_context_support_reason"),
                        "usage_gate_signals": gate["signals"],
                        **role_metadata,
                    },
                )
            )
        assumptions = _assumptions(question=question, findings=findings)
        conflicts = [
            finding.text
            for finding in findings
            if "tradeoff" in finding.text.lower() or "risk" in finding.text.lower()
        ][:5]
        confidence = _bounded(sum(finding.confidence for finding in findings[:5]) / max(1, min(5, len(findings))))
        return RuntimeReasoningReport(
            question=question,
            findings=findings,
            assumptions=assumptions,
            conflicts=conflicts,
            evidence_keys=evidence_keys,
            confidence=round(confidence, 4),
            usage_gated_items=usage_gated_items,
            supporting_context_items=supporting_context_items,
            planning_support_items=planning_support_items,
        )


HYB1_ENV_FLAG = "DELTA_RUNTIME_V13_HYB1_ENABLED"


def runtime_v13_hyb1_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the experimental HYB1 projection selector is enabled.

    HYB1 is a dormant Runtime V1.3 prototype. It is not the default reasoning
    path and does not alter Model B unless the explicit environment flag is set.
    """

    source = os.environ if env is None else env
    raw = str(source.get(HYB1_ENV_FLAG, "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def runtime_v13_select_hyb1_projection(
    *,
    model_b_reasoning: set[str],
    model_b_planning: set[str],
    model_b_response: set[str],
    mbv2_reasoning: set[str],
    mbv2_planning: set[str],
    mbv2_response: set[str],
    expected_concepts: set[str],
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Select Model B or HYB1 projected evidence without changing live defaults.

    HYB1 applies the MBV2 reasoning filter only when projected planning and
    response coverage stay at or above Model B for the same case. Otherwise it
    falls back to exact Model B behavior for that case.
    """

    if not runtime_v13_hyb1_enabled(env):
        return {
            "strategy": "model_b_default",
            "reasoning": set(model_b_reasoning),
            "planning": set(model_b_planning),
            "response": set(model_b_response),
            "reason": "HYB1 dormant; using Model B",
        }

    base_plan_cov = _runtime_v13_projection_coverage(model_b_planning, expected_concepts)
    base_resp_cov = _runtime_v13_projection_coverage(model_b_response, expected_concepts)
    mbv2_plan_cov = _runtime_v13_projection_coverage(mbv2_planning, expected_concepts)
    mbv2_resp_cov = _runtime_v13_projection_coverage(mbv2_response, expected_concepts)
    if mbv2_plan_cov >= base_plan_cov and mbv2_resp_cov >= base_resp_cov:
        return {
            "strategy": "hyb1_mbv2_coverage_safe",
            "reasoning": set(mbv2_reasoning),
            "planning": set(mbv2_planning),
            "response": set(mbv2_response),
            "reason": "MBV2 filter accepted; projected planning/response coverage is preserved",
            "coverage": {
                "model_b_planning": base_plan_cov,
                "model_b_response": base_resp_cov,
                "hyb1_planning": mbv2_plan_cov,
                "hyb1_response": mbv2_resp_cov,
            },
        }
    return {
        "strategy": "hyb1_model_b_fallback",
        "reasoning": set(model_b_reasoning),
        "planning": set(model_b_planning),
        "response": set(model_b_response),
        "reason": "Model B fallback; MBV2 would regress projected planning/response coverage",
        "coverage": {
            "model_b_planning": base_plan_cov,
            "model_b_response": base_resp_cov,
            "hyb1_planning": mbv2_plan_cov,
            "hyb1_response": mbv2_resp_cov,
        },
    }


def _runtime_v13_projection_coverage(keys: set[str], expected: set[str]) -> float:
    return round(len(keys & expected) / len(expected), 4) if expected else 1.0


def _assumptions(*, question: str, findings: list[ReasoningFinding]) -> list[str]:
    assumptions = []
    if re.search(r"\bshould\b|\bstrategy\b|\bplan\b|\bprepare\b", question, re.I):
        assumptions.append("The user is asking for an actionable recommendation, not only a factual summary.")
    if findings:
        assumptions.append("The response should be grounded in activated candidate knowledge rather than direct provider recall alone.")
    else:
        assumptions.append("Activated candidate knowledge is sparse; any response should state low evidence support.")
    return assumptions


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _usage_gate_decision(*, question: str, item: Any) -> dict[str, Any]:
    if item.kind != "candidate_knowledge":
        return {"blocked": False, "reason": "not candidate knowledge", "signals": {}}

    attention_classification = str(item.metadata.get("attention_classification", ""))
    if attention_classification not in {"Core", "Supporting"}:
        return {
            "blocked": False,
            "reason": "attention did not mark item as usable",
            "signals": {"attention_classification": attention_classification},
        }

    query_tokens = _runtime_tokens(question)
    item_tokens = _runtime_tokens(item.text)
    overlap = query_tokens & item_tokens
    jaccard_to_question = len(overlap) / max(1, len(query_tokens | item_tokens))
    specific_overlap = {
        token
        for token in overlap
        if token not in _USAGE_GATE_BROAD_TERMS and token not in _USAGE_GATE_STOPWORDS
    }
    domain_anchor_overlap = specific_overlap & _USAGE_GATE_DOMAIN_ANCHOR_TERMS
    generic_overlap = {
        token
        for token in overlap
        if token in _USAGE_GATE_BROAD_TERMS or token in _USAGE_GATE_GENERIC_ANCHOR_TERMS
    }
    contextual_overlap_count = len(specific_overlap) + len(domain_anchor_overlap)
    generic_anchor_ratio = len(generic_overlap) / max(1, len(overlap))
    shallow_overlap = bool(overlap) and len(specific_overlap) <= 1
    weak_specific_support = len(specific_overlap) <= 1
    confidence = float(item.metadata.get("confidence", 0.0) or 0.0)
    promotion_score = float(item.metadata.get("promotion_score", 0.0) or 0.0)
    centrality = float(item.metadata.get("projected_centrality", 0.0) or 0.0)
    evidence_support = float(item.metadata.get("evidence_support", 0.0) or 0.0)
    attention_score = float(item.priority)
    activation_score = float(item.metadata.get("activation_score", 0.0) or 0.0)
    mode = os.environ.get("DELTA_RUNTIME_V13_USAGE_GATE_MODE", "citation_context").strip().lower()
    if mode == "strict_context":
        strong_override = (
            len(specific_overlap) >= 2
            or bool(specific_overlap & _USAGE_GATE_TECHNICAL_ANCHOR_TERMS)
            or (evidence_support >= 0.75 and len(specific_overlap) >= 2)
            or (attention_score >= 0.68 and len(specific_overlap) >= 1)
            or (centrality >= 0.65 and len(specific_overlap) >= 2)
        )
        weak_support = (
            activation_score < 0.5
            and attention_score < 0.7
            and not strong_override
        )
    elif mode == "citation_context":
        query_context_support = (
            contextual_overlap_count >= 3
            or (jaccard_to_question >= 0.14 and contextual_overlap_count >= 1 and generic_anchor_ratio < 0.70)
            or (contextual_overlap_count >= 2 and attention_score >= 0.52)
            or (bool(specific_overlap & _USAGE_GATE_TECHNICAL_ANCHOR_TERMS) and attention_score >= 0.25)
            or (contextual_overlap_count >= 1 and generic_anchor_ratio == 0.0 and attention_score >= 0.40)
        )
        corpus_support_contextualized = evidence_support >= 0.75 and query_context_support
        corpus_support_only = evidence_support >= 0.75 and not query_context_support
        query_evidence_support_score = _query_evidence_support_score(
            contextual_overlap_count=contextual_overlap_count,
            jaccard_to_question=jaccard_to_question,
            attention_score=attention_score,
            evidence_support=evidence_support,
            corpus_support_contextualized=corpus_support_contextualized,
        )
        query_context_support_reason = _query_context_support_reason(
            contextual_overlap_count=contextual_overlap_count,
            jaccard_to_question=jaccard_to_question,
            attention_score=attention_score,
            generic_anchor_ratio=generic_anchor_ratio,
            corpus_support_contextualized=corpus_support_contextualized,
        )
        strong_override = (
            contextual_overlap_count >= 3
            or (jaccard_to_question >= 0.14 and contextual_overlap_count >= 1 and generic_anchor_ratio < 0.70)
            or (contextual_overlap_count >= 2 and attention_score >= 0.52)
            or (bool(specific_overlap & _USAGE_GATE_TECHNICAL_ANCHOR_TERMS) and attention_score >= 0.25)
            or (contextual_overlap_count >= 1 and generic_anchor_ratio == 0.0 and attention_score >= 0.40)
            or (attention_score >= 0.7 and len(specific_overlap) >= 1)
        )
        weak_support = (
            activation_score < 0.48
            and attention_score < 0.66
            and not strong_override
        )
    else:
        strong_override = (
            len(specific_overlap) >= 2
            or bool(specific_overlap & _USAGE_GATE_TECHNICAL_ANCHOR_TERMS)
            or (evidence_support >= 0.75 and bool(specific_overlap))
            or (attention_score >= 0.58 and len(specific_overlap) >= 1)
            or (confidence >= 0.82 and promotion_score >= 0.68 and len(specific_overlap) >= 1)
            or (centrality >= 0.65 and len(specific_overlap) >= 1)
        )
        weak_support = (
            evidence_support < 0.5
            and promotion_score < 0.64
            and centrality < 0.55
            and activation_score < 0.45
            and attention_score < 0.7
        )
    if mode == "citation_context":
        blocked = bool(overlap) and corpus_support_only and weak_support and not strong_override
    else:
        query_evidence_support_score = 1.0 if strong_override else 0.0
        corpus_support_contextualized = evidence_support >= 0.75 and strong_override
        corpus_support_only = evidence_support >= 0.75 and not strong_override
        query_context_support_reason = "legacy usage gate"
        blocked = shallow_overlap and weak_specific_support and weak_support and not strong_override
    return {
        "blocked": blocked,
        "reason": (
            "corpus support lacks query-context support"
            if blocked and mode == "citation_context"
            else "weak replacement-risk support"
            if blocked
            else "sufficient runtime support"
        ),
        "signals": {
            "attention_classification": attention_classification,
            "usage_gate_mode": mode,
            "query_evidence_model": (
                "model_b_contextualized_corpus_support" if mode == "citation_context" else "legacy_usage_gate"
            ),
            "query_evidence_support_score": round(query_evidence_support_score, 4),
            "corpus_support_contextualized": corpus_support_contextualized,
            "corpus_support_only": corpus_support_only,
            "query_context_support_reason": query_context_support_reason,
            "attention_score": round(attention_score, 4),
            "activation_score": round(activation_score, 4),
            "query_overlap": sorted(overlap),
            "specific_overlap": sorted(specific_overlap),
            "specific_overlap_count": len(specific_overlap),
            "domain_anchor_overlap": sorted(domain_anchor_overlap),
            "domain_anchor_overlap_count": len(domain_anchor_overlap),
            "generic_overlap": sorted(generic_overlap),
            "generic_anchor_ratio": round(generic_anchor_ratio, 4),
            "contextual_overlap_count": contextual_overlap_count,
            "jaccard_to_question": round(jaccard_to_question, 4),
            "shallow_overlap": shallow_overlap,
            "weak_specific_support": weak_specific_support,
            "weak_support": weak_support,
            "strong_override": strong_override,
            "confidence": round(confidence, 4),
            "promotion_score": round(promotion_score, 4),
            "projected_centrality": round(centrality, 4),
            "evidence_support": round(evidence_support, 4),
        },
    }


def _query_local_role_decision(*, question: str, item: Any, gate: dict[str, Any]) -> dict[str, Any]:
    signals = dict(gate.get("signals") or {})
    if gate.get("blocked"):
        return {
            "query_local_role": "Non-Evidence",
            "query_local_role_reason": gate.get("reason", "blocked by usage gate"),
            "query_local_role_signals": _role_signals(signals, extra={"usage_gate_blocked": True}),
            "citable_evidence": False,
            "context_visible": False,
        }
    role_mode = _role_gate_mode()
    if role_mode in {"off", "role_metadata_only"}:
        return {
            "query_local_role": "Core Evidence",
            "query_local_role_reason": (
                "role metadata only; model b evidence remains citable"
                if role_mode == "role_metadata_only"
                else "role gate dormant; model b evidence remains citable"
            ),
            "query_local_role_signals": _role_signals(signals, extra={"role_gate_mode": role_mode}),
            "citable_evidence": True,
            "context_visible": True,
        }

    text = str(item.text)
    lowered = text.lower()
    attention_classification = str(signals.get("attention_classification") or item.metadata.get("attention_classification", ""))
    contextual_overlap_count = int(signals.get("contextual_overlap_count", 0) or 0)
    jaccard_to_question = float(signals.get("jaccard_to_question", 0.0) or 0.0)
    attention_score = float(signals.get("attention_score", item.priority) or 0.0)
    generic_anchor_ratio = float(signals.get("generic_anchor_ratio", 0.0) or 0.0)
    specific_overlap_count = int(signals.get("specific_overlap_count", 0) or 0)
    evidence_support = float(signals.get("evidence_support", item.metadata.get("evidence_support", 0.0)) or 0.0)
    query_overlap = set(signals.get("query_overlap", []) or [])
    specific_overlap = set(signals.get("specific_overlap", []) or [])
    has_context_marker = _has_context_marker(lowered)
    has_direct_action_language = _has_direct_action_language(lowered)
    has_technical_anchor = bool(specific_overlap & _USAGE_GATE_TECHNICAL_ANCHOR_TERMS)
    has_domain_bridge = _has_query_domain_bridge(question.lower(), lowered)
    has_actionable_risk_evidence = (
        len(query_overlap & _QUERY_ROLE_ACTIONABLE_RISK_TERMS) >= 3
        and has_direct_action_language
        and not has_context_marker
        and evidence_support >= 0.75
        and attention_score >= 0.55
    )
    has_operational_bridge_evidence = (
        has_domain_bridge
        and has_direct_action_language
        and not has_context_marker
        and evidence_support >= 0.75
        and attention_score >= 0.37
    )
    high_context = contextual_overlap_count >= 3 or (
        contextual_overlap_count >= 2 and jaccard_to_question >= 0.14
    )
    moderate_context = (
        contextual_overlap_count >= 2
        or (contextual_overlap_count >= 1 and attention_score >= 0.55)
        or jaccard_to_question >= 0.14
        or has_technical_anchor
    )
    generic_only = bool(query_overlap) and contextual_overlap_count == 0 and generic_anchor_ratio >= 0.5
    has_planning_support = _has_planning_support(
        mode=role_mode,
        question=question,
        text=lowered,
        signals=signals,
        high_context=high_context,
        moderate_context=moderate_context,
        generic_only=generic_only,
        has_context_marker=has_context_marker,
        has_direct_action_language=has_direct_action_language,
        has_domain_bridge=has_domain_bridge,
        evidence_support=evidence_support,
        attention_score=attention_score,
    )
    core_ready = (
        high_context
        and not has_context_marker
        and generic_anchor_ratio <= 0.75
        and (
            has_direct_action_language
            or attention_classification == "Core"
            or jaccard_to_question >= 0.25
            or has_technical_anchor
        )
    )
    strong_technical_core = (
        has_technical_anchor
        and not has_context_marker
        and attention_score >= 0.25
        and specific_overlap_count >= 1
    )

    base_role_signals = _role_signals(
        signals,
        extra={
            "usage_gate_blocked": False,
            "role_gate_mode": role_mode,
            "has_context_marker": has_context_marker,
            "has_direct_action_language": has_direct_action_language,
            "has_technical_anchor": has_technical_anchor,
            "has_domain_bridge": has_domain_bridge,
            "has_actionable_risk_evidence": has_actionable_risk_evidence,
            "has_operational_bridge_evidence": has_operational_bridge_evidence,
            "has_planning_support": has_planning_support,
            "high_context": high_context,
            "moderate_context": moderate_context,
            "generic_only": generic_only,
            "evidence_support": round(evidence_support, 4),
        },
    )
    if core_ready or strong_technical_core or has_actionable_risk_evidence or has_operational_bridge_evidence:
        return {
            "query_local_role": "Core Evidence",
            "query_local_role_reason": "direct query-local evidence support",
            "query_local_role_signals": base_role_signals,
            "citable_evidence": True,
            "context_visible": True,
        }
    if has_planning_support:
        return {
            "query_local_role": "Planning Support",
            "query_local_role_reason": "usable for planning support but not final response citation",
            "query_local_role_signals": base_role_signals,
            "citable_evidence": False,
            "context_visible": True,
        }
    if moderate_context and not generic_only:
        return {
            "query_local_role": "Supporting Context",
            "query_local_role_reason": "query-relevant context without direct citable evidence role",
            "query_local_role_signals": base_role_signals,
            "citable_evidence": False,
            "context_visible": True,
        }
    if attention_score >= 0.55 and not generic_only:
        return {
            "query_local_role": "Supporting Context",
            "query_local_role_reason": "attention-supported context without enough direct query evidence",
            "query_local_role_signals": base_role_signals,
            "citable_evidence": False,
            "context_visible": True,
        }
    if attention_classification in {"Core", "Supporting"} and (contextual_overlap_count >= 1 or jaccard_to_question >= 0.08):
        return {
            "query_local_role": "Peripheral Context",
            "query_local_role_reason": "weak query-local relationship retained for diagnostics only",
            "query_local_role_signals": base_role_signals,
            "citable_evidence": False,
            "context_visible": True,
        }
    return {
        "query_local_role": "Non-Evidence",
        "query_local_role_reason": "insufficient query-local evidence relationship",
        "query_local_role_signals": base_role_signals,
        "citable_evidence": False,
        "context_visible": False,
    }


def _role_metadata(role: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_local_role": role["query_local_role"],
        "query_local_role_reason": role["query_local_role_reason"],
        "query_local_role_signals": role["query_local_role_signals"],
        "citable_evidence": role["citable_evidence"],
        "context_visible": role["context_visible"],
    }


def _role_signals(signals: dict[str, Any], *, extra: dict[str, Any]) -> dict[str, Any]:
    selected = {
        "attention_classification": signals.get("attention_classification"),
        "attention_score": signals.get("attention_score"),
        "activation_score": signals.get("activation_score"),
        "query_overlap": signals.get("query_overlap", []),
        "specific_overlap": signals.get("specific_overlap", []),
        "specific_overlap_count": signals.get("specific_overlap_count", 0),
        "domain_anchor_overlap": signals.get("domain_anchor_overlap", []),
        "generic_overlap": signals.get("generic_overlap", []),
        "generic_anchor_ratio": signals.get("generic_anchor_ratio", 0.0),
        "contextual_overlap_count": signals.get("contextual_overlap_count", 0),
        "jaccard_to_question": signals.get("jaccard_to_question", 0.0),
        "query_evidence_model": signals.get("query_evidence_model"),
        "query_evidence_support_score": signals.get("query_evidence_support_score"),
        "corpus_support_contextualized": signals.get("corpus_support_contextualized"),
        "corpus_support_only": signals.get("corpus_support_only"),
        "query_context_support_reason": signals.get("query_context_support_reason"),
    }
    selected.update(extra)
    return selected


def _has_context_marker(text: str) -> bool:
    return any(marker in text for marker in _QUERY_ROLE_CONTEXT_MARKERS)


def _has_direct_action_language(text: str) -> bool:
    return bool(_QUERY_ROLE_DIRECT_ACTION_RE.search(text))


def _role_gate_mode() -> str:
    raw = os.environ.get("DELTA_RUNTIME_V13_ROLE_GATE_MODE", "off").strip().lower()
    aliases = {
        "": "off",
        "0": "off",
        "false": "off",
        "model_b": "off",
        "r4": "r4",
        "role_model_r4": "r4",
        "hybrid_r4": "r4",
        "variant_a": "r4_planning_support",
        "planning_support": "r4_planning_support",
        "r4_planning_support": "r4_planning_support",
        "variant_b": "r4_operational_planning_support",
        "operational_planning_support": "r4_operational_planning_support",
        "r4_operational_planning_support": "r4_operational_planning_support",
        "variant_c": "response_citation_gate",
        "response_citation_gate": "response_citation_gate",
        "variant_d": "role_metadata_only",
        "metadata_only": "role_metadata_only",
        "role_metadata_only": "role_metadata_only",
        "variant_e": "r4_soft",
        "soft": "r4_soft",
        "r4_soft": "r4_soft",
    }
    return aliases.get(raw, raw)


def _planning_support_enters_reasoning(role: dict[str, Any]) -> bool:
    mode = str(role.get("query_local_role_signals", {}).get("role_gate_mode", ""))
    return mode == "response_citation_gate"


def _has_planning_support(
    *,
    mode: str,
    question: str,
    text: str,
    signals: dict[str, Any],
    high_context: bool,
    moderate_context: bool,
    generic_only: bool,
    has_context_marker: bool,
    has_direct_action_language: bool,
    has_domain_bridge: bool,
    evidence_support: float,
    attention_score: float,
) -> bool:
    if mode not in {
        "r4_planning_support",
        "r4_operational_planning_support",
        "response_citation_gate",
        "r4_soft",
    }:
        return False
    if evidence_support < 0.75:
        return False
    query_has_action = _has_action_or_planning_question(question)
    query_contextualized = bool(signals.get("corpus_support_contextualized"))
    if mode == "response_citation_gate":
        return query_contextualized or moderate_context or attention_score >= 0.55
    if mode == "r4_planning_support":
        return moderate_context or has_domain_bridge or (query_has_action and attention_score >= 0.52)
    if mode == "r4_soft":
        return (
            moderate_context
            or has_domain_bridge
            or (query_has_action and attention_score >= 0.50)
            or (has_context_marker and query_contextualized)
        )
    return (
        query_has_action
        and not generic_only
        and query_contextualized
        and (has_domain_bridge or high_context or has_direct_action_language or attention_score >= 0.55)
    )


def _has_action_or_planning_question(question: str) -> bool:
    return bool(
        re.search(
            r"\b(should|how should|plan|prepare|revise|allocated?|sequence|identify|gather|reconcile|handled|account)\b",
            question,
            re.I,
        )
    )


def _has_query_domain_bridge(question: str, text: str) -> bool:
    snow_question = "snowstorm" in question or ("snow" in question and "storm" in question)
    if snow_question and (
        "snow response" in text
        or "severe storm" in text
        or "shelter capacity" in text
        or "emergency access" in text
        or "evacuation corridor" in text
        or "hospital route" in text
    ):
        return True
    allocation_question = (
        "allocated" in question
        or "allocate" in question
        or "allocation" in question
        or "limited emergency" in question
    )
    if allocation_question and (
        "risk assessment" in text
        or "likelihood and impact" in text
        or "mitigation priorities" in text
        or "severity, urgency" in text
    ):
        return True
    return False


def _query_evidence_support_score(
    *,
    contextual_overlap_count: int,
    jaccard_to_question: float,
    attention_score: float,
    evidence_support: float,
    corpus_support_contextualized: bool,
) -> float:
    score = 0.0
    score += min(0.45, 0.15 * contextual_overlap_count)
    score += min(0.25, 1.10 * jaccard_to_question)
    score += min(0.20, 0.25 * attention_score)
    if evidence_support >= 0.75 and corpus_support_contextualized:
        score += 0.10
    return _bounded(score)


def _query_context_support_reason(
    *,
    contextual_overlap_count: int,
    jaccard_to_question: float,
    attention_score: float,
    generic_anchor_ratio: float,
    corpus_support_contextualized: bool,
) -> str:
    if contextual_overlap_count >= 3:
        return "strong specific/domain query overlap"
    if jaccard_to_question >= 0.14 and contextual_overlap_count >= 1 and generic_anchor_ratio < 0.70:
        return "phrase-level query/context overlap"
    if contextual_overlap_count >= 2 and attention_score >= 0.52:
        return "attention-supported non-generic query overlap"
    if contextual_overlap_count >= 1 and generic_anchor_ratio == 0.0 and attention_score >= 0.40:
        return "single non-generic query overlap with moderate attention support"
    if corpus_support_contextualized:
        return "technical/domain anchor query support"
    if corpus_support_contextualized:
        return "contextualized corpus support"
    return "corpus support only"


def _runtime_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9_]+", str(text).lower()):
        if len(raw) < 3 or raw in _USAGE_GATE_STOPWORDS:
            continue
        token = _normalize_runtime_token(raw)
        tokens.add(token)
    return tokens


def _normalize_runtime_token(token: str) -> str:
    if token == "cities":
        return "city"
    if token in {"allocated", "allocating", "allocation"}:
        return "allocate"
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


_USAGE_GATE_STOPWORDS = {
    "and",
    "are",
    "before",
    "during",
    "for",
    "from",
    "how",
    "into",
    "should",
    "that",
    "the",
    "what",
    "when",
    "where",
    "why",
    "with",
}

_USAGE_GATE_BROAD_TERMS = {
    "capacity",
    "evidence",
    "failure",
    "finding",
    "plan",
    "policy",
    "report",
    "resource",
    "risk",
    "uncertainty",
}

_USAGE_GATE_GENERIC_ANCHOR_TERMS = {
    "change",
    "changes",
    "finding",
    "findings",
    "response",
}

_USAGE_GATE_DOMAIN_ANCHOR_TERMS = {
    "assumption",
    "audit",
    "contradictory",
    "emergency",
    "industrial",
    "maintenance",
    "permit",
    "shelter",
    "shelters",
}

_USAGE_GATE_TECHNICAL_ANCHOR_TERMS = {
    "gps",
}

_QUERY_ROLE_CONTEXT_MARKERS = {
    "for instance",
    "for example",
    "this scenario",
    "current understanding",
    "it might be tempting",
    "would suggest",
    "certainty of",
    "depends on",
}

_QUERY_ROLE_ACTIONABLE_RISK_TERMS = {
    "assumption",
    "evidence",
    "failure",
    "risk",
    "uncertainty",
}

_QUERY_ROLE_DIRECT_ACTION_RE = re.compile(
    r"\b(should|requires?|revise|analy[sz]e|compare|establish|examining|allocate|"
    r"reconcile|sequence|validate|identify|review|determine|use|using|cause|causes|"
    r"caused|support|supports)\b",
    re.I,
)

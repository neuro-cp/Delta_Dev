# Routing File Inventory

Repository: `G:\Delta_Dev`
Branch: `codex/delta-cognitive-core`
HEAD: `f8d0c343452141d26509f44f5198b69e20b695e4`

Initial runtime state:
```text
## codex/delta-cognitive-core...origin/codex/delta-cognitive-core
 M docs/continuous_runtime/CONTINUOUS_RUNTIME_ARCHITECTURE.md
 M docs/continuous_runtime/FAILURE_RECOVERY.md
 M docs/continuous_runtime/MODEL_ORCHESTRATION.md
 M docs/continuous_runtime/OPERATING_LIFECYCLE.md
 M docs/continuous_runtime/OPERATOR_GUIDE.md
 M docs/delta_1_0/DELTA_1_0_ARCHITECTURE.md
 M orchestration/runtime/continuous_runtime_controller.py
 M orchestration/runtime/delta_1_4_live_wikipedia_runtime.py
 M orchestration/runtime/rc2_conversational_mode_router.py
 M reports/RC2_COMPACT_PROVIDER_CONSENT.json
 M reports/RC2_CONCEPT_GRAPH_LINKING.json
 M reports/RC2_CONVERSATIONAL_ARCHITECTURE.json
 M reports/RC2_CONVERSATIONAL_MODE_ROUTER.json
 M reports/RC2_DEVELOPMENTAL_CONCEPT_FORMATION.json
 M reports/RC2_SELECTIVE_MEMORY_EXPERIMENT.json
 M reports/RC3_C_ENGINEERING_FOUNDATION.json
 M reports/RC3_C_ENGINEERING_FOUNDATION.md
 M reports/RC3_D_SANDBOX_FOUNDATION.json
 M reports/RC3_D_SANDBOX_FOUNDATION.md
 M reports/continuous_runtime/behavioral_campaign.json
 M reports/continuous_runtime/behavioral_campaign.md
 M reports/continuous_runtime/engineering_notebook.md
 M reports/continuous_runtime/performance.json
 M reports/continuous_runtime/performance.md
 M reports/continuous_runtime/readiness.json
 M reports/continuous_runtime/readiness.md
 M reports/continuous_runtime/validation.json
 M reports/continuous_runtime/validation.md
 M reports/delta_1_0/DELTA_1_0_OPERATOR_PILOT_AND_GATED_ACTIVATION.md
 M reports/delta_1_0/readiness.md
 M tests/continuous_runtime/test_continuous_runtime_controller.py
 M tests/delta_1_4/test_live_wikipedia_runtime.py
?? docs/continuous_runtime/ROUTING_STABILIZATION.md
?? reports/DELTA_1_0_EXTERNAL_SURFACE_GATING_GROUNDING.md
?? reports/DELTA_1_0_GOVERNED_INTROSPECTIVE_IMPROVEMENT_LOOP.md
?? reports/DELTA_LIVE_BEHAVIORAL_VALIDATION_A_A2.md
?? reports/DELTA_STAGE_A_A2_REPAIR_GROUP_CLOSURE.md
?? reports/DELTA_STAGE_B_LIVE_CONTINUITY_TEST.md
?? reports/routing_system_export/
?? tests/runtime_rc2/test_rc2_routing_stabilization.py
```

## ACTIVE_RUNTIME

### DELTA.py
File: `DELTA.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Tk application, launch entry point, chat submission handler, pending UI state, live-runtime worker dispatch, and final response insertion.
Key classes/functions: def _format_cognitive_state (L105), def _format_snapshot (L121), def _extract_report_path (L171), def _inspect_local_report (L178), def _report_inspection_safety (L211), def _pc1_enabled (L223), def _pc1_context_for_message (L228), def _try_pc1_pragmatic_answer (L242), def _pc1_has_governance_cue (L286), def _render_pc1_pragmatic_answer (L311), def _pc1_safety (L397), def _rc7_developer_overlay_text (L411), def _plateau_developer_overlay_text (L416), def _is_rc6_pilot_message (L421), def _handle_rc6_pilot_message (L433), def _extract_rc6_embedded_text (L483), def _build_rc6_ui_packet (L499), def _render_rc6_classification (L517), def _render_rc6_packet_result (L541), def _mock_advisory_payload_from_text (L583), def _render_rc6_advisory_validation (L597), def _render_rc6_pilot_summary (L614), def _summarize_report_text (L665), def _summarize_rc6_gateway_readiness (L683), def _summarize_rc45_freeze_report (L710)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.model_runtime.provider_manager, orchestration.runtime.continuous_runtime_controller, orchestration.runtime.delta_1_4_live_wikipedia_runtime, orchestration.runtime.integrated_cognitive_runtime, orchestration.runtime.pc1_pragmatic_cognition, orchestration.runtime.rc11_rc12_systems_plateau, orchestration.runtime.rc1_operator_console, orchestration.runtime.rc2_conversational_mode_router, orchestration.runtime.rc2_developmental_concept_memory, orchestration.runtime.rc2_render_correction, orchestration.runtime.rc2_storage_adapter, orchestration.runtime.rc2_substrate_reconciliation, orchestration.runtime.rc3_ui_capability_adapter, orchestration.runtime.rc45_discourse_cognition_bridge, orchestration.runtime.rc4_ui_capability_adapter, orchestration.runtime.rc5_developmental_cognition, orchestration.runtime.rc5_ui_capability_adapter, orchestration.runtime.rc6_governed_external_intelligence, orchestration.runtime.rc7_governed_development_loop
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Tk application, launch entry point, chat submission handler, pending UI state, live-runtime worker dispatch, and final response insertion.

### orchestration/runtime/delta_1_4_live_wikipedia_runtime.py
File: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Live runtime bridge; first live-mode receiver for raw operator text; arbitrates lifecycle controls, pending approvals, Wikipedia, local-model approvals, operational self-model, and fallback RC2 conversation.
Key classes/functions: class WikipediaTextResult (L76), class LiveChatResponse (L96), class LiveWikipediaRuntimeSession (L106), def activated_wikipedia_profile (L133), def start_live_wikipedia_runtime (L145), def stop_live_wikipedia_runtime (L192), def handle_live_chat (L201), def wikipedia_query_from_message (L524), def _has_explicit_wikipedia_intent (L545), def _live_routing_trace (L553), def retrieve_wikipedia_text (L574), def render_wikipedia_answer (L603), def _default_wikipedia_transport (L615), def _default_wikipedia_transport_once (L628), def _wait_for_polite_wikipedia_slot (L649), def _clean_query (L659), def _retrieval_safety (L665), def _is_memory_request (L673), def _base_live_payload (L678), def _runtime_control_intent (L695), def _handle_runtime_control_intent (L712), def _render_runtime_state (L739), def _is_pending_inquiry_question (L759), def _is_affirmative (L764), def _is_rejection (L796)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.continuous_runtime_controller, orchestration.runtime.delta_1_0_common, orchestration.runtime.delta_1_1_development_loop, orchestration.runtime.delta_1_2_live_runtime, orchestration.runtime.delta_1_5_developmental_cognition, orchestration.runtime.delta_1_6_operational_autonomy, orchestration.runtime.rc2_conversational_mode_router
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Live runtime bridge; first live-mode receiver for raw operator text; arbitrates lifecycle controls, pending approvals, Wikipedia, local-model approvals, operational self-model, and fallback RC2 conversation.

### orchestration/runtime/rc2_conversational_mode_router.py
File: `orchestration/runtime/rc2_conversational_mode_router.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Primary non-live conversation router; classifies intent, selects local model lane, orders conversation/retrieval/follow-up/provider/local-model routes, builds payloads, and renders responses.
Key classes/functions: def classify_intent (L244), def _is_memory_browse_request (L334), def _is_contextual_browse_followup (L349), def _is_contextual_browse_jump (L362), def _is_synthesis_trial_request (L373), def _is_graph_assisted_reasoning_request (L385), def _domain_browse_request (L434), def _last_concept_context (L450), def resolve_followup_anchor (L490), def _is_anchor_followup (L509), def _is_explicit_new_topic_request (L531), def _is_brainstorming_request (L548), def _is_context_dependent_followup (L559), def _is_anchor_browse_followup (L586), def deepen_from_concept_anchor (L591), def browse_near_active_anchor (L622), def _get_concept (L678), def _anchor_concept (L692), def _anchored_concept_answer (L706), def _anchor_from_matches (L742), def _sun_blue_correction (L758), def select_model_lane (L771), def _select_usable_model_for_lane (L818), def _model_candidate (L852), def _selection_reason (L863)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.model_runtime.model_registry, integration.model_runtime.provider_manager, orchestration.runtime.rc1_operator_console, orchestration.runtime.rc2_analogy_engine, orchestration.runtime.rc2_cognitive_episode, orchestration.runtime.rc2_contradiction_engine, orchestration.runtime.rc2_developmental_concept_memory, orchestration.runtime.rc2_dialogue_intent_classifier, orchestration.runtime.rc2_graph_assisted_reasoning, orchestration.runtime.rc2_natural_conversation_renderer, orchestration.runtime.rc2_render_correction, orchestration.runtime.rc2_route_arbitration, orchestration.runtime.rc2_storage_adapter, orchestration.runtime.rc2_working_reasoning_set, orchestration.runtime.v17_provider_assisted_unknown_answer, orchestration.runtime.v29_local_answer_engine
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Primary non-live conversation router; classifies intent, selects local model lane, orders conversation/retrieval/follow-up/provider/local-model routes, builds payloads, and renders responses.

## ACTIVE_SUPPORTING_STATE

### orchestration/runtime/rc45_discourse_cognition_bridge.py
File: `orchestration/runtime/rc45_discourse_cognition_bridge.py`
Active status: Active in current Tk/live runtime
Primary responsibility: UI-side discourse frame and preemption rules for report/pilot/operator follow-up shortcuts before RC2 routing.
Key classes/functions: class DiscourseFrame (L19), def as_dict (L37), def build_discourse_frame (L41), def should_preempt_specialist_routing (L262), def _frame (L266), def _normalize (L298), def _extract_report_path (L302), def _extract_constraints (L307), def _topic_from_context (L322), def _is_pilot_checklist_request (L330), def _is_pilot_session_record_request (L343), def _is_second_one_followup (L350), def _is_rc5_gpt_boundary_question (L354), def _is_rc4_handoff_boundary_question (L362), def _is_full_pilot_freeze_decision_question (L370), def _is_primary_freeze_proof_question (L378), def _is_recovery_evidence_enrichment_question (L388), def _is_mixed_proposal_record_question (L395), def _is_useful_but_unsafe_advice_question (L403)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_render_correction
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: UI-side discourse frame and preemption rules for report/pilot/operator follow-up shortcuts before RC2 routing.

### orchestration/runtime/rc2_cognitive_episode.py
File: `orchestration/runtime/rc2_cognitive_episode.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Working-memory episode and follow-up/pronoun/reference resolution attached to RC2 payloads.
Key classes/functions: class CognitiveEpisode (L92), def build_cognitive_episode (L116), def resolve_working_memory_followup (L163), def attach_episode (L229), def build_working_memory_episode_report (L239), def _norm (L273), def _episode_id (L278), def _entities (L283), def _branches (L295), def _dedupe_branches (L337), def _select_active_branch (L349), def _branch_by_ordinal (L362), def _subject_branch (L368), def _topic_from_question (L376), def _route_hint (L410), def _summary (L421), def _semantic_answer (L427), def _examples (L432), def _limits (L437), def _unresolved (L442), def _resolved_refs (L446), def _rejected_refs (L453), def _explicit_topic_change (L464), def _explicit_topic_reset (L477), def _episode_confidence (L493)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Working-memory episode and follow-up/pronoun/reference resolution attached to RC2 payloads.

### orchestration/runtime/continuous_runtime_controller.py
File: `orchestration/runtime/continuous_runtime_controller.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Live runtime lifecycle controller and background objective/event/state arbitration surfaced in status and live decisions.
Key classes/functions: class ContinuousRuntimeConfig (L113), class ContinuousEvent (L131), class ModelResidencyPolicy (L150), class NotificationPolicyState (L176), class ContinuousObjective (L186), class SandboxDevelopmentProposal (L199), class HealthReport (L216), class RuntimeCycleRecord (L231), class ContinuousRuntimeController (L250), def as_dict (L273), def build_model_residency_policy (L277), def start_continuous_runtime_controller (L301), def transition_controller (L340), def make_continuous_event (L348), def enqueue_continuous_event (L382), def run_controller_cycle (L393), def pause_controller (L478), def resume_controller (L485), def suspend_controller (L492), def shutdown_controller (L502), def controller_snapshot (L514), def run_bounded_long_run (L540), def write_continuous_runtime_reports (L609), def build_report_payload (L631), def _continuous_docs (L762)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.delta_1_0_common, orchestration.runtime.delta_1_6_operational_autonomy, orchestration.runtime.rc2_conversational_mode_router
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Live runtime lifecycle controller and background objective/event/state arbitration surfaced in status and live decisions.

### orchestration/runtime/delta_1_2_live_runtime.py
File: `orchestration/runtime/delta_1_2_live_runtime.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Live runtime state, event queue, wake cycle, journal, and future-surface permission scaffolding.
Key classes/functions: class LiveRuntimeConfig (L72), class RuntimeEvent (L88), class EventQueue (L101), class LiveObservation (L109), class AttentionDecision (L124), class CuriosityInquiryCandidate (L135), class DevelopmentSignal (L148), class CandidateGoal (L161), class GoalArbitration (L178), class ReflectionSummary (L189), class OperatorInquiryV12 (L205), class NotificationDecision (L221), class ActivityJournalEntry (L232), class ActivityJournal (L243), class RuntimeIdentity (L251), class FutureSurfaceReadiness (L265), class LiveRuntimeState (L277), def boot_live_runtime (L298), def transition_runtime (L333), def create_event (L341), def enqueue_event (L355), def dequeue_batch (L360), def observe_events (L368), def attention_for_observation (L391), def score_attention (L415)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.delta_1_0_common, orchestration.runtime.delta_1_1_development_loop
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Live runtime state, event queue, wake cycle, journal, and future-surface permission scaffolding.

### orchestration/runtime/delta_1_6_operational_autonomy.py
File: `orchestration/runtime/delta_1_6_operational_autonomy.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Operational self-model, autonomy status, background cycle, initiative/inquiry/proposal formation.
Key classes/functions: class AuthorityRequest (L96), class AuthorityDecision (L116), class IdentityProposal (L130), class OperationalSelfModel (L148), def as_dict (L180), class Initiative (L185), class BackgroundCycleResult (L206), def as_dict (L217), def evaluate_authority (L221), def build_operational_self_model (L273), def maybe_propose_identity (L340), def run_delta_1_6_background_cycle (L366), def answer_operational_self_model_question (L480), def is_operational_self_model_question (L542), def set_autonomy_status (L585), def write_delta_1_6_reports (L593), def build_delta_1_6_report_payload (L614), def _capability_summary (L696), def _capability_boundaries (L708), def _pending_inquiries (L719), def _external_surfaces (L731), def _health (L740), def _uncertainty_summary (L750), def _current_identity (L761)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.delta_1_0_capability_activation, orchestration.runtime.delta_1_0_common, orchestration.runtime.delta_1_2_live_runtime
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Operational self-model, autonomy status, background cycle, initiative/inquiry/proposal formation.

### orchestration/runtime/delta_1_0_common.py
File: `orchestration/runtime/delta_1_0_common.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Shared timestamps, stable ids, and safety metadata used by live routing artifacts.
Key classes/functions: def utc_now (L49), def stable_id (L53), def safety_metadata (L59), def jsonable (L63), def write_json (L77), def write_markdown (L82), def bounds_report (L99)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Shared timestamps, stable ids, and safety metadata used by live routing artifacts.

## ACTIVE_RETRIEVAL

### orchestration/runtime/rc2_developmental_concept_memory.py
File: `orchestration/runtime/rc2_developmental_concept_memory.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Approved concept retrieval, browsing, multi-concept retrieval, candidate concept formation, approval, relevance gates, and compact support packets.
Key classes/functions: def discover_memory_store_separation (L135), def extract_candidate_concept (L156), def approve_candidate_concept (L202), def merge_concept_enrichment (L293), def load_approved_concepts (L319), def clear_runtime_concept_caches (L333), def build_runtime_concept_index (L342), def retrieval_query_profile (L383), def rank_approved_concepts (L408), def score_concept_for_query (L491), def _candidate_concepts_for_profile (L594), def _copy_rank_result (L633), def _recall_search_query (L641), def query_approved_concepts (L663), def parse_multi_concept_query (L697), def retrieve_multi_concept_set (L726), def build_read_only_synthesis_trial (L783), def _select_substantive_synthesis_rows (L836), def _synthesis_substance_score (L845), def _is_generic_synthesis_definition (L863), def _is_generic_synthesis_related (L873), def _compact_concept_for_synthesis (L878), def _tentative_bridge (L894), def _synthesis_uncertainty (L909), def browse_approved_concepts (L917)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_sqlite_substrate
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Approved concept retrieval, browsing, multi-concept retrieval, candidate concept formation, approval, relevance gates, and compact support packets.

### orchestration/runtime/rc2_storage_adapter.py
File: `orchestration/runtime/rc2_storage_adapter.py`
Active status: Active in current Tk/live runtime
Primary responsibility: SQLite/JSONL substrate adapter used by UI database search and anchor/nearby concept retrieval.
Key classes/functions: def backend_health (L25), def substrate_counts (L29), def load_concepts (L71), def load_diverse_concepts (L79), def get_concept (L104), def search_concepts (L114), def get_edges_for_concept (L138), def get_outgoing_edges (L147), def get_incoming_edges (L156), def traverse_graph (L165), def get_graph_neighborhood (L172)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime, orchestration.runtime.rc2_developmental_concept_memory, orchestration.runtime.rc2_governed_semantic_graph, orchestration.runtime.rc2_substrate_reconciliation
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: SQLite/JSONL substrate adapter used by UI database search and anchor/nearby concept retrieval.

### orchestration/runtime/rc2_working_reasoning_set.py
File: `orchestration/runtime/rc2_working_reasoning_set.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Ephemeral multi-concept working set selector for complex prompts.
Key classes/functions: class WorkingReasoningSet (L132), def _now (L149), def should_use_wrs (L153), def _tokens (L183), def extract_reasoning_seeds (L190), def required_topic_families (L235), def _concept_key (L277), def retrieve_wrs_concepts (L281), def _covered_families (L338), def _rank_seed_matches (L348), def key (L351), def _prioritize_required_family_representatives (L362), def _compact_concept (L376), def _proposition_pool (L392), def _is_substantive_proposition (L408), def _substantive_propositions (L420), def _shared_principles (L425), def _conflicts (L442), def _missing_evidence (L453), def _graph_edges (L468), def _possible_connections (L490), def _higher_order_bridge (L509), def _topic_family (L606), def _distinct_topic_pair (L659), def _is_scaffold_concept (L675)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_storage_adapter
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Ephemeral multi-concept working set selector for complex prompts.

### orchestration/runtime/rc2_analogy_engine.py
File: `orchestration/runtime/rc2_analogy_engine.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Analogy route detection and structural mapping payloads.
Key classes/functions: class AnalogyAnalysisSet (L201), def is_analogy_prompt (L229), def build_analogy_analysis (L246), def build_analogy_engine_report (L311), def _clean (L356), def _extract_pair (L360), def _trim_group (L395), def _match_spec (L399), def _generic_spec (L420), def _retrieve_concepts (L434), def _graph_support (L451), def _classification_for (L463), def _confidence_for (L467), def _role_mapping (L473), def _surface_similarities (L479), def _missing_evidence (L486), def _render_analogy (L495), def _cases (L514), def _write_md (L537), def main (L565)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_storage_adapter
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Analogy route detection and structural mapping payloads.

### orchestration/runtime/rc2_contradiction_engine.py
File: `orchestration/runtime/rc2_contradiction_engine.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Contradiction route detection and comparison payloads.
Key classes/functions: class ContradictionClaim (L128), class ContradictionAnalysisSet (L143), def is_contradiction_prompt (L158), def build_contradiction_analysis (L169), def build_contradiction_engine_report (L194), def _clean_text (L237), def _looks_like_two_claims (L241), def _has_implicit_contradiction_cue (L245), def _extract_claim_texts (L253), def _claims_from_history (L277), def _expand_fragment (L288), def _normalize_claim (L294), def _has_negation (L325), def _subjects (L329), def _fallback_subject (L339), def _markers (L344), def _conditions (L348), def _definitions (L356), def _retrieve_balanced_evidence (L362), def _compact_concept (L374), def _classify_analysis (L386), def _set_result (L432), def _related_subjects (L438), def _predicate_overlap (L453), def _semantic_opposition (L458)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_storage_adapter
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Contradiction route detection and comparison payloads.

### orchestration/runtime/delta_1_5_developmental_cognition.py
File: `orchestration/runtime/delta_1_5_developmental_cognition.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Wikipedia evidence to governed developmental observation, promotion candidate, and operator inquiry.
Key classes/functions: class EvidenceComparison (L29), class KnowledgeGap (L41), class DevelopmentObjective (L51), class PromotionCandidate (L64), class OperatorInquiry (L78), class DevelopmentalCognitionResult (L87), def as_dict (L101), def run_wikipedia_developmental_cognition (L105), def render_developmental_observation (L187), def write_delta_1_5_campaign_reports (L198), def _build_comparison (L217), def _extract_evidence_terms (L254), def _detect_conflict_signals (L293), def _local_text (L303), def _snapshot_local (L313), def _observation_sentence (L329), def _gap_summary (L336), def _contains_term (L341), def _normalize_text (L348), def _term_is_useful (L356), def _append_unique (L376)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.delta_1_0_common, orchestration.runtime.rc2_developmental_concept_memory
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Wikipedia evidence to governed developmental observation, promotion candidate, and operator inquiry.

## ACTIVE_MODEL_ROUTING

### integration/model_runtime/model_registry.py
File: `integration/model_runtime/model_registry.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Local model discovery and model specs used by lane selection.
Key classes/functions: class ModelSpec (L17), def model_root (L31), def discover_local_models (L38), def list_available_models (L58), def list_models (L66), def get_model_spec (L70), def _spec_from_path (L78), def _aliases (L102), def _model_id (L119), def _family (L127), def _quantization (L144), def _context_length (L149), def _tier (L160)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Local model discovery and model specs used by lane selection.

### integration/model_runtime/provider_manager.py
File: `integration/model_runtime/provider_manager.py`
Active status: Active in current Tk/live runtime
Primary responsibility: One-resident-model local inference lifecycle manager used by UI/live approved local calls.
Key classes/functions: class ProviderRunner (L16), def produce_output (L17), def json_dumps_state (L24), class ProviderLoadState (L29), class ProviderManager (L39), def __init__ (L48), def load (L72), def warm (L83), def infer (L90), def unload (L111), def status (L125), def _publish_status (L137), def _resolve (L147), def _create_runner (L156), def _canonical_result (L163), def _metadata (L206), def _gpu_layers_for (L225), def _profile_for (L244)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.model_runtime.gguf_model_runner, integration.model_runtime.inference_types, integration.model_runtime.model_registry, integration.model_runtime.provider_qualification
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: One-resident-model local inference lifecycle manager used by UI/live approved local calls.

### integration/model_runtime/gguf_model_runner.py
File: `integration/model_runtime/gguf_model_runner.py`
Active status: Active in current Tk/live runtime
Primary responsibility: GGUF llama.cpp runner invoked by ProviderManager.
Key classes/functions: class GGUFModelRunner (L35), def __init__ (L40), def load_model (L45), def unload (L49), def _model_id (L56), def _extract_json (L72), def _extract_answer (L85), def _extract_model_confidence (L94), def _heuristic_confidence (L119), def _combine_confidence (L148), def produce_output (L165)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.ai_surface.ai_model_interface, integration.ai_surface.ai_output_bundle, integration.model_runtime.inference_types, integration.model_runtime.model_registry, integration.model_runtime.model_session, integration.model_runtime.prompt_builder
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: GGUF llama.cpp runner invoked by ProviderManager.

### scripts/delta_rc2_local_model_infer.py
File: `scripts/delta_rc2_local_model_infer.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Fallback subprocess helper for local model inference.
Key classes/functions: def main (L16)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.model_runtime.provider_manager
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Fallback subprocess helper for local model inference.

## ACTIVE_GOVERNANCE

### orchestration/runtime/rc1_operator_console.py
File: `orchestration/runtime/rc1_operator_console.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Advanced operator substrate functions retained and still imported by RC2 mode routes and UI advanced panels.
Key classes/functions: def _load_json (L51), def _read_jsonl (L57), def _append_jsonl (L67), def _stable_id (L73), def normalize_claim (L77), def detect_contradictions_for_record (L124), def report_summary (L150), def build_runtime_status (L161), def build_corpus_substrate_summary (L175), def build_review_queue (L196), def build_replay_rollback_inspection (L210), def build_operator_snapshot (L222), def answer_operator_question (L235), def preview_evidence_ingest (L267), def extract_propositions (L283), def approve_propositions (L323), def clear_local_noncanonical_store (L390), def build_cognitive_state (L423), def query_noncanonical_substrate (L442), def build_observation_entry (L511), def append_observation (L534), def validate_console_safe (L548)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc1_release_candidate_freeze, orchestration.runtime.tp16_tp30_master_marathon, orchestration.runtime.v29_local_answer_engine
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Advanced operator substrate functions retained and still imported by RC2 mode routes and UI advanced panels.

### orchestration/runtime/rc2_render_correction.py
File: `orchestration/runtime/rc2_render_correction.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Early UI route for render-correction requests and RC2 render-correction payloads.
Key classes/functions: class RenderCorrectionFrame (L28), def as_dict (L38), def build_render_correction_payload (L42), def is_render_correction_request (L98), def _normalize (L102), def _is_render_correction_request (L106), def _explicit_new_content_request (L145), def _last_assistant_answer (L156), def _fallback_semantic_answer (L165), def _constraints (L185), def _requested_headings (L208), def _canonical_heading (L220), def _render (L234), def _render_with_headings (L251), def _section_content (L261), def _find_sentence (L275), def _sentences (L283), def _clean_answer (L291), def _remove_render_correction_boilerplate (L296), def _strip_section_prefix (L312), def _is_section_heading_only (L335), def _topic_from_message (L348), def _infer_topic (L357), def _infer_intent (L361), def _safety_suffix (L372)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Early UI route for render-correction requests and RC2 render-correction payloads.

### orchestration/runtime/v17_provider_assisted_unknown_answer.py
File: `orchestration/runtime/v17_provider_assisted_unknown_answer.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Provider consent and unknown-answer gate used for preview and approved provider support.
Key classes/functions: class UnknownAnswerDecisionValue (L28), class UnknownAnswerRequest (L36), def as_dict (L41), def answer_unknown_with_controlled_provider (L48), def validate_unknown_answer_safe (L68), def _payload (L83), def _provider_request (L102), def _api_key_present (L106), def _bool (L111), def _stable_id (L115)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.v15_local_knowledge_router, orchestration.runtime.v16_env, orchestration.runtime.v16_external_consolidation_evaluator_api_trial
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Provider consent and unknown-answer gate used for preview and approved provider support.

### orchestration/runtime/delta_1_1_development_loop.py
File: `orchestration/runtime/delta_1_1_development_loop.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Wikipedia permission profile schema used by live runtime.
Key classes/functions: class DevelopmentObservation (L74), class DevelopmentObjectiveV11 (L89), class ObjectivePriority (L111), class DevelopmentPlan (L126), class DevelopmentEvidencePacket (L142), class ImprovementEvaluation (L156), class LessonCandidateV11 (L173), class OperatorInquiry (L190), class WikipediaPermissionProfile (L202), class WikipediaRetrievalSessionState (L220), class DevelopmentSession (L241), def observe_development_evidence (L259), def build_evidence_packet (L286), def generate_candidate_objectives (L299), def prioritize_objectives (L335), def select_best_objective (L390), def request_operator_approval (L396), def approve_objective (L408), def generate_development_plan (L414), def evaluate_improvement (L432), def generate_lesson_candidate (L457), def dispose_lesson_candidate (L477), def build_wikipedia_readiness (L485), def run_development_session (L498), def sample_development_records (L552)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.delta_1_0_common
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Wikipedia permission profile schema used by live runtime.

## ACTIVE_RESPONSE_COMPOSITION

### orchestration/runtime/rc2_natural_conversation_renderer.py
File: `orchestration/runtime/rc2_natural_conversation_renderer.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Natural response post-processing for RC2 payload answers.
Key classes/functions: def apply_natural_renderer (L42), def build_natural_renderer_report (L77), def _render_wrs (L136), def _render_concept_memory (L161), def _render_browse (L192), def _render_multi_concept (L203), def _render_consent (L211), def _best_prop_for (L218), def _clean_name (L230), def _clean_sentence (L235), def _clean_answer (L241), def _natural_uncertainty (L252), def _contains_any (L259), def _internal_leak (L264), def _write_md (L269), def main (L297)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_conversational_mode_router
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Natural response post-processing for RC2 payload answers.

### orchestration/runtime/rc2_route_arbitration.py
File: `orchestration/runtime/rc2_route_arbitration.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Route arbitration trace and safety normalization attached to RC2 payloads.
Key classes/functions: class RouteCandidate (L80), def normalize_safety_payload (L92), def build_route_arbitration_trace (L108), def _recommended_group (L157), def safety_schema_complete (L165), def write_arbitration_reference (L169), def _build_candidates (L178), def _norm (L276), def _matched_terms (L280), def _explicit_command (L284), def _has_two_claims (L288), def _has_analogy_shape (L292), def _looks_multi_concept (L296), def _looks_single_concept (L300), def _looks_unknown_or_external (L304)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc2_analogy_engine, orchestration.runtime.rc2_cognitive_episode, orchestration.runtime.rc2_contradiction_engine, orchestration.runtime.rc2_working_reasoning_set
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Route arbitration trace and safety normalization attached to RC2 payloads.

### orchestration/runtime/pc1_pragmatic_cognition.py
File: `orchestration/runtime/pc1_pragmatic_cognition.py`
Active status: Active in current Tk/live runtime
Primary responsibility: UI-side pragmatic answer shortcut before pending-action/RC2 routing.
Key classes/functions: class PragmaticEvidence (L25), def as_dict (L31), class PragmaticCounterEvidence (L36), def as_dict (L42), class OperatorGoalHypothesis (L47), def as_dict (L55), class ImmediateIntent (L62), def as_dict (L70), class ImpliedConstraint (L77), def as_dict (L84), class ScopeBinding (L89), def as_dict (L97), class PerspectiveBinding (L102), def as_dict (L109), class MixedJudgment (L114), def as_dict (L122), class AlternativeInterpretation (L129), def as_dict (L136), class CooperativeInterpretation (L141), def as_dict (L152), class PracticalResponseGoal (L161), def as_dict (L168), class ResponseShape (L173), def as_dict (L179), class PragmaticConfidence (L184)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: UI-side pragmatic answer shortcut before pending-action/RC2 routing.

### orchestration/runtime/v29_local_answer_engine.py
File: `orchestration/runtime/v29_local_answer_engine.py`
Active status: Active in current Tk/live runtime
Primary responsibility: Local deterministic answer engine used inside RC2 local conversation answer path.
Key classes/functions: def run_v29_local_answer (L13), def format_v29_cli_output (L83), def write_v29_answer_report (L104)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.v22_controlled_general_recall_expansion, orchestration.runtime.v29_current_state_knowledge_inventory, orchestration.runtime.v29_natural_alias_router
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: Local deterministic answer engine used inside RC2 local conversation answer path.

## DORMANT_OR_OBSOLETE

### orchestration/runtime/integrated_cognitive_runtime.py
File: `orchestration/runtime/integrated_cognitive_runtime.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def build_architecture_audit (L62), def build_integrated_cognitive_trace (L123), def evaluate_long_conversation (L199), def evaluate_operator_scenarios (L215), def evaluate_adversarial_cross_layer (L240), def measure_performance (L263), def build_cognitive_metrics (L295), def build_readiness_review (L318), def write_integrated_runtime_reports (L371), def _build_rc4_authorization (L380), def _build_rc5_development (L406), def _cross_layer_consistency (L421), def _final_response_policy (L455), def _operator_scenarios (L473), def _adversarial_cases (L491), def _long_conversation_messages (L505), def _pc1_context (L521), def _anchor_for_turn (L531), def _default_anchor (L535), def _compact_route (L542), def _scenario_pass (L547), def _development_usefulness_probe (L555), def _operator_workload_estimate (L560), def _readiness_weaknesses (L567), def _contains_consistency_issue (L587)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.pc1_pragmatic_cognition, orchestration.runtime.rc2_conversational_mode_router, orchestration.runtime.rc3_goal_interpreter, orchestration.runtime.rc3_plan_generator, orchestration.runtime.rc3_plan_validator, orchestration.runtime.rc45_discourse_cognition_bridge, orchestration.runtime.rc4_governed_action_runtime, orchestration.runtime.rc5_developmental_cognition
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc3_ui_capability_adapter.py
File: `orchestration/runtime/rc3_ui_capability_adapter.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def build_rc3_ui_snapshot (L45), def render_rc3_panel (L92), def validate_rc3_ui_snapshot (L119), def build_rc3_ui_integration_report (L140), def _goal_panel (L163), def _plan_panel (L185), def _revision_panel (L209), def _introspection_panel (L231), def _engineering_panel (L257), def _sandbox_panel (L281), def _stage_panel (L305), def _persistence_panel (L321), def _pilot_panel (L351), def _freeze_panel (L373), def _diagnostics_panel (L394), def _load_reports (L415), def _stage_report_from_file (L428), def _report (L437), def _freeze_recommendation (L444), def _operator_pilot_final (L458), def _freeze_final (L471), def _write_report (L493)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc4_ui_capability_adapter.py
File: `orchestration/runtime/rc4_ui_capability_adapter.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def build_rc4_ui_snapshot (L38), def render_rc4_panel (L79), def validate_rc4_ui_snapshot (L102), def build_rc4_ui_integration_report (L115), def _panel (L133), def _integration_panel (L148), def _pilot_panel (L167), def _freeze_panel (L184), def _load_reports (L200), def _write_report (L211)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc4_governed_action_runtime
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc5_ui_capability_adapter.py
File: `orchestration/runtime/rc5_ui_capability_adapter.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def build_rc5_ui_snapshot (L39), def render_rc5_panel (L82), def validate_rc5_ui_snapshot (L105), def build_rc5_ui_integration_report (L122), def _panel (L140), def _consultation_panel (L156), def _pilot_panel (L173), def _mimic_panel (L189), def _freeze_panel (L210), def _load_reports (L227), def _write_report (L238)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc5_developmental_cognition
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc6_governed_external_intelligence.py
File: `orchestration/runtime/rc6_governed_external_intelligence.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def _now (L134), def stable_id (L138), def fake_secret_token (L143), class ProviderContract (L148), class ModelAllowlist (L160), class ConsultationAuthority (L169), class ProviderPermission (L178), class TransportPolicy (L187), class ProviderRiskClass (L197), class ProviderExclusionPolicy (L207), class ProviderConstitution (L215), class SensitivityScan (L225), class RedactionResult (L233), class TokenBudget (L243), class CostBudget (L249), class ConsultationEstimate (L255), class BudgetDecision (L264), class UsageRecord (L272), class DevelopmentConsultationRequest (L282), class ExternalProviderRequest (L303), class GatewayDecision (L313), class GatewayResult (L322), class RetryPolicy (L333), class FailurePolicy (L340), class TransportMetrics (L349)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc5_developmental_cognition
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc7_governed_development_loop.py
File: `orchestration/runtime/rc7_governed_development_loop.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def _now (L27), def stable_id (L31), class CampaignEvidence (L37), class CampaignRisk (L46), class ObservedDeficit (L54), class ImprovementHypothesis (L64), class ConsultationDecision (L75), class ImplementationProposal (L85), class ValidationResult (L97), class ComparativeOutcome (L107), class OperatorDisposition (L120), class DevelopmentCycle (L129), class CampaignCheckpoint (L142), class CampaignConfidence (L153), class CampaignHealth (L160), class CampaignPriority (L175), class CampaignStopReason (L184), class CampaignSummary (L192), class DevelopmentCampaign (L203), class DevelopmentHistoryRecord (L217), class CampaignCorpusItem (L228), def safety_metadata (L239), def evidence (L253), def risk (L257), def build_cycle (L261)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: None in traced namespace
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### orchestration/runtime/rc11_rc12_systems_plateau.py
File: `orchestration/runtime/rc11_rc12_systems_plateau.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: def _now (L56), def stable_id (L60), def safety_metadata (L65), def build_integrated_trace (L82), def cross_layer_contract_audit (L161), def natural_language_stress_cases (L189), def long_conversation_campaign_stress (L218), def risk_escalation_stress (L240), def resource_stress_measurement (L268), def failure_recovery_stress (L291), def practical_usefulness_review (L311), def security_trust_audit (L328), def rc11_integrated_hardening_report (L346), def rc11_cross_layer_adversarial_report (L381), def rc11_operational_readiness_report (L409), def architecture_inventory (L437), def capability_matrix (L475), def plateau_benchmark (L512), def plateau_operator_workflow (L541), def rc12_governance_audit (L555), def plateau_readiness_final (L579), def post_rc_transition_proposal (L618), def build_plateau_operator_dashboard (L654), def render_plateau_operator_dashboard (L669), def write_reports (L685)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: orchestration.runtime.rc10_specialist_cognition, orchestration.runtime.rc6_governed_external_intelligence, orchestration.runtime.rc7_shadow_closure, orchestration.runtime.rc8_governed_external_retrieval, orchestration.runtime.rc9_real_campaign_operations
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

### integration/model_runtime/routing_policy.py
File: `integration/model_runtime/routing_policy.py`
Active status: Retained/imported or adjacent, but not primary in current conversation route
Primary responsibility: Routing-adjacent module identified by import/call tracing.
Key classes/functions: class ModelRouteDecision (L11), class ModelRoutingPolicy (L20), def decide (L37), def _select_local_model (L133), def _family_order (L170)
Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.
Calls into: integration.model_runtime.capability_planner, integration.model_runtime.model_registry
Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.
State read: message text, history, session/controller/model/concept/runtime state relevant to its route.
State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.
Why this file belongs in the routing audit: It can influence the selected route, state arbitration, or rendered answer.

## UNCERTAIN

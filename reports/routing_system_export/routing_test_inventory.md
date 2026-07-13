# Routing Test Inventory

## `orchestration/tests/runtime/test_model_abstraction.py`
File: `orchestration/tests/runtime/test_model_abstraction.py`
Routes covered: local_model
Important prompts: hi, no
Assertions: assert discovered; assert spec.family == "phi4"; assert spec.quantization == "Q4_K_M"; assert spec.provider == "local_gguf"; assert spec.capabilities == ("text",); assert spec.path == str(model_path); assert "vision" in spec.capabilities; assert spec.mmproj_path == str(projector_path)
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `orchestration/tests/runtime/test_provider_qualification.py`
File: `orchestration/tests/runtime/test_provider_qualification.py`
Routes covered: why
Important prompts: hi, why, no
Assertions: assert by_name["good"].qualified is True; assert by_name["good"].recommended_gpu_layers == 24; assert by_name["good"].recommended_context == 4096; assert by_name["good"].average_tokens_per_second == 41.0; assert by_name["good"].stable is True; assert by_name["bad"].qualified is False; assert "unsupported metadata" in "; ".join(by_name["bad"].errors); assert (tmp_path / "provider_qualification.json").exists()
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/continuous_runtime/test_continuous_runtime_controller.py`
File: `tests/continuous_runtime/test_continuous_runtime_controller.py`
Routes covered: handle_live_chat, Wikipedia, pause, suspend
Important prompts: hi, Wikipedia, pause, suspend, no
Assertions: assert "en.wikipedia.org" in url; assert controller.lifecycle_state in LIFECYCLE_STATES; assert controller.lifecycle_state == "IDLE"; assert len(controller.event_queue) == 2; assert controller.event_queue[0].event_type == "HEALTH_WARNING"; assert high.event_id in controller.processed_event_ids; assert low.event_id in controller.processed_event_ids; assert controller.lifecycle_state == "IDLE"
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/delta_1_3/test_behavioral_maturation.py`
File: `tests/delta_1_3/test_behavioral_maturation.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert payload["route"] == "local_conversation_model_lane"; assert payload["provider_calls_performed"] is False; assert payload["web_search_performed"] is False; assert payload["memory_candidate"] is None; assert "router precedence" in payloads[1]["answer"].lower(); assert "focused live-path regressions" in payloads[2]["answer"].lower(); assert "need the topic" not in answers; assert "operator approval" in answers
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/delta_1_4/test_live_wikipedia_runtime.py`
File: `tests/delta_1_4/test_live_wikipedia_runtime.py`
Routes covered: handle_live_chat, Wikipedia, local_model, suspend
Important prompts: hi, Wikipedia, suspend, local model, yes, no
Assertions: assert "en.wikipedia.org" in url; assert wikipedia_query_from_message("Wikipedia: Ada Lovelace") == "Ada Lovelace"; assert wikipedia_query_from_message("Look up Ada Lovelace on Wikipedia.") == "Ada Lovelace"; assert wikipedia_query_from_message("Tell me what Wikipedia has regarding Ada Lovelace.") == "Ada Lovelace"; assert wikipedia_query_from_message("Who is Ada Lovelace?") == ""; assert wikipedia_query_from_message("what is the first concept that comes to mind related to physics") == ""; assert wikipedia_query_from_message("Thanks, that makes sense.") == ""; assert result.title == "Ada Lovelace"
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/delta_1_5/test_developmental_cognition.py`
File: `tests/delta_1_5/test_developmental_cognition.py`
Routes covered: handle_live_chat, Wikipedia
Important prompts: hi, Wikipedia, no
Assertions: assert "en.wikipedia.org" in url; assert result.comparison.classification == "HIGHER_RESOLUTION"; assert "titration" in result.comparison.novel_terms; assert "Bronsted-Lowry acid-base theory" in result.comparison.novel_terms; assert result.promotion_candidate.approval_required is True; assert result.promotion_candidate.automatic_memory_write is False; assert result.operator_inquiry.blocks_promotion is True; assert result.safety["provider_calls_performed"] is False
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/delta_1_6/test_operational_autonomy.py`
File: `tests/delta_1_6/test_operational_autonomy.py`
Routes covered: handle_live_chat, Wikipedia, pause, suspend
Important prompts: hi, Wikipedia, pause, suspend, no
Assertions: assert "en.wikipedia.org" in url; assert model.system_identifier == "DELTA"; assert model.identity_status == "UNDEFINED"; assert model.current_conversational_identity == "undefined"; assert "live_runtime_session" in model.current_capabilities; assert "wikipedia_text_read_only_session_scope" in model.current_capabilities; assert "provider_calls" in model.disabled_capabilities; assert "commit_or_push" in model.prohibited_actions
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_arc_ii/test_arc_ii_knowledge_substrate.py`
File: `tests/runtime_arc_ii/test_arc_ii_knowledge_substrate.py`
Routes covered: why
Important prompts: hi, why, no
Assertions: assert set(KNOWLEDGE_TYPES) <= types; assert field in obj; assert obj["rollback_token"]; assert obj["audit_id"]; assert data["registries"]["entity_registry"]["objects"]; assert data["registries"]["observation_registry"]["objects"]; assert data["registries"]["evidence_registry"]["objects"]; assert data["registries"]["relationship_registry"]["objects"]
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_arc_iv/test_arc_iv_knowledge_evolution.py`
File: `tests/runtime_arc_iv/test_arc_iv_knowledge_evolution.py`
Routes covered: why
Important prompts: hi, why, no
Assertions: assert candidate.source_proposal_id == proposal.proposal_id; assert candidate.affected_entities; assert candidate.affected_concepts; assert candidate.affected_relationships; assert candidate.write_performed is False; assert graph["live_write_performed"] is False; assert len(graph["nodes"]) == 2; assert simulation["write_performed"] is False
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_analogy_engine.py`
File: `tests/runtime_rc2/test_rc2_analogy_engine.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert payload["matched"] is True; assert payload["route"] == "analogy_analysis"; assert payload["provider_calls_performed"] is False; assert payload["training_performed"] is False; assert payload["canonical_write_performed"] is False; assert is_analogy_prompt("How is photosynthesis like charging a battery?"); assert is_analogy_prompt("What works and what breaks in that analogy?"); assert is_analogy_prompt("Test this analogy: photosynthesis/respiration is like charging/discharging.")
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_cognitive_capability_benchmark.py`
File: `tests/runtime_rc2/test_rc2_cognitive_capability_benchmark.py`
Routes covered: inferred routing-adjacent
Important prompts: no
Assertions: assert len(cases) >= 100; assert {; assert review["report_voice"]["count"] == 1; assert "summary_findings" in review; assert report["case_count"] >= 100; assert report["safety_passed"] is True; assert "text_pathology_review" in report
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_contradiction_engine.py`
File: `tests/runtime_rc2/test_rc2_contradiction_engine.py`
Routes covered: route_message
Important prompts: hi, no
Assertions: assert payload["matched"] is True; assert payload["route"] == "contradiction_analysis"; assert payload["provider_calls_performed"] is False; assert payload["web_search_performed"] is False; assert payload["training_performed"] is False; assert payload["canonical_write_performed"] is False; assert is_contradiction_prompt(prompt); assert _classification(prompt) == "direct_contradiction"
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_conversation_carryover.py`
File: `tests/runtime_rc2/test_rc2_conversation_carryover.py`
Routes covered: route_message, local_model, tell me more, why
Important prompts: hi, tell me more, why, no
Assertions: assert isinstance(anchor, dict); assert anchor.get("active_concept_name"); assert followup["route"] == "developmental_concept_anchor_followup"; assert "Daytime Sky Color" in followup["answer"]; assert followup.get("local_model_offer") is None; assert followup["provider_calls_performed"] is False; assert followup["training_performed"] is False; assert followup["canonical_write_performed"] is False
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_conversational_mode_router.py`
File: `tests/runtime_rc2/test_rc2_conversational_mode_router.py`
Routes covered: route_message, local_model, tell me more, pronoun
Important prompts: hi, tell me more, local model, yes, no
Assertions: assert rc1.build_cognitive_state()["noncanonical_propositions"] == 0; assert "Conversation" in MODES; assert "Conversation" in DISPLAY_MODES; assert "Research" in DISPLAY_MODES; assert "Memory Mode" in DISPLAY_MODES; assert "Evidence Review" in MODES; assert "Investigation" in DISPLAY_MODES; assert "Developer" in DISPLAY_MODES
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_governed_semantic_graph.py`
File: `tests/runtime_rc2/test_rc2_governed_semantic_graph.py`
Routes covered: why
Important prompts: hi, why, no
Assertions: assert result["stored_this_run"] == 12; assert result["approved_edges_total"] == 12; assert result["graph_store_mutated"] is True; assert result["canonical_write_performed"] is False; assert result["automatic_graph_growth_enabled"] is False; assert result["synthesis_enabled_by_default"] is False; assert len(rows) == 12; assert all(row["approval_status"] == "approved_noncanonical" for row in rows)
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_graph_assisted_reasoning.py`
File: `tests/runtime_rc2/test_rc2_graph_assisted_reasoning.py`
Routes covered: route_message, why
Important prompts: hi, why, no
Assertions: assert result["route"] == "read_only_graph_assisted_reasoning_trial"; assert result["read_only"] is True; assert result["trial_only"] is True; assert result["graph_write_performed"] is False; assert result["memory_write_performed"] is False; assert result["provider_calls_performed"] is False; assert result["training_performed"] is False; assert result["canonical_write_performed"] is False
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_level2_runtime_integration.py`
File: `tests/runtime_rc2/test_rc2_level2_runtime_integration.py`
Routes covered: local_model
Important prompts: no
Assertions: assert report["cycles_completed"] >= 40; assert report["actual_local_model_calls"] >= 20; assert report["scores"]["safety_score"] == 1.0; assert report["scores"]["planning_model_calls"] >= 5; assert report["warmed_model"]["loaded"] is True; assert report["planning_model"]["loaded"] is True; assert report["recommendation"] in {"READY_FOR_LEVEL2_RC2_MANUAL_OPERATOR_REVIEW", "LEVEL2_REPAIR_REQUIRED"}; assert (tmp_path / "reports" / "RC2_LEVEL2_RUNTIME_INTEGRATION.json").exists()
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: Yes
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_natural_conversation_renderer.py`
File: `tests/runtime_rc2/test_rc2_natural_conversation_renderer.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert marker not in answer; assert payload["route"] == "developmental_concept_memory"; assert "blood pressure" in payload["answer"].lower(); assert payload["route"] == "working_reasoning_set"; assert "blood pressure" in payload["answer"].lower(); assert "allerg" in payload["answer"].lower(); assert payload["route"] == "contradiction_analysis"; assert "both be true" in payload["answer"].lower() or "can both" in payload["answer"].lower()
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_render_correction.py`
File: `tests/runtime_rc2/test_rc2_render_correction.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert payload["route"] == "render_correction"; assert "Blood pressure" in payload["answer"]; assert payload["memory_candidate"] is None; assert payload["provider_calls_performed"] is False; assert payload["render_correction"]["operation"] == "RENDER_CORRECTION"; assert payload["render_correction"]["scope"] == "presentation_only"; assert payload["route"] == "render_correction"; assert payload["answer"].startswith("1. What I inspected")
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_retrieval_ranking.py`
File: `tests/runtime_rc2/test_rc2_retrieval_ranking.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert result["matched"] is True; assert result["matches"][0]["concept_name"] == "Static Electricity"; assert result["provider_calls_performed"] is False if "provider_calls_performed" in result else True; assert payload["route"] == "developmental_multi_concept_retrieval"; assert payload["multi_concept_retrieval"]["synthesis_readiness"] is False; assert "Synthesis is not enabled yet" in payload["answer"]; assert "Photosynthesis" in names; assert "Cellular Respiration" in names
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_routing_precedence.py`
File: `tests/runtime_rc2/test_rc2_routing_precedence.py`
Routes covered: route_message, local_model, pronoun
Important prompts: hi, no
Assertions: assert payload["route"] == "contradiction_analysis"; assert arbitration["selected_group"] == "contradiction_analysis"; assert any(item["route"] == "working_memory_reference_resolution" for item in arbitration["candidate_routes"]); assert payload["route"] == "analogy_analysis"; assert arbitration["selected_group"] == "analogy_analysis"; assert any(item["route"] == "working_reasoning_set" for item in arbitration["candidate_routes"]); assert payload["route"] in {"working_reasoning_set", "developmental_multi_concept_retrieval", "developmental_concept_memory"}; assert payload["route"] != "session_memory"
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_routing_stabilization.py`
File: `tests/runtime_rc2/test_rc2_routing_stabilization.py`
Routes covered: route_message, greeting, tell me more
Important prompts: hi, tell me more, no
Assertions: assert first["route"] == "developmental_concept_memory"; assert physics["route"] == "local_conversation_model_lane"; assert "motion" in str(physics["answer"]).lower(); assert "advanced operator mode evidence standard" not in str(physics["answer"]).lower(); assert physics["routing_observability"]["explicit_new_topic_request"] is True; assert physics["routing_observability"]["memory_retrieval_bypassed"] is True; assert followup["route"] == "session_memory"; assert "physics" in str(followup["answer"]).lower()
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_working_memory_episode.py`
File: `tests/runtime_rc2/test_rc2_working_memory_episode.py`
Routes covered: route_message, local_model, why
Important prompts: hi, why, no
Assertions: assert payload["route"] == "session_memory"; assert "blood pressure" in payload["answer"].lower(); assert not (payload.get("local_model_offer") or {}).get("offered"); assert not payload["provider_calls_performed"]; assert payload["route"] == "session_memory"; assert "blood pressure" in answer; assert "allerg" in answer; assert payload["route"] == "session_memory"
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc2/test_rc2_working_reasoning_set.py`
File: `tests/runtime_rc2/test_rc2_working_reasoning_set.py`
Routes covered: route_message, local_model
Important prompts: hi, no
Assertions: assert "allergies" in seeds; assert "blood pressure" in seeds; assert should_use_wrs("What common reasoning principles connect allergies and blood pressure?"); assert result["matched"] is True; assert result["retrieved_concept_count"] >= 2; assert result["retrieved_proposition_count"] >= 2; assert result["safety"]["provider_calls_performed"] is False; assert result["safety"]["training_performed"] is False
Uses real runtime or fixture: real runtime API
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc3/test_rc3_e_to_k_foundations.py`
File: `tests/runtime_rc3/test_rc3_e_to_k_foundations.py`
Routes covered: pause
Important prompts: hi, pause, no
Assertions: assert [report["stage"] for report in reports] == [f"RC3-{stage}" for stage in "EFGHIJK"]; assert all(report["overall"] == 1.0 for report in reports[:5]); assert reports[5]["scores"]["real_operator_evidence"] == 0.0; assert reports[6]["scores"]["real_operator_evidence"] == 0.0; assert all(report["safety_metadata_completeness"] == 1.0 for report in reports); assert all(report["delta_75_interaction_performed"] is False for report in reports); assert validation.result == "rejected"; assert "unrestricted_permission_claim" in validation.rejection_reasons
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_rc9/test_rc9_real_campaign_operations.py`
File: `tests/runtime_rc9/test_rc9_real_campaign_operations.py`
Routes covered: pause
Important prompts: hi, pause, no
Assertions: assert {"started", "paused", "resumed", "deferred", "cancelled", "abandoned", "superseded", "completed"}.issubset(SESSION_STATES); assert session.resume_token is not None; assert session.interruption is not None; assert session.state.status == "resumed"; assert expected.issubset(trials); assert trials["cancelled_campaign"].continuation.decision == "STOP_OPERATOR_CANCELLED"; assert "operator_workload_excessive" in trials["operator_workload_overload"].continuation.reasons; assert session.evidence[0].evidence_class == "PROVIDER_ADVISORY_EVIDENCE"
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

## `tests/runtime_v31/test_v31_learning_readiness.py`
File: `tests/runtime_v31/test_v31_learning_readiness.py`
Routes covered: why
Important prompts: hi, why, no
Assertions: assert opportunities; assert opportunities[0].requires_review is True; assert opportunities[0].eligible_for_learning is False; assert proposal.review_status == "admin_approved"; assert proposal.eligible_for_gated_integration is True; assert proposal.integrated is False; assert approval.valid is True; assert event.allowed is False
Uses real runtime or fixture: fixture or indirect
Uses fake Wikipedia: No/unclear
Uses real local model: No/fixture/unclear
Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.

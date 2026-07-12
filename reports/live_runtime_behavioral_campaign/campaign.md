# Live Runtime Behavioral Campaign

- Campaign id: `live-runtime-behavioral-campaign-fe58006a63aad849`
- Generated: `2026-07-12T05:23:54+00:00`
- Passed: `True`
- Scenarios: `373`
- Turns: `1500`
- Families: `20`
- Pathologies: `0`
- Governance violations: `0`
- Duration seconds: `194.9828`

## Routes
`contradiction_analysis`, `developmental_concept_memory`, `live_context_declaration`, `live_memory_governance`, `live_operational_self_model`, `live_pending_inquiries`, `live_promotion_approval`, `live_promotion_approval_ambiguous`, `live_promotion_rejection`, `live_promotion_rejection_ambiguous`, `live_runtime_control_pause`, `live_runtime_control_resume`, `live_runtime_control_suspend`, `live_runtime_paused`, `live_runtime_suspended`, `live_wikipedia_retrieval_failed`, `live_wikipedia_text_retrieval`, `local_conversation_model_lane`, `local_model_consent_required`, `session_memory`, `social_conversation`

## Lifecycle States
`ACTIVE_OBJECTIVE`, `ASSESSING`, `BOOT`, `EVENT_PENDING`, `IDLE`, `INITIALIZING`, `JOURNALING`, `LOADING_STATE`, `MODEL_AVAILABLE`, `MODEL_UNAVAILABLE`, `OBJECTIVE_BLOCKED`, `OBJECTIVE_COMPLETED`, `OBSERVING`, `PAUSED`, `PROMOTION_PENDING`, `PROPOSAL_PREPARING`, `RECOVERING`, `RESTARTED`, `SUSPENDED`, `WAITING_FOR_OPERATOR`, `WIKIPEDIA_AVAILABLE`, `WIKIPEDIA_RESULT_PRESENT`

## Wikipedia
- Fake network calls: `298`
- Fake cache hits: `108`
- Fake failures exercised: `12`
- Policy: bulk campaign uses deterministic fake Wikipedia transport; no real Wikipedia API calls are required

## Readiness
- Recommendation: `LIVE_RUNTIME_BEHAVIORAL_CLOSURE_READY_FOR_OPERATOR_PILOT`
- Approval-to-action demonstrated: `True`

## Real API Smoke
- Passed: `True`
- Real network request upper bound: `1`
- Cache entries: `1`

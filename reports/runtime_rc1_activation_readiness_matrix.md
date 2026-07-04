# RC1 Activation Readiness Matrix

- phase: RC1 Activation Readiness Matrix
- runtime_maturity_estimate: 97%
- final_recommendation: `PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES`

## Capability Matrix

| Capability | Status | First State | Order | Key Gates |
| --- | --- | --- | --- | --- |
| live document adapter | disabled; adversarial validation flagged live_document_adapter_disabled_fixture_only | fixture_only | 1 | manual RC1 validation; fixture parser parity; no persistence by default |
| real corpus ingestion | disabled; no live ingestion path is authorized | admin_gated | 6 | admin approval; input folder allowlist; dry-run manifest; size cap |
| semantic record persistence | disabled outside simulated E2E harness | dry_run | 2 | fixture-only semantic output folder; schema validation; noncanonical namespace |
| replay batch persistence | disabled; replay is scaffolded and simulated | dry_run | 3 | semantic record dry-run complete; batch manifest; no scheduler |
| consolidation candidate persistence | disabled; candidates are report-only/simulated | dry_run | 4 | replay batch dry-run complete; review state starts pending; no integration |
| approval-gated substrate write | disabled; previous trials require exact structured approval and remain local | owner_override_only | 8 | exact approval phrase; overwatch allow or owner override; rollback token |
| read-only substrate retrieval | available as deterministic RC1 query adapter over fixtures | read_only | 5 | read-only adapter; no recall mutation; grounding required |
| grounded answer synthesis | available locally for deterministic repo/self-description and fixture answers | read_only | 5 | evidence packet; uncertainty note; no provider fallback unless gated |
| provider-assisted evidence | disabled; provider authority and calls remain off | overwatch_gated | 10 | explicit admin gate; cost limit; evidence-only status; overwatch review |
| specialist deliberation | dormant/advisory; specialists remain non-authoritative | overwatch_gated | 11 | specialist outputs advisory only; disagreement capture; no routing authority |
| graph repair | report-only; adversarial validation flagged graph_repair_is_report_only | dry_run | 9 | repair preview only; human review; rollback plan before mutation |
| executive planning | non-executing; adversarial validation bounded this pathology | read_only | 7 | planning-only flag; no action binding; review before execution |
| rollback execution | disabled; rollback references exist but do not execute | admin_gated | 9 | trial write exists; exact rollback approval; pre/post audit |
| evaluation/regression loop | manual test/report loop active; schedulers disabled | read_only | 0 | manual invocation; fixed fixtures; no scheduler |
| sleep/replay consolidation | design/scaffold only; no scheduled consolidation | dry_run | 3 | manual batch; review-only consolidation; no scheduler; no canonical write |

## Safety

- autonomous_browsing_performed: False
- autonomous_execution_performed: False
- background_worker_started: False
- fine_tuning_performed: False
- hidden_write_performed: False
- hyb1: dormant_env_gated
- knowledge_mutation_performed: False
- memory_mutation_performed: False
- model_b_default: unchanged
- model_update_performed: False
- provider_authority_granted: False
- provider_call_performed: False
- scheduler_started: False
- training_performed: False

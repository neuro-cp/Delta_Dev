# RC2 Substrate Reconciliation

Created: 2026-07-10T02:18:23+00:00
Recommendation: USE_ACTIVE_RUNTIME_CONCEPTS_FOR_UI_AND_WRS_DEFER_INSTILLATION_UNTIL_COUNTERS_STAY_RECONCILED

## Authoritative Runtime Counters

- Active runtime concepts: 8979
- Active graph edges: 5505
- Substrate replay events: 14484
- Legacy JSONL concepts: 9963
- Legacy JSONL graph edges: 10001

## Counter Reconciliation

| Counter | Value | Source | Meaning | Runtime authoritative |
| --- | ---: | --- | --- | --- |
| active_runtime_concepts | 8979 | SQLite concepts table | Authoritative active concept rows available to runtime retrieval/WRS. | True |
| active_graph_edges | 5505 | SQLite graph_edges table | Approved noncanonical graph edges available to graph-assisted retrieval. | True |
| substrate_replay_events | 14484 | SQLite substrate_replay_events table | Replay-review/audit events derived from indexed concepts and graph edges; not a concept total. | False |
| concept_replay_events | 8979 | SQLite substrate_replay_events where target_type='concept' | Replay-review events corresponding to active concept rows. | False |
| graph_edge_replay_events | 5505 | SQLite substrate_replay_events where target_type='graph_edge' | Replay-review events corresponding to active graph edge rows. | False |
| legacy_jsonl_concepts | 9963 | legacy JSONL approved concept stores | Historical/audit source records, not the primary runtime count when SQLite is available. | False |
| legacy_jsonl_graph_edges | 10001 | legacy JSONL graph edge store | Historical/audit source graph edges, not the primary runtime edge count when SQLite is available. | False |
| developmental_memory_records | 10000 | developmental memory state | Legacy local developmental memory count. This is diagnostic, not the canonical runtime substrate count. | False |
| migration_audit_events | 22 | SQLite migration_audit table | Backend migration/repair/cleanup events. This is operational history, not a concept count. | False |

## Consistency

- active_concepts_match_concept_replay_events: True
- active_edges_match_edge_replay_events: True
- runtime_uses_single_authoritative_concept_count: True
- ui_header_should_display: active_runtime_concepts
- database_should_display: active_runtime_concepts
- wrs_should_retrieve_from: storage_adapter_active_runtime_substrate

## Safety

- training_performed: False
- fine_tuning_performed: False
- weight_update_performed: False
- canonical_write_performed: False
- noncanonical_memory_write_performed: False
- graph_write_performed: False
- provider_calls_performed: False
- web_search_performed: False
- autonomous_action_performed: False
- scheduler_started: False
- hyb1_promoted: False
- model_b_replaced: False
- delta_75_push_performed: False

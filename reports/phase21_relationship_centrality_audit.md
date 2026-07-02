# Phase 21 Relationship Centrality Audit

Read-only aggregate diagnostic. No experiment stores or canonical knowledge were modified.

| Run | Concepts Sampled | Direct Semantic Edges | Projected Memory Edges | Avg Direct Edges | Avg Projected Edges | Hypothesis |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| planning_20 | 50 | 0 | 35 | 0.0 | 0.7 | relationships_exist_at_memory_layer_but_are_not_projected_to_semantic_layer |
| planning_30 | 50 | 0 | 40 | 0.0 | 0.8 | relationships_exist_at_memory_layer_but_are_not_projected_to_semantic_layer |
| planning_40 | 50 | 0 | 39 | 0.0 | 0.78 | relationships_exist_at_memory_layer_but_are_not_projected_to_semantic_layer |

## Aggregate

- Concepts sampled: `150`
- Concepts with direct semantic edges: `0`
- Concepts with projected memory edges: `114`
- Direct semantic ratio: `0.0`
- Projected memory ratio: `0.76`
- Conclusion: `governance_centrality_is_blind_to_existing_memory_relationships`

## Diagnosis Counts

- `memory_graph_not_projected`: `114`
- `no_relationship_evidence`: `36`

## Interpretation

Relationship structure exists in the memory layer for most sampled concepts, but no sampled concepts have direct semantic relationship edges. Promotion governance is therefore measuring concept-level centrality over a graph that does not yet expose the memory evidence graph.

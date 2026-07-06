# TP8 Canonical Promotion Policy

- phase: `TP8 Canonical Promotion Policy`
- canonical_memory_enabled: `False`
- minimum_provenance_requirements: `['source_references', 'source_checksum', 'audit_id', 'operator_id']`
- minimum_operator_approval_requirements: `['two independent reviewers', 'explicit promotion approval', 'minority objection preservation']`
- contradiction_handling_requirements: `['unresolved contradictions block', 'contradictions preserved', 'no deletion of counterevidence']`
- uncertainty_thresholds: `{'max_unresolved_uncertainty': 0, 'minimum_confidence': 0.85}`
- reviewer_agreement_requirements: `{'minimum_agreement': 1.0, 'minority_objection_blocks': True}`
- rollback_requirements: `['pre_promotion_state', 'rollback_target', 'reversible_transformation_path']`
- replay_requirements: `['read_only_replay_before', 'read_only_replay_after_simulation']`
- audit_requirements: `['approval_chain', 'promotion_rationale', 'timestamp', 'source_lineage']`
- rejection_requirements: `['reason_code', 'evidence_gap', 'reviewer_disagreement', 'operator_visible']`
- abstention_requirements: `['block_if_uncertain', 'block_if_source_ambiguous', 'block_if_stale']`

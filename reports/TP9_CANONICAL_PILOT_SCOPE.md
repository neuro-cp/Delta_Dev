# TP9 Canonical Pilot Scope

- phase: `TP9 Canonical Pilot Scope`
- pilot_enabled: `False`
- scope: `single-domain, operator-reviewed, canonical-write design only`
- allowed_knowledge: `['low-risk project self-description claims', 'fully provenanced operational-status claims']`
- excluded_knowledge: `['personal memory', 'medical/legal/financial claims', 'action instructions', 'provider-derived authority', 'unresolved contradictions']`
- activation_requirement: `separate future explicit approval required`
- approval_model: `single candidate, exact approval, multi-reviewer policy satisfied`
- target_store: `disabled canonical pilot store design`
- rollback_requirement: `per-record rollback token plus pre-write snapshot`
- audit_requirement: `source proposal, reviewer chain, policy gate results, rollback handle, timestamp`

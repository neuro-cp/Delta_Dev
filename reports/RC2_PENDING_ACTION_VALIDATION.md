# Rc2 Pending Action Validation

- summary: `Follow-up elaboration offers create typed pending actions; bare yes without an active action remains social only.`
- pending_action_score: `1.0`
- followup_deepening_score: `1.0`
- stateful_scenarios: `[{'scenario': 'followup_creates_local_model_deepening_action', 'route': 'local_model_consent_required', 'pending_action': {'action_type': 'local_model_deepening', 'pending_action_created': True, 'followup_instruction': 'tell me more', 'expires_after_turns': 1}, 'passed': True}, {'scenario': 'bare_yes_without_pending_action_is_social_only', 'route': 'social_conversation', 'passed': True}, {'scenario': 'planning_uses_planning_lane', 'selected_lane': 'planning', 'selected_model': 'mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m', 'passed': True}, {'scenario': 'local_model_execution_probe', 'executed': True, 'available': True, 'selected_lane': 'planning', 'selected_model': 'mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m', 'reason': None, 'answer_preview': '1. Verify the invoice details against the purchase order. 2. Check for any discrepancies or errors in the invoice. 3. Approve or reject the invoice based on the findings.', 'passed': True}]`
- safe: `True`
- training_performed: `False`
- canonical_write_performed: `False`
- provider_calls_performed: `False`

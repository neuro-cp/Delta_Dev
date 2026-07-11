# RC6_TRANSPORT_SCAFFOLD_BENCHMARK

- Generated: 2026-07-11T02:43:52+00:00
- Passed: True
- Score: 1.0
- Recommendation: RC6_TRANSPORT_SCAFFOLD_READY_DISABLED_BY_DEFAULT

## Safety
- provider_call_performed: False
- provider_enabled_default: False
- autonomous_action_performed: False
- memory_write_performed: False
- canonical_write_performed: False
- rc4_authorization_bypassed: False
- external_authority_granted: False
- delta75_interaction_performed: False
- hidden_persistence_performed: False
- training_performed: False

## Summary
```json
{
  "checks": {
    "disabled_adapter_no_call": true,
    "enabled_mock_succeeds_only_with_gates": true,
    "gateway_remains_advisory": true,
    "malformed_response_fails_closed": true,
    "operator_approval_required": true
  },
  "disabled_transport": {
    "failure_reason": "gateway_rejected_before_transport",
    "metrics": {
      "attempted": false,
      "attempts": 0,
      "estimated_cost_usd": 0.0,
      "failed_closed": true,
      "latency_ms": 0.0,
      "prompt_tokens": 0,
      "response_tokens": 0,
      "succeeded": false
    },
    "provider_call_performed": false,
    "raw_response": null,
    "result_id": "rc6-92df90a36323ae7d8738",
    "status": "provider_disabled"
  },
  "enabled_transport": {
    "failure_reason": "",
    "metrics": {
      "attempted": true,
      "attempts": 1,
      "estimated_cost_usd": 0.0,
      "failed_closed": false,
      "latency_ms": 0.0,
      "prompt_tokens": 0,
      "response_tokens": 0,
      "succeeded": true
    },
    "provider_call_performed": true,
    "raw_response": {
      "alternative_causes": [
        "fixture_only"
      ],
      "assumptions": [
        "operator supplied a mock transport"
      ],
      "confidence": 0.5,
      "diagnosis": "Mock transport response; no real provider was contacted.",
      "missing_info": [
        "real provider response"
      ],
      "remedies": [
        "Use this only to test schema handling."
      ],
      "risks": [
        "mistaking mock evidence for live provider evidence"
      ],
      "rollback": [
        "disable mock transport"
      ],
      "tests": [
        "validate transport result status"
      ]
    },
    "result_id": "rc6-ab3321bf9b11dfaf4daa",
    "status": "succeeded"
  },
  "malformed_transport": {
    "failure_reason": "advisory_response_validation_failed",
    "metrics": {
      "attempted": true,
      "attempts": 1,
      "estimated_cost_usd": 0.0,
      "failed_closed": false,
      "latency_ms": 0.0,
      "prompt_tokens": 0,
      "response_tokens": 0,
      "succeeded": true
    },
    "provider_call_performed": true,
    "raw_response": {
      "diagnosis": "missing required fields"
    },
    "result_id": "rc6-f9bfb3dc2d176994d03c",
    "status": "schema_failed"
  },
  "passed": true,
  "recommendation": "RC6_TRANSPORT_SCAFFOLD_READY_DISABLED_BY_DEFAULT",
  "report": "RC6_TRANSPORT_SCAFFOLD_BENCHMARK",
  "score": 1.0
}
```

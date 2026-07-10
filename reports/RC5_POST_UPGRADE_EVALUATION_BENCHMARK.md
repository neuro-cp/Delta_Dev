# RC5 POST UPGRADE EVALUATION BENCHMARK

Report: RC5_POST_UPGRADE_EVALUATION_BENCHMARK

Passed: True

Recommendation: n/a

Freeze status: n/a

```json
{
  "cases": {
    "failed": {
      "baseline": {
        "evaluation_id": "rc5-baseline-45f5cf3a8dbac57c",
        "evidence": "fixture_baseline",
        "meta": {
          "authority": "evidence",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "baseline evaluation",
          "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
          "rc3_relationship": "uses_goals_plans_governance_as_evidence",
          "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
          "rollback_or_revocation": "discard_artifact_or_operator_revoke",
          "safety": {
            "automatic_consultation_performed": false,
            "canonical_write_performed": false,
            "developmental_memory_auto_write": false,
            "gpt_api_calls_performed": false,
            "protected_repository_interaction": false,
            "provider_calls_performed": false,
            "purpose_mutation_performed": false,
            "rc4_authorization_bypassed": false,
            "training_performed": false,
            "upgrade_self_approved": false
          },
          "serialization": "json",
          "token_budget": {
            "default_packet_tokens": 1000,
            "max_packet_tokens": 2000
          },
          "validation": "deterministic"
        },
        "metric_name": "retrieval_precision",
        "value": 0.62
      },
      "causal_confidence": "low",
      "comparison_id": "rc5-comparison-a5de72e77c102096",
      "delta": -0.02,
      "disposition": "REJECT_OR_REVISE",
      "meta": {
        "authority": "evaluation",
        "cost_metadata": {
          "estimated_cost_usd": 0.0
        },
        "lifecycle": "draft",
        "operator_visibility": "reports_and_ui",
        "owner": "operator",
        "persistence_policy": "ephemeral_or_report_only",
        "provenance": "rc5_deterministic_developmental_cognition",
        "purpose": "comparative evaluation",
        "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
        "rc3_relationship": "uses_goals_plans_governance_as_evidence",
        "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
        "rollback_or_revocation": "discard_artifact_or_operator_revoke",
        "safety": {
          "automatic_consultation_performed": false,
          "canonical_write_performed": false,
          "developmental_memory_auto_write": false,
          "gpt_api_calls_performed": false,
          "protected_repository_interaction": false,
          "provider_calls_performed": false,
          "purpose_mutation_performed": false,
          "rc4_authorization_bypassed": false,
          "training_performed": false,
          "upgrade_self_approved": false
        },
        "serialization": "json",
        "token_budget": {
          "default_packet_tokens": 1000,
          "max_packet_tokens": 2000
        },
        "validation": "deterministic"
      },
      "post_upgrade": {
        "evaluation_id": "rc5-post-7e56ec9e70a76fd2",
        "evidence": "fixture_post_upgrade",
        "meta": {
          "authority": "evidence",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "post-upgrade evaluation",
          "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
          "rc3_relationship": "uses_goals_plans_governance_as_evidence",
          "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
          "rollback_or_revocation": "discard_artifact_or_operator_revoke",
          "safety": {
            "automatic_consultation_performed": false,
            "canonical_write_performed": false,
            "developmental_memory_auto_write": false,
            "gpt_api_calls_performed": false,
            "protected_repository_interaction": false,
            "provider_calls_performed": false,
            "purpose_mutation_performed": false,
            "rc4_authorization_bypassed": false,
            "training_performed": false,
            "upgrade_self_approved": false
          },
          "serialization": "json",
          "token_budget": {
            "default_packet_tokens": 1000,
            "max_packet_tokens": 2000
          },
          "validation": "deterministic"
        },
        "metric_name": "retrieval_precision",
        "value": 0.6
      },
      "regression_findings": []
    },
    "improve": {
      "baseline": {
        "evaluation_id": "rc5-baseline-45f5cf3a8dbac57c",
        "evidence": "fixture_baseline",
        "meta": {
          "authority": "evidence",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "baseline evaluation",
          "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
          "rc3_relationship": "uses_goals_plans_governance_as_evidence",
          "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
          "rollback_or_revocation": "discard_artifact_or_operator_revoke",
          "safety": {
            "automatic_consultation_performed": false,
            "canonical_write_performed": false,
            "developmental_memory_auto_write": false,
            "gpt_api_calls_performed": false,
            "protected_repository_interaction": false,
            "provider_calls_performed": false,
            "purpose_mutation_performed": false,
            "rc4_authorization_bypassed": false,
            "training_performed": false,
            "upgrade_self_approved": false
          },
          "serialization": "json",
          "token_budget": {
            "default_packet_tokens": 1000,
            "max_packet_tokens": 2000
          },
          "validation": "deterministic"
        },
        "metric_name": "retrieval_precision",
        "value": 0.62
      },
      "causal_confidence": "moderate",
      "comparison_id": "rc5-comparison-5509357057cb6c6d",
      "delta": 0.19,
      "disposition": "RETAIN_AFTER_REVIEW",
      "meta": {
        "authority": "evaluation",
        "cost_metadata": {
          "estimated_cost_usd": 0.0
        },
        "lifecycle": "draft",
        "operator_visibility": "reports_and_ui",
        "owner": "operator",
        "persistence_policy": "ephemeral_or_report_only",
        "provenance": "rc5_deterministic_developmental_cognition",
        "purpose": "comparative evaluation",
        "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
        "rc3_relationship": "uses_goals_plans_governance_as_evidence",
        "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
        "rollback_or_revocation": "discard_artifact_or_operator_revoke",
        "safety": {
          "automatic_consultation_performed": false,
          "canonical_write_performed": false,
          "developmental_memory_auto_write": false,
          "gpt_api_calls_performed": false,
          "protected_repository_interaction": false,
          "provider_calls_performed": false,
          "purpose_mutation_performed": false,
          "rc4_authorization_bypassed": false,
          "training_performed": false,
          "upgrade_self_approved": false
        },
        "serialization": "json",
        "token_budget": {
          "default_packet_tokens": 1000,
          "max_packet_tokens": 2000
        },
        "validation": "deterministic"
      },
      "post_upgrade": {
        "evaluation_id": "rc5-post-e1cd70dd3985e1af",
        "evidence": "fixture_post_upgrade",
        "meta": {
          "authority": "evidence",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "post-upgrade evaluation",
          "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
          "rc3_relationship": "uses_goals_plans_governance_as_evidence",
          "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
          "rollback_or_revocation": "discard_artifact_or_operator_revoke",
          "safety": {
            "automatic_consultation_performed": false,
            "canonical_write_performed": false,
            "developmental_memory_auto_write": false,
            "gpt_api_calls_performed": false,
            "protected_repository_interaction": false,
            "provider_calls_performed": false,
            "purpose_mutation_performed": false,
            "rc4_authorization_bypassed": false,
            "training_performed": false,
            "upgrade_self_approved": false
          },
          "serialization": "json",
          "token_budget": {
            "default_packet_tokens": 1000,
            "max_packet_tokens": 2000
          },
          "validation": "deterministic"
        },
        "metric_name": "retrieval_precision",
        "value": 0.81
      },
      "regression_findings": []
    },
    "regress": {
      "baseline": {
        "evaluation_id": "rc5-baseline-45f5cf3a8dbac57c",
        "evidence": "fixture_baseline",
        "meta": {
          "authority": "evidence",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "baseline evaluation",
          "rc2_relationship": "evaluates_conversation_and_cognition_without_mutating_rc2",
          "rc3_relationship": "uses_goals_plans_governance_as_evidence",
          "rc4_relationship": "hands_off_upgrade_proposals_to_governed_action_runtime",
          "rollback_or_revocation": "discard_artifact_or_operator_revoke",
          "safety": {
            "automatic_consultation_performed": false,
            "canonical_write_performed": false,
            "developmental_memory_auto_write": false,
            "gpt_api_calls_performed": false,
            "protected_repository_interaction": false,
            "provider_calls_performed": false,
            "purpose_mutation_performed": false,
            "rc4_authorization_bypassed": false,
            "training_performed": false,
            "upgrade_self_approved": false
          },
          "serialization": "json",
          "token_budget": {
            "default_packet_tokens": 1000,
            "max_packet_tokens": 2000
          },
          "validation": "deterministic"
        },
        "metric_name": "retrieval_precision",
        "value": 0.62
      },
      "causal_confidence": "low",
      "comparison_id": "rc5-comparison-39f1dcb3340acb2b",
      "delta": 0.2,
      "disposition": "REJECT_OR_REVISE",
      "meta": {
        "authority": "evaluation",
        "cost_metadata": {
          "estimated_cost_usd": 0.0
        },
        "lifecycle": "draft",
        "operator_visibility"
```

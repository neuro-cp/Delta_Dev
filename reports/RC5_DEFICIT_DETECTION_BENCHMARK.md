# RC5 DEFICIT DETECTION BENCHMARK

Report: RC5_DEFICIT_DETECTION_BENCHMARK

Passed: True

Recommendation: n/a

Freeze status: n/a

```json
{
  "cases": {
    "isolated": {
      "affected_capability": "one minor anomaly should not trigger upgrade",
      "candidate_causes": [
        {
          "candidate_id": "rc5-cause-300c8e31047d8ea7",
          "cause": "isolated low-severity anomaly",
          "confidence": 0.2,
          "counterevidence": [],
          "meta": {
            "authority": "hypothesis",
            "cost_metadata": {
              "estimated_cost_usd": 0.0
            },
            "lifecycle": "draft",
            "operator_visibility": "reports_and_ui",
            "owner": "operator",
            "persistence_policy": "ephemeral_or_report_only",
            "provenance": "rc5_deterministic_developmental_cognition",
            "purpose": "root cause candidate",
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
          "supporting_evidence": [
            "rc5-evidence-7a37d30437ec75a4"
          ]
        },
        {
          "candidate_id": "rc5-cause-74f3d6b372165100",
          "cause": "fixture_or_input_issue",
          "confidence": 0.8,
          "counterevidence": [
            "rc5-evidence-7a37d30437ec75a4"
          ],
          "meta": {
            "authority": "hypothesis",
            "cost_metadata": {
              "estimated_cost_usd": 0.0
            },
            "lifecycle": "draft",
            "operator_visibility": "reports_and_ui",
            "owner": "operator",
            "persistence_policy": "ephemeral_or_report_only",
            "provenance": "rc5_deterministic_developmental_cognition",
            "purpose": "root cause candidate",
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
          "supporting_evidence": []
        }
      ],
      "confidence": 0.2,
      "deficit_class": "NO_CONFIRMED_DEFICIT",
      "discriminating_test": {
        "cheapest_next_action": "collect more evidence before upgrade",
        "description": "collect more evidence before upgrade",
        "distinguishes_between": [
          "isolated low-severity anomaly",
          "fixture_or_input_issue"
        ],
        "meta": {
          "authority": "proposal_only",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_policy": "ephemeral_or_report_only",
          "provenance": "rc5_deterministic_developmental_cognition",
          "purpose": "discriminating test",
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
        "success_signal": "metric separates candidate causes",
        "test_id": "rc5-disc-test-2b3a09d054b5f6e8"
      },
      "expected_capability": "one minor anomaly should not trigger upgrade",
      "hypothesis_id": "rc5-deficit-444029dc3092a9ab",
      "meta": {
        "authority": "hypothesis",
        "cost_metadata": {
          "estimated_cost_usd": 0.0
        },
        "lifecycle": "draft",
        "operator_visibility": "reports_and_ui",
        "owner": "operator",
        "persistence_policy": "ephemeral_or_report_only",
        "provenance": "rc5_deterministic_developmental_cognition",
        "purpose": "deficit hypothesis",
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
      "missing_evidence": [
        "recurrence",
        "severity"
      ],
      "observed_failure": "single low-severity anomaly",
      "recurrence": 1,
      "severity": "low"
    },
    "metric": {
      "affected_capability": "metric should evaluate protected criterion",
      "candidate_causes": [
        {
          "candidate_id": "rc5-cause-555209077b399d30",
          "cause": "missing evaluation metric",
          "confidence": 0.82,
          "counterevidence": [],
          "meta": {
            "authority": "hypothesis",
            "cost_metadata": {
              "estimated_cost_usd": 0.0
            },
            "lifecycle": "draft",
            "operator_visibility": "reports_and_ui",
            "owner": "operator",
            "persistence_policy": "ephemeral_or_report_only",
            "provenance": "rc5_deterministic_developmental_cognition",
            "purpose": "root cause candidate",
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
          "supporting_evidence": [
            "rc5-evidence-58dbc1530bd0ec41"
          ]
        },
        {
          "candidate_id": "rc5-cause-74f3d6b372165100",
          "cause": "fixture_or_input_issue",
          "confidence": 0.18,
          "counterevidence": [
            "rc5-evidence-58dbc1530bd0ec41"
          ],
          "meta": {
            "authority": "hypothesis",
            "cost_metadata": {
              "estimated_cost_usd": 0.0
            },
            "lifecycle": "draft",
            "operator_visibility": "reports_and_ui",
            "owner": "operator",
            "persistence_policy": "ephemeral_or_report_only",
            "provenance": "rc5_deterministic_developmental_cognition",
            "purpose": "root cause candidate",
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
          "supporting_evidence": []
        }
      ],
      "confidence": 0.82,
      "deficit_class": "PERFORMANCE_METRIC_DEFICIT",
      "discriminating_test": {
        "cheapest_next_action": "define and run a protected-purpose metric before proposing capability change",
        "description": "define and run a protected-purpose metric before proposing capability change",
        "distinguishes_between": [
          "missing evaluation metric",
          "fixture_or_input_issue"
        ],
        "meta": {
          "authority": "proposal_only",
          "cost_metadata": {
            "estimated_cost_usd": 0.0
          },
          "lifecycle": "draft",
          "operator_visibility": "reports_and_ui",
          "owner": "operator",
          "persistence_poli
```

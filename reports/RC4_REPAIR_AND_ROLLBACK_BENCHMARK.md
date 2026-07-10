# RC4 REPAIR AND ROLLBACK BENCHMARK

Report: RC4_REPAIR_AND_ROLLBACK_BENCHMARK
Passed: True
Recommendation: n/a
Freeze status: n/a

```json
{
  "application": {
    "evidence": [
      "disposable_fixture",
      "patch_hash_checked",
      "rollback_ticket_created"
    ],
    "live_repository_mutated": false,
    "meta": {
      "audit_requirements": [
        "provenance",
        "safety_metadata",
        "operator_visibility"
      ],
      "authority": "fixture_result",
      "lifecycle": "draft",
      "operator_visibility": "developer_overlay_and_reports",
      "owner": "operator",
      "persistence_status": "ephemeral_or_report_only",
      "provenance": "rc4_deterministic_runtime",
      "purpose": "repository application result",
      "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
      "rollback_behavior": "not_applicable",
      "safety": {
        "automatic_commit_performed": false,
        "automatic_push_performed": false,
        "canonical_write_performed": false,
        "delta75_interaction_performed": false,
        "deployment_performed": false,
        "live_repository_mutation_performed": false,
        "network_access_performed": false,
        "plugin_activation_performed": false,
        "provider_calls_performed": false,
        "training_performed": false
      },
      "serialization": "json",
      "validation": "deterministic"
    },
    "outcome": "APPLICATION_FAILED_AND_ROLLED_BACK",
    "result_id": "rc4-repo-application-93c4cd45c89f16e6",
    "rollback_result": {
      "exact_restoration": true,
      "leftover_artifacts": [],
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "rollback result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "ROLLED_BACK",
      "result_id": "rc4-rollback-result-58a9c7bc36420289",
      "ticket_id": "rc4-rollback-ticket-09443b2deda50501"
    },
    "rollback_ticket": {
      "created_at": "2026-07-10T18:33:08+00:00",
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "rollback_authority",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "rollback ticket",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "rollback_kind": "workspace_restore",
      "target": "disposable_git_fixture",
      "ticket_id": "rc4-rollback-ticket-09443b2deda50501"
    }
  },
  "checks": {
    "failure_detected": true,
    "irreversible_not_claimed": true,
    "partial_failures_reported": true,
    "repair_bounded": true,
    "rollback_verified": true
  },
  "passed": true,
  "recovery_results": [
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "RECOVERED_OR_REPORTED",
      "restoration_complete": true,
      "result_id": "rc4-recovery-result-1c6784936498fd25",
      "scenario": "patch_does_not_apply"
    },
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "RECOVERED_OR_REPORTED",
      "restoration_complete": true,
      "result_id": "rc4-recovery-result-22b9a9ab52ba1f99",
      "scenario": "validation_command_crashes"
    },
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "RECOVERED_OR_REPORTED",
      "restoration_complete": true,
      "result_id": "rc4-recovery-result-eda57ff3ce3b7f35",
      "scenario": "sandbox_process_times_out"
    },
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "RECOVERED_OR_REPORTED",
      "restoration_complete": true,
      "result_id": "rc4-recovery-result-04815b0e2e8aff7f",
      "scenario": "workspace_corrupts"
    },
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "deployment_performed": false,
          "live_repository_mutation_performed": false,
          "network_access_performed": false,
          "plugin_activation_performed": false,
          "provider_calls_performed": false,
          "training_performed": false
        },
        "serialization": "json",
        "validation": "deterministic"
      },
      "outcome": "RECOVERED_OR_REPORTED",
      "restoration_complete": true,
      "result_id": "rc4-recovery-result-1d0fe484bb902778",
      "scenario": "authorization_expires_mid_run"
    },
    {
      "evidence_preserved": true,
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "evidence",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "recovery result",
        "rc3_relationship": "requires_rc3_proposal_or_operator_goal",
        "rollback_behavior": "not_applicable",
        "safety": {
          "automatic_commit_performed": false,
          "automatic_push_performed": false,
          "canonical_write_performed": false,
          "delta75_interaction_performed": false,
          "
```

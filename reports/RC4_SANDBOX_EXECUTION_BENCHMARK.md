# RC4 SANDBOX EXECUTION BENCHMARK

Report: RC4_SANDBOX_EXECUTION_BENCHMARK
Passed: True
Recommendation: n/a
Freeze status: n/a

```json
{
  "checks": {
    "classification_honest": true,
    "fixture_execution_succeeded": true,
    "live_repository_not_mutated": true,
    "network_command_blocked": true,
    "teardown_verified": true
  },
  "episode": {
    "authorization": {
      "authorization_id": "rc4-authorization-fa3dd696b0a7e9b6",
      "created_at": "2026-07-13T06:31:24+00:00",
      "grant": {
        "approver": "operator",
        "approver_role": "operator",
        "expires_at": "2026-07-13T06:41:24+00:00",
        "grant_id": "rc4-permission-grant-05aa01c1105dd0f2",
        "issued_at": "2026-07-13T06:31:24+00:00",
        "meta": {
          "audit_requirements": [
            "provenance",
            "safety_metadata",
            "operator_visibility"
          ],
          "authority": "bounded_operator_authority",
          "lifecycle": "draft",
          "operator_visibility": "developer_overlay_and_reports",
          "owner": "operator",
          "persistence_status": "ephemeral_or_report_only",
          "provenance": "rc4_deterministic_runtime",
          "purpose": "permission grant",
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
        "revocation_reason": "",
        "revoked": false,
        "scope": {
          "allowed_commands": [
            "python_compile"
          ],
          "allowed_paths": [
            "src/example.py"
          ],
          "allowed_tools": [
            "filesystem_read",
            "filesystem_write_fixture",
            "diff_generator",
            "compiler"
          ],
          "max_changed_files": 2,
          "max_diff_lines": 80,
          "max_duration_seconds": 10,
          "meta": {
            "audit_requirements": [
              "provenance",
              "safety_metadata",
              "operator_visibility"
            ],
            "authority": "scope_only",
            "lifecycle": "draft",
            "operator_visibility": "developer_overlay_and_reports",
            "owner": "operator",
            "persistence_status": "ephemeral_or_report_only",
            "provenance": "rc4_deterministic_runtime",
            "purpose": "bounded action scope",
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
          "network_allowed": false,
          "persistence_allowed": false,
          "providers_allowed": false,
          "required_evidence": [
            "transcript",
            "diff",
            "validation_result",
            "teardown"
          ],
          "rollback_required": true,
          "target_branch": "main",
          "target_repository": "fixture_repo"
        }
      },
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "validation_only",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "execution authorization envelope",
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
      "policy_id": "rc4-default-execution-policy",
      "request": {
        "created_at": "2026-07-13T06:31:24+00:00",
        "meta": {
          "audit_requirements": [
            "provenance",
            "safety_metadata",
            "operator_visibility"
          ],
          "authority": "request_only",
          "lifecycle": "draft",
          "operator_visibility": "developer_overlay_and_reports",
          "owner": "operator",
          "persistence_status": "ephemeral_or_report_only",
          "provenance": "rc4_deterministic_runtime",
          "purpose": "execution request",
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
        "purpose": "Apply exact fixture patch and validate it in disposable workspace.",
        "request_id": "rc4-execution-request-e9244462bf6952fb",
        "requested_action": "Apply exact fixture patch and validate it in disposable workspace.",
        "requested_commands": [
          "python_compile"
        ],
        "requested_tools": [
          "filesystem_read",
          "diff_generator"
        ],
        "requester": "operator",
        "target_branch": "main",
        "target_paths": [
          "src/example.py"
        ],
        "target_repository": "fixture_repo"
      }
    },
    "decision": {
      "authorization_id": "rc4-authorization-fa3dd696b0a7e9b6",
      "decision_id": "rc4-authorization-decision-39232a4001614ceb",
      "evaluated_at": "2026-07-13T06:31:24+00:00",
      "evidence_requirements": [
        "transcript",
        "diff",
        "validation_result",
        "teardown"
      ],
      "meta": {
        "audit_requirements": [
          "provenance",
          "safety_metadata",
          "operator_visibility"
        ],
        "authority": "gate_decision",
        "lifecycle": "draft",
        "operator_visibility": "developer_overlay_and_reports",
        "owner": "operator",
        "persistence_status": "ephemeral_or_report_only",
        "provenance": "rc4_deterministic_runtime",
        "purpose": "authorization decision",
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
      "outcome": "AUTHORIZED",
      "reasons": [
        "authorization_scope_valid"
      ],
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
      }
    },
    "episode_id": "rc4-episode-794931f57c7eafaf",
    "execution_result": {
      "evidence": {
        "artifacts": [
          {
            "artifact_id": "rc4-artifact-1930c4fe64148765",
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
              "purpose": "execution artifact",
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
            "path": "src/example.py",
            "retained": false,
            "sha256": "5da0c72778b1c2b85bc0fc20b5b93ff4bca56eff0fd4679fa3f23b809fc638de"
          }
        ],
        "evidence_id": "rc4-execution-evidence-6de63b383cc7d476",
        "filesystem_diff": "--- a/src/example.py\n+++ b/src/example.py\n@@ -1,2 +1,2 @@\n def fixture_function():\n-    return 'old'\n+    return 'new'\n",
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
          "purpose": "execution evidence",
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
            "plugin_act
```

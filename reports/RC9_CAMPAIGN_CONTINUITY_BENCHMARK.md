# RC9_CAMPAIGN_CONTINUITY_BENCHMARK

- Generated: 2026-07-11T03:20:02+00:00
- Passed: True
- Recommendation: RC9_CAMPAIGN_CONTINUITY_READY
- Real operator campaign evidence: fixture_or_developer_rehearsal_only

## Safety
- automatic_code_modification_performed: False
- automatic_approval_performed: False
- provider_call_performed: False
- scheduler_started: False
- persistent_memory_write_performed: False
- campaign_execution_performed: False
- rc3_bypassed: False
- rc4_bypassed: False
- autonomous_development_performed: False
- autonomous_campaign_started: False
- automatic_session_persistence: False
- automatic_campaign_resume: False
- automatic_export_performed: False
- real_operator_evidence_fabricated: False

## Payload
```json
{
  "average_estimated_review_minutes": 10.4667,
  "checks": {
    "cancelled_stops": true,
    "changed_goal_pauses": true,
    "completed_completes": true,
    "failed_implementation_pauses": true,
    "resume_token_for_resumed_campaign": true,
    "unsafe_external_advice_rejected": true,
    "workload_overload_pauses": true
  },
  "generated_at": "2026-07-11T03:20:02+00:00",
  "passed": true,
  "recommendation": "RC9_CAMPAIGN_CONTINUITY_READY",
  "report": "RC9_CAMPAIGN_CONTINUITY_BENCHMARK",
  "safety": {
    "automatic_approval_performed": false,
    "automatic_campaign_resume": false,
    "automatic_code_modification_performed": false,
    "automatic_export_performed": false,
    "automatic_session_persistence": false,
    "autonomous_campaign_started": false,
    "autonomous_development_performed": false,
    "campaign_execution_performed": false,
    "persistent_memory_write_performed": false,
    "provider_call_performed": false,
    "rc3_bypassed": false,
    "rc4_bypassed": false,
    "real_operator_evidence_fabricated": false,
    "scheduler_started": false
  },
  "score": 1.0,
  "trial_count": 15,
  "trials": {
    "abandoned_campaign": {
      "campaign": {
        "campaign_id": "rc7-29d5a076c9b604cdddc7",
        "checkpoints": [
          {
            "campaign_id": "rc7-29d5a076c9b604cdddc7",
            "checkpoint_id": "rc7-b9802419c633e6cd69d2",
            "evidence_quality": 0.86,
            "label": "shadow_review",
            "open_deficits": 1,
            "resolved_deficits": 0,
            "stop_reason": "none"
          }
        ],
        "confidence": {
          "basis": [
            "evidence_quality",
            "resolution_velocity",
            "operator_workload"
          ],
          "confidence_id": "rc7-7cd3b442d7e5a59f9021",
          "value": 0.594
        },
        "created_at": "2026-07-11T03:20:02+00:00",
        "cycles": [
          {
            "comparison": {
              "benefits": [],
              "comparison_id": "rc7-86d5fa01c8413d7eb0bf",
              "confidence": 0.5,
              "new_behavior": "abandoned_campaign remains unresolved.",
              "old_behavior": "abandoned_campaign failed or required manual interpretation.",
              "operator_workload_delta": 0.0,
              "proposal_id": "rc7-717d099c913d2c102469",
              "recommendation": "MORE_EVIDENCE_REQUIRED",
              "regressions": []
            },
            "consultation": {
              "channel": "local_only",
              "consultation_needed": false,
              "decision_id": "rc7-4d570363394a717f623a",
              "hypothesis_id": "rc7-501d72501286711a3f55",
              "provider_call_performed": false,
              "rationale": "local evidence sufficient"
            },
            "created_at": "2026-07-11T03:20:02+00:00",
            "cycle_id": "rc7-bb09deffec2cd6aa428e",
            "deficit": {
              "deficit_id": "rc7-edfbe9c9be221b9fb941",
              "description": "abandoned campaign",
              "evidence": [
                {
                  "evidence_id": "rc7-95a78e3471f4c91a0084",
                  "limitations": [],
                  "quality": 0.86,
                  "source": "fixture",
                  "summary": "abandoned_campaign observed in deterministic pilot"
                }
              ],
              "recurrence": 1,
              "severity": "medium",
              "status": "open"
            },
            "disposition": {
              "decision": "abandoned",
              "disposition_id": "rc7-9d2a46647a0d7d89c67e",
              "next_step": "revise_or_stop",
              "proposal_id": "rc7-717d099c913d2c102469",
              "rationale": "operator decision is abandoned"
            },
            "hypothesis": {
              "confidence": 0.52,
              "deficit_id": "rc7-edfbe9c9be221b9fb941",
              "expected_benefit": "improve targeted behavior without changing authority",
              "hypothesis_id": "rc7-501d72501286711a3f55",
              "risks": [
                {
                  "mitigation": "operator review and rollback",
                  "risk_id": "rc7-bbeb6acce59228cee55d",
                  "risk_type": "scope_creep",
                  "severity": "medium"
                }
              ],
              "status": "unresolved",
              "summary": "Bounded improvement may reduce abandoned campaign."
            },
            "proposal": {
              "executable": false,
              "hypothesis_id": "rc7-501d72501286711a3f55",
              "operator_approval_required": true,
              "proposal_id": "rc7-717d099c913d2c102469",
              "rollback_plan": [
                "reject_proposal",
                "restore_previous_behavior"
              ],
              "scope": "single_subsystem_shadow_only",
              "summary": "Prepare bounded proposal for abandoned campaign.",
              "validation_plan": [
                "focused_test",
                "fast_validation"
              ]
            },
            "validation": {
              "evidence": [
                {
                  "evidence_id": "rc7-95a78e3471f4c91a0084",
                  "limitations": [],
                  "quality": 0.86,
                  "source": "fixture",
                  "summary": "abandoned_campaign observed in deterministic pilot"
                }
              ],
              "failures": [
                "validation_failed"
              ],
              "metrics": {
                "safety": 1.0,
                "target_metric": 0.45
              },
              "passed": false,
              "proposal_id": "rc7-717d099c913d2c102469",
              "validation_id": "rc7-79016aad63d41cd23283"
            }
          }
        ],
        "health": {
          "confidence": 0.594,
          "evidence_quality": 0.86,
          "health_id": "rc7-85d198b47c66f2055454",
          "improvement_velocity": 0.0,
          "open_deficits": 1,
          "operator_workload": 0.0,
          "repeated_failures": 0,
          "repeated_regressions": 0,
          "resolved_deficits": 0,
          "stop_reasons": [],
          "stop_required": false
        },
        "objective": "organize governed development without autonomous action",
        "priority": {
          "campaign_id": "rc7-29d5a076c9b604cdddc7",
          "operator_owned": true,
          "priority": "normal_shadow_review",
          "priority_id": "rc7-d284237921d2e9cb356c",
          "rationale": "operator owns reprioritization; RC7 only reports campaign state"
        },
        "summary": {
          "campaign_id": "rc7-29d5a076c9b604cdddc7",
          "limitations": [
            "no autonomous execution",
            "no persistence changes",
            "no scheduling",
            "fixtures are not real operator evidence"
          ],
          "recommendation": "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS",
          "status": "shadow_only",
          "strengths": [
            "campaign state is inspectable",
            "comparative evidence is explicit",
            "operator authority preserved"
          ],
          "summary_id": "rc7-cc5e6cb07ba2825bd273",
          "weaknesses": [
            "real operator evidence still required before activation"
          ]
        },
        "title": "abandoned campaign"
      },
      "continuation": {
        "assessment_id": "rc9-50ca2c552f748f9c2706",
        "campaign_id": "rc7-29d5a076c9b604cdddc7",
        "continue_allowed": false,
        "decision": "PAUSE_OR_STOP_FOR_OPERATOR_REVIEW",
        "reasons": [
          "operator_or_campaign_stop",
          "insufficient_evidence"
        ]
      },
      "created_at": "2026-07-11T03:20:02+00:00",
      "disposition": {
        "disposition_id": "rc9-9d2a46647a0d7d89c67e",
        "next_step": "PAUSE_OR_STOP_FOR_OPERATOR_REVIEW",
        "operator_decision": "abandoned",
        "rationale": "operator decision is abandoned; RC9 records but does not infer authority"
      },
      "evidence": [
        {
          "evidence_class": "DEVELOPER_REHEARSAL_EVIDENCE",
          "evidence_id": "rc9-c87cfc5aa32ed30329e8",
          "limitations": [
            "not real operator evidence"
          ],
          "quality": 0.45,
          "source": "deterministic_fixture",
          "summary": "abandoned_campaign session evidence"
        }
      ],
      "interruption": null,
      "resume_token": null,
      "session_id": "rc9-48b0bbc9f16e4ac373a6",
      "state": {
        "active_hypothesis": "Bounded improvement may reduce abandoned campaign.",
        "changed_goal": null,
        "prior_operator_decisions": [
          "abandoned"
        ],
        "state_id": "rc9-bb529d525afa7bf00d65",
        "status": "abandoned",
        "unresolved_hypotheses": [
          "Bounded improvement may reduce abandoned campaign."
        ]
      },
      "workload": {
        "clarification_count": 1,
        "estimated_review_minutes": 8.0,
        "evidence_search_burden": 0.2,
        "interruptions": 0,
        "observed_review_minutes": null,
        "rejected_proposals": 1,
        "repeated_steps": 0,
        "resume_burden": 0.2,
        "workload_class": "estimated",
        "workload_id": "rc9-b71862251eb451f46360"
      }
    },
    "accepted_hypothesis": {
      "campaign": {
        "campaign_id": "rc7-48bb6f1728e22d928464",
        "checkpoints": [
          {
            "campaign_id": "rc7-48bb6f1728e22d928464",
            "checkpoint_id": "rc7-569354475e9d1f3b4a41",
            "evidence_quality": 0.86,
            "label": "shadow_review",
            "open_deficits": 0,
            "resolved_deficits": 1,
            "stop_reason": "none"
          }
        ],
        "confidence": {
          "basis": [
            "evidence_quality",
            "resolution_velocity",
            "operator_workload"
          ],
          "confidence_id": "rc7-6d31e3065761efc3a31d",
          "value": 0.944
        },
        "created_at": "2026-07-11T03:20:02+00:00",
        "cycles": [
          {
            "comparison": {
              "benefits": [
                "more inspectable development evidence"
              ],
              "comparison_id": "rc7-445e7447232d1c3073f4",
              "confidence": 0.82,
              "new_behavior": "accepted_hypothesis is handled by a bounded campaign artifact.",
              "old_behavior": "accepted_hypothesis failed or required manual interpretation.",
              "operator_workload_delta": 0.0,
              "proposal_id": "rc7-28cd5256cf477c8afef9",
              "recommendation": "RETAIN_AFTER_OPERATOR_REVIEW",
              "regressions": []
            },
            "consultation": {
              "channel": "local_only",
              "consultation_needed": false,
              "decision_id": "rc7-9f29b0866d1d4f100d4a",
              "hypothesis_id": "rc7-b4c8bd61eec07758d284",
              "provider_call_performed": false,
              "rationale": "local evidence sufficient"
            },
            "created_at": "2026-07-11T03:20:02+00:00",
            "cycle_id": "rc7-73605712d7016df49ec1",
            "deficit": {
              "deficit_id": "rc7-f0c74773be336639c6db",
              "description": "accepted hypothesis",
              "evidence": [
                {
                  "evidence_id": "rc7-8983d672e91723f3b921",
                  "limitations": [],
                  "quality": 0.86,
                  "source": "fixture",
                  "summary": "accepted_hypothesis observed in deterministic pilot"
                }
              ],
              "recurrence": 1,
              "severity": "medium",
              "status": "resolved"
            },
            "disposition": {
              "decision": "accepted",
              "disposition_id": "rc7-2f9d03e33ba130e41dc2",
              "next_step": "retain_shadow_evidence",
              "proposal_id": "rc7-28cd5256cf477c8afef9",
              "rationale": "operator decision is accepted"
            },
            "hypothesis": {
              "confidence": 0.78,
              "deficit_id": "rc7-f0c74773be336639c6db",
              "expected_benefit": "improve targeted behavior without changing authority",
              "hypothesis_id": "rc7-b4c8bd61eec07758d284",
              "risks": [
                {
                  "mitigation": "operator review and rollback",
                  "risk_id": "rc7-bbeb6acce59228cee55d",
                  "risk_type": "scope_creep",
                  "severity": "medium"
                }
              ],
              "status": "validated",
              "summary": "Bounded improvement may reduce accepted hypothesis."
            },
            "proposal": {
              "executable": false,
              "hypothesis_id": "rc7-b4c8bd61eec07758d284",
              "operator_approval_required": true,
              "proposal_id": "rc7-28cd5256cf477c8afef9",
              "rollback_plan": [
                "reject_proposal",
                "restore_previous_behavior"
              ],
              "scope": "single_subsystem_shadow_only",
              "summary": "Prepare bounded proposal for accepted hypothesis.",
              "validation_plan": [
                "focused_test",
                "fast_validation"
              ]
            },
            "validation": {
              "evidence": [
                {
                  "evidence_id": "rc7-8983d672e91723f3b921",
                  "limitations": [],
                  "quality": 0.86,
                  "source": "fixture",
                  "summary": "accepted_hypothesis observed in deterministic pilot"
                }
              ],
              "failures": [],
              "metrics": {
                "safety": 1.0,
                "target_metric": 0.9
              },
              "passed": true,
              "proposal_id": "rc7-28cd5256cf477c8afef9",
              "validation_id": "rc7-95be445107f29fc5d323"
            }
          }
        ],
        "health": {
          "confidence": 0.944,
          "evidence_quality": 0.86,
          "health_id": "rc7-c2191107013665202ea4",
          "improvement_velocity": 1.0,
          "open_deficits": 0,
          "operator_workload": 0.0,
          "repeated_failures": 0,
          "repeated_regressions": 0,
          "resolved_deficits": 1,
          "stop_reasons": [],
          "stop_required": false
        },
        "objective": "organize governed development without autonomous action",
        "priority": {
          "campaign_id": "rc7-48bb6f1728e22d928464",
          "operator_owned": true,
          "priority": "normal_shadow_review",
          "priority_id": "rc7-62d46621dfc320c8eb34",
          "rationale": "operator owns reprioritization; RC7 only reports campaign state"
        },
        "summary": {
          "campaign_id": "rc7-48bb6f1728e22d928464",
          "limitations": [
            "no autonomous execution",
            "no persistence changes",
            "no scheduling",
            "fixtures are not real operator evidence"
          ],
          "recommendation": "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS",
          "status": "shadow_only",
          "strengths": [
            "campaign state is inspectable",
            "comparative evidence is explicit",
            "operator authority preserved"
          ],
          "summary_id": "rc7-e02ef1a11c4ab7e9ce61",
          "weaknesses": [
            "real operator evidence still required before activation"
          ]
        },
        "title": "accepted hypothesis"
      },
      "continuation": {
        "assessment_id": "rc9-51d41fea38881eb4f4b0",
        "campaign_id": "rc7-48bb6f1728e22d928464",
        "continue_allowed": true,
        "decision": "CONTINUE_WITH_OPERATOR_REVIEW",
        "reasons": [
          "no_stop_reason"
        ]
      },
      "created_at": "2026-07-11T03:20:02+00:00",
      "disposition": {
        "disposition_id": "rc9-2f9d03e33ba130e41dc2",
        "next_step": "CONTINUE_WITH_OPERATOR_REVIEW",
        "operator_decision": "accepted",
        "rationale": "operator decision is accepted; RC9 records but does not infer authority"
      },
      "evidence": [
        {
          "evidence_class": "DEVELOPER_REHEARSAL_EVIDENCE",
          "evidence_id": "rc9-db34e2d6bb48860b6969",
          "limitations": [
            "not real operator evidence"
          ],
          "quality": 0.86,
          "source": "deterministic_fixture",
          "summary": "accepted_hypothesis session evidence"
        }
      ],
      "interruption": null,
      "resume_token": null,
      "session_id": "rc9-4ae44215429b68f9b8a7",
      "state": {
        "active_hypothesis": "Bounded improvement may reduce accepted hypothesis.",
        "changed_goal": null,
        "prior_operator_decisions": [
          "accepted"
        ],
        "state_id": "rc9-51350d19ac916409a2f8",
        "status": "started",
        "unresolved_hypotheses": []
      },
      "workload": {
        "clarification_count": 1,
        "estimated_review_minutes": 8.0,
        "evidence_search_burden": 0.2,
        "interruptions": 0,
        "observed_review_minutes": null,
        "rejected_proposals": 0,
        "repeated_steps": 0,
        "resume_burden": 0.2,
        "workload_class": "estimated",
        "workload_id": "rc9-17404c24cae8210aed00"
      }
    },
    "cancelled_campaign": {
      "campaign": {
        "campaign_id": "rc7-a362b7a0b2847792b5da",
        "checkpoints": [
          {
            "campaign_id": "rc7-a362b7a0b2847792b5da",
            "checkpoint_id": "rc7-9547c054d3ffcdd6b35f",
            "evidence_quality": 0.86,
            "label": "shadow_review",
            "open_deficits": 1,
            "resolved_deficits": 0,
            "stop_reason": "none"
          }
        ],
        "confidence": {
          "basis": [
            "evi
```

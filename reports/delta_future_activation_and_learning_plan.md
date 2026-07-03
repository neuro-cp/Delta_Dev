# DELTA Future Activation And Learning Plan

Planning/report-only checkpoint. No runtime behavior changed.

## Current Checkpoint

- Latest verified phase: Runtime V1.5E Local Knowledge Inventory Answer Router
- Active capability: manual local console-only self-knowledge answers through `scripts/ask_delta.py`
- Model B: default
- HYB1: dormant/env-gated only
- Training: disabled
- Provider calls: disabled
- Memory/canonical writes: disabled
- Recall mutation: disabled
- Action execution: disabled

## Plan Summary

DELTA should continue outward from the safe console path:

1. V1.5F Self-Question Test Pack
2. V1.5G Feedback -> Memory Candidate Proposal
3. V1.5H Human-Approved Canonical Memory Write Trial Design
4. V1.5I Recall Bridge Limited Trial
5. V1.5J Demo Script / Showcase Report

## First Demonstrable Loop

User asks about DELTA, DELTA answers from repo-local knowledge, the user
corrects it, DELTA captures feedback, proposes a memory candidate, waits for
human approval, and only later writes canonical memory with audit and rollback
support.

## External Evaluator Boundary

Future daily evaluator review may recommend promote/defer/reject/human-review,
but it must not mutate memory, change routing, delete records, activate tools,
train models, promote HYB1, or become authority.

## Risk Register

- overfitting to one user
- sarcasm mistaken as confirmation
- malicious confirmations
- premature memory writes
- HYB1 accidental promotion
- provider/evaluator treated as authority
- action execution before ledger/approval
- background scheduler introduced too early
- generic agent drift

## Final Recommendation

`PROCEED_SELF_QUESTION_TEST_PACK`

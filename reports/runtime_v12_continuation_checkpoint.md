# Runtime V1.2 Continuation Checkpoint

Date: 2026-07-02

## Current State

Runtime V1 fixture behavior should be treated as frozen. Runtime V1.2 evaluated
the same read-only runtime pipeline against the real Phase A candidate store:

`.tmp/experiments/phaseA_architecture_graduation/overnight_3000/store/knowledge.jsonl`

The evaluation completed and generated the full `runtime_v12_*` report bundle.
The overall grade is `PASS WITH ISSUES`.

## Important Result

Runtime V1.2 did not reproduce fixture-clean behavior on real learned
knowledge. This is evidence, not a reason to tune immediately.

Strengths:

- Candidate store remained read-only.
- Grounding stayed `1.0`.
- Confidence calibration stayed `1.0`.
- Planning score stayed `1.0`.
- Hallucinations stayed `0`.

Real-store bottlenecks:

- Retrieval precision: `0.16`
- Retrieval recall: `0.5333`
- Attention precision: `0.55`
- Attention recall: `0.4333`
- Noise used in reasoning: `12`
- Working memory efficiency: `0.19`

The fixture suite was clean; the actual Phase A corpus exposes activation and
attention failure modes that were not visible in synthetic fixtures.

## Reports

- `reports/runtime_v12_real_knowledge.md`
- `reports/runtime_v12_real_knowledge.json`
- `reports/runtime_v12_retrieval_analysis.md`
- `reports/runtime_v12_attention_analysis.md`
- `reports/runtime_v12_reasoning_analysis.md`
- `reports/runtime_v12_planning_analysis.md`
- `reports/runtime_v12_response_analysis.md`
- `reports/runtime_v12_failure_catalog.md`
- `reports/runtime_v12_runtime_health.md`
- `reports/runtime_v12_question_scorecards.md`

## Code Added

- `tools/runtime_v12_real_knowledge.py`
- `orchestration/tests/runtime/test_runtime_v12_real_knowledge.py`

Docs updated:

- `docs/UPDATE.md`
- `docs/ROADMAP.md`
- `docs/COGNITIVE_GAP_ANALYSIS.md`

## Verification

Passed:

```powershell
.\.venv311\Scripts\python.exe -m py_compile tools\runtime_v12_real_knowledge.py orchestration\tests\runtime\test_runtime_v12_real_knowledge.py orchestration\runtime\runtime_evaluation.py
```

Passed:

```powershell
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_runtime_v12_real_knowledge.py orchestration\tests\runtime\test_runtime_evaluation.py orchestration\tests\runtime\test_knowledge_attention.py orchestration\tests\runtime\test_runtime_v1_pipeline.py orchestration\tests\runtime\test_candidate_knowledge_retrieval.py
```

Result: `14 passed`.

## Guardrails For Next Instance

Do not modify learning, validation, normalization, governance, promotion
scoring, provider prompts, canonical storage, or candidate stores based on this
result.

Do not begin conversation support yet.

Do not migrate candidate knowledge to canonical storage yet.

The next justified work is diagnostic: inspect why real-store activation chooses
irrelevant concepts and why attention suppresses core concepts. Preserve Runtime
V1.2 reports as the baseline before any retrieval or attention changes.

## Suggested Next Question

Are the V1.2 failures caused by:

1. lexical retrieval being too weak for real learned propositions,
2. expected-concept selection being too brittle in the evaluator,
3. attention scoring suppressing semantically relevant but lexically distant
   concepts,
4. duplicate/redundant concepts confusing ranking, or
5. missing concept roles/metadata needed by runtime activation?

Answer that diagnostically before changing runtime behavior.

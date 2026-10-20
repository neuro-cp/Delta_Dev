# Delta Trust Evaluation - 2026-10-19

## Scope And Method

Evaluation preceded runtime source edits. The baseline was commit `5043af4`
with the user's unrelated deleted artifact and scratch files left untouched.
The configured pytest spine passed 60 tests with one optional test skipped.
Passing tests did not establish the trustworthiness of the reported cognition.

Fresh mock-runtime experiments ran for 10, 25, 50 and 100 ticks. No live data
stores, real model inference, external tools or biological-runtime stepping were
used. The persistent artifacts are JSONL, not trained neural weights.

Raw local experiments are in `.tmp/audit-2026-10-19-before` and
`.tmp/audit-2026-10-19-final`. Portable measured summaries are in
`docs/evaluation/2026-10-19-stability.json`. Reproduce with
`tools/delta_stability.py --output <new-directory> --ticks 10 25 50 100`.

## Reproduced Defects And Corrections

1. **Circular prediction validation.** All 16 seeded predictions could validate
   against the seed observations that generated them. Three shared tokens were
   sufficient, with no temporal or independent-evidence requirement. Prediction
   confidence then rose by 0.05. Replaced this with explicit attributed outcome
   assessments, source checks, prediction identity, chronology and source-evidence
   exclusion. Forecast confidence is preserved when recording an outcome.
2. **Semantic suppression confused similarity with equivalence.** Adding `not`
   to a sufficiently long claim could discard the contradiction. Reversing
   `Alice follows Bob` to `Bob follows Alice` was also a duplicate. Identity now
   preserves word order, punctuation, and negation, normalizing only case/space.
3. **Similarity silently superseded knowledge.** A related candidate populated
   `revision_history`, which removed earlier claims from `latest()`. Consolidation
   now preserves both claims. No implicit semantic revision is inferred from
   token overlap. Existing historical supersession records are not rewritten.
4. **Attention was treated as evidence of knowledge.** The current observation
   was recalled as a prior experience; relevance to itself generated a learning
   candidate, which became semantic knowledge. Recall now precedes appending the
   current input. Relevance proposals are typed `context_relevance`; only explicit
   `claim` candidates with evidence IDs are eligible for consolidation. Legacy
   untyped candidates deserialize as `unreviewed` and require review.
5. **Historical prediction rows leaked into current readers.** Working memory,
   simulation callers, CLI, console and report generation used `.all()`. They
   now resolve `.latest()`. Failed predictions cannot boost simulated support.
   Old lexical `supported` outcomes remain in history but are excluded from
   accuracy and reported as unverified.
6. **Runtime events lagged their own state.** The 100th tick reported 214 memories
   against 216 stored. Post-tick snapshots now summarize the completed tick.
   Internal scheduler prompts are attributed to `delta:runtime`, not `operator`.
7. **Counted runs could sleep for a negative duration.** When a slow tick passed
   a supplied duration deadline, the count-driven loop still used that expired
   deadline for sleep. Counted runs now use their tick limit and nonnegative
   interval. Negative bounds fail explicitly; zero ticks means zero ticks.
8. **Inspection generated new proposals.** Each console poll called agency again,
   creating a new plan ID unrelated to the recorded tick. The console now shows
   the recorded agency proposal, or null before any recorded tick.
9. **Model escalation lost context.** Moving to the second reasoning model
   discarded attended context and working memory. Escalation now carries the
   original payload forward alongside the previous answer. Verified with fake
   runners, not a real-model quality experiment.
10. **Report generation overwrote historical evidence.** The reporting command
    now writes `docs/LATEST_RUNTIME_REPORT.md`, preserves the first-life report,
    distinguishes current prediction count from history rows, and states that
    store totals are cumulative, not run-specific deltas.

## Validated Properties

- Seed facts cannot validate their own derived predictions.
- Text overlap and internal model output cannot close predictions automatically.
- Explicit later supported and failed assessments append distinct revisions.
- Replaying an assessment is idempotent, including after reopening the store.
- Conflicting assessments in one batch leave the prediction open.
- Original prediction creation time and forecast confidence survive validation.
- Negated and role-reversed claims remain distinct; related claims are preserved.
- Unreviewed, relevance-only, and evidence-free candidates do not promote.
- Completed predictions do not reappear as open working context.
- Runtime event counts agree with post-tick stores in every measured tick.
- Agency proposals remain non-executing in the evaluated path.
- Inspection reproduces recorded agency rather than inventing another proposal.
- Escalation preserves working context without mutating the caller's payload.

## What Is Still Not Established

An explicit assessment is an attributed observation, not automatic proof of
reality. Source labels are local conventions, not authentication. A trusted
caller can still supply a false assessment or an unsupported claim. Consolidation
requires evidence identifiers but does not yet verify their existence or logical
entailment. These boundaries require a governed ingestion/review path.

Predictions are still generic templates derived from definitions, not structured
conditional models with measurable horizons. There is no expiry, calibrated
confidence revision, or policy to reopen closed predictions when later evidence
conflicts. Legacy self-supported knowledge/predictions have not been migrated.

Contradiction detection remains a lexical shared-token/negation heuristic. Zero
contradictions in the repaired idle workload means fewer artificial conflicts;
it does not demonstrate a reliable contradiction classifier.

Self-model health is heuristic. Reflection count uses learning records as a
proxy; attention distribution counts memory tags rather than observed attention;
consolidation rate includes bootstrap concepts. These are not scientific scores
of intelligence, learning efficiency, or cognitive health.

JSONL stores repeatedly scan files and lack a shared transaction or multiwriter
protocol. Crash recovery, truncated-tail handling, simultaneous writers, and
multi-day stability have not been verified. The 100-tick run is a bounded idle
workload, not evidence of general adaptive competence.

## Recommendation

Keep the existing architecture. Build a small, governed evidence ingestion and
review workflow with explicit claims, traceable source records, measurable
prediction contracts, and independent outcome fixtures. Evaluate that workflow
before broad refactoring, increasing runtime duration, or adding more regions.

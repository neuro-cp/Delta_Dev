# Delta: Implemented Mechanics

Inspection date: 2026-10-19. This describes executable behavior in the current
repository, not a claim that every architectural label is fully realized.

## Two Runtime Paths

The canonical developer path is `tools/delta_cli.py` -> `CognitiveRuntime` ->
`CognitiveCycle` -> `CognitiveLoop`. It is an explicit Python service pipeline
using dataclasses, rule-based decisions, and JSONL persistence.

Separately, `engine/runtime.py` defines `BrainRuntime`, an older biological-style
dynamics engine. It loads region/population definitions and profiles, evolves
activity, applies competition and modulatory signals, and can latch decisions.
`RecallBridge` can construct this runtime when runtime recall is enabled. The
CLI defaults and all current stability experiments disable that optional path.

These paths share some integration surfaces; they are not one demonstrated,
unified neural learning system. New Python service labels do not prove that
historically tuned dynamics have been integrated or superseded.

## One Bounded Tick

1. Derive a self-model from persistent stores and read active goals.
2. Construct an internal prompt from health warnings or a generic review request.
3. Retrieve prior experience, append the current observation, rank recalled items,
   and assemble working memory. Runtime-generated input is `delta:runtime`.
4. Classify the task, build candidate routes, choose a route, and produce an answer.
5. Append the answer and its observation-to-output temporal relationship.
6. Produce structured reflection and a durable learning proposal record.
7. Apply explicit external prediction-outcome assessments if any are available.
8. Run consolidation over the last three learning records under the claim gate.
9. Recompute the self-model to reflect completed writes.
10. Score hypothetical goal options and produce one non-executing agency proposal.
11. Append a runtime event with IDs, consolidation counts, agency, post-tick
    metrics, duration and tick index.

This is sequential orchestration. There are no independently running regional
agents or implemented cognitive resource scheduler in this path. Planning and
consolidation appear as deferred stages inside `CognitiveCycle`; the outer
runtime supplies consolidation, simulation and agency. This distinction matters
when comparing `--cycle` with `--runtime-ticks`.

## Persistent State

`MemoryStore` appends experience records containing a UUID, timestamp, kind,
text, source, confidence, tags and metadata. It rereads JSONL on inspection.
`RelationshipStore` records typed links; the active cycle creates a temporal
link from observation to output. This is not yet causal discovery.

`SemanticKnowledgeStore` stores concept definitions, supporting/contradicting
evidence IDs, creation source, confidence, timestamps and revision references.
`latest()` excludes IDs explicitly superseded by revision references. New
consolidation no longer infers those references from lexical similarity.

`PredictionEngine.latest()` folds append-only rows by prediction ID. Goals have
a similar latest-by-ID view. Learning records and plan records have their own
stores. Experiences remain history; knowledge and predictions have separate
notions of active state. Raw row counts are not interchangeable with object counts.

Working memory is a temporary list for one cycle, not a persistent matrix. The
active path has no standalone `MemoryMatrix` implementation. Calling the stores
a memory matrix is an architectural analogy, not a description of a learned
tensor or integrated associative memory algorithm. Episodic/replay code exists
elsewhere but is not fully integrated into this default path.

## Retrieval, Attention And Working Memory

Experience retrieval tokenizes the query and each record's text, tags, layer and
metadata. It scores token overlap divided by the larger token-set size, weighted
by stored confidence. The cycle requests up to eight recalled records.

Attention reranks those candidates and keeps five. Its current formula is:

```text
0.55 * task_relevance
+ 0.25 * confidence
+ 0.15 * operator_priority
+ 0.05 * experience_bias
```

Task relevance is shared task tokens divided by task-token count. Operator
priority comes from an `operator` tag; experience bias is 0.2 for experience
records. These are hand-selected weights, not learned attention parameters.
There is no durable latch, learned goal weighting, novelty estimator, or decay
in this service. Retrieval and attention are distinct calls but currently use
closely related lexical signals.

Working memory combines the current input, attended experiences, related
semantic definitions and up to five current open predictions. It is forwarded
to reasoning as advisory JSON. It has no explicit global token budget, does not
receive active goals in this path, and is discarded after the cycle. A separate
older working-memory buffer with decay exists but is not this builder.

## Reasoning And Model Plugins

`CognitiveLoop` adapts the inquiry, interprets/task-types it, builds a task graph,
applies route constraints, scores possible routes and chooses one. Route
selection prioritizes estimated confidence, then cost, then a fixed tie-break.
Available routes include deterministic solving, recall, LLM fallback and operator
query. Small arithmetic is handled by the deterministic route.

The mock model echoes the question with a fixed confidence. The real model router
can sequence configured local GGUF models, feeding an earlier answer forward for
critique until a confidence threshold is met. Escalation now retains working
memory and attended context. The returned confidence is not a calibrated estimate
of factual accuracy. Real-model behavior was not measured in this evaluation.

Result evaluation currently checks execution success, nonempty output and a
placeholder-string guard. It does not fact-check arbitrary answers. Receiving a
successful answer therefore does not establish that Delta learned a true fact.

## Reflection, Learning And Consolidation

Reflection is rule-based: it records successful output, relevant attended IDs,
candidate memory IDs and working-memory summary. Surprise and conflict fields
are currently empty in the normal path. It does not introspect a neural model.

Learning produces relevance candidates, confidence suggestions, questions and
goal candidates. The current relevance candidate says that attended context
overlaps the prompt; it does not extract a factual world model. Such candidates
are now typed `context_relevance` and cannot become factual knowledge merely
because a cycle ran. Untyped historical candidates are `unreviewed`.

Consolidation accepts explicit `claim` candidates carrying evidence IDs, suppresses
exact normalized duplicates, appends new semantic records, detects potential
contradictions and may generate predictions. This remains a structural gate:
the caller must govern claim extraction/review, and the engine does not yet prove
that the supplied evidence entails the claim. Positive/negative confidence
suggestions are not applied to semantic knowledge automatically.

Contradiction detection uses shared tokens and opposing negation. It can preserve
a simple conflict but cannot reliably interpret scope, exceptions, causality,
quantifiers or time. Its outputs should be treated as investigation candidates.

## Predictions And Simulation

A sufficiently confident semantic definition generates a template expectation:
`If this concept is relevant again, expect: <definition>`. Initial prediction
confidence is 0.8 times semantic confidence. This is not yet a falsifiable
conditional model of an environment.

Validation now requires a later persisted `prediction_outcome` from an explicit
operator/tool/sensor/test source, metadata identifying the prediction, a
`supported` or `failed` outcome, and a validation source. Seed evidence cannot
validate its own forecast. The update appends a row with the same prediction ID,
retains the original timestamp/confidence, and records assessment provenance.
Old lexical confirmations are excluded from accuracy. Source names are
conventions rather than authenticated identities.

Simulation matches option tokens against knowledge, predictions and relationship
descriptions, then combines average confidence, goal overlap and evidence counts
through fixed weights. It emits a templated expected outcome and heuristic risk.
It neither rolls forward a learned world state nor runs physical simulations.
Failed predictions no longer contribute positive simulation support.

## Goals, Planning, Agency And Execution

Goals persist descriptions, priority, urgency, value, effort, confidence and
progress. Executive control ranks goal pressure. Planning chooses a simulated
option by confidence minus risk and emits a short proposed plan. Decision scoring
uses expected benefit, goal satisfaction, cost and risk.

Agency selects a high-priority goal and returns a proposal with
`execution_authority=false`. The runtime persists that proposal and embedded
plan in its event; it does not execute the plan or automatically complete goals.
Without active stored goals, agency can derive temporary goals from self-model
observations. There is no demonstrated long-term goal adaptation loop yet.

## Self-Model And Console

The self-model recomputes counts, confidence summaries, temporal activity and
health warnings from stores. It is derived state. Its ratios are descriptive
heuristics: relationship count per experience is not graph-theoretic density;
tag distribution is not measured attention flow; learning-record count proxies
reflection activity. They must not be read as intelligence scores.

The console is a standard-library HTTP page that polls `/api/state` and displays
store snapshots. It now shows recorded agency and current prediction versions.
It remains a basic inspector, without a full recorded working-memory timeline,
region performance dashboard or visual knowledge graph.

## Historical Decision Latch

`BrainRuntime._evaluate_decision_latch` compares the leading two channel
dominances and a relief signal. Both thresholds must hold for a configured number
of consecutive steps. The counter resets when conditions fail. Once committed,
the latch records winner, time, step and signal values, and may influence PFC
working state and decision bias. This temporal behavior is different from ranking
five memories once per cognitive cycle.

`PopulationModel` contains bounded activity/rate dynamics, tonic stabilization,
excitation/inhibition and optional noise. `CompetitionKernel` normalizes and
smooths channel dominance and applies lateral inhibition. These are implemented
dynamical mechanisms; they are not by themselves trained language understanding.
Their tuned parameters were left unchanged and were not validated by the mock
runtime tests. Legacy diagnostics include a hard-coded external trace path that
must be contained before further experiments with that runtime.

## Practical Assessment

The architecture supports persistent state, explicit interfaces, mock/real model
routing and bounded proposals. The immediate work is to connect independent
evidence to reviewed knowledge, measurable predictions and goal outcomes. Merely
running more ticks or attaching a stronger LLM does not establish this feedback.

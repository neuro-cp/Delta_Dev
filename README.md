# DELTA — Developmental Cognitive Model

> **Development note:** `main` is the stable repository entry point and may lag active development. For the most recent implementation, review the repository's newest active development branch before evaluating DELTA. At the time this README was added, the principal development line is `codex/delta-cognitive-core`.

DELTA is an experimental **developmental cognitive architecture** designed to place model capabilities inside an inspectable, persistent, evidence-driven, and explicitly governed runtime.

Rather than treating a language model as an autonomous authority, DELTA separates reasoning capability from operational authority. Models can contribute analysis, proposals, authored material, and bounded problem solving, while the surrounding runtime controls evidence, persistence, permissions, evaluation, state transitions, and consequential actions.

The central engineering question is:

> **How can increasingly capable AI systems learn, operate, and adapt while remaining observable, bounded, attributable, and subject to explicit authority?**

## Why DELTA Exists

Modern language models can perform sophisticated reasoning but are commonly deployed through comparatively thin orchestration layers. DELTA explores a different architecture: a durable cognitive runtime in which capability development, evidence, permissions, memory, evaluation, and operator control are first-class system components.

The project is intended as a research platform for environments where AI behavior must be more than useful — it must also be **inspectable, reproducible, attributable, constrained, and recoverable**.

DELTA therefore emphasizes:

- explicit separation between recommendation and authorization;
- persistent state rather than prompt-only continuity;
- provenance-linked evidence;
- bounded learning and task missions;
- independent evaluation before capability claims;
- sandboxed work before tracked-source application;
- operator-controlled authority boundaries;
- durable audit and replay records;
- restart-safe state transitions;
- constrained external-provider and resource access;
- prevention of silent permission expansion.

## Conceptual Model

```text
Observed Evidence
       |
       v
Capability / Gap Assessment
       |
       v
Bounded Mission Selection
       |
       v
Reasoning + Sandboxed Work
       |
       v
Independent Evaluation
       |
       v
Governance / Authority Boundary
       |
       v
Validated Runtime State
       |
       +----> reassessment / next mission
```

A model response is evidence or a proposal — **not authority**.

A completed task is activity — **not automatically proof of learning**.

A capability claim requires retained evidence and the evaluation path applicable to that claim.

## Security- and Assurance-Relevant Properties

DELTA is being developed around properties useful wherever model capability must coexist with strict operational control.

### 1. Authority Separation

The reasoning system does not implicitly inherit authority over the environment. Sensitive actions can be placed behind explicit approval boundaries, including:

- external model/provider calls;
- acquisition of external resources;
- evaluator acquisition;
- protected-scope access;
- tracked-source modification;
- Git operations;
- deployment;
- permission expansion.

Approval records are intended to be scoped, attributable, persistent, and consumable rather than functioning as indefinite blanket permission.

### 2. Evidence and Provenance

DELTA retains structured evidence supporting runtime decisions and capability assessments. The architecture is designed so that consequential state can be traced to the evidence, evaluation, request, or operator action that produced it.

This supports post-hoc inspection and reduces dependence on opaque conversational context.

### 3. Bounded Development

Developmental or learning work occurs through bounded missions rather than unrestricted self-modification. Missions can be evaluated independently before results are promoted into durable capability state or applied to tracked source.

The current system does **not** claim autonomous online retraining of model weights.

### 4. Sandboxed Execution

Work can be separated from authoritative repository/runtime state. Proposed changes may be generated and validated in bounded environments before crossing a controlled application boundary.

This provides a natural location for policy enforcement, testing, evaluator gating, and human review.

### 5. Persistent Governance

Authority decisions are represented as runtime state rather than transient UI events. The design tracks request identity, scope, disposition, response provenance, and consumption so that restart or replay does not silently recreate authority.

### 6. Recovery and Replay

The runtime is designed around durable state and restart-safe behavior. This allows interrupted work, pending authority requests, evidence, and mission state to be reconstructed without relying solely on model context.

### 7. Provider Independence

External language models are treated as replaceable reasoning resources rather than as DELTA's identity or governing authority. Provider output remains advisory until accepted through the relevant runtime path.

This separation is intended to make the architecture adaptable across local models, hosted models, specialized evaluators, and future inference systems.

## Potential Application Areas

DELTA is a general research architecture rather than a finished domain product. Its governance model may be relevant to systems involving:

- controlled AI-assisted analysis;
- human-supervised autonomous workflows;
- cyber-defense and software-assurance environments;
- high-consequence decision-support systems;
- long-running analytical agents;
- model evaluation and red-team environments;
- constrained research automation;
- multi-model reasoning systems;
- provenance-sensitive intelligence workflows;
- AI systems operating across different trust or permission domains.

These are architectural directions, not claims of current operational certification or deployment readiness.

## Architecture

```text
+---------------------------------------------------------+
|                 Model / Reasoning Layer                 |
|  local model | hosted model | evaluator | specialist   |
+----------------------------+----------------------------+
                             |
                             | advisory output
                             v
+---------------------------------------------------------+
|               DELTA Developmental Runtime               |
|                                                         |
|  evidence + provenance                                  |
|  capability / gap state                                 |
|  agenda + mission selection                             |
|  resource policy                                        |
|  evaluator policy                                       |
|  sandbox orchestration                                  |
|  lifecycle / recovery                                   |
|  behavioral validation                                  |
+----------------------------+----------------------------+
                             |
                             | governed request
                             v
+---------------------------------------------------------+
|                    Authority Layer                      |
|                                                         |
|  scoped approval / rejection                            |
|  protected boundaries                                   |
|  one-use authority records                              |
|  immutable response history                             |
+----------------------------+----------------------------+
                             |
                             v
+---------------------------------------------------------+
|                 Validated Runtime State                 |
|  evidence | dispositions | capabilities | next goals   |
+---------------------------------------------------------+
```

## Current Developmental Runtime

The newer cognitive-core development line includes work around:

- persistent mission, capability, evidence, and agenda state;
- explicit operator approval and one-use authority records;
- local/external resource policy with provenance and deduplication;
- bounded learning missions;
- evaluator gating;
- sandbox validation;
- tracked-source application boundaries;
- behavioral-failure and repository-behavior-contract paths;
- governed code-repair workflows;
- operator views for live runtime inspection;
- lifecycle, replay, authority, and recovery regression tests.

The active system should not be interpreted as an unrestricted autonomous agent. It can investigate and propose within its current envelope while pausing at defined authority boundaries.

## Repository Orientation

The repository has evolved through multiple experimental stages. The `main` branch contains earlier foundations and research components, while newer development may exist on active branches.

Important areas across the project include:

- `engine/` — core processing components;
- `learning/` — learning/development experiments;
- `environment/` — environment-facing components;
- `episodes/` — episodic/runtime artifacts;
- `inspection/` — inspection and observability tooling;
- `integration/` — integration surfaces;
- `config/` — configuration;
- `docs/` — architectural and development documentation.

On the cognitive-core development line, additional important surfaces include:

- `DELTA.py` — desktop runtime/client;
- `orchestration/runtime/` — governed runtime controllers, policy, evidence, lifecycle, monitoring, and validation bridges;
- `tests/runtime_gsr/` — focused governance/runtime contract tests;
- `docs/ARCHITECTURE.md` — architecture and cognitive-cycle intent;
- `docs/INVARIANTS.md` — authority, evidence, state, and development invariants;
- `docs/UPDATE.md` — detailed development handoff/history.

## Trust Model

DELTA's working assumption is that **capability and authority should not be synonymous**.

A highly capable reasoning component may still be treated as untrusted with respect to consequential actions. The runtime can therefore allow broad analytical capability while independently constraining what actions can cross system boundaries.

```text
model recommendation != authorization
capability claim      != observed activity
generated artifact    != validated evidence
successful sandbox    != permission to deploy
```

This distinction is foundational to the project.

## Human Operator Role

The operator is not expected to manually supervise every internal computation. Instead, DELTA attempts to place human involvement at meaningful authority boundaries.

The intended pattern is:

```text
machine autonomy inside a bounded envelope
                 +
human authority at consequential boundaries
```

This allows experimentation with increasingly persistent and capable systems without assuming that increased reasoning ability should automatically produce increased permissions.

## Evaluation Philosophy

DELTA distinguishes between:

1. **activity** — something happened;
2. **output** — the system produced an artifact;
3. **evidence** — retained information supports a proposition;
4. **evaluation** — a defined process tests that proposition;
5. **capability state** — the runtime has sufficient evidence to retain a capability assessment.

This is intended to prevent dashboards, model confidence, or successful one-off outputs from being mistaken for demonstrated developmental progress.

## Model and Tooling Relationship

Language models and coding agents have been used during DELTA's development as engineering and architectural tools. They are not represented as DELTA's persistent identity or independent authority.

The runtime itself owns its persisted developmental state. External reasoning systems can contribute proposals and implementation work, but they do not automatically write beliefs, goals, permissions, or validated capability claims into authoritative state.

## Current Limitations

DELTA remains an experimental research system.

Current limitations include:

- no demonstrated unrestricted or open-ended intelligence growth;
- no claim of autonomous online model-weight training;
- provider and external-resource access remain intentionally constrained;
- some developmental paths remain experimental;
- historical research artifacts coexist with current runtime components;
- long-running operation remains subject to budget, process, duplication, recovery, and authority controls;
- the system has not been certified for classified, safety-critical, or other regulated operational environments.

These limitations are stated explicitly because the project's objective is measurable, inspectable development rather than inflated autonomy claims.

## What to Review First

For a technical evaluation of DELTA:

1. **Check the newest active branch.** Do not assume `main` represents the current runtime.
2. Review the architecture and invariants documentation.
3. Inspect the governed runtime controllers and authority paths.
4. Inspect evidence/provenance persistence and restart behavior.
5. Review focused governance and lifecycle tests.
6. Examine sandbox-to-tracked-source boundaries.
7. Evaluate failure behavior: rejection, interruption, replay, duplicate requests, and unavailable providers.
8. Treat demonstrations as illustrations; use retained evidence and tests for capability conclusions.

## Research Direction

The long-term research direction is a developmental loop capable of identifying measurable gaps, selecting bounded work, gathering evidence, evaluating outcomes, and updating durable state — while preserving a strict distinction between **increasing capability** and **increasing authority**.

DELTA is therefore less an attempt to build an unconstrained autonomous agent than an attempt to answer a harder systems question:

> **Can an AI system become more capable over time while its actions remain governable, attributable, inspectable, and recoverable?**

That is the core problem this repository explores.

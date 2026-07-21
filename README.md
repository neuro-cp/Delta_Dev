# DELTA

DELTA is a **Developmental Cognitive Model** research project: a governed
runtime around language-model capabilities rather than a claim that a single
model is autonomously retraining itself.

The project focuses on making learning and development inspectable:

```text
observed evidence
  -> bounded task or learning mission
  -> sandboxed work and independent evaluation
  -> operator review at authority boundaries
  -> durable, provenance-linked runtime records
```

DELTA does not treat a model response, a heartbeat, or a pile of artifacts as
proof of learning. Capability claims require retained evidence and the
applicable evaluation path. Provider output is advisory evidence, never
authority to mutate tracked source, expand permissions, commit, push, or
deploy.

## What Is Here

The repository contains the current developmental runtime and the engineering
substrate around it:

- persistent mission, capability, evidence, and agenda state;
- explicit operator approval and one-use authority records;
- local and external resource policy with provenance and deduplication;
- bounded learning missions, evaluator gating, sandbox validation, and
  tracked-source application boundaries;
- behavioral-failure and repository-behavior-contract paths for governed code
  repair;
- Tkinter operator views for inspecting live runtime state and responding only
  to concrete pending requests;
- focused regression tests for lifecycle, replay, authority, and recovery
  invariants.

The active system is not an unrestricted autonomous agent. It can investigate
and propose inside its current envelope, but it pauses at authority boundaries
such as provider calls, protected scope, evaluator acquisition, tracked-source
application, Git, and deployment.

## Architecture

```text
Language or Local Model
        | advisory reasoning or bounded authored material
        v
Developmental Runtime
  - evidence and provenance
  - capability and gap assessment
  - agenda and mission selection
  - resource/evaluator policy
  - sandbox work and sealed evaluation
        |
        v
Operator Governance
  - scoped approvals and rejections
  - immutable response history
  - no implicit authority expansion
        |
        v
Validated Runtime State
  - retained evidence and dispositions
  - restart-safe records
  - next-goal reassessment
```

DELTA's long-term aspiration is a developmental loop that can identify and
resolve measurable capability gaps. Its current implementation is deliberately
more conservative: the runtime can persist and reassess work, but promotion,
source expansion, provider use, and tracked-source application remain
governed.

## Quick Start

### Requirements

- Windows 10 or 11
- Python 3.11
- Git
- An isolated virtual environment at `.venv311` (recommended)

### Create or activate the environment

```powershell
cd G:\Delta_Dev
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip pytest
```

This project intentionally keeps most runtime dependencies local and explicit.
Do not add provider keys or install packages merely to run the standard local
tests.

### Start the desktop runtime

```powershell
cd G:\Delta_Dev
.\.venv311\Scripts\python.exe .\DELTA.py
```

The desktop application is a Tkinter client over governed runtime surfaces.
The **Developer Overlay** and runtime-monitor views are useful for inspecting
state during a demo, but they are observers; they do not grant authority.

### Run focused verification

Use focused tests while working on a surface instead of treating a full
repository collection as the default signal:

```powershell
.\.venv311\Scripts\python.exe -m pytest -q tests\runtime_gsr\test_continuous_operator_monitor.py
```

The configured default test spine is also available:

```powershell
.\.venv311\Scripts\python.exe -m pytest
```

Some historical test areas are preserved as evidence and may need separate
triage. Real-provider tests remain opt-in; ordinary local validation should not
prompt for model configuration or call a provider.

## Runtime Safety Model

The important boundary is:

```text
proposal or model recommendation != authorization
```

Examples of actions that require explicit governed handling include:

- a provider or external-research request;
- evaluator material that could influence a capability claim;
- tracked-source application after sandbox validation;
- permission expansion, Git, deployment, or protected-path changes.

The implementation is designed to preserve request identity, scope, status,
one-use consumption, response provenance, and restart recovery. A completed or
rejected request cannot be silently reopened as a new pending action.

## How GPT-5.6 and Codex Were Used

### GPT-5.6

GPT-5.6 was used in the **development process** as an architectural review and
specification partner. It helped pressure-test the system design: identifying
missing transitions, distinguishing meaningful behavioral evidence from
activity telemetry, refining authority boundaries, and reviewing proposed
acceptance criteria.

It is not represented as DELTA's identity, decision authority, persistent
memory, or model-training mechanism. A design discussion does not become
runtime knowledge until DELTA's own evidence and governance paths record and
validate it.

### Codex

Codex was used as the repository engineering agent. Its work included reading
the existing architecture, implementing narrow integrations, adding focused
tests, running bounded validation, inspecting real runtime artifacts, and
keeping changes within the repository's governance rules.

Codex does not act as DELTA's cognitive controller. In particular, it does not
silently write DELTA's beliefs, self-model, goals, or capability claims. It can
improve the software that hosts those processes, while the runtime itself owns
its persisted state and the human operator retains consequential authority.

### What Neither Tool Did

- Neither tool trained or fine-tuned DELTA model weights.
- Neither tool automatically granted provider, source, Git, deployment, or
  tracked-source authority.
- Neither tool turned model prose into a validated capability without an
  independent evaluation path.
- Neither tool substitutes a demo status display for evidence of successful
  development.

## Repository Layout

- `DELTA.py` - the Tkinter desktop application and user-facing runtime client.
- `orchestration/runtime/` - governed controllers, policy, lifecycle, runtime
  monitors, evidence, and validation bridges.
- `tests/runtime_gsr/` - focused runtime and governance contract tests.
- `docs/ARCHITECTURE.md` - system architecture and cognitive-cycle intent.
- `docs/INVARIANTS.md` - authority, evidence, state, and development rules.
- `docs/UPDATE.md` - detailed continuation and historical handoff log.

The repository also contains historical research outputs, test artifacts, and
scratch material. Treat them as evidence only unless they are imported by the
runtime or covered by current tests.

## Current Limitations

- The system has not demonstrated unrestricted, open-ended intelligence growth.
- Runtime learning is record- and evaluation-based; it is not online weight
  training.
- Provider and source access are intentionally constrained and may be paused
  awaiting operator approval.
- Long-running work remains subject to process, budget, duplicate-prevention,
  and restart-safety controls.

Those constraints are intentional. DELTA is being built as an inspectable,
evidence-driven developmental system where increased capability does not imply
unchecked authority.

## Further Reading

- [Architecture](docs/ARCHITECTURE.md)
- [Runtime invariants](docs/INVARIANTS.md)
- [Development handoff log](docs/UPDATE.md)

## Hackathon Submission Note

This repository is being shared to document and discuss DELTA's architecture,
development process, and governance approach. The author does **not** wish to
be considered for prizes, awards, or winnings associated with a Devpost
submission. This note is informational; any formal withdrawal from prize
consideration should also be communicated through the relevant Devpost
submission flow or directly to the event organizers.

# DELTA

DELTA is a Developmental Cognitive Model (DCM) project.

A DCM is not a replacement for a foundation language model. It is the complete
cognitive stack around one or more language engines: a governed developmental
runtime that grows knowledge through reviewed experience, structured memory,
evidence, graph reasoning, competency testing, and controlled distillation.

The project is not an LLM wrapper and it is not claiming that day-to-day
learning currently happens inside model weights. DELTA's learning loop lives in
the runtime: conversation and evidence produce candidate concepts, operator
review controls what enters the noncanonical substrate, graph links and replay
support reasoning, competency tests measure readiness, and neural training is
reserved as a later graduation event.

The architecture has three layers:

```text
Foundation Model
(Language Engine)
        |
        v
Developmental Cognitive Runtime
(Memory, retrieval, graph reasoning, governance, operator review)
        |
        v
Developmental Cognitive Model Checkpoint
(A distilled model produced from reviewed curricula and competency tests)
```

The current checkpoint is primarily Layer 2: the cognitive runtime and
noncanonical substrate. A future distilled checkpoint may internalize selected
validated behaviors, but the runtime remains the place where provenance,
rollback, operator review, and long-term knowledge management stay explicit.

## Developmental Lifecycle

DELTA's day-to-day learning occurs continuously in the runtime. Training is not
the default learning mechanism; it is a periodic graduation step after enough
reviewed evidence has accumulated.

```text
Experience
        |
        v
Review
        |
        v
Structured Memory
        |
        v
Knowledge Graph
        |
        v
Replay
        |
        v
Competency Tests
        |
        v
Curriculum
        |
        v
Training Packet
        |
        v
Distillation
        |
        v
Developmental Cognitive Model
```

## Core Principle

Influence pathways should be observable, bounded, deterministic where possible,
and reversible or inspectable before they are allowed to affect runtime state.

Neural training is a graduation event, not the default learning mechanism.
DELTA should first learn through governed concept formation, graph expansion,
replay, review, and competency testing. Only mature, reviewed curricula should
be packaged for possible distillation.

## Current Scaling Focus

The RC2 substrate expansion moved DELTA into systems-engineering territory:
large concept and graph stores now need indexes, caches, adjacency maps,
cluster analysis, retrieval latency checks, and graph analytics before further
large-scale growth. Future expansion should be gated by usefulness and
performance, not raw concept count.

## Main Areas

- `engine/` - runtime dynamics, salience, value, decision, execution governance.
- `memory/` - working, semantic, replay-derived, and inspection memory surfaces.
- `learning/` - design-time and governed learning proposal infrastructure.
- `orchestration/` - inquiry interpretation, task routing, execution, and recall.
- `integration/` - AI/substrate interfaces and bridge surfaces.
- `inspection/` - read-only analysis and audit tooling.
- `regions/`, `neuron/`, `profiles/`, `config/` - compiled substrate definition.
- `environment/` - simple simulation/world loop support.

## Local Artifacts

The repository currently contains research outputs and historical experiment
material, including `z testing/`, `z artifacts/`, trace dumps, generated images,
and root-level scratch scripts. Treat those as experimental evidence unless a
file is clearly imported by the runtime or covered by tests.

The external backup at `C:\Users\Admin\Desktop\delta backup` is intentionally
outside this repository. See `docs/legacy_backup_inventory.md` before copying
anything from it back into the active project.

## Testing

The default pytest config is currently a smoke spine over coherent surfaces:

```powershell
.\.venv311\Scripts\python.exe -m pytest
```

Real-model orchestration tests require `RUN_REAL_MODELS=1`; normal test runs
should not prompt for model configuration.

The broader historical test tree still contains legacy collection failures from
renamed or removed modules. Treat those as a triage queue, not as the current
baseline.

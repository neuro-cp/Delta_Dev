# DELTA-75

DELTA-75 is an experimental cognitive substrate for structured reasoning,
episodic experience, replay-driven interpretation, and governed learning.

The project is not an LLM wrapper. The runtime is intended to provide explicit
mechanics for signal propagation, salience, memory, decision pressure,
arbitration, replay, and inspection. AI models can be attached as plugins or
interpretive surfaces, but they should not become hidden authority inside the
substrate.

## Core Principle

Influence pathways should be observable, bounded, deterministic where possible,
and reversible or inspectable before they are allowed to affect runtime state.

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

# DELTA-75 Development Roadmap

This roadmap favors substrate integrity over adding capability too quickly.

## Current Stable Spine

- Orchestration smoke tests pass.
- AI/substrate boundary tests pass.
- Execution dry-run tests pass.
- Risk surface and execution-preview tests pass.
- The external legacy backup is outside the repository and documented as
  reference material.

Default check:

```powershell
.\.venv311\Scripts\python.exe -m pytest
```

## Priority 1: Preserve The Architecture Boundary

- Keep LLM/model surfaces as plugins, adapters, or interpretive helpers.
- Do not allow model output to mutate runtime state directly.
- Require explicit governance for learning, execution, and promotion pathways.
- Prefer read-only inspection surfaces before adding control surfaces.

## Priority 2: Triage Historical Test Breakage

The broad historical suite currently has collection failures from renamed or
missing modules, especially:

- `engine.cognition.*`
- `memory.context.runtime_context`
- `engine.affective_urgency.urgency_driver`
- `memory.inspection.diffing.diff_runner`

Recommended approach:

1. Decide whether each missing module represents live architecture or abandoned
   experiment history.
2. Move abandoned tests into a clearly named legacy/characterization area.
3. Restore or adapt live tests one module family at a time.
4. Expand `pyproject.toml` only after each family has a passing baseline.

## Priority 3: Clean Source Versus Evidence

The repository still mixes source code with experiment output, dumps, traces,
plots, and root-level scratch scripts.

Recommended buckets:

- `runtime`: importable substrate code
- `tests`: current passing contract tests
- `experiments`: runnable but non-baseline experiment scripts
- `artifacts`: generated traces, plots, dumps, and logs
- `archive`: preserved historical material

This can be done gradually without deleting anything.

## Priority 4: Learning Loop Definition

The AGI-machine direction depends on a strict learning ladder:

1. runtime activity
2. episode trace
3. replay interpretation
4. proposal generation
5. risk, fragility, and governance evaluation
6. inspection
7. explicit promotion
8. bounded runtime influence

Each step should have its own schema, tests, and no hidden authority over the
next step.

## Priority 5: Backup Mining

Only mine `C:\Users\Admin\Desktop\delta backup` for specific missing pieces.
Good candidate families are dry-run execution, risk surfaces, AEM/proposal
interfaces, and bridge scaffolds. Avoid wholesale copying from `deltagem`.

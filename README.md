# DELTA-75

DELTA-75 is an experimental persistent cognitive architecture for structured
reasoning, memory, attention, and governed learning. It is software coordinating
cognitive processes and state, not a single trained neural model. Language
models can contribute reasoning as replaceable plugins; the substrate is
responsible for governing what becomes knowledge or an authorized action.

## Assessment Scope

This branch, `codex/evaluated-governance-baseline`, preserves a focused evaluation
and repair of the local baseline at `5043af4`. During publication on 2026-10-19,
the remote `codex/delta-cognitive-core` branch was found to contain 342 additional
commits, ending at `f8dcb92`. Those newer changes were not evaluated here and are
not overwritten or merged by this snapshot.

All capability assessments and measurements below apply to this evaluated
snapshot, not to the latest development branch or the entire historical test
tree. This is a reproducible baseline, not a claim that newer work lacks the
capabilities described as unproven here.

## What Currently Works

The active service path coordinates a bounded cognitive cycle: retrieve prior
experience, record an observation, rank context, reason, store the result,
produce reflection and learning proposals, assess explicit prediction outcomes,
consolidate eligible claims, and produce a non-executing agency proposal.

- Experience records are append-only and separate from derived semantic records.
- Prediction readers distinguish current state from historical revisions.
- Attention uses fixed relevance, confidence, and priority weights.
- Working memory packages current and retrieved context for reasoning.
- Reasoning can use deterministic routes or a model plugin.
- Learning produces structured proposals; consolidation governs promotion.
- The self-model derives summaries from other regions rather than owning facts.
- Simulation scores hypothetical options using existing records and heuristics.
- Agency proposes actions without independently acquiring execution authority.

There are two important execution paths: the service-oriented cognitive pipeline
and an older population/competition dynamics engine. The latter includes a
decision latch requiring sustained threshold satisfaction. That temporal
mechanism is distinct from ranking retrieved context. The mocked service
experiments below did not exercise or establish integration of those dynamics.

## Complexity And Design Assessment

| Dimension | Assessment of this snapshot |
| --- | --- |
| Software and integration | Substantial: interacting regions, persistent stores, revision lifecycles, and multiple execution paths |
| Active service algorithms | Mostly lexical matching, weighted scores, thresholds, templates, and deterministic rules |
| Demonstrated adaptation | Early: continuity and governance are better established than learning from independent outcomes |

The architecture has useful foundations: explicit authority boundaries,
replaceable reasoning components, provenance, and separation of observations
from derived knowledge. These make Delta a worthwhile experimental platform.

The main design weakness is breadth ahead of demonstrated adaptive behavior.
Names such as learning, reflection, and simulation identify responsibilities;
they do not establish that the corresponding mechanisms learn, understand, or
predict accurately. Fixed attention weights do not demonstrate learned salience,
and heuristic option scoring is not a learned model of environmental dynamics.
The original dynamics and the service pipeline also remain insufficiently
validated as one integrated cognitive mechanism.

The project does not need to be discarded or redesigned merely because these
gaps exist. However, complexity should earn its place through measurable
benefit. Earlier architectural descriptions that implied completeness, or that
treated the old latch as automatically subsumed by working memory, exceeded the
available evidence. This snapshot establishes no AGI claim.

## Evaluation Evidence

The configured test suite passed **86 tests with 1 skipped**. The optional
real-model test was not enabled. Isolated mocked experiments ran for 10, 25, 50,
and 100 ticks. At 100 ticks the repaired pipeline recorded:

| Measurement | Result |
| --- | --- |
| Experiences | 216; runtime event count reconciled with the store |
| Semantic records | 16 seeded concepts, with no internal-prompt promotions |
| Predictions | 16 open, with no self-confirmed outcomes |
| Contradictions | 0 |
| Relationships / learning records | 100 / 100 |
| Goals | 4 |
| Prediction accuracy | Unknown: no independent outcome was supplied |

Repairs addressed circular prediction validation, semantic over-suppression,
implicit supersession, stale revision readers, lagging counts, scheduler bounds,
inspection side effects, and lost model-escalation context. The evidence supports
specific governance and execution improvements, not general reliability or
intelligence. Learning-record counts are not counts of verified facts learned.

The idle benchmark supplied no new independent environmental evidence. Stable
knowledge counts are appropriate in that setting. Failure to demonstrate
adaptation here is neither proof of adaptation nor proof that it is impossible.
Long-duration reliability, real-model reasoning quality, and end-to-end adaptive
learning remain outside this evaluation.

## What Would Justify Further Development

The highest-value next evaluation is a controlled environment with independent
outcomes, changing conditions, and held-out trials. Measure prediction
calibration, adaptation, retention across sessions, false knowledge accumulation,
and decision stability under comparable resource budgets.

Compare a simple same-model memory baseline, the service pipeline with
evidence-driven learning, and that pipeline with competition/latch dynamics.
For the latch specifically, include a simple persistence or smoothing baseline:
stable decisions may help under noise, but may also delay correction or preserve
a wrong choice. Integration alone is not evidence of improvement.

Continue where experience demonstrably improves future behavior, and simplify
mechanisms that add complexity without benefit. A convincing adaptive experiment
would be more informative than adding several new cognitive regions. This is an
evaluation recommendation, not a claim that the experiment has been completed.

See `docs/SYSTEM_MECHANICS.md`, `docs/TRUST_REPORT.md`,
`docs/STABILITY_REPORT.md`, and `docs/evaluation/2026-10-19-stability.json` for
implementation details, limitations, and measured evidence. Resume development
by reading `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/UPDATE.md`.

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

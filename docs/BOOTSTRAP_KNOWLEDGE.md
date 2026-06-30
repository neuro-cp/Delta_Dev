# DELTA Bootstrap Knowledge

This document records the intentionally seeded foundational concepts used to
ground Delta's first runtime.

The bootstrap is not an encyclopedic import. It introduces cognitive primitives
that help the substrate organize later experience.

Every concept has:

- Origin: Bootstrap Knowledge
- Reason: Foundational Cognitive Primitive

## Concepts

| Concept | Reason |
| --- | --- |
| identity | Supports continuity of entities and Delta's self-model across change. |
| time | Supports sequence, memory, prediction, and planning. |
| object | Supports bounded entities with persistent properties. |
| cause and effect | Supports expectations, simulation, and prediction. |
| evidence | Supports provenance and confidence changes. |
| confidence | Supports graded belief instead of binary truth. |
| contradiction | Supports preserving and investigating conflicting claims. |
| goal | Supports agency and long-term direction. |
| action | Supports bounded change attempts and authority separation. |
| planning | Supports comparing strategies before action. |
| prediction | Supports expected future observations and later validation. |
| simulation | Supports non-executing hypothetical future evaluation. |
| learning | Supports transforming experience into better internal organization. |
| language | Supports symbolic communication and interpretation. |
| number | Supports quantity, order, measurement, and comparison. |
| curiosity | Supports investigation of uncertainty, contradictions, and missing links. |

## Bootstrap Goals

- Increase semantic knowledge coverage from foundational concepts.
- Investigate contradictions before relying on conflicting knowledge.
- Improve prediction accuracy by comparing expectations against later
  observations.
- Reduce uncertainty by turning repeated observations into semantic knowledge.

## Provenance Policy

Seeded semantic records use `creation_source=bootstrap:foundational`.

Seeded memories use `source=delta:bootstrap`.

Seeded goals use `origin=bootstrap`.

The loader is idempotent. Running it twice should not duplicate concepts or
bootstrap goals.

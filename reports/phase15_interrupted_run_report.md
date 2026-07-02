# Phase 15 Interrupted Broad-Corpus Run

Date: 2026-07-01

This report analyzes the intentionally interrupted Phase 15 broad-corpus
training run. The operator stopped the run, so this is not treated as a runtime
failure.

## Configuration

- Store: `.tmp/experiments/phase15_broad_corpus_training`
- Requested cycles: `300`
- Completed cycles observed before freeze: `190`
- Provider mode: qualified local GGUF providers
- Max generation tokens: `DELTA_MAX_TOKENS=192`
- Curriculum mode: broad corpus, randomized without replacement, balanced
- Saturation stop: enabled
- Final summary JSON from runner: not produced because the run was interrupted
- Reconstructed summary: `reports/phase15_interrupted_summary.json`

## Runtime Totals

| Metric | Value |
| --- | ---: |
| Runtime events / cycles | 190 |
| Memories | 397 |
| Latest relationships | 190 |
| Learning records | 190 |
| Semantic records, append-only | 472 |
| Latest semantic knowledge | 448 |
| Prediction records, append-only | 488 |
| Latest predictions | 471 |
| Latest contradictions | 46 |
| Open contradictions | 46 |

## Prediction Quality

| Metric | Value |
| --- | ---: |
| Latest predictions | 471 |
| Open predictions | 454 |
| Evaluated predictions | 17 |
| Supported predictions | 17 |
| Failed predictions | 0 |
| Accuracy over evaluated predictions | 1.0 |
| Validation coverage | 0.0361 |
| Failure rate | 0.0 |
| Average evidence score | 0.7276 |

## Growth Over Time

| Cycle | Semantic Records | Prediction Records | Contradictions | Active Profile |
| ---: | ---: | ---: | ---: | --- |
| 25 | 83 | 98 | 4 | information_synthesis |
| 50 | 149 | 164 | 9 | analogical_reasoning |
| 75 | 213 | 230 | 12 | failure_analysis |
| 100 | 273 | 290 | 17 | risk_assessment |
| 125 | 330 | 347 | 22 | negotiation |
| 150 | 379 | 395 | 31 | ethical_tradeoffs |
| 175 | 440 | 456 | 41 | experimental_design |
| 187 | 469 | 485 | 46 | contradiction |

## Curriculum Coverage

The run executed `190` unique objectives. The balanced scheduler distributed
cycles across the broad profile set:

| Profile | Cycles |
| --- | ---: |
| planning | 8 |
| contradiction | 8 |
| causal_reasoning | 8 |
| scientific_reasoning | 8 |
| tool_use | 8 |
| long_dependency | 7 |
| probabilistic_reasoning | 7 |
| resource_allocation | 7 |
| multi_agent_coordination | 7 |
| economics | 7 |
| medical_reasoning | 7 |
| mechanical_diagnosis | 7 |
| software_debugging | 7 |
| systems_engineering | 7 |
| cybersecurity_defense | 7 |
| experimental_design | 7 |
| ethical_tradeoffs | 7 |
| negotiation | 7 |
| risk_assessment | 7 |
| failure_analysis | 7 |
| counterfactual_reasoning | 7 |
| analogical_reasoning | 7 |
| cross_domain_transfer | 7 |
| hierarchical_planning | 7 |
| information_synthesis | 7 |
| hypothesis_revision | 7 |
| prediction | 2 |
| transfer | 1 |

## Findings

The broad corpus removed the immediate curriculum saturation bottleneck. The
previous repeated-objective 100-cycle run plateaued at `+19` latest semantic
knowledge records. This interrupted run reached `448` latest semantic knowledge
records after `190` cycles.

The new bottleneck is feedback throughput. Delta generated `471` latest
predictions, but only `17` were evaluated. Validation coverage fell to `0.0361`.
The system is now producing hypotheses much faster than it is observing outcomes
and validating them.

Contradiction pressure also increased. The broad corpus produced `46` open
contradictions. This is not runaway behavior at this scale, but it is a clear
signal that richer experience now stresses contradiction resolution.

The run did not stop because of saturation. It was operator-interrupted. The
partial store remains valid because all runtime state was isolated under
`.tmp/experiments`.

## Recommendation

Do not reduce prediction generation yet. The broad corpus is doing the job it
was meant to do: creating many new hypotheses and durable concepts. The next
experiment should add outcome observations or validation-oriented curriculum
passes that close open predictions, then measure whether validation coverage
improves without suppressing semantic growth.

Before rerunning 300 cycles, use a two-stage loop:

1. Run broad-corpus learning until semantic growth remains strong.
2. Run a validation curriculum against the open prediction backlog.

The next measured question should be: can Delta turn the newly generated
prediction backlog into evidence-backed belief revision?

# Curriculum Analysis

## Phase 14 Cognitive Calibration

Phase 14 froze provider infrastructure and tested whether better experience
selection improves cognitive pressure.

Baseline comparison:

| Run | Completed | Candidates | Utility | Information Gain | Surprise |
| --- | ---: | ---: | ---: | ---: | ---: |
| Provider smoke | 28/28 | 112 | 0.43 | 0.384 | 0.0804 |
| Cognitive calibration | 32/32 | 128 | 0.6081 | 0.5525 | 0.2422 |

The calibration run used `CalibrationCurriculumGenerator`, which selects
purpose-built objectives for prediction pressure, contradiction resolution,
belief revision, planning failure, transfer learning, and cross-domain
reasoning. Objectives are scored before scheduling using novelty, information
gain, prediction opportunity, belief challenge, surprise, and diversity.

Phase 14 run:

- run id: `calibration_20260701T040306Z`
- report: `reports/phase14_calibration_report.md`
- completed: `32/32`
- generated experience candidates: `128`
- average utility: `0.6081`
- average information gain: `0.5525`
- average surprise: `0.2422`

Capability utility:

| Capability | Count | Utility | Information Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| prediction | 8 | 0.6781 | 0.6133 | 0.35 |
| cross_domain | 8 | 0.6426 | 0.5859 | 0.2188 |
| contradiction | 4 | 0.5692 | 0.5257 | 0.25 |
| transfer | 4 | 0.5628 | 0.5134 | 0.1875 |
| planning | 8 | 0.5458 | 0.4911 | 0.1812 |

Highest-utility objective:

- `prediction-error-snow-route`
- utility: `0.7372`
- information gain: `0.669`
- surprise: `0.5125`

Lowest-utility objective:

- `planning-failure-hospital`
- utility: `0.4953`
- information gain: `0.4407`
- surprise: `0.175`

Interpretation:

- Curriculum selection is now a demonstrated lever. The same provider stack
  produced substantially higher utility and surprise when prompts were designed
  around prediction error, contradiction, and falsification.
- The result is not yet evidence of durable learning. It is evidence that
  better experiences create stronger learning pressure.
- Planning prompts need sharper outcome constraints. The hospital staffing
  objective produced lower pressure because providers tended to answer with
  generic contingency planning rather than explicit prediction and revision.
- Future calibration should keep expanding objective diversity while rejecting
  prompts that do not produce prediction, contradiction, or revision signals.

Next experiment:

Run a 100-experience calibration batch using only high-performing objective
families plus revised planning prompts that require explicit original-plan,
failure-evidence, revised-plan, and falsification fields.

## Governed Training Run

After calibration, Delta ran a local-provider governed cognitive training
shakedown and a 50-cycle governed training run through `CognitiveRuntime`.

50-cycle run:

- run id: `governed_training_20260701T042214Z`
- store: `data/training/phase14_governed_50`
- report: `reports/phase14_governed_training_50.md`
- cycles completed: `50/50`
- memories: `+100`
- relationships: `+50`
- learning records: `+50`
- semantic knowledge: `+1`
- predictions: `+8`
- contradictions: `+12`
- final prediction coverage: `0.9583`
- final prediction accuracy: `1.0`

The run proved that Delta can operate through local-provider governed cognitive
cycles, not just isolated provider inferences. It also exposed the next
bottleneck: learning records are being produced, but the semantic candidates are
too generic to produce strong durable knowledge growth.

Current conclusion:

Experience selection is no longer the only bottleneck. The next learning-loop
constraint is contentful knowledge formation from provider output, reflection,
and evidence.

## Semantic Extraction Follow-Up

The learning bottleneck was addressed by improving the existing `LearningEngine`
so successful provider outputs can emit reusable semantic candidates. This was
not a new cognitive region; it changed the conversion from successful cycle
output to learning proposal.

Comparison:

| Metric | Previous 50-cycle run | Semantic extraction run |
| --- | ---: | ---: |
| Learning records | +50 | +50 |
| Semantic knowledge | +1 | +19 |
| Predictions | +8 | +19 |
| Contradictions | +12 | 0 |
| Learning efficiency | 0.34 | 0.70 |
| Knowledge stability | 0.2941 | 1.0 |

Semantic extraction run:

- run id: `governed_training_20260701T042836Z`
- store: `data/training/phase14_governed_50_semantic_extraction`
- report: `reports/phase14_governed_training_50_semantic_extraction.md`
- cycles completed: `50/50`
- semantic knowledge: `+19`
- predictions: `+19`
- contradictions: `0`

Updated conclusion:

Semantic extraction is now productive at the 50-cycle scale. The next visible
bottleneck is prediction validation backlog: richer semantic knowledge generated
more predictions, leaving `20` open predictions at run end.

## 100-Cycle Semantic Extraction Run

The next gate was a 100-cycle governed training pass with the same semantic
extraction behavior.

- run id: `governed_training_20260701T043112Z`
- store: `data/training/phase14_governed_100_semantic_extraction`
- report: `reports/phase14_governed_training_100_semantic_extraction.md`
- cycles completed: `100/100`
- memories: `+200`
- relationships: `+100`
- learning records: `+100`
- semantic knowledge: `+19`
- predictions: `+19`
- contradictions: `0`
- open predictions: `20`

The 100-cycle run did not produce more latest semantic knowledge than the
50-cycle semantic extraction run. This suggests the repeated objective set
saturated quickly: more cycles over the same objectives created more experience
and learning records, but not more durable knowledge.

Updated conclusion:

The current training bottleneck is objective diversity and outcome validation,
not raw cycle count. Before 250+ cycles, Delta needs a larger non-repeating
objective set and explicit outcome observations for open predictions.

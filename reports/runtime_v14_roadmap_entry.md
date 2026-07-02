# Runtime V1.4 Roadmap Entry

## 1. Confirmed V1.3 Final State

Runtime V1.3 is complete.

- Model B remains the default runtime.
- HYB1 is retained only as a dormant/env-gated prototype.
- HYB1 is enabled only with `DELTA_RUNTIME_V13_HYB1_ENABLED=true`.
- HYB1 default parity passed.
- HYB1 enabled validation passed.
- No further Runtime V1.3 variant work should continue unless explicitly requested.

## 2. Current Roadmap Next Phase

The next roadmap phase should be:

`Runtime V1.4 - new live-safe signal research`

The existing docs contain one discrepancy: `docs/ROADMAP.md` still lists
`Runtime V1.2: Real Knowledge Evaluation` under `Current Phase`, but later
roadmap and update sections record Runtime V1.3 Model B, role compromise, and
HYB1 dormant-prototype completion. The substance of the current project state
therefore points past V1.3 even though the roadmap header is stale.

## 3. Why V1.4 Should Not Be More V1.3 Tuning

Runtime V1.3 exhausted the current live-safe signal set:

- activation rank
- attention selection
- `citation_context`
- query decomposition
- relation matching
- evidence contextualization
- planning/response preservation

The final V1.3 conclusion is that remaining misses are not safely recoverable
by more gate tuning with the current signals. Model B is the safe default, HYB1
is a dormant candidate, and further V1.3 optimization loops risk overfitting
same-topic noise behavior.

## 4. Candidate V1.4 Signal Families

V1.4 should investigate new evidence-role signals that explain why evidence
matters, not merely whether it is nearby:

- causal role
- evidence function
- claim polarity
- contradiction direction
- revision target
- planning dependency
- decision-criticality
- uncertainty role

## 5. Recommended First V1.4 Task

Run a report-only signal audit over the remaining V1.3 misses.

Primary question:

Which new evidence-role signal would have separated expected evidence from
same-topic noise without admitting additional unsafe reasoning evidence?

The audit should classify each remaining miss by which signal family would have
made the concept live-usable and whether that signal is derivable from existing
stored fields or requires new metadata.

## 6. Forbidden Work Carried Over From V1.3

Do not:

- run more Runtime V1.3 variants
- patch Model B defaults
- enable HYB1 by default
- loosen citation gates
- change learning, governance, promotion, normalization, provider prompts, or
  canonical storage
- change benchmark fixtures to make V1.3 look better
- run broad optimization loops before a V1.4 signal audit identifies a specific
  missing signal

## 7. Continuation Prompt For Next Codex Stream

We are working in `G:\Delta_Dev` on DELTA.

Runtime V1.3 is complete.

Final V1.3 state:

- Model B remains the default runtime.
- HYB1 is retained only as a dormant/env-gated prototype.
- HYB1 is enabled only with `DELTA_RUNTIME_V13_HYB1_ENABLED=true`.
- HYB1 default parity passed.
- HYB1 enabled validation passed.
- No V1.3 variant work should continue unless explicitly requested.

Next phase:

Runtime V1.4 - new live-safe signal research.

First task:

Create a report-only V1.4 signal audit over the remaining V1.3 misses. Determine
which new evidence-role signal families, such as causal role, evidence
function, claim polarity, contradiction direction, revision target, planning
dependency, decision-criticality, or uncertainty role, would separate expected
evidence from same-topic noise. Do not patch runtime behavior, do not modify
Model B defaults, do not enable HYB1 by default, and do not run more V1.3
optimization variants.

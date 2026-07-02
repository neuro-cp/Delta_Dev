# Phase 17 Prompt Artifact Provider Attribution

Date: 2026-07-01

This report checks whether Phase 17 prompt-artifact failures came from a
specific local provider.

Source:

- `reports/phase17_validation_report.json`
- `.tmp/experiments/phase15_broad_corpus_training`

Attribution method:

1. For each failed prediction, locate the source semantic concept.
2. Read its supporting evidence memory ids.
3. Find the `orchestration_output` memory.
4. Use that memory's provider tag.

This is best-effort attribution from experiment-store provenance. It does not
prove a provider is globally weak; it identifies provider/output patterns in
this specific Phase 15/17 dataset.

## Failed Predictions By Provider

| Provider | Failed Predictions |
| --- | ---: |
| Llama 3.1 8B Q4_K_M | 26 |
| Qwen2.5 7B Q4_K_M | 26 |
| Mistral 7B Q4_K_M | 4 |
| Phi-3.1 Mini Q4_K_M | 1 |

Raw failure count alone is misleading because the providers did not contribute
the same number of candidate concepts.

## Concept Denominators

| Provider | Candidate Concepts | Artifact Concepts | Artifact Rate | Failed Concepts | Failed Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen2.5 7B Q4_K_M | 270 | 52 | 0.1926 | 22 | 0.0815 |
| Llama 3.1 8B Q4_K_M | 125 | 40 | 0.3200 | 25 | 0.2000 |
| Mistral 7B Q4_K_M | 20 | 6 | 0.3000 | 4 | 0.2000 |
| Phi-3.1 Mini Q4_K_M | 17 | 1 | 0.0588 | 1 | 0.0588 |

Five failed predictions referenced revised concept ids rather than original
source concept ids and were not included in denominator-derived failed-rate
rows.

## Interpretation

Prompt-artifact failures are not from a single provider.

However, Llama produced a higher artifact rate and failed-concept rate than
Qwen in this dataset:

- Qwen artifact rate: `0.1926`
- Llama artifact rate: `0.3200`
- Qwen failed rate: `0.0815`
- Llama failed rate: `0.2000`

Mistral's artifact and failed rates are also high, but its sample is only `20`
candidate concepts, so that should be treated cautiously.

Phi produced the lowest artifact rate, but its sample is only `17` candidate
concepts.

## Profile Skew

Failed predictions were concentrated in profiles such as:

- cross-domain transfer
- long dependency
- hypothesis revision
- contradiction
- ethical tradeoffs
- hierarchical planning

This means provider behavior is confounded with routing. Llama handled many
long-dependency, transfer, analogical, and ethics-style tasks, which naturally
invite verbose explanatory outputs. Those outputs may be more likely to contain
answer scaffolding and prompt-shaped fragments.

## Conclusion

The prompt-artifact issue is partly an extraction/normalization problem and
partly a provider-output-style problem.

The strongest provider-specific hypothesis from this dataset is:

> Llama 3.1 produced a higher proportion of prompt-shaped or redundant semantic
> candidates than Qwen2.5 during broad-corpus training.

This should not trigger routing changes yet. The next controlled check should
run the same small objective set through Qwen, Llama, Mistral, and Phi, then
compare semantic extraction artifact rate directly.

## Recommendation

Before promotion governance:

1. Keep provider attribution in semantic-candidate quality reports.
2. Add extraction normalization for `answer`, `goal`, `evidence that would...`,
   and `testable prediction...` scaffolding.
3. Run a controlled provider artifact-rate comparison on identical prompts.
4. Penalize provider/capability pairings only after controlled comparison, not
   from this routed broad-corpus dataset alone.

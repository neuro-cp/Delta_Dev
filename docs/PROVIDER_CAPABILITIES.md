# Provider Capabilities

Provider capability evidence is local, empirical, and provisional. Delta should
not treat these values as permanent rankings.

## Backend Baseline

The current desktop provider pool uses CUDA-backed GGUF inference with one
provider loaded at a time.

| Provider | Qualified | GPU Layers | Tokens/sec | Peak VRAM |
| --- | --- | ---: | ---: | ---: |
| Llama 3.1 8B Q4_K_M | yes | 36 | 15.9165 | 6639 MB |
| Mistral 7B Q4_K_M | yes | 36 | 15.5774 | 6420 MB |
| Phi-3.1 Mini Q4_K_M | yes | 36 | 16.166 | 4822 MB |
| Qwen2.5 7B Q4_K_M | yes | 36 | 15.5569 | 5849 MB |

Source:

- `data/model_runtime/provider_capabilities.json`
- `reports/provider_backend_benchmark.md`

## Phase 14 Calibration Evidence

Run id: `calibration_20260701T040306Z`

| Provider | Count | Utility | Information Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| Qwen2.5 7B Q4_K_M | 8 | 0.6702 | 0.6087 | 0.3063 |
| Phi-3.1 Mini Q4_K_M | 8 | 0.6104 | 0.5578 | 0.2625 |
| Llama 3.1 8B Q4_K_M | 8 | 0.5919 | 0.5378 | 0.1875 |
| Mistral 7B Q4_K_M | 8 | 0.5599 | 0.5056 | 0.2125 |

Preliminary capability leaders:

| Capability | Provider | Utility | Count |
| --- | --- | ---: | ---: |
| prediction | Qwen2.5 7B Q4_K_M | 0.7184 | 2 |
| planning | Qwen2.5 7B Q4_K_M | 0.6663 | 2 |
| cross_domain | Qwen2.5 7B Q4_K_M | 0.6927 | 2 |
| contradiction | Mistral 7B Q4_K_M | 0.5927 | 1 |
| transfer | Llama 3.1 8B Q4_K_M | 0.6145 | 1 |

Interpretation:

- Qwen2.5 produced the highest average utility in this small calibration run,
  especially for prediction, planning, and cross-domain prompts.
- Mistral showed the strongest contradiction score, but only from one objective
  in this run.
- Llama and Phi remain competitive and should not be removed from routing based
  on this small sample.
- These values are evidence for the next calibration batch, not production
  routing law.

Next provider-specialization step:

Run capability-specific batches with at least 10 objectives per capability
before updating adaptive routing priors.

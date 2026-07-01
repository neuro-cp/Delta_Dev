# Phase 14 Cognitive Calibration Report

Run ID: `calibration_20260701T040306Z`

Completed: 32/32
Generated experience candidates: 128
Average utility: 0.6081
Average information gain: 0.5525
Average surprise: 0.2422

## By Provider

| Provider | Count | Utility | Info Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | 8 | 0.5919 | 0.5378 | 0.1875 |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | 8 | 0.5599 | 0.5056 | 0.2125 |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | 8 | 0.6104 | 0.5578 | 0.2625 |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | 8 | 0.6702 | 0.6087 | 0.3063 |

## By Capability

| Capability | Count | Utility | Info Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| contradiction | 4 | 0.5692 | 0.5257 | 0.25 |
| cross_domain | 8 | 0.6426 | 0.5859 | 0.2188 |
| planning | 8 | 0.5458 | 0.4911 | 0.1812 |
| prediction | 8 | 0.6781 | 0.6133 | 0.35 |
| transfer | 4 | 0.5628 | 0.5134 | 0.1875 |

## By Objective

| Objective | Count | Utility | Info Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| contradictory-policy | 4 | 0.5692 | 0.5257 | 0.25 |
| cross-domain-budget-weather | 4 | 0.6559 | 0.6014 | 0.25 |
| cross-domain-research-policy | 4 | 0.6293 | 0.5703 | 0.1875 |
| planning-failure-construction | 4 | 0.5964 | 0.5415 | 0.1875 |
| planning-failure-hospital | 4 | 0.4953 | 0.4407 | 0.175 |
| prediction-error-inventory | 4 | 0.6189 | 0.5576 | 0.1875 |
| prediction-error-snow-route | 4 | 0.7372 | 0.669 | 0.5125 |
| transfer-medical-to-maintenance | 4 | 0.5628 | 0.5134 | 0.1875 |

## Best Provider By Capability

| Capability | Provider | Utility | Info Gain | Surprise | Count |
| --- | --- | ---: | ---: | ---: | ---: |
| contradiction | mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | 0.5927 | 0.5454 | 0.25 | 1 |
| cross_domain | qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | 0.6927 | 0.6306 | 0.25 | 2 |
| planning | qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | 0.6663 | 0.598 | 0.3 | 2 |
| prediction | qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | 0.7184 | 0.6515 | 0.425 | 2 |
| transfer | meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | 0.6145 | 0.5639 | 0.25 | 1 |

## Notes

- This report is generated from experiment scheduler results joined to queue metadata.
- Generated experiences are candidates only; no direct semantic knowledge promotion is performed.
- Surprise is present but uneven; inspect the capability and objective tables before expanding the next run.

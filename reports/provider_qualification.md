# Provider Qualification Report

| Model | Loads | Inference | VRAM | tok/s | Recommended GPU Layers | Notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | yes | yes | 551.0 | 4.88 | 32 | Qualified |
| ministral-3-3b-instruct-2512-gguf-ministral-3-3b-instruct-2512-q4-k-m | no | no |  |  |  | No probed GPU-layer setting completed both load and inference. |
| ministral-3-3b-instruct-2512-gguf-ministral-3-3b-instruct-2512-q6-k | no | no |  |  |  | No probed GPU-layer setting completed both load and inference. |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | yes | yes | 545.0 | 5.09 | 32 | Qualified |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | yes | yes | 553.0 | 9.28 | 32 | Qualified |
| phi-4-mini-reasoning-gguf-phi-4-mini-reasoning-q4-k-m | no | no |  |  |  | No probed GPU-layer setting completed both load and inference. |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | yes | yes | 523.0 | 4.69 | 32 | Qualified |
| qwen2-5-vl-7b-instruct-gguf-qwen2-5-vl-7b-instruct-q4-k-m | no | no |  |  |  | No probed GPU-layer setting completed both load and inference. |
| qwen3-5-9b-gguf-qwen3-5-9b-q4-k-m | no | no |  |  |  | No probed GPU-layer setting completed both load and inference. |

Failures are recorded per model; one failure does not abort the suite.

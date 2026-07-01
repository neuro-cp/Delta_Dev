# Provider Health

| Model | Qualified | Stable | Memory Leak | GPU Layers | Context | tok/s | Failures | Last Successful Run |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | yes | yes | no | 32 | 8192 | 4.88 | 0 | layers=32, context=8192 |
| ministral-3-3b-instruct-2512-gguf-ministral-3-3b-instruct-2512-q4-k-m | no | no | no |  |  |  | 21 |  |
| ministral-3-3b-instruct-2512-gguf-ministral-3-3b-instruct-2512-q6-k | no | no | no |  |  |  | 21 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | yes | yes | no | 32 | 8192 | 5.09 | 0 | layers=32, context=8192 |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | yes | yes | no | 32 | 4096 | 9.28 | 0 | layers=32, context=4096 |
| phi-4-mini-reasoning-gguf-phi-4-mini-reasoning-q4-k-m | no | no | no |  |  |  | 21 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | yes | yes | no | 32 | 8192 | 4.69 | 0 | layers=32, context=8192 |
| qwen2-5-vl-7b-instruct-gguf-qwen2-5-vl-7b-instruct-q4-k-m | no | no | no |  |  |  | 28 |  |
| qwen3-5-9b-gguf-qwen3-5-9b-q4-k-m | no | no | no |  |  |  | 28 |  |

This file is Delta's provider maintenance log for the current hardware profile.

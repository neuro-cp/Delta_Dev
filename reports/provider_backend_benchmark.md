# Provider Backend Benchmark

| Model | Quant | Ctx | Layers | Status | Prompt Tok | Gen Tok | First Token | tok/s | RAM Base | RAM Peak | VRAM Base | VRAM Peak | GPU Util | CPU Util | Load | Unload | Notes |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | Q4_K_M | 8192 | 12 | gpu_offload_observed | 5 | 100 | 0.5266 | 6.4167 | 20.375 | 5540.6953 | 532.0 | 3384.0 | 81.0 |  | 1.7198 | 0.5318 |  |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | Q4_K_M | 8192 | 20 | gpu_offload_observed | 5 | 100 | 0.3583 | 7.6419 | 357.4766 | 5289.3516 | 630.0 | 4753.0 | 80.0 |  | 1.7696 | 0.4673 |  |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | Q4_K_M | 8192 | 28 | gpu_offload_observed | 5 | 100 | 0.1472 | 10.4384 | 361.3008 | 5036.3398 | 763.0 | 5860.0 | 41.0 |  | 2.0673 | 0.4659 |  |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | Q4_K_M | 8192 | 32 | gpu_offload_observed | 5 | 100 | 0.0635 | 13.9936 | 363.75 | 4910.5195 | 632.0 | 6490.0 | 49.0 |  | 2.2564 | 0.4988 |  |
| meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m | Q4_K_M | 8192 | 36 | gpu_offload_observed | 5 | 100 | 0.0416 | 15.9165 | 364.2148 | 4878.9961 | 644.0 | 6639.0 | 79.0 |  | 2.3391 | 0.439 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | Q4_K_M | 8192 | 12 | gpu_offload_observed | 5 | 100 | 0.5739 | 6.0427 | 365.0586 | 5192.4375 | 636.0 | 3154.0 | 89.0 |  | 1.0258 | 0.4076 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | Q4_K_M | 8192 | 20 | gpu_offload_observed | 5 | 100 | 0.3863 | 7.6549 | 369.6133 | 4937.9766 | 716.0 | 4391.0 | 45.0 |  | 1.3208 | 0.4025 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | Q4_K_M | 8192 | 28 | gpu_offload_observed | 5 | 100 | 0.1532 | 10.5839 | 370.4453 | 4683.2617 | 729.0 | 5729.0 | 81.0 |  | 1.6973 | 0.3869 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | Q4_K_M | 8192 | 32 | gpu_offload_observed | 5 | 100 | 0.0607 | 13.576 | 371.5664 | 4556.793 | 659.0 | 6201.0 | 45.0 |  | 1.8494 | 0.3892 |  |
| mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m | Q4_K_M | 8192 | 36 | gpu_offload_observed | 5 | 100 | 0.0376 | 15.5774 | 371.4844 | 4524.0156 | 643.0 | 6420.0 | 52.0 |  | 1.791 | 0.4026 |  |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | Q4_K_M | 4096 | 12 | gpu_offload_observed | 5 | 16 | 0.4087 | 7.1681 | 372.1367 | 3789.0 | 645.0 | 2425.0 | 51.0 |  | 0.7449 | 0.3505 |  |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | Q4_K_M | 4096 | 20 | gpu_offload_observed | 5 | 16 | 0.2622 | 9.2441 | 493.0234 | 3405.7109 | 715.0 | 3332.0 | 49.0 |  | 0.9567 | 0.3226 |  |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | Q4_K_M | 4096 | 28 | gpu_offload_observed | 5 | 16 | 0.1147 | 11.4564 | 493.2031 | 3023.5664 | 712.0 | 4255.0 | 96.0 |  | 1.1772 | 0.3157 |  |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | Q4_K_M | 4096 | 32 | gpu_offload_observed | 5 | 16 | 0.0529 | 14.5318 | 493.7891 | 2831.8125 | 721.0 | 4713.0 | 34.0 |  | 1.178 | 0.3424 |  |
| phi-3-1-mini-4k-instruct-gguf-phi-3-1-mini-4k-instruct-q4-k-m | Q4_K_M | 4096 | 36 | gpu_offload_observed | 5 | 16 | 0.0293 | 16.166 | 493.9141 | 2767.2383 | 741.0 | 4822.0 | 29.0 |  | 1.2108 | 0.281 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | Q4_K_M | 8192 | 12 | gpu_offload_observed | 5 | 50 | 0.4264 | 7.3923 | 493.3906 | 5025.1719 | 751.0 | 3348.0 | 33.0 |  | 1.3978 | 0.4881 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | Q4_K_M | 8192 | 20 | gpu_offload_observed | 5 | 100 | 0.2421 | 8.7731 | 491.2969 | 4897.6094 | 731.0 | 4506.0 | 44.0 |  | 1.6981 | 0.484 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | Q4_K_M | 8192 | 28 | gpu_offload_observed | 5 | 100 | 0.0627 | 13.6117 | 492.1133 | 4771.1289 | 730.0 | 5711.0 | 44.0 |  | 2.1987 | 0.4747 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | Q4_K_M | 8192 | 32 | gpu_offload_observed | 5 | 100 | 0.0359 | 15.3681 | 492.1328 | 4754.5312 | 730.0 | 5873.0 | 43.0 |  | 2.1868 | 0.4448 |  |
| qwen2-5-7b-instruct-gguf-qwen2-5-7b-instruct-q4-k-m | Q4_K_M | 8192 | 36 | gpu_offload_observed | 5 | 100 | 0.0361 | 15.5569 | 491.5977 | 4755.3086 | 732.0 | 5849.0 | 49.0 |  | 2.1837 | 0.489 |  |

Backend status is inferred from VRAM delta during a 100-token generation.

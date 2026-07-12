# TERRA Validation

## Role Limit

This is the implementation and validation report from the requested TERRA-led single-model cycle. The audit and exploration roles were performed as disciplined internal passes, not as independently switched models.

## Automated Validation

| Check | Result |
| --- | --- |
| Live Wikipedia, developmental cognition, operational autonomy, provider manager, and RC2 routing tests | `97 passed in 40.35s` |
| Continuous runtime tests | `9 passed in 2.03s` |
| Full live behavioral campaign | `373 scenarios`, `1,500 turns`, `20 families`, `0 pathologies`, `0 governance violations` |
| Python compilation of changed source and tests | PASS |
| JSON and secret scan | PASS; no credential assignment patterns found |
| Unsafe authority scan | PASS; only the existing Wikipedia `urlopen` and controlled local-model subprocess fallback were present; no runtime commit or push path found |

The continuous-runtime test file and controller were pre-existing dirty-tree files, so that nine-test result is validation context only and is excluded from the campaign commit.

## Bounded Real-Model Pilot

The pilot used actual local GGUF models with `DELTA_N_GPU_LAYERS=-1` and `DELTA_MAX_TOKENS=72`. It used one `ProviderManager(keep_loaded=True)` and the real `handle_live_chat` path.

| Step | Selected lane | Model | Inference latency | Wall time | Residency result |
| --- | --- | --- | --- | --- | --- |
| Conversation | reasoning_analysis | Meta-Llama-3.1-8B Q4_K_M | 6.6103 s | 8.8224 s | Llama resident |
| Planning | planning | Mistral-7B-Instruct-v0.3 Q4_K_M | 4.5331 s | 5.9306 s | Mistral resident; Llama unloaded |
| Conversation return | everyday_conversation | Meta-Llama-3.1-8B Q4_K_M | 6.4359 s | 7.6770 s | Llama resident; Mistral unloaded |

Before final cleanup, the manager had `load_count=3`, `unload_count=2`, and exactly one loaded model. Its final explicit unload produced `load_count=3`, `unload_count=3`, and no active model.

GPU samples moved from roughly 1.07 GB idle to 6.9-7.2 GB during inference. Each live response recorded `provider_calls_performed=false`, `external_retrieval_performed=false`, `memory_candidate=null`, and no canonical write.

The unavailable-model path was safely simulated through the real live bridge using a manager that raises an inference error. It cleared the request, recorded `MODEL_UNAVAILABLE`, and performed no provider, web, or memory action.

## Desktop Runtime Pilot

The actual DELTA desktop application was launched with bounded local-model settings.

1. Start Live Runtime succeeded and displayed warm Llama residency.
2. `Wikipedia: Fermi paradox` began a real text-only Wikipedia request. Pause was clicked while the worker was active; the UI immediately displayed a queued pause and remained responsive. After the response surfaced with provenance and a gated candidate, the controller was `PAUSED` with `PAUSED_FOR_REVIEW` health.
3. Resume succeeded. `Explain the concept of octarine in practical terms.` created a local-model consent request.
4. `ask the local model` started real Llama inference. Suspend was clicked while the worker was active; the UI displayed a queued suspend. The local answer surfaced with the explicit one-turn governance statement, then the controller was `SUSPENDED`.
5. Stop reached `SHUTDOWN` cleanly. The test application was closed to release the resident model.

## Governance Results

- No unrestricted web access: PASS. One operator-started, text-only Wikipedia call was used in the UI smoke.
- No provider authority: PASS. Local GGUF inference remained local and `provider_calls_performed=false`.
- No hidden retrieval: PASS. Retrieval was visible in transcript, payload, provenance, and status.
- No hidden persistence or memory write: PASS.
- No automatic canonical or noncanonical promotion: PASS.
- No runtime commit, push, deployment, or permission expansion authority: PASS.
- No purpose mutation: PASS.
- DELTA-75 scope: excluded from reads, edits, staging, commit, and report evidence.

## TERRA Validation Verdict

`CONFIRMED_AND_REPAIRED` for SOL-001 through SOL-003.

`CONFIRMED_BY_PILOT` for the real-model integration gap in SOL-004.

`CONFIRMED_AND_DEFERRED` for long-horizon proof and low-risk consolidation work.
